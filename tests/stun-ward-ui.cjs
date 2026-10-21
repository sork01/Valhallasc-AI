// Real PvP statuses in a private world. Paired canvas frames differ only in the victim's effect;
// sampling the same sprite box within one browser turn avoids camera, scenery and animation noise.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server');
const client = new Client({ name: 'valhallasc-stun-ward-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const errors = [];
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const send = (page, command) => page.evaluate(command => Online.send(command), command);
const debug = async (page, command) => { await send(page, { type: 'debug', command }); await page.waitForTimeout(180); };
const cast = (page, id, fx = -1, fy = 0) => send(page, { type: 'skill', id, fx, fy });
const pvp = (page, command) => send(page, { type: 'pvp', command });
async function pixelDelta(page, id, kind) {
  return page.evaluate(({ id, kind }) => {
    const who = id === Online.id ? Field.hero : Field.remotePlayers.find(p => p.id === id);
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    const [x, y] = Field._debug.w2s(who.x, who.y);
    const box = kind === 'bar' ? [x - 31, y + 19, 62, 9] : [x - 100, y - 185, 200, 235];
    const grab = () => g.getImageData(...box.map(v => Math.round(v * k))).data;
    Field._debug.drawFrame(0); const before = grab();
    const saved = { stun: who.stun, buffs: who.buffs, absorb: who.absorb, wardHitAt: who.wardHitAt, wardBreakAt: who.wardBreakAt, stunHitAt: who.stunHitAt };
    if (kind === 'bar') who.absorb = 0;
    else if (kind === 'stun') { who.stun = 0; who.stunHitAt = -99; }
    else if (kind === 'hit') who.wardHitAt = -99;
    else if (kind === 'break') who.wardBreakAt = -99;
    else if (kind === 'stunHit') who.stunHitAt = -99;
    else { who.buffs = who.buffs.filter(b => b.id !== 'arcaneward'); who.absorb = 0; who.wardHitAt = who.wardBreakAt = -99; }
    Field._debug.drawFrame(0); const after = grab(); Object.assign(who, saved); Field._debug.drawFrame(0);
    let changed = 0;
    for (let i = 0; i < before.length; i += 4) if (Math.abs(before[i] - after[i]) + Math.abs(before[i+1] - after[i+1]) + Math.abs(before[i+2] - after[i+2]) > 25) changed++;
    return changed;
  }, { id, kind });
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: binary } }));
  const world = await call('start_world', { startLevel: 99, godMode: false, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  async function player(name, cls, x, y) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    await debug(page, { op: 'teleport', zone: 0, x, y });
    await debug(page, { op: 'set_time', hour: 12, freeze: true });
    await page.waitForTimeout(500);
    return page;
  }
  const mage = await player('WardMage', 'mage', 9, 9);
  const assassin = await player('StunAssassin', 'assassin', 10.5, 9);
  const observer = await player('Bystander', 'warrior', 8, 10.5);
  const mageId = await mage.evaluate(() => Online.id), assassinId = await assassin.evaluate(() => Online.id), observerId = await observer.evaluate(() => Online.id);
  await pvp(assassin, { op: 'duel_request', id: mageId });
  await mage.waitForFunction(() => Pvp.state.requests.length > 0);
  await pvp(mage, { op: 'duel_accept', id: assassinId });
  await mage.waitForFunction(() => Pvp.state.duel);
  check(await pixelDelta(mage, mageId, 'stun') === 0, 'normal hero has no stun pixels');
  check(await pixelDelta(observer, mageId, 'ward') === 0, 'normal remote mage has no ward pixels');

  // Knife Ring is a real landed blow, and may dodge: reset only its cooldown/resource before retrying.
  for (let i = 0; i < 8; i++) {
    await debug(assassin, { op: 'reset_cooldowns' }); await debug(assassin, { op: 'set_resource', amount: 100 });
    await cast(assassin, 'knifering');
    try { await mage.waitForFunction(() => Field.hero.stun > 1, null, { timeout: 800 }); break; } catch (_) {}
  }
  await mage.waitForFunction(() => Field.hero.stun > 0);
  check(await pixelDelta(mage, mageId, 'stunHit') > 30, 'stun landing adds a short impact flare');
  const earlySeconds = +(await mage.locator('[data-buff="stun"] i').textContent()).replace('s', '');
  check(await mage.locator('[data-buff="stun"]').isVisible(), 'victim sees a labelled stun status with seconds');
  check(await pixelDelta(mage, mageId, 'stun') > 80, 'stun visibly changes pixels above the victim sprite');
  await observer.waitForFunction(id => Field.remotePlayers.find(p => p.id === id)?.stun > 0, mageId);
  check(await pixelDelta(observer, mageId, 'stun') > 80, 'nearby bystander sees the stunned remote character');
  check(await pixelDelta(observer, observerId, 'stun') === 0, 'bystander has no stun effect');
  check(await observer.locator('[data-buff="stun"]').count() === 0, 'bystander gets no victim HUD status');
  await mage.screenshot({ path: path.join(world.artifacts, 'stunned-mage.png') });
  await mage.waitForFunction(early => { const n = document.querySelector('[data-buff="stun"] i'); return n && parseInt(n.textContent) < early; }, earlySeconds, { timeout: 10000 });
  check(true, 'stun countdown decreases');
  check(await pixelDelta(mage, mageId, 'stun') > 80, 'stun effect lasts beyond the landing flash');
  await mage.waitForFunction(() => !Field.hero.stun, null, { timeout: 15000 });
  await mage.waitForFunction(() => !document.querySelector('[data-buff="stun"]'));
  check(await pixelDelta(mage, mageId, 'stun') === 0, 'stun pixels disappear after recovery');

  // Root and wound use the same HUD, with authoritative durations.
  for (let i = 0; i < 8; i++) {
    await debug(mage, { op: 'reset_cooldowns' }); await debug(mage, { op: 'set_resource', amount: 99999 });
    await cast(mage, 'arcanestorm', 1, 0);
    try { await assassin.waitForFunction(() => Field.hero.root > 0, null, { timeout: 600 }); break; } catch (_) {}
  }
  check(await assassin.locator('[data-buff="root"]').isVisible(), 'root status appears on its victim');
  await assassin.waitForFunction(() => !Field.hero.root);
  for (let i = 0; i < 8; i++) {
    await debug(assassin, { op: 'reset_cooldowns' }); await debug(assassin, { op: 'set_resource', amount: 100 });
    await cast(assassin, 'thousandcuts');
    try { await mage.waitForFunction(() => Field.hero.woundLeft > 0, null, { timeout: 600 }); break; } catch (_) {}
  }
  check(await mage.locator('[data-buff="wound"]').isVisible(), 'wound status shows the server expiry');

  // Ward: soak still draws after the eight-second reduction ends; its bar and shell vanish at expiry.
  await debug(mage, { op: 'set_resource', amount: 99999 });
  await cast(mage, 'arcaneward');
  await mage.waitForFunction(() => Field.hero.absorb > 0);
  const full = await mage.evaluate(() => Field.hero.absorb);
  check(await pixelDelta(mage, mageId, 'ward') > 300, 'ward and remaining-soak bar visibly surround the caster');
  await observer.waitForFunction(id => Field.remotePlayers.find(p => p.id === id)?.absorb > 0, mageId);
  check(await pixelDelta(observer, mageId, 'ward') > 300, 'opponent and bystander see the ward');
  check(await pixelDelta(observer, observerId, 'ward') === 0, 'unwarded character has no ward effect');
  const ice = await mage.evaluate(() => {
    const c = document.createElement('canvas'); c.width = 240; c.height = 280;
    const g = c.getContext('2d'); g.translate(120, 205);
    Field._debug.drawMageWardShell(g, { ...Field.hero, wardHitAt: -99, wardBreakAt: -99 }, 0);
    const blue = ([x,y,w,h]) => { const d = g.getImageData(x + 120, y + 205, w, h).data; let count = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i+3] > 150 && d[i+2] > d[i] + 20 && d[i+2] > d[i+1] + 5) count++;
      return count;
    };
    const clusters = [[-95,-160,60,80],[-30,-195,60,70],[35,-160,65,80],[-95,-45,65,100],[25,-45,70,100]].map(blue);
    const center = g.getImageData(105, 110, 30, 65).data; let covered = 0;
    for (let i = 3; i < center.length; i += 4) if (center[i] > 100) covered++;
    const aura = [[-84,-67,7,8],[77,-67,7,8],[-4,37,8,7]].map(([x,y,w,h]) => {
      const d = g.getImageData(x + 120, y + 205, w, h).data; let peak = 0;
      for (let i = 3; i < d.length; i += 4) peak = Math.max(peak, d[i]);
      return peak;
    });
    return { clusters, covered, aura };
  });
  check(ice.clusters.every(n => n > 40), `five faceted blue ice clusters surround the mage (${ice.clusters})`);
  check(ice.covered === 0, 'frost leaves the character at the centre clear');
  check(ice.aura.every(a => a >= 60 && a < 130), `faint elliptical aura joins the ice along both sides and the bottom (${ice.aura})`);
  // Draw the real warded actor's shell twice in isolation to check the motion preference.
  const motionDelta = () => mage.evaluate(() => {
    const c = document.createElement('canvas'); c.width = 220; c.height = 260; const g = c.getContext('2d');
    const render = t => { g.setTransform(1,0,0,1,0,0); g.clearRect(0,0,220,260); g.translate(110,190); Field._debug.drawMageWardShell(g, Field.hero, t); return g.getImageData(0,0,220,260).data; };
    const a = render(0), b = render(2); let changed = 0;
    for (let i = 0; i < a.length; i += 4) if (Math.abs(a[i+3] - b[i+3]) > 10) changed++;
    return changed;
  });
  check(await motionDelta() === 0, 'reduced-motion ward stays static');
  await mage.emulateMedia({ reducedMotion: 'no-preference' });
  check(await motionDelta() > 30, 'normal-motion ward animates');
  await mage.emulateMedia({ reducedMotion: 'reduce' });
  await mage.screenshot({ path: path.join(world.artifacts, 'arcane-ward.png') });
  const preview = await mage.evaluate(() => {
    const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
    const bg = g.createLinearGradient(0,0,0,512); bg.addColorStop(0,'#101a2b'); bg.addColorStop(1,'#263b4d');
    g.fillStyle = bg; g.fillRect(0,0,512,512); g.translate(256,360); g.scale(1.8,1.8);
    const who = { ...Field.hero, hurtT: 0, atkT: 0, moving: false, stun: 0, wardHitAt: -99, wardBreakAt: -99 };
    Field.mageSprites.draw(g, who, 0); Field._debug.drawMageWardShell(g, who, 0);
    return c.toDataURL('image/png').split(',')[1];
  });
  fs.writeFileSync(path.join(world.artifacts, 'ward-ice-reference-preview.png'), Buffer.from(preview, 'base64'));
  await mage.waitForFunction(() => !Field.hero.buffs.some(b => b.id === 'arcaneward'), null, { timeout: 20000 });
  check(await mage.evaluate(() => Field.hero.absorb > 0 && Field.hero.absorbLeft > 0), 'PvP soak outlives damage reduction');
  check(await pixelDelta(mage, mageId, 'ward') > 300, 'soak alone keeps the ice barrier visible');
  check(await pixelDelta(mage, mageId, 'bar') > 60, 'soak bar is visible even with nearby actors in front');
  await mage.screenshot({ path: path.join(world.artifacts, 'arcane-ward-soak.png') });
  await mage.waitForFunction(() => !Field.hero.absorb, null, { timeout: 4000 });
  check(await pixelDelta(mage, mageId, 'break') > 30, 'expiry produces a visible ward burst');
  await mage.waitForTimeout(800);
  check(await pixelDelta(mage, mageId, 'ward') === 0, 'expired ward leaves no effect');

  // Recast and land strikes until the soak is spent, while its damage reduction is still active.
  await debug(mage, { op: 'reset_cooldowns' }); await debug(mage, { op: 'set_resource', amount: 99999 }); await cast(mage, 'arcaneward');
  await mage.waitForFunction(() => Field.hero.absorb > 0);
  let sawHit = false, sawBreak = false;
  for (let i = 0; i < 35; i++) {
    await debug(assassin, { op: 'reset_cooldowns' });
    await debug(assassin, { op: 'set_resource', amount: 100 });
    await cast(assassin, 'assassinate');
    await mage.waitForTimeout(70);
    const left = await mage.evaluate(() => Field.hero.absorb);
    if (left < full) sawHit ||= await pixelDelta(mage, mageId, 'hit') > 30;
    if (!left) { sawBreak = await pixelDelta(mage, mageId, 'break') > 30; break; }
  }
  check(sawHit, 'a soaked blow flashes the ward');
  check(sawBreak, 'exhausting the soak bursts the ward');
  check(await mage.evaluate(() => Field.hero.buffs.some(b => b.id === 'arcaneward')), 'damage reduction can remain after the soak breaks');
  check(await pixelDelta(observer, mageId, 'ward') > 100, 'remaining reduction still draws a ward for others');
  await pvp(mage, { op: 'duel_cancel' });
  await mage.waitForFunction(() => !Field.hero.woundLeft);
  check(await mage.locator('[data-buff="wound"]').count() === 0, 'duel end clears wound HUD');

  const sv = await browser.newPage();
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  assert.deepEqual(await sv.evaluate(() => ['Stunned', 'Rooted', 'Wounded', 'Ward: 123', 'Cannot move, attack or cast.'].map(Locale.translate)),
    ['Bedövad', 'Fastrotad', 'Sårad', 'Skydd: 123', 'Kan inte röra sig, attackera eller använda förmågor.']); checks += 5;
  assert.deepEqual(errors, [], 'no browser errors');
  console.log(`stun-ward-ui: ${checks} checks passed; screenshots in ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
