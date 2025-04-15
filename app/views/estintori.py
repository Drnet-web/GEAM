from flask import render_template, redirect, url_for, flash, request, jsonify
from app import db
from app.models.estintore import Estintore
from app.models.cliente import Cliente
from app.models.log import Log
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import os
import re
import csv
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from flask import make_response
from flask_login import login_required
from reportlab.platypus import Image
from reportlab.lib.units import cm
import pdfkit  # Aggiungi questa importazione
from reportlab.lib.pagesizes import A4, landscape
# Importiamo il blueprint dalla definizione in __init__.py
from app.views import estintori_bp
# Creiamo il form per gli estintori
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, ValidationError
from datetime import datetime, timedelta, date

class EstintoreForm(FlaskForm):
    """Form per la gestione degli estintori"""
    
    estintore_id = HiddenField('ID Estintore')
    cliente_id = HiddenField('ID Cliente', validators=[DataRequired()])
    
    # Campi obbligatori
    tipologia = SelectField('Tipologia', validators=[DataRequired(message="La tipologia è obbligatoria")], choices=[
        ('CO2', 'CO2'),
        ('Polvere', 'Polvere'),
        ('Idrico', 'Idrico'),
        ('Carrello Polvere', 'Carrello Polvere'),
        ('Carrello Idrico', 'Carrello Idrico'),
        ('NASPO UNI25', 'NASPO UNI25'),
        ('Idrante UNI45', 'Idrante UNI45'),
        ('Idrante UNI70', 'Idrante UNI70'),
        ('Porta REI', 'Porta REI'),
        ('Automatico Polvere', 'Automatico Polvere'),
        ('Automatico Idrico', 'Automatico Idrico'),
        ('CPS', 'CPS'),
        ('Registro', 'Registro'),
        ('Altro', 'Altro')
    ])
    
    marca = StringField('Marca', validators=[
        DataRequired(message="La marca è obbligatoria"),
        Length(min=2, max=50, message="La marca deve essere tra 2 e 50 caratteri")
    ])
    
    matricola = StringField('Matricola', validators=[
        DataRequired(message="La matricola è obbligatoria"),
        Length(min=2, max=50, message="La matricola deve essere tra 2 e 50 caratteri")
    ])
    
    dislocazione = StringField('Dislocazione', validators=[
        DataRequired(message="La dislocazione è obbligatoria"),
        Length(min=2, max=150, message="La dislocazione deve essere tra 2 e 150 caratteri")
    ])
    
    capacita = SelectField('Capacità', validators=[DataRequired(message="La capacità è obbligatoria")])
    
    data_fabbricazione = StringField('Data Fabbricazione (MM/YYYY)', validators=[
        DataRequired(message="La data di fabbricazione è obbligatoria")
    ])
    
    data_installazione = DateField('Data Installazione', format='%Y-%m-%d', 
                                 validators=[DataRequired(message="La data di installazione è obbligatoria")])
    
    data_controllo = DateField('Data Controllo', format='%Y-%m-%d', 
                              validators=[DataRequired(message="La data di controllo è obbligatoria")])
    
    data_revisione = DateField('Data Revisione', format='%Y-%m-%d', validators=[Optional()])
    
    data_collaudo = DateField('Data Collaudo', format='%Y-%m-%d', validators=[Optional()])
    
    stato = SelectField('Stato', validators=[DataRequired()], choices=[
        ('Attivo', 'Attivo'),
        ('In manutenzione', 'In manutenzione')
    ])
    
    # Campi opzionali
    coordinate = StringField('Coordinate', validators=[Optional()])
    note = TextAreaField('Note', validators=[Optional()])
    
    submit = SubmitField('Salva Estintore')
    
    def validate_data_fabbricazione(self, field):
        """Validazione formato data fabbricazione (MM/YYYY)"""
        if not re.match(r'^(0[1-9]|1[0-2])\/[0-9]{4}$', field.data):
            raise ValidationError('Formato data non valido. Utilizzare MM/YYYY (es: 05/2023)')
    
    def validate_matricola(self, field):
        """Verifica che non esista già la matricola (deve essere unica)"""
        if self.estintore_id.data:
            estintore = Estintore.query.filter(
                Estintore.matricola == field.data, 
                Estintore.id != int(self.estintore_id.data)
            ).first()
        else:
            estintore = Estintore.query.filter(Estintore.matricola == field.data).first()
        
        if estintore:
            raise ValidationError('Questa matricola è già registrata')
            
    def validate_capacita(self, field):
        """Verifica che la capacità sia valida per il tipo di estintore"""
        if not hasattr(self, 'tipologia') or not self.tipologia.data:
            return
        
        # Ottieni le capacità valide per la tipologia
        capacita_valide = Estintore.CAPACITA_PER_TIPOLOGIA.get(self.tipologia.data, [])
        
        # Se il campo è vuoto o non è tra le capacità valide
        if not field.data or field.data not in capacita_valide:
            raise ValidationError(f'Capacità non valida per estintore di tipo {self.tipologia.data}')
        

            
        return True

