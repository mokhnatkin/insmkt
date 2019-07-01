from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://insmkt:fjEidk89@localhost:3306/insmkt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)




class Hint(db.Model):#всплывающая подсказка
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(128),index=True,unique=True,nullable=False)
    text = db.Column(db.String(2000),nullable=False)
    url = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


#Insclass.__table__.drop(db.session.bind)
Hint.__table__.create(db.session.bind, checkfirst=True)
#Insclass_all_names.__table__.create(db.session.bind, checkfirst=True)