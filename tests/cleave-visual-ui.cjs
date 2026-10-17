// Capture the live Cleave skill in a private real-sprite browser world.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-cleave-visual', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 4, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('CleaveReview');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 4 && !!Field.warriorSprites, null, { timeout: 60000 });
  assert.equal(await page.locator('#skillbar-slots [data-slot="2"]').getAttribute('data-skill'), 'cleave');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 100 } }));
  await page.waitForFunction(() => Field.hero.resource >= 10);

  const shot = await page.evaluate(() => new Promise((resolve, reject) => {
    const deadline = performance.now() + 5000;
    function sample() {
      const effect = Field._debug.effects.find(e => e.kind === 'skCleave');
      if (effect && effect.t >= .19 && effect.t <= .32) {
        resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'),
          reach: effect.r, arc: effect.arc, age: effect.t });
        return;
      }
      if (performance.now() > deadline) { reject(new Error('Server Cleave effect did not reach the capture window')); return; }
      requestAnimationFrame(sample);
    }
    requestAnimationFrame(sample);
    Online.send({ type: 'skill', id: 'cleave', fx: 1, fy: 0 });
  }));
  assert.equal(shot.reach, 1.9, 'Cleave shows the catalog reach');
  assert.ok(shot.arc > 3.5 && shot.arc < 3.6, 'Cleave shows the catalog cone angle');
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  const output = path.join(world.artifacts, 'cleave-live-effect.png');
  fs.writeFileSync(output, Buffer.from(shot.image.split(',')[1], 'base64'));
  console.log(`Cleave live cast, reach ${shot.reach}, arc ${shot.arc.toFixed(2)}, frame ${shot.age.toFixed(2)} s: ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
