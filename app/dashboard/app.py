from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

CONFIG_FILE = 'app/config/config.json'

@app.route("/")
def index():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return render_template('index.html', repositories=config['repositories'])

@app.route("/add_repo", methods=["POST"])
def add_repo():
    data = request.json
    with open(CONFIG_FILE, 'r+') as f:
        config = json.load(f)
        config['repositories'].append(data)
        f.seek(0)
        json.dump(config, f, indent=4)
    return jsonify({"message": "Repository toegevoegd."}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
