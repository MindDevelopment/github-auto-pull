from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
import json
import os
from functools import wraps
from http import HTTPStatus

app = Flask(__name__)
app.secret_key = os.urandom(24)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'config', 'config.json')

# Error handling
class ConfigError(Exception):
    pass

# Helper functies
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ConfigError(f"Configuratie fout: {str(e)}")

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        restart_sync_service()
    except Exception as e:
        raise ConfigError(f"Fout bij opslaan configuratie: {str(e)}")

def restart_sync_service():
    try:
        os.system("taskkill /f /im python.exe /fi \"windowtitle eq sync_service\"")
        os.system("start cmd /k \"python app/sync_service.py\"")
    except Exception as e:
        raise ConfigError(f"Fout bij herstarten service: {str(e)}")

# Authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Not found"}), HTTPStatus.NOT_FOUND

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.errorhandler(ConfigError)
def config_error(error):
    return jsonify({"error": str(error)}), HTTPStatus.INTERNAL_SERVER_ERROR

# Base routes
# Base routes
@app.route('/')
def index():
    try:
        config = load_config()
        return render_template('index.html', 
                             repositories=config['repositories'],
                             readonly=True)
    except ConfigError as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            config = load_config()
            if (request.form['username'] == config['admin']['username'] and 
                request.form['password'] == config['admin']['password']):
                session['logged_in'] = True
                return redirect(url_for('admin'))
            return render_template('login.html', error="Ongeldige inloggegevens"), HTTPStatus.UNAUTHORIZED
        except ConfigError as e:
            return render_template('login.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required  # Alleen admin pagina vereist login
def admin():
    try:
        config = load_config()
        return render_template('admin.html', 
                             repositories=config['repositories'],
                             webhook=config['discord_webhook'])
    except ConfigError as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

# API routes
@app.route("/api/repositories", methods=["GET", "POST", "PUT", "DELETE"])
@admin_required
def manage_repositories():
    try:
        config = load_config()
        
        if request.method == "GET":
            return jsonify(config['repositories'])
        
        elif request.method == "POST":
            new_repo = request.json
            if not all(k in new_repo for k in ['name', 'url', 'local_path']):
                return jsonify({"error": "Missende velden"}), HTTPStatus.BAD_REQUEST
            config['repositories'].append(new_repo)
        
        elif request.method == "PUT":
            repo_data = request.json
            if not all(k in repo_data for k in ['old_name', 'name', 'url', 'local_path']):
                return jsonify({"error": "Missende velden"}), HTTPStatus.BAD_REQUEST
            for i, repo in enumerate(config['repositories']):
                if repo['name'] == repo_data['old_name']:
                    config['repositories'][i] = {
                        'name': repo_data['name'],
                        'url': repo_data['url'],
                        'local_path': repo_data['local_path']
                    }
                    break
            else:
                return jsonify({"error": "Repository niet gevonden"}), HTTPStatus.NOT_FOUND
        
        elif request.method == "DELETE":
            repo_name = request.json.get('name')
            if not repo_name:
                return jsonify({"error": "Naam niet opgegeven"}), HTTPStatus.BAD_REQUEST
            original_length = len(config['repositories'])
            config['repositories'] = [r for r in config['repositories'] 
                                    if r['name'] != repo_name]
            if len(config['repositories']) == original_length:
                return jsonify({"error": "Repository niet gevonden"}), HTTPStatus.NOT_FOUND
        
        save_config(config)
        return jsonify({"status": "success"})
        
    except ConfigError as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"error": "Onverwachte fout"}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/webhook", methods=["PUT"])
@admin_required
def update_webhook():
    try:
        webhook = request.json.get('webhook')
        if not webhook:
            return jsonify({"error": "Webhook URL niet opgegeven"}), HTTPStatus.BAD_REQUEST
        
        config = load_config()
        config['discord_webhook'] = webhook
        save_config(config)
        return jsonify({"status": "success"})
        
    except ConfigError as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"error": "Onverwachte fout"}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        config = load_config()
        return jsonify(config.get('sync_status', {}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
