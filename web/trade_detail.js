(() => {
  const state = {
    trade: null,
    closed: false,
    candles: [],
    timeframe: '1m',
    visible: 90,
    offset: 0,
    dragging: false,
    dragX: 0,
    dragOffset: 0,
    pinchDistance: 0,
    pinchVisible: 90,
    focus: false,
  };

  const el = (id) => document.getElementById(id);
  const finite = (value) => Number.isFinite(Number(value));

  function timeLabel(ms) {
    const value = Number(ms);
    if (!Number.isFinite(value) || value <= 0) return '—';
    return new Date(value).toLocaleString();
  }

  function durationLabel(startMs, endMs = Date.now()) {
    const start = Number(startMs);
    const end = Number(endMs);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return '—';
    const total = Math.max(0, Math.round((end - start) / 1000));
    const minutes = Math.floor(total / 60);
    const seconds = total % 60;
    if (minutes < 60) return `${minutes}m ${seconds}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  }

  function install() {
    if (el('tradeDetailDialog')) return;
    const dialog = document.createElement('dialog');
    dialog.id = 'tradeDetailDialog';
    dialog.className = 'trade-detail-dialog';
    dialog.innerHTML = `
      <div class="trade-detail-shell">
        <header class="trade-detail-head">
          <button class="icon-btn" id="closeTradeDetail" aria-label="Close trade detail">←</button>
          <div><span class="eyebrow">Fast paper trade</span><h2 id="tradeDetailTitle">BTCUSDT</h2></div>
          <span class="pill neutral" id="tradeDetailState">PAPER</span>
        </header>
        <section class="trade-hero">
          <div><span>Position</span><strong id="tradeDetailSide">—</strong><small id="tradeDetailEntryTime">—</small></div>
          <div><span>Net P&amp;L</span><strong id="tradeDetailPnl">—</strong><small id="tradeDetailDuration">—</small></div>
        </section>
        <section class="trade-level-grid">
          <article><span>ENTRY</span><strong id="tradeEntryPrice">—</strong></article>
          <article><span id="tradeMarkLabel">CURRENT</span><strong id="tradeMarkPrice">—</strong></article>
          <article class="take"><span>TAKE PROFIT</span><strong id="tradeTpPrice">—</strong></article>
          <article class="stop"><span>STOP LOSS</span><strong id="tradeSlPrice">—</strong></article>
        </section>
        <section class="trade-chart-panel">
          <div class="trade-chart-toolbar">
            <label>Timeframe<select id="tradeDetailTimeframe"><option value="1m">1m</option><option value="5m">5m</option><option value="15m">15m</option></select></label>
            <div class="trade-chart-actions">
              <button type="button" class="mini-chart-btn" id="tradeZoomOut">−</button>
              <button type="button" class="mini-chart-btn" id="tradeZoomIn">＋</button>
              <button type="button" class="mini-chart-btn" id="tradeChartReset">RESET</button>
              <button type="button" class="mini-chart-btn" id="tradeChartFocus">FULL</button>
            </div>
          </div>
          <canvas id="tradeDetailChart" aria-label="Interactive trade chart"></canvas>
          <div class="trade-chart-legend">
            <span class="entry-line">ENTRY</span><span class="tp-line">TP</span><span class="sl-line">SL</span><span class="current-line">CURRENT/EXIT</span><span>EMA20</span><span>EMA50</span>
          </div>
          <p id="tradeChartHint">Pinch to zoom · drag left/right to inspect candles</p>
        </section>
        <section class="section-card trade-facts">
          <div class="section-head"><div><span class="eyebrow">Execution</span><h3>Trade facts</h3></div><span class="pill demo">PAPER</span></div>
          <div class="setting-row"><span>Margin / notional</span><strong id="tradeMarginNotional">—</strong></div>
          <div class="setting-row"><span>Effective leverage</span><strong id="tradeLeverage">—</strong></div>
          <div class="setting-row"><span>Entry score</span><strong id="tradeEntryScore">—</strong></div>
          <div class="setting-row"><span>Fees</span><strong id="tradeFees">—</strong></div>
          <div class="setting-row"><span>Gross P&amp;L</span><strong id="tradeGrossPnl">—</strong></div>
          <div class="setting-row"><span>Exit reason</span><strong id="tradeExitReason">OPEN</strong></div>
        </section>
        <section class="section-card trade-evidence">
          <div class="section-head"><div><span class="eyebrow">Strategy evidence</span><h3>Why the bot sees this direction</h3></div><span class="pill neutral" id="tradeSignalBadge">CURRENT</span></div>
          <p class="muted-copy">Entry score is preserved on the position. Indicator rows below show the latest server signal while the trade is open; future releases can persist a full entry-time indicator snapshot.</p>
          <div id="tradeEvidenceList" class="evidence-list"></div>
        </section>
        <button type="button" class="danger-btn full" id="tradeDetailClosePosition">CLOSE FAST PAPER POSITION</button>
      </div>`;
    document.body.appendChild(dialog);

    el('closeTradeDetail').addEventListener('click', () => dialog.close());
    el('tradeDetailTimeframe').addEventListener('change', async (event) => {
      state.timeframe = event.target.value;
      state.offset = 0;
      await loadCandles();
    });
    el('tradeZoomIn').addEventListener('click', () => setVisible(state.visible * 0.75));
    el('tradeZoomOut').addEventListener('click', () => setVisible(state.visible * 1.3));
    el('tradeChartReset').addEventListener('click', () => {
      state.visible = 90;
      state.offset = 0;
      renderChart();
    });
    el('tradeChartFocus').addEventListener('click', () => {
      state.focus = !state.focus;
      dialog.classList.toggle('chart-focus', state.focus);
      el('tradeChartFocus').textContent = state.focus ? 'DETAIL' : 'FULL';
      window.setTimeout(renderChart, 30);
    });
    el('tradeDetailClosePosition').addEventListener('click', async () => {
      if (!state.closed && momentumState?.openPosition) {
        await ebaRunnerCommand('/api/runner/close', { target: 'fast' });
        dialog.close();
      }
    });

    attachChartGestures(el('tradeDetailChart'));
  }

  function setVisible(value) {
    state.visible = Math.max(20, Math.min(240, Math.round(value)));
    const maxOffset = Math.max(0, state.candles.length - state.visible);
    state.offset = Math.max(0, Math.min(state.offset, maxOffset));
    renderChart();
  }

  function touchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.hypot(dx, dy);
  }

  function attachChartGestures(canvas) {
    canvas.addEventListener('touchstart', (event) => {
      if (event.touches.length === 2) {
        state.pinchDistance = touchDistance(event.touches);
        state.pinchVisible = state.visible;
        state.dragging = false;
      } else if (event.touches.length === 1) {
        state.dragging = true;
        state.dragX = event.touches[0].clientX;
        state.dragOffset = state.offset;
      }
    }, { passive: true });

    canvas.addEventListener('touchmove', (event) => {
      if (event.touches.length === 2 && state.pinchDistance > 0) {
        event.preventDefault();
        const distance = touchDistance(event.touches);
        if (distance > 0) setVisible(state.pinchVisible * (state.pinchDistance / distance));
      } else if (event.touches.length === 1 && state.dragging) {
        event.preventDefault();
        const width = Math.max(1, canvas.getBoundingClientRect().width);
        const dx = event.touches[0].clientX - state.dragX;
        const candleShift = Math.round((-dx / width) * state.visible);
        const maxOffset = Math.max(0, state.candles.length - state.visible);
        state.offset = Math.max(0, Math.min(maxOffset, state.dragOffset + candleShift));
        renderChart();
      }
    }, { passive: false });
    canvas.addEventListener('touchend', () => {
      state.dragging = false;
      state.pinchDistance = 0;
    });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      setVisible(state.visible * (event.deltaY > 0 ? 1.15 : 0.85));
    }, { passive: false });
  }

  function tradeFromOpen(position) {
    return {
      ...position,
      closed: false,
      exit_price: null,
      exit_time_ms: null,
      net_pnl_usd: Number(position.unrealized_net_usd || 0),
      gross_pnl_usd: Number(position.unrealized_gross_usd || 0),
    };
  }

  function openCurrentTradeDetail() {
    if (!momentumState?.openPosition) return;
    openTradeDetail(tradeFromOpen(momentumState.openPosition), false);
  }

  function openHistoryTradeDetail(trade) {
    if (!trade) return;
    openTradeDetail({ ...trade, closed: true }, true);
  }

  async function openTradeDetail(trade, closed) {
    install();
    state.trade = trade;
    state.closed = Boolean(closed);
    state.offset = 0;
    state.visible = 90;
    state.timeframe = '1m';
    el('tradeDetailTimeframe').value = '1m';
    renderDetail();
    el('tradeDetailDialog').showModal();
    await loadCandles();
  }

  function renderDetail() {
    const trade = state.trade;
    if (!trade) return;
    const side = String(trade.side || '').toUpperCase();
    const closed = state.closed;
    const mark = closed ? trade.exit_price : trade.mark_price;
    const pnl = closed ? Number(trade.net_pnl_usd || 0) : Number(trade.unrealized_net_usd || 0);
    const gross = closed ? Number(trade.gross_pnl_usd || 0) : Number(trade.unrealized_gross_usd || 0);
    const totalFees = Number(trade.entry_fee_usd || 0) + Number(trade.exit_fee_usd || 0);

    el('tradeDetailTitle').textContent = `${trade.symbol || 'BTCUSDT'} · ${closed ? 'CLOSED' : 'OPEN'}`;
    el('tradeDetailState').textContent = closed ? 'CLOSED' : 'OPEN PAPER';
    el('tradeDetailState').className = closed ? 'pill neutral' : 'pill positive-pill';
    el('tradeDetailSide').textContent = `${side} ${Number(trade.effective_leverage || 0).toFixed(1)}x`;
    el('tradeDetailSide').className = side === 'SHORT' ? 'negative' : 'positive-text';
    el('tradeDetailEntryTime').textContent = `Entered ${timeLabel(trade.entry_time_ms)}`;
    el('tradeDetailPnl').textContent = formatUsd(pnl);
    el('tradeDetailPnl').className = pnl >= 0 ? 'positive-text' : 'negative';
    el('tradeDetailDuration').textContent = durationLabel(trade.entry_time_ms, closed ? trade.exit_time_ms : Date.now());
    el('tradeEntryPrice').textContent = formatPrice(trade.entry_price);
    el('tradeMarkLabel').textContent = closed ? 'EXIT' : 'CURRENT';
    el('tradeMarkPrice').textContent = formatPrice(mark);
    el('tradeTpPrice').textContent = finite(trade.take_profit_price) ? formatPrice(trade.take_profit_price) : '—';
    el('tradeSlPrice').textContent = finite(trade.stop_price) ? formatPrice(trade.stop_price) : '—';
    el('tradeMarginNotional').textContent = `${formatUsd(trade.margin_usd)} / ${formatUsd(trade.notional_usd)}`;
    el('tradeLeverage').textContent = `${Number(trade.effective_leverage || 0).toFixed(1)}x${trade.leverage_cap ? ` · cap ${trade.leverage_cap}x` : ''}`;
    el('tradeEntryScore').textContent = `${Number(trade.score || 0)} / 8`;
    el('tradeFees').textContent = formatUsd(totalFees);
    el('tradeGrossPnl').textContent = formatUsd(gross);
    el('tradeGrossPnl').className = gross >= 0 ? 'positive-text' : 'negative';
    el('tradeExitReason').textContent = closed ? String(trade.exit_reason || 'CLOSED') : 'OPEN · monitoring TP / SL / reversal / max hold';
    el('tradeDetailClosePosition').hidden = closed;
    renderEvidence(side);
  }

  function evidenceRow(label, value, good = null) {
    const stateClass = good === true ? 'pass' : good === false ? 'fail' : 'neutral';
    const icon = good === true ? '✓' : good === false ? '×' : '•';
    return `<div class="evidence-row ${stateClass}"><span>${icon} ${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
  }

  function renderEvidence(side) {
    const signal = momentumState?.signal || {};
    const long = side === 'LONG';
    const short = side === 'SHORT';
    const ema1 = finite(signal.ema20_1m) && finite(signal.ema50_1m)
      ? (long ? Number(signal.ema20_1m) > Number(signal.ema50_1m) : Number(signal.ema20_1m) < Number(signal.ema50_1m))
      : null;
    const ema5 = finite(signal.ema20_5m) && finite(signal.ema50_5m)
      ? (long ? Number(signal.ema20_5m) > Number(signal.ema50_5m) : Number(signal.ema20_5m) < Number(signal.ema50_5m))
      : null;
    const structure = long ? signal.higherHighHigherLow : short ? signal.lowerHighLowerLow : null;
    const breakout = long ? signal.breakoutUp : short ? signal.breakoutDown : null;
    const rsi = Number(signal.rsi14);
    const rsiGood = finite(rsi) ? (long ? rsi >= 52 && rsi <= 72 : rsi >= 28 && rsi <= 48) : null;
    const adx = Number(signal.adx14);
    const adxGood = finite(adx) ? adx >= 20 : null;
    const volume = Number(signal.volumeRatio);
    const volumeGood = finite(volume) ? volume >= 1.15 : null;
    const spread = Number(signal.spreadBps);

    el('tradeSignalBadge').textContent = `${signal.decision || 'NO_TRADE'} ${Number(signal.longScore || 0)}/${Number(signal.shortScore || 0)}`;
    el('tradeEvidenceList').innerHTML = [
      evidenceRow('1m EMA20 vs EMA50', `${formatPrice(signal.ema20_1m)} / ${formatPrice(signal.ema50_1m)}`, ema1),
      evidenceRow('5m EMA20 vs EMA50', `${formatPrice(signal.ema20_5m)} / ${formatPrice(signal.ema50_5m)}`, ema5),
      evidenceRow(long ? 'Higher high / higher low' : 'Lower high / lower low', structure ? 'YES' : 'NO', Boolean(structure)),
      evidenceRow('RSI14', finite(rsi) ? rsi.toFixed(1) : '—', rsiGood),
      evidenceRow('ADX14 trend strength', finite(adx) ? adx.toFixed(1) : '—', adxGood),
      evidenceRow('Volume vs 20-bar average', finite(volume) ? `${volume.toFixed(2)}×` : '—', volumeGood),
      evidenceRow(long ? 'Upside breakout' : 'Downside breakout', breakout ? 'YES' : 'NO', Boolean(breakout)),
      evidenceRow('Fake breakout risk', signal.fakeBreakoutRisk ? 'YES' : 'NO', signal.fakeBreakoutRisk === false),
      evidenceRow('Spread', finite(spread) ? `${spread.toFixed(2)} bps` : '—', null),
    ].join('');
  }

  async function loadCandles() {
    if (!state.trade) return;
    el('tradeChartHint').textContent = 'Loading trade chart…';
    try {
      const payload = {
        provider: 'binance',
        symbol: state.trade.symbol || 'BTCUSDT',
        timeframe: state.timeframe,
        limit: 300,
      };
      if (demoSessionToken) payload.sessionToken = demoSessionToken;
      const result = await postJson('/api/chart', payload);
      state.candles = Array.isArray(result.candles) ? result.candles : [];
      state.offset = 0;
      el('tradeChartHint').textContent = `${state.candles.length} candles · pinch zoom · drag to pan`;
      renderChart();
    } catch (error) {
      state.candles = [];
      el('tradeChartHint').textContent = error.message || 'Trade chart unavailable';
      renderChart();
    }
  }

  function emaSeries(values, period) {
    if (values.length < period) return [];
    const output = Array(values.length).fill(null);
    let ema = values.slice(0, period).reduce((sum, value) => sum + value, 0) / period;
    output[period - 1] = ema;
    const alpha = 2 / (period + 1);
    for (let index = period; index < values.length; index += 1) {
      ema = alpha * values[index] + (1 - alpha) * ema;
      output[index] = ema;
    }
    return output;
  }

  function drawLevel(ctx, y, width, left, right, label, color, dash = []) {
    ctx.save();
    ctx.setLineDash(dash);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(width - right, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = color;
    ctx.font = 'bold 10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(label, left + 5, Math.max(12, y - 5));
    ctx.restore();
  }

  function renderChart() {
    const canvas = el('tradeDetailChart');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    const width = Math.max(320, Math.floor(rect.width));
    const height = Math.max(360, Math.floor(rect.height || 520));
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = '#080d12';
    ctx.fillRect(0, 0, width, height);

    if (!state.candles.length) {
      ctx.fillStyle = '#8c99a7';
      ctx.textAlign = 'center';
      ctx.font = '13px system-ui, sans-serif';
      ctx.fillText('Waiting for trade candles…', width / 2, height / 2);
      return;
    }

    const count = Math.min(state.visible, state.candles.length);
    const maxOffset = Math.max(0, state.candles.length - count);
    state.offset = Math.max(0, Math.min(state.offset, maxOffset));
    const end = state.candles.length - state.offset;
    const start = Math.max(0, end - count);
    const data = state.candles.slice(start, end);
    const trade = state.trade || {};
    const levels = [trade.entry_price, trade.take_profit_price, trade.stop_price, state.closed ? trade.exit_price : trade.mark_price].filter(finite).map(Number);
    let minPrice = Math.min(...data.map((item) => Number(item.low)), ...levels);
    let maxPrice = Math.max(...data.map((item) => Number(item.high)), ...levels);
    const span = Math.max(maxPrice - minPrice, Math.abs(maxPrice) * 0.0004, 1);
    minPrice -= span * 0.06;
    maxPrice += span * 0.06;

    const padding = { left: 8, right: 70, top: 12, bottom: 28 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const yFor = (price) => padding.top + ((maxPrice - Number(price)) / (maxPrice - minPrice)) * plotHeight;
    const step = plotWidth / data.length;
    const candleWidth = Math.max(2, Math.min(10, step * 0.62));

    ctx.font = '10px system-ui, sans-serif';
    for (let index = 0; index <= 5; index += 1) {
      const y = padding.top + (plotHeight * index) / 5;
      const price = maxPrice - ((maxPrice - minPrice) * index) / 5;
      ctx.strokeStyle = 'rgba(140,153,167,.13)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillStyle = '#7f8b98';
      ctx.textAlign = 'left';
      ctx.fillText(Number(price).toLocaleString('en-US', { maximumFractionDigits: 2 }), width - padding.right + 6, y + 3);
    }

    data.forEach((candle, index) => {
      const x = padding.left + step * index + step / 2;
      const open = Number(candle.open);
      const high = Number(candle.high);
      const low = Number(candle.low);
      const close = Number(candle.close);
      const color = close >= open ? '#64df58' : '#ff5e5e';
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x, yFor(high));
      ctx.lineTo(x, yFor(low));
      ctx.stroke();
      const top = Math.min(yFor(open), yFor(close));
      const bodyHeight = Math.max(1, Math.abs(yFor(close) - yFor(open)));
      ctx.fillRect(x - candleWidth / 2, top, candleWidth, bodyHeight);
    });

    const closes = state.candles.map((item) => Number(item.close));
    const ema20 = emaSeries(closes, 20).slice(start, end);
    const ema50 = emaSeries(closes, 50).slice(start, end);
    [[ema20, '#5ea1ff'], [ema50, '#f6c85f']].forEach(([series, color]) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      let moved = false;
      series.forEach((value, index) => {
        if (!finite(value)) return;
        const x = padding.left + step * index + step / 2;
        const y = yFor(value);
        if (!moved) {
          ctx.moveTo(x, y);
          moved = true;
        } else ctx.lineTo(x, y);
      });
      if (moved) ctx.stroke();
    });

    if (finite(trade.entry_price)) drawLevel(ctx, yFor(trade.entry_price), width, padding.left, padding.right, `ENTRY ${formatPrice(trade.entry_price)}`, '#7fdc8a', [6, 4]);
    if (finite(trade.take_profit_price)) drawLevel(ctx, yFor(trade.take_profit_price), width, padding.left, padding.right, `TP ${formatPrice(trade.take_profit_price)}`, '#52d273', [3, 3]);
    if (finite(trade.stop_price)) drawLevel(ctx, yFor(trade.stop_price), width, padding.left, padding.right, `SL ${formatPrice(trade.stop_price)}`, '#ff6565', [3, 3]);
    const current = state.closed ? trade.exit_price : trade.mark_price;
    if (finite(current)) drawLevel(ctx, yFor(current), width, padding.left, padding.right, `${state.closed ? 'EXIT' : 'CURRENT'} ${formatPrice(current)}`, '#62a4ff');

    const firstTime = Number(data[0]?.time || 0);
    const lastTime = Number(data[data.length - 1]?.time || 0);
    ctx.fillStyle = '#7f8b98';
    ctx.font = '10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    if (firstTime) ctx.fillText(new Date(firstTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), padding.left, height - 8);
    ctx.textAlign = 'right';
    if (lastTime) ctx.fillText(new Date(lastTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), width - padding.right, height - 8);
  }

  function fastPositionMarkup(position) {
    const pnl = Number(position.unrealized_net_usd || 0);
    return `<div class="position-row fast-position-row" data-open-fast-detail="1"><div><strong>FAST PAPER · BTCUSDT ${escapeHtml(position.side)} ${Number(position.effective_leverage || 0).toFixed(1)}x</strong><small>Entry ${escapeHtml(formatPrice(position.entry_price))} · Current ${escapeHtml(formatPrice(position.mark_price))} · TP ${escapeHtml(formatPrice(position.take_profit_price))} · SL ${escapeHtml(formatPrice(position.stop_price))}</small></div><span class="pnl ${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</span></div>`;
  }

  function renderAllPortfolioPositions() {
    const mt5Positions = Array.isArray(mt5Snapshot?.positions) ? mt5Snapshot.positions : [];
    const rows = [];
    if (paperState?.openPosition) rows.push(paperPositionMarkup(paperState.openPosition));
    if (momentumState?.openPosition) rows.push(fastPositionMarkup(momentumState.openPosition));
    rows.push(...mt5Positions.map(mt5PositionMarkup));

    const openCount = (paperState?.openPosition ? 1 : 0) + (momentumState?.openPosition ? 1 : 0) + mt5Positions.length;
    el('openPositionCount').textContent = String(openCount);
    let pnl = Number(paperState?.unrealizedPnlUsd || 0) + Number(momentumState?.unrealizedPnlUsd || 0);
    if (mt5Snapshot?.account?.currency === 'USD') pnl += mt5Positions.reduce((sum, item) => sum + Number(item.profit || 0), 0);
    el('unrealizedValue').textContent = openCount ? formatUsd(pnl) : '—';
    el('unrealizedValue').className = pnl >= 0 ? 'positive-text' : 'negative';
    el('positionsList').innerHTML = rows.length
      ? `<div class="mini-list">${rows.join('')}</div>`
      : '<article class="empty-state"><div class="empty-icon">◎</div><h3>No open positions</h3><p>Fast Momentum, Cash & Carry and MT5 positions will appear here.</p></article>';
    el('positionsList').querySelector('[data-open-fast-detail]')?.addEventListener('click', openCurrentTradeDetail);
  }

  function decorateMomentumCard() {
    const card = el('momentumCard');
    if (!card) return;
    let banner = el('momentumOpenBanner');
    if (!banner) {
      banner = document.createElement('button');
      banner.type = 'button';
      banner.id = 'momentumOpenBanner';
      banner.className = 'momentum-open-banner';
      const edge = card.querySelector('.edge-score');
      card.insertBefore(banner, edge || card.firstChild);
      banner.addEventListener('click', openCurrentTradeDetail);
      const signalLabel = card.querySelector('.edge-score span');
      if (signalLabel) signalLabel.textContent = 'NEW ENTRY SIGNAL';
    }
    const position = momentumState?.openPosition;
    if (position) {
      const pnl = Number(position.unrealized_net_usd || 0);
      banner.hidden = false;
      banner.innerHTML = `<span>OPEN POSITION</span><strong>${escapeHtml(position.side)} ${Number(position.effective_leverage || 0).toFixed(1)}x</strong><small>Entry ${escapeHtml(formatPrice(position.entry_price))} · Current ${escapeHtml(formatPrice(position.mark_price))} · ${escapeHtml(formatUsd(pnl))}</small>`;
    } else {
      banner.hidden = true;
    }
  }

  function decorateHistory() {
    const cards = [...document.querySelectorAll('#momentumHistoryList .history-trade')];
    const trades = [...(momentumState?.history || [])].reverse();
    cards.forEach((card, index) => {
      card.classList.add('clickable-trade');
      card.onclick = () => openHistoryTradeDetail(trades[index]);
      if (!card.querySelector('.trade-open-hint')) {
        const hint = document.createElement('small');
        hint.className = 'trade-open-hint';
        hint.textContent = 'Tap to open trade chart & details';
        card.appendChild(hint);
      }
    });
    const total = Number(paperState?.history?.length || 0) + Number(momentumState?.history?.length || 0);
    if (el('paperTradeCount')) el('paperTradeCount').textContent = `${total} PAPER`;
  }

  function decoratePositionPanel() {
    const panel = el('momentumPositionPanel');
    if (!panel) return;
    panel.classList.toggle('clickable-trade', Boolean(momentumState?.openPosition));
    const body = el('momentumPositionBody');
    if (body && momentumState?.openPosition && !body.querySelector('.trade-open-hint')) {
      const hint = document.createElement('small');
      hint.className = 'trade-open-hint';
      hint.textContent = 'Tap this card for chart, TP/SL and indicators';
      body.appendChild(hint);
    }
    panel.onclick = (event) => {
      if (event.target.closest('button')) return;
      if (momentumState?.openPosition) openCurrentTradeDetail();
    };
  }

  function decorateChartSummary() {
    if (chartProvider?.value !== 'binance' || !momentumState?.openPosition) return;
    const position = momentumState.openPosition;
    const pnl = Number(position.unrealized_net_usd || 0);
    el('chartDecisionBadge').textContent = `OPEN ${position.side}`;
    el('chartPositionSummary').innerHTML = `<button type="button" class="trade-summary-button" id="openChartTradeDetail"><span><strong>FAST PAPER · ${escapeHtml(position.side)} ${Number(position.effective_leverage || 0).toFixed(1)}x</strong><small>Entry ${escapeHtml(formatPrice(position.entry_price))} · TP ${escapeHtml(formatPrice(position.take_profit_price))} · SL ${escapeHtml(formatPrice(position.stop_price))}</small></span><strong class="${pnl >= 0 ? 'positive-text' : 'negative'}">${escapeHtml(formatUsd(pnl))}</strong></button>`;
    el('openChartTradeDetail')?.addEventListener('click', openCurrentTradeDetail);
  }

  function syncDecorations() {
    renderAllPortfolioPositions();
    decorateMomentumCard();
    decorateHistory();
    decoratePositionPanel();
    if (el('tradeDetailDialog')?.open && state.trade && !state.closed && momentumState?.openPosition) {
      state.trade = tradeFromOpen(momentumState.openPosition);
      renderDetail();
      renderChart();
    }
  }

  install();

  if (typeof renderMomentumUi === 'function') {
    const baseRenderMomentumUi = renderMomentumUi;
    renderMomentumUi = function renderMomentumWithTradeDetail() {
      baseRenderMomentumUi();
      syncDecorations();
    };
  }

  if (typeof renderCombinedPositions === 'function') {
    renderCombinedPositions = renderAllPortfolioPositions;
  }

  if (typeof renderMt5Positions === 'function') {
    const baseRenderMt5Positions = renderMt5Positions;
    renderMt5Positions = function renderMt5AndFastPositions() {
      baseRenderMt5Positions();
      renderAllPortfolioPositions();
    };
  }

  if (typeof refreshChart === 'function') {
    const baseRefreshChart = refreshChart;
    refreshChart = async function refreshChartWithTradeDetail() {
      await baseRefreshChart();
      decorateChartSummary();
    };
  }

  window.addEventListener('resize', () => {
    if (el('tradeDetailDialog')?.open) renderChart();
  });

  syncDecorations();
})();
