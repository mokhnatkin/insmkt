from flask import render_template, flash, redirect, url_for, request, g, \
                    current_app, send_from_directory
from app import db
from app.class_profile.forms import ClassProfileForm, InsformForm
from flask_login import current_user, login_required
from app.models import Company, Insclass, Premium_per_month, Claim_per_month
from datetime import datetime
from app.class_profile import bp
from app.universal_routes import before_request_u, required_roles_u, \
                    save_to_log, get_hint, add_str_timestamp, save_to_excel, \
                    transform_check_dates, str_to_date, str_to_bool
from app.transform_data import merge_two_df_convert_to_list, convert_df_to_list, \
                    get_df_prem_or_claim_per_period, merge_claims_prems_compute_LR
from app.plot_graphs import plot_linear_graph


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def get_class_companies(class_id,b,e,show_last_year,b_l_y,e_l_y,insform=False):#инфо по выбранному классу по компаниям за период
    def get_form_name(form_id):#получаем имя  формы страхования по id
        insforms = current_app.config['INS_FORMS']#insurance forms
        res = None
        for f in insforms:
            if f[0] == form_id:
                res = f[1]
        return res
        
    if insform:
        class_name = get_form_name(class_id)
    else:
        _class_name = Insclass.query.filter(Insclass.id == class_id).first()
        class_name = _class_name.alias#class name

    premiums_total = None
    premiums_total_l_y = None
    claims_total = None
    claims_total_l_y = None
    lr_av = None
    lr_av_l_y = None
    ############################################################################
    df_premiums,premiums_total=get_df_prem_or_claim_per_period(class_id,b,e,True,False,insform)
    df_claims,claims_total=get_df_prem_or_claim_per_period(class_id,b,e,False,False,insform)
    df_class_companies,lr_av=merge_claims_prems_compute_LR(df_claims,df_premiums,False,False)
    if show_last_year:
        df_premiums_l_y,premiums_total_l_y=get_df_prem_or_claim_per_period(class_id,b_l_y,e_l_y,True,False,insform)
        df_claims_l_y,claims_total_l_y=get_df_prem_or_claim_per_period(class_id,b_l_y,e_l_y,False,False,insform)
        df_class_companies_l_y,lr_av_l_y=merge_claims_prems_compute_LR(df_claims_l_y,df_premiums_l_y,False,False)
        class_companies = merge_two_df_convert_to_list(df_class_companies,df_class_companies_l_y,False,False,True,False)
    else:
        class_companies = convert_df_to_list(df_class_companies,False,True,False)
    return class_name, class_companies, premiums_total, premiums_total_l_y, claims_total, claims_total_l_y, lr_av, lr_av_l_y


def get_class_info(class_id,b,e,show_last_year,b_l_y,e_l_y,insform=False):#инфо по динамике развития класса за период
    class_totals_l_y = None
    df_premiums,premiums_total=get_df_prem_or_claim_per_period(class_id,b,e,True,True,insform)    
    df_claims,claims_total=get_df_prem_or_claim_per_period(class_id,b,e,False,True,insform)
    df_premiums_claims_lr,lr_av=merge_claims_prems_compute_LR(df_claims,df_premiums,True,False)    
    class_totals = {'total_p':premiums_total,'total_c':claims_total,'total_lr':lr_av}
    if show_last_year:
        df_premiums_l_y,premiums_total_l_y=get_df_prem_or_claim_per_period(class_id,b_l_y,e_l_y,True,True,insform)
        df_claims_l_y,claims_total_l_y=get_df_prem_or_claim_per_period(class_id,b_l_y,e_l_y,False,True,insform)
        df_premiums_claims_lr_l_y,lr_av_l_y=merge_claims_prems_compute_LR(df_claims_l_y,df_premiums_l_y,True,True)
        class_totals_l_y = {'total_p':premiums_total_l_y,'total_c':claims_total_l_y,'total_lr':lr_av_l_y}
        class_info = merge_two_df_convert_to_list(df_premiums_claims_lr,df_premiums_claims_lr_l_y,False,False,True,True)
    else:
        class_info = convert_df_to_list(df_premiums_claims_lr,False,True,True)
    return class_info, class_totals, class_totals_l_y



