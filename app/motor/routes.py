from flask import render_template, flash, redirect, url_for, request, g, send_from_directory
from app import db
from app.motor.forms import MotorForm
from flask_login import current_user, login_required
from app.models import Company, Financial_per_month, Premium_per_month, \
                        Claim_per_month, Indicator, Insclass
from datetime import datetime
from flask import send_from_directory
from app.motor import bp
from app.universal_routes import before_request_u, required_roles_u, get_months, \
                                get_months, save_to_log, get_hint, save_to_excel, transform_check_dates


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def get_flow_data(company_id,b,e,flow_type):#данные по показателю
    months = get_months(b,e)#какие месяцы относятся к заданному периоду
    ind_value = 0.0
    indicator = Indicator.query.filter(Indicator.name == flow_type).first()        
    ind_id = indicator.id#id нужного индикатора    
    for month in months:
        begin = month['begin']
        end = month['end']
        ind_v_m = Financial_per_month.query.join(Indicator) \
                        .with_entities(Financial_per_month.value) \
                        .filter(Financial_per_month.company_id == company_id) \
                        .filter(Indicator.id == ind_id) \
                        .filter(Financial_per_month.beg_date == begin) \
                        .filter(Financial_per_month.end_date == end).first()
        if ind_v_m is not None:
            ind_value += ind_v_m.value
    return ind_value


def get_premiums_claims_data(company_id,b,e,data_type,class_name):
    months = get_months(b,e)#какие месяцы относятся к заданному периоду
    ind_value = 0.0
    ins_class = Insclass.query.filter(Insclass.name == class_name).first()
    class_id = ins_class.id
    for month in months:
        begin = month['begin']
        end = month['end']
        if data_type == 'premiums':
            ind_v_m = Premium_per_month.query.join(Insclass) \
                        .with_entities(Premium_per_month.value) \
                        .filter(Premium_per_month.company_id == company_id) \
                        .filter(Insclass.id == class_id) \
                        .filter(Premium_per_month.beg_date == begin) \
                        .filter(Premium_per_month.end_date == end).first()
        elif data_type == 'claims':
            ind_v_m = Claim_per_month.query.join(Insclass) \
                        .with_entities(Claim_per_month.value) \
                        .filter(Claim_per_month.company_id == company_id) \
                        .filter(Insclass.id == class_id) \
                        .filter(Claim_per_month.beg_date == begin) \
                        .filter(Claim_per_month.end_date == end).first()
        if ind_v_m is not None:
            ind_value += ind_v_m.value
    return ind_value