# Route per la lista estintori
@estintori_bp.route('/')
def index():
    """Visualizza la lista di tutti gli estintori"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtri
    cliente_id = request.args.get('cliente_id', None, type=int)
    tipologia = request.args.get('tipologia', None)
    stato = request.args.get('stato', None)
    search = request.args.get('search', '')
    
    query = Estintore.query.join(Cliente)
    
    # Applica i filtri
    if cliente_id:
        query = query.filter(Estintore.cliente_id == cliente_id)
    
    if tipologia:
        query = query.filter(Estintore.tipologia == tipologia)
    
    if stato:
        query = query.filter(Estintore.stato == stato)
    
    if search:
        query = query.filter(
            or_(
                Estintore.matricola.ilike(f'%{search}%'),
                Estintore.dislocazione.ilike(f'%{search}%'),
                Cliente.azienda.ilike(f'%{search}%')
            )
        )
    
    # Ordinamento
    sort_by = request.args.get('sort_by', 'cliente')
    order = request.args.get('order', 'asc')
    
    # Gestione ordinamento con join
    if sort_by == 'cliente':
        if order == 'asc':
            query = query.order_by(Cliente.azienda.asc())
        else:
            query = query.order_by(Cliente.azienda.desc())
    else:
        if order == 'asc':
            query = query.order_by(getattr(Estintore, sort_by).asc())
        else:
            query = query.order_by(getattr(Estintore, sort_by).desc())
    
    # Paginazione
    estintori = query.paginate(page=page, per_page=per_page)
    
    # Ottieni il cliente se filtrato
    cliente_filtrato = None
    if cliente_id:
        cliente_filtrato = Cliente.query.get_or_404(cliente_id)
    
    # Ottieni tutte le tipologie per il filtro
    tipologie = db.session.query(Estintore.tipologia).distinct().all()
    tipologie = [t[0] for t in tipologie]
    
    # Lista clienti per il filtro
    clienti = Cliente.query.order_by(Cliente.azienda).all()
    
    # Data attuale per i calcoli di scadenza
    from datetime import datetime
    oggi = datetime.now()
    
    return render_template('estintori/index.html', 
                          estintori=estintori, 
                          search=search,
                          sort_by=sort_by,
                          order=order,
                          cliente_id=cliente_id,
                          cliente_filtrato=cliente_filtrato,
                          tipologie=tipologie,
                          tipologia_filtrata=tipologia,
                          stato_filtrato=stato,
                          clienti=clienti,
                          now=oggi)

# Route per creare un nuovo estintore
@estintori_bp.route('/nuovo', methods=['GET', 'POST'])
def nuovo():
    """Crea un nuovo estintore o duplica uno esistente"""
    # Inizializziamo il form
    form = EstintoreForm()
    
    # Prendiamo il cliente_id dalla query string (se presente)
    cliente_id = request.args.get('cliente_id', None, type=int)
    cliente = None
    next_postazione = None  # Aggiungiamo la variabile per la prossima postazione
    
    # Verifica se stiamo duplicando un estintore esistente
    duplica_da_id = request.args.get('duplica_da', None, type=int)
    suffisso_nuovo = request.args.get('suffisso', None)
    
    # Se stiamo duplicando e siamo in GET, pre-popoliamo il form
    if duplica_da_id and request.method == 'GET':
        # Otteniamo l'estintore originale
        estintore_orig = Estintore.query.get_or_404(duplica_da_id)
        
        # Prepopoliamo il form con i dati dell'estintore originale
        form.cliente_id.data = estintore_orig.cliente_id
        form.tipologia.data = estintore_orig.tipologia
        form.marca.data = estintore_orig.marca
        form.dislocazione.data = estintore_orig.dislocazione
        form.capacita.data = estintore_orig.capacita
        form.data_fabbricazione.data = estintore_orig.data_fabbricazione
        form.data_installazione.data = estintore_orig.data_installazione
        form.data_controllo.data = estintore_orig.data_controllo
        form.data_revisione.data = estintore_orig.data_revisione
        form.data_collaudo.data = estintore_orig.data_collaudo
        form.stato.data = estintore_orig.stato
        form.coordinate.data = estintore_orig.coordinate
        form.note.data = estintore_orig.note
        
        # Lascia la matricola vuota perché deve essere unica
        form.matricola.data = ""
        
        # Imposta il suffisso se fornito
        if hasattr(form, 'suffisso_postazione'):
            form.suffisso_postazione.data = suffisso_nuovo
        
        # Prendiamo il cliente
        cliente_id = estintore_orig.cliente_id
        cliente = Cliente.query.get_or_404(cliente_id)
    
    if cliente_id:
        cliente = Cliente.query.get_or_404(cliente_id)
        form.cliente_id.data = cliente_id
        # Calcoliamo la prossima postazione
        next_postazione = Estintore.get_next_postazione(cliente_id)
    
    # Popoliamo le scelte per la capacità in base alla tipologia
    if form.tipologia.data:
        capacita_opzioni = Estintore.CAPACITA_PER_TIPOLOGIA.get(form.tipologia.data, [])
        form.capacita.choices = [(cap, cap) for cap in capacita_opzioni]
    else:
        form.capacita.choices = []
    
    # Gestiamo il submit del form
    if request.method == 'POST':
        # Prima di validare, impostiamo le opzioni di capacità in base alla tipologia selezionata
        if form.tipologia.data:
            capacita_opzioni = Estintore.CAPACITA_PER_TIPOLOGIA.get(form.tipologia.data, [])
            form.capacita.choices = [(cap, cap) for cap in capacita_opzioni]
        
        if form.validate_on_submit():
            # Gestione data di collaudo - controllo più stringente
            data_collaudo_valida = True
            
            if form.data_collaudo.data:
                try:
                    # Verifica se la data è valida
                    data_collaudo = form.data_collaudo.data
                    if not isinstance(data_collaudo, date):
                        raise ValueError("Non è una data valida")
                        
                    # Verifica se l'anno è in un range ragionevole
                    if data_collaudo.year < 2000 or data_collaudo.year > 2100:
                        raise ValueError("Anno fuori range")
                        
                    # Controllo aggiuntivo: conversione e riconversione
                    data_collaudo_str = data_collaudo.strftime('%Y-%m-%d')
                    _ = datetime.strptime(data_collaudo_str, '%Y-%m-%d').date()
                except Exception as e:
                    data_collaudo_valida = False
                    flash(f'Data di collaudo non valida: {str(e)}. Utilizzare il formato YYYY-MM-DD', 'danger')
            
            if not data_collaudo_valida:
                return render_template('estintori/form.html', 
                                  form=form, 
                                  title='Nuovo Estintore' if not duplica_da_id else 'Duplica Estintore', 
                                  cliente_id=cliente_id,
                                  cliente=cliente,
                                  next_postazione=next_postazione)
            
            # Calcola automaticamente la data di controllo in base al tipo di cliente
            if form.data_installazione.data:
                # Ottieni il cliente
                cliente_per_calcolo = Cliente.query.get(form.cliente_id.data)
            
                # Calcola la data di controllo in base al tipo di cliente
                from datetime import timedelta
                if cliente_per_calcolo and cliente_per_calcolo.tipologia == "Stagionale":
                    # Cliente stagionale: 12 mesi
                    data_controllo = form.data_installazione.data + timedelta(days=365)  # circa 12 mesi
                else:
                    # Altri clienti: 6 mesi
                    data_controllo = form.data_installazione.data + timedelta(days=182)  # circa 6 mesi
    
                # Imposta la data di controllo nel form se non è già stata impostata dall'utente
                if not form.data_controllo.data:
                    form.data_controllo.data = data_controllo
            
            # Se tutto è valido, creiamo il nuovo estintore
            cliente = Cliente.query.get_or_404(int(form.cliente_id.data))
            
            # Se stiamo duplicando, utilizza la stessa postazione dell'originale
            if duplica_da_id:
                estintore_orig = Estintore.query.get_or_404(duplica_da_id)
                postazione = estintore_orig.postazione
                
                # Aggiungi dati al messaggio flash
                messaggio_extra = f" (duplicato dall'estintore {estintore_orig.matricola}, postazione {postazione})"
            else:
                # Otteniamo il prossimo numero di postazione
                postazione = Estintore.get_next_postazione(cliente.id)
                messaggio_extra = ""
            
            # Creiamo l'estintore
            estintore = Estintore(
                cliente_id=cliente.id,
                tipologia=form.tipologia.data,
                marca=form.marca.data,
                matricola=form.matricola.data,
                dislocazione=form.dislocazione.data,
                postazione=postazione,
                capacita=form.capacita.data,
                data_fabbricazione=form.data_fabbricazione.data,
                data_installazione=form.data_installazione.data,
                data_controllo=form.data_controllo.data,
                data_revisione=form.data_revisione.data if form.data_revisione.data else None,
                data_collaudo=form.data_collaudo.data if form.data_collaudo.data else None,
                stato=form.stato.data,
                coordinate=form.coordinate.data,
                note=form.note.data
            )
            
            # Aggiungi il suffisso se disponibile
            if hasattr(form, 'suffisso_postazione') and form.suffisso_postazione.data:
                estintore.suffisso_postazione = form.suffisso_postazione.data
            elif suffisso_nuovo and duplica_da_id:
                # Se stiamo duplicando, usa il suffisso calcolato
                estintore.suffisso_postazione = suffisso_nuovo
            
            db.session.add(estintore)
            db.session.commit()
            
            # Registrazione nel log
            Log.log_estintore('creazione', estintore, utente='admin')  # In futuro sostituire con utente reale
            
            flash(f'Estintore {estintore.tipologia} - {estintore.matricola} creato con successo!{messaggio_extra}', 'success')
            
            # Redirect alla lista estintori del cliente
            return redirect(url_for('estintori.index', cliente_id=cliente.id))
    
    # Prepopoliamo la data di installazione con la data corrente
    if not form.data_installazione.data:
        form.data_installazione.data = datetime.now().date()
    
    # Prepopoliamo la data di controllo (in base al tipo di cliente)
    if not form.data_controllo.data:
        from datetime import timedelta as td
        cliente_per_calcolo = Cliente.query.get(form.cliente_id.data)
        if cliente_per_calcolo and cliente_per_calcolo.tipologia == "Stagionale":
            # Cliente stagionale: 12 mesi
            form.data_controllo.data = form.data_installazione.data + td(days=365)  # circa 12 mesi
        else:
            # Altri clienti: 6 mesi
            form.data_controllo.data = form.data_installazione.data + td(days=182)  # circa 6 mesi
    
    return render_template('estintori/form.html', 
                          form=form, 
                          title='Nuovo Estintore' if not duplica_da_id else 'Duplica Estintore', 
                          cliente_id=cliente_id,
                          cliente=cliente,
                          next_postazione=next_postazione)

# Route per visualizzare un estintore
@estintori_bp.route('/<int:id>')
def visualizza(id):
    """Visualizza i dettagli di un estintore"""
    estintore = Estintore.query.get_or_404(id)
    cliente = Cliente.query.get_or_404(estintore.cliente_id)
    
    # Ottieni i log per questo estintore
    logs = Log.query.filter_by(estintore_id=id).order_by(Log.data_ora.desc()).limit(10).all()
    
    return render_template('estintori/visualizza.html', 
                          estintore=estintore,
                          cliente=cliente,
                          logs=logs,
                          now=datetime.now())


# Route per modificare un estintore
@estintori_bp.route('/modifica/<int:id>', methods=['GET', 'POST'])
def modifica(id):
    """Modifica un estintore esistente"""
    estintore = Estintore.query.get_or_404(id)
    cliente = Cliente.query.get_or_404(estintore.cliente_id)
    
    form = EstintoreForm(obj=estintore)
    form.estintore_id.data = estintore.id
    form.cliente_id.data = estintore.cliente_id
    
    # Popoliamo le capacità in base alla tipologia
    if form.tipologia.data:
        capacita_opzioni = Estintore.CAPACITA_PER_TIPOLOGIA.get(form.tipologia.data, [])
        form.capacita.choices = [(cap, cap) for cap in capacita_opzioni]
    else:
        form.capacita.choices = []
    
    if request.method == 'POST':
        # Prima di validare, impostiamo le opzioni di capacità in base alla tipologia selezionata
        if form.tipologia.data:
            capacita_opzioni = Estintore.CAPACITA_PER_TIPOLOGIA.get(form.tipologia.data, [])
            form.capacita.choices = [(cap, cap) for cap in capacita_opzioni]
        
        if form.validate_on_submit():
            # Gestione data di collaudo - controllo più stringente
            data_collaudo_valida = True
            
            if form.data_collaudo.data:
                try:
                    # Verifica se la data è valida
                    data_collaudo = form.data_collaudo.data
                    if not isinstance(data_collaudo, date):
                        raise ValueError("Non è una data valida")
                        
                    # Verifica se l'anno è in un range ragionevole
                    if data_collaudo.year < 2000 or data_collaudo.year > 2100:
                        raise ValueError("Anno fuori range")
                        
                    # Controllo aggiuntivo: conversione e riconversione
                    data_collaudo_str = data_collaudo.strftime('%Y-%m-%d')
                    _ = datetime.strptime(data_collaudo_str, '%Y-%m-%d').date()
                except Exception as e:
                    data_collaudo_valida = False
                    flash(f'Data di collaudo non valida: {str(e)}. Utilizzare il formato YYYY-MM-DD', 'danger')
            
            if not data_collaudo_valida:
                return render_template('estintori/form.html', 
                                  form=form, 
                                  estintore=estintore, 
                                  cliente=cliente,
                                  cliente_id=cliente.id,
                                  title='Modifica Estintore')
            
            # Salva i vecchi valori per il log
            vecchi_valori = estintore.to_dict()
            
            # Controlla se la data di installazione è stata modificata
            data_installazione_modificata = estintore.data_installazione != form.data_installazione.data
            
            # Se la data di installazione è stata modificata, ricalcola la data di controllo
            # in base al tipo di cliente (fisso o stagionale)
            if data_installazione_modificata:
                # Calcola automaticamente la data di controllo in base al tipo di cliente
                from datetime import timedelta
                if cliente.tipologia == "Stagionale":
                    # Cliente stagionale: 12 mesi
                    form.data_controllo.data = form.data_installazione.data + timedelta(days=365)  # circa 12 mesi
                else:
                    # Altri clienti: 6 mesi
                    form.data_controllo.data = form.data_installazione.data + timedelta(days=182)  # circa 6 mesi
            
            # Aggiorna i valori
            estintore.tipologia = form.tipologia.data
            estintore.marca = form.marca.data
            estintore.matricola = form.matricola.data
            estintore.dislocazione = form.dislocazione.data
            estintore.capacita = form.capacita.data
            estintore.data_fabbricazione = form.data_fabbricazione.data
            estintore.data_installazione = form.data_installazione.data
            estintore.data_controllo = form.data_controllo.data
            estintore.data_revisione = form.data_revisione.data if form.data_revisione.data else None
            estintore.data_collaudo = form.data_collaudo.data if form.data_collaudo.data else None
            estintore.stato = form.stato.data
            estintore.coordinate = form.coordinate.data
            estintore.note = form.note.data
            
            db.session.commit()
            
            # Prima di registrare il log, assicurati che il cliente sia caricato
            if not hasattr(estintore, 'cliente') or not estintore.cliente:
                estintore.cliente = Cliente.query.get(estintore.cliente_id)
            
            # Registrazione nel log
            Log.log_estintore('modifica', estintore, vecchi_valori=vecchi_valori, utente='admin')
            
            flash(f'Estintore {estintore.tipologia} - {estintore.matricola} aggiornato con successo!', 'success')
            return redirect(url_for('estintori.visualizza', id=estintore.id))
    
    return render_template('estintori/form.html', 
                          form=form, 
                          estintore=estintore, 
                          cliente=cliente,
                          cliente_id=cliente.id,
                          title='Modifica Estintore')

# Route per eliminare un estintore
@estintori_bp.route('/elimina/<int:id>', methods=['POST'])
def elimina(id):
    """Elimina un estintore"""
    estintore = Estintore.query.get_or_404(id)
    cliente_id = estintore.cliente_id
    
    # Carica il cliente per assicurarsi che le informazioni siano disponibili per il log
    cliente = Cliente.query.get(cliente_id)
    
    # Associa il cliente all'estintore (se non è già caricato)
    if not hasattr(estintore, 'cliente') or not estintore.cliente:
        estintore.cliente = cliente
    
    # Salva i dati dell'estintore prima dell'eliminazione per il log
    estintore_dati = estintore.to_dict()
    
    # Mantieni il riferimento alla matricola e tipologia per il messaggio flash
    matricola = estintore.matricola
    tipologia = estintore.tipologia
    
    # Elimina l'estintore
    db.session.delete(estintore)
    db.session.commit()
    
    # Crea un log utilizzando la funzione log_estintore statica
    # che abbiamo già corretto in precedenza
    log = Log(
        azione='eliminazione',
        dettagli={
            'estintore': estintore_dati,
            'cliente_info': {
                'id': cliente_id,
                'azienda': cliente.azienda if cliente else 'N/D'
            },
            'tipo_eliminazione': 'estintore'  # Aggiungiamo un flag esplicito
        },
        estintore_id=None,  # L'estintore non esiste più
        cliente_id=cliente_id,  # Assicurati che sia associato al cliente
        utente='admin'  # In futuro sostituire con utente reale
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Estintore {tipologia} - {matricola} eliminato con successo!', 'success')
    
    # Redirect alla pagina degli estintori del cliente
    if cliente_id:
        return redirect(url_for('estintori.index', cliente_id=cliente_id))
    else:
        return redirect(url_for('estintori.index'))

# API per ottenere le capacità per tipologia
@estintori_bp.route('/api/capacita/<tipologia>')
def api_capacita(tipologia):
    """API per ottenere le capacità disponibili per una tipologia di estintore"""
    capacita = Estintore.CAPACITA_PER_TIPOLOGIA.get(tipologia, [])
    return jsonify([{'id': c, 'text': c} for c in capacita])



# Route per la pagina delle scadenze
@estintori_bp.route('/scadenze')
def scadenze():
    """Visualizza gli estintori in scadenza"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Ottieni la data corrente
    oggi = datetime.now().date()
    
    # Filtri
    periodo = request.args.get('periodo', 'prossimi30')
    cliente_id = request.args.get('cliente_id', None, type=int)
    tipo_scadenza = request.args.get('tipo_scadenza', 'tutto')
    tipo_cliente = request.args.get('tipo_cliente', 'tutti')
    zona = request.args.get('zona', 'tutte')
    
    # Nuovi filtri per data
    data_inizio_str = request.args.get('data_inizio', '')
    data_fine_str = request.args.get('data_fine', '')
    
    data_inizio = None
    data_fine = None
    
    # Conversione delle date se presenti e non vuote
    if data_inizio_str and data_inizio_str.strip():
        try:
            data_inizio = datetime.strptime(data_inizio_str, '%Y-%m-%d').date()
        except ValueError:
            # Solo se la stringa non è vuota e il formato è sbagliato, mostriamo l'errore
            if data_inizio_str.strip():
                flash('Formato data inizio non valido', 'warning')
            data_inizio_str = ''
    
    if data_fine_str and data_fine_str.strip():
        try:
            data_fine = datetime.strptime(data_fine_str, '%Y-%m-%d').date()
        except ValueError:
            # Solo se la stringa non è vuota e il formato è sbagliato, mostriamo l'errore
            if data_fine_str.strip():
                flash('Formato data fine non valido', 'warning')
            data_fine_str = ''
    
    # Costruisci la query base
    query = Estintore.query.join(Cliente)
    
    # Applica il filtro per cliente
    if cliente_id:
        query = query.filter(Estintore.cliente_id == cliente_id)
    
    # Applica il filtro per tipo di cliente
    if tipo_cliente != 'tutti':
        query = query.filter(Cliente.tipologia == tipo_cliente)
    
    # Applica il filtro per zona
    if zona != 'tutte' and zona:
        query = query.filter(Cliente.zona == zona)
    
    # Se sono specificate entrambe le date, usa l'intervallo personalizzato
    if data_inizio and data_fine:
        if tipo_scadenza == 'tutto':
            query = query.filter(or_(
                and_(Estintore.data_controllo >= data_inizio, Estintore.data_controllo <= data_fine),
                and_(Estintore.data_revisione >= data_inizio, Estintore.data_revisione <= data_fine),
                and_(Estintore.data_collaudo >= data_inizio, Estintore.data_collaudo <= data_fine)
            ))
        else:
            # Applica il filtro per tipo di scadenza
            if tipo_scadenza == 'controllo':
                data_campo = Estintore.data_controllo
            elif tipo_scadenza == 'revisione':
                data_campo = Estintore.data_revisione
            elif tipo_scadenza == 'collaudo':
                data_campo = Estintore.data_collaudo
            
            query = query.filter(and_(data_campo >= data_inizio, data_campo <= data_fine))
    
    # Altrimenti applica il filtro per periodo predefinito
    elif not (data_inizio or data_fine):
        if tipo_scadenza == 'tutto':
            if periodo == 'scaduti':
                query = query.filter(or_(
                    Estintore.data_controllo < oggi,
                    Estintore.data_revisione < oggi,
                    Estintore.data_collaudo < oggi
                ))
            elif periodo == 'prossimi30':
                data_limite = oggi + timedelta(days=30)
                query = query.filter(or_(
                    and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= data_limite),
                    and_(Estintore.data_revisione >= oggi, Estintore.data_revisione <= data_limite),
                    and_(Estintore.data_collaudo >= oggi, Estintore.data_collaudo <= data_limite)
                ))
            elif periodo == 'prossimi60':
                data_limite = oggi + timedelta(days=60)
                query = query.filter(or_(
                    and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= data_limite),
                    and_(Estintore.data_revisione >= oggi, Estintore.data_revisione <= data_limite),
                    and_(Estintore.data_collaudo >= oggi, Estintore.data_collaudo <= data_limite)
                ))
            elif periodo == 'prossimi90':
                data_limite = oggi + timedelta(days=90)
                query = query.filter(or_(
                    and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= data_limite),
                    and_(Estintore.data_revisione >= oggi, Estintore.data_revisione <= data_limite),
                    and_(Estintore.data_collaudo >= oggi, Estintore.data_collaudo <= data_limite)
                ))
            elif periodo == 'prossimi180':
                data_limite = oggi + timedelta(days=180)
                query = query.filter(or_(
                    and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= data_limite),
                    and_(Estintore.data_revisione >= oggi, Estintore.data_revisione <= data_limite),
                    and_(Estintore.data_collaudo >= oggi, Estintore.data_collaudo <= data_limite)
                ))
        else:
            # Applica il filtro per tipo di scadenza
            if tipo_scadenza == 'controllo':
                data_campo = Estintore.data_controllo
            elif tipo_scadenza == 'revisione':
                data_campo = Estintore.data_revisione
            elif tipo_scadenza == 'collaudo':
                data_campo = Estintore.data_collaudo
            
            if periodo == 'scaduti':
                query = query.filter(data_campo < oggi)
            elif periodo == 'prossimi30':
                data_limite = oggi + timedelta(days=30)
                query = query.filter(and_(data_campo >= oggi, data_campo <= data_limite))
            elif periodo == 'prossimi60':
                data_limite = oggi + timedelta(days=60)
                query = query.filter(and_(data_campo >= oggi, data_campo <= data_limite))
            elif periodo == 'prossimi90':
                data_limite = oggi + timedelta(days=90)
                query = query.filter(and_(data_campo >= oggi, data_campo <= data_limite))
            elif periodo == 'prossimi180':
                data_limite = oggi + timedelta(days=180)
                query = query.filter(and_(data_campo >= oggi, data_campo <= data_limite))
    
    # Se è specificata solo una data, usa quella come filtro
    elif data_inizio:
        if tipo_scadenza == 'tutto':
            query = query.filter(or_(
                Estintore.data_controllo >= data_inizio,
                Estintore.data_revisione >= data_inizio,
                Estintore.data_collaudo >= data_inizio
            ))
        else:
            # Applica il filtro per tipo di scadenza
            if tipo_scadenza == 'controllo':
                data_campo = Estintore.data_controllo
            elif tipo_scadenza == 'revisione':
                data_campo = Estintore.data_revisione
            elif tipo_scadenza == 'collaudo':
                data_campo = Estintore.data_collaudo
            
            query = query.filter(data_campo >= data_inizio)
    
    elif data_fine:
        if tipo_scadenza == 'tutto':
            query = query.filter(or_(
                Estintore.data_controllo <= data_fine,
                Estintore.data_revisione <= data_fine,
                Estintore.data_collaudo <= data_fine
            ))
        else:
            # Applica il filtro per tipo di scadenza
            if tipo_scadenza == 'controllo':
                data_campo = Estintore.data_controllo
            elif tipo_scadenza == 'revisione':
                data_campo = Estintore.data_revisione
            elif tipo_scadenza == 'collaudo':
                data_campo = Estintore.data_collaudo
                
            query = query.filter(data_campo <= data_fine)
    
    # Ordinamento
    # Per il tipo "tutto", ordiniamo per la data più vicina tra le tre
    if tipo_scadenza == 'tutto':
        # Prima ordina per cliente e poi per postazione
        query = query.order_by(Cliente.azienda.asc(), 
                              Estintore.postazione.asc(),
                              Estintore.data_controllo.asc(), 
                              Estintore.data_revisione.asc(), 
                              Estintore.data_collaudo.asc())
    else:
        # Applica il filtro per tipo di scadenza
        if tipo_scadenza == 'controllo':
            data_campo = Estintore.data_controllo
        elif tipo_scadenza == 'revisione':
            data_campo = Estintore.data_revisione
        elif tipo_scadenza == 'collaudo':
            data_campo = Estintore.data_collaudo
        
        # Prima ordina per cliente e postazione, poi per data specifica
        query = query.order_by(Cliente.azienda.asc(),
                              Estintore.postazione.asc(), 
                              data_campo.asc())
    
    # Paginazione
    estintori = query.paginate(page=page, per_page=per_page)
    
    # Ottieni il cliente se filtrato
    cliente_filtrato = None
    if cliente_id:
        cliente_filtrato = Cliente.query.get_or_404(cliente_id)
    
    # Ottieni tutti i clienti per il filtro
    clienti = Cliente.query.order_by(Cliente.azienda).all()
    
    # Ottieni tutte le zone per il filtro
    zone = db.session.query(Cliente.zona).distinct().order_by(Cliente.zona).all()
    
    return render_template('estintori/scadenze.html', 
                          estintori=estintori,
                          periodo=periodo,
                          cliente_id=cliente_id,
                          cliente_filtrato=cliente_filtrato,
                          clienti=clienti,
                          tipo_scadenza=tipo_scadenza,
                          tipo_cliente=tipo_cliente,
                          zona=zona,
                          zone=zone,
                          oggi=oggi,
                          data_inizio=data_inizio_str,
                          data_fine=data_fine_str)

