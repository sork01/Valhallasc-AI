// Private art review: capture every Undervault chamber and compare its look with all other dungeons.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-undervault-visual', version: '1' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Vault Artist'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && window.VaultArt && window.Field, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await debug({ op: 'explore_all' });
  await debug({ op: 'set_level', level: 99 });
  const stage = async (zone, x, y, name) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    await page.waitForTimeout(450);
    const png = await page.evaluate(() => document.getElementById('fieldcv').toDataURL('image/png'));
    fs.writeFileSync(path.join(world.artifacts, name + '.png'), Buffer.from(png.split(',')[1], 'base64'));
  };
  for (const [name, x, y] of [
    ['stair-hall', 15, 111], ['barracks', 64, 106], ['gatewarden-court', 102, 104],
    ['ossuary', 96, 55], ['choir-chapel', 43, 53], ['cistern', 35, 13],
    ['colossus-forge', 82, 25], ['hollow-throne', 113, 28],
  ]) await stage(5, x, y, `vault-${name}`);
  const zones = await page.evaluate(() => WORLD_MAP.zones.map((z, i) => ({ i: i + 1, name: z.name, spawn: z.spawn, copies: z.copies, players: z.players })).filter(z => z.players || z.copies));
  assert.ok(zones.length >= 2 && zones.some(z => z.i === 5), 'the Undervault and other private dungeons are available for comparison');
  if (!process.env.VISUAL_VAULT_ONLY) for (const z of zones.filter(z => z.i !== 5))
    await stage(z.i, z.spawn.x, z.spawn.y, `compare-zone-${z.i}`);
  assert.deepEqual(errors, [], `browser errors: ${errors.join('; ')}`);
  console.log(`Undervault chambers${process.env.VISUAL_VAULT_ONLY ? '' : ` and ${zones.length - 1} other dungeons`} captured at ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) { try { await call('stop_world'); } catch (_) {} }
  await client.close();
});
