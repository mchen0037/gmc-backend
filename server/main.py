import os

from server import app

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.debug = True
    app.run()