# Route per la pagina dei log
@estintori_bp.route('/logs')
def logs():
    """Visualizza i log del sistema"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtri
    azione = request.args.get('azione', None)
    cliente_id = request.args.get('cliente_id', None, type=int)
    
    query = Log.query.order_by(Log.data_ora.desc())
    
    # Applica i filtri
    if azione:
        query = query.filter(Log.azione == azione)
    
    if cliente_id:
        query = query.filter(Log.cliente_id == cliente_id)
    
    # Paginazione
    logs = query.paginate(page=page, per_page=per_page)
    
    # Ottieni il cliente se filtrato
    cliente_filtrato = None
    if cliente_id:
        cliente_filtrato = Cliente.query.get_or_404(cliente_id)
    
    # Ottieni tutti i clienti per il filtro
    clienti = Cliente.query.order_by(Cliente.azienda).all()
    
    # Ottieni tutte le azioni per il filtro
    azioni = db.session.query(Log.azione).distinct().all()
    azioni = [a[0] for a in azioni]
    
    return render_template('estintori/logs.html', 
                          logs=logs,
                          azione=azione,
                          cliente_id=cliente_id,
                          cliente_filtrato=cliente_filtrato,
                          clienti=clienti,
                          azioni=azioni)

@estintori_bp.route('/report')
def report():
    tipo = request.args.get('tipo', '')
    
    if tipo == 'clienti_scadenze_custom':
        data_inizio = datetime.strptime(request.args.get('data_inizio'), '%Y-%m-%d')
        data_fine = datetime.strptime(request.args.get('data_fine'), '%Y-%m-%d')
        tipo_scadenza = request.args.get('tipo_scadenza', 'tutto')
        cliente_id = request.args.get('cliente_id', '')
        tipo_cliente = request.args.get('tipo_cliente', 'tutti')
        zona = request.args.get('zona', 'tutte')
        
        # Chiamiamo la funzione che genera questo tipo di report
        return generate_clienti_scadenze_custom_report()
    
    elif tipo == 'clienti_scadenze':
        periodo = request.args.get('periodo', 'prossimi30')
        return generate_clienti_scadenze_report(periodo)
    
    elif tipo == 'lista_controllo':
        cliente_id = request.args.get('cliente_id')
        con_scadenze = request.args.get('con_scadenze') == 'on'
        return generate_lista_controllo(cliente_id, con_scadenze)
    
    elif tipo == 'estintori_cliente':
        cliente_id = request.args.get('cliente_id')
        scadenze = request.args.get('scadenze') == 'on'
        formato = request.args.get('formato', 'pdf')
        return generate_estintori_cliente_report(cliente_id, scadenze, formato)
    
    # Caso di default - mostra la pagina di selezione dei report
    return render_template('estintori/report.html', 
                          clienti=Cliente.query.order_by(Cliente.azienda).all(),
                          zone=db.session.query(Cliente.zona).distinct().order_by(Cliente.zona).all())

      
import qrcode
import io
from flask import send_file

@estintori_bp.route('/<int:id>/qrcode')
def generate_qrcode(id):
    """Genera un QR code per l'estintore"""
    estintore = Estintore.query.get_or_404(id)
    cliente = Cliente.query.get_or_404(estintore.cliente_id)
    
    # Se è richiesto solo l'immagine QR
    if request.args.get('img_only') == '1':
        # Dati da inserire nel QR code
        qr_data = f"""
        ID: {estintore.id}
        Matricola: {estintore.matricola}
        Tipologia: {estintore.tipologia} {estintore.capacita}
        Cliente: {cliente.azienda}
        Dislocazione: {estintore.dislocazione}
        Data Controllo: {estintore.data_controllo.strftime('%d/%m/%Y')}
        """
        
        # Genera QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converti l'immagine in bytes per inviarla come risposta HTTP
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    
    # Altrimenti, mostra la pagina con il QR code
    return render_template('estintori/qrcode.html', 
                           estintore=estintore, 
                           cliente=cliente)

