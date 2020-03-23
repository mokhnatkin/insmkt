# helpier function for data extract and transform
import pandas as pd
from app import db
from app.models import Company, Indicator, Financial, \
            Premium, Financial_per_month, \
            Premium_per_month, Claim_per_month, Insclass
from datetime import datetime
from flask import current_app


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


def get_str_month_yyyy_mm(input_date,include_year=True):#получаем в формате гггг-мм исходя из даты
    month_str = str(input_date.month)
    if len(month_str) == 1:
        month_str = '0' + month_str
    if include_year:
        month_name = str(input_date.year) + '-' + month_str#month name like 2019-01
        month_name_p_1y = str(input_date.year+1) + '-' + month_str#month name like 2019-01 (plus 1 year)
    else:
        month_name = month_str#month name like 2019-01
        month_name_p_1y = month_str#month name like 2019-01 (plus 1 year)        
    return month_name, month_name_p_1y


def get_df_prem_or_claim_monthly(class_id,b,e,prem):#get pandas data frame for claims for given class (_id) and period
    months = get_months(b,e)
    df_items = pd.DataFrame()

    for month in months:
        begin = month['begin']
        end = month['end']
        if prem:#premiums
            df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Company)
                            .with_entities(Company.id,Company.alias,Premium_per_month.value)
                            .filter(Premium_per_month.insclass_id == class_id)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
        else:#claims
            df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Company)
                            .with_entities(Company.id,Company.alias,Claim_per_month.value)
                            .filter(Claim_per_month.insclass_id == class_id)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)

        month_name,month_name_p_1y = get_str_month_yyyy_mm(begin)
        df_item_per_month['month_name'] = month_name
        df_items = pd.concat([df_items, df_item_per_month])#append all months

    return df_items



def get_df_prem_or_claim_per_period(class_id,b,e,prem,by_month=False,insform=False):#get pandas data frame for claims for given class (_id) / form and period
    months = get_months(b,e)
    df_items = pd.DataFrame()
    total_value = None
    obligatory = False
    voluntary_personal = False
    voluntary_property = False

    if insform:#prems / claims for ins form
        insforms = current_app.config['INS_FORMS']
        if class_id == insforms[0][0]:#obligatory
            obligatory = True
        elif class_id == insforms[1][0]:#voluntary_personal
            voluntary_personal = True
        elif class_id == insforms[2][0]:#voluntary_property
            voluntary_property = True

    for month in months:
        begin = month['begin']
        end = month['end']
        if prem:#premiums
            if by_month:#group by months
                if obligatory and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Insclass)
                            .with_entities(Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.obligatory == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_personal and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Insclass)
                            .with_entities(Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_personal == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_property and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Insclass)
                            .with_entities(Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_property == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                else:#ins class, not form
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .with_entities(Premium_per_month.value)
                            .filter(Premium_per_month.insclass_id == class_id)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
            else:
                if obligatory and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.obligatory == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_personal and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_personal == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_property and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Premium_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_property == True)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)
                else:#ins class, not form
                    df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                            .join(Company)
                            .with_entities(Company.id,Company.alias,Premium_per_month.value)
                            .filter(Premium_per_month.insclass_id == class_id)
                            .filter(Premium_per_month.beg_date == begin)
                            .filter(Premium_per_month.end_date == end)
                        .statement,db.session.bind)

        else:#claims
            if by_month:
                if obligatory and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Insclass)                    
                            .with_entities(Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.obligatory == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_personal and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Insclass)                    
                            .with_entities(Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_personal == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_property and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Insclass)                    
                            .with_entities(Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_property == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                else:#ins class, not form                
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .with_entities(Claim_per_month.value)
                            .filter(Claim_per_month.insclass_id == class_id)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
            else:
                if obligatory and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.obligatory == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_personal and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_personal == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                elif voluntary_property and insform:
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Company)
                            .join(Insclass)
                            .with_entities(Company.id,Company.alias,Claim_per_month.value)
                            .filter(Insclass.sum_to_totals == True)
                            .filter(Insclass.voluntary_property == True)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
                else:#ins class, not form                
                    df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                            .join(Company)
                            .with_entities(Company.id,Company.alias,Claim_per_month.value)
                            .filter(Claim_per_month.insclass_id == class_id)
                            .filter(Claim_per_month.beg_date == begin)
                            .filter(Claim_per_month.end_date == end)
                        .statement,db.session.bind)
        if by_month:
            month_name,month_name_p_1y = get_str_month_yyyy_mm(begin)
            df_item_per_month['month_name'] = month_name            
            df_item_per_month['month_name_p_1y'] = month_name_p_1y
        df_items = pd.concat([df_items, df_item_per_month])#append all months
    
    if not df_items.empty:
        total_value = df_items['value'].sum()
        if by_month:
            df_items = df_items.groupby(['month_name','month_name_p_1y'], as_index=False).sum()#values by months
            df_items = df_items.sort_values(by='month_name',ascending=True)#sort asc
        else:
            df_items = df_items.groupby(['id','alias'], as_index=False).sum()#values by companies
            df_items = df_items.sort_values(by='value',ascending=False)#sort desc
            df_items['share'] = round(df_items['value']/total_value*100,2)

    return df_items,total_value


