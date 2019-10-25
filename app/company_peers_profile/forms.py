from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired
from app.models import Company
from wtforms.fields.html5 import DateField
from flask import flash, g
from datetime import datetime



class CompanyProfileForm(FlaskForm):#портрет компании - выбор компании
    company = SelectField('Выберите компанию',choices = [],validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    show_last_year = BooleanField('Показать данные по сравнению с аналогичным периодом прошлого года')
    show_info_submit = SubmitField('Показать информацию')
    save_to_file_submit = SubmitField('Сохранить в файл')

    def __init__(self, *args, **kwargs):
        super(CompanyProfileForm, self).__init__(*args, **kwargs)
        companies = Company.query.with_entities(Company.id,Company.alias) \
                .filter(Company.nonlife==True).order_by(Company.alias).all()
        sources_db = [(str(a.id), a.alias) for a in companies]
        self.company.choices = sources_db
    

class PeersForm(FlaskForm):#обзор конкурентов
    company = SelectField('Выберите Вашу компанию',choices = [],validators=[DataRequired()])
    peers = SelectMultipleField('Выберите тех, кого считаете конкурентами (удерживайте Ctrl)',choices = [],validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    show_competitors = BooleanField('Показать детали по каждому конкуренту')
    show_info_submit = SubmitField('Показать информацию')
    save_to_file_submit = SubmitField('Сохранить в файл')

    def __init__(self, *args, **kwargs):
        super(PeersForm, self).__init__(*args, **kwargs)
        companies = Company.query.with_entities(Company.id,Company.alias) \
                .filter(Company.nonlife==True).order_by(Company.alias).all()
        sources_db = [(str(a.id), a.alias) for a in companies]
        self.company.choices = sources_db
        self.peers.choices = sources_db