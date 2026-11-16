import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pivots, cluster, detectBreakout, cooldownAllows, recordSignal, isSupportedTimeframe } from './lib/levels.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const CACHE_TTL_MS = 60_000;
const cache = new Map();
const telegramSent = new Set();

function send(res, status, body, type = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'Content-Type': type, 'X-Content-Type-Options': 'nosniff' });
  res.end(type.startsWith('application/json') ? JSON.stringify(body) : body);
}

function indicators(raw) {
  const candles = raw.map((c) => ({
    time: Math.floor(Number(c[0]) / 1000),
    open: Number(c[1]), high: Number(c[2]), low: Number(c[3]),
    close: Number(c[4]), volume: Number(c[5]), closeTime: Number(c[6])
  }));
  let atr = null;
  let trSeed = [];
  let atrValue = null;
  const volumes = [];
  return candles.map((c, i) => {
    const previousClose = i ? candles[i - 1].close : c.close;
    const tr = Math.max(c.high - c.low, Math.abs(c.high - previousClose), Math.abs(c.low - previousClose));
    if (i < 14) {
      trSeed.push(tr);
      if (i === 13) atrValue = trSeed.reduce((a, b) => a + b, 0) / 14;
    } else {
      atrValue = ((atrValue * 13) + tr) / 14;
    }
    volumes.push(c.volume);
    const volSma = i >= 19 ? volumes.slice(i - 19, i + 1).reduce((a, b) => a + b, 0) / 20 : null;
    return { ...c, atr: i >= 13 ? atrValue : null, volSma };
  });
}

function evaluate(candles, symbol, timeframe) {
  const state = new Map();
  let latestSignal = null;
  let latestZones = [];
  for (let i = 0; i < candles.length; i += 1) {
    const visible = candles.slice(0, i + 1);
    const confirmedPivots = pivots(visible, 3, 3);
    const zones = cluster(confirmedPivots, null, 0.25);
    const c = candles[i];
    if (Number.isFinite(c.atr) && Number.isFinite(c.volSma)) {
      for (const zone of zones) {
        const signal = detectBreakout(c, zone, c.atr, c.volSma, 1.5);
        if (signal && cooldownAllows(zone.id, i, state, 12)) {
          recordSignal(zone.id, i, state);
          if (i === candles.length - 1) {
            latestSignal = { ...signal, symbol, timeframe, time: c.time, barIndex: i };
          }
          // Match Pine's one-alert-per-closed-bar behavior: first seed-ordered zone wins.
          break;
        }
      }
    }
    if (i === candles.length - 1) latestZones = zones;
  }
  return { latestSignal, zones: latestZones };
}

async function notifyTelegram(signal) {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;
  if (!token || !chatId || !signal) return;
  const key = [signal.symbol, signal.timeframe, signal.time, signal.zoneId, signal.direction].join(':');
  if (telegramSent.has(key)) return;
  telegramSent.add(key);
  const text = [
    `Bullseye Levels — ${signal.direction}`,
    `${signal.symbol} · ${signal.timeframe}`,
    `Entry: ${signal.entry}`,
    `Stop loss: ${signal.stopLoss}`,
    `Target (1:2): ${signal.target}`,
    `Zone strength: ${signal.strength} touches`,
    'Educational scenario only — not investment advice.'
  ].join('\n');
  try {
    const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text })
    });
    if (!response.ok) throw new Error(`Telegram HTTP ${response.status}`);
    const result = await response.json();
    if (!result.ok) throw new Error('Telegram rejected the message');
  } catch (error) {
    telegramSent.delete(key);
    console.error('Telegram alert failed:', error.message);
  }
}

async function indicatorHandler(symbol, timeframe) {
  if (!/^[A-Z0-9]{3,20}$/.test(symbol) || !isSupportedTimeframe(timeframe)) {
    return { statusCode: 400, body: { status: 'NO_TRADE', reason: 'Unsupported symbol or timeframe. Use Binance symbols and 15m/1h only.' } };
  }
  const key = `${symbol}:${timeframe}`;
  const cached = cache.get(key);
  if (cached && Date.now() - cached.createdAt < CACHE_TTL_MS) return { statusCode: 200, body: cached.body, cached: true };

  const url = new URL('https://api.binance.com/api/v3/klines');
  url.searchParams.set('symbol', symbol);
  url.searchParams.set('interval', timeframe);
  url.searchParams.set('limit', '500');
  const upstream = await fetch(url, { signal: AbortSignal.timeout(12_000) });
  if (!upstream.ok) throw new Error(`Binance HTTP ${upstream.status}`);
  const raw = await upstream.json();
  if (!Array.isArray(raw)) throw new Error('Unexpected Binance response');

  // Binance includes the currently-forming candle; discard it unconditionally.
  const completed = raw.filter((row) => Number(row[6]) < Date.now());
  if (completed.length < 40) {
    return { statusCode: 200, body: { status: 'NO_TRADE', reason: 'Not enough completed candles for ATR/SMA and confirmed pivots.', symbol, timeframe, candles: [], zones: [], signal: null } };
  }
  const candles = indicators(completed);
  const { latestSignal, zones } = evaluate(candles, symbol, timeframe);
  const signal = latestSignal ? { ...latestSignal, rr: 2 } : null;
  const body = {
    status: signal ? 'SIGNAL' : 'NO_TRADE',
    symbol, timeframe,
    updatedAt: new Date().toISOString(),
    candles: candles.map(({ time, open, high, low, close, volume }) => ({ time, open, high, low, close, volume })),
    zones: zones.map((z) => ({ ...z, startTime: candles[z.seedIndex]?.time ?? candles[0].time })),
    signal
  };
  cache.set(key, { createdAt: Date.now(), body });
  if (signal) await notifyTelegram(signal);
  return { statusCode: 200, body, cached: false };
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8' };
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    if (req.method !== 'GET') return send(res, 405, { error: 'Method not allowed' });
    const match = url.pathname.match(/^\/api\/indicator\/([^/]+)\/([^/]+)$/);
    if (match) {
      const result = await indicatorHandler(match[1].toUpperCase(), match[2]);
      return send(res, result.statusCode, result.body);
    }
    if (url.pathname === '/health') return send(res, 200, { ok: true });
    const relative = url.pathname === '/' ? 'indicator.html' : decodeURIComponent(url.pathname.slice(1));
    const file = path.resolve(ROOT, relative);
    if (!file.startsWith(ROOT + path.sep) && file !== path.join(ROOT, 'indicator.html')) return send(res, 403, { error: 'Forbidden' });
    const data = await readFile(file);
    return send(res, 200, data, MIME[path.extname(file)] || 'application/octet-stream');
  } catch (error) {
    console.error(error.message);
    return send(res, 502, { status: 'NO_TRADE', error: 'Market data temporarily unavailable.' });
  }
});

server.listen(PORT, () => console.log(`Bullseye Levels listening on :${PORT}`));
