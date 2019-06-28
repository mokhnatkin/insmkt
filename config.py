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
    STATIC_FOLDER = 'static'#static files
    MAX_CONTENT_PATH = 10485760#max size of uploaded file - 10MB
    ALLOWED_EXTENSIONS = set(['xls', 'xlsx'])#extensions allowed for file uploads
    #Echange server conf
    EXCHANGE_USERNAME = os.environ.get('EXCHANGE_USERNAME')
    EXCHANGE_PASSWORD = os.environ.get('EXCHANGE_PASSWORD')
    EXCHANGE_SERVER = os.environ.get('EXCHANGE_SERVER')
    EXCHANGE_PRIMARY_SMTP_ADDRESS = os.environ.get('EXCHANGE_PRIMARY_SMTP_ADDRESS')
    #loggin
    VIEWS_FOR_LOGGING = [{'id':0,'name':'index'},
                        {'id':1,'name':'company_profile'},
                        {'id':2,'name':'class_profile'},
                        {'id':3,'name':'peers_review'},
                        {'id':4,'name':'ranking'},
                        {'id':5,'name':'motor'}]
