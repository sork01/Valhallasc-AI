// REBIRTH-ART, by looking: a second browser takes a close screenshot of a reborn player at each of the five tiers (title,
// name colour and ground aura as other players see them, once on foot and once on a coloured mount) and writes
// test-results/rebirth-look/tier-N.png plus one contact sheet. The assertions only check the files exist and differ;
// the judgement is the picture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld, root } = require('../scripts/testing/driver.cjs');

const SAVE = JSON.stringify({ lang: 'en', sound: false, char: null, draft: null });
const out = path.join(root, 'test-results/rebirth-look');
fs.mkdirSync(out, { recursive: true });
async function enter(browser, world, name) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  await page.addInitScript(save => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', save); }, SAVE);
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.id);
  return page;
}
const debug = (page, command) => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);

(async () => {
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const subject = await enter(browser, world, 'Phoenix');
    const watcher = await enter(browser, world, 'Onlooker');
    // The grass of the meadow, a few tiles from the start, away from the city and from enemies.
    await debug(watcher, { op: 'teleport', zone: 0, x: 40, y: 24 });
    await debug(subject, { op: 'teleport', zone: 0, x: 43.5, y: 24 });
    await watcher.waitForFunction(() => [...Field.remotePlayers.values()].some(p => p.look.name === 'Phoenix'), null, { timeout: 15000 });
    await debug(subject, { op: 'give_mount', mount: 'horse' });
    const shots = [];
    for (const mounted of [false, true]) {
      for (let tier = 1; tier <= 5; tier++) {
        const tiers = [0, 0, 0, 0, 0]; tiers[tier - 1] = 1;
        await debug(subject, { op: 'set_rebirth', tiers });
        await subject.waitForFunction(t => Field.hero.reborn?.tier === t, tier, { timeout: 10000 });
        if (tier >= 2) { await subject.evaluate(t => Online.send({ type: 'select_mount_tint', tier: t }), tier); await subject.waitForFunction(t => Field.hero.mountTint === t, tier, { timeout: 10000 }); }
        else await subject.evaluate(() => Online.send({ type: 'select_mount_tint', tier: 0 }));
        if (mounted !== await subject.evaluate(() => !!Field.hero.mounted)) { await subject.evaluate(() => document.activeElement?.blur?.()); await subject.keyboard.press('h'); await subject.waitForFunction(m => !!Field.hero.mounted === m, mounted, { timeout: 10000 }); }
        await watcher.waitForFunction(t => [...Field.remotePlayers.values()].some(p => p.look.name === 'Phoenix' && p.reborn?.tier === t), tier, { timeout: 10000 });
        await watcher.waitForTimeout(500);
        const at = await watcher.evaluate(() => { const p = [...Field.remotePlayers.values()].find(p => p.look.name === 'Phoenix'); const [x, y] = Field._debug.w2s(p.x, p.y); const canvas = document.getElementById('fieldcv'); const r = canvas.getBoundingClientRect(); return { x: r.left + x * r.width / 1600, y: r.top + y * r.height / 900, k: r.width / 1600 }; });
        const file = path.join(out, `tier-${tier}${mounted ? '-mounted' : ''}.png`);
        const w = Math.round(300 * at.k), h = Math.round(290 * at.k);
        await watcher.screenshot({ path: file, clip: { x: Math.max(0, at.x - w / 2), y: Math.max(0, at.y - h * .78), width: w, height: h } });
        shots.push(file);
      }
    }
    assert.equal(new Set(shots.map(f => fs.readFileSync(f).toString('base64'))).size, shots.length, 'ten different pictures');
    // One contact sheet, assembled in the page so no image library is needed.
    const sheet = await watcher.evaluate(async files => {
      const imgs = await Promise.all(files.map(src => new Promise(res => { const i = new Image(); i.onload = () => res(i); i.src = src; })));
      const w = Math.max(...imgs.map(i => i.width)), h = Math.max(...imgs.map(i => i.height));
      const c = document.createElement('canvas'); c.width = w * 5; c.height = h * 2; const g = c.getContext('2d');
      imgs.forEach((img, n) => g.drawImage(img, (n % 5) * w, Math.floor(n / 5) * h));
      return c.toDataURL('image/png');
    }, await Promise.all(shots.map(async f => 'data:image/png;base64,' + fs.readFileSync(f).toString('base64'))));
    fs.writeFileSync(path.join(out, 'sheet.png'), Buffer.from(sheet.split(',')[1], 'base64'));
    console.log('Rebirth look: ten screenshots and a contact sheet in test-results/rebirth-look');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
