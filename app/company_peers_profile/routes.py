from flask import render_template, flash, redirect, url_for, request, g, Response, send_from_directory
from app import db
from app.company_peers_profile.forms import CompanyProfileForm, PeersForm
from flask_login import current_user, login_required
from app.models import Company, Insclass, Indicator, Financial, \
            Financial_per_month, Premium_per_month, Claim_per_month            
from datetime import datetime
from app.company_peers_profile import bp
from app.universal_routes import before_request_u, required_roles_u, \
                    save_to_log, get_num_companies_at_date, is_id_in_arr, \
                    get_num_companies_per_period, get_hint, save_to_excel, transform_check_dates, \
                    str_to_date, str_to_bool
from app.transform_data import get_months, get_df_indicators, get_df_prem_or_claim_per_period_for_company, \
                                merge_claims_prems_compute_LR_for_company, compute_other_financial_indicators, \
                                get_df_financial_per_period_for_company
import pandas as pd
from app.plot_graphs import plot_linear_graph, plot_barchart


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def df_row_peers_to_list(row,N_companies):
    peers = list()
    if N_companies < 1 or N_companies > 50:
        return peers
    for c in range(N_companies):
        value_num = 'value'+str(c)
        if c == 0:
            value = row.value0
        elif c == 1:
            value = row.value1
        elif c == 2:
            value = row.value2
        peers.append({value_num:value})
    return peers


def df_to_list(df,N_companies):#вспомогат. ф-ция
    output = list()
    peers = list()
    
    i = 0
    for row_index,row in df.iterrows():
        base = {'row_index':i,'system_name':row.system_name,'fullname':row.fullname,
                'value':row.value,'total':row.total,'mkt_av':row.mkt_av,'share':row.share, 'peers':peers}
        output.append(base)
        i += 1
    
    if N_companies is not None and N_companies > 0:# peers given        
        for c in range(N_companies):
            df_c = df
            if c > 0:
                df_c = df_c.drop(['value_current'], axis=1)#drop columns
            df_c.rename(columns = {'value'+str(c):'value_current'}, inplace = True)#rename columns

            peers_current_column = list()
            for row_index,row in df_c.iterrows():
                peers_current_column.append(row.value_current)
            peers.append(peers_current_column)
        
        #transponse
        peers_t = list(map(list, zip(*peers)))

        i = 0
        for el in output:#attach peers to output
            el['peers'] = peers_t[i]
            i += 1
    
    return output


def df_premiums_claims_to_list(df,N_companies):#вспомогат. ф-ция
    output = list()
    peers_premiums = list()
    peers_claims = list()
    peers_lr = list()
    i = 0
    for row_index,row in df.iterrows():
        if row.claims>0 or row.premiums>0:
            output.append({'row_index':i,'alias':row.alias,'claims':row.claims,
                        'claims_share':row.claims_share,'premiums':row.premiums,'premiums_share':row.premiums_share,'lr':row.lr,
                        'peers_premiums':peers_premiums,'peers_claims':peers_claims,'peers_lr':peers_lr})
            i += 1

    if N_companies is not None and N_companies>0:#peers given
        for c in range(N_companies):
            df_c = df
            if c > 0:
                df_c = df_c.drop(['premiums_current'], axis=1)#drop columns
                df_c = df_c.drop(['claims_current'], axis=1)#drop columns
                df_c = df_c.drop(['lr_current'], axis=1)#drop columns
            df_c.rename(columns = {'premiums'+str(c):'premiums_current'}, inplace = True)#rename columns
            df_c.rename(columns = {'claims'+str(c):'claims_current'}, inplace = True)#rename columns
            df_c.rename(columns = {'lr'+str(c):'lr_current'}, inplace = True)#rename columns

            peers_current_column_premiums = list()
            peers_current_column_claims = list()
            peers_current_column_lr = list()
            for row_index,row in df_c.iterrows():
                peers_current_column_premiums.append(row.premiums_current)
                peers_current_column_claims.append(row.claims_current)
                peers_current_column_lr.append(row.lr_current)
            peers_premiums.append(peers_current_column_premiums)
            peers_claims.append(peers_current_column_claims)
            peers_lr.append(peers_current_column_lr)

        #transponse
        peers_premiums_t = list(map(list, zip(*peers_premiums)))
        peers_claims_t = list(map(list, zip(*peers_claims)))
        peers_lr_t = list(map(list, zip(*peers_lr)))

        i = 0
        for el in output:#attach peers to output
            el['peers_premiums'] = peers_premiums_t[i]
            el['peers_claims'] = peers_claims_t[i]
            el['peers_lr'] = peers_lr_t[i]
            i += 1
    
    return output


