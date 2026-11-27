const { run } = require('./lib/touch.cjs');
const { execFileSync } = require('node:child_process');
run([{
  name: 'class-resources',
  async mutate(page) {
    const before = execFileSync('git', ['show', '28bb0184:client/field.js'], { encoding: 'utf8' });
    await page.route('**/field.js*', r => r.fulfill({ contentType: 'text/javascript', body: before }));
  },
  async test({ player, check }) {
    const mage = await player('ManaReturn', { characterClass: 'mage' });
    const tooltip = await mage.locator('#resource-bar').getAttribute('title');
    check(tooltip.includes('10%') && tooltip.includes('20% of maximum mana'), 'mana tooltip explains chance and maximum-mana return');
    const result = await mage.evaluate(() => {
      const saved = Prefs.floatingText;
      Prefs.set({ floatingText: { ...saved, healing: true } });
      const at = { type: 'event', actor: Online.id, x: Field.hero.x, y: Field.hero.y, fx: 1, fy: 0, value: 0, points: [], heal: 0 };
      const count = () => Field._debug.floaters.filter(f => f.text === '+20 mana').length;
      const before = count();
      Field._debug.event({ ...at, kind: 'skill', skill: 'arcaneward', mana: 20 });
      const after = count();
      Prefs.set({ floatingText: { ...saved, healing: false } });
      Field._debug.event({ ...at, kind: 'skill', skill: 'arcaneward', mana: 20 });
      const hidden = count();
      Prefs.set({ floatingText: { ...saved, healing: true } });
      Field._debug.event({ ...at, kind: 'skill', skill: 'arcaneward', mana: 0 });
      const zero = count();
      Field._debug.event({ ...at, kind: 'consume', mana: 20, resourceType: 'mana' });
      const potion = count();
      Prefs.set({ floatingText: saved });
      return { before, after, hidden, zero, potion };
    });
    check(result.after === result.before + 1, 'a skill mana return displays once');
    check(result.hidden === result.after && result.zero === result.after, 'healing/resources setting suppresses returns and zero returns stay quiet');
    check(result.potion === result.after + 1, 'existing potion mana feedback still displays once');
    await mage.close();
    const warrior = await player('HalfRage', { characterClass: 'warrior' });
    check((await warrior.locator('#resource-bar').getAttribute('title')).includes('1 per 4 damage dealt and 1 per 2 damage taken'), 'rage tooltip gives the new generation rates');
    await warrior.close();
    const swedish = await player('ManaSvenska', { characterClass: 'priest', lang: 'sv' });
    await swedish.waitForFunction(() => document.getElementById('resource-bar').title.includes('10% chans'));
    check((await swedish.locator('#resource-bar').getAttribute('title')).includes('20% av maximal mana'), 'Swedish priest tooltip describes the same rule');
    await swedish.close();
  },
}]);
