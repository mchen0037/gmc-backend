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

import pickle
import codecs

from patsy import dmatrices
import numpy as np
from sklearn.linear_model import LogisticRegression

import pickle

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

    print (data.columns)

    y, X = dmatrices('qual~danceability+energy+key+loudness+mode+speechiness+acousticness+instrumentalness+liveness+valence+tempo+duration_ms+time_signature', data, return_type="dataframe")

    y = np.ravel(y)

    model = LogisticRegression()
    model.fit(X,y)

    model_bytes = codecs.encode(pickle.dumps(model), "base64").decode()

    conn = psycopg2.connect(host=HOST ,database=DBNAME, user=DBUSER, password=PASSWORD)
    cur = conn.cursor()

    query = """INSERT INTO test_bytea VALUES(%s, %s)"""
    cur.execute(query, (user, model_bytes))

    conn.commit()
    cur.close()


def prediction(user, data):



    # Retrieve the model from the database
    conn = psycopg2.connect(host=HOST ,database=DBNAME, user=DBUSER, password=PASSWORD)
    cur = conn.cursor()

    query = """SELECT model FROM test_bytea WHERE id=%s"""
    cur.execute(query, ('nothing_faith',))
    b = cur.fetchone()

    new_model = pickle.loads(codecs.decode(b[0].encode(), "base64"))

    conn.commit()
    cur.close()

    y, X = dmatrices('qual ~ danceability + energy + key + loudness + mode + speechiness + acousticness + instrumentalness + liveness + valence + tempo + duration_ms + time_signature',
                 data, return_type="dataframe")

    preds = new_model.predict(X)

    # ro.r("""logModel.probs = predict(logModelA, new_dat, type='response')""")
    # print(ro.r("""logModel.probs"""))
    # ro.r("""logModel.preds=rep('bad', dim(new_dat)[1])""")
    # ro.r("""logModel.preds[logModel.probs > 0.25]='okay'""")
    # ro.r("""logModel.preds[logModel.probs > 0.75]='good'""")
    # c = ro.r("""logModel.preds""")

    # the sk-learn model is much different from the R version, figure out why
    # later, but the software engineering aspect is more improtant right now.

    list = []
    for x in preds:
        if x == 1:
            list.append('good')
        else:
            list.append('bad')

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
    df['qual'] = Series(col)

    col = []
    df2 = pandas.DataFrame(eval(str(BAD_AUDIO_FEATURES)))
    for x in range(df2.shape[0]):
        col.append(0)
    df2['qual'] = Series(col)

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
    df['qual'] = Series(col)

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