def get_info_for_company_profile_per_period(company_id,peers,b,e,N_companies,show_last_year,show_competitors):#get info
    balance_indicators = list()
    flow_indicators = list()
    premiums = list()
    other_financial_indicators = list()
    totals = None

    df_balance_indicators = get_df_indicators(True,b,e,company_id,peers,N_companies)
    df_flow_indicators = get_df_indicators(False,b,e,company_id,peers,N_companies)
    df_premiums_by_class, total_premiums = get_df_prem_or_claim_per_period_for_company(company_id,b,e,True,peers,N_companies)
    df_claims_by_class, total_claims = get_df_prem_or_claim_per_period_for_company(company_id,b,e,False,peers,N_companies)
    df_premiums_claims, lr_av = merge_claims_prems_compute_LR_for_company(df_claims_by_class,df_premiums_by_class,N_companies)
    months = get_months(b,e)#период анализа
    other_financial_indicators = compute_other_financial_indicators(df_balance_indicators,df_flow_indicators,len(months),N_companies)

    if not show_last_year:
        balance_indicators = df_to_list(df_balance_indicators,N_companies)
        flow_indicators = df_to_list(df_flow_indicators,N_companies)
        premiums = df_premiums_claims_to_list(df_premiums_claims,N_companies)

    totals = {'total_premiums':total_premiums, 'total_claims':total_claims, 'lr_av':lr_av}

    return df_balance_indicators, df_flow_indicators, df_premiums_claims, other_financial_indicators, \
        balance_indicators, flow_indicators, premiums, totals


def merge_df_and_df_l_y(df1,df2):
    output = list()
    df = pd.merge(df1,df2,on='id')#merge 2 df
    df = df.drop(['system_name_y', 'fullname_y'], axis=1)#drop columns
    df.rename(columns = {'system_name_x':'system_name','fullname_x':'fullname','value_x':'value','total_x':'total',
                                                'mkt_av_x':'mkt_av','share_x':'share','value_y':'value_l_y','total_y':'total_l_y',
                                                'mkt_av_y':'mkt_av_l_y','share_y':'share_l_y'}, inplace = True)#rename columns
    df['value_delta'] = round((df['value'] / df['value_l_y'] - 1) * 100,2)
    df['value_delta_abs'] = round(df['value'] - df['value_l_y'],2)
    df['total_delta'] = round((df['total'] / df['total_l_y'] - 1) * 100,2)
    df['total_delta_abs'] = round(df['total'] - df['total_l_y'],2)
    i = 0
    for row_index,row in df.iterrows():
        output.append({'row_index':i,'system_name':row.system_name,'fullname':row.fullname,
                        'value':row.value,'total':row.total,'mkt_av':row.mkt_av,'share':row.share,
                        'value_l_y':row.value_l_y,'total_l_y':row.total_l_y,'mkt_av_l_y':row.mkt_av_l_y,'share_l_y':row.share_l_y,
                        'value_delta':row.value_delta,'value_delta_abs':row.value_delta_abs,
                        'total_delta':row.total_delta,'total_delta_abs':row.total_delta_abs})
        i += 1
    return output


