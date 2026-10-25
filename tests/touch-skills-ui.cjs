const { run, replace, safeSpot, record, touch } = require('./lib/touch.cjs');
const suite = {
  name: 'touch-skills',
  mutate: page => replace(page, 'touch.js', 'saved[cls()] = next;', 'saved[cls()] = DEFAULTS[cls()];'),
  async test({ player, check, sleep, out, width, height }) {
    const page = await player('TouchSkills'); await safeSpot(page);
    check(await page.evaluate(() => !('obsolete' in Settings.layout)), 'old unknown layout keys are discarded');
    check(await page.evaluate(() => TouchControls.assignments().join(',') === 'fireball,arcaneward,blink,chainlightning'), 'old preferences load class defaults');
    await page.locator('#touch-actions [data-action="menu"]').click(); await page.locator('#p-settings').click(); await page.locator('#set-edit-ui').click();
    check(await page.locator('#touch-skill-editor').isVisible(), 'Edit UI exposes touch assignments');
    await page.locator('#touch-skill-editor select[data-arc="0"]').selectOption('arcaneward');
    check(await page.evaluate(() => Prefs.touchSkills.mage[0] === 'arcaneward'), 'assignment is stored');
    await page.locator('#layout-done').click(); await page.locator('#set-back').click(); await page.locator('#p-resume').click();
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click(); await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    await page.waitForFunction(() => document.querySelector('#touch-skills [data-arc="0"]').dataset.skill === 'arcaneward');
    check(await page.evaluate(() => TouchControls.assignments()[0] === 'arcaneward'), 'assignment survives reload');
    check(await page.evaluate(() => !TouchControls.assign(0, 'cleave') && !TouchControls.assign(6, 'arcaneward')), 'invalid class and slot assignments are refused');
    await safeSpot(page); await record(page);
    const stick = await page.locator('#touch-stick').boundingBox(), skill = await page.locator('#touch-skills [data-arc="0"]').boundingBox();
    const x = stick.x + stick.width / 2, y = stick.y + stick.height / 2, sx = skill.x + skill.width / 2, sy = skill.y + skill.height / 2;
    const send = await touch(page);
    await send('touchStart', [[1, x, y]]); await send('touchMove', [[1, x + 35, y]]); await sleep(200);
    await send('touchStart', [[1, x + 35, y], [2, sx, sy]]); await send('touchEnd', [[2, sx, sy]]);
    await page.waitForFunction(() => Field.hero.skillCd?.arcaneward > 0, null, { timeout: 5000 }).catch(async e => {
      console.error(await page.evaluate(() => ({ sent: touchSent, hero: { resource: Field.hero.resource, cd: Field.hero.skillCd, paused: !Field.canAct }, button: document.querySelector('#touch-skills [data-arc="0"]').outerHTML })));
      await page.screenshot({ path: `${out}/skills-failure-${width}x${height}.png` }); throw e;
    });
    check(await page.evaluate(() => touchSent.some(m => m.type === 'skill' && m.id === 'arcaneward')), 'second finger casts the assigned skill');
    await page.evaluate(() => { touchSent.length = 0; }); await sleep(250);
    check(await page.evaluate(() => touchSent.some(m => m.type === 'input' && m.dx && m.dy)), 'first finger continues moving after the skill tap');
    await send('touchEnd', []);
    for (const selector of ['#touch-skills button', '#touch-actions button', '#touch-quickuse button']) {
      const bad = await page.locator(selector).evaluateAll(nodes => nodes.filter(n => n.getClientRects().length).map(n => { const r = n.getBoundingClientRect(); return { text: n.textContent, w: r.width, h: r.height }; }).filter(r => r.w < 43.9 || r.h < 43.9));
      check(bad.length === 0, `${selector}: visible targets stay at least 44px: ${JSON.stringify(bad)}`);
    }
    await page.locator('#touch-quickuse > button').click();
    check(await page.locator('#skillbar').isVisible(), 'the other skills tray opens');
    await page.locator('#touch-quickuse > button').click();
    check(await page.locator('#skillbar').isHidden(), 'the tray closes');
    await page.screenshot({ path: `${out}/controls-${width}x${height}.png` });
    await page.context().close();
    for (const [name, expected] of Object.entries({ warrior: ['cleave', 'battlecry', 'shieldwall', 'charge'], assassin: ['shadowstep', 'throwingknives', 'evasion', 'lunge'], priest: ['mend', 'smite', 'wardoflight', 'holynova'], hunter: ['powershot', 'multishot', 'rollaway', 'huntersmark'] })) {
      const other = await player('Touch' + name, { characterClass: name });
      check(await other.evaluate(expected => TouchControls.assignments().join(',') === expected.join(','), expected), `${name} gets its own defaults`);
      check(await other.evaluate(() => TouchControls.assignments().every(id => Skillbar.catalog.some(s => s.id === id))), `${name} defaults name real class abilities`);
      await other.context().close();
    }
    const swedish = await player('TouchSvenska', { lang: 'sv' });
    check(await swedish.locator('#touch-actions [data-action="menu"]').textContent() === 'Meny', 'touch actions have Swedish labels');
    await swedish.locator('#touch-actions [data-action="menu"]').click(); await swedish.locator('#p-settings').click();
    check(await swedish.locator('label:has(#set-low-graphics)').textContent().then(s => s.includes('Låg grafik')), 'Low graphics is translated by hand');
    await swedish.context().close();
  },
};
module.exports = suite;
if (require.main === module) run([suite]).catch(e => { console.error(e); process.exitCode = 1; });
