(() => {
  const byId = (id) => document.getElementById(id);

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = String(value ?? '—');
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
      : 'Research DB is optional on the web runtime; repo continuity still reports the active M5 frontier.');
    renderStatusChips('researchExperimentStatuses', store.experimentStatus);
    renderStatusChips('researchLifecycleStatuses', store.lifecycleStatus);
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
  window.EBAResearch = { refresh };

  window.setInterval(() => {
    const screen = document.querySelector('[data-screen="research"]');
    if (screen?.classList.contains('active')) refresh();
  }, 15_000);
})();