def merge_premiums_df_and_df_l_y(df1,df2,totals1,totals2):
    output = list()
    df = pd.merge(df1,df2,on='id',how='outer')#merge 2 df
    df = df.drop(['alias_y'], axis=1)#drop columns
    df.rename(columns = {'alias_x':'alias','claims_x':'claims','claims_share_x':'claims_share','premiums_x':'premiums',
                                                'premiums_share_x':'premiums_share','lr_x':'lr','claims_y':'claims_l_y',
                                                'claims_share_y':'claims_share_l_y','premiums_y':'premiums_l_y',
                                                'premiums_share_y':'premiums_share_l_y','lr_y':'lr_l_y'}, inplace = True)#rename columns
    df['premiums_delta'] = round((df['premiums'] / df['premiums_l_y'] - 1) * 100,2)
    df['lr_delta'] = round(df['lr'] - df['lr_l_y'],2)
    df['claims_delta'] = round((df['claims'] / df['claims_l_y'] - 1) * 100,2)
    i = 0
    for row_index,row in df.iterrows():
        if row.claims>0 or row.premiums>0:
            output.append({'row_index':i,'alias':row.alias,'claims':row.claims,
                        'claims_share':row.claims_share,'premiums':row.premiums,'premiums_share':row.premiums_share,'lr':row.lr,
                        'claims_l_y':row.claims_l_y,'claims_share_l_y':row.claims_share_l_y,'premiums_l_y':row.premiums_l_y,
                        'premiums_share_l_y':row.premiums_share_l_y,'lr_l_y':row.lr_l_y,
                        'claims_delta':row.claims_delta, 'premiums_delta':row.premiums_delta, 'lr_delta':row.lr_delta})
            i += 1
    total_premiums_delta = round((totals1['total_premiums'] / totals2['total_premiums'] - 1)*100,2)
    total_claims_delta = round((totals1['total_claims'] / totals2['total_claims'] - 1)*100,2)
    total_lr_delta = round(totals1['lr_av'] - totals2['lr_av'],2)
    totals = {'total_premiums':totals1['total_premiums'], 'total_claims':totals1['total_claims'], 'lr_av':totals1['lr_av'],
            'total_premiums_l_y':totals2['total_premiums'], 'total_claims_l_y':totals2['total_claims'], 'lr_av_l_y':totals2['lr_av'],
            'total_premiums_delta':total_premiums_delta,'total_claims_delta':total_claims_delta,'total_lr_delta':total_lr_delta}
    return output,totals


def merge_other_fin_ind_and_l_y(input1,input2):#вспомогат.
    output = list()
    for item1 in input1:
        for item2 in input2:
            if item1['ind_id'] == item2['ind_id']:
                try:
                    delta_c = round(item1['value_c']-item2['value_c'],2)
                except:
                    delta_c = 'N.A.'
                try:
                    delta_m = round(item1['value_m']-item2['value_m'],2)
                except:
                    delta_m = 'N.A.'
                output.append({'ind_id':item1['ind_id'],'name':item1['name'],
                                'value_c':item1['value_c'],'value_m':item1['value_m'],
                                'value_c_l_y':item2['value_c'],'value_m_l_y':item2['value_m'],
                                'delta_c':delta_c,'delta_m':delta_m})
    return output


def get_general_motor_info(company_id,peers,b,e,b_l_y,e_l_y,N_companies,show_last_year,show_competitors):#инфа по авто и общая инфа в разрезе компаний
    balance_indicators = list()
    flow_indicators = list()
    premiums = list()
    other_financial_indicators = list()

    _company_name = Company.query.with_entities(Company.alias).filter(Company.id == company_id).first()
    company_name = _company_name[0]#company name

    peers_names_arr = list()
    if show_competitors and peers is not None:
        for company in peers:        
            cur_company = Company.query.filter(Company.id == company[0]).first()
            cur_company_name = cur_company.alias
            peers_names_arr.append({'peer_name':cur_company_name})

    df_balance_indicators, df_flow_indicators, df_premiums_claims, other_financial_indicators, \
        balance_indicators, flow_indicators, premiums, \
        totals = get_info_for_company_profile_per_period(company_id,peers,b,e,N_companies,show_last_year,show_competitors)

    if show_last_year:
        df_balance_indicators_l_y, df_flow_indicators_l_y, df_premiums_claims_l_y, other_financial_indicators_l_y, \
            balance_indicators_l_y, flow_indicators_l_y, premiums_l_y, \
            totals_l_y = get_info_for_company_profile_per_period(company_id,peers,b_l_y,e_l_y,N_companies,show_last_year,show_competitors)
        balance_indicators = merge_df_and_df_l_y(df_balance_indicators,df_balance_indicators_l_y)
        flow_indicators = merge_df_and_df_l_y(df_flow_indicators,df_flow_indicators_l_y)
        premiums, totals = merge_premiums_df_and_df_l_y(df_premiums_claims,df_premiums_claims_l_y,totals,totals_l_y)
        other_financial_indicators = merge_other_fin_ind_and_l_y(other_financial_indicators,other_financial_indicators_l_y)
                
    return company_name, balance_indicators, flow_indicators, premiums, peers_names_arr, other_financial_indicators, totals


