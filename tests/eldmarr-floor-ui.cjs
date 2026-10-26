// Eldmarr's actual floor warning must remain visible through his real sprite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium, STUB } = require('./lib/playwright.cjs');
const world = new TestWorld();
let browser, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const results = [];

(async () => {
  assert.ok(!STUB, 'Run with REAL_SPRITES=1: the boss must actually cover the warning');
  world.godMode = true; world.levelSpread = 0; world.startLevel = 99;
  await world.start();
  const viewports = process.env.MUTATE ? [{ width: 1440, height: 900 }] : [{ width: 1440, height: 900 }, { width: 844, height: 390 }];
  for (const viewport of viewports) {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport, reducedMotion: 'reduce', hasTouch: viewport.width < 1000 });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill('Floor Observer ' + viewport.width); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero && Field.cathedralSprites?.img.cf_eldmarr?.complete, null, { timeout: 60000 });
    if (process.env.MUTATE) await page.evaluate(() => { BossMech.drawForeground = () => {}; });
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 46, x: 109, y: 41 } }));
    await page.waitForFunction(() => Field.zone === 46 && BossMech.fights.some(f => f.throne && f.tele.some(t => t.lava === false)), null, { timeout: 30000 });
    for (const lava of [false, true]) {
      await page.waitForFunction(lava => BossMech.fights.some(f => f.throne && f.tele.some(t => t.lava === lava)), lava, { timeout: 15000 });
      const proof = await page.evaluate(({ lava }) => {
        const fight = BossMech.fights.find(f => f.throne), tele = fight.tele.find(t => t.lava === lava), shape = tele.shapes[0];
        const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), atlas = Field.cathedralSprites.img.cf_eldmarr;
        const foreground = BossMech.drawForeground, hud = BossMech.drawHud, drawImage = g.drawImage;
        const t = performance.now() / 1000, order = [];
        const [sx, sy] = Field._debug.w2s((shape.x0 + shape.x1) / 2, (shape.y0 + shape.y1) / 2);
        let skipBoss = false;
        g.drawImage = function (img, ...args) {
          if (img === atlas) { order.push('boss'); if (skipBoss) return; }
          return drawImage.call(this, img, ...args);
        };
        BossMech.drawHud = () => {};
        const pixels = () => {
          Field._debug.drawFrame(t);
          const p = g.getTransform().transformPoint(new DOMPoint(sx, sy));
          return g.getImageData(Math.round(p.x) - 22, Math.round(p.y) - 16, 44, 32).data;
        };
        const changed = (a, b) => {
          let count = 0;
          for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]) > 35) count++;
          return count;
        };
        try {
          BossMech.drawForeground = () => {};
          const covered = pixels(); skipBoss = true; const uncovered = pixels(); skipBoss = false;
          order.length = 0;
          BossMech.drawForeground = function (...args) { order.push('warning'); return foreground.apply(this, args); };
          const visible = pixels();
          const actorBeforeWarning = order.lastIndexOf('boss') >= 0 && order.lastIndexOf('warning') > order.lastIndexOf('boss');
          Prefs.set({ lowGraphics: true });
          const low = pixels(); BossMech.drawForeground = () => {}; const lowCovered = pixels();
          Prefs.set({ lowGraphics: false });
          return { lava, shape, coveredPixels: changed(covered, uncovered), warningPixels: changed(covered, visible), lowGraphicsPixels: changed(low, lowCovered), actorBeforeWarning, total: tele.total };
        } finally {
          g.drawImage = drawImage; BossMech.drawForeground = foreground; BossMech.drawHud = hud; Field._debug.drawFrame(t);
        }
      }, { lava });
      check(proof.coveredPixels > 80, 'The real boss covers this floor cell: ' + JSON.stringify(proof));
      check(proof.actorBeforeWarning, 'The warning is drawn after the boss');
      check(proof.warningPixels > 150, 'The floor cue remains visible over the boss: ' + JSON.stringify(proof));
      check(proof.lowGraphicsPixels > 150, 'Low graphics preserves the foreground cue');
      check(proof.total === 8, 'The authoritative eight-second warning remains unchanged');
      await page.screenshot({ path: path.join(world.runDir, `eldmarr-floor-${viewport.width}-${lava ? 'lava' : 'warning'}.png`) });
      results.push({ viewport, ...proof });
    }
    check(errors.length === 0, JSON.stringify(errors));
    await browser.close(); browser = null;
  }
  fs.writeFileSync(path.join(world.runDir, 'eldmarr-floor-ui.json'), JSON.stringify({ checks, results }, null, 2));
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.runDir }));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
