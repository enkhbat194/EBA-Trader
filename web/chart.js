(() => {
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

  function render(canvas, candles, markers = [], positions = []) {
    const { ctx, width, height } = resizeCanvas(canvas);
    if (!Array.isArray(candles) || candles.length < 2) {
      drawEmpty(ctx, width, height, 'Waiting for market candles…');
      return;
    }

    const data = candles.filter((item) => finite(item.open) && finite(item.high) && finite(item.low) && finite(item.close));
    if (data.length < 2) {
      drawEmpty(ctx, width, height, 'Chart data unavailable');
      return;
    }

    const padding = { left: 10, right: 66, top: 14, bottom: 28 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    let minPrice = Math.min(...data.map((item) => Number(item.low)));
    let maxPrice = Math.max(...data.map((item) => Number(item.high)));
    positions.forEach((position) => {
      if (finite(position.priceOpen)) {
        minPrice = Math.min(minPrice, Number(position.priceOpen));
        maxPrice = Math.max(maxPrice, Number(position.priceOpen));
      }
    });
    const span = Math.max(maxPrice - minPrice, Math.abs(maxPrice) * 0.0005, 0.0001);
    minPrice -= span * 0.06;
    maxPrice += span * 0.06;

    const yFor = (price) => padding.top + ((maxPrice - Number(price)) / (maxPrice - minPrice)) * plotHeight;
    const step = plotWidth / data.length;
    const candleWidth = Math.max(2, Math.min(9, step * 0.62));

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#080d12';
    ctx.fillRect(0, 0, width, height);

    ctx.lineWidth = 1;
    ctx.font = '10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    for (let i = 0; i <= 5; i += 1) {
      const y = padding.top + (plotHeight * i) / 5;
      const price = maxPrice - ((maxPrice - minPrice) * i) / 5;
      ctx.strokeStyle = 'rgba(140,153,167,.12)';
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillStyle = '#7f8b98';
      ctx.fillText(priceLabel(price), width - padding.right + 8, y + 3);
    }

    data.forEach((candle, index) => {
      const x = padding.left + step * index + step / 2;
      const open = Number(candle.open);
      const high = Number(candle.high);
      const low = Number(candle.low);
      const close = Number(candle.close);
      const up = close >= open;
      const color = up ? '#64df58' : '#ff5e5e';
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(x, yFor(high));
      ctx.lineTo(x, yFor(low));
      ctx.stroke();
      const bodyTop = Math.min(yFor(open), yFor(close));
      const bodyHeight = Math.max(1, Math.abs(yFor(close) - yFor(open)));
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight);
    });

    const firstTime = Number(data[0].time || 0);
    const lastTime = Number(data[data.length - 1].time || 0);
    ctx.fillStyle = '#7f8b98';
    ctx.font = '10px system-ui, sans-serif';
    ctx.textAlign = 'left';
    if (firstTime) ctx.fillText(new Date(firstTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), padding.left, height - 8);
    ctx.textAlign = 'right';
    if (lastTime) ctx.fillText(new Date(lastTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), width - padding.right, height - 8);

    positions.forEach((position) => {
      if (!finite(position.priceOpen)) return;
      const y = yFor(position.priceOpen);
      const sell = Number(position.type) === 1 || String(position.side || '').toLowerCase() === 'sell';
      const color = sell ? '#ff6b6b' : '#5ce16b';
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.font = 'bold 10px system-ui, sans-serif';
      ctx.textAlign = 'left';
      const side = sell ? 'SELL' : 'BUY';
      ctx.fillText(`${side} ${priceLabel(position.priceOpen)}`, padding.left + 4, Math.max(12, y - 5));
    });

    markers.forEach((marker) => {
      if (!finite(marker.price)) return;
      const y = yFor(marker.price);
      const kind = String(marker.kind || marker.side || '').toUpperCase();
      const color = kind.includes('SELL') ? '#ff5e5e' : kind.includes('EXIT') ? '#4c83ff' : '#64df58';
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(width - padding.right - 8, y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#dce6f0';
      ctx.font = '10px system-ui, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(marker.label || kind || 'BOT', width - padding.right - 16, y + 3);
    });
  }

  window.EBAChart = { render };
})();

// Base app.js is a deferred script after chart.js. DOMContentLoaded therefore
// fires only after the base Binance/MT5 bindings exist. Load the optional paper
// layer then so it can extend those bindings without duplicating the core UI.
window.addEventListener('DOMContentLoaded', () => {
  const script = document.createElement('script');
  script.src = './paper_ui.js';
  script.defer = true;
  document.body.appendChild(script);
});