def get_general_info(b,e):#общая инфо по компаниям
    general_info = list()
    companies = Company.query.with_entities(Company.id,Company.alias) \
                .filter(Company.nonlife==True).all()
    totals = {}
    total_premiums = 0
    total_net_premiums = 0
    total_claims = 0
    total_net_claims = 0
    total_motor_TPL_premiums = 0
    total_motor_TPL_claims = 0
    total_casco_premiums = 0
    total_casco_claims = 0
    total_motor_premiums = 0
    total_motor_claims = 0
    for company in companies:
        premiums = get_flow_data(company.id,b,e,'premiums')
        net_premiums = get_flow_data(company.id,b,e,'net_premiums')
        claims = get_flow_data(company.id,b,e,'claims')
        net_claims = get_flow_data(company.id,b,e,'net_claims')
        motor_TPL_premiums = get_premiums_claims_data(company.id,b,e,'premiums','obligatory_motor_TPL')
        motor_TPL_claims = get_premiums_claims_data(company.id,b,e,'claims','obligatory_motor_TPL')
        casco_premiums = get_premiums_claims_data(company.id,b,e,'premiums','motor_hull')
        casco_claims = get_premiums_claims_data(company.id,b,e,'claims','motor_hull')
        if premiums > 0:
            #вычисляемые        
            if net_premiums > 0:
                net_LR = round(net_claims / net_premiums * 100,2)
            else:
                net_LR = 'N.A.'
            if premiums > 0:
                re_share = round((premiums-net_premiums)/premiums*100,2)
                motor_TPL_prem_share = round(motor_TPL_premiums / premiums *100,2)
                casco_prem_share = round(casco_premiums / premiums *100,2)
            else:
                re_share = 'N.A.'
                motor_TPL_prem_share = 'N.A.'
                casco_prem_share = 'N.A.'
            motor_premiums = motor_TPL_premiums + casco_premiums
            motor_claims = motor_TPL_claims + casco_claims
            if motor_premiums > 0:
                motor_TPL_prem_share_in_motor = round(motor_TPL_premiums / motor_premiums *100,2)
                casco_prem_share_in_motor = round(casco_premiums / motor_premiums *100,2)
            else:
                motor_TPL_prem_share_in_motor = 'N.A.'
                casco_prem_share_in_motor = 'N.A.'
            obj = {'company_id': company.id, 'alias':company.alias,'premiums':premiums,'net_premiums':net_premiums,
                    'claims':claims,'net_claims':net_claims, 'net_LR':net_LR,'re_share':re_share,
                    'motor_TPL_premiums':motor_TPL_premiums,'motor_TPL_claims':motor_TPL_claims,
                    'casco_premiums':casco_premiums,'casco_claims':casco_claims,
                    'motor_TPL_prem_share':motor_TPL_prem_share,'casco_prem_share':casco_prem_share,
                    'motor_premiums':motor_premiums,'motor_claims':motor_claims,
                    'motor_TPL_prem_share_in_motor':motor_TPL_prem_share_in_motor,
                    'casco_prem_share_in_motor':casco_prem_share_in_motor}
            general_info.append(obj)
            total_premiums += premiums
            total_net_premiums += net_premiums
            total_claims += claims
            total_net_claims += net_claims
            total_motor_TPL_premiums += motor_TPL_premiums
            total_motor_TPL_claims += motor_TPL_claims
            total_casco_premiums += casco_premiums
            total_casco_claims += casco_claims
            total_motor_premiums += motor_premiums
            total_motor_claims += motor_claims            
    general_info.sort(key=lambda x: x['motor_premiums'], reverse=True)#сортируем по убыванию
    if total_net_premiums > 0:
        total_net_LR = round(total_net_claims / total_net_premiums * 100,2)
    else:
        total_net_LR = 'N.A.'
    if total_premiums > 0:
        total_re_share = round((total_premiums-total_net_premiums)/total_premiums*100,2)
        total_motor_TPL_prem_share = round(total_motor_TPL_premiums / total_premiums *100,2)
        total_casco_prem_share = round(total_casco_premiums / total_premiums *100,2)
    else:
        total_re_share = 'N.A.'
        total_motor_TPL_prem_share = 'N.A.'
        total_casco_prem_share = 'N.A.'
    if total_motor_premiums > 0:
        total_motor_TPL_prem_share_in_motor = round(total_motor_TPL_premiums / total_motor_premiums *100,2)
        total_casco_prem_share_in_motor = round(total_casco_premiums / total_motor_premiums *100,2)
    else:
        total_motor_TPL_prem_share_in_motor = 'N.A.'
        total_casco_prem_share_in_motor = 'N.A.'        
    totals = {'total_premiums':total_premiums, 'total_net_premiums':total_net_premiums,
               'total_claims':total_claims, 'total_net_claims':total_net_claims,
               'total_motor_TPL_premiums':total_motor_TPL_premiums,
               'total_motor_TPL_claims':total_motor_TPL_claims,
               'total_casco_premiums':total_casco_premiums,'total_casco_claims':total_casco_claims,
               'total_motor_premiums':total_motor_premiums,'total_motor_claims':total_motor_claims,
               'total_net_LR':total_net_LR,'total_re_share':total_re_share,
               'total_motor_TPL_prem_share':total_motor_TPL_prem_share,
               'total_casco_prem_share':total_casco_prem_share,
               'total_motor_TPL_prem_share_in_motor':total_motor_TPL_prem_share_in_motor,
               'total_casco_prem_share_in_motor':total_casco_prem_share_in_motor}
    return general_info, totals


