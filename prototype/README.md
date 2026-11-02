# Training Audit Recorder — Assignment 2

**Selected feature:** FR-01 / US-01 from Assignment 1: "As a trainer, I want to record a training audit, so that I can preserve a clear, consistent observation."

This is an offline, local web prototype using **Python 3.9+ standard library, HTML, CSS, JavaScript, and SQLite**. No third-party packages, accounts, internet, or credentials are needed.

## Run

1. Open a terminal in the `prototype` folder.
2. Run `python app.py` (on some systems, use `python3 app.py`).
3. Open **http://127.0.0.1:8000** in a browser.
4. Enter a date, process area, result, and fictional, non-identifying note (10–500 characters). Select **Save audit**.
5. The confirmation shows a generated ID, and **Recently saved** shows the record. Refresh to confirm persistence.
6. Stop the server with **Ctrl+C**.

Saved records are created locally in `prototype/data/audits.sqlite3`. To reset demonstration data, stop the server and delete that SQLite database file. The application will recreate it on next start.

## Automated verification

In the `prototype` folder, run:

```bash
python -m unittest -v test_app.py
```

The 12 tests use temporary SQLite databases and ephemeral local HTTP ports; they do **not** modify the demo database. Test results from the completed run are provided under `evidence/test_results.txt` in the submission archive.

## File guide

- `app.py` — web server, validation, application service, SQLite repository
- `index.html` — accessible audit entry form and recent-records section
- `styles.css` — responsive presentation and validation/confirmation states
- `app.js` — form submission, error handling, safe record display
- `test_app.py` — repeatable automated V&V tests
- `../evidence/` — UML diagram, actual browser screenshot, test log
- `../report/` — APA report in Word and PDF

## Scope and limitations

Implements **one story only**: create an audit and display its saved confirmation/recent records. Does not implement coaching-action assignment (US-02), action status updates (US-03), dashboard/export (US-04–06), login, role authorization, deployment, or production data protection. Input restrictions and SQLite constraints reduce mistakes but do not replace authentication, privacy controls, or human review of notes. **Never enter real employee or confidential data.** This is for local grading/demo use only.
