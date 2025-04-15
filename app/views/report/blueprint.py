from flask import Blueprint, render_template, jsonify, request
from app import db
from app.models.cliente import Cliente
from app.models.estintore import Estintore
from sqlalchemy import func, and_
from datetime import datetime, timedelta

# Crea il blueprint
report_bp = Blueprint('report', __name__, url_prefix='/report')

@report_bp.route('/')
def index():
    """Pagina principale della sezione Report"""
    return render_template('report/index.html')

@report_bp.route('/api/estintori-tipologia')
def api_estintori_tipologia():
    estintori_per_tipologia = db.session.query(
        Estintore.tipologia, func.count(Estintore.id).label('totale')
    ).group_by(Estintore.tipologia).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in estintori_per_tipologia])

@report_bp.route('/api/estintori-stato')
def api_estintori_stato():
    estintori_per_stato = db.session.query(
        Estintore.stato, func.count(Estintore.id).label('totale')
    ).group_by(Estintore.stato).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in estintori_per_stato])

@report_bp.route('/api/clienti-tipologia')
def api_clienti_tipologia():
    clienti_per_tipologia = db.session.query(
        Cliente.tipologia, func.count(Cliente.id).label('totale')
    ).group_by(Cliente.tipologia).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in clienti_per_tipologia])

@report_bp.route('/api/clienti-zona')
def api_clienti_zona():
    clienti_per_zona = db.session.query(
        Cliente.zona, func.count(Cliente.id).label('totale')
    ).group_by(Cliente.zona).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in clienti_per_zona])

@report_bp.route('/api/estintori-scadenze')
def api_estintori_scadenze():
    oggi = datetime.now().date()
    scaduti = db.session.query(func.count(Estintore.id)).filter(Estintore.data_controllo < oggi).scalar()
    entro_30_giorni = db.session.query(func.count(Estintore.id)).filter(
        and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= oggi + timedelta(days=30))
    ).scalar()
    entro_90_giorni = db.session.query(func.count(Estintore.id)).filter(
        and_(Estintore.data_controllo > oggi + timedelta(days=30), 
             Estintore.data_controllo <= oggi + timedelta(days=90))
    ).scalar()
    entro_180_giorni = db.session.query(func.count(Estintore.id)).filter(
        and_(Estintore.data_controllo > oggi + timedelta(days=90),
             Estintore.data_controllo <= oggi + timedelta(days=180))
    ).scalar()
    oltre_180_giorni = db.session.query(func.count(Estintore.id)).filter(
        Estintore.data_controllo > oggi + timedelta(days=180)
    ).scalar()
    return jsonify([
        {'name': 'Scaduti', 'value': scaduti},
        {'name': 'Entro 30 giorni', 'value': entro_30_giorni},
        {'name': 'Entro 90 giorni', 'value': entro_90_giorni},
        {'name': 'Entro 180 giorni', 'value': entro_180_giorni},
        {'name': 'Oltre 180 giorni', 'value': oltre_180_giorni}
    ])

@report_bp.route('/api/estintori-zona')
def api_estintori_zona():
    estintori_per_zona = db.session.query(
        Cliente.zona, func.count(Estintore.id).label('totale')
    ).join(Cliente, Estintore.cliente_id == Cliente.id).group_by(Cliente.zona).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in estintori_per_zona])

@report_bp.route('/api/estintori-mese')
def api_estintori_mese():
    oggi = datetime.now().date()
    mesi = 12
    result = []
    for i in range(mesi):
        inizio_mese = (oggi.replace(day=1) + timedelta(days=32*i)).replace(day=1)
        fine_mese = (oggi.replace(day=1) + timedelta(days=32*(i+1))).replace(day=1) - timedelta(days=1)
        conteggio = db.session.query(func.count(Estintore.id)).filter(
            and_(Estintore.data_controllo >= inizio_mese, Estintore.data_controllo <= fine_mese)
        ).scalar()
        result.append({'name': inizio_mese.strftime('%b %Y'), 'value': conteggio})
    return jsonify(result)

@report_bp.route('/api/distribuzione-capacita')
def api_distribuzione_capacita():
    estintori_per_capacita = db.session.query(
        Estintore.capacita, func.count(Estintore.id).label('totale')
    ).group_by(Estintore.capacita).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in estintori_per_capacita])

@report_bp.route('/api/clienti-comune')
def api_clienti_comune():
    clienti_per_comune = db.session.query(
        Cliente.comune, func.count(Cliente.id).label('totale')
    ).group_by(Cliente.comune).all()
    return jsonify([{'name': row[0], 'value': row[1]} for row in clienti_per_comune])

@report_bp.route('/api/scadenze-prossime')
def api_scadenze_prossime():
    oggi = datetime.today().date()
    tra_30_giorni = oggi + timedelta(days=30)
    scadenze = db.session.query(func.count(Estintore.id)).filter(
        Estintore.data_controllo.between(oggi, tra_30_giorni)
    ).scalar()
    return jsonify([{'name': 'Prossime 30gg', 'value': scadenze}])

@report_bp.route('/api/stato-scadenze')
def api_stato_scadenze():
    oggi = datetime.today().date()
    scaduti = db.session.query(func.count(Estintore.id)).filter(Estintore.data_controllo < oggi).scalar()
    in_regola = db.session.query(func.count(Estintore.id)).filter(Estintore.data_controllo >= oggi).scalar()
    return jsonify([
        {'name': 'Scaduti', 'value': scaduti},
        {'name': 'In regola', 'value': in_regola}
    ])