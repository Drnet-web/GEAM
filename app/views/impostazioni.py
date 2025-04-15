from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app
from app import db
import os
import datetime
import sqlite3
import shutil
import glob

# Crea il blueprint
impostazioni_bp = Blueprint('impostazioni', __name__, url_prefix='/impostazioni')

@impostazioni_bp.route('/')
def index():
    """Pagina principale delle impostazioni"""
    # Ottieni la lista dei backup disponibili
    backups = get_backups()
    return render_template('impostazioni/index.html', backups=backups)

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
    """Incrementa la versione del programma"""
    from app.version import increment_version
    
    # Ottieni il livello di incremento dall'input
    level = request.form.get('level', 'patch')
    if level not in ['patch', 'minor', 'major']:
        level = 'patch'
    
    # Incrementa la versione
    nuova_versione = increment_version(level)
    
    flash(f'Versione incrementata a {nuova_versione}', 'success')
    return redirect(url_for('impostazioni.index'))