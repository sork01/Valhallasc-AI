// Real rear enemy hits in a private world; one victim and one nearby observer.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const world = new TestWorld();
world.startLevel = 99; world.godMode = false; world.levelSpread = 0;
let browser, checks = 0;
const errors = [];
const check = (value, text) => { assert.ok(value, text); checks++; };
const send = (page, packet) => page.evaluate(packet => Online.send(packet), packet);
const debug = (page, command) => send(page, { type: 'debug', command });
async function pixels(page, id, suppress) {
  return page.evaluate(({ id, suppress }) => {
    const actor = id === Online.id ? Field.hero : Field.remotePlayers.find(p => p.id === id);
    const saved = { daze: actor.daze, stunHitAt: actor.stunHitAt };
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    const [x, y] = Field._debug.w2s(actor.x, actor.y);
    const grab = () => g.getImageData(...[x - 65, y - 180, 130, 75].map(n => Math.round(n * k))).data;
    Field._debug.drawFrame(0); const before = grab();
    if (suppress) { actor.daze = 0; actor.stunHitAt = -99; }
    Field._debug.drawFrame(0); const after = grab();
    Object.assign(actor, saved); Field._debug.drawFrame(0);
    let changed = 0;
    for (let i = 0; i < before.length; i += 4)
      if (Math.abs(before[i] - after[i]) + Math.abs(before[i+1] - after[i+1]) + Math.abs(before[i+2] - after[i+2]) > 25) changed++;
    return changed;
  }, { id, suppress });
}
(async () => {
  const info = await world.start();
  browser = await chromium.launch({ headless: true });
  async function player(name, x) {
    const page = await browser.newPage({ viewport: { width: 1024, height: 768 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    if (process.env.DAZE_CLIENT_DIR) {
      for (const name of ['field.js', 'game.js', 'sv-data.js'])
        await page.route(`**/${name}`, route => route.fulfill({ path: path.join(process.env.DAZE_CLIENT_DIR, name), contentType: 'text/javascript' }));
    }
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
    await page.goto(info.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click(); await page.locator('#name').fill(name); await page.locator('#go').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
    await debug(page, { op: 'teleport', zone: 0, x, y: 25 });
    await page.waitForFunction(x => Math.abs(Field.hero.x - x) < .2, x);
    return page;
  }
  const victim = await player('DazeVictim', 25), witness = await player('DazeWitness', 30);
  const id = await victim.evaluate(() => Online.id);
  await send(victim, { type: 'attack', fx: 1, fy: 0 });
  await debug(victim, { op: 'spawn_enemy', kind: 'green', x: 23.5, y: 25, level: 1 });
  await victim.waitForFunction(() => Field.hero.daze > 2, null, { timeout: 30000 });
  await debug(victim, { op: 'set_god_mode', enabled: true });
  check(await victim.evaluate(() => !Field.hero.stun), 'daze is separate from stun');
  await victim.waitForFunction(() => document.querySelector('[data-buff="daze"]'));
  const badge = victim.locator('[data-buff="daze"]');
  check(await badge.isVisible(), 'Dazed status has a countdown');
  check((await badge.getAttribute('title')).includes('50%'), 'tooltip explains half speed');
  check(await pixels(victim, id, true) > 50, 'victim has visible overhead daze stars');
  await witness.waitForFunction(id => Field.remotePlayers.find(p => p.id === id)?.daze > 0, id);
  check(await pixels(witness, id, true) > 50, 'nearby player sees the daze stars');
  check(await witness.locator('[data-buff="daze"]').count() === 0, 'observer does not get victim status');
  check(await pixels(victim, id, false) === 0, 'paired rendering control has no changed pixels');
  await victim.screenshot({ path: path.join(world.runDir, 'dazed-player.png') });
  check(await victim.evaluate(() => Locale.translate('Dazed')) === 'Dazed', 'English status stays English');
  await victim.waitForFunction(() => !Field.hero.daze, null, { timeout: 15000 });
  await victim.waitForFunction(() => !document.querySelector('[data-buff="daze"]'));
  check(true, 'countdown and status disappear on recovery');
  check(await pixels(victim, id, true) === 0, 'no daze stars after expiry');
  await victim.close(); await witness.close();
  const sv = await browser.newPage({ viewport: { width: 800, height: 600 } });
  if (process.env.DAZE_CLIENT_DIR)
    await sv.route('**/sv-data.js', route => route.fulfill({ path: path.join(process.env.DAZE_CLIENT_DIR, 'sv-data.js'), contentType: 'text/javascript' }));
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(info.url);
  assert.deepEqual(await sv.evaluate(() => ['Dazed', 'Movement speed is reduced by 50%.'].map(Locale.translate)),
    ['Omtöcknad', 'Rörelsehastigheten är sänkt med 50%.']); checks += 2;
  assert.deepEqual(errors, [], 'no browser errors');
  console.log(`daze-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  await world.stop();
});
