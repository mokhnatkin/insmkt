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


class User(UserMixin,db.Model):#пользователь (хранится в БД)
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(64),index=True,unique=True)
    email = db.Column(db.String(120),index=True,unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post',backref='author',lazy='dynamic')
    views = db.relationship('View_log',backref='user',lazy='dynamic')
    last_seen = db.Column(db.DateTime,default=datetime.utcnow)
    role = db.Column(db.String(20),default='user', nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash,password)

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def get_reset_password_token(self,expires_in=3600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time()+expires_in},
            app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')
    
    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token,app.config['SECRET_KEY'],algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)



class View_log(db.Model):#лог - какие view запускал пользователь
    id = db.Column(db.Integer,primary_key=True)
    view_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime,default=datetime.utcnow)


#Insclass.__table__.drop(db.session.bind)
View_log.__table__.create(db.session.bind, checkfirst=True)
#Insclass_all_names.__table__.create(db.session.bind, checkfirst=True)