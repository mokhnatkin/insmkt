from flask import render_template, flash, redirect, url_for, request, g, Response
from app import db
from app.class_profile.forms import ClassProfileForm
from flask_login import current_user, login_required
from app.models import Company, Insclass, Premium_per_month, Claim_per_month
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from app.class_profile import bp
from app.universal_routes import before_request_u, required_roles_u, get_months, save_to_log


@bp.before_request
def before_request():
    return before_request_u()


def required_roles(*roles):
    return required_roles_u(*roles)


def get_class_companies(class_id,b,e):#инфо по выбранному классу по компаниям за период
    _class_name = Insclass.query.filter(Insclass.id == class_id).first()
    class_name = _class_name.alias#class name
    months = get_months(b,e)#list of months for a given period
    ##########################################################
    #fetch premiums and claims for class and period
    premiums_per_month = list()
    claims_per_month = list()
    for month in months:
        begin = month['begin']
        end = month['end']
        #fetch premiums
        premiums = Premium_per_month.query.join(Company) \
                            .with_entities(Company.id,Premium_per_month.value) \
                            .filter(Premium_per_month.insclass_id == class_id) \
                            .filter(Premium_per_month.beg_date == begin) \
                            .filter(Premium_per_month.end_date == end).all()
        for i in premiums:
            ind = {'b':begin,'e':end,'company_id':i.id,'value':i.value}
            premiums_per_month.append(ind)
        #fetch claims
        claims = Claim_per_month.query.join(Company) \
                            .with_entities(Company.id,Claim_per_month.value) \
                            .filter(Claim_per_month.insclass_id == class_id) \
                            .filter(Claim_per_month.beg_date == begin) \
                            .filter(Claim_per_month.end_date == end).all()
        for i in claims:
            ind = {'b':begin,'e':end,'company_id':i.id,'value':i.value}
            claims_per_month.append(ind)            
    ##################################################################
    class_companies = list()#final list to be returned
    companies = Company.query.all()
    total_mkt_prem = 0.0
    for c in companies:#compute for each company        
        total_prem = 0.0
        total_claim = 0.0
        for m in premiums_per_month:
            if m['company_id'] == c.id:
                total_prem += m['value']
        for m in claims_per_month:
            if m['company_id'] == c.id:
                total_claim += m['value']
        total_mkt_prem += total_prem
        if total_prem > 0:
            lr = round(total_claim / total_prem * 100,2)#коэф-т выплат
        else:
            lr = 'N.A.'
        if total_prem > 0 or total_claim > 0:
            company_el = {'id': c.id, 'name': c.alias, 'premium': total_prem, 'claim': total_claim, 'lr':lr}
            class_companies.append(company_el)
    class_companies.sort(key=lambda x: x['premium'], reverse=True)#сортируем по убыванию
    #compute mkt share
    for i in class_companies:
        share = round(i['premium'] / total_mkt_prem * 100,2)
        i['share'] = share
    return class_name, class_companies


def get_class_info(class_id,b,e):#инфо по динамике развития класса за период
    months = get_months(b,e)#list of months for a given period
    class_info = list()#final list to be returned
    for month in months:
        begin = month['begin']
        end = month['end']
        premiums = Premium_per_month.query \
                            .with_entities(Premium_per_month.value) \
                            .filter(Premium_per_month.insclass_id == class_id) \
                            .filter(Premium_per_month.beg_date == begin) \
                            .filter(Premium_per_month.end_date == end).all()
        claims = Claim_per_month.query \
                            .with_entities(Claim_per_month.value) \
                            .filter(Claim_per_month.insclass_id == class_id) \
                            .filter(Claim_per_month.beg_date == begin) \
                            .filter(Claim_per_month.end_date == end).all()                            
        month_total_p = 0.0
        for p in premiums:
            month_total_p += p.value
        month_total_c = 0.0
        for c in claims:
            month_total_c += c.value            
        month_name = str(begin.year) + '-' +str(begin.month)
        if month_total_p > 0:
            lr = round(month_total_c / month_total_p * 100,2)
        else:
            lr = 'N.A.'
        el = {'month_name':month_name,'premium':month_total_p,'claim':month_total_c,'lr':lr}
        class_info.append(el)
    total_p = 0.0
    total_c = 0.0
    for i in class_info:
        total_p += i['premium']
        total_c += i['claim']
    if total_c > 0:
        total_lr = round(total_c / total_p * 100, 2)
    else:
        total_c = 'N.A.'
    class_totals = {'total_p':total_p,'total_c':total_c,'total_lr':total_lr}
    return class_info, class_totals


