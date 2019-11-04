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
    TMP_UPLOAD_FOLDER = 'tmp'#path to uploaded files (temporary)
    STATIC_FOLDER = 'static'#static files
    TMP_STATIC_FOLDER = 'static_tmp'#static files (temporary)
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
                        {'id':5,'name':'motor'},
                        {'id':6,'name':'company_profile_file'},
                        {'id':7,'name':'class_profile_file'},
                        {'id':8,'name':'peers_review_file'},
                        {'id':9,'name':'ranking_file'},
                        {'id':10,'name':'motor_file'},
                        {'id':11,'name':'form_profile'},
                        {'id':12,'name':'form_profile_file'}]
    DICT_TYPES = [('CompaniesList','Список компаний'),
                    ('ClassesList','Список классов'),
                    ('IndicatorsList','Список показателей')]#типы справочников
    DATA_TYPES = [('Premiums','Страховые премии'),
                    ('Claims','Страховые выплаты'),
                    ('Financials','Основные финансовые показатели'),
                    ('Prudentials','Пруденциальные нормативы')]#типы данных
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    INS_FORMS = [('obligatory','Обязательное страхование'),
                    ('voluntary_personal','Добровольное личное страхование'),
                    ('voluntary_property','Добровольное имущественное страхование')]#формы страхования
