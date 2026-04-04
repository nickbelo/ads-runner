from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import json, os, uuid

app = Flask(__name__)
MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media/slides')
SLIDES_FILE = os.path.join(os.path.dirname(__file__), 'slides.json')
ALLOWED = {'png','jpg','jpeg','gif','webp','mp4','webm','mov'}

os.makedirs(MEDIA_DIR, exist_ok=True)

def load_slides():
    if os.path.exists(SLIDES_FILE):
        with open(SLIDES_FILE) as f:
            return json.load(f)
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
    data = request.json
    slides = load_slides()
    slide = {
        'id': str(uuid.uuid4()),
        'type': data['type'],          # 'image' | 'video' | 'url' | 'youtube'
        'src': data['src'],
        'duration': data.get('duration', 10),
        'order': len(slides),
        'active': True
    }
    slides.append(slide)
    save_slides(slides)
    return jsonify(slide)

@app.route('/api/slides/<slide_id>', methods=['DELETE'])
def delete_slide(slide_id):
    slides = [s for s in load_slides() if s['id'] != slide_id]
    save_slides(slides)
    return jsonify({'ok': True})

@app.route('/api/slides/reorder', methods=['POST'])
def reorder():
    save_slides(request.json)
    return jsonify({'ok': True})

@app.route('/api/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file'}), 400
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED:
        return jsonify({'error': 'File type not allowed'}), 400
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    file.save(os.path.join(MEDIA_DIR, filename))
    file_type = 'video' if ext in {'mp4','webm','mov'} else 'image'
    return jsonify({'filename': filename, 'type': file_type, 'url': f'/media/{filename}'})

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)