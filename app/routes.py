from flask import render_template, flash, redirect, url_for, request, jsonify, g, send_file, Response
from app import app, db
from app.forms import LoginForm, RegistrationForm, PostForm, DictUploadForm, DataUploadForm, \
                ComputePerMonthIndicators, CompanyProfileForm, ClassProfileForm, PeersForm, \
                RankingForm, DictSelectForm, AddNewCompanyName, AddNewClassName, \
                AddEditCompanyForm, AddEditClassForm, SendEmailToUsersForm, EditUserForm, \
                ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post, Upload, Company, Insclass, Indicator, Financial, \
            Premium, Claim, Financial_per_month, Premium_per_month, Claim_per_month, \
            Compute, Company_all_names, Insclass_all_names, View_log
from werkzeug.urls import url_parse
from datetime import datetime
from flask_babel import get_locale
from werkzeug.utils import secure_filename
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import numpy as np
from xlrd import open_workbook
from functools import wraps
import random
from exchangelib import Account, Credentials, Configuration, DELEGATE, Message
from threading import Thread


@app.before_request
def before_request():
    if current_user.is_authenticated:    
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.locale = str(get_locale())
        try:
            q = Premium.query.order_by(Premium.report_date.desc()).first()#max report_date
            g.last_report_date = q.report_date
        except:
            g.last_report_date = datetime.utcnow()
        try:
            q = Premium.query.order_by(Premium.report_date).first()#max report_date
            g.min_report_date = q.report_date
        except:
            g.min_report_date = datetime.utcnow()


#A function defintion which will work as a decorator for each view – we can call this with @required_roles
def required_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if get_current_user_role() not in roles:
                flash('У вашей роли недостаточно полномочий','error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return wrapper
 

def get_current_user_role():#возвращает роль текущего пользователя
    return current_user.role        


@app.route('/',methods=['GET','POST'])
@app.route('/index',methods=['GET','POST'])
@login_required
def index():#домашняя страница
    form = PostForm()
    save_to_log('index',current_user.id)
    if form.validate_on_submit():
        post = Post(body=form.post.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Ваш пост опубликован!')
        return redirect(url_for('index'))
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
    return render_template('index.html',title='Домашняя страница', form=form, posts=posts, \
                    motor_TPL_premium=motor_TPL_premium, motor_TPL_premium_len=motor_TPL_premium_len, \
                    show_motor_TPL=show_motor_TPL, show_net_prem=show_net_prem, \
                    net_premiums=net_premiums, net_premiums_len=net_premiums_len)


@app.route('/login',methods=['GET','POST'])#вход
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неправильный логин или пароль')
            return redirect(url_for('login'))
        login_user(user,remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)        
    return render_template('login.html',title='Вход',form=form)


@app.route('/logout')#выход
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register',methods=['GET','POST'])#регистрация
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы зарегистрированы!')
        return redirect(url_for('login'))
    return render_template('register.html',title='Регистрация',form=form)

@app.route('/instruction')#инструкция
@login_required
@required_roles('admin')
def instruction():
    company_list = '_companies.xlsx'#образец для загрузки справочника - список компаний
    insclass_list = '_classes.xlsx'#образец для загрузки справочника - список классов
    indicator_list = '_indicators.xlsx'#образец для загрузки справочника - список показателей
    return render_template('instruction.html',title='Инструкция',company_list=company_list,insclass_list=insclass_list,indicator_list=indicator_list)


@app.route('/user/<username>')#профиль пользователя
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.timestamp.desc())
    return render_template('user.html',user=user,posts=posts)


@app.route('/edit_user/<user_id>',methods=['GET', 'POST'])#редактировать email пользователя
@login_required
@required_roles('admin')
def edit_user(user_id=None):
    form = EditUserForm()
    obj = User.query.filter(User.id == user_id).first()
    if request.method == 'GET':        
        form = EditUserForm(obj=obj)
    if form.validate_on_submit():
        obj.username = form.username.data
        obj.email = form.email.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('edit_user', user_id=user_id))
    return render_template('edit_user.html',form=form)


@app.route('/users')#список пользователей
@login_required
@required_roles('admin')
def users():
    users = None
    users_len = 0
    try:
        users = User.query.all()
        users_len = len(users)
    except:
        pass
    return render_template('users.html',users=users,users_len=users_len)

@app.route('/files')#список загруженных файлов
@login_required
@required_roles('admin')
def files():
    files = Upload.query.order_by(Upload.timestamp.desc()).all()
    return render_template('files.html',files=files)

@app.route('/computes')#список выполненных перерасчетов
@login_required
@required_roles('admin')
def computes():
    computes = Compute.query.order_by(Compute.timestamp.desc()).all()
    return render_template('computes.html',computes=computes)

@app.route('/files/<fname>')#файл для скачивания на комп
@login_required
@required_roles('admin')
def downloadFile(fname = None):
    p = os.path.join(os.path.dirname(os.path.abspath(app.config['UPLOAD_FOLDER'])),app.config['UPLOAD_FOLDER'],fname)
    return send_file(p, as_attachment=True)


