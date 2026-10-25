const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');
const defaults = {
  warrior: ['cleave', 'battlecry', 'shieldwall', 'whirlwind'],
  mage: ['twinbolt', 'arcaneward', 'fireball', 'barrage'],
  assassin: ['throwingknives', 'evasion', 'lunge', 'flurry'],
  priest: ['mend', 'smite', 'wardoflight', 'prayer'],
  hunter: ['powershot', 'multishot', 'rollaway', 'piercingarrow'],
};
const suite = {
  name: 'touch-skill-unlocks',
  mutate: page => replace(page, 'touch.js', 'skill.level <= (Field.hero?.level || 1)', 'true'),
  async test({ player, check, width, height, out }) {
    for (const [name, ids] of Object.entries(defaults)) {
      const page = await player('Unlock' + name, { characterClass: name });
      await safeSpot(page);
      for (const level of [1, 3, 4, 7, 8, 11, 12, 15, 16]) {
        await debug(page, { op: 'set_level', level });
        await page.waitForFunction(level => Field.hero.level === level, level);
        await page.evaluate(() => TouchControls.update());
        const expected = ids.slice(0, Math.floor(level / 4));
        const visible = await page.locator('#touch-skills .touch-skill:visible').evaluateAll(nodes => nodes.map(n => n.dataset.skill));
        check(visible.join(',') === expected.join(','), `${name} level ${level}: only earned skills fill the arc (${visible})`);
        check(await page.locator('#touch-skills .touch-attack').isVisible(), `${name} level ${level}: Attack stays visible`);
        if (level === 1) {
          check(await page.evaluate(id => !TouchControls.assign(0, id), ids[0]), `${name}: cannot assign a locked skill`);
          await page.evaluate(() => TouchControls.edit(true));
          check(await page.locator('#touch-skill-editor select').evaluateAll(nodes => nodes.every(n => [...n.options].every(o => !o.value || Skillbar.state(o.value).skill.level <= Field.hero.level))), `${name}: assignment pickers offer only earned skills`);
          await page.evaluate(() => TouchControls.edit(false));
        }
        if (name === 'mage' && [1, 4, 16].includes(level)) await page.screenshot({ path: `${out}/unlocks-${level}-${width}x${height}.png` });
      }
      if (name === 'mage') {
        await page.evaluate(() => {
          Prefs.set({ touchSkills: { mage: ['fireball', 'arcaneward', null, 'blink'] } });
        });
        await debug(page, { op: 'set_level', level: 4 });
        await page.waitForFunction(() => Field.hero.level === 4);
        await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
        await page.waitForFunction(() => Online.connected && Field.hero?.level === 4);
        await page.evaluate(() => TouchControls.update());
        check(await page.locator('#touch-skills .touch-skill:visible').count() === 0, 'reloaded locked custom choices stay hidden');
        check(await page.evaluate(() => TouchControls.assign(2, 'twinbolt') && Prefs.touchSkills.mage.join(',') === 'fireball,arcaneward,twinbolt,blink'), 'editing another slot preserves locked custom choices');
        await debug(page, { op: 'set_level', level: 20 });
        await page.waitForFunction(() => Field.hero.level === 20);
        await page.evaluate(() => TouchControls.update());
        check(await page.locator('#touch-skills .touch-skill:visible').evaluateAll(nodes => nodes.map(n => n.dataset.skill).join(',') === 'fireball,arcaneward,twinbolt,blink'), 'custom skills appear automatically when earned');
        check(await page.evaluate(() => TouchControls.assign(0, null)), 'an earned slot can be deliberately emptied');
        check(await page.locator('#touch-skills [data-arc="0"]').isHidden(), 'deliberately empty slots stay hidden');
      }
      await page.context().close();
    }
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
