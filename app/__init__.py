import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

# Inizializza le estensioni
db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap5()

# Abilita il supporto per le chiavi esterne in SQLite
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def create_app(config=None):
    app = Flask(__name__)
    
    # Configurazione
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'geam.sqlite'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    
    # Stampa il percorso del database per debug
    print("Database path:", os.path.join(app.instance_path, 'geam.sqlite'))
    
    # Assicurati che la cartella instance esista
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Aggiungi questo per rendere disponibile la versione in tutti i template
    @app.context_processor
    def inject_version():
        try:
            from app.version import get_version
            return {'version': get_version()}
        except Exception:
            return {'version': '1.0.0'}  # Valore di fallback
    
    # Inizializza le estensioni con l'app
    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    
    # Registra i blueprint
    from app.views.dashboard import dashboard_bp
    from app.views.clienti import clienti_bp
    from app.views.estintori import estintori_bp
    from app.views.impostazioni import impostazioni_bp
    from app.views.report import report_bp  # Aggiungi questa riga
    from app.views.fornitori import fornitori_bp
    from app.views.aggiornamenti import aggiornamenti_bp
    from app.views.timeline import timeline_bp

    
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clienti_bp)
    app.register_blueprint(estintori_bp)
    app.register_blueprint(impostazioni_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(fornitori_bp)
    app.register_blueprint(aggiornamenti_bp)
    app.register_blueprint(timeline_bp)
    
    # Configurazione del logging
    if not app.debug:
        handler = logging.FileHandler(os.path.join(app.instance_path, 'geam.log'))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
    
    # Crea le tabelle se non esistono
    with app.app_context():
        db.create_all()
    
    # Filtro personalizzato per Jinja2 (conversione newline in <br>)
    @app.template_filter('nl2br')
    def nl2br(value):
        if value:
            return value.replace('\n', '<br>')
        return ''
    
    return app