def df_to_list_for_plot(df,N_digits,N_round):#вспомогат. ф-ция
    labels = list()
    values = list()    
    for row_index,row in df.iterrows():
        labels.append(row.month_name)
        if N_round == 0:
            value = round(row.value/N_digits)
        else:
            value = round(row.value/N_digits,N_round)
        values.append(value)
    return labels,values


def df_to_list_for_lr(df,show_last_year):#вспомогат. ф-ция
    labels = list()
    values = list()
    values_l_y = list()
    if show_last_year:
        for row_index,row in df.iterrows():
            labels.append(row.alias_x)
            values.append(row.lr_x)
            values_l_y.append(row.lr_y)
    else:
        for row_index,row in df.iterrows():
            labels.append(row.alias)
            values.append(row.lr)
    return labels,values,values_l_y


def df_to_list_for_plot_prems(df,N_digits,N_round,show_last_year):#вспомогат. ф-ция
    labels = list()
    values = list()
    values_l_y = list()
    if show_last_year:
        for row_index,row in df.iterrows():
            labels.append(row.alias_x)
            if N_round == 0:
                try:
                    value = round(row.premiums_x/N_digits)
                except:
                    value = 0
                try:
                    value_l_y = round(row.premiums_y/N_digits)
                except:
                    value_l_y = 0
            else:
                try:
                    value = round(row.premiums_x/N_digits,N_round)
                except:
                    value = 0
                try:
                    value_l_y = round(row.premiums_y/N_digits,N_round)
                except:
                    value_l_y = 0
            values.append(value)
            values_l_y.append(value_l_y)
    else:
        for row_index,row in df.iterrows():
            labels.append(row.alias)
            if N_round == 0:
                value = round(row.premiums/N_digits)                
            else:
                value = round(row.premiums/N_digits,N_round)
            values.append(value)
    return labels,values,values_l_y


