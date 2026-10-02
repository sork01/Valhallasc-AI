// Male and female bodies for every class, through the real creation screen and a real server. Runs on the stub
// sprites (tests/lib/playwright.cjs): this checks the choice, the saved look, which sprite class is loaded and what
// other players see. What the female art looks like is checked on the real atlases by tests/sprites-real.cjs.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-gender-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const CLASSES = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
const SPRITE = { warrior: 'WarriorSprite', mage: 'MageSprite', assassin: 'AssassinSprite', priest: 'PriestSprite', hunter: 'HunterSprite' };
const open = async (url, errors) => {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  return page;
};
const pressed = (page, id) => page.locator(id).getAttribute('aria-pressed');

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const a = await open(world.url, errors);

  // The creation screen: male is the default, the choice is a pair of buttons, and it survives a class change.
  check(await pressed(a, '#gender-male') === 'true' && await pressed(a, '#gender-female') === 'false', 'A new character is male by default');
  check(await a.locator('#custom .seg button').allTextContents().then(t => t.join() === 'Male,Female'), 'The creation screen offers Male and Female');
  for (const cls of CLASSES) {
    await a.locator('#cls-' + cls).click();
    check(await pressed(a, '#gender-male') === 'true', `${cls}: still male until chosen`);
    await a.locator('#gender-female').click();
    check(await pressed(a, '#gender-female') === 'true' && await pressed(a, '#gender-male') === 'false', `${cls}: Female can be chosen`);
    await a.waitForFunction(cls => !!valhalla.sprites[cls + 'F'] && !document.getElementById('go').disabled, cls, { timeout: 30000 });
    check(await a.evaluate(([cls, name]) => valhalla.sprites[cls + 'F'].constructor === window[name].Female && window[name].Female !== window[name], [cls, SPRITE[cls]]), `${cls}: the female sprite class is loaded, not the male one`);
    check(await a.evaluate(cls => valhalla.sprites[cls + 'F'].meta.gender === 'female' && Object.values(valhalla.sprites[cls + 'F'].meta.parts).some(p => p.png.includes('_f_')), cls), `${cls}: the female atlas metadata says female and names its own files`);
    check(await a.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).draft.gender === 'female'), `${cls}: the draft remembers Female`);
    await a.locator('#gender-male').click();
    check(await pressed(a, '#gender-male') === 'true' && await pressed(a, '#gender-female') === 'false', `${cls}: and back to Male`);
    check(await a.evaluate(([cls, name]) => !!valhalla.sprites[cls] && valhalla.sprites[cls].constructor === window[name] && valhalla.sprites[cls].meta.gender !== 'female', [cls, SPRITE[cls]]), `${cls}: the male sprite is the original class`);
  }
  // Gear lists and colours are the class's own for both bodies.
  await a.locator('#cls-hunter').click(); await a.locator('#gender-female').click();
  check(await a.locator('#create-hunterArmor option').allTextContents().then(t => t.length === 1 && t[0].includes('Jerkin')) && await a.locator('#custom .swatches .sw').count() === 10, 'The female Hunter has the same starter gear and the same six hair and four skin choices');

  // Play a female Hunter. The server stores the look, so it also survives a reload.
  await a.locator('#name').fill('Freya'); await a.locator('#go').click({ timeout: 30000 });
  await a.waitForFunction(() => Online.connected && !!Field.hunterSprites, null, { timeout: 60000 });
  check(await a.evaluate(() => Field.hero.look.gender === 'female' && Field.hero.look.class === 'hunter'), 'The server confirms a female Hunter');
  check(await a.evaluate(() => Field.hunterSprites.constructor === HunterSprite.Female), 'In the field she is drawn with the female Hunter sprite');
  await a.waitForFunction(() => document.getElementById('hud-portrait').style.backgroundImage.includes('data:image'), null, { timeout: 30000 });
  check(await a.evaluate(() => valhalla.sprites.hunterF.portrait().length > 100 && document.getElementById('hud-portrait').style.backgroundImage.includes(valhalla.sprites.hunterF.portrait().slice(0, 60))), 'The HUD portrait comes from the female sprite');

  // A male Mage in the same world sees her as female, and she sees him as male.
  const b = await open(world.url, errors);
  await b.locator('#cls-mage').click(); await b.locator('#name').fill('Ulfar'); await b.locator('#go').click({ timeout: 30000 });
  await b.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  check(await b.evaluate(() => Field.hero.look.gender === 'male' && Field.mageSprites.constructor === MageSprite), 'A character made without touching the choice is a male Mage');
  await b.waitForFunction(() => Field.remotePlayers.some(p => p.look.name === 'Freya' && p.sprite), null, { timeout: 30000 });
  check(await b.evaluate(() => { const p = Field.remotePlayers.find(p => p.look.name === 'Freya'); return p.look.gender === 'female' && p.sprite.constructor === HunterSprite.Female; }), 'The Mage sees Freya as a female Hunter');
  await a.waitForFunction(() => Field.remotePlayers.some(p => p.look.name === 'Ulfar' && p.sprite), null, { timeout: 30000 });
  check(await a.evaluate(() => { const p = Field.remotePlayers.find(p => p.look.name === 'Ulfar'); return p.look.gender === 'male' && p.sprite.constructor === MageSprite; }), 'Freya sees Ulfar as a male Mage');
  await b.close();

  await a.reload(); await a.locator('#start').click(); await a.locator('#login-guest').click();
  await a.waitForFunction(() => Online.connected && !!Field.hunterSprites, null, { timeout: 60000 });
  check(await a.evaluate(() => Field.hero.look.gender === 'female' && Field.hunterSprites.constructor === HunterSprite.Female), 'After a reload she is still a female Hunter');

  // A look saved before genders existed has no field and loads as male.
  check(await a.evaluate(() => { const old = { class: 'mage', name: 'Old' }; return (window.MageSprite.variant(old) === window.MageSprite) && (window.MageSprite.variant({ ...old, gender: 'female' }) === window.MageSprite.Female) && (window.MageSprite.variant({ ...old, gender: 'other' }) === window.MageSprite); }), 'Only the exact word "female" picks the female sprite');
  check(errors.length === 0, 'No page errors: ' + errors.join('; '));
  console.log(`gender ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
