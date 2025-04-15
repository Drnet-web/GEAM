from flask import render_template, redirect, url_for, flash, request, jsonify
from app import db
from app.models.cliente import Cliente
from app.models.estintore import Estintore
from app.models.log import Log
from sqlalchemy import or_
import os
from datetime import datetime

# Importiamo il blueprint dalla definizione in __init__.py
from app.views import clienti_bp

# Creiamo il form per i clienti
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
    
    # Campi opzionali
    telefono = StringField('Telefono', validators=[
        Optional(),
        Length(max=20, message="Il telefono non può superare 20 caratteri")
    ])
    
    cellulare = StringField('Cellulare', validators=[
        Optional(),
        Length(max=15, message="Il cellulare non può superare 15 caratteri")
    ])
    
    email = StringField('Email', validators=[
        Optional(),
        Email(message="Formato email non valido"),
        Length(max=120, message="L'email non può superare 120 caratteri")
    ])
    
    coordinate = StringField('Coordinate', validators=[
        Optional(),
        Length(max=100, message="Le coordinate non possono superare 100 caratteri")
    ])
    
    note = TextAreaField('Note', validators=[Optional()])
    
    submit = SubmitField('Salva Cliente')
    
    def validate_cap(self, field):
        """Validazione formato CAP (5 cifre)"""
        if not field.data.isdigit() or len(field.data) != 5:
            raise ValidationError('Il CAP deve essere composto da 5 cifre')
    
    def validate_provincia(self, field):
        """Validazione formato provincia (2 lettere)"""
        if not re.match(r'^[A-Za-z]{2}$', field.data):
            raise ValidationError('La provincia deve essere composta da 2 lettere')
        
        # Convertiamo in maiuscolo
        field.data = field.data.upper()
    
    def validate_cellulare(self, field):
        """Validazione formato cellulare italiano"""
        if field.data:
            if not re.match(r'^(\+39)?\s?3\d{8,9}$', field.data):
                raise ValidationError('Formato cellulare non valido (es: 3xx1234567 o +39 3xx1234567)')
    
    def validate_azienda(self, field):
        """Verifica che non esista già l'azienda (in caso di nuovo cliente)"""
        if self.cliente_id.data:
            cliente = Cliente.query.filter(
                Cliente.azienda == field.data, 
                Cliente.id != int(self.cliente_id.data)
            ).first()
        else:
            cliente = Cliente.query.filter(Cliente.azienda == field.data).first()
        
        if cliente:
            raise ValidationError('Questa azienda esiste già')

