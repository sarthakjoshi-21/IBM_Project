/**
 * VoyageIntel AI — Main Application Logic
 * =========================================
 * Handles section navigation, AI chat, itinerary generation,
 * history management, template loading, and UI state orchestration.
 */

'use strict';

/* ══════════════════════════════════════════════════════════════
   STATE
   ══════════════════════════════════════════════════════════════ */
const VI = {
  activeSection: 'hero',
  currentTrip: null,
  isLoading: false,
};

/* ══════════════════════════════════════════════════════════════
   SECTION NAVIGATION
   ══════════════════════════════════════════════════════════════ */
function showSection(name) {
  const sections = ['hero', 'chat', 'planner', 'dashboard', 'history'];
  sections.forEach(s => {
    const el = document.getElementById(`${s}-section`);
    if (el) el.classList.toggle('d-none', s !== name);
  });
  VI.activeSection = name;
  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (name === 'history') loadHistory();
  if (name === 'dashboard' && VI.currentTrip) renderDashboard(VI.currentTrip);
  if (name === 'chat') populateChatChips();
}

/* ══════════════════════════════════════════════════════════════
   TEMPLATE CHIPS
   ══════════════════════════════════════════════════════════════ */
function populateChatChips() {
  const container = document.getElementById('chat-chips');
  if (!container || !window.VI_TEMPLATES) return;
  if (container.children.length > 0) return; // already populated
  window.VI_TEMPLATES.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'vi-chip';
    btn.textContent = `${t.icon} ${t.label}`;
    btn.onclick = () => {
      document.getElementById('chat-input').value = t.prompt;
      sendMessage();
    };
    container.appendChild(btn);
  });
}

function populatePlannerTemplates() {
  const container = document.getElementById('template-list');
  if (!container || !window.VI_TEMPLATES) return;
  window.VI_TEMPLATES.forEach(t => {
    const item = document.createElement('div');
    item.className = 'vi-template-item';
    item.innerHTML = `
      <span class="vi-template-icon">${t.icon}</span>
      <div>
        <div class="vi-template-label">${t.label}</div>
      </div>`;
    item.onclick = () => loadTemplate(t.id);
    container.appendChild(item);
  });
}

function loadTemplate(id) {
  const t = (window.VI_TEMPLATES || []).find(x => x.id === id);
  if (!t) return;

  // If on planner, pre-fill description fields
  if (VI.activeSection === 'planner') {
    const prefEl = document.getElementById('p-prefs');
    if (prefEl) prefEl.value = t.prompt;
    showToast(`Template loaded: ${t.label}`, 'info');
    return;
  }

  // Otherwise open chat and send the template prompt
  showSection('chat');
  setTimeout(() => {
    document.getElementById('chat-input').value = t.prompt;
    sendMessage();
  }, 200);
}

/* ══════════════════════════════════════════════════════════════
   CHAT
   ══════════════════════════════════════════════════════════════ */
function sendMessage() {
  if (VI.isLoading) return;
  const input = document.getElementById('chat-input');
  const message = (input.value || '').trim();
  if (!message) return;

  const region = document.getElementById('region-select')?.value || 'india';
  input.value = '';

  appendMessage('user', message);
  setAIStatus('busy');
  showTypingIndicator();
  VI.isLoading = true;
  toggleSendBtn(false);

  fetch('/api/chat/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, region }),
  })
  .then(r => r.json())
  .then(data => {
    removeTypingIndicator();
    if (data.error) {
      appendMessage('bot', `⚠️ **Error:** ${data.error}`);
      setAIStatus('error');
    } else {
      appendMessage('bot', data.reply);
      setAIStatus('ready');
      if (data.tokens_used) {
        document.getElementById('token-counter').textContent =
          `${data.tokens_used.toLocaleString()} tokens`;
      }
      // Extract metrics from the reply heuristically
      extractAndDisplayMetrics(data.reply);
    }
  })
  .catch(err => {
    removeTypingIndicator();
    appendMessage('bot', '⚠️ Network error. Please check your connection and try again.');
    setAIStatus('error');
    console.error('Chat error:', err);
  })
  .finally(() => {
    VI.isLoading = false;
    toggleSendBtn(true);
  });
}