def compare_to_l_y(general_info,general_info_l_y,totals,totals_l_y):#динамика по сравнению с прошлым годом
    deltas = list()
    total_deltas = {}
    companies = list()
    for c in general_info:
        company = {'id':c['company_id'],'alias':c['alias']}
        companies.append(company)
    for company in companies:        
        for el in general_info:
            if el['company_id'] == company['id']:
                premiums = el['premiums']
                net_premiums = el['net_premiums']
                claims = el['claims']
                net_claims = el['net_claims']
                motor_TPL_premiums = el['motor_TPL_premiums']
                motor_TPL_claims = el['motor_TPL_claims']
                casco_premiums = el['casco_premiums']
                casco_claims = el['casco_claims']
                motor_premiums = el['motor_premiums']
                motor_claims = el['motor_claims']
                break
            else:
                continue
        for el in general_info_l_y:
            if el['company_id'] == company['id']:
                premiums_l_y = el['premiums']
                net_premiums_l_y = el['net_premiums']
                claims_l_y = el['claims']
                net_claims_l_y = el['net_claims']
                motor_TPL_premiums_l_y = el['motor_TPL_premiums']
                motor_TPL_claims_l_y = el['motor_TPL_claims']
                casco_premiums_l_y = el['casco_premiums']
                casco_claims_l_y = el['casco_claims']
                motor_premiums_l_y = el['motor_premiums']
                motor_claims_l_y = el['motor_claims']                
                break
            else:
                continue
        if premiums > 0:
            if premiums_l_y > 0:
                premiums_delta = round((premiums / premiums_l_y-1)*100,2)
            else:
                premiums_delta = 'N.A.'
            if net_premiums_l_y > 0:
                net_premiums_delta = round((net_premiums / net_premiums_l_y-1)*100,2)
            else:
                net_premiums_delta = 'N.A.'
            if claims_l_y > 0:
                claims_delta = round((claims / claims_l_y-1)*100,2)
            else:
                claims_delta = 'N.A.'
            if net_claims_l_y > 0:
                net_claims_delta = round((net_claims / net_claims_l_y-1)*100,2)
            else:
                net_claims_delta = 'N.A.'
            if motor_TPL_premiums_l_y > 0:
                motor_TPL_premiums_delta = round((motor_TPL_premiums / motor_TPL_premiums_l_y-1)*100,2)
            else:
                motor_TPL_premiums_delta = 'N.A.'
            if motor_TPL_claims_l_y > 0:
                motor_TPL_claims_delta = round((motor_TPL_claims / motor_TPL_claims_l_y -1)*100,2)
            else:
                motor_TPL_claims_delta = 'N.A.'
            if casco_premiums_l_y > 0:
                casco_premiums_delta = round((casco_premiums / casco_premiums_l_y -1)*100,2)
            else:
                casco_premiums_delta = 'N.A.'
            if casco_claims_l_y > 0:
                casco_claims_delta = round(( casco_claims / casco_claims_l_y -1)*100,2)
            else:
                casco_claims_delta = 'N.A.'
            if motor_premiums_l_y > 0:
                motor_premiums_delta = round(( motor_premiums / motor_premiums_l_y -1)*100,2)
            else:
                motor_premiums_delta = 'N.A.'
            if motor_claims_l_y > 0:
                motor_claims_delta = round(( motor_claims / motor_claims_l_y -1)*100,2)
            else:
                motor_claims_delta = 'N.A.'
            obj = {'company_id':company['id'], 'alias':company['alias'], 'motor_premiums':motor_premiums,
                        'premiums_delta':premiums_delta, 'net_premiums_delta':net_premiums_delta,
                        'claims_delta':claims_delta,'net_claims_delta':net_claims_delta,
                        'motor_TPL_premiums_delta':motor_TPL_premiums_delta,'motor_TPL_claims_delta':motor_TPL_claims_delta,
                        'casco_premiums_delta':casco_premiums_delta,'casco_claims_delta':casco_claims_delta,
                        'motor_premiums_delta':motor_premiums_delta,'motor_claims_delta':motor_claims_delta}
            deltas.append(obj)
    deltas.sort(key=lambda x: x['motor_premiums'], reverse=True)#сортируем по убыванию
    #итоговые изменения
    if totals_l_y['total_premiums'] > 0:
        total_premiums_delta = round((totals['total_premiums'] / totals_l_y['total_premiums']-1)*100,2)
    else:
        total_premiums_delta = 'N.A.'
    if totals_l_y['total_net_premiums'] > 0:
        total_net_premiums_delta = round((totals['total_net_premiums'] / totals_l_y['total_net_premiums']-1)*100,2)
    else:
        total_net_premiums_delta = 'N.A.'
    if totals_l_y['total_claims'] > 0:
        total_claims_delta = round((totals['total_claims'] / totals_l_y['total_claims']-1)*100,2)
    else:
        total_claims_delta = 'N.A.'
    if totals_l_y['total_net_claims'] > 0:
        total_net_claims_delta = round((totals['total_net_claims'] / totals_l_y['total_net_claims']-1)*100,2)
    else:
        total_net_claims_delta = 'N.A.'
    if totals_l_y['total_motor_TPL_premiums'] > 0:
        total_motor_TPL_premiums_delta = round((totals['total_motor_TPL_premiums'] / totals_l_y['total_motor_TPL_premiums']-1)*100,2)
    else:
        total_motor_TPL_premiums_delta = 'N.A.'
    if totals_l_y['total_motor_TPL_claims'] > 0:
        total_motor_TPL_claims_delta = round((totals['total_motor_TPL_claims'] / totals_l_y['total_motor_TPL_claims'] -1)*100,2)
    else:
        total_motor_TPL_claims_delta = 'N.A.'
    if totals_l_y['total_casco_premiums'] > 0:
        total_casco_premiums_delta = round((totals['total_casco_premiums'] / totals_l_y['total_casco_premiums'] -1)*100,2)
    else:
        total_casco_premiums_delta = 'N.A.'
    if totals_l_y['total_casco_claims'] > 0:
        total_casco_claims_delta = round((totals['total_casco_claims'] / totals_l_y['total_casco_claims'] -1)*100,2)
    else:
        total_casco_claims_delta = 'N.A.'
    if totals_l_y['total_motor_premiums'] > 0:
        total_motor_premiums_delta = round(( totals['total_motor_premiums'] / totals_l_y['total_motor_premiums'] -1)*100,2)
    else:
        total_motor_premiums_delta = 'N.A.'
    if totals_l_y['total_motor_claims'] > 0:
        total_motor_claims_delta = round(( totals['total_motor_claims'] / totals_l_y['total_motor_claims'] -1)*100,2)
    else:
        total_motor_claims_delta = 'N.A.'
    total_deltas = {'total_premiums_delta':total_premiums_delta,'total_net_premiums_delta':total_net_premiums_delta,
                    'total_claims_delta':total_claims_delta,'total_net_claims_delta':total_net_claims_delta,
                    'total_motor_TPL_premiums_delta':total_motor_TPL_premiums_delta,
                    'total_motor_TPL_claims_delta':total_motor_TPL_claims_delta,
                    'total_casco_premiums_delta':total_casco_premiums_delta,
                    'total_casco_claims_delta':total_casco_claims_delta,
                    'total_motor_premiums_delta':total_motor_premiums_delta,
                    'total_motor_claims_delta':total_motor_claims_delta}
    return deltas, total_deltas