@bp.route('/chart_for_company.png/<company_id>/<b>/<e>/<b_l_y>/<e_l_y>/<show_last_year_str>/<annotate_param>/<chart_type>/<indicator_type>')#plot chart for a given class
def plot_png_for_company(company_id,b,e,b_l_y,e_l_y,show_last_year_str,annotate_param,chart_type,indicator_type):
    show_last_year = str_to_bool(show_last_year_str)
    annotate = str_to_bool(annotate_param)
    b = str_to_date(b)
    e = str_to_date(e)
    b_l_y = str_to_date(b_l_y)
    e_l_y = str_to_date(e_l_y)
    
    labels = list()
    values = list()
    values_l_y = list()
    label1 = 'текущий период'
    label2 = 'прошлый год'
    title = None

    if chart_type == 'linear_graph':
        if indicator_type == 'equity':
            df = get_df_financial_per_period_for_company(True,company_id,'equity',b,e)
            labels,values = df_to_list_for_plot(df,1000,0)
            title = 'Собственный капитал на конец месяца, млн.тг.'
            if show_last_year:
                df = get_df_financial_per_period_for_company(True,company_id,'equity',b_l_y,e_l_y)
                labels,values_l_y = df_to_list_for_plot(df,1000,0)
        elif indicator_type == 'reserves':
            df = get_df_financial_per_period_for_company(True,company_id,'reserves',b,e)
            labels,values = df_to_list_for_plot(df,1000,0)
            title = 'Страховые резервы на конец месяца, млн.тг.'
            if show_last_year:
                df = get_df_financial_per_period_for_company(True,company_id,'reserves',b_l_y,e_l_y)
                labels,values_l_y = df_to_list_for_plot(df,1000,0)
        elif indicator_type == 'solvency_margin':
            df = get_df_financial_per_period_for_company(True,company_id,'solvency_margin',b,e)
            labels,values = df_to_list_for_plot(df,1,2)
            title = 'Норматив ФМП на конец месяца'
            if show_last_year:
                df = get_df_financial_per_period_for_company(True,company_id,'solvency_margin',b_l_y,e_l_y)
                labels,values_l_y = df_to_list_for_plot(df,1,2)
        elif indicator_type == 'net_prem':
            df = get_df_financial_per_period_for_company(False,company_id,'net_premiums',b,e)
            labels,values = df_to_list_for_plot(df,1000,0)
            title = 'Норматив ФМП на конец месяца'
            if show_last_year:
                df = get_df_financial_per_period_for_company(False,company_id,'net_premiums',b_l_y,e_l_y)
                labels,values_l_y = df_to_list_for_plot(df,1000,0)

        return plot_linear_graph(labels,values,values_l_y,label1,label2,show_last_year,annotate,title)

    elif chart_type == 'bar_chart':
        if indicator_type == 'lr_lob':
            df_premiums_by_class, total_premiums = get_df_prem_or_claim_per_period_for_company(company_id,b,e,True,None,None)
            df_claims_by_class, total_claims = get_df_prem_or_claim_per_period_for_company(company_id,b,e,False,None,None)
            df_premiums_claims, lr_av = merge_claims_prems_compute_LR_for_company(df_claims_by_class,df_premiums_by_class,None)
            labels,values,values_l_y = df_to_list_for_lr(df_premiums_claims.head(5),False)
            title = 'Коэффициент выплат, топ-5 классов'
            ylabel = 'Коэффициент выплат %'
            if show_last_year:
                df_premiums_by_class_l_y, total_premiums_l_y = get_df_prem_or_claim_per_period_for_company(company_id,b_l_y,e_l_y,True,None,None)
                df_claims_by_class_l_y, total_claims_l_y = get_df_prem_or_claim_per_period_for_company(company_id,b_l_y,e_l_y,False,None,None)
                df_premiums_claims_l_y, lr_av = merge_claims_prems_compute_LR_for_company(df_claims_by_class_l_y,df_premiums_by_class_l_y,None)
                df_merged = pd.merge(df_premiums_claims,df_premiums_claims_l_y,on='id',how='outer')
                labels,values,values_l_y = df_to_list_for_lr(df_merged.head(5),show_last_year)
        elif indicator_type == 'premiums_lob':
            df_premiums_by_class, total_premiums = get_df_prem_or_claim_per_period_for_company(company_id,b,e,True,None,None)
            df_claims_by_class, total_claims = get_df_prem_or_claim_per_period_for_company(company_id,b,e,False,None,None)
            df_premiums_claims, lr_av = merge_claims_prems_compute_LR_for_company(df_claims_by_class,df_premiums_by_class,None)
            labels,values,values_l_y = df_to_list_for_plot_prems(df_premiums_claims.head(5),1000,0,False)
            title = 'Страховой портфель, топ-5 классов'
            ylabel = 'Премии, млн. тг.'
            if show_last_year:
                df_premiums_by_class_l_y, total_premiums_l_y = get_df_prem_or_claim_per_period_for_company(company_id,b_l_y,e_l_y,True,None,None)
                df_claims_by_class_l_y, total_claims_l_y = get_df_prem_or_claim_per_period_for_company(company_id,b_l_y,e_l_y,False,None,None)
                df_premiums_claims_l_y, lr_av_l_y = merge_claims_prems_compute_LR_for_company(df_claims_by_class_l_y,df_premiums_by_class_l_y,None)
                df_merged = pd.merge(df_premiums_claims,df_premiums_claims_l_y,on='id',how='outer')                
                labels,values,values_l_y = df_to_list_for_plot_prems(df_merged.head(5),1000,0,show_last_year)
        
        return plot_barchart(labels,values,values_l_y,title,ylabel,show_last_year,label1,label2)

           

def path_to_charts(base_img_path,company_id,b,e,b_l_y,e_l_y,show_last_year,annotate,chart_type,indicator_type):#путь к графику
    path = "/" + base_img_path + "/" + company_id + "/" + b.strftime('%m-%d-%Y') + "/" + e.strftime('%m-%d-%Y') + "/" + b_l_y.strftime('%m-%d-%Y') + "/" + e_l_y.strftime('%m-%d-%Y') + "/" + str(show_last_year) + "/" + str(annotate) + "/" + chart_type + "/" + indicator_type
    return path


