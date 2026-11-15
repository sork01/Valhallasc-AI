// BOSSMECH-NIGHT: does a boss telegraph stay readable at night? A real client in a private world, the Stormgate-style Static rods
// (blue ground telegraphs, the same table as bossmech-static-ui) drawn on open ground in Greenmeadow. The world clock is set through
// the debug op set_time (frozen) to noon and then to night; at each time the rod's pixels are compared with the ground beside it
// (tint = blue minus the mean of red and green, luminance = Rec.601). Numbers are printed and written to the artifacts folder.
// The check fails when the night telegraph is no longer clearly tinted (MIN_TINT, default 5 as in bossmech-static-ui).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debug = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debug].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const minTint = Number(process.env.MIN_TINT || 5);
const base = { x: 250, y: 235 };
const rods = [[base.x + 5, base.y - 4], [base.x + 5, base.y + 4], [base.x - 5, base.y - 4], [base.x - 5, base.y + 4]];
const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bossmech-night-'));
const table = path.join(dir, 'boss-mechanics.txt');
fs.writeFileSync(table, JSON.stringify({
  green: { mechanics: [{ name: 'Static', block: 'static', limit: 12, warn_at: 2, per_hit: 1, r: 5, rods, rod_r: 1.8, immune: 8, dark: 12 }] },
}));
const client = new Client({ name: 'valhallasc-bossmech-night-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', VALHALLA_BOSSMECH_FILE: table, ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Nightwatch'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const send = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(300));
  await send({ op: 'set_god_mode', enabled: true });
  await send({ op: 'teleport', zone: 0, x: base.x, y: base.y });
  await page.waitForFunction(() => Math.hypot(Field.hero.x - 250, Field.hero.y - 235) < 8, null, { timeout: 15000 });
  const h = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await send({ op: 'spawn_enemy', kind: 'green', x: h.x + 2, y: h.y, level: 99 });
  await page.waitForFunction(() => BossMech.active, null, { timeout: 15000 });
  const first = await page.evaluate(() => JSON.parse(JSON.stringify(BossMech.fights[0] || null)));
  const rod = first.tele.find(t => t.rod).shapes[0];

  // Samples a 24 x 12 px patch on the rod and an equal patch 11 tiles south of the boss (on screen, clear of the rods): the rod's contrast is its tint and
  // luminance minus the control's, so the darkness veil acts on both alike and only the telegraph remains in the difference.
  const sample = () => page.evaluate(({ x, y, cx, cy }) => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    const patch = (wx, wy) => {
      const [sx, sy] = Field._debug.w2s(wx, wy);
      const d = g.getImageData(Math.round((sx - 12) * k), Math.round((sy - 6) * k), Math.round(24 * k), Math.round(12 * k)).data;
      let tint = 0, lum = 0; const n = d.length / 4;
      for (let i = 0; i < d.length; i += 4) { tint += d[i + 2] - (d[i] + d[i + 1]) / 2; lum += .299 * d[i] + .587 * d[i + 1] + .114 * d[i + 2]; }
      return { tint: tint / n, lum: lum / n };
    };
    return { rod: patch(x, y), control: patch(cx, cy), hour: DayNight.hour };
  }, { x: rod.x, y: rod.y, cx: 250, cy: 246 });

  const results = {};
  for (const [label, hour] of [['noon', 12], ['night', 1]]) {
    await send({ op: 'set_time', hour, freeze: true });
    // The clock arrives in snapshots: wait for the client to show the frozen hour, then let a frame paint.
    await page.waitForFunction(h => Math.abs(DayNight.hour - h) < 0.5 || Math.abs(Math.abs(DayNight.hour - h) - 24) < 0.5, hour, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(900);
    const s = await sample();
    results[label] = {
      clientHour: Number(s.hour.toFixed(2)),
      rodTint: +s.rod.tint.toFixed(2), controlTint: +s.control.tint.toFixed(2), tintContrast: +(s.rod.tint - s.control.tint).toFixed(2),
      rodLum: +s.rod.lum.toFixed(1), controlLum: +s.control.lum.toFixed(1), lumContrast: +(s.rod.lum - s.control.lum).toFixed(1),
    };
    await page.screenshot({ path: path.join(world.artifacts, `bossmech-night-${label}.png`) });
  }
  console.log(JSON.stringify(results, null, 1));
  fs.writeFileSync(path.join(world.artifacts, 'bossmech-night-numbers.json'), JSON.stringify(results, null, 1));
  check(results.noon.tintContrast > minTint, `noon: the rod is tinted ${results.noon.tintContrast} above the control patch`);
  check(results.night.tintContrast > minTint, `night: the rod is still tinted ${results.night.tintContrast} above the control patch (MIN_TINT ${minTint})`);
  assert.deepEqual(errors, []);
  console.log(`bossmech-night-ui: ${checks} checks passed; artifacts in ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
