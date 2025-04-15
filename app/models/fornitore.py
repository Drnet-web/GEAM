from app import db
from datetime import datetime

class Fornitore(db.Model):
    """Modello per i fornitori"""
    __tablename__ = 'fornitori'

    id = db.Column(db.Integer, primary_key=True)
    azienda = db.Column(db.String(100), nullable=False, unique=True)
    indirizzo = db.Column(db.String(150), nullable=False)
    cap = db.Column(db.String(5), nullable=False)
    provincia = db.Column(db.String(2), nullable=False)
    comune = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    cellulare = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        """Converte il fornitore in un dizionario per il log"""
        return {
            'id': self.id,
            'azienda': self.azienda,
            'indirizzo': self.indirizzo,
            'cap': self.cap,
            'provincia': self.provincia,
            'comune': self.comune,
            'telefono': self.telefono or "",
            'cellulare': self.cellulare or "",
            'email': self.email or "",
            'note': self.note or ""
        }