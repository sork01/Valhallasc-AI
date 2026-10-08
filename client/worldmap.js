'use strict';
// World map (M, or the button under the minimap). Everything is drawn from window.WORLD_MAP, so a zone added to
// world/map.txt appears with its real ground, obstacles, camp, gates and spawn points; the only hand-made part is
// LAYOUT, where each zone sits on the world sheet (tests/worldmap-ui.cjs fails when a zone has no place).
// The world view is a row of zone tiles joined by the gate roads; pressing a tile zooms into that zone's map.
(() => {
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const STAGE = { w: 100, h: 62 };
  // Square tiles on the 100x62 sheet, placed so the gates read as a journey: Greenmeadow -> Crags -> Glacier -> Gloamfen / Skaldholm -> the Wyrdwood -> Bifrost Reach, up the Stormrift -> Ran's Deep, down the Maelstrom.
  const LAYOUT = [{x:2,y:43,s:14},{x:18,y:30,s:14},{x:34,y:10,s:18},{x:12,y:4,s:18},{x:40,y:32,s:20},{x:25,y:47,s:14},{x:62,y:37,s:20},{x:54,y:2,s:18},{x:75,y:1,s:18},{x:82,y:21,s:18},{x:82,y:43,s:10},{x:92,y:43,s:8},{x:89,y:53,s:8},{x:63,y:20,s:15},{x:2,y:25,s:14},{x:2,y:13,s:10}];
  const GROUND = { meadow: '#3f9b48', ember: '#2b1f22', frost: '#cfe3f0', fen: '#2f4a2c', city: '#5f9b4a', vault: '#07080e', wyrd: '#6a5430', sky: '#1a1838', deep: '#0b3550', nacre: '#286776', astral: '#39776f', prismwaste: '#ad887e', orrery: '#37394e', cathedral_left: '#123b38', cathedral_right: '#442c3e', cathedral_main: '#161529' };
  const DIRT = { meadow: '#c9a26a', ember: '#6a5040', frost: '#9fb7cc', fen: '#8a6a40', city: '#b6a98c', vault: '#3a3f55', wyrd: '#b89860', sky: '#f0c8f4', deep: '#c8c29a', nacre: '#addbd3', astral: '#d7bc84', prismwaste: '#ead7a8', orrery: '#ad907b', cathedral_left: '#50877c', cathedral_right: '#967086', cathedral_main: '#514568' };
  const PORTAL = { meadow: '#7ae8c8', ember: '#ff8a3a', frost: '#8fd8ff', fen: '#b8e060', city: '#ffd36a', vault: '#59d9ff', wyrd: '#e0963a', sky: '#9fc4ff', deep: '#4fe0e8', nacre: '#b0ffe6', astral: '#c4b6ff', prismwaste: '#ffe3ac', orrery: '#f4c981', cathedral_left: '#64daca', cathedral_right: '#f29cb4', cathedral_main: '#d5b9ff' };
  const BLURB = {
    meadow: 'Green pastures round the walled town of Alderhaven.',
    ember: 'Lava fords and ash-grey crags above Cinderwatch Camp.',
    frost: 'Four rings of ice that spiral up to a summit bowl.',
    fen: 'A dusk fen round a dark lake, lit by the lanterns of Lanternmere.',
    wyrd: 'An autumn forest, a troll bridge and a storm-wracked moor, between Hollowmoot and Skuldwatch.',
    sky: 'Floating islands over the storm, joined by rainbow-shard bridges, around Heimdall\'s Perch.',
    deep: 'The sea floor under the storm: the Shallows round Keelhaven and the Net, a labyrinth of living coral with Ran\'s Court at its heart.',
    nacre: 'A peaceful merfolk city of 120 shell homes, coral gardens and a Meeting Stone beside the three-wing Drowned Cathedral.',
    astral: 'A grassy impact basin of starglass groves and living constellations, reached from Nacrehold.',
    prismwaste: 'A salt and mirror desert beyond Astralhollow, with three broken ridges and the Last Shade refuge.',
    orrery: 'A vast broken clock beyond the Prismwaste, with the Stillpoint refuge and two dangerous winding courts.',
    cathedral_left:'The Flooded Cloister: level 40, four bosses, a private five-player wing.',
    cathedral_right:'The Coral Reliquary: level 45, four bosses, a private five-player wing.',
    cathedral_main:'The Grand Nave: level 50, four bosses, a private five-player wing.',
    vault: 'A dungeon of bones and torchlight under the Meeting Stone, for a party of five.',
  };
  // Base level and a dot colour for every enemy kind (the level matches Slime::default_level in server/src/world.rs;
  // the test compares the two).
  const KINDS = {
    green: ['Green Slime', 2, '#4fd25f'], blue: ['Blue Slime', 3, '#4aa8ff'], pink: ['Pink Slime', 3, '#ff7bbd'], yellow: ['Golden Slime', 4, '#ffd23f'],
    beetle: ['Ironhide Beetle', 5, '#8aafbf'], big: ['King Slime', 6, '#8f6bff'],
    wisp: ['Cinder Wisp', 5, '#ee6a1c'], spider: ['Magma Spider', 7, '#b09ab8'], wraith: ['Ash Wraith', 8, '#a89cd0'], golem: ['Basalt Golem', 10, '#c0b8c0'],
    cinderlord: ['Cinderlord (Elite · 2 players)', 10, '#ffb13b'],
    crab: ['Rime Crab', 10, '#6fb3dc'], wolf: ['Frostfang Wolf', 12, '#9fb4c8'], yeti: ['Glacier Yeti', 13, '#e4eef8'], wyrm: ['Rime Wyrm', 15, '#6bc6e8'],
    gloomroot: ['Gloomroot Colossus (Elite · 5 players)', 20, '#4fe0c8'],
    toad: ['Fen Toad', 15, '#8bc34a'], croc: ['Mire Crocodile', 17, '#a9c45a'], knight: ['Drowned Knight', 18, '#8fc0a8'], hydra: ['Mire Hydra', 20, '#c4e8b0'],
    thrall: ['Vault Thrall', 19, '#d8d2bc'], archer: ['Bone Archer (ranged)', 19, '#e6dfc4'], acolyte: ['Hollow Acolyte (ranged)', 20, '#b46bff'],
    gatewarden: ['Hrolf Bonegate (Boss)', 20, '#ffd24a'], choir: ['Valka, the Hollow Choir (Boss)', 20, '#7be0ff'],
    colossus: ['Ironwake, the Vault Colossus (Boss)', 21, '#ff9a3a'], hollowking: ['Haldor, the Hollow King (Boss)', 21, '#9cff8f'],
    boar: ['Rotfang Boar', 21, '#d0603a'], crow: ['Gallowcrow (ranged)', 23, '#9a84d6'], troll: ['Mosshide Troll', 25, '#6fb064'], weaver: ['Wyrdweaver (ranged)', 27, '#c070e8'],
    galehound: ['Galehound', 30, '#9fc0ee'], prismgolem: ['Prism Golem', 31, '#a9a0f0'], skyray: ['Skyray (ranged)', 32, '#6a86d0'], einherjar: ['Hollow Einherjar', 33, '#8ad0e8'], thunderroc: ['Thunderroc', 35, '#f0c070'],
    draugr: ['Drowned Draugr', 35, '#8ac4b8'], angler: ['Lantern Angler (ranged)', 36, '#9ffff0'], moray: ['Gnashing Moray', 37, '#c8e070'], siren: ['Siren (ranged)', 38, '#ff9ae8'], shellback: ['Shellback', 39, '#a8d090'], kraken: ['The Kraken (Elite · 5 players)', 40, '#b890f0'], hvitserk: ['Hvitserk (Elite · 3 players)', 37, '#e0b43a'], ghostmaw: ['Ghostmaw (Elite · 3 players)', 39, '#d8f0f8'],
    voidmoth: ['Void Moth', 40, '#c7a8ff'], crystalwyrm: ['Crystalwyrm', 41, '#6de8ff'], orbitbeetle: ['Orbit Beetle', 42, '#f4a43a'], eclipsedryad: ['Eclipse Dryad', 43, '#9ed17a'], meteorgolem: ['Meteor Golem', 45, '#b39bd1'],
    miragejackal: ['Mirage Jackal',45,'#e7b990'], shardscarab:['Shard Scarab',46,'#99e6dc'], glassharrier:['Glass Harrier',47,'#d5c5ff'], prismsentinel:['Prism Sentinel',48,'#d5e9ed'], mirrorqueen:['Mirror Queen (Elite · 3 players)',49,'#e7b8ff'], sunshard:['Sunshard (Elite · 5 players)',50,'#ffd58a'],
    bronzemantis:['Bronze Mantis',50,'#c8a66b'], gearling:['Gearling',51,'#9bc2be'], orbitseer:['Orbit Seer (ranged)',52,'#a3dce4'], chronoguard:['Chronoguard',53,'#b4a7ba'], pendulummatron:['Pendulum Matron (Elite · 3 players)',54,'#e1b5a9'], epochengine:['Epoch Engine (Elite · 5 players)',55,'#dab47d'],
    ram: ['Stormram', 29, '#8fe0ff'], oakhorn: ['Oakhorn (Elite · 3 players)', 25, '#ff9a3a'], hrungnir: ['Hrungnir (Elite · 5 players)', 30, '#7ab4ff'],
  };
  for (const e of CATHEDRAL_ENEMIES) KINDS[e.kind]=[e.name+(e.boss?' (Boss)':''),e.level,e.color];
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const kindInfo = kind => KINDS[kind] || [kind, 1, '#ff6b8a'];
  const travelMasters = z => (z.npcs || []).filter(n => n.travelStop);
  // Fog of war: the server saves which of a zone's 3x3 cells the character has stood in (Field.explored, one bitmask per
  // zone). Nothing from an unvisited cell is shown: not its ground, gates, camp, enemies or people.
  const CELLS = 9;
  const maskOf = i => { const e = window.Field?.explored; return e ? (e[i] || 0) : (1 << CELLS) - 1; };
  const visited = i => maskOf(i) !== 0;
  const charted = i => { let n = 0; for (let b = maskOf(i); b; b >>= 1) n += b & 1; return n; };
  const known = (i, x, y) => window.Field.fog.seen(i, x, y);
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  let zones = null, tiles = [], roadRefs = [], fogSignature = '', view = 'world', current = 0, previousFocus = null, highlight = null, timer = 0, tickTimer = 0;
  const cache = new Map();

  function load() {
    if (zones) return zones;
    const W = window.WORLD_MAP;
    zones = [{ ...W, theme: 'meadow', name: W.name || 'Greenmeadow', paths: window.Field?.meadowPaths || [] },
      ...(W.zones || []).map(z => ({ theme: 'ember', paths: [], ...z }))];
    zones.forEach((z, i) => {
      z.portals ||= [];
      const levels = z.levels || (() => { const l = z.slimes.filter(s => s.kind !== 'big').map(s => kindInfo(s.kind)[1]); return l.length ? [Math.min(...l), Math.max(...l)] : null; })();
      z.range = levels;
      z.place = LAYOUT[i] || { x: 4 + ((i - LAYOUT.length) % 4) * 24, y: 58, s: 16 };   // unplaced zones queue along the bottom edge
    });
    return zones;
  }

  // ---------- ground ----------
  function objectColour(o, theme) {
    const fen = theme === 'fen', frost = theme === 'frost', ember = theme === 'ember', wyrd = theme === 'wyrd';
    switch (o.kind) {
      case 'skypine': return '#52c0a0';
      case 'prism': return '#b9a0ff';
      case 'orrery': return '#f4c981';
      case 'column': return '#e8ecff';
      case 'skyrock': return '#aab6d8';
      case 'cloudpuff': return '#f0f4ff';
      case 'wardstone': case 'windcairn': case 'spirelight': case 'pylon': case 'hallgate': return '#ffd36a';
      case 'nest': return '#8a6a4a';
      case 'reefwall': return '#d86a78';
      case 'kelp': return '#2a8a5a';
      case 'coral': case 'anemone': return '#e0708a';
      case 'tidebell': return '#ffd36a';
      case 'clam': case 'sunkencolumn': return '#d8d4c4';
      case 'shiprib': case 'anchor': return '#8a6a4a';
      case 'deeprock': case 'vent': return '#5a6678';
      case 'pearllamp': return '#c8fff0';
      case 'lava': return '#ff6a2a';
      case 'ice': return '#4f93c8';
      case 'water': return wyrd ? '#2f6f9a' : '#244f5c';
      case 'crag': return '#4a4a58';
      case 'pine': return '#1f4a3a';
      case 'beacon': return '#ff9a2e';
      case 'gallows': case 'ribcage': return '#d8d0b8';
      case 'elderash': return '#8a5a2a';
      case 'thicket': return '#6a2f58';
      case 'tree': return wyrd ? '#a8451e' : fen ? '#1b4a2a' : frost ? '#1f5a52' : ember ? '#150f13' : '#1f6b3a';
      case 'spire': return wyrd ? '#d8d8c8' : fen ? '#b8c0b0' : frost ? '#8ccdf0' : '#4b3b5e';
      case 'rock': return wyrd ? '#7a7a80' : fen ? '#6b7a68' : frost ? '#7f93aa' : ember ? '#6a6672' : '#8a93a8';
      case 'rampart': return '#6f7078';
      case 'vaultwall': return '#5d6482';
      case 'pillar': return '#a3abc0';
      case 'brazier': return '#ff9a3a';
      case 'torch': return '#ffcf6a';
      case 'sarcophagus': return '#6a7088';
      case 'bones': return '#d6cfb6';
      case 'tower': return '#3f6a8a';
      case 'stall': return '#e0a040';
      case 'nacrehouse': case 'nacrestall': case 'house': case 'chapel': return o.color || '#a08060';
      case 'crystal': case 'obelisk': return '#a4e9e3';
      case 'astraltree': return '#244f64';
      case 'starstone': return '#637994';
      case 'starbloom': return '#d8afe9';
      case 'astralshrub': return '#5eaa91';
      case 'astrolamp': case 'starwell': return '#ffe2a0';
      case 'astralhouse': case 'observatory': return '#94bbc5';
      case 'mirrorwall': return '#e8d9ef';
      case 'sunspire': case 'lens_pillar': return '#ffe3ae';
      case 'glassstone': return '#9b8ca8';
      case 'saltbrush': return '#d8c9c3';
      case 'shade_tent': return '#a5798f';
      case 'bush': return fen ? '#3f6a3a' : frost ? '#4a8a78' : ember ? '#3a2a30' : '#2f8a45';
      default: return '#8a7a62';
    }
  }
  const FEATURE = new Set(['lava', 'ice', 'water', 'thicket']);
  const RADIUS = { crag: 1.3, pine: 1.4, elderash: 3.5, lava: 1.5, water: 1.1, ice: 1.15, thicket: 1.15, tree: 1.4, bush: .8, rock: .9, spire: 1, lamp: .5, flowers: .5 };
  function paint(index, px) {
    const key = `${index}:${px}`; if (cache.has(key)) return cache.get(key);
    const z = zones[index], k = px / z.size, c = document.createElement('canvas'); c.width = c.height = px;
    const g = c.getContext('2d');
    g.fillStyle = GROUND[z.theme]; g.fillRect(0, 0, px, px);
    let seed = 7 + index * 131; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    for (let n = 0; n < 70; n++) { g.fillStyle = rnd() < .5 ? 'rgba(255,255,255,.05)' : 'rgba(0,0,0,.07)'; g.beginPath(); g.arc(rnd() * px, rnd() * px, (4 + rnd() * 9) * k, 0, 6.283); g.fill(); }
    g.lineCap = g.lineJoin = 'round'; g.strokeStyle = g.fillStyle = DIRT[z.theme]; g.lineWidth = 2.8 * k;
    for (const p of z.paths || []) { g.beginPath(); p.forEach(([x, y], i) => i ? g.lineTo(x * k, y * k) : g.moveTo(x * k, y * k)); g.stroke(); }
    if (z.theme === 'meadow') { g.beginPath(); g.arc(36 * k, 36 * k, 3.5 * k, 0, 6.283); g.fill(); }
    (z.sky || []).forEach((row, y) => { for (let x = 0; x < z.size; x++) { const c = row[x]; if (c && c !== ' ') { g.fillStyle = c === '=' ? '#f0c8f4' : '#8ad4b8'; g.fillRect(x * k, y * k, k + .6, k + .6); } } });   // floating islands and their bridges
    for (const [x0, y0, x1, y1] of z.rooms || []) { g.fillStyle = '#2f3347'; g.fillRect(x0 * k, y0 * k, (x1 - x0) * k, (y1 - y0) * k); }   // a dungeon's floor
    const PAVE = { 1: '#b6a98c', 2: '#ece2c8', 3: '#b8765a' };
    for (const r of z.roads || []) {
      g.fillStyle = g.strokeStyle = PAVE[r.t] || '#b6a98c';
      if (r.x0 !== undefined) g.fillRect(r.x0 * k, r.y0 * k, (r.x1 - r.x0) * k, (r.y1 - r.y0) * k);
      else if (r.r0 !== undefined) { g.lineWidth = (r.r1 - r.r0) * k; g.beginPath(); g.arc(r.x * k, r.y * k, (r.r0 + r.r1) / 2 * k, 0, 6.283); g.stroke(); }
      else { g.beginPath(); g.arc(r.x * k, r.y * k, r.r * k, 0, 6.283); g.fill(); }
    }
    if (z.city && z.theme !== 'city' && z.theme !== 'nacre') for (const t of [z.city, ...(z.camps || [])]) {
      g.fillStyle = { meadow: '#d8cbb0', ember: '#88705d', frost: '#8fa6bd', fen: '#6a5238', wyrd: '#8a6a44', sky: '#cdd2f2', deep: '#4a7a82', astral: '#8fa9b2', prismwaste: '#c5a58d', orrery: '#a58a77' }[z.theme];
      g.fillRect(t.x0 * k, t.y0 * k, (t.x1 - t.x0) * k, (t.y1 - t.y0) * k);
    }
    const objects = (z.objects || []).filter(o => o.kind !== 'post' && o.kind !== 'void');
    for (const pass of [0, 1]) for (const o of objects) {
      if (FEATURE.has(o.kind) !== (pass === 0)) continue;
      g.fillStyle = objectColour(o, z.theme);
      if (o.width) { g.fillRect((o.x - o.width / 2) * k, (o.y - o.depth / 2) * k, Math.max(1, o.width * k), Math.max(1, o.depth * k)); continue; }
      if (o.kind === 'grandfountain' || o.kind === 'fountain' || o.kind === 'meetingstone') { g.fillStyle = o.kind === 'meetingstone' ? '#59d9ff' : '#58a8d8'; g.beginPath(); g.arc(o.x * k, o.y * k, Math.max(2, (o.r || 1) * k), 0, 6.283); g.fill(); continue; }
      g.beginPath(); g.arc(o.x * k, o.y * k, Math.max(1, (RADIUS[o.kind] || .8) * k), 0, 6.283); g.fill();
    }
    if (z.city && z.theme !== 'city' && z.theme !== 'nacre') for (const t of [z.city, ...(z.camps || [])]) { g.fillStyle = '#ffe9a0'; g.beginPath(); g.arc(t.plaza.x * k, t.plaza.y * k, Math.max(2, 2.4 * k), 0, 6.283); g.fill(); }
    for (const n of z.npcs || []) { g.fillStyle = '#f5d477'; g.beginPath(); g.arc(n.x * k, n.y * k, Math.max(1, .55 * k), 0, 6.283); g.fill(); }
    cache.set(key, c); return c;
  }
  function copy(canvas, source) { canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height); canvas.getContext('2d').drawImage(source, 0, 0, canvas.width, canvas.height); }

  // ---------- world view ----------
  const rangeText = z => z.range ? (z.range[0] === z.range[1] ? `Lv ${z.range[0]}` : `Lv ${z.range[0]}–${z.range[1]}`) + (z.players ? ` · ${z.players} players` : '') : 'Safe city';
  const edgePoint = (a, b) => {                                     // where the road from a's centre to b's centre leaves a's square
    const ax = a.x + a.s / 2, ay = a.y + a.s / 2, dx = b.x + b.s / 2 - ax, dy = b.y + b.s / 2 - ay, t = (a.s / 2 + .6) / Math.max(Math.abs(dx), Math.abs(dy));
    return [ax + dx * t, ay + dy * t];
  };
  function svgNode(tag, attrs) { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; }
  function buildWorld() {
    const stage = $('wm-world'); stage.replaceChildren(); tiles = []; roadRefs = [];
    const roads = svgNode('svg', { viewBox: `0 0 ${STAGE.w} ${STAGE.h}`, class: 'wm-roads', 'aria-hidden': 'true' });
    const seen = new Set();
    zones.forEach((z, i) => z.portals.forEach(p => {
      const pair = [i, p.to].sort().join('-'); if (seen.has(pair) || !zones[p.to]) return; seen.add(pair);
      const a = z.place, b = zones[p.to].place, [x1, y1] = edgePoint(a, b), [x2, y2] = edgePoint(b, a);
      const road = svgNode('g', { 'data-road': pair });
      const back = zones[p.to].portals.find(q => q.to === i);
      roadRefs.push({ node: road, shown: () => known(i, p.x, p.y) || (back && known(p.to, back.x, back.y)) });
      road.append(svgNode('title', {}), svgNode('line', { x1, y1, x2, y2, class: 'wm-road-under' }), svgNode('line', { x1, y1, x2, y2, class: 'wm-road' }),
        svgNode('circle', { cx: x1, cy: y1, r: .9, class: 'wm-gate-dot' }), svgNode('circle', { cx: x2, cy: y2, r: .9, class: 'wm-gate-dot' }));
      road.firstChild.textContent = `${p.name[0].toUpperCase()}${p.name.slice(1)} joins ${z.name} and ${zones[p.to].name}`;
      roads.append(road);
    }));
    stage.append(roads);
    zones.forEach((z, i) => {
      const { x, y, s } = z.place, tile = el('button', '', 'wm-tile'); tile.type = 'button'; tile.dataset.zone = String(i); tile.dataset.theme = z.theme;
      Object.assign(tile.style, { left: `${x / STAGE.w * 100}%`, top: `${y / STAGE.h * 100}%`, width: `${s / STAGE.w * 100}%`, height: `${s / STAGE.h * 100}%` });
      tile.setAttribute('aria-label', `${z.name}, ${z.range ? `levels ${z.range[0]} to ${z.range[1]}` : 'a safe city'}. Open its map`);
      const canvas = el('canvas'); canvas.width = canvas.height = 220; copy(canvas, paint(i, 220));
      const fog = el('canvas', '', 'wm-tile-fog'); fog.width = fog.height = 220; fog.setAttribute('aria-hidden', 'true');
      const label = el('span', '', 'wm-tile-label'); label.append(el('b', z.name), el('small', rangeText(z)));
      const you = el('i', '', 'wm-you'); you.hidden = true; you.title = 'You are here';
      tile.append(canvas, fog, label, you);
      if (travelMasters(z).length) {
        const badge = el('span', '✦', 'wm-travel-badge'); badge.setAttribute('aria-hidden', 'true');
        badge.title = travelMasters(z).map(n => n.name).join(', ');
        tile.append(badge);
      }
      tile.addEventListener('click', () => zoomTo(i, tile));
      stage.append(tile); tiles.push(tile);
    });
    stage.append(el('div', 'Valhalla', 'wm-sheet-title'));
    refreshFog();
  }
  // Repaint everything the fog touches on the world sheet. Cheap, and only runs when the saved masks change.
  function refreshFog() {
    fogSignature = JSON.stringify(window.Field.explored);
    roadRefs.forEach(r => r.node.setAttribute('visibility', r.shown() ? 'visible' : 'hidden'));
    zones.forEach((z, i) => {
      const tile = tiles[i], g = tile.querySelector('.wm-tile-fog').getContext('2d'), unseen = !visited(i);
      g.clearRect(0, 0, 220, 220); window.Field.fog.paint(g, 220, 220, i);
      tile.disabled = unseen; tile.dataset.fog = unseen ? 'full' : 'partial';
      tile.querySelector('b').textContent = unseen ? 'Unexplored' : z.name;
      tile.querySelector('small').textContent = unseen ? 'Not yet visited' : `${rangeText(z)} · ${charted(i)}/${CELLS} charted`;
      tile.setAttribute('aria-label', unseen ? 'Unexplored zone' : `${z.name}, ${z.range ? `levels ${z.range[0]} to ${z.range[1]}` : 'a safe city'}, ${charted(i)} of ${CELLS} places charted${travelMasters(z).length ? `, ${travelMasters(z).length} travel master${travelMasters(z).length === 1 ? '' : 's'}` : ''}. Open its map`);
    });
  }

  // ---------- zone view ----------
  function drawDots(z) {
    const canvas = $('wm-dots'), g = canvas.getContext('2d'), k = canvas.width / z.size;
    g.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of z.slimes || []) {
      if (!known(current, s.x, s.y)) continue;
      const [, , col] = kindInfo(s.kind), dim = highlight && highlight !== s.kind;
      g.globalAlpha = dim ? .18 : 1; g.fillStyle = col; g.strokeStyle = '#10141c'; g.lineWidth = highlight === s.kind ? 3 : 1.5;
      g.beginPath(); g.arc(s.x * k, s.y * k, (highlight === s.kind ? 1.3 : .95) * k, 0, 6.283); g.fill(); g.stroke();
    }
    g.globalAlpha = 1;
  }
  const pos = (z, x, y) => ({ left: `${x / z.size * 100}%`, top: `${y / z.size * 100}%` });
  function renderZone(index) {
    const z = zones[index]; current = index;
    copy($('wm-ground'), paint(index, 768)); highlight = null; drawDots(z);
    const fg = $('wm-fog').getContext('2d'); fg.clearRect(0, 0, 768, 768); window.Field.fog.paint(fg, 768, 768, index);
    const markers = $('wm-markers'); markers.replaceChildren();
    for (const p of z.portals) {
      const dest = zones[p.to]; if (!dest || !known(index, p.x, p.y)) continue;
      const gate = el('button', '', 'wm-gate'); gate.type = 'button'; gate.dataset.portal = p.id; gate.dataset.to = String(p.to); gate.style.setProperty('--glow', PORTAL[dest.theme]);
      Object.assign(gate.style, pos(z, p.x, p.y));
      gate.classList.toggle('low', p.y / z.size > .85); gate.classList.toggle('right', p.x / z.size > .72); gate.classList.toggle('high', p.y / z.size < .08);
      const near = z.portals.find(o => o !== p && known(index, o.x, o.y) && Math.hypot(o.x - p.x, o.y - p.y) < z.size * .14);   // close gates put their labels on opposite sides
      if (near) gate.classList.add(p.x < near.x ? 'west' : 'east');
      const away = visited(p.to);
      gate.append(el('span', away ? `to ${dest.name}` : 'to unexplored lands', 'wm-gate-label'));
      gate.setAttribute('aria-label', away ? `${p.name}, leads to ${dest.name}. Open its map` : `${p.name}, leads to unexplored lands`);
      if (!away) { gate.disabled = true; gate.dataset.unexplored = 'true'; }
      gate.addEventListener('click', () => { highlight = null; renderZone(p.to); setView('zone'); });
      markers.append(gate);
    }
    for (const c of [z.city, ...(z.camps || [])].filter(Boolean)) if (known(index, c.plaza.x, c.plaza.y)) {
      const hub = el('span', c.name === z.name ? 'City centre' : c.name, 'wm-hub'); hub.dataset.hub = 'true';
      Object.assign(hub.style, pos(z, c.plaza.x, c.plaza.y)); markers.append(hub);
    }
    for (const n of travelMasters(z)) {
      const marker = el('span', '', 'wm-travel'); marker.dataset.npc = n.id;
      marker.setAttribute('role', 'img'); marker.setAttribute('aria-label', `${n.name}, travel master at ${n.travelStop}`);
      marker.append(el('i', '✦'), el('b', 'Travel Master'));
      Object.assign(marker.style, pos(z, n.x, n.y)); markers.append(marker);
    }
    const me = el('span', '', 'wm-me'); me.append(el('i'), el('b', 'You')); me.hidden = true; me.dataset.me = 'true'; markers.append(me);
    markers.append(el('div', '', 'wm-party'));
    side(z); tick();
  }
  function side(z) {
    const box = $('wm-side'); box.replaceChildren();
    box.append(el('h4', z.name, 'wm-side-name'), el('p', z.tagline || BLURB[z.theme] || '', 'wm-side-blurb'));
    const facts = el('ul', '', 'wm-facts');
    facts.append(el('li', z.range ? (z.players ? `Dungeon for ${z.players} players of level ${z.range[0]}` : `Recommended levels ${z.range[0]}–${z.range[1]}`) : 'No enemies inside the walls'));
    facts.append(el('li', `Charted ${charted(current)} of ${CELLS} places`, 'wm-charted'));
    for (const c of [z.city, ...(z.camps || [])].filter(Boolean)) if (known(current, c.plaza.x, c.plaza.y)) facts.append(el('li', `${c.name}: sanctuary${z.camps?.length ? '' : `, ${(z.quests || []).length} quest${(z.quests || []).length === 1 ? '' : 's'}`}`));
    if (z.camps?.length) facts.append(el('li', `${(z.quests || []).length} quests across ${1 + z.camps.length} hubs`));
    box.append(facts);
    if (travelMasters(z).length) {
      box.append(el('h5', 'Travel Masters ✦', 'wm-side-title'));
      const list = el('ul', '', 'wm-travel-list');
      for (const n of travelMasters(z)) list.append(el('li', `${n.name} · ${n.travelStop}`));
      box.append(list);
    }
    const counts = new Map(); for (const s of (z.slimes || []).filter(s => known(current, s.x, s.y))) counts.set(s.kind, (counts.get(s.kind) || 0) + 1);
    if (counts.size) {
      box.append(el('h5', 'Enemies', 'wm-side-title'));
      const list = el('ul', '', 'wm-kinds');
      [...counts].sort((a, b) => kindInfo(a[0])[1] - kindInfo(b[0])[1]).forEach(([kind, n]) => {
        const [name, baseLevel, col] = kindInfo(kind), level = z.cathedralWing ? z.min_level : baseLevel, row = el('li'), b = el('button', '', 'wm-kind'); b.type = 'button'; b.dataset.kind = kind;
        const dot = el('i'); dot.style.background = col;
        b.append(dot, el('span', name), el('small', kind === 'big' ? 'king, rare' : `Lv ${level} · ${n}`));
        const on = () => { highlight = kind; drawDots(z); }, off = () => { highlight = null; drawDots(z); };
        b.addEventListener('pointerenter', on); b.addEventListener('pointerleave', off); b.addEventListener('focus', on); b.addEventListener('blur', off);
        row.append(b); list.append(row);
      });
      box.append(list);
    }
    const seenGates = z.portals.filter(p => zones[p.to] && known(current, p.x, p.y));
    if (seenGates.length) {
      box.append(el('h5', 'Gates', 'wm-side-title'));
      const list = el('ul', '', 'wm-gates');
      seenGates.forEach(p => {
        const row = el('li'), b = el('button', `${p.name[0].toUpperCase()}${p.name.slice(1)} → ${visited(p.to) ? zones[p.to].name : 'unexplored lands'}`, 'window-tool'); b.type = 'button'; b.dataset.to = String(p.to); b.disabled = !visited(p.to);
        b.addEventListener('click', () => { renderZone(p.to); setView('zone'); }); row.append(b); list.append(row);
      });
      box.append(list);
    }
  }

  // ---------- live markers ----------
  function tick() {
    if (!open()) return;
    if (window.Field?.hero?.dead || !window.Online?.connected) { close(); return; }
    if (JSON.stringify(window.Field.explored) !== fogSignature) { refreshFog(); if (view === 'zone') renderZone(current); }
    const hero = window.Field.hero, here = window.Field.zone || 0;
    zones.forEach((z, i) => {
      const you = tiles[i]?.querySelector('.wm-you'); if (!you) return;
      you.hidden = i !== here; if (i === here) Object.assign(you.style, pos(z, hero.x, hero.y));
    });
    if (view !== 'zone') return;
    const z = zones[current], me = $('wm-markers').querySelector('.wm-me');
    me.hidden = here !== current; if (!me.hidden) Object.assign(me.style, pos(z, hero.x, hero.y));
    const party = $('wm-markers').querySelector('.wm-party');
    const mates = here === current ? (window.Field.remotePlayers || []).filter(r => window.Social?.isPartyMember(r.id) && known(here, r.x, r.y)) : [];
    party.replaceChildren(...mates.map(r => { const m = el('i', '', 'wm-mate'); m.title = r.name || 'Party member'; Object.assign(m.style, pos(z, r.x, r.y)); return m; }));
    $('wm-here').textContent = here === current ? 'You are here' : `You are in ${zones[here].name}`;
  }

  // ---------- views and the zoom ----------
  function setView(next) {
    view = next; $('wm-body').dataset.view = next; $('wm-zone').hidden = next !== 'zone'; $('wm-world').hidden = next !== 'world';
    $('wm-back').hidden = next === 'world';
    $('wm-title-zone').textContent = next === 'zone' ? ` › ${zones[current].name}` : '';
    if (next === 'zone') { const zv = $('wm-zone'); zv.classList.remove('wm-fade'); void zv.offsetWidth; zv.classList.add('wm-fade'); }
    tick();
  }
  function zoomTo(index, tile) {
    if (!visited(index)) return;
    clearTimeout(timer); renderZone(index);
    const world = $('wm-world');
    if (reduced() || !tile) { world.style.transition = world.style.transform = world.style.opacity = ''; setView('zone'); return; }
    const st = world.getBoundingClientRect(), r = tile.getBoundingClientRect();
    const scale = Math.min(st.width / r.width, st.height / r.height) * .92;
    world.style.transformOrigin = `${r.left + r.width / 2 - st.left}px ${r.top + r.height / 2 - st.top}px`;
    world.style.transition = 'transform .38s ease-in, opacity .38s ease-in';
    world.style.transform = `translate(${st.left + st.width / 2 - r.left - r.width / 2}px, ${st.top + st.height / 2 - r.top - r.height / 2}px) scale(${scale})`;
    world.style.opacity = '0';
    $('wm-body').dataset.view = 'zooming';
    timer = setTimeout(() => { world.style.transition = world.style.transform = world.style.opacity = ''; setView('zone'); $('wm-back').focus(); }, 390);
  }
  function toWorld() {
    clearTimeout(timer);
    const world = $('wm-world'), tile = tiles[current];
    setView('world');
    if (!reduced() && tile) {
      const st = world.getBoundingClientRect(), r = tile.getBoundingClientRect();
      world.style.transformOrigin = `${r.left + r.width / 2 - st.left}px ${r.top + r.height / 2 - st.top}px`;
      world.style.transition = 'none'; world.style.opacity = '0';
      world.style.transform = `translate(${st.left + st.width / 2 - r.left - r.width / 2}px, ${st.top + st.height / 2 - r.top - r.height / 2}px) scale(${Math.min(st.width / r.width, st.height / r.height) * .92})`;
      void world.offsetWidth;
      world.style.transition = 'transform .32s ease-out, opacity .32s ease-out'; world.style.transform = 'none'; world.style.opacity = '1';
      timer = setTimeout(() => { world.style.transition = world.style.transform = world.style.opacity = ''; }, 340);
    }
    tile?.focus({ preventScroll: true });
  }
  const open = () => !$('worldmap').hidden;
  function canShow() {
    return !$('scene-game').hidden && window.Online?.connected && !window.Field?.hero?.dead && !open() && $('pause').hidden && $('equipment').hidden
      && $('npc-dialogue').hidden && !window.Skillbar?.open && !window.Quests?.open && !window.Social?.open && !window.City?.open && !window.Settings?.active;
  }
  function show() {
    if (!canShow()) return false;
    load(); if (!tiles.length) buildWorld(); else if (JSON.stringify(window.Field.explored) !== fogSignature) refreshFog();
    previousFocus = document.activeElement;
    window.Field.setPaused(true); $('worldmap').hidden = false; setView('world');
    const here = window.Field.zone || 0; (tiles[here] || tiles[0]).focus({ preventScroll: true });
    clearInterval(tickTimer); tickTimer = setInterval(tick, 250);
    return true;
  }
  function close(resume = true) {
    if (!open()) return;
    clearTimeout(timer); clearInterval(tickTimer);
    const world = $('wm-world'); world.style.transition = world.style.transform = world.style.opacity = '';
    $('worldmap').hidden = true; setView('world');
    if (resume) { window.Field?.setPaused(false); previousFocus?.focus?.({ preventScroll: true }); }
  }
  const back = () => view === 'zone' ? toWorld() : close();

  $('wm-close').addEventListener('click', () => close());
  $('wm-back').addEventListener('click', () => toWorld());
  $('wm-open').addEventListener('click', () => show());
  $('minimap').addEventListener('click', () => show());
  $('worldmap').addEventListener('pointerdown', event => { if (event.target === $('worldmap')) close(); });
  // Registered before game.js, so an open map keeps every key and M never reaches the other panels.
  addEventListener('keydown', event => {
    if ($('scene-game').hidden || event.ctrlKey || event.altKey || event.metaKey) return;
    const key = event.key.toLowerCase(), typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName || '');
    if (open()) {
      if (key === 'tab') {                                          // keep focus inside the panel
        const buttons = [...$('worldmap').querySelectorAll('button:not(:disabled)')].filter(b => b.offsetParent);
        const first = buttons[0], last = buttons.at(-1); event.stopImmediatePropagation();
        if (event.shiftKey && (document.activeElement === first || !buttons.includes(document.activeElement))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !buttons.includes(document.activeElement))) { event.preventDefault(); first.focus(); }
        return;
      }
      event.stopImmediatePropagation();
      if (key === 'enter' || key === ' ') return;                   // let the focused button act
      event.preventDefault();
      if (event.repeat) return;
      if (key === 'escape' || key === 'backspace') back();
      else if (key === 'm') close();
      return;
    }
    if (key !== 'm' || event.repeat || typing) return;            // N is the sound toggle in the field
    if (show()) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);

  window.WorldMap = {
    show, close, get open() { return open(); }, get view() { return view; }, get zone() { return current; },
    reset() { close(false); },
    // For the tests: the layout and kind table the map was written against.
    _layout: LAYOUT, _kinds: KINDS,
  };
})();
