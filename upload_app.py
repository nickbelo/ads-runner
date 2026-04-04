from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, session, redirect, url_for,
    Response, stream_with_context
)
from flask_cors import CORS
from werkzeug.utils import secure_filename
from functools import wraps
import json
import os
import uuid
import subprocess
import threading
import datetime

try:
    import bcrypt
except ImportError:
    os.system("pip install bcrypt --break-system-packages")
    import bcrypt

app = Flask(__name__)
CORS(app)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = '/home/pi/ads-runner'
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'slides')
SLIDES_FILE = os.path.join(BASE_DIR, 'slides.json')
ENV_FILE = os.path.join(BASE_DIR, '.env')

os.makedirs(MEDIA_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov'}


# ── Load .env config ──────────────────────────────────────────────────────────
def load_env():
    config = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    config[k.strip()] = v.strip()
    return config


env = load_env()
app.secret_key = env.get('SECRET_KEY') or 'change-me-run-setup_auth.py'


# ── Helpers ───────────────────────────────────────────────────────────────────
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


def check_password(plain):
    env_data = load_env()
    hashed = env_data.get('ADMIN_PASSWORD_HASH', '')
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized', 'login': '/login'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET'])
def login_page():
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def do_login():
    data = request.get_json() or {}
    password = data.get('password', '')
    env_data = load_env()
    if not env_data.get('ADMIN_PASSWORD_HASH'):
        return jsonify({'error': 'No password set. Run setup_auth.py on the RPi first.'}), 503
    if check_password(password):
        session.permanent = True
        session['logged_in'] = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Incorrect password'}), 401


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


# ── Admin page ────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def admin():
    return render_template('admin.html')


# ── Slides API ────────────────────────────────────────────────────────────────
@app.route('/api/slides', methods=['GET'])
@login_required
def get_slides():
    return jsonify(load_slides())


@app.route('/api/slides', methods=['POST'])
@login_required
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
@login_required
def delete_slide(slide_id):
    slides = load_slides()
    updated = [s for s in slides if s['id'] != slide_id]
    if len(updated) == len(slides):
        return jsonify({'error': 'Slide not found'}), 404
    save_slides(updated)
    return jsonify({'ok': True})


@app.route('/api/slides/reorder', methods=['POST'])
@login_required
def reorder_slides():
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
    save_slides(data)
    return jsonify({'ok': True})


# ── Upload API ────────────────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
@login_required
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
    file.save(os.path.join(MEDIA_DIR, unique_name))
    file_type = 'video' if ext in {'mp4', 'webm', 'mov'} else 'image'
    return jsonify({'filename': unique_name, 'type': file_type, 'url': f'/media/{unique_name}'})


# ── Deploy ────────────────────────────────────────────────────────────────────
_deploy_lock = threading.Lock()


def _restart_self_after_delay(delay=2.0):
    """
    Restarts ads-upload in a background thread after a short delay.
    This lets the streaming response finish and flush to the browser
    before this process is terminated by systemd.
    """
    def _do_restart():
        import time
        time.sleep(delay)
        subprocess.run(['sudo', 'systemctl', 'restart', 'ads-upload'])
    t = threading.Thread(target=_do_restart, daemon=True)
    t.start()


def run_deploy():
    """
    Generator that runs each deploy step as a subprocess and yields
    log lines in real time. Yields structured lines:
      [STATUS] message   — INFO / OK / ERROR / WARN

    The final step (restarting ads-upload) is special: since this process
    IS ads-upload, we fire the restart in a background thread after a short
    delay and immediately yield success — giving the response time to flush
    before systemd kills the old process.
    """
    regular_steps = [
        {
            'label': 'Fetching latest code from GitHub',
            'cmd': ['git', '-C', BASE_DIR, 'fetch', '--all'],
        },
        {
            'label': 'Pulling changes (main branch)',
            'cmd': ['git', '-C', BASE_DIR, 'reset', '--hard', 'origin/main'],
        },
        {
            'label': 'Installing / updating dependencies',
            'cmd': [
                os.path.join(BASE_DIR, 'venv/bin/pip'),
                'install', '-r', os.path.join(BASE_DIR, 'requirements.txt'),
                '--quiet'
            ],
        },
        {
            'label': 'Restarting player service (ads-runner)',
            'cmd': ['sudo', 'systemctl', 'restart', 'ads-runner'],
        },
    ]

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    yield f"[INFO] Deploy started at {timestamp}\n"

    overall_ok = True

    for step in regular_steps:
        yield f"[INFO] ── {step['label']}...\n"
        try:
            result = subprocess.run(
                step['cmd'],
                capture_output=True,
                text=True,
                timeout=120
            )
            for line in result.stdout.splitlines():
                if line.strip():
                    yield f"[INFO] {line}\n"
            # pip writes progress to stderr — surface as WARN not ERROR
            for line in result.stderr.splitlines():
                if line.strip():
                    yield f"[WARN] {line}\n"

            if result.returncode == 0:
                yield f"[OK]   {step['label']} — done\n"
            else:
                yield f"[ERROR] {step['label']} failed (exit {result.returncode})\n"
                overall_ok = False
        except subprocess.TimeoutExpired:
            yield f"[ERROR] {step['label']} timed out after 120s\n"
            overall_ok = False
        except Exception as e:
            yield f"[ERROR] {step['label']} raised exception: {str(e)}\n"
            overall_ok = False

    # ── Self-restart step ─────────────────────────────────────────────────────
    # We cannot wait() on our own restart — systemd will SIGTERM this process.
    # Instead: schedule the restart 2s from now in a background thread so this
    # generator has time to flush the final lines to the browser first.
    yield f"[INFO] ── Restarting upload service (ads-upload)...\n"
    if overall_ok:
        _restart_self_after_delay(delay=2.0)
        yield f"[OK]   Restarting upload service (ads-upload) — restarting in background\n"
        yield f"[OK]   ── All steps completed successfully\n"
        yield f"[INFO] Service will restart in ~2 seconds. Page will reload automatically.\n"
        yield "[DONE] success\n"
    else:
        # Earlier steps failed — still restart so the service picks up any
        # partial code changes, but report overall failure.
        _restart_self_after_delay(delay=2.0)
        yield f"[WARN] Restarting upload service (ads-upload) despite earlier errors\n"
        yield f"[WARN] ── Deploy finished with errors — check output above\n"
        yield "[DONE] error\n"


@app.route('/api/deploy', methods=['POST'])
@login_required
def deploy():
    if not _deploy_lock.acquire(blocking=False):
        return jsonify({'error': 'A deploy is already in progress'}), 409

    def generate():
        try:
            yield from run_deploy()
        finally:
            _deploy_lock.release()

    return Response(
        stream_with_context(generate()),
        mimetype='text/plain',
        headers={
            'X-Accel-Buffering': 'no',   # disable nginx buffering if behind proxy
            'Cache-Control': 'no-cache',
        }
    )


@app.route('/api/deploy/status', methods=['GET'])
@login_required
def deploy_status():
    busy = not _deploy_lock.acquire(blocking=False)
    if not busy:
        _deploy_lock.release()
    return jsonify({'deploying': busy})


# ── Media serving ─────────────────────────────────────────────────────────────
@app.route('/media/<path:filename>')
@login_required
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=False)