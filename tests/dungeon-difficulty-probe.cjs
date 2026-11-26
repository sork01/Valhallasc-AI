// Compare the running candidate executable with the retained live executable in private worlds.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const raw = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../world/map.txt'), 'utf8'));
const fixtures = [raw, ...raw.zones].flatMap((map, zone) => {
  if (!map.copies || map.raid) return [];
  const spawn = map.slimes.find(s => !s.ambush && s.kind !== map.final_boss) || map.slimes.find(s => !s.ambush);
  return [{ zone, name: map.name, kind: spawn.kind, x: spawn.x, y: spawn.y }];
});
async function capture(binary, performance = false) {
  process.env.VALHALLA_BINARY = binary;
  const w = new TestWorld(); w.levelSpread = 0;
  const rows = [];
  let timing;
  try {
    await w.start(); await w.connect({ bot: 'DungeonProbe', class: 'warrior' });
    for (const fixture of fixtures) {
      await w.debug('DungeonProbe', { op: 'teleport', zone: fixture.zone, x: fixture.x + 5, y: fixture.y });
      const monster = await w.waitFor(() => w.views.get('DungeonProbe')?.slimes?.find(s => s.kind === fixture.kind), 5000, fixture.name + ' monster');
      rows.push({ zone: fixture.zone, name: fixture.name, kind: fixture.kind, level: monster.level, maxHp: monster.maxHp });
    }
    if (performance) {
      await w.debug('DungeonProbe', { op: 'teleport', zone: 0, x: raw.spawn.x, y: raw.spawn.y });
      const ticks = [], times = [];
      const sample = data => { const p = JSON.parse(data.toString()); if (p.type === 'snapshot') { ticks.push(p.tick); times.push(Date.now()); } };
      const socket = w.bots.get('DungeonProbe').socket; socket.on('message', sample);
      await w.waitFor(() => ticks.length >= 30, 4000, '30 private snapshots'); socket.off('message', sample);
      const milliseconds = times[29] - times[0];
      assert.ok(milliseconds <= 3000, `30 snapshots took ${milliseconds}ms`);
      assert.ok(ticks.slice(1, 30).every((tick, i) => tick - ticks[i] === 2), 'snapshot tick gaps remain two');
      timing = { count: 30, milliseconds, tickGap: 2 };
    }
    return { rows, timing, artifacts: w.runDir };
  } finally { await w.stop(); }
}
(async () => {
  const candidate = process.env.VALHALLA_BINARY;
  const baseline = process.env.DIFFICULTY_BASELINE_BINARY;
  assert.ok(candidate && baseline, 'Provide candidate and retained executable paths');
  const before = await capture(baseline);
  const after = await capture(candidate, true);
  assert.equal(before.rows.length, 20); assert.equal(after.rows.length, 20);
  for (const [index, row] of after.rows.entries()) {
    const prior = before.rows[index];
    assert.deepEqual([row.zone, row.kind, row.level], [prior.zone, prior.kind, prior.level]);
    assert.ok(Math.abs(row.maxHp - prior.maxHp * 2) <= 1, `${row.name}: health must double (${prior.maxHp} -> ${row.maxHp})`);
  }
  const output = path.resolve(__dirname, '../test-results/dungeon-difficulty/protocol.json'); fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify({ before, after }, null, 2) + '\n');
  console.log(`PASS dungeon-difficulty-probe: 20 private dungeon health comparisons; ${after.timing.count} snapshots in ${after.timing.milliseconds}ms, tick gaps ${after.timing.tickGap}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
