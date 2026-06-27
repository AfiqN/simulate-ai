const API = '/api';
let pollTimer = null;
let startTime = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// -- Init --
document.addEventListener('DOMContentLoaded', () => {
  loadHistory();
  $('form').addEventListener('submit', submitSimulation);
});

// -- Submit --
async function submitSimulation(e) {
  e.preventDefault();
  const btn = $('button[type="submit"]');
  btn.disabled = true;

  const body = {
    stimulus: $('#stimulus').value.trim(),
    agent_count: parseInt($('#agents').value) || 5,
    provider: $('#provider').value || null,
    crisis_override: $('#crisis').value.trim() || null,
    rag_enabled: $('#rag').value === '' ? null : $('#rag').value === 'true',
  };

  if (!body.stimulus) { btn.disabled = false; return; }

  try {
    const res = await fetch(`${API}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    startPolling(data.id);
  } catch (err) {
    btn.disabled = false;
    alert(`Error: ${err.message}`);
  }
}

// -- Polling --
function startPolling(runId) {
  const status = $('#status');
  const result = $('#result');
  status.classList.add('visible');
  result.classList.remove('visible');
  startTime = Date.now();
  updateStatusLine('queued', null);

  pollTimer = setInterval(() => pollStatus(runId), 3000);
}

async function pollStatus(runId) {
  try {
    const res = await fetch(`${API}/simulate/${runId}`);
    const data = await res.json();
    const elapsed = Math.round((Date.now() - startTime) / 1000);

    if (data.status === 'completed') {
      stopPolling();
      renderResult(data);
      loadHistory();
    } else if (data.status === 'failed') {
      stopPolling();
      updateStatusLine('failed', elapsed, data.error);
      $('button[type="submit"]').disabled = false;
    } else {
      updateStatusLine(data.progress || data.status, elapsed, data.scenario_name);
    }
  } catch (err) {
    // network blip — keep polling
  }
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function updateStatusLine(status, elapsed, extra) {
  const el = $('#status .status-line');
  let text = status;
  if (elapsed != null) text += ` (${elapsed}s)`;
  if (extra) text += ` — ${extra}`;
  el.innerHTML = `<span class="dot"></span>${esc(text)}`;
}

// -- Result --
function renderResult(data) {
  $('#status').classList.remove('visible');
  const section = $('#result');
  section.classList.add('visible');
  $('button[type="submit"]').disabled = false;

  const r = data.result || {};
  const m = r.resilience_metrics || {};
  const verdictClass = `verdict-${(m.verdict || '').toLowerCase()}`;

  let html = `<div class="metrics">`;
  html += `Verdict: <span class="verdict ${verdictClass}">${esc(m.verdict || '—')}</span>\n`;
  html += `Stability: ${m.decision_stability ?? '—'} | Drift: ${fmtDrift(m.utility_drift_mean)}\n`;
  html += `Crisis: ${esc(r.crisis_event || '—')}\n`;
  html += `Time: ${data.elapsed_s ? Math.round(data.elapsed_s) + 's' : '—'}`;
  html += `</div>`;

  if (r.report_md) {
    html += `<details><summary>Full Report</summary>`;
    html += `<div class="report-body">${esc(r.report_md)}</div></details>`;
  }

  section.querySelector('.result-body').innerHTML = html;
}

function fmtDrift(v) {
  if (v == null) return '—';
  return (v >= 0 ? '+' : '') + v.toFixed(2);
}

// -- History --
async function loadHistory() {
  try {
    const res = await fetch(`${API}/runs?limit=30`);
    const data = await res.json();
    renderHistory(data.runs || []);
    $('.meta').textContent = `${data.total || 0} runs`;
  } catch { /* silent */ }
}

function renderHistory(runs) {
  const tbody = $('#history-table tbody');
  if (!runs.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No runs yet</td></tr>`;
    return;
  }
  tbody.innerHTML = runs.map(r => {
    const verdictClass = `verdict-${(r.verdict || '').toLowerCase()}`;
    return `<tr>
      <td>${esc(r.id.slice(0, 8))}</td>
      <td class="scenario">${esc(r.scenario_name || '—')}</td>
      <td><span class="verdict ${verdictClass}">${esc(r.verdict || r.status)}</span></td>
      <td>${r.elapsed_s ? Math.round(r.elapsed_s) + 's' : '—'}</td>
    </tr>`;
  }).join('');
}

// -- Util --
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
