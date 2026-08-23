(() => {
  const views = new WeakMap();

  function finite(value) {
    return Number.isFinite(Number(value));
  }

  function priceLabel(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '—';
    if (n >= 1000) return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
    if (n >= 10) return n.toFixed(2);
    return n.toFixed(4);
  }

  function resizeCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    const width = Math.max(320, Math.floor(rect.width));
    const height = Math.max(320, Math.floor(rect.height || 360));
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx, width, height };
  }

  function drawEmpty(ctx, width, height, text) {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#080d12';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = '#8c99a7';
    ctx.font = '13px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(text, width / 2, height / 2);
  }

  function emaSeries(data, period) {
    const output = new Array(data.length).fill(null);
    if (data.length < period) return output;
    const alpha = 2 / (period + 1);
    let value = 0;
    for (let i = 0; i < period; i += 1) value += Number(data[i].close);
    value /= period;
    output[period - 1] = value;
    for (let i = period; i < data.length; i += 1) {
      value = alpha * Number(data[i].close) + (1 - alpha) * value;
      output[i] = value;
    }
    return output;
  }

  function stateFor(canvas) {
    if (views.has(canvas)) return views.get(canvas);
    const state = {
      candles: [], markers: [], positions: [], visible: 90, offset: 0,
      dragging: false, dragX: 0, dragOffset: 0, pinchDistance: 0, pinchVisible: 90,
    };
    views.set(canvas, state);
    installInteraction(canvas, state);
    return state;
  }

  function clampView(state) {
    state.visible = Math.max(20, Math.min(Math.max(20, state.candles.length), Math.round(state.visible)));
    const maxOffset = Math.max(0, state.candles.length - state.visible);
    state.offset = Math.max(0, Math.min(maxOffset, Math.round(state.offset)));
  }

  function rerender(canvas) {
    const state = stateFor(canvas);
    draw(canvas, state);
  }

  function touchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.hypot(dx, dy);
  }

  function installToolbar(canvas, state) {
    const card = canvas.closest('.chart-card');
    if (!card || card.querySelector('.live-chart-actions')) return;
    const bar = document.createElement('div');
    bar.className = 'live-chart-actions';
    bar.innerHTML = '<span>EMA20 / EMA50</span><div><button type="button" data-live-zoom="out">−</button><button type="button" data-live-zoom="in">＋</button><button type="button" data-live-reset>RESET</button></div>';
    canvas.insertAdjacentElement('beforebegin', bar);
    bar.querySelector('[data-live-zoom="in"]').addEventListener('click', () => {
      state.visible *= 0.75; clampView(state); rerender(canvas);
    });
    bar.querySelector('[data-live-zoom="out"]').addEventListener('click', () => {
      state.visible *= 1.3; clampView(state); rerender(canvas);
    });
    bar.querySelector('[data-live-reset]').addEventListener('click', () => {
      state.visible = Math.min(90, Math.max(20, state.candles.length)); state.offset = 0; rerender(canvas);
    });
  }

  function installInteraction(canvas, state) {
    canvas.style.touchAction = 'none';
    installToolbar(canvas, state);
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
        if (distance > 0) {
          state.visible = state.pinchVisible * (state.pinchDistance / distance);
          clampView(state); rerender(canvas);
        }
      } else if (event.touches.length === 1 && state.dragging) {
        event.preventDefault();
        const width = Math.max(1, canvas.getBoundingClientRect().width);
        const dx = event.touches[0].clientX - state.dragX;
        state.offset = state.dragOffset + Math.round((-dx / width) * state.visible);
        clampView(state); rerender(canvas);
      }
    }, { passive: false });
    canvas.addEventListener('touchend', () => { state.dragging = false; state.pinchDistance = 0; });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      state.visible *= event.deltaY > 0 ? 1.15 : 0.85;
      clampView(state); rerender(canvas);
    }, { passive: false });
  }

  function drawLine(ctx, points, color) {
    let started = false;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    points.forEach((point) => {
      if (!point || !finite(point.x) || !finite(point.y)) return;
      if (!started) { ctx.moveTo(point.x, point.y); started = true; }
      else ctx.lineTo(point.x, point.y);
    });
    if (started) ctx.stroke();
  }

  function draw(canvas, state) {
    const { ctx, width, height } = resizeCanvas(canvas);
    if (!Array.isArray(state.candles) || state.candles.length < 2) {
      drawEmpty(ctx, width, height, 'Waiting for market candles…'); return;
    }
    const full = state.candles.filter((item) => finite(item.open) && finite(item.high) && finite(item.low) && finite(item.close));
    if (full.length < 2) { drawEmpty(ctx, width, height, 'Chart data unavailable'); return; }
    clampView(state);
    const end = Math.max(1, full.length - state.offset);
    const start = Math.max(0, end - state.visible);
    const data = full.slice(start, end);
    const ema20Full = emaSeries(full, 20);
    const ema50Full = emaSeries(full, 50);
    const ema20 = ema20Full.slice(start, end);
    const ema50 = ema50Full.slice(start, end);

    const padding = { left: 10, right: 66, top: 14, bottom: 28 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    let minPrice = Math.min(...data.map((item) => Number(item.low)));
    let maxPrice = Math.max(...data.map((item) => Number(item.high)));
    [...ema20, ...ema50].forEach((value) => { if (finite(value)) { minPrice = Math.min(minPrice, Number(value)); maxPrice = Math.max(maxPrice, Number(value)); } });
    state.positions.forEach((position) => { if (finite(position.priceOpen)) { minPrice = Math.min(minPrice, Number(position.priceOpen)); maxPrice = Math.max(maxPrice, Number(position.priceOpen)); } });
    state.markers.forEach((marker) => { if (finite(marker.price)) { minPrice = Math.min(minPrice, Number(marker.price)); maxPrice = Math.max(maxPrice, Number(marker.price)); } });
    const span = Math.max(maxPrice - minPrice, Math.abs(maxPrice) * 0.0005, 0.0001);
    minPrice -= span * 0.06; maxPrice += span * 0.06;
    const yFor = (price) => padding.top + ((maxPrice - Number(price)) / (maxPrice - minPrice)) * plotHeight;
    const step = plotWidth / data.length;
    const candleWidth = Math.max(2, Math.min(9, step * 0.62));
    const firstTime = Number(data[0].time || 0);
    const lastTime = Number(data[data.length - 1].time || 0);
    const timeSpan = Math.max(1, lastTime - firstTime);
    const xForTime = (timestamp) => padding.left + Math.max(0, Math.min(1, (Number(timestamp) - firstTime) / timeSpan)) * plotWidth;

    ctx.clearRect(0, 0, width, height); ctx.fillStyle = '#080d12'; ctx.fillRect(0, 0, width, height);
    ctx.lineWidth = 1; ctx.font = '10px system-ui, sans-serif'; ctx.textAlign = 'left';
    for (let i = 0; i <= 5; i += 1) {
      const y = padding.top + (plotHeight * i) / 5;
      const price = maxPrice - ((maxPrice - minPrice) * i) / 5;
      ctx.strokeStyle = 'rgba(140,153,167,.12)'; ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke();
      ctx.fillStyle = '#7f8b98'; ctx.fillText(priceLabel(price), width - padding.right + 8, y + 3);
    }
    data.forEach((candle, index) => {
      const x = padding.left + step * index + step / 2;
      const open = Number(candle.open), high = Number(candle.high), low = Number(candle.low), close = Number(candle.close);
      const color = close >= open ? '#64df58' : '#ff5e5e';
      ctx.strokeStyle = color; ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(x, yFor(high)); ctx.lineTo(x, yFor(low)); ctx.stroke();
      const bodyTop = Math.min(yFor(open), yFor(close)); const bodyHeight = Math.max(1, Math.abs(yFor(close) - yFor(open)));
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    });
    const emaPoints = (values) => values.map((value, index) => finite(value) ? ({ x: padding.left + step * index + step / 2, y: yFor(value) }) : null);
    drawLine(ctx, emaPoints(ema20), '#4c83ff');
    drawLine(ctx, emaPoints(ema50), '#f2c94c');

    ctx.fillStyle = '#7f8b98'; ctx.font = '10px system-ui, sans-serif'; ctx.textAlign = 'left';
    if (firstTime) ctx.fillText(new Date(firstTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), padding.left, height - 8);
    ctx.textAlign = 'right'; if (lastTime) ctx.fillText(new Date(lastTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), width - padding.right, height - 8);

    state.positions.forEach((position) => {
      if (!finite(position.priceOpen)) return;
      const y = yFor(position.priceOpen); const sell = Number(position.type) === 1 || String(position.side || '').toLowerCase() === 'sell';
      const color = sell ? '#ff6b6b' : '#5ce16b'; ctx.setLineDash([5, 4]); ctx.strokeStyle = color; ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(width - padding.right, y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = color; ctx.font = 'bold 10px system-ui, sans-serif'; ctx.textAlign = 'left'; ctx.fillText(`${sell ? 'SELL' : 'BUY'} ${priceLabel(position.priceOpen)}`, padding.left + 4, Math.max(12, y - 5));
    });
    state.markers.forEach((marker) => {
      if (!finite(marker.price) || !finite(marker.time) || Number(marker.time) < firstTime || Number(marker.time) > lastTime) return;
      const x = xForTime(marker.time), y = yFor(marker.price), kind = String(marker.kind || marker.side || '').toUpperCase();
      const color = kind.includes('SELL') ? '#ff5e5e' : kind.includes('EXIT') ? '#4c83ff' : '#64df58';
      ctx.setLineDash([2, 5]); ctx.strokeStyle = `${color}88`; ctx.beginPath(); ctx.moveTo(x, padding.top); ctx.lineTo(x, padding.top + plotHeight); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = color; ctx.beginPath(); if (kind.includes('EXIT')) ctx.arc(x, y, 5.5, 0, Math.PI * 2); else { ctx.moveTo(x, y - 7); ctx.lineTo(x - 6, y + 5); ctx.lineTo(x + 6, y + 5); ctx.closePath(); } ctx.fill();
      ctx.fillStyle = '#dce6f0'; ctx.font = 'bold 9px system-ui, sans-serif'; ctx.textAlign = x > width * 0.68 ? 'right' : 'left'; ctx.fillText(marker.label || kind || 'BOT', x > width * 0.68 ? x - 8 : x + 8, Math.max(12, y - 9));
    });
  }

  function render(canvas, candles, markers = [], positions = []) {
    const state = stateFor(canvas);
    const previousLength = state.candles.length;
    state.candles = Array.isArray(candles) ? candles : [];
    state.markers = Array.isArray(markers) ? markers : [];
    state.positions = Array.isArray(positions) ? positions : [];
    if (!previousLength && state.candles.length) state.visible = Math.min(90, state.candles.length);
    clampView(state); draw(canvas, state);
  }

  window.EBAChart = { render };
})();

window.addEventListener('DOMContentLoaded', () => {
  ['./mt5_ui.js', './paper_ui.js'].forEach((src) => {
    const script = document.createElement('script'); script.src = src; script.defer = true; document.body.appendChild(script);
  });
});
