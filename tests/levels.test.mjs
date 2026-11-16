import test from 'node:test';
import assert from 'node:assert/strict';
import { pivots, cluster, detectBreakout, cooldownAllows, recordSignal, isSupportedTimeframe } from '../lib/levels.mjs';

test('strict 3-left/3-right pivots are confirmed only when right candles exist', () => {
  const highs = [1, 2, 3, 10, 3, 2, 1];
  const candles = highs.map((high, i) => ({ high, low: i, atr: 2, volume: 10, close: 0, time: i }));
  assert.deepEqual(pivots(candles, 3, 3), [
    { index: 3, type: 'supply', price: 10, atr: 2 }
  ]);
  assert.deepEqual(pivots(candles.slice(0, 6), 3, 3), []);
});

test('clusters nearby same-side pivots into one zone and rejects isolated touches', () => {
  const input = [
    { index: 2, type: 'supply', price: 100, atr: 4 },
    { index: 8, type: 'supply', price: 100.8, atr: 4 },
    { index: 5, type: 'demand', price: 90, atr: 4 },
    { index: 12, type: 'demand', price: 90.5, atr: 4 },
    { index: 20, type: 'supply', price: 110, atr: 4 }
  ];
  const zones = cluster(input, 4, 0.25);
  assert.deepEqual(zones, [
    { id: 'supply-2', type: 'supply', seedIndex: 2, bottom: 100, top: 100.8, center: 100.4, touches: 2, strength: 2, pivotIndices: [2, 8] },
    { id: 'demand-5', type: 'demand', seedIndex: 5, bottom: 90, top: 90.5, center: 90.25, touches: 2, strength: 2, pivotIndices: [5, 12] }
  ]);
});

test('cluster threshold is seed anchored and uses the smaller ATR', () => {
  const input = [
    { index: 1, type: 'supply', price: 100, atr: 4 },
    { index: 2, type: 'supply', price: 100.9, atr: 4 },
    { index: 3, type: 'supply', price: 101.8, atr: 4 }
  ];
  const zones = cluster(input, 4, 0.25);
  assert.equal(zones.length, 1);
  assert.equal(zones[0].touches, 2);
});

test('volume filter rejects a price breakout when volume is not strictly above threshold', () => {
  const zone = { id: 'supply-1', bottom: 99, top: 100, touches: 2 };
  assert.equal(detectBreakout({ close: 101, volume: 150 }, zone, 5, 100, 1.5), null);
  assert.equal(detectBreakout({ close: 101, volume: 151 }, zone, 5, 100, 1.5).direction, 'LONG');
});

test('breakout requires strict ATR price buffer and produces exact long/short SL and TP', () => {
  const zone = { id: 'demand-4', bottom: 99, top: 100, touches: 3, strength: 3 };
  assert.equal(detectBreakout({ close: 100.5, volume: 200 }, zone, 5, 100), null);
  const long = detectBreakout({ close: 101, volume: 200 }, zone, 5, 100);
  assert.deepEqual(long, {
    direction: 'LONG', zoneId: 'demand-4', entry: 101, stopLoss: 98,
    target: 107, risk: 3, rewardRisk: 2, touches: 3, strength: 3
  });
  const short = detectBreakout({ close: 98.4, volume: 200 }, zone, 5, 100);
  assert.equal(short.direction, 'SHORT');
  assert.equal(short.zoneId, 'demand-4');
  assert.equal(short.entry, 98.4);
  assert.equal(short.stopLoss, 101);
  assert.ok(Math.abs(short.target - 93.2) < 1e-10);
  assert.ok(Math.abs(short.risk - 2.6) < 1e-10);
  assert.equal(short.rewardRisk, 2);
});

test('cooldown suppresses bars 1–11 and permits bar 12, independently per zone', () => {
  const state = new Map();
  recordSignal('supply-2', 100, state);
  assert.equal(cooldownAllows('supply-2', 111, state, 12), false);
  assert.equal(cooldownAllows('supply-2', 112, state, 12), true);
  assert.equal(cooldownAllows('demand-3', 101, state, 12), true);
});

test('only 15m and 1h are supported', () => {
  assert.equal(isSupportedTimeframe('15m'), true);
  assert.equal(isSupportedTimeframe('1h'), true);
  assert.equal(isSupportedTimeframe('5m'), false);
});