function appendMessage(role, content) {
  const window_ = document.getElementById('chat-window');
  const isBot = role === 'bot';
  const msg = document.createElement('div');
  msg.className = `vi-msg ${isBot ? 'vi-msg-bot' : 'vi-msg-user'} vi-animate-in`;

  const avatar = document.createElement('div');
  avatar.className = 'vi-msg-avatar';
  avatar.innerHTML = isBot
    ? '<i class="bi bi-robot"></i>'
    : '<i class="bi bi-person-fill"></i>';

  const bubble = document.createElement('div');
  bubble.className = 'vi-msg-bubble';
  // Render Markdown if available
  if (window.marked && isBot) {
    bubble.innerHTML = window.marked.parse(content);
  } else {
    bubble.textContent = content;
  }

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  window_.appendChild(msg);
  window_.scrollTop = window_.scrollHeight;
}

function showTypingIndicator() {
  const w = document.getElementById('chat-window');
  const indicator = document.createElement('div');
  indicator.id = 'typing-indicator';
  indicator.className = 'vi-msg vi-msg-bot';
  indicator.innerHTML = `
    <div class="vi-msg-avatar"><i class="bi bi-robot"></i></div>
    <div class="vi-msg-bubble" style="padding:10px 16px;">
      <span class="vi-typing-dot"></span>
      <span class="vi-typing-dot"></span>
      <span class="vi-typing-dot"></span>
    </div>`;
  w.appendChild(indicator);
  w.scrollTop = w.scrollHeight;
}

function removeTypingIndicator() {
  document.getElementById('typing-indicator')?.remove();
}

function clearChat() {
  fetch('/api/chat/reset', { method: 'POST' })
    .then(() => {
      const w = document.getElementById('chat-window');
      // Clear and re-add welcome message
      w.innerHTML = `
        <div class="vi-msg vi-msg-bot">
          <div class="vi-msg-avatar"><i class="bi bi-robot"></i></div>
          <div class="vi-msg-bubble">
            <p class="mb-1">Conversation cleared. Ready for your next travel planning session!</p>
            <div class="vi-chip-row mt-2" id="chat-chips"></div>
          </div>
        </div>`;
      populateChatChips();
      document.getElementById('token-counter').textContent = '';
      setAIStatus('ready');
      showToast('Chat cleared.', 'success');
    });
}

function setAIStatus(state) {
  const el = document.getElementById('ai-status');
  if (!el) return;
  const map = {
    ready: { cls: 'vi-status-ready', txt: '● Ready' },
    busy:  { cls: 'vi-status-busy',  txt: '● Thinking...' },
    error: { cls: 'vi-status-error', txt: '● Error' },
  };
  const s = map[state] || map.ready;
  el.className = `vi-status-badge ${s.cls}`;
  el.textContent = s.txt;
}

function toggleSendBtn(enabled) {
  const btn = document.getElementById('send-btn');
  if (!btn) return;
  btn.disabled = !enabled;
  btn.innerHTML = enabled
    ? '<i class="bi bi-send-fill me-1"></i>Send'
    : '<i class="bi bi-hourglass-split me-1"></i>Processing...';
}

// Allow Enter (without Shift) to send
document.addEventListener('DOMContentLoaded', () => {
  const inp = document.getElementById('chat-input');
  if (inp) {
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }
  populatePlannerTemplates();
  populateChatChips();
  updateClimatePanel('india');
});

/* ══════════════════════════════════════════════════════════════
   ITINERARY GENERATION
   ══════════════════════════════════════════════════════════════ */
