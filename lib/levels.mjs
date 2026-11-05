/**
 * Bullseye Levels deterministic core.
 * Candle schema: { time, open, high, low, close, volume, atr? }.
 * Pivot schema returned: { index, type: 'supply'|'demand', price, atr }.
 */

/** Return confirmed strict swing pivots, oldest-first. */
export function pivots(candles, l = 3, r = 3) {
  if (!Array.isArray(candles)) throw new TypeError('candles must be an array');
  if (!Number.isInteger(l) || l < 1 || !Number.isInteger(r) || r < 1) {
    throw new RangeError('l and r must be positive integers');
  }
  const found = [];
  for (let i = l; i < candles.length - r; i += 1) {
    const c = candles[i];
    if (!Number.isFinite(c?.high) || !Number.isFinite(c?.low)) continue;
    let isHigh = true;
    let isLow = true;
    for (let j = i - l; j <= i + r; j += 1) {
      if (j === i) continue;
      if (c.high <= candles[j]?.high) isHigh = false;
      if (c.low >= candles[j]?.low) isLow = false;
      if (!isHigh && !isLow) break;
    }
    if (isHigh) found.push({ index: i, type: 'supply', price: c.high, atr: c.atr });
    if (isLow) found.push({ index: i, type: 'demand', price: c.low, atr: c.atr });
  }
  return found.sort((a, b) => a.index - b.index || a.type.localeCompare(b.type));
}

/**
 * Seed-anchored clustering. atr may be a scalar fallback or an index-aligned
 * array; pivot.atr takes precedence. Invalid ATR pivots are ignored.
 */
export function cluster(pivotList, atr, k = 0.25) {
  if (!Array.isArray(pivotList)) throw new TypeError('pivots must be an array');
  if (!Number.isFinite(k) || k < 0) throw new RangeError('k must be non-negative');
  const atrAt = (p) => p.atr ?? (Array.isArray(atr) ? atr[p.index] : atr);
  const valid = pivotList
    .filter((p) => Number.isFinite(p?.index) && Number.isFinite(p?.price)
      && (p.type === 'supply' || p.type === 'demand')
      && Number.isFinite(atrAt(p)) && atrAt(p) > 0)
    .slice()
    .sort((a, b) => a.index - b.index);
  const groups = [];
  for (const p of valid) {
    const pAtr = atrAt(p);
    const candidates = groups
      .filter((g) => g.type === p.type)
      .map((g) => ({ g, distance: Math.abs(p.price - g.seed.price) }))
      .filter(({ g, distance }) => distance <= k * Math.min(g.seedAtr, pAtr))
      .sort((a, b) => a.distance - b.distance || a.g.seed.index - b.g.seed.index);
    if (candidates.length) {
      candidates[0].g.members.push(p);
    } else {
      groups.push({ type: p.type, seed: p, seedAtr: pAtr, members: [p] });
    }
  }
  return groups.filter((g) => g.members.length >= 2).map((g) => {
    const prices = g.members.map((p) => p.price);
    return {
      id: `${g.type}-${g.seed.index}`,
      type: g.type,
      seedIndex: g.seed.index,
      bottom: Math.min(...prices),
      top: Math.max(...prices),
      center: prices.reduce((sum, price) => sum + price, 0) / prices.length,
      touches: g.members.length,
      strength: g.members.length,
      pivotIndices: g.members.map((p) => p.index)
    };
  });
}

/** Return a LONG/SHORT signal object, or null when every gate is not met. */
export function detectBreakout(candle, zone, atr, volSma, mult = 1.5) {
  if (!candle || !zone || !Number.isFinite(candle.close)
    || !Number.isFinite(candle.volume) || !Number.isFinite(atr) || atr <= 0
    || !Number.isFinite(volSma) || volSma < 0 || !Number.isFinite(mult) || mult < 0
    || !Number.isFinite(zone.bottom) || !Number.isFinite(zone.top)
    || zone.bottom > zone.top) return null;
  if (!(candle.volume > volSma * mult)) return null;
  let direction = null;
  if (candle.close > zone.top + 0.10 * atr) direction = 'LONG';
  else if (candle.close < zone.bottom - 0.10 * atr) direction = 'SHORT';
  if (!direction) return null;
  const entry = candle.close;
  const stopLoss = direction === 'LONG'
    ? zone.bottom - 0.20 * atr
    : zone.top + 0.20 * atr;
  const risk = Math.abs(entry - stopLoss);
  if (!(risk > 0) || !Number.isFinite(risk)) return null;
  const target = direction === 'LONG' ? entry + 2 * risk : entry - 2 * risk;
  return {
    direction, zoneId: zone.id, entry, stopLoss, target,
    risk, rewardRisk: 2, touches: zone.touches, strength: zone.strength ?? zone.touches
  };
}

/** True when the zone has no signal in the preceding cooldown bars. */
export function cooldownAllows(zoneId, barIndex, lastSignalByZone, cooldown = 12) {
  if (zoneId == null || !Number.isInteger(barIndex) || !Number.isInteger(cooldown) || cooldown < 0) {
    return false;
  }
  const last = lastSignalByZone instanceof Map
    ? lastSignalByZone.get(zoneId)
    : lastSignalByZone?.[zoneId];
  return last == null || barIndex - last >= cooldown;
}

/** Record a successfully emitted signal; caller invokes only after cooldownAllows. */
export function recordSignal(zoneId, barIndex, lastSignalByZone) {
  if (!Number.isInteger(barIndex)) throw new TypeError('barIndex must be an integer');
  if (lastSignalByZone instanceof Map) lastSignalByZone.set(zoneId, barIndex);
  else if (lastSignalByZone && typeof lastSignalByZone === 'object') lastSignalByZone[zoneId] = barIndex;
  else throw new TypeError('lastSignalByZone must be a Map or object');
}

/** Normalize API timeframe names; no other intervals are supported. */
export function isSupportedTimeframe(tf) {
  return tf === '15m' || tf === '1h';
}