# Route per la lista clienti
# Route per la lista clienti
@clienti_bp.route('/')
def index():
    """Visualizza la lista di tutti i clienti"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Cliente.query
    
    # Filtraggio per ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            or_(
                Cliente.azienda.ilike(f'%{search}%'),
                Cliente.comune.ilike(f'%{search}%'),
                Cliente.zona.ilike(f'%{search}%')
            )
        )
    
    # Filtraggio per tipologia cliente
    tipologia = request.args.get('tipologia', 'tutti')
    if tipologia != 'tutti':
        query = query.filter(Cliente.tipologia == tipologia)
    
    # Ordinamento
    sort_by = request.args.get('sort_by', 'azienda')
    order = request.args.get('order', 'asc')
    
    if order == 'asc':
        query = query.order_by(getattr(Cliente, sort_by).asc())
    else:
        query = query.order_by(getattr(Cliente, sort_by).desc())
    
    # Paginazione
    clienti = query.paginate(page=page, per_page=per_page)
    
    return render_template('clienti/index.html', 
                          clienti=clienti, 
                          search=search,
                          sort_by=sort_by,
                          order=order,
                          tipologia=tipologia)  # Aggiungi tipologia al contesto

# Route per creare un nuovo cliente
@clienti_bp.route('/nuovo', methods=['GET', 'POST'])
def nuovo():
    """Crea un nuovo cliente"""
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
        
        # Registrazione nel log
        Log.log_cliente('creazione', cliente, utente='admin')  # In futuro sostituire con utente reale
        
        flash(f'Cliente "{cliente.azienda}" creato con successo!', 'success')
        return redirect(url_for('clienti.index'))
    
    return render_template('clienti/form.html', form=form, title='Nuovo Cliente')

# Route per visualizzare un cliente
@clienti_bp.route('/<int:id>')
def visualizza(id):
    """Visualizza i dettagli di un cliente"""
    cliente = Cliente.query.get_or_404(id)
    
    # Conteggio estintori
    total_estintori = Estintore.query.filter_by(cliente_id=id).count()
    
    # Data attuale per i calcoli di scadenza
    oggi = datetime.now()
    
    # Prossime scadenze
    prossime_scadenze = Estintore.query.filter_by(cliente_id=id).filter(
        Estintore.data_controllo >= oggi.date()
    ).order_by(Estintore.data_controllo).limit(5).all()
    
    return render_template('clienti/visualizza.html', 
                          cliente=cliente,
                          total_estintori=total_estintori,
                          prossime_scadenze=prossime_scadenze,
                          now=oggi)

# Route per modificare un cliente
@clienti_bp.route('/modifica/<int:id>', methods=['GET', 'POST'])
def modifica(id):
    """Modifica un cliente esistente"""
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    form.cliente_id.data = cliente.id
    
    if form.validate_on_submit():
        # Salva i vecchi valori per il log
        vecchi_valori = cliente.to_dict()
        
        # Aggiorna i valori
        form.populate_obj(cliente)
        
        # Assicurati che la provincia sia maiuscola
        cliente.provincia = cliente.provincia.upper()
        
        db.session.commit()
        
        # Registrazione nel log
        Log.log_cliente('modifica', cliente, vecchi_valori=vecchi_valori, utente='admin')
        
        flash(f'Cliente "{cliente.azienda}" aggiornato con successo!', 'success')
        return redirect(url_for('clienti.visualizza', id=cliente.id))
    
    return render_template('clienti/form.html', form=form, cliente=cliente, title='Modifica Cliente')

@clienti_bp.route('/elimina/<int:id>', methods=['POST'])
def elimina(id):
    """Elimina un cliente"""
    cliente = Cliente.query.get_or_404(id)
    
    # Verifica se ci sono estintori associati
    estintori_associati = Estintore.query.filter_by(cliente_id=id).count()
    if estintori_associati > 0:
        flash(f'Impossibile eliminare il cliente "{cliente.azienda}" perché ha {estintori_associati} estintori associati!', 'danger')
        return redirect(url_for('clienti.visualizza', id=id))
    
    # Salva i valori per il messaggio flash
    nome_azienda = cliente.azienda
    
    # Crea un dizionario con i dati del cliente da salvare nel log
    cliente_dati = {
        "id": cliente.id,
        "azienda": cliente.azienda,
        "indirizzo": cliente.indirizzo,
        "cap": cliente.cap,
        "provincia": cliente.provincia,
        "comune": cliente.comune,
        "zona": cliente.zona,
        "tipologia": cliente.tipologia,
        "telefono": cliente.telefono or "",
        "cellulare": cliente.cellulare or "",
        "email": cliente.email or "",
        "coordinate": cliente.coordinate or "",
        "note": cliente.note or ""
    }
    
    # Elimina il cliente
    db.session.delete(cliente)
    db.session.commit()  # Commit separato per eliminare prima il cliente
    
    # Ora crea il log DOPO aver eliminato il cliente
    log = Log(
        azione='eliminazione',
        dettagli={"cliente": cliente_dati},
        cliente_id=None,  # Cliente già eliminato, non associare a nessun cliente
        utente='admin'  # In futuro sostituire con utente reale
    )
    db.session.add(log)
    db.session.commit()  # Commit del log
    
    flash(f'Cliente "{nome_azienda}" eliminato con successo!', 'success')
    return redirect(url_for('clienti.index'))

# API per ottenere l'elenco dei clienti (per form dinamici)
@clienti_bp.route('/api/lista')
def api_lista():
    """API per ottenere la lista dei clienti (per select dinamiche)"""
    clienti = Cliente.query.order_by(Cliente.azienda).all()
    
    result = [{'id': c.id, 'text': c.azienda} for c in clienti]
    return jsonify(result)