def merge_claims_prems_compute_LR(df_items_x,df_items_y,by_month=False,l_y=False):#merge claims and premiums data frames on 'id', compute LR and convert to list (e.g. merged w/ last year if show_last_year)
    df_merged = pd.DataFrame()
    lr_av = None
    if not df_items_x.empty and not df_items_y.empty:
        if by_month:
            df_merged = pd.merge(df_items_x,df_items_y,on='month_name')
            df_merged = df_merged.sort_values(by='month_name',ascending=True)#sort asc
            if l_y:
                df_merged['month_name_join'] = df_merged['month_name_p_1y_y']
            else:
                df_merged['month_name_join'] = df_merged['month_name']
        else:
            df_merged = pd.merge(df_items_x,df_items_y,on='id')
            df_merged = df_merged.sort_values(by='value_y',ascending=False)#sort by prems
        df_merged['lr'] = round(df_merged['value_x']/df_merged['value_y']*100,2)
        lr_av = round(df_items_x['value'].sum() / df_items_y['value'].sum() * 100,2)
    return df_merged, lr_av


def get_df_prem_or_claim_per_period_for_company(company_id,b,e,prem,peers,N_companies):#get pandas data frame for claims for given class (_id) and period
    months = get_months(b,e)
    df_items = pd.DataFrame()
    total_value = None
    
    for month in months:
        begin = month['begin']
        end = month['end']
        if prem:
            df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                        .join(Company)
                        .join(Insclass)
                        .with_entities(Insclass.id,Insclass.alias,Premium_per_month.value)
                        .filter(Premium_per_month.company_id == company_id)
                        .filter(Premium_per_month.beg_date == begin)
                        .filter(Premium_per_month.end_date == end)
                    .statement,db.session.bind)
        else:#claims
            df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                        .join(Company)
                        .join(Insclass)
                        .with_entities(Insclass.id,Insclass.alias,Claim_per_month.value)
                        .filter(Claim_per_month.company_id == company_id)
                        .filter(Claim_per_month.beg_date == begin)
                        .filter(Claim_per_month.end_date == end)
                    .statement,db.session.bind)
        df_items = pd.concat([df_items, df_item_per_month])#append all months    
    if not df_items.empty:
        total_value = df_items['value'].sum()
        df_items = df_items.groupby(['id','alias'], as_index=False).sum()#values by companies
        df_items['share'] = round(df_items['value']/total_value*100,2)    
        if prem:
            df_items.rename(columns = {'value':'premiums', 'share':'premiums_share'}, inplace = True)#rename columns
        else:
            df_items.rename(columns = {'value':'claims', 'share':'claims_share'}, inplace = True)#rename columns

    if peers is not None:#peers are given
        i = 0
        for peer in peers:#for each peer
            df_items_peer = pd.DataFrame()
            for month in months:
                begin = month['begin']
                end = month['end']
                if prem:
                    df_item_per_month_peer = pd.read_sql(db.session.query(Premium_per_month)
                                .join(Insclass)
                                .with_entities(Premium_per_month.insclass_id.label('id'),Premium_per_month.value)
                                .filter(Premium_per_month.company_id == peer)
                                .filter(Premium_per_month.beg_date == begin)
                                .filter(Premium_per_month.end_date == end)
                            .statement,db.session.bind)
                else:#claims
                    df_item_per_month_peer = pd.read_sql(db.session.query(Claim_per_month)
                                .join(Insclass)
                                .with_entities(Claim_per_month.insclass_id.label('id'),Claim_per_month.value)
                                .filter(Claim_per_month.company_id == peer)
                                .filter(Claim_per_month.beg_date == begin)
                                .filter(Claim_per_month.end_date == end)
                            .statement,db.session.bind)
                if df_items_peer.empty:
                    df_items_peer = df_item_per_month_peer
                else:
                    df_items_peer = pd.concat([df_items_peer, df_item_per_month_peer],sort=False)#append all months

            if not df_items_peer.empty:
                df_items_peer = df_items_peer.groupby(['id'], as_index=False).sum()#values by companies
                if prem:
                    df_items_peer.rename(columns = {'value':'premiums'+str(i)}, inplace = True)#rename columns
                else:
                    df_items_peer.rename(columns = {'value':'claims'+str(i)}, inplace = True)#rename columns
            df_items = pd.merge(df_items,df_items_peer,on='id',how='outer')
            i += 1

    return df_items,total_value


