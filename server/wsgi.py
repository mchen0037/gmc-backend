from whitenoise import WhiteNoise

from server import app

application = WhiteNoise(app)
application.add_files('static/', prefix='static/')
