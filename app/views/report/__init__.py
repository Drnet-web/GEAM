from flask import Blueprint

# Crea il blueprint
report_bp = Blueprint('report', __name__, url_prefix='/report')

# Importa le viste
from app.views.report.blueprint import *