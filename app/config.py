import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Chiave segreta per la protezione dei form
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chiave-segreta-difficile-da-indovinare'
    
    # Configurazione database SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, '../gestionale_geam.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurazione Bootstrap
    BOOTSTRAP_SERVE_LOCAL = True
    
    # Configurazione sessione
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)