from flask import Blueprint

bp = Blueprint('motor', __name__)

from app.motor import routes