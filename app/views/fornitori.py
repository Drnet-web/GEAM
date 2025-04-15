from flask import render_template, redirect, url_for, flash, request, jsonify
from app import db
from app.models.fornitore import Fornitore
from app.models.log import Log
from sqlalchemy import or_
from datetime import datetime

# Importiamo il blueprint dalla definizione in __init__.py
from app.views import fornitori_bp

# Creiamo il form per i fornitori
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
import re

class FornitoreForm(FlaskForm):
    """Form per la gestione dei fornitori"""
    fornitore_id = HiddenField('ID Fornitore')
    
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
    
    note = TextAreaField('Note', validators=[Optional()])
    
    submit = SubmitField('Salva Fornitore')
    
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
        """Verifica che non esista già l'azienda (in caso di nuovo fornitore)"""
        if self.fornitore_id.data:
            fornitore = Fornitore.query.filter(
                Fornitore.azienda == field.data, 
                Fornitore.id != int(self.fornitore_id.data)
            ).first()
        else:
            fornitore = Fornitore.query.filter(Fornitore.azienda == field.data).first()
        
        if fornitore:
            raise ValidationError('Questa azienda esiste già')


# Route per la lista fornitori
@fornitori_bp.route('/')
def index():
    """Visualizza la lista di tutti i fornitori"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Fornitore.query
    
    # Filtraggio per ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            or_(
                Fornitore.azienda.ilike(f'%{search}%'),
                Fornitore.comune.ilike(f'%{search}%')
            )
        )
    
    # Ordinamento
    sort_by = request.args.get('sort_by', 'azienda')
    order = request.args.get('order', 'asc')
    
    if order == 'asc':
        query = query.order_by(getattr(Fornitore, sort_by).asc())
    else:
        query = query.order_by(getattr(Fornitore, sort_by).desc())
    
    # Paginazione
    fornitori = query.paginate(page=page, per_page=per_page)
    
    return render_template('fornitori/index.html', 
                          fornitori=fornitori, 
                          search=search,
                          sort_by=sort_by,
                          order=order)


# Route per creare un nuovo fornitore
@fornitori_bp.route('/nuovo', methods=['GET', 'POST'])
def nuovo():
    """Crea un nuovo fornitore"""
    form = FornitoreForm()
    
    if form.validate_on_submit():
        fornitore = Fornitore(
            azienda=form.azienda.data,
            indirizzo=form.indirizzo.data,
            cap=form.cap.data,
            provincia=form.provincia.data.upper(),
            comune=form.comune.data,
            telefono=form.telefono.data,
            cellulare=form.cellulare.data,
            email=form.email.data,
            note=form.note.data
        )
        
        db.session.add(fornitore)
        db.session.commit()
        
        # Registrazione nel log
        log = Log(
            azione='creazione',
            dettagli={"fornitore": fornitore.to_dict()},
            utente='admin'  # In futuro sostituire con utente reale
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Fornitore "{fornitore.azienda}" creato con successo!', 'success')
        return redirect(url_for('fornitori.index'))
    
    return render_template('fornitori/form.html', form=form, title='Nuovo Fornitore')


# Route per visualizzare un fornitore
@fornitori_bp.route('/<int:id>')
def visualizza(id):
    """Visualizza i dettagli di un fornitore"""
    fornitore = Fornitore.query.get_or_404(id)
    
    return render_template('fornitori/visualizza.html', 
                          fornitore=fornitore,
                          now=datetime.now())


# Route per modificare un fornitore
@fornitori_bp.route('/modifica/<int:id>', methods=['GET', 'POST'])
def modifica(id):
    """Modifica un fornitore esistente"""
    fornitore = Fornitore.query.get_or_404(id)
    form = FornitoreForm(obj=fornitore)
    form.fornitore_id.data = fornitore.id
    
    if form.validate_on_submit():
        # Salva i vecchi valori per il log
        vecchi_valori = fornitore.to_dict()
        
        # Aggiorna i valori
        form.populate_obj(fornitore)
        
        # Assicurati che la provincia sia maiuscola
        fornitore.provincia = fornitore.provincia.upper()
        
        db.session.commit()
        
        # Registrazione nel log
        log = Log(
            azione='modifica',
            dettagli={
                "fornitore": fornitore.to_dict(),
                "vecchi_valori": vecchi_valori
            },
            utente='admin'  # In futuro sostituire con utente reale
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Fornitore "{fornitore.azienda}" aggiornato con successo!', 'success')
        return redirect(url_for('fornitori.visualizza', id=fornitore.id))
    
    return render_template('fornitori/form.html', form=form, fornitore=fornitore, title='Modifica Fornitore')


# Route per eliminare un fornitore
@fornitori_bp.route('/elimina/<int:id>', methods=['POST'])
def elimina(id):
    """Elimina un fornitore"""
    fornitore = Fornitore.query.get_or_404(id)
    
    # Salva i valori per il messaggio flash
    nome_azienda = fornitore.azienda
    
    # Crea un dizionario con i dati del fornitore da salvare nel log
    fornitore_dati = fornitore.to_dict()
    
    # Elimina il fornitore
    db.session.delete(fornitore)
    db.session.commit()  # Commit separato per eliminare prima il fornitore
    
    # Ora crea il log DOPO aver eliminato il fornitore
    log = Log(
        azione='eliminazione',
        dettagli={"fornitore": fornitore_dati},
        utente='admin'  # In futuro sostituire con utente reale
    )
    db.session.add(log)
    db.session.commit()  # Commit del log
    
    flash(f'Fornitore "{nome_azienda}" eliminato con successo!', 'success')
    return redirect(url_for('fornitori.index'))


# API per ottenere l'elenco dei fornitori (per form dinamici)
@fornitori_bp.route('/api/lista')
def api_lista():
    """API per ottenere la lista dei fornitori (per select dinamiche)"""
    fornitori = Fornitore.query.order_by(Fornitore.azienda).all()
    
    result = [{'id': f.id, 'text': f.azienda} for f in fornitori]
    return jsonify(result)