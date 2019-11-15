from flask import render_template, flash, redirect, url_for, request, g
from app import db
from app.auth.forms import LoginForm, RegistrationForm, \
                ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
from app.auth import bp
from app.universal_routes import before_request_u, send_email


@bp.before_request
def before_request():
    return before_request_u()


@bp.route('/login',methods=['GET','POST'])#вход
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неправильный логин или пароль')
            return redirect(url_for('auth.login'))
        login_user(user,remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)        
    return render_template('auth/login.html',title='Вход',form=form)


@bp.route('/logout')#выход
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register',methods=['GET','POST'])#регистрация
def register():
    h1_txt = 'Регистрация'
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,email=form.email.data,send_emails=form.send_emails.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы зарегистрированы!')
        return redirect(url_for('auth.login'))
    return render_template('add_edit_DB_item.html',title='Регистрация',form=form, h1_txt=h1_txt)


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    subject = 'Восстановление пароля'
    body = render_template('email/reset_password.txt',user=user,token=token)
    recipients = [user.email]
    send_email(subject,body,recipients)


@bp.route('/reset_password_request',methods=['GET', 'POST'])#запросить восстановление пароля
def reset_password_request():
    h1_txt = 'Восстановление пароля'
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter(User.email == form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash('Было отправлено письмо с дальнейшими инструкциями. Проверьте свой почтовый ящик.')
            return redirect(url_for('auth.login'))
        else:
            flash('Пользователь с таким e-mail не зарегистрирован')
            return redirect(url_for('auth.login'))
    return render_template('add_edit_DB_item.html',title='Восстановление пароля',h1_txt=h1_txt,form=form)


@bp.route('/reset_password/<token>',methods=['GET', 'POST'])#восстановление пароля - изменить пароль
def reset_password(token):
    h1_txt = 'Изменение пароля'
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()    
        flash('Пароль успешно изменён')
        return redirect(url_for('auth.login'))
    return render_template('add_edit_DB_item.html',title='Изменение пароля',form=form, h1_txt=h1_txt)