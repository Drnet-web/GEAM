from flask import Blueprint, render_template, request, jsonify
from datetime import date
from app.models.estintore import Estintore

timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')

@timeline_bp.route('/')
def index():
    return render_template('calendar.html')

@timeline_bp.route('/api/eventi')
def api_eventi():
    eventi = []
    estintori = Estintore.query.all()

    for est in estintori:
        try:
            if est.data_controllo:
                eventi.append({
                    'id': f"CONT-{est.id}",
                    'title': f"[Controllo] {est.cliente.azienda} - {est.tipologia} {est.capacita}",
                    'start': est.data_controllo.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#3498db'
                })
            if est.data_revisione:
                eventi.append({
                    'id': f"REV-{est.id}",
                    'title': f"[Revisione] {est.cliente.azienda} - {est.tipologia} {est.capacita}",
                    'start': est.data_revisione.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#e67e22'
                })
            if est.data_collaudo:
                eventi.append({
                    'id': f"COLL-{est.id}",
                    'title': f"[Collaudo] {est.cliente.azienda} - {est.tipologia} {est.capacita}",
                    'start': est.data_collaudo.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#e74c3c'
                })
        except Exception as e:
            print(f"Errore su estintore ID {est.id}: {e}")

    return jsonify(eventi)