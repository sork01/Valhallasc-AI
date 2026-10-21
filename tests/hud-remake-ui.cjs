// HUD remake (UI-HUD-REMAKE) in a real browser: the gold/enemies line, the Character button and the controls hint are gone, the zone and
// online count sit under the minimap and follow a zone change and a second player, and a layout saved with the removed pieces still loads.
// The scrollbars use the gilded in-game theme. Client-only; nothing here touches gameplay state.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-hud-remake', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const KEY = 'valhallasc.save.v1';
const stored = page => page.evaluate(k => JSON.parse(localStorage.getItem(k) || '{}'), KEY);
const rect = (page, selector) => page.locator(selector).evaluate(n => { const r = n.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; });
const text = page => page.locator('#network-status').textContent();
async function enter(browser, url, name, viewport, seed) {
  const page = await browser.newPage({ viewport, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  await page.addInitScript(seed => { if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify(seed)); } }, seed);
  await page.goto(url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  return page;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  // A layout saved before the remake still names the removed pieces: it must load, and the next save drops them.
  const seed = { lang: 'en', sound: false, char: null, draft: null, ui: { character: { x: -4, y: 3 }, hint: { x: 2, y: -2 }, bags: { x: -3, y: -2 } } };
  const page = await enter(browser, world.url, 'Hudder', { width: 1440, height: 900 }, seed);

  // --- the removed pieces ---
  for (const sel of ['#equipment-open', '.hud-hint', '.hud-stats', '#hud-gold', '#hud-kills', '[data-ui="character"]', '[data-ui="hint"]'])
    check(await page.locator(sel).count() === 0, `${sel} is gone`);
  check(!/ gold · \d+ (enemies|slimes)/.test(await page.locator('.hud-tr').innerText()), 'The gold and enemies line is not in the top right');
  check(await page.evaluate(() => Prefs.layout.character !== undefined), 'The old layout was read without an error');
  check(await page.locator('#inventory-open').isVisible() && await page.locator('#social-open').isVisible(), 'Bags and Social stay');
  await page.keyboard.press('e');
  check(await page.locator('#equipment').isVisible(), 'E still opens the character window');
  check(await page.locator('#bag-gold').textContent().then(t => /^\d+ gold$/.test(t)), 'Gold is shown in the bags window');
  await page.keyboard.press('Escape');

  // --- zone and online count under the minimap ---
  const place = async () => { const m = await rect(page, '#minimap'), s = await rect(page, '#network-status'); return { m, s }; };
  await page.waitForFunction(() => /^Greenmeadow · \d+ online$/.test(document.getElementById('network-status').textContent), null, { timeout: 10000 });
  let { m, s } = await place();
  check(s.t >= m.b - 1 && s.t - m.b < 40, `The pill sits right under the minimap (${m.b.toFixed(0)} -> ${s.t.toFixed(0)})`);
  check(Math.abs(s.r - m.r) < 2 && s.l >= m.l - 2, 'It is right-aligned with the minimap and no wider than it');
  check(await page.locator('.hud-tr #network-status').count() === 1 && await page.locator('#network-status').count() === 1, 'There is one pill, inside the minimap column');
  const horse = await rect(page, '#mount-toggle'), travel = await rect(page, '#city-travel');
  check(travel.t >= horse.b - 1, `Visit button clears the minimap column (${horse.b.toFixed(0)} -> ${travel.t.toFixed(0)})`);
  const top = await rect(page, '#stage');
  check(s.t > top.t + 10, 'Nothing is left at the top centre');
  check(await text(page) === 'Greenmeadow · 1 online', `One player online reads "${await text(page)}"`);
  const second = await enter(browser, world.url, 'Visitor', { width: 1440, height: 900 }, { lang: 'en', sound: false, char: null, draft: null });
  await page.waitForFunction(() => document.getElementById('network-status').textContent === 'Greenmeadow · 2 online', null, { timeout: 10000 });
  check(true, 'A second player makes it 2 online');
  await second.close();
  await page.waitForFunction(() => document.getElementById('network-status').textContent === 'Greenmeadow · 1 online', null, { timeout: 15000 });
  check(true, 'The count drops again when they leave');
  const home = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y })), crags = await page.evaluate(() => WORLD_MAP.zones[0].spawn);
  await page.evaluate(spot => Online.send({ type: 'debug', ref: 950, command: { op: 'teleport', zone: 1, x: spot.x, y: spot.y } }), crags);
  await page.waitForFunction(() => /^Emberfall Crags · \d+ online$/.test(document.getElementById('network-status').textContent), null, { timeout: 10000 });
  check(true, 'The zone name follows a zone change');
  await page.evaluate(spot => Online.send({ type: 'debug', ref: 951, command: { op: 'teleport', zone: 0, x: spot.x, y: spot.y } }), home);
  await page.waitForFunction(() => /^Greenmeadow · \d+ online$/.test(document.getElementById('network-status').textContent), null, { timeout: 10000 });

  // --- the layout migrates: Edit UI saves only the pieces that exist ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#set-edit-ui').click();
  check(await page.locator('.layout-handle').count() === 10, 'Edit UI offers ten pieces (the food and potion bar is part of the skillbar)');
  await page.locator('#layout-done').click(); await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  const ui = (await stored(page)).ui || {};
  check(!('character' in ui) && !('hint' in ui) && 'bags' in ui, `Saved layout dropped the removed pieces: ${JSON.stringify(ui)}`);

  // --- scrollbars ---
  const bars = await page.evaluate(() => {
    const probe = document.createElement('div'); probe.id = 'sbprobe';
    probe.style.cssText = 'position:fixed;left:0;top:0;width:100px;height:60px;overflow:scroll'; probe.innerHTML = '<div style="width:400px;height:400px"></div>';
    document.body.append(probe);
    const thumb = getComputedStyle(probe, '::-webkit-scrollbar-thumb'), track = getComputedStyle(probe, '::-webkit-scrollbar-track'), whole = getComputedStyle(probe, '::-webkit-scrollbar');
    const out = { width: whole.width, thumbBg: thumb.backgroundImage, thumbRadius: thumb.borderTopLeftRadius, trackBg: track.backgroundColor, scrollbarWidth: getComputedStyle(probe).scrollbarWidth, bar: probe.offsetWidth - probe.clientWidth };
    probe.remove(); return out;
  });
  check(bars.scrollbarWidth === 'auto', `No standards scrollbar property overrides the theme (${bars.scrollbarWidth})`);
  check(/gradient/.test(bars.thumbBg) && parseFloat(bars.thumbRadius) > 2, `Thumb is a rounded gradient (${bars.thumbBg.slice(0, 40)}, ${bars.thumbRadius})`);
  check(bars.trackBg !== 'rgba(0, 0, 0, 0)', `Track has its own colour (${bars.trackBg})`);
  check(await page.evaluate(() => ['.chat-log', '.tracker-list', '#quest-list', '.social-body', '.wm-side', '.gossip-parchment'].every(sel => { const n = document.querySelector(sel); return !n || getComputedStyle(n).scrollbarWidth === 'auto'; })), 'No panel keeps the browser default thin bar');
  const log = page.locator('#chat-log');
  await page.evaluate(() => { for (let i = 0; i < 30; i++) { const p = document.createElement('p'); p.textContent = 'line ' + i; document.getElementById('chat-log').append(p); } });
  await page.screenshot({ path: path.join(world.artifacts, 'hud-remake-1440.png') });
  check(await log.evaluate(n => n.scrollHeight > n.clientHeight), 'The chat log scrolls');

  // --- the stylesheet arrangement (a player who chose the plain layout): 80% by default, then the same arrangement at 100% ---
  const lay = await enter(browser, world.url, 'Layouter', { width: 1440, height: 900 }, { lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} });
  await lay.waitForFunction(() => /online$/.test(document.getElementById('network-status').textContent));
  check(await lay.evaluate(() => Prefs.uiScale) === .8, 'UI size defaults to 80%');
  const arrange = async label => {
    await lay.waitForTimeout(150);
    const r = {}; for (const [k, sel] of Object.entries({ stage: '#stage', frame: '.hud-tl', tracker: '#quest-tracker', chat: '#chat', skill: '#skillbar', quick: '#quickuse', bags: '#inventory-open', social: '#social-open', map: '#minimap', globe: '#wm-open', pill: '#network-status' })) r[k] = await rect(lay, sel);
    const u = r.stage.w / 100, st = r.stage, near = (x, y, tol = 1.2) => Math.abs(x - y) <= tol * u;
    check(near(r.tracker.l, st.l + 1.4 * u) && r.tracker.t >= r.frame.b - 1, `${label}: the quest tracker is on the left, under the character frame (${JSON.stringify({ tracker: r.tracker, frame: r.frame, st })})`);
    check(near(r.chat.l, st.l + 1.4 * u) && near(r.chat.b, st.b - .6 * u), `${label}: chat is in the bottom left corner`);
    check(near(r.skill.b, st.b - .6 * u) && near((r.skill.l + r.skill.r) / 2, (st.l + st.r) / 2, .5), `${label}: the skillbar is centred at the very bottom`);
    check(near(r.quick.l, r.skill.l + 6.46 * u, .5) && r.quick.b <= r.skill.t + 1 && r.skill.t - r.quick.b < 1.6 * u, `${label}: food and potions sit on the skillbar's top edge, 6.46 cqw in (${r.quick.l.toFixed(0)} vs ${r.skill.l.toFixed(0)}, gap ${(r.skill.t - r.quick.b).toFixed(0)})`);
    check(near(r.bags.r, st.r - 1.5 * u) && near(r.bags.b, st.b - .6 * u), `${label}: the bags button is in the bottom right corner`);
    check(near(r.social.r, r.bags.r, .3) && r.social.b <= r.bags.t + 1 && r.bags.t - r.social.b < 1.2 * u, `${label}: the social button is just above it (gap ${(r.bags.t - r.social.b).toFixed(0)})`);
    check(near(r.map.r, st.r - 1.4 * u) && near(r.map.t, st.t + 1.4 * u), `${label}: the minimap is in the top right corner`);
    check(r.globe.t >= st.t + 1.5 * u && r.globe.l >= st.l && r.globe.b <= r.map.b, `${label}: the world map button is fully on screen (top ${(r.globe.t - st.t).toFixed(0)})`);
    const boxes = ['frame', 'tracker', 'chat', 'skill', 'quick', 'bags', 'social', 'map', 'pill'], hit = (a, b) => !(a.r <= b.l + 1 || b.r <= a.l + 1 || a.b <= b.t + 1 || b.b <= a.t + 1);
    const clash = []; for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) if (hit(r[boxes[i]], r[boxes[j]])) clash.push(boxes[i] + '/' + boxes[j]);
    check(clash.length === 0, `${label}: no HUD pieces overlap (${clash.join(', ') || 'none'})`);
    await lay.screenshot({ path: path.join(world.artifacts, `hud-layout-${label.replace('%', '')}.png`) });
  };
  await arrange('80%');
  await lay.keyboard.press('Escape'); await lay.locator('#p-settings').click(); await lay.locator('#set-uiscale').fill('100'); await lay.locator('#set-back').click(); await lay.locator('#p-resume').click();
  await arrange('100%');

  // --- phone width ---
  const phone = await enter(browser, world.url, 'Phoner', { width: 844, height: 390 }, { lang: 'en', sound: false, char: null, draft: null });
  await phone.waitForFunction(() => /^Greenmeadow · \d+ online$/.test(document.getElementById('network-status').textContent), null, { timeout: 10000 });
  const pm = await rect(phone, '#minimap'), ps = await rect(phone, '#network-status'), pst = await rect(phone, '#stage');
  check(ps.t >= pm.b - 1 && ps.l >= pst.l && ps.r <= pst.r + 1 && ps.w <= pm.w + 2, `At 844x390 the pill stays under the minimap and inside the stage (${JSON.stringify(ps)})`);
  // The food and potion bar is anchored to the skillbar, so it follows it on a small stage too.
  const pq = await rect(phone, '#quickuse'), pb = await rect(phone, '#skillbar');
  check(pq.b <= pb.t + 1 && pb.t - pq.b < 0.02 * pst.w && Math.abs(pq.l - pb.l - 0.0646 * pst.w) < 0.012 * pst.w, `At 844x390 the food and potion bar sits on the skillbar (${JSON.stringify({ pq, pb })})`);
  // A visitor who never moved anything gets Sork's arrangement; Reset goes back to it, and a layout of one's own is kept.
  check(await phone.evaluate(() => JSON.stringify(Prefs.layout.party) === '{"x":61.04,"y":17.53}' && Prefs.layout.quests.y === -2.48 && Prefs.panelSize.chat.w === 34.36 && Prefs.panelSize.quests.h === 31.28), 'A fresh visitor gets the shipped layout and panel sizes');
  check(await phone.evaluate(() => document.getElementById('chat').style.getPropertyValue('--pw') !== '' || getComputedStyle(document.getElementById('chat')).getPropertyValue('--pw') !== ''), 'The default chat width is applied');
  await phone.evaluate(() => { Settings.startEdit(); Settings.layout.bags = { x: 0, y: 0 }; Prefs.set({ ui: { map: { x: 2, y: 2 } } }); Settings.refresh(); });
  check(await phone.evaluate(() => Object.keys(Prefs.layout).join() === 'map'), 'A layout the player saved replaces the shipped one');
  await phone.evaluate(() => { Settings.stopEdit(); Settings.reset(); });
  check(await phone.evaluate(() => Object.keys(Prefs.layout).length === 9 && Settings.layout.party.x === 61.04), 'Reset returns to the shipped layout');
  await phone.screenshot({ path: path.join(world.artifacts, 'hud-remake-844x390.png') });
  await phone.close();
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`hud-remake-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); });
