// Browser-only checks for Skaldholm (zone 4, the walled city): the summit gate, the city theme (lawn, cobbles, marble, golden sky),
// the wall, the Great Fountain, the Meeting Stone, walking townspeople, the eleven-quest journal with hand-in objectives, the minimap
// and the HUD. Rules, rewards and persistence are exercised by the Rust tests and the `skaldholm` / `skaldholm_quests` MCP scenarios;
// this walks with real canvas clicks and asserts what the player sees.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-skaldholm-ui', version: '1.0.0' });
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
  let r = 0, gr = 0, b = 0, n = d.length / 4;
  for (let i = 0; i < d.length; i += 4) { r += d[i]; gr += d[i + 1]; b += d[i + 2]; }
  return { r: r / n, g: gr / n, b: b / n };
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
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('CityUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  // The maps are fogged until a cell is visited; these checks read the whole minimap, so uncover it all first.
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.length >= 5 && Field.explored.every(m => m === 511), null, { timeout: 10000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);

  // The map data the client uses comes from the same file the server loads.
  const zones = await page.evaluate(() => Field._debug.zones.map(z => ({ name: z.name, theme: z.theme, size: z.size, levels: z.levels, portals: z.portals.map(p => p.id + '>' + p.to), roads: (z.roads || []).length,
    houses: z.objects.filter(o => o.kind === 'house' && o.sign === 'live').length, kinds: [...new Set(z.objects.map(o => o.kind))].sort().join(), slimes: (z.slimes || []).length, npcs: (z.npcs || []).length, walkers: (z.npcs || []).filter(n => n.route).length })));
  check(zones.length === 7 && zones[4].name === 'Skaldholm' && zones[4].theme === 'city' && zones[4].size === 160 && !zones[4].levels && zones[4].slimes === 0, 'The client knows the city: name, city theme, 160 tiles, no levels, no enemies');
  check(zones[2].portals.join() === 'crags_gate>1,fen_gate>3,city_gate>4' && zones[4].portals.join() === 'glacier_gate>2,undervault_stairs>5,wyrd_gate>6', 'The glacier summit has a second gate to the city, which has the gate back');
  check(zones[4].houses >= 100 && zones[4].roads >= 15 && ['rampart', 'tower', 'grandfountain', 'meetingstone'].every(k => zones[4].kinds.includes(k)), `The city has ${zones[4].houses} signed houses, ${zones[4].roads} road shapes, a wall, towers, the fountain and the stone`);
  check(zones[4].npcs >= 40 && zones[4].walkers >= 12, `${zones[4].npcs} townspeople, ${zones[4].walkers} of them walkers`);
  // A house's sprite is drawn into a box; the roof reaches (w+d)/2*44 px to each side and the front corner (w+d)/2*22 px below the origin.
  const clipped = await page.evaluate(() => WORLD_MAP.zones.concat([WORLD_MAP]).flatMap(z => z.objects || []).filter(o => o.kind === 'house' || o.kind === 'chapel').filter(o => {
    const [bw, bh, ox, oy] = City.spriteBox(o), span = o.width + o.depth;
    return ox < (span + 1.3) * 22 || bw - ox < (span + 1.3) * 22 || bh - oy < span * 11 + 6 || oy < 330;
  }).map(o => `${o.width}x${o.depth}`));
  check(clipped.length === 0, `Every house and chapel sprite box holds the whole building (clipped: ${[...new Set(clipped)].join(', ') || 'none'})`);

  const click = async (x, y) => {
    const [sx, sy] = await page.evaluate(([x, y]) => Field._debug.w2s(x, y), [x, y]);
    const crowded = await page.evaluate(([x, y]) => City.npcs.some(n => Math.hypot(n.x - x, n.y - y) < 2.5), [x, y]);
    if (crowded || sx < 60 || sx > 1540 || sy < 60 || sy > 840) { await page.evaluate(([x, y]) => Online.send({ type: 'move', x, y }), [x, y]); return; }
    const box = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(box.x + sx / 1600 * box.width, box.y + sy / 900 * box.height);
  };
  const reach = (x, y, within = .6, zone = 4) => page.waitForFunction(([x, y, within, zone]) => Field.zone !== zone || Math.hypot(Field.hero.x - x, Field.hero.y - y) < within, [x, y, within, zone], { timeout: 40000 })
    .catch(async error => { await shot('stuck'); throw Error(`Never reached ${x},${y}; hero ${JSON.stringify(await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, zone: Field.zone, goal: Field.hero.goal })))}`, { cause: error }); });
  const stageAt = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [zone, x, y], { timeout: 10000 });
    let last = null;
    for (let i = 0; i < 40; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < 1) break;
      last = now; await page.waitForTimeout(80);
    }
  };

  // Cross the Skaldholm Gate (in the Rimeveil summit bowl) with real canvas clicks.
  const gate = await page.evaluate(() => Field._debug.zones[2].portals.find(p => p.id === 'city_gate'));
  await stageAt(2, gate.x, gate.y + 8);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [gate.x, gate.y + 4])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 2); }
  await page.waitForTimeout(900);
  await shot('gate-summit');
  check(await page.evaluate(() => Field.zone === 2), 'Still on the glacier in front of the new gate');
  await click(gate.x, gate.y - 1.2);
  await page.waitForFunction(() => Field.zone === 4, null, { timeout: 30000 });
  await page.waitForTimeout(1200);
  await shot('city-arrival');
  check(await page.evaluate(() => Field.zone === 4 && Field.zoneName === 'Skaldholm' && Field.zoneTheme === 'city'), 'Walking into the gate moves the hero into the city');
  check(await page.locator('#area-title b').textContent() === 'Skaldholm' && (await page.locator('#area-title span').textContent()).includes('hundred hearths'), 'The banner names Skaldholm and its tagline outside the walls');
  check(await page.evaluate(() => Field.slimes.length === 0 && Field.remotePlayers.length === 0), 'No enemies, nobody else');
  check(await page.evaluate(() => !document.getElementById('city-travel').hidden && /Visit Skaldholm/.test(document.getElementById('city-travel').textContent)), 'The travel button offers a walk into Skaldholm');
  const lawn = await look(page, [.55, .55, .8, .75]);
  check(lawn.g > lawn.r + 20 && lawn.g > lawn.b + 30, `The forecourt lawn is green (${lawn.r | 0},${lawn.g | 0},${lawn.b | 0})`);
  // A sunlit sky: the sky beyond the map's south edge (the bottom corners of the screen) is a bright blue-to-peach gradient, not a dusk.
  const sky = await look(page, [.0, .93, .08, 1]);
  check(sky.r + sky.g + sky.b > 380 || (await look(page, [.92, 0, 1, .07])).b > 150, `The sky is bright (${sky.r | 0},${sky.g | 0},${sky.b | 0})`);

  // Real walk: the travel button routes through the Great Gate into the city.
  await page.locator('#city-travel').click();
  await page.waitForFunction(() => Field.hero.y < 133, null, { timeout: 60000 });
  await page.evaluate(() => Online.send({ type: 'stop' }));
  await page.waitForTimeout(700);
  await shot('great-gate');
  check(await page.evaluate(() => Field.hero.y < 134 && Math.abs(Field.hero.x - 80) < 12), 'The travel button walks the hero through the Great Gate onto the avenue');
  check(await page.locator('#city-travel').isHidden() || await page.locator('#area-title span').textContent().then(t => t.includes('Sanctuary')), 'Inside the walls the area is a sanctuary');

  // Ground: cobbles on the avenue (grey-beige), marble in the plaza (pale), lawn between the streets, brick in the stone court.
  await stageAt(4, 80, 96);
  await page.waitForTimeout(700);
  await shot('plaza-south');
  const groundTypes = await page.evaluate(() => {
    const out = {}; const z = Field._debug.zones[4];
    const type = (x, y) => { let t = 0; for (const r of z.roads) { const rect = r.x0 !== undefined; const d = rect ? 0 : Math.hypot(x - r.x, y - r.y); const inside = rect ? x >= r.x0 && x <= r.x1 && y >= r.y0 && y <= r.y1 : (r.r0 !== undefined ? d >= r.r0 && d <= r.r1 : d <= r.r); if (inside) t = r.t; } return t; };
    for (const [name, x, y] of [['avenue', 80.5, 120.5], ['plaza', 80.5, 62.5], ['court', 100.5, 124.5], ['lawn', 64.5, 120.5], ['trade', 30.5, 76.5]]) out[name] = type(x, y);
    return out;
  });
  check(groundTypes.avenue === 1 && groundTypes.plaza === 2 && groundTypes.court === 3 && groundTypes.lawn === 0 && groundTypes.trade === 1, `The road list paints avenue ${groundTypes.avenue}, plaza ${groundTypes.plaza}, court ${groundTypes.court}, lawn ${groundTypes.lawn}`);
  const cobbles = await look(page, [.47, .5, .53, .56]);
  check(Math.abs(cobbles.r - cobbles.b) < 50 && cobbles.r > 90 && cobbles.r < 200, `The avenue is warm-grey cobbles (${cobbles.r | 0},${cobbles.g | 0},${cobbles.b | 0})`);

  // The Great Fountain: pale marble and blue water in the middle of the view, with moving jets.
  await stageAt(4, 80, 90);
  await page.waitForTimeout(900);
  const fountainShot = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600, [sx, sy] = Field._debug.w2s(80, 76);
    const x = Math.max(0, Math.round((sx - 330) * k)), y = Math.max(0, Math.round((sy - 330) * k)), d = g.getImageData(x, y, Math.round(660 * k), Math.round(300 * k)).data;
    let blue = 0, h = 0; for (let i = 0; i < d.length; i += 4) { if (d[i + 2] > d[i] + 40 && d[i + 2] > 140) blue++; h = (Math.imul(h, 31) + d[i] + (d[i + 1] << 3) + (d[i + 2] << 6)) | 0; }
    return { blue: blue / (d.length / 4), h };
  });
  const f1 = await fountainShot(); await page.waitForTimeout(450); const f2 = await fountainShot();
  check(f1.blue > .08, `The Great Fountain shows water (${(f1.blue * 100).toFixed(1)}% blue)`);
  check(f1.h !== f2.h, 'The jets and glints move from frame to frame');
  await shot('fountain');

  // The Meeting Stone: glowing blue runes round a dark monolith.
  await stageAt(4, 100, 126);
  await page.waitForTimeout(900);
  const stoneGlow = () => page.evaluate(() => {
    const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), k = cv.width / 1600, [sx, sy] = Field._debug.w2s(100, 118);
    const x = Math.max(0, Math.round((sx - 130) * k)), y = Math.max(0, Math.round((sy - 330) * k)), d = g.getImageData(x, y, Math.round(260 * k), Math.round(360 * k)).data;
    let cyan = 0; for (let i = 0; i < d.length; i += 4) if (d[i] < 170 && d[i + 1] > 190 && d[i + 2] > 220) cyan++;
    return cyan;
  });
  const glow = await stoneGlow();
  check(glow > 60, `The Meeting Stone's runes glow cyan (${glow} bright pixels)`);
  check(await page.evaluate(() => Field._debug.objects.some(o => o.kind === 'meetingstone' && Math.abs(o.x - 100) < 1 && Math.abs(o.y - 118) < 1) && City.npcs.some(n => n.id === 'city_stonewarden')), 'The stone stands in its court beside its warden');
  await shot('meeting-stone');

  // The wall: stage at the north wall from inside; ramparts and towers are drawn there and block the hero.
  await stageAt(4, 30, 17);
  await debug({ op: 'teleport', zone: 4, x: 30, y: 17 });
  await page.evaluate(() => Online.send({ type: 'move', x: 30, y: 2 }));
  await page.waitForTimeout(2500);
  await shot('north-wall');
  check(await page.evaluate(() => Field.hero.y > 12.5 && Field.hero.y < 16.5), 'The north wall holds the hero back');
  await page.evaluate(() => Online.send({ type: 'stop' }));

  // Walking townspeople: the client places them from the server's clock with the same arithmetic as the Rust tests (reference values from there).
  const ref = await page.evaluate(() => {
    const n = { x: 0, y: 0, route: [[0, 0], [10, 0], [10, 5]], speed: 2, pause: 1, phase: .5 };
    return [0, 1, 6, 8, 10.5, 16].map(t => City.routePoint(n, t));
  });
  const want = [[0, 0], [1, 0], [10, 0], [10, 3], [9.105573, 4.552786], [0, 0]];
  check(ref.every((p, i) => Math.abs(p.x - want[i][0]) < 1e-5 && Math.abs(p.y - want[i][1]) < 1e-5), `The client's walking arithmetic equals the server's (${ref.map(p => p.x.toFixed(2) + ',' + p.y.toFixed(2)).join(' ')})`);
  await stageAt(4, 80, 112);
  const kid = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_watch_avenue'); return { x: n.x, y: n.y }; });
  await page.waitForTimeout(3200);
  const kid2 = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_watch_avenue'); return { x: n.x, y: n.y, moving: n.moving }; });
  const moved = await page.evaluate(() => City.npcs.filter(n => n.route && n.moving).length);
  check(moved >= 4, `${moved} townspeople are walking right now`);
  check(Math.hypot(kid.x - kid2.x, kid.y - kid2.y) > .05 || kid2.moving === false, 'Positions change over time (or the watchman is pausing)');
  const spread = await page.evaluate(() => { const ps = ['city_kid_lotta', 'city_kid_pelle', 'city_kid_ebba', 'city_kid_anton'].map(id => City.npcs.find(n => n.id === id)); return Math.min(...ps.flatMap((a, i) => ps.slice(i + 1).map(b => Math.hypot(a.x - b.x, a.y - b.y)))); });
  check(spread > 3, `The four children are spread round the fountain (closest pair ${spread.toFixed(1)} apart)`);
  // Click a walker on the canvas at the place the client draws him, and reach his conversation.
  await page.waitForFunction(() => { const n = City.npcs.find(n => n.id === 'city_courier'); return n && !n.moving; }, null, { timeout: 30000 }).catch(() => {});
  const walker = await page.evaluate(() => City.npcs.find(n => n.id === 'city_courier'));
  await stageAt(4, walker.x + 2.4, walker.y + 2.4);
  const [wx, wy] = await page.evaluate(() => { const n = City.npcs.find(n => n.id === 'city_courier'); return Field._debug.w2s(n.x, n.y); });
  const box = await page.locator('#fieldcv').boundingBox();
  await page.mouse.click(box.x + wx / 1600 * box.width, box.y + (wy - 55) / 900 * box.height);
  await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  check(await page.locator('#npc-name').textContent() === 'Courier Fia' && (await page.locator('#npc-text').textContent()).includes('parcels'), 'A click on a walking courier opens her conversation');
  await page.keyboard.press('Escape');

  // Minimap: city colours, with the buildings as footprints and the fountain as a blue disc.
  const mini = await page.evaluate(() => { const c = document.getElementById('minimap'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let green = 0, blue = 0, red = 0; for (let i = 0; i < d.length; i += 4) { if (d[i + 3] === 0) continue; if (d[i + 1] > d[i] + 25 && d[i + 1] > d[i + 2] + 25) green++; if (d[i + 2] > d[i] + 60 && d[i + 2] > 170) blue++; if (d[i] > d[i + 2] + 60 && d[i] > 150 && d[i + 1] < 140) red++; } return { green, blue, red }; });
  check(mini.green > 1500 && mini.blue > 20 && mini.red > 150, `The minimap shows lawn (${mini.green}), the fountain (${mini.blue}) and house roofs (${mini.red})`);

  // The journal: eleven city quests, local ones first; the first conversation at the gate captain through a real canvas click.
  await stageAt(4, 80, 128);
  await page.keyboard.press('q');
  check(await page.locator('#quest-journal').isVisible() && await page.locator('#quest-list .quest-card').count() === 0 && await page.locator('#quest-list .quest-empty').count() > 0, 'The journal lists no quest that has not been taken');
  check(await page.evaluate(() => { const q = WORLD_MAP.zones.flatMap(z => z.quests || []); const g = q.find(x => x.id === 'city_gel'); return q.filter(x => x.id.startsWith('city_')).length === 12 && g.level === 12 && g.objectives[0].label.includes('Slime Gel') && g.objectives[0].count === 8; }), 'The city catalogue has twelve quests, including the hand-in of eight Slime Gel at level 12');
  await page.keyboard.press('Escape');
  const nameplate = id => page.evaluate(id => { const n = City.npcs.find(n => n.id === id); return Field._debug.w2s(n.x, n.y); }, id);
  const talkByClick = async id => {
    const at = await page.evaluate(id => { const n = City.npcs.find(n => n.id === id); return { x: n.x, y: n.y }; }, id);
    await stageAt(4, at.x + 2.6, at.y + 2.6);
    const [sx, sy] = await nameplate(id), b = await page.locator('#fieldcv').boundingBox();
    await page.mouse.click(b.x + sx / 1600 * b.width, b.y + (sy - 55) / 900 * b.height);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible', timeout: 30000 });
  };
  await talkByClick('city_captain');
  check(await page.locator('#npc-name').textContent() === 'Captain Ingrid Stormwatch', 'A click on the gate captain reaches her');
  await page.locator('#npc-quests .gossip-row[data-quest="city_welcome"]').click();
  await page.locator('#npc-quests [data-quest="city_welcome"] [data-action="accept"]').click();
  await page.waitForFunction(() => document.querySelector('#npc-quests .gossip-row[data-quest="city_welcome"]')?.dataset.status === 'active');
  await page.keyboard.press('Escape');
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('The Great Gate Opens') && t.includes('Herald Bran')), 'The welcome appears in the live tracker');
  await page.getByRole('button', { name: 'Collapse quest tracker' }).click();
  for (const id of ['city_herald', 'city_librarian', 'city_guildmaster', 'city_stonewarden', 'city_healer']) {
    await talkByClick(id);
    check(await page.locator('#npc-name').textContent() === await page.evaluate(id => City.npcs.find(n => n.id === id).name, id), `Canvas interaction reaches ${id}`);
    if (id === 'city_healer') check((await page.locator('#npc-offers').textContent()).includes('Health Potion'), 'Sister Liv offers healing supplies');
    if (id === 'city_guildmaster') check((await page.locator('#npc-offers').textContent()).includes('Stew') && (await page.locator('#npc-offers').textContent()).includes('Satchel'), 'Tobias offers food and bags');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
  }
  await page.getByRole('button', { name: 'Expand quest tracker' }).click();
  await page.keyboard.press('q');
  check((await page.locator('#quest-list [data-quest="city_welcome"]').textContent()).includes('Ready to turn in'), 'Five conversations complete the introduction');
  await page.keyboard.press('Escape');
  await talkByClick('city_captain');
  await page.locator('#npc-quests .gossip-row[data-quest="city_welcome"]').click();
  await page.locator('#npc-quests [data-quest="city_welcome"] [data-action="claim"]').click();
  await page.waitForFunction(() => !document.querySelector('#npc-quests [data-quest="city_welcome"]'));
  check(await page.evaluate(() => Quests.marker('city_herald') === '!' && Quests.marker('city_alchemist') === '!'), 'Turn-in unlocks the herald\'s letters and the alchemist\'s order');
  await page.keyboard.press('Escape');

  // A hand-in quest: the alchemist's gel. The tracker follows the bag; the reward takes the items.
  await talkByClick('city_alchemist');
  await page.locator('#npc-quests .gossip-row[data-quest="city_gel"]').click();
  await page.locator('#npc-quests [data-quest="city_gel"] [data-action="accept"]').click();
  await page.waitForFunction(() => document.querySelector('#npc-quests .gossip-row[data-quest="city_gel"]')?.dataset.status === 'active');
  await page.keyboard.press('Escape');
  await debug({ op: 'give_item', item: 'slime_gel', quantity: 5 });
  await page.waitForFunction(() => /Bring Slime Gel: 5\/8/.test(document.getElementById('quest-tracker').textContent), null, { timeout: 10000 });
  check(await page.locator('#quest-tracker').textContent().then(t => t.includes('Bring Slime Gel: 5/8')), 'The tracker counts five Slime Gel straight from the bag');
  await debug({ op: 'give_item', item: 'slime_gel', quantity: 5 });
  await debug({ op: 'give_item', item: 'blue_gel', quantity: 4 });
  await page.waitForFunction(() => /Return to Alchemist Orsolya Quill/.test(document.getElementById('quest-tracker').textContent), null, { timeout: 10000 });
  await talkByClick('city_alchemist');
  await page.locator('#npc-quests .gossip-row[data-quest="city_gel"]').click();
  await page.locator('#npc-quests [data-quest="city_gel"] [data-action="claim"]').click();
  await page.waitForFunction(() => !document.querySelector('#npc-quests [data-quest="city_gel"]'));
  const bag = item => page.evaluate(item => (Field.hero.inventory.find(i => i.item === item) || {}).quantity || 0, item);
  check(await bag('slime_gel') === 2 && await bag('blue_gel') === 0, 'The reward took exactly eight gel and four blue gel from the bag');
  await page.keyboard.press('Escape');
  await shot('city-quests');

  // Back out through the Glacier Gate by clicking.
  const back = await page.evaluate(() => Field._debug.zones[4].portals[0]);
  await stageAt(4, back.x, back.y - 6);
  for (const step of await page.evaluate(([x, y]) => Field._debug.routeTo({ x, y }), [back.x, back.y - 3])) { await click(step.x, step.y); await reach(step.x, step.y, 1.3, 4); }
  await page.waitForTimeout(700);
  await click(back.x, back.y + 1.2);
  await page.waitForFunction(() => Field.zone === 2, null, { timeout: 30000 });
  await page.waitForTimeout(600);
  check(await page.locator('#area-title b').textContent() === 'Rimeveil Glacier', 'Returning restores the glacier banner');
  check(await page.evaluate(([x, y]) => Math.hypot(Field.hero.x - x, Field.hero.y - y) < 2, [back.tx, back.ty]), 'The Glacier Gate arrives beside the Skaldholm Gate');
  check(await page.evaluate(() => Field.slimes.length > 0 && Field.slimes.every(s => s.zone === 2)), 'Back on the glacier only glacier enemies are shown');
  const again = await look(page);
  check(again.b > again.r, `The glacier is cold-toned again (${again.r | 0},${again.g | 0},${again.b | 0})`);
  await shot('glacier-again');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} focused city UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
