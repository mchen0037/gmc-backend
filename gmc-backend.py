from flask import Flask
from flask_cors import CORS, cross_origin
from flask import flash, redirect, render_template, request, session, abort, make_response
from flask import jsonify
from flask import request
import subprocess
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super secret'
# //cross origin request -security stuff
CORS(app)

# localhost:4000/getusername is the url
# This route can recieve get requests or post requests
# the function below handles the request.

# http://localhost:4000/username?id=1 args is whatever is after the questionmark

# http://localhost:4000/username/1
@app.route("/username/<int:id>", methods = ['GET'])
def getUser(id):
    # print(request.args.get('id'))
    print(id)
    # return jsonify({"username": "yoboimightychen", "id": request.args.get('id')});
    return jsonify({"username": "yoboimightychen", "id": id})


@app.route("/login", methods = ['POST'])
@cross_origin()
def login():
    print(request.json)


    return jsonify(request.json)


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
