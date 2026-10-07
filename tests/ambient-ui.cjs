// Real browser and private Rust server: temporary adventurers look and move like remote players.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld, root } = require('../scripts/testing/driver.cjs');

const names = new Set(fs.readFileSync(path.join(root, 'world/ambient_names.txt'), 'utf8').trim().split('\n'));
const world = new TestWorld();
world.ambientPlayers = true;
let browser, page, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };

(async () => {
  const started = await world.start();
  browser = await chromium.launch({ headless: true });
  page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(started.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('AmbientUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.remotePlayers.length >= 3 && Field.remotePlayers.every(p => p.sprite), null, { timeout: 60000 });
  const first = await page.evaluate(() => Field.remotePlayers.map(p => ({ id: p.id, name: p.look.name, class: p.look.class, level: p.level, x: p.x, y: p.y, sprite: !!p.sprite })));
  check(first.length >= 3 && first.length <= 6, 'An occupied shared zone has three to six adventurers');
  check(first.every(p => names.has(p.name) && p.level >= 1 && p.level <= 5 && p.sprite), 'Names, map levels and class sprites are present');
  check(new Set(first.map(p => p.name)).size === first.length, 'Names do not repeat within the zone');
  check(first.every(p => p.x < 24 || p.x > 48 || p.y < 72 || p.y > 94), 'Field arrivals do not appear inside the Alderhaven quest hub');
  const health = await (await fetch(started.url + 'health')).json();
  check(health.online === 1 && health.visibleOnline === first.length + 1, 'The real connection count stays separate from visible players');
  await page.keyboard.press('o');
  await page.locator('#social-panel').waitFor({ state: 'visible' });
  await page.locator('#social-tab-online').click();
  await page.waitForFunction(id => !!document.querySelector(`#social-panel [data-player="${id}"]`), first[0].id);
  check(await page.locator(`#social-panel [data-player="${first[0].id}"]`).isVisible(), 'Adventurers appear in the online roster');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(9000);
  const later = await page.evaluate(() => Field.remotePlayers.map(p => ({ id: p.id, x: p.x, y: p.y })));
  check(first.some(before => later.some(after => after.id === before.id && Math.hypot(after.x - before.x, after.y - before.y) > .5)), 'At least one adventurer walks through the world');
  check(errors.length === 0, 'The browser reports no JavaScript errors');
  await page.screenshot({ path: path.join(started.artifacts, 'ambient-adventurers.png') });
  console.log(`${checks} ambient browser checks passed; screenshot: ${started.artifacts}/ambient-adventurers.png`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await page?.context().close().catch(() => {});
  await browser?.close().catch(() => {});
  await world.stop().catch(() => {});
});