def merge_claims_prems_compute_LR_for_company(df_items_x,df_items_y,N_companies):#merge claims and premiums data frames on 'id', compute LR and convert to list (e.g. merged w/ last year if show_last_year)
    df_merged = pd.DataFrame()
    lr_av = None
    if not df_items_x.empty and not df_items_y.empty:
        df_merged = pd.merge(df_items_x,df_items_y,on='id')
        df_merged['lr'] = round(df_merged['claims'] / df_merged['premiums'] * 100,2)
        lr_av = round(df_items_x['claims'].sum() / df_items_y['premiums'].sum() * 100,2)
        df_merged = df_merged.drop(['alias_y'], axis=1)#drop columns
        df_merged.rename(columns = {'alias_x':'alias'}, inplace = True)#rename columns
        df_merged = df_merged.sort_values(by='premiums',ascending=False)#sort desc
    if N_companies is not None and N_companies>0:#peers are given        
        for i in range(N_companies):
            df_merged['lr'+str(i)] = round(df_merged['claims'+str(i)] / df_merged['premiums'+str(i)] * 100,2)
    return df_merged, lr_av


def get_df_financial_per_period(ind_name,b,e):#get pandas data frame for given indicator (ind_name) and period
    df_items = pd.DataFrame()
    total_value = None
    ind_id = Indicator.query.filter(Indicator.name == ind_name).first()
    _id = ind_id.id
    months = get_months(b,e)

    for month in months:
        begin = month['begin']
        end = month['end']
        df_item_per_month = pd.read_sql(db.session.query(Financial_per_month)
                    .join(Company)
                    .with_entities(Company.id,Company.alias,Financial_per_month.value)
                    .filter(Financial_per_month.indicator_id == _id)
                    .filter(Financial_per_month.beg_date == begin)
                    .filter(Financial_per_month.end_date == end)
                    .filter(Company.nonlife == True)
                .statement,db.session.bind)
        df_items = pd.concat([df_items, df_item_per_month])#append all months
    if not df_items.empty:
        df_items = df_items.groupby(['id','alias'], as_index=False).sum()#values by companies
        df_items = df_items.sort_values(by='value',ascending=False)#sort desc
        total_value = df_items['value'].sum()
        df_items['share'] = round(df_items['value']/total_value*100,2)
    return df_items,total_value


