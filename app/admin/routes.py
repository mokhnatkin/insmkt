from flask import render_template, flash, redirect, url_for, request, \
                current_app, jsonify, g, send_file, Response
from app import db
from app.admin.forms import EditUserForm, DictUploadForm, DataUploadForm, \
                    ComputePerMonthIndicators, DictSelectForm, \
                    AddNewCompanyName, AddNewClassName, \
                    AddEditCompanyForm, AddEditClassForm, \
                    UsageLogForm, SendEmailToUsersForm
from flask_login import login_required
from app.models import User, Post, Upload, Company, Insclass, Indicator, Financial, \
            Premium, Claim, Financial_per_month, Premium_per_month, Claim_per_month, \
            Compute, Company_all_names, Insclass_all_names, View_log
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import re
import io
from xlrd import open_workbook
import random
from sqlalchemy import func
from app.admin import bp
from app.universal_routes import before_request_u, required_roles_u, \
                        get_view_name, send_email


@bp.before_request
def before_request():
    return before_request_u()

def required_roles(*roles):
    return required_roles_u(*roles)


@bp.route('/instruction')#инструкция
@login_required
@required_roles('admin')
def instruction():
    company_list = '_companies.xlsx'#образец для загрузки справочника - список компаний
    insclass_list = '_classes.xlsx'#образец для загрузки справочника - список классов
    indicator_list = '_indicators.xlsx'#образец для загрузки справочника - список показателей
    return render_template('admin/admin/instruction.html',title='Инструкция',company_list=company_list,insclass_list=insclass_list,indicator_list=indicator_list)


@bp.route('/edit_user/<user_id>',methods=['GET', 'POST'])#редактировать email пользователя
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
        return redirect(url_for('admin.edit_user', user_id=user_id))
    return render_template('admin/edit_user.html',form=form)


@bp.route('/users')#список пользователей
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
    return render_template('admin/users.html',users=users,users_len=users_len)


@bp.route('/files')#список загруженных файлов
@login_required
@required_roles('admin')
def files():
    files = Upload.query.order_by(Upload.timestamp.desc()).all()
    return render_template('admin/files.html',files=files)


@bp.route('/computes')#список выполненных перерасчетов
@login_required
@required_roles('admin')
def computes():
    computes = Compute.query.order_by(Compute.timestamp.desc()).all()
    return render_template('admin/computes.html',computes=computes)


@bp.route('/files/<fname>')#файл для скачивания на комп
@login_required
@required_roles('admin')
def downloadFile(fname = None):
    p = os.path.join(os.path.dirname(os.path.abspath(current_app.config['UPLOAD_FOLDER'])),current_app.config['UPLOAD_FOLDER'],fname)
    return send_file(p, as_attachment=True)


def allowed_file(filename):#проверка файла - расширение должно быть разрешено
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']        


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


