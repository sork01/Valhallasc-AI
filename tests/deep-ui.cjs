// Browser-only checks for Ran's Deep (levels 35-40): the data the client holds, the sea-floor sand and the pale trail, the coral walls, the
// black water beyond the outer wall, the underwater tint, Keelhaven's decks, the tidebells' circles (dim until you take a chime quest,
// amber while it waits, bright and counting while a bell rings, gold once the chain has rung), the tracker's count, the Maelstrom and the
// eight monster kinds in every clip. Rules, levels, combat and persistence are exercised by the Rust tests and the `deep` / `deep_quests`
// MCP scenarios; this asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-deep-ui', version: '1.0.0' });
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
  const world = await call('start_world', { startLevel: 38 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  // Display-only fixture: while `stage` is set, the browser's copy of each Ran's Deep snapshot gets one extra monster of every kind in a
  // chosen state, so every clip can be drawn without a hero meeting them. The server is untouched.
  let stage = null;
  const kinds = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw'];
  const levels = { draugr: 35, angler: 36, moray: 37, siren: 38, shellback: 39, kraken: 40, hvitserk: 37, ghostmaw: 39 };
  const health = { draugr: 24000, angler: 20500, moray: 27000, siren: 23500, shellback: 40000, kraken: 280000, hvitserk: 150000, ghostmaw: 190000 };
  const windup = { draugr: .55, angler: .6, moray: .25, siren: .7, shellback: .9, kraken: 1, hvitserk: .9, ghostmaw: .35 };
  const elite = new Set(['kraken', 'hvitserk', 'ghostmaw']);
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 8) return text;
    kinds.forEach((kind, i) => {
      const D = [-14, -10, -6, -2, 2, 6, 10, 14][i], x = me.x + (-8 + D) / 2, y = me.y + (-8 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: 1000 + i, kind, zone: 8, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: i, dir: 1, elite: elite.has(kind), hunt: false });
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
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('DeepUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.deepSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  await debug({ op: 'explore_all' });
  await page.waitForFunction(() => Field.explored?.length >= 9 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const stageAt = async (x, y) => {
    await debug({ op: 'teleport', zone: 8, x, y });
    await page.waitForFunction(([x, y]) => Field.zone === 8 && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
    await page.waitForTimeout(400);
  };
  const colourAt = (x, y, lift = 0) => page.evaluate(([x, y, lift]) => {
    const [sx, sy0] = Field._debug.w2s(x, y), sy = sy0 - lift, cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.max(0, Math.round((sx - 3) * k)), Math.max(0, Math.round((sy - 3) * k)), Math.max(1, Math.round(6 * k)), Math.max(1, Math.round(6 * k))).data;
    let r = 0, gr = 0, b = 0; const n = d.length / 4;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
    return { r: r / n, g: gr / n, b: b / n };
  }, [x, y, lift]);
  // Colours of the canvas along a bell's circle (24 points on the circle, 3x3 pixels each).
  const ringAt = bell => page.evaluate(w => {
    const cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d'), out = [];
    for (let i = 0; i < 24; i++) {
      const a = i / 24 * 6.283, [sx, sy] = Field._debug.w2s(w.x + Math.cos(a) * w.r, w.y + Math.sin(a) * w.r);
      const d = g.getImageData(Math.max(0, Math.round((sx - 1.5) * k)), Math.max(0, Math.round((sy - 1.5) * k)), Math.max(1, Math.round(3 * k)), Math.max(1, Math.round(3 * k))).data;
      let r = 0, gr = 0, b = 0; const n = d.length / 4;
      for (let j = 0; j < d.length; j += 4) { r += d[j]; gr += d[j + 1]; b += d[j + 2]; }
      out.push({ r: r / n, g: gr / n, b: b / n });
    }
    return out;
  }, bell);
  // The map data the client uses comes from the same file the server loads.
  const z = await page.evaluate(() => { const a = Field._debug.zones[8]; return { n: Field._debug.zones.length, name: a.name, theme: a.theme, size: a.size, levels: a.levels, city: a.city.name, camps: (a.camps || []).length, walls: a.objects.filter(o => o.kind === 'reefwall').length, bells: a.places.filter(p => p.chain).length, places: a.places.length, portals: a.portals.map(p => p.id + '>' + p.to + ':' + p.look).join(), quests: a.quests.length, npcs: a.npcs.length, chimes: a.quests.filter(q => q.objectives.some(o => o.kind === 'chime')).length, elites: a.slimes.filter(s => ['kraken', 'hvitserk', 'ghostmaw'].includes(s.kind)).length, trail: a.paths.length, bounds: a.bounds }; });
  check(z.n === 10 && z.name === "Rán's Deep" && z.theme === 'deep' && z.size === 176 && z.levels.join() === '35,40', 'The client knows Ran\'s Deep: name, deep theme, 176 tiles, levels 35-40');
  check(z.city === 'Keelhaven' && z.camps === 0 && z.walls > 300 && z.bells === 12 && z.places === 17 && z.portals === 'maelstrom_up>7:maelstrom,nacre_gate>9:undefined' && z.trail === 1, `One hub, ${z.walls} coral wall pieces, twelve bells, seventeen places, a trail and the Maelstrom up`);
  check(z.quests === 24 && z.npcs === 8 && z.chimes === 3 && z.elites === 3, 'Twenty-four quests (three of them chimes), eight people and three elites are in the data');
  check(await page.evaluate(stub => { const m = Field.deepSprites.meta; return m.kinds.join() === 'draugr,angler,moray,siren,shellback,kraken,hvitserk,ghostmaw' && (stub || m.kinds.every(k => Field.deepSprites.img[k].naturalWidth === 768 && Field.deepSprites.img[k].naturalHeight === 480)); }, STUB), 'The eight monster atlases load with their metadata (and are 768x480 each)');
  check(await page.evaluate(() => Field._debug.zones[7].portals.some(p => p.id === 'maelstrom_down' && p.to === 8 && p.look === 'maelstrom')), 'Bifrost Reach has the Maelstrom down to Ran\'s Deep');

  // Keelhaven: weathered ship decks under a bell of light, with the sea beyond.
  await stageAt(80, 160);
  await shot('keelhaven');
  check(await page.evaluate(() => Field.zone === 8 && Field.zoneName === "Rán's Deep" && Field.zoneTheme === 'deep'), 'The hero is in Ran\'s Deep');
  check(await page.locator('#area-title b').textContent() === "Rán's Deep" && (await page.locator('#area-title span').textContent()).includes('Keelhaven'), 'The banner names Keelhaven as the sanctuary');
  check(await page.locator('#city-travel').isHidden(), 'The travel button is hidden inside the hub');
  const deck = await colourAt(84, 163);
  check(deck.b > deck.r - 5 && deck.r + deck.g + deck.b < 520, `Keelhaven's decks are cool, dim timber (${deck.r | 0},${deck.g | 0},${deck.b | 0})`);
  check(await page.evaluate(() => City.npcs.filter(n => n.id.startsWith('deep_') || n.id === 'travel_keelhaven').length === 8 && Quests.marker('deep_warden') === '?'), 'The people are loaded; the warden has the arrived progression quest to turn in (?)');
  // The Shallows: teal-grey sand with the underwater tint over it, and a pale trail.
  await stageAt(34, 134);
  await shot('shallows');
  const sand = await colourAt(40, 138);
  check(sand.b > sand.r + 10 && sand.g > sand.r && sand.r + sand.g + sand.b < 330, `The Shallows are dark teal sand (${sand.r | 0},${sand.g | 0},${sand.b | 0})`);
  check(await page.locator('#city-travel').isVisible() && (await page.locator('#city-travel').textContent()).includes('Keelhaven'), 'Outside the hub the travel button offers Keelhaven');
  await stageAt(80, 130);
  const trail = await colourAt(80, 128), off = await colourAt(92, 128);
  check(trail.r > off.r + 25 && trail.r > 110, `The trail to the Net is pale shell-sand (${trail.r | 0},${trail.g | 0},${trail.b | 0}) against dark sand beside it (${off.r | 0})`);
  // The Net: pink and violet coral walls, a trail between them.
  await stageAt(96, 114);
  await shot('net-door');
  const wall = await colourAt(100, 120, 34);
  check(Math.max(wall.r, wall.b) > wall.g + 35, `Coral walls are rose and violet, not sea-coloured (${wall.r | 0},${wall.g | 0},${wall.b | 0})`);
  const mini = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let walls = 0, bells = 0, trail = 0; for (let i = 0; i < d.length; i += 4) { if (Math.abs(d[i] - 216) < 18 && Math.abs(d[i + 1] - 106) < 18 && Math.abs(d[i + 2] - 120) < 18 && d[i + 3] > 0) walls++; if (d[i] > 235 && Math.abs(d[i + 1] - 211) < 14 && d[i + 2] < 140 && d[i + 3] > 0) bells++; if (Math.abs(d[i] - 200) < 10 && Math.abs(d[i + 1] - 194) < 10 && Math.abs(d[i + 2] - 154) < 10 && d[i + 3] > 0) trail++; } return { walls, bells, trail }; });
  check(mini.walls > 400 && mini.trail > 40, `The minimap draws the Net's walls (${mini.walls} px) and the trail (${mini.trail} px)`);
  // Beyond the outer wall there is only black water.
  await stageAt(14, 100);
  const beyond = await colourAt(4, 100);
  check(beyond.r + beyond.g + beyond.b < 190 && beyond.r + beyond.g + beyond.b < sand.r + sand.g + sand.b - 60, `Past the outer wall the water is black (${beyond.r | 0},${beyond.g | 0},${beyond.b | 0})`);
  // The underwater tint: the whole frame leans blue-green.
  const frame = await page.evaluate(() => { const cv = document.getElementById('fieldcv'), d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let r = 0, g = 0, b = 0, n = 0; for (let i = 0; i < d.length; i += 40) { r += d[i]; g += d[i + 1]; b += d[i + 2]; n++; } return { r: r / n, g: g / n, b: b / n }; });
  check(frame.b > frame.r + 15 && frame.g > frame.r, `The whole view leans blue-green (${frame.r | 0},${frame.g | 0},${frame.b | 0})`);

  // The tidebells: dim until you have a chime quest, amber while it waits, bright blue while a bell rings, gold once the chain has rung.
  const bell = await page.evaluate(() => Field.place('deep_harbour_a1'));
  check(bell && bell.r === 2.6 && bell.chain === 'deep_harbour' && bell.burn === 35, 'The first harbour bell is a 2.6-tile circle of a chain that burns 35 s');
  await stageAt(bell.x + 6, bell.y + 2);
  await shot('bell-idle');
  check(await page.evaluate(() => Quests.chime('deep_harbour_a1').state === 'none'), 'With no chime quest the bell is idle');
  const idle = await ringAt(bell);
  const idleBlue = idle.reduce((m, c) => Math.max(m, c.b - c.r), -999);
  await debug({ op: 'quest', id: 'deep_welcome', action: 'finish' });
  await debug({ op: 'quest', id: 'deep_draugr', action: 'finish' });
  await debug({ op: 'quest', id: 'deep_longship', action: 'finish' });
  await debug({ op: 'quest', id: 'deep_harbour', action: 'accept' });
  await page.waitForFunction(() => Quests.chime('deep_harbour_a1').state === 'waiting', null, { timeout: 10000 });
  await page.waitForTimeout(500);
  await shot('bell-waiting');
  const waiting = await ringAt(bell);
  const amberOf = ring => ring.reduce((m, c) => Math.max(m, c.r - c.b), -999);
  check(amberOf(waiting) > amberOf(idle) + 25, `Taking the chime quest turns the circle amber (best red-minus-blue ${amberOf(waiting).toFixed(0)} against ${amberOf(idle).toFixed(0)} idle)`);
  check(await page.locator('#quest-tracker').textContent().then(t => /Ring the Harbour Bells: 0\/3 ringing/.test(t)), 'The tracker shows the objective as bells ringing (0/3 ringing)');
  await stageAt(bell.x, bell.y + 2);
  await page.waitForFunction(() => Quests.chime('deep_harbour_a1').state === 'ringing', null, { timeout: 10000 });
  await page.waitForTimeout(300);
  await shot('bell-ringing');
  const ringing = await page.evaluate(() => Quests.chime('deep_harbour_a1'));
  check(ringing.state === 'ringing' && ringing.left > 30 && ringing.left <= 35 && ringing.have === 1 && ringing.need === 3, `Standing in it rings the bell: ${ringing.left.toFixed(1)} s left, ${ringing.have} of ${ringing.need}`);
  check(await page.locator('#quest-tracker').textContent().then(t => /Ring the Harbour Bells: 1\/3 ringing/.test(t)), 'The tracker counts it (1/3 ringing)');
  const on = await ringAt(bell);
  check(on.reduce((m, c) => Math.max(m, c.b + c.g - c.r), -999) > idle.reduce((m, c) => Math.max(m, c.b + c.g - c.r), -999) + 40, 'A ringing bell draws a bright blue-white circle with its arc');
  // The time left falls, and walking away leaves the bell ringing until it is spent.
  const t0 = ringing.left;
  await stageAt(80, 165);
  await page.waitForTimeout(3200);
  const later = await page.evaluate(() => Quests.chime('deep_harbour_a1'));
  check(later.state === 'ringing' && later.left < t0 - 2.5, `The bell keeps sounding after the hero leaves, and its time falls (${later.left.toFixed(1)} s)`);
  // Done: the whole chain rung, the circle turns gold and stays so.
  await debug({ op: 'quest', id: 'deep_harbour', action: 'complete' });
  await page.waitForFunction(() => Quests.chime('deep_harbour_a1').state === 'done', null, { timeout: 10000 });
  await stageAt(bell.x + 6, bell.y + 2);
  await page.waitForTimeout(500);
  const done = (await ringAt(bell)).reduce((m, c) => (c.r - c.b > m.r - m.b ? c : m), { r: 0, g: 0, b: 255 });
  check(done.r > done.b + 20 && done.g > done.b + 12, `A rung chain glows gold (${done.r | 0},${done.g | 0},${done.b | 0})`);
  check(await page.evaluate(() => ['tidebell', 'reefwall', 'kelp', 'coral', 'clam', 'shiprib', 'anchor', 'deeprock', 'vent', 'pearllamp', 'anemone', 'sunkencolumn'].every(k => City.art[k] && Field._debug.zones[8].objects.some(o => o.kind === k)) && typeof DeepArt.maelstrom === 'function'), 'Every prop of the zone has artwork registered with the city renderer');
  // The Maelstrom up, drawn as a spout with the destination's name.
  await stageAt(80, 164);
  await shot('maelstrom');
  check(await page.evaluate(() => Field._debug.zones[8].portals[0].look === 'maelstrom'), 'The gate in Keelhaven is the Maelstrom');

  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  await stageAt(80, 90);
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007].map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 280) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(300 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state]) => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000 && s.state === state).length === 8, [state], { timeout: 10000 });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 8 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    if (state === 'idle') check((await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => s.d.name))).join() === 'Drowned Draugr,Lantern Angler,Gnashing Moray,Siren,Shellback,The Kraken,Hvitserk the Drowned,Ghostmaw', 'The bestiary names come from the Deep table');
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  const same = []; seen.forEach((hashes, i) => i && hashes.forEach((h, kind) => { if (h === seen[i - 1][kind]) same.push(`${kinds[kind]}@${i}`); }));
  check(STUB || same.length === 0, `All eight monsters draw something new in each state (${seen.length} states; unchanged: ${same.join(', ') || 'none'})`);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < 1000), null, { timeout: 10000 });
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`deep-ui: ${checks} checks passed`);
})().then(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close(); process.exit(0); },
  async error => { console.error(error); await browser?.close().catch(() => {}); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); process.exit(1); });