def get_df_financial_at_date(ind_name,e):#get pandas data frame for given indicator (ind_name) and date
    df_items = pd.DataFrame()
    total_value = None
    ind_id = Indicator.query.filter(Indicator.name == ind_name).first()
    _id = ind_id.id    
    df_items = pd.read_sql(db.session.query(Financial)
                    .join(Company)
                    .with_entities(Company.id,Company.alias,Financial.value)
                    .filter(Financial.indicator_id == _id)
                    .filter(Financial.report_date == e)
                    .filter(Company.nonlife == True)
                .statement,db.session.bind)
    if not df_items.empty:
        df_items = df_items.sort_values(by='value',ascending=False)#sort desc
        total_value = df_items['value'].sum()
        df_items['share'] = round(df_items['value']/total_value*100,2)
    return df_items,total_value


def get_df_financial_per_period_for_company(balance,company_id,ind_name,b,e,include_year=True):#get pandas data frame for given indicator (ind_name) and date
    ind_id = Indicator.query.filter(Indicator.name == ind_name).first()
    _id = ind_id.id
    months = get_months(b,e)
    df_items = pd.DataFrame()
    
    for month in months:
        begin = month['begin']
        end = month['end']
        if balance:#balance indicator
            df_item_per_month = pd.read_sql(db.session.query(Financial)
                                    .join(Company)
                                    .with_entities(Financial.value)
                                    .filter(Financial.indicator_id == _id)
                                    .filter(Financial.company_id == company_id)
                                    .filter(Financial.report_date == end)
                                .statement,db.session.bind)
        else:#flow
            df_item_per_month = pd.read_sql(db.session.query(Financial_per_month)
                                    .join(Company)
                                    .with_entities(Financial_per_month.value)
                                    .filter(Financial_per_month.indicator_id == _id)
                                    .filter(Financial_per_month.company_id == company_id)
                                    .filter(Financial_per_month.beg_date == begin)
                                    .filter(Financial_per_month.end_date == end)                                    
                .statement,db.session.bind)
        month_name,month_name_p_1y = get_str_month_yyyy_mm(begin,include_year)
        df_item_per_month['month_name'] = month_name
        df_items = pd.concat([df_items, df_item_per_month])#append all months
    
    if not df_items.empty:
        df_items = df_items.groupby(['month_name'], as_index=False).sum()#values by months
        df_items = df_items.sort_values(by='month_name',ascending=True)#sort asc
    
    return df_items    


def convert_df_to_list(df_items,LR_to_list=False,claim_prem=False,by_month=False):#convert data frame to list; data frame should be sorted to get correct row_index
    output_list = list()
    i = 0
    if not df_items.empty:
        for row_index,row in df_items.iterrows():
            if LR_to_list:#loss ratio
                output_list.append({'row_index':i,'alias':row.alias_x,'lr':row.lr})
            elif claim_prem and not by_month:#claims, premiums, LR
                if row.value_y != 0 or row.value_x != 0:#premiums or claims not eq. to 0
                    output_list.append({'row_index':i,'alias':row.alias_x,'premium':row.value_y,'claim':row.value_x,
                                        'claim_share':row.share_x,'prem_share':row.share_y,'lr':row.lr})
            elif by_month:
                output_list.append({'month_name':row.month_name,'premium':row.value_y,'claim':row.value_x,'lr':row.lr})
            else:#other indicators
                output_list.append({'row_index':i,'alias':row.alias,'value':row.value,'share':row.share})
            i += 1
    return output_list


