import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir,'.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY')
    POSTS_PER_PAGE = 10#number of posts per page (pagination)
    #SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.environ.get('SQLALCHEMY_TRACK_MODIFICATIONS')    
    LANGUAGES = ['ru','en']
    #file upload
    UPLOAD_FOLDER = 'files_uploaded'#path to uploaded files
    MAX_CONTENT_PATH = 10485760#max size of uploaded file - 10MB
    ALLOWED_EXTENSIONS = set(['xls', 'xlsx'])#extensions allowed for file uploads
    