@estintori_bp.route('/aggiorna-scadenze-multiplo', methods=['POST'])
def aggiorna_scadenze_multiplo():
    """Aggiorna le date di scadenza di più estintori contemporaneamente"""
    # Ottieni gli ID degli estintori selezionati
    selected_ids = request.form.getlist('selected_ids[]')
    
    if not selected_ids:
        flash('Nessun estintore selezionato', 'warning')
        return redirect(url_for('estintori.scadenze'))
    
    estintori_aggiornati = 0
    
    for estintore_id in selected_ids:
        estintore = Estintore.query.get(estintore_id)
        if not estintore:
            continue
        
        # Salva i vecchi valori per il log
        vecchi_valori = estintore.to_dict()
        modificato = False
        
        # Controlla se c'è stato un aggiornamento della data di controllo
        data_controllo_str = request.form.get(f'data_controllo_{estintore_id}')
        if data_controllo_str:
            try:
                data_controllo = datetime.strptime(data_controllo_str, '%Y-%m-%d').date()
                if data_controllo != estintore.data_controllo:
                    estintore.data_controllo = data_controllo
                    modificato = True
            except ValueError:
                flash(f'Formato data controllo non valido per estintore ID {estintore_id}. Valore non aggiornato.', 'warning')
        
        # Controlla se c'è stato un aggiornamento della data di revisione
        data_revisione_str = request.form.get(f'data_revisione_{estintore_id}')
        if data_revisione_str:
            try:
                data_revisione = datetime.strptime(data_revisione_str, '%Y-%m-%d').date()
                if estintore.data_revisione != data_revisione:
                    estintore.data_revisione = data_revisione
                    modificato = True
            except ValueError:
                flash(f'Formato data revisione non valido per estintore ID {estintore_id}. Valore rimosso.', 'warning')
                estintore.data_revisione = None
                if estintore.data_revisione is not None:
                    modificato = True
        elif request.form.get(f'data_revisione_{estintore_id}') == '' and estintore.data_revisione is not None:
            estintore.data_revisione = None
            modificato = True
        
        # Controlla se c'è stato un aggiornamento della data di collaudo
        data_collaudo_str = request.form.get(f'data_collaudo_{estintore_id}')
        if data_collaudo_str:
            try:
                data_collaudo = datetime.strptime(data_collaudo_str, '%Y-%m-%d').date()
                if estintore.data_collaudo != data_collaudo:
                    estintore.data_collaudo = data_collaudo
                    modificato = True
            except ValueError:
                flash(f'Formato data collaudo non valido per estintore ID {estintore_id}. Valore rimosso.', 'warning')
                estintore.data_collaudo = None
                if estintore.data_collaudo is not None:
                    modificato = True
        elif request.form.get(f'data_collaudo_{estintore_id}') == '' and estintore.data_collaudo is not None:
            estintore.data_collaudo = None
            modificato = True
        
        # Controlla se c'è stato un aggiornamento dello stato
        stato = request.form.get(f'stato_{estintore_id}')
        if stato and stato != estintore.stato:
            estintore.stato = stato
            modificato = True
        
        # Se c'è stata almeno una modifica, aggiorna l'estintore e crea un log
        if modificato:
            # Carica cliente esplicitamente prima
            cliente = Cliente.query.get(estintore.cliente_id)
            
            # Prepara il dettaglio delle modifiche
            campi_modificati = []
            nuovo_dict = estintore.to_dict()
            
            for campo, valore_vecchio in vecchi_valori.items():
                if campo in nuovo_dict and nuovo_dict[campo] != valore_vecchio:
                    campi_modificati.append({
                        'campo': campo,
                        'vecchio': valore_vecchio,
                        'nuovo': nuovo_dict[campo]
                    })
            
            # Commit delle modifiche all'estintore
            db.session.commit()
            
            # Crea manualmente il log con dettagli completi
            log = Log(
                azione='modifica',
                dettagli={
                    'estintore': nuovo_dict,
                    'vecchi_valori': vecchi_valori,
                    'campi_modificati': campi_modificati,
                    'cliente_info': {
                        'id': estintore.cliente_id,
                        'azienda': cliente.azienda if cliente else 'Cliente non trovato'
                    }
                },
                estintore_id=estintore.id,
                cliente_id=estintore.cliente_id,
                utente='admin'
            )
            db.session.add(log)
            db.session.commit()
            
            estintori_aggiornati += 1
    
    # Mostra un messaggio con il numero di estintori aggiornati
    if estintori_aggiornati > 0:
        flash(f'{estintori_aggiornati} estintori aggiornati con successo!', 'success')
    else:
        flash('Nessun estintore è stato modificato', 'info')
    
    # Ottieni tutti i parametri dalla richiesta (sia GET che POST)
    # I parametri potrebbero essere in request.args (GET) o in un campo nascosto del form (POST)
    params = {}
    
    # Parametri da mantenere nel redirect
    param_names = ['periodo', 'cliente_id', 'tipo_scadenza', 'tipo_cliente', 'data_inizio', 'data_fine', 'page']
    
    # Prima controlla nei parametri POST (il form potrebbe aver inviato parametri nascosti)
    for param in param_names:
        if param in request.form:
            params[param] = request.form.get(param)
    
    # Poi controlla nei parametri GET (URL)
    for param in param_names:
        if param in request.args and param not in params:
            params[param] = request.args.get(param)
    
    # Se c'è un referer, estrai anche i parametri da lì
    referer = request.headers.get('Referer', '')
    if referer and '?' in referer:
        query_string = referer.split('?')[1]
        referer_params = {}
        for kv_pair in query_string.split('&'):
            if '=' in kv_pair:
                k, v = kv_pair.split('=', 1)
                referer_params[k] = v
        
        # Integra i parametri dal referer
        for param in param_names:
            if param in referer_params and param not in params:
                params[param] = referer_params[param]
    
    # Costruisci l'URL di redirect con tutti i parametri
    return redirect(url_for('estintori.scadenze', **params))
    