@bp.route('/upload_file/<upload_type>',methods=['GET', 'POST'])#загрузить файл
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
                    return redirect(url_for('admin.upload_file', upload_type='data'))
            form.file.data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))            
            try:
                wb = open_workbook(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                num_sheets = len(wb.sheet_names())
            except:
                flash('Не могу открыть excel файл - неизвестный формат.')
                return redirect(url_for('admin.upload_file', upload_type='data'))
            if num_sheets > 1:
                flash('В выбранном файле более одного листа. Удалите ненужные листы во избежание ошибок')
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                except:
                    pass
                return redirect(url_for('admin.upload_file', upload_type='data'))
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
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                        except:
                            pass
                        db.session.delete(upload)
                        db.session.commit()
                    return redirect(url_for('admin.upload_file', upload_type='dictionary'))
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
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                        except:
                            pass
                        db.session.delete(upload)
                        db.session.commit()                            
                        return redirect(url_for('admin.upload_file', upload_type='data'))
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
                                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                            except:
                                pass
                            db.session.delete(upload)
                            db.session.commit()                                
                            return redirect(url_for('admin.upload_file', upload_type='data'))
                    else:
                        flash('При обработке файла возникли ошибки!')
                    return redirect(url_for('admin.upload_file', upload_type='data'))
        else:
            flash('Файл не выбран, либо некорректное расширение. Доступные расширения:'+str(current_app.config['ALLOWED_EXTENSIONS']))
    return render_template('admin/upload_file.html',title='Загрузка файла',form=form,descr=descr)


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


@bp.route('/dictionary_values',methods=['GET', 'POST'])#просмотр значений выбранного справочника
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
    return render_template('admin/dictionary_values.html',title='Просмотр справочников',form=form, \
        show_companies=show_companies,show_classes=show_classes,show_indicators=show_indicators, \
        companies=companies,insclasses=insclasses,indicators=indicators, \
        company_has_other_names=company_has_other_names,class_has_other_names=class_has_other_names)


@bp.route('/add_new_company_name/<company_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
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
        return redirect(url_for('admin.add_new_company_name', company_id=company_id))
    return render_template('admin/company_all_names.html',company_name=company_name,all_names=all_names, \
                            form=form)


@bp.route('/edit_company_name/<company_id>/<_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
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
        return redirect(url_for('admin.add_new_company_name', company_id=company_id))
    return render_template('admin/company_all_names.html',form=form,company_name=company_name,all_names=all_names)


@bp.route('/add_new_class_name/<class_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
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
        return redirect(url_for('admin.add_new_class_name', class_id=class_id))
    return render_template('admin/class_all_names.html',class_name=class_name,all_names=all_names, \
                            form=form)


@bp.route('/edit_class_name/<class_id>/<_id>',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
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
        return redirect(url_for('admin.add_new_class_name', class_id=class_id))
    return render_template('admin/class_all_names.html',form=form,class_name=class_name,all_names=all_names)


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


@bp.route('/compute',methods=['GET','POST'])#перерасчет показателей
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
            return redirect(url_for('admin.compute'))
        else:
            flash('Данный перерасчёт уже был выполнен. Повторного перерасчёта не требуется.')
            return redirect(url_for('admin.compute'))
    return render_template('admin/compute.html',title='Перерасчет показателей',form=form,descr=descr)


@bp.route('/add_new_company',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
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
            return redirect(url_for('admin.add_new_company'))        
        flash('Новая компания добавлена')
        return redirect(url_for('admin.add_new_company'))
    return render_template('admin/add_edit_company.html', form=form)


@bp.route('/edit_company/<company_id>',methods=['GET', 'POST'])#изменить имя компании (переименование)
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
        return redirect(url_for('admin.edit_company', company_id=company_id))
    return render_template('admin/add_edit_company.html',form=form)


@bp.route('/add_new_class',methods=['GET', 'POST'])#добавить новое имя класса (переименование)
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
            return redirect(url_for('admin.add_new_class'))        
        flash('Новый класс добавлен')
        return redirect(url_for('admin.add_new_class'))
    return render_template('admin/add_edit_class.html', form=form)


@bp.route('/edit_class/<class_id>',methods=['GET', 'POST'])#изменить имя класса (переименование)
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
        return redirect(url_for('admin.edit_class', class_id=class_id))
    return render_template('admin/add_edit_class.html',form=form)


@bp.route('/send_email_to_users',methods=['GET', 'POST'])#отправить мейл пользователям
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
                return redirect(url_for('admin.send_email_to_users'))
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
            return redirect(url_for('admin.send_email_to_users'))
        flash('Сообщение отправлено.')
        return redirect(url_for('admin.send_email_to_users'))
    return render_template('admin/send_email.html', form=form, descr=descr)



def get_data_for_usage_log(beg_d,end_d):#получаем данные для лога
    log_events = View_log.query.join(User) \
                    .with_entities(User.username,View_log.timestamp,View_log.view_id) \
                    .filter(View_log.timestamp >= beg_d) \
                    .filter(View_log.timestamp <= end_d) \
                    .order_by(View_log.timestamp.desc()).all()
    events_by_user = View_log.query.join(User) \
                    .with_entities(User.username,func.count(View_log.view_id).label("amount")) \
                    .filter(View_log.timestamp >= beg_d) \
                    .filter(View_log.timestamp <= end_d) \
                    .group_by(User.username).order_by(func.count(View_log.view_id).desc()).all()
    events_by_page = View_log.query \
                    .with_entities(View_log.view_id,func.count(View_log.view_id).label("amount")) \
                    .filter(View_log.timestamp >= beg_d) \
                    .filter(View_log.timestamp <= end_d) \
                    .group_by(View_log.view_id).order_by(func.count(View_log.view_id).desc()).all()
    events_by_day = list()
    req_by_date = dict()
    for e in log_events:
        d = datetime(e.timestamp.year,e.timestamp.month,e.timestamp.day)
        if d not in req_by_date:
            req_by_date[d] = 1        
        else:
            req_by_date[d] += 1
    for key, val in list(req_by_date.items()):
        day_item = {"date":key,"amount":val}
        events_by_day.append(day_item)
    events_by_day.sort(key=lambda x: x['date'], reverse=False)
    return log_events, events_by_user, events_by_page, events_by_day


@bp.route('/usage_log',methods=['GET','POST'])#отправить мейл пользователям
@login_required
@required_roles('admin')
def usage_log():
    form = UsageLogForm()
    if request.method == 'GET':
        today = datetime.utcnow()
        beg_this_month = datetime(today.year,today.month,1)
        stat_min_date = View_log.query \
            .with_entities(func.min(View_log.timestamp).label("min_time")).first()        
        min_date = stat_min_date[0]
        beg_d = max(beg_this_month,min_date)
        end_d = today
        form.begin_d.data = beg_d
        form.end_d.data = end_d
        log_events, events_by_user, events_by_page, events_by_day = get_data_for_usage_log(beg_d,end_d)
    if form.validate_on_submit():
        b = form.begin_d.data
        e = form.end_d.data + timedelta(days=1)        
        log_events, events_by_user, events_by_page, events_by_day = get_data_for_usage_log(b,e)
    return render_template('admin/usage_log.html',title='Лог использования портала', \
        get_view_name=get_view_name,log_events=log_events, min_date=min_date, \
        events_by_user=events_by_user,events_by_page=events_by_page,form=form, \
        events_by_day=events_by_day)