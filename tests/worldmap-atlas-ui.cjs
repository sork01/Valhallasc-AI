// Focused visual and fog check for the connected world atlas.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-atlas-ui', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('AtlasUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  await page.evaluate(() => document.activeElement?.blur?.()); await page.keyboard.press('m');
  await page.waitForFunction(() => WorldMap.open && WorldMap.view === 'world');
  const result = await page.evaluate(() => {
    const zones = Field._debug.zones;
    const surface = zones.filter(z => !z.sealedTemplate && z.theme !== 'arena' && !z.players).length;
    const atlas = document.querySelector('.wm-atlas');
    const tiles = [...document.querySelectorAll('.wm-tile')];
    const hidden = tiles.filter(t => t.dataset.fog === 'full');
    return {
      surface, islands: atlas.querySelectorAll('.wm-island').length,
      bridges: atlas.querySelectorAll('.wm-land-links g').length,
      visibleBridges: [...atlas.querySelectorAll('.wm-land-links g')].filter(g => getComputedStyle(g).visibility === 'visible').length,
      hiddenTerrain: hidden.every(t => getComputedStyle(t.querySelector('canvas:not(.wm-tile-fog)')).visibility === 'hidden'),
      unknownLabels: hidden.every(t => t.querySelector('b').dataset.short === '?'),
      hiddenRoads: [...document.querySelectorAll('.wm-roads [data-road]')].every(r => r.getAttribute('visibility') === 'hidden'),
      arenaHidden: !document.querySelector(`.wm-tile[data-zone="${zones.length - 1}"]`),
    };
  });
  assert.equal(result.islands, result.surface, 'One illustrated land region per surface zone');
  assert.ok(result.bridges > 15 && result.visibleBridges === result.bridges, 'Geography stays connected before routes are charted');
  assert.ok(result.hiddenTerrain && result.unknownLabels && result.hiddenRoads, 'Fog hides unvisited ground and portal routes');
  assert.ok(result.arenaHidden, 'The private arena has no public map region');
  assert.deepEqual(errors, []);
  await page.screenshot({ path: path.join(world.artifacts, 'connected-atlas.png') });
  await page.evaluate(() => Online.send({ type: 'debug', ref: 812, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.[28] === 511, null, { timeout: 10000 });
  await page.waitForFunction(() => document.querySelector('.wm-tile[data-zone="28"]')?.dataset.fog === 'partial', null, { timeout: 10000 });
  await page.screenshot({ path: path.join(world.artifacts, 'charted-atlas.png') });
  console.log('5 connected-atlas checks passed; screenshots: ' + world.artifacts);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
