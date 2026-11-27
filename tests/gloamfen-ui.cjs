// Browser-only checks for Gloamfen (levels 15-20): the summit gate, fen ground and dusk sky, the lake, thicket ridges,
// monster artwork in every state, Lanternmere's NPCs, the sixteen-quest journal and the HUD. Rules, levels, combat and
// persistence are exercised by the Rust tests and the `gloamfen` / `fen_quests` MCP scenarios; this walks with real
// canvas clicks and asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const zlib = require('node:zlib');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-gloamfen-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
// Average colour of a region of the world canvas, as fractions of its width and height.
const look = (page, [x0, y0, x1, y1] = [.15, .2, .85, .8], fenWater = false) => page.evaluate(([x0, y0, x1, y1, fenWater]) => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * x0), Math.floor(h * y0), Math.floor(w * (x1 - x0)), Math.floor(h * (y1 - y0))).data;
  let r = 0, gr = 0, b = 0, water = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) {
    r += d[i]; gr += d[i + 1]; b += d[i + 2];
    const teal = fenWater ? d[i] < 70 && d[i + 1] >= d[i] + 25 && d[i + 2] >= d[i] + 35 && d[i + 2] < 170 && d[i + 1] < 120 : d[i] < 42 && d[i + 1] >= d[i] + 14 && d[i + 2] >= d[i] + 14 && d[i + 1] + d[i + 2] < 150;
    if (teal) water++;
  }
  return { r: r / n, g: gr / n, b: b / n, water: water / n };
}, [x0, y0, x1, y1, fenWater]);
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  // Display-only fixture: while `stage` is set, the browser's copy of each glacier snapshot gets one extra monster of every
  // kind in a chosen state, so every clip can be drawn without a level-1 hero meeting them. The server is untouched.
  let stage = null;
  // Fixture ids sit far above the server's monster ids (which pass 1000 in a busy world), so a real monster can never be taken for one.
  const STAGE = 90000;
  const kinds = ['toad', 'croc', 'knight', 'hydra', 'gloomroot'];
  const levels = { toad: 15, croc: 17, knight: 18, hydra: 20, gloomroot: 20 }, health = { toad: 2000, croc: 2800, knight: 3400, hydra: 5200, gloomroot: 90000 }, windup = { toad: .45, croc: .35, knight: .6, hydra: .55, gloomroot: .85 };
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 3) return text;
    kinds.forEach((kind, i) => {
      const D = [-12, -6, 0, 6, 12][i], x = me.x + (-7 + D) / 2, y = me.y + (-7 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: STAGE + i, kind, zone: 3, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: 3, dir: i % 2 ? -1 : 1 });
    });
    // Defence in depth: actors of the other zones in a fen packet must not be shown.
    snap.slimes.push({ id: STAGE + 100, kind: 'yeti', zone: 2, level: 10, x: me.x + 2, y: me.y - 4, hx: me.x, hy: me.y, hp: 1100, maxHp: 1100, r: .4, windupTime: .6, state: 'idle', st: 1, hop: 0, hopV: 0, hurtT: 0, recT: 0, landT: 0, dead: false, dieT: 0, respawn: 0, atkCd: 1, blink: 2, seed: 1, dir: 1 });
    snap.slimes.push({ id: STAGE + 101, kind: 'green', zone: 0, level: 2, x: me.x - 2, y: me.y - 4, hx: me.x, hy: me.y, hp: 60, maxHp: 60, r: .3, windupTime: .45, state: 'idle', st: 1, hop: 0, hopV: 0, hurtT: 0, recT: 0, landT: 0, dead: false, dieT: 0, respawn: 0, atkCd: 1, blink: 2, seed: 1, dir: 1 });
    snap.players.push({ ...me, id: 'ghost-from-the-glacier', zone: 2, x: me.x + 3, y: me.y - 3 });
    return JSON.stringify(packet);
  };
  await page.routeWebSocket(/\/ws$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => server.send(message));
    // The client offers compress:true once pako is loaded, so snapshots arrive as raw-deflate binary frames: inflate, restage, send text.
    server.onMessage(message => {
      if (typeof message === 'string') return ws.send(restage(message));
      let text; try { text = zlib.inflateRawSync(message).toString('utf8'); } catch (_) { return ws.send(message); }
      const out = restage(text);
      ws.send(out === text ? message : out);
    });
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.addInitScript(`window.STAGE_ID = ${STAGE};`);
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('FenUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  // The loading screen (#connection-overlay) closes only when LoadGate has seen every asset the world asked for (LoadGate.whenIdle),
  // which can be seconds after the welcome. It covers the canvas until then: a click under it never reaches the field (the summit
  // click was lost under it, pointerdown target #connection-overlay). The first canvas click waits for it to close.
  await page.waitForFunction(() => document.getElementById('connection-overlay').hidden, null, { timeout: 60000 });
  // MUTATE=overlay brings the loading screen back over the canvas: the assertion below must fail.
  if (process.env.MUTATE === 'overlay') await page.evaluate(() => { document.getElementById('connection-overlay').hidden = false; });
  check(await page.evaluate(() => document.getElementById('connection-overlay').hidden), 'The loading screen is closed before the first canvas click');
  // The maps are fogged until a cell is visited; these checks read the whole minimap, so uncover it all first.
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.length >= 5 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  // The day-night tint follows the server clock: each colour check pins the hour it describes (the fen's night palette is teal-grey).
  const pinHour = async h => { await page.evaluate(h => Online.send({ type: 'debug', ref: 1, command: { op: 'set_time', hour: h, freeze: true } }), h); await page.waitForFunction(h => Math.abs(DayNight.hour - h) < .05, h, { timeout: 10000 }); await page.waitForTimeout(1500); };
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });

  // The map data the client uses comes from the same file the server loads.
  const zones = await page.evaluate(() => Field._debug.zones.map(z => ({ name: z.name, theme: z.theme, size: z.size, levels: z.levels, portals: z.portals.map(p => p.id + '>' + p.to), water: z.objects.filter(o => o.kind === 'water').length, thicket: z.objects.filter(o => o.kind === 'thicket').length })));
  check(zones.length === 48 && zones[3].name === 'Gloamfen' && zones[3].theme === 'fen' && zones[3].size === 280 && zones[3].levels.join() === '15,20', 'The client knows the fen: name, fen theme, 280 tiles (the authored shape), levels 15-20');
  check(['crags_gate>1', 'fen_gate>3', 'city_gate>4'].every(g => zones[2].portals.includes(g)) && zones[3].portals.includes('summit_gate>2'), 'The glacier summit has a gate to the fen, which has the gate back (other portals are the compact-atlas walking routes)');
  check(zones[3].water > 150 && zones[3].thicket >= 100, `The fen has a lake of ${zones[3].water} water discs and ${zones[3].thicket} thicket blocks`);

  // Staging only: a test shortcut puts the hero near what is under test, instead of a long walk across the map. The gate
  // crossings, the NPC clicks, the walk through the first gap and the last steps of each approach stay real.
  const click = async (x, y) => {
    // The fen's monsters chase the hero during a walk. A step with live monsters on it was sent as a plain move (no client goal), and
    // one run stopped 2.2 tiles short of such a step (143,50) with no goal and never arrived. Its monster positions were not logged,
    // so this is the probable cause, not a verified one. Defeat the live monsters near the step first (the clearMonsters kill path).
    await clearMonsters([{ x, y }]);
    // The camera eases after the walker: a click computed mid-walk lands off its step (the walk to 82,59 went wrong this way).
    // Wait until the hero has stopped and the target's screen point stops moving, then read the point and click it.
    let prev = null;
    for (let i = 0; i < 60; i++) {
      const now = await page.evaluate(([x, y]) => ({ p: Field._debug.w2s(x, y), moving: Math.hypot(Field.hero.x - Field.hero.nx, Field.hero.y - Field.hero.ny) > .02 }), [x, y]);
      if (prev && !now.moving && Math.abs(now.p[0] - prev.p[0]) < .5 && Math.abs(now.p[1] - prev.p[1]) < .5) break;
      prev = now; await page.waitForTimeout(60);
    }
    const [sx, sy] = prev.p;
    // A monster drawn over the click point takes the click as its target, and the server's Target clears the walk goal (the walk
    // stalled beside a toad that way). Such a step is sent as a plain move instead of a click.
    const crowded = await page.evaluate(([x, y, sx, sy]) => Field.slimes.some(s => {
      if (s.dead) return false;
      if (Math.hypot(s.x - x, s.y - y) < 2.5) return true;
      const [px, py] = Field._debug.w2s(s.x, s.y);
      return Math.abs(px - sx) < 60 && sy > py - 120 && sy < py + 14;
    }) || City.npcs.some(n => Math.hypot(n.x - x, n.y - y) < 2.5), [x, y, sx, sy]);
    // The canvas shows 1600 logical units across its CSS width (pointerWorld maps a click the same way), so a logical point is
    // scaled by the width alone. A 1440x900 viewport letterboxes the canvas to 810 px high, i.e. 900 logical units.
    const box = await page.locator('#fieldcv').boundingBox(), scale = box.width / 1600, logicalH = box.height / scale;
    if (crowded || sx < 60 || sx > 1540 || sy < 60 || sy > logicalH - 60) { await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [x, y]); return; }
    await page.mouse.click(box.x + sx * scale, box.y + sy * scale);
  };
  const reach = (x, y, within = .6, zone = 1) => page.waitForFunction(([x, y, within, zone]) => Field.zone !== zone || Math.hypot(Field.hero.x - x, Field.hero.y - y) < within, [x, y, within, zone], { timeout: 40000 })
    .catch(async error => { await shot('stuck'); throw Error(`Never reached ${x},${y}; hero ${JSON.stringify(await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, zone: Field.zone, goal: Field.hero.goal })))}`, { cause: error }); });
  // The fen's own monsters wander onto a scripted walk and aggro as the hero passes (toads and crocs in the chase state): a click on
  // one takes it as the target and the walk stops (seen at 143,50, 83,58 and 144,52). Before a walk, the live monsters within 10
  // tiles of its points are defeated through the ordinary kill path (debug kill_enemy).
  const clearMonsters = async points => {
    const ids = await page.evaluate(pts => Field.slimes.filter(s => !s.dead && s.id < window.STAGE_ID && pts.some(p => Math.hypot(s.x - p.x, s.y - p.y) < 10)).map(s => s.id), points);
    for (const id of ids) await page.evaluate(id => Online.send({ type: 'debug', ref: 1, command: { op: 'kill_enemy', id } }), id);
    if (ids.length) await page.waitForTimeout(1200);
    return ids.length;
  };
  const stageAt = async (zone, x, y) => {
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone, x, y } }), [zone, x, y]);
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    // The server may correct a teleport a moment later (a late snapshot clears a route set before it): wait until the sprite and the
    // server agree, so the first click after staging is not lost.
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.nx - x, Field.hero.ny - y) < 2 && Math.hypot(Field.hero.x - Field.hero.nx, Field.hero.y - Field.hero.ny) < .05, [zone, x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
  };

  // Cross the summit gate (in the middle of the Rimeveil bowl) with real canvas clicks.
  const gate = await page.evaluate(() => Field._debug.zones[2].portals.find(p => p.id === 'fen_gate'));
  // Rimeveil's land is NORTH of its fen seam line (the fen is south): stand north of the gate and walk south across it.
  await stageAt(2, gate.x, gate.y - 8);
  const glacierGate = await look(page);
  await clearMonsters([{ x: gate.x, y: gate.y - 4 }, { x: gate.x, y: gate.y + 1.2 }]);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [gate.x, gate.y - 4])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 2); }
  await page.waitForTimeout(900);
  await shot('gate-summit');
  check(await page.evaluate(() => Field.zone === 2), 'Still on the glacier in front of the new gate');
  check(glacierGate.b > glacierGate.r, `The glacier is still cold-toned at the summit (${glacierGate.r | 0},${glacierGate.g | 0},${glacierGate.b | 0})`);
  await click(gate.x, gate.y + 1.2);
  await page.waitForFunction(() => Field.zone === 3, null, { timeout: 30000 });
  await page.waitForTimeout(900);
  await shot('fen-arrival');
  const fenState = await page.evaluate(() => ({ zone: Field.zone, name: Field.zoneName, theme: Field.zoneTheme }));
  check(fenState.zone === 3 && fenState.name === 'Gloamfen' && fenState.theme === 'fen', `Walking into the gate moves the hero into the fen (${JSON.stringify(fenState)})`);
  // The arrival is on the fen's north shore, so the banner names the authored region there; Lanternmere's name needs the town box.
  const banner = { b: await page.locator('#area-title b').textContent(), span: await page.locator('#area-title span').textContent() };
  check(banner.b === 'The Old Quarter' && banner.span.includes('Recommended levels 15'), `The arrival banner names the fen region beside the gate (${JSON.stringify(banner)})`);
  // The fen's authored monsters (world/map.txt: toads, crocs, knights, hydras, the gloomroot, two elites) are level 13-22. The map
  // also places three ambush sleepers here (a raid-key Firelord at 99, the Empty Seat foe and the Halloween Hollow Rider).
  const fenKinds = ['toad', 'croc', 'knight', 'hydra', 'gloomroot', 'bellowmaw', 'rustmarshal'], ambushKinds = ['ember_firelord', 'hollow_rider', 'es_foe_04'];
  const badSlimes = await page.evaluate(([fenKinds, ambushKinds]) => Field.slimes.filter(s => !(s.zone === 3 && Number.isInteger(s.level) && (fenKinds.includes(s.kind) ? s.level >= 13 && s.level <= 22 : ambushKinds.includes(s.kind)))).map(s => ({ kind: s.kind, zone: s.zone, level: s.level })), [fenKinds, ambushKinds]);
  check(await page.evaluate(() => Field.slimes.length > 0) && badSlimes.length === 0, `Only fen enemies (and the three ambush sleepers), each with an integer level, are shown (${JSON.stringify(badSlimes)})`);
  // The fen atlases load when the first fen enemy is in view (after the walk into the fen), not at login.
  await page.waitForFunction(() => !!Field.fenSprites?.meta, null, { timeout: 60000 });
  // Each fen atlas is an 8 x 5 grid of frames at its own frame size (client/assets/fen.txt kindFrames), so the size is derived per kind.
  const fenManifest = JSON.parse(fs.readFileSync(path.join(path.resolve(__dirname, '..'), 'client/assets/fen.txt'), 'utf8'));
  const fenFrames = Object.fromEntries(Object.entries(fenManifest.kindFrames).map(([k, v]) => [k, v.frame]));
  check(await page.evaluate(([stub, kinds, frames]) => { const m = Field.fenSprites.meta; return m.kinds.join() === kinds.join() && (stub || m.kinds.every(k => Field.fenSprites.img[k].naturalWidth === frames[k][0] * 8 && Field.fenSprites.img[k].naturalHeight === frames[k][1] * 5)); }, [STUB, fenManifest.kinds, fenFrames]), 'The four fen monster atlases are loaded (8 x 5 frames of each kind\'s size on the real art)');
  check(await page.evaluate(() => Field.remotePlayers.length === 0), 'Nobody else is shown (only players in this zone are drawn)');
  // The night sky beyond the map's north edge (top-right corner of the screen): dark, cool and blue-grey (the fen's night palette).
  await pinHour(22);
  const sky = [await look(page, [.9, 0, 1, .07])];
  check(sky.every(s => s.r < 90 && s.b >= s.g && s.g >= s.r), `The sky is a dark cool night over the fen (${sky.map(s => `${s.r | 0},${s.g | 0},${s.b | 0}`).join(' / ')})`);
  const lake = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 36) < 12 && Math.abs(d[i + 1] - 79) < 12 && Math.abs(d[i + 2] - 92) < 12 && d[i + 3] > 0) n++; return n; });
  check(lake > 400, `The minimap draws the mere (${lake} lake-coloured pixels)`);

  // The journal holds only quests taken; the first town conversation through the walk to the reeve.
  await page.keyboard.press('q');
  // A new hero already holds Greenmeadow's landing quests; the point is that no fen quest is listed before it is taken.
  const journal = { shown: await page.locator('#quest-journal').isVisible(), fen: await page.locator('#quest-list [data-quest^="fen_"]').count(), list: (await page.locator('#quest-list').textContent()).slice(0, 160) };
  check(journal.shown && journal.fen === 0, `The journal lists no fen quest that has not been taken (${JSON.stringify(journal)})`);
  // The data behind the fen quests: levels, the five-player elite and its blue ring.
  const catalogue = await page.evaluate(() => { const q = WORLD_MAP.zones.flatMap(z => z.quests || []); const e = q.find(x => x.id === 'fen_gloomroot'); const item = e && WORLD_ITEMS.find(i => i.id === e.rewardItem); return { fen: q.filter(x => x.id.startsWith('fen_')).length, hydraLevel: q.find(x => x.id === 'fen_hydra_hunt')?.level, players: e?.recommendedPlayers, level: e?.level, reward: e?.rewardItem, rarity: item?.rarity }; });
  check(catalogue.fen === 34 && catalogue.hydraLevel === 20 && catalogue.players === 5 && catalogue.level === 20 && catalogue.rarity === 'rare', `The fen catalogue has 34 fen quests and the five-player elite pays a blue ring (${JSON.stringify(catalogue)})`);
  await page.keyboard.press('Escape');
  await page.evaluate(() => Field.visitNpc('fen_reeve'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-name').textContent() === 'Reeve Osric', 'Journal travel reaches the town reeve');
  await page.locator('#npc-quest-list .journal-quest[data-quest="fen_welcome"]').click();
  await page.locator('#npc-dialogue [data-action="accept"]').click();
  // Accepting closes the conversation; the live tracker shows the quest once the server's ledger has it.
  await page.waitForFunction(() => document.querySelector('#quest-tracker')?.textContent.includes('Lights on the Water'), null, { timeout: 30000 });
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('Lights on the Water') && t.includes('Lamplighter Wren')), 'The introduction appears in the live tracker');
  // Accepting already closed the conversation; a bare Escape would open the pause menu and block the canvas clicks below.
  if (await page.locator('#npc-dialogue').isVisible()) await page.keyboard.press('Escape');
  const townNpcs = await page.evaluate(() => ({ ids: City.npcs.map(n => n.id), marker: Quests.marker('fen_ranger') }));
  // The fen now also holds its outposts and mailboxes, so the town is checked by its people: the reeve and six, and the travel master.
  const townPeople = ['fen_reeve', 'fen_lamplighter', 'fen_healer', 'fen_trader', 'fen_ranger', 'fen_scholar', 'fen_ferryman', 'travel_lanternmere'];
  check(townPeople.every(id => townNpcs.ids.includes(id)) && townNpcs.marker === '◆', `The town NPCs, travel master and talk-objective markers are shown (${JSON.stringify(townNpcs)})`);
  await page.getByRole('button', { name: 'Collapse quest tracker' }).click();
  await page.waitForTimeout(700);
  for (const id of ['fen_lamplighter', 'fen_healer', 'fen_trader', 'fen_ranger', 'fen_scholar', 'fen_ferryman']) {
    // The town is wider than one screen: stage the hero beside the NPC (the click on the NPC stays real).
    const at = await page.evaluate(id => { const n = City.npcs.find(n => n.id === id); return { x: n.x, y: n.y }; }, id);
    await stageAt(3, at.x + 2.6, at.y + 2.6);
    const [sx, sy] = await page.evaluate(id => { const n = City.npcs.find(n => n.id === id); return Field._debug.w2s(n.x, n.y); }, id);
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + (sy - 55) / 900 * box.height);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 }).catch(async error => {
      await shot('town-interaction-stuck');
      throw Error(`NPC ${id}, click ${sx},${sy}: ${JSON.stringify(await page.evaluate(([id, sx, sy]) => { const n = City.npcs.find(n => n.id === id); return { hero: { x: Field.hero.x, y: Field.hero.y, goal: Field.hero.goal }, npc: n && { x: n.x, y: n.y, zone: Field.zone }, under: (e => e && `${e.tagName}#${e.id}.${e.className}`)(document.elementFromPoint(sx, sy)), canvasBox: (c => c && [c.left, c.top, c.width, c.height])(document.getElementById('fieldcv').getBoundingClientRect()), w2sNpc: [sx, sy], cv: Field.zone, dialogue: getComputedStyle(document.querySelector('#npc-dialogue')).display }; }, [id, box.x + sx / 1600 * box.width, box.y + (sy - 55) / 900 * box.height]))}`, { cause: error });
    });
    check(await page.locator('#npc-name').textContent() === await page.evaluate(id => City.npcs.find(n => n.id === id).name, id), `Canvas interaction reaches ${id}`);
    if (id === 'fen_healer') check((await page.locator('#npc-dialogue').textContent()).includes('Health Potion'), `Sister Maren offers healing supplies (${(await page.locator('#npc-dialogue').textContent()).replace(/\s+/g, ' ').slice(0, 300)})`);
    if (id === 'fen_trader') {
      // Merchants list their stock behind the Buy tab (`#merchant-stock`), not in the greeting.
      await page.locator('#npc-offers [data-view="buy"]').click();
      await page.waitForFunction(() => Shop.open && !!document.querySelector('#merchant-stock'), null, { timeout: 15000 });
      const stock = await page.locator('#merchant-stock').textContent();
      check(stock.includes('Stew') && stock.includes('Satchel'), 'Trader Torvald offers food and bags');
    }
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
  }
  const townBanner = { b: await page.locator('#area-title b').textContent(), span: await page.locator('#area-title span').textContent(), hero: await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y })) };
  check(townBanner.b === 'Lanternmere' && townBanner.span.includes('Sanctuary'), `The area banner names Lanternmere in the town (${JSON.stringify(townBanner)})`);
  // Looked at inside the town at midday (the arrival view shows the mere, not the decking; the night palette is cool).
  await pinHour(12);
  const town = await look(page, [.35, .4, .65, .6]);
  check(town.r > town.b + 10 && town.r < 190, `Lanternmere stands on warm timber decking (${town.r | 0},${town.g | 0},${town.b | 0})`);
  check(await page.locator('#city-travel').isHidden(), 'The travel button is hidden inside Lanternmere');
  await page.keyboard.press('q');
  const introduction = page.locator('#quest-list [data-quest="fen_welcome"]');
  await page.waitForTimeout(500);
  // The journal row opens its detail page (the old folded row with a summary is gone): the page says the quest is ready to turn in.
  await introduction.click();
  const detail = page.locator('#quest-journal article.journal-detail[data-quest="fen_welcome"]');
  await detail.locator('.quest-state').waitFor({ state: 'visible' });
  check((await detail.locator('.quest-state').textContent()).includes('Ready to turn in'), 'All six town conversations complete the introduction');
  await detail.locator('button').filter({ hasText: 'Return to Reeve Osric' }).click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  await page.locator('#npc-quest-list .journal-quest[data-quest="fen_welcome"]').click();
  await page.locator('#npc-dialogue [data-action="claim"]').click();
  await page.waitForFunction(() => !document.querySelector('#npc-quest-list [data-quest="fen_welcome"]'));
  check(await page.evaluate(() => Quests.marker('fen_ranger') === '!' && Quests.markerInfo('fen_trader').repeatable), 'Turn-in unlocks the toad hunt and the repeatable town patrol');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Expand quest tracker' }).click();
  await shot('lanternmere');

  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [0, 1, 2, 3, 4].map(i => window.STAGE_ID + i).map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 250) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(270 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state]) => Field.slimes.filter(s => s.id >= window.STAGE_ID && s.id < window.STAGE_ID + 100 && s.state === state).length === 5, [state], { timeout: 10000 }).catch(async error => {
      throw Error(`The ${state} packet fixture never reached the browser: ${JSON.stringify(await page.evaluate(() => ({ zone: Field.zone, hero: { x: Field.hero.x, y: Field.hero.y }, injected: Field.slimes.filter(s => s.id >= window.STAGE_ID && s.id < window.STAGE_ID + 100).map(s => [s.id, s.state, s.zone]), count: Field.slimes.length, ids: Field.slimes.slice(0, 12).map(s => [s.id, s.kind, s.zone]) })))}`, { cause: error });
    });
    await page.evaluate(() => { Field.hero.target = Field.slimes.find(s => s.id === window.STAGE_ID + 2) || null; });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    check(await page.evaluate(() => Field.slimes.every(s => s.zone === 3) && Field.remotePlayers.length === 0), `A glacier monster, a meadow monster and a glacier player in the ${state} packet are not shown`);
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= window.STAGE_ID && s.id < window.STAGE_ID + 100).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 5 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    if (state === 'idle') check((await page.evaluate(() => Field.slimes.filter(s => s.id >= window.STAGE_ID && s.id < window.STAGE_ID + 100).map(s => s.d.name))).join() === 'Fen Toad,Mire Crocodile,Drowned Knight,Mire Hydra,Gloomroot Colossus', 'The bestiary names come from the fen table');
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  check(STUB || seen.every((hashes, i) => i === 0 || hashes.every((h, kind) => h !== seen[i - 1][kind])), `All five monsters draw something new in each state (${seen.length} states)`);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < window.STAGE_ID), null, { timeout: 10000 });
  await page.evaluate(() => { Field.hero.target = null; });

  // A real walk along the client's own route, across the fen's central land (80,50) to (82,60), 14 tiles, every cell of the route on
  // land and 3.5+ tiles from the summit seam. The walk stays on the central land, away from the north-west corner; a walker that
  // walks back over the summit line returns to Rimeveil by design (the arrival sits inside the seam's reach), so this route is kept
  // short of it.
  const shore = { x: 82, y: 60 };
  await stageAt(3, 80, 50);
  await clearMonsters([{ x: 80, y: 50 }, shore]);
  const route = await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [shore.x, shore.y]);
  check(route.length >= 2, `The client routes across the fen's central land (${route.length} steps)`);
  for (const step of route) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 3); }
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.waitForTimeout(800);
  await shot('fen-west-gap');
  const inside = await look(page);
  const walked = await page.evaluate(() => ({ zone: Field.zone, x: Field.hero.x, y: Field.hero.y, goal: Field.hero.goal }));
  check(walked.zone === 3 && Math.hypot(walked.x - shore.x, walked.y - shore.y) < 2, `The hero walked the route and stands at its end (${JSON.stringify(walked)})`);
  check(inside.g > inside.r && inside.g > inside.b && inside.r + inside.g + inside.b < 360, `The ground is dark fen green (${inside.r | 0},${inside.g | 0},${inside.b | 0}), not snow or ember`);
  // The ridge list the client keeps is the authored one: world/map.txt's Gloamfen block (a top-level zone is zone index + 1, so zones[2]).
  const authoredFen = JSON.parse(fs.readFileSync(path.join(path.resolve(__dirname, '..'), 'world/map.txt'), 'utf8')).zones[2];
  const authoredThickets = authoredFen.objects.filter(o => o.kind === 'thicket').length, clientThickets = await page.evaluate(() => Field._debug.objects.filter(o => o.kind === 'thicket').length);
  check(authoredFen.name === 'Gloamfen' && authoredThickets > 0 && clientThickets === authoredThickets, `The client keeps the whole thicket ridge list as obstacles (${clientThickets} of ${authoredThickets} authored)`);
  // The mere from the west shore (staged): the lake lies west of the staging point, so the water is read from the left of the view.
  // Mere water is teal-grey at night (about 33,73,102 on the night-tinted ground), which the old daylight test (green < 90, blue < 60)
  // did not reach; the classifier below accepts it.
  await stageAt(3, 41, 68);
  await page.waitForTimeout(700);
  await shot('fen-lake');
  const mere = await look(page, [0, .2, .5, .9], true);
  check(mere.water > .05, `The mere is drawn as dark teal water (${(mere.water * 100).toFixed(1)}% of the west of the view)`);
  // The standing stones (spires) of the fen: the six-stone cluster at (105,65), read from the authored map (zones[2] is Gloamfen).
  const stones = authoredFen.objects.filter(o => o.kind === 'spire' && Math.hypot(o.x - 105, o.y - 65) < 8);
  await stageAt(3, 105, 65);
  await page.waitForTimeout(700);
  await shot('fen-stones');
  const drawnStones = await page.evaluate(() => Field._debug.objects.filter(o => o.kind === 'spire' && Math.hypot(o.x - 105, o.y - 65) < 8).length);
  check(stones.length >= 5 && drawnStones === stones.length && await page.evaluate(() => Math.hypot(Field.hero.x - 105, Field.hero.y - 65) < 4), `The standing stones of the cluster at 105,65 are drawn (${drawnStones} of ${stones.length} authored)`);

  // Back out through the summit gate by clicking.
  const back = await page.evaluate(() => Field._debug.zones[3].portals[0]);
  await stageAt(3, back.x, back.y + 7);
  await clearMonsters([{ x: back.x, y: back.y + 7 }, { x: back.x, y: back.y + 3 }, { x: back.x, y: back.y - 1.2 }]);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [back.x, back.y + 3])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 3); }
  await page.waitForTimeout(900);
  await shot('gate-fen');
  await click(back.x, back.y - 1.2);
  await page.waitForFunction(() => Field.zone === 2, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  const returnBanner = { b: await page.locator('#area-title b').textContent(), span: await page.locator('#area-title span').textContent() };
  // The banner names the glacier region beside the gate (The Southern Drifts, an authored name in world/map.txt) with the glacier's levels.
  const rime = JSON.parse(fs.readFileSync(path.join(path.resolve(__dirname, '..'), 'world/map.txt'), 'utf8')).zones[1];
  check(rime.name === 'Rimeveil Glacier' && !!returnBanner.b && JSON.stringify(fs.readFileSync(path.join(path.resolve(__dirname, '..'), 'world/map.txt'), 'utf8')).includes(returnBanner.b) && returnBanner.span.includes(`Recommended levels ${rime.levels[0]}–${rime.levels[1]}`), `Returning restores the glacier banner beside the gate (${JSON.stringify(returnBanner)})`);
  check(await page.evaluate(([x, y]) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [back.tx, back.ty]), 'The summit gate arrives beside the Gloamfen gate');
  check(await page.evaluate(() => Field.slimes.length > 0 && Field.slimes.every(s => s.zone === 2)), 'Back on the glacier only glacier enemies are shown');
  const again = await look(page);
  check(again.b > again.r, `The glacier is cold-toned again (${again.r | 0},${again.g | 0},${again.b | 0})`);
  await shot('glacier-again');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} focused fen UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
