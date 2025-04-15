from app import db
from datetime import datetime
import re

class Cliente(db.Model):
    __tablename__ = 'clienti'
    
    id = db.Column(db.Integer, primary_key=True)
    azienda = db.Column(db.String(100), unique=True, nullable=False, index=True)
    indirizzo = db.Column(db.String(150), nullable=False)
    cap = db.Column(db.String(5), nullable=False)
    provincia = db.Column(db.String(2), nullable=False)
    comune = db.Column(db.String(100), nullable=False)
    zona = db.Column(db.String(100), nullable=False)
    tipologia = db.Column(db.String(20), nullable=False)
    
    # Campi opzionali
    telefono = db.Column(db.String(20))
    cellulare = db.Column(db.String(15))
    email = db.Column(db.String(120))
    coordinate = db.Column(db.String(100))
    note = db.Column(db.Text)
    
    # Timestamp per creazione e aggiornamento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazione con gli estintori
    estintori = db.relationship('Estintore', backref='cliente', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Cliente, self).__init__(**kwargs)
    
    @staticmethod
    def validate_cap(cap):
        """Valida il formato del CAP italiano (5 cifre)"""
        if not cap or not re.match(r'^\d{5}$', cap):
            return False
        return True
    
    @staticmethod
    def validate_provincia(provincia):
        """Valida il formato della provincia italiana (2 lettere)"""
        if not provincia or not re.match(r'^[A-Za-z]{2}$', provincia):
            return False
        return True
    
    @staticmethod
    def validate_cellulare(cellulare):
        """Valida il formato del cellulare italiano"""
        if not cellulare:
            return True  # Il campo è opzionale
        # Formato: +39xxxxxxxxxx o 3xxxxxxxxx
        if not re.match(r'^(\+39)?\s?3\d{8,9}$', cellulare):
            return False
        return True
    
    @staticmethod
    def validate_email(email):
        """Valida il formato dell'email"""
        if not email:
            return True  # Il campo è opzionale
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        return True
    
    def to_dict(self):
        """Converte l'oggetto in un dizionario"""
        return {
            'id': self.id,
            'azienda': self.azienda,
            'indirizzo': self.indirizzo,
            'cap': self.cap,
            'provincia': self.provincia,
            'comune': self.comune,
            'zona': self.zona,
            'tipologia': self.tipologia,
            'telefono': self.telefono,
            'cellulare': self.cellulare,
            'email': self.email,
            'coordinate': self.coordinate,
            'note': self.note
        }
    
    def __repr__(self):
        return f'<Cliente {self.azienda}>'