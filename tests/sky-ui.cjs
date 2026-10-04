// Browser-only checks for Bifrost Reach (levels 30-35): the data the client holds, the floating islands and the void between them (open
// sky and storm, never ground), the rainbow-shard bridges, the marble of Heimdall's Perch, the ward circles (dim until you take a
// ward quest, amber and counting while you hold one), the Windcairn (dark until visited), the journal's seconds, and the five
// monster kinds in every clip. Rules, levels, combat and persistence are exercised by the Rust tests and the `bifrost` /
// `sky_quests` MCP scenarios; this asserts what the player sees. Run against the real art with REAL_SPRITES=1 (npm run test:art does).
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-sky-ui', version: '1.0.0' });
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
  const world = await call('start_world', { startLevel: 33 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  // Display-only fixture: while `stage` is set, the browser's copy of each Bifrost snapshot gets one extra monster of every kind in a
  // chosen state, so every clip can be drawn without a hero meeting them. The server is untouched.
  let stage = null;
  const kinds = ['galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc'];
  const levels = { galehound: 30, prismgolem: 31, skyray: 32, einherjar: 33, thunderroc: 35 }, health = { galehound: 12500, prismgolem: 17500, skyray: 13500, einherjar: 18500, thunderroc: 22000 };
  const windup = { galehound: .28, prismgolem: .8, skyray: .5, einherjar: .55, thunderroc: .35 };
  const restage = text => {
    let packet; try { packet = JSON.parse(text); } catch { return text; }
    const snap = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null, me = snap?.players[0];
    if (!stage || !me || me.zone !== 7) return text;
    kinds.forEach((kind, i) => {
      const D = [-12, -6, 0, 6, 12][i], x = me.x + (-8 + D) / 2, y = me.y + (-8 - D) / 2, dead = stage.state === 'dead';
      snap.slimes.push({ id: 1000 + i, kind, zone: 7, level: levels[kind], x, y, hx: x, hy: y, hp: dead ? 0 : health[kind] * (stage.state === 'hurt' ? .55 : 1), maxHp: health[kind], r: .4, windupTime: windup[kind],
        state: stage.state, st: stage.state === 'windup' ? .1 : stage.state === 'lunge' ? .15 : 1, hop: 0, hopV: 0, hurtT: stage.state === 'hurt' ? .2 : 0, recT: 0, landT: 0, dead, dieT: dead ? stage.dieT : 0, respawn: 0, atkCd: 1, blink: 2, seed: i, dir: 1, elite: false, hunt: false });
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
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('SkyUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites && !!Field.skySprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  await debug({ op: 'explore_all' });
  await page.waitForFunction(() => Field.explored?.length >= 8 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const stageAt = async (x, y) => {
    await debug({ op: 'teleport', zone: 7, x, y });
    await page.waitForFunction(([x, y]) => Field.zone === 7 && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
    await page.waitForTimeout(400);
  };
  // The colour of the world canvas at a world point (a few pixels averaged).
  const colourAt = (x, y) => page.evaluate(([x, y]) => {
    const [sx, sy] = Field._debug.w2s(x, y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.max(0, Math.round((sx - 3) * k)), Math.max(0, Math.round((sy - 3) * k)), Math.max(1, Math.round(6 * k)), Math.max(1, Math.round(6 * k))).data;
    let r = 0, gr = 0, b = 0; const n = d.length / 4;
    for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
    return { r: r / n, g: gr / n, b: b / n };
  }, [x, y]);

  // Colours of the canvas along a ward's rune circle (24 points on the circle, 3x3 pixels each).
  const ringAt = ward => page.evaluate(w => {
    const cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d'), out = [];
    for (let i = 0; i < 24; i++) {
      const a = i / 24 * 6.283, [sx, sy] = Field._debug.w2s(w.x + Math.cos(a) * w.r, w.y + Math.sin(a) * w.r);
      const d = g.getImageData(Math.max(0, Math.round((sx - 1.5) * k)), Math.max(0, Math.round((sy - 1.5) * k)), Math.max(1, Math.round(3 * k)), Math.max(1, Math.round(3 * k))).data;
      let r = 0, gr = 0, b = 0; const n = d.length / 4;
      for (let j = 0; j < d.length; j += 4) { r += d[j]; gr += d[j + 1]; b += d[j + 2]; }
      out.push({ r: r / n, g: gr / n, b: b / n });
    }
    return out;
  }, ward);
  // The map data the client uses comes from the same file the server loads.
  const z = await page.evaluate(() => { const a = Field._debug.zones[7]; return { n: Field._debug.zones.length, name: a.name, theme: a.theme, size: a.size, levels: a.levels, city: a.city.name, camps: (a.camps || []).length, rows: a.sky.length, wide: a.sky.every(r => r.length === 160), voids: a.objects.filter(o => o.kind === 'void').length, places: (a.places || []).map(p => p.id), waves: a.places.filter(p => (p.waves || []).length).length, portals: a.portals.map(p => p.id + '>' + p.to).join(), quests: a.quests.length, npcs: a.npcs.length, holds: a.quests.filter(q => q.objectives.some(o => o.kind === 'hold')).length }; });
  check(z.n === 10 && z.name === 'Bifrost Reach' && z.theme === 'sky' && z.size === 160 && z.levels.join() === '30,35', 'The client knows Bifrost Reach: name, sky theme, 160 tiles, levels 30-35');
  check(z.city === "Heimdall's Perch" && z.camps === 0 && z.rows === 160 && z.wide && z.voids > 300 && z.places.length === 7 && z.waves === 3 && z.portals === 'stormrift_down>6', `One hub, the floor as 160 rows, ${z.voids} void obstacles, seven places (three wards) and the gate back down`);
  check(z.quests === 22 && z.npcs === 8 && z.holds === 3, 'Twenty-two quests (three of them holds) and eight people are in the data');
  check(await page.evaluate(stub => { const m = Field.skySprites.meta; return m.kinds.join() === 'galehound,prismgolem,skyray,einherjar,thunderroc' && (stub || m.kinds.every(k => Field.skySprites.img[k].naturalWidth === 768 && Field.skySprites.img[k].naturalHeight === 480)); }, STUB), 'The five monster atlases load with their metadata (and are 768x480 each)');
  check(await page.evaluate(() => Field._debug.zones[6].portals.some(p => p.id === 'sky_gate' && p.to === 7)), 'The Wyrdwood has the Stormrift to Bifrost Reach');

  // Heimdall's Perch: a hub of pale cloud-marble on an island over the storm.
  await stageAt(80, 144);
  await shot('perch');
  check(await page.evaluate(() => Field.zone === 7 && Field.zoneName === 'Bifrost Reach' && Field.zoneTheme === 'sky'), 'The hero is in Bifrost Reach');
  check(await page.locator('#area-title b').textContent() === 'Bifrost Reach' && (await page.locator('#area-title span').textContent()).includes("Heimdall's Perch"), 'The banner names Heimdall\'s Perch as the sanctuary');
  check(await page.locator('#city-travel').isHidden(), 'The travel button is hidden inside the hub');
  const marble = await look(page, [.35, .55, .65, .8]);
  check(marble.r > 150 && marble.g > 150 && marble.b > 170, `The Perch is pale marble (${marble.r | 0},${marble.g | 0},${marble.b | 0})`);
  check(await page.evaluate(() => City.npcs.filter(n => n.id.startsWith('sky_') || n.id === 'travel_perch').length === 8 && Quests.marker('sky_warden') === '?'), 'The people are loaded; the warden has the arrived progression quest to turn in (?)');
  // Windward Meadow: turquoise grass, windswept pines, nothing like the forest.
  await stageAt(30, 112);
  await shot('windward');
  const grass = await colourAt(32, 112);
  check(grass.g > grass.r + 25 && grass.g > 120, `Windward Meadow is turquoise grass (${grass.r | 0},${grass.g | 0},${grass.b | 0})`);
  check(await page.locator('#city-travel').isVisible() && (await page.locator('#city-travel').textContent()).includes("Heimdall's Perch"), 'Outside the hub the travel button offers the Perch');
  // The bridge: rainbow glass over open sky. Past its edge there is no ground at all, only sky and storm.
  await stageAt(43.5, 134.5);
  await shot('bridge');
  const deck = [await colourAt(38.5, 134.5), await colourAt(49.5, 134.5), await colourAt(52.5, 134.5)];   // away from the hero's own sprite
  check(deck.every(c => Math.max(c.r, c.g, c.b) - Math.min(c.r, c.g, c.b) > 35 && c.r + c.g + c.b > 400), `The bridge deck is coloured glass (${deck.map(c => `${c.r | 0},${c.g | 0},${c.b | 0}`).join(' | ')})`);
  check(new Set(deck.map(c => `${c.r >> 4},${c.g >> 4},${c.b >> 4}`)).size >= 2, 'and the colour changes along the deck');
  const sideways = await colourAt(43.5, 124);
  check(Math.abs(sideways.g - grass.g) > 20 || Math.abs(sideways.r - grass.r) > 30, `Past the edge of the bridge is void, not grass (${sideways.r | 0},${sideways.g | 0},${sideways.b | 0})`);
  const storm = await colourAt(43.5, 142);
  check(storm.r < 130 && storm.b > storm.g - 10, `Below the bridge the sky is storm cloud or twilight (${storm.r | 0},${storm.g | 0},${storm.b | 0})`);
  const rain = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let island = 0, glass = 0; for (let i = 0; i < d.length; i += 4) { if (Math.abs(d[i] - 138) < 14 && Math.abs(d[i + 1] - 212) < 14 && Math.abs(d[i + 2] - 184) < 14 && d[i + 3] > 0) island++; if (Math.abs(d[i] - 240) < 14 && Math.abs(d[i + 1] - 200) < 14 && Math.abs(d[i + 2] - 244) < 14 && d[i + 3] > 0) glass++; } return { island, glass }; });
  check(rain.island > 300 && rain.glass > 40, `The minimap draws the islands (${rain.island} px) and the bridges (${rain.glass} px)`);

  // The wards: a stone with a floating crystal inside a rune circle. Dim blue until you take a ward quest.
  const ward = await page.evaluate(() => Field.place('sky_ward_wind'));
  check(ward && ward.r === 4.5 && ward.waves.length === 2, 'The first ward is a 4.5-tile circle with two waves');
  await stageAt(ward.x + 6.5, ward.y + 2);
  await shot('ward-idle');
  check(await page.evaluate(() => Quests.hold('sky_ward_wind').state === 'none'), 'With no ward quest the circle is idle');
  const ringIdle = (await ringAt(ward)).reduce((m, c) => Math.max(m, c.b - c.g), -999);
  check(ringIdle > -22, `The idle ring is cool blue-white against the green ground (best blue-minus-green ${ringIdle.toFixed(0)}, bare grass is about -43)`);
  check(!await page.evaluate(() => Quests.visited('sky_windcairn')), 'The Windcairn is dark before the quest');
  await debug({ op: 'quest', id: 'sky_welcome', action: 'finish' });
  await debug({ op: 'quest', id: 'sky_hounds', action: 'finish' });
  await debug({ op: 'quest', id: 'sky_cairn', action: 'finish' });
  await debug({ op: 'quest', id: 'sky_ward_wind', action: 'accept' });
  await page.waitForFunction(() => Quests.hold('sky_ward_wind').state === 'active', null, { timeout: 10000 });
  check(true, 'Taking the ward quest makes the circle active');
  await page.locator('#quest-tracker').waitFor({ state: 'visible' });
  check(await page.locator('#quest-tracker').textContent().then(t => /Hold the Windward Ward: 0\/60 s/.test(t)), 'The tracker shows the objective in seconds (0/60 s)');
  await stageAt(ward.x, ward.y + 2);
  await page.waitForFunction(() => Quests.hold('sky_ward_wind').have >= 17, null, { timeout: 50000 });
  await shot('ward-active');
  const have = await page.evaluate(() => Quests.hold('sky_ward_wind').have);
  check(have >= 17 && await page.locator('#quest-tracker').textContent().then(t => new RegExp(`Hold the Windward Ward: ${have}/60 s|Hold the Windward Ward: ${have + 1}/60 s`).test(t)), `Standing in the circle counts the seconds (${have}) in the tracker`);
  const ringOn = (await ringAt(ward)).reduce((m, c) => Math.max(m, c.r - c.b), -999);
  check(ringOn > 50, `The active ring is amber (best red-minus-blue ${ringOn.toFixed(0)}, bare grass is about -13)`);
  check(await page.evaluate(([x, y]) => Field.slimes.filter(s => s.kind === 'galehound' && !s.dead && Math.hypot(s.x - x, s.y - y) < 14).length >= 1, [ward.x, ward.y]), 'After fifteen seconds the first wave, a galehound, is hunting at the ward');
  // Done: the circle turns gold and stays so.
  await debug({ op: 'quest', id: 'sky_ward_wind', action: 'complete' });
  await page.waitForFunction(() => Quests.hold('sky_ward_wind').state === 'done', null, { timeout: 10000 });
  await page.waitForTimeout(500);
  const ringDone = (await ringAt(ward)).reduce((m, c) => (c.r - c.b > m.r - m.b ? c : m), { r: 0, g: 0, b: 255 });
  check(ringDone.r > ringDone.b + 60 && ringDone.g > ringDone.b + 40, `A held ward glows gold (${ringDone.r | 0},${ringDone.g | 0},${ringDone.b | 0})`);
  // Finishing the Windcairn quest has lit it.
  check(await page.evaluate(() => Quests.visited('sky_windcairn')), 'The Windcairn is lit once its quest is done');
  await stageAt(22, 112);
  await shot('windcairn');
  // The Stormcrown's pylon, the Hall Gate, the spire and the nest are all in the data and drawn by the art file.
  check(await page.evaluate(() => ['wardstone', 'windcairn', 'spirelight', 'pylon', 'hallgate', 'nest', 'prism', 'column', 'skypine', 'skyrock', 'cloudpuff'].every(k => City.art[k] && Field._debug.zones[7].objects.some(o => o.kind === k))), 'Every prop of the zone has artwork registered with the city renderer');

  // Every kind in every clip: the canvas must change from one state to the next and nothing may throw.
  await stageAt(80, 86);
  const monsterHashes = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600;
    return [1000, 1001, 1002, 1003, 1004].map(id => {
      const s = Field.slimes.find(m => m.id === id), [sx, sy] = Field._debug.w2s(s.x, s.y);
      const x = Math.max(0, Math.round((sx - 110) * k)), y = Math.max(0, Math.round((sy - 280) * k)), d = g.getImageData(x, y, Math.round(220 * k), Math.round(300 * k)).data;
      let h = 0; for (let i = 0; i < d.length; i += 5) h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0;
      return h;
    });
  });
  const seen = [];
  for (const [state, dieT] of [['idle', 0], ['windup', 0], ['lunge', 0], ['hurt', 0], ['dead', .2], ['dead', .45], ['dead', 3]]) {
    stage = { state, dieT };
    await page.waitForFunction(([state]) => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000 && s.state === state).length === 5, [state], { timeout: 10000 });
    await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
    const frames = await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => Field._debug.enemyFrame(s)));
    const wanted = { idle: f => f[0] === 'idle', windup: f => f[0] === 'attack' && f[1] < 3, lunge: f => f[0] === 'attack' && f[1] >= 3 && f[1] <= 5, hurt: f => f[0] === 'hurt' };
    const dying = dieT === .2 ? f => f[0] === 'die' && f[1] >= 1 && f[1] <= 2 : dieT === .45 ? f => f[0] === 'die' && f[1] >= 3 && f[1] <= 4 : f => f[0] === 'die' && f[1] === 7;
    check(frames.length === 5 && frames.every(state === 'dead' ? dying : wanted[state]), `The ${state}${state === 'dead' ? ' ' + dieT + 's' : ''} state picks its own clip and frame: ${JSON.stringify(frames[0])}`);
    if (state === 'idle') check((await page.evaluate(() => Field.slimes.filter(s => s.id >= 1000 && s.id < 2000).map(s => s.d.name))).join() === 'Galehound,Prism Golem,Skyray,Hollow Einherjar,Thunderroc', 'The bestiary names come from the Bifrost table');
    seen.push(await monsterHashes());
    if (state === 'idle' || state === 'lunge') await shot('bestiary-' + state);
  }
  stage = null;
  check(STUB || seen.every((hashes, i) => i === 0 || hashes.every((h, kind) => h !== seen[i - 1][kind])), `All five monsters draw something new in each state (${seen.length} states)`);
  await page.waitForFunction(() => Field.slimes.every(s => s.id < 1000), null, { timeout: 10000 });
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`sky-ui: ${checks} checks passed`);
})().then(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close(); process.exit(0); },
  async error => { console.error(error); await browser?.close().catch(() => {}); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); process.exit(1); });
