from flask import Blueprint

bp = Blueprint('class_profile', __name__)

from app.class_profile import routes