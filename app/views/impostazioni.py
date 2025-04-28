from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from app import db
import os
import datetime
import sqlite3
import shutil
import glob
import json

# Crea il blueprint
impostazioni_bp = Blueprint('impostazioni', __name__, url_prefix='/impostazioni')

def load_config():
    """Carica la configurazione locale (config.json)"""
    config_path = os.path.join(current_app.instance_path, 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            current_app.logger.error(f"Errore caricamento config.json: {e}")
    return {}


@impostazioni_bp.route('/')
def index():
    """Pagina principale delle impostazioni"""
    backups = get_backups()
    config = load_config()
    is_developer = config.get('developer_mode', False)  # Prende il valore da config.json
    return render_template('impostazioni/index.html', backups=backups, is_developer=is_developer)


@impostazioni_bp.route('/backup/create', methods=['POST'])
def create_backup():
    """Crea un nuovo backup del database"""
    try:
        # Ottieni il percorso del database principale
        db_path = db.engine.url.database
        
        # Crea il percorso della cartella di backup
        backup_folder = os.path.join(current_app.instance_path, 'backups')
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        # Crea il nome del file di backup con timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_folder, backup_filename)
        
        # Copia il database
        shutil.copy2(db_path, backup_path)
        
        # Elimina backup in eccesso (mantieni solo i 14 più recenti)
        cleanup_old_backups()
        
        flash(f'Backup creato con successo: {backup_filename}', 'success')
    except Exception as e:
        flash(f'Errore durante la creazione del backup: {str(e)}', 'danger')
    
    return redirect(url_for('impostazioni.index'))

@impostazioni_bp.route('/backup/download/<filename>')
def download_backup(filename):
    """Scarica un backup"""
    backup_folder = os.path.join(current_app.instance_path, 'backups')
    backup_path = os.path.join(backup_folder, filename)
    if not os.path.exists(backup_path):
        flash('Backup non trovato', 'danger')
        return redirect(url_for('impostazioni.index'))
    
    return send_file(backup_path, as_attachment=True)

@impostazioni_bp.route('/backup/delete/<filename>', methods=['POST'])
def delete_backup(filename):
    """Elimina un backup"""
    backup_folder = os.path.join(current_app.instance_path, 'backups')
    backup_path = os.path.join(backup_folder, filename)
    if not os.path.exists(backup_path):
        flash('Backup non trovato', 'danger')
    else:
        try:
            os.remove(backup_path)
            flash(f'Backup {filename} eliminato con successo', 'success')
        except Exception as e:
            flash(f'Errore durante l\'eliminazione del backup: {str(e)}', 'danger')
    
    return redirect(url_for('impostazioni.index'))

@impostazioni_bp.route('/db/check', methods=['POST'])
def check_db():
    """Verifica l'integrità del database"""
    try:
        # Ottieni il percorso del database principale
        db_path = db.engine.url.database
        
        # Crea una connessione al database
        conn = sqlite3.connect(db_path)
        
        # Esegui il comando PRAGMA integrity_check
        cursor = conn.cursor()
        cursor.execute('PRAGMA integrity_check;')
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == 'ok':
            flash('Controllo integrità database completato: nessun problema rilevato.', 'success')
        else:
            flash(f'Controllo integrità database completato: problemi rilevati! Dettagli: {result[0]}', 'danger')
    except Exception as e:
        flash(f'Errore durante il controllo del database: {str(e)}', 'danger')
    
    return redirect(url_for('impostazioni.index'))

@impostazioni_bp.route('/db/vacuum', methods=['POST'])
def vacuum_db():
    """Compatta il database"""
    try:
        # Ottieni il percorso del database principale
        db_path = db.engine.url.database
        
        # Crea una connessione al database
        conn = sqlite3.connect(db_path)
        
        # Esegui il comando VACUUM
        cursor = conn.cursor()
        cursor.execute('VACUUM;')
        conn.commit()
        conn.close()
        
        # Ottieni dimensione del file prima e dopo
        from os.path import getsize
        size_mb = getsize(db_path) / (1024 * 1024)
        
        flash(f'Database compattato con successo. Dimensione attuale: {size_mb:.2f} MB', 'success')
    except Exception as e:
        flash(f'Errore durante la compattazione del database: {str(e)}', 'danger')
    
    return redirect(url_for('impostazioni.index'))

def get_backups():
    """Ottieni la lista dei backup disponibili"""
    backup_folder = os.path.join(current_app.instance_path, 'backups')
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)
        
    backup_files = glob.glob(os.path.join(backup_folder, 'backup_*.db'))
    backups = []
    
    for backup_file in backup_files:
        filename = os.path.basename(backup_file)
        # Estrai timestamp dal nome del file
        try:
            timestamp_str = filename.replace('backup_', '').replace('.db', '')
            timestamp = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            size = os.path.getsize(backup_file)
            size_mb = size / (1024 * 1024)  # Converti in MB
            
            backups.append({
                'filename': filename,
                'timestamp': timestamp,
                'formatted_date': timestamp.strftime('%d/%m/%Y %H:%M:%S'),
                'size_mb': round(size_mb, 2)
            })
        except:
            # Se non riesci a estrarre il timestamp, usa l'ultima modifica del file
            timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(backup_file))
            size = os.path.getsize(backup_file)
            size_mb = size / (1024 * 1024)
            
            backups.append({
                'filename': filename,
                'timestamp': timestamp,
                'formatted_date': timestamp.strftime('%d/%m/%Y %H:%M:%S'),
                'size_mb': round(size_mb, 2)
            })
    
    # Ordina per timestamp decrescente (più recente prima)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return backups

