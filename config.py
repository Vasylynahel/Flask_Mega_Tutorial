#  app = Flask(__name__)
#  app.config['SECRET_KEY'] = 'you-will-never-guess'
# ...and more variables here as needed
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
