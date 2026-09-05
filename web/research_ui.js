(() => {
  const byId = (id) => document.getElementById(id);

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = String(value ?? '—');
  }

  function shortSha(value) {
    const text = typeof value === 'string' ? value.trim() : '';
    return text ? text.slice(0, 12) : 'NOT PINNED';
  }

  function renderStatusChips(id, values) {
    const container = byId(id);
    if (!container) return;
    container.replaceChildren();
    const entries = Object.entries(values || {});
    if (!entries.length) {
      const chip = document.createElement('span');
      chip.className = 'research-status-chip';
      chip.textContent = 'No persisted runs on this runtime';
      container.appendChild(chip);
      return;
    }
    entries.forEach(([name, count]) => {
      const chip = document.createElement('span');
      chip.className = 'research-status-chip';
      chip.textContent = `${String(name).toUpperCase()} ${Number(count) || 0}`;
      container.appendChild(chip);
    });
  }

  function ensureProductionProofCard() {
    if (byId('productionProofCard')) return;
    const updated = byId('researchUpdated');
    if (!updated?.parentElement) return;
    const card = document.createElement('article');
    card.className = 'section-card';
    card.id = 'productionProofCard';
    card.innerHTML = `
      <div class="section-head">
        <div><span class="eyebrow">Production proof</span><h3>Linode runtime verification</h3></div>
        <span class="pill neutral" id="productionProofBadge">WAITING</span>
      </div>
      <div class="research-flow">
        <div class="research-flow-row"><span>Host / journald / services</span><strong id="productionLocalProof">—</strong></div>
        <div class="research-flow-row"><span>Demo no-paste reconnect</span><strong id="productionDemoProof">—</strong></div>
        <div class="research-flow-row"><span>Chart smoke</span><strong id="productionChartProof">—</strong></div>
        <div class="research-flow-row"><span>Positions API</span><strong id="productionPositionsProof">—</strong></div>
        <div class="research-flow-row"><span>Fast restart recovery</span><strong id="productionFastRestartProof">—</strong></div>
        <div class="research-flow-row"><span>Last collected</span><strong id="productionProofTime">—</strong></div>
      </div>`;
    updated.parentElement.insertBefore(card, updated);
  }

  function ensureNextD0Card() {
    if (byId('nextD0Card')) return;
    const updated = byId('researchUpdated');
    if (!updated?.parentElement) return;
    const card = document.createElement('article');
    card.className = 'section-card research-d0-card';
    card.id = 'nextD0Card';
    card.innerHTML = `
      <div class="section-head">
        <div><span class="eyebrow">Strategy Factory v2 · D0 data</span><h3>Frozen discovery corpus</h3></div>
        <span class="pill neutral" id="nextD0Badge">CHECKING</span>
      </div>
      <div class="research-d0-progress" aria-label="Next D0 dataset progress">
        <div class="research-d0-progress-head"><strong id="nextD0ProgressText">0 / 10</strong><span id="nextD0ProgressPercent">0%</span></div>
        <div class="research-d0-track"><span id="nextD0ProgressBar"></span></div>
      </div>
      <div class="research-flow">
        <div class="research-flow-row"><span>Service</span><strong id="nextD0Service">—</strong></div>
        <div class="research-flow-row"><span>Phase</span><strong id="nextD0Phase">—</strong></div>
        <div class="research-flow-row"><span>Next window</span><strong id="nextD0NextWindow">—</strong></div>
        <div class="research-flow-row"><span>Builder contract</span><strong id="nextD0SourceSha">NOT PINNED</strong></div>
        <div class="research-flow-row"><span>Performance evaluation</span><strong id="nextD0EvaluationLock">LOCKED</strong></div>
        <div class="research-flow-row"><span>Fresh confirmation</span><strong id="nextD0Confirmation">NO · DISCOVERY ONLY</strong></div>
      </div>
      <p class="research-d0-note" id="nextD0Note">Dataset materialization only. A completed D0 dataset is not a verified profitable strategy.</p>`;
    const proofCard = byId('productionProofCard');
    updated.parentElement.insertBefore(card, proofCard || updated);
  }

  function proofText(passed, available = true) {
    if (!available) return 'WAITING';
    return passed ? 'PASS' : 'NOT YET';
  }

  function renderProductionProof(proof) {
    ensureProductionProofCard();
    const available = proof?.available === true;
    const localPassed = proof?.localContractPassed === true;
    const smokePassed = proof?.productionSmokePassed === true;
    const demoPassed = proof?.demoReconnect?.passed === true;
    const chartPassed = proof?.chart?.passed === true;
    const positionsPassed = proof?.localApi?.positions === true;
    const fastRestart = proof?.fastRestart || {};

    setText('productionProofBadge', proofText(smokePassed, available));
    setText('productionLocalProof', proofText(localPassed, available));
    setText('productionDemoProof', proofText(demoPassed, available));
    setText('productionChartProof', proofText(chartPassed, available));
    setText('productionPositionsProof', proofText(positionsPassed, available));
    setText(
      'productionFastRestartProof',
      fastRestart.passed === true ? 'PASS' : (fastRestart.phase || 'WAITING_FOR_OPEN'),
    );
    setText('productionProofTime', available ? (proof.collectedAt || '—') : 'Waiting for Linode collector');

    const badge = byId('productionProofBadge');
    if (badge) {
      badge.className = smokePassed ? 'pill positive-pill' : 'pill neutral';
    }
  }

  function nextD0ServiceText(serviceState) {
    if (!serviceState || serviceState.available !== true) return 'UNAVAILABLE';
    const active = String(serviceState.activeState || '').toLowerCase();
    const sub = String(serviceState.subState || '').toLowerCase();
    if (active === 'failed') return `FAILED · EXIT ${serviceState.execMainStatus ?? '—'}`;
    if (active === 'activating') return 'MATERIALIZING';
    if (active === 'active') return sub ? `ACTIVE · ${sub.toUpperCase()}` : 'ACTIVE';
    if (active === 'inactive' && serviceState.result === 'success') return 'IDLE · LAST RUN OK';
    return active ? active.toUpperCase() : 'UNKNOWN';
  }

  function renderNextD0(nextD0) {
    ensureNextD0Card();
    const available = nextD0?.available === true;
    const expectedRaw = Number(nextD0?.expectedWindowCount);
    const expected = Number.isFinite(expectedRaw) && expectedRaw > 0 ? expectedRaw : 10;
    const completedRaw = Number(nextD0?.completedWindowCount);
    const completed = Number.isFinite(completedRaw)
      ? Math.max(0, Math.min(expected, completedRaw))
      : 0;
    const percent = Math.round((completed / expected) * 100);
    const service = nextD0?.serviceState || {};
    const activeState = String(service.activeState || '').toLowerCase();
    const failed = service.available === true && activeState === 'failed';
    const complete = available && nextD0.phase === 'COMPLETE' && completed === expected;
    const running = service.available === true && ['activating', 'active'].includes(activeState);

    let badgeText = 'WAITING';
    let badgeClass = 'pill neutral';
    if (failed) {
      badgeText = 'SERVICE FAILED';
      badgeClass = 'pill negative-pill';
    } else if (complete) {
      badgeText = 'DATA READY';
      badgeClass = 'pill positive-pill';
    } else if (running || (available && nextD0.phase === 'IN_PROGRESS')) {
      badgeText = 'MATERIALIZING';
      badgeClass = 'pill demo';
    }

    setText('nextD0Badge', badgeText);
    setText('nextD0ProgressText', `${completed} / ${expected}`);
    setText('nextD0ProgressPercent', `${percent}%`);
    setText('nextD0Service', nextD0ServiceText(service));
    setText('nextD0Phase', available ? (nextD0.phase || 'IN_PROGRESS') : (nextD0.reason || 'WAITING FOR FIRST RECEIPT'));
    setText('nextD0NextWindow', nextD0?.nextWindowName || (complete ? 'NONE · CORPUS COMPLETE' : 'WAITING FOR RECEIPT'));
    setText('nextD0SourceSha', shortSha(nextD0?.sourceCodeSha));
    setText('nextD0EvaluationLock', nextD0?.performanceEvaluationAllowed === true ? 'UNEXPECTEDLY OPEN' : 'LOCKED');
    setText('nextD0Confirmation', nextD0?.freshConfirmationEvidence === true ? 'UNEXPECTEDLY TRUE' : 'NO · DISCOVERY ONLY');
    setText(
      'nextD0Note',
      complete
        ? '10/10 data receipts complete. This is still D0 discovery data, not verified profitability; evaluator authority is a separate gate.'
        : failed
          ? 'Local materialization failed. Performance evaluation stays locked until the operational failure is repaired and all 10 receipts are validated.'
          : 'Dataset materialization only. Performance evaluation stays locked until all 10 receipts and the immutable corpus receipt are complete.',
    );

    const badge = byId('nextD0Badge');
    if (badge) badge.className = badgeClass;
    const bar = byId('nextD0ProgressBar');
    if (bar) bar.style.width = `${percent}%`;

    const evaluation = byId('nextD0EvaluationLock');
    if (evaluation) {
      evaluation.className = nextD0?.performanceEvaluationAllowed === true ? 'negative' : 'research-lock-value';
    }
  }

  function render(payload) {
    const progress = payload.progress || {};
    const store = payload.researchStore || {};
    const dataPlane = payload.dataPlane || {};
    const ablation = payload.ablation || {};
    const locks = payload.locks || {};

    setText('researchMilestone', payload.milestone || 'M5');
    setText('researchStage', payload.stage || 'M5 IN PROGRESS');
    setText('researchFocus', payload.focus || 'Waiting for continuity state');
    setText('researchBuild', `Build ${payload.buildSha || 'unknown'} · ${payload.runtime || 'runtime unknown'}`);
    setText('researchDoneCount', progress.completed ?? 0);
    setText('researchTodoCount', progress.remaining ?? 0);
    setText('researchStrategyCount', store.strategies ?? 0);
    setText('researchExperimentCount', store.experiments ?? 0);
    setText('researchDbState', store.available ? 'CONNECTED' : 'NO LOCAL DB');
    setText('researchVenue', dataPlane.venue || '—');
    setText('researchSymbol', dataPlane.symbol || '—');
    setText('researchFootprint', dataPlane.footprintIntegrity || '—');
    setText('researchAlignment', dataPlane.causalAlignment || '—');
    setText('researchFeatureDataset', dataPlane.featureDataset || '—');
    setText('researchAblationStatus', ablation.status || '—');
    setText('researchBaselineAdapter', ablation.baselineAdapter || '—');
    setText('researchOrderflowAdapter', ablation.orderflowAdapter || '—');
    setText('researchFeatures', Array.isArray(ablation.features) ? ablation.features.join(' + ') : '—');
    setText('researchExecutionAssumptions', ablation.executionAssumptions || '—');
    setText('researchOosLock', locks.frozenOos ? 'LOCKED' : 'UNLOCKED');
    setText('researchLiveLock', locks.realExecution ? 'LOCKED' : 'UNLOCKED');
    setText('researchRankAuthority', locks.rankingHasLifecycleAuthority ? 'ENABLED' : 'NO AUTHORITY');
    setText('researchStoreDetail', store.available
      ? `${store.versions || 0} versions · ${store.experiments || 0} experiments`
      : 'Research DB is optional on the web runtime; repo continuity still reports the active research frontier.');
    renderStatusChips('researchExperimentStatuses', store.experimentStatus);
    renderStatusChips('researchLifecycleStatuses', store.lifecycleStatus);
    renderProductionProof(payload.productionProof || {});
    renderNextD0(payload.strategyFactoryV2NextD0 || {});
    setText('researchUpdated', `Status loaded · ${new Date().toLocaleTimeString()}`);
  }

  async function refresh() {
    const button = byId('researchRefresh');
    if (button) button.disabled = true;
    setText('researchUpdated', 'Refreshing research state…');
    try {
      const response = await fetch('/api/research/status', { cache: 'no-store' });
      const payload = await response.json();
      if (!response.ok || payload.ok !== true) {
        throw new Error(payload.message || `Research status failed (${response.status})`);
      }
      render(payload);
    } catch (error) {
      setText('researchUpdated', error.message || 'Research status unavailable');
      setText('researchDbState', 'UNAVAILABLE');
    } finally {
      if (button) button.disabled = false;
    }
  }

  byId('researchRefresh')?.addEventListener('click', refresh);
  document.querySelector('[data-nav="research"]')?.addEventListener('click', refresh);
  byId('refreshApp')?.addEventListener('click', () => {
    const screen = document.querySelector('[data-screen="research"]');
    if (screen?.classList.contains('active')) refresh();
  });
  window.EBAResearch = { refresh };

  for (const src of ['./scanner_heartbeat.js', './credential_ui.js']) {
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    document.head.appendChild(script);
  }

  window.setInterval(() => {
    const screen = document.querySelector('[data-screen="research"]');
    if (screen?.classList.contains('active')) refresh();
  }, 15_000);
})();
