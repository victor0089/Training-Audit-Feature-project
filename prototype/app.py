"""Training Audit Recorder: standard-library-only Assignment 2 prototype.

Run: python app.py
Do not enter actual employee data. This is an unauthenticated teaching prototype.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import re
import sqlite3
import os

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / 'data' / 'audits.sqlite3'
PROCESS_AREAS = ('Outbound Pack', 'Rebin', 'Induct', 'Pick', 'Other')
RESULTS = ('Meets Standard', 'Needs Follow-up')
STATIC_FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
}


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_date TEXT NOT NULL,
            process_area TEXT NOT NULL CHECK(process_area IN
              ('Outbound Pack','Rebin','Induct','Pick','Other')),
            result TEXT NOT NULL CHECK(result IN
              ('Meets Standard','Needs Follow-up')),
            observation_note TEXT NOT NULL CHECK(length(observation_note) BETWEEN 10 AND 500),
            created_at TEXT NOT NULL
        )''')


def validate_audit(payload: object) -> tuple[dict, dict]:
    """Return (sanitized value dict, field_errors). Never trust browser validation."""
    if not isinstance(payload, dict):
        return {}, {'form': 'Send one JSON object containing the audit fields.'}
    errors = {}
    values = {}
    for key in ('observation_date', 'process_area', 'result', 'observation_note'):
        raw = payload.get(key)
        if not isinstance(raw, str):
            errors[key] = 'This field is required.'
            continue
        values[key] = raw.strip()
        if not values[key]:
            errors[key] = 'This field is required.'

    if 'observation_date' in values and values['observation_date']:
        s = values['observation_date']
        try:
            parsed = date.fromisoformat(s)
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', s) or parsed.isoformat() != s:
                raise ValueError('Bad date')
            if parsed > date.today():
                errors['observation_date'] = 'Choose today or an earlier date.'
        except ValueError:
            errors['observation_date'] = 'Enter a valid date (YYYY-MM-DD).'
    if values.get('process_area') and values['process_area'] not in PROCESS_AREAS:
        errors['process_area'] = 'Select one of the available process areas.'
    if values.get('result') and values['result'] not in RESULTS:
        errors['result'] = 'Select one of the available results.'
    if values.get('observation_note'):
        length = len(values['observation_note'])
        if not 10 <= length <= 500:
            errors['observation_note'] = 'Enter 10 to 500 characters.'
    return values, errors


class AuditRepository:
    """SQLite persistence layer. One connection per operation for thread safety."""
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def create(self, values: dict) -> dict:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with closing(sqlite3.connect(self.db_path, timeout=5)) as db, db:
            cursor = db.execute('''INSERT INTO audits
              (observation_date, process_area, result, observation_note, created_at)
              VALUES (?, ?, ?, ?, ?)''',
              (values['observation_date'], values['process_area'],
               values['result'], values['observation_note'], now))
            numeric_id = cursor.lastrowid
        return {'id': f'AUD-{numeric_id:06d}', **values, 'created_at': now}

    def latest(self, limit: int = 20) -> list[dict]:
        with closing(sqlite3.connect(self.db_path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            rows = db.execute('''SELECT id, observation_date, process_area, result,
                               observation_note, created_at
                               FROM audits ORDER BY id DESC LIMIT ?''', (limit,)).fetchall()
        return [{'id': f"AUD-{r['id']:06d}", 'observation_date': r['observation_date'],
                 'process_area': r['process_area'], 'result': r['result'],
                 'observation_note': r['observation_note'], 'created_at': r['created_at']}
                for r in rows]


class AuditService:
    """Application layer: enforce validation before writing to the repository."""
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def record(self, payload: object) -> tuple[dict | None, dict]:
        values, errors = validate_audit(payload)
        if errors:
            return None, errors
        return self.repository.create(values), {}

    def recent(self) -> list[dict]:
        return self.repository.latest()


def make_handler(db_path: Path):
    service = AuditService(AuditRepository(db_path))

    class Handler(BaseHTTPRequestHandler):
        server_version = 'AuditRecorder/1.0'

        def _headers(self, status: int, mime: str, length: int):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(length))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()

        def _json(self, status: int, obj: dict | list):
            raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self._headers(status, 'application/json; charset=utf-8', len(raw))
            self.wfile.write(raw)

        def do_GET(self):
            route = self.path.split('?', 1)[0]
            if route == '/api/audits':
                return self._json(200, {'audits': service.recent()})
            if route not in STATIC_FILES:
                return self._json(404, {'error': 'Page not found.'})
            filename, mimetype = STATIC_FILES[route]
            content = (ROOT / filename).read_bytes()
            self._headers(200, mimetype, len(content))
            self.wfile.write(content)

        def do_POST(self):
            if self.path != '/api/audits':
                return self._json(404, {'error': 'Endpoint not found.'})
            if not self.headers.get('Content-Type', '').lower().startswith('application/json'):
                return self._json(415, {'error': 'Send application/json.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                return self._json(400, {'error': 'Invalid request size.'})
            if size <= 0 or size > 8192:
                return self._json(413, {'error': 'Request must be 1–8192 bytes.'})
            try:
                payload = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeDecodeError):
                return self._json(400, {'error': 'Invalid JSON request.'})
            record, errors = service.record(payload)
            if errors:
                return self._json(422, {'error': 'Please correct the highlighted fields.', 'fields': errors})
            return self._json(201, {'message': 'Audit saved.', 'audit': record})

        def log_message(self, format, *args):
            # Quiet console during automated verification.
            pass

    return Handler


def main():
    port = int(os.environ.get('PORT', '8000'))
    db_path = Path(os.environ.get('AUDIT_DB', str(DEFAULT_DB)))
    init_db(db_path)
    httpd = ThreadingHTTPServer(('127.0.0.1', port), make_handler(db_path))
    print(f'Training Audit Recorder: http://127.0.0.1:{port}', flush=True)
    print('Prototype only: fictional data; no authentication.', flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    main()