@bp.route('/chart_for_class.png/<c_id>/<b>/<e>/<b_l_y>/<e_l_y>/<show_last_year_str>/<annotate_param>/<chart_type>/<insform_str>')#plot chart for a given class
def plot_png_for_class(c_id,b,e,b_l_y,e_l_y,show_last_year_str,annotate_param,chart_type,insform_str='False'):
    show_last_year = str_to_bool(show_last_year_str)
    annotate = str_to_bool(annotate_param)
    insform = str_to_bool(insform_str)
    b = str_to_date(b)
    e = str_to_date(e)
    b_l_y = str_to_date(b_l_y)
    e_l_y = str_to_date(e_l_y)
    class_info, class_totals, class_totals_l_y = get_class_info(c_id,b,e,show_last_year,b_l_y,e_l_y,insform)#динамика развития по классу
    labels = list()
    values = list()
    values_l_y = list()
    label1 = None
    label2 = None
    title = None
    for el in class_info:#compute values and labels for graph
        labels.append(el['month_name'])
        if chart_type == 'prem':
            values.append(round(el['premium']/1000))
            if show_last_year:
                values_l_y.append(round(el['premium_l_y']/1000))
        elif chart_type == 'claim':
            values.append(round(el['claim']/1000))
            if show_last_year:
                values_l_y.append(round(el['claim_l_y']/1000))
        elif chart_type == 'lr':
            values.append(el['lr'])
            if show_last_year:
                values_l_y.append(el['lr_l_y'])
    label1 = 'текущий период'
    label2 = 'прошлый год'

    if chart_type == 'prem':
        title = 'Помесячная динамика премий, млн.тг.'
    elif chart_type == 'claim':
        title = 'Помесячная динамика выплат, млн.тг.'
    elif chart_type == 'lr':
        title = 'Помесячная динамика коэффициента выплат, %'
    elif chart_type == 'prem_claim_scatter':
        title = 'Ежемесячные премии и выплаты по компаниям'

    if chart_type in ('prem','claim','lr'):
        return plot_linear_graph(labels,values,values_l_y,label1,label2,show_last_year,annotate,title)
    else:
        return None


def path_to_charts(base_img_path,class_id,b,e,b_l_y,e_l_y,show_last_year,annotate,chart_type,insform):#путь к графику
    path = "/" + base_img_path + "/" + class_id + "/" + b.strftime('%m-%d-%Y') + "/" + \
                e.strftime('%m-%d-%Y') + "/" + b_l_y.strftime('%m-%d-%Y') + "/" + \
                e_l_y.strftime('%m-%d-%Y') + "/" + str(show_last_year) + "/" + \
                str(annotate) + "/" + chart_type + "/" + str(insform)
    return path


