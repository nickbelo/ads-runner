from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import os
import uuid

app = Flask(__name__)
CORS(app)

# Fix 2: Absolute paths so both apps always read/write the same files
BASE_DIR = '/home/pi/ads-runner'
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'slides')
SLIDES_FILE = os.path.join(BASE_DIR, 'slides.json')

os.makedirs(MEDIA_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS


def load_slides():
    if os.path.exists(SLIDES_FILE):
        with open(SLIDES_FILE) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def save_slides(slides):
    with open(SLIDES_FILE, 'w') as f:
        json.dump(slides, f, indent=2)


@app.route('/')
def admin():
    return render_template('admin.html')


@app.route('/api/slides', methods=['GET'])
def get_slides():
    return jsonify(load_slides())


@app.route('/api/slides', methods=['POST'])
def add_slide():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    slides = load_slides()
    slide = {
        'id': str(uuid.uuid4()),
        'type': data.get('type', 'image'),
        'src': data.get('src', ''),
        'duration': int(data.get('duration', 10)),
        'order': len(slides),
        'active': True
    }
    slides.append(slide)
    save_slides(slides)
    return jsonify(slide), 201


@app.route('/api/slides/<slide_id>', methods=['DELETE'])
def delete_slide(slide_id):
    slides = load_slides()
    updated = [s for s in slides if s['id'] != slide_id]
    if len(updated) == len(slides):
        return jsonify({'error': 'Slide not found'}), 404
    save_slides(updated)
    return jsonify({'ok': True})


@app.route('/api/slides/reorder', methods=['POST'])
def reorder_slides():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_slides(data)
    return jsonify({'ok': True})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    unique_name = f"{uuid.uuid4()}.{ext}"
    save_path = os.path.join(MEDIA_DIR, unique_name)
    file.save(save_path)

    file_type = 'video' if ext in {'mp4', 'webm', 'mov'} else 'image'

    return jsonify({
        'filename': unique_name,
        'type': file_type,
        'url': f'/media/{unique_name}'
    })


# Fix 4: Serve uploaded media so thumbnails appear correctly in admin
@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=False)