@bp.route('/motor',methods=['GET','POST'])
@login_required
def motor():#инфо по автострахованию
    title = 'Автострахование'
    descr = 'Общая информация по компаниям и автострахованию. Выберите класс и период.'
    form = MotorForm()
    b = g.min_report_date
    e = g.last_report_date 
    b_l_y = None
    e_l_y = None
    general_info = None    
    general_info_l_y = None
    delta_info = None
    totals = None
    totals_l_y = None
    total_deltas = None
    show_last_year = False
    show_general_info = False
    show_info = False
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        show_last_year = form.show_last_year.data
        #преобразуем даты выборки (сбросим на 1-е число) и проверим корректность ввода
        b,e,b_l_y,e_l_y,period_str,check_res,err_txt = transform_check_dates(form.begin_d.data,form.end_d.data,show_last_year)
        if not check_res:
            flash(err_txt)
            return redirect(url_for('motor.motor'))
        
        show_general_info = form.show_general_info.data
        try:
            general_info, totals = get_general_info(b,e)#общая информация                      
            if show_last_year == True:               
                try:
                    general_info_l_y, totals_l_y = get_general_info(b_l_y,e_l_y)
                    delta_info, total_deltas = compare_to_l_y(general_info,general_info_l_y,totals,totals_l_y)
                except:
                    flash('Не могу получить данные за прошлый год')
                    return redirect(url_for('motor.motor'))            
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('motor.motor'))

        if form.show_info_submit.data:#show data
            save_to_log('motor',current_user.id)
            show_info = True
        elif form.save_to_file_submit.data:
            save_to_log('motor_file',current_user.id)
            sheets = list()
            sheets_names = list()            
            sheets.append(general_info)
            sheets_names.append(period_str + ' общ. и авто')            
            if show_last_year == True:
                period_l_y_str = b_l_y.strftime('%Y-%m') + '_' + e_l_y.strftime('%Y-%m')                
                sheets.append(general_info_l_y)               
                sheets_names.append(period_l_y_str + ' общ. и авто')                
            wb_name = 'motor_general_' + period_str
            path, wb_name_f = save_to_excel('motor_general',period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('motor/motor.html',title=title,form=form,descr=descr, \
                b=b,e=e,show_last_year=show_last_year,b_l_y=b_l_y,e_l_y=e_l_y, \
                general_info=general_info, len=len, show_info=show_info, \
                general_info_l_y=general_info_l_y,show_general_info=show_general_info, \
                delta_info=delta_info, totals=totals, totals_l_y=totals_l_y, \
                total_deltas=total_deltas, get_hint=get_hint)