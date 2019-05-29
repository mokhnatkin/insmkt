from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://insmkt:fjEidk89@localhost:3306/insmkt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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


Insclass_all_names.__table__.drop(db.session.bind)
#Insclass.__table__.create(db.session.bind, checkfirst=True)
#Insclass_all_names.__table__.create(db.session.bind, checkfirst=True)