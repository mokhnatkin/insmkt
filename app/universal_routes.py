from flask import flash, redirect, url_for, g, current_app
from app import db
from flask_login import current_user
from app.models import Company, Indicator, Financial, \
            Premium, Financial_per_month, View_log, Hint, \
            Premium_per_month, Claim_per_month
from datetime import datetime
from flask_babel import get_locale
from functools import wraps
import random
from exchangelib import Account, Credentials, Configuration, DELEGATE, Message
from threading import Thread
import xlwt
from werkzeug.utils import secure_filename
import os


def before_request_u():
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
def required_roles_u(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if get_current_user_role() not in roles:
                flash('У вашей роли недостаточно полномочий','error')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return wrapped
    return wrapper
 

def get_current_user_role():#возвращает роль текущего пользователя
    return current_user.role


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


def send_async_email(app,msg):#асинхронная отправка email
    with app.app_context():
        msg.send()


def send_email(subject,body,recipients):#функция отправки email с заданной темой, телом
    credentials = Credentials(username=current_app.config['EXCHANGE_USERNAME'],password=current_app.config['EXCHANGE_PASSWORD'])
    config = Configuration(server=current_app.config['EXCHANGE_SERVER'],credentials=credentials)
    account = Account(primary_smtp_address=current_app.config['EXCHANGE_PRIMARY_SMTP_ADDRESS'],config=config,autodiscover=False,access_type=DELEGATE)
    msg = Message(account=account,subject=subject,body=body,to_recipients=recipients)
    Thread(target=send_async_email,args=(current_app._get_current_object(),msg)).start()
    

#список функций для логирования
views_for_logging = current_app.config['VIEWS_FOR_LOGGING']


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


def get_hint(name):#получаем текст и url подсказки по её имени
    hint = Hint.query.filter(Hint.name == name).first()
    return hint


def allowed_file(filename):#проверка файла - расширение должно быть разрешено
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']        


def add_str_timestamp(filename):#adds string timestamp to filename in order to make in unique
    dt = datetime.utcnow()
    stamp = round(dt.timestamp())
    uId = str(stamp)
    rand_n = str(random.randrange(100, 1000, 1))#add random number
    u_filename = uId+'_'+rand_n+'_'+filename
    return u_filename


def save_to_excel(item_name,period_str,wb_name,sheets,sheets_names):#save to excel
    #list of system col. names and their meanings
    column_names_ver = dict()
    column_names_ver['id'] = 'Системный ID'
    column_names_ver['ind_id'] = 'Системный ID'
    column_names_ver['name'] = 'Наименование'
    column_names_ver['fullname'] = 'Полное наименование'
    column_names_ver['mkt_av'] = 'Среднее по рынку (выбранным конкурентам)'
    column_names_ver['total'] = 'Всего'
    column_names_ver['share'] = 'Доля %'
    column_names_ver['value'] = 'Значение'
    column_names_ver['value_c'] = 'Значение по компании'
    column_names_ver['value_m'] = 'Значение по рынку (выбранным конкурентам)'
    column_names_ver['premium'] = 'Премии'
    column_names_ver['claim'] = 'Выплаты'
    column_names_ver['LR'] = 'Коэффициент выплат %'
    column_names_ver['av_premium_mkt'] = 'Сред. премии рынок (выбранные конкуренты)'
    column_names_ver['av_claim_mkt'] = 'Сред. выплаты рынок (выбранные конкуренты)'
    column_names_ver['av_LR_mkt'] = 'Сред. коэф. убыточности рынок (выбранные конкуренты)'
    column_names_ver['peers_balance_ind'] = ''
    column_names_ver['peers_flow_ind'] = ''
    column_names_ver['peers_other_fin_ind'] = ''
    column_names_ver['lr'] = 'Коэффициент выплат %'
    column_names_ver['month_name'] = 'Год-Месяц'
    column_names_ver['alias'] = 'Компания'
    column_names_ver['premiums'] = 'Премии'
    column_names_ver['net_premiums'] = 'Чистые премии'
    column_names_ver['claims'] = 'Выплаты'
    column_names_ver['net_claims'] = 'Чистые выплаты'
    column_names_ver['net_LR'] = 'Чистый коэф. выплат'
    column_names_ver['re_share'] = 'Доля перестрахования в премиях %'
    column_names_ver['motor_TPL_premiums'] = 'Премии ОС ГПО ВТС'
    column_names_ver['motor_TPL_claims'] = 'Выплаты ОС ГПО ВТС'
    column_names_ver['casco_premiums'] = 'Премии каско'
    column_names_ver['casco_claims'] = 'Выплаты каско'
    column_names_ver['motor_TPL_prem_share'] = 'Доля ОС ГПО ВТС в валовых премиях %'
    column_names_ver['casco_prem_share'] = 'Доля каско в валовых премиях %'
    column_names_ver['motor_premiums'] = 'Премии по автострахованию'
    column_names_ver['motor_claims'] = 'Выплаты по автострахованию'
    column_names_ver['motor_TPL_prem_share_in_motor'] = 'Доля ОС ГПО ВТС в премиях по автострахованию'
    column_names_ver['casco_prem_share_in_motor'] = 'Доля каско в премиях по автострахованию'
    column_names_ver['row_index'] = 'N'
    column_names_ver['value_l_y'] = 'Значение за аналогичный период прошлого года'
    column_names_ver['share_l_y'] = 'Доля за аналогичный период прошлого года %'
    column_names_ver['change'] = 'Изменение %'
    column_names_ver['prem_share'] = 'Доля по премиям %'
    column_names_ver['claim_share'] = 'Доля по выплатам %'
    column_names_ver['premium_l_y'] = 'Премии за прошлый период'
    column_names_ver['claim_l_y'] = 'Выплаты за прошлый период'
    column_names_ver['prem_share_l_y'] = 'Доля по премиям за прошлый период %'
    column_names_ver['claim_share_l_y'] = 'Доля по выплатам за прошлый период %'
    column_names_ver['lr_l_y'] = 'Коэффициент выплат за прошлый период %'
    column_names_ver['prem_change'] = 'Изменение премий по сравнению с прошлым периодом %'
    column_names_ver['claim_change'] = 'Изменение выплат по сравнению с прошлым периодом %'
    column_names_ver['lr_change'] = 'Изменение коэффициента выплат по сравнению с прошлым периодом %'
    column_names_ver['peer_name'] = 'Конкурент'
    column_names_ver['class_name'] = 'Класс страхования'
    column_names_ver['peer_premium'] = 'Премии, собранные конкурентом'
    column_names_ver['peer_claim'] = 'Выплаты, произведенные конкурентом'
    column_names_ver['peer_LR'] = 'Коэффициент выплат %'
    column_names_ver['gross_LR'] = 'Валовый коэффициент выплат %'
    column_names_ver['motor_TPL_LR'] = 'Коэффициент выплат по ОС ГПО ВТС %'
    column_names_ver['casco_LR'] = 'Коэффициент выплат по каско %'
    column_names_ver['motor_LR'] = 'Коэффициент выплат по автострахованию %'
    column_names_ver['system_name'] = 'Наименование'
    column_names_ver['total_l_y'] = 'Всего по рынку за прошлый период'
    column_names_ver['mkt_av_l_y'] = 'Среднее по рынку за прошлый период'
    column_names_ver['value_delta'] = 'Изменение по компании %'
    column_names_ver['value_delta_abs'] = 'Изменение по компании в абсолюте'
    column_names_ver['total_delta'] = 'Изменение по рынку %'
    column_names_ver['total_delta_abs'] = 'Изменение по рынку в абсолюте'
    column_names_ver['value_c_l_y'] = 'Значение по компании за прошлый период'
    column_names_ver['value_m_l_y'] = 'Значение по рынку за прошлый период'
    column_names_ver['delta_c'] = 'Изменение по компании'
    column_names_ver['delta_m'] = 'Изменение по рынку'
    column_names_ver['claims_share'] = 'Доля по выплатам'
    column_names_ver['premiums_share'] = 'Доля по премиям'
    column_names_ver['claims_l_y'] = 'Выплаты за прошлый период'
    column_names_ver['claims_share_l_y'] = 'Доля по выплатам за прошлый период'
    column_names_ver['premiums_l_y'] = 'Премии за прошлый период'
    column_names_ver['premiums_share_l_y'] = 'Доля по премиям за прошлый период'
    column_names_ver['claims_delta'] = 'Изменение по выплатам %'
    column_names_ver['premiums_delta'] = 'Изменение по премиям %'
    column_names_ver['lr_delta'] = 'Изменение коэффициента выплат %'


    #############################################################################
    workbook = xlwt.Workbook()
    i = 0
    path = None
    #descriptive sheet
    sh = workbook.add_sheet('total')
    sh.write(0,0,item_name)
    sh.write(1,0,period_str)
    for sheet in sheets:
        sh = workbook.add_sheet(sheets_names[i])
        rows = len(sheet)
        for row in range(rows):
            row_array = sheet[row]            
            col = 0
            for k, v in row_array.items():
                try:                   
                    if row == 0:                        
                        if k in column_names_ver:
                            sh.write(row, col, column_names_ver[k])
                        else:
                            sh.write(row, col, k)
                        sh.write(row+1, col, v)
                    else:
                        sh.write(row+1, col, v)
                except:
                    continue
                col+=1
        i+=1
    #save wb
    wb_name = secure_filename(wb_name)
    wb_name = add_str_timestamp(wb_name) + '.xls'    
    try:        
        workbook.save(os.path.join(current_app.config['TMP_STATIC_FOLDER'], wb_name))
        path = os.path.join(os.path.dirname(os.path.abspath(current_app.config['TMP_STATIC_FOLDER'])),current_app.config['TMP_STATIC_FOLDER'])        
    except:
        pass
    return path, wb_name#returns path to saved file and its name


def transform_check_dates(b,e,show_last_year):#get dates from input form and transform
    check_res = True
    err_txt = None
    b = datetime(b.year,b.month,1)#первое число
    e = datetime(e.year,e.month,1)
    period_str = b.strftime('%Y-%m') + '_' + e.strftime('%Y-%m')
    period_str_full = 'с '+ b.strftime('%d.%m.%Y') + ' по '+ e.strftime('%d.%m.%Y')
    base_err_txt = 'Вы запросили аналитику за период ' + period_str_full + '. Выгрузка невозможна, т.к. '
    if e <= b:
        check_res = False
        err_txt = base_err_txt + 'дата окончания должна быть больше даты начала'
    #аналогичный период прошлого года
    b_l_y = datetime(b.year-1,b.month,1)
    e_l_y = datetime(e.year-1,e.month,1)
    if b < g.min_report_date or e > g.last_report_date :
        check_res = False
        err_txt = base_err_txt + 'данные за запрошенный период отсутствуют. Выберите любой период в диапазоне с ' \
                + g.min_report_date.strftime('%d.%m.%Y') + ' по ' \
                    + g.last_report_date.strftime('%d.%m.%Y')
    if show_last_year:
        if b_l_y < g.min_report_date or e_l_y > g.last_report_date :
            check_res = False
            err_txt = base_err_txt + 'данные за прошлый период отсутствуют в системе. Укажите другой период, либо снимите галочку Показать данные по сравнению с аналогичным периодом прошлого года'
    return b,e,b_l_y,e_l_y,period_str,check_res,err_txt


def str_to_date(date_str):#вспомогат. ф-ция
    return datetime.strptime(date_str, '%m-%d-%Y')


def str_to_bool(bool_str):#вспомогат. ф-ция
    if bool_str == 'True':
        res = True
    else:
        res = False
    return res
