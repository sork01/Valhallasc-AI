// Compare exact old/new executables in disposable worlds. No combat grind or public connections.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '../..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
// Defaults describe the latest boss health change (1.15.13).
const factor = Number(process.env.BOSS_HP_FACTOR || 1.5);
const prior = read(process.env.BOSS_HP_FIXTURE || 'tests/fixtures/dungeon-power-before-boss-hp-plus50.txt');
const powers = read('world/elite-power.txt');
assert.deepEqual(Object.keys(powers), Object.keys(prior));
const changed = new Set(Object.keys(prior).filter(kind => prior[kind][0] !== powers[kind][0]));
assert.equal(changed.size, 65);
for (const [kind, old] of Object.entries(prior)) {
  assert.equal(powers[kind][1], old[1], `${kind}: unchanged damage`);
  assert.ok(Math.abs(powers[kind][0] - old[0] * (changed.has(kind) ? factor : 1)) < 1e-10);
}
const raw = read('world/map.txt');
const fixtures = [raw, ...raw.zones].flatMap((map, zone) => {
  const dungeon = map.copies > 0 && !map.raid;
  if (!dungeon && !map.raid) return [];
  const unique = new Map();
  for (const spawn of map.slimes) {
    if (!spawn.ambush && (map.raid || changed.has(spawn.kind))) unique.set(spawn.kind, spawn);
  }
  if (dungeon) {
    const pack = map.slimes.find(s => !s.ambush && !changed.has(s.kind));
    assert.ok(pack, `${map.name}: ordinary pack control`); unique.set(pack.kind, pack);
  }
  return [...unique.values()].map(spawn => ({ zone, kind: spawn.kind, x: spawn.x, y: spawn.y, boss: dungeon && changed.has(spawn.kind) }));
});
assert.equal(fixtures.filter(f => f.boss).length, 65);
async function capture(binary) {
  process.env.VALHALLA_BINARY = binary;
  const world = new TestWorld(); world.levelSpread = 0;
  const rows = [];
  try {
    await world.start(); await world.connect({ bot: 'BossHealth', class: 'warrior' });
    for (const f of fixtures) {
      await world.debug('BossHealth', { op: 'teleport', zone: f.zone, x: f.x + 3, y: f.y });
      const enemy = await world.waitFor(() => world.views.get('BossHealth')?.slimes?.find(s => s.kind === f.kind), 5000, f.kind);
      rows.push({ zone: f.zone, kind: f.kind, level: enemy.level, maxHp: enemy.maxHp, boss: f.boss });
    }
    return rows;
  } finally { await world.stop(); }
}
(async () => {
  const candidate = process.env.VALHALLA_BINARY, baseline = process.env.BOSS_HP_BASELINE_BINARY;
  assert.ok(candidate && baseline, 'provide both retained and candidate executable paths');
  const before = await capture(baseline), after = await capture(candidate);
  for (let i = 0; i < after.length; i++) {
    const a = after[i], b = before[i];
    assert.deepEqual([a.zone, a.kind, a.level], [b.zone, b.kind, b.level]);
    assert.ok(Math.abs(a.maxHp - b.maxHp * (a.boss ? factor : 1)) <= (a.boss ? 1 : 0), `${a.kind}: ${b.maxHp} -> ${a.maxHp}`);
  }
  const report = path.join(root, 'test-results/dungeon-boss-health/protocol.json');
  fs.mkdirSync(path.dirname(report), { recursive: true });
  fs.writeFileSync(report, JSON.stringify({ before, after }, null, 2) + '\n');
  console.log(`PASS: ${after.filter(r => r.boss).length} dungeon bosses have ${factor * 100}% health; ${after.filter(r => !r.boss).length} pack/raid controls unchanged.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
