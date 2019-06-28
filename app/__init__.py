from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os



db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    login.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    with app.app_context():
        from app.errors import bp as errors_bp
        app.register_blueprint(errors_bp)
        from app.auth import bp as auth_bp
        app.register_blueprint(auth_bp,url_prefix='/auth')
        from app.class_profile import bp as class_profile_bp
        app.register_blueprint(class_profile_bp)
        from app.admin import bp as admin_bp
        app.register_blueprint(admin_bp)
        from app.company_peers_profile import bp as company_peers_profile_bp
        app.register_blueprint(company_peers_profile_bp)
        from app.main import bp as main_bp
        app.register_blueprint(main_bp)
        from app.ranking import bp as ranking_bp
        app.register_blueprint(ranking_bp)
        from app.motor import bp as motor_bp
        app.register_blueprint(motor_bp)
    return app


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

from app import models



"""
from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel
from app.auth import auth
from app.admin import admin
from app.class_profile import class_profile
from app.company_peers_profile import company_peers_profile
from app.errors import errors
from app.main import main
from app.ranking import ranking

#import flask_excel as excel


db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'
bootstrap = Bootstrap()
moment = Moment()
babel = Babel()
#excel.init_excel()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    #db.init_app(app)
    #login.init_app(app)
    #bootstrap.init_app(app)
    #moment.init_app(app)
    #babel.init_app(app)
    #excel.init_app(app)
    with app.app_context():
        db.init_app(app)
        login.init_app(app)
        bootstrap.init_app(app)
        moment.init_app(app)
        babel.init_app(app)        
        app.register_blueprint(errors)        
        app.register_blueprint(auth,url_prefix='/auth')    
        app.register_blueprint(class_profile)    
        app.register_blueprint(admin)    
        app.register_blueprint(company_peers_profile)    
        app.register_blueprint(ranking)    
        app.register_blueprint(main)
    
    if not app.debug:    
        if not os.path.exists('logs'):
            os.mkdir('logs')
        #writing errors to log file
        file_handler = RotatingFileHandler('logs/insmkt.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s: %(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Ins mkt app startup')
    
    return app




@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

from app import models
"""