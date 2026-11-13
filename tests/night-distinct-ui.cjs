// Focused check for NIGHT-LOOK-DISTINCT: deep, theme-aware night darkness and lamp contrast
// while preserving actor/UI readability, Prefs.night scaling, enclosed zones, and render budget.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-night-distinct-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const reply = await client.callTool({ name, arguments: args });
  assert.ok(!reply.isError, `${name}: ${JSON.stringify(reply.content)}`);
  return reply.structuredContent;
}
const lum = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
const canvasBrightness = page => page.evaluate(() => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * .15), Math.floor(h * .15), Math.floor(w * .7), Math.floor(h * .7)).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
  return sum / (d.length / 4);
});
const taskSeconds = async cdp => (await cdp.send('Performance.getMetrics')).metrics.find(m => m.name === 'TaskDuration').value;

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE === 'flat') {
    // Regression guard: reverting to the old subtle 0.27 wash must fail the distinct-night thresholds.
    await page.route('**/daynight.js', r => {
      const body = fs.readFileSync(path.join(root, 'client/daynight.js'), 'utf8')
        .replace(/const mulAlpha = [^;]+;/, '')
        .replace(/\.56 \* nightDepth/g, '0')
        .replace(/\.44 \* nightDepth/g, '.27 * nightDepth')
        .replace(/\.24 \* nightDepth/g, '0');
      r.fulfill({ contentType: 'application/javascript', body });
    });
  }
  await page.addInitScript(() => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Nightwatch'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!window.DayNight && DayNight.hour >= 0 && Field.hero?.hp > 0, null, { timeout: 60000 });

  // 1. Canvas unit checks across themes, Prefs.night, lowGraphics, and lamp light contrast.
  const unit = await page.evaluate(() => {
    const sample = (theme, h, setting, lowGfx = false, lights = [], pt = [100, 75]) => {
      Prefs.set({ night: setting, lowGraphics: lowGfx });
      DayNight.setZone({ theme });
      DayNight.sync({ hour: h, hoursPerSecond: 0 });
      DayNight.tick(20);
      const canvas = document.createElement('canvas'); canvas.width = 240; canvas.height = 160;
      const g = canvas.getContext('2d'); g.fillStyle = '#a0b0a0'; g.fillRect(0, 0, 240, 160);
      DayNight.draw(g, 240, 160, lights, (x, y) => [x, y]);
      return [...g.getImageData(pt[0], pt[1], 1, 1).data].slice(0, 3);
    };
    const themes = ['meadow', 'ember', 'frostwake', 'fen', 'lapiserg', 'yearwheel', 'wyrd'];
    const byTheme = {};
    for (const th of themes) {
      byTheme[th] = {
        noon: sample(th, 12, 1),
        dusk: sample(th, 18.5, 1),
        midnight: sample(th, 0, 1),
        half: sample(th, 0, 0.5),
        off: sample(th, 0, 0),
        lowGfx: sample(th, 0, 1, true),
      };
    }
    const lit = sample('meadow', 0, 1, false, [{ x: 120, y: 126 }], [120, 80]);
    const unlit = sample('meadow', 0, 1, false, [{ x: 120, y: 126 }], [20, 80]);
    Prefs.set({ night: 1, lowGraphics: false });
    return { byTheme, lit, unlit };
  });

  for (const [th, s] of Object.entries(unit.byTheme)) {
    const ln = lum(s.noon), lm = lum(s.midnight), lh = lum(s.half), ll = lum(s.lowGfx);
    check(lm <= ln * 0.48, `${th} midnight is distinctly dark (${lm.toFixed(1)} <= 48% of noon ${ln.toFixed(1)})`);
    check(lm >= ln * 0.18, `${th} midnight stays readable (${lm.toFixed(1)} >= 18% of noon)`);
    check(s.midnight[2] > s.midnight[0] && s.midnight[2] > s.midnight[1], `${th} midnight keeps cool night hue (${JSON.stringify(s.midnight)})`);
    check(JSON.stringify(s.off) === JSON.stringify(s.noon), `${th} Prefs.night=0 removes night darkening`);
    check(lh > lm && lh < ln, `${th} Prefs.night=0.5 scales smoothly (${lh.toFixed(1)} between ${lm.toFixed(1)} and ${ln.toFixed(1)})`);
    check(ll <= ln * 0.52, `${th} lowGraphics midnight also darkens distinctly (${ll.toFixed(1)})`);
  }
  check(lum(unit.lit) > lum(unit.unlit) * 1.8 && unit.lit[0] > unit.unlit[0] * 2,
    `lamp cutouts & warm glow pop against unlit night (${JSON.stringify(unit.lit)} vs ${JSON.stringify(unit.unlit)})`);

  // 2. Live world screenshots & brightness across Day, Dusk, Midnight (Alderhaven lamps + outdoor zones + Vault).
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_god_mode', enabled: true } }));
  const visit = async (zone, x, y, hour, nightPref = 1) => {
    await page.evaluate(n => Prefs.set({ night: n }), nightPref);
    await page.evaluate(c => Online.send({ type: 'debug', command: c }), { op: 'teleport', zone, x, y });
    await page.waitForFunction(z => Field.zone === z, zone, { timeout: 10000 });
    const outdoor = await page.evaluate(z => DayNight.isOutdoor(z === 0 ? { theme: 'meadow' } : WORLD_MAP.zones[z - 1]), zone);
    await page.waitForFunction(o => o ? DayNight.outdoorBlend > .95 : DayNight.outdoorBlend < .05, outdoor, { timeout: 15000 });
    await page.evaluate(h => Online.send({ type: 'debug', command: { op: 'set_time', hour: h, freeze: true } }), hour);
    await page.waitForFunction(h => Math.abs(DayNight.hour - h) < .05 || (h === 0 && DayNight.hour > 23.95), hour, { timeout: 10000 });
    await page.waitForTimeout(800);
    return canvasBrightness(page);
  };

  // Find a lamp in Alderhaven (zone 0) so screenshots show both town lamps and buildings/NPCs.
  const lampSpot = await page.evaluate(() => {
    const o = Field._debug.objects.find(o => o.kind === 'lamp');
    return o ? { x: Math.round(o.x), y: Math.round(o.y + 2) } : { x: 40, y: 40 };
  });
  const dayMeadow = await visit(0, lampSpot.x, lampSpot.y, 12, 1);
  await page.screenshot({ path: path.join(world.artifacts, 'day-meadow.png') });
  const duskMeadow = await visit(0, lampSpot.x, lampSpot.y, 18.5, 1);
  await page.screenshot({ path: path.join(world.artifacts, 'dusk-meadow.png') });
  const nightMeadow = await visit(0, lampSpot.x, lampSpot.y, 0, 1);
  await page.screenshot({ path: path.join(world.artifacts, 'night-meadow.png') });
  const nightOffMeadow = await visit(0, lampSpot.x, lampSpot.y, 0, 0);
  await page.screenshot({ path: path.join(world.artifacts, 'night-off-meadow.png') });

  check(nightMeadow <= dayMeadow * 0.62, `Greenmeadow live midnight is distinctly darker than noon (${nightMeadow.toFixed(1)} vs ${dayMeadow.toFixed(1)})`);
  check(nightMeadow >= dayMeadow * 0.22 && nightMeadow >= 12, `Greenmeadow midnight stays readable (${nightMeadow.toFixed(1)})`);
  check(Math.abs(nightOffMeadow - dayMeadow) <= dayMeadow * 0.12, `Greenmeadow Prefs.night=0 restores daytime brightness (${nightOffMeadow.toFixed(1)} vs ${dayMeadow.toFixed(1)})`);
  check(duskMeadow > nightMeadow && duskMeadow < dayMeadow * 1.05, `Dusk sits between day and night (${duskMeadow.toFixed(1)})`);

  for (const [z, name, shot] of [[1, 'Emberfall Crags', 'ember'], [2, 'Rimeveil Glacier', 'frost'], [3, 'Gloamfen', 'fen']]) {
    const sp = await page.evaluate(zn => WORLD_MAP.zones[zn - 1].spawn, z);
    const noon = await visit(z, sp.x, sp.y, 12, 1);
    const night = await visit(z, sp.x, sp.y, 0, 1);
    await page.screenshot({ path: path.join(world.artifacts, `night-${shot}.png`) });
    check(night <= noon * 0.64, `${name} midnight is distinctly darker than noon (${night.toFixed(1)} vs ${noon.toFixed(1)})`);
    check(night >= 12 && night >= noon * 0.20, `${name} midnight stays readable (${night.toFixed(1)} of ${noon.toFixed(1)})`);
  }

  // Enclosed dungeon check (zone 5 = Undervault)
  const vNoon = await visit(5, 36, 52, 12, 1);
  const vNight = await visit(5, 36, 52, 0, 1);
  check(Math.abs(vNight - vNoon) <= Math.max(3, vNoon * 0.06), `Enclosed dungeon ignores day/night cycle (${vNoon.toFixed(1)} vs ${vNight.toFixed(1)})`);

  // 3. Render budget check at Greenmeadow midnight
  await visit(0, lampSpot.x, lampSpot.y, 0, 1);
  const cdp = await page.context().newCDPSession(page); await cdp.send('Performance.enable');
  const measure = async n => {
    await page.evaluate(v => Prefs.set({ night: v }), n);
    await page.waitForTimeout(600);
    const t0 = await taskSeconds(cdp); await page.waitForTimeout(4000);
    return (await taskSeconds(cdp)) - t0;
  };
  const onCost = await measure(1), offCost = await measure(0);
  check(onCost <= offCost * 1.35 + 0.1, `Night rendering stays within budget (${onCost.toFixed(2)}s on vs ${offCost.toFixed(2)}s off per 4s)`);
  check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${checks} night-distinct checks passed; artifacts: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (started) { try { await call('stop_world'); } catch (_) {} }
  await client.close();
});
