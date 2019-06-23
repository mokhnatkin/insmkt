from flask import render_template, flash, redirect, url_for, request, \
                    current_app, g
from app import db
from app.main.forms import PostForm
from flask_login import current_user, login_required
from app.models import User, Post, Upload, Company, Insclass, Indicator, Financial, \
            Premium, Claim, Financial_per_month, Premium_per_month, Claim_per_month, \
            Compute, Company_all_names, Insclass_all_names, View_log
from app.main import bp
from app.universal_routes import before_request_u, required_roles_u, save_to_log
                    

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
    posts = Post.query.order_by(Post.timestamp.desc()).limit(5).all()#query 5 last posts
    #get id of motor TPL class
    try:
        motor_TPL_class_id = Insclass.query.filter(Insclass.name == 'obligatory_motor_TPL').first()
    except:
        motor_TPL_class_id = None
    #query top 10 motor TPL premium for last report_date togegher w/ company names
    show_motor_TPL = False
    motor_TPL_premium = None
    motor_TPL_premium_len = None
    if motor_TPL_class_id is not None and g.last_report_date is not None:
        motor_TPL_premium = Premium.query.join(Company) \
                            .with_entities(Premium.value,Company.alias) \
                            .filter(Premium.insclass_id == motor_TPL_class_id.id) \
                            .filter(Premium.report_date == g.last_report_date) \
                            .filter(Company.nonlife == True) \
                            .order_by(Premium.value.desc()).limit(10).all()
    try:
        motor_TPL_premium_len = len(motor_TPL_premium)
    except:
        pass
    if motor_TPL_premium is not None and motor_TPL_premium_len > 0:
        show_motor_TPL = True
    #get id of net premium indicator
    try:
        net_premium_id = Indicator.query.filter(Indicator.name == 'net_premiums').first()
    except:
        net_premium_id = None
    show_net_prem = False
    #query top 10 companies by net premium
    net_premiums = None
    net_premiums_len = None
    if net_premium_id is not None and g.last_report_date is not None:
        net_premiums = Financial.query.join(Company) \
                        .with_entities(Financial.value,Company.alias) \
                        .filter(Financial.indicator_id == net_premium_id.id) \
                        .filter(Financial.report_date == g.last_report_date) \
                        .filter(Company.nonlife == True) \
                        .order_by(Financial.value.desc()).limit(10).all()
    try:
        net_premiums_len = len(net_premiums)
    except:
        pass                        
    if net_premiums is not None and net_premiums_len>0:
        show_net_prem = True
    return render_template('main/index.html',title='Домашняя страница', form=form, posts=posts, \
                    motor_TPL_premium=motor_TPL_premium, motor_TPL_premium_len=motor_TPL_premium_len, \
                    show_motor_TPL=show_motor_TPL, show_net_prem=show_net_prem, \
                    net_premiums=net_premiums, net_premiums_len=net_premiums_len)


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
