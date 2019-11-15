from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField                    
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from app.models import User
from wtforms.fields.html5 import DateField


class LoginForm(FlaskForm):#вход
    username = StringField('Логин',validators=[DataRequired()])
    password = PasswordField('Пароль',validators=[DataRequired()])
    remember_me = BooleanField('Запомни меня')
    submit = SubmitField('Вход')


class ResetPasswordRequestForm(FlaskForm):#ввод email для восстановления пароля
    email = StringField('E-mail',validators=[DataRequired(), Email()])
    submit = SubmitField('Запросить восстановление пароля')


class ResetPasswordForm(FlaskForm):#форма для ввода нового пароля при восстановлении
    password = PasswordField('Пароль',validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль',validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Изменить пароль')


class RegistrationForm(FlaskForm):#зарегистрироваться
    username = StringField('Логин',validators=[DataRequired()])
    email = StringField('E-mail',validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль',validators=[DataRequired(), EqualTo('password')])
    send_emails = BooleanField('Получать на e-mail рассылки об обновлениях приложения',default=True)
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self,username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким логином уже зарегистрирован.')

    def validate_email(self,email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким e-mail адресом уже зарегистрирован.')