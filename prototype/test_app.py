"""Run all verification tests: python -m unittest -v test_app.py"""
from contextlib import closing
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import sqlite3
import unittest
from app import init_db, make_handler, AuditRepository

GOOD = {
    'observation_date': '2026-10-20',
    'process_area': 'Rebin',
    'result': 'Meets Standard',
    'observation_note': 'Observed the expected scan sequence using fictional test data.'
}

class APITests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.db = Path(self.folder.name) / 'audits.sqlite3'
        init_db(self.db)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.db))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.folder.cleanup()

    def request(self, path='/api/audits', payload=None, mime='application/json'):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': mime} if payload is not None else {}
        request = Request(self.base + path, data=data, headers=headers)
        try:
            with urlopen(request, timeout=3) as result:
                return result.status, json.loads(result.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_01_valid_create_returns_unique_id(self):
        status, body = self.request(payload=GOOD)
        self.assertEqual(status, 201)
        self.assertEqual(body['audit']['id'], 'AUD-000001')
        self.assertEqual(body['audit']['process_area'], 'Rebin')

    def test_02_required_fields_rejected_without_insert(self):
        status, body = self.request(payload={'observation_date': '', 'process_area': '', 'result': '', 'observation_note': ''})
        self.assertEqual(status, 422)
        self.assertEqual(len(body['fields']), 4)
        self.assertEqual(self.request()[1]['audits'], [])

    def test_03_invalid_calendar_date_rejected(self):
        status, body = self.request(payload={**GOOD, 'observation_date': '2026-02-30'})
        self.assertEqual(status, 422)
        self.assertIn('observation_date', body['fields'])

    def test_04_future_date_rejected(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        status, body = self.request(payload={**GOOD, 'observation_date': future})
        self.assertEqual(status, 422)
        self.assertIn('observation_date', body['fields'])

    def test_05_unsupported_result_rejected(self):
        status, body = self.request(payload={**GOOD, 'result': 'Unknown'})
        self.assertEqual(status, 422)
        self.assertIn('result', body['fields'])

    def test_06_short_note_rejected(self):
        status, body = self.request(payload={**GOOD, 'observation_note': 'Short'})
        self.assertEqual(status, 422)
        self.assertIn('observation_note', body['fields'])

    def test_07_saved_records_persist_across_repository_instances(self):
        self.request(payload=GOOD)
        repo = AuditRepository(self.db)
        record = repo.latest()[0]
        self.assertEqual(record['observation_note'], GOOD['observation_note'])
        self.assertTrue(record['created_at'])

    def test_08_sequential_ids_and_newest_first(self):
        self.request(payload=GOOD)
        self.request(payload={**GOOD, 'process_area': 'Pick'})
        audits = self.request()[1]['audits']
        self.assertEqual([r['id'] for r in audits], ['AUD-000002', 'AUD-000001'])

    def test_09_unsupported_area_rejected(self):
        status, body = self.request(payload={**GOOD, 'process_area': 'Unknown Area'})
        self.assertEqual(status, 422)
        self.assertIn('process_area', body['fields'])

    def test_10_database_check_constraint_defends_invalid_values(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with closing(sqlite3.connect(self.db)) as db, db:
                db.execute('INSERT INTO audits (observation_date,process_area,result,observation_note,created_at) VALUES (?,?,?,?,?)',
                           ('2026-10-20', 'Bad Area', 'Meets Standard', GOOD['observation_note'], '2026-10-20T00:00:00+00:00'))

    def test_11_not_found_route_rejected(self):
        status, body = self.request(path='/api/private')
        self.assertEqual(status, 404)

    def test_12_html_payload_stored_as_plain_text_not_markup(self):
        payload = {**GOOD, 'observation_note': '<img src=x onerror=alert(1)> visible demo text'}
        status, _ = self.request(payload=payload)
        self.assertEqual(status, 201)
        # UI uses DOM textContent; the API must not insert or transform markup.
        self.assertEqual(self.request()[1]['audits'][0]['observation_note'], payload['observation_note'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