@estintori_bp.route('/duplica/<int:id>')
def duplica(id):
    """Duplica un estintore esistente con un nuovo suffisso"""
    # Ottieni l'estintore originale
    estintore_orig = Estintore.query.get_or_404(id)
    cliente = Cliente.query.get_or_404(estintore_orig.cliente_id)
    
    # Definisci i possibili suffissi
    suffissi = ['A', 'B', 'C', 'D', 'E', 'bis']
    
    # Cerca estintori con la stessa postazione
    estintori_stessa_postazione = Estintore.query.filter_by(
        cliente_id=estintore_orig.cliente_id, 
        postazione=estintore_orig.postazione
    ).all()
    
    # Raccogli i suffissi già usati
    suffissi_usati = [e.suffisso_postazione for e in estintori_stessa_postazione 
                     if e.suffisso_postazione]
    
    # Trova il primo suffisso non usato
    suffisso_nuovo = None
    for s in suffissi:
        if s not in suffissi_usati:
            suffisso_nuovo = s
            break
    
    # Se tutti i suffissi sono usati, utilizza un numero incrementale
    if not suffisso_nuovo:
        numeri_usati = [int(e.suffisso_postazione) for e in estintori_stessa_postazione 
                       if e.suffisso_postazione and e.suffisso_postazione.isdigit()]
        
        if numeri_usati:
            suffisso_nuovo = str(max(numeri_usati) + 1)
        else:
            suffisso_nuovo = "2"
    
    # Redirect alla pagina di creazione di un nuovo estintore con i dati precompilati
    return redirect(url_for('estintori.nuovo', 
                           cliente_id=cliente.id,
                           duplica_da=estintore_orig.id,
                           suffisso=suffisso_nuovo))
                           
                           
                           
                           
                           
                           
                           


