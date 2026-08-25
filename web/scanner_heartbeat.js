(() => {
  const byId = (id) => document.getElementById(id);
  let latestStatus = null;

  function formatLocalTime(ms) {
    const value = Number(ms);
    if (!Number.isFinite(value) || value <= 0) return '—';
    return new Date(value).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  function formatCountdown(targetMs) {
    const value = Number(targetMs);
    if (!Number.isFinite(value) || value <= 0) return '—';
    const seconds = Math.ceil((value - Date.now()) / 1000);
    if (seconds <= 0) return 'due now';
    return `in ${seconds}s`;
  }

  function install() {
    const grid = document.querySelector('[data-screen="home"] .metric-grid');
    if (!grid || byId('scannerHeartbeatCard')) return;
    const card = document.createElement('article');
    card.className = 'section-card';
    card.id = 'scannerHeartbeatCard';
    card.innerHTML = `
      <div class="section-head">
        <div><span class="eyebrow">Server scanner</span><h3>Fast Momentum heartbeat</h3></div>
        <span class="pill neutral" id="scannerHeartbeatState">CHECKING</span>
      </div>
      <div class="setting-row"><span>Decision</span><strong id="scannerHeartbeatDecision">—</strong></div>
      <div class="setting-row"><span>Last server scan</span><strong id="scannerHeartbeatLast">—</strong></div>
      <div class="setting-row"><span>Next expected scan</span><strong id="scannerHeartbeatNext">—</strong></div>
      <div class="setting-row"><span>Scan interval</span><strong id="scannerHeartbeatInterval">—</strong></div>
      <small class="muted-copy" id="scannerHeartbeatDetail">Reading Linode runner heartbeat…</small>`;
    grid.insertAdjacentElement('afterend', card);
  }

  function render(status) {
    latestStatus = status;
    const intervalSeconds = Math.max(1, Number(status?.intervalSeconds || 15));
    const lastFastMs = Number(status?.lastFastScanAtMs || 0);
    const fastRunning = Boolean(status?.fastRunning);
    const threadAlive = Boolean(status?.fastThreadAlive);
    const ageMs = lastFastMs > 0 ? Date.now() - lastFastMs : Number.POSITIVE_INFINITY;
    const staleAfterMs = Math.max(45_000, intervalSeconds * 3_000);
    const healthy = fastRunning && threadAlive && ageMs <= staleAfterMs;
    const state = byId('scannerHeartbeatState');
    const fastState = status?.fastState || {};
    const signal = fastState.signal || {};
    const decision = signal.decision || 'NO_TRADE';

    if (state) {
      if (healthy) {
        state.textContent = 'LIVE';
        state.className = 'pill positive-pill';
      } else if (!fastRunning) {
        state.textContent = 'OFF';
        state.className = 'pill neutral';
      } else {
        state.textContent = 'STALE';
        state.className = 'pill demo';
      }
    }

    if (byId('scannerHeartbeatDecision')) {
      byId('scannerHeartbeatDecision').textContent = decision;
      byId('scannerHeartbeatDecision').className = decision === 'NO_TRADE' ? 'negative' : 'positive-text';
    }
    if (byId('scannerHeartbeatLast')) byId('scannerHeartbeatLast').textContent = formatLocalTime(lastFastMs);
    if (byId('scannerHeartbeatNext')) {
      byId('scannerHeartbeatNext').textContent = lastFastMs > 0
        ? formatCountdown(lastFastMs + intervalSeconds * 1000)
        : 'waiting for first scan';
    }
    if (byId('scannerHeartbeatInterval')) byId('scannerHeartbeatInterval').textContent = `${intervalSeconds}s`;

    const reason = fastState.reason || status?.lastError || 'Server-side scanner heartbeat is healthy.';
    if (byId('scannerHeartbeatDetail')) {
      const ageSeconds = Number.isFinite(ageMs) ? Math.max(0, Math.round(ageMs / 1000)) : null;
      byId('scannerHeartbeatDetail').textContent = ageSeconds == null
        ? reason
        : `${reason} · last scan ${ageSeconds}s ago`;
    }
  }

  async function refresh() {
    try {
      const response = await fetch('/api/runner/status', { cache: 'no-store' });
      const status = await response.json();
      if (!response.ok || status.ok !== true) throw new Error(status.message || 'Runner status unavailable');
      render(status);
    } catch (error) {
      const state = byId('scannerHeartbeatState');
      if (state) {
        state.textContent = 'ERROR';
        state.className = 'pill demo';
      }
      if (byId('scannerHeartbeatDetail')) {
        byId('scannerHeartbeatDetail').textContent = error.message || 'Runner heartbeat unavailable';
      }
    }
  }

  install();
  refresh();
  window.setInterval(() => {
    if (latestStatus) render(latestStatus);
  }, 1_000);
  window.setInterval(refresh, 5_000);
})();
