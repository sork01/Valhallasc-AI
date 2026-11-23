const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

requireMemoryLimit();
const world = new TestWorld();
world.startLevel = 99;

(async () => {
  await world.start();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1120, height: 720 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => {
      window.AudioContext = window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click();
    await page.locator('#name').fill('WarpApproach');
    await page.locator('#go').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();

    for (const [from, to] of [[1, 9], [9, 1]]) {
      const gate = await page.evaluate(([from, to]) => Field._debug.zones[from].portals.find(p => p.to === to && p.walk), [from, to]);
      assert.ok(gate, `Live map has a walking warp from zone ${from} to zone ${to}`);
      const [dx, dy] = gate.walk;
      const x = gate.x - 6 * dx, y = gate.y - 6 * dy;
      await page.evaluate(({ zone, x, y }) => {
        Field.clearInput();
        Online.send({ type: 'stop' });
        Online.send({ type: 'debug', command: { op: 'teleport', zone, x, y } });
      }, { zone: from, x, y });
      await page.waitForFunction(({ zone, x, y }) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1, { zone: from, x, y });
      const paint = await page.evaluate(() => {
        const g = document.getElementById('fieldcv').getContext('2d');
        const { stroke, fillText } = g;
        const labels = [];
        let strips = 0;
        g.stroke = function (...args) {
          // The old warp approach was a 34 px tan stripe or a 2 px brown highlight.
          if ((this.lineWidth === 34 && this.strokeStyle === '#d8c395') ||
              (this.lineWidth === 2 && this.strokeStyle === '#a28d69')) strips++;
          return stroke.apply(this, args);
        };
        g.fillText = function (label, ...args) {
          labels.push(label);
          return fillText.call(this, label, ...args);
        };
        try { Field._debug.drawFrame(10); } finally { Object.assign(g, { stroke, fillText }); }
        return { strips, labels };
      });
      assert.equal(paint.strips, 0, `No brown warp approach strip from zone ${from} to zone ${to}`);
      const heading = from === 1 ? 'Dive into the depths' : 'Rising current';
      assert.ok(paint.labels.some(label => label.includes(heading)), `The warp still displays ${heading}`);
      assert.ok(paint.labels.some(label => label.includes(gate.name)), `The warp still displays ${gate.name}`);
      await page.evaluate(([dx, dy]) => Field.setTouchDirection(dx - dy, dx + dy), gate.walk);
      await page.waitForFunction(zone => Field.zone === zone, to, { timeout: 20000 });
      await page.evaluate(() => { Field.clearInput(); Online.send({ type: 'stop' }); });
      console.log(`Warp ${from} → ${to} renders without the strip and remains usable`);
    }
    assert.deepEqual(errors, [], 'No browser errors');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => world.stop());
