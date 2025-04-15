from app import db
from datetime import datetime
import json

class Log(db.Model):
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    estintore_id = db.Column(db.Integer, db.ForeignKey('estintori.id', ondelete='SET NULL'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.id', ondelete='SET NULL'), nullable=True)
    azione = db.Column(db.String(50), nullable=False)
    dettagli = db.Column(db.Text, nullable=False)
    data_ora = db.Column(db.DateTime, default=lambda: datetime.now(), nullable=False)
    utente = db.Column(db.String(50), nullable=True)  # Per futura implementazione autenticazione
    
    def __init__(self, azione, dettagli, estintore_id=None, cliente_id=None, utente=None):
        self.azione = azione
        self.dettagli = json.dumps(dettagli) if isinstance(dettagli, dict) else dettagli
        self.estintore_id = estintore_id
        self.cliente_id = cliente_id
        self.utente = utente
    
    @property
    def dettagli_dict(self):
        """Restituisce i dettagli come dizionario, se erano stati salvati come JSON"""
        try:
            return json.loads(self.dettagli)
        except:
            return self.dettagli
    
    @staticmethod
    def log_estintore(azione, estintore, vecchi_valori=None, utente=None):
        """
        Registra un'operazione su un estintore
        
        :param azione: Tipo di azione (creazione, modifica, eliminazione)
        :param estintore: Oggetto Estintore dopo l'operazione
        :param vecchi_valori: Dizionario con i vecchi valori in caso di modifica
        :param utente: Nome utente che ha effettuato l'operazione
        """
        dettagli = {
            'estintore': estintore.to_dict(),
            'cliente_info': {
                'id': estintore.cliente_id,
                'azienda': estintore.cliente.azienda if hasattr(estintore, 'cliente') and estintore.cliente else None
            }
        }
        
        if vecchi_valori:
            dettagli['vecchi_valori'] = vecchi_valori
                
            # Identifica quali campi sono stati modificati
            campi_modificati = []
            for campo, valore in vecchi_valori.items():
                if campo in dettagli['estintore'] and dettagli['estintore'][campo] != valore:
                    campi_modificati.append({
                        'campo': campo,
                        'vecchio': valore,
                        'nuovo': dettagli['estintore'][campo]
                    })
            
            dettagli['campi_modificati'] = campi_modificati
        
        log = Log(
            azione=azione,
            dettagli=dettagli,
            estintore_id=estintore.id,
            cliente_id=estintore.cliente_id,  # Assicurati che cliente_id sia sempre impostato
            utente=utente
        )
        
        db.session.add(log)
        db.session.commit()
        
        return log
    
    @staticmethod
    def log_cliente(azione, cliente, vecchi_valori=None, utente=None):
        """
        Registra un'operazione su un cliente
    
        :param azione: Tipo di azione (creazione, modifica, eliminazione)
        :param cliente: Oggetto Cliente dopo l'operazione
        :param vecchi_valori: Dizionario con i vecchi valori in caso di modifica
        :param utente: Nome utente che ha effettuato l'operazione
        """
        dettagli = {
            'cliente': cliente.to_dict() if hasattr(cliente, 'to_dict') else cliente
        }
    
        if vecchi_valori:
            dettagli['vecchi_valori'] = vecchi_valori
        
            # Identifica quali campi sono stati modificati
            campi_modificati = []
            for campo, valore in vecchi_valori.items():
                if campo in dettagli['cliente'] and dettagli['cliente'][campo] != valore:
                    campi_modificati.append({
                    'campo': campo,
                    'vecchio': valore,
                    'nuovo': dettagli['cliente'][campo]
                    })
        
            dettagli['campi_modificati'] = campi_modificati
    
        # Assicuriamoci che cliente_id sia impostato correttamente
        cliente_id = cliente.id if hasattr(cliente, 'id') else None
    
        log = Log(
            azione=azione,
            dettagli=dettagli,
            cliente_id=cliente_id,  # Assicurati che sia impostato correttamente
            utente=utente
        )
    
        db.session.add(log)
        db.session.commit()
    
        return log
    
    def __repr__(self):
        return f'<Log {self.id}: {self.azione} su {"estintore" if self.estintore_id else "cliente"} in data {self.data_ora}>'
        

@classmethod
def log_fornitore(cls, azione, fornitore, vecchi_valori=None, utente=None):
    """Registra un'operazione su un fornitore nel log"""
    dettagli = {
        "fornitore": fornitore.to_dict()
    }
    
    if vecchi_valori:
        dettagli["vecchi_valori"] = vecchi_valori
    
    log = cls(
        azione=azione,
        dettagli=dettagli,
        utente=utente
    )
    
    db.session.add(log)
    db.session.commit()
    
    return log