@bp.route('/company_profile',methods=['GET','POST'])
@login_required
def company_profile():#портрет компании
    descr = 'Портрет компании на последнюю отчетную дату (с начала года).'
    form = CompanyProfileForm()
    balance_indicators = list()
    flow_indicators = list()
    other_financial_indicators = list()
    premiums = list()    
    img_path_premiums_by_LoB_pie =None
    img_path_lr_by_LoB = None
    company_name = None
    img_path_solvency_margin = None
    img_path_net_premium = None
    img_path_equity = None
    img_path_reserves = None
    show_last_year = False
    b = g.min_report_date
    e = g.last_report_date
    b_l_y = None
    e_l_y = None
    show_info = False
    totals = None
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число)
        show_last_year = form.show_last_year.data
        #преобразуем даты выборки (сбросим на 1-е число) и проверим корректность ввода
        b,e,b_l_y,e_l_y,period_str,check_res,err_txt = transform_check_dates(form.begin_d.data,form.end_d.data,show_last_year)
        if not check_res:
            flash(err_txt)
            return redirect(url_for('company_peers_profile.company_profile'))

        #подготовим данные для таблиц
        try:
            company_name, balance_indicators, flow_indicators, premiums, \
                peers_names_arr, other_financial_indicators, totals = get_general_motor_info(int(form.company.data),None,b,e,b_l_y,e_l_y,None,show_last_year,False)        
        except:
            flash('Не удается получить данные. Возможно, выбранная компания не существовала в заданный период. Попробуйте выбрать другой период.')
            return redirect(url_for('company_peers_profile.company_profile'))

        #зададим пути к диаграммам        
        base_name = 'chart_for_company.png'
        img_path_solvency_margin = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'linear_graph','solvency_margin')
        img_path_net_premium = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'linear_graph','net_prem')
        img_path_equity = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'linear_graph','equity')
        img_path_reserves = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'linear_graph','reserves')
        img_path_lr_by_LoB = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'bar_chart','lr_lob')
        img_path_premiums_by_LoB_pie = path_to_charts(base_name,form.company.data,b,e,b_l_y,e_l_y,show_last_year,True,'bar_chart','premiums_lob')
        
        
        if form.show_info_submit.data:#show data
            save_to_log('company_profile',current_user.id)
            show_info = True

        elif form.save_to_file_submit.data:#save to excel file
            save_to_log('company_profile_file',current_user.id)
            sheets = list()
            sheets_names = list()
            sheets.append(balance_indicators)
            sheets.append(flow_indicators)
            sheets.append(other_financial_indicators)
            sheets.append(premiums)
            sheets_names.append(period_str + ' баланс')
            sheets_names.append(period_str + ' ОПУ')
            sheets_names.append(period_str + ' другие фин.')
            sheets_names.append(period_str + ' страх.портфель')
            wb_name = company_name + '_' + period_str
            path, wb_name_f = save_to_excel(company_name,period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('company_peers_profile/company_profile.html',title='Портрет компании',form=form,descr=descr,company_name=company_name, \
                balance_indicators=balance_indicators, flow_indicators=flow_indicators, \
                img_path_premiums_by_LoB_pie=img_path_premiums_by_LoB_pie, \
                img_path_lr_by_LoB=img_path_lr_by_LoB,img_path_solvency_margin=img_path_solvency_margin, \
                img_path_net_premium=img_path_net_premium,b=b,e=e,b_l_y=b_l_y,e_l_y=e_l_y, \
                img_path_equity=img_path_equity,other_financial_indicators=other_financial_indicators, \
                img_path_reserves=img_path_reserves,premiums=premiums, \
                show_last_year=show_last_year, \
                get_hint=get_hint,show_info=show_info,totals=totals)


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
    company_name = None
    peers_names = None
    peers_names_arr = None
    premiums = list()
    show_competitors = False
    b = g.min_report_date
    e = g.last_report_date
    show_info = False
    if request.method == 'GET':#подставим в форму доступные мин. и макс. отчетные даты
        beg_this_year = datetime(g.last_report_date.year,1,1)
        form.begin_d.data = max(g.min_report_date,beg_this_year)
        form.end_d.data = g.last_report_date
    if form.validate_on_submit():
        #преобразуем даты выборки (сбросим на 1-е число) и проверим корректность ввода
        b,e,b_l_y,e_l_y,period_str,check_res,err_txt = transform_check_dates(form.begin_d.data,form.end_d.data,False)
        if not check_res:
            flash(err_txt)
            return redirect(url_for('company_peers_profile.peers_review'))
        c_id = int(form.company.data)#компания
        peers_str = form.peers.data#выбранные конкуренты
        peers = list()
        for c in peers_str:#convert id to int
            peers.append((int(c),))
        #подготовим данные для таблиц
        if form.company.data in peers_str:
            flash('''Вы выбрали Вашу компанию в списке конкурентов. 
                Сравнивать себя с собой не имеет большого смысла, не правда ли?
                Составьте список конкурентов без указания своей компании и попробуйте снова.''')
            return redirect(url_for('company_peers_profile.peers_review'))
        show_competitors = form.show_competitors.data#показывать детали по каждому конкуренту
        try:
            company_name, balance_indicators, flow_indicators, premiums, \
                peers_names_arr, other_financial_indicators, totals = get_general_motor_info(c_id,peers,b,e,b_l_y,e_l_y,len(peers),False,show_competitors)
            peers_names = get_peers_names(peers)        
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранным компаниям за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('company_peers_profile.peers_review'))

        if form.show_info_submit.data:#show data
            save_to_log('peers_review',current_user.id)
            show_info = True
        elif form.save_to_file_submit.data:
            save_to_log('peers_review_file',current_user.id)
            sheets = list()
            sheets_names = list()
            sheets.append(balance_indicators)
            sheets.append(flow_indicators)
            sheets.append(other_financial_indicators)
            sheets.append(premiums)            
            sheets_names.append(period_str + ' баланс')
            sheets_names.append(period_str + ' ОПУ')
            sheets_names.append(period_str + ' другие фин.')
            sheets_names.append(period_str + ' страх.портфель')
            
            if show_competitors == True:#показывать конкурентов
                peer_count = 0
                peer_balance_flow_indicators_col_names = ['Название компании','Название показателя','Значение, тыс.тг.']
                peer_other_financial_indicators_col_names = ['Название компании','Название показателя','Значение']
                peer_premiums_col_names = ['Название компании', 'Класс', 'Премии, тыс.тг.','Выплаты, тыс.тг.','Коэффициент выплат, %']
                for peer in peers_names_arr:#по каждой компании
                    peer_name_obj = peers_names_arr[peer_count]
                    peer_name = peer_name_obj['peer_name']
                    balance_indicators_peer,flow_indicators_peer,other_financial_indicators_peer,premiums_peer = prepare_peer_info_for_excel(peer_count,peer_name,balance_indicators,flow_indicators,other_financial_indicators,premiums)
                    sheets.append(balance_indicators_peer)
                    sheets.append(flow_indicators_peer)
                    sheets.append(other_financial_indicators_peer)
                    sheets.append(premiums_peer)
                    sheets_names.append(str(peer_count) + ' баланс')
                    sheets_names.append(str(peer_count) + ' ОПУ')
                    sheets_names.append(str(peer_count) + ' другие фин.')
                    sheets_names.append(str(peer_count) + ' страх.портфель')
                    peer_count += 1
            
            wb_name = company_name + '_' + period_str
            path, wb_name_f = save_to_excel(company_name,period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('company_peers_profile/peers_review.html',title='Сравнение с конкурентами',form=form,descr=descr, b=b,e=e,\
                        company_name=company_name,balance_indicators=balance_indicators, \
                        flow_indicators=flow_indicators,other_financial_indicators=other_financial_indicators, \
                        peers_names=peers_names,show_competitors=show_competitors, len=len, \
                        peers_names_arr=peers_names_arr,get_hint=get_hint,premiums=premiums,show_info=show_info)


def prepare_peer_info_for_excel(peer_count,peer_name,balance_indicators,flow_indicators,other_financial_indicators,premiums):
    #вспомогательная функция - получаем показатели по каждому конкуренту
    balance_indicators_peer = list()
    flow_indicators_peer = list()
    other_financial_indicators_peer = list()
    premiums_peer = list()
    for ind in balance_indicators:
        peers_ind = ind['peers']
        peer_ind = peers_ind[peer_count]
        balance_indicators_peer.append({'peer_name':peer_name,'fullname':ind['fullname'],'value':peer_ind})
    for ind in flow_indicators:
        peers_ind = ind['peers']
        peer_ind = peers_ind[peer_count]
        flow_indicators_peer.append({'peer_name':peer_name,'fullname':ind['fullname'],'value':peer_ind})
    for ind in other_financial_indicators:
        peers_ind = ind['peers']
        peer_ind = peers_ind[peer_count]
        other_financial_indicators_peer.append({'peer_name':peer_name,'fullname':ind['name'],'value':peer_ind})
    for ind in premiums:
        class_name = ind['alias']
        premiums_peer.append({'peer_name':peer_name,'class_name':class_name,'peer_premium':ind['peers_premiums'][peer_count],'peer_claim':ind['peers_claims'][peer_count],'peer_LR':ind['peers_lr'][peer_count]})
    return balance_indicators_peer,flow_indicators_peer,other_financial_indicators_peer,premiums_peer

