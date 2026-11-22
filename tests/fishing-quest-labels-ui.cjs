// Run with TOUCH_SIZE=844x390 bash scripts/test-touch-bounded.sh tests/fishing-quest-labels-ui.cjs.
const {run, replace, debug} = require('./lib/touch.cjs');

const npcId = 'fisher_meadow_0';
const questId = 'fisher_meadow_0_1';

const suite = {
  name: 'fishing-quest-labels',
  mutate(page) {
    return replace(page, 'quests.js',
      'objectives: q.objectives.map(o => o.label == null && o.what ? { ...o, label: Locale.translate(o.what) } : o),',
      'objectives: q.objectives,');
  },
  async test({player, check}) {
    for (const [lang, name] of [['en','Pier Sprat'], ['sv','Bryggskarpsill']]) {
      const page = await player('Sprat' + lang, {lang, characterClass:'warrior'});
      const expected = `${name}: 1/5`;
      async function verify(locator, prefix, surface) {
        await locator.waitFor({state:'attached'});
        const text = (await locator.textContent()).trim();
        check(text === prefix + expected, `${lang} ${surface} displays ${JSON.stringify(prefix + expected)}, got ${JSON.stringify(text)}`);
      }

      await debug(page, {op:'quest', id:questId, action:'accept'});
      await debug(page, {op:'give_item', item:'fish_pier_sprat', quantity:1});
      await page.waitForFunction(id => Field.hero.quests.some(q => q.id === id && q.counts[0] === 1), questId);
      await verify(page.locator(`#quest-tracker [data-quest="${questId}"] .tracker-objective`), '• ', 'tracker');

      await page.evaluate(() => Quests.show());
      await page.locator(`#quest-list [data-quest="${questId}"]`).tap();
      await verify(page.locator('#quest-page .journal-objectives li'), '• ', 'journal');
      await page.evaluate(() => Quests.close());

      const {x,y} = await page.evaluate(id => WORLD_MAP.npcs.find(n => n.id === id), npcId);
      await debug(page, {op:'teleport', zone:0, x, y});
      await page.waitForFunction(({x,y}) => Math.hypot(Field.hero.x-x,Field.hero.y-y) < .5, {x,y});
      await page.evaluate(npc => Online.send({type:'interact',npc}), npcId);
      await page.locator(`#npc-quest-list [data-quest="${questId}"]`).tap();
      await verify(page.locator('#npc-quests .quest-objectives'), '', 'Fisher dialog');
      await page.context().close();
    }
  },
};

run([suite]).catch(error => { console.error(error); process.exitCode = 1; });
