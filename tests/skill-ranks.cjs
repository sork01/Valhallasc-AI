// Private-world check: rank effects come from saved level and keep the same skill ID.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { castSkill } = require('../scripts/testing/tools.cjs');

(async () => {
  const world = new TestWorld();
  try {
    await world.start();
    await world.connect({ bot: 'RankMage', class: 'mage' });
    await world.debug('RankMage', { op: 'set_level', level: 23 });
    const first = await castSkill(world, 'RankMage', { skill: 'arcaneward', resetCooldown: true });
    assert.ok(first.cast, 'base Arcane Ward casts');
    await world.waitFor(() => world.summary('RankMage').buffs.some(b => b.id === 'arcaneward'), 3000, 'base ward buff');

    const advance = await world.debug('RankMage', { op: 'set_level', level: 24 });
    assert.deepEqual(advance.result.unlocked, ['arcaneward']);
    const ranked = await castSkill(world, 'RankMage', { skill: 'arcaneward', resetCooldown: true });
    assert.ok(ranked.cast, 'ranked Arcane Ward casts through the same ID');
    await world.waitFor(() => world.summary('RankMage').buffs.some(b => b.id === 'arcaneward'), 3000, 'ranked ward buff');

    await world.debug('RankMage', { op: 'set_level', level: 29 });
    const baseBlink = await castSkill(world, 'RankMage', { skill: 'blink', resetCooldown: true });
    assert.ok(baseBlink.cast && baseBlink.cooldownLeft > 0);
    const blinkAdvance = await world.debug('RankMage', { op: 'set_level', level: 30 });
    assert.deepEqual(blinkAdvance.result.unlocked, ['blink']);
    const rankedBlink = await castSkill(world, 'RankMage', { skill: 'blink', resetCooldown: true });
    assert.ok(rankedBlink.cast && rankedBlink.cooldownLeft < baseBlink.cooldownLeft - 0.8,
      'rank 2 reduces the authoritative cooldown');

    await world.debug('RankMage', { op: 'set_level', level: 49 });
    const thirdAdvance = await world.debug('RankMage', { op: 'set_level', level: 50 });
    assert.deepEqual(thirdAdvance.result.unlocked, ['blink']);
    const thirdBlink = await castSkill(world, 'RankMage', { skill: 'blink', resetCooldown: true });
    assert.ok(thirdBlink.cast && thirdBlink.cooldownLeft < rankedBlink.cooldownLeft - 0.8,
      'rank 3 reduces the authoritative cooldown further');

    await world.debug('RankMage', { op: 'set_level', level: 69 });
    const fourthAdvance = await world.debug('RankMage', { op: 'set_level', level: 70 });
    assert.deepEqual(fourthAdvance.result.unlocked, ['blink']);
    const fourthBlink = await castSkill(world, 'RankMage', { skill: 'blink', resetCooldown: true });
    assert.ok(fourthBlink.cast && fourthBlink.cooldownLeft < thirdBlink.cooldownLeft - 0.8,
      'rank 4 reduces the authoritative cooldown further');

    for (const [bot, playerClass, skill] of [
      ['RankWarrior', 'warrior', 'cleave'], ['RankAssassin', 'assassin', 'throwingknives'],
      ['RankPriest', 'priest', 'mend'],
    ]) {
      await world.connect({ bot, class: playerClass });
      await world.debug(bot, { op: 'set_level', level: 61 });
      const unlock = await world.debug(bot, { op: 'set_level', level: 62 });
      assert.deepEqual(unlock.result.unlocked, [skill], `${playerClass} receives rank 4 at level 62`);
    }

    await world.restart();
    assert.equal(world.player('RankMage').level, 70, 'saved level survives restart');
    const resumed = await castSkill(world, 'RankMage', { skill: 'blink', resetCooldown: true });
    assert.ok(resumed.cast && resumed.cooldownLeft < thirdBlink.cooldownLeft - 0.8,
      'rank remains authoritative after restart');
    console.log('Skill rank unlock, server buff and restart checks passed');
  } finally {
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
