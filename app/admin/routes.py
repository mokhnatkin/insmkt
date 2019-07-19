from flask import render_template, flash, redirect, url_for, request, \
                current_app, jsonify, g, send_file, Response
from app import db
from app.admin.forms import EditUserForm, DictUploadForm, DataUploadForm, \
                    ComputePerMonthIndicators, DictSelectForm, \
                    AddNewCompanyName, AddNewClassName, \
                    AddEditCompanyForm, AddEditClassForm, \
                    UsageLogForm, SendEmailToUsersForm, HintForm
from flask_login import login_required
from app.models import User, Post, Upload, Company, Insclass, Indicator, Financial, \
            Premium, Claim, Financial_per_month, Premium_per_month, Claim_per_month, \
            Compute, Company_all_names, Insclass_all_names, View_log, Hint
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
                        get_view_name, send_email, allowed_file, add_str_timestamp


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
    h1_txt = 'Изменить данные пользователя'
    obj = User.query.filter(User.id == user_id).first()
    if request.method == 'GET':        
        form = EditUserForm(obj=obj)
    if form.validate_on_submit():
        obj.username = form.username.data
        obj.email = form.email.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('admin.edit_user', user_id=user_id))
    return render_template('admin/add_edit_DB_item.html',form=form,h1_txt=h1_txt)


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

@bp.route('/download_from_static/<fname>')
def download_from_static(fname):
    p = os.path.join(os.path.dirname(os.path.abspath(current_app.config['STATIC_FOLDER'])),current_app.config['STATIC_FOLDER'],fname)
    return send_file(p)


@bp.route('/files/<fname>')#файл для скачивания на комп
@login_required
@required_roles('admin')
def downloadFile(fname = None):
    p = os.path.join(os.path.dirname(os.path.abspath(current_app.config['UPLOAD_FOLDER'])),current_app.config['UPLOAD_FOLDER'],fname)
    return send_file(p, as_attachment=True)




