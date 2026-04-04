Part 2 — The Ads Runner App Code
Project structure
ads-runner/
├── app.py                  # Flask app — slide player backend
├── upload_app.py           # Flask app — upload & admin panel
├── requirements.txt
├── slides.json             # Playlist config (auto-generated)
├── media/
│   └── slides/            # uploaded files live here
└── templates/
    ├── player.html         # fullscreen slide player
    └── admin.html         # upload + playlist manager
app.py — The media player backend
pythonfrom flask import Flask, render_template, jsonify, send_from_directory
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
upload_app.py — Upload & admin backend
pythonfrom flask import Flask, render_template, request, jsonify, send_from_directory
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
templates/player.html — The fullscreen player
html<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ads Runner</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #000; width: 100vw; height: 100vh; overflow: hidden; }
  #slide-container { width: 100%; height: 100%; position: relative; }
  .slide { position: absolute; inset: 0; display: none; }
  .slide.active { display: flex; align-items: center; justify-content: center; }
  .slide img { width: 100%; height: 100%; object-fit: contain; }
  .slide video { width: 100%; height: 100%; object-fit: contain; background: #000; }
  .slide iframe { width: 100%; height: 100%; border: none; }
</style>
</head>
<body>
<div id="slide-container"></div>
<script>
let slides = [], current = 0, timer = null;

async function fetchSlides() {
  const res = await fetch('/api/slides');
  slides = (await res.json()).filter(s => s.active);
}

function buildSlide(s) {
  const div = document.createElement('div');
  div.className = 'slide';
  div.dataset.id = s.id;

  if (s.type === 'image') {
    const img = document.createElement('img');
    img.src = `/media/slides/${s.src}`;
    div.appendChild(img);
  } else if (s.type === 'video') {
    const vid = document.createElement('video');
    vid.src = `/media/slides/${s.src}`;
    vid.muted = true; vid.autoplay = true; vid.loop = false;
    vid.addEventListener('ended', () => nextSlide());
    div.appendChild(vid);
  } else if (s.type === 'youtube') {
    const iframe = document.createElement('iframe');
    const vid = s.src.includes('v=') ? s.src.split('v=')[1].split('&')[0] : s.src.split('/').pop();
    iframe.src = `https://www.youtube.com/embed/${vid}?autoplay=1&mute=1&controls=0&loop=1&playlist=${vid}`;
    iframe.allow = 'autoplay';
    div.appendChild(iframe);
  } else if (s.type === 'url') {
    const iframe = document.createElement('iframe');
    iframe.src = s.src;
    div.appendChild(iframe);
  }
  return div;
}

function showSlide(index) {
  clearTimeout(timer);
  document.querySelectorAll('.slide').forEach(el => el.classList.remove('active'));
  if (!slides.length) return;
  current = ((index % slides.length) + slides.length) % slides.length;
  const s = slides[current];
  let el = document.querySelector(`[data-id="${s.id}"]`);
  if (!el) { el = buildSlide(s); document.getElementById('slide-container').appendChild(el); }
  el.classList.add('active');

  if (s.type === 'video') {
    const vid = el.querySelector('video');
    if (vid) { vid.currentTime = 0; vid.play(); return; }
  }
  if (s.type !== 'video') {
    timer = setTimeout(() => nextSlide(), (s.duration || 10) * 1000);
  }
}

function nextSlide() { showSlide(current + 1); }

async function init() {
  await fetchSlides();
  if (slides.length) {
    slides.forEach(s => {
      const el = buildSlide(s);
      document.getElementById('slide-container').appendChild(el);
    });
    showSlide(0);
  }
  // Refresh playlist every 30s for live updates
  setInterval(async () => {
    const old = slides.map(s => s.id).join(',');
    await fetchSlides();
    const newIds = slides.map(s => s.id).join(',');
    if (old !== newIds) {
      document.getElementById('slide-container').innerHTML = '';
      showSlide(0);
    }
  }, 30000);
}

init();
</script>
</body>
</html>

Part 3 — Upload & Admin UI
templates/admin.html — Upload panel (accessible from any device on the LAN)
html<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ads Runner — Admin</title>
<style>
  :root { --bg: #0f0f11; --card: #1a1a1f; --border: #2a2a32; --text: #e2e2e8; --muted: #888; --accent: #6c63ff; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font: 15px/1.6 system-ui, sans-serif; padding: 24px; }
  h1 { font-size: 22px; font-weight: 500; margin-bottom: 4px; }
  p.sub { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
  .card h2 { font-size: 16px; font-weight: 500; margin-bottom: 14px; }
  .drop-zone { border: 2px dashed var(--border); border-radius: 8px; padding: 32px; text-align: center; cursor: pointer; transition: border-color .2s; }
  .drop-zone:hover, .drop-zone.over { border-color: var(--accent); }
  .drop-zone p { color: var(--muted); font-size: 13px; margin-top: 8px; }
  input[type=file] { display: none; }
  .btn { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; cursor: pointer; }
  .btn:hover { opacity: .85; }
  .btn.danger { background: #c0392b; }
  .form-row { display: flex; gap: 10px; margin-bottom: 10px; }
  .form-row input, .form-row select { flex: 1; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; color: var(--text); font-size: 14px; }
  #slide-list { list-style: none; }
  #slide-list li { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
  #slide-list li:last-child { border-bottom: none; }
  .thumb { width: 80px; height: 48px; object-fit: cover; border-radius: 6px; background: var(--border); }
  .slide-info { flex: 1; }
  .slide-info strong { display: block; font-size: 14px; }
  .slide-info span { font-size: 12px; color: var(--muted); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 500; }
  .badge.image { background: #1a3a5c; color: #7ab8f5; }
  .badge.video { background: #3a1a3a; color: #c57af5; }
  .badge.url { background: #1a3a2a; color: #7af5a8; }
  .badge.youtube { background: #3a1a1a; color: #f57a7a; }
  #toast { position: fixed; bottom: 24px; right: 24px; background: var(--accent); color: #fff; padding: 10px 18px; border-radius: 8px; font-size: 14px; display: none; z-index: 99; }
</style>
</head>
<body>
<h1>Ads Runner</h1>
<p class="sub">Manage slides displayed on the TV · accessible on your local network</p>

<div class="card">
  <h2>Upload media</h2>
  <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
    <button class="btn">Choose files</button>
    <p>or drag & drop here · JPG, PNG, GIF, WebP, MP4, WebM, MOV</p>
  </div>
  <input type="file" id="file-input" multiple accept="image/*,video/*" onchange="handleFiles(this.files)">
</div>

<div class="card">
  <h2>Add URL or YouTube video</h2>
  <div class="form-row">
    <select id="url-type">
      <option value="url">Website URL</option>
      <option value="youtube">YouTube video</option>
    </select>
    <input type="text" id="url-src" placeholder="https://...">
    <input type="number" id="url-duration" placeholder="Duration (s)" value="30" style="max-width:140px">
    <button class="btn" onclick="addUrlSlide()">Add</button>
  </div>
</div>

<div class="card">
  <h2>Current playlist</h2>
  <ul id="slide-list"><li style="color:var(--muted);font-size:14px">Loading...</li></ul>
</div>

<div id="toast"></div>

<script>
async function loadSlides() {
  const res = await fetch('/api/slides');
  const slides = await res.json();
  const list = document.getElementById('slide-list');
  if (!slides.length) { list.innerHTML = '<li style="color:var(--muted);font-size:14px">No slides yet.</li>'; return; }
  list.innerHTML = slides.map(s => `
    <li>
      ${s.type === 'image' ? `<img class="thumb" src="/media/${s.src}" alt="">` : `<div class="thumb" style="display:flex;align-items:center;justify-content:center;font-size:12px;color:var(--muted)">${s.type}</div>`}
      <div class="slide-info">
        <strong>${s.src || s.type}</strong>
        <span>${s.duration}s &nbsp;</span><span class="badge ${s.type}">${s.type}</span>
      </div>
      <button class="btn danger" onclick="deleteSlide('${s.id}')">Remove</button>
    </li>
  `).join('');
}

async function handleFiles(files) {
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.filename) {
      await fetch('/api/slides', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: data.type, src: data.filename, duration: 10 })
      });
      toast(`Uploaded: ${file.name}`);
    }
  }
  loadSlides();
}

async function addUrlSlide() {
  const type = document.getElementById('url-type').value;
  const src = document.getElementById('url-src').value.trim();
  const duration = parseInt(document.getElementById('url-duration').value) || 30;
  if (!src) return;
  await fetch('/api/slides', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, src, duration })
  });
  document.getElementById('url-src').value = '';
  toast('Slide added');
  loadSlides();
}

