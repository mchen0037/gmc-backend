from flask import Flask
from flask_cors import CORS, cross_origin
from flask import flash, redirect, render_template, request, session, abort, make_response
from flask import jsonify
from flask import request
import subprocess
import os
from os import listdir
import pandas
from pandas import Series
import rpy2.robjects as ro
import psycopg2

from rpy2.robjects.packages import importr # import R's "base" package
base = importr('base')
from rpy2.robjects import pandas2ri # install any dependency package if you get error like "module not found"
pandas2ri.activate()

root = "/home/mighty/gmc/gmc-backend"
DBNAME = os.environ["GMC_DBNAME"]
HOST = os.environ["GMC_HOST"]
PORT = os.environ["GMC_PORT"]
DBUSER = os.environ["GMC_USER"]
PASSWORD = os.environ["GMC_PASSWORD"]

def createModel(user, data):
    # print(user, data)
    # convert the pandas dataframe into a R dataframe
    dat = pandas2ri.py2ri(data)
    ro.globalenv['dat'] = dat

    ro.globalenv['DBNAME'] = DBNAME
    ro.globalenv['HOST'] = HOST
    ro.globalenv['PORT'] = PORT
    ro.globalenv['DBUSER'] = DBUSER
    ro.globalenv['PASSWORD'] = PASSWORD
    ro.globalenv['USER'] = user


    ro.r("""
        print(dim(dat))
    """)
    # path = root + '/models/' + str(user) + '''.csv'''
    # r_query = "dat = read.csv(\'" + path + "\')"
    # ro.r(r_query)
    ro.r("""
        attach(dat)
    """)
    # this comment is to commemorate the 1 hour you spent frekaing out at R because you literally
    # passed the same in the good and bad data from your front end... holy..
    ro.r("""
        logModelA =
        glm(class~danceability+energy+key+loudness+mode+speechiness+acousticness+instrumentalness+liveness+valence+tempo+duration_ms+time_signature,
        data=dat,
        family='binomial')
    """)
    ro.r("""
        require(RPostgreSQL)
        drv <- dbDriver("PostgreSQL")
    """)

    # Now store the model into a database.
    ro.r("""
        con <- dbConnect(drv, dbname=DBNAME,
                    host=HOST,
                    port=PORT,
                    user=DBUSER,
                    password=PASSWORD)

        # serialize the model into bytes
        x <- serialize(logModelA, NULL)

        # save the raw vector as a character vector instead; paste it as a comma-separated string
        x_conv <- as.character(x)
        x_collapse = paste(x_conv, collapse=",")
        x_collapse = paste("{", x_collapse,"}", sep="")


        query = sprintf("INSERT INTO test_bytea VALUES ('%s','%s')", USER, x_collapse)
        res <- dbSendQuery(con, statement=query);
    """)

def prediction(user, data):

    dat = pandas2ri.py2ri(data)
    ro.globalenv['new_dat'] = dat

    ro.globalenv['DBNAME'] = DBNAME
    ro.globalenv['HOST'] = HOST
    ro.globalenv['PORT'] = PORT
    ro.globalenv['DBUSER'] = DBUSER
    ro.globalenv['PASSWORD'] = PASSWORD
    ro.globalenv['USER'] = user

    # Retrieve the model from the database
    ro.r("""
        require(RPostgreSQL)
        drv <- dbDriver("PostgreSQL")
    """)

    ro.r("""
        con <- dbConnect(drv, dbname=DBNAME,
                    host=HOST,
                    port=PORT,
                    user=DBUSER,
                    password=PASSWORD)

        query = sprintf("SELECT * FROM test_bytea WHERE id='%s'", USER)

        res <- dbSendQuery(con, statement=query);
        z = dbFetch(res)

        y = strsplit(z$model, ",")[[1]]
        y[1] = substring(y[1], 2)
        y[length(y)] = substring(y[length(y)], 1, nchar(y[length(y)]) - 1)

        raw_model = as.raw(as.hexmode(y))
        logModelA = unserialize(raw_model)

    """)


    # file = """load('/home/mighty/gmc/gmc-backend/models/""" + user + """.rda')"""
    # test = """read.csv('/home/mighty/gmc/gmc-backend/models/test.csv')"""
    #
    # ro.r("""models = """ + file)
    # print(ro.r("""logModelA"""))
    # ro.r("""new_dat = """ + test)

    ro.r("""logModel.probs = predict(logModelA, new_dat, type='response')""")
    print(ro.r("""logModel.probs"""))
    ro.r("""logModel.preds=rep('bad', dim(new_dat)[1])""")
    ro.r("""logModel.preds[logModel.probs > 0.25]='okay'""")
    ro.r("""logModel.preds[logModel.probs > 0.75]='good'""")
    c = ro.r("""logModel.preds""")

    list = []
    for x in c:
        list.append(x)

    return list