# Aggiungi questa funzione che verrà chiamata dalla route report esistente
def generate_estintori_cliente_report(cliente_id, solo_scadenze=False, formato='pdf'):
    """Genera un report patrimoniale degli estintori di un cliente specifico"""
    # Verifica che sia specificato un cliente
    if not cliente_id:
        flash('È necessario selezionare un cliente per generare il report', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Ottieni il cliente
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Ottieni gli estintori del cliente
    query = Estintore.query.filter_by(cliente_id=cliente_id)
    
    # Se richiesto, filtra solo per estintori in scadenza
    if solo_scadenze:
        oggi = datetime.now().date()
        scadenza_limite = oggi + timedelta(days=30)
        query = query.filter(
            or_(
                Estintore.data_controllo <= scadenza_limite,
                Estintore.data_revisione <= scadenza_limite,
                Estintore.data_collaudo <= scadenza_limite
            )
        )
    
    # Ordina per numero di postazione
    estintori = query.order_by(Estintore.postazione).all()
    
    # Genera il report nel formato richiesto
    if formato == 'csv':
        return generate_csv(cliente, estintori, solo_scadenze)
    else:
        return generate_pdf(cliente, estintori, solo_scadenze)

def generate_csv(cliente, estintori, solo_scadenze):
    """Genera un report patrimoniale in formato CSV"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # Prepara l'intestazione con tutti i campi
    header = [
        'Postazione', 'Matricola', 'Tipologia', 'Capacità', 
        'Marca', 'Dislocazione', 'Data Fabbricazione',
        'Data Installazione', 'Data Controllo', 'Data Revisione', 
        'Data Collaudo', 'Giorni al Controllo', 'Giorni alla Revisione',
        'Giorni al Collaudo', 'Stato', 'Coordinate', 'Note'
    ]
    writer.writerow(header)
    
    # Aggiungi i dati
    oggi = datetime.now().date()
    for estintore in estintori:
        giorni_controllo = (estintore.data_controllo - oggi).days if estintore.data_controllo else None
        giorni_revisione = (estintore.data_revisione - oggi).days if estintore.data_revisione else None
        giorni_collaudo = (estintore.data_collaudo - oggi).days if estintore.data_collaudo else None
        
        # Formatta le postazioni con eventuale suffisso
        postazione = f"{estintore.postazione}{f'/{estintore.suffisso_postazione}' if estintore.suffisso_postazione else ''}"
        
        row = [
            postazione,
            estintore.matricola,
            estintore.tipologia,
            estintore.capacita,
            estintore.marca,
            estintore.dislocazione,
            estintore.data_fabbricazione,
            estintore.data_installazione.strftime('%d/%m/%Y') if estintore.data_installazione else '',
            estintore.data_controllo.strftime('%d/%m/%Y') if estintore.data_controllo else '',
            estintore.data_revisione.strftime('%d/%m/%Y') if estintore.data_revisione else '',
            estintore.data_collaudo.strftime('%d/%m/%Y') if estintore.data_collaudo else '',
            giorni_controllo,
            giorni_revisione,
            giorni_collaudo,
            estintore.stato,
            estintore.coordinate,
            estintore.note
        ]
        writer.writerow(row)
    
    # Crea la risposta HTTP con header corretto per download CSV
    output.seek(0)
    nome_file = f"patrimoniale_{cliente.azienda.replace(' ', '_')}"
    if solo_scadenze:
        nome_file += "_in_scadenza"
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={nome_file}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response


def generate_pdf(cliente, estintori, solo_scadenze):
    """Genera un report patrimoniale in formato PDF"""
    # Crea un buffer per il PDF
    buffer = io.BytesIO()
    
    # Imposta il documento con orientamento orizzontale (landscape) ma con margini ridotti
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=15, rightMargin=15, topMargin=15, bottomMargin=15)
    styles = getSampleStyleSheet()
    elements = []
    
    # Crea un layout con logo a sinistra e titolo/info cliente a destra
    # Percorso al logo - adattalo al percorso corretto nel tuo progetto
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'logo.png')
    
    # Verifica che il file esista
    if os.path.exists(logo_path):
        # Crea un contenitore per logo e titolo
        logo_img = Image(logo_path, width=2*cm, height=2*cm)  # Dimensioni del logo
        
        # Crea layout a due colonne: logo a sinistra, titolo a destra
        header_data = [[logo_img, ""]]
        
        # Crea il testo del titolo
        title_style = styles['Title']
        title_style.fontSize = 14
        title_text = f"Report Patrimoniale Estintori - {cliente.azienda}"
        if solo_scadenze:
            title_text += " (Solo estintori in scadenza)"
        
        # Aggiungi le informazioni sul cliente
        cliente_info = (
            f"Indirizzo: {cliente.indirizzo}, {cliente.cap} {cliente.comune} ({cliente.provincia})<br/>"
            f"Tel: {cliente.telefono or 'N/D'} &nbsp;&nbsp; "
            f"Email: {cliente.email or 'N/D'}"
        )
        
        # Aggiungi titolo e info cliente alla cella di destra
        header_data[0][1] = Paragraph(f"<font size='14'><b>{title_text}</b></font><br/><font size='9'>{cliente_info}</font>", styles['Normal'])
        
        # Crea tabella intestazione con il logo
        header_table = Table(header_data, colWidths=[2.5*cm, doc.width-2.5*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(header_table)
    else:
        # Se il logo non esiste, usa solo il titolo
        title_style = styles['Title']
        title_style.fontSize = 14
        title_text = f"Report Patrimoniale Estintori - {cliente.azienda}"
        if solo_scadenze:
            title_text += " (Solo estintori in scadenza)"
        title = Paragraph(title_text, title_style)
        elements.append(title)
        
        # Aggiungi informazioni sul cliente in formato più compatto
        cliente_info = (
            f"<font size='9'>Indirizzo: {cliente.indirizzo}, {cliente.cap} {cliente.comune} ({cliente.provincia}) &nbsp;&nbsp; "
            f"Tel: {cliente.telefono or 'N/D'} &nbsp;&nbsp; "
            f"Email: {cliente.email or 'N/D'}</font>"
        )
        elements.append(Paragraph(cliente_info, styles['Normal']))
    
    elements.append(Spacer(1, 10))
    
    # Prepara i dati per la tabella - versione ottimizzata
    data = [
        ['P.', 'Matricola', 'Tipologia', 'Cap.', 'Dislocazione', 'D. Fabb.', 'D. Install.', 'Data Controllo', 'Data Revisione', 'Data Collaudo', 'Stato']
    ]
    
    # Aggiungi i dati degli estintori
    oggi = datetime.now().date()
    for estintore in estintori:
        giorni_controllo = (estintore.data_controllo - oggi).days if estintore.data_controllo else None
        giorni_revisione = (estintore.data_revisione - oggi).days if estintore.data_revisione else None
        giorni_collaudo = (estintore.data_collaudo - oggi).days if estintore.data_collaudo else None
        
        # Formatta le postazioni con eventuale suffisso
        postazione = f"{estintore.postazione}{f'/{estintore.suffisso_postazione}' if estintore.suffisso_postazione else ''}"
        
        # Formatta le date in modo compatto ma leggibile
        data_controllo = f"{estintore.data_controllo.strftime('%d/%m/%y')}\n{giorni_controllo} gg" if estintore.data_controllo else 'N/D'
        data_revisione = f"{estintore.data_revisione.strftime('%d/%m/%y')}\n{giorni_revisione} gg" if estintore.data_revisione else 'N/D'
        data_collaudo = f"{estintore.data_collaudo.strftime('%d/%m/%y')}\n{giorni_collaudo} gg" if estintore.data_collaudo else 'N/D'
        
        # Data installazione in formato compatto
        data_install = estintore.data_installazione.strftime('%d/%m/%y') if estintore.data_installazione else 'N/D'
        
        row = [
            postazione,
            estintore.matricola,
            estintore.tipologia,
            estintore.capacita,
            estintore.dislocazione,
            estintore.data_fabbricazione,
            data_install,
            data_controllo,
            data_revisione,
            data_collaudo,
            estintore.stato
        ]
        data.append(row)
    
    # Crea la tabella con larghezze colonne ottimizzate
    available_width = doc.width
    col_widths = [
        available_width * 0.04,  # Postazione (4%)
        available_width * 0.09,  # Matricola (9%)
        available_width * 0.09,  # Tipologia (9%)
        available_width * 0.05,  # Capacità (5%) - leggermente aumentata
        available_width * 0.14,  # Dislocazione (14%) - aumentata per compensare
        available_width * 0.06,  # Data Fabbricazione (6%)
        available_width * 0.06,  # Data Installazione (6%)
        available_width * 0.12,  # Data Controllo (12%)
        available_width * 0.12,  # Data Revisione (12%)
        available_width * 0.12,  # Data Collaudo (12%)
        available_width * 0.11   # Stato (11%)
    ]
    
    # Assicurati che tutte le colonne abbiano almeno una larghezza minima
    min_width = 30
    col_widths = [max(w, min_width) for w in col_widths]
    
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Stile della tabella
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Centra intestazioni
        ('ALIGN', (0, 1), (7, -1), 'CENTER'),  # Centra prime 8 colonne di dati
        ('ALIGN', (8, 1), (10, -1), 'CENTER'),  # Centra le date
        ('ALIGN', (11, 1), (11, -1), 'CENTER'),  # Centra lo stato
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),  # Intestazione
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Dati
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ])
    
    # Colora le celle delle date in base alla scadenza
    for i in range(1, len(data)):
        # Controllo
        if 'gg' in data[i][7]:
            giorni_str = data[i][7].split('\n')[1].split(' gg')[0]
            try:
                giorni = int(giorni_str)
                if giorni < 0:
                    table_style.add('BACKGROUND', (7, i), (7, i), colors.lightpink)
                elif giorni <= 30:
                    table_style.add('BACKGROUND', (7, i), (7, i), colors.lightyellow)
                else:
                    table_style.add('BACKGROUND', (7, i), (7, i), colors.lightgreen)
            except ValueError:
                pass
        
        # Revisione
        if 'gg' in data[i][8]:
            giorni_str = data[i][8].split('\n')[1].split(' gg')[0]
            try:
                giorni = int(giorni_str)
                if giorni < 0:
                    table_style.add('BACKGROUND', (8, i), (8, i), colors.lightpink)
                elif giorni <= 30:
                    table_style.add('BACKGROUND', (8, i), (8, i), colors.lightyellow)
                else:
                    table_style.add('BACKGROUND', (8, i), (8, i), colors.lightgreen)
            except ValueError:
                pass
        
        # Collaudo
        if 'gg' in data[i][9]:
            giorni_str = data[i][9].split('\n')[1].split(' gg')[0]
            try:
                giorni = int(giorni_str)
                if giorni < 0:
                    table_style.add('BACKGROUND', (9, i), (9, i), colors.lightpink)
                elif giorni <= 30:
                    table_style.add('BACKGROUND', (9, i), (9, i), colors.lightyellow)
                else:
                    table_style.add('BACKGROUND', (9, i), (9, i), colors.lightgreen)
            except ValueError:
                pass
    
    table.setStyle(table_style)
    elements.append(table)
    
    
    # Aggiungi riepilogo e data generazione in modo compatto
    footer_text = (
        f"<font size='8'>Totale estintori: {len(estintori)} | "
        f"Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}</font>"
    )
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Costruisci il PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Crea la risposta HTTP
    nome_file = f"patrimoniale_{cliente.azienda.replace(' ', '_')}"
    if solo_scadenze:
        nome_file += "_in_scadenza"
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={nome_file}.pdf'
    
    return response

@estintori_bp.route('/report/generate/<tipo>')
def report_generate(tipo):
    """
    Genera un report PDF in base al tipo specificato
    """
    from datetime import datetime
    import pdfkit  # Assicurati di avere pdfkit installato e configurato
    from flask import render_template, make_response
    
    now = datetime.now()
    
    if tipo == 'estintori':
        # Ottieni tutti gli estintori ordinati per cliente
        estintori = Estintore.query.join(Cliente).order_by(Cliente.azienda, Estintore.postazione).all()
        
        # Raggruppa gli estintori per cliente
        clienti_dict = {}
        estintori_per_cliente = {}
        
        for estintore in estintori:
            if estintore.cliente_id not in clienti_dict:
                clienti_dict[estintore.cliente_id] = estintore.cliente
                estintori_per_cliente[estintore.cliente_id] = []
            
            estintori_per_cliente[estintore.cliente_id].append(estintore)
        
        clienti = list(clienti_dict.values())
        
        # Calcola statistiche per il riepilogo
        estintori_scaduti = 0
        estintori_prossimi30 = 0
        estintori_in_manutenzione = 0
        
        for estintore in estintori:
            giorni_controllo = (estintore.data_controllo - now.date()).days
            if giorni_controllo < 0:
                estintori_scaduti += 1
            elif giorni_controllo <= 30:
                estintori_prossimi30 += 1
                
            if estintore.stato == 'In manutenzione':
                estintori_in_manutenzione += 1
        
        # Renderizza il template HTML per il PDF
        rendered = render_template(
            'report_estintori_completo.html',
            estintori=estintori,
            clienti=clienti,
            estintori_per_cliente=estintori_per_cliente,
            clienti_count=len(clienti),
            estintori_scaduti=estintori_scaduti,
            estintori_prossimi30=estintori_prossimi30,
            estintori_in_manutenzione=estintori_in_manutenzione,
            now=now
        )
        
        # Opzioni per pdfkit
        options = {
            'page-size': 'A4',
            'orientation': 'Landscape',
            'margin-top': '1cm',
            'margin-right': '1cm',
            'margin-bottom': '1cm',
            'margin-left': '1cm',
            'encoding': 'UTF-8',
            'footer-right': 'Pagina [page] di [toPage]',
            'footer-font-size': '8',
            'footer-line': True,
            'footer-spacing': '5'
        }
        
        # Genera il PDF
        #df = pdfkit.from_string(rendered, False, options=options)
        import os
        wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
        
        
        
        # Crea la risposta
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=elenco_estintori_{now.strftime("%Y%m%d")}.pdf'
        
        return response
    
    
    # Fallback - Redirect alla pagina report se il tipo non è valido
    flash('Tipo di report non valido', 'danger')
    return redirect(url_for('estintori.report'))
    
# report lista di controllo
def generate_lista_controllo(cliente_id, con_scadenze=False):
    """
    Genera una lista di controllo per i tecnici da compilare durante la manutenzione
    """
    # Importazioni necessarie
    import pdfkit
    import base64
    import os
    import tempfile
    from datetime import datetime, timedelta
    from flask import render_template, make_response, current_app
    from sqlalchemy import or_
    
    # Verifica che sia specificato un cliente
    if not cliente_id:
        flash('È necessario selezionare un cliente per generare la lista di controllo', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Ottieni il cliente
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Ottieni gli estintori del cliente
    query = Estintore.query.filter_by(cliente_id=cliente_id)
    
    # Se richiesto, filtra solo per estintori in scadenza o in manutenzione
    if con_scadenze:
        oggi = datetime.now().date()
        scadenza_limite = oggi + timedelta(days=30)
        query = query.filter(
            or_(
                Estintore.data_controllo <= scadenza_limite,
                Estintore.data_revisione <= scadenza_limite,
                Estintore.data_collaudo <= scadenza_limite,
                Estintore.stato == 'In manutenzione'
            )
        )
    
    # Ordina per numero di postazione
    estintori = query.order_by(Estintore.postazione).all()
    
    # Se non ci sono estintori, mostra un messaggio e reindirizza
    if not estintori:
        flash(f'Nessun estintore trovato per il cliente {cliente.azienda}', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Carica il logo come base64
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'Logo.png')
    logo_data_uri = None
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as image_file:
                logo_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                logo_data_uri = f"data:image/png;base64,{logo_base64}"
        except Exception as e:
            current_app.logger.error(f"Errore nel caricamento del logo: {str(e)}")
    
    # Crea un file HTML temporaneo per il footer con numerazione pagine
    footer_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            font-size: 9px;
            margin: 0;
            padding: 5px 0;
            border-top: 1px solid #ddd;
        }
        .container {
            display: flex;
            justify-content: space-between;
            width: 100%;
        }
        .left {
            text-align: left;
        }
        .center {
            text-align: center;
        }
        .right {
            text-align: right;
        }
    </style>
    <script>
        function subst() {
            var vars = {};
            var query_strings_from_url = document.location.search.substring(1).split('&');
            for (var query_string in query_strings_from_url) {
                if (query_strings_from_url.hasOwnProperty(query_string)) {
                    var temp_var = query_strings_from_url[query_string].split('=', 2);
                    vars[temp_var[0]] = decodeURI(temp_var[1]);
                }
            }
            var css_selector_classes = ['page', 'frompage', 'topage', 'webpage', 'section', 'subsection', 'date', 'isodate', 'time', 'title', 'doctitle', 'sitepage', 'sitepages'];
            for (var css_class in css_selector_classes) {
                if (css_selector_classes.hasOwnProperty(css_class)) {
                    var element = document.getElementsByClassName(css_selector_classes[css_class]);
                    for (var j = 0; j < element.length; ++j) {
                        element[j].textContent = vars[css_selector_classes[css_class]];
                    }
                }
            }
        }
    </script>
</head>
<body onload="subst()">
    <div class="container">
        <div class="left">Stampe liste controllo</div>
        <div class="center">Data generazione: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</div>
        <div class="right">Pagina <span class="page"></span> di <span class="topage"></span></div>
    </div>
</body>
</html>"""
    
    # Crea il file temporaneo per il footer
    footer_file = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
    footer_file.write(footer_html.encode('utf-8'))
    footer_file.close()
    
    # Renderizza il template HTML per il PDF - solo formato A4
    now = datetime.now()
    template_name = 'estintori/lista_controllo_a4.html'
    
    try:
        rendered = render_template(
            template_name,
            cliente=cliente,
            estintori=estintori,
            now=now,
            logo_data_uri=logo_data_uri
        )
    except Exception as e:
        current_app.logger.error(f"Errore nel rendering del template: {str(e)}")
        flash(f'Errore nella generazione del PDF: {str(e)}', 'danger')
        return redirect(url_for('estintori.report'))
    
    # Opzioni per pdfkit - sempre formato A4 orizzontale
    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'encoding': 'UTF-8',
        'footer-html': footer_file.name,
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '2cm',  # Margine inferiore aumentato per il footer
        'margin-left': '1cm'
    }
    
    try:
        # Genera il PDF
        pdf = pdfkit.from_string(rendered, False, options=options)
        
        # Rimuovi il file temporaneo del footer
        os.unlink(footer_file.name)
        
        # Crea la risposta
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=lista_controllo_{cliente.azienda.replace(" ", "_")}_{now.strftime("%Y%m%d")}.pdf'
        
        return response
    
    except Exception as e:
        # Rimuovi il file temporaneo del footer in caso di errore
        if os.path.exists(footer_file.name):
            os.unlink(footer_file.name)
        
        current_app.logger.error(f"Errore nella generazione del PDF: {str(e)}")
        flash(f'Errore nella generazione del PDF: {str(e)}', 'danger')
        return redirect(url_for('estintori.report'))
        
        # Aggiungi questa funzione a estintori.py, nella sezione delle funzioni di report

