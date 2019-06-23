from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField
from flask import flash, g
from datetime import datetime


class RankingForm(FlaskForm):#ранкинг    
    begin_d = DateField('Начало, дата', format='%Y-%m-%d',validators=[DataRequired()])
    end_d = DateField('Конец, дата', format='%Y-%m-%d',validators=[DataRequired()])
    show_last_year = BooleanField('Показать данные по сравнению с аналогичным периодом прошлого года')
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