def merge_two_df_convert_to_list(df_items_x,df_items_y,relative=False,LR_two_df=False,claim_prem=False,by_month=False):#merge two data frames on 'id' and convert to list (e.g. merged w/ last year if show_last_year)
    output_list = list()
    if not df_items_x.empty and not df_items_y.empty:
        if by_month:
            df_merged = pd.merge(df_items_x,df_items_y,on='month_name_join')
        else:
            df_merged = pd.merge(df_items_x,df_items_y,on='id')
        if not claim_prem and relative and not LR_two_df:
            df_merged['change'] = round(df_merged['value_x']-df_merged['value_y'],2)
        elif not claim_prem and not relative:
            df_merged['change'] = round((df_merged['value_x']-df_merged['value_y'])/df_merged['value_y']*100,2)
        elif LR_two_df:
            df_merged['change'] = round(df_merged['lr_x']-df_merged['lr_y'],2)
        elif claim_prem:
            df_merged['prem_change'] = round((df_merged['value_y_x']-df_merged['value_y_y'])/df_merged['value_y_y']*100,2)
            df_merged['claim_change'] = round((df_merged['value_x_x']-df_merged['value_x_y'])/df_merged['value_x_y']*100,2)
            df_merged['lr_change'] = round(df_merged['lr_x']-df_merged['lr_y'],2)
        i = 0
        for row_index,row in df_merged.iterrows():
            if LR_two_df:#LR for 2 periods
                output_list.append({'row_index':i,'alias':row.alias_x_x,'lr':row.lr_x,'lr_l_y':row.lr_y,'change':row.change})
            elif claim_prem and not by_month:#claims, prems, two periods
                if row.value_y_x != 0 or row.value_y_y != 0 or row.value_x_x != 0 or row.value_x_y != 0:#premiums or claims not eq. to 0
                    output_list.append({'row_index':i,'alias':row.alias_x_x,'premium':row.value_y_x,'premium_l_y':row.value_y_y,
                                'claim':row.value_x_x,'claim_l_y':row.value_x_y,'prem_share':row.share_y_x,'prem_share_l_y':row.share_y_y,
                                'claim_share':row.share_x_x,'claim_share_l_y':row.share_x_y,'lr':row.lr_x,'lr_l_y':row.lr_y,
                                'prem_change':row.prem_change,'claim_change':row.claim_change,'lr_change':row.lr_change})
            elif claim_prem and by_month:#claims, prems, two periods by months
                output_list.append({'month_name':row.month_name_x,'premium':row.value_y_x,'premium_l_y':row.value_y_y,
                                'claim':row.value_x_x,'claim_l_y':row.value_x_y,'lr':row.lr_x,'lr_l_y':row.lr_y,
                                'prem_change':row.prem_change,'claim_change':row.claim_change,'lr_change':row.lr_change})            
            else:#other indicators
                output_list.append({'row_index':i,'alias':row.alias_x,'value':row.value_x,'share':row.share_x,
                            'value_l_y':row.value_y,'share_l_y':row.share_y,'change':row.change})
            i += 1
    return output_list


