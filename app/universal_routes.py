from flask import flash, redirect, url_for, g
from app import db
from flask_login import current_user
from app.models import Company, Indicator, Financial, \
            Premium, Financial_per_month, View_log
from datetime import datetime
from flask_babel import get_locale
from functools import wraps
import random
from exchangelib import Account, Credentials, Configuration, DELEGATE, Message
from threading import Thread



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
    credentials = Credentials(username=app.config['EXCHANGE_USERNAME'],password=app.config['EXCHANGE_PASSWORD'])
    config = Configuration(server=app.config['EXCHANGE_SERVER'],credentials=credentials)
    account = Account(primary_smtp_address=app.config['EXCHANGE_PRIMARY_SMTP_ADDRESS'],config=config,autodiscover=False,access_type=DELEGATE)
    msg = Message(account=account,subject=subject,body=body,to_recipients=recipients)
    Thread(target=send_async_email,args=(app,msg)).start()
    #msg.send()



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