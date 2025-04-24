from flask import Blueprint

# Creazione dei blueprint
clienti_bp = Blueprint('clienti', __name__, url_prefix='/clienti')
fornitori_bp = Blueprint('fornitori', __name__, url_prefix='/fornitori')  # Nuovo blueprint
estintori_bp = Blueprint('estintori', __name__, url_prefix='/estintori')
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

# Importazione delle viste separatamente per evitare problemi di circolarità
from . import clienti
from . import fornitori  # Importa fornitori separatamente
from . import estintori
from . import dashboard
from .timeline import timeline_bp


__all__ = ['clienti_bp', 'estintori_bp', 'dashboard_bp', 'fornitori_bp']