app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret'
# //cross origin request -security stuff
CORS(app)

@app.route("/train", methods=['POST'])
def train():
    USER = request.get_json()["user"]
    GOOD_AUDIO_FEATURES = request.get_json()["good"]
    BAD_AUDIO_FEATURES = request.get_json()["bad"]

    # this is so janky please fix this lol
    df = pandas.DataFrame(eval(str(GOOD_AUDIO_FEATURES)))
    col = []
    for x in range(df.shape[0]):
        col.append(1)
    df['class'] = Series(col)

    df2 = pandas.DataFrame(eval(str(BAD_AUDIO_FEATURES)))
    col = []
    for x in range(df2.shape[0]):
        col.append(0)
    df2['class'] = Series(col)

    frames = [df, df2]
    data = pandas.concat(frames, sort=False)

    # Rather than saving a .csv file, how can we directly use the pandas data
    # frame from python and send it to the R kernel to create the model?
    # data.to_csv('models/' + str(USER) + '.csv')

    createModel(USER, data)

    # do something with the audio features. i.e: Call RPy2 and train model.
    return jsonify({"result": True})

@app.route("/models/<string:user>", methods=['GET'])
def models(user):
    print("Checking for model for ", user, "...")

    conn = psycopg2.connect(host=HOST ,database=DBNAME, user=DBUSER, password=PASSWORD)
    cur = conn.cursor()

    query = """ SELECT id FROM test_bytea WHERE id = %s"""
    cur.execute(query, (user,))

    res = cur.fetchone()
    if res is None:
        print("No model for ", user, " exists. Create a new model.")
        fileExists = False
    else:
        print("A model exists for ", user, "! Welcome back!")
        fileExists = True

    cur.close()

    return jsonify({"result": fileExists})

@app.route("/delete/<string:user>", methods=['GET'])
def delete(user):
    conn = psycopg2.connect(host=HOST ,database=DBNAME, user=DBUSER, password=PASSWORD)
    cur = conn.cursor()

    query = """DELETE FROM test_bytea WHERE id = %s"""
    cur.execute(query, (user,))
    print("Deleted ", cur.rowcount, " rows in the DB.")

    conn.commit()
    cur.close()

    return jsonify({"result": True})

@app.route("/all", methods=['GET'])
def all():
    l = os.listdir()
    print(l)
    return ('yo')

@app.route("/predict/<string:user>", methods=['POST'])
def predict(user):

    AUDIO_FEATURES = request.get_json()["test"]

    df = pandas.DataFrame(eval(str(AUDIO_FEATURES)))
    col = []
    for x in range(df.shape[0]):
        col.append('bad')
    df['class'] = Series(col)

    # df.to_csv('models/test.csv')

    res = prediction(user, df)
    print(res)

    return jsonify({"results": res})


# localhost:4000/getusername is the url
# This route can recieve get requests or post requests
# the function below handles the request.

# http://localhost:4000/username?id=1 args is whatever is after the questionmark

# http://localhost:4000/username/1
# @app.route("/username", methods = ['POST'])
# def getUser():
#     # print(request.args.get('id'))
#     userID = request.get_json()["userID"]
#     print(request.get_json()["userID"])
#
#     # return jsonify({"username": "yoboimightychen", "id": request.args.get('id')});
#     # jsonify({"username": "yoboimightychen", "id": id}
#     return


# @app.route("/login", methods = ['POST'])
# def login():
#     print(request.get_json()["userID"])
#
#     return "got stuff"
#     # return jsonify(request.json)


# @app.route("/createuser")
# def createUser():
#     # user = request.args.get('id')
#     user_name = request.args.get('name')
#
#     # query = "INSERT INTO "
#
#     print(app.secret_key)
#     return 'hey';


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True,host='0.0.0.0', port=4000)
