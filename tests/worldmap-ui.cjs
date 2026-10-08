// Browser checks for the world map (M): it opens and closes with the keys, shows every zone as a pressable tile with
// its own ground, zooms into a zone with its gates and enemies, follows the hero, and leaves the other panels alone.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-worldmap-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  // Source checks that need no browser: the enemy table the map uses must match the server's levels.
  const rust = fs.readFileSync(path.join(root, 'server/src/world.rs'), 'utf8');
  const body = rust.slice(rust.indexOf('pub fn default_level'), rust.indexOf('// Gold carried by a default-level enemy'));
  const server = {}; for (const [, names, level] of body.matchAll(/((?:"\w+"\s*\|?\s*)+)=>\s*(\d+)/g)) for (const [, name] of names.matchAll(/"(\w+)"/g)) server[name] = Number(level);
  Object.assign(server, Object.fromEntries(JSON.parse(fs.readFileSync(path.join(root, 'world/cathedral.txt'), 'utf8')).map(e => [e.kind, e.level])));
  check(Object.keys(server).length >= 17, `Parsed ${Object.keys(server).length} enemy levels from world.rs`);

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
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('MapUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const visible = id => page.locator(id).isVisible();
  const press = async key => { await page.evaluate(() => document.activeElement?.blur?.()); await page.keyboard.press(key); };

  // --- the data the map was written against ---
  const data = await page.evaluate(() => ({ zones: Field._debug.zones.map(z => ({ name: z.name, kinds: [...new Set((z.slimes || []).map(s => s.kind))], portals: (z.portals || []).map(p => p.to) })), layout: WorldMap._layout.length, kinds: Object.fromEntries(Object.entries(WorldMap._kinds).map(([k, v]) => [k, v[1]])) }));
  check(data.layout >= data.zones.length, `Every one of the ${data.zones.length} zones has a place on the world sheet (${data.layout})`);
  check(data.zones.every(z => z.kinds.every(k => k in data.kinds)), 'Every enemy kind in every zone is in the map legend');
  check(Object.entries(data.kinds).every(([k, level]) => (server[k] ?? 2) === level), `The legend levels equal the server's (${Object.entries(data.kinds).filter(([k, l]) => (server[k] ?? 2) !== l).map(([k]) => k)})`);

  // --- opening and closing ---
  check(!await visible('#worldmap') && await visible('#wm-open'), 'The map is closed and a globe button is on the minimap');
  check(await page.evaluate(() => { const hit = (a, b) => !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top), r = id => document.querySelector(id).getBoundingClientRect(), m = r('#wm-open'); const mini = r('#minimap'); return ['#city-travel', '#equipment-open', '#hud-portrait', '.hud-stats'].every(id => !hit(m, r(id))) && hit(m, mini) && m.width < mini.width / 3 && m.width > 20 && m.left >= 0 && m.right <= innerWidth; }), 'The globe is small, stuck to the minimap corner and overlaps no other control');
  check(await page.evaluate(() => { const b = document.getElementById('wm-open'); return !b.textContent.trim() && !!b.querySelector('svg circle') && b.getAttribute('aria-label').includes('(M)'); }), 'The globe is an icon with an accessible name');
  await press('m');
  check(await visible('#worldmap') && await page.evaluate(() => WorldMap.open && WorldMap.view === 'world'), 'M opens the world map on the world view');
  check(await page.locator('.wm-tile[data-zone="9"] .wm-travel-badge').isHidden(), 'Unvisited zones do not reveal their travel-master badge');
  check(await page.evaluate(() => !Field.canAct), 'The game is paused behind the map');
  check(await page.locator('#pause').isHidden(), 'M does not open the pause menu');
  await shot('map-world');
  await press('m');
  check(!await visible('#worldmap') && await page.evaluate(() => Field.canAct), 'M closes it and the game resumes');
  await press('m'); await press('Escape');
  check(!await visible('#worldmap') && await page.locator('#pause').isHidden(), 'Esc closes the map without opening the pause menu');
  await page.locator('#minimap').click();
  check(await visible('#worldmap'), 'Pressing the minimap opens it');
  await page.locator('#wm-close').click();
  await page.locator('#wm-open').click();
  check(await visible('#worldmap'), 'The globe opens it');
  await page.keyboard.press('Escape');

  // --- fog of war: a new character has seen one cell of one zone ---
  const stand = async (zone, x, y) => {
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone, x, y } }), [zone, x, y]);
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 3 && (Field.explored[zone] & (1 << (Math.min(2, Math.floor(y / Field._debug.zones[zone].size * 3)) * 3 + Math.min(2, Math.floor(x / Field._debug.zones[zone].size * 3))))) !== 0, [zone, x, y], { timeout: 15000 });
  };
  const miniPx = (x, y) => page.evaluate(([x, y]) => Array.from(document.getElementById('minimap').getContext('2d').getImageData(x, y, 1, 1).data), [x, y]);
  check(await page.evaluate(() => JSON.stringify(Field.explored)) === '[16]', `A new character has uncovered only the middle cell of Greenmeadow (${await page.evaluate(() => JSON.stringify(Field.explored))})`);
  const dark = px => px[0] > 130 && px[1] > 140 && px[2] > 160;                      // fog is pale mist, not black
  check(dark(await miniPx(8, 8)) && dark(await miniPx(136, 136)) && dark(await miniPx(72, 8)) && !dark(await miniPx(72, 72)) && !dark(await miniPx(60, 80)), 'The minimap is misted over except the middle cell');
  const hidden = await page.evaluate(() => { let fogged = 0, drawn = 0; const g = document.getElementById('minimap').getContext('2d'); for (const s of Field.slimes) { if (s.dead || Field.fog.seen(0, s.x, s.y)) continue; fogged++; const d = g.getImageData(Math.round(s.x * 1.5), Math.round(s.y * 1.5), 1, 1).data; if (d[0] > 200 && d[1] < 140 && d[2] > 100) drawn++; } return { fogged, drawn }; });
  check(hidden.fogged > 0 && hidden.drawn === 0, `No enemy dot shows in the fog (${hidden.fogged} slimes are in fogged cells)`);
  await press('m');
  const first = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => ({ name: t.querySelector('b').textContent, small: t.querySelector('small').textContent, disabled: t.disabled, fog: t.dataset.fog })));
  check(first[0].name === 'Greenmeadow' && /^Lv 2–5 · 1\/9 charted$/.test(first[0].small) && first.slice(1).every(t => t.name === 'Unexplored' && t.disabled && t.fog === 'full' && t.small === 'Not yet visited'), `Only Greenmeadow is known; the other four tiles read Unexplored (${first.map(t => t.name)})`);
  check(await page.evaluate(() => [...document.querySelectorAll('.wm-roads [data-road]')].every(r => r.getAttribute('visibility') === 'hidden')), 'No road is drawn to a gate nobody has seen');
  const tilePx = (zone, fx, fy) => page.evaluate(([zone, fx, fy]) => { const c = document.querySelector(`.wm-tile[data-zone="${zone}"] .wm-tile-fog`); return c.getContext('2d').getImageData(Math.round(fx * 219), Math.round(fy * 219), 1, 1).data[3]; }, [zone, fx, fy]);
  check(await tilePx(0, .5, .5) === 0 && await tilePx(0, .5, .5) < await tilePx(0, .1, .1) && await tilePx(0, .1, .1) > 200 && await tilePx(1, .5, .5) > 200, 'On the tiles the visited cell is clear and the rest is fog');
  const stage = await page.evaluate(() => { const r = document.getElementById('wm-world').getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }; });
  const tiles = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => { const r = t.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }; }));
  check(tiles.length === data.zones.length && tiles.every(t => t.left >= stage.left && t.right <= stage.right && t.top >= stage.top && t.bottom <= stage.bottom), 'Every tile is inside the world sheet');
  check(tiles.every((a, i) => tiles.every((b, j) => i >= j || a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top)), 'No two tiles overlap');
  const you = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => { const y = t.querySelector('.wm-you'), r = t.getBoundingClientRect(), p = y.getBoundingClientRect(); return { shown: !y.hidden, x: (p.left + p.width / 2 - r.left) / r.width, y: (p.top + p.height / 2 - r.top) / r.height }; }));
  const spawn = await page.evaluate(() => ({ x: Field.hero.x / 96, y: Field.hero.y / 96 }));
  check(you[0].shown && you.slice(1).every(y => !y.shown) && Math.abs(you[0].x - spawn.x) < .02 && Math.abs(you[0].y - spawn.y) < .02, 'The marker is on Greenmeadow where the hero stands');
  check(await page.evaluate(() => document.activeElement.classList.contains('wm-tile') && document.activeElement.dataset.zone === '0'), 'Focus starts on the tile of the zone you are in');
  const panel = await page.locator('.wm-panel').boundingBox();
  check(panel.x >= 0 && panel.y >= 0 && panel.x + panel.width <= 1440 && panel.y + panel.height <= 900, `The panel fits the window (${panel.width | 0}x${panel.height | 0})`);

  await page.locator('.wm-tile[data-zone="3"]').click({ force: true, timeout: 1000 }).catch(() => {});
  check(await page.evaluate(() => WorldMap.view === 'world'), 'An unexplored tile does not open');
  // The meadow's own map: fog everywhere but the middle cell; nothing from the fog is listed or drawn.
  await page.locator('.wm-tile[data-zone="0"]').click();
  check(await visible('#wm-zone') && await page.locator('.wm-gate').count() === 0 && await page.locator('.wm-hub').count() === 0, 'In the meadow, the unseen gate and Alderhaven are not marked');
  const fogs = await page.evaluate(() => { const g = document.getElementById('wm-fog').getContext('2d'), a = (x, y) => g.getImageData(x, y, 1, 1).data[3]; return { mid: a(384, 384), corner: a(20, 20), north: a(384, 60), south: a(384, 700) }; });
  check(fogs.mid === 0 && fogs.corner > 200 && fogs.north > 200 && fogs.south > 200, `The zone map is clear in the visited cell only (${JSON.stringify(fogs)})`);
  const dotsOut = await page.evaluate(() => { const g = document.getElementById('wm-dots').getContext('2d').getImageData(0, 0, 768, 768).data; let inside = 0, outside = 0; for (let y = 0; y < 768; y++) for (let x = 0; x < 768; x++) if (g[(y * 768 + x) * 4 + 3] > 0) { if (x >= 244 && x < 524 && y >= 244 && y < 524) inside++; else outside++; } return { inside, outside }; });
  check(dotsOut.inside > 0 && dotsOut.outside === 0, `Enemy dots are drawn only inside the visited cell (${dotsOut.inside} in, ${dotsOut.outside} out)`);
  const meadowSide = await page.locator('#wm-side').textContent();
  const inCell = await page.evaluate(() => WORLD_MAP.slimes.filter(s => Field.fog.seen(0, s.x, s.y)).length);
  check(/Charted 1 of 9 places/.test(meadowSide) && !/Alderhaven: sanctuary/.test(meadowSide) && !/Gates/.test(meadowSide), 'The side panel counts one of nine places and omits the unseen town and gates');
  check((await page.locator('.wm-kind small').allTextContents()).reduce((n, t) => n + Number(t.split('·')[1] || 0), 0) <= inCell && inCell > 0, `Only the ${inCell} enemies in the visited cell are listed`);
  await shot('map-fog-meadow');
  await press('Escape'); await press('Escape');

  // A travel master is a visible navigation landmark even when her cell is still misted over.
  await stand(9, 150, 35);
  check(await page.evaluate(() => !Field.fog.seen(9, 100, 164)), 'Nacrehold’s travel-master cell is still unexplored');
  const masterPx = await miniPx(75, 123);
  check(masterPx[1] > 200 && masterPx[0] < 220 && masterPx[2] > 190, `The minimap spark marks Auralis through the mist (${masterPx})`);
  await press('m');
  check(await page.locator('.wm-tile[data-zone="9"] .wm-travel-badge').isVisible(), 'A visited city shows a travel-master badge on the world sheet');
  await page.locator('.wm-tile[data-zone="9"]').click();
  check(await page.locator('.wm-travel[data-npc="travel_nacrehold"]').count() === 1 && (await page.locator('.wm-travel-list').textContent()).includes('Travel Master Auralis'), 'The Nacrehold map and side list name Auralis');
  check(await page.evaluate(() => { const m = document.querySelector('.wm-travel[data-npc="travel_nacrehold"]'); return Math.abs(parseFloat(m.style.left) - 100 / 192 * 100) < .01 && Math.abs(parseFloat(m.style.top) - 164 / 192 * 100) < .01; }), 'Auralis is marked at her exact map coordinates even before that cell is charted');
  await shot('map-nacrehold-travel');
  await press('Escape'); await press('Escape');

  // --- visiting the other zones uncovers one cell each, and the glacier two ---
  await stand(1, 48, 86); await stand(2, 64, 118); await stand(2, 64, 52); await stand(3, 64, 9); await stand(5, 15, 111); await stand(6, 12, 150); await stand(7, 80, 144); await stand(8, 80, 160); await stand(4, 80, 150);
  const later = await page.evaluate(() => Field._debug.zones.slice(9).map((z,i) => ({zone:i+9,...z.spawn})));
  for (const z of later) await stand(z.zone,z.x,z.y);
  await stand(4,80,150);
  await press('m');
  const all = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => ({ name: t.querySelector('b').textContent, small: t.querySelector('small').textContent, disabled: t.disabled })));
  check(all.map(t => t.name).join() === data.zones.map(z => z.name).join() && all.every(t => !t.disabled), `Every visited zone is named again: ${all.map(t => t.name).join(', ')}`);
  const masters = await page.evaluate(() => Field._debug.zones.map((z, zone) => ({ zone, size: z.size, npcs: (z.npcs || []).filter(n => n.travelStop) })).filter(z => z.npcs.length));
  check(masters.reduce((n, z) => n + z.npcs.length, 0) === 14 && masters.length === 13, 'The catalog includes all 14 travel masters across 13 zones');
  check(await page.locator('.wm-travel-badge:visible').count() === masters.length, 'Every visited travel-master zone has a world-sheet badge');
  for (const z of masters) {
    await page.locator(`.wm-tile[data-zone="${z.zone}"]`).click();
    const marks = await page.evaluate(() => [...document.querySelectorAll('.wm-travel')].map(m => ({ id: m.dataset.npc, x: parseFloat(m.style.left), y: parseFloat(m.style.top) })));
    check(marks.length === z.npcs.length && z.npcs.every(n => marks.some(m => m.id === n.id && Math.abs(m.x - n.x / z.size * 100) < .01 && Math.abs(m.y - n.y / z.size * 100) < .01)), `${data.zones[z.zone].name}: every travel master has an exact zone-map marker`);
    await page.locator('#wm-back').click();
  }
  check(/^Lv 5–10 · 1\/9/.test(all[1].small) && /^Lv 10–15 · 2\/9/.test(all[2].small) && /^Lv 15–20 · 1\/9/.test(all[3].small) && /^Safe city · 1\/9/.test(all[4].small) && /^Lv 20 · 5 players · 1\/9/.test(all[5].small) && /^Lv 2–5 · 1\/9/.test(all[0].small) && /^Lv 20–30 · 1\/9/.test(all[6].small), `Levels and charted counts on the tiles: ${all.map(t => t.small).join(' | ')}`);
  const roads = await page.evaluate(() => [...document.querySelectorAll('.wm-roads [data-road]')].filter(r => r.getAttribute('visibility') === 'visible').map(r => r.dataset.road).sort());
  const expectedRoads = [...new Set(data.zones.flatMap((z,i) => z.portals.map(to => [i,to].sort().join('-'))))].sort();
  check(roads.join() === expectedRoads.join(), `Roads appear once either end's gate has been seen (${roads})`);
  check(await page.evaluate(() => [...document.querySelectorAll('.wm-tile canvas:not(.wm-tile-fog)')].every(c => { const g = c.getContext('2d').getImageData(0, 0, 220, 220).data; const set = new Set(); for (let i = 0; i < g.length; i += 4 * 97) set.add((g[i] >> 4) + ',' + (g[i + 1] >> 4) + ',' + (g[i + 2] >> 4)); return set.size >= 6; })), 'Every tile carries drawn ground under its fog');
  await shot('map-world');

  // --- zooming into a zone ---
  await page.locator('.wm-tile[data-zone="2"]').click();
  check(await visible('#wm-zone') && await page.locator('#wm-world').isHidden() && await page.evaluate(() => WorldMap.view === 'zone' && WorldMap.zone === 2), 'Pressing the Glacier tile zooms into its map');
  check(await page.locator('#wm-title').textContent() === 'World Map › Rimeveil Glacier' && await visible('#wm-back'), 'The title names the zone and a Back to world button appears');
  const ground = await page.evaluate(() => { const g = document.getElementById('wm-ground').getContext('2d').getImageData(0, 0, 768, 768).data; let r = 0, b = 0, n = 0; for (let i = 0; i < g.length; i += 4 * 61) { r += g[i]; b += g[i + 2]; n++; } return { r: r / n, b: b / n }; });
  check(ground.b > 140 && ground.r > 100, `The glacier ground is pale and cold (${ground.r | 0},${ground.b | 0})`);
  const gl = await page.evaluate(() => { const g = document.getElementById('wm-fog').getContext('2d'), a = (x, y) => g.getImageData(x, y, 1, 1).data[3]; return { south: a(384, 700), centre: a(384, 384), north: a(384, 40), west: a(40, 384) }; });
  check(gl.south === 0 && gl.centre === 0 && gl.north > 200 && gl.west > 200, `Two glacier cells are clear, the north and west are fog (${JSON.stringify(gl)})`);
  await shot('map-glacier');
  const gates = await page.evaluate(() => [...document.querySelectorAll('.wm-gate')].map(g => ({ id: g.dataset.portal, to: g.dataset.to, label: g.textContent, x: g.style.left, y: g.style.top })));
  check(gates.map(g => g.id).join() === 'crags_gate,fen_gate,city_gate' && gates.map(g => g.label).join() === 'to Emberfall Crags,to Gloamfen,to Skaldholm', `Its three gates are marked and say where they lead (${gates.map(g => g.label)})`);
  const gp = await page.evaluate(() => Field._debug.zones[2].portals.map(p => [p.x / 128 * 100, p.y / 128 * 100]));
  check(gates.every((g, i) => Math.abs(parseFloat(g.x) - gp[i][0]) < .01 && Math.abs(parseFloat(g.y) - gp[i][1]) < .01), 'Each gate sits at the real portal position');
  check(await page.evaluate(() => { const l = [...document.querySelectorAll('.wm-gate-label')].map(e => e.getBoundingClientRect()); return l.every((a, i) => l.every((b, j) => i >= j || a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top)); }), 'The three gate labels do not cover one another');
  check(await page.evaluate(() => { const r = document.querySelector('.wm-stage').getBoundingClientRect(), p = document.querySelector('.wm-panel').getBoundingClientRect(); return r.width === r.height && r.right <= p.right && r.bottom <= p.bottom; }), 'The zone map is square and inside the panel');
  check(await page.locator('.wm-hub').textContent() === 'Rimeward Camp', 'The camp is labelled');
  const expectKinds = await page.evaluate(() => { const n = {}; for (const s of Field._debug.zones[2].slimes) if (Field.fog.seen(2, s.x, s.y)) n[s.kind] = (n[s.kind] || 0) + 1; return n; });
  const listed = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('.wm-kind')].map(b => [b.dataset.kind, Number(b.querySelector('small').textContent.split('·')[1])])));
  check(JSON.stringify(listed) === JSON.stringify(expectKinds) && Object.keys(listed).length >= 1, `The legend counts only enemies in uncovered cells (${JSON.stringify(listed)})`);
  const side = await page.locator('#wm-side').textContent();
  const questCount = await page.evaluate(() => Field._debug.zones[2].quests.length);
  check(/Recommended levels 10–15/.test(side) && side.includes(`${questCount} quests`) && /Charted 2 of 9 places/.test(side), 'It gives the level range, the quest count and how much is charted');
  const dots = () => page.evaluate(() => { const g = document.getElementById('wm-dots').getContext('2d').getImageData(0, 0, 768, 768).data; let a = 0; for (let i = 3; i < g.length; i += 4) if (g[i] > 200) a++; return a; });
  const kind = Object.keys(listed)[0], total = Object.values(listed).reduce((a, b) => a + b, 0);
  const lit = await dots(); await page.locator(`.wm-kind[data-kind="${kind}"]`).hover(); const one = await dots();
  if (Object.keys(listed).length > 1) check(lit > 0 && one > 0 && one < lit, `Hovering a kind brightens its dots only (${one} of ${lit} opaque pixels, ${total} enemies)`);
  await page.mouse.move(5, 5); check(await dots() === lit, 'Moving away restores them');
  // Through a gate, straight to the next zone's map.
  await page.locator('.wm-gate[data-portal="fen_gate"]').click();
  check(await page.locator('#wm-title').textContent() === 'World Map › Gloamfen' && await page.locator('.wm-hub').textContent() === 'Lanternmere', 'Pressing a gate opens the zone beyond it');
  check(await page.locator('.wm-gate').count() === 1 && await page.locator('.wm-gate').textContent() === 'to Rimeveil Glacier', 'Gloamfen shows its summit gate, which stands in the cell the hero visited');
  await page.locator('.wm-me').waitFor({ state: 'hidden' });
  await page.locator('#wm-back').click(); await page.locator('.wm-tile[data-zone="2"]').click();
  await page.locator('.wm-gates button[data-to="1"]').click();
  check(await page.locator('#wm-title').textContent() === 'World Map › Emberfall Crags', 'The Gates list navigates too');
  check(await page.locator('.wm-gate[data-portal="rimeveil_gate"]').count() === 0 && await page.locator('.wm-gate[data-portal="meadow_gate"]').count() === 1, 'The Crags show the meadow gate they came through and not the unseen north gate');
  await page.locator('.wm-gate[data-portal="meadow_gate"]').isDisabled().then(d => check(d === false, 'A gate to a visited zone can be pressed'));
  check(await page.locator('.wm-me').isHidden() && /You are in Skaldholm/.test(await page.locator('#wm-here').textContent()), 'In another zone the map says where you are instead');
  // --- stepping back ---
  await press('Escape');
  check(await visible('#worldmap') && await visible('#wm-world') && await page.locator('#wm-zone').isHidden(), 'Esc from a zone goes back to the world, not out of the map');
  await page.locator('.wm-tile[data-zone="4"]').click();
  await page.locator('#wm-back').click();
  check(await visible('#wm-world') && await page.locator('#wm-title').textContent() === 'World Map', 'The Back button returns to the world');
  await page.locator('.wm-tile[data-zone="3"]').click(); await press('Backspace');
  check(await visible('#wm-world'), 'Backspace also goes back');
  await press('Escape');
  check(!await visible('#worldmap'), 'Esc from the world closes the map');

  // --- the hero's marker follows, and the map uncovers new ground while it is open ---
  await press('m');
  check(/1\/9 charted/.test(await page.locator('.wm-tile[data-zone="3"] small').textContent()), 'Gloamfen starts with one place charted');
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 3, x: 90, y: 40 } }));
  await page.waitForFunction(() => Field.zone === 3 && Math.hypot(Field.hero.x - 90, Field.hero.y - 40) < 2, null, { timeout: 15000 });
  await page.waitForFunction(() => /2\/9 charted/.test(document.querySelector('.wm-tile[data-zone="3"] small').textContent), null, { timeout: 3000 });
  check(true, 'Standing in a new cell uncovers it on the open map within a moment');
  const here = await page.evaluate(() => [...document.querySelectorAll('.wm-you')].map(y => !y.hidden).join());
  check(here === data.zones.map((_,i)=>i===3).join(), `The marker moved to the Gloamfen tile (${here})`);
  await page.locator('.wm-tile[data-zone="3"]').click();
  await page.waitForFunction(() => { const m = document.querySelector('.wm-me'); return m && !m.hidden; });
  const fogNow = await page.evaluate(() => { const g = document.getElementById('wm-fog').getContext('2d'); return g.getImageData(Math.round(106 / 128 * 768), Math.round(21 / 128 * 768), 1, 1).data[3]; });
  check(fogNow === 0, 'The new cell is clear on the zone map');
  const me = await page.evaluate(() => { const s = document.querySelector('.wm-stage').getBoundingClientRect(), m = document.querySelector('.wm-me i').getBoundingClientRect(); return { x: (m.left + m.width / 2 - s.left) / s.width, y: (m.top + m.height / 2 - s.top) / s.height, hx: Field.hero.x / 128, hy: Field.hero.y / 128 }; });
  check(Math.abs(me.x - me.hx) < .01 && Math.abs(me.y - me.hy) < .01, `"You" stands at the hero's place on the zone map (${me.x.toFixed(3)},${me.y.toFixed(3)} vs ${me.hx.toFixed(3)},${me.hy.toFixed(3)})`);
  await shot('map-gloamfen');
  await press('Escape'); await press('Escape');

  // --- other panels and keys ---
  await press('q');
  check(await page.evaluate(() => Quests.open), 'Q opens the quest journal');
  await press('m');
  check(!await visible('#worldmap'), 'M does nothing while the journal is open');
  await press('Escape');
  await press('m');
  await press('q'); await press('i'); await press('e');
  check(await visible('#worldmap') && !await page.evaluate(() => Quests.open) && await page.locator('#equipment').isHidden(), 'With the map open, Q, I and E do not open panels behind it');
  await press('Escape');
  const sound = () => page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).sound);
  const before = await sound(); await press('n');
  check(await sound() === !before && !await visible('#worldmap'), 'N toggles the sound in the field and M no longer does');
  await press('n');
  check(await sound() === before, 'N toggles it back');

  // --- the zoom animation (motion allowed) ---
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await press('m');
  await page.locator('.wm-tile[data-zone="1"]').click();
  check(await page.evaluate(() => document.getElementById('wm-body').dataset.view) === 'zooming', 'With motion on, the sheet zooms toward the tile first');
  await page.waitForFunction(() => !document.getElementById('wm-zone').hidden && WorldMap.view === 'zone', null, { timeout: 3000 });
  check(await page.evaluate(() => { const w = document.getElementById('wm-world'); return w.hidden && !w.style.transform && !w.style.opacity; }), 'After the zoom the world sheet is reset for next time');
  await page.locator('#wm-back').click();
  await page.waitForFunction(() => { const w = document.getElementById('wm-world'); return !w.hidden && !w.style.transform && getComputedStyle(w).opacity === '1'; }, null, { timeout: 3000 });
  check(await page.evaluate(() => { const w = document.getElementById('wm-world'); return !w.hidden && !w.style.transform && getComputedStyle(w).opacity === '1'; }), 'Zooming back out ends on the full sheet');
  await press('Escape');
  check(await page.evaluate(() => Field.canAct), 'Closing the map hands the game back');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} world map UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
