// End-to-end Chromium + Rust server test for CORPSE-RUN-GHOST-RESPAWN:
// death leaves corpse on the ground -> 3.2s later player releases at nearest camp/graveyard as a translucent ghost
// -> world becomes bleak black-and-white with fog -> peaceful ghost navigates back via corpse arrow & minimap ->
// reaching corpse resurrects at corpse location at 50% HP and restores normal color.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debugBin = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debugBin].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const shotDir = process.env.SHOT_DIR || fs.mkdtempSync(path.join(root, 'test-results', 'corpse-run-'));
fs.mkdirSync(shotDir, { recursive: true });
const mutate = process.env.MUTATE === '1';

const client = new Client({ name: 'valhallasc-corpse-run-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

// Measure how colorful a grid of pixels on #fieldcv is (excluding HUD edges).
// Returns { maxChroma, avgChroma, grayscaleFraction } over sampled points.
async function measureCanvasColor(page) {
  return page.evaluate(() => {
    const cv = document.getElementById('fieldcv');
    const ctx = cv.getContext('2d');
    const w = cv.width, h = cv.height;
    let maxChroma = 0, sumChroma = 0, grayCount = 0, total = 0;
    // Sample interior bands away from top-left portrait / bottom bars / hero center arrow
    for (let gy = 0.22; gy <= 0.78; gy += 0.07) {
      for (let gx = 0.15; gx <= 0.85; gx += 0.07) {
        if (Math.abs(gx - 0.5) < 0.14 && Math.abs(gy - 0.5) < 0.18) continue;
        const px = Math.floor(gx * w), py = Math.floor(gy * h);
        const d = ctx.getImageData(px, py, 1, 1).data;
        const chroma = Math.max(d[0], d[1], d[2]) - Math.min(d[0], d[1], d[2]);
        if (chroma > maxChroma) maxChroma = chroma;
        sumChroma += chroma;
        if (chroma <= 4) grayCount++;
        total++;
      }
    }
    return { maxChroma, avgChroma: sumChroma / total, grayscaleFraction: grayCount / total, total };
  });
}

(async () => {
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')],
    cwd: root,
    stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(process.env.NODE_PATH ? { NODE_PATH: process.env.NODE_PATH } : {}), ...(binary ? { VALHALLA_BINARY: binary } : {}) },
  }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Wraith'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x && !!(Field.warriorSprites || Field.mageSprites || Field.assassinSprites || Field.priestSprites || Field.hunterSprites), null, { timeout: 60000 });

  const debug = command => page.evaluate(command => {
    Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command });
  }, command).then(() => page.waitForTimeout(250));
  const waitFrames = () => page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));

  // Teleport to open grassy ground near Alderhaven (slimes[0]) so there is a clear walk back from spawn (250, 167).
  const deathSpot = { zone: 0, x: 239.35, y: 161.72 };
  await debug({ op: 'teleport', zone: deathSpot.zone, x: deathSpot.x, y: deathSpot.y });
  await page.waitForFunction(({ x, y }) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1.5, deathSpot, { timeout: 10000 });
  await waitFrames();

  const aliveColor = await measureCanvasColor(page);
  check(aliveColor.maxChroma > 15, `Alive world has color (maxChroma=${aliveColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-01-alive.png') });

  // Die at deathSpot.
  await debug({ op: 'die' });
  await page.waitForFunction(() => Field.hero.dead === true, null, { timeout: 5000 });
  await waitFrames();
  const fallenState = await page.evaluate(() => ({
    dead: Field.hero.dead,
    ghost: !!Field.hero.ghost,
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
    corpse: Field.hero.corpse,
  }));
  check(fallenState.dead && !fallenState.ghost, 'Hero starts fallen before releasing spirit');
  check(!fallenState.deadMsgHidden && fallenState.ghostMsgHidden, 'Defeated overlay shows while fallen');
  check(fallenState.corpse && Math.hypot(fallenState.corpse.x - deathSpot.x, fallenState.corpse.y - deathSpot.y) < 1.5, 'Corpse recorded at death spot');
  await page.screenshot({ path: path.join(shotDir, 'corpse-02-fallen.png') });

  // Wait for 3.2s spirit release.
  await page.waitForFunction(() => Field.hero.dead === true && Field.hero.ghost === true, null, { timeout: 10000 });
  await waitFrames();
  const ghostState = await page.evaluate(() => ({
    x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, dead: Field.hero.dead, ghost: Field.hero.ghost,
    corpse: Field.hero.corpse, corpses: Field.corpses.map(c => ({ id: c.id, x: c.x, y: c.y })),
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
    ghostBanner: document.getElementById('ghost-msg').textContent.trim(),
    canAct: Field.canAct,
    attackBlocked: Field.useSkill('attack'),
    worldMapOpenable: (() => { const opened = WorldMap.show(); if (opened) WorldMap.close(); return opened; })(),
  }));
  const distFromCorpse = Math.hypot(ghostState.x - ghostState.corpse.x, ghostState.y - ghostState.corpse.y);
  check(ghostState.dead && ghostState.ghost && ghostState.hp === 0, 'Hero is in ghost state with 0 hp');
  check(distFromCorpse > 5, `Ghost respawned away from corpse (${distFromCorpse.toFixed(1)} tiles)`);
  check(ghostState.deadMsgHidden && !ghostState.ghostMsgHidden, 'Dead overlay hides and Spirit Form banner appears');
  check(ghostState.corpses.length >= 1, 'Corpse stays on the ground in zone snapshot');
  check(!ghostState.canAct && !ghostState.attackBlocked, 'Ghost cannot attack or cast');
  check(ghostState.worldMapOpenable, 'Ghost can open the world map to navigate');

  if (mutate) {
    // Deliberate falsification check: expect alive color when ghost should be B&W.
    const ghostColorMut = await measureCanvasColor(page);
    assert.ok(ghostColorMut.maxChroma > 50, 'MUTATE: forcing failure on B&W ghost world');
  }

  const ghostColor = await measureCanvasColor(page);
  check(ghostColor.grayscaleFraction > 0.95 && ghostColor.maxChroma <= 6, `Ghost world is black & white with fog (frac=${ghostColor.grayscaleFraction.toFixed(2)}, maxChroma=${ghostColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-03-ghost-spawn.png') });

  // Verify peaceful ghost: spawn a hostile enemy right next to the ghost and tick; ghost stays ignored & unhurt.
  await debug({ op: 'spawn_enemy', kind: 'slime', x: ghostState.x + 1.5, y: ghostState.y, level: 1 });
  await page.waitForTimeout(700);
  const hostileNear = await page.evaluate(() => Field.slimes.map(s => ({ state: s.state, kind: s.kind })));
  check(hostileNear.every(s => s.state !== 'chase' && s.state !== 'windup'), 'Hostile mobs do not aggro the ghost');

  // Walk close to the corpse (~3 tiles away) along an unobstructed route so both the see-through ghost AND the corpse appear together on screen.
  const approachPt = await page.evaluate(() => ({ x: Field.hero.corpse.x + 2.8, y: Field.hero.corpse.y + 1.2 }));
  const route = await page.evaluate(pt => {
    const r = Field._debug.routeTo(pt);
    return r.length ? r : [pt];
  }, approachPt);
  for (const wp of route) {
    await page.evaluate(pt => { Online.send({ type: 'move', x: pt.x, y: pt.y }); }, wp);
    await page.waitForFunction(pt => Math.hypot(Field.hero.x - pt.x, Field.hero.y - pt.y) < 1.3, wp, { timeout: 10000 });
  }
  await page.evaluate(() => { Online.send({ type: 'stop' }); });
  await page.waitForTimeout(150);
  await waitFrames();
  await page.screenshot({ path: path.join(shotDir, 'corpse-04-near-corpse.png') });

  // Measure alpha scaling check on MageSprite.draw when drawing a ghost.
  const ghostAlphaApplied = await page.evaluate(() => {
    const spr = Field.mageSprites || Field.warriorSprites || Field.assassinSprites || Field.priestSprites || Field.hunterSprites;
    if (!spr) return null;
    const dummy = document.createElement('canvas'); dummy.width = 64; dummy.height = 64;
    const g = dummy.getContext('2d');
    let drawnAlpha = 1;
    const origDrawImage = g.drawImage.bind(g);
    g.drawImage = (...args) => { drawnAlpha = g.globalAlpha; origDrawImage(...args); };
    spr.draw(g, { dead: true, ghost: true, moving: false, fx: 1, fy: 1, walk: 0, atkT: 0, hurtT: 0, deadT: 0 }, 0);
    return drawnAlpha;
  });
  check(ghostAlphaApplied !== null && ghostAlphaApplied < 0.6 && ghostAlphaApplied > 0.2, `Ghost character sprite renders translucent (alpha=${ghostAlphaApplied})`);

  // Walk directly onto the corpse to trigger half-HP resurrection.
  await page.evaluate(() => { Online.send({ type: 'move', x: Field.hero.corpse.x, y: Field.hero.corpse.y }); });
  await page.waitForFunction(() => !Field.hero.dead && !Field.hero.ghost && !Field.hero.corpse, null, { timeout: 10000 });
  await waitFrames();

  const revivedState = await page.evaluate(() => ({
    x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, maxHp: Field.hero.maxHp,
    dead: Field.hero.dead, ghost: Field.hero.ghost, corpse: Field.hero.corpse,
    corpsesCount: Field.corpses.length,
    deadMsgHidden: document.getElementById('dead-msg').hidden,
    ghostMsgHidden: document.getElementById('ghost-msg').hidden,
  }));
  const expectedHalfHp = Math.max(1, Math.round(revivedState.maxHp * 0.5));
  check(Math.abs(revivedState.hp - expectedHalfHp) <= 1, `Resurrected at half HP (${revivedState.hp}/${revivedState.maxHp})`);
  check(Math.hypot(revivedState.x - deathSpot.x, revivedState.y - deathSpot.y) < 2.2, 'Resurrected at the corpse location');
  check(revivedState.corpsesCount === 0, 'Corpse cleared after resurrection');
  check(revivedState.deadMsgHidden && revivedState.ghostMsgHidden, 'Death and ghost banners hidden after resurrection');

  const revivedColor = await measureCanvasColor(page);
  check(revivedColor.maxChroma > 15, `Normal world color restored after resurrection (maxChroma=${revivedColor.maxChroma})`);
  await page.screenshot({ path: path.join(shotDir, 'corpse-05-resurrected.png') });

  check(errors.length === 0, `No uncaught page errors: ${errors.join('; ')}`);
  console.log(`PASS corpse-run-ui (${checks} checks). Screenshots in ${shotDir}`);
})().finally(async () => {
  await browser?.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
