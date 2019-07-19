from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField, SelectField                    
from wtforms.validators import DataRequired
from app.models import Insclass
from wtforms.fields.html5 import DateField
from flask import flash, g
from datetime import datetime



class ClassProfileForm(FlaskForm):#информация по продукту    
    insclass = SelectField('Выберите класс страхования',choices = [],validators=[DataRequired()])
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    show_last_year = BooleanField('Показать данные по сравнению с аналогичным периодом прошлого года')
    show_info_submit = SubmitField('Показать информацию')
    save_to_file_submit = SubmitField('Сохранить в файл')

    def __init__(self, *args, **kwargs):
        super(ClassProfileForm, self).__init__(*args, **kwargs)
        insclasses = Insclass.query.with_entities(Insclass.id,Insclass.alias) \
                .filter(Insclass.nonlife == 1) \
                .order_by(Insclass.obligatory.desc()) \
                .order_by(Insclass.voluntary_property.desc()) \
                .order_by(Insclass.voluntary_personal.desc()) \
                .order_by(Insclass.id).all()
        sources_db = [(str(a.id), a.alias) for a in insclasses]
        self.insclass.choices = sources_db

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