def process_file(file_type,file_subtype,wb,report_date,frst_row,others_col_1,others_col_2,others_col_3):#обработаем загруженный excel файл
    xl_sheet = wb.sheet_by_index(0)
    processed_ok = False
    print('process_file started')
    if file_type == 'Dictionary':
        if file_subtype == 'CompaniesList':
            for row in range(1,xl_sheet.nrows):
                name = str(xl_sheet.cell_value(row, 0)).strip()                
                nonlife = xl_sheet.cell_value(row, 1)
                alive = xl_sheet.cell_value(row, 2)
                alias = str(xl_sheet.cell_value(row, 3)).strip()
                company = Company(name=name,nonlife=nonlife,alive=alive,alias=alias)#сохраняем компанию
                db.session.add(company)
                db.session.commit()
                #получаем id сохраненной компании
                c_saved = Company.query.filter(Company.name == name).first()
                c_id = c_saved.id
                c_all_names = Company_all_names(name=name,company_id=c_id)
                db.session.add(c_all_names)
        elif file_subtype == 'ClassesList':
            for row in range(1,xl_sheet.nrows):
                name = str(xl_sheet.cell_value(row, 0)).strip()
                fullname = str(xl_sheet.cell_value(row, 1)).strip()
                nonlife = xl_sheet.cell_value(row, 2)
                obligatory = xl_sheet.cell_value(row, 3)
                voluntary_personal = xl_sheet.cell_value(row, 4)
                voluntary_property = xl_sheet.cell_value(row, 5)
                alias = str(xl_sheet.cell_value(row, 6)).strip()
                insclass = Insclass(name=name,fullname=fullname,nonlife=nonlife,obligatory=obligatory,voluntary_personal=voluntary_personal,voluntary_property=voluntary_property,alias=alias)            
                db.session.add(insclass)
                db.session.commit()
                #получаем id сохраненного класса
                c_saved = Insclass.query.filter(Insclass.name == name) \
                                .filter(Insclass.fullname == fullname).first()
                c_id = c_saved.id
                c_all_names = Insclass_all_names(name=name,fullname=fullname,insclass_id=c_id)
                db.session.add(c_all_names)
        elif file_subtype == 'IndicatorsList':
            for row in range(1,xl_sheet.nrows):
                name = str(xl_sheet.cell_value(row, 0)).strip()
                fullname = str(xl_sheet.cell_value(row, 1)).strip()
                description = str(xl_sheet.cell_value(row, 2)).strip()
                flow = xl_sheet.cell_value(row, 3)
                basic = xl_sheet.cell_value(row, 4)
                indicator = Indicator(name=name,fullname=fullname,description=description,flow=flow,basic=basic)            
                db.session.add(indicator)
        db.session.commit()
        processed_ok = True

    elif file_type == 'Data':
        companies_dict, indicators_dict, insclasses_dict = get_dictionaries_file_check_and_processing()
        if file_subtype in ('Premiums','Claims'):#загружаем данные - премии или выплаты по классам и страховым
            insclasses_list, cl_dict, classes_not_found = create_insclasses_list(frst_row,xl_sheet,insclasses_dict,others_col_1,others_col_2,others_col_3)
            for row in range(frst_row-1,xl_sheet.nrows):
                name = str(xl_sheet.cell_value(row, 1)).strip()
                try:
                    company_id = companies_dict[name] #определим id компании                    
                except:                    
                    continue
                for i in range(2,xl_sheet.ncols):
                    try:
                        insclass_id = cl_dict[str(i)]#определим id показателя                        
                    except:                        
                        continue
                    try:                        
                        value = float(xl_sheet.cell_value(row, i))
                    except:
                        value = 0.0                                        
                    if file_subtype == 'Premiums':
                        premium = Premium(report_date=report_date,company_id=company_id,insclass_id=insclass_id,value=value)
                        db.session.add(premium)
                    elif file_subtype == 'Claims':
                        claim = Claim(report_date=report_date,company_id=company_id,insclass_id=insclass_id,value=value)
                        db.session.add(claim)
            db.session.commit()

        elif file_subtype in ('Financials','Prudentials'):#загружаем данные - основные фин. показатели по страховым
            ind_dict, indicators_not_found = create_indicators_list(file_subtype,frst_row,xl_sheet,indicators_dict)
            for row in range(frst_row-1,xl_sheet.nrows):
                name = str(xl_sheet.cell_value(row, 1)).strip() #текстовое наименование компании            
                try:
                    company_id = companies_dict[name] #определим id компании
                except:
                    continue
                for i in range(2,xl_sheet.ncols):
                    try:
                        indicator_id = ind_dict[str(i)]#определим id показателя
                    except:
                        continue
                    try:
                        value = float(xl_sheet.cell_value(row, i))                        
                    except:
                        value = 0.0                        
                    financial = Financial(report_date=report_date,company_id=company_id,indicator_id=indicator_id,value=value)
                    db.session.add(financial)
            db.session.commit()
        processed_ok = True
    return processed_ok


def delete_file_from_server(filename,param):#удалить файл; param=upload из папки UPLOAD_FOLDER, param=upload_temporary из папки TMP_UPLOAD_FOLDER
    res = False
    msg = 'Не удалось удалить файл ' + str(filename)
    if param == 'upload':
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            res = True
        except:
            pass
    elif param == 'upload_temporary':
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], current_app.config['TMP_UPLOAD_FOLDER'], filename))
            res = True
        except:
            pass        
    return res, msg    


def check_process_file_res(file_subtype,report_date):#проверка результатов загрузки и отработки файла
    print('start check_process_file_res')
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
    count = 0
    while True:
        count += 1
        r = random.choice(rows)
        if r.value > 0:
            found += 1
            rand_rows.append(r)
        if found > 2 or count > 1000:#выведем три случайные записи больше 0, либо после 1000 попыток
            break
    return N_rows, rand_rows


def get_dictionaries_file_check_and_processing():#вспомогательная функция, наполним словари с компаниями, классами, показателями для обработки файлов
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
    return companies_dict, indicators_dict, insclasses_dict


def add_special_to_other_classes(cl_fullname,colnum,others_col_1,others_col_2,others_col_3):#добавляем для классов "иные", чтобы однозначно их опознать
    if cl_fullname == 'иные классы (виды) страхования':#особая логика
        if colnum == others_col_1-1:
            cl_fullname = cl_fullname + '_' + 'other_voluntary_personal'
        elif colnum == others_col_2-1:
            cl_fullname = cl_fullname + '_' + 'other_voluntary_property'
        elif colnum == others_col_3-1:
            cl_fullname = cl_fullname + '_' + 'other_obligatory'
    return cl_fullname


