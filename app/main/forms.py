from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
                    TextAreaField, FileField, SelectField, DateTimeField, \
                    SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from app.models import User, Company, Insclass
from wtforms.fields.html5 import DateField
from flask import flash, g
from datetime import datetime



class PostForm(FlaskForm):#опубликовать пост
    post = TextAreaField('Ваш пост:',validators=[DataRequired(), Length(min=1,max=500)])
    submit = SubmitField('Опубликовать')