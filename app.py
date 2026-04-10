from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import json
import os
import mimetypes

app = Flask(__name__)
CORS(app)

BASE_DIR = '/home/pi/ads-runner'
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'slides')
SLIDES_FILE = os.path.join(BASE_DIR, 'slides.json')

os.makedirs(MEDIA_DIR, exist_ok=True)

# Chunk size for streaming video — 1MB per chunk keeps workers responsive
CHUNK_SIZE = 1024 * 1024


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
    """
    Stream media files with HTTP range request support.
    Range requests are required for video scrubbing and prevent gunicorn
    worker timeouts caused by blocking sendall() on large files over Wi-Fi.
    Chromium will always send a Range header for video — this handles it correctly.
    """
    file_path = os.path.join(MEDIA_DIR, filename)

    # Safety check — prevent directory traversal
    real_path = os.path.realpath(file_path)
    real_media = os.path.realpath(MEDIA_DIR)
    if not real_path.startswith(real_media + os.sep):
        return Response('Forbidden', status=403)

    if not os.path.isfile(file_path):
        return Response('Not found', status=404)

    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or 'application/octet-stream'

    range_header = request.headers.get('Range')

    if range_header:
        # Parse Range: bytes=start-end
        try:
            byte_range = range_header.strip().replace('bytes=', '')
            start_str, end_str = byte_range.split('-')
            start = int(start_str)
            end = int(end_str) if end_str else file_size - 1
        except (ValueError, AttributeError):
            return Response('Invalid range', status=416)

        # Clamp end to file size
        end = min(end, file_size - 1)
        if start > end or start < 0:
            return Response(
                'Range Not Satisfiable', status=416,
                headers={'Content-Range': f'bytes */{file_size}'}
            )

        length = end - start + 1

        def generate_range():
            with open(file_path, 'rb') as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Content-Type': mime_type,
            'Cache-Control': 'no-cache',
        }
        return Response(generate_range(), status=206, headers=headers)

    else:
        # Full file request — still stream in chunks, don't block
        def generate_full():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk

        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size),
            'Content-Type': mime_type,
            'Cache-Control': 'no-cache',
        }
        return Response(generate_full(), status=200, headers=headers)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=False)