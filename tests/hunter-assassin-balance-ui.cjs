const { run } = require('./lib/touch.cjs');
const { execFileSync } = require('node:child_process');
run([{
  name: 'hunter-assassin-balance',
  async mutate(page) {
    const before = execFileSync('git', ['show', '995be12a:client/game.js'], { encoding: 'utf8' });
    await page.route('**/game.js*', r => r.fulfill({ contentType: 'text/javascript', body: before }));
  },
  async test({ player, check }) {
    for (const lang of ['en', 'sv']) for (const characterClass of ['hunter', 'assassin']) {
      const page = await player(`${characterClass}${lang}`, { characterClass, lang });
      const rate = characterClass === 'hunter' ? 15 : 10;
      const expected = lang === 'sv' ? `återhämtar ${rate} per sekund` : `regenerates ${rate} per second`;
      await page.waitForFunction(text => document.getElementById('resource-bar').title.includes(text), expected);
      check((await page.locator('#resource-bar').getAttribute('title')).includes(expected), `${lang} ${characterClass}: ${rate} energy per second`);
      await page.close();
    }
  },
}]);
