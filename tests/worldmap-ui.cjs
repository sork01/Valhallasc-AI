// Browser checks for the world map (M) on the organic atlas: it opens and closes with the keys, shows one tile per
// outdoor province from the painted reference, marks dungeon entrances, zooms into a zone with its gates and enemies,
// follows the hero, and leaves the other panels alone. The enemy legend must cover every kind the map spawns.
// MUTATE=legend drops one map kind from the legend; MUTATE=levels puts the Lantern Queen back at 83. Both must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs'); requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
let browser, world, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
(async () => {
  // Source data: the map is the authority for which zones exist, which kinds they spawn and who travels.
  const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
  const zones = [map, ...(map.zones || [])];
  const mapKinds = new Set(zones.filter(z => !z.sealedTemplate && z.theme !== 'arena').flatMap(z => (z.slimes || []).map(s => s.kind)));
  const masters = zones.map((z, zone) => ({ zone, size: z.size, npcs: (z.npcs || []).filter(n => n.travelStop) })).filter(z => z.npcs.length);
  check(mapKinds.size >= 300, `The map spawns ${mapKinds.size} enemy kinds in open zones (floor 300)`);
  check(masters.length >= 20 && masters.reduce((n, z) => n + z.npcs.length, 0) >= 25, `The map has ${masters.reduce((n, z) => n + z.npcs.length, 0)} travel masters in ${masters.length} zones (floors 25 and 20)`);
  // The server's default levels for enemies: world.rs `default_level`, plus the catalogs the server merges in.
  const rust = fs.readFileSync(path.join(root, 'server/src/world.rs'), 'utf8');
  const body = rust.slice(rust.indexOf('pub fn default_level'), rust.indexOf('// Gold carried by a default-level enemy'));
  const server = {}; for (const [, names, level] of body.matchAll(/((?:"\w+"\s*\|?\s*)+)=>\s*(\d+)/g)) for (const [, name] of names.matchAll(/"(\w+)"/g)) server[name] = Number(level);
  for (const catalog of ['cathedral', 'eye_below', 'elder_hollow', 'thousandfold', 'rain_crown', 'seed_vault', 'sunken_astrolabe', 'thunderheart_gate', 'blooming_labyrinth', 'solar_crucible', 'amber_archive', 'silent_solstice', 'emberwake', 'empty-seat-enemies', 'raid_key', 'chained_forge', 'blackhour', 'longship', 'nornroot', 'skybridge']) {
    const file = path.join(root, `world/${catalog}.txt`);
    if (fs.existsSync(file)) Object.assign(server, Object.fromEntries(JSON.parse(fs.readFileSync(file, 'utf8')).map(e => [e.kind, e.level])));
  }
  check(Object.keys(server).length >= 17, `Parsed ${Object.keys(server).length} enemy levels from world.rs`);

  world = new TestWorld();
  await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !/401|Failed to load resource/.test(message.text())) errors.push(message.text()); });
  if (process.env.MUTATE) {
    const source = fs.readFileSync(path.join(root, 'client/worldmap.js'), 'utf8');
    let changed = source;
    if (process.env.MUTATE === 'legend') changed = source.replace(/\n\s*slagmaw: \['Slagmaw \(Elite\)'[^\n]*\n/, '\n');
    if (process.env.MUTATE === 'levels') changed = source.replace("lanternqueen:['Lantern Queen (Elite · 3 players)',82,", "lanternqueen:['Lantern Queen (Elite · 3 players)',83,");
    assert.notEqual(changed, source, 'mutation target exists');
    await page.route('**/worldmap.js', r => r.fulfill({ contentType: 'text/javascript', body: changed }));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('MapUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const shot = name => page.screenshot({ path: path.join(world.runDir, name + '.png') });
  const visible = id => page.locator(id).isVisible();
  // A province opens from its name label (the tile is covered there); a DOM click runs the same handler as a press.
  const openTile = zone => page.evaluate(zone => (document.querySelector(`.wm-name[data-zone="${zone}"]`) || document.querySelector(`.wm-city[data-zone="${zone}"]`) || document.querySelector(`.wm-tile[data-zone="${zone}"]`)).click(), zone);
  const press = async key => { await page.evaluate(() => document.activeElement?.blur?.()); await page.keyboard.press(key); };

  // --- the data the map was written against ---
  const data = await page.evaluate(() => ({
    zones: Field._debug.zones.map(z => ({ name: z.name, sealed: !!z.sealedTemplate || z.theme === 'arena', players: z.players || 0 })),
    tiles: WORLD_MAP.atlas.regions.map(r => r.zone),
    legend: Object.fromEntries(Object.entries(WorldMap._kinds).map(([k, v]) => [k, v[1]])),
    cities: WORLD_MAP.atlas.cities.map(c => c.zone),
  }));
  // Masters a player can open from the sheet: province tiles and the nested cities (interiors need a visit first).
  const reachable = masters.filter(m => data.tiles.includes(m.zone) || data.cities.includes(m.zone));
  check(data.tiles.length >= 20 && new Set(data.tiles).size === data.tiles.length && data.tiles.every(z => !data.zones[z].players && !data.zones[z].sealed), `One tile per outdoor province (${data.tiles.length}), none of them a dungeon or arena`);
  check(await page.evaluate(() => { const graph = WorldMap._graph, seen = new Set([0]), queue = [0]; for (const i of queue) for (const edge of graph[i]) { if (!graph[edge.to].some(back => back.to === i)) return false; if (!seen.has(edge.to)) { seen.add(edge.to); queue.push(edge.to); } } return graph.length === Field._debug.zones.length && seen.size === Field._debug.zones.filter(z => !z.sealedTemplate && z.theme !== 'arena').length; }), 'The authoritative gate graph is reciprocal and connects every open zone');
  // Legend: every kind the map spawns is listed, with the server's level (Lantern Queen is 82 on both sides).
  const missing = [...mapKinds].filter(k => !(k in data.legend));
  check(missing.length === 0, `Every kind the map spawns is in the legend (missing: ${missing.join(', ') || 'none'})`);
  const levelMismatch = Object.entries(data.legend).filter(([k, level]) => mapKinds.has(k) && (server[k] ?? level) !== level).map(([k, level]) => `${k} ${level}`);
  check(levelMismatch.length === 0, `The legend levels equal the server's (${levelMismatch.join(', ') || 'none differ'})`);
  check(data.legend.lanternqueen === server.lanternqueen, `Lantern Queen reads ${data.legend.lanternqueen}, the server's default ${server.lanternqueen}`);

  // --- opening and closing ---
  check(!await visible('#worldmap') && await visible('#wm-open'), 'The map is closed and a globe button is on the minimap');
  check(await page.evaluate(() => { const b = document.getElementById('wm-open'); return !b.textContent.trim() && !!b.querySelector('svg circle') && b.getAttribute('aria-label').includes('(M)'); }), 'The globe is an icon with an accessible name');
  await press('m');
  check(await visible('#worldmap') && await page.evaluate(() => WorldMap.open && WorldMap.view === 'world'), 'M opens the world map on the world view');
  check(await page.locator('.wm-tile').count() === data.tiles.length, 'The world sheet draws exactly one tile per province');
  check(await page.evaluate(() => !Field.canAct), 'The game is paused behind the map');
  check(await page.locator('#pause').isHidden(), 'M does not open the pause menu');
  check(await page.evaluate(() => document.querySelectorAll('.wm-roads, .wm-connection-path, .wm-route-road').length === 0), 'No inter-zone road overlay is drawn on the world map');
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
    await page.waitForFunction(([zone, x, y]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 3 && (Field.explored[zone] & (1 << (Math.min(2, Math.floor(y / Field._debug.zones[zone].size * 3)) * 3 + Math.min(2, Math.floor(x / Field._debug.zones[zone].size * 3))))), [zone, x, y], { timeout: 15000 });
  };
  // A new hero starts on the pier, so the one charted cell is the 3x3 cell under the hero (not necessarily the middle).
  const cell = await page.evaluate(() => { const z = Field._debug.zones[0], col = Math.min(2, Math.floor(Field.hero.x / z.size * 3)), row = Math.min(2, Math.floor(Field.hero.y / z.size * 3)); return { col, row, bit: row * 3 + col }; });
  check(await page.evaluate(bit => JSON.stringify(Field.explored) === JSON.stringify([1 << bit]), cell.bit), `A new character has uncovered only the cell under the hero in Greenmeadow (${cell.col},${cell.row})`);
  await press('m');
  const first = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => ({ zone: +t.dataset.zone, disabled: t.disabled, fog: t.dataset.fog })));
  check(first.find(t => t.zone === 0) && !first.find(t => t.zone === 0).disabled && first.filter(t => t.zone !== 0).every(t => t.disabled && t.fog === 'full'), 'Only Greenmeadow is known; every other tile is unexplored and disabled');
  check(await page.evaluate(() => document.activeElement.classList.contains('wm-tile') && document.activeElement.dataset.zone === '0'), 'Focus starts on the tile of the zone you are in');
  const stage = await page.evaluate(() => { const r = document.getElementById('wm-world').getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }; });
  const tiles = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => { const r = t.getBoundingClientRect(); return { left: r.left, top: r.top, right: r.right, bottom: r.bottom }; }));
  check(tiles.every(t => t.left >= stage.left - 1 && t.right <= stage.right + 1 && t.top >= stage.top - 1 && t.bottom <= stage.bottom + 1), 'Every province tile is inside the world sheet');
  const you = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => ({ zone: +t.dataset.zone, here: t.dataset.here === 'true', shown: !t.querySelector('.wm-you').hidden })));
  check(you.filter(y => y.shown).map(y => y.zone).join() === '0' && you.find(y => y.zone === 0).here, 'The marker is on Greenmeadow, the only tile marked as where you are');
  const panel = await page.locator('.wm-panel').boundingBox();
  check(panel.x >= 0 && panel.y >= 0 && panel.x + panel.width <= 1440 && panel.y + panel.height <= 900, `The panel fits the window (${panel.width | 0}x${panel.height | 0})`);
  // Names on the sheet do not collide with each other.
  const names = await page.evaluate(() => [...document.querySelectorAll('.wm-name')].filter(n => !n.hidden).map(n => { const r = n.getBoundingClientRect(); return { zone: +n.dataset.zone, left: r.left, top: r.top, right: r.right, bottom: r.bottom }; }));
  const overlap = (a, b) => !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
  check(names.every((a, i) => names.every((b, j) => i >= j || !overlap(a, b))), `No two names on the sheet overlap (${names.length} shown)`);
  await openTile(3).catch(() => {});
  check(await page.evaluate(() => WorldMap.view === 'world'), 'An unexplored tile does not open');
  // The meadow's own map: fog everywhere but the middle cell; nothing from the fog is listed or drawn.
  await openTile(0);
  check(await visible('#wm-zone') && await page.locator('.wm-gate').count() === 0 && await page.locator('.wm-hub').count() === 0, 'In the meadow, the unseen gate and the town are not marked');
  const fogs = await page.evaluate(({ col, row }) => { const g = document.getElementById('wm-fog').getContext('2d'), a = (x, y) => g.getImageData(x, y, 1, 1).data[3]; return { cell: a(col * 256 + 128, row * 256 + 128), corner: a(20, 20), north: a(384, 60), far: a(700, 20) }; }, cell);
  check(fogs.cell === 0 && fogs.corner > 200 && fogs.north > 200 && fogs.far > 200, `The zone map is clear in the visited cell only (${JSON.stringify(fogs)})`);
  // The visited cell is the 256-pixel cell of the 3x3 grid under the hero.
  const dotsOut = await page.evaluate(({ col, row }) => { const g = document.getElementById('wm-dots').getContext('2d').getImageData(0, 0, 768, 768).data; let inside = 0, outside = 0; for (let y = 0; y < 768; y++) for (let x = 0; x < 768; x++) if (g[(y * 768 + x) * 4 + 3]) ((x >= col * 256 && x < col * 256 + 256 && y >= row * 256 && y < row * 256 + 256) ? inside++ : outside++); return { inside, outside }; }, cell);
  check(dotsOut.outside === 0, `Enemy dots are drawn only inside the visited cell (${dotsOut.inside} in, ${dotsOut.outside} out)`);
  const meadowSide = await page.locator('#wm-side').textContent();
  check(/Charted 1 of 9 places/.test(meadowSide) && !/Gates/.test(meadowSide), 'The side panel counts one of nine places and omits the unseen gates');
  const inCell = await page.evaluate(() => WORLD_MAP.slimes.filter(s => Field.fog.seen(0, s.x, s.y)).length);
  check((await page.locator('.wm-kind small').allTextContents()).reduce((n, t) => n + Number(t.split('·')[1] || 0), 0) <= inCell, `Only enemies in the visited cell are listed (${inCell} there)`);
  await shot('map-fog-meadow');
  await press('Escape'); await press('Escape');

  // A travel master is a visible navigation landmark even when her cell is still misted over.
  const nacrehold = masters.find(m => m.npcs.some(n => n.id === 'travel_nacrehold'));
  check(!!nacrehold, 'The map places the Nacrehold travel master');
  await stand(nacrehold.zone, 150, 35);
  await press('m');
  // The old travel-master badge is no longer rendered by the organic sheet (its CSS remains): the tile itself must be open.
  check(await page.locator(`.wm-name[data-zone="${nacrehold.zone}"]`).isEnabled(), 'A visited travel-master city is open on the world sheet');
  await openTile(nacrehold.zone);
  check(await page.locator('.wm-travel[data-npc="travel_nacrehold"]').count() === 1, 'The Nacrehold map marks its travel master');
  await shot('map-nacrehold-travel');
  await press('Escape'); await press('Escape');

  // Visit the other open zones so every name is charted, then check every travel master's marker.
  // One debug call charts every zone (one teleport per zone exhausts the 1.5 GiB runner).
  await page.evaluate(() => Online.send({ type: 'debug', ref: 812, command: { op: 'explore_all' } }));
  await page.waitForFunction(() => Field.explored?.[46] === 511, null, { timeout: 15000 });
  await press('m');
  const all = await page.evaluate(() => [...document.querySelectorAll('.wm-tile')].map(t => ({ zone: +t.dataset.zone, disabled: t.disabled })));
  check(all.every(t => !t.disabled), 'Every visited zone is named again');
  // Each province view keeps its scenery art, so opening all masters exceeds the 1.5 GiB runner: sample six, Nacrehold among them.
  const sample = [...new Set([nacrehold, ...reachable.slice(0, 6)])];
  for (const z of sample) {
    await openTile(z.zone);
    const marks = await page.evaluate(() => [...document.querySelectorAll('.wm-travel')].map(m => ({ id: m.dataset.npc, x: parseFloat(m.style.left), y: parseFloat(m.style.top) })));
    check(z.npcs.every(n => marks.some(m => m.id === n.id && Math.abs(m.x - n.x / z.size * 100) < .01 && Math.abs(m.y - n.y / z.size * 100) < .01)), `Zone ${z.zone} marks its ${z.npcs.length} travel master(s) at their real positions (sample of ${sample.length} of ${reachable.length})`);
    await page.locator('#wm-back').click();
  }
  check(await page.evaluate(() => document.querySelectorAll('.wm-roads, .wm-connection-path').length === 0), 'No inter-zone dashed road connectors appear after charting zones');
  await shot('map-world');

  // --- zooming into a zone ---
  // The map is already open from the explore step above: do not press M again (it would close the map).
  const rimeveil = data.tiles.find(z => zones[z]?.name === 'Rimeveil Glacier') ?? 2;
  await openTile(rimeveil);
  await page.waitForFunction(z => WorldMap.view === 'zone' && WorldMap.zone === z, rimeveil, { timeout: 5000 }).catch(() => {});
  check(await page.evaluate(z => { const w = document.getElementById('wm-world'), zn = document.getElementById('wm-zone'); return WorldMap.view === 'zone' && WorldMap.zone === z && w.hidden && !zn.hidden; }, rimeveil), 'Pressing the Glacier tile zooms into its own map');
  check(await page.locator('#wm-title').textContent() === 'World Map › Rimeveil Glacier' && (await page.evaluate(() => !document.getElementById('wm-back').hidden)), `The title names the zone and a Back to world button appears (${JSON.stringify(await page.locator('#wm-title').textContent())}, back ${(await page.evaluate(() => !document.getElementById('wm-back').hidden))})`);
  const gl = await page.evaluate(() => { const g = document.getElementById('wm-fog').getContext('2d'), a = (x, y) => g.getImageData(x, y, 1, 1).data[3]; return { centre: a(384, 384), north: a(384, 60), west: a(20, 384) }; });
  check(gl.centre === 0 && gl.north === 0 && gl.west === 0, `After explore_all the glacier map is clear (${JSON.stringify(gl)})`);
  const gates = await page.evaluate(() => [...document.querySelectorAll('.wm-gate')].map(g => ({ id: g.dataset.portal, to: +g.dataset.to, label: g.textContent, x: parseFloat(g.style.left), y: parseFloat(g.style.top) })));
  const portals = await page.evaluate(z => Field._debug.zones[z].portals.map(p => ({ id: p.id, to: p.to, x: p.x / Field._debug.zones[z].size * 100, y: p.y / Field._debug.zones[z].size * 100 })), rimeveil);
  check(gates.length >= 1 && gates.every(g => portals.some(p => p.id === g.id && p.to === g.to && Math.abs(p.x - g.x) < .01 && Math.abs(p.y - g.y) < .01)), `Each gate on the zone map is a real portal at its real position (${gates.length} shown)`);
  check(gates.every(g => g.label.startsWith('to ')), 'Every gate says where it leads');
  check(await page.evaluate(() => { const l = [...document.querySelectorAll('.wm-gate-label')].map(e => e.getBoundingClientRect()); return l.every((a, i) => l.every((b, j) => i >= j || a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top)); }), 'No two gate labels overlap');
  await shot('map-glacier');
  const expectKinds = await page.evaluate(z => { const n = {}; for (const s of Field._debug.zones[z].slimes) if (Field.fog.seen(z, s.x, s.y)) n[s.kind] = (n[s.kind] || 0) + 1; return n; }, rimeveil);
  const listed = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('.wm-kind')].map(b => [b.dataset.kind, Number(b.querySelector('small').textContent.split('·')[1])])));
  const sorted = o => JSON.stringify(Object.entries(o).sort(([a], [b]) => a.localeCompare(b)));
  check(sorted(listed) === sorted(expectKinds), `The legend counts only enemies in uncovered cells (${JSON.stringify(listed)})`);
  check(Object.keys(listed).every(k => mapKinds.has(k)), 'Every listed kind is one the map spawns');
  const side = await page.locator('#wm-side').textContent();
  check(side.includes(`${await page.evaluate(z => Field._debug.zones[z].quests.length, rimeveil)} quests`) && /Charted \d of 9 places/.test(side), 'The side panel gives the quest count and how much is charted');
  const dots = () => page.evaluate(() => { const g = document.getElementById('wm-dots').getContext('2d').getImageData(0, 0, 768, 768).data; let a = 0; for (let i = 3; i < g.length; i += 4) if (g[i] > 0) a++; return a; });
  const shown = await page.locator('.wm-kind').evaluateAll(bs => bs.filter(b => b.getBoundingClientRect().width > 0).map(b => b.dataset.kind));
  const kind = shown[0];
  check(shown.length > 0, `The legend rows are on screen (${shown.length} of ${Object.keys(listed).length})`);
  if (kind && Object.keys(listed).length > 1) { const lit = await dots(); await page.locator(`.wm-kind[data-kind="${kind}"]`).hover(); const one = await dots(); check(lit > 0 && one > 0 && one < lit, `Hovering a kind brightens its dots only (${one} of ${lit})`); await page.mouse.move(5, 5); check(await dots() === lit, 'Moving away restores them'); }
  await shot('map-glacier');
  // Through a gate, straight to the next zone's map.
  const gate = gates[0];
  await page.locator(`.wm-gate[data-portal="${gate.id}"]`).click();
  const next = zones[gate.to].name;
  check(await page.locator('#wm-title').textContent() === `World Map › ${next}`, `Pressing a gate opens the zone beyond it (${next})`);
  await page.locator('#wm-back').click();
  await openTile(rimeveil);
  await page.locator(`.wm-gates button[data-to="${gate.to}"]`).click();
  check(await page.locator('#wm-title').textContent() === `World Map › ${next}`, 'The Gates list navigates too');
  // --- stepping back ---
  await press('Escape');
  check(await visible('#worldmap') && await visible('#wm-world') && await page.locator('#wm-zone').isHidden(), 'Esc from a zone goes back to the world, not out of the map');
  await openTile(0);
  await page.locator('#wm-back').click();
  check(await visible('#wm-world') && await page.locator('#wm-title').textContent() === 'World Map', 'The Back button returns to the world');
  await openTile(0); await press('Backspace');
  check(await visible('#wm-world'), 'Backspace also goes back');
  await press('Escape');
  check(!await visible('#worldmap'), 'Esc from the world closes the map');

  // --- the hero's marker follows, and the map uncovers new ground while it is open ---
  await press('m');
  await page.evaluate(() => Online.send({ type: 'debug', ref: 1, command: { op: 'teleport', zone: 0, x: 250, y: 235 } }));
  await page.waitForFunction(() => Field.zone === 0, null, { timeout: 15000 });
  await page.evaluate(() => WorldMap.show());
  check(await page.evaluate(() => document.querySelector('.wm-tile[data-zone="0"]').dataset.here === 'true'), 'Standing on Greenmeadow keeps its tile marked');
  await press('Escape');
  check(!await visible('#worldmap') && await page.locator('#pause').isHidden(), 'Esc closes the map once, without opening the pause menu');

  // --- other panels and keys ---
  await press('q');
  check(await page.evaluate(() => Quests.open), `Q opens the quest journal (${JSON.stringify(await page.evaluate(() => ({ quests: Quests.open, map: WorldMap.open, canAct: Field.canAct, active: document.activeElement?.id || document.activeElement?.className })))})`);
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

  // --- the transition (motion allowed): a zone fades in; the world sheet returns with no leftover transform ---
  // The old zoom-toward-the-tile step is gone; the view now fades (wm-fade).
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await press('m');
  await openTile(0);
  await page.waitForFunction(() => WorldMap.view === 'zone' && WorldMap.zone === 0, null, { timeout: 3000 });
  check(await page.evaluate(() => document.getElementById('wm-zone').classList.contains('wm-fade')), 'With motion on, a zone fades in');
  await page.locator('#wm-back').click();
  await page.waitForFunction(() => { const w = document.getElementById('wm-world'); return !w.hidden && !w.style.transform && getComputedStyle(w).opacity === '1'; }, null, { timeout: 3000 });
  check(await page.evaluate(() => { const w = document.getElementById('wm-world'); return !w.hidden && !w.style.transform && getComputedStyle(w).opacity === '1'; }), 'Back on the world sheet it is fully shown with no leftover transform');
  await press('Escape');
  check(await page.evaluate(() => Field.canAct), 'Closing the map hands the game back');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} world map UI checks passed; screenshots: ${world.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (world) await world.stop().catch(() => {});
});