@bp.route('/class_profile',methods=['GET','POST'])
@login_required
def class_profile():#инфо по классу
    descr = 'Информация по классу страхования. Выберите класс и период.'
    form = ClassProfileForm()
    b = g.min_report_date
    e = g.last_report_date
    class_name = None
    class_companies = None
    premiums_total = None
    premiums_total_l_y = None
    claims_total = None
    claims_total_l_y = None
    lr_av = None
    lr_av_l_y = None
    delta_prem_total = None
    delta_claim_total = None
    delta_lr_total = None
    class_totals = None
    class_info = None
    class_totals_l_y = None
    img_path_prem = None
    img_path_claim = None
    img_path_lr = None
    show_last_year = False
    class_companies_l_y = None    
    b_l_y = None
    e_l_y = None
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
            return redirect(url_for('class_profile.class_profile'))
        class_id = int(form.insclass.data)        
        try:
            class_name, class_companies, premiums_total, premiums_total_l_y, claims_total, claims_total_l_y, lr_av, lr_av_l_y = get_class_companies(class_id,b,e,show_last_year,b_l_y,e_l_y,False)#информация по компаниям по выбранному классу
            class_info, class_totals, class_totals_l_y = get_class_info(class_id,b,e,show_last_year,b_l_y,e_l_y,False)            
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранному классу за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('class_profile.class_profile'))
        if show_last_year:
            delta_prem_total = round((premiums_total - premiums_total_l_y) / premiums_total_l_y * 100,2)
            delta_claim_total = round((claims_total - claims_total_l_y) / claims_total_l_y * 100,2)
            delta_lr_total = round(lr_av - lr_av_l_y,2)
        
        #пути к графикам
        base_name = 'chart_for_class.png'
        img_path_prem = path_to_charts(base_name,form.insclass.data,b,e,b_l_y,e_l_y,show_last_year,True,'prem',False)
        img_path_claim = path_to_charts(base_name,form.insclass.data,b,e,b_l_y,e_l_y,show_last_year,True,'claim',False)
        img_path_lr = path_to_charts(base_name,form.insclass.data,b,e,b_l_y,e_l_y,show_last_year,False,'lr',False)
 
        if form.show_info_submit.data:#show data
            save_to_log('class_profile',current_user.id)
            show_info = True

        elif form.save_to_file_submit.data:
            save_to_log('class_profile_file',current_user.id)
            sheets = list()
            sheets_names = list()            
            sheets.append(class_companies)
            sheets.append(class_info)
            sheets_names.append(period_str + ' по компаниям')
            sheets_names.append(period_str + ' по месяцам')
            wb_name = class_name + '_' + period_str
            path, wb_name_f = save_to_excel(class_name,period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('class_profile/class_profile.html',title='Информация по продукту', \
                form=form,descr=descr, \
                b=b,e=e,class_companies=class_companies,class_name=class_name, \
                img_path_prem=img_path_prem, img_path_lr=img_path_lr, \
                img_path_claim=img_path_claim,class_info=class_info,class_totals=class_totals ,\
                show_last_year=show_last_year,class_companies_l_y=class_companies_l_y, \
                b_l_y=b_l_y,e_l_y=e_l_y, \
                get_hint=get_hint,show_info=show_info, \
                premiums_total=premiums_total, premiums_total_l_y=premiums_total_l_y, \
                claims_total=claims_total, claims_total_l_y=claims_total_l_y, \
                lr_av=lr_av, lr_av_l_y=lr_av_l_y, \
                delta_prem_total = delta_prem_total, delta_claim_total = delta_claim_total, \
                delta_lr_total = delta_lr_total, \
                class_totals_l_y=class_totals_l_y)


@bp.route('/insform_profile',methods=['GET','POST'])
@login_required
def insform_profile():#инфо по классу
    descr = 'Информация по форме страхования (обязательная / ДЛС / ДИС). Выберите форму и период.'
    form = InsformForm()
    b = g.min_report_date
    e = g.last_report_date
    class_name = None
    class_companies = None
    premiums_total = None
    premiums_total_l_y = None
    claims_total = None
    claims_total_l_y = None
    lr_av = None
    lr_av_l_y = None
    delta_prem_total = None
    delta_claim_total = None
    delta_lr_total = None
    class_totals = None
    class_info = None
    class_totals_l_y = None
    img_path_prem = None
    img_path_claim = None
    img_path_lr = None
    show_last_year = False
    class_companies_l_y = None    
    b_l_y = None
    e_l_y = None
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
            return redirect(url_for('class_profile.insform_profile'))
        form_id = form.insform.data        
        try:
            class_name, class_companies, premiums_total, premiums_total_l_y, claims_total, claims_total_l_y, lr_av, lr_av_l_y = get_class_companies(form_id,b,e,show_last_year,b_l_y,e_l_y,True)#информация по компаниям по выбранному классу
            class_info, class_totals, class_totals_l_y = get_class_info(form_id,b,e,show_last_year,b_l_y,e_l_y,True)
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранной форме страхования за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('class_profile.insform_profile'))
        if show_last_year:
            delta_prem_total = round((premiums_total - premiums_total_l_y) / premiums_total_l_y * 100,2)
            delta_claim_total = round((claims_total - claims_total_l_y) / claims_total_l_y * 100,2)
            delta_lr_total = round(lr_av - lr_av_l_y,2)
        
        #пути к графикам
        base_name = 'chart_for_class.png'
        img_path_prem = path_to_charts(base_name,form_id,b,e,b_l_y,e_l_y,show_last_year,True,'prem',True)
        img_path_claim = path_to_charts(base_name,form_id,b,e,b_l_y,e_l_y,show_last_year,True,'claim',True)
        img_path_lr = path_to_charts(base_name,form_id,b,e,b_l_y,e_l_y,show_last_year,False,'lr',True)

        if form.show_info_submit.data:#show data
            save_to_log('form_profile',current_user.id)
            show_info = True

        elif form.save_to_file_submit.data:
            save_to_log('form_profile_file',current_user.id)
            sheets = list()
            sheets_names = list()            
            sheets.append(class_companies)
            sheets.append(class_info)
            sheets_names.append(period_str + ' по компаниям')
            sheets_names.append(period_str + ' по месяцам')
            wb_name = class_name + '_' + period_str
            path, wb_name_f = save_to_excel(class_name,period_str,wb_name,sheets,sheets_names)#save file and get path
            if path is not None:                
                return send_from_directory(path, filename=wb_name_f, as_attachment=True)
            else:
                flash('Не могу сформировать файл, либо сохранить на сервер')
    return render_template('class_profile/class_profile.html',title='Информация по форме страхования', \
                form=form,descr=descr, \
                b=b,e=e,class_companies=class_companies,class_name=class_name, \
                img_path_prem=img_path_prem, img_path_lr=img_path_lr, \
                img_path_claim=img_path_claim,class_info=class_info,class_totals=class_totals ,\
                show_last_year=show_last_year,class_companies_l_y=class_companies_l_y, \
                b_l_y=b_l_y,e_l_y=e_l_y, \
                get_hint=get_hint,show_info=show_info, \
                premiums_total=premiums_total, premiums_total_l_y=premiums_total_l_y, \
                claims_total=claims_total, claims_total_l_y=claims_total_l_y, \
                lr_av=lr_av, lr_av_l_y=lr_av_l_y, \
                delta_prem_total = delta_prem_total, delta_claim_total = delta_claim_total, \
                delta_lr_total = delta_lr_total, \
                class_totals_l_y=class_totals_l_y)