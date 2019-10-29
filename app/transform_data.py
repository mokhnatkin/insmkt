# helpier function for data extract and transform
import pandas as pd
from app import db
from app.models import Company, Indicator, Financial, \
            Premium, Financial_per_month, \
            Premium_per_month, Claim_per_month
from datetime import datetime



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


def get_df_prem_or_claim_per_period(class_id,b,e,prem,by_month=False):#get pandas data frame for claims for given class (_id) and period
    months = get_months(b,e)
    df_items = pd.DataFrame()
    for month in months:
        begin = month['begin']
        end = month['end']
        if prem:
            if by_month:
                df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)                        
                        .with_entities(Premium_per_month.value)
                        .filter(Premium_per_month.insclass_id == class_id)
                        .filter(Premium_per_month.beg_date == begin)
                        .filter(Premium_per_month.end_date == end)
                    .statement,db.session.bind)                
            else:
                df_item_per_month = pd.read_sql(db.session.query(Premium_per_month)
                        .join(Company)
                        .with_entities(Company.id,Company.alias,Premium_per_month.value)
                        .filter(Premium_per_month.insclass_id == class_id)
                        .filter(Premium_per_month.beg_date == begin)
                        .filter(Premium_per_month.end_date == end)
                    .statement,db.session.bind)
        else:#claims
            if by_month:
                df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                        .with_entities(Claim_per_month.value)
                        .filter(Claim_per_month.insclass_id == class_id)
                        .filter(Claim_per_month.beg_date == begin)
                        .filter(Claim_per_month.end_date == end)
                    .statement,db.session.bind)
            else:
                df_item_per_month = pd.read_sql(db.session.query(Claim_per_month)
                        .join(Company)
                        .with_entities(Company.id,Company.alias,Claim_per_month.value)
                        .filter(Claim_per_month.insclass_id == class_id)
                        .filter(Claim_per_month.beg_date == begin)
                        .filter(Claim_per_month.end_date == end)
                    .statement,db.session.bind)
        if by_month:
            month_str = str(begin.month)
            if len(month_str) == 1:
                month_str = '0' + month_str
            month_name = str(begin.year) + '-' + month_str#month name like 2019-01
            month_name_p_1y = str(begin.year+1) + '-' + month_str#month name like 2019-01 (plus 1 year)
            df_item_per_month['month_name'] = month_name            
            df_item_per_month['month_name_p_1y'] = month_name_p_1y
        df_items = pd.concat([df_items, df_item_per_month])#append all months
    
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


def get_df_financial_per_period(ind_name,b,e):#get pandas data frame for given indicator (ind_name) and period    
    ind_id = Indicator.query.filter(Indicator.name == ind_name).first()
    _id = ind_id.id
    months = get_months(b,e)
    df_items = pd.DataFrame()
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
    df_items = df_items.groupby(['id','alias'], as_index=False).sum()#values by companies
    df_items = df_items.sort_values(by='value',ascending=False)#sort desc
    total_value = df_items['value'].sum()
    df_items['share'] = round(df_items['value']/total_value*100,2)
    return df_items,total_value


def get_df_financial_at_date(ind_name,e):#get pandas data frame for given indicator (ind_name) and date
    ind_id = Indicator.query.filter(Indicator.name == ind_name).first()
    _id = ind_id.id    
    df_items = pd.read_sql(db.session.query(Financial)
                    .join(Company)
                    .with_entities(Company.id,Company.alias,Financial.value)
                    .filter(Financial.indicator_id == _id)
                    .filter(Financial.report_date == e)                    
                    .filter(Company.nonlife == True)
                .statement,db.session.bind)    
    df_items = df_items.sort_values(by='value',ascending=False)#sort desc
    total_value = df_items['value'].sum()
    df_items['share'] = round(df_items['value']/total_value*100,2)
    return df_items,total_value


def convert_df_to_list(df_items,LR_to_list=False,claim_prem=False,by_month=False):#convert data frame to list; data frame should be sorted to get correct row_index
    output_list = list()
    i = 0
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

