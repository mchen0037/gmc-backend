from flask import Flask
from flask_cors import CORS, cross_origin
from flask import flash, redirect, render_template, request, session, abort, make_response
from flask import jsonify
from flask import request
import subprocess
import os
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
    # print(ro.r("""summary(dat)"""))
    # print(ro.r("""names(dat)"""))
    # print(ro.r("""acousticness"""))


    # this comment is to commemorate the 1 hour you spent frekaing out at R because you literally
    # passed the same in the good and bad data from your front end... holy..

    model = ro.r("""
    logModelA =
    glm(class~danceability+energy+key+loudness+mode+speechiness+acousticness+instrumentalness+liveness+valence+tempo+duration_ms+time_signature,
    data=dat,
    family='binomial') """)

    # print(model)

    ro.r("""
    save(logModelA, file = "models/""" + str(user) + """.rda")
    """)

def predict():
    ro.r("""load('/home/mighty/gmc/gmc-backend/models/')""")
    print(ro.r("""model"""))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret'
# //cross origin request -security stuff
CORS(app)

@app.route("/train", methods=['POST'])
def train():
    USER = request.get_json()["user"]
    GOOD_AUDIO_FEATURES = request.get_json()["good"]
    BAD_AUDIO_FEATURES = request.get_json()["bad"]

    # print(type(GOOD_AUDIO_FEATURES))
    # print(GOOD_AUDIO_FEATURES)

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

    data.to_csv('models/' + str(USER) + '.csv')

    createModel(USER)

    # do something with the audio features. i.e: Call RPy2 and train model.
    return jsonify({"result": True})

@app.route("/predict/<string:user", methods=['GET'])
def predict():
    print('hello')
    return('yo')


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
