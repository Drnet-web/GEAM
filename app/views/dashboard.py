from flask import render_template, Blueprint
from app.models.cliente import Cliente
from app.models.estintore import Estintore
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func

# Blueprint importato in __init__.py
from app.views import dashboard_bp

@dashboard_bp.route('/')
def index():
    """
    Dashboard principale con statistiche e riassunto
    """
    
    # Statistiche di base
    total_clienti = Cliente.query.count()
    total_estintori = Estintore.query.count()
    
    # Estintori per tipologia
    estintori_per_tipologia = db.session.query(
        Estintore.tipologia, func.count(Estintore.id)
    ).group_by(Estintore.tipologia).all()
    
    # Estintori in scadenza nei prossimi 30 giorni
    oggi = datetime.now().date()
    scadenza_30_giorni = oggi + timedelta(days=30)
    
    estintori_in_scadenza = Estintore.query.filter(
        (Estintore.data_controllo <= scadenza_30_giorni) & 
        (Estintore.data_controllo >= oggi)
    ).count()
    
    # Estintori scaduti
    estintori_scaduti = Estintore.query.filter(
        Estintore.data_controllo < oggi
    ).count()
    
    # Clienti per tipologia
    clienti_per_tipologia = db.session.query(
        Cliente.tipologia, func.count(Cliente.id)
    ).group_by(Cliente.tipologia).all()
    
    # Estintori attivi vs in manutenzione
    estintori_stato = db.session.query(
        Estintore.stato, func.count(Estintore.id)
    ).group_by(Estintore.stato).all()
    
    return render_template('dashboard/index.html',
                          total_clienti=total_clienti,
                          total_estintori=total_estintori,
                          estintori_per_tipologia=estintori_per_tipologia,
                          estintori_in_scadenza=estintori_in_scadenza,
                          estintori_scaduti=estintori_scaduti,
                          clienti_per_tipologia=clienti_per_tipologia,
                          estintori_stato=estintori_stato)