def create_insclasses_list(frst_row,xl_sheet,insclasses_dict,others_col_1,others_col_2,others_col_3):#список классов исходя из первой строки файла
    insclasses_list = list()
    classes_not_found = list()
    for i in range(2,xl_sheet.ncols):
        el = xl_sheet.cell_value(frst_row-3, i)
        try:
            cl = el.strip()
        except:
            cl = el
        insclasses_list.append(cl)
    cl_dict = dict()#словарь: ключ - номер колонки, значение - id класса
    colnum = 2
    for cl_fullname in insclasses_list:#пройдемся по строке с названиями показателей
        cl_fullname = add_special_to_other_classes(cl_fullname,colnum,others_col_1,others_col_2,others_col_3)
        try:
            cl_id = insclasses_dict[cl_fullname]
            cl_dict[str(colnum)] = cl_id
        except:
            classes_not_found.append({'class':cl_fullname,'column_number':str(colnum+1)})
        colnum += 1
    return insclasses_list, cl_dict, classes_not_found


def create_indicators_list(file_subtype,frst_row,xl_sheet,indicators_dict):#список классов исходя из первой строки файла
    indicators_list = list()
    indicators_not_found = list()
    ind_dict = dict()#словарь: ключ - номер колонки, значение - id показателя
    if file_subtype == 'Financials':
        indicators_row_num = frst_row-3#названия показателей хранятся в 5-й строке файла (осн. фин. показатели)
    elif file_subtype == 'Prudentials':
        indicators_row_num = frst_row-5#названия показателей хранятся в 8-й строке файла (прудики)    
    for i in range(2,xl_sheet.ncols):
        el = xl_sheet.cell_value(indicators_row_num, i)
        try:
            cl = el.strip()
        except:
            cl = el
        indicators_list.append(cl)
    colnum = 2
    for ind_fullname in indicators_list:#пройдемся по строке с названиями показателей
        try:
            ind_id = indicators_dict[ind_fullname]
            ind_dict[str(colnum)] = ind_id
        except:
            indicators_not_found.append({'indicator':ind_fullname,'column_number':str(colnum+1)})
        colnum += 1
    return ind_dict, indicators_not_found


def get_companies_values_from_sheet(companies_dict, xl_sheet, frst_row):#какие компании и классы не удалось прочитать
    values_not_converted = list()
    companies_not_found = list()
    for row in range(frst_row-1,xl_sheet.nrows):#по каждой строке
        name = str(xl_sheet.cell_value(row, 1))#текстовое наименование компании
        try:
            company_id = companies_dict[name]#определим id компании            
        except:
            companies_not_found.append({'company_name':name,'row_number':str(row+1)})
        for i in range(2,xl_sheet.ncols):#по каждому классу читаем значение            
            value_str = xl_sheet.cell_value(row, i)
            if value_str != '':#cell not empty
                try:
                    value = float(value_str)
                except:
                    values_not_converted.append({'company_name':name,'row_number':str(row+1),'column_number':str(i+1),'value':str(value_str)})                
    return values_not_converted, companies_not_found


def check_file_content(file_subtype,wb,report_date,frst_row,others_col_1,others_col_2,others_col_3):#check content of data file
    values_not_converted = None
    companies_not_found = None
    classes_not_found = None
    indicators_not_found = None    
    xl_sheet = wb.sheet_by_index(0)
    companies_dict, indicators_dict, insclasses_dict = get_dictionaries_file_check_and_processing()
    values_not_converted, companies_not_found = get_companies_values_from_sheet(companies_dict, xl_sheet, frst_row)
    if file_subtype in ('Premiums','Claims'):#загружаем данные - премии или выплаты по классам и страховым
        insclasses_list, cl_dict, classes_not_found = create_insclasses_list(frst_row,xl_sheet,insclasses_dict,others_col_1,others_col_2,others_col_3)        
    elif file_subtype in ('Financials','Prudentials'):#загружаем данные - основные фин. показатели по страховым
        ind_dict, indicators_not_found = create_indicators_list(file_subtype,frst_row,xl_sheet,indicators_dict)
    return values_not_converted, companies_not_found, classes_not_found, indicators_not_found


