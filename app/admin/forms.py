from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, \
                    FileField, SelectField, DateTimeField, TextAreaField, \
                    BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from app.models import User
from wtforms.fields.html5 import DateField
from flask import flash, g, current_app
from datetime import datetime


class EditUserForm(FlaskForm):#изменить пользователя
    username = StringField('Логин',validators=[DataRequired()])
    email = StringField('E-mail',validators=[DataRequired(), Email()])
    send_emails = BooleanField('Отправлять e-mail рассылки?')
    submit = SubmitField('Изменить')


class ChangeRoleForm(FlaskForm):#дать админский / пользовательский доступ
    submit = SubmitField('Подтвердить')


class DictUploadForm(FlaskForm):#загрузить справочник компаний
    dict_types = current_app.config['DICT_TYPES']    
    name = StringField('Описание',validators=[DataRequired()])
    dict_type = SelectField('Тип справочника',choices = dict_types,validators=[DataRequired()])
    file = FileField('Выберите файл для загрузки',validators=[DataRequired()])
    submit = SubmitField('Загрузить')

        
class DataUploadForm(FlaskForm):#загрузить справочник компаний
    data_types = current_app.config['DATA_TYPES']
    name = StringField('Описание',validators=[DataRequired()])
    data_type = SelectField('Тип данных',choices = data_types,validators=[DataRequired()])
    report_date = DateTimeField('Отчетная дата (в формате дд.мм.гггг)',format='%d.%m.%Y',validators=[DataRequired()])
    file = FileField('Выберите файл для загрузки',validators=[DataRequired()])
    frst_row = IntegerField('Укажите номер первой строки с данными по компаниям',validators=[DataRequired()])
    others_col_1 = IntegerField('При загрузке премий и выплат: Укажите номер столбца для иных классов, добровольное личное страхование')
    others_col_2 = IntegerField('При загрузке премий и выплат: Укажите номер столбца для иных классов, добровольное имущественное страхование')
    others_col_3 = IntegerField('При загрузке премий и выплат: Укажите номер столбца для иных классов, обязательное страхование')
    submit = SubmitField('Загрузить')


class ComputePerMonthIndicators(FlaskForm):#рассчитать показатели, премии, выплаты за месяц
    data_types = current_app.config['DATA_TYPES']
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


class DictSelectForm(FlaskForm):#выбор типа справочника для просмотра значений
    dict_types = current_app.config['DICT_TYPES']
    dict_type = SelectField('Тип справочника',choices = dict_types,validators=[DataRequired()])    
    submit = SubmitField('Показать')


class AddNewCompanyName(FlaskForm):#добавление нового названия компании
    name = StringField('Название',validators=[DataRequired()])
    submit = SubmitField('Добавить / изменить')


class AddNewClassName(FlaskForm):#добавление нового названия класса
    name = StringField('Название',validators=[DataRequired()])
    fullname = StringField('Полное название (из файлов НБ)',validators=[DataRequired()])
    submit = SubmitField('Добавить / изменить')


class AddEditCompanyForm(FlaskForm):#добавить новую компанию / изменить
    name = StringField('Полное название (из файлов НБ)',validators=[DataRequired()])
    alias = StringField('Краткое (отображаемое) название',validators=[DataRequired()])
    nonlife = BooleanField('Компания по общему страхованию')
    alive = BooleanField('Действующая компания')
    submit = SubmitField('Добавить / изменить')


class AddEditClassForm(FlaskForm):#добавить новый класс страхования / изменить
    name = StringField('Системное название на английском',validators=[DataRequired()])
    fullname = StringField('Полное название (из файлов НБ)',validators=[DataRequired()])
    alias = StringField('Краткое (отображаемое) название',validators=[DataRequired()])
    sum_to_totals = BooleanField('Участвует в расчете общей суммы по форме страхования')
    nonlife = BooleanField('Относится к общему страхованию')
    obligatory = BooleanField('Относится к обязательному страхованию')
    voluntary_personal = BooleanField('Относится к добровольному личному страхованию')
    voluntary_property = BooleanField('Относится к добровольному имущественному страхованию')
    submit = SubmitField('Добавить / изменить')


class UsageLogForm(FlaskForm):#лог использования    
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    show_details = BooleanField('Показать детали')
    submit = SubmitField('Показать')
    
    def validate(self):#дата окончания должна быть больше даты начала
        d_beg = datetime(self.begin_d.data.year,self.begin_d.data.month,self.begin_d.data.day)
        d_end = datetime(self.end_d.data.year,self.end_d.data.month,self.end_d.data.day)
        if self.begin_d.data > self.end_d.data:
            flash('Дата окончания должна быть больше даты начала')
            return False        
        else:
            return True


class SendEmailToUsersForm(FlaskForm):#отправить всем пользователям email
    subject = StringField('Тема сообщения',validators=[DataRequired()])
    body = TextAreaField('Текст сообщения',validators=[DataRequired(), Length(min=1,max=500)])
    send_to_all = BooleanField('Отправить всем')
    users = SelectMultipleField('Получатели (удерживайте Ctrl)',choices = [])
    submit = SubmitField('Отправить сообщение')

    def __init__(self, *args, **kwargs):
        super(SendEmailToUsersForm, self).__init__(*args, **kwargs)
        all_users = User.query.filter(User.send_emails == True).order_by(User.last_seen.desc()).all()
        all_users_str = [(str(a.id), a.username) for a in all_users]
        self.users.choices = all_users_str


class HintForm(FlaskForm):#добавить подсказку
    name = StringField('Системное имя подсказки',validators=[DataRequired(), Length(min=1,max=128)])
    title = StringField('Заголовок подсказки',validators=[DataRequired(), Length(min=1,max=500)])
    text = TextAreaField('Текст подсказки',validators=[DataRequired(), Length(min=1,max=2000)])    
    submit = SubmitField('Добавить / изменить подсказку')

