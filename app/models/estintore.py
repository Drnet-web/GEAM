from app import db
from datetime import datetime
import json

class Estintore(db.Model):
    __tablename__ = 'estintori'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.id', ondelete='CASCADE'), nullable=False)
    tipologia = db.Column(db.String(50), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    matricola = db.Column(db.String(50), nullable=False, unique=True)
    dislocazione = db.Column(db.String(150), nullable=False)
    postazione = db.Column(db.Integer, nullable=False)
    suffisso_postazione = db.Column(db.String(10), nullable=True)
    capacita = db.Column(db.String(20), nullable=False)
    
    # Date importanti
    data_fabbricazione = db.Column(db.String(7), nullable=False)  # Formato MM/YYYY
    data_installazione = db.Column(db.Date, nullable=False)
    data_controllo = db.Column(db.Date, nullable=False)
    data_revisione = db.Column(db.Date, nullable=True)
    data_collaudo = db.Column(db.Date, nullable=True)
    
    # Stato
    stato = db.Column(db.String(20), nullable=False, default='Attivo')
    
    # Campi opzionali
    coordinate = db.Column(db.String(100))
    note = db.Column(db.Text)
    
    # Timestamp per creazione e aggiornamento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Dizionario delle capacità permesse per tipologia
    CAPACITA_PER_TIPOLOGIA = {
    'CO2': ['1KG', '2KG', '3KG', '4KG', '5KG', '6KG', '9KG', '12KG'],
    'Polvere': ['1KG', '2KG', '3KG', '4KG', '5KG', '6KG', '9KG', '12KG'],
    'Idrico': ['2L', '4L', '6L', '9L', '12L'],  # Modificato da KG a L
    'Carrello Polvere': ['1KG', '2KG', '3KG', '4KG', '5KG', '6KG', '9KG', '12KG', '25KG', '30KG', '50KG'],
    'Carrello Idrico': ['30L', '50L'],  # Modificato da KG a L
    'NASPO UNI25': ['20MT', '25MT', '30MT'],
    'Idrante UNI45': ['20MT', '25MT', '30MT'],
    'Idrante UNI70': ['20MT', '25MT', '30MT'],
    'Porta REI': ['1 Anta', '2 Ante', 'Scorrevole'],
    'Automatico Polvere': ['1KG', '2KG', '3KG', '4KG', '5KG', '6KG', '9KG', '12KG'],
    'Automatico Idrico': ['6L'],  # Modificato da KG a L
    'CPS': ['Grande', 'Piccola'],
    'Registro': ['Cartaceo', 'Digitale'],
    'Altro': ['1KG', '2KG', '3KG', '4KG', '5KG', '6KG', '9KG', '12KG', '25KG', '30KG', '50KG',
             '1L', '2L', '3L', '4L', '5L', '6L', '9L', '12L', '25L', '30L', '50L',  # Aggiunto L
             '20MT', '25MT', '30MT', '1 Anta', '2 Ante', 'Scorrevole', 
             'Grande', 'Piccola', 'Cartaceo', 'Digitale', 'Altro']
    }
    
    @staticmethod
    def get_next_postazione(cliente_id):
        """
        Restituisce il prossimo numero di postazione disponibile per un cliente.
        Se ci sono "buchi" nella numerazione, utilizza il primo numero disponibile.
        """
        # Ottieni tutte le postazioni usate dal cliente
        postazioni_usate = db.session.query(Estintore.postazione)\
                          .filter(Estintore.cliente_id == cliente_id)\
                          .order_by(Estintore.postazione).all()
        
        postazioni_usate = [p[0] for p in postazioni_usate]
        
        # Se non ci sono postazioni, inizia da 1
        if not postazioni_usate:
            return 1
        
        # Trova il primo "buco" nella sequenza
        for i in range(1, len(postazioni_usate)):
            if postazioni_usate[i] - postazioni_usate[i-1] > 1:
                return postazioni_usate[i-1] + 1
        
        # Se non ci sono buchi, restituisci l'ultimo numero + 1
        return postazioni_usate[-1] + 1
    
    @staticmethod
    def validate_capacita(tipologia, capacita):
        """Verifica che la capacità sia valida per il tipo di estintore"""
        if tipologia not in Estintore.CAPACITA_PER_TIPOLOGIA:
            return False
        
        return capacita in Estintore.CAPACITA_PER_TIPOLOGIA[tipologia]
    
    def to_dict(self):
        """Converte l'oggetto in un dizionario"""
        return {
            'id': self.id,
            'cliente_id': self.cliente_id,
            'tipologia': self.tipologia,
            'marca': self.marca,
            'matricola': self.matricola,
            'dislocazione': self.dislocazione,
            'postazione': self.postazione,
            'capacita': self.capacita,
            'data_fabbricazione': self.data_fabbricazione,
            'data_installazione': self.data_installazione.strftime('%d/%m/%Y') if self.data_installazione else None,
            'data_controllo': self.data_controllo.strftime('%d/%m/%Y') if self.data_controllo else None,
            'data_revisione': self.data_revisione.strftime('%d/%m/%Y') if self.data_revisione else None,
            'data_collaudo': self.data_collaudo.strftime('%d/%m/%Y') if self.data_collaudo else None,
            'stato': self.stato,
            'coordinate': self.coordinate,
            'note': self.note
        }
    
    def __repr__(self):
        return f'<Estintore {self.tipologia} {self.matricola}>'