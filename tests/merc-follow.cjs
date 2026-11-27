// Real hiring and snapshots around existing Skaldholm buildings; private server only.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { route } = require('../scripts/testing/route.cjs');
const kit = require('../scripts/testing/tools.cjs');
const fs = require('node:fs');
const map = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../world/map.txt'))).zones[3];
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
// Perpendicular distance from the straight line from->to: a detour bends off it, a straight walk does not.
const offLine = (p, from, to) => {
  const dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1;
  return Math.abs((p.x - from.x) * dy - (p.y - from.y) * dx) / len;
};
const w = new TestWorld();
const mercs = () => (w.snapshot?.players || []).filter(p => p.look.name.startsWith('Merc '));
(async () => {
  w.startLevel = 20; w.levelSpread = 0;
  await w.start(); await w.connect({ bot: 'hirer', class: 'warrior' });
  // Use an outdoor quest contract while exercising outdoor pathfinding.
  await w.debug('hirer', { op: 'quest', id: 'fen_hydra', action: 'finish' });
  await kit.teleport(w, 'hirer', { npc: 'fen_reeve' });
  await kit.talkTo(w, 'hirer', 'fen_reeve', 'quest:accept:fen_gloomroot');
  await w.debug('hirer', { op: 'set_gold', gold: 10000 });
  for (const cls of ['mage', 'assassin', 'priest', 'hunter']) {
    await w.advance(600);
    await w.action('hirer', { type: 'interact', npc: 'fen_reeve', offer: `merc_${cls}` });
    await w.waitFor(() => mercs().some(p => p.look.class === cls), 5000, `Hire ${cls}`);
  }
  assert.equal(mercs().length, 4);
  assert.equal(w.player('hirer').gold, 5200);
  let checks = 2;
  for (const [from, to] of [
    // Shaped Skaldholm (2026-11): the old x 93..107 / 55..69 endpoints are void. Each pair runs straight through a
    // building's centre (the Hall at 79.5,61 and the house at 85.5,99), so the route bends 4+ tiles off the line.
    [{ x: 79.5, y: 66.5 }, { x: 79.5, y: 55.5 }],
    [{ x: 79.5, y: 99.5 }, { x: 91.5, y: 98.5 }],
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
        const worst = Math.max(0, ...trace.filter(p => p.class === cls).map(p => offLine(p, from, to)));
        assert.ok(worst > 2.5, `${cls} took the detour (largest offset ${worst.toFixed(2)}, samples ${trace.filter(p => p.class === cls).length})`); checks++;
      }
    } finally { w.off('change', inspect); }
  }
  assert.equal(w.snapshot.online, 1); checks++;
  console.log(`${checks} private mercenary following checks passed. Artifact: ${w.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => w.stop());