def generate_clienti_scadenze_report(periodo='prossimi30'):
    """
    Genera un report dei clienti con estintori in scadenza nel periodo specificato,
    raggruppando gli estintori per cliente.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import or_, and_
    import pdfkit
    import tempfile
    import os
    
    # Ottieni la data corrente
    oggi = datetime.now().date()
    
    # Calcola la data limite in base al periodo
    if periodo == 'prossimi30':
        data_limite = oggi + timedelta(days=30)
    elif periodo == 'prossimi60':
        data_limite = oggi + timedelta(days=60)
    elif periodo == 'prossimi90':
        data_limite = oggi + timedelta(days=90)
    elif periodo == 'prossimi180':
        data_limite = oggi + timedelta(days=180)
    elif periodo == 'scaduti':
        # Per scaduti, la data limite è oggi (solo estintori già scaduti)
        data_limite = oggi
    else:
        data_limite = oggi + timedelta(days=30)  # Default: 30 giorni
    
    # Costruisci la query per trovare tutti gli estintori in scadenza
    query = Estintore.query.join(Cliente)
    
    # Condizione per gli estintori scaduti o in scadenza
    if periodo == 'scaduti':
        scadenze_condition = or_(
            Estintore.data_controllo < oggi,
            Estintore.data_revisione < oggi,
            Estintore.data_collaudo < oggi
        )
    else:
        scadenze_condition = or_(
            and_(Estintore.data_controllo >= oggi, Estintore.data_controllo <= data_limite),
            and_(Estintore.data_revisione >= oggi, Estintore.data_revisione <= data_limite),
            and_(Estintore.data_collaudo >= oggi, Estintore.data_collaudo <= data_limite)
        )
    
    # Applica la condizione
    query = query.filter(scadenze_condition)
    
    # Ordina per cliente e postazione
    query = query.order_by(Cliente.azienda, Estintore.postazione)
    
    # Esegui la query
    estintori = query.all()
    
    # Se non ci sono estintori in scadenza, mostra un messaggio e reindirizza
    if not estintori:
        flash(f'Nessun estintore trovato in scadenza nel periodo selezionato', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Raggruppa gli estintori per cliente
    clienti_dict = {}
    estintori_per_cliente = {}
    clienti_id_list = []
    
    # Contatore totale estintori in scadenza
    total_estintori = 0
    
    for estintore in estintori:
        if estintore.cliente_id not in clienti_dict:
            clienti_dict[estintore.cliente_id] = estintore.cliente
            estintori_per_cliente[estintore.cliente_id] = []
            clienti_id_list.append(estintore.cliente_id)
        
        # Calcola i giorni rimanenti per ogni tipo di scadenza
        giorni_controllo = (estintore.data_controllo - oggi).days if estintore.data_controllo else None
        giorni_revisione = (estintore.data_revisione - oggi).days if estintore.data_revisione else None
        giorni_collaudo = (estintore.data_collaudo - oggi).days if estintore.data_collaudo else None
        
        # Flag per indicare se ciascuna scadenza rientra nel periodo
        scadenza_controllo = False
        scadenza_revisione = False
        scadenza_collaudo = False
        
        # Controllo se periodo è 'scaduti' o una delle altre opzioni
        if periodo == 'scaduti':
            scadenza_controllo = giorni_controllo is not None and giorni_controllo < 0
            scadenza_revisione = giorni_revisione is not None and giorni_revisione < 0
            scadenza_collaudo = giorni_collaudo is not None and giorni_collaudo < 0
        else:
            scadenza_controllo = giorni_controllo is not None and 0 <= giorni_controllo <= (data_limite - oggi).days
            scadenza_revisione = giorni_revisione is not None and 0 <= giorni_revisione <= (data_limite - oggi).days
            scadenza_collaudo = giorni_collaudo is not None and 0 <= giorni_collaudo <= (data_limite - oggi).days
        
        # Aggiunge le informazioni di scadenza all'estintore
        estintore.giorni_controllo = giorni_controllo
        estintore.giorni_revisione = giorni_revisione
        estintore.giorni_collaudo = giorni_collaudo
        estintore.scadenza_controllo = scadenza_controllo
        estintore.scadenza_revisione = scadenza_revisione
        estintore.scadenza_collaudo = scadenza_collaudo
        
        # Aggiungi l'estintore alla lista del cliente solo se ha almeno una scadenza nel periodo
        if scadenza_controllo or scadenza_revisione or scadenza_collaudo:
            estintori_per_cliente[estintore.cliente_id].append(estintore)
            total_estintori += 1
    
    # Ottieni la lista dei clienti in ordine
    clienti = [clienti_dict[cliente_id] for cliente_id in clienti_id_list]
    
    # Filtra i clienti senza estintori in scadenza (potrebbe accadere dopo l'elaborazione)
    clienti = [cliente for cliente in clienti if estintori_per_cliente[cliente.id]]
    
    # Renderizza il template - PERCORSO CORRETTO
    now = datetime.now()
    rendered = render_template(
        'estintori/clienti_scadenze_30gg.html',  # Specifica la sottocartella 'estintori/'
        clienti=clienti,
        estintori_per_cliente=estintori_per_cliente,
        total_estintori=total_estintori,
        oggi=oggi,
        now=now,
        timedelta=timedelta,
        periodo=periodo
    )
    
    # Crea il file temporaneo per il footer
    footer_html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                font-size: 9px;
                margin: 0;
                padding: 5px 0;
                border-top: 1px solid #ddd;
            }
            .container {
                display: flex;
                justify-content: space-between;
                width: 100%;
            }
            .left {
                text-align: left;
            }
            .center {
                text-align: center;
            }
            .right {
                text-align: right;
            }
        </style>
        <script>
            function subst() {
                var vars = {};
                var query_strings_from_url = document.location.search.substring(1).split('&');
                for (var query_string in query_strings_from_url) {
                    if (query_strings_from_url.hasOwnProperty(query_string)) {
                        var temp_var = query_strings_from_url[query_string].split('=', 2);
                        vars[temp_var[0]] = decodeURI(temp_var[1]);
                    }
                }
                var css_selector_classes = ['page', 'frompage', 'topage', 'webpage', 'section', 'subsection', 'date', 'isodate', 'time', 'title', 'doctitle', 'sitepage', 'sitepages'];
                for (var css_class in css_selector_classes) {
                    if (css_selector_classes.hasOwnProperty(css_class)) {
                        var element = document.getElementsByClassName(css_selector_classes[css_class]);
                        for (var j = 0; j < element.length; ++j) {
                            element[j].textContent = vars[css_selector_classes[css_class]];
                        }
                    }
                }
            }
        </script>
    </head>
    <body onload="subst()">
        <div class="container">
            <div class="left">Report clienti con scadenze</div>
            <div class="center">Data generazione: """ + now.strftime('%d/%m/%Y %H:%M') + """</div>
            <div class="right">Pagina <span class="page"></span> di <span class="topage"></span></div>
        </div>
    </body>
    </html>"""
    
    # Crea il file temporaneo per il footer
    footer_file = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
    footer_file.write(footer_html.encode('utf-8'))
    footer_file.close()
    
    # Opzioni per pdfkit
    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'encoding': 'UTF-8',
        'footer-html': footer_file.name,
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '2cm',
        'margin-left': '1cm'
    }
    
    try:
        # Genera il PDF
        pdf = pdfkit.from_string(rendered, False, options=options)
        
        # Rimuovi il file temporaneo del footer
        os.unlink(footer_file.name)
        
        # Crea la risposta
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=clienti_scadenze_{periodo}_{now.strftime("%Y%m%d")}.pdf'
        
        return response
    
    except Exception as e:
        # Rimuovi il file temporaneo del footer in caso di errore
        if os.path.exists(footer_file.name):
            os.unlink(footer_file.name)
        
        current_app.logger.error(f"Errore nella generazione del PDF: {str(e)}")
        flash(f'Errore nella generazione del PDF: {str(e)}', 'danger')
        return redirect(url_for('estintori.report'))
        
