from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
CONFIG_FILE = 'app/config/config.json'

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    restart_sync_service()

def restart_sync_service():
    os.system("taskkill /f /im python.exe /fi \"windowtitle eq sync_service\"")
    os.system("start cmd /k \"python app/sync_service.py\"")

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        config = load_config()
        if (request.form['username'] == config['admin']['username'] and 
            request.form['password'] == config['admin']['password']):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return redirect(url_for('login', error=True))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route("/")
def index():
    return redirect(url_for('admin'))

@app.route("/admin")
@admin_required
def admin():
    config = load_config()
    return render_template('admin.html', 
                         repositories=config['repositories'],
                         webhook=config['discord_webhook'])

@app.route("/api/repositories", methods=["GET", "POST", "PUT", "DELETE"])
@admin_required
def manage_repositories():
    config = load_config()
    
    if request.method == "GET":
        return jsonify(config['repositories'])
    
    elif request.method == "POST":
        new_repo = request.json
        config['repositories'].append(new_repo)
    
    elif request.method == "PUT":
        repo_data = request.json
        for i, repo in enumerate(config['repositories']):
            if repo['name'] == repo_data['old_name']:
                config['repositories'][i] = {
                    'name': repo_data['name'],
                    'url': repo_data['url'],
                    'local_path': repo_data['local_path']
                }
    
    elif request.method == "DELETE":
        repo_name = request.json['name']
        config['repositories'] = [r for r in config['repositories'] 
                                if r['name'] != repo_name]
    
    save_config(config)
    return jsonify({"status": "success"})

@app.route("/api/webhook", methods=["PUT"])
@admin_required
def update_webhook():
    config = load_config()
    config['discord_webhook'] = request.json['webhook']
    save_config(config)
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