def get_df_indicators(balance,b,e,company_id,peers,N_companies):#get balance / flow indicators for given company / mkt
    df_indicators = pd.DataFrame()
    df_indicators_mkt = pd.DataFrame()
    
    if balance:        
        df_indicators_company = pd.read_sql(db.session.query(Financial)#indicators for selected company
                        .join(Company)
                        .join(Indicator)
                        .with_entities(Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Financial.value)
                        .filter(Indicator.flow == False)
                        .filter(Financial.report_date == e)
                        .filter(Financial.company_id == company_id)
                    .statement,db.session.bind)        
        if peers is None:
            df_indicators_mkt = pd.read_sql(db.session.query(Financial)#balance indicators for all non-life companies except for selected
                        .join(Company)
                        .join(Indicator)
                        .with_entities(Company.id.label('company_id'),Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Financial.value)
                        .filter(Indicator.flow == False)
                        .filter(Financial.report_date == e)
                        .filter(Company.nonlife == True)
                    .statement,db.session.bind)
            #df_indicators_mkt.rename(columns = {'value':'total'}, inplace = True)
        else:#peers are given            
            df_indicators_peers = pd.DataFrame()
            i = 0
            for peer in peers:
                df_indicators_peer = pd.read_sql(db.session.query(Financial)#indicators for selected company
                        .join(Company)
                        .join(Indicator)
                        .with_entities(Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Company.id.label('company_id'),Financial.value)
                        .filter(Indicator.flow == False)
                        .filter(Financial.report_date == e)
                        .filter(Financial.company_id == peer)
                    .statement,db.session.bind)
                df_indicators_mkt = pd.concat([df_indicators_mkt, df_indicators_peer])#append all peers
                if df_indicators_peers.empty:#1st peer
                    df_indicators_peers = df_indicators_peer
                    df_indicators_peers.rename(columns = {'value':'value0'}, inplace = True)#rename columns
                else:#2nd peer and later
                    df_indicators_peers = pd.merge(df_indicators_peers,df_indicators_peer,on='id')
                    if i == 1:
                        df_indicators_peers = df_indicators_peers.drop(['system_name_y', 'fullname_y','company_id_x','company_id_y'], axis=1)#drop columns
                        df_indicators_peers.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname','value':'value1'}, inplace = True)#rename columns                        
                    elif i > 1:
                        df_indicators_peers = df_indicators_peers.drop(['system_name_y', 'fullname_y','company_id'], axis=1)#drop columns
                        df_indicators_peers.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname','value':'value'+str(i)}, inplace = True)#rename columns
                i += 1

    else:#flow
        months = get_months(b,e)
        df_indicators_company = pd.DataFrame()
        for month in months:#for company
            begin = month['begin']
            end = month['end']
            df_indicators_company_per_month = pd.read_sql(db.session.query(Financial_per_month)#indicators for selected company
                            .join(Company)
                            .join(Indicator)
                            .with_entities(Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Financial_per_month.value)
                            .filter(Indicator.flow == True)
                            .filter(Financial_per_month.beg_date == begin)
                            .filter(Financial_per_month.end_date == end)
                            .filter(Financial_per_month.company_id == company_id)
                        .statement,db.session.bind)
            df_indicators_company = pd.concat([df_indicators_company, df_indicators_company_per_month])#append all months            
        df_indicators_company = df_indicators_company.groupby(['id','system_name','fullname'], as_index=False).sum()#group by
        if peers is None:#for whole mkt
            for month in months:
                begin = month['begin']
                end = month['end']
                df_indicators_mkt_per_month = pd.read_sql(db.session.query(Financial_per_month)#flow indicators for all non-life companies except for selected
                                .join(Company)
                                .join(Indicator)
                                .with_entities(Company.id.label('company_id'),Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Financial_per_month.value)
                                .filter(Indicator.flow == True)
                                .filter(Financial_per_month.beg_date == begin)
                                .filter(Financial_per_month.end_date == end)
                                .filter(Company.nonlife == True)
                            .statement,db.session.bind)
                df_indicators_mkt = pd.concat([df_indicators_mkt, df_indicators_mkt_per_month])#append all months
            
        else:#peers are given
            df_indicators_peers = pd.DataFrame()
            i = 0
            for peer in peers:
                df_indicators_peer = pd.DataFrame()
                for month in months:#for each peer
                    begin = month['begin']
                    end = month['end']
                    df_indicators_peer_per_month = pd.read_sql(db.session.query(Financial_per_month)#indicators for selected company
                                    .join(Company)
                                    .join(Indicator)
                                    .with_entities(Company.id.label('company_id'),Indicator.id,Indicator.name.label('system_name'),Indicator.fullname,Financial_per_month.value)
                                    .filter(Indicator.flow == True)
                                    .filter(Financial_per_month.beg_date == begin)
                                    .filter(Financial_per_month.end_date == end)
                                    .filter(Financial_per_month.company_id == peer)
                                .statement,db.session.bind)
                    df_indicators_peer = pd.concat([df_indicators_peer, df_indicators_peer_per_month])#append all months            
                df_indicators_peer = df_indicators_peer.groupby(['id','system_name','fullname','company_id'], as_index=False).sum()#group by
                df_indicators_mkt = pd.concat([df_indicators_mkt, df_indicators_peer])#append all peers                
                if df_indicators_peers.empty:#1st peer
                    df_indicators_peers = df_indicators_peer
                    df_indicators_peers.rename(columns = {'value':'value0'}, inplace = True)#rename columns
                else:#2nd peer and later
                    df_indicators_peers = pd.merge(df_indicators_peers,df_indicators_peer,on='id')
                    if i == 1:
                        df_indicators_peers = df_indicators_peers.drop(['system_name_y', 'fullname_y','company_id_x','company_id_y'], axis=1)#drop columns
                        df_indicators_peers.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname','value':'value1'}, inplace = True)#rename columns                        
                    elif i > 1:
                        df_indicators_peers = df_indicators_peers.drop(['system_name_y', 'fullname_y','company_id'], axis=1)#drop columns
                        df_indicators_peers.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname','value':'value'+str(i)}, inplace = True)#rename columns                        
                i += 1

    if not df_indicators_mkt.empty and peers is None:
        df_indicators_mkt = df_indicators_mkt.groupby(['id','system_name','fullname','company_id'], as_index=False).sum()#group by
        df_indicators_mkt.rename(columns = {'value':'total'}, inplace = True)
    elif not df_indicators_mkt.empty and peers is not None and not df_indicators_peers.empty:        
        df_indicators_mkt = df_indicators_mkt.groupby(['id','system_name','fullname'], as_index=False).sum()#group by
        df_indicators_mkt.rename(columns = {'value':'total'}, inplace = True)
        df_indicators_mkt = pd.merge(df_indicators_mkt,df_indicators_peers,on='id')
        df_indicators_mkt = df_indicators_mkt.drop(['system_name_y', 'fullname_y'], axis=1)#drop columns
        df_indicators_mkt.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname'}, inplace = True)#rename columns                

    if not df_indicators_mkt.empty:#compute N companies
        if N_companies is None:
            c_N_b = df_indicators_mkt.company_id.nunique()#no. of companies in data frame
        else:
            c_N_b = N_companies
        df_indicators_mkt = df_indicators_mkt.groupby(['id','system_name','fullname'], as_index=False).sum()#group by indicators

    if not df_indicators_company.empty and not df_indicators_mkt.empty:
        df_indicators = pd.merge(df_indicators_company,df_indicators_mkt,on='id')
        if peers is None:#for whole mkt
            df_indicators = df_indicators.drop(['system_name_y', 'fullname_y','company_id'], axis=1)#drop columns
        else:
            df_indicators = df_indicators.drop(['system_name_y', 'fullname_y'], axis=1)#drop columns
        df_indicators.rename(columns = {'system_name_x':'system_name', 'fullname_x':'fullname','value_x':'value'}, inplace = True)#rename columns
        df_indicators['mkt_av'] = df_indicators['total'] / c_N_b        
        df_indicators['share'] = round(df_indicators['value'] / df_indicators['total'] * 100,2)
    
    return df_indicators


