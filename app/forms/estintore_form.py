from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, ValidationError
import re
from datetime import datetime
from app.models.estintore import Estintore

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