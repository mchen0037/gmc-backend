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

root = "/home/mighty/gmc/gmc-backend"

def createModel(user):
    print(user)
    path = root + '/models/' + str(user) + '''.csv'''
    r_query = "dat = read.csv(\'" + path + "\')"
    dat = ro.r(r_query)
    ro.r("""attach(dat)""")
    # this comment is to commemorate the 1 hour you spent frekaing out at R because you literally
    # passed the same in the good and bad data from your front end... holy..

    model = ro.r("""
    logModelA =
    glm(class~danceability+energy+key+loudness+mode+speechiness+acousticness+instrumentalness+liveness+valence+tempo+duration_ms+time_signature,
    data=dat,
    family='binomial') """)

    ro.r("""
    save(logModelA, file = "models/""" + str(user) + """.rda")
    """)

def prediction(user):
    # user = "nothing_faith"
    file = """load('/home/mighty/gmc/gmc-backend/models/""" + user + """.rda')"""
    test = """read.csv('/home/mighty/gmc/gmc-backend/models/test.csv')"""

    ro.r("""models = """ + file)
    print(ro.r("""logModelA"""))
    ro.r("""new_dat = """ + test)

    ro.r("""logModel.probs = predict(logModelA, new_dat, type='response')""")
    # print(ro.r("""logModel.probs"""))
    ro.r("""logModel.preds=rep('bad', dim(new_dat)[1])""")
    ro.r("""logModel.preds[logModel.probs > 0.5]='good'""")
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
        col.append('good')
    df['class'] = Series(col)

    df2 = pandas.DataFrame(eval(str(BAD_AUDIO_FEATURES)))
    col = []
    for x in range(df2.shape[0]):
        col.append('bad')
    df2['class'] = Series(col)

    frames = [df, df2]
    data = pandas.concat(frames, sort=False)

    data.to_csv('models/' + str(USER) + '.csv')

    createModel(USER)

    # do something with the audio features. i.e: Call RPy2 and train model.
    return jsonify({"result": True})

@app.route("/models/<string:user>", methods=['GET'])
def models(user):
    # print(root + "/models/" + user + ".rda")
    fileExists = (os.path.isfile(root + "/models/" + user + ".rda"))
    return jsonify({"result": fileExists})

@app.route("/delete/<string:user>", methods=['GET'])
def delete(user):
    os.remove(root + "/models/" + user + ".rda")
    os.remove(root + "/models/" + user + ".csv")
    return jsonify({"result": True})

@app.route("/all", methods=['GET'])
def all():
    l = os.listdir()
    print(l)
    return ('yo')

@app.route("/predict/<string:user>", methods=['POST'])
def predict(user):
    print(user)
    AUDIO_FEATURES = request.get_json()["test"]

    df = pandas.DataFrame(eval(str(AUDIO_FEATURES)))
    col = []
    for x in range(df.shape[0]):
        col.append('bad')
    df['class'] = Series(col)

    df.to_csv('models/test.csv')

    res = prediction(user)
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
