// A free Mend (`PRIEST-MEND-PROC`) lights up on the skill bar and the touch controls and can be cast with no mana.
// Run: bash scripts/test-touch-bounded.sh tests/mend-proc-ui.cjs     MUTATE=1 must fail.
const { run, replace, debug } = require('./lib/touch.cjs');

// Reads both control layouts for one made-up hero state. All in one task, so no snapshot can slip in between.
const probe = (page, state) => page.evaluate(state => {
  const hero = Field.hero, saved = { resource: hero.resource, mendFree: hero.mendFree, skillCd: hero.skillCd };
  Object.assign(hero, state); Skillbar.update();
  const read = id => {
    const slot = document.querySelector(`#skillbar-slots [data-skill="${id}"]`);
    const arc = document.querySelector(`#touch-skills [data-skill="${id}"]`);
    return {
      disabled: slot.disabled, free: slot.classList.contains('free-cast'), empty: slot.classList.contains('resource-empty'),
      label: slot.querySelector('.skill-cooldown').textContent, glow: getComputedStyle(slot).boxShadow,
      arcFree: !!arc?.classList.contains('free-cast'), arcDisabled: !!arc?.disabled, arcLabel: arc?.querySelector('.touch-free')?.textContent || '',
      ready: Skillbar.state(id).ready,
    };
  };
  const result = { mend: read('mend'), smite: read('smite') };
  Object.assign(hero, saved); Skillbar.update();
  return result;
}, state);

const suite = {
  name: 'mend-proc',
  mutate: page => replace(page, 'skillbar.js', "skill?.id === 'mend' && Field.hero.mendFree > 0", 'false'),
  async test({ player, check, out, width, height }) {
    for (const [kind, options] of [['touch', {}], ['desktop', { isMobile: false, hasTouch: false }]]) {
      const page = await player('Mend' + kind, { characterClass: 'priest', ...options });
      await page.waitForFunction(() => document.querySelector('#skillbar-slots [data-skill="mend"]'));
      check(await page.evaluate(() => /10% chance to ready Mend and make it free for 4 seconds\. Not in PvP\./.test(Skillbar.catalog.find(s => s.id === 'mend').description)), 'the skill book explains the proc');

      const dry = await probe(page, { resource: 0, mendFree: 0, skillCd: {} });
      check(dry.mend.disabled && dry.mend.empty && !dry.mend.free && !dry.mend.ready, `${kind}: an empty priest cannot Mend: ${JSON.stringify(dry.mend)}`);
      check(!dry.mend.label && dry.mend.glow === 'none', `${kind}: no highlight without the proc`);
      const lit = await probe(page, { resource: 0, mendFree: 3, skillCd: {} });
      check(!lit.mend.disabled && !lit.mend.empty && lit.mend.free && lit.mend.ready, `${kind}: a free Mend is usable with no mana: ${JSON.stringify(lit.mend)}`);
      check(lit.mend.label === 'Free!' && lit.mend.glow !== 'none', `${kind}: it is highlighted: ${JSON.stringify(lit.mend)}`);
      check(lit.smite.disabled && !lit.smite.free && !lit.smite.label, `${kind}: no other spell is free: ${JSON.stringify(lit.smite)}`);
      const cooling = await probe(page, { resource: 0, mendFree: 3, skillCd: { mend: 1.4 } });
      check(cooling.mend.disabled && cooling.mend.free && cooling.mend.label === '1.4', `${kind}: the cooldown still shows after a free cast`);
      if (kind === 'touch') {
        check(lit.mend.arcFree && !lit.mend.arcDisabled && lit.mend.arcLabel === 'Free!', `touch button is highlighted: ${JSON.stringify(lit.mend)}`);
        check(!dry.mend.arcFree && dry.mend.arcDisabled && !lit.smite.arcFree, 'touch buttons stay plain otherwise');
      }
      check(await page.evaluate(() => {
        const hero = Field.hero, saved = [hero.resource, hero.mendFree, hero.skillCd];
        Object.assign(hero, { resource: 0, mendFree: 0, skillCd: {} });
        const refused = !Field.useSkill('mend');
        hero.mendFree = 3;
        const cast = Field.useSkill('mend'), other = Field.useSkill('smite');
        [hero.resource, hero.mendFree, hero.skillCd] = saved;
        return refused && cast && !other;
      }), `${kind}: the controls send a free Mend and nothing else`);

      // The real thing: swing at a tough monster until the game readies a free Mend.
      await debug(page, { op: 'set_god_mode', on: true });
      await debug(page, { op: 'teleport', zone: 0, x: 250, y: 235 });
      await page.waitForFunction(() => Math.hypot(Field.hero.nx - 250, Field.hero.ny - 235) < 8);
      // An elite outlives any number of swings; weaker practice monsters died before the roll came up.
      await debug(page, { op: 'spawn_enemy', kind: 'cinderlord', x: await page.evaluate(() => Field.hero.nx + 1.2), y: await page.evaluate(() => Field.hero.ny), level: 99 });
      await page.waitForTimeout(600);
      await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'cinderlord' && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 4));
      await page.evaluate(() => Field.targetEnemy(Field.slimes.find(s => s.kind === 'cinderlord' && !s.dead).id));
      await page.waitForFunction(() => {
        if (!Field.hero.target) { const foe = Field.slimes.find(s => s.kind === 'cinderlord' && !s.dead); if (foe) Field.targetEnemy(foe.id); }
        return Field.hero.mendFree > 0 && document.querySelector('#skillbar-slots [data-skill="mend"]').classList.contains('free-cast');
      }, null, { timeout: 60000, polling: 50 });
      check(true, `${kind}: normal hits ready a free Mend`);
      if (kind === 'desktop') {
        // The touch layout hides the desktop bar behind its tray, so the picture of the bar is taken here.
        await page.locator('#skillbar').screenshot({ path: `${out}/mend-proc-bar-${width}x${height}.png` });
      } else await page.screenshot({ path: `${out}/mend-proc-touch-${width}x${height}.png` });
      await page.context().close();
    }
    const swedish = await player('MendSvenska', { characterClass: 'priest', lang: 'sv' });
    await swedish.waitForFunction(() => document.querySelector('#skillbar-slots [data-skill="mend"]'));
    const lit = await probe(swedish, { resource: 0, mendFree: 3, skillCd: {} });
    check(lit.mend.label === 'Gratis!' && lit.mend.arcLabel === 'Gratis!', `the label is Swedish: ${JSON.stringify(lit.mend)}`);
    await swedish.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