@app.route('/explore')#все посты
@login_required
def explore():
    page = request.args.get('page',1,type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page,app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('explore',page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore',page=posts.prev_num) if posts.has_prev else None
    return render_template('explore.html',title='Все посты',posts=posts.items,next_url=next_url,prev_url=prev_url)


def allowed_file(filename):#проверка файла - расширение должно быть разрешено
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']        

def add_str_timestamp(filename):#adds string timestamp to filename in order to make in unique
    dt = datetime.utcnow()
    stamp = round(dt.timestamp())
    uId = str(stamp)
    u_filename = uId+'_'+filename
    return u_filename

def process_file(file_type,file_subtype,file_content,report_date,frst_row,others_col_1,others_col_2,others_col_3):#обработаем загруженный excel файл
    processed_ok = False
    companies_dict = dict()
    indicators_dict = dict()
    insclasses_dict = dict()
    companies = Company_all_names.query.all()#получим список компаний
    for company in companies:
        companies_dict[company.name] = company.company_id #в словаре companies_dict храним id компании (ключ - имя)
    indicators = Indicator.query.all()#получим список показателей
    for indicator in indicators:
        indicators_dict[indicator.fullname] = indicator.id #в словаре indicators_dict храним id показателя (ключ - имя)
    insclasses = Insclass_all_names.query.all()#получим список классов
    for insclass in insclasses:
        if insclass.fullname == 'иные классы (виды) страхования':#иные классы (виды) повторяются 3 раза
            tml_fullname = insclass.fullname + '_' + insclass.name#добавим для уникальности
            insclasses_dict[tml_fullname] = insclass.insclass_id
        else:
            insclasses_dict[insclass.fullname] = insclass.insclass_id#в словаре insclasses_dict храним id класса (ключ - имя)    
    if file_type == 'Dictionary' and file_subtype == 'CompaniesList':#загружаем справочники - список страховых компаний
        for row in file_content:
            name = row[0].strip()
            nonlife = row[1]
            alive = row[2]
            alias = row[3]
            company = Company(name=name,nonlife=nonlife,alive=alive,alias=alias)#сохраняем компанию
            db.session.add(company)
            db.session.commit()
            #получаем id сохраненной компании
            c_saved = Company.query.filter(Company.name == name).first()
            c_id = c_saved.id
            c_all_names = Company_all_names(name=name,company_id=c_id)
            db.session.add(c_all_names)
    elif file_type == 'Dictionary' and file_subtype == 'ClassesList':#загружаем справочники - список классов
        for row in file_content:
            name = row[0].strip()
            fullname = row[1].strip()
            nonlife = row[2]
            obligatory = row[3]
            voluntary_personal = row[4]
            voluntary_property = row[5]
            alias = row[6]
            insclass = Insclass(name=name,fullname=fullname,nonlife=nonlife,obligatory=obligatory,voluntary_personal=voluntary_personal,voluntary_property=voluntary_property,alias=alias)            
            db.session.add(insclass)
            db.session.commit()
            #получаем id сохраненного класса
            c_saved = Insclass.query.filter(Insclass.name == name) \
                            .filter(Insclass.fullname == fullname).first()
            c_id = c_saved.id
            c_all_names = Insclass_all_names(name=name,fullname=fullname,insclass_id=c_id)
            db.session.add(c_all_names)
    elif file_type == 'Dictionary' and file_subtype == 'IndicatorsList':#справочник - список показателей
        for row in file_content:
            name = row[0].strip()
            fullname = row[1].strip()
            description = row[2].strip()
            flow = row[3]
            basic = row[4]
            indicator = Indicator(name=name,fullname=fullname,description=description,flow=flow,basic=basic)            
            db.session.add(indicator)
    elif file_type == 'Data' and file_subtype in ('Premiums','Claims'):#загружаем данные - премии или выплаты по классам и страховым
        insclasses_list_raw = list()
        insclasses_list = list()
        insclasses_list_raw = file_content[frst_row-3]
        for el in insclasses_list_raw:
            cl = el.strip()
            insclasses_list.append(cl)
        N = len(insclasses_list)
        cl_dict = dict()#словарь: ключ - номер колонки, значение - id класса
        colnum = 0
        for cl_fullname in insclasses_list:#пройдемся по строке с названиями показателей
            try:
                if cl_fullname == 'иные классы (виды) страхования':#особая логика
                    if colnum == others_col_1-1:
                        cl_fullname = cl_fullname + '_' + 'other_voluntary_personal'
                    elif colnum == others_col_2-1:
                        cl_fullname = cl_fullname + '_' + 'other_voluntary_property'
                    elif colnum == others_col_3-1:
                        cl_fullname = cl_fullname + '_' + 'other_obligatory'
                cl_id = insclasses_dict[cl_fullname]
                cl_dict[str(colnum)] = cl_id
            except:
                pass
            colnum += 1
        for row in file_content:#пройдемся по каждой строке файла
            name = str(row[1]) #текстовое наименование компании
            try:
                company_id = companies_dict[name] #определим id компании
            except:
                continue
            for i in range(2,N):
                try:
                    insclass_id = cl_dict[str(i)]#определим id показателя
                except:
                    continue
                try:
                    value = float(row[i])
                except:
                    value = 0.0
                    pass                
                if file_subtype == 'Premiums':
                    premium = Premium(report_date=report_date,company_id=company_id,insclass_id=insclass_id,value=value)
                    db.session.add(premium)
                elif file_subtype == 'Claims':
                    claim = Claim(report_date=report_date,company_id=company_id,insclass_id=insclass_id,value=value)
                    db.session.add(claim)
    elif file_type == 'Data' and file_subtype in ('Financials','Prudentials'):#загружаем данные - основные фин. показатели по страховым
        indicators_list_raw = list()
        indicators_list = list()
        if file_subtype == 'Financials':
            indicators_list_raw = file_content[frst_row-3]#названия показателей хранятся в 5-й строке файла (осн. фин. показатели)
        elif file_subtype == 'Prudentials':
            indicators_list_raw = file_content[frst_row-5]#названия показателей хранятся в 8-й строке файла (прудики)
        for el in indicators_list_raw:
            ind = el.strip()
            indicators_list.append(ind)
        N = len(indicators_list)
        ind_dict = dict()#словарь: ключ - номер колонки, значение - id показателя
        colnum = 0
        for ind_fullname in indicators_list:#пройдемся по строке с названиями показателей
            try:
                ind_id = indicators_dict[ind_fullname]
                ind_dict[str(colnum)] = ind_id
            except:
                pass
            colnum += 1
        for row in file_content:#пройдемся по каждой строке файла            
            name = str(row[1]) #текстовое наименование компании            
            try:
                company_id = companies_dict[name] #определим id компании
            except:
                continue                
            for i in range(2,N):
                try:
                    indicator_id = ind_dict[str(i)]#определим id показателя
                except:
                    continue
                try:
                    value = float(row[i])
                except:
                    value = 0.0
                    pass
                financial = Financial(report_date=report_date,company_id=company_id,indicator_id=indicator_id,value=value)
                db.session.add(financial)
    else:
        processed_ok = False
        quit()
    db.session.commit()
    processed_ok = True
    return processed_ok

def check_process_file_res(file_subtype,report_date):#проверка результатов загрузки и отработки файла
    N_rows = 0
    rand_rows = list()
    _sm_id = Indicator.query.filter(Indicator.name=='solvency_margin').first()
    sm_id = _sm_id.id#id маржи платежеспособности
    if file_subtype == 'Financials':
        rows = Financial.query.join(Company).join(Indicator) \
                .with_entities(Company.alias,Indicator.fullname,Financial.report_date,Financial.value) \
                .filter(Financial.indicator_id != sm_id) \
                .filter(Financial.report_date == report_date).all()
    elif file_subtype == 'Prudentials':
        rows = Financial.query.join(Company).join(Indicator) \
                .with_entities(Company.alias,Indicator.fullname,Financial.report_date,Financial.value) \
                .filter(Financial.indicator_id == sm_id) \
                .filter(Financial.report_date == report_date).all()
    elif file_subtype == 'Premiums':
        rows = Premium.query.join(Company).join(Insclass) \
                .with_entities(Company.alias,Insclass.alias,Premium.report_date,Premium.value) \
                .filter(Premium.report_date == report_date).all()
    elif file_subtype == 'Claims':
        rows = Claim.query.join(Company).join(Insclass) \
                .with_entities(Company.alias,Insclass.alias,Claim.report_date,Claim.value) \
                .filter(Claim.report_date == report_date).all()
    N_rows = len(rows)
    found = 0
    while True:
        r = random.choice(rows)
        if r.value > 0.1:
            found += 1
            rand_rows.append(r)
        if found > 2:#выведем три случайные записи больше 0
            break
    return N_rows, rand_rows


@app.route('/upload_file/<upload_type>',methods=['GET', 'POST'])#загрузить файл
@login_required
@required_roles('admin')
def upload_file(upload_type):
    if upload_type == 'dictionary':
        form = DictUploadForm()
        descr = 'Здесь из excel файлов загружаются справочники'
    elif upload_type == 'data':
        form = DataUploadForm()
        descr = 'Здесь из excel файлов (источник - НБ РК, https://nationalbank.kz/?docid=1075&switch=russian) загружаются финансовые данные. Каждая книга должна содержать только один лист'
    if form.validate_on_submit():
        if 'file' not in request.files:# check if the post request has the file part
            flash('Файл не выбран')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':# if user does not select file, browser also submit an empty part without filename
            flash('Файл не выбран')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            name = add_str_timestamp(form.name.data)
            filename = secure_filename(form.file.data.filename)
            filename = add_str_timestamp(filename) #adds string timestamp to filename in order to make in unique            
            if upload_type == 'dictionary':
                upload = Upload(name=name,file_type='Dictionary',dict_type=form.dict_type.data,file_name=filename)
            elif upload_type == 'data':
                already_uploaded = Upload.query.filter(Upload.file_type=='Data').filter(Upload.data_type == form.data_type.data).filter(Upload.report_date == form.report_date.data).first()
                if already_uploaded is None:
                    upload = Upload(name=name,file_type='Data',data_type=form.data_type.data,file_name=filename,report_date=form.report_date.data)
                else:
                    flash('Данный файл уже был загружен. Повторная загрузка не требуется.')
                    return redirect(url_for('upload_file', upload_type='data'))
            form.file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))            
            try:
                wb = open_workbook(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                num_sheets = len(wb.sheet_names())
            except:
                flash('Не могу открыть excel файл - неизвестный формат.')
                return redirect(url_for('upload_file', upload_type='data'))
            if num_sheets > 1:
                flash('В выбранном файле более одного листа. Удалите ненужные листы во избежание ошибок')
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except:
                    pass
                return redirect(url_for('upload_file', upload_type='data'))
            else:
                db.session.add(upload)
                db.session.commit()
                flash('Файл загружен!')
                file_content = request.get_array(field_name='file')
                if upload_type == 'dictionary':
                    del file_content[0]#удаляем первую запись в массиве (заголовок)
                    process_res = process_file('Dictionary',form.dict_type.data,file_content,datetime.utcnow(),1,1,1,1)
                    if process_res:
                        flash('Файл успешно обработан!')
                    else:
                        flash('При обработке файла возникли ошибки!')
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        except:
                            pass
                        db.session.delete(upload)
                        db.session.commit()
                    return redirect(url_for('upload_file', upload_type='dictionary'))
                elif upload_type == 'data':
                    frst_row = int(form.frst_row.data)#первая строка с данными по компаниям
                    others_col_1 = int(form.others_col_1.data)#столбец с иными классами, ДЛС
                    others_col_2 = int(form.others_col_2.data)#столбец с иными классами, ДИС
                    others_col_3 = int(form.others_col_3.data)#столбец с иными классами, ОС
                    try:
                        process_res = process_file('Data',form.data_type.data,file_content,form.report_date.data,frst_row,others_col_1,others_col_2,others_col_3)
                    except:
                        flash('Не удалось обработать файл! Проверьте входной файл и корректность заполнения номера первой строки с данными.')                        
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        except:
                            pass
                        db.session.delete(upload)
                        db.session.commit()                            
                        return redirect(url_for('upload_file', upload_type='data'))
                    if process_res:
                        try:
                            N_rows, rand_rows = check_process_file_res(form.data_type.data,form.report_date.data)
                            flash('Файл загружен и обработан. Проверьте результаты загруки и произведите перерасчёт!')
                            flash('Результаты загрузки: создано записей ' + str(N_rows) + '. Проверьте случайные записи из числа созданных:')
                            for r in rand_rows:
                                flash('---' + str(r))
                        except:
                            flash('Не получилось проверить результат обработки файла! Возможно, данные не были загружены в БД. Проверьте входной файл и корректность заполнения номера первой строки с данными.')
                            try:
                                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            except:
                                pass
                            db.session.delete(upload)
                            db.session.commit()                                
                            return redirect(url_for('upload_file', upload_type='data'))
                    else:
                        flash('При обработке файла возникли ошибки!')
                    return redirect(url_for('upload_file', upload_type='data'))
        else:
            flash('Файл не выбран, либо некорректное расширение. Доступные расширения:'+str(app.config['ALLOWED_EXTENSIONS']))
    return render_template('upload_file.html',title='Загрузка файла',form=form,descr=descr)


def class_has_other_names(class_id):
    res = False
    names = Insclass_all_names.query.filter(Insclass_all_names.insclass_id==class_id).all()
    if len(names)>1:
        res = True
    return res

def company_has_other_names(company_id):
    res = False
    names = Company_all_names.query.filter(Company_all_names.company_id==company_id).all()
    if len(names)>1:
        res = True
    return res


@app.route('/dictionary_values',methods=['GET', 'POST'])#просмотр значений выбранного справочника
@login_required
@required_roles('admin')
def dictionary_values():
    form = DictSelectForm()
    show_companies = False
    show_classes = False
    show_indicators = False
    companies = None
    insclasses = None
    indicators = None
    if form.validate_on_submit():
        dict_type = form.dict_type.data
        if dict_type == 'CompaniesList':
            companies = Company.query.all()
            show_companies = True
        elif dict_type == 'ClassesList':
            insclasses = Insclass.query.all()
            show_classes = True
        elif dict_type == 'IndicatorsList':
            indicators = Indicator.query.all()
            show_indicators = True
    return render_template('dictionary_values.html',title='Просмотр справочников',form=form, \
        show_companies=show_companies,show_classes=show_classes,show_indicators=show_indicators, \
        companies=companies,insclasses=insclasses,indicators=indicators, \
        company_has_other_names=company_has_other_names,class_has_other_names=class_has_other_names)


@app.route('/add_new_company_name/<company_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def add_new_company_name(company_id=None):
    company = Company.query.filter(Company.id==company_id).first()
    company_name = company.alias
    all_names = Company_all_names.query.filter(Company_all_names.company_id==company_id).all()
    form = AddNewCompanyName()
    if form.validate_on_submit():
        new_name = form.name.data
        c_all_names = Company_all_names(name=new_name,company_id=company_id)
        db.session.add(c_all_names)
        db.session.commit()
        flash('Новое наименование добавлено')
        return redirect(url_for('add_new_company_name', company_id=company_id))
    return render_template('company_all_names.html',company_name=company_name,all_names=all_names, \
                            form=form)


@app.route('/edit_company_name/<company_id>/<_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def edit_company_name(company_id=None,_id = None):
    form = AddNewCompanyName()
    obj = Company_all_names.query.filter(Company_all_names.id == _id).first()
    company = Company.query.filter(Company.id==company_id).first()
    company_name = company.alias
    all_names = Company_all_names.query.filter(Company_all_names.company_id==company_id).all()    
    if request.method == 'GET':
        form = AddNewCompanyName(obj=obj)
    if form.validate_on_submit():
        obj.name = form.name.data        
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('add_new_company_name', company_id=company_id))
    return render_template('company_all_names.html',form=form,company_name=company_name,all_names=all_names)


@app.route('/add_new_class_name/<class_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def add_new_class_name(class_id=None):
    insclass = Insclass.query.filter(Insclass.id==class_id).first()
    class_name = insclass.alias
    all_names = Insclass_all_names.query.filter(Insclass_all_names.insclass_id==class_id).all()
    form = AddNewClassName()
    if form.validate_on_submit():
        new_name = form.name.data
        new_fullname = form.fullname.data
        c_all_names = Insclass_all_names(name=new_name,fullname=new_fullname,insclass_id=class_id)
        db.session.add(c_all_names)
        db.session.commit()
        flash('Новое наименование добавлено')
        return redirect(url_for('add_new_class_name', class_id=class_id))
    return render_template('class_all_names.html',class_name=class_name,all_names=all_names, \
                            form=form)


@app.route('/edit_class_name/<class_id>/<_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def edit_class_name(class_id=None,_id = None):
    form = AddNewClassName()
    obj = Insclass_all_names.query.filter(Insclass_all_names.id == _id).first()
    insclass = Insclass.query.filter(Insclass.id==class_id).first()
    class_name = insclass.alias
    all_names = Insclass_all_names.query.filter(Insclass_all_names.insclass_id==class_id).all()    
    if request.method == 'GET':
        form = AddNewClassName(obj=obj)
    if form.validate_on_submit():
        obj.name = form.name.data
        obj.fullname = form.fullname.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('add_new_class_name', class_id=class_id))
    return render_template('class_all_names.html',form=form,class_name=class_name,all_names=all_names)


def compute_indicators(data_type,begin_date,end_date):#рассчитать показатели за месяц
    processed_ok = False    
    if begin_date.month == 1 and begin_date.day == 1:#check if begin_date is the beggining of the year
        new_year = True
    else:
        new_year = False
    if data_type == 'Financials':#фин. показатели (только flow)
        #на начало периода
        data_begin_date = Financial.query.join(Indicator).filter(Indicator.flow==True).filter(Financial.report_date==begin_date).all()
        #на конец периода
        data_end_date = Financial.query.join(Indicator).filter(Indicator.flow==True).filter(Financial.report_date==end_date).all()
        dict_begin_date = dict()
        dict_end_date = dict()
        for el in data_begin_date:
            uId = str(el.company_id) + '_' +str(el.indicator_id)
            if not new_year:
                dict_begin_date[uId] = el.value
            else:
                dict_begin_date[uId] = 0.0#обнуляем начальные данные, если начала периода перерасчета - 1 января, т.к. в файлах данные идут с накопительным итогом
        for el in data_end_date:
            uId = str(el.company_id) + '_' +str(el.indicator_id)
            dict_end_date[uId] = el.value        
        for key,val in dict_end_date.items():#compute delta for each element in new data
            try:
                old_value = dict_begin_date[key]
            except:
                old_value = 0.0#company and indicator not found in old (begin) data
            delta = val - old_value
            #decompose key(uId) into companyId and indicatorId
            s = re.split('_',key)
            company_id = int(s[0])
            indicator_id = int(s[1])
            financial_per_month = Financial_per_month(beg_date=begin_date,end_date=end_date,company_id=company_id,indicator_id=indicator_id,value=delta)
            db.session.add(financial_per_month)
    elif data_type in ('Premiums','Claims'):        
        if data_type == 'Premiums':
            #на начало периода
            data_begin_date = Premium.query.filter(Premium.report_date==begin_date).all()
            #на конец периода
            data_end_date = Premium.query.filter(Premium.report_date==end_date).all()
        elif data_type == 'Claims':
            #на начало периода
            data_begin_date = Claim.query.filter(Claim.report_date==begin_date).all()
            #на конец периода
            data_end_date = Claim.query.filter(Claim.report_date==end_date).all()            
        dict_begin_date = dict()
        dict_end_date = dict()
        for el in data_begin_date:
            uId = str(el.company_id) + '_' +str(el.insclass_id)
            if not new_year:
                dict_begin_date[uId] = el.value
            else:
                dict_begin_date[uId] = 0.0#обнуляем начальные данные, если начала периода перерасчета - 1 января, т.к. в файлах данные идут с накопительным итогом
        for el in data_end_date:
            uId = str(el.company_id) + '_' +str(el.insclass_id)
            dict_end_date[uId] = el.value        
        for key,val in dict_end_date.items():#compute delta for each element in new data
            try:
                old_value = dict_begin_date[key]
            except:
                old_value = 0.0#company and indicator not found in old (begin) data
            delta = val - old_value
            #decompose key(uId) into companyId and insclass_id
            s = re.split('_',key)
            company_id = int(s[0])
            insclass_id = int(s[1])
            if data_type == 'Premiums':
                premium_per_month = Premium_per_month(beg_date=begin_date,end_date=end_date,company_id=company_id,insclass_id=insclass_id,value=delta)
                db.session.add(premium_per_month)
            elif data_type == 'Claims':
                claim_per_month = Claim_per_month(beg_date=begin_date,end_date=end_date,company_id=company_id,insclass_id=insclass_id,value=delta)
                db.session.add(claim_per_month)
    else:
        processed_ok = False
        quit()
    #теперь сохраняем информацию о прошедшем перерасчете в модель Compute
    compute = Compute(data_type=data_type,beg_date=begin_date,end_date=end_date)
    db.session.add(compute)
    db.session.commit()
    processed_ok = True
    return processed_ok


def check_compute_res(data_type,begin_date,end_date):#проверка результатов загрузки и отработки файла
    N_rows = 0
    rand_rows = list()
    if data_type == 'Financials':
        rows = Financial_per_month.query.join(Company).join(Indicator) \
                .with_entities(Company.alias,Indicator.fullname,Financial_per_month.value) \
                .filter(Financial_per_month.beg_date == begin_date) \
                .filter(Financial_per_month.end_date == end_date).all()
    elif data_type == 'Premiums':
        rows = Premium_per_month.query.join(Company).join(Insclass) \
                .with_entities(Company.alias,Insclass.alias,Premium_per_month.value) \
                .filter(Premium_per_month.beg_date == begin_date) \
                .filter(Premium_per_month.end_date == end_date).all()
    elif data_type == 'Claims':
        rows = Claim_per_month.query.join(Company).join(Insclass) \
                .with_entities(Company.alias,Insclass.alias,Claim_per_month.value) \
                .filter(Claim_per_month.beg_date == begin_date) \
                .filter(Claim_per_month.end_date == end_date).all()
    N_rows = len(rows)
    found = 0
    while True:
        r = random.choice(rows)
        if r.value > 0.1:
            found += 1
            rand_rows.append(r)
        if found > 2:#выведем три случайные записи больше 0
            break
    return N_rows, rand_rows


@app.route('/compute',methods=['GET','POST'])#перерасчет показателей
@login_required
@required_roles('admin')
def compute():#перерасчёт
    descr = 'Здесь запускается перерасчет показателей за месяц (премии, выплаты и др.). Выберите тип данных, начало и конец месяца.'
    form = ComputePerMonthIndicators()
    if form.validate_on_submit():
        #сначала проверим - возможно перерасчет за этот месяц уже выполнялся
        already_computed = Compute.query.filter(Compute.data_type == form.data_type.data).filter(Compute.beg_date == form.begin_date.data).filter(Compute.end_date == form.end_date.data).first()
        if already_computed is None:
            process_res = compute_indicators(form.data_type.data,form.begin_date.data,form.end_date.data)
            if process_res:
                N_rows, rand_rows = check_compute_res(form.data_type.data,form.begin_date.data,form.end_date.data)
                flash('Перерасчёт осуществлён! Проверьте результаты перерасчёта!')
                flash('Результаты перерасчёта: создано записей ' + str(N_rows) + '. Проверьте случайные записи из числа созданных:')
                for r in rand_rows:
                    flash('---' + str(r))
            else:
                flash('Во время перерасчёта возникли ошибки!')        
            return redirect(url_for('compute'))
        else:
            flash('Данный перерасчёт уже был выполнен. Повторного перерасчёта не требуется.')
            return redirect(url_for('compute'))
    return render_template('compute.html',title='Перерасчет показателей',form=form,descr=descr)


def get_months(b,e):#определим, какие именно месяцы относятся к запрашиваемому периоду
    months = list()
    cur_b = b
    while True:
        if cur_b.month<12:
            cur_e = datetime(cur_b.year,cur_b.month+1,1)
        else:
            cur_e = datetime(cur_b.year+1,1,1)
        if cur_e > e:
            break            
        m = {'begin':cur_b,'end':cur_e}
        months.append(m)
        cur_b = cur_e
    return months


def get_num_companies_per_period(b,e,given_number):#сколько nonlife компаний действовали за заданный период
    N = 0
    if given_number is not None:#число конкурентов уже известно
        N = given_number
    else:
        #логика такая: если у компании за заданный период чистые премии > 0, то она считается действовавшей
        _np_id = Indicator.query.filter(Indicator.name == 'net_premiums').first()
        np_id = _np_id.id #id чистых премий
        net_prem = Financial_per_month.query.filter(Financial_per_month.indicator_id == np_id) \
                            .filter(Financial_per_month.beg_date >= b) \
                            .filter(Financial_per_month.end_date <= e).all()
        nonlife_companies = Company.query.with_entities(Company.id) \
                                    .filter(Company.nonlife==True).all()
        for c in nonlife_companies:
            total_p = 0.0
            for p in net_prem:
                if c.id == p.company_id:
                    total_p += p.value
            if total_p > 0:
                N += 1
    return N

def get_num_companies_at_date(report_date,given_number):#сколько nonlife компаний действовали за заданный период
    N = 0
    if given_number is not None:#число конкурентов уже известно
        N = given_number
    else:
        #логика такая: если у компании есть балансовые показатели (собств. капитал) на заданную дату, то она считается действовавшей
        _eq_id = Indicator.query.filter(Indicator.name == 'equity').first()
        eq_id = _eq_id.id #id чистых премий
        equity = Financial.query.join(Company) \
                        .filter(Company.nonlife == True) \
                        .filter(Financial.indicator_id == eq_id) \
                        .filter(Financial.report_date == report_date).all()
        N = len(equity)
    return N


def show_company_profile(company_id,peers,begin_d,end_d,N_companies,show_competitors):#вспомогательная функция - выдаем статистику по компании
    _company_name = Company.query.with_entities(Company.alias).filter(Company.id == company_id).first()
    company_name = _company_name[0]
    ############################################################################
    #balance financial indicators for given company
    main_indicators_balance = Financial.query.join(Indicator) \
                        .with_entities(Indicator.id,Indicator.name,Indicator.fullname,Financial.value) \
                        .filter(Indicator.flow == False) \
                        .filter(Financial.company_id == company_id) \
                        .filter(Financial.report_date == end_d).all()
    c_N_b = get_num_companies_at_date(end_d,N_companies)
    mkt_balance_indicators = list()
    balance_indicators = list()
    peers_balance_indicators = list()    
    #now compute balance ind for the market
    peers_names_arr = list()
    for company in peers:
        indicators_for_c = Financial.query.join(Indicator) \
                            .with_entities(Indicator.id,Financial.value) \
                            .filter(Indicator.flow == False) \
                            .filter(Financial.company_id == company[0]) \
                            .filter(Financial.report_date == end_d).all()
        mkt_balance_indicators.append(indicators_for_c)
        if show_competitors:
            cur_company = Company.query.filter(Company.id == company[0]).first()
            cur_company_name = cur_company.alias
            peers_names_arr.append({'peer_name':cur_company_name})
            for ind in indicators_for_c:
                peers_balance_indicators.append({'peer_name':cur_company_name,'indicator_id':ind.id,'peer_value':ind.value})
    for i in main_indicators_balance:
        peers_balance_ind = list()
        total_v = 0.0
        for company in mkt_balance_indicators:
            for el in company:
                if el.id == i.id:
                    total_v += el.value
        mkt_av = round(total_v / c_N_b,2) #market average for indicator i
        share = (i.value / total_v)*100#market share
        for ind in peers_balance_indicators:
            if ind['indicator_id'] == i.id:
                peers_balance_ind.append({'peer_name':ind['peer_name'],'peer_value':ind['peer_value']})
        balance_ind = {'id': i.id, 'name': i.name, 'fullname': i.fullname, \
            'value': i.value, 'mkt_av': mkt_av, 'total': total_v, 'share':share, \
            'peers_balance_ind': peers_balance_ind}
        balance_indicators.append(balance_ind) #now contains marker average for each indicator
    ############################################################################
    #now compute flow indicators
    flow_indicators = list()
    flow_indicators_per_month = list()
    months = get_months(begin_d,end_d)
    for month in months:
        begin = month['begin']
        end = month['end']
        main_indicators_flow = Financial_per_month.query.join(Indicator) \
                            .with_entities(Indicator.id,Financial_per_month.value) \
                            .filter(Indicator.flow == True) \
                            .filter(Financial_per_month.company_id == company_id) \
                            .filter(Financial_per_month.beg_date == begin) \
                            .filter(Financial_per_month.end_date == end).all()
        for i in main_indicators_flow:
            ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
            flow_indicators_per_month.append(ind)
    flow_ind = Indicator.query.filter(Indicator.flow == True).all()
    for ind in flow_ind:
        total_v = 0
        for m in flow_indicators_per_month:
            if m['id'] == ind.id:
                total_v += m['value']
        flow_ind_el = {'id': ind.id, 'name': ind.name, 'fullname': ind.fullname, 'value': total_v}
        flow_indicators.append(flow_ind_el)
    #now compute mkt average for flow indicators
    peers_flow_indicators = list()
    flow_indicators_per_month_per_c = list()
    for company in peers:
        for month in months:
            begin = month['begin']
            end = month['end']
            main_indicators_flow = Financial_per_month.query.join(Indicator) \
                                .with_entities(Indicator.id,Financial_per_month.value) \
                                .filter(Indicator.flow == True) \
                                .filter(Financial_per_month.company_id == company[0]) \
                                .filter(Financial_per_month.beg_date == begin) \
                                .filter(Financial_per_month.end_date == end).all()
            for i in main_indicators_flow:
                ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
                flow_indicators_per_month_per_c.append(ind)
            if show_competitors:
                for el in main_indicators_flow:
                    peers_flow_indicators.append({'peer_id':company[0],'indicator_id':el.id,'peer_value':el.value})
    c_N = get_num_companies_per_period(begin_d,end_d,N_companies)#number of non-life companies
    for ind in flow_indicators:
        peers_flow_ind = list()
        total_v = 0
        for i in flow_indicators_per_month_per_c:
            if i['id'] == ind['id']:
                total_v += i['value']
        ind['total'] = total_v
        ind['mkt_av'] = round(total_v / c_N,2)
        ind['share'] = (ind["value"] / total_v)*100#market share        
        for p in peers:#по каждому конкуренту
            total_v_p = 0.0
            for el in peers_flow_indicators:
                if el['indicator_id'] == ind['id'] and el['peer_id'] == p[0]:
                    total_v_p += el['peer_value']
            peers_flow_ind.append({'peer_value':total_v_p})
        ind['peers_flow_ind'] = peers_flow_ind

    ############################################################################
    #now premium by class
    premiums = list()
    prem_per_m = list()
    claim_per_m = list()
    insclasses = Insclass.query.all()
    for month in months:
        begin = month['begin']
        end = month['end']
        prem_m = Premium_per_month.query \
                    .with_entities(Premium_per_month.value,Premium_per_month.insclass_id) \
                    .filter(Premium_per_month.company_id == company_id) \
                    .filter(Premium_per_month.beg_date == begin) \
                    .filter(Premium_per_month.end_date == end).all()
        for i in prem_m:
            prem_per_m.append({'insclass_id':i.insclass_id,'premium':i.value})
        claim_m = Claim_per_month.query \
                    .with_entities(Claim_per_month.value,Claim_per_month.insclass_id) \
                    .filter(Claim_per_month.company_id == company_id) \
                    .filter(Claim_per_month.beg_date == begin) \
                    .filter(Claim_per_month.end_date == end).all()
        for i in claim_m:
            claim_per_m.append({'insclass_id':i.insclass_id,'claim':i.value})
    for cl in insclasses:
        total_prem = 0.0
        total_claim = 0.0
        for p in prem_per_m:
            if cl.id == p['insclass_id']:
                total_prem += p['premium']
        for c in claim_per_m:
            if cl.id == c['insclass_id']:
                total_claim += c['claim']
        if total_prem>0.0:
            LR = round(total_claim / total_prem * 100,2)
        else:
            LR = 'N.A.'
        if total_prem>0.0 or total_claim>0.0:
            premiums.append({'id':cl.id, 'name':cl.alias, 'premium':total_prem, 'claim':total_claim, 'LR':LR})
    premiums.sort(key=lambda x: x['premium'], reverse=True)#сортируем по убыванию премий
    return company_name, balance_indicators, flow_indicators, premiums, peers_names_arr


def get_other_financial_indicators(balance_indicators,flow_indicators,b,e):#расчет других фин. показателей
    other_financial_indicators = list()
    #получаем нужные значения по компании и по рынку
    #ищем среди показателей ОПУ
    peer_net_income = list()
    peer_premiums = list()
    peer_net_premiums = list()
    peer_claims = list()
    peer_net_claims = list()
    for x in flow_indicators:
        if x['name'] == 'net_income':#прибыль
            net_income_c = x['value']
            net_income_m = x['total']
            for p in x['peers_flow_ind']:
                peer_net_income.append(p['peer_value'])
        elif x['name'] == 'premiums':#гросс премии
            premiums_c = x['value']
            premiums_m = x['total']
            for p in x['peers_flow_ind']:
                peer_premiums.append(p['peer_value'])
        elif x['name'] == 'net_premiums':#чистые премии
            net_premiums_c = x['value']
            net_premiums_m = x['total']
            for p in x['peers_flow_ind']:
                peer_net_premiums.append(p['peer_value'])
        elif x['name'] == 'claims':#гросс выплаты
            claims_c = x['value']
            claims_m = x['total']
            for p in x['peers_flow_ind']:
                peer_claims.append(p['peer_value'])
        elif x['name'] == 'net_claims':#чистые выплаты
            net_claims_c = x['value']
            net_claims_m = x['total']
            for p in x['peers_flow_ind']:
                peer_net_claims.append(p['peer_value'])
        else:
            continue
    #####################################################################
    #ищем среди балансовых показателей
    peer_equity = list()
    for y in balance_indicators:
        if y['name'] == 'equity':#собственный капитал
            equity_c = y['value']
            equity_m = y['total']
            for p in y['peers_balance_ind']:
                peer_equity.append(p['peer_value'])
            break
    months = get_months(b,e)#период анализа
    N = len(months)#кол-во месяцев в анализируемом периоде
    #расчитываем нужные показатели
    Npeers = len(peer_equity)
    peers_roe = list()
    peers_eq_us = list()
    peers_lr = list()
    peers_re_p = list()
    peers_re_c = list()
    #########################################################################
    name = 'ROE (экстраполированная годовая прибыль к собственному капиталу), %'
    value_c = round(net_income_c / equity_c / N * 12 * 100, 1)    
    value_m = round(net_income_m / equity_m / N * 12 * 100, 1)
    if value_c < 0:
        value_c = 'N.A.'
    if value_m < 0:
        value_m = 'N.A.'
    for i in range (0,Npeers):
        value_p = round(peer_net_income[i] / peer_equity[i] / N * 12 * 100, 1)
        if value_p < 0:
            value_p = 'N.A.'
        peers_roe.append({'peer_value':value_p})
    other_financial_indicators.append({'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_roe})
    name = 'Использование капитала (экстраполированные годовые чистые премии к собственному капиталу)'
    value_c = round(net_premiums_c / equity_c / N * 12, 2)
    value_m = round(net_premiums_m / equity_m / N * 12, 2)
    for i in range (0,Npeers):
        value_p = round(peer_net_premiums[i] / peer_equity[i] / N * 12, 2)
        peers_eq_us.append({'peer_value':value_p})
    other_financial_indicators.append({'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_eq_us})
    name = 'Коэффициент выплат (чистые выплаты к чистым премиям), %'
    try:
        value_c = round(net_claims_c / net_premiums_c * 100,1)
    except:
        value_c = 'N.A.'
    try:
        value_m = round(net_claims_m / net_premiums_m * 100,1)
    except:
        value_m = 'N.A.'
    for i in range (0,Npeers):
        try:
            value_p = round(peer_net_claims[i] / peer_net_premiums[i] * 100,1)
        except:
            value_p = 'N.A.'
        peers_lr.append({'peer_value':value_p})
    other_financial_indicators.append({'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_lr})
    name = 'Доля перестрахования в премиях, %'
    try:
        value_c = round((premiums_c-net_premiums_c)/premiums_c*100,1)
    except:
        value_c = 'N.A.'
    try:
        value_m = round((premiums_m-net_premiums_m)/premiums_m*100,1)
    except:
        value_m = 'N.A.'
    for i in range (0,Npeers):
        try:
            value_p = round((peer_premiums[i]-peer_net_premiums[i])/peer_premiums[i]*100,1)
        except:
            value_p = 'N.A.'
        peers_re_p.append({'peer_value':value_p})
    other_financial_indicators.append({'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_re_p})
    name = 'Доля перестрахования в выплатах, %'
    try:
        value_c = round((claims_c-net_claims_c)/claims_c*100,1)
    except:
        value_c = 'N.A.'
    try:
        value_m = round((claims_m-net_claims_m)/claims_m*100,1)
    except:
        value_m = 'N.A.'
    for i in range (0,Npeers):
        try:
            value_p = round((peer_claims[i]-peer_net_claims[i])/peer_claims[i]*100,1)
        except:
            value_p = 'N.A.'
        peers_re_c.append({'peer_value':value_p})
    other_financial_indicators.append({'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_re_c})
    return other_financial_indicators


def is_id_in_arr(_id, _arr):
    arr = list()
    for el in _arr:
        cur_id = el['id']
        arr.append(cur_id)
    if _id in arr:
        res = True
    else:
        res = False
    return res

@app.route('/company_profile',methods=['GET','POST'])
@login_required
def company_profile():#портрет компании
    descr = 'Портрет компании на последнюю отчетную дату (с начала года).'
    form = CompanyProfileForm()
    balance_indicators = list()
    flow_indicators = list()
    other_financial_indicators = list()
    balance_indicators_l_y = list()
    flow_indicators_l_y = list()
    other_financial_indicators_l_y = list()    
    show_charts = False
    show_balance = False
    show_income_statement = False
    show_other_financial_indicators = False
    show_premiums = False
    img_path_premiums_by_LoB_pie =None
    img_path_lr_by_LoB = None
    company_name = None
    premiums = None
    premiums_l_y = None
    img_path_solvency_margin = None
    img_path_net_premium = None
    img_path_equity = None
    img_path_reserves = None
    show_last_year = False
    b = g.min_report_date
    e = g.last_report_date
    b_l_y = None
    e_l_y = None
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        b = form.begin_d.data
        e = form.end_d.data
        save_to_log('company_profile',current_user.id)
        b = datetime(b.year,b.month,1)
        e = datetime(e.year,e.month,1)
        show_last_year = form.show_last_year.data
        #аналогичный период прошлого года
        b_l_y = datetime(b.year-1,b.month,1)
        e_l_y = datetime(e.year-1,e.month,1)
        #зададим пути к диаграммам
        base_img_path = "/chart.png/" + form.company.data + "/" + b.strftime('%m-%d-%Y') + "/" + e.strftime('%m-%d-%Y')
        img_path_premiums_by_LoB_pie = base_img_path + "/premiums_lob"
        img_path_lr_by_LoB = base_img_path + "/lr_lob"
        img_path_solvency_margin = base_img_path + "/solvency_margin"
        img_path_net_premium = base_img_path + "/net_prem"
        img_path_equity = base_img_path + "/equity"
        img_path_reserves = base_img_path + "/reserves"
        #подготовим данные для таблиц
        try:
            peers = Company.query.with_entities(Company.id).filter(Company.nonlife==True).all()#list of non-life companies
        except:
            flash('Не могу получить список компаний с сервера. Проверьте справочник Компаний или обратитесь к администратору')
            return redirect(url_for('company_profile'))
        try:
            company_name, balance_indicators, flow_indicators, premiums, peers_names_arr = show_company_profile(int(form.company.data),peers,b,e,None,False)
            other_financial_indicators = get_other_financial_indicators(balance_indicators,flow_indicators,b,e)
            if show_last_year == True:
                try:
                    company_name_l_y, balance_indicators_l_y, flow_indicators_l_y, premiums_l_y, peers_names_arr_l_y = show_company_profile(int(form.company.data),peers,b_l_y,e_l_y,None,False)
                    other_financial_indicators_l_y = get_other_financial_indicators(balance_indicators_l_y,flow_indicators_l_y,b_l_y,e_l_y)
                except:
                    flash('Не могу получить данные за прошлый год')
                    return redirect(url_for('company_profile'))
        except:
            flash('Не удается получить данные. Возможно, выбранная компания не существовала в заданный период. Попробуйте выбрать другой период.')
            return redirect(url_for('company_profile'))
        show_charts = True
        if len(other_financial_indicators) > 0:
            show_other_financial_indicators = True        
        if len(balance_indicators) > 0:
            show_balance = True
        if len(flow_indicators) > 0:
            show_income_statement = True
        if len(premiums) > 0:
            show_premiums = True
    return render_template('company_profile.html',title='Портрет компании',form=form,descr=descr,company_name=company_name, \
                balance_indicators=balance_indicators, flow_indicators=flow_indicators, \
                show_charts=show_charts,img_path_premiums_by_LoB_pie=img_path_premiums_by_LoB_pie, \
                img_path_lr_by_LoB=img_path_lr_by_LoB,img_path_solvency_margin=img_path_solvency_margin, \
                img_path_net_premium=img_path_net_premium,b=b,e=e,show_other_financial_indicators=show_other_financial_indicators, \
                show_balance=show_balance,show_income_statement=show_income_statement, \
                img_path_equity=img_path_equity,other_financial_indicators=other_financial_indicators, \
                img_path_reserves=img_path_reserves,premiums=premiums,show_premiums=show_premiums, \
                show_last_year=show_last_year,other_financial_indicators_l_y=other_financial_indicators_l_y, \
                balance_indicators_l_y=balance_indicators_l_y, flow_indicators_l_y=flow_indicators_l_y, \
                premiums_l_y=premiums_l_y,round=round,is_id_in_arr=is_id_in_arr,b_l_y=b_l_y,e_l_y=e_l_y)


@app.route('/chart.png/<c_id>/<begin>/<end>/<chart_type>')#plot chart for a given company (id = c_id) and chart type, and given period
def plot_png(c_id,begin,end,chart_type):
    b = datetime.strptime(begin, '%m-%d-%Y')
    e = datetime.strptime(end, '%m-%d-%Y')
    if chart_type == 'premiums_lob':
        fig = create_piechart(c_id,b,e)
    elif chart_type == 'lr_lob':
        fig = create_barchart(c_id,b,e)
    elif chart_type == 'solvency_margin':
        fig = create_plot(c_id,'solvency_margin',b,e)
    elif chart_type == 'net_prem':
        fig = create_plot(c_id,'net_prem',b,e)
    elif chart_type == 'equity':
        fig = create_plot(c_id,'equity',b,e)
    elif chart_type == 'reserves':
        fig = create_plot(c_id,'reserves',b,e)        
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


def create_piechart(c_id,b,e):#plots pie chart for a given company (premium split)
    values, labels = get_premiums_by_LoB(int(c_id),b,e)
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%')
    ax.set_title('Страховые премии, топ-5 классов')
    return fig


def get_premiums_by_LoB(company_id,b,e):
    #premiums by line of business for given company for given period
    top5_insclasses_labels = list()
    top5_insclasses_values = list()
    premiums_by_LoB_per_month = list()
    premiums_by_LoB = list()
    months = get_months(b,e)
    for month in months:
        begin = month['begin']
        end = month['end']
        p_by_LoB_m = Premium_per_month.query.join(Insclass) \
                            .with_entities(Insclass.id,Premium_per_month.value) \
                            .filter(Premium_per_month.company_id==company_id) \
                            .filter(Premium_per_month.beg_date==begin) \
                            .filter(Premium_per_month.end_date==end).all()
        for i in p_by_LoB_m:
            ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
            premiums_by_LoB_per_month.append(ind)
    ins_classes = Insclass.query.all()
    for cl in ins_classes:
        total_v = 0
        for m in premiums_by_LoB_per_month:
            if m['id'] == cl.id:
                total_v += m['value']
        premim_LoB = {'id': cl.id, 'alias': cl.alias, 'value': total_v}
        premiums_by_LoB.append(premim_LoB)
    premiums_by_LoB.sort(key=lambda x: x['value'], reverse=True)#сортируем премии по убыванию
    total_premium = 0.0
    premiums_by_LoB_list = list()
    for el in premiums_by_LoB:
        total_premium += el['value']
        element = {'id': el['id'], 'fullname': el['alias'], 'value': el['value'], 'share': 0.0}
        premiums_by_LoB_list.append(element)
    max_share = 0.0
    for el in premiums_by_LoB_list:
        share = round(el['value'] / total_premium * 100 ,1)
        el['share'] = share
        max_share = max(share,max_share)
    if max_share < 90:#если это не компания, продающая один продукт
        #now take 5 top classes
        top5_insclasses = list()
        top5_insclasses = premiums_by_LoB_list[:5]
        total_top5 = 0.0
        total_top5_share = 0.0
        for el in top5_insclasses:
            total_top5 += el['value']
            total_top5_share += el['share']
        others = {'id': 100, 'fullname': 'прочие', 'value': total_premium-total_top5, 'share': round(100-total_top5_share,1)}
        top5_insclasses.append(others)
        for el in top5_insclasses:#prepare labels and values for pie chart        
            top5_insclasses_labels.append(el['fullname'])
            top5_insclasses_values.append(el['share'])
    else:#если компания продает один продукт
        top5_insclasses_labels.append(premiums_by_LoB_list[0]['fullname'])
        top5_insclasses_values.append(premiums_by_LoB_list[0]['share'])
    return top5_insclasses_values, top5_insclasses_labels


def create_barchart(c_id,b,e):#plots bar chart for a given company
    labels, values = get_lr_by_LoB(c_id,b,e)
    ind = np.arange(len(values))  # the x locations for the groups
    fig, ax = plt.subplots()
    w = 0.75
    ax.bar(ind, values, w)    
    ax.set_ylabel('Коэф. выплат, брутто, %')
    ax.set_title('Коэф. выплат по продуктам, топ-5 классов')
    ax.set_xticks(ind)
    ax.set_xticklabels(labels)    
    return fig


def get_lr_by_LoB(company_id,b,e):#рассчитаем коэф. выплат по продуктам для выбранной компании
    lr_list = list()
    premiums_by_LoB_per_month = list()
    claims_by_LoB_per_month = list()
    premiums_by_LoB = list()
    claims_by_LoB = list()
    months = get_months(b,e)
    for month in months:
        begin = month['begin']
        end = month['end']
        p_by_LoB_m = Premium_per_month.query.join(Insclass) \
                            .with_entities(Insclass.id,Premium_per_month.value) \
                            .filter(Premium_per_month.company_id==company_id) \
                            .filter(Premium_per_month.beg_date==begin) \
                            .filter(Premium_per_month.end_date==end).all()
        for i in p_by_LoB_m:
            ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
            premiums_by_LoB_per_month.append(ind)
        c_by_LoB_m = Claim_per_month.query.join(Insclass) \
                            .with_entities(Insclass.id,Claim_per_month.value) \
                            .filter(Claim_per_month.company_id==company_id) \
                            .filter(Claim_per_month.beg_date==begin) \
                            .filter(Claim_per_month.end_date==end).all()
        for i in c_by_LoB_m:
            ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
            claims_by_LoB_per_month.append(ind)
    ins_classes = Insclass.query.all()
    for cl in ins_classes:
        p_total_v = 0
        for m in premiums_by_LoB_per_month:
            if m['id'] == cl.id:
                p_total_v += m['value']
        premim_LoB = {'id': cl.id, 'alias': cl.alias, 'value': p_total_v}
        premiums_by_LoB.append(premim_LoB)
        c_total_v = 0
        for m in claims_by_LoB_per_month:
            if m['id'] == cl.id:
                c_total_v += m['value']
        claim_LoB = {'id': cl.id, 'alias': cl.alias, 'value': c_total_v}
        claims_by_LoB.append(claim_LoB)        
    premiums_by_LoB.sort(key=lambda x: x['value'], reverse=True)#сортируем премии по убыванию
    premiums_by_LoB = premiums_by_LoB[:5]#select first top 5 classes by premiums
    for p in premiums_by_LoB:
        class_id = p['id']
        class_name = p['alias']
        premium = p['value']
        for c in claims_by_LoB:
            if c['id'] == class_id:
                claim = c['value']
        lr = round(claim / premium * 100, 1)
        element = {'class_id':class_id,'class_name':class_name,'lr':lr}
        lr_list.append(element)
    labels = list()
    values = list() 
    for el in lr_list:
        labels.append(el['class_name'])
        values.append(el['lr'])
    return labels, values


def create_plot(c_id,plot_type,b,e):#plots pie chart for a given company
    labels, values = get_data_for_plot(int(c_id),plot_type,b,e)
    fig, ax = plt.subplots()
    ax.plot(labels, values)
    if plot_type == 'solvency_margin':
        ax.set_title('Помесячная динамика норматива ФМП')
        for i,j in zip(labels,values):
            ax.annotate(str(j),xy=(i,j))
    elif plot_type == 'net_prem':
        ax.set_title('Помесячная динамика чистых премий, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(round(j)),xy=(i,j))
    elif plot_type == 'equity':
        ax.set_title('Помесячная динамика собственного капитала, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(round(j)),xy=(i,j))
    elif plot_type == 'reserves':
        ax.set_title('Помесячная динамика страховых резервов, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(round(j)),xy=(i,j))
    fig.autofmt_xdate()
    return fig


def get_data_for_plot(company_id,plot_type,b,e):
    labels = list()
    values = list()    
    if plot_type == 'solvency_margin':
        _sm_id = Indicator.query.filter(Indicator.name == 'solvency_margin').first()
        sm_id = _sm_id.id
        solvency_margin = Financial.query.filter(Financial.indicator_id == sm_id) \
                            .filter(Financial.company_id == company_id) \
                            .filter(Financial.report_date >= b) \
                            .filter(Financial.report_date <= e) \
                            .order_by(Financial.report_date).all()
        for el in solvency_margin:
            label = str(el.report_date.year) + '-' +str(el.report_date.month)
            labels.append(label)
            values.append(el.value)
    elif plot_type =='net_prem':
        _np_id = Indicator.query.filter(Indicator.name == 'net_premiums').first()
        np_id = _np_id.id
        net_prem = Financial_per_month.query.filter(Financial_per_month.indicator_id == np_id) \
                        .filter(Financial_per_month.company_id == company_id) \
                        .filter(Financial_per_month.beg_date >= b) \
                        .filter(Financial_per_month.end_date <= e) \
                        .order_by(Financial_per_month.beg_date).all()
        for el in net_prem:
            label = str(el.beg_date.year) + '-' +str(el.beg_date.month)
            labels.append(label)
            values.append(el.value/1000)
    elif plot_type =='equity':
        _eq_id = Indicator.query.filter(Indicator.name == 'equity').first()
        eq_id = _eq_id.id
        equity = Financial.query.filter(Financial.indicator_id == eq_id) \
                            .filter(Financial.company_id == company_id) \
                            .filter(Financial.report_date >= b) \
                            .filter(Financial.report_date <= e) \
                            .order_by(Financial.report_date).all()
        for el in equity:
            label = str(el.report_date.year) + '-' +str(el.report_date.month)
            labels.append(label)
            values.append(el.value/1000)
    elif plot_type =='reserves':
        _rs_id = Indicator.query.filter(Indicator.name == 'reserves').first()
        rs_id = _rs_id.id
        equity = Financial.query.filter(Financial.indicator_id == rs_id) \
                            .filter(Financial.company_id == company_id) \
                            .filter(Financial.report_date >= b) \
                            .filter(Financial.report_date <= e) \
                            .order_by(Financial.report_date).all()
        for el in equity:
            label = str(el.report_date.year) + '-' +str(el.report_date.month)
            labels.append(label)
            values.append(el.value/1000)            
    return labels, values


def get_class_companies(class_id,b,e):#инфо по выбранному классу по компаниям за период
    _class_name = Insclass.query.filter(Insclass.id == class_id).first()
    class_name = _class_name.alias#class name
    months = get_months(b,e)#list of months for a given period
    ##########################################################
    #fetch premiums and claims for class and period
    premiums_per_month = list()
    claims_per_month = list()
    for month in months:
        begin = month['begin']
        end = month['end']
        #fetch premiums
        premiums = Premium_per_month.query.join(Company) \
                            .with_entities(Company.id,Premium_per_month.value) \
                            .filter(Premium_per_month.insclass_id == class_id) \
                            .filter(Premium_per_month.beg_date == begin) \
                            .filter(Premium_per_month.end_date == end).all()
        for i in premiums:
            ind = {'b':begin,'e':end,'company_id':i.id,'value':i.value}
            premiums_per_month.append(ind)
        #fetch claims
        claims = Claim_per_month.query.join(Company) \
                            .with_entities(Company.id,Claim_per_month.value) \
                            .filter(Claim_per_month.insclass_id == class_id) \
                            .filter(Claim_per_month.beg_date == begin) \
                            .filter(Claim_per_month.end_date == end).all()
        for i in claims:
            ind = {'b':begin,'e':end,'company_id':i.id,'value':i.value}
            claims_per_month.append(ind)            
    ##################################################################
    class_companies = list()#final list to be returned
    companies = Company.query.all()
    total_mkt_prem = 0.0
    for c in companies:#compute for each company        
        total_prem = 0.0
        total_claim = 0.0
        for m in premiums_per_month:
            if m['company_id'] == c.id:
                total_prem += m['value']
        for m in claims_per_month:
            if m['company_id'] == c.id:
                total_claim += m['value']
        total_mkt_prem += total_prem
        if total_prem > 0:
            lr = round(total_claim / total_prem * 100,2)#коэф-т выплат
        else:
            lr = 'N.A.'
        if total_prem > 0 or total_claim > 0:
            company_el = {'id': c.id, 'name': c.alias, 'premium': total_prem, 'claim': total_claim, 'lr':lr}
            class_companies.append(company_el)
    class_companies.sort(key=lambda x: x['premium'], reverse=True)#сортируем по убыванию
    #compute mkt share
    for i in class_companies:
        share = round(i['premium'] / total_mkt_prem * 100,2)
        i['share'] = share
    return class_name, class_companies


def get_class_info(class_id,b,e):#инфо по динамике развития класса за период
    months = get_months(b,e)#list of months for a given period
    class_info = list()#final list to be returned
    for month in months:
        begin = month['begin']
        end = month['end']
        premiums = Premium_per_month.query \
                            .with_entities(Premium_per_month.value) \
                            .filter(Premium_per_month.insclass_id == class_id) \
                            .filter(Premium_per_month.beg_date == begin) \
                            .filter(Premium_per_month.end_date == end).all()
        claims = Claim_per_month.query \
                            .with_entities(Claim_per_month.value) \
                            .filter(Claim_per_month.insclass_id == class_id) \
                            .filter(Claim_per_month.beg_date == begin) \
                            .filter(Claim_per_month.end_date == end).all()                            
        month_total_p = 0.0
        for p in premiums:
            month_total_p += p.value
        month_total_c = 0.0
        for c in claims:
            month_total_c += c.value            
        month_name = str(begin.year) + '-' +str(begin.month)
        if month_total_p > 0:
            lr = round(month_total_c / month_total_p * 100,2)
        else:
            lr = 'N.A.'
        el = {'month_name':month_name,'premium':month_total_p,'claim':month_total_c,'lr':lr}
        class_info.append(el)
    total_p = 0.0
    total_c = 0.0
    for i in class_info:
        total_p += i['premium']
        total_c += i['claim']
    if total_c > 0:
        total_lr = round(total_c / total_p * 100, 2)
    else:
        total_c = 'N.A.'
    class_totals = {'total_p':total_p,'total_c':total_c,'total_lr':total_lr}
    return class_info, class_totals

@app.route('/chart_for_class.png/<c_id>/<begin>/<end>/<chart_type>')#plot chart for a given class
def plot_png_for_class(c_id,begin,end,chart_type):
    b = datetime.strptime(begin, '%m-%d-%Y')
    e = datetime.strptime(end, '%m-%d-%Y')    
    fig = create_plot_for_class(c_id,b,e,chart_type)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


def create_plot_for_class(c_id,b,e,chart_type):#plots pie chart for a given company
    class_info, class_totals = get_class_info(c_id,b,e)#динамика развития по классу
    labels = list()
    values_prem = list()
    values_claim = list()    
    for el in class_info:
        labels.append(el['month_name'])
        values_prem.append(round(el['premium']/1000))
        values_claim.append(round(el['claim']/1000))        
    #plot chart depending on chart_type
    if chart_type == 'prem':
        values = values_prem
        fig, ax = plt.subplots()
        ax.plot(labels, values)
        ax.set_title('Помесячная динамика премий, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(j),xy=(i,j))
    elif chart_type == 'claim':
        values = values_claim
        fig, ax = plt.subplots()
        ax.plot(labels, values)
        ax.set_title('Помесячная динамика выплат, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(round(j)),xy=(i,j))
    fig.autofmt_xdate()
    return fig


@app.route('/class_profile',methods=['GET','POST'])
@login_required
def class_profile():#инфо по классу
    descr = 'Информация по классу страхования. Выберите класс и период.'
    form = ClassProfileForm()
    b = g.min_report_date
    e = g.last_report_date
    class_companies = None
    class_companies_len = None
    class_totals = None
    class_info = None
    class_name = None
    img_path_prem = None
    img_path_claim = None
    show_last_year = False
    class_name_l_y = None
    class_companies_l_y = None
    class_info_l_y = None
    class_totals_l_y = None
    b_l_y = None
    e_l_y = None
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        b = form.begin_d.data
        e = form.end_d.data
        save_to_log('class_profile',current_user.id)
        b = datetime(b.year,b.month,1)
        e = datetime(e.year,e.month,1)
        show_last_year = form.show_last_year.data
        #аналогичный период прошлого года
        b_l_y = datetime(b.year-1,b.month,1)
        e_l_y = datetime(e.year-1,e.month,1)
        class_id = int(form.insclass.data)
        try:
            class_name, class_companies = get_class_companies(class_id,b,e)#информация по компаниям по выбранному классу
            class_info, class_totals = get_class_info(class_id,b,e)
            if show_last_year == True:
                try:
                    class_name_l_y, class_companies_l_y = get_class_companies(class_id,b_l_y,e_l_y)
                    class_info_l_y, class_totals_l_y = get_class_info(class_id,b_l_y,e_l_y)
                except:
                    flash('Не могу получить данные за прошлый год')
                    return redirect(url_for('class_profile'))
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранному классу за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('class_profile'))
        class_companies_len = len(class_companies)
        #базовый путь к графикам
        base_img_path = "/chart_for_class.png/" + form.insclass.data + "/" + b.strftime('%m-%d-%Y') + "/" + e.strftime('%m-%d-%Y')
        img_path_prem = base_img_path + "/prem"
        img_path_claim = base_img_path + "/claim"
    return render_template('class_profile.html',title='Информация по продукту',form=form,descr=descr, \
                b=b,e=e,class_companies=class_companies,class_name=class_name, \
                class_companies_len=class_companies_len,img_path_prem=img_path_prem, \
                img_path_claim=img_path_claim,class_info=class_info,class_totals=class_totals ,\
                show_last_year=show_last_year,class_companies_l_y=class_companies_l_y, \
                class_totals_l_y=class_totals_l_y,b_l_y=b_l_y,e_l_y=e_l_y)


def get_peers_names(peers):#получаем имена конкурентов исходя из их id
    ids = list()
    for p in peers:
        ids.append(p[0])
    nonlife_companies = Company.query.with_entities(Company.id,Company.alias) \
        .filter(Company.nonlife==True).all()
    res_str = ' | '
    for c in nonlife_companies:
        if c.id in ids:
            res_str = res_str + c.alias + ' | '
    return res_str

@app.route('/peers_review',methods=['GET','POST'])
@login_required
def peers_review():#сравнение с конкурентами
    descr = 'Сравнение с конкурентами за выбранный период'
    form = PeersForm()
    balance_indicators = list()
    flow_indicators = list()
    other_financial_indicators = list() 
    show_balance = False
    show_income_statement = False
    show_other_financial_indicators = False
    company_name = None
    peers_names = None
    peers_names_arr = None
    show_competitors = False
    b = g.min_report_date
    e = g.last_report_date
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        b = form.begin_d.data
        e = form.end_d.data
        c_id = int(form.company.data)#компания
        peers_str = form.peers.data#выбранные конкуренты
        peers = list()
        for c in peers_str:#convert id to int
            peers.append((int(c),))        
        save_to_log('peers_review',current_user.id)        
        b = datetime(b.year,b.month,1)
        e = datetime(e.year,e.month,1)
        #подготовим данные для таблиц
        if form.company.data in peers_str:
            flash('''Вы выбрали Вашу компанию в списке конкурентов. 
                Сравнивать себя с собой не имеет большого смысла, не правда ли?
                Составьте список конкурентов без указания своей компании и попробуйте снова.''')
            return redirect(url_for('peers_review'))
        show_competitors = form.show_competitors.data#показывать детали по каждому конкуренту
        try:
            company_name, balance_indicators, flow_indicators, premiums, peers_names_arr = show_company_profile(c_id,peers,b,e,len(peers),show_competitors)
            other_financial_indicators = get_other_financial_indicators(balance_indicators,flow_indicators,b,e)
            peers_names = get_peers_names(peers)            
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранным компаниям за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('peers_review'))
        if len(other_financial_indicators) > 0:
            show_other_financial_indicators = True
        if len(balance_indicators) > 0:
            show_balance = True
        if len(flow_indicators) > 0:
            show_income_statement = True
    return render_template('peers_review.html',title='Сравнение с конкурентами',form=form,descr=descr, \
                        show_balance=show_balance,show_income_statement=show_income_statement, \
                        show_other_financial_indicators=show_other_financial_indicators,b=b,e=e, \
                        company_name=company_name,balance_indicators=balance_indicators, \
                        flow_indicators=flow_indicators,other_financial_indicators=other_financial_indicators, \
                        peers_names=peers_names,show_competitors=show_competitors,peers_names_arr=peers_names_arr)


def get_ranking(b,e):#вспомогательная функция - получаем данные для ранкинга
    months = get_months(b,e)
    nonlife_companies = Company.query.filter(Company.nonlife==True).all()#список nonlife компаний
    ############################################################################
    try:
        net_premium_id = Indicator.query.filter(Indicator.name == 'net_premiums').first()
    except:
        net_premium_id = None
    #query companies by net premium
    net_premiums = list()
    net_premiums_per_month = list()    
    if net_premium_id is not None:
        for month in months:
            begin = month['begin']
            end = month['end']
            net_premiums_per_m = Financial_per_month.query.join(Company) \
                            .with_entities(Company.id,Financial_per_month.value) \
                            .filter(Financial_per_month.indicator_id == net_premium_id.id) \
                            .filter(Financial_per_month.beg_date == begin) \
                            .filter(Financial_per_month.end_date == end) \
                            .filter(Company.nonlife == True).all()
            for i in net_premiums_per_m:
                ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
                net_premiums_per_month.append(ind)
        for c in nonlife_companies:
            total_v = 0
            for m in net_premiums_per_month:
                if m['id'] == c.id:
                    total_v += m['value']            
            net_premiums.append({'id': c.id, 'alias': c.alias, 'value': total_v})
        net_premiums.sort(key=lambda x: x['value'], reverse=True)#сортируем по убыванию    
    net_premiums_total = sum(i['value'] for i in net_premiums)
    for el in net_premiums:
        if net_premiums_total>0:
            share = round(el['value'] / net_premiums_total * 100,2)
            if share < 0:
                el['share'] = 'N.A.'
            else:
                el['share'] = share
    ##########################################################################
    try:
        equity_id = Indicator.query.filter(Indicator.name == 'equity').first()
    except:
        equity_id = None
    #query companies by equity
    if equity_id is not None and e is not None:
        equities = Financial.query.join(Company) \
                            .with_entities(Financial.value,Company.alias,Company.id) \
                            .filter(Financial.indicator_id == equity_id.id) \
                            .filter(Financial.report_date == e) \
                            .filter(Company.nonlife == True) \
                            .order_by(Financial.value.desc()).all()
    equity_total = sum(i.value for i in equities)
    equity = list()
    for el in equities:
        if equity_total>0:
            share = round(el.value / equity_total * 100,2)
            if share < 0:
                share = 'N.A.'
        equity.append({'id': el.id, 'value':el.value,'alias':el.alias,'share':share})
    #########################################################################
    try:
        netincome_id = Indicator.query.filter(Indicator.name == 'net_income').first()
    except:
        netincome_id = None
    #query companies by net income
    netincome = list()
    netincome_per_month = list()    
    if netincome_id is not None:
        for month in months:
            begin = month['begin']
            end = month['end']
            netincome_per_m = Financial_per_month.query.join(Company) \
                            .with_entities(Company.id,Financial_per_month.value) \
                            .filter(Financial_per_month.indicator_id == netincome_id.id) \
                            .filter(Financial_per_month.beg_date == begin) \
                            .filter(Financial_per_month.end_date == end) \
                            .filter(Company.nonlife == True).all()
            for i in netincome_per_m:
                ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
                netincome_per_month.append(ind)
        for c in nonlife_companies:
            total_v = 0
            for m in netincome_per_month:
                if m['id'] == c.id:
                    total_v += m['value']
            netincome.append({'id': c.id, 'alias': c.alias, 'value': total_v})
        netincome.sort(key=lambda x: x['value'], reverse=True)#сортируем по убыванию
    netincome_total = sum(i['value'] for i in netincome)
    for el in netincome:
        if netincome_total>0:
            share = round(el['value'] / netincome_total * 100,2)
            if share < 0:
                el['share'] = 'N.A.'
            else:
                el['share'] = share    
    ##############################################################################
    try:
        solvency_margin_id = Indicator.query.filter(Indicator.name == 'solvency_margin').first()
    except:
        solvency_margin_id = None
    #query solvency margins
    if solvency_margin_id is not None and e is not None:
        solvency_margin = Financial.query.join(Company) \
                            .with_entities(Financial.value,Company.alias,Company.id) \
                            .filter(Financial.indicator_id == solvency_margin_id.id) \
                            .filter(Financial.report_date == e) \
                            .filter(Company.nonlife == True) \
                            .order_by(Financial.value.desc()).all()
    solvency_margin_av = round(sum(i.value for i in solvency_margin) / float(len(solvency_margin)),2)
    #################################################################################
    try:
        net_claim_id = Indicator.query.filter(Indicator.name == 'net_claims').first()
    except:
        net_claim_id = None
    #query net claims
    net_claims = list()
    net_claims_per_month = list()    
    if net_claim_id is not None:
        for month in months:
            begin = month['begin']
            end = month['end']
            net_claims_per_m = Financial_per_month.query.join(Company) \
                            .with_entities(Company.id,Financial_per_month.value) \
                            .filter(Financial_per_month.indicator_id == net_claim_id.id) \
                            .filter(Financial_per_month.beg_date == begin) \
                            .filter(Financial_per_month.end_date == end) \
                            .filter(Company.nonlife == True).all()
            for i in net_claims_per_m:
                ind = {'b':begin, 'e':end, 'id':i.id, 'value':i.value}
                net_claims_per_month.append(ind)
        for c in nonlife_companies:
            total_v = 0
            for m in net_claims_per_month:
                if m['id'] == c.id:
                    total_v += m['value']
            net_claims.append({'id': c.id, 'alias': c.alias, 'value': total_v})
    netclaim_total = sum(i['value'] for i in net_claims)
    ###########################################################################
    #compute LR (net claim coefficient)
    lr_list = list()
    for p in net_premiums:
        company_id = p['id']
        company_name = p['alias']
        premium = p['value']
        for c in net_claims:
            if c['id'] == company_id:
                claim = c['value']
        if premium > 0:
            lr = round(claim / premium * 100, 1)
        else:
            lr = 'N.A.'
        element = {'id':p['id'], 'company_name':company_name,'lr':lr}
        lr_list.append(element)
    lr_av = round(netclaim_total / net_premiums_total * 100, 2)
    return net_premiums, equity, netincome, solvency_margin, lr_list, \
        net_premiums_total, equity_total, netincome_total, solvency_margin_av, lr_av


@app.route('/ranking',methods=['GET','POST'])#ранкинг, обзор рынка
@login_required
def ranking():
    form = RankingForm()
    b = g.min_report_date
    e = g.last_report_date
    net_premiums = None
    net_premiums_total = None
    net_premiums_len = None
    equity = None
    equity_total = None
    equity_len = None
    netincome = None
    netincome_total = None
    netincome_len = None
    solvency_margin = None
    solvency_margin_av = None
    solvency_margin_len = None
    lr_list = None
    lr_av = None
    lr_list_len = None
    show_last_year = False
    net_premiums_l_y = None
    equity_l_y = None
    netincome_l_y = None
    solvency_margin_l_y = None
    lr_list_l_y = None
    net_premiums_total_l_y = None
    equity_total_l_y = None
    netincome_total_l_y = None
    solvency_margin_av_l_y = None
    lr_av_l_y = None
    b_l_y = None
    e_l_y = None
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        b = form.begin_d.data
        e = form.end_d.data        
        save_to_log('ranking',current_user.id)
        b = datetime(b.year,b.month,1)
        e = datetime(e.year,e.month,1)
        show_last_year = form.show_last_year.data
        #аналогичный период прошлого года
        b_l_y = datetime(b.year-1,b.month,1)
        e_l_y = datetime(e.year-1,e.month,1)        
        net_premiums, equity, netincome, solvency_margin, lr_list, \
                net_premiums_total, equity_total, netincome_total, \
                solvency_margin_av, lr_av = get_ranking(b,e)#рассчитаем показатели
        if show_last_year == True:
            try:
                net_premiums_l_y, equity_l_y, netincome_l_y, solvency_margin_l_y, lr_list_l_y, \
                    net_premiums_total_l_y, equity_total_l_y, netincome_total_l_y, \
                    solvency_margin_av_l_y, lr_av_l_y = get_ranking(b_l_y,e_l_y)#рассчитаем показатели за прошлый год
            except:
                flash('Не могу получить данные за прошлый год')
                return redirect(url_for('ranking'))        
        net_premiums_len = len(net_premiums)
        equity_len = len(equity)
        netincome_len = len(netincome)
        solvency_margin_len = len(solvency_margin)
        lr_list_len = len(lr_list)
    return render_template('ranking.html', \
                    net_premiums=net_premiums,net_premiums_len=net_premiums_len, \
                    equity=equity, equity_len=equity_len, b=b, e=e, show_last_year=show_last_year, \
                    netincome=netincome, netincome_len=netincome_len, \
                    solvency_margin=solvency_margin, solvency_margin_len=solvency_margin_len, \
                    lr_list=lr_list, lr_list_len=lr_list_len,form=form, \
                    net_premiums_total=net_premiums_total,equity_total=equity_total, \
                    netincome_total=netincome_total, solvency_margin_av=solvency_margin_av, \
                    lr_av=lr_av,net_premiums_l_y=net_premiums_l_y, equity_l_y=equity_l_y, \
                    netincome_l_y=netincome_l_y, solvency_margin_l_y=solvency_margin_l_y, \
                    lr_list_l_y=lr_list_l_y, net_premiums_total_l_y=net_premiums_total_l_y, \
                    equity_total_l_y=equity_total_l_y, netincome_total_l_y=netincome_total_l_y, \
                    solvency_margin_av_l_y=solvency_margin_av_l_y, lr_av_l_y=lr_av_l_y, \
                    round=round,is_id_in_arr=is_id_in_arr,b_l_y=b_l_y,e_l_y=e_l_y)


@app.route('/add_new_company',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def add_new_company():
    form = AddEditCompanyForm()
    if form.validate_on_submit():
        name = form.name.data
        alias = form.alias.data
        nonlife = form.nonlife.data
        alive = form.alive.data    
        company = Company(name=name,alias=alias,nonlife=nonlife,alive=alive)
        db.session.add(company)
        db.session.commit()
        try:
            c_saved = Company.query.filter(Company.name == name).first()
            _id = c_saved.id
            company_all_names = Company_all_names(name=name,company_id=_id)
            db.session.add(company_all_names)
            db.session.commit()
        except:
            flash('Не могу получить id созданной компании')
            return redirect(url_for('add_new_company'))        
        flash('Новая компания добавлена')
        return redirect(url_for('add_new_company'))
    return render_template('add_edit_company.html', form=form)


@app.route('/edit_company/<company_id>',methods=['GET', 'POST'])#изменить имя компании (переименование)
@login_required
@required_roles('admin')
def edit_company(company_id=None):
    form = AddEditCompanyForm()
    obj = Company.query.filter(Company.id == company_id).first()
    if request.method == 'GET':        
        form = AddEditCompanyForm(obj=obj)
    if form.validate_on_submit():
        obj.name = form.name.data
        obj.alias = form.alias.data
        obj.nonlife = form.nonlife.data
        obj.alive = form.alive.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('edit_company', company_id=company_id))
    return render_template('add_edit_company.html',form=form)


@app.route('/add_new_class',methods=['GET', 'POST'])#добавить новое имя класса (переименование)
@login_required
@required_roles('admin')
def add_new_class():
    form = AddEditClassForm()
    if form.validate_on_submit():
        name = form.name.data
        fullname = form.fullname.data
        alias = form.alias.data
        nonlife = form.nonlife.data
        obligatory = form.obligatory.data
        voluntary_personal = form.voluntary_personal.data
        voluntary_property = form.voluntary_property.data
        insclass = Insclass(name=name,fullname=fullname,alias=alias, \
                nonlife=nonlife,obligatory=obligatory, \
                voluntary_personal=voluntary_personal,voluntary_property=voluntary_property)
        db.session.add(insclass)
        db.session.commit()
        try:
            c_saved = Insclass.query.filter(Insclass.name == name).first()
            _id = c_saved.id
            insclass_all_names = Insclass_all_names(name=name,fullname=fullname,insclass_id=_id)
            db.session.add(insclass_all_names)
            db.session.commit()
        except:
            flash('Не могу получить id созданного класса')
            return redirect(url_for('add_new_class'))        
        flash('Новый класс добавлен')
        return redirect(url_for('add_new_class'))
    return render_template('add_edit_class.html', form=form)


@app.route('/edit_class/<class_id>',methods=['GET', 'POST'])#изменить имя класса (переименование)
@login_required
@required_roles('admin')
def edit_class(class_id=None):
    form = AddEditClassForm()
    obj = Insclass.query.filter(Insclass.id == class_id).first()
    if request.method == 'GET':        
        form = AddEditClassForm(obj=obj)
    if form.validate_on_submit():
        obj.name = form.name.data
        obj.fullname = form.fullname.data
        obj.alias = form.alias.data
        obj.nonlife = form.nonlife.data
        obj.obligatory = form.obligatory.data
        obj.voluntary_personal = form.voluntary_personal.data
        obj.voluntary_property = form.voluntary_property.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('edit_class', class_id=class_id))
    return render_template('add_edit_class.html',form=form)


def send_async_email(app,msg):#асинхронная отправка email
    with app.app_context():
        msg.send()


def send_email(subject,body,recipients):#функция отправки email с заданной темой, телом
    credentials = Credentials(username=app.config['EXCHANGE_USERNAME'],password=app.config['EXCHANGE_PASSWORD'])
    config = Configuration(server=app.config['EXCHANGE_SERVER'],credentials=credentials)
    account = Account(primary_smtp_address=app.config['EXCHANGE_PRIMARY_SMTP_ADDRESS'],config=config,autodiscover=False,access_type=DELEGATE)
    msg = Message(account=account,subject=subject,body=body,to_recipients=recipients)
    Thread(target=send_async_email,args=(app,msg)).start()
    #msg.send()


@app.route('/send_email_to_users',methods=['GET', 'POST'])#отправить мейл пользователям
@login_required
@required_roles('admin')
def send_email_to_users():
    form = SendEmailToUsersForm()
    descr = 'Заполните тему и текст сообщения. Выберите получателей, или пометьте Отправить всем'
    if form.validate_on_submit():
        subject = form.subject.data
        body = form.body.data
        send_to_all = form.send_to_all.data
        recipients = list()
        users_selected = list()
        if send_to_all == True:#отправляем всем пользователям
            try:
                users = User.query.all()
                for u in users:
                    recipients.append(u.email)
            except:
                flash('Не могу получить список пользователей с сервера')
                return redirect(url_for('send_email_to_users'))
        else:#отправляем только выбранным
            user_list = form.users.data
            for c in user_list:#convert id to int
                users_selected.append((int(c),))
            for u in users_selected:
                _u = User.query.filter(User.id == u[0]).first()                
                recipients.append(_u.email)
        try:#пытаемся отправить сообщение            
            send_email(subject,body,recipients)
        except:
            flash('Не могу отправить сообщение')
            return redirect(url_for('send_email_to_users'))
        flash('Сообщение отправлено.')
        return redirect(url_for('send_email_to_users'))
    return render_template('send_email.html', form=form, descr=descr)


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    subject = 'Восстановление пароля'
    body = render_template('email/reset_password.txt',user=user,token=token)
    recipients = [user.email]
    send_email(subject,body,recipients)


@app.route('/reset_password_request',methods=['GET', 'POST'])#запросить восстановление пароля
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter(User.email == form.email.data).first()
        if user:
            send_password_reset_email(user)
            flash('Было отправлено письмо с дальнейшими инструкциями. Проверьте свой почтовый ящик.')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким e-mail не зарегистрирован')
            return redirect(url_for('login'))
    return render_template('reset_password_request.html',title='Восстановление пароля',form=form)


@app.route('/reset_password/<token>',methods=['GET', 'POST'])#восстановление пароля - изменить пароль
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()    
        flash('Пароль успешно изменён')
        return redirect(url_for('login'))
    return render_template('reset_password.html',title='Изменение пароля',form=form)

#список функций для логирования
views_for_logging = [{'id':0,'name':'index'},
                        {'id':1,'name':'company_profile'},
                        {'id':2,'name':'class_profile'},
                        {'id':3,'name':'peers_review'},
                        {'id':4,'name':'ranking'}
                    ]


def save_to_log(view_name,user_id):#сохраним факт запроса в лог
    view_id = get_view_id(view_name)
    log_instance = View_log(view_id=view_id,user_id=user_id)
    db.session.add(log_instance)
    db.session.commit()


def get_view_id(name):#получаем id запрошенной функции
    res = None
    for v in views_for_logging:
        if v['name'] == name:
            res = v['id']
    return res


def get_view_name(_id):#получаем название запрошенной функции
    res = None
    for v in views_for_logging:
        if v['id'] == _id:
            res = v['name']
    return res

@app.route('/usage_log')#отправить мейл пользователям
@login_required
@required_roles('admin')
def usage_log():
    page = request.args.get('page',1,type=int)
    log_events = View_log.query.join(User) \
                .with_entities(User.username,View_log.timestamp,View_log.view_id) \
                .order_by(View_log.timestamp.desc()).paginate(page,app.config['POSTS_PER_PAGE'],False)
    next_url = url_for('usage_log',page=log_events.next_num) if log_events.has_next else None
    prev_url = url_for('usage_log',page=log_events.prev_num) if log_events.has_prev else None                
    return render_template('usage_log.html',title='Лог использования портала', \
        get_view_name=get_view_name,log_events=log_events.items,next_url=next_url,prev_url=prev_url)


    #page = request.args.get('page',1,type=int)
    #posts = Post.query.order_by(Post.timestamp.desc()).paginate(page,app.config['POSTS_PER_PAGE'],False)
    #next_url = url_for('explore',page=posts.next_num) if posts.has_next else None
    #prev_url = url_for('explore',page=posts.prev_num) if posts.has_prev else None
    #return render_template('explore.html',title='Все посты',posts=posts.items,next_url=next_url,prev_url=prev_url)