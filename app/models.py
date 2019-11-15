from app import db, login
from datetime import datetime
from time import time
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app


class User(UserMixin,db.Model):#пользователь (хранится в БД)
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(64),index=True,unique=True)
    email = db.Column(db.String(120),index=True,unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    views = db.relationship('View_log',backref='user',lazy='dynamic')
    last_seen = db.Column(db.DateTime,default=datetime.utcnow)
    role = db.Column(db.String(20),default='user', nullable=False)
    send_emails = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash,password)

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def get_reset_password_token(self,expires_in=3600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time()+expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token,current_app.config['SECRET_KEY'],algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Post(db.Model):#пост пользователя
    id = db.Column(db.Integer,primary_key=True)
    body = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


class Company(db.Model):#страховая компания
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(250),index=True,unique=True)
    alias = db.Column(db.String(128),unique=True)
    nonlife = db.Column(db.Boolean)
    alive = db.Column(db.Boolean)
    financials = db.relationship('Financial',backref='company',lazy='dynamic')
    premiums = db.relationship('Premium',backref='company',lazy='dynamic')
    claims = db.relationship('Claim',backref='company',lazy='dynamic')
    financials_per_month = db.relationship('Financial_per_month',backref='company',lazy='dynamic')
    premiums_per_month = db.relationship('Premium_per_month',backref='company',lazy='dynamic')
    claims_per_month = db.relationship('Claim_per_month',backref='company',lazy='dynamic')
    all_names = db.relationship('Company_all_names',backref='company',lazy='dynamic')

    def __repr__(self):
        return '<Company {}>'.format(self.name)


class Company_all_names(db.Model):#все наименования СК (на случай переименования)
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(250),index=True,unique=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))

    def __repr__(self):
        return '<CompanyAllName {}>'.format(self.name)


class Insclass(db.Model):#класс страхования
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True)
    fullname = db.Column(db.String(256))
    alias = db.Column(db.String(128),unique=True)
    nonlife = db.Column(db.Boolean)
    obligatory = db.Column(db.Boolean)
    voluntary_personal = db.Column(db.Boolean)
    voluntary_property = db.Column(db.Boolean)
    premiums = db.relationship('Premium',backref='insclass',lazy='dynamic')
    claims = db.relationship('Claim',backref='insclass',lazy='dynamic')
    premiums_per_month = db.relationship('Premium_per_month',backref='insclass',lazy='dynamic')
    claims_per_month = db.relationship('Claim_per_month',backref='insclass',lazy='dynamic')
    all_names = db.relationship('Insclass_all_names',backref='insclass',lazy='dynamic')

    def __repr__(self):
        return '<Class {}>'.format(self.name)


class Insclass_all_names(db.Model):#все наименования классов
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True)
    fullname = db.Column(db.String(256))
    insclass_id = db.Column(db.Integer,db.ForeignKey('insclass.id'))

    def __repr__(self):
        return '<InsclassAllName {}>'.format(self.name)


class Indicator(db.Model):#класс страхования
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True)
    fullname = db.Column(db.String(256))
    description = db.Column(db.String(256))
    flow = db.Column(db.Boolean)
    basic = db.Column(db.Boolean)
    financials = db.relationship('Financial',backref='indicator',lazy='dynamic')
    financials_per_month = db.relationship('Financial_per_month',backref='indicator',lazy='dynamic')

    def __repr__(self):
        return '<Indicator {}>'.format(self.name)


class Upload(db.Model):#загрузка excel файла
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True)
    file_type = db.Column(db.String(20))
    dict_type = db.Column(db.String(20))
    data_type = db.Column(db.String(20))
    file_name = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
    report_date = db.Column(db.DateTime,index=True)

    def __repr__(self):
        return '<Upload {}>'.format(self.name)


class Financial(db.Model):#основные фин. показатели
    id = db.Column(db.Integer,primary_key=True)
    report_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    indicator_id = db.Column(db.Integer,db.ForeignKey('indicator.id'))
    value = db.Column(db.Float)


class Premium(db.Model):#премии
    id = db.Column(db.Integer,primary_key=True)
    report_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    insclass_id = db.Column(db.Integer,db.ForeignKey('insclass.id'))
    value = db.Column(db.Float)


class Claim(db.Model):#выплаты
    id = db.Column(db.Integer,primary_key=True)
    report_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    insclass_id = db.Column(db.Integer,db.ForeignKey('insclass.id'))
    value = db.Column(db.Float)


class Financial_per_month(db.Model):#основные фин. показатели за месяц
    id = db.Column(db.Integer,primary_key=True)
    beg_date = db.Column(db.DateTime,index=True)
    end_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    indicator_id = db.Column(db.Integer,db.ForeignKey('indicator.id'))
    value = db.Column(db.Float)


class Premium_per_month(db.Model):#премии за месяц
    id = db.Column(db.Integer,primary_key=True)
    beg_date = db.Column(db.DateTime,index=True)
    end_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    insclass_id = db.Column(db.Integer,db.ForeignKey('insclass.id'))
    value = db.Column(db.Float)


class Claim_per_month(db.Model):#выплаты
    id = db.Column(db.Integer,primary_key=True)
    beg_date = db.Column(db.DateTime,index=True)
    end_date = db.Column(db.DateTime,index=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    insclass_id = db.Column(db.Integer,db.ForeignKey('insclass.id'))
    value = db.Column(db.Float)


class Compute(db.Model):#выполненные перерасчёты
    id = db.Column(db.Integer,primary_key=True)
    data_type = db.Column(db.String(20))
    beg_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


class View_log(db.Model):#лог - какие view запускал пользователь
    id = db.Column(db.Integer,primary_key=True)
    view_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


class Hint(db.Model):#всплывающая подсказка
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True,nullable=False)
    text = db.Column(db.String(2000),nullable=False)
    title = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))
