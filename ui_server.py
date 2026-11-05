"""Offline workbench. Run: python3 ui_server.py --port 0"""
import argparse
import csv
import io
import json
import mimetypes
import os
import tempfile
import uuid
import subprocess
import sys
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

LIMIT = 512 * 1024
FIELDS = ['id', 'characters', 'scene', 'camera', 'motion']

class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.lock = threading.RLock()

    def path(self, name):
        p = self.root
        for part in Path(name).parts:
            if part in ('..', '.') or part.startswith('.') or '/' in part:
                raise ValueError('Đường dẫn không hợp lệ')
            p = p / part
            if p.is_symlink(): raise ValueError('Không hỗ trợ liên kết tượng trưng')
        if not p.is_relative_to(self.root): raise ValueError('Đường dẫn không hợp lệ')
        return p

    def text(self, name):
        return self.path(name).read_text(encoding='utf-8')

    def atomic_write(self, name, content):
        target = self.path(name)
        if target.exists():
            backup = self.path('ui-backups/' + uuid.uuid4().hex + '/' + name)
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(target.read_bytes())
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='ui-write-', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(content); f.flush(); os.fsync(f.fileno())
            os.replace(temp, target)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def validate(self, script, scene_text):
        ids = re.findall(r'^\s*(\d{3})[.:)\-]?\s+.+$', script, re.M)
        if not ids or len(ids) != len(set(ids)):
            raise ValueError('Kịch bản cần ID ba chữ số duy nhất, ví dụ 001. Lời thoại')
        reader = csv.DictReader(io.StringIO(scene_text), strict=True)
        if reader.fieldnames != FIELDS: raise ValueError('CSV cần đúng cột: ' + ', '.join(FIELDS))
        try: rows = list(reader)
        except csv.Error as e: raise ValueError('CSV không hợp lệ: ' + str(e))
        seen = []
        known = {p.name for p in self.path('characters').iterdir() if p.is_dir() and not p.is_symlink()}
        for row in rows:
            if set(row) != set(FIELDS) or any(v is None for v in row.values()): raise ValueError('Số cột CSV không đúng')
            sid = row['id']
            if not re.fullmatch(r'\d{3}', sid) or sid in seen: raise ValueError('ID cảnh phải là ba chữ số và không trùng')
            seen.append(sid)
            for key in ('scene', 'camera', 'motion'):
                if not row[key].strip(): raise ValueError(f'Cảnh {sid}: thiếu {key}')
            names = [x.strip() for x in row['characters'].split(';') if x.strip()]
            if any(n not in known for n in names): raise ValueError(f'Cảnh {sid}: nhân vật không tồn tại')
        if set(seen) != set(ids): raise ValueError('ID cảnh phải khớp chính xác ID câu trong script.md')
        return rows

    def save(self, data):
        name, content = data.get('file'), data.get('content')
        if name not in ('script.md', 'style.md', 'scenes.csv') or not isinstance(content, str) or not content.strip():
            raise ValueError('Tệp hoặc nội dung không hợp lệ')
        if name in ('script.md', 'scenes.csv'):
            self.validate(content if name == 'script.md' else self.text('script.md'), content if name == 'scenes.csv' else self.text('scenes.csv'))
        self.atomic_write(name, content.encode('utf-8'))
        return {'message': 'Đã lưu; bản trước được giữ trong ui-backups/'}

    def motion(self):
        self.validate(self.text('script.md'), self.text('scenes.csv'))
        with tempfile.TemporaryDirectory(prefix='ui-motion-', dir=self.root) as temp:
            stage = Path(temp)
            for name in ('scripts/build_motion_prompts.py', 'scenes.csv', 'out/audio/timing.csv', 'out/motion_prompts.csv'):
                src = self.path(name)
                if src.exists():
                    dst = stage / name; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(src.read_bytes())
            (stage / 'out').mkdir(exist_ok=True)
            result = subprocess.run([sys.executable, '-I', str(stage / 'scripts/build_motion_prompts.py')], cwd=stage, capture_output=True, text=True, timeout=20)
            if result.returncode: raise ValueError('Không tạo được prompt: ' + result.stderr[-1500:])
            output = (stage / 'out/motion_prompts.csv').read_bytes()
            self.atomic_write('out/motion_prompts.csv', output)
        return {'message': 'Đã tạo motion_prompts.csv bằng script cục bộ; không gọi mạng.'}

    def state(self):
        scenes = list(csv.DictReader(io.StringIO(self.text('scenes.csv'))))
        characters, assets = [], []
        def asset(rel):
            p = self.path(rel)
            if p.is_file() and p.stat().st_size:
                assets.append({'path': rel, 'url': '/assets/' + rel, 'bytes': p.stat().st_size})
                return '/assets/' + rel
            return None
        cp = self.path('characters')
        for d in sorted(cp.iterdir()):
            if d.is_symlink() or not d.is_dir() or not re.fullmatch(r'[a-zA-Z0-9_-]+', d.name): continue
            desc = self.text(f'characters/{d.name}/desc.txt')
            images = []
            for p in sorted(d.iterdir()):
                if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp') and re.fullmatch(r'[a-zA-Z0-9_-]+\.[a-zA-Z]+', p.name):
                    url = asset(f'characters/{d.name}/{p.name}')
                    if url: images.append(url)
            characters.append({'name': d.name, 'description': desc, 'images': images})
        for s in scenes:
            sid = s['id']
            if not re.fullmatch(r'\d{3}', sid): continue
            for folder, ext in [('images', 'png'), ('images', 'jpg'), ('audio', 'mp3'), ('videos', 'mp4')]:
                asset(f'out/{folder}/{sid}.{ext}')
        for rel in ('out/audio/voiceover.mp3', 'out/audio/subtitles.srt', 'out/final.mp4'):
            asset(rel)
        mp = self.path('out/motion_prompts.csv')
        prompts = list(csv.DictReader(io.StringIO(mp.read_text(encoding='utf-8')))) if mp.exists() else []
        return {'script': self.text('script.md'), 'style': self.text('style.md'), 'scenes': scenes,
                'characters': characters, 'assets': assets, 'prompts': prompts,
                'timing_available': self.path('out/audio/timing.csv').is_file(),
                'capabilities': {'motion': True, 'image': False, 'tts': False, 'video': False, 'render': False}}


