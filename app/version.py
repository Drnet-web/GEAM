import os
import json
from flask import current_app
import datetime

# Percorso del file di configurazione
CONFIG_FILE = 'version_config.json'

def get_config_path():
    """Ottieni il percorso completo del file di configurazione"""
    instance_path = current_app.instance_path
    return os.path.join(instance_path, CONFIG_FILE)

def load_config():
    """Carica la configurazione dal file"""
    config_path = get_config_path()
    
    # Se il file di configurazione non esiste, crea uno default
    if not os.path.exists(config_path):
        default_config = {
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            },
            "last_update": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Assicurati che la directory instance esista
        if not os.path.exists(current_app.instance_path):
            os.makedirs(current_app.instance_path)
            
        # Salva la configurazione default
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        
        return default_config
    
    # Carica la configurazione esistente
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Errore nel caricamento della configurazione: {str(e)}")
        return {
            "version": {
                "major": 1,
                "minor": 0, 
                "patch": 0
            },
            "last_update": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def save_config(config):
    """Salva la configurazione nel file"""
    config_path = get_config_path()
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        current_app.logger.error(f"Errore nel salvataggio della configurazione: {str(e)}")
        return False

def get_version():
    """Ottieni la versione corrente come stringa"""
    config = load_config()
    version = config.get('version', {"major": 1, "minor": 0, "patch": 0})
    return f"{version['major']}.{version['minor']}.{version['patch']}"

def increment_version(level='patch', changelog=''):
    """Incrementa la versione al livello specificato (patch, minor, major) e aggiorna il changelog"""
    
    config = load_config()
    version = config.get('version', {"major": 1, "minor": 0, "patch": 0})
    
    if level == 'patch':
        version['patch'] += 1
    elif level == 'minor':
        version['minor'] += 1
        version['patch'] = 0
    elif level == 'major':
        version['major'] += 1
        version['minor'] = 0
        version['patch'] = 0
    
    config['version'] = version
    config['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if changelog:
        config['changelog'] = changelog.replace('\r\n', '\n')  # normalizza ritorni a capo
    
    save_config(config)
    return f"{version['major']}.{version['minor']}.{version['patch']}"
