from flask_wtf import FlaskForm
from wtforms import TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length



class PostForm(FlaskForm):#опубликовать пост
    post = TextAreaField('Ваш пост:',validators=[DataRequired(), Length(min=1,max=500)])
    submit = SubmitField('Опубликовать')


class ConfirmSwitchSendEmailsForm(FlaskForm):#отписаться от рассылок
    submit = SubmitField('Подтвердить')