def compute_round_coef(input1,input2,N,TN,roundN,is_positive):#вспомогат.ф-ция
    try:
        coef = round(input1 / input2 / N * TN * 100,roundN)
    except:
        coef = 'N.A.'
    if is_positive:
        if coef < 0:
            coef = 'N.A.'
    return coef


def compute_round_change(input1,input2,roundN):#вспомогат.ф-ция
    try:
        change = round((input1-input2)/input1*100,roundN)
    except:
        change = 'N.A.'
    return change    


def compute_other_financial_indicators(df_balance_indicators,df_flow_indicators,N,N_companies):#compute other fin indicators for company profile and peer review
    output = list()
    peers_templ = list()
    peers_ind_all = list()
    if N_companies is not None and N_companies > 0:
        peers = True
    else:
        peers = False

    if not df_balance_indicators.empty and not df_flow_indicators.empty:
        net_income_c = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_income', 'value'].iloc[0]#net income for given company
        net_income_m = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_income', 'total'].iloc[0]#net income for mkt
        net_premiums_c = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_premiums', 'value'].iloc[0]
        net_premiums_m = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_premiums', 'total'].iloc[0]
        net_claims_c = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_claims', 'value'].iloc[0]
        net_claims_m = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_claims', 'total'].iloc[0]
        premiums_c = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'premiums', 'value'].iloc[0]
        premiums_m = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'premiums', 'total'].iloc[0]
        claims_c = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'claims', 'value'].iloc[0]
        claims_m = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'claims', 'total'].iloc[0]
        equity_c = df_balance_indicators.loc[df_balance_indicators['system_name'] == 'equity', 'value'].iloc[0]
        equity_m = df_balance_indicators.loc[df_balance_indicators['system_name'] == 'equity', 'total'].iloc[0]

        if peers:#peers are given
            peers_values = list()
            for c in range(N_companies):
                net_income_peer = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_income', 'value'+str(c)].iloc[0]#net income for given company
                net_premiums_peer = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_premiums', 'value'+str(c)].iloc[0]
                net_claims_peer = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'net_claims', 'value'+str(c)].iloc[0]
                premiums_peer = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'premiums', 'value'+str(c)].iloc[0]
                claims_peer = df_flow_indicators.loc[df_flow_indicators['system_name'] == 'claims', 'value'+str(c)].iloc[0]
                equity_peer = df_balance_indicators.loc[df_balance_indicators['system_name'] == 'equity', 'value'+str(c)].iloc[0]
                peers_values.append({'net_income':net_income_peer,'net_premiums':net_premiums_peer,'net_claims':net_claims_peer,
                                'premiums':premiums_peer,'claims':claims_peer,'equity':equity_peer})

        #start computing indicators
        #ROE
        name = 'ROE годовой %'
        ind_id = 'roe'
        value_c = compute_round_coef(net_income_c,equity_c,N,12,1,True)
        value_m = compute_round_coef(net_income_m,equity_m,N,12,1,True)
        output.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers':peers_templ})
        if peers:
            peers_ind = list()
            for c in range(N_companies):
                value_p = compute_round_coef(peers_values[c]['net_income'],peers_values[c]['equity'],N,12,1,True)
                peers_ind.append(value_p)
            peers_ind_all.append(peers_ind)

        #Equity usage
        name = 'Использование капитала'
        ind_id = 'equity_usage'
        value_c = compute_round_coef(net_premiums_c,equity_c,N*100,12,2,True)
        value_m = compute_round_coef(net_premiums_m,equity_m,N*100,12,2,True)
        output.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers':peers_templ})
        if peers:
            peers_ind = list()
            for c in range(N_companies):
                value_p = compute_round_coef(peers_values[c]['net_premiums'],peers_values[c]['equity'],N*100,12,2,True)
                peers_ind.append(value_p)
            peers_ind_all.append(peers_ind)
        #net loss ratio
        name = 'Коэффициент выплат, нетто %'
        ind_id = 'LR_coef_net'
        value_c = compute_round_coef(net_claims_c,net_premiums_c,1,1,1,False)
        value_m = compute_round_coef(net_claims_m,net_premiums_m,1,1,1,False)
        output.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers':peers_templ})
        if peers:
            peers_ind = list()
            for c in range(N_companies):
                value_p = compute_round_coef(peers_values[c]['net_claims'],peers_values[c]['net_premiums'],1,1,1,False)
                peers_ind.append(value_p)
            peers_ind_all.append(peers_ind)
        #re share premiums
        name = 'Доля перестрахования в премиях, %'
        ind_id = 'RE_prem'
        value_c = compute_round_change(premiums_c,net_premiums_c,1)
        value_m = compute_round_change(premiums_m,net_premiums_m,1)
        output.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers':peers_templ})
        if peers:
            peers_ind = list()
            for c in range(N_companies):
                value_p = compute_round_change(peers_values[c]['premiums'],peers_values[c]['net_premiums'],1)
                peers_ind.append(value_p)
            peers_ind_all.append(peers_ind)
        #re share claims
        name = 'Доля перестрахования в выплатах, %'
        ind_id = 'RE_claim'
        value_c = compute_round_change(claims_c,net_claims_c,1)
        value_m = compute_round_change(claims_m,net_claims_m,1)
        output.append({'ind_id':ind_id,'name':name,'value_c':value_c,'value_m':value_m,'peers':peers_templ})
        if peers:
            peers_ind = list()
            for c in range(N_companies):
                value_p = compute_round_change(peers_values[c]['claims'],peers_values[c]['net_claims'],1)
                peers_ind.append(value_p)
            peers_ind_all.append(peers_ind)
            
        if peers:
            i = 0
            for el in output:
                el['peers'] = peers_ind_all[i]
                i+= 1
    
    return output