def cleanup_old_backups():
    """Elimina i backup più vecchi se si supera il limite di 14"""
    backups = get_backups()
    if len(backups) > 14:
        # Ottieni i backup da eliminare (i più vecchi oltre i primi 14)
        to_delete = backups[14:]
        backup_folder = os.path.join(current_app.instance_path, 'backups')
        for backup in to_delete:
            try:
                os.remove(os.path.join(backup_folder, backup['filename']))
            except:
                pass
                
                
                
                
@impostazioni_bp.route('/versione/incrementa', methods=['POST'])
def incrementa_versione():
    """Incrementa la versione del programma e aggiorna il changelog"""
    from app.version import increment_version
    
    level = request.form.get('level', 'patch')
    if level not in ['patch', 'minor', 'major']:
        level = 'patch'

    changelog = request.form.get('changelog', '')  # prendiamo anche il changelog dal form

    nuova_versione = increment_version(level, changelog)

    flash(f'Versione incrementata a {nuova_versione}', 'success')
    return redirect(url_for('impostazioni.index'))


from flask import current_app   # aggiungi in cima insieme agli altri import

@impostazioni_bp.route("/toggle-mode", methods=["POST"])
def toggle_mode():
    pw = request.form.get("pw", "").strip()

    # password obbligatoria
    if pw != "emily":
        flash("Password errata o mancante: operazione annullata", "danger")
        return redirect(url_for("impostazioni.index"))

    # percorso del file di configurazione
    cfg_path = os.path.join(current_app.instance_path, "config.json")

    # leggi la config attuale (se manca, usa default)
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            current_app.logger.error(f"Config.json corrotto? {e}")

    # calcola la nuova modalità
    current = cfg.get("developer_mode", False)
    cfg["developer_mode"] = not current         # flip sviluppatore ⇄ produzione
    current_app.config["DEVELOPER_MODE"] = cfg["developer_mode"]  # aggiorno anche l’in-memory (facoltativo)

    # salva il file
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        flash(f"Impossibile salvare la configurazione: {e}", "danger")
        return redirect(url_for("impostazioni.index"))

    flash(
        "Modalità passata a PRODUZIONE" if current else "Modalità passata a SVILUPPO",
        "success",
    )
    return redirect(url_for("impostazioni.index"))