def check_file_name_ext(request,file_data,future_action):
    res = False
    msg = 'Файл не выбран'
    filename = None
    if 'file' not in request.files:# check if the post request has the file part        
        return res, msg, filename
    _file = request.files['file']
    if _file.filename == '':# if user does not select file, browser also submit an empty part without filename
        return res, msg, filename
    if _file and allowed_file(_file.filename):
        filename = secure_filename(file_data.filename)
        filename = add_str_timestamp(filename) #adds string timestamp to filename in order to make in unique
        try:
            if future_action == 'check':
                file_data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], current_app.config['TMP_UPLOAD_FOLDER'], filename))
            elif future_action == 'upload':
                file_data.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            res = True
        except:
            msg = 'Не получилось сохранить файл'
    return res, msg, filename


def open_xls_file(filename,future_action):#пытаемся открыть файл, проверяем кол-во листов
    res = False
    msg = None
    wb = None    
    try:
        if future_action == 'check':
            wb = open_workbook(os.path.join(current_app.config['UPLOAD_FOLDER'], current_app.config['TMP_UPLOAD_FOLDER'], filename))
        elif future_action == 'upload':
            wb = open_workbook(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        num_sheets = len(wb.sheet_names())
        if num_sheets == 1:
            res = True
        else:
            msg = 'В выбранном файле более одного листа. Удалите лишние листы во избежание ошибок. Файл должен содержать только один лист.'
            res_del, msg_del = delete_file_from_server(filename,'upload_temporary') #param= upload / upload_temporary
            if not res_del:
                msg = msg + msg_del
    except:
        msg = 'Не могу открыть excel файл, неизвестный формат'
    return res, msg, wb


@bp.route('/check_file_before_upload/<upload_type>',methods=['GET', 'POST'])#проверить файл перед загрузкой
@login_required
@required_roles('admin')
def check_file_before_upload(upload_type):
    title = 'Проверка файла перед загрузкой'
    h1_txt = 'Проверка файлов перед загрузкой'
    if upload_type == 'dictionary':
        form = DictUploadForm()
        descr = 'Проверка файла со справочниками'
    elif upload_type == 'data':
        form = DataUploadForm()
        descr = 'Проверка файла с данными перед загрузкой в систему'    
    values_not_converted = None
    companies_not_found = None
    classes_not_found = None
    indicators_not_found = None
    show_form = True
    if form.validate_on_submit():
        show_form = False
        res, msg, filename = check_file_name_ext(request,form.file.data,'check')
        if not res:#имя файла или расширение некорректные
            flash(msg)
            return redirect(request.url)
        else:#всё ОК, файл сохранен, можно открывать и обрабатывать
            res, msg, wb = open_xls_file(filename,'check')
            if not res:#не удалось открыть файл, либо там более одного листа
                flash(msg)
                return redirect(request.url)
            else:#всё ОК, получили файл в объекте wb
                frst_row = int(form.frst_row.data)#первая строка с данными по компаниям
                try:
                    others_col_1 = int(form.others_col_1.data)#столбец с иными классами, ДЛС
                    others_col_2 = int(form.others_col_2.data)#столбец с иными классами, ДИС
                    others_col_3 = int(form.others_col_3.data)#столбец с иными классами, ОС
                except:
                    pass
                values_not_converted, companies_not_found, classes_not_found, indicators_not_found = check_file_content(form.data_type.data,wb,form.report_date.data,frst_row,others_col_1,others_col_2,others_col_3)
                res_del, msg_del = delete_file_from_server(filename,'upload_temporary') #param= upload / upload_temporary
                if not res_del:
                    flash(msg_del)
    return render_template('admin/check_file.html',title=title, \
                        form=form,descr=descr,h1_txt=h1_txt, show_form=show_form, \
                        values_not_converted=values_not_converted, \
                        companies_not_found=companies_not_found,classes_not_found=classes_not_found, \
                        indicators_not_found=indicators_not_found)


@bp.route('/upload_file/<upload_type>',methods=['GET', 'POST'])#загрузить файл
@login_required
@required_roles('admin')
def upload_file(upload_type):
    title = 'Загрузка файла'
    h1_txt = 'Загрузка файла'
    if upload_type == 'dictionary':
        form = DictUploadForm()
        descr = 'Здесь из excel файлов загружаются справочники'
    elif upload_type == 'data':
        form = DataUploadForm()
        descr = 'Здесь из excel файлов (источник - НБ РК, https://nationalbank.kz/?docid=1075&switch=russian) загружаются финансовые данные. Каждая книга должна содержать только один лист'
    if form.validate_on_submit():
        res, msg, filename = check_file_name_ext(request,form.file.data,'upload')
        if not res:#имя файла или расширение некорректные
            flash(msg)
            return redirect(request.url)
        else:#всё ОК, файл сохранен, можно открывать и обрабатывать
            res, msg, wb = open_xls_file(filename,'upload')
            if not res:#не удалось открыть файл, либо там более одного листа
                flash(msg)
                res_del, msg_del = delete_file_from_server(filename,'upload') #param= upload / upload_temporary
                if not res_del:
                    flash(msg_del)
                return redirect(request.url)
            else:#всё ОК, получили файл в объекте wb
                #save to DB info about file uploaded
                name = add_str_timestamp(form.name.data)
                if upload_type == 'dictionary':
                    upload = Upload(name=name,file_type='Dictionary',dict_type=form.dict_type.data,file_name=filename)
                elif upload_type == 'data':
                    already_uploaded = Upload.query.filter(Upload.file_type=='Data').filter(Upload.data_type == form.data_type.data).filter(Upload.report_date == form.report_date.data).first()
                    if already_uploaded is None:
                        upload = Upload(name=name,file_type='Data',data_type=form.data_type.data,file_name=filename,report_date=form.report_date.data)
                    else:
                        res_del, msg_del = delete_file_from_server(filename,'upload') #param= upload / upload_temporary
                        if not res_del:
                            flash(msg_del)                       
                        flash('Данный файл уже был загружен. Повторная загрузка не требуется.')
                        return redirect(request.url)
                db.session.add(upload)
                db.session.commit()
                flash('Файл сохранен на сервер и загружен!')
                if upload_type == 'dictionary':                    
                    process_res = process_file('Dictionary',form.dict_type.data,wb,datetime.utcnow(),1,1,1,1)
                else:
                    frst_row = int(form.frst_row.data)#первая строка с данными по компаниям
                    try:
                        others_col_1 = int(form.others_col_1.data)#столбец с иными классами, ДЛС
                        others_col_2 = int(form.others_col_2.data)#столбец с иными классами, ДИС
                        others_col_3 = int(form.others_col_3.data)#столбец с иными классами, ОС
                    except:
                        pass
                    process_res = process_file('Data',form.data_type.data,wb,form.report_date.data,frst_row,others_col_1,others_col_2,others_col_3)                 
                if not process_res:
                    flash('При обработке файла возникли ошибки!')
                    res_del, msg_del = delete_file_from_server(filename,'upload') #param= upload / upload_temporary
                    if not res_del:
                        flash(msg_del)
                    db.session.delete(upload)
                    db.session.commit()
                    return redirect(request.url)
                else:
                    if upload_type == 'dictionary':
                        flash('Файл успешно обработан!')
                    else:
                        try:
                            N_rows, rand_rows = check_process_file_res(form.data_type.data,form.report_date.data)
                            flash('Файл загружен и обработан. Проверьте результаты загруки и произведите перерасчёт!')
                            flash('Результаты загрузки: создано записей ' + str(N_rows) + '. Проверьте случайные записи из числа созданных:')
                            for r in rand_rows:
                                flash('---' + str(r))
                        except:
                            flash('Не получилось проверить результат обработки файла! Возможно, данные не были загружены в БД. Проверьте входной файл и корректность заполнения номера первой строки с данными.')
                            res_del, msg_del = delete_file_from_server(filename,'upload') #param= upload / upload_temporary
                            if not res_del:
                                flash(msg_del)
                            db.session.delete(upload)
                            db.session.commit()
                            return redirect(request.url)
    return render_template('admin/add_edit_DB_item.html',title=title, \
                        form=form,descr=descr,h1_txt=h1_txt)


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
    title='Перерасчет показателей'
    h1_txt = 'Перерасчет показателей за период'
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
    return render_template('admin/add_edit_DB_item.html',title=title,
                h1_txt=h1_txt,form=form,descr=descr)


@bp.route('/add_new_company',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def add_new_company():
    form = AddEditCompanyForm()
    h1_txt = 'Добавить компанию'
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
    return render_template('admin/add_edit_DB_item.html', form=form, h1_txt=h1_txt)


@bp.route('/edit_company/<company_id>',methods=['GET', 'POST'])#изменить имя компании (переименование)
@login_required
@required_roles('admin')
def edit_company(company_id=None):
    form = AddEditCompanyForm()
    h1_txt = 'Изменить компанию'
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
    return render_template('admin/add_edit_DB_item.html',form=form, h1_txt=h1_txt)


@bp.route('/add_new_class',methods=['GET', 'POST'])#добавить новое имя класса (переименование)
@login_required
@required_roles('admin')
def add_new_class():
    form = AddEditClassForm()
    h1_txt = 'Добавить класс'
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
    return render_template('admin/add_edit_DB_item.html', form=form, h1_txt=h1_txt)


@bp.route('/edit_class/<class_id>',methods=['GET', 'POST'])#изменить имя класса (переименование)
@login_required
@required_roles('admin')
def edit_class(class_id=None):
    form = AddEditClassForm()
    h1_txt = 'Изменить класс'
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
    return render_template('admin/add_edit_DB_item.html',form=form, h1_txt=h1_txt)


@bp.route('/send_email_to_users',methods=['GET', 'POST'])#отправить мейл пользователям
@login_required
@required_roles('admin')
def send_email_to_users():
    form = SendEmailToUsersForm()
    h1_txt = 'Отправка email сообщения пользователям'
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
    return render_template('admin/add_edit_DB_item.html', form=form, descr=descr, \
                h1_txt=h1_txt)


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
    log_events = None
    events_by_user = None
    events_by_page = None
    events_by_day = None
    show_info = False    
    stat_min_date = View_log.query \
            .with_entities(func.min(View_log.timestamp).label("min_time")).first()
    min_date = stat_min_date[0]
    if form.validate_on_submit():
        b = form.begin_d.data
        e = form.end_d.data + timedelta(days=1)        
        log_events, events_by_user, events_by_page, events_by_day = get_data_for_usage_log(b,e)
        show_info = True
    return render_template('admin/usage_log.html',title='Лог использования портала', \
        get_view_name=get_view_name,log_events=log_events, min_date=min_date, \
        events_by_user=events_by_user,events_by_page=events_by_page,form=form, \
        events_by_day=events_by_day,show_info=show_info)


@bp.route('/add_new_hint',methods=['GET', 'POST'])#добавить новое имя компании (переименование)
@login_required
@required_roles('admin')
def add_new_hint():
    form = HintForm()
    title = 'Добавление подсказки'
    h1_txt = 'Добавить новую подсказу'
    if form.validate_on_submit():        
        hint = Hint(name=form.name.data,text=form.text.data,title=form.title.data)
        db.session.add(hint)
        db.session.commit()
        flash('Подсказка добавлена')
        return redirect(url_for('admin.hints'))
    return render_template('admin/add_edit_DB_item.html',form=form,h1_txt=h1_txt,title=title)


@bp.route('/edit_hint/<hint_id>',methods=['GET', 'POST'])#редактировать подсказку
@login_required
@required_roles('admin')
def edit_hint(hint_id=None):
    form = HintForm()
    h1_txt = 'Изменить подсказку'
    obj = Hint.query.filter(Hint.id == hint_id).first()
    if request.method == 'GET':        
        form = HintForm(obj=obj)
    if form.validate_on_submit():
        obj.name = form.name.data
        obj.text = form.text.data
        obj.title = form.title.data
        db.session.commit()
        flash('Успешно изменено!')
        return redirect(url_for('admin.hints'))
    return render_template('admin/add_edit_DB_item.html',form=form,h1_txt=h1_txt)


@bp.route('/hints')#список подсказок
@login_required
@required_roles('admin')
def hints():
    title = 'Список подсказок'
    hints = Hint.query.all()
    return render_template('admin/hints.html',title=title,hints=hints)

