from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
                    TextAreaField, FileField, SelectField, DateTimeField, \
                    SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from app.models import User, Company, Insclass
from wtforms.fields.html5 import DateField
from flask import flash, g
from datetime import datetime


class LoginForm(FlaskForm):#вход
    username = StringField('Логин',validators=[DataRequired()])
    password = PasswordField('Пароль',validators=[DataRequired()])
    remember_me = BooleanField('Запомни меня')
    submit = SubmitField('Вход')


class RegistrationForm(FlaskForm):#зарегистрироваться
    username = StringField('Логин',validators=[DataRequired()])
    email = StringField('E-mail',validators=[DataRequired(), Email()])
    password = PasswordField('Пароль',validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль',validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self,username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким логином уже зарегистрирован.')

    def validate_email(self,email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким e-mail адресом уже зарегистрирован.')


class PostForm(FlaskForm):#опубликовать пост
    post = TextAreaField('Ваш пост:',validators=[DataRequired(), Length(min=1,max=500)])
    submit = SubmitField('Опубликовать')


class DictUploadForm(FlaskForm):#загрузить справочник компаний   
    dict_types = [('CompaniesList','Список компаний'), ('ClassesList','Список классов'),('IndicatorsList','Список показателей')]#типы справочников
    name = StringField('Описание',validators=[DataRequired()])
    dict_type = SelectField('Тип справочника',choices = dict_types,validators=[DataRequired()])
    file = FileField('Выберите файл для загрузки',validators=[DataRequired()])
    submit = SubmitField('Загрузить')

        
class DataUploadForm(FlaskForm):#загрузить справочник компаний    
    data_types = [('Premiums','Страховые премии'), ('Claims','Страховые выплаты'),('Financials','Основные финансовые показатели'),('Prudentials','Пруденциальные нормативы')]#типы данных
    name = StringField('Описание',validators=[DataRequired()])
    data_type = SelectField('Тип данных',choices = data_types,validators=[DataRequired()])
    report_date = DateTimeField('Отчетная дата (в формате дд.мм.гггг)',format='%d.%m.%Y',validators=[DataRequired()])
    file = FileField('Выберите файл для загрузки',validators=[DataRequired()])
    frst_row = IntegerField('Укажите номер первой строки с данными по компаниям',validators=[DataRequired()])
    submit = SubmitField('Загрузить')


class ComputePerMonthIndicators(FlaskForm):#рассчитать показатели, премии, выплаты за месяц
    data_types = [('Premiums','Страховые премии'), ('Claims','Страховые выплаты'),('Financials','Основные финансовые показатели')]#типы данных
    data_type = SelectField('Тип данных',choices = data_types)
    begin_date = DateTimeField('Начало (в формате дд.мм.гггг)',format='%d.%m.%Y',validators=[DataRequired()])
    end_date = DateTimeField('Конец (в формате дд.мм.гггг)',format='%d.%m.%Y',validators=[DataRequired()])
    submit = SubmitField('Рассчитать')
    def validate(self):#дата окончания должна быть больше даты начала
        if self.begin_date.data > self.end_date.data:
            flash('Дата окончания должна быть больше даты начала')
            return False
        else:
            return True


class CompanyProfileForm(FlaskForm):#портрет компании - выбор компании
    companies = Company.query.with_entities(Company.id,Company.alias) \
        .filter(Company.nonlife==True).order_by(Company.alias).all()
    companies_str = list()
    for c in companies:
        c_id = str(c[0])
        companies_str.append((c_id,c[1]))
    company = SelectField('Выберите компанию',choices = companies_str,validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    submit = SubmitField('Показать портрет')
    def validate(self):#дата окончания должна быть больше даты начала
        d_beg = datetime(self.begin_d.data.year,self.begin_d.data.month,self.begin_d.data.day)
        d_end = datetime(self.end_d.data.year,self.end_d.data.month,self.end_d.data.day)
        if self.begin_d.data > self.end_d.data:
            flash('Дата окончания должна быть больше даты начала')
            return False
        elif d_beg < g.min_report_date or d_end > g.last_report_date:
            #b.strftime('%m-%d-%Y')
            err_txt='Данные за запрошенный период отсутствуют. Выберите любой период в диапазоне с ' \
                + g.min_report_date.strftime('%d.%m.%Y') + ' по ' \
                    + g.last_report_date.strftime('%d.%m.%Y')
            flash(err_txt)
            return False
        else:
            return True


class ClassProfileForm(FlaskForm):#информация по продукту
    insclasses = Insclass.query.with_entities(Insclass.id,Insclass.alias) \
                .filter(Insclass.nonlife == 1) \
                .order_by(Insclass.obligatory.desc()) \
                .order_by(Insclass.voluntary_property.desc()) \
                .order_by(Insclass.voluntary_personal.desc()).all()
    insclasses_str = list()
    for c in insclasses:
        c_id = str(c[0])
        insclasses_str.append((c_id,c[1]))
    insclass = SelectField('Выберите класс страхования',choices = insclasses_str,validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])    
    submit = SubmitField('Показать информацию')
    def validate(self):#дата окончания должна быть больше даты начала
        d_beg = datetime(self.begin_d.data.year,self.begin_d.data.month,self.begin_d.data.day)
        d_end = datetime(self.end_d.data.year,self.end_d.data.month,self.end_d.data.day)
        if self.begin_d.data > self.end_d.data:
            flash('Дата окончания должна быть больше даты начала')
            return False
        elif d_beg < g.min_report_date or d_end > g.last_report_date:            
            err_txt='Данные за запрошенный период отсутствуют. Выберите любой период в диапазоне с ' \
                + g.min_report_date.strftime('%d.%m.%Y') + ' по ' \
                    + g.last_report_date.strftime('%d.%m.%Y')
            flash(err_txt)
            return False
        else:
            return True    


class PeersForm(FlaskForm):#обзор конкурентов
    companies = Company.query.with_entities(Company.id,Company.alias).filter(Company.nonlife==True).all()
    companies_str = list()
    for c in companies:
        c_id = str(c[0])
        companies_str.append((c_id,c[1]))
    company = SelectField('Выберите Вашу компанию',choices = companies_str,validators=[DataRequired()])
    peers = SelectMultipleField('Выберите тех, кого считаете конкурентами (удерживайте Ctrl)',choices = companies_str,validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    submit = SubmitField('Сравнить с конкурентами')
    def validate(self):#дата окончания должна быть больше даты начала
        d_beg = datetime(self.begin_d.data.year,self.begin_d.data.month,self.begin_d.data.day)
        d_end = datetime(self.end_d.data.year,self.end_d.data.month,self.end_d.data.day)
        if self.begin_d.data > self.end_d.data:
            flash('Дата окончания должна быть больше даты начала')
            return False
        elif d_beg < g.min_report_date or d_end > g.last_report_date:            
            err_txt='Данные за запрошенный период отсутствуют. Выберите любой период в диапазоне с ' \
                + g.min_report_date.strftime('%d.%m.%Y') + ' по ' \
                    + g.last_report_date.strftime('%d.%m.%Y')
            flash(err_txt)
            return False
        else:
            return True


class RankingForm(FlaskForm):#ранкинг    
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    submit = SubmitField('Показать')
    def validate(self):#дата окончания должна быть больше даты начала
        d_beg = datetime(self.begin_d.data.year,self.begin_d.data.month,self.begin_d.data.day)
        d_end = datetime(self.end_d.data.year,self.end_d.data.month,self.end_d.data.day)
        if self.begin_d.data > self.end_d.data:
            flash('Дата окончания должна быть больше даты начала')
            return False
        elif d_beg < g.min_report_date or d_end > g.last_report_date:
            #b.strftime('%m-%d-%Y')
            err_txt='Данные за запрошенный период отсутствуют. Выберите любой период в диапазоне с ' \
                + g.min_report_date.strftime('%d.%m.%Y') + ' по ' \
                    + g.last_report_date.strftime('%d.%m.%Y')
            flash(err_txt)
            return False
        else:
            return True


class DictSelectForm(FlaskForm):#выбор типа справочника для просмотра значений
    dict_types = [('CompaniesList','Список компаний'), ('ClassesList','Список классов'),('IndicatorsList','Список показателей')]#типы справочников    
    dict_type = SelectField('Тип справочника',choices = dict_types,validators=[DataRequired()])    
    submit = SubmitField('Показать')


class AddNewCompanyName(FlaskForm):#добавление нового названия компании
    name = StringField('Название',validators=[DataRequired()])
    submit = SubmitField('Добавить')
