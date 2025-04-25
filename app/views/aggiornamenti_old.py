import os
import json
import logging
import requests
import zipfile
import shutil
import datetime
from flask import Blueprint, render_template, current_app, flash, redirect, url_for, jsonify

aggiornamenti_bp = Blueprint('aggiornamenti', __name__, url_prefix='/aggiornamenti')

LOG_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOG_FOLDER, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_FOLDER, 'update.log'),
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UPDATE_CACHE_PATH = os.path.join(BASE_PATH, 'update_cache')
TEMP_PATH = os.path.join(UPDATE_CACHE_PATH, 'temp')
BACKUP_PATH = os.path.join(BASE_PATH, 'backups')
RELEASE_ZIP_PATH = os.path.join(UPDATE_CACHE_PATH, 'geam_release.zip')
VERSION_JSON_PATH = os.path.join(BASE_PATH, 'instance', 'version_config.json')
VERSION_JSON_URL = "https://raw.githubusercontent.com/Drnet-web/GEAM/main/instance/version_config.json"

os.makedirs(UPDATE_CACHE_PATH, exist_ok=True)
os.makedirs(TEMP_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)

def get_version_local():
    try:
        with open(VERSION_JSON_PATH, 'r') as f:
            return json.load(f)['version']
    except Exception as e:
        logging.error(f"Errore lettura versione locale: {e}")
        return None

def get_version_remote():
    try:
        response = requests.get(VERSION_JSON_URL, timeout=10)
        if response.status_code == 200:
            return response.json()['version']
        else:
            logging.warning(f"Versione remota non disponibile. Status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Errore lettura versione remota: {e}")
    return None

def build_release_url(version):
    try:
        tag = f"v{version['major']}.{version['minor']}.{version['patch']}"
        return f"https://github.com/Drnet-web/GEAM/archive/refs/tags/{tag}.zip"
    except Exception as e:
        logging.error(f"Errore nella costruzione dell'URL della release: {e}")
        return None

def is_update_in_progress():
    flag_path = os.path.join(current_app.instance_path, 'update_in_progress.flag')
    if os.path.exists(flag_path):
        try:
            creation_time = os.path.getmtime(flag_path)
            age_seconds = datetime.datetime.now().timestamp() - creation_time
            if age_seconds > 180:
                logging.warning("Flag aggiornamento trovato ma troppo vecchio. Eliminazione automatica.")
                os.remove(flag_path)
                return False
        except Exception as e:
            logging.error(f"Errore durante il controllo età flag: {e}")
        return True
    return False

def set_update_flag():
    with open(os.path.join(current_app.instance_path, 'update_in_progress.flag'), 'w') as f:
        f.write('1')

def clear_update_flag():
    flag_path = os.path.join(current_app.instance_path, 'update_in_progress.flag')
    if os.path.exists(flag_path):
        os.remove(flag_path)

def versioni_uguali(v1, v2):
    return v1 == v2

@aggiornamenti_bp.route('/')
def index():
    return render_template('aggiornamenti/index.html')

@aggiornamenti_bp.route('/api/check-version')
def check_version():
    locale = get_version_local()
    remota = get_version_remote()
    aggiorna = (not versioni_uguali(locale, remota)) if locale and remota else False
    return jsonify({
        'locale': locale,
        'remota': remota,
        'disponibile': aggiorna
    })

@aggiornamenti_bp.route('/api/download-release')
def download_release():
    if is_update_in_progress():
        return jsonify({'success': False, 'message': 'Aggiornamento già in corso.'})

    versione_remota = get_version_remote()
    url = build_release_url(versione_remota)
    if not url:
        return jsonify({'success': False, 'message': 'Errore creazione URL release.'})

    set_update_flag()
    try:
        logging.info(f"Download release da {url}")
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(RELEASE_ZIP_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info("Release scaricata con successo.")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': f"Errore HTTP {response.status_code}"})
    except Exception as e:
        logging.exception("Errore durante download")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        clear_update_flag()
        
def zip_selected_folders(zip_path, folders):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for folder in folders:
            abs_folder = os.path.join(BASE_PATH, folder)
            for root, dirs, files in os.walk(abs_folder):
                for file in files:
                    if file.endswith('.sqlite') or file.endswith('.zip'):
                        continue
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, BASE_PATH)
                    zf.write(full_path, rel_path)


@aggiornamenti_bp.route('/installa-release')
def installa_release():
    if is_update_in_progress():
        flash("Un aggiornamento è già in corso.", "danger")
        return redirect(url_for('aggiornamenti.index'))

    versione_locale = get_version_local()
    versione_remota = get_version_remote()
    if not versione_locale or not versione_remota:
        flash("Impossibile confrontare le versioni.", "danger")
        return redirect(url_for('aggiornamenti.index'))

    if versioni_uguali(versione_locale, versione_remota):
        flash("La versione installata è già aggiornata.", "info")
        return redirect(url_for('aggiornamenti.index'))

    set_update_flag()
    try:
        logging.info("Avvio procedura di installazione release...")

        with zipfile.ZipFile(RELEASE_ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(TEMP_PATH)

        cartelle = [d for d in os.listdir(TEMP_PATH) if os.path.isdir(os.path.join(TEMP_PATH, d))]
        logging.info(f"Contenuto TEMP_PATH dopo estrazione: {cartelle}")

        if not cartelle:
            raise Exception("Impossibile trovare la cartella estratta dentro update_cache/temp")

        estratta = cartelle[0]
        source_path = os.path.join(TEMP_PATH, estratta)
        logging.info(f"Path cartella sorgente da aggiornare: {source_path}")

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_zip = os.path.join(BACKUP_PATH, f"backup_GEAM_{timestamp}.zip")
        logging.info(f"Creo backup: {backup_zip}")

        zip_selected_folders(backup_zip, ['app', 'templates', 'instance'])

        logging.info("Backup creato correttamente.")

        for root, dirs, files in os.walk(source_path):
            for file in files:
                rel_dir = os.path.relpath(root, source_path)
                dest_dir = os.path.join(BASE_PATH, rel_dir)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(os.path.join(root, file), os.path.join(dest_dir, file))
                logging.info(f"Aggiornato file: {file}")

        with open(VERSION_JSON_PATH, 'w') as f:
            json.dump({"version": versione_remota}, f, indent=4)
        logging.info("Versione aggiornata localmente")

        flash("Aggiornamento completato con successo.", "success")
    except Exception as e:
        logging.exception("Errore durante l'installazione della release")
        flash(f"Errore durante l'installazione: {str(e)}", "danger")
    finally:
        clear_update_flag()
        shutil.rmtree(TEMP_PATH, ignore_errors=True)

    return redirect(url_for('aggiornamenti.index'))


@aggiornamenti_bp.route('/api/release-notes')
def release_notes():
    try:
        remote = get_version_remote()
        if not remote:
            return jsonify({'success': False, 'note': ''})

        version_str = f"v{remote['major']}.{remote['minor']}.{remote['patch']}"
        url = f"https://raw.githubusercontent.com/Drnet-web/GEAM/main/releases/{version_str}/note.txt"

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return jsonify({'success': True, 'note': response.text})
        else:
            return jsonify({'success': False, 'note': ''})
    except Exception as e:
        logging.error(f"Errore recupero note di rilascio da GitHub: {e}")
        return jsonify({'success': False, 'note': ''})