@bp.route('/chart_for_class.png/<c_id>/<begin>/<end>/<chart_type>')#plot chart for a given class
def plot_png_for_class(c_id,begin,end,chart_type):
    b = datetime.strptime(begin, '%m-%d-%Y')
    e = datetime.strptime(end, '%m-%d-%Y')    
    fig = create_plot_for_class(c_id,b,e,chart_type)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')


def create_plot_for_class(c_id,b,e,chart_type):#plots pie chart for a given company
    class_info, class_totals = get_class_info(c_id,b,e)#динамика развития по классу
    labels = list()
    values_prem = list()
    values_claim = list()    
    for el in class_info:
        labels.append(el['month_name'])
        values_prem.append(round(el['premium']/1000))
        values_claim.append(round(el['claim']/1000))        
    #plot chart depending on chart_type
    if chart_type == 'prem':
        values = values_prem
        fig, ax = plt.subplots()
        ax.plot(labels, values)
        ax.set_title('Помесячная динамика премий, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(j),xy=(i,j))
    elif chart_type == 'claim':
        values = values_claim
        fig, ax = plt.subplots()
        ax.plot(labels, values)
        ax.set_title('Помесячная динамика выплат, млн.тг.')
        for i,j in zip(labels,values):
            ax.annotate(str(round(j)),xy=(i,j))
    fig.autofmt_xdate()
    return fig


@bp.route('/class_profile',methods=['GET','POST'])
@login_required
def class_profile():#инфо по классу
    descr = 'Информация по классу страхования. Выберите класс и период.'
    form = ClassProfileForm()
    b = g.min_report_date
    e = g.last_report_date
    class_companies = None
    class_companies_len = None
    class_totals = None
    class_info = None
    class_name = None
    img_path_prem = None
    img_path_claim = None
    show_last_year = False
    class_name_l_y = None
    class_companies_l_y = None
    class_info_l_y = None
    class_totals_l_y = None
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
        save_to_log('class_profile',current_user.id)
        b = datetime(b.year,b.month,1)
        e = datetime(e.year,e.month,1)
        show_last_year = form.show_last_year.data
        #аналогичный период прошлого года
        b_l_y = datetime(b.year-1,b.month,1)
        e_l_y = datetime(e.year-1,e.month,1)
        class_id = int(form.insclass.data)
        try:
            class_name, class_companies = get_class_companies(class_id,b,e)#информация по компаниям по выбранному классу
            class_info, class_totals = get_class_info(class_id,b,e)
            if show_last_year == True:
                try:
                    class_name_l_y, class_companies_l_y = get_class_companies(class_id,b_l_y,e_l_y)
                    class_info_l_y, class_totals_l_y = get_class_info(class_id,b_l_y,e_l_y)
                except:
                    flash('Не могу получить данные за прошлый год')
                    return redirect(url_for('class_profile.class_profile'))
        except:
            flash('Не могу получить информацию с сервера. Возможно, данные по выбранному классу за заданный период отсутствуют. Попробуйте задать другой период.')
            return redirect(url_for('class_profile.class_profile'))
        class_companies_len = len(class_companies)
        #базовый путь к графикам
        base_img_path = "/chart_for_class.png/" + form.insclass.data + "/" + b.strftime('%m-%d-%Y') + "/" + e.strftime('%m-%d-%Y')
        img_path_prem = base_img_path + "/prem"
        img_path_claim = base_img_path + "/claim"
    return render_template('class_profile/class_profile.html',title='Информация по продукту',form=form,descr=descr, \
                b=b,e=e,class_companies=class_companies,class_name=class_name, \
                class_companies_len=class_companies_len,img_path_prem=img_path_prem, \
                img_path_claim=img_path_claim,class_info=class_info,class_totals=class_totals ,\
                show_last_year=show_last_year,class_companies_l_y=class_companies_l_y, \
                class_totals_l_y=class_totals_l_y,b_l_y=b_l_y,e_l_y=e_l_y)