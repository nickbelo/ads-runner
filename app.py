from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Fix 2: Absolute paths so both apps always read/write the same files
BASE_DIR = '/home/pi/ads-runner'
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'slides')
SLIDES_FILE = os.path.join(BASE_DIR, 'slides.json')

os.makedirs(MEDIA_DIR, exist_ok=True)


def load_slides():
    if os.path.exists(SLIDES_FILE):
        with open(SLIDES_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=False)