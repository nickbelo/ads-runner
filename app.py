from flask import Flask, render_template, jsonify, send_from_directory
import json, os

app = Flask(__name__)
MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media/slides')
SLIDES_FILE = os.path.join(os.path.dirname(__file__), 'slides.json')

def load_slides():
    if os.path.exists(SLIDES_FILE):
        with open(SLIDES_FILE) as f:
            return json.load(f)
    return []

@app.route('/')
def player():
    return render_template('player.html')

@app.route('/api/slides')
def get_slides():
    return jsonify(load_slides())

@app.route('/media/slides/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)