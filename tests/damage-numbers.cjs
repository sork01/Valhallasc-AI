// UI-DAMAGE-NUMBERS, the maths: the path of a floating number (client/damagenumbers.js is pure, so it runs here without a browser).
const assert = require('node:assert/strict');
const D = require('../client/damagenumbers.js');
let checks = 0;
const check = (c, m) => { assert.ok(c, m); checks++; };
const seeded = seed => () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;

for (const kind of Object.keys(D.KINDS)) {
  const k = D.KINDS[kind], f = { kind, text: '123', t: 0, lane: 0, z0: 0, side: 1 };
  // Starts at the head: no climb yet, fully there; rises monotonically; ends transparent; never below the head.
  check(D.pose({ ...f, t: .001 }).dz < 2, `${kind} starts at the head`);
  let last = -1, lastAlpha = 2;
  for (let t = 0; t < k.life; t += .01) {
    const p = D.pose({ ...f, t });
    check(p.dz >= last - 1e-9, `${kind} rises monotonically at ${t.toFixed(2)}s`); last = p.dz;
    check(p.alpha <= lastAlpha + 1e-9 || t < .15, `${kind} never gets more opaque after the pop`); lastAlpha = p.alpha;
    check(p.dz >= 0, `${kind} never sinks below the head`);
  }
  check(D.pose({ ...f, t: k.life - .005 }).alpha < .05, `${kind} ends transparent`);
  check(!D.pose({ ...f, t: k.life }).visible, `${kind} is gone at the end`);
  check(D.pose({ ...f, t: k.life * k.hold * .8 }).alpha === 1, `${kind} holds at full opacity before it fades`);
  const r = D.pose({ ...f, t: k.life * .5 }, true);
  check(r.dx === 0 && r.dz === 0 && r.scale === 1, `${kind} fades in place under reduced motion`);
  if (k.pop > 1.05) check(D.pose({ ...f, t: .12 }).scale > 1.05 && D.pose({ ...f, t: .005 }).scale < .6, `${kind} pops in from small to over full size`);
  if (k.ease > .4) { const a = D.pose({ ...f, t: k.life * .25 }).dz, b = D.pose({ ...f, t: k.life * .5 }).dz - a, c = D.pose({ ...f, t: k.life * .75 }).dz - D.pose({ ...f, t: k.life * .5 }).dz;
    check(a > b && b > c, `${kind} rises fast at first and slows`); }
}
check(D.KINDS.crit.size > D.KINDS.hit.size && D.KINDS.miss.size < D.KINDS.hit.size, 'crits are bigger and a miss is smaller than a hit');

// A run of hits over one head never overlaps (any pair, any frame), whatever side each number happens to pick.
function overlapsIn(hits, interval, delay, seed, kind = 'hit') {
  let list = [], worst = 0, spawned = 0, t = 0;
  const rand = seeded(seed), anchor = { x: 5, y: 7, head: 70 };
  for (let frame = 0; frame < 400; frame++) {
    while (spawned < hits && spawned * interval <= t + 1e-9) {
      for (let i = 0; i < (delay ? 5 : 1); i++) D.spawn(list, { ...anchor, kind, text: String(1000 + spawned * 37 + i), delay: delay ? i * .06 : 0 }, rand);
      spawned++;
    }
    const vis = list.filter(f => D.pose(f).visible);
    for (let i = 0; i < vis.length; i++) for (let j = i + 1; j < vis.length; j++) {
      const a = D.box(vis[i]), b = D.box(vis[j]);
      if (a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1) worst++;
    }
    list = D.step(list, .016); t += .016;
  }
  return worst;
}
for (const seed of [1, 2, 3, 4, 5]) {
  check(overlapsIn(10, .1, false, seed) === 0, `ten hits 0.1 s apart overlap (seed ${seed})`);
  check(overlapsIn(10, .05, false, seed) === 0, `ten hits 0.05 s apart overlap (seed ${seed})`);
  check(overlapsIn(3, .6, true, seed) === 0, `three five-hit skills overlap (seed ${seed})`);
  check(overlapsIn(10, .2, false, seed, 'crit') === 0, `ten crits 0.2 s apart overlap (seed ${seed})`);
}
// The cap: a flood keeps at most MAX_ALIVE numbers fading normally; the extra ones are told to leave fast.
{
  const list = []; for (let i = 0; i < 150; i++) D.spawn(list, { x: i, y: 0, head: 50, kind: 'hit', text: '9' });
  const live = list.filter(f => f.t < D.KINDS.hit.life - .2);
  check(live.length <= D.MAX_ALIVE, `a flood of 150 leaves ${live.length} normal numbers`);
}
check(D.format(7) === '7' && D.format(1234) === '1,234' && D.format(9999) === '9,999', 'thousands separator');
check(D.format(12345) === '12.3k' && D.format(123456) === '123k' && D.format(1500000) === '1.5M' && D.format(25000000) === '25M', 'large numbers are compact');
check(D.format(0) === '0' && D.format(-250) === '-250', 'zero and negatives');
// A party burst on one target must finish promptly, without a late replay of
// queued hits after combat has stopped. Different positions do not expose this.
{
  let list = [];
  for (let i = 0; i < 300; i++) D.spawn(list, { x: 5, y: 7, head: 70, kind: i % 3 ? 'hit' : 'crit', text: String(i) }, seeded(i));
  check(list.every(f => f.t >= -.32 - 1e-9), 'a party burst cannot queue old numbers for seconds');
  list = D.step(list, 2);
  check(list.length === 0, 'all numbers from a finished party burst expire within two seconds');
}
console.log(`${checks} damage-number checks passed`);
