// Exact release executable: real accepted Mage/Priest casts report actual mana returned.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const world = new TestWorld(); world.startLevel = 40; world.levelSpread = 0;
(async () => {
  await world.start();
  const results = [];
  for (const [className, id] of [['mage', 'arcaneward'], ['priest', 'mend']]) {
    const bot = className;
    await world.connect({ bot, class: className });
    const max = world.player(bot).maxResource;
    let returned = false, casts = 0;
    for (; casts < 150 && !returned; casts++) {
      await world.debug(bot, { op: 'reset_cooldowns' });
      await world.debug(bot, { op: 'set_resource', amount: max * .5 });
      if (className === 'priest') await world.debug(bot, { op: 'set_hp', hp: world.player(bot).maxHp * .5 });
      const earlier = new Set(world.events);
      await world.action(bot, { type: 'skill', id, fx: 1, fy: 0 });
      const event = await world.waitFor(() => world.events.find(e => !earlier.has(e) && e.bot === bot && e.kind === 'skill' && e.skill === id), 5000, `${className} accepted cast`);
      assert.ok(Number.isFinite(event.mana), 'accepted casts report the authoritative mana return');
      if (event.mana > 0) {
        assert.ok(Math.abs(event.mana - max * .2) < 1e-8, `${className}: ${event.mana}/${max}`);
        returned = true;
      }
    }
    assert.ok(returned, `${className}: no mana return in 150 accepted casts`);
    results.push({ class: className, casts, manaReturned: max * .2, maximum: max });
    await world.disconnect(bot);
  }
  world.saveReport({ passed: true, results });
  console.log('PASS class resources: ' + JSON.stringify(results));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => world.stop());
