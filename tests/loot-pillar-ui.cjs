// Private browser check of the same canvas painter used for live ground drops.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-loot-pillar-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: getDefaultEnvironment() }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('PillarTester'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });

  const samples = await page.evaluate(() => {
    const rarities = ['uncommon', 'rare', 'epic', 'legendary'];
    const common = WORLD_ITEMS.find(i => i.rarity === 'common' && i.kind !== 'material');
    const make = (rarity, time, gear = true) => {
      const canvas = document.createElement('canvas'); canvas.width = 130; canvas.height = 190;
      const g = canvas.getContext('2d');
      const drop = { id: 731, item: common.id, gear: gear ? { rarity } : null, x: 0, y: 0 };
      Field._debug.drawLootPillar(g, drop, gear ? common : WORLD_ITEMS.find(i => i.rarity === rarity), 53, 182, time);
      return Array.from(g.getImageData(0, 0, 130, 190).data);
    };
    const colors = data => {
      let pixels = 0, top = 190, brightness = 0, red = 0, green = 0, blue = 0;
      for (let p = 0; p < data.length; p += 4) {
        const a = data[p + 3]; if (a < 15) continue;
        pixels++; top = Math.min(top, Math.floor(p / 4 / 130));
        red += data[p] * a; green += data[p + 1] * a; blue += data[p + 2] * a;
        brightness += a;
      }
      return { pixels, top, brightness, red, green, blue };
    };
    const out = rarities.map(rarity => {
      const first = make(rarity, 1.2), second = make(rarity, 2.1);
      return { rarity, first: colors(first), moved: first.some((value, i) => value !== second[i]) };
    });
    const catalog = colors(make('epic', 1.2, false));
    const noItem = (() => {
      const canvas = document.createElement('canvas'); canvas.width = 130; canvas.height = 190;
      Field._debug.drawLootPillar(canvas.getContext('2d'), { id: 1, item: null, gear: { rarity: 'legendary' } }, common, 53, 182, 1);
      return colors(Array.from(canvas.getContext('2d').getImageData(0, 0, 130, 190).data));
    })();
    const ordinary = (() => {
      const canvas = document.createElement('canvas'); canvas.width = 130; canvas.height = 190;
      Field._debug.drawLootPillar(canvas.getContext('2d'), { id: 2, item: common.id }, common, 53, 182, 1);
      return colors(Array.from(canvas.getContext('2d').getImageData(0, 0, 130, 190).data));
    })();
    const canvas = document.createElement('canvas'); canvas.width = 520; canvas.height = 215;
    const g = canvas.getContext('2d'); g.fillStyle = '#162338'; g.fillRect(0, 0, 520, 215);
    rarities.forEach((rarity, i) => {
      Field._debug.drawLootPillar(g, { id: i + 1, item: common.id, gear: { rarity } }, common, i * 130 + 53, 183, 2);
      g.fillStyle = '#fff'; g.font = '14px sans-serif'; g.fillText(rarity, i * 130 + 30, 205);
    });
    canvas.id = 'pillar-preview'; canvas.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;width:520px;height:215px';
    document.body.append(canvas);
    return { out, catalog, noItem, ordinary };
  });
  for (const { rarity, first, moved } of samples.out) {
    assert.ok(first.pixels > 70, `${rarity} emits visible particles`);
    assert.ok(first.top < 140, `${rarity} has a tall pillar`);
    assert.ok(moved, `${rarity} particles animate`);
    if (rarity === 'uncommon') assert.ok(first.green > first.red && first.green > first.blue, 'green pillar');
    if (rarity === 'rare') assert.ok(first.blue > first.red && first.blue > first.green, 'blue pillar');
    if (rarity === 'epic') assert.ok(first.red > first.green && first.blue > first.green, 'purple pillar');
    if (rarity === 'legendary') assert.ok(first.red > first.green && first.green > first.blue, 'orange pillar');
  }
  assert.ok(samples.out.every((v, i, a) => !i || v.first.top < a[i - 1].first.top), 'higher rarity pillars rise further');
  assert.ok(samples.catalog.pixels > 70, 'catalog rarity works without a rolled copy');
  assert.equal(samples.noItem.pixels, 0, 'gold does not get an item pillar');
  assert.equal(samples.ordinary.pixels, 0, 'common items do not get a pillar');
  await page.locator('#pillar-preview').screenshot({ path: path.join(world.artifacts, 'loot-pillars.png') });
  assert.deepEqual(errors, []);
  console.log('loot-pillar-ui: four animated rarity pillars, effective rarity, and gold filtering passed');
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
