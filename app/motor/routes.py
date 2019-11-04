from flask import render_template, flash, redirect, url_for, request, g, send_from_directory
from app import db
from app.motor.forms import MotorForm
from flask_login import current_user, login_required
from app.models import Company, Financial_per_month, Premium_per_month, \
                        Claim_per_month, Indicator, Insclass
from datetime import datetime
from flask import send_from_directory
from app.motor import bp
import pandas as pd
from app.universal_routes import before_request_u, required_roles_u, \
                                save_to_log, get_hint, save_to_excel, transform_check_dates
from app.transform_data import get_df_financial_per_period, merge_claims_prems_compute_LR, get_df_prem_or_claim_per_period


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def get_class_id(class_name):#ins class id
    ins_class = Insclass.query.filter(Insclass.name == class_name).first()#casco id
    class_id = ins_class.id
    return class_id

def get_info_per_period(b,e,show_last_year):#вспомогат. ф-ция - получаем инфо по периоду
    general_info = list()    
    totals = None
    #list of names for columns of final data frame
    column_names = dict()
    column_names['net_claims'] = 'net_claims'
    column_names['net_premiums'] = 'net_premiums'
    column_names['net_LR'] = 'net_LR'
    column_names['premiums'] = 'premiums'
    column_names['claims'] = 'claims'
    column_names['gross_LR'] = 'gross_LR'
    column_names['re_share'] = 're_share'
    column_names['casco_claims'] = 'casco_claims'
    column_names['casco_premiums'] = 'casco_premiums'
    column_names['casco_LR'] = 'casco_LR'
    column_names['motor_TPL_claims'] = 'motor_TPL_claims'
    column_names['motor_TPL_premiums'] = 'motor_TPL_premiums'
    column_names['motor_TPL_LR'] = 'motor_TPL_LR'
    column_names['motor_premiums'] = 'motor_premiums'
    column_names['motor_claims'] = 'motor_claims'
    column_names['motor_LR'] = 'motor_LR'
    column_names['motor_TPL_prem_share'] = 'motor_TPL_prem_share'
    column_names['casco_prem_share'] = 'casco_prem_share'
    column_names['motor_TPL_prem_share_in_motor'] = 'motor_TPL_prem_share_in_motor'
    column_names['casco_prem_share_in_motor'] = 'casco_prem_share_in_motor'
    
    if show_last_year:#names of columns w/ _l_y
        for k,v in column_names.items():
            column_names[k] = v + '_l_y'#add _l_y for last year data
        
    df_net_premiums,net_premiums_total=get_df_financial_per_period('net_premiums',b,e)#net premiums per period
    df_net_claims,net_claims_total=get_df_financial_per_period('net_claims',b,e)#net claims per period
    df_net_lr,net_lr_av = merge_claims_prems_compute_LR(df_net_claims,df_net_premiums,False,False)#net Loss Ratio per period
    df_net_lr = df_net_lr.drop(['share_x', 'alias_y', 'share_y'], axis=1)#drop columns
    df_net_lr.rename(columns = {'alias_x':'alias', 'value_x':column_names['net_claims'],'value_y':column_names['net_premiums'],'lr':column_names['net_LR']}, inplace = True)#rename columns
    
    df_premiums,premiums_total=get_df_financial_per_period('premiums',b,e)#premiums
    df_merged = pd.merge(df_net_lr,df_premiums,on='id')#merge 2 df
    df_merged = df_merged.drop(['share', 'alias_y'], axis=1)#drop columns
    df_merged.rename(columns = {'alias_x':'alias', 'value':column_names['premiums']}, inplace = True)#rename
    df_claims,claims_total=get_df_financial_per_period('claims',b,e)#claims
    df_merged = pd.merge(df_merged,df_claims,on='id')#merge 2 df
    df_merged = df_merged.drop(['share', 'alias_y'], axis=1)#drop columns
    df_merged.rename(columns = {'alias_x':'alias', 'value':column_names['claims']}, inplace = True)#rename
    df_lr,gross_lr_av = merge_claims_prems_compute_LR(df_claims,df_premiums,False,False)#Loss Ratio per period
    df_merged = pd.merge(df_merged,df_lr,on='id')#merge 2 df
    df_merged = df_merged.drop(['alias_x','alias_y','share_x','share_y','value_x','value_y'], axis=1)#drop columns
    df_merged.rename(columns = {'lr':column_names['gross_LR']}, inplace = True)#rename columns
    df_merged[column_names['re_share']] = round((df_merged[column_names['premiums']]-df_merged[column_names['net_premiums']])/df_merged[column_names['premiums']]*100,2)
    total_re_share = round((premiums_total-net_premiums_total)/premiums_total*100,2)

    class_id = get_class_id('motor_hull')#casco id    
    df_premiums_casco,premiums_casco_total=get_df_prem_or_claim_per_period(class_id,b,e,True,False,False)
    df_claims_casco,claims_casco_total=get_df_prem_or_claim_per_period(class_id,b,e,False,False,False)
    df_lr_casco,lr_casco_av=merge_claims_prems_compute_LR(df_claims_casco,df_premiums_casco,False,False)
    df_lr_casco = df_lr_casco.drop(['alias_x','alias_y','share_x','share_y'], axis=1)#drop columns
    df_lr_casco.rename(columns = {'value_x':column_names['casco_claims'], 'value_y': column_names['casco_premiums'], 'lr':column_names['casco_LR']}, inplace = True)#rename columns
    df_merged = pd.merge(df_merged,df_lr_casco,on='id')#merge 2 df

    class_id = get_class_id('obligatory_motor_TPL')#motor TPL id    
    df_premiums_motor_TPL,premiums_motor_TPL_total=get_df_prem_or_claim_per_period(class_id,b,e,True,False,False)
    df_claims_motor_TPL,claims_motor_TPL_total=get_df_prem_or_claim_per_period(class_id,b,e,False,False,False)
    df_lr_motor_TPL,lr_motor_TPL_av=merge_claims_prems_compute_LR(df_claims_motor_TPL,df_premiums_motor_TPL,False,False)
    df_lr_motor_TPL = df_lr_motor_TPL.drop(['alias_x','alias_y','share_x','share_y'], axis=1)#drop columns
    df_lr_motor_TPL.rename(columns = {'value_x':column_names['motor_TPL_claims'], 'value_y': column_names['motor_TPL_premiums'], 'lr':column_names['motor_TPL_LR']}, inplace = True)#rename columns
    df_merged = pd.merge(df_merged,df_lr_motor_TPL,on='id')#merge 2 df

    df_merged[column_names['motor_premiums']] = df_merged[column_names['casco_premiums']] + df_merged[column_names['motor_TPL_premiums']]#total motor premiums
    motor_premiums_total = premiums_motor_TPL_total + premiums_casco_total
    df_merged[column_names['motor_claims']] = df_merged[column_names['casco_claims']] + df_merged[column_names['motor_TPL_claims']]#total motor claims
    motor_claims_total = claims_motor_TPL_total + claims_casco_total
    df_merged[column_names['motor_LR']] = round(df_merged[column_names['motor_claims']] / df_merged[column_names['motor_premiums']]*100,2)#total motor claims ratio
    motor_lr_av = round(motor_claims_total / motor_premiums_total * 100,2)
    df_merged[column_names['motor_TPL_prem_share']] = round(df_merged[column_names['motor_TPL_premiums']] / df_merged[column_names['premiums']]*100,2)
    motor_TPL_prem_share_av = round(premiums_motor_TPL_total / premiums_total*100,2)
    df_merged[column_names['casco_prem_share']] = round(df_merged[column_names['casco_premiums']] / df_merged[column_names['premiums']]*100,2)
    casco_prem_share_av = round(premiums_casco_total / premiums_total*100,2)
    df_merged[column_names['motor_TPL_prem_share_in_motor']] = round(df_merged[column_names['motor_TPL_premiums']] / df_merged[column_names['motor_premiums']]*100,2)
    motor_TPL_prem_share_in_motor_av = round(premiums_motor_TPL_total / motor_premiums_total*100,2)
    df_merged[column_names['casco_prem_share_in_motor']] = round(df_merged[column_names['casco_premiums']] / df_merged[column_names['motor_premiums']]*100,2)
    casco_prem_share_in_motor_av = round(premiums_casco_total / motor_premiums_total*100,2)
    df_merged = df_merged.sort_values(by=column_names['motor_premiums'],ascending=False)#sort by motor premiums
    
    if not show_last_year:
        i = 0
        for row_index,row in df_merged.iterrows():
            general_info.append({'row_index':i,'alias':row.alias,'premiums':row.premiums,'claims':row.claims,'gross_LR':row.gross_LR,
                                'net_premiums':row.net_premiums,'net_claims':row.net_claims,'net_LR':row.net_LR,
                                're_share':row.re_share,
                                'motor_TPL_premiums':row.motor_TPL_premiums,'motor_TPL_claims':row.motor_TPL_claims,'motor_TPL_LR':row.motor_TPL_LR,
                                'casco_premiums':row.casco_premiums,'casco_claims':row.casco_claims,'casco_LR':row.casco_LR,
                                'motor_premiums':row.motor_premiums,'motor_claims':row.motor_claims,'motor_LR':row.motor_LR,
                                'motor_TPL_prem_share':row.motor_TPL_prem_share,'casco_prem_share':row.casco_prem_share,
                                'motor_TPL_prem_share_in_motor':row.motor_TPL_prem_share_in_motor,'casco_prem_share_in_motor':row.casco_prem_share_in_motor})
            i += 1

    totals = {'premiums_total':premiums_total,'claims_total':claims_total,'gross_lr_av':gross_lr_av,
                'net_premiums_total':net_premiums_total,'net_claims_total':net_claims_total,'net_lr_av':net_lr_av,
                'total_re_share':total_re_share,
                'premiums_motor_TPL_total':premiums_motor_TPL_total,'claims_motor_TPL_total':claims_motor_TPL_total,'lr_motor_TPL_av':lr_motor_TPL_av,
                'premiums_casco_total':premiums_casco_total,'claims_casco_total':claims_casco_total,'lr_casco_av':lr_casco_av,
                'motor_premiums_total':motor_premiums_total,'motor_claims_total':motor_claims_total,'motor_lr_av':motor_lr_av,
                'motor_TPL_prem_share_av':motor_TPL_prem_share_av,'casco_prem_share_av':casco_prem_share_av,
                'motor_TPL_prem_share_in_motor_av':motor_TPL_prem_share_in_motor_av,'casco_prem_share_in_motor_av':casco_prem_share_in_motor_av}

    return df_merged,general_info,totals


