from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
import json
import os
import logging
from filelock import FileLock
from functools import wraps
from http import HTTPStatus
from datetime import timedelta
from utils.database import DatabaseConnection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.permanent_session_lifetime = timedelta(hours=1)


# Update de database initialisatie
try:
    db = DatabaseConnection(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'github_auto_pull')
    )
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    raise

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    try:
        repositories = db.get_all_repositories()
        return render_template('index.html', 
                             repositories=repositories,
                             readonly=True)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            if (request.form['username'] == os.environ.get('ADMIN_USERNAME') and 
                request.form['password'] == os.environ.get('ADMIN_PASSWORD')):
                session.permanent = True
                session['logged_in'] = True
                next_page = request.args.get('next') or url_for('admin')
                return redirect(next_page)
            return render_template('login.html', error="Invalid credentials"), HTTPStatus.UNAUTHORIZED
        except Exception as e:
            return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    try:
        repositories = db.get_all_repositories()
        return render_template('admin.html', 
                             repositories=repositories,
                             webhook=os.environ.get('DISCORD_WEBHOOK'))
    except Exception as e:
        return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/repositories", methods=["GET", "POST", "DELETE"])
@admin_required
def manage_repositories():
    try:
        if request.method == "POST":
            new_repo = request.json
            if not all(k in new_repo for k in ['name', 'url', 'local_path']):
                return jsonify({"error": "Missing required fields"}), HTTPStatus.BAD_REQUEST
            
            repo_id = db.add_repository(
                new_repo['name'],
                new_repo['url'],
                new_repo['local_path']
            )
            return jsonify({"status": "success", "id": repo_id})
        
        elif request.method == "GET":
            repositories = db.get_all_repositories()
            return jsonify(repositories)
            
        elif request.method == "DELETE":
            repo_id = request.args.get('id')
            if not repo_id:
                return jsonify({"error": "Repository ID required"}), HTTPStatus.BAD_REQUEST
            
            db.delete_repository(repo_id)
            return jsonify({"status": "success"})
            
    except Exception as e:
        logger.error(f"Error in manage_repositories: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/webhook", methods=["PUT"])
@admin_required
def update_webhook():
    try:
        webhook = request.json.get('webhook')
        if not webhook:
            return jsonify({"error": "Webhook URL required"}), HTTPStatus.BAD_REQUEST
        
        # Update webhook in environment
        os.environ['DISCORD_WEBHOOK'] = webhook
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error in update_webhook: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

if __name__ == "__main__":
    app.debug = False
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host="0.0.0.0", port=5000, threaded=True)
