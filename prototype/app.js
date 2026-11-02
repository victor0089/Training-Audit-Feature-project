'use strict';
const form = document.querySelector('#audit-form');
const feedback = document.querySelector('#feedback');
const note = document.querySelector('#observation_note');
const count = document.querySelector('#note-count');
const save = document.querySelector('#save-button');
const list = document.querySelector('#recent-list');
const today = new Date();
const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const dateField = document.querySelector('#observation_date');
dateField.max = localToday;
dateField.value = localToday;

const errorMap = { observation_date: 'date-error', process_area: 'area-error', result: 'result-error', observation_note: 'note-error' };
function clearErrors() {
  Object.values(errorMap).forEach(id => document.getElementById(id).textContent = '');
  document.querySelectorAll('[aria-invalid="true"]').forEach(el => el.removeAttribute('aria-invalid'));
  feedback.hidden = true;
  feedback.classList.remove('error-feedback');
}
function showMessage(message, isError = false) {
  feedback.textContent = message;
  feedback.classList.toggle('error-feedback', isError);
  feedback.hidden = false;
  feedback.focus();
}
function showErrors(errors) {
  for (const [field, message] of Object.entries(errors)) {
    const errorEl = document.getElementById(errorMap[field]);
    if (errorEl) errorEl.textContent = message;
    const input = form.elements.namedItem(field);
    if (input && input instanceof HTMLElement) input.setAttribute('aria-invalid', 'true');
  }
}
function makeText(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value; // Treat stored notes as text, never executable HTML.
  return node;
}
function renderRecent(audits) {
  list.replaceChildren();
  document.querySelector('#count').textContent = String(audits.length);
  if (!audits.length) {
    const empty = makeText('div', 'empty', 'No audits yet. Complete the form to create your first audit.');
    list.appendChild(empty); return;
  }
  audits.forEach(audit => {
    const card = makeText('article', 'audit-card', '');
    const head = makeText('div', 'audit-head', '');
    head.append(makeText('span', 'audit-id', audit.id), makeText('time', 'audit-date', audit.observation_date));
    card.append(head, makeText('div', 'audit-area', audit.process_area));
    card.append(makeText('span', `status ${audit.result === 'Needs Follow-up' ? 'followup' : ''}`, audit.result));
    card.append(makeText('p', 'audit-note', audit.observation_note));
    list.appendChild(card);
  });
}
async function refreshList() {
  try {
    const response = await fetch('/api/audits', { cache: 'no-store' });
    if (!response.ok) throw new Error('Unable to fetch saved records.');
    const body = await response.json();
    renderRecent(body.audits);
  } catch (_) { list.textContent = 'Recent audits are temporarily unavailable.'; }
}

note.addEventListener('input', () => { count.textContent = `${note.value.length} / 500`; });
form.addEventListener('reset', () => {
  clearErrors();
  setTimeout(() => { dateField.value = localToday; count.textContent = '0 / 500'; }, 0);
});
form.addEventListener('submit', async (event) => {
  event.preventDefault(); clearErrors();
  const values = new FormData(form);
  const payload = {
    observation_date: String(values.get('observation_date') || ''),
    process_area: String(values.get('process_area') || ''),
    result: String(values.get('result') || ''),
    observation_note: String(values.get('observation_note') || '')
  };
  save.disabled = true; save.textContent = 'Saving…';
  try {
    const response = await fetch('/api/audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const body = await response.json();
    if (!response.ok) {
      showErrors(body.fields || {}); showMessage(body.error || 'Unable to save audit.', true); return;
    }
    form.reset();
    showMessage(`Saved ${body.audit.id}. Your observation is now in recent records.`);
    await refreshList();
  } catch (_) { showMessage('Connection problem. Check that the Python server is running.', true); }
  finally { save.disabled = false; save.innerHTML = 'Save audit <span aria-hidden="true">→</span>'; }
});
refreshList();
