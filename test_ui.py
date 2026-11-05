"""Real local HTTP integration tests; no third-party packages."""
import csv
import http.client
import importlib.util
import io
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class UITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ('script.md', 'scenes.csv', 'style.md', 'characters', 'scripts', 'out', 'ui'):
            src = ROOT / name
            if src.is_dir(): shutil.copytree(src, self.root / name)
            else: shutil.copy2(src, self.root / name)
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.tmp.cleanup()

    def start(self):
        self.assertTrue((ROOT / 'ui_server.py').exists(), 'Local UI server is not implemented')
        spec = importlib.util.spec_from_file_location('ui_server', ROOT / 'ui_server.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.server = mod.make_server(self.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.port = self.server.server_port

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        hs = {'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'application/json'}
        if headers: hs.update(headers)
        conn.request(method, path, json.dumps(body) if body is not None else None, hs)
        res = conn.getresponse(); data = res.read(); conn.close()
        try: data = json.loads(data)
        except (ValueError, UnicodeDecodeError): pass
        return res.status, data

    def test_state_reports_real_missing_assets(self):
        self.start()
        status, state = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertEqual(len(state['scenes']), 5)
        self.assertEqual(len(state['characters']), 3)
        self.assertEqual(state['assets'], [])
        self.assertFalse(state['capabilities']['video'])
        self.assertIn('001.', state['script'])
        self.assertEqual(self.request('GET', '/.env')[0], 404)
        self.assertEqual(self.request('GET', '/%2e%2e/script.md')[0], 404)

    def test_document_save_is_atomic_and_backed_up(self):
        self.start()
        original = (self.root / 'script.md').read_text()
        changed = original.replace('Ai từng', 'Bạn từng')
        status, data = self.request('POST', '/api/save', {'file': 'script.md', 'content': changed})
        self.assertEqual(status, 200, data)
        self.assertEqual((self.root / 'script.md').read_text(), changed)
        backups = list((self.root / 'ui-backups').glob('*/script.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)
        self.assertEqual(self.request('GET', '/api/state')[1]['script'], changed)
        style = (self.root / 'style.md').read_text()
        self.assertEqual(self.request('POST', '/api/save', {'file': 'style.md', 'content': style + '\nTest'})[0], 200)
        self.assertEqual(self.request('POST', '/api/save', {'file': '../x', 'content': 'x'})[0], 400)
        self.assertEqual(self.request('POST', '/api/save', {'file': '.env', 'content': 'x'})[0], 400)

    def test_scene_and_script_validation_rejects_inconsistent_data(self):
        self.start()
        original = (self.root / 'scenes.csv').read_text()
        for invalid in (original.replace('001,', '999,', 1), original.replace('002,', '001,', 1), original.replace('salmon,', 'unknown,', 1), original.replace('camera,motion', 'camera,wrong'), original.replace('wide shot', '', 1), original.replace('003,', '../,', 1)):
            status, data = self.request('POST', '/api/save', {'file': 'scenes.csv', 'content': invalid})
            self.assertEqual(status, 400, data)
            self.assertEqual((self.root / 'scenes.csv').read_text(), original)
        script = (self.root / 'script.md').read_text()
        self.assertEqual(self.request('POST', '/api/save', {'file': 'script.md', 'content': script.replace('001.', '009.')})[0], 400)
        self.assertEqual(self.request('POST', '/api/save', {'file': 'script.md', 'content': script + '\n001. duplicate'})[0], 400)
        self.assertEqual(self.request('POST', '/api/save', {'file': 'scenes.csv', 'content': original.replace('wide shot', 'wide camera', 1)})[0], 200)

    def test_motion_generation_uses_existing_local_builder(self):
        self.start()
        target = self.root / 'out/motion_prompts.csv'
        target.unlink(missing_ok=True)
        status, data = self.request('POST', '/api/motion', {})
        self.assertEqual(status, 200, data)
        rows = list(csv.DictReader(io.StringIO(target.read_text())))
        self.assertEqual(len(rows), 5)
        self.assertIn('boy chews', rows[0]['prompt'])
        self.assertEqual(rows[0]['speech'], '4.50')
        rows[0]['prompt'] = 'KEEP MANUAL'; rows[0]['override'] = '1'
        with target.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        self.assertEqual(self.request('POST', '/api/motion', {})[0], 200)
        self.assertEqual(list(csv.DictReader(io.StringIO(target.read_text())))[0]['prompt'], 'KEEP MANUAL')
        self.assertTrue(list((self.root / 'ui-backups').glob('*/out/motion_prompts.csv')))

    def test_ui_serves_local_interface_and_blocks_unsafe_requests(self):
        self.start()
        for url, marker in [('/', b'lang="vi"'), ('/app.js', b'/api/save'), ('/app.css', b'@media')]:
            status, body = self.request('GET', url)
            self.assertEqual(status, 200)
            self.assertIn(marker, body)
        self.assertEqual(self.request('GET', '/favicon.ico')[0], 204)
        payload = {'file': 'style.md', 'content': 'blocked'}
        self.assertEqual(self.request('POST', '/api/save', payload, {'Origin': 'https://evil.test'})[0], 403)
        self.assertEqual(self.request('POST', '/api/save', payload, {'Host': 'evil.test'})[0], 403)
        self.assertEqual(self.request('POST', '/api/save', payload, {'Content-Length': '600000'})[0], 413)
        self.assertEqual(self.request('POST', '/api/save', payload, {'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request('POST', '/api/shell', {'cmd': 'echo nope'})[0], 404)
        (self.root / 'style.md').unlink()
        (self.root / 'style.md').symlink_to(self.root / 'script.md')
        self.assertEqual(self.request('POST', '/api/save', payload)[0], 400)
        self.assertEqual(self.request('GET', '/assets/../script.md')[0], 400)

if __name__ == '__main__': unittest.main()
