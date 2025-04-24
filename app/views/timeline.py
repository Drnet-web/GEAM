from flask import Blueprint, render_template, request, jsonify
from datetime import date
from app.models.estintore import Estintore
from flask import send_file

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
                    'color': '#3498db'  # blu
                })
            if est.data_revisione:
                eventi.append({
                    'id': f"REV-{est.id}",
                    'title': f"[Revisione] {est.cliente.azienda} - {est.tipologia} {est.capacita}",
                    'start': est.data_revisione.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#e67e22'  # arancione
                })
            if est.data_collaudo:
                eventi.append({
                    'id': f"COLL-{est.id}",
                    'title': f"[Collaudo] {est.cliente.azienda} - {est.tipologia} {est.capacita}",
                    'start': est.data_collaudo.strftime('%Y-%m-%d'),
                    'allDay': True,
                    'color': '#e74c3c'  # rosso
                })
        except Exception as e:
            print(f"Errore su estintore ID {est.id}: {e}")

    return jsonify(eventi)
    from flask import send_file
import pdfkit
import os
from flask import render_template

@timeline_bp.route('/report')
def report():
    estintori = Estintore.query.all()
    return render_template('timeline_report.html', estintori=estintori)

@timeline_bp.route('/report/pdf')
def report_pdf():
    estintori = Estintore.query.all()
    rendered = render_template('timeline_report.html', estintori=estintori)

    # Percorsi assoluti
    html_path = os.path.abspath("temp_report.html")
    pdf_path = os.path.abspath("report_interventi.pdf")

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(rendered)

    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None
    }

    pdfkit.from_file(html_path, pdf_path, options=options)

    os.remove(html_path)
    return send_file(pdf_path, as_attachment=True)