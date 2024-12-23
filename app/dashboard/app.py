from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from werkzeug.security import safe_string_compare as safe_str_cmp
import os
import logging
from functools import wraps
from http import HTTPStatus
from datetime import timedelta
from utils.database import DatabaseConnection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging configuration eerst
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-here'),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    TEMPLATES_AUTO_RELOAD=True
)

# Database connection in een try-except block
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
            # Gebruik safe_str_cmp voor veilige string vergelijking
            if (safe_str_cmp(request.form.get('username', ''), os.getenv('ADMIN_USERNAME', '')) and 
                safe_str_cmp(request.form.get('password', ''), os.getenv('ADMIN_PASSWORD', ''))):
                session.permanent = True
                session['logged_in'] = True
                next_page = request.args.get('next') or url_for('admin')
                return redirect(next_page)
            logger.warning(f"Failed login attempt for user: {request.form.get('username')}")
            return render_template('login.html', error="Invalid credentials"), HTTPStatus.UNAUTHORIZED
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
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
                             webhook=os.getenv('DISCORD_WEBHOOK'))
    except Exception as e:
        logger.error(f"Admin page error: {str(e)}")
        return render_template('error.html', error=str(e)), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/repositories", methods=["GET", "POST", "DELETE"])
@admin_required
def manage_repositories():
    try:
        if request.method == "POST":
            new_repo = request.get_json()
            if not new_repo or not all(k in new_repo for k in ['name', 'url', 'local_path']):
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
        logger.error(f"Repository management error: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

@app.route("/api/webhook", methods=["PUT"])
@admin_required
def update_webhook():
    try:
        webhook_data = request.get_json()
        webhook = webhook_data.get('webhook') if webhook_data else None
        if not webhook:
            return jsonify({"error": "Webhook URL required"}), HTTPStatus.BAD_REQUEST
        
        # Update webhook in environment en .env file
        os.environ['DISCORD_WEBHOOK'] = webhook
        with open('.env', 'r') as f:
            lines = f.readlines()
        with open('.env', 'w') as f:
            updated = False
            for line in lines:
                if line.startswith('DISCORD_WEBHOOK='):
                    f.write(f'DISCORD_WEBHOOK={webhook}\n')
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f'\nDISCORD_WEBHOOK={webhook}\n')
                
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Webhook update error: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
