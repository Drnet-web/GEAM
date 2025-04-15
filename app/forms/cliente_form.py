from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
import re
from app.models.cliente import Cliente

class ClienteForm(FlaskForm):
    """Form per la gestione dei clienti"""
    
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
    
    def validate_cap(form, field):
        """Validazione formato CAP (5 cifre)"""
        if not field.data.isdigit() or len(field.data) != 5:
            raise ValidationError('Il CAP deve essere composto da 5 cifre')
    
    def validate_provincia(form, field):
        """Validazione formato provincia (2 lettere)"""
        if not re.match(r'^[A-Za-z]{2}$', field.data):
            raise ValidationError('La provincia deve essere composta da 2 lettere')
        
        # Convertiamo in maiuscolo
        field.data = field.data.upper()
    
    def validate_cellulare(form, field):
        """Validazione formato cellulare italiano"""
        if field.data:
            if not re.match(r'^(\+39)?\s?3\d{8,9}$', field.data):
                raise ValidationError('Formato cellulare non valido (es: 3xx1234567 o +39 3xx1234567)')
    
    def validate_azienda(form, field):
        """Verifica che non esista già l'azienda (in caso di nuovo cliente)"""
        cliente = Cliente.query.filter(Cliente.azienda == field.data).first()
        if cliente and not hasattr(form, 'id'):
            raise ValidationError('Questa azienda esiste già')