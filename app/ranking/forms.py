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
    show_info_submit = SubmitField('Показать информацию')
    save_to_file_submit = SubmitField('Сохранить в файл')
    
