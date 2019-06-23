from flask import Blueprint

bp = Blueprint('ranking', __name__)

from app.ranking import routes