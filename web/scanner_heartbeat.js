(() => {
  const byId = (id) => document.getElementById(id);
  let latestStatus = null;
  let settingsGuardInstalled = false;

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

  function formatAge(ms) {
    const value = Number(ms);
    if (!Number.isFinite(value) || value <= 0) return 'not yet';
    const seconds = Math.max(0, Math.round((Date.now() - value) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    return `${Math.round(seconds / 60)}m ago`;
  }

  function fastHealth(status) {
    const intervalSeconds = Math.max(1, Number(status?.intervalSeconds || 15));
    const lastFastMs = Number(status?.lastFastScanAtMs || 0);
    const fastAvailable = status?.fastPaperAvailable !== false;
    const fastRunning = Boolean(status?.fastRunning);
    const threadAlive = Boolean(status?.fastThreadAlive);
    const ageMs = lastFastMs > 0 ? Date.now() - lastFastMs : Number.POSITIVE_INFINITY;
    const staleAfterMs = Math.max(45_000, intervalSeconds * 3_000);
    const healthy = fastAvailable && fastRunning && threadAlive && ageMs <= staleAfterMs;
    return {
      intervalSeconds,
      lastFastMs,
      fastAvailable,
      fastRunning,
      threadAlive,
      ageMs,
      staleAfterMs,
      healthy,
    };
  }

  function renameMetric(valueId, label) {
    const value = byId(valueId);
    const card = value?.closest('.metric-card');
    const heading = card?.querySelector('span');
    if (heading) heading.textContent = label;
  }

  function install() {
    renameMetric('opportunityCount', 'Carry opportunity');
    renameMetric('expectedNetValue', 'Carry expected net');

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
    const health = fastHealth(status);
    const state = byId('scannerHeartbeatState');
    const fastState = status?.fastState || {};
    const signal = fastState.signal || {};
    const decision = signal.decision || 'NO_TRADE';

    if (state) {
      if (health.healthy) {
        state.textContent = 'LIVE';
        state.className = 'pill positive-pill';
      } else if (!health.fastRunning) {
        state.textContent = health.fastAvailable ? 'READY' : 'OFF';
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
    if (byId('scannerHeartbeatLast')) {
      byId('scannerHeartbeatLast').textContent = formatLocalTime(health.lastFastMs);
    }
    if (byId('scannerHeartbeatNext')) {
      byId('scannerHeartbeatNext').textContent = health.lastFastMs > 0
        ? formatCountdown(health.lastFastMs + health.intervalSeconds * 1000)
        : 'waiting for first scan';
    }
    if (byId('scannerHeartbeatInterval')) {
      byId('scannerHeartbeatInterval').textContent = `${health.intervalSeconds}s`;
    }

    const reason = fastState.reason || 'Server-side Fast Momentum scanner heartbeat.';
    if (byId('scannerHeartbeatDetail')) {
      const ageSeconds = Number.isFinite(health.ageMs)
        ? Math.max(0, Math.round(health.ageMs / 1000))
        : null;
      byId('scannerHeartbeatDetail').textContent = ageSeconds == null
        ? reason
        : `${reason} · last scan ${ageSeconds}s ago`;
    }
  }

  function renderSettingsHealth(status, uiError = null) {
    const health = fastHealth(status);
    const scannerStatus = byId('serverRunnerStatus');
    const scannerMode = byId('serverRunnerMode');
    const scannerScans = byId('serverRunnerScans');

    let label = 'OFFLINE';
    let className = 'negative';
    if (!health.fastAvailable) {
      label = 'OFFLINE';
    } else if (!health.fastRunning) {
      label = 'READY';
      className = 'positive-text';
    } else if (health.healthy) {
      label = 'ACTIVE';
      className = 'positive-text';
    } else {
      label = 'STALE';
    }

    if (scannerStatus) {
      scannerStatus.textContent = label;
      scannerStatus.className = className;
    }
    if (scannerMode) {
      scannerMode.textContent = health.fastRunning ? 'FAST' : health.fastAvailable ? 'FAST READY' : 'OFFLINE';
    }
    if (scannerScans) {
      const parts = [`Fast ${formatAge(health.lastFastMs)}`];
      if (health.fastRunning && !health.threadAlive) parts.push('scanner thread not alive');
      if (uiError) parts.push(`UI sync warning: ${uiError.message || String(uiError)}`);
      scannerScans.textContent = parts.join(' · ');
    }
  }

  function renderSettingsApiFailure(error) {
    const scannerStatus = byId('serverRunnerStatus');
    const scannerMode = byId('serverRunnerMode');
    const scannerScans = byId('serverRunnerScans');
    if (scannerStatus) {
      scannerStatus.textContent = 'UNREACHABLE';
      scannerStatus.className = 'negative';
    }
    if (scannerMode) scannerMode.textContent = '—';
    if (scannerScans) {
      scannerScans.textContent = `Runner API unavailable: ${error.message || String(error)}`;
    }
  }

  function installSettingsRunnerGuard() {
    if (settingsGuardInstalled) return true;
    if (
      typeof ebaFetchRunnerStatus !== 'function'
      || typeof ebaApplyRunnerStatus !== 'function'
      || typeof ebaSyncRunnerStatus !== 'function'
    ) {
      return false;
    }

    const originalApplyRunnerStatus = ebaApplyRunnerStatus;

    ebaApplyRunnerStatus = function guardedApplyRunnerStatus(status) {
      renderSettingsHealth(status);
      try {
        originalApplyRunnerStatus(status);
      } catch (error) {
        renderSettingsHealth(status, error);
        return status;
      }
      // The legacy renderer uses aggregate threadAlive. Re-assert Fast Momentum
      // health after it finishes so a disabled/retired carry scanner cannot make
      // the active Fast scanner appear offline.
      renderSettingsHealth(status);
      return status;
    };

    ebaSyncRunnerStatus = async function guardedSyncRunnerStatus() {
      let status;
      try {
        status = await ebaFetchRunnerStatus();
      } catch (error) {
        renderSettingsApiFailure(error);
        return null;
      }
      ebaApplyRunnerStatus(status);
      return status;
    };

    if (typeof ebaRunnerSyncTimer !== 'undefined' && ebaRunnerSyncTimer !== null) {
      window.clearInterval(ebaRunnerSyncTimer);
    }
    if (typeof ebaRunnerSyncTimer !== 'undefined') {
      ebaRunnerSyncTimer = window.setInterval(ebaSyncRunnerStatus, 5_000);
    }
    settingsGuardInstalled = true;
    ebaSyncRunnerStatus();
    return true;
  }

  function installSettingsGuardWhenReady(attempt = 0) {
    if (installSettingsRunnerGuard()) return;
    if (attempt >= 40) return;
    window.setTimeout(() => installSettingsGuardWhenReady(attempt + 1), 50);
  }

  async function refresh() {
    try {
      const response = await fetch('/api/runner/status', { cache: 'no-store' });
      const status = await response.json();
      if (!response.ok || status.ok !== true) {
        throw new Error(status.message || 'Runner status unavailable');
      }
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
  installSettingsGuardWhenReady();
  refresh();
  window.setInterval(() => {
    if (latestStatus) render(latestStatus);
  }, 1_000);
  window.setInterval(refresh, 5_000);
})();
