from flask import Blueprint

bp = Blueprint('company_peers_profile', __name__)

from app.company_peers_profile import routes