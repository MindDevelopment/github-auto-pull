from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
import json
import os
import logging
from functools import wraps
from http import HTTPStatus
from datetime import timedelta

app = Flask(__name__)
# Gebruik een vast secret key of haal deze uit environment variables
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
# Session timeout instellen
app.permanent_session_lifetime = timedelta(hours=1)

CONFIG_FILE = 'app/config/config.json'
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Logging configuratie
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Custom exception voor configuratie gerelateerde fouten"""
    pass

def load_config():
    """Laad configuratie met verbeterde error handling"""
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            # Valideer required fields
            required_fields = ['repositories', 'discord_webhook', 'admin']
            if not all(field in config for field in required_fields):
                raise ConfigError("Missende verplichte configuratie velden")
            return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Configuratie fout: {str(e)}")
        raise ConfigError(f"Configuratie fout: {str(e)}")

def save_config(config):
    """Laad configuratie met verbeterde error handling"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Configuratie fout: {str(e)}")
        raise ConfigError(f"Configuratie fout: {str(e)}")

def restart_sync_service():
    """Herstart sync service met verbeterde error handling"""
    try:
        # Stop bestaande service
        os.system("pkill -f 'python.*sync_service.py'")
        # Start nieuwe service
        os.system("nohup python app/sync_service.py > /dev/null 2>&1 &")
    except Exception as e:
        logger.error(f"Fout bij herstarten service: {str(e)}")
        raise ConfigError(f"Fout bij herstarten service: {str(e)}")

def admin_required(f):
    """Verbeterde admin authenticatie decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), HTTPStatus.NOT_FOUND

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), HTTPStatus.INTERNAL_SERVER_ERROR

@app.errorhandler(ConfigError)
def config_error(error):
    return render_template('error.html', error=str(error)), HTTPStatus.INTERNAL_SERVER_ERROR

# Static files route
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files met caching"""
    return send_from_directory(STATIC_FOLDER, filename, cache_timeout=300)

# Routes
@app.route('/')
def index():
    try:
        config = load_config()
        return render_template('index.html', 
                             repositories=config['repositories'],
                             readonly=True)
    except ConfigError as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            config = load_config()
            if (request.form['username'] == config['admin']['username'] and 
                request.form['password'] == config['admin']['password']):
                session.permanent = True
                session['logged_in'] = True
                next_page = request.args.get('next') or url_for('admin')
                return redirect(next_page)
            return render_template('login.html', error="Invalid credentials"), HTTPStatus.UNAUTHORIZED
        except ConfigError as e:
            return render_template('login.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    try:
        config = load_config()
        return render_template('admin.html', 
                             repositories=config['repositories'],
                             webhook=config['discord_webhook'])
    except ConfigError as e:
        return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR

# API routes
@app.route("/api/repositories", methods=["GET", "POST", "PUT", "DELETE"])
@admin_required
def manage_repositories():
    try:
        config = load_config()
        
        if request.method == "POST":
            new_repo = request.json
            if not all(k in new_repo for k in ['name', 'url', 'local_path']):
                return jsonify({"error": "Missing required fields"}), HTTPStatus.BAD_REQUEST
            
            # Controleer of repository al bestaat
            if any(repo['name'] == new_repo['name'] for repo in config['repositories']):
                return jsonify({"error": "Repository name already exists"}), HTTPStatus.BAD_REQUEST
            
            # Voeg nieuwe repository toe
            config['repositories'].append(new_repo)
            
            # Initialiseer sync status voor nieuwe repository
            if 'sync_status' not in config:
                config['sync_status'] = {}
            if 'last_sync_times' not in config['sync_status']:
                config['sync_status']['last_sync_times'] = {}
            if 'sync_errors' not in config['sync_status']:
                config['sync_status']['sync_errors'] = {}
            if 'sync_statistics' not in config['sync_status']:
                config['sync_status']['sync_statistics'] = {}
            
            config['sync_status']['last_sync_times'][new_repo['name']] = None
            config['sync_status']['sync_errors'][new_repo['name']] = []
            config['sync_status']['sync_statistics'][new_repo['name']] = {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0
            }
            
            # Sla de configuratie op
            save_config(config)
            return jsonify({"status": "success"})
            
        elif request.method == "DELETE":
            repo_name = request.json.get('name')
            if not repo_name:
                return jsonify({"error": "Repository name required"}), HTTPStatus.BAD_REQUEST
            
            original_length = len(config['repositories'])
            config['repositories'] = [r for r in config['repositories'] if r['name'] != repo_name]
            
            if len(config['repositories']) == original_length:
                return jsonify({"error": "Repository not found"}), HTTPStatus.NOT_FOUND
            
            save_config(config)
            return jsonify({"status": "success"})
            
    except Exception as e:
        logging.error(f"Error in manage_repositories: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route("/api/webhook", methods=["PUT"])
@admin_required
def update_webhook():
    try:
        webhook = request.json.get('webhook')
        if not webhook:
            return jsonify({"error": "Webhook URL required"}), HTTPStatus.BAD_REQUEST
        
        config = load_config()
        config['discord_webhook'] = webhook
        save_config(config)
        return jsonify({"status": "success"})
        
    except ConfigError as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        logger.error(f"Error in update_webhook: {str(e)}")
        return jsonify({"error": "Unexpected error"}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        config = load_config()
        return jsonify(config.get('sync_status', {}))
    except Exception as e:
        logger.error(f"Error in get_status: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

if __name__ == "__main__":
    # Production configuratie
    app.debug = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host="0.0.0.0", port=5000, threaded=True)
