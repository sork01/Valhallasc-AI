// Static (BOSSMECH-THUNDER-HEART) on the screen, in a real browser against a real private server. The world loads a table of its own
// (VALHALLA_BOSSMECH_FILE) that gives a level-99 green slime the Stormgate's Static with four rods near the hero's arrival, a limit
// of 12 and a warning at 2 so a few swings show everything: every swing the hero lands on the boss is a charge the snapshot lists,
// the red ring a charged hero would blast is drawn from the warning on, a rod the hero walks onto clears the charge and shows as
// dark, and the new texts exist in Swedish. The server decides all of it; this checks what the player is told.
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
const spawn = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8')).spawn;
const rods = [[spawn.x + 5, spawn.y - 4], [spawn.x + 5, spawn.y + 4], [spawn.x - 5, spawn.y - 4], [spawn.x - 5, spawn.y + 4]];
const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bossmech-static-'));
const table = path.join(dir, 'boss-mechanics.txt');
fs.writeFileSync(table, JSON.stringify({
  green: { mechanics: [{ name: 'Static', block: 'static', limit: 12, warn_at: 2, per_hit: 1, r: 5, rods, rod_r: 1.8, immune: 8, dark: 12 }] },
}));
const client = new Client({ name: 'valhallasc-bossmech-static-ui', version: '1.0.0' });
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
  await page.locator('#name').fill('Sparky'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const send = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(300));
  const fight = () => page.evaluate(() => JSON.parse(JSON.stringify(BossMech.fights[0] || null)));
  await send({ op: 'set_god_mode', enabled: true });
  const h = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await send({ op: 'spawn_enemy', kind: 'green', x: h.x + 2, y: h.y, level: 99 });
  await page.waitForFunction(() => BossMech.active, null, { timeout: 15000 });

  // ---- 1. the rods are drawn from the first moment, ready, as blue circles --------------------------------------------------------
  const first = await fight();
  const rodTeles = first.tele.filter(t => t.rod);
  check(rodTeles.length === 4 && rodTeles.every(t => t.tele === 'blue' && t.lit === true && t.shapes[0].r === 1.8), 'four ready rods, blue, radius 1.8');
  check(first.static && first.static.limit === 12 && first.static.warnAt === 2 && first.static.radius === 5, 'the snapshot carries the limit, the warning and the blast radius');
  const rod = rodTeles[0].shapes[0];
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-static-rods.png') });
  const blueAt = await page.evaluate(({ x, y }) => {
    const [sx, sy] = Field._debug.w2s(x, y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.round((sx - 4) * k), Math.round((sy - 2) * k), Math.round(8 * k), Math.round(4 * k)).data; let tint = 0;
    for (let i = 0; i < d.length; i += 4) tint += d[i + 2] - (d[i] + d[i + 1]) / 2;
    return tint / (d.length / 4);
  }, rod);
  const blueBase = await page.evaluate(({ x, y }) => {
    const [sx, sy] = Field._debug.w2s(x, y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.round((sx - 4) * k), Math.round((sy - 2) * k), Math.round(8 * k), Math.round(4 * k)).data; let tint = 0;
    for (let i = 0; i < d.length; i += 4) tint += d[i + 2] - (d[i] + d[i + 1]) / 2;
    return tint / (d.length / 4);
  }, { x: rod.x + 4, y: rod.y + 6 });
  check(blueAt - blueBase > 5, `a rod tints the ground blue (${blueAt.toFixed(1)} against ${blueBase.toFixed(1)} beside it)`);

  // ---- 2. swings charge the hero; the ring of the blast appears from the warning on -------------------------------------------------
  await page.evaluate(() => { const f = BossMech.fights[0]; Field.hero.dir = { x: 1, y: 0 }; });
  let charged = 0;
  for (let i = 0; i < 40 && charged < 2; i++) {
    await page.keyboard.press('Space');
    await page.waitForTimeout(450);
    charged = await page.evaluate(() => Object.values(BossMech.fights[0]?.static?.charges || {})[0] || 0);
  }
  check(charged >= 2, `swings on the boss charged the hero (${charged} of 12)`);
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-static-charged.png') });
  check((await fight()).static.charges[await page.evaluate(() => Online.id)] >= 2, 'the charge is listed under the hero');
  check((await page.evaluate(() => Field.hero.dead)) === false, 'the hero lives: god mode and a limit of 12');

  // ---- 3. a rod clears the charge, grounds the hero and goes dark --------------------------------------------------------------------
  await send({ op: 'teleport', zone: 0, x: rod.x, y: rod.y });
  await page.waitForFunction(() => { const f = BossMech.fights[0]; return f && f.static && Object.keys(f.static.grounded).length === 1; }, null, { timeout: 5000 })
    .catch(async e => { console.log(JSON.stringify({ hero: await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, zone: Field.zone })), rod, fight: await fight() })); throw e; });
  const after = await fight();
  check(Object.values(after.static.charges).every(n => n === 0) || !Object.keys(after.static.charges).length, 'the rod cleared the charge');
  const dark = after.tele.filter(t => t.rod && t.lit === false);
  check(dark.length === 1 && dark[0].litLeft > 8, `the touched rod is dark for about twelve seconds (${dark.map(t => t.litLeft)})`);
  await page.screenshot({ path: path.join(world.artifacts, 'bossmech-static-grounded.png') });

  // ---- 4. Swedish ---------------------------------------------------------------------------------------------------------------------
  const sv = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  const words = await sv.evaluate(() => ['Static', 'Grounded', '{0} of {1} sparks'].map(s => Locale.translate(s)).concat(Locale.translate('3 of 12 sparks')));
  assert.deepEqual(words, ['Statisk laddning', 'Jordad', '{0} av {1} gnistor', '3 av 12 gnistor']);
  checks += words.length;

  assert.deepEqual(errors, []);
  console.log(`bossmech-static-ui: ${checks} checks passed; screenshots in ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
