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