def make_server(root, port=0):
    project = Project(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args): pass
        def reply(self, status, data, mime='application/json; charset=utf-8'):
            if not isinstance(data, bytes): data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; media-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers(); self.wfile.write(data)
        def host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')
        def do_GET(self):
            if not self.host_ok(): return self.reply(403, {'error': 'Host không hợp lệ'})
            try:
                with project.lock:
                    if self.path == '/favicon.ico': return self.reply(204, b'', 'image/x-icon')
                    if self.path == '/api/state': return self.reply(200, project.state())
                    static = {'/': ('ui/index.html', 'text/html; charset=utf-8'), '/app.js': ('ui/app.js', 'text/javascript; charset=utf-8'), '/app.css': ('ui/app.css', 'text/css; charset=utf-8')}
                    if self.path in static:
                        name, mime = static[self.path]; return self.reply(200, project.path(name).read_bytes(), mime)
                    if self.path.startswith('/assets/'):
                        rel = self.path[len('/assets/'):]
                        if rel in {a['path'] for a in project.state()['assets']}:
                            return self.reply(200, project.path(rel).read_bytes(), mimetypes.guess_type(rel)[0] or 'application/octet-stream')
                    return self.reply(404, {'error': 'Không tìm thấy'})
            except (ValueError, OSError, KeyError) as e: self.reply(400, {'error': str(e)})
        def do_POST(self):
            if not self.host_ok(): return self.reply(403, {'error': 'Host không hợp lệ'})
            expected = 'http://' + self.headers.get('Host', '')
            if self.headers.get('Origin') != expected:
                return self.reply(403, {'error': 'Origin không hợp lệ'})
            if self.headers.get('Transfer-Encoding'):
                return self.reply(400, {'error': 'Không hỗ trợ Transfer-Encoding'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 1 or size > LIMIT: return self.reply(413, {'error': 'Giới hạn 512 KiB'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.reply(415, {'error': 'Yêu cầu JSON'})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict): raise ValueError('Yêu cầu JSON object')
                with project.lock:
                    if self.path == '/api/motion': return self.reply(200, project.motion())
                    if self.path == '/api/save': return self.reply(200, project.save(data))
                    self.reply(404, {'error': 'Chưa tích hợp thao tác này'})
            except (ValueError, OSError, KeyError, TypeError) as e:
                self.reply(400, {'error': str(e)})
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.project = project
    return server

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    if args.port == 3000: parser.error('Port 3000 is reserved')
    server = make_server(Path(__file__).resolve().parent, args.port)
    print(f'UI http://127.0.0.1:{server.server_port}', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