async function deleteSlide(id) {
  await fetch(`/api/slides/${id}`, { method: 'DELETE' });
  toast('Slide removed');
  loadSlides();
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.style.display = 'block';
  setTimeout(() => el.style.display = 'none', 2500);
}

const dz = document.getElementById('drop-zone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('over'));
dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('over'); handleFiles(e.dataTransfer.files); });

loadSlides();
</script>
</body>
</html>

requirements.txt
flask==3.0.3
flask-cors==4.0.0
gunicorn==22.0.0
werkzeug==3.0.3

Accessing the admin panel from any device on the same network
From any phone, tablet, or laptop on the same Wi-Fi:
http://raspberrypi-1.local:3001
The TV displays the player at http://localhost:3000 via Chromium kiosk, while your devices manage the playlist through port 3001.

Quick reference — useful commands
bash# Deploy new code from GitHub
ssh pi@raspberrypi-1.local '/home/pi/deploy.sh'

# Check service status
sudo systemctl status ads-runner ads-display ads-upload

# View logs
journalctl -u ads-runner -f
journalctl -u ads-display -f

# Restart everything
sudo systemctl restart ads-runner ads-upload ads-display

# Manually trigger display refresh (if Chromium needs a reload)
DISPLAY=:0 xdotool key ctrl+r

That covers all 3 parts. To summarize what you get: the RPi boots → systemd starts Flask + Chromium kiosk automatically → the TV shows your slides → anyone on the local network can open raspberrypi-1.local:3001 to upload images/videos or paste YouTube/website URLs. New slides appear within 30 seconds without restarting anything.
Want me to generate any of these files as downloadable files, or move on to adding features like slide scheduling with time windows, or a drag-to-reorder playlist UI?