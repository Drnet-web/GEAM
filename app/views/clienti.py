
from flask import render_template, redirect, url_for, flash, request, jsonify
from app import db
from app.models.cliente import Cliente
from app.models.estintore import Estintore
from app.models.log import Log
from sqlalchemy import or_
import os
from datetime import datetime

from app.views import clienti_bp

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
import re

class ClienteForm(FlaskForm):
    """Form per la gestione dei clienti"""
    cliente_id = HiddenField('ID Cliente')
    
    azienda = StringField('Azienda', validators=[
        DataRequired(message="L'azienda è obbligatoria"),
        Length(min=2, max=100, message="L'azienda deve essere tra 2 e 100 caratteri")
    ])
    indirizzo = StringField('Indirizzo', validators=[
        DataRequired(message="L'indirizzo è obbligatorio"),
        Length(min=2, max=150, message="L'indirizzo deve essere tra 2 e 150 caratteri")
    ])
    cap = StringField('CAP', validators=[
        DataRequired(message="Il CAP è obbligatorio"),
        Length(min=5, max=5, message="Il CAP deve essere di 5 cifre")
    ])
    provincia = StringField('Provincia', validators=[
        DataRequired(message="La provincia è obbligatoria"),
        Length(min=2, max=2, message="La provincia deve essere di 2 lettere")
    ])
    comune = StringField('Comune', validators=[
        DataRequired(message="Il comune è obbligatorio"),
        Length(min=2, max=100, message="Il comune deve essere tra 2 e 100 caratteri")
    ])
    zona = StringField('Zona', validators=[
        DataRequired(message="La zona è obbligatoria"),
        Length(min=2, max=100, message="La zona deve essere tra 2 e 100 caratteri")
    ])
    tipologia = SelectField('Tipologia', choices=[
        ('Fisso', 'Fisso'),
        ('Stagionale', 'Stagionale'),
        ('Occasionale', 'Occasionale'),
        ('Cessato', 'Cessato')
    ], validators=[DataRequired(message="La tipologia è obbligatoria")])
    telefono = StringField('Telefono', validators=[Optional(), Length(max=20)])
    cellulare = StringField('Cellulare', validators=[Optional(), Length(max=15)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    coordinate = StringField('Coordinate', validators=[Optional(), Length(max=100)])
    note = TextAreaField('Note', validators=[Optional()])
    submit = SubmitField('Salva Cliente')
    
    # --- validators (immutati) ---
    def validate_cap(self, field):
        if not field.data.isdigit() or len(field.data) != 5:
            raise ValidationError('Il CAP deve essere composto da 5 cifre')
    def validate_provincia(self, field):
        if not re.match(r'^[A-Za-z]{2}$', field.data):
            raise ValidationError('La provincia deve essere composta da 2 lettere')
        field.data = field.data.upper()
    def validate_cellulare(self, field):
        if field.data and not re.match(r'^(\+39)?\s?3\d{8,9}$', field.data):
            raise ValidationError('Formato cellulare non valido (es: 3xx1234567 o +39 3xx1234567)')
    def validate_azienda(self, field):
        if self.cliente_id.data:
            cliente = Cliente.query.filter(Cliente.azienda == field.data, Cliente.id != int(self.cliente_id.data)).first()
        else:
            cliente = Cliente.query.filter(Cliente.azienda == field.data).first()
        if cliente:
            raise ValidationError('Questa azienda esiste già')


# ------------------- ROUTES -----------------------

@clienti_bp.route('/')
def index():
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'azienda')
    order = request.args.get('order', 'asc')
    tipologia = request.args.get('tipologia', '')
    page = request.args.get('page', 1, type=int)
    
    # nuovo parametro: solo clienti SENZA estintori
    solo_senza_estintori = request.args.get('solo_senza_estintori', '') == 'on'
    
    query = Cliente.query
    
    if search:
        query = query.filter(Cliente.azienda.ilike(f"%{search}%"))
    if tipologia and tipologia != 'tutti':
        query = query.filter(Cliente.tipologia == tipologia)
    
    if solo_senza_estintori:
        # left‑join e filtra dove l'id estintore è NULL
        query = (query
                 .outerjoin(Estintore)
                 .filter(Estintore.id.is_(None)))
    
    if sort_by:
        sort_column = getattr(Cliente, sort_by, Cliente.azienda)
        sort_column = sort_column.desc() if order == 'desc' else sort_column.asc()
        query = query.order_by(sort_column)
    
    clienti = query.paginate(page=page, per_page=20)
    
    tipologie = [t[0] for t in db.session.query(Cliente.tipologia).distinct().all()]
    
    return render_template('clienti/index.html',
                           clienti=clienti,
                           search=search,
                           sort_by=sort_by,
                           order=order,
                           tipologia=tipologia,
                           tipologie=tipologie,
                           solo_senza_estintori=solo_senza_estintori)


@clienti_bp.route('/nuovo', methods=['GET', 'POST'])
def nuovo():
    form = ClienteForm()
    if form.validate_on_submit():
        cliente = Cliente(
            azienda=form.azienda.data,
            indirizzo=form.indirizzo.data,
            cap=form.cap.data,
            provincia=form.provincia.data.upper(),
            comune=form.comune.data,
            zona=form.zona.data,
            tipologia=form.tipologia.data,
            telefono=form.telefono.data,
            cellulare=form.cellulare.data,
            email=form.email.data,
            coordinate=form.coordinate.data,
            note=form.note.data
        )
        db.session.add(cliente)
        db.session.commit()
        Log.log_cliente('creazione', cliente, utente='admin')
        flash(f'Cliente "{cliente.azienda}" creato con successo!', 'success')
        return redirect(url_for('clienti.index'))
    return render_template('clienti/form.html', form=form, title='Nuovo Cliente')


@clienti_bp.route('/<int:id>')
def visualizza(id):
    cliente = Cliente.query.get_or_404(id)
    total_estintori = Estintore.query.filter_by(cliente_id=id).count()
    oggi = datetime.now()
    prossime_scadenze = (Estintore.query.filter_by(cliente_id=id)
                         .filter(Estintore.data_controllo >= oggi.date())
                         .order_by(Estintore.data_controllo).limit(5).all())
    return render_template('clienti/visualizza.html',
                           cliente=cliente,
                           total_estintori=total_estintori,
                           prossime_scadenze=prossime_scadenze,
                           now=oggi)


@clienti_bp.route('/modifica/<int:id>', methods=['GET', 'POST'])
def modifica(id):
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    form.cliente_id.data = cliente.id
    if form.validate_on_submit():
        vecchi_valori = cliente.to_dict()
        form.populate_obj(cliente)
        cliente.provincia = cliente.provincia.upper()
        db.session.commit()
        Log.log_cliente('modifica', cliente, vecchi_valori=vecchi_valori, utente='admin')
        flash(f'Cliente "{cliente.azienda}" aggiornato con successo!', 'success')
        return redirect(url_for('clienti.visualizza', id=cliente.id))
    return render_template('clienti/form.html', form=form, cliente=cliente, title='Modifica Cliente')


@clienti_bp.route('/elimina/<int:id>', methods=['POST'])
def elimina(id):
    cliente = Cliente.query.get_or_404(id)
    estintori_associati = Estintore.query.filter_by(cliente_id=id).count()
    if estintori_associati > 0:
        flash(f'Impossibile eliminare il cliente "{cliente.azienda}" perché ha {estintori_associati} estintori associati!', 'danger')
        return redirect(url_for('clienti.visualizza', id=id))
    nome_azienda = cliente.azienda
    cliente_dati = cliente.to_dict()
    db.session.delete(cliente)
    db.session.commit()
    log = Log(azione='eliminazione', dettagli={'cliente': cliente_dati}, cliente_id=None, utente='admin')
    db.session.add(log)
    db.session.commit()
    flash(f'Cliente "{nome_azienda}" eliminato con successo!', 'success')
    return redirect(url_for('clienti.index'))


@clienti_bp.route('/api/lista')
def api_lista():
    clienti = Cliente.query.order_by(Cliente.azienda).all()
    return jsonify([{'id': c.id, 'text': c.azienda} for c in clienti])
