from flask import render_template, flash, redirect, url_for, request, g, Response
from app import db
from app.company_peers_profile.forms import CompanyProfileForm, PeersForm
from flask_login import current_user, login_required
from app.models import Company, Insclass, Indicator, Financial, \
            Financial_per_month, Premium_per_month, Claim_per_month            
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import numpy as np
from app.company_peers_profile import bp
from app.universal_routes import before_request_u, required_roles_u, \
                    save_to_log, get_num_companies_at_date, get_months, is_id_in_arr, \
                    get_num_companies_per_period, get_hint


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


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

    #now compute mkt average for premiums
    premiums_per_month_per_c = list()
    claims_per_month_per_c = list()
    for company in peers:
        for month in months:
            begin = month['begin']
            end = month['end']
            prem_m = Premium_per_month.query \
                        .with_entities(Premium_per_month.value,Premium_per_month.insclass_id) \
                        .filter(Premium_per_month.company_id == company[0]) \
                        .filter(Premium_per_month.beg_date == begin) \
                        .filter(Premium_per_month.end_date == end).all()
            for i in prem_m:
                premiums_per_month_per_c.append({'peer_id':company[0], 'insclass_id':i.insclass_id,'premium':i.value})
            claim_m = Claim_per_month.query \
                        .with_entities(Claim_per_month.value,Claim_per_month.insclass_id) \
                        .filter(Claim_per_month.company_id == company[0]) \
                        .filter(Claim_per_month.beg_date == begin) \
                        .filter(Claim_per_month.end_date == end).all()
            for i in claim_m:
                claims_per_month_per_c.append({'peer_id':company[0], 'insclass_id':i.insclass_id,'claim':i.value})    
    c_N = get_num_companies_per_period(begin_d,end_d,N_companies)
    for cl in premiums:
        total_prem = 0.0
        total_claim = 0.0
        for p in premiums_per_month_per_c:
            if cl['id'] == p['insclass_id']:
                total_prem += p['premium']
        for c in claims_per_month_per_c:
            if cl['id'] == c['insclass_id']:
                total_claim += c['claim']
        if total_prem>0.0:
            LR = round(total_claim / total_prem * 100,2)
        else:
            LR = 'N.A.'
        cl['av_premium_mkt'] = total_prem / c_N
        cl['av_claim_mkt'] = total_claim / c_N
        cl['av_LR_mkt'] = LR

        if show_competitors:
            peers_prem_claim_LR = list()
            for company in peers:
                total_prem = 0.0
                total_claim = 0.0
                for p in premiums_per_month_per_c:
                    if cl['id'] == p['insclass_id'] and p['peer_id'] == company[0]:
                        total_prem += p['premium']
                for c in claims_per_month_per_c:
                    if cl['id'] == c['insclass_id'] and c['peer_id'] == company[0]:
                        total_claim += c['claim']
                if total_prem>0.0:
                    LR = round(total_claim / total_prem * 100,2)
                else:
                    LR = 'N.A.'
                peers_prem_claim_LR.append({'peer_id':company[0],'peer_premium':total_prem,'peer_claim':total_claim,'peer_LR':LR})
            cl['peers_prem_claim_LR'] = peers_prem_claim_LR
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
    name = 'ROE годовой, %'
    ind_id = 'roe'
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
    other_financial_indicators.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_roe})
    name = 'Использование капитала'
    ind_id = 'equity_usage'
    value_c = round(net_premiums_c / equity_c / N * 12, 2)
    value_m = round(net_premiums_m / equity_m / N * 12, 2)
    for i in range (0,Npeers):
        value_p = round(peer_net_premiums[i] / peer_equity[i] / N * 12, 2)
        peers_eq_us.append({'peer_value':value_p})
    other_financial_indicators.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_eq_us})
    name = 'Коэффициент выплат, нетто %'
    ind_id = 'LR_coef_net'
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
    other_financial_indicators.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_lr})
    name = 'Доля перестрахования в премиях, %'
    ind_id = 'RE_prem'
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
    other_financial_indicators.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_re_p})
    name = 'Доля перестрахования в выплатах, %'
    ind_id = 'RE_claim'
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
    other_financial_indicators.append({'ind_id': ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers_other_fin_ind':peers_re_c})
    return other_financial_indicators


@bp.route('/company_profile',methods=['GET','POST'])
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
            return redirect(url_for('company_peers_profile.company_profile'))
        try:
            company_name, balance_indicators, flow_indicators, premiums, peers_names_arr = show_company_profile(int(form.company.data),peers,b,e,None,False)
            other_financial_indicators = get_other_financial_indicators(balance_indicators,flow_indicators,b,e)
            if show_last_year == True:
                try:
                    company_name_l_y, balance_indicators_l_y, flow_indicators_l_y, premiums_l_y, peers_names_arr_l_y = show_company_profile(int(form.company.data),peers,b_l_y,e_l_y,None,False)
                    other_financial_indicators_l_y = get_other_financial_indicators(balance_indicators_l_y,flow_indicators_l_y,b_l_y,e_l_y)
                except:
                    flash('Не могу получить данные за прошлый год')
                    return redirect(url_for('company_peers_profile.company_profile'))
        except:
            flash('Не удается получить данные. Возможно, выбранная компания не существовала в заданный период. Попробуйте выбрать другой период.')
            return redirect(url_for('company_peers_profile.company_profile'))
        show_charts = True
        if len(other_financial_indicators) > 0:
            show_other_financial_indicators = True        
        if len(balance_indicators) > 0:
            show_balance = True
        if len(flow_indicators) > 0:
            show_income_statement = True
        if len(premiums) > 0:
            show_premiums = True
    return render_template('company_peers_profile/company_profile.html',title='Портрет компании',form=form,descr=descr,company_name=company_name, \
                balance_indicators=balance_indicators, flow_indicators=flow_indicators, \
                show_charts=show_charts,img_path_premiums_by_LoB_pie=img_path_premiums_by_LoB_pie, \
                img_path_lr_by_LoB=img_path_lr_by_LoB,img_path_solvency_margin=img_path_solvency_margin, \
                img_path_net_premium=img_path_net_premium,b=b,e=e,show_other_financial_indicators=show_other_financial_indicators, \
                show_balance=show_balance,show_income_statement=show_income_statement, \
                img_path_equity=img_path_equity,other_financial_indicators=other_financial_indicators, \
                img_path_reserves=img_path_reserves,premiums=premiums,show_premiums=show_premiums, \
                show_last_year=show_last_year,other_financial_indicators_l_y=other_financial_indicators_l_y, \
                balance_indicators_l_y=balance_indicators_l_y, flow_indicators_l_y=flow_indicators_l_y, \
                premiums_l_y=premiums_l_y,round=round,is_id_in_arr=is_id_in_arr, \
                b_l_y=b_l_y,e_l_y=e_l_y,get_hint=get_hint)



@bp.route('/chart.png/<c_id>/<begin>/<end>/<chart_type>')#plot chart for a given company (id = c_id) and chart type, and given period
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

@bp.route('/peers_review',methods=['GET','POST'])
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
    premiums = None
    show_competitors = False
    show_premiums = False
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
            return redirect(url_for('company_peers_profile.peers_review'))
        show_competitors = form.show_competitors.data#показывать детали по каждому конкуренту
        try:
            company_name, balance_indicators, flow_indicators, premiums, peers_names_arr = show_company_profile(c_id,peers,b,e,len(peers),show_competitors)
            other_financial_indicators = get_other_financial_indicators(balance_indicators,flow_indicators,b,e)
            peers_names = get_peers_names(peers)            
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранным компаниям за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('company_peers_profile.peers_review'))
        if len(other_financial_indicators) > 0:
            show_other_financial_indicators = True
        if len(balance_indicators) > 0:
            show_balance = True
        if len(flow_indicators) > 0:
            show_income_statement = True
        if len(premiums) > 0:            
            show_premiums = True
    return render_template('company_peers_profile/peers_review.html',title='Сравнение с конкурентами',form=form,descr=descr, \
                        show_balance=show_balance,show_income_statement=show_income_statement, \
                        show_other_financial_indicators=show_other_financial_indicators,b=b,e=e, \
                        company_name=company_name,balance_indicators=balance_indicators, \
                        flow_indicators=flow_indicators,other_financial_indicators=other_financial_indicators, \
                        peers_names=peers_names,show_competitors=show_competitors,show_premiums=show_premiums, \
                        peers_names_arr=peers_names_arr,get_hint=get_hint,premiums=premiums)