def generate_clienti_scadenze_custom_report():
    """
    Genera un report dei clienti con estintori in scadenza in un intervallo di date personalizzato,
    con possibilità di filtrare per tipo di scadenza, cliente, tipo di cliente e zona.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import or_, and_
    import pdfkit
    import tempfile
    import os
    from flask import request, flash, redirect, url_for, render_template, make_response, current_app
    
    # Ottieni i parametri dalla richiesta
    data_inizio_str = request.args.get('data_inizio')
    data_fine_str = request.args.get('data_fine')
    tipo_scadenza = request.args.get('tipo_scadenza', 'tutto')
    cliente_id = request.args.get('cliente_id')
    tipo_cliente = request.args.get('tipo_cliente', 'tutti')
    zona = request.args.get('zona', 'tutte')
    
    # Debug dei parametri ricevuti
    current_app.logger.info(f"Parametri report: inizio={data_inizio_str}, fine={data_fine_str}, "
                           f"tipo={tipo_scadenza}, cliente={cliente_id}, "
                           f"tipo_cliente={tipo_cliente}, zona={zona}")
    
    # Converti le date
    try:
        data_inizio = datetime.strptime(data_inizio_str, '%Y-%m-%d').date()
        data_fine = datetime.strptime(data_fine_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Date non valide', 'danger')
        return redirect(url_for('estintori.report'))
    
    # Verifica che le date siano valide
    if data_inizio > data_fine:
        flash('La data di inizio non può essere successiva alla data di fine', 'danger')
        return redirect(url_for('estintori.report'))
    
    # Ottieni la data corrente
    oggi = datetime.now().date()
    
    # Costruisci la query base
    query = Estintore.query.join(Cliente)
    
    # Ottieni il cliente filtrato se specificato
    cliente_filtrato = None
    if cliente_id:
        cliente_filtrato = Cliente.query.get(cliente_id)
        query = query.filter(Estintore.cliente_id == cliente_id)
    
    # Applica il filtro per tipo di cliente se specificato
    if tipo_cliente != 'tutti':
        query = query.filter(Cliente.tipologia == tipo_cliente)
    
    # Applica il filtro per zona se specificato
    if zona != 'tutte':
        query = query.filter(Cliente.zona == zona)
    
    # Costruisci le condizioni per le scadenze
    conditions = []
    
    # Aggiungi le condizioni basate sul tipo di scadenza selezionato
    if tipo_scadenza == 'tutto' or tipo_scadenza == 'controllo':
        conditions.append(and_(
            Estintore.data_controllo.isnot(None),
            Estintore.data_controllo >= data_inizio,
            Estintore.data_controllo <= data_fine
        ))
    
    if tipo_scadenza == 'tutto' or tipo_scadenza == 'revisione':
        conditions.append(and_(
            Estintore.data_revisione.isnot(None),
            Estintore.data_revisione >= data_inizio,
            Estintore.data_revisione <= data_fine
        ))
    
    if tipo_scadenza == 'tutto' or tipo_scadenza == 'collaudo':
        conditions.append(and_(
            Estintore.data_collaudo.isnot(None),
            Estintore.data_collaudo >= data_inizio,
            Estintore.data_collaudo <= data_fine
        ))
    
    # Unisci le condizioni con OR
    if conditions:
        query = query.filter(or_(*conditions))
    else:
        # Se non ci sono condizioni (caso raro), mostra un messaggio
        flash('Nessun tipo di scadenza selezionato', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Per debug, stampa la query SQL
    from sqlalchemy.dialects import sqlite
    sql_query = str(query.statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    current_app.logger.info(f"Query SQL: {sql_query}")
    
    # Ordina per cliente e postazione
    query = query.order_by(Cliente.azienda, Estintore.postazione)
    
    # Esegui la query
    estintori = query.all()
    
    # Debug: conteggio estintori trovati
    current_app.logger.info(f"Estintori trovati nella query: {len(estintori)}")
    
    # Se non ci sono estintori in scadenza, mostra un messaggio e reindirizza
    if not estintori:
        flash(f'Nessun estintore trovato in scadenza nell\'intervallo di date selezionato', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Debug: verifica date di revisione uniche
    date_revisione = set()
    for est in estintori:
        if est.data_revisione:
            date_revisione.add(est.data_revisione)
    current_app.logger.info(f"Date di revisione uniche: {len(date_revisione)}")
    
    # Raggruppa gli estintori per cliente
    clienti_dict = {}
    estintori_per_cliente = {}
    clienti_id_list = []
    
    # Contatore totale estintori in scadenza
    total_estintori = 0
    total_estintori_visualizzati = 0
    
    for estintore in estintori:
        # Aggiungi il cliente al dizionario se non c'è già
        if estintore.cliente_id not in clienti_dict:
            clienti_dict[estintore.cliente_id] = estintore.cliente
            estintori_per_cliente[estintore.cliente_id] = []
            clienti_id_list.append(estintore.cliente_id)
        
        # Calcola i giorni rimanenti per ogni tipo di scadenza
        giorni_controllo = (estintore.data_controllo - oggi).days if estintore.data_controllo else None
        giorni_revisione = (estintore.data_revisione - oggi).days if estintore.data_revisione else None
        giorni_collaudo = (estintore.data_collaudo - oggi).days if estintore.data_collaudo else None
        
        # Flag per indicare se ciascuna scadenza rientra nell'intervallo selezionato
        # Imposta inizialmente tutti a False
        scadenza_controllo = False
        scadenza_revisione = False
        scadenza_collaudo = False
        
        # Determina quali scadenze rientrano nell'intervallo specificato
        if tipo_scadenza == 'tutto' or tipo_scadenza == 'controllo':
            scadenza_controllo = (estintore.data_controllo is not None and 
                                data_inizio <= estintore.data_controllo <= data_fine)
        
        if tipo_scadenza == 'tutto' or tipo_scadenza == 'revisione':
            scadenza_revisione = (estintore.data_revisione is not None and 
                                data_inizio <= estintore.data_revisione <= data_fine)
        
        if tipo_scadenza == 'tutto' or tipo_scadenza == 'collaudo':
            scadenza_collaudo = (estintore.data_collaudo is not None and 
                               data_inizio <= estintore.data_collaudo <= data_fine)
        
        # Debug per verificare i valori calcolati
        current_app.logger.debug(f"Estintore {estintore.matricola}: "
                               f"controllo={scadenza_controllo} ({estintore.data_controllo}), "
                               f"revisione={scadenza_revisione} ({estintore.data_revisione}), "
                               f"collaudo={scadenza_collaudo} ({estintore.data_collaudo})")
        
        # Aggiunge le informazioni di scadenza all'estintore
        estintore.giorni_controllo = giorni_controllo
        estintore.giorni_revisione = giorni_revisione
        estintore.giorni_collaudo = giorni_collaudo
        estintore.scadenza_controllo = scadenza_controllo
        estintore.scadenza_revisione = scadenza_revisione
        estintore.scadenza_collaudo = scadenza_collaudo
        
        # Conteggio tutte le scadenze
        total_estintori += 1
        
        # Aggiungi l'estintore alla lista del cliente solo se ha almeno una scadenza nel periodo
        # e corrispondente al tipo selezionato
        if ((tipo_scadenza == 'tutto' and (scadenza_controllo or scadenza_revisione or scadenza_collaudo)) or
            (tipo_scadenza == 'controllo' and scadenza_controllo) or
            (tipo_scadenza == 'revisione' and scadenza_revisione) or
            (tipo_scadenza == 'collaudo' and scadenza_collaudo)):
            estintori_per_cliente[estintore.cliente_id].append(estintore)
            total_estintori_visualizzati += 1
    
    # Filtra i clienti senza estintori in scadenza
    clienti_filtrati = []
    for cliente_id in clienti_id_list:
        if estintori_per_cliente[cliente_id]:
            clienti_filtrati.append(clienti_dict[cliente_id])
    
    # Debug del conteggio finale
    current_app.logger.info(f"Totale estintori visualizzati: {total_estintori_visualizzati}")
    current_app.logger.info(f"Totale clienti filtrati: {len(clienti_filtrati)}")
    
    # Verifica che ci siano effettivamente estintori con scadenze da mostrare
    if total_estintori_visualizzati == 0:
        flash(f'Nessun estintore trovato con scadenze nell\'intervallo di date selezionato', 'warning')
        return redirect(url_for('estintori.report'))
    
    # Renderizza il template
    now = datetime.now()
    rendered = render_template(
        'estintori/clienti_scadenze_30gg.html',
        clienti=clienti_filtrati,
        estintori_per_cliente=estintori_per_cliente,
        total_estintori=total_estintori_visualizzati,
        total_estintori_trovati=total_estintori,
        oggi=oggi,
        now=now,
        timedelta=timedelta,
        periodo='custom_',
        data_inizio=data_inizio,
        data_fine=data_fine,
        tipo_scadenza=tipo_scadenza,
        tipo_cliente=tipo_cliente,
        zona=zona,
        cliente_filtrato=cliente_filtrato
    )
    
    # Crea il file temporaneo per il footer
    footer_html = """<!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                font-size: 9px;
                margin: 0;
                padding: 5px 0;
                border-top: 1px solid #ddd;
            }
            .container {
                display: flex;
                justify-content: space-between;
                width: 100%;
            }
            .left {
                text-align: left;
            }
            .center {
                text-align: center;
            }
            .right {
                text-align: right;
            }
        </style>
        <script>
            function subst() {
                var vars = {};
                var query_strings_from_url = document.location.search.substring(1).split('&');
                for (var query_string in query_strings_from_url) {
                    if (query_strings_from_url.hasOwnProperty(query_string)) {
                        var temp_var = query_strings_from_url[query_string].split('=', 2);
                        vars[temp_var[0]] = decodeURI(temp_var[1]);
                    }
                }
                var css_selector_classes = ['page', 'frompage', 'topage', 'webpage', 'section', 'subsection', 'date', 'isodate', 'time', 'title', 'doctitle', 'sitepage', 'sitepages'];
                for (var css_class in css_selector_classes) {
                    if (css_selector_classes.hasOwnProperty(css_class)) {
                        var element = document.getElementsByClassName(css_selector_classes[css_class]);
                        for (var j = 0; j < element.length; ++j) {
                            element[j].textContent = vars[css_selector_classes[css_class]];
                        }
                    }
                }
            }
        </script>
    </head>
    <body onload="subst()">
        <div class="container">
            <div class="left">Report clienti con scadenze personalizzato</div>
            <div class="center">Periodo: """ + data_inizio.strftime('%d/%m/%Y') + " - " + data_fine.strftime('%d/%m/%Y') + """</div>
            <div class="right">Pagina <span class="page"></span> di <span class="topage"></span></div>
        </div>
    </body>
    </html>"""
    
    # Crea il file temporaneo per il footer
    footer_file = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
    footer_file.write(footer_html.encode('utf-8'))
    footer_file.close()
    
    # Opzioni per pdfkit
    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'encoding': 'UTF-8',
        'footer-html': footer_file.name,
        'margin-top': '1cm',
        'margin-right': '1cm',
        'margin-bottom': '2cm',
        'margin-left': '1cm'
    }
    
    try:
        # Genera il PDF
        pdf = pdfkit.from_string(rendered, False, options=options)
        
        # Rimuovi il file temporaneo del footer
        os.unlink(footer_file.name)
        
        # Crea la risposta
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=clienti_scadenze_custom_{data_inizio.strftime("%Y%m%d")}_{data_fine.strftime("%Y%m%d")}.pdf'
        
        return response
    
    except Exception as e:
        # Rimuovi il file temporaneo del footer in caso di errore
        if os.path.exists(footer_file.name):
            os.unlink(footer_file.name)
        
        current_app.logger.error(f"Errore nella generazione del PDF: {str(e)}")
        flash(f'Errore nella generazione del PDF: {str(e)}', 'danger')
        return redirect(url_for('estintori.report'))