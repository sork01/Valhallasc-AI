// Verify the exact executable's energy recovery using authoritative simulation ticks.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const world = new TestWorld();
world.levelSpread = 0;
(async () => {
  await world.start();
  const results = [];
  for (const [className, rate] of [['hunter', 15], ['assassin', 10]]) {
    const bot = className;
    await world.connect({ bot, class: className });
    await world.debug(bot, { op: 'set_resource', amount: 0 });
    await world.waitFor(() => world.player(bot).resource < 5, 5000, 'depleted energy snapshot');
    const first = { tick: world.views.get(bot).tick, energy: world.player(bot).resource };
    await world.waitFor(() => world.views.get(bot).tick >= first.tick + 40, 10000, 'two simulation seconds');
    const last = { tick: world.views.get(bot).tick, energy: world.player(bot).resource };
    const expected = (last.tick - first.tick) * .05 * rate;
    assert.ok(Math.abs(last.energy - first.energy - expected) < 1e-6,
      `${className}: expected ${rate} energy/second; gained ${last.energy - first.energy} over ${last.tick - first.tick} ticks`);
    results.push({ class: className, rate, ticks: last.tick - first.tick, gained: last.energy - first.energy });
    await world.disconnect(bot);
  }
  console.log('PASS energy recovery: ' + JSON.stringify(results));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => world.stop());
