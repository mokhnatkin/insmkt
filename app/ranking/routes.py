from flask import render_template, flash, redirect, url_for, request, g
from app import db
from app.ranking.forms import RankingForm
from flask_login import current_user, login_required
from app.models import Company, Indicator, Financial, Financial_per_month            
from datetime import datetime
from app.ranking import bp
from app.universal_routes import before_request_u, required_roles_u, save_to_log, \
                            get_months, is_id_in_arr


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


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


@bp.route('/ranking',methods=['GET','POST'])#ранкинг, обзор рынка
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
                return redirect(url_for('ranking.ranking'))        
        net_premiums_len = len(net_premiums)
        equity_len = len(equity)
        netincome_len = len(netincome)
        solvency_margin_len = len(solvency_margin)
        lr_list_len = len(lr_list)
    return render_template('ranking/ranking.html', \
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