def compute_percent_change(value,value_l_y):#вспомогат. - изменение величины в %
    return round((value / value_l_y - 1) * 100,2)


def get_general_motor_info(b,e,b_l_y,e_l_y,show_last_year):#инфа по авто и общая инфа в разрезе компаний
    delta_info = list()
    total_deltas = None

    df_merged,general_info,totals = get_info_per_period(b,e,False)

    if show_last_year:
        df_merged_l_y,general_info_l_y,totals_l_y = get_info_per_period(b_l_y,e_l_y,True)
        df_merged_tmp = pd.merge(df_merged,df_merged_l_y,on='id')#merge 2 df        
        df_merged_tmp['premiums_delta'] = round((df_merged_tmp['premiums'] / df_merged_tmp['premiums_l_y'] - 1) * 100,2)
        df_merged_tmp['net_premiums_delta'] = round((df_merged_tmp['net_premiums'] / df_merged_tmp['net_premiums_l_y'] - 1) * 100,2)
        df_merged_tmp['claims_delta'] = round((df_merged_tmp['claims'] / df_merged_tmp['claims_l_y'] - 1) * 100,2)
        df_merged_tmp['net_claims_delta'] = round((df_merged_tmp['net_claims'] / df_merged_tmp['net_claims_l_y'] - 1) * 100,2)
        df_merged_tmp['casco_premiums_delta'] = round((df_merged_tmp['casco_premiums'] / df_merged_tmp['casco_premiums_l_y'] - 1) * 100,2)
        df_merged_tmp['motor_TPL_premiums_delta'] = round((df_merged_tmp['motor_TPL_premiums'] / df_merged_tmp['motor_TPL_premiums_l_y'] - 1) * 100,2)
        df_merged_tmp['motor_premiums_delta'] = round((df_merged_tmp['motor_premiums'] / df_merged_tmp['motor_premiums_l_y'] - 1) * 100,2)
        df_merged_tmp['casco_claims_delta'] = round((df_merged_tmp['casco_claims'] / df_merged_tmp['casco_claims_l_y'] - 1) * 100,2)
        df_merged_tmp['motor_TPL_claims_delta'] = round((df_merged_tmp['motor_TPL_claims'] / df_merged_tmp['motor_TPL_claims_l_y'] - 1) * 100,2)
        df_merged_tmp['motor_claims_delta'] = round((df_merged_tmp['motor_claims'] / df_merged_tmp['motor_claims_l_y'] - 1) * 100,2)
        
        i = 0
        for row_index,row in df_merged_tmp.iterrows():
            delta_info.append({'row_index':i,'alias':row.alias_x,'premiums_delta':row.premiums_delta,'net_premiums_delta':row.net_premiums_delta,
                                'claims_delta':row.claims_delta,'net_claims_delta':row.net_claims_delta,
                                'casco_premiums_delta':row.casco_premiums_delta,'motor_TPL_premiums_delta':row.motor_TPL_premiums_delta,
                                'motor_premiums_delta':row.motor_premiums_delta,'casco_claims_delta':row.casco_claims_delta,
                                'motor_TPL_claims_delta':row.motor_TPL_claims_delta,'motor_claims_delta':row.motor_claims_delta})
            i+=1
        
        total_deltas = {'total_premiums_delta':compute_percent_change(totals['premiums_total'],totals_l_y['premiums_total']),
                        'total_net_premiums_delta':compute_percent_change(totals['net_premiums_total'],totals_l_y['net_premiums_total']),
                        'total_claims_delta':compute_percent_change(totals['claims_total'],totals_l_y['claims_total']),
                        'total_net_claims_delta':compute_percent_change(totals['net_claims_total'],totals_l_y['net_claims_total']),
                        'total_casco_premiums_delta':compute_percent_change(totals['premiums_casco_total'],totals_l_y['premiums_casco_total']),
                        'total_motor_TPL_premiums_delta':compute_percent_change(totals['premiums_motor_TPL_total'],totals_l_y['premiums_motor_TPL_total']),
                        'total_motor_premiums_delta':compute_percent_change(totals['motor_premiums_total'],totals_l_y['motor_premiums_total']),
                        'total_casco_claims_delta':compute_percent_change(totals['claims_casco_total'],totals_l_y['claims_casco_total']),
                        'total_motor_TPL_claims_delta':compute_percent_change(totals['claims_motor_TPL_total'],totals_l_y['claims_motor_TPL_total']),
                        'total_motor_claims_delta':compute_percent_change(totals['motor_claims_total'],totals_l_y['motor_claims_total'])}

    return general_info, totals, delta_info, total_deltas


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
    delta_info = None
    totals = None    
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
            general_info, totals, delta_info, total_deltas = get_general_motor_info(b,e,b_l_y,e_l_y,show_last_year)
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
            wb_name = 'motor_general_' + period_str
            path, wb_name_f = save_to_excel('motor_general',period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('motor/motor.html',title=title,form=form,descr=descr, \
                b=b,e=e,show_last_year=show_last_year,b_l_y=b_l_y,e_l_y=e_l_y, \
                general_info=general_info, show_info=show_info, \
                show_general_info=show_general_info, \
                delta_info=delta_info, totals=totals, \
                total_deltas=total_deltas, get_hint=get_hint)