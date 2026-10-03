// Browser-only checks for Gloamfen (levels 15-20): the summit gate, fen ground and dusk sky, the lake, thicket ridges,
// monster artwork in every state, Lanternmere's NPCs, the sixteen-quest journal and the HUD. Rules, levels, combat and
// persistence are exercised by the Rust tests and the `gloamfen` / `fen_quests` MCP scenarios; this walks with real
// canvas clicks and asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
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
const look = (page, [x0, y0, x1, y1] = [.15, .2, .85, .8]) => page.evaluate(([x0, y0, x1, y1]) => {
  const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), w = cv.width, h = cv.height;
  const d = g.getImageData(Math.floor(w * x0), Math.floor(h * y0), Math.floor(w * (x1 - x0)), Math.floor(h * (y1 - y0))).data;
  let r = 0, gr = 0, b = 0, water = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; if (d[i] < 42 && d[i + 1] >= d[i] + 14 && d[i + 2] >= d[i] + 14 && d[i + 1] + d[i + 2] < 150) water++; }
  return { r: r / n, g: gr / n, b: b / n, water: water / n };
}, [x0, y0, x1, y1]);
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
  const kinds = ['toad', 'croc', 'knight', 'hydra', 'gloomroot'];
  const levels = { toad: 15, croc: 17, knight: 18, hydra: 20, gloomroot: 20 }, health = { toad: 2000, croc: 2800, knight: 3400, hydra: 5200, gloomroot: 90000 }, windup = { toad: .45, croc: .35, knight: .6, hydra: .55, gloomroot: .85 };
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 3) return text;
    kinds.forEach((kind, i) => {
      const D = [-12, -6, 0, 6, 12][i], x = me.x + (-7 + D) / 2, y = me.y + (-7 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: 1000 + i, kind, zone: 3, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: 3, dir: i % 2 ? -1 : 1 });
    });
    // Defence in depth: actors of the other zones in a fen packet must not be shown.
    snap.slimes.push({ id: 2000, kind: 'yeti', zone: 2, level: 10, x: me.x + 2, y: me.y - 4, hx: me.x, hy: me.y, hp: 1100, maxHp: 1100, r: .4, windupTime: .6, state: 'idle', st: 1, hop: 0, hopV: 0, hurtT: 0, recT: 0, landT: 0, dead: false, dieT: 0, respawn: 0, atkCd: 1, blink: 2, seed: 1, dir: 1 });
    snap.slimes.push({ id: 2001, kind: 'green', zone: 0, level: 2, x: me.x - 2, y: me.y - 4, hx: me.x, hy: me.y, hp: 60, maxHp: 60, r: .3, windupTime: .45, state: 'idle', st: 1, hop: 0, hopV: 0, hurtT: 0, recT: 0, landT: 0, dead: false, dieT: 0, respawn: 0, atkCd: 1, blink: 2, seed: 1, dir: 1 });
    snap.players.push({ ...me, id: 'ghost-from-the-glacier', zone: 2, x: me.x + 3, y: me.y - 3 });
    return JSON.stringify(packet);
  };
  await page.routeWebSocket(/\/ws$/, ws => {
    const server = ws.connectToServer();
    ws.onMessage(message => server.send(message));
    server.onMessage(message => ws.send(typeof message === 'string' ? restage(message) : message));
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('FenUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.fenSprites && !!Field.rimeSprites, null, { timeout: 60000 });
  // The maps are fogged until a cell is visited; these checks read the whole minimap, so uncover it all first.
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.length >= 5 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });

  // The map data the client uses comes from the same file the server loads.
  const zones = await page.evaluate(() => Field._debug.zones.map(z => ({ name: z.name, theme: z.theme, size: z.size, levels: z.levels, portals: z.portals.map(p => p.id + '>' + p.to), water: z.objects.filter(o => o.kind === 'water').length, thicket: z.objects.filter(o => o.kind === 'thicket').length })));
  check(zones.length === 6 && zones[3].name === 'Gloamfen' && zones[3].theme === 'fen' && zones[3].size === 128 && zones[3].levels.join() === '15,20', 'The client knows the fen: name, fen theme, 128 tiles, levels 15-20');
  check(zones[2].portals.join() === 'crags_gate>1,fen_gate>3,city_gate>4' && zones[3].portals.join() === 'summit_gate>2', 'The glacier summit has a gate to the fen, which has the gate back');
  check(zones[3].water > 150 && zones[3].thicket > 100, `The fen has a lake of ${zones[3].water} water discs and ${zones[3].thicket} thicket blocks`);
  check(await page.evaluate(stub => { const m = Field.fenSprites.meta; return m.kinds.join() === 'toad,croc,knight,hydra,gloomroot' && (stub || m.kinds.every(k => Field.fenSprites.img[k].naturalWidth === 768 && Field.fenSprites.img[k].naturalHeight === 480)); }, STUB), 'The four fen monster atlases are loaded (768x480 on the real art)');

  // Staging only: a test shortcut puts the hero near what is under test, instead of a long walk across the map. The gate
  // crossings, the NPC clicks, the walk through the first gap and the last steps of each approach stay real.
  const click = async (x, y) => {
    const [sx, sy] = await page.evaluate(([x, y]) => Field._debug.w2s(x, y), [x, y]);
    const crowded = await page.evaluate(([x, y]) => Field.slimes.some(s => !s.dead && Math.hypot(s.x - x, s.y - y) < 2.5) || City.npcs.some(n => Math.hypot(n.x - x, n.y - y) < 2.5), [x, y]);
    if (crowded || sx < 60 || sx > 1540 || sy < 60 || sy > 840) { await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [x, y]); return; }
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + sy / 900 * box.height);
  };
  const reach = (x, y, within = .6, zone = 1) => page.waitForFunction(([x, y, within, zone]) => Field.zone !== zone || Math.hypot(Field.hero.x - x, Field.hero.y - y) < within, [x, y, within, zone], { timeout: 40000 })
    .catch(async error => { await shot('stuck'); throw Error(`Never reached ${x},${y}; hero ${JSON.stringify(await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, zone: Field.zone, goal: Field.hero.goal })))}`, { cause: error }); });
  const stageAt = async (zone, x, y) => {
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone, x, y } }), [zone, x, y]);
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
  };

  // Cross the summit gate (in the middle of the Rimeveil bowl) with real canvas clicks.
  const gate = await page.evaluate(() => Field._debug.zones[2].portals.find(p => p.id === 'fen_gate'));
  await stageAt(2, gate.x, gate.y + 8);
  const glacierGate = await look(page);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [gate.x, gate.y + 4])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 2); }
  await page.waitForTimeout(900);
  await shot('gate-summit');
  check(await page.evaluate(() => Field.zone === 2), 'Still on the glacier in front of the new gate');
  check(glacierGate.b > glacierGate.r, `The glacier is still cold-toned at the summit (${glacierGate.r | 0},${glacierGate.g | 0},${glacierGate.b | 0})`);
  await click(gate.x, gate.y - 1.2);
  await page.waitForFunction(() => Field.zone === 3, null, { timeout: 30000 });
  await page.waitForTimeout(900);
  await shot('fen-arrival');
  check(await page.evaluate(() => Field.zone === 3 && Field.zoneName === 'Gloamfen' && Field.zoneTheme === 'fen'), 'Walking into the gate moves the hero into the fen');
  check(await page.locator('#area-title b').textContent() === 'Gloamfen' && (await page.locator('#area-title span').textContent()).includes('Lanternmere'), 'The area banner identifies Lanternmere as the quest hub and sanctuary');
  check(await page.locator('#city-travel').isHidden(), 'The Alderhaven travel button is hidden inside the town');
  check(await page.evaluate(() => Field.slimes.length > 0 && Field.slimes.every(s => s.zone === 3 && Number.isInteger(s.level) && s.level >= 13 && s.level <= 22)), 'Only fen enemies, each with an integer level, are shown');
  check(await page.evaluate(() => Field.remotePlayers.length === 0), 'Nobody else is shown (only players in this zone are drawn)');
  // A violet dusk: the sky beyond the map's north edge (the top-right corner of the screen) is dark and bluish-violet.
  const sky = [await look(page, [.9, 0, 1, .07])];
  check(sky.every(s => s.r < 90 && s.b > s.r + 8 && s.b >= s.g), `The sky is a dark violet dusk (${sky.map(s => `${s.r | 0},${s.g | 0},${s.b | 0}`).join(' / ')})`);
  const town = await look(page, [.35, .4, .65, .6]);
  check(town.r > town.b + 10 && town.r < 190, `Lanternmere stands on warm timber decking (${town.r | 0},${town.g | 0},${town.b | 0})`);
  const lake = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 36) < 12 && Math.abs(d[i + 1] - 79) < 12 && Math.abs(d[i + 2] - 92) < 12 && d[i + 3] > 0) n++; return n; });
  check(lake > 400, `The minimap draws the mere (${lake} lake-coloured pixels)`);

  // The journal: sixteen fen quests, local ones first, the first town conversation through real clicks.
  await page.keyboard.press('q');
  check(await page.locator('#quest-journal').isVisible() && (await page.locator('#quest-list [data-quest="welcome"]').textContent()).includes('is back in Greenmeadow'), 'Meadow quests explain that their givers are in Greenmeadow');
  check(await page.locator('#quest-list [data-quest^="fen_"]').count() === 18 && await page.locator('#quest-list [data-quest^="rime_"]').count() === 14 && await page.locator('#quest-list [data-quest^="crags_"]').count() === 14, 'The journal lists all eighteen fen quests beside the fourteen glacier and fourteen Crags quests');
  check(await page.locator('#quest-list .quest-card').first().getAttribute('data-quest') === 'fen_welcome', 'Local town quests sort first');
  check(await page.locator('#quest-list [data-quest="fen_crocs"]').textContent().then(t => t.includes('Locked') && t.includes('The Choir in the Reeds')), 'Later hunts explain their prerequisite');
  check(await page.locator('#quest-list [data-quest="fen_hydra_hunt"]').textContent().then(t => t.includes('Recommended level 20')), 'The journal shows each quest\'s recommended level');
  // The elite quest: five players, a guaranteed blue ring, shown in the journal.
  check(await page.locator('#quest-list [data-quest="fen_gloomroot"]').textContent().then(t => t.includes('Group: 5 players') && t.includes('Recommended level 20') && t.includes('Celestial Amber Ring') && t.includes('Rare (blue)')), 'The journal shows the five-player elite quest and its blue ring');
  check(await page.locator('#quest-list [data-quest="fen_gloomroot"] [data-rarity="rare"]').count() === 1, 'The reward line carries the blue rarity');
  await page.locator('#quest-list [data-quest="fen_welcome"] button').filter({ hasText: 'Get quest from Reeve Osric' }).click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-name').textContent() === 'Reeve Osric', 'Journal travel reaches the town reeve');
  await page.locator('#npc-quests .gossip-row[data-quest="fen_welcome"]').click();
  await page.locator('#npc-quests [data-quest="fen_welcome"] [data-action="accept"]').click();
  await page.waitForFunction(() => document.querySelector('#npc-quests .gossip-row[data-quest="fen_welcome"]')?.dataset.status === 'active');
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('Lights on the Water') && t.includes('Lamplighter Wren')), 'The introduction appears in the live tracker');
  await page.keyboard.press('Escape');
  check(await page.evaluate(() => City.npcs.length === 8 && City.npcs.every(n => n.id.startsWith('fen_') || n.id === 'travel_lanternmere') && Quests.marker('fen_ranger') === '◆'), 'The town NPCs, travel master and talk-objective markers are shown');
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
      throw Error(`NPC ${id}, click ${sx},${sy}: ${JSON.stringify(await page.evaluate(() => ({ hero: { x: Field.hero.x, y: Field.hero.y, goal: Field.hero.goal } })))}`, { cause: error });
    });
    check(await page.locator('#npc-name').textContent() === await page.evaluate(id => City.npcs.find(n => n.id === id).name, id), `Canvas interaction reaches ${id}`);
    if (id === 'fen_healer') check((await page.locator('#npc-offers').textContent()).includes('Health Potion'), 'Sister Maren offers healing supplies');
    if (id === 'fen_trader') check((await page.locator('#npc-offers').textContent()).includes('Stew') && (await page.locator('#npc-offers').textContent()).includes('Satchel'), 'Trader Torvald offers food and bags');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
  }
  await page.keyboard.press('q');
  const introduction = page.locator('#quest-list [data-quest="fen_welcome"]');
  check((await introduction.textContent()).includes('Ready to turn in'), 'All six town conversations complete the introduction');
  await introduction.locator('button').filter({ hasText: 'Return to Reeve Osric' }).click();
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  await page.locator('#npc-quests .gossip-row[data-quest="fen_welcome"]').click();
  await page.locator('#npc-quests [data-quest="fen_welcome"] [data-action="claim"]').click();
  await page.waitForFunction(() => !document.querySelector('#npc-quests [data-quest="fen_welcome"]'));
  check(await page.evaluate(() => Quests.marker('fen_ranger') === '!' && Quests.markerInfo('fen_trader').repeatable), 'Turn-in unlocks the toad hunt and the repeatable town patrol');
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Expand quest tracker' }).click();
  await shot('lanternmere');

  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [1000, 1001, 1002, 1003, 1004].map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 250) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(270 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state]) => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000 && s.state === state).length === 5, [state], { timeout: 10000 });
    await page.evaluate(() => { Field.hero.target = Field.slimes.find(s => s.id === 1002) || null; });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    check(await page.evaluate(() => Field.slimes.every(s => s.zone === 3) && Field.remotePlayers.length === 0), `A glacier monster, a meadow monster and a glacier player in the ${state} packet are not shown`);
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 5 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    if (state === 'idle') check((await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => s.d.name))).join() === 'Fen Toad,Mire Crocodile,Drowned Knight,Mire Hydra,Gloomroot Colossus', 'The bestiary names come from the fen table');
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  check(STUB || seen.every((hashes, i) => i === 0 || hashes.every((h, kind) => h !== seen[i - 1][kind])), `All five monsters draw something new in each state (${seen.length} states)`);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < 1000), null, { timeout: 10000 });
  await page.evaluate(() => { Field.hero.target = null; });

  // Through the first gap in the northern thicket: a real walk along the client's own route, from the boardwalk to the west bank.
  await stageAt(3, 30, 33);
  const route = await page.evaluate(() => Field._debug.routeTo({ x: 18, y: 41 }));
  check(route.length >= 2, `The client routes through the west gap (${route.length} steps)`);
  for (const step of route) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 3); }
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.waitForTimeout(800);
  await shot('fen-west-gap');
  const inside = await look(page);
  check(await page.evaluate(() => Field.zone === 3 && Field.hero.y > 38.5), 'The hero walked through the gap and stands on the west bank');
  check(inside.g > inside.r && inside.g > inside.b && inside.r + inside.g + inside.b < 360, `The ground is dark fen green (${inside.r | 0},${inside.g | 0},${inside.b | 0}), not snow or ember`);
  check(await page.evaluate(() => Field._debug.objects.filter(o => o.kind === 'thicket').length > 100), 'The client keeps the whole thicket ridge list as obstacles');
  // The lake from the west shore (staged): dark teal water fills a good part of the view.
  await stageAt(3, 41, 68);
  await page.waitForTimeout(700);
  await shot('fen-lake');
  const mere = await look(page, [.45, .3, .95, .75]);
  check(mere.water > .05, `The mere is drawn as dark teal water (${(mere.water * 100).toFixed(1)}% of the view)`);
  // The causeway and the island, for a look at the standing stones (staged).
  await stageAt(3, 76, 76);
  await page.waitForTimeout(700);
  await shot('fen-island');
  check(await page.evaluate(() => Field.zone === 3 && Math.hypot(Field.hero.x - 66, Field.hero.y - 76) < 12), 'The causeway leads to the island, which is drawn');

  // Back out through the summit gate by clicking.
  const back = await page.evaluate(() => Field._debug.zones[3].portals[0]);
  await stageAt(3, back.x, back.y + 7);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [back.x, back.y + 3])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 3); }
  await page.waitForTimeout(900);
  await shot('gate-fen');
  await click(back.x, back.y - 1.2);
  await page.waitForFunction(() => Field.zone === 2, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  check(await page.locator('#area-title b').textContent() === 'Rimeveil Glacier', 'Returning restores the glacier banner');
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
