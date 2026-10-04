// Browser-only checks for the Wyrdwood (levels 20-30): the data the client holds, the autumn forest ground, the river bridge, the
// storm sky and rain on the heights, both hubs and their travel buttons, the Elder Ash and the beacons (dark until a quest has lit
// them), the escort (Eydis walks beside the hero and her stranded self is hidden), and the seven monster kinds in every clip.
// Rules, levels, combat and persistence are exercised by the Rust tests and the `wyrdwood` / `wyrd_quests` MCP scenarios; this
// asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-wyrdwood-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// Average colour of a region of the world canvas, as fractions of its width and height.
const look = (page, [x0, y0, x1, y1] = [.3, .35, .7, .65]) => page.evaluate(([x0, y0, x1, y1]) => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * x0), Math.floor(h * y0), Math.floor(w * (x1 - x0)), Math.floor(h * (y1 - y0))).data;
  let r = 0, gr = 0, b = 0; const n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
  return { r: r / n, g: gr / n, b: b / n };
}, [x0, y0, x1, y1]);
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world', { startLevel: 26 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  // Display-only fixture: while `stage` is set, the browser's copy of each Wyrdwood snapshot gets one extra monster of every kind in
  // a chosen state, so every clip can be drawn without a hero meeting them. The server is untouched.
  let stage = null;
  const kinds = ['boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir'];
  const levels = { boar: 21, crow: 23, troll: 25, weaver: 27, ram: 29, oakhorn: 25, hrungnir: 30 }, health = { boar: 5600, crow: 4300, troll: 9500, weaver: 7600, ram: 11500, oakhorn: 60000, hrungnir: 150000 };
  const windup = { boar: .3, crow: .5, troll: .8, weaver: .7, ram: .25, oakhorn: 1, hrungnir: .9 };
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 6) return text;
    kinds.forEach((kind, i) => {
      const D = [-18, -12, -6, 0, 6, 12, 18][i], x = me.x + (-8 + D) / 2, y = me.y + (-8 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: 1000 + i, kind, zone: 6, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: i, dir: 1, elite: kind === 'oakhorn' || kind === 'hrungnir' });
    });
    return JSON.stringify(packet);
  };
  await page.routeWebSocket(/\/ws$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => server.send(message));
    server.onMessage(message => ws.send(typeof message === 'string' ? restage(message) : message));
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('WyrdUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.wyrdSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  await debug({ op: 'explore_all' });
  await page.waitForFunction(() => Field.explored?.length >= 7 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const stageAt = async (x, y) => {
    await debug({ op: 'teleport', zone: 6, x, y });
    await page.waitForFunction(([x, y]) => Field.zone === 6 && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
    await page.waitForTimeout(400);
  };

  // The map data the client uses comes from the same file the server loads.
  const z = await page.evaluate(() => { const a = Field._debug.zones[6]; return { n: Field._debug.zones.length, name: a.name, theme: a.theme, size: a.size, levels: a.levels, camps: (a.camps || []).map(c => c.name), city: a.city.name, bridges: (a.bridges || []).length, places: (a.places || []).map(p => p.id), portals: a.portals.map(p => p.id + '>' + p.to), beacons: a.objects.filter(o => o.kind === 'beacon').length, crags: a.objects.filter(o => o.kind === 'crag').length, water: a.objects.filter(o => o.kind === 'water').length, quests: (a.quests || []).length, npcs: (a.npcs || []).length }; });
  check(z.n === 8 && z.name === 'Wyrdwood' && z.theme === 'wyrd' && z.size === 192 && z.levels.join() === '20,30', 'The client knows the Wyrdwood: name, wyrd theme, 192 tiles, levels 20-30');
  check(z.city === 'Hollowmoot' && z.camps.join() === 'Skuldwatch' && z.bridges === 1 && z.places.length === 6 && z.portals.join() === 'skaldholm_gate>4', 'Two hubs, one bridge, six named places and the gate back to Skaldholm');
  check(z.beacons === 3 + 1 && z.crags > 100 && z.water > 150 && z.quests >= 24 && z.npcs === 17, `The ridges (${z.crags} crags), the river (${z.water} discs), four beacons, ${z.quests} quests and ${z.npcs} people are all in the data`);
  check(await page.evaluate(stub => { const m = Field.wyrdSprites.meta; return m.kinds.join() === 'boar,crow,troll,weaver,ram,oakhorn,hrungnir' && (stub || m.kinds.every(k => Field.wyrdSprites.img[k].naturalWidth === 768 && Field.wyrdSprites.img[k].naturalHeight === 480)); }, STUB), 'The seven monster atlases load with their metadata');
  check(await page.evaluate(() => Field._debug.zones[4].portals.some(p => p.id === 'wyrd_gate' && p.to === 6)), 'Skaldholm has the East Gate to the Wyrdwood');

  // Hollowmoot: a root-town under the Elder Ash, warm timber decking, autumn all round.
  await stageAt(33, 156);
  await shot('hollowmoot');
  check(await page.evaluate(() => Field.zone === 6 && Field.zoneName === 'Wyrdwood' && Field.zoneTheme === 'wyrd'), 'The hero is in the Wyrdwood');
  check(await page.locator('#area-title b').textContent() === 'Wyrdwood' && (await page.locator('#area-title span').textContent()).includes('Hollowmoot'), 'The banner names Hollowmoot as the sanctuary');
  check(await page.locator('#city-travel').isHidden(), 'The travel button is hidden inside Hollowmoot');
  const town = await look(page, [.1, .55, .4, .9]);
  check(town.r > town.b + 15 && town.r < 190, `Hollowmoot stands on warm timber (${town.r | 0},${town.g | 0},${town.b | 0})`);
  check(await page.evaluate(() => City.npcs.filter(n => n.id.startsWith('wyrd_') || n.id.startsWith('travel_')).length === 17 && Quests.marker('wyrd_warden') === '?'), 'The people are loaded; the Moot-Warden has the arrived progression quest to turn in (?)');
  // Out in the forest the ground is autumn leaf litter.
  await stageAt(80, 140);
  await shot('forest');
  const forest = await look(page, [.25, .3, .75, .75]);
  check(forest.r > forest.b + 25 && forest.r > 60, `The south forest is autumn-toned (${forest.r | 0},${forest.g | 0},${forest.b | 0})`);
  check(await page.locator('#city-travel').isVisible() && (await page.locator('#city-travel').textContent()).includes('Hollowmoot'), 'Outside the hubs the travel button offers the nearest one (Hollowmoot)');
  // The Troll Bridge: brown planks over the gap in the river.
  await stageAt(96, 112);
  await shot('bridge');
  const deck = await look(page, [.42, .4, .58, .6]);
  check(deck.r > deck.b + 20 && deck.r > 90, `The bridge deck is timber (${deck.r | 0},${deck.g | 0},${deck.b | 0})`);
  const river = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 47) < 18 && Math.abs(d[i + 1] - 111) < 20 && Math.abs(d[i + 2] - 154) < 24 && d[i + 3] > 0) n++; return n; });
  check(river > 150, `The minimap draws the river Skuld (${river} river-coloured pixels)`);
  // Skuldwatch: the Great Beacon burns; the travel button follows the nearest hub.
  await stageAt(96, 91);
  await shot('skuldwatch');
  check((await page.locator('#area-title span').textContent()).includes('Skuldwatch') && await page.locator('#city-travel').isHidden(), 'Skuldwatch is named as the sanctuary when the hero walks in, and the travel button hides');
  check(await page.evaluate(() => { const o = Field._debug.objects.find(o => o.kind === 'beacon' && o.great); return !!o && Math.hypot(o.x - Field.hero.x, o.y - Field.hero.y) < 12; }), 'The Great Beacon stands in the fort yard');
  // The heights: stormy, grey-green moor, runestones.
  const lowSky = await look(page, [.9, 0, 1, .07]);
  await stageAt(96, 62);
  await shot('heights');
  const moor = await look(page, [.25, .3, .75, .75]);
  const highSky = await look(page, [.9, 0, 1, .07]);
  check(moor.g > moor.r - 5 && moor.g > 50, `The Highmoor is olive-green, not leaf-brown (${moor.r | 0},${moor.g | 0},${moor.b | 0})`);
  check(highSky.r < lowSky.r + 10 || highSky.b > highSky.r, `The sky darkens towards the storm (${lowSky.r | 0},${lowSky.g | 0},${lowSky.b | 0} -> ${highSky.r | 0},${highSky.g | 0},${highSky.b | 0})`);
  // The beacons are dark until a quest lights them.
  const dark = await page.evaluate(() => Quests.visited('wyrd_beacon_west') || Quests.visited('wyrd_beacon_ridge'));
  check(!dark, 'No beacon is lit before the quest');
  // The summit: Hrungnir's court, a ring of stones, the giant standing in it.
  await stageAt(104, 21);
  await shot('summit');
  check(await page.evaluate(() => Field.slimes.some(s => s.kind === 'hrungnir' && s.d.elite && s.d.name === 'Hrungnir')), 'Hrungnir stands in the summit court with an elite nameplate');
  await stageAt(152, 138);
  check(await page.evaluate(() => Field.slimes.some(s => s.kind === 'oakhorn' && s.d.elite)), 'Oakhorn stands in its grove');

  // The escort: take the quest, find Eydis, talk to her through the canvas, and she walks beside the hero while her stranded self disappears.
  await debug({ op: 'quest', id: 'wyrd_watch_welcome', action: 'finish' });
  await debug({ op: 'quest', id: 'wyrd_escort', action: 'accept' });
  await page.waitForFunction(() => Quests.markerInfo('wyrd_eydis').symbol === '◆', null, { timeout: 10000 });
  check(true, 'Eydis is marked as an objective once the escort quest is taken');
  const eydis = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'wyrd_eydis'); return { x: n.x, y: n.y }; });
  await stageAt(eydis.x + 2.2, eydis.y + 2.2);
  const [sx, sy] = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'wyrd_eydis'); return Field._debug.w2s(n.x, n.y); });
  const box = await page.locator('#fieldcv').boundingBox();
  await page.mouse.click(box.x + sx / 1600 * box.width, box.y + (sy - 55) / 900 * box.height);
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-name').textContent() === 'Eydis Mapwright', 'Clicking the stranded cartographer opens her conversation');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => Field.remotePlayers.some(r => r.escort && r.escort.npc === 'wyrd_eydis'), null, { timeout: 15000 });
  await page.waitForTimeout(800);
  await shot('escort');
  const e = await page.evaluate(() => { const r = Field.remotePlayers.find(r => r.escort); return { name: r.look.name, hp: r.hp, maxHp: r.maxHp, owner: r.escort.owner === Online.id }; });
  check(e.name === 'Eydis Mapwright' && e.owner && e.hp === e.maxHp && e.maxHp > 400, 'Eydis joins as a walker owned by this hero, with her own health');
  check(await page.evaluate(() => !!City.npcs.find(n => n.id === 'wyrd_eydis').escort), 'The stranded copy is flagged as an escort NPC (and not drawn while she walks)');
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('Safe Passage') && t.includes('Eydis')), 'The tracker shows the escort objective');
  // When her hero falls, the quest fails: the walker disappears and the stranded one is back.
  await debug({ op: 'die' });
  await page.waitForFunction(() => !Field.remotePlayers.some(r => r.escort), null, { timeout: 15000 });
  check(await page.evaluate(() => document.body.innerText.includes('Quest failed: Safe Passage')), 'The chat tells the hero the quest failed when they fell, and Eydis is gone');

  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 15000 });
  await stageAt(70, 150);
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [1000, 1001, 1002, 1003, 1004, 1005, 1006].map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 280) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(300 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state]) => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000 && s.state === state).length === 7, [state], { timeout: 10000 });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 7 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    if (state === 'idle') check((await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => s.d.name))).join() === 'Rotfang Boar,Gallowcrow,Mosshide Troll,Wyrdweaver,Stormram,Oakhorn,Hrungnir', 'The bestiary names come from the Wyrdwood table');
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  check(STUB || seen.every((hashes, i) => i === 0 || hashes.every((h, kind) => h !== seen[i - 1][kind])), `All seven monsters draw something new in each state (${seen.length} states)`);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < 1000), null, { timeout: 10000 });
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`wyrdwood-ui: ${checks} checks passed`);
})().then(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close(); process.exit(0); },
  async error => { console.error(error); await browser?.close().catch(() => {}); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); process.exit(1); });
