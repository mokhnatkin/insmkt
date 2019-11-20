from flask import render_template, flash, redirect, url_for, request, \
                    current_app, g
from app import db
from app.main.forms import PostForm, ConfirmSwitchSendEmailsForm
from flask_login import current_user, login_required
from app.models import User, Post, Upload, Company, Insclass, Indicator, Financial, \
            Premium, Claim, Financial_per_month, Premium_per_month, Claim_per_month, \
            Compute, Company_all_names, Insclass_all_names, View_log
from app.main import bp
from app.universal_routes import before_request_u, required_roles_u, save_to_log, send_email
import pandas as pd
                    

@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)



@bp.route('/',methods=['GET','POST'])
@bp.route('/index',methods=['GET','POST'])
@login_required
def index():#домашняя страница
    form = PostForm()
    save_to_log('index',current_user.id)
    if form.validate_on_submit():
        post = Post(body=form.post.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Ваш пост опубликован!')
        return redirect(url_for('main.index'))
    admin_email = current_app.config['ADMIN_EMAIL']
    posts = Post.query.order_by(Post.timestamp.desc()).limit(5).all()#query 5 last posts

    
    #get id of motor TPL class
    try:
        motor_TPL_class_id = Insclass.query.filter(Insclass.name == 'obligatory_motor_TPL').first()
        _id = motor_TPL_class_id.id
    except:
        _id = None

    motor_TPL_premium = list()
    if _id is not None:
        df_premium = pd.read_sql(db.session.query(Premium)
            .join(Company)
            .with_entities(Premium.value,Company.alias)
            .filter(Premium.insclass_id == _id)
            .filter(Premium.report_date == g.last_report_date)
            .filter(Company.nonlife == True)
            .filter(Premium.value > 0)            
        .statement,db.session.bind)#motor TPL premiums data frame (last report date)

        prem_sum = df_premium['value'].sum()
        df_premium['share'] = round(df_premium['value'] / prem_sum * 100,2)
        df_premium = df_premium.sort_values(by='value',ascending=False)

        i = 0
        for row_index,row in df_premium.iterrows():
            motor_TPL_premium.append({'row_index':i,'alias':row.alias,'value':row.value,'share':row.share})
            i += 1
    

    #get id of net premium indicator
    try:
        net_premium_id = Indicator.query.filter(Indicator.name == 'net_premiums').first()
        _id = net_premium_id.id
    except:
        _id = None

    net_premiums = list()
    if _id is not None:
        df_net_prem = pd.read_sql(db.session.query(Financial)
            .join(Company)
            .with_entities(Financial.value,Company.alias)
            .filter(Financial.indicator_id == _id)
            .filter(Financial.report_date == g.last_report_date)
            .filter(Company.nonlife == True)
            .filter(Financial.value > 0)
        .statement,db.session.bind)
    
        net_prem_sum = df_net_prem['value'].sum()
        df_net_prem['share'] = round(df_net_prem['value'] / net_prem_sum * 100,2)
        df_net_prem = df_net_prem.sort_values(by='value',ascending=False)
    
        i = 0
        for row_index,row in df_net_prem.iterrows():
            net_premiums.append({'row_index':i,'alias':row.alias,'value':row.value,'share':row.share})
            i += 1
    
    return render_template('main/index.html',title='Домашняя страница', form=form, posts=posts, \
                    admin_email=admin_email, motor_TPL_premium=motor_TPL_premium, net_premiums=net_premiums)
                   


@bp.route('/user/<username>')#профиль пользователя
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.timestamp.desc())
    return render_template('main/user.html',user=user,posts=posts)


@bp.route('/explore')#все посты
@login_required
def explore():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page,current_app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('main.explore',page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore',page=posts.prev_num) if posts.has_prev else None
    return render_template('main/explore.html',title='Все посты',posts=posts.items,next_url=next_url,prev_url=prev_url)


@bp.route('/disable_send_emails/<user_id>',methods=['GET', 'POST'])#отменить рассылку email
@login_required
def disable_send_emails(user_id):
    if int(current_user.id) != int(user_id):
        flash('Вы не можете менять настройки для других пользователей')
        return redirect(url_for('main.index'))
    user = User.query.filter(User.id == user_id).first()
    if not user:
        return redirect(url_for('main.index'))
    h1_txt = 'Отписаться от e-mail рассылок, пользователь ' + user.username
    title = 'Отписаться'
    if user.send_emails == False:
        flash('Вы уже отписаны от e-mail рассылок.')
        return redirect(url_for('main.index'))
    form = ConfirmSwitchSendEmailsForm()
    if form.validate_on_submit():
        user.disable_send_emails()
        db.session.commit()    
        flash('Вы отписались от e-mail рассылок. Если захотите снова подписаться, зайдите в Настройки')
        return redirect(url_for('main.index'))
    return render_template('add_edit_DB_item.html',title=title,form=form,h1_txt=h1_txt)



@bp.route('/enable_send_emails/<user_id>',methods=['GET', 'POST'])#вернуть рассылку email
@login_required
def enable_send_emails(user_id):
    if int(current_user.id) != int(user_id):
        flash('Вы не можете менять настройки для других пользователей')
        return redirect(url_for('main.index'))    
    user = User.query.filter(User.id == user_id).first()
    if not user:
        return redirect(url_for('main.index'))
    h1_txt = 'Подписаться на e-mail рассылки, пользователь ' + user.username
    title = 'Подписаться'
    if user.send_emails == True:
        flash('Вы уже подписаны на e-mail рассылки.')
        return redirect(url_for('main.index'))
    form = ConfirmSwitchSendEmailsForm()
    if form.validate_on_submit():
        user.enable_send_emails()
        db.session.commit()    
        flash('Вы подписались на e-mail рассылки. Если захотите отписаться, зайдите в Настройки')
        return redirect(url_for('main.index'))
    return render_template('add_edit_DB_item.html',title=title,form=form,h1_txt=h1_txt)

