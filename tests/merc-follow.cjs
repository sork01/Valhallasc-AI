// Real hiring and snapshots around existing Skaldholm buildings; private server only.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { route } = require('../scripts/testing/route.cjs');
const fs = require('node:fs');
const map = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../world/map.txt'))).zones[3];
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const w = new TestWorld();
const mercs = () => (w.snapshot?.players || []).filter(p => p.look.name.startsWith('Merc '));
(async () => {
  w.startLevel = 20; w.levelSpread = 0;
  await w.start(); await w.connect({ bot: 'hirer', class: 'warrior' });
  await w.debug('hirer', { op: 'set_gold', gold: 10000 });
  await w.debug('hirer', { op: 'teleport', zone: 4, x: 101.7, y: 119.7 });
  for (const cls of ['mage', 'assassin', 'priest', 'hunter']) {
    await w.advance(600);
    await w.action('hirer', { type: 'interact', npc: 'city_meetingstone', offer: `merc_${cls}` });
    await w.waitFor(() => mercs().some(p => p.look.class === cls), 5000, `Hire ${cls}`);
  }
  assert.equal(mercs().length, 4);
  assert.equal(w.player('hirer').gold, 5200);
  let checks = 2;
  for (const [from, to] of [
    [{ x: 93, y: 58 }, { x: 107, y: 58 }],
    [{ x: 69, y: 27 }, { x: 55, y: 27 }],
  ]) {
    // Cross-zone setup brings the whole hired group to a known, safe starting point.
    await w.debug('hirer', { op: 'teleport', zone: 0, x: 80, y: 25 });
    await w.debug('hirer', { op: 'teleport', zone: 4, ...from });
    await w.waitFor(() => mercs().length === 4 && mercs().every(p => p.zone === 4 && distance(p, from) < 4));
    assert.ok(route(map, from, to).length > 1, 'Existing building requires a detour'); checks++;
    const previous = new Map(mercs().map(p => [p.id, { ...p, time: w.snapshot.time }]));
    const trace = [];
    let failure;
    const inspect = () => {
      if (!w.snapshot || w.player('hirer')?.zone !== 4) return;
      for (const p of mercs()) {
        const old = previous.get(p.id), time = w.snapshot.time;
        if (old && time > old.time) {
          // Faster than every class: allow packet rounding, but reject recovery/leash warps.
          if (distance(old, p) > (time - old.time) * 7 + .25) failure ||= `${p.look.class} warped instead of routing`;
          trace.push({ class: p.look.class, x: p.x, y: p.y, time });
        }
        previous.set(p.id, { ...p, time });
      }
    };
    w.on('change', inspect);
    try {
      await w.debug('hirer', { op: 'teleport', zone: 4, ...to });
      await w.waitFor(() => mercs().length === 4 && mercs().every(p => distance(p, to) < 4), 30000, 'All four hired fighters walk around the building');
      assert.equal(failure, undefined); checks++;
      for (const cls of ['mage', 'assassin', 'priest', 'hunter']) {
        assert.ok(trace.some(p => p.class === cls && Math.abs(p.y - from.y) > 2.5), `${cls} took the detour`); checks++;
      }
    } finally { w.off('change', inspect); }
  }
  assert.equal(w.snapshot.online, 1); checks++;
  console.log(`${checks} private mercenary following checks passed. Artifact: ${w.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => w.stop());
