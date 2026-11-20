// Run only on an approved browser host, using the bounded runner. Native warning stays enabled.
process.env.TEST_GUEST_WARNING = '1';
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld();
let browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function guest(page, accept = true) {
  let text;
  page.once('dialog', async dialog => { text = dialog.message(); await (accept ? dialog.accept() : dialog.dismiss()); });
  await page.locator('#login-guest').click();
  check(text && /progress|framsteg/.test(text), 'guest warning explains the progression risk');
  return text;
}
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  await page.addInitScript(() => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
  });
  await page.goto(world.url); await page.locator('#start').click();
  await guest(page, false);
  check(await page.locator('#scene-login').isVisible() && !await page.evaluate(() => Online.connected), 'Cancel keeps sign-in open without joining');
  await guest(page);
  check(await page.locator('#scene-create').isVisible(), 'fresh guest chooses job and appearance');
  await page.locator('#cls-mage').click(); await page.locator('#gender-female').click(); await page.locator('#name').fill('GuestMage'); await page.locator('#go').click();
  await page.waitForFunction(() => Online.connected && Field.hero?.look?.class === 'mage');
  const firstId = await page.evaluate(() => Online.id);
  check(await page.evaluate(() => Field.hero.look.gender === 'female'), 'the chosen job and body reach the authoritative character');
  await page.reload(); await page.locator('#start').click(); await guest(page);
  check(await page.locator('#scene-chars').isVisible() && await page.locator('.char-play').count() === 1, 'returning guest sees the saved character');
  await page.locator('#chars-new').click(); await page.locator('#cls-hunter').click(); await page.locator('#name').fill('GuestHunter'); await page.locator('#go').click();
  await page.waitForFunction(() => Online.connected && Field.hero?.look?.class === 'hunter');
  check(await page.evaluate(id => Online.id !== id, firstId), 'New character creates a separate job without replacing the first');
  await page.reload(); await page.locator('#start').click(); await guest(page);
  check(await page.locator('.char-play').count() === 2 && await page.locator('.char-del').count() === 0, 'guest choices retain both access keys without account deletion controls');
  await page.locator('.char-play').filter({ hasText: 'GuestMage' }).click();
  await page.waitForFunction(id => Online.connected && Online.id === id && Field.hero.look.class === 'mage', firstId);
  check(true, 'choosing the earlier guest restores its original server identity');
  await page.evaluate(() => { const key = 'valhallasc.save.v1', save = JSON.parse(localStorage.getItem(key)); save.lang = 'sv'; localStorage.setItem(key, JSON.stringify(save)); });
  await page.reload(); await page.locator('#start').click();
  check((await guest(page, false)).startsWith('Gästframsteg'), 'Swedish guest warning is localized');
  console.log(`Guest character choice: ${checks} native dialog/job/picker/persistence browser checks passed.`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