function generateItinerary() {
  const dest = document.getElementById('p-dest')?.value?.trim();
  if (!dest) { showToast('Please enter a destination.', 'warning'); return; }

  const params = {
    origin:            document.getElementById('p-origin')?.value?.trim() || '',
    destination:       dest,
    duration_days:     parseInt(document.getElementById('p-days')?.value) || 3,
    group_size:        parseInt(document.getElementById('p-group')?.value) || 2,
    budget_total:      document.getElementById('p-budget')?.value?.trim() || 'flexible',
    budget_currency:   document.getElementById('p-currency')?.value || '₹',
    persona:           document.getElementById('p-persona')?.value || 'balanced',
    optimisation_mode: document.getElementById('p-optmode')?.value || 'balanced',
    travel_dates:      document.getElementById('p-dates')?.value?.trim() || '',
    preferences:       document.getElementById('p-prefs')?.value?.trim() || '',
    constraints:       document.getElementById('p-constraints')?.value?.trim() || '',
    region:            document.getElementById('p-region')?.value || 'india',
  };

  showLoading('Generating your itinerary via IBM Watsonx.ai · Granite...');

  fetch('/api/itinerary/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  .then(r => r.json())
  .then(data => {
    hideLoading();
    if (data.error) {
      showToast(`Error: ${data.error}`, 'danger');
      return;
    }

    VI.currentTrip = {
      id: data.trip_id,
      params,
      itinerary: data.itinerary,
      tokens_used: data.tokens_used,
    };

    renderItinerary(data);
    updateSidebarMetrics(params, data);
    updateClimatePanel(params.region);
    showToast(`Itinerary generated! Trip ID: ${data.trip_id}`, 'success');
  })
  .catch(err => {
    hideLoading();
    showToast('Network error during generation.', 'danger');
    console.error(err);
  });
}

function renderItinerary(data) {
  const output = document.getElementById('itinerary-output');
  const content = document.getElementById('itinerary-content');
  const actions = document.getElementById('itinerary-actions');
  const metrics = document.getElementById('itin-metrics');

  if (!output) return;

  // Metric cards
  const p = VI.currentTrip?.params || {};
  const feasScore = extractFeasibilityScore(data.itinerary);
  const comfortW = extractComfortWeight(data.itinerary);

  metrics.innerHTML = `
    <div class="col-6 col-md-3">
      <div class="vi-itin-metric">
        <div class="vi-itin-metric-val vi-accent">${feasScore ?? '—'}</div>
        <div class="vi-itin-metric-lbl">Feasibility Score</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="vi-itin-metric">
        <div class="vi-itin-metric-val" style="color:var(--vi-green)">${comfortW ? comfortW + '%' : '—'}</div>
        <div class="vi-itin-metric-lbl">Avg Comfort Weight</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="vi-itin-metric">
        <div class="vi-itin-metric-val">${p.duration_days || '—'}</div>
        <div class="vi-itin-metric-lbl">Days</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="vi-itin-metric">
        <div class="vi-itin-metric-val" style="color:var(--vi-blue)">${p.group_size || '—'}</div>
        <div class="vi-itin-metric-lbl">Travellers</div>
      </div>
    </div>`;

  // Render Markdown
  if (window.marked) {
    content.innerHTML = window.marked.parse(data.itinerary);
  } else {
    content.textContent = data.itinerary;
  }

  // Actions bar
  actions.innerHTML = `
    <button class="btn btn-sm vi-btn-ghost" onclick="showSection('dashboard')">
      <i class="bi bi-speedometer2 me-1"></i>Dashboard
    </button>
    <a class="btn btn-sm vi-btn-accent" href="/api/export/${data.trip_id}/pdf" target="_blank">
      <i class="bi bi-file-pdf me-1"></i>Download PDF
    </a>`;

  output.classList.remove('d-none');
  output.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Update sidebar metrics
  updateSidebarMetricsFromScores(feasScore, comfortW, p);
}

function updateSidebarMetrics(params, data) {
  document.getElementById('stat-days').textContent  = params.duration_days || '—';
  document.getElementById('stat-group').textContent = params.group_size || '—';
}

function updateSidebarMetricsFromScores(feasScore, comfortW, params) {
  if (feasScore !== null) {
    document.getElementById('metric-feasibility').textContent = feasScore;
    document.getElementById('metric-feasibility-bar').style.width = feasScore + '%';
  }
  if (comfortW !== null) {
    document.getElementById('metric-comfort').textContent = comfortW + '%';
    document.getElementById('metric-comfort-bar').style.width = comfortW + '%';
  }
  document.getElementById('stat-days').textContent  = params.duration_days || '—';
  document.getElementById('stat-group').textContent = params.group_size || '—';
}

function extractAndDisplayMetrics(text) {
  const fs = extractFeasibilityScore(text);
  const cw = extractComfortWeight(text);
  if (fs !== null) {
    document.getElementById('metric-feasibility').textContent = fs;
    document.getElementById('metric-feasibility-bar').style.width = fs + '%';
  }
  if (cw !== null) {
    document.getElementById('metric-comfort').textContent = cw + '%';
    document.getElementById('metric-comfort-bar').style.width = cw + '%';
  }
}

function extractFeasibilityScore(text) {
  const m = text.match(/feasibility\s+score[:\s*]*(\d{1,3})/i);
  return m ? Math.min(100, parseInt(m[1])) : null;
}

function extractComfortWeight(text) {
  const m = text.match(/comfort\s+weight[:\s*]*(\d{1,3})/i);
  return m ? Math.min(100, parseInt(m[1])) : null;
}

function clearPlanner() {
  ['p-origin','p-dest','p-budget','p-dates','p-prefs','p-constraints'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const out = document.getElementById('itinerary-output');
  if (out) out.classList.add('d-none');
}

/* ══════════════════════════════════════════════════════════════
   DASHBOARD
   ══════════════════════════════════════════════════════════════ */
function renderDashboard(trip) {
  if (!trip) return;
  const p = trip.params;
  document.getElementById('dash-dest').textContent   = p.destination || '—';
  document.getElementById('dash-days').textContent   = p.duration_days || '—';
  document.getElementById('dash-budget').textContent = (p.budget_currency||'₹') + (p.budget_total||'—');
  document.getElementById('dash-group').textContent  = p.group_size || '—';

  renderTimeline(trip.itinerary, parseInt(p.duration_days) || 3);
  window.VI_Charts?.renderAll(trip);
}

function renderTimeline(itinerary, days) {
  const container = document.getElementById('timeline-container');
  if (!container) return;
  container.innerHTML = '';

  const timeline = document.createElement('div');
  timeline.className = 'vi-timeline';

  for (let d = 1; d <= days; d++) {
    const item = document.createElement('div');
    item.className = 'vi-timeline-item';
    item.innerHTML = `
      <div class="vi-timeline-dot"></div>
      <div class="vi-timeline-card">
        <div class="vi-timeline-day">Day ${d}</div>
        <div class="vi-timeline-title">Itinerary Day ${d}</div>
        <div class="vi-timeline-meta">Refer to the full itinerary for detailed activities</div>
        <div class="vi-timeline-slots">
          <span class="vi-slot-tag vi-slot-morning">☀ Morning</span>
          <span class="vi-slot-tag vi-slot-afternoon">🌤 Afternoon</span>
          <span class="vi-slot-tag vi-slot-evening">🌙 Evening</span>
        </div>
      </div>`;
    timeline.appendChild(item);
  }
  container.appendChild(timeline);
}

/* ══════════════════════════════════════════════════════════════
   HISTORY
   ══════════════════════════════════════════════════════════════ */
function loadHistory() {
  fetch('/api/history/')
    .then(r => r.json())
    .then(data => renderHistory(data.trips || []))
    .catch(() => showToast('Failed to load history.', 'warning'));
}

function renderHistory(trips) {
  const container = document.getElementById('history-container');
  const empty     = document.getElementById('history-empty');
  if (!container) return;

  // Remove old cards (keep empty placeholder)
  Array.from(container.children).forEach(c => {
    if (c.id !== 'history-empty') c.remove();
  });

  if (!trips.length) {
    empty?.classList.remove('d-none');
    return;
  }
  empty?.classList.add('d-none');

  trips.forEach(t => {
    const card = document.createElement('div');
    card.className = 'vi-history-card vi-animate-in';
    card.innerHTML = `
      <div class="vi-history-icon"><i class="bi bi-map-fill"></i></div>
      <div class="flex-grow-1">
        <div class="vi-history-dest">${t.destination || 'Unknown Destination'}</div>
        <div class="vi-history-meta">
          From: ${t.origin || '—'} · ${t.duration_days || '?'} days ·
          ${(t.persona || 'balanced').charAt(0).toUpperCase() + (t.persona||'').slice(1)} ·
          ${t.group_size || 1} traveller(s) ·
          <span class="vi-muted-sm">ID: ${t.id}</span>
        </div>
        <div class="vi-muted-sm mt-1">${formatDate(t.created_at)}</div>
      </div>
      <div class="vi-history-actions">
        <a class="btn btn-sm vi-btn-ghost" href="/api/export/${t.id}/pdf" target="_blank">
          <i class="bi bi-file-pdf me-1"></i>PDF
        </a>
        <button class="btn btn-sm vi-btn-ghost" onclick="deleteTrip('${t.id}', this.closest('.vi-history-card'))">
          <i class="bi bi-trash3"></i>
        </button>
      </div>`;
    container.appendChild(card);
  });
}

function deleteTrip(id, cardEl) {
  fetch(`/api/history/${id}`, { method: 'DELETE' })
    .then(() => {
      cardEl?.remove();
      showToast('Trip deleted.', 'success');
      // Show empty state if no cards left
      const cards = document.querySelectorAll('.vi-history-card');
      if (!cards.length) document.getElementById('history-empty')?.classList.remove('d-none');
    })
    .catch(() => showToast('Delete failed.', 'danger'));
}

function clearAllHistory() {
  if (!confirm('Delete all trip history?')) return;
  fetch('/api/history/', { method: 'DELETE' })
    .then(() => {
      loadHistory();
      showToast('History cleared.', 'success');
    })
    .catch(() => showToast('Failed to clear history.', 'danger'));
}

/* ══════════════════════════════════════════════════════════════
   CLIMATE PANEL
   ══════════════════════════════════════════════════════════════ */
const CLIMATE_DATA = {
  india: {
    season: 'Oct–Feb (Winter)',
    risk: 'Monsoon Jun–Sep',
    crowd: 'High in Dec–Jan',
    window: 'Oct–Feb ideal',
  },
  europe: {
    season: 'Apr–May, Sep–Oct (Shoulder)',
    risk: 'Winter cold Nov–Feb',
    crowd: 'Peak in Jul–Aug',
    window: 'May & Sep optimal',
  },
  asia: {
    season: 'Nov–Feb (Dry season)',
    risk: 'Typhoon Jul–Oct',
    crowd: 'Chinese NY peak',
    window: 'Dec–Feb ideal',
  },
  americas: {
    season: 'Jun–Aug (North summer)',
    risk: 'Hurricane Jun–Nov',
    crowd: 'Summer peak',
    window: 'Varies by region',
  },
};

function updateClimatePanel(region) {
  const d = CLIMATE_DATA[region] || CLIMATE_DATA.india;
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  set('clim-season', d.season);
  set('clim-risk',   d.risk);
  set('clim-crowd',  d.crowd);
  set('clim-window', d.window);
}

document.getElementById('region-select')?.addEventListener('change', function() {
  updateClimatePanel(this.value);
});

/* ══════════════════════════════════════════════════════════════
   LOADING OVERLAY
   ══════════════════════════════════════════════════════════════ */
function showLoading(msg) {
  const overlay = document.getElementById('loading-overlay');
  const msgEl   = document.getElementById('loading-msg');
  if (msgEl) msgEl.textContent = msg || 'Processing...';
  overlay?.classList.remove('d-none');
  document.getElementById('generate-btn').disabled = true;
}

function hideLoading() {
  document.getElementById('loading-overlay')?.classList.add('d-none');
  const btn = document.getElementById('generate-btn');
  if (btn) btn.disabled = false;
}

/* ══════════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
   ══════════════════════════════════════════════════════════════ */
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const colourMap = {
    success: 'var(--vi-green)',
    danger:  'var(--vi-accent)',
    warning: 'var(--vi-amber)',
    info:    'var(--vi-blue)',
  };

  const toastEl = document.createElement('div');
  toastEl.className = 'toast align-items-center border-0 show';
  toastEl.style.borderLeft = `3px solid ${colourMap[type] || colourMap.info} !important`;
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${msg}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button>
    </div>`;

  container.appendChild(toastEl);
  setTimeout(() => toastEl.remove(), 4500);
}

/* ══════════════════════════════════════════════════════════════
   UTILITIES
   ══════════════════════════════════════════════════════════════ */
function formatDate(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return isoString; }
}
