'use strict';
/* The first map: "Greenmeadow Field". A big open isometric meadow (2:1 diamond tiles) with trees,
   bushes, rocks and slimes. Ground is pre-rendered in chunks; trees, bushes and rocks are sprites
   drawn once; heroes and slimes use animated atlases. Warrior, Mage and Assassin equipment is composited
   from independent body, armor and weapon layers; procedural art remains as a loading fallback.
   Coordinates: world units are tiles (x right-down, y left-down). Screen: sx = (x-y)*TW/2, sy = (x+y)*TH/2.
   API: Field.start({canvas, mini, char, opts, onHud, onEvent}); Field.stop(); Field.setPaused(bool); Field.equip(change). */
(() => {
  const TW = 88, TH = 44, CH = 8;                    // tile size (px), chunk size (tiles)
  let MAP = WORLD_MAP.size;                           // map size (tiles) of the zone the hero is in
  const VW = 1600, VH = 900;                          // virtual viewport in px; the canvas is scaled to fit
  const SPR = 2;                                      // sprite cache resolution
  const OL = '#1c1428';
  // Zone 0 is Greenmeadow with Alderhaven; the server numbers the rest like WORLD_MAP.zones. Each has its own
  // size, obstacles, theme (terrain, sky, sprites) and gates. The server decides which zone the hero is in.
  const ZONES = [{ name: 'Greenmeadow', theme: 'meadow', size: WORLD_MAP.size, spawn: WORLD_MAP.spawn, objects: WORLD_MAP.objects, city: WORLD_MAP.city, npcs: WORLD_MAP.npcs, portals: WORLD_MAP.portals || [], paths: WORLD_MAP.paths || null, levels: null },
    ...(WORLD_MAP.zones || []).map(z => ({ theme: 'ember', paths: null, levels: null, portals: [], ...z }))];
  let zone = 0, zdef = ZONES[0], SPAWN = WORLD_MAP.spawn;

  // ---------- small helpers ----------
  const rngf = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const hash2 = (x, y, s) => { let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 2147483647)) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
  const vnoise = (x, y, s) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  };
  const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
  const lerp = (a, b, t) => a + (b - a) * t;
  const segDist = (px, py, ax, ay, bx, by) => { const dx = bx - ax, dy = by - ay, t = clamp(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy || 1), 0, 1); return Math.hypot(px - ax - dx * t, py - ay - dy * t); };
  const w2sRaw = (x, y) => [(x - y) * TW / 2, (x + y) * TH / 2];
  const canvasOf = (w, h, scale) => { const c = document.createElement('canvas'); c.width = Math.ceil(w * scale); c.height = Math.ceil(h * scale); const g = c.getContext('2d'); g.scale(scale, scale); return [c, g]; };
  const shade = (hex, k) => { const n = parseInt(hex.slice(1), 16), t = k < 0 ? 0 : 255, p = Math.abs(k); return '#' + [n >> 16, (n >> 8) & 255, n & 255].map(v => Math.round(v + (t - v) * p).toString(16).padStart(2, '0')).join(''); };

  // ---------- the map ----------
  const yearSeason=(x,y)=>x<200?(y<200?3:0):(y<200?2:1);
  function yearGround(x,y,tone,dirt,alt) {
    const s=yearSeason(x,y);
    const grass=[[116,47,42],[89,57,45],[35,54,46],[196,48,85]][s];
    const road=[[42,41,69],[38,57,72],[28,46,60],[191,37,77]][s];
    const [h,sat,light]=dirt?road:grass;
    return `hsl(${h+tone*11},${sat+tone*7}%,${light+tone*10+alt}%)`;
  }
  const PATHS = [
    [[36, 79], [36, 71], [36, 62], [33, 52], [38, 44], [36, 36], [42, 28], [50, 22], [54, 12]],
    [[36, 36], [26, 32], [16, 26], [10, 16]],
  ];
  const map = { dirt: new Uint8Array(0), tone: new Float32Array(0) };
  let objects = [], nightLights = [];
  function buildMap() {
    MAP = zdef.size; SPAWN = zdef.spawn;
    map.dirt = new Uint8Array(MAP * MAP); map.tone = new Float32Array(MAP * MAP);
    const paths = zdef.paths || PATHS, ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city' || zdef.theme === 'asterion', vault = zdef.theme === 'skybridge' || zdef.theme === 'nornroot' || zdef.theme === 'vault' || zdef.theme === 'eye_below' || zdef.theme === 'elder_hollow' || zdef.theme === 'thousandfold' || zdef.theme === 'rain_crown' || zdef.theme === 'seed_vault' || zdef.theme === 'sunken_astrolabe' || zdef.theme === 'thunderheart_gate' || SeasonDungeonArt.isTheme(zdef.theme) || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', prism = zdef.theme === 'prismwaste', orrery = zdef.theme === 'orrery', moonspore = zdef.theme === 'moonspore', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) {
      const i = y * MAP + x, cx = x + .5, cy = y + .5;
      map.tone[i] = vnoise(cx * .16, cy * .16, ember ? 11 : frost ? 21 : fen ? 31 : city ? 41 : vault ? 51 : wyrd ? 61 : sky ? 71 : astral ? 91 : prism ? 101 : orrery ? 111 : moonspore ? 121 : zdef.theme === 'stormglass' ? 131 : zdef.theme === 'sunward' ? 141 : zdef.theme === 'ribbonwild' ? 151 : zdef.theme === 'tanglecrown' ? 161 : zdef.theme === 'worldtree' ? 171 : zdef.theme === 'heartwood' ? 181 : zdef.theme === 'lapiserg' ? 191 : zdef.theme === 'frostwake' ? 201 : zdef.theme === 'cairnspine' ? 211 : zdef.theme === 'yearwheel' ? 221 : deep ? 81 : 1) * .65 + vnoise(cx * .55, cy * .55, ember ? 12 : frost ? 22 : fen ? 32 : city ? 42 : vault ? 52 : wyrd ? 62 : sky ? 72 : astral ? 92 : prism ? 102 : orrery ? 112 : moonspore ? 122 : zdef.theme === 'stormglass' ? 132 : zdef.theme === 'sunward' ? 142 : zdef.theme === 'ribbonwild' ? 152 : zdef.theme === 'tanglecrown' ? 162 : zdef.theme === 'worldtree' ? 172 : zdef.theme === 'heartwood' ? 182 : zdef.theme === 'lapiserg' ? 192 : zdef.theme === 'frostwake' ? 202 : zdef.theme === 'cairnspine' ? 212 : zdef.theme === 'yearwheel' ? 222 : deep ? 82 : 2) * .35;
      let d = 99; for (const p of paths) for (let k = 0; k < p.length - 1; k++) d = Math.min(d, segDist(cx, cy, p[k][0], p[k][1], p[k + 1][0], p[k + 1][1]));
      if (!ember && !frost && !fen && !city && !vault && !wyrd && !sky && !astral && !prism && !orrery && !moonspore && zdef.theme !== 'stormglass' && zdef.theme !== 'sunward' && zdef.theme !== 'ribbonwild' && zdef.theme !== 'tanglecrown' && zdef.theme !== 'worldtree' && zdef.theme !== 'heartwood' && zdef.theme !== 'lapiserg' && zdef.theme !== 'frostwake' && zdef.theme !== 'cairnspine' && zdef.theme !== 'yearwheel' && !deep) d = Math.min(d, Math.hypot(cx - 36, cy - 36) - 2.4);
      map.dirt[i] = d < 1.15 + vnoise(cx * .5, cy * .5, 3) * .6 ? 1 : 0;
    }
    if (city || zdef.theme === 'nacre') paintRoads(zdef.roads);
    if (vault) paintRooms(zdef.rooms);
    map.floor = null;
    if (sky) paintSky(zdef.sky);
    if (zdef.theme === 'moonwell') paintMoonwell(zdef.moonwellFloor);
    objects = zdef.objects.map(o => ({ ...o }));
    nightLights = objects.filter(o => ['lamp', 'brazier', 'torch', 'campfire', 'lantern', 'house', 'inn', 'shop'].some(k => o.kind.includes(k)));
  }
  // Skaldholm's ground: the zone lists its streets (type 1 cobbles), plazas and squares (2 marble, 3 brick) as rectangles, discs and rings.
  function paintRoads(roads) {
    map.dirt.fill(0);
    for (const r of roads || []) {
      const rect = r.x0 !== undefined, rad = r.r1 ?? r.r, bx0 = rect ? r.x0 : r.x - rad, bx1 = rect ? r.x1 : r.x + rad, by0 = rect ? r.y0 : r.y - rad, by1 = rect ? r.y1 : r.y + rad;
      for (let y = Math.max(0, Math.floor(by0)); y <= Math.min(MAP - 1, Math.floor(by1)); y++) for (let x = Math.max(0, Math.floor(bx0)); x <= Math.min(MAP - 1, Math.floor(bx1)); x++) {
        const cx = x + .5, cy = y + .5; let inside;
        if (rect) inside = cx >= r.x0 && cx <= r.x1 && cy >= r.y0 && cy <= r.y1;
        else { const d = Math.hypot(cx - r.x, cy - r.y); inside = r.r0 !== undefined ? d >= r.r0 && d <= r.r1 : d <= r.r; }
        if (inside) map.dirt[y * MAP + x] = r.t;
      }
    }
  }
  // The Undervault's floor: the zone lists its rooms and corridors as rectangles; everything else is solid rock, left black.
  function paintRooms(rooms) {
    map.dirt.fill(0);
    for (const [x0, y0, x1, y1] of rooms || []) for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) map.dirt[y * MAP + x] = 1;
  }
  // Bifrost Reach: the zone lists its 160 rows as text (' ' void, '#' island, '=' bridge). Only floor is drawn; void shows the sky and the storm below.
  function paintSky(rows) {
    map.floor = new Uint8Array(MAP * MAP); map.dirt.fill(0);
    (rows || []).forEach((row, y) => { for (let x = 0; x < MAP; x++) { const c = row[x]; if (c && c !== ' ') { map.floor[y * MAP + x] = 1; if (c === '=') map.dirt[y * MAP + x] = 1; } } });
  }
  function paintMoonwell(rows) {
    map.floor = new Uint8Array(MAP * MAP); map.dirt.fill(0);
    (rows || []).forEach((row,y)=>{for(let x=0;x<MAP;x++)if(row[x]&&row[x]!==' '){
      map.floor[y*MAP+x]=1;map.dirt[y*MAP+x]=row[x]==='='?1:0;
    }});
  }
  const isVoid = (x, y) => !!map.floor && (x < 0 || y < 0 || x >= MAP || y >= MAP || !map.floor[y * MAP + x]);
  // Switch to another zone: new ground, obstacles and minimap. Everything tied to the old zone's coordinates goes.
  function setZone(z) {
    zone = ZONES[z] ? z : 0; zdef = ZONES[zone];
    window.DayNight?.setZone(zdef);
    window.Weather?.setZone(zdef);
    buildMap(); chunks.clear();
    if (mini) buildMini();
    if (hero) { pendingNpc = null; pendingChest = null; cityRoute = []; hero.target = null; hero.pvpTargetId = null; hero.goal = null; }
    floaters = []; parts = []; effects = []; bolts = []; ebolts = []; drops = []; chests = []; signs = []; marker = null; slimes = []; remotePlayers.clear(); bubbles.clear();
    instanceCleared = false; clearedAt = -99;
  }

  // ---------- sprites (drawn once) ----------
  const sprites = { tree: [], bush: [], rock: [] };
  function outlineUnion(g, circles, col, grow) { g.fillStyle = col; for (const c of circles) { g.beginPath(); g.arc(c.x, c.y, c.r + grow, 0, 6.283); g.fill(); } }
  function makeTree(v) {
    const [c, g] = canvasOf(210, 270, SPR), ax = 105, ay = 258, rng = rngf(100 + v * 17);
    const pal = [['#8bea8f', '#3fae55', '#1f6b3a'], ['#9be27a', '#4aa83a', '#256b2a'], ['#ffd06a', '#e58a2a', '#9a4a18'], ['#a5f0b8', '#38b48a', '#1b6b57']][v % 4];
    // trunk
    const tg = g.createLinearGradient(ax - 16, 0, ax + 16, 0); tg.addColorStop(0, '#6a4326'); tg.addColorStop(.55, '#9a6a3c'); tg.addColorStop(1, '#5a381e');
    g.fillStyle = tg; g.strokeStyle = OL; g.lineWidth = 4; g.lineJoin = 'round';
    g.beginPath(); g.moveTo(ax - 22, ay); g.quadraticCurveTo(ax - 10, ay - 22, ax - 11, ay - 60); g.lineTo(ax - 12, ay - 118); g.lineTo(ax + 12, ay - 118); g.quadraticCurveTo(ax + 10, ay - 60, ax + 12, ay - 24); g.quadraticCurveTo(ax + 16, ay - 8, ax + 24, ay); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = 'rgba(40,20,8,.45)'; g.lineWidth = 2.5; for (let i = 0; i < 4; i++) { const yy = ay - 30 - i * 22; g.beginPath(); g.moveTo(ax - 6 + rng() * 4, yy); g.lineTo(ax - 4 + rng() * 6, yy - 14); g.stroke(); }
    // canopy: overlapping blobs, one shared outline
    const cx = ax, cy = 112, blobs = [{ x: cx - 44, y: cy + 14, r: 40 }, { x: cx + 46, y: cy + 16, r: 40 }, { x: cx, y: cy - 24, r: 52 }, { x: cx - 26, y: cy - 2, r: 46 }, { x: cx + 28, y: cy - 4, r: 46 }, { x: cx, y: cy + 26, r: 38 }];
    outlineUnion(g, blobs, OL, 4);
    for (const b of blobs) { const gr = g.createRadialGradient(b.x - b.r * .3, b.y - b.r * .4, b.r * .1, b.x, b.y, b.r); gr.addColorStop(0, pal[0]); gr.addColorStop(.6, pal[1]); gr.addColorStop(1, pal[2]); g.fillStyle = gr; g.beginPath(); g.arc(b.x, b.y, b.r, 0, 6.283); g.fill(); }
    g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 4; g.lineCap = 'round';
    for (const b of blobs) { g.beginPath(); g.arc(b.x, b.y, b.r * .72, Math.PI * 1.1, Math.PI * 1.45); g.stroke(); }
    g.fillStyle = 'rgba(20,60,30,.35)'; for (let i = 0; i < 16; i++) { const a = rng() * 6.283, d = 20 + rng() * 45; g.beginPath(); g.ellipse(cx + Math.cos(a) * d, cy + 14 + Math.sin(a) * d * .6, 7, 4, .4, 0, 6.283); g.fill(); }
    if (v % 4 !== 2 && v % 4 !== 3) { g.fillStyle = '#ff5a5a'; g.strokeStyle = OL; g.lineWidth = 2; for (let i = 0; i < 5; i++) { const a = rng() * 6.283, d = 18 + rng() * 40; g.beginPath(); g.arc(cx + Math.cos(a) * d, cy + 10 + Math.sin(a) * d * .7, 5, 0, 6.283); g.fill(); g.stroke(); } }
    return { c, ax, ay, w: 210, h: 270 };
  }
  function makeBush(v) {
    const [c, g] = canvasOf(120, 100, SPR), ax = 60, ay = 84, rng = rngf(300 + v * 11);
    const pal = [['#7fe08a', '#3aa650', '#1f6b3a'], ['#95dc6a', '#56aa3a', '#2b6b26'], ['#7fe0c0', '#38a888', '#1c6650'], ['#b0e06a', '#7ab030', '#46701c']][v % 4];
    const blobs = [{ x: ax - 26, y: ay - 16, r: 22 }, { x: ax + 26, y: ay - 16, r: 22 }, { x: ax, y: ay - 28, r: 27 }, { x: ax - 10, y: ay - 8, r: 22 }, { x: ax + 12, y: ay - 8, r: 22 }];
    outlineUnion(g, blobs, OL, 3.5);
    for (const b of blobs) { const gr = g.createRadialGradient(b.x - b.r * .3, b.y - b.r * .4, b.r * .1, b.x, b.y, b.r); gr.addColorStop(0, pal[0]); gr.addColorStop(.65, pal[1]); gr.addColorStop(1, pal[2]); g.fillStyle = gr; g.beginPath(); g.arc(b.x, b.y, b.r, 0, 6.283); g.fill(); }
    g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 3; g.lineCap = 'round'; for (const b of blobs) { g.beginPath(); g.arc(b.x, b.y, b.r * .7, Math.PI * 1.1, Math.PI * 1.45); g.stroke(); }
    const berry = ['#ff4d6d', '#ffd23f', '#ff9ad5', '#ffffff'][v % 4]; g.fillStyle = berry; g.strokeStyle = OL; g.lineWidth = 1.8;
    for (let i = 0; i < 6; i++) { const a = rng() * 6.283, d = 6 + rng() * 26; g.beginPath(); g.arc(ax + Math.cos(a) * d, ay - 18 + Math.sin(a) * d * .5, 3.6, 0, 6.283); g.fill(); g.stroke(); }
    return { c, ax, ay, w: 120, h: 100 };
  }
  function makeRock(v) {
    const [c, g] = canvasOf(90, 70, SPR), ax = 45, ay = 58, rng = rngf(500 + v * 13), s = 1 + v * .12;
    const pts = [[-30, 0], [-34, -14], [-18, -34], [6, -40], [28, -26], [34, -8], [26, 0]].map(([x, y]) => [ax + x * s * (.9 + rng() * .2), ay + y * s * (.9 + rng() * .2)]);
    g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; g.fillStyle = '#9aa3b8';
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#c7cede'; g.beginPath(); g.moveTo(pts[1][0] + 3, pts[1][1] + 2); g.lineTo(pts[2][0], pts[2][1] + 2); g.lineTo(pts[3][0], pts[3][1] + 2); g.lineTo(ax, ay - 20); g.closePath(); g.fill();
    g.fillStyle = '#727b92'; g.beginPath(); g.moveTo(pts[4][0], pts[4][1]); g.lineTo(pts[5][0], pts[5][1]); g.lineTo(pts[6][0], pts[6][1]); g.lineTo(ax + 6, ay - 4); g.closePath(); g.fill();
    g.fillStyle = '#6fc07a'; g.beginPath(); g.ellipse(ax - 12, ay - 3, 10, 4, 0, 0, 6.283); g.fill();     // moss
    return { c, ax, ay, w: 90, h: 70 };
  }
  // Emberfall Crags scenery, drawn once like the meadow's: charred trees, thorn bushes, basalt and obsidian.
  const emberSprites = { tree: [], bush: [], rock: [], spire: [] };
  function makeCharTree(v) {
    const [c, g] = canvasOf(210, 270, SPR), ax = 105, ay = 258, rng = rngf(900 + v * 19);
    g.lineCap = 'round'; g.lineJoin = 'round';
    const limb = (x0, y0, x1, y1, w0, w1) => {
      const n = 12;
      for (const [col, grow] of [[OL, 5], ['#2a1f24', 0]]) {
        for (let i = 0; i < n; i++) {
          const t0 = i / n, t1 = (i + 1) / n, w = lerp(w0, w1, t0) + grow;
          g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(lerp(x0, x1, t0), lerp(y0, y1, t0)); g.lineTo(lerp(x0, x1, t1), lerp(y0, y1, t1)); g.stroke();
        }
      }
      g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = Math.max(1.5, w1 * .35); g.beginPath(); g.moveTo(x0 - w0 * .25, y0); g.lineTo(x1 - w1 * .25, y1); g.stroke();
    };
    const lean = (v % 2 ? 1 : -1) * (6 + v * 3);
    limb(ax - 4, ay, ax + lean * .4, ay - 90, 26, 16);
    limb(ax + lean * .4, ay - 90, ax + lean, ay - 160, 16, 9);
    const forks = [[-1, 70, 52], [1, 100, 62], [-1, 128, 46], [1, 150, 40]];
    forks.forEach(([side, h, len], i) => {
      const bx = ax + lean * (h / 160) * .9, by = ay - h, ex = bx + side * (len + rng() * 14), ey = by - 30 - rng() * 28;
      limb(bx, by, ex, ey, 9, 3.5);
      if (i % 2 === 0) limb(ex, ey, ex + side * (14 + rng() * 10), ey - 22, 3.5, 1.8);
    });
    limb(ax + lean, ay - 160, ax + lean + 10 + rng() * 8, ay - 200, 9, 3);
    // glowing scorch marks and drifting embers
    g.shadowColor = '#ff7a22'; g.shadowBlur = 8;
    g.strokeStyle = '#ff8a2e'; g.lineWidth = 2.2;
    for (let i = 0; i < 4; i++) { const y = ay - 20 - i * 24 - rng() * 8; g.beginPath(); g.moveTo(ax - 7 + lean * (ay - y) / 400, y); g.lineTo(ax - 2 + lean * (ay - y) / 400, y - 7); g.lineTo(ax + 4 + lean * (ay - y) / 400, y - 3); g.stroke(); }
    g.shadowBlur = 0; g.fillStyle = '#ffb347';
    for (let i = 0; i < 6; i++) { g.beginPath(); g.arc(ax + (rng() - .5) * 90, ay - 80 - rng() * 140, 1.6 + rng() * 1.2, 0, 6.283); g.fill(); }
    g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(ax, ay - 2, 30, 8, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 210, h: 270 };
  }
  function makeEmberBush(v) {
    const [c, g] = canvasOf(120, 100, SPR), ax = 60, ay = 84, rng = rngf(1300 + v * 7);
    g.lineCap = 'round';
    for (let i = 0; i < 9; i++) {
      const a = -Math.PI / 2 + (i - 4) * .3 + (rng() - .5) * .2, len = 30 + rng() * 22, ex = ax + Math.cos(a) * len, ey = ay - 6 + Math.sin(a) * len * .8;
      g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(ax + (i - 4) * 3, ay); g.quadraticCurveTo(ax + Math.cos(a) * len * .4, ay - len * .5, ex, ey); g.stroke();
      g.strokeStyle = i % 2 ? '#3a2a30' : '#52383a'; g.lineWidth = 3; g.beginPath(); g.moveTo(ax + (i - 4) * 3, ay); g.quadraticCurveTo(ax + Math.cos(a) * len * .4, ay - len * .5, ex, ey); g.stroke();
    }
    g.shadowColor = '#ff7a22'; g.shadowBlur = 8; g.fillStyle = '#ff9a3a'; g.strokeStyle = OL; g.lineWidth = 1.6;
    for (let i = 0; i < 6; i++) { const a = rng() * 6.283, d = 8 + rng() * 28; g.beginPath(); g.arc(ax + Math.cos(a) * d, ay - 22 + Math.sin(a) * d * .5, 3.4, 0, 6.283); g.fill(); g.stroke(); }
    g.shadowBlur = 0;
    return { c, ax, ay, w: 120, h: 100 };
  }
  function makeBasalt(v) {
    const [c, g] = canvasOf(90, 70, SPR), ax = 45, ay = 58, rng = rngf(1700 + v * 13), s = 1 + v * .12;
    const pts = [[-30, 0], [-34, -14], [-18, -34], [6, -40], [28, -26], [34, -8], [26, 0]].map(([x, y]) => [ax + x * s * (.9 + rng() * .2), ay + y * s * (.9 + rng() * .2)]);
    g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; g.fillStyle = '#4a4650';
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#6a6672'; g.beginPath(); g.moveTo(pts[1][0] + 3, pts[1][1] + 2); g.lineTo(pts[2][0], pts[2][1] + 2); g.lineTo(pts[3][0], pts[3][1] + 2); g.lineTo(ax, ay - 20); g.closePath(); g.fill();
    g.fillStyle = '#2f2c35'; g.beginPath(); g.moveTo(pts[4][0], pts[4][1]); g.lineTo(pts[5][0], pts[5][1]); g.lineTo(pts[6][0], pts[6][1]); g.lineTo(ax + 6, ay - 4); g.closePath(); g.fill();
    g.shadowColor = '#ff7a22'; g.shadowBlur = 6; g.strokeStyle = '#ff8a2e'; g.lineWidth = 2; g.beginPath(); g.moveTo(ax - 14, ay - 28); g.lineTo(ax - 6, ay - 16); g.lineTo(ax - 10, ay - 6); g.moveTo(ax + 10, ay - 22); g.lineTo(ax + 16, ay - 10); g.stroke(); g.shadowBlur = 0;
    return { c, ax, ay, w: 90, h: 70 };
  }
  function makeSpire(v) {
    const [c, g] = canvasOf(110, 190, SPR), ax = 55, ay = 176, rng = rngf(2100 + v * 17);
    g.lineJoin = 'round';
    const shard = (x, w, h, lean, shade) => {
      const top = [x + lean, ay - h];
      for (const [dir, col] of [[-1, shade[0]], [1, shade[1]]]) {
        g.fillStyle = col; g.strokeStyle = OL; g.lineWidth = 3.4; g.beginPath(); g.moveTo(x + dir * w, ay); g.lineTo(x + dir * w * .8, ay - h * .55); g.lineTo(top[0], top[1]); g.lineTo(x, ay - h * .5); g.lineTo(x, ay); g.closePath(); g.fill(); g.stroke();
      }
      g.strokeStyle = 'rgba(255,255,255,.35)'; g.lineWidth = 2; g.beginPath(); g.moveTo(x - w * .55, ay - 6); g.lineTo(top[0] - 1, top[1] + 8); g.stroke();
    };
    const dark = ['#2a2036', '#18101f'], mid = ['#3b2d4b', '#241a31'];
    shard(ax - 22, 15, 80 + v * 6, -6, mid); shard(ax + 22, 14, 70, 8, mid); shard(ax, 24, 140 + v * 9, 4 + (v % 2 ? 6 : -6), dark);
    g.shadowColor = '#ff7a22'; g.shadowBlur = 10; g.strokeStyle = '#ff8a2e'; g.lineWidth = 2.2; g.beginPath(); g.moveTo(ax - 6, ay - 4); g.lineTo(ax - 2, ay - 26); g.lineTo(ax - 8, ay - 44); g.stroke(); g.shadowBlur = 0;
    g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(ax, ay - 1, 30, 8, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 110, h: 190 };
  }
  // Rimeveil Glacier scenery, drawn once like the others: snow-laden pines, frosted shrubs, snowy boulders, ice
  // crystals, and 'ice' ridge blocks (the glacier's walls; neighbouring discs overlap into one ridge).
  const frostSprites = { tree: [], bush: [], rock: [], spire: [], ice: [] };
  function makeFrostPine(v) {
    const [c, g] = canvasOf(190, 290, SPR), ax = 95, ay = 278, rng = rngf(3100 + v * 23);
    g.lineJoin = 'round';
    g.fillStyle = OL; g.fillRect(ax - 10, ay - 40, 20, 42); g.fillStyle = '#5b463a'; g.fillRect(ax - 7, ay - 40, 14, 40); g.fillStyle = '#3e2f29'; g.fillRect(ax + 1, ay - 40, 6, 40);
    const tiers = 4 + (v % 2), height = 235 + v * 8;
    for (let i = 0; i < tiers; i++) {
      const t = i / (tiers - 1), base = ay - 34 - i * (height - 90) / tiers * .8, w = lerp(66, 28, t) + rng() * 5, h = lerp(92, 74, t), apex = [ax + (rng() - .5) * 4, base - h];
      const hem = []; for (let k = 0; k <= 8; k++) hem.push([ax - w + 2 * w * k / 8, base + (k % 2 ? 8 : 0) + rng() * 4]);
      const path = () => { g.beginPath(); g.moveTo(apex[0], apex[1]); hem.forEach(p => g.lineTo(p[0], p[1])); g.closePath(); };
      const gr = g.createLinearGradient(ax - w, 0, ax + w, 0); gr.addColorStop(0, '#37806f'); gr.addColorStop(.55, '#235a52'); gr.addColorStop(1, '#173f42');
      path(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.4; g.stroke();
      g.fillStyle = 'rgba(6,24,36,.3)'; g.beginPath(); g.moveTo(apex[0], apex[1]); g.lineTo(hem[8][0], hem[8][1]); g.lineTo(hem[5][0], hem[5][1] - 2); g.closePath(); g.fill();
      // snow: a cap near the apex and a ragged drift along each skirt
      g.fillStyle = '#f3faff'; g.beginPath(); g.moveTo(apex[0], apex[1] + 1);
      for (let k = 0; k <= 6; k++) g.lineTo(apex[0] + (k - 3) * w * .2, apex[1] + h * .36 + (k % 2 ? 7 : 0) - Math.abs(k - 3) * -3 - (k === 0 || k === 6 ? 10 : 0));
      g.closePath(); g.fill();
      g.fillStyle = '#cfe6f6'; g.beginPath(); g.moveTo(apex[0] + 2, apex[1] + 6); g.lineTo(apex[0] + w * .6, apex[1] + h * .34); g.lineTo(apex[0] + 2, apex[1] + h * .4); g.closePath(); g.fill();
      g.strokeStyle = 'rgba(240,250,255,.9)'; g.lineWidth = 3; g.lineCap = 'round';
      for (let k = 1; k < 8; k += 2) { g.beginPath(); g.moveTo(hem[k][0] - 7, hem[k][1] - 7); g.lineTo(hem[k][0] + 8, hem[k][1] - 5); g.stroke(); }
    }
    g.fillStyle = 'rgba(20,40,70,.28)'; g.beginPath(); g.ellipse(ax, ay - 2, 34, 9, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 190, h: 290 };
  }
  function makeFrostBush(v) {
    const [c, g] = canvasOf(120, 100, SPR), ax = 60, ay = 84, rng = rngf(3500 + v * 7);
    g.lineJoin = 'round';
    // One low dome of evergreen with a snow cap, scalloped along its edge, and a few frost berries.
    const w = 38 + v * 2, h = 30 + (v % 2) * 3, cy = ay - h * .55;
    const dome = () => { g.beginPath(); g.moveTo(ax - w, ay - 2); for (let i = 0; i <= 8; i++) { const a = Math.PI + i / 8 * Math.PI; g.lineTo(ax + Math.cos(a) * w + (i % 2 ? 0 : (rng() - .5) * 3), ay - 2 + Math.sin(a) * (h + (i % 2 ? 0 : 4))); } g.lineTo(ax + w, ay - 2); g.quadraticCurveTo(ax, ay + 8, ax - w, ay - 2); g.closePath(); };
    const gr = g.createLinearGradient(ax - w, 0, ax + w, 0); gr.addColorStop(0, '#4a9484'); gr.addColorStop(.5, '#2e6f65'); gr.addColorStop(1, '#1d4a4a');
    dome(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.2; g.stroke();
    g.fillStyle = 'rgba(8,30,40,.25)'; g.beginPath(); g.ellipse(ax + w * .45, cy + 6, w * .5, h * .5, 0, 0, 6.283); g.fill();
    g.strokeStyle = '#2a5a52'; g.lineWidth = 1.6; g.lineCap = 'round';
    for (let i = 0; i < 9; i++) { const x = ax - w * .8 + rng() * w * 1.6, y = ay - 6 - rng() * h * .7; g.beginPath(); g.moveTo(x, y); g.lineTo(x + (rng() - .5) * 8, y - 6 - rng() * 4); g.stroke(); }
    g.fillStyle = '#f2f9ff'; g.beginPath(); g.moveTo(ax - w * .7, cy - 2);
    for (let i = 0; i <= 6; i++) g.lineTo(ax - w * .7 + i * w * 1.4 / 6, ay - h - 2 + Math.abs(i - 3) * 5 + (i % 2 ? 5 : 0));
    g.quadraticCurveTo(ax, cy - h * .15, ax - w * .7, cy - 2); g.closePath(); g.fill();
    g.fillStyle = '#9bd8ff'; g.strokeStyle = '#1c3c64'; g.lineWidth = 1.4;
    for (let i = 0; i < 4; i++) { g.beginPath(); g.arc(ax - w * .55 + rng() * w * 1.1, ay - 12 - rng() * 10, 2.6, 0, 6.283); g.fill(); g.stroke(); }
    return { c, ax, ay, w: 120, h: 100 };
  }
  function makeSnowRock(v) {
    const [c, g] = canvasOf(90, 70, SPR), ax = 45, ay = 58, rng = rngf(3900 + v * 13), s = 1 + v * .12;
    const pts = [[-30, 0], [-34, -14], [-18, -34], [6, -40], [28, -26], [34, -8], [26, 0]].map(([x, y]) => [ax + x * s * (.9 + rng() * .2), ay + y * s * (.9 + rng() * .2)]);
    g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; g.fillStyle = '#6f8196';
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#4b5b72'; g.beginPath(); g.moveTo(pts[4][0], pts[4][1]); g.lineTo(pts[5][0], pts[5][1]); g.lineTo(pts[6][0], pts[6][1]); g.lineTo(ax + 6, ay - 4); g.closePath(); g.fill();
    g.fillStyle = '#f2f9ff'; g.beginPath(); g.moveTo(pts[1][0] + 2, pts[1][1] + 3); g.lineTo(pts[2][0], pts[2][1]); g.lineTo(pts[3][0], pts[3][1]); g.lineTo(pts[4][0] - 2, pts[4][1] + 2); g.lineTo(ax + 6, ay - 28); g.lineTo(ax - 4, ay - 25); g.lineTo(ax - 14, ay - 29); g.closePath(); g.fill();
    return { c, ax, ay, w: 90, h: 70 };
  }
  function makeIceSpire(v) {
    const [c, g] = canvasOf(110, 190, SPR), ax = 55, ay = 176, rng = rngf(4300 + v * 17);
    g.lineJoin = 'round';
    const shard = (x, w, h, lean, shade) => {
      const top = [x + lean, ay - h];
      for (const [dir, col] of [[-1, shade[0]], [1, shade[1]]]) {
        const gr = g.createLinearGradient(0, ay, 0, ay - h); gr.addColorStop(0, col[0]); gr.addColorStop(1, col[1]);
        g.fillStyle = gr; g.strokeStyle = OL; g.lineWidth = 3.2; g.beginPath(); g.moveTo(x + dir * w, ay); g.lineTo(x + dir * w * .8, ay - h * .55); g.lineTo(top[0], top[1]); g.lineTo(x, ay - h * .5); g.lineTo(x, ay); g.closePath(); g.fill(); g.stroke();
      }
      g.strokeStyle = 'rgba(255,255,255,.7)'; g.lineWidth = 2; g.beginPath(); g.moveTo(x - w * .55, ay - 6); g.lineTo(top[0] - 1, top[1] + 8); g.stroke();
    };
    const light = [['#7fb9e0', '#d9f3ff'], ['#4b86b8', '#9ad0f0']], mid = [['#5c9ccb', '#bfe6fa'], ['#376f9e', '#7fbbe2']];
    shard(ax - 22, 15, 78 + v * 6, -6, mid); shard(ax + 22, 14, 68, 8, mid); shard(ax, 24, 138 + v * 9, 4 + (v % 2 ? 6 : -6), light);
    g.fillStyle = 'rgba(160,230,255,.25)'; g.beginPath(); g.ellipse(ax, ay - 70, 36, 74, 0, 0, 6.283); g.fill();
    g.fillStyle = 'rgba(20,40,70,.3)'; g.beginPath(); g.ellipse(ax, ay - 1, 30, 8, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 110, h: 190 };
  }
  function makeIceBlock(v) {
    const [c, g] = canvasOf(190, 170, SPR), ax = 95, ay = 140, rng = rngf(4700 + v * 31);
    g.lineJoin = 'round';
    // a jagged crest above a wide base: left facet light, right facet dark, a snow lip on top
    const peaks = []; const n = 7;
    for (let k = 0; k <= n; k++) { const u = k / n, mid = 1 - Math.abs(u - .5) * 1.5; peaks.push([ax - 78 + 156 * u, ay - 50 - mid * (30 + rng() * 36) - (k % 2 ? 0 : 12 + rng() * 10)]); }
    const outline = () => { g.beginPath(); g.moveTo(ax - 80, ay + 4); g.lineTo(ax - 84, ay - 26); peaks.forEach(p => g.lineTo(p[0], p[1])); g.lineTo(ax + 84, ay - 26); g.lineTo(ax + 80, ay + 4); g.quadraticCurveTo(ax, ay + 40, ax - 80, ay + 4); g.closePath(); };
    const gr = g.createLinearGradient(0, ay - 110, 0, ay + 30); gr.addColorStop(0, '#e9f8ff'); gr.addColorStop(.45, '#8fc7ea'); gr.addColorStop(1, '#3d77a6');
    outline(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.6; g.stroke();
    g.save(); outline(); g.clip();
    g.fillStyle = 'rgba(20,60,110,.34)'; g.beginPath(); g.moveTo(ax + 6, ay - 120); g.lineTo(ax + 96, ay - 40); g.lineTo(ax + 96, ay + 40); g.lineTo(ax - 10, ay + 40); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 2.4; g.lineCap = 'round';
    for (let k = 0; k < 4; k++) { const x = ax - 66 + rng() * 120, y = ay - 70 + rng() * 60; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 10 + rng() * 12, y + 16 + rng() * 14); g.stroke(); }
    g.strokeStyle = 'rgba(30,70,120,.5)'; g.lineWidth = 1.6;
    for (let k = 0; k < 3; k++) { const x = ax - 50 + rng() * 100, y = ay - 50 + rng() * 50; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 8, y + 12); g.lineTo(x + 3, y + 24); g.stroke(); }
    g.restore();
    g.fillStyle = '#f6fcff'; g.beginPath(); g.moveTo(peaks[0][0] - 3, peaks[0][1] + 6);
    peaks.forEach((p, i) => { g.lineTo(p[0], p[1] + 1); if (i < n) g.lineTo((p[0] + peaks[i + 1][0]) / 2, Math.max(p[1], peaks[i + 1][1]) + 8 + rng() * 5); });
    g.lineTo(peaks[n][0] + 3, peaks[n][1] + 8); g.closePath(); g.fill();
    return { c, ax, ay, w: 190, h: 170 };
  }
  // Gloamfen scenery, drawn once like the others: drowned willows, reed clumps, mossy boulders, broken columns, and
  // 'thicket' ridge blocks (bramble walls; neighbouring discs overlap into one hedge).
  const fenSprites = { tree: [], bush: [], rock: [], spire: [], thicket: [] };
  function makeWillow(v) {
    const [c, g] = canvasOf(210, 270, SPR), ax = 105, ay = 258, rng = rngf(5100 + v * 29);
    g.lineJoin = 'round'; g.lineCap = 'round';
    // a leaning, knotted trunk with two heavy boughs
    const lean = (v % 2 ? 1 : -1) * 10;
    g.fillStyle = OL; g.beginPath(); g.moveTo(ax - 20, ay + 2); g.quadraticCurveTo(ax - 8, ay - 40, ax + lean - 8, ay - 120); g.lineTo(ax + lean + 11, ay - 120); g.quadraticCurveTo(ax + 6, ay - 40, ax + 22, ay + 2); g.closePath(); g.fill();
    const tg = g.createLinearGradient(ax - 18, 0, ax + 22, 0); tg.addColorStop(0, '#4a4034'); tg.addColorStop(.55, '#6b5c48'); tg.addColorStop(1, '#2e271f');
    g.fillStyle = tg; g.beginPath(); g.moveTo(ax - 17, ay); g.quadraticCurveTo(ax - 6, ay - 40, ax + lean - 5, ay - 118); g.lineTo(ax + lean + 8, ay - 118); g.quadraticCurveTo(ax + 5, ay - 40, ax + 19, ay); g.closePath(); g.fill();
    g.strokeStyle = 'rgba(20,14,8,.5)'; g.lineWidth = 2.2; for (let i = 0; i < 5; i++) { const yy = ay - 24 - i * 20; g.beginPath(); g.moveTo(ax - 5 + rng() * 6, yy); g.lineTo(ax - 3 + rng() * 8, yy - 12); g.stroke(); }
    g.fillStyle = '#5f8a4a'; g.beginPath(); g.ellipse(ax - 9, ay - 52, 6, 20, .15, 0, 6.283); g.fill();                 // moss on the shaded side
    // crown: a low, dark dome of leaves with long hanging fronds in front
    const cx = ax + lean, cy = 110, blobs = [{ x: cx - 46, y: cy + 14, r: 34 }, { x: cx + 46, y: cy + 16, r: 34 }, { x: cx, y: cy - 20, r: 46 }, { x: cx - 24, y: cy, r: 40 }, { x: cx + 26, y: cy - 2, r: 40 }];
    outlineUnion(g, blobs, OL, 4);
    for (const b of blobs) { const gr = g.createRadialGradient(b.x - b.r * .3, b.y - b.r * .4, b.r * .1, b.x, b.y, b.r); gr.addColorStop(0, '#7fa85a'); gr.addColorStop(.6, '#456f3e'); gr.addColorStop(1, '#233d2c'); g.fillStyle = gr; g.beginPath(); g.arc(b.x, b.y, b.r, 0, 6.283); g.fill(); }
    for (let i = 0; i < 17; i++) {                                                                                       // fronds
      const x = cx - 78 + i * 9.6 + (rng() - .5) * 4, top = cy + 18 + Math.abs(i - 8) * -1.4 + rng() * 8, len = 46 + rng() * 52 - Math.abs(i - 8) * 2;
      g.strokeStyle = OL; g.lineWidth = 5.4; g.beginPath(); g.moveTo(x, top); g.quadraticCurveTo(x + (rng() - .5) * 8, top + len * .6, x + (rng() - .5) * 10, top + len); g.stroke();
      g.strokeStyle = i % 3 ? '#5f8f4a' : '#86b062'; g.lineWidth = 3; g.beginPath(); g.moveTo(x, top); g.quadraticCurveTo(x + (rng() - .5) * 8, top + len * .6, x + (rng() - .5) * 10, top + len); g.stroke();
    }
    g.fillStyle = 'rgba(14,22,40,.32)'; g.beginPath(); g.ellipse(ax, ay - 2, 36, 9, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 210, h: 270 };
  }
  function makeReeds(v) {
    const [c, g] = canvasOf(120, 100, SPR), ax = 60, ay = 84, rng = rngf(5500 + v * 7);
    g.lineJoin = 'round'; g.lineCap = 'round';
    g.fillStyle = OL; g.beginPath(); g.ellipse(ax, ay - 1, 30, 9, 0, 0, 6.283); g.fill();
    g.fillStyle = '#4a3c2a'; g.beginPath(); g.ellipse(ax, ay - 2, 27, 7, 0, 0, 6.283); g.fill();
    g.fillStyle = '#6a8a48'; g.beginPath(); g.ellipse(ax - 6, ay - 4, 14, 3.6, 0, 0, 6.283); g.fill();
    const n = 11 + (v % 3);
    for (let i = 0; i < n; i++) {
      const x = ax - 24 + i * (48 / (n - 1)) + (rng() - .5) * 4, h = 34 + rng() * 34 + (i % 3 ? 0 : 8), bend = (rng() - .5) * 22;
      g.strokeStyle = OL; g.lineWidth = 5; g.beginPath(); g.moveTo(x, ay - 3); g.quadraticCurveTo(x + bend * .2, ay - h * .6, x + bend, ay - h); g.stroke();
      g.strokeStyle = i % 2 ? '#7aa04e' : '#a2c068'; g.lineWidth = 2.8; g.beginPath(); g.moveTo(x, ay - 3); g.quadraticCurveTo(x + bend * .2, ay - h * .6, x + bend, ay - h); g.stroke();
      if (i % 3 === 1) {                                                                                                // a cattail
        g.strokeStyle = OL; g.lineWidth = 7.4; g.beginPath(); g.moveTo(x + bend, ay - h - 1); g.lineTo(x + bend + .8, ay - h - 13); g.stroke();
        g.strokeStyle = '#7a4a2c'; g.lineWidth = 4.6; g.beginPath(); g.moveTo(x + bend, ay - h - 1); g.lineTo(x + bend + .8, ay - h - 12); g.stroke();
      }
    }
    return { c, ax, ay, w: 120, h: 100 };
  }
  function makeFenRock(v) {
    const [c, g] = canvasOf(90, 70, SPR), ax = 45, ay = 58, rng = rngf(5900 + v * 13), s = 1 + v * .12;
    const pts = [[-30, 0], [-34, -14], [-18, -34], [6, -40], [28, -26], [34, -8], [26, 0]].map(([x, y]) => [ax + x * s * (.9 + rng() * .2), ay + y * s * (.9 + rng() * .2)]);
    g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; g.fillStyle = '#7d8a78';
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#a6b39c'; g.beginPath(); g.moveTo(pts[1][0] + 3, pts[1][1] + 2); g.lineTo(pts[2][0], pts[2][1] + 2); g.lineTo(pts[3][0], pts[3][1] + 2); g.lineTo(ax, ay - 20); g.closePath(); g.fill();
    g.fillStyle = '#566253'; g.beginPath(); g.moveTo(pts[4][0], pts[4][1]); g.lineTo(pts[5][0], pts[5][1]); g.lineTo(pts[6][0], pts[6][1]); g.lineTo(ax + 6, ay - 4); g.closePath(); g.fill();
    g.fillStyle = '#4f7f3a'; g.beginPath(); g.ellipse(ax - 6, ay - 30 - v, 15, 6, -.2, 0, 6.283); g.fill();                  // a cap of moss
    g.fillStyle = '#7ab04e'; g.beginPath(); g.ellipse(ax - 9, ay - 32 - v, 8, 3, -.2, 0, 6.283); g.fill();
    g.fillStyle = '#6f9a45'; g.beginPath(); g.ellipse(ax + 14, ay - 3, 10, 3.6, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 90, h: 70 };
  }
  function makeColumn(v) {
    const [c, g] = canvasOf(110, 190, SPR), ax = 55, ay = 176, rng = rngf(6300 + v * 17);
    g.lineJoin = 'round';
    // a fluted stone column snapped off at an angle, with its capital lying at its foot and moss and ivy on it
    const h = 100 + v * 14, w = 15;
    const body = () => { g.beginPath(); g.moveTo(ax - w, ay); g.lineTo(ax - w + 1, ay - h + 8); g.lineTo(ax - 3, ay - h - 6); g.lineTo(ax + 5, ay - h + 2); g.lineTo(ax + w, ay - h + 14); g.lineTo(ax + w, ay); g.closePath(); };
    const gr = g.createLinearGradient(ax - w, 0, ax + w, 0); gr.addColorStop(0, '#b4b8a6'); gr.addColorStop(.5, '#8a9082'); gr.addColorStop(1, '#565c52');
    body(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.6; g.stroke();
    g.strokeStyle = 'rgba(30,36,28,.4)'; g.lineWidth = 2; for (let k = -1; k <= 1; k++) { g.beginPath(); g.moveTo(ax + k * 8, ay - 4); g.lineTo(ax + k * 8, ay - h + 14 - k * 3); g.stroke(); }
    g.fillStyle = '#d0d4c0'; g.beginPath(); g.moveTo(ax - 3, ay - h - 6); g.lineTo(ax + 5, ay - h + 2); g.lineTo(ax + w, ay - h + 14); g.lineTo(ax + 4, ay - h + 12); g.closePath(); g.fill();
    g.fillStyle = '#4f7f3a'; for (let k = 0; k < 4; k++) { g.beginPath(); g.ellipse(ax - w + 4 + rng() * 14, ay - 12 - k * 20 - rng() * 8, 8 + rng() * 5, 5, 0, 0, 6.283); g.fill(); }
    g.strokeStyle = '#3d6a2c'; g.lineWidth = 2.2; g.lineCap = 'round'; g.beginPath(); g.moveTo(ax + 8, ay - 6); for (let k = 1; k < 7; k++) g.lineTo(ax + 8 + Math.sin(k * 1.6) * 7, ay - 6 - k * 13); g.stroke();
    g.fillStyle = '#9a9e8c'; g.strokeStyle = OL; g.lineWidth = 3; g.beginPath(); g.ellipse(ax + 26, ay - 6, 15, 8, .1, 0, 6.283); g.fill(); g.stroke();
    g.fillStyle = '#7ab04e'; g.beginPath(); g.ellipse(ax + 24, ay - 11, 9, 3, 0, 0, 6.283); g.fill();
    g.fillStyle = 'rgba(14,22,40,.3)'; g.beginPath(); g.ellipse(ax, ay - 1, 28, 8, 0, 0, 6.283); g.fill();
    return { c, ax, ay, w: 110, h: 190 };
  }
  function makeThicket(v) {
    const [c, g] = canvasOf(190, 170, SPR), ax = 95, ay = 140, rng = rngf(6700 + v * 31);
    g.lineJoin = 'round'; g.lineCap = 'round';
    // a bramble hedge: a dark mass with a ragged crest, long arching canes, pale thorns and a few dusky berries
    const peaks = []; const n = 8;
    for (let k = 0; k <= n; k++) { const u = k / n, mid = 1 - Math.abs(u - .5) * 1.4; peaks.push([ax - 80 + 160 * u, ay - 44 - mid * (26 + rng() * 34) - (k % 2 ? 0 : 10 + rng() * 10)]); }
    const outline = () => { g.beginPath(); g.moveTo(ax - 82, ay + 4); g.lineTo(ax - 86, ay - 24); peaks.forEach(p => g.lineTo(p[0], p[1])); g.lineTo(ax + 86, ay - 24); g.lineTo(ax + 82, ay + 4); g.quadraticCurveTo(ax, ay + 34, ax - 82, ay + 4); g.closePath(); };
    const gr = g.createLinearGradient(0, ay - 110, 0, ay + 30); gr.addColorStop(0, '#4a5a3a'); gr.addColorStop(.5, '#2e3b2c'); gr.addColorStop(1, '#171d19');
    outline(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.8; g.stroke();
    g.save(); outline(); g.clip();
    g.fillStyle = 'rgba(8,10,20,.38)'; g.beginPath(); g.moveTo(ax + 6, ay - 120); g.lineTo(ax + 96, ay - 40); g.lineTo(ax + 96, ay + 40); g.lineTo(ax - 10, ay + 40); g.closePath(); g.fill();
    for (let k = 0; k < 14; k++) {                                                                                       // arching canes
      const x = ax - 78 + rng() * 156, y = ay - 10 + rng() * 26, ex = x + (rng() - .5) * 70, ey = y - 36 - rng() * 44;
      g.strokeStyle = '#0d110e'; g.lineWidth = 4.4; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo((x + ex) / 2 + 14, (y + ey) / 2 - 20, ex, ey); g.stroke();
      g.strokeStyle = k % 3 ? '#5a4a3a' : '#7a6a52'; g.lineWidth = 2; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo((x + ex) / 2 + 14, (y + ey) / 2 - 20, ex, ey); g.stroke();
    }
    g.fillStyle = '#d8d4b8'; for (let k = 0; k < 22; k++) { const x = ax - 80 + rng() * 160, y = ay - 80 + rng() * 90; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 3 + rng() * 3, y - 8 - rng() * 4); g.lineTo(x + 6, y + 1); g.closePath(); g.fill(); }
    g.fillStyle = '#9a4a9a'; g.strokeStyle = '#2a1230'; g.lineWidth = 1.2; for (let k = 0; k < 7; k++) { g.beginPath(); g.arc(ax - 70 + rng() * 140, ay - 60 + rng() * 60, 3.2, 0, 6.283); g.fill(); g.stroke(); }
    g.restore();
    g.fillStyle = '#6f9a45'; g.beginPath(); g.moveTo(peaks[0][0] - 3, peaks[0][1] + 7);                                 // moss along the crest
    peaks.forEach((p, i) => { g.lineTo(p[0], p[1] + 1); if (i < n) g.lineTo((p[0] + peaks[i + 1][0]) / 2, Math.max(p[1], peaks[i + 1][1]) + 6 + rng() * 5); });
    g.lineTo(peaks[n][0] + 3, peaks[n][1] + 8); g.closePath(); g.fill();
    return { c, ax, ay, w: 190, h: 170 };
  }
  function buildSprites() {
    for (let v = 0; v < 4; v++) {
      sprites.tree[v] = makeTree(v); sprites.bush[v] = makeBush(v); sprites.rock[v] = makeRock(v);
      emberSprites.tree[v] = makeCharTree(v); emberSprites.bush[v] = makeEmberBush(v); emberSprites.rock[v] = makeBasalt(v); emberSprites.spire[v] = makeSpire(v);
      frostSprites.tree[v] = makeFrostPine(v); frostSprites.bush[v] = makeFrostBush(v); frostSprites.rock[v] = makeSnowRock(v); frostSprites.spire[v] = makeIceSpire(v); frostSprites.ice[v] = makeIceBlock(v);
      fenSprites.tree[v] = makeWillow(v); fenSprites.bush[v] = makeReeds(v); fenSprites.rock[v] = makeFenRock(v); fenSprites.spire[v] = makeColumn(v); fenSprites.thicket[v] = makeThicket(v);
    }
  }
  const WYRD_NONE = {};                                   // the Wyrdwood's scenery is drawn by client/wyrdart.js through City.art
  const spriteSet = () => zdef.theme === 'skybridge' || zdef.theme === 'nornroot' || zdef.theme === 'wyrd' || zdef.theme === 'sky' || zdef.theme === 'deep' || zdef.theme === 'nacre' || zdef.theme === 'astral' || zdef.theme === 'prismwaste' || zdef.theme === 'orrery' || zdef.theme === 'moonspore' || zdef.theme === 'stormglass' || zdef.theme === 'sunward' || zdef.theme === 'ribbonwild' || zdef.theme === 'tanglecrown' || zdef.theme === 'worldtree' || zdef.theme === 'heartwood' || zdef.theme === 'lapiserg' || zdef.theme === 'frostwake' || zdef.theme === 'cairnspine' || zdef.theme === 'yearwheel' || zdef.theme === 'eye_below' || zdef.theme === 'elder_hollow' || zdef.theme === 'thousandfold' || zdef.theme === 'rain_crown' || zdef.theme === 'seed_vault' || zdef.theme === 'sunken_astrolabe' || zdef.theme === 'thunderheart_gate' || SeasonDungeonArt.isTheme(zdef.theme) || CathedralArt.isTheme(zdef.theme) ? WYRD_NONE : zdef.theme === 'ember' ? emberSprites : zdef.theme === 'frost' ? frostSprites : zdef.theme === 'fen' ? fenSprites : sprites;

  // ---------- ground chunks ----------
  const chunks = new Map(); let chunkScale = 1;
  const CLIFF = 120, PADX = 10, PADTOP = 40;
  function chunkGeom(cx, cy) { const x0 = cx * CH, y0 = cy * CH; return { x0, y0, ox: (x0 - (y0 + CH)) * TW / 2 - TW / 2 - PADX, oy: (x0 + y0) * TH / 2 - PADTOP, w: CH * TW + TW + PADX * 2, h: CH * TH + TH + PADTOP + CLIFF }; }
  function renderChunk(cx, cy) {
    const G = chunkGeom(cx, cy), [c, g] = canvasOf(G.w, G.h, chunkScale);
    const ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city' || zdef.theme === 'asterion', asterion = zdef.theme === 'asterion', vault = zdef.theme === 'skybridge' || zdef.theme === 'nornroot' || zdef.theme === 'vault' || zdef.theme === 'eye_below' || zdef.theme === 'elder_hollow' || zdef.theme === 'thousandfold' || zdef.theme === 'rain_crown' || zdef.theme === 'seed_vault' || zdef.theme === 'sunken_astrolabe' || zdef.theme === 'thunderheart_gate' || SeasonDungeonArt.isTheme(zdef.theme) || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', prism = zdef.theme === 'prismwaste', orrery = zdef.theme === 'orrery', moonspore = zdef.theme === 'moonspore', stormglass = zdef.theme === 'stormglass', sunward = zdef.theme === 'sunward', ribbonwild = zdef.theme === 'ribbonwild', tanglecrown = zdef.theme === 'tanglecrown', worldtree = zdef.theme === 'worldtree', heartwood = zdef.theme === 'heartwood', lapis = zdef.theme === 'lapiserg', frostwake = zdef.theme === 'frostwake', cairn = zdef.theme === 'cairnspine', yearwheel = zdef.theme === 'yearwheel', moonwell = zdef.theme === 'moonwell', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    const arenas = vault ? (zdef.slimes || []).filter(m => BOSS_KINDS.includes(m.kind)) : [];
    for (let ty = 0; ty < CH; ty++) for (let tx = 0; tx < CH; tx++) {
      const x = G.x0 + tx, y = G.y0 + ty; if (x >= MAP || y >= MAP) continue;
      const i = y * MAP + x, px = (x - y) * TW / 2 - G.ox, py = (x + y) * TH / 2 - G.oy, tone = map.tone[i], dirt = map.dirt[i];
      if (vault && !dirt) continue;                                                  // solid rock: stays black
      if ((sky || moonwell) && !map.floor[i]) continue;                              // open water or sky
      const alt = ((x + y) & 1) ? 1.4 : -1.4, e = .7;
      const ribbonHue = [344,44,177,272][Math.floor(((Math.atan2(y-67,x-72)+Math.PI*2+Math.PI/4)%(Math.PI*2))/(Math.PI/2))];
      g.fillStyle = zdef.theme === 'arena' ? (x < 3 || y < 3 || x > 28 || y > 28 ? '#423746' : x === 16 || y === 16 ? '#ae8456' : (x + y) % 2 ? '#6e6877' : '#777180') : zdef.theme === 'skybridge' ? SkybridgeArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'nornroot' ? NornrootArt.ground(x,y,tone,alt,zdef) : moonwell ? MoonwellArt.ground(x,y,tone,dirt,alt,zdef) : zdef.theme === 'eye_below' ? EyeBelowArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'elder_hollow' ? ElderHollowArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'thousandfold' ? PavilionArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'rain_crown' ? RainCrownArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'seed_vault' ? SeedVaultArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'sunken_astrolabe' ? SunkenArt.ground(x,y,tone,alt,zdef) : zdef.theme === 'thunderheart_gate' ? ThunderArt.ground(x,y,tone,alt,zdef) : SeasonDungeonArt.isTheme(zdef.theme) ? SeasonDungeonArt.ground(zdef.theme,x,y,tone,alt,zdef) : CathedralArt.isTheme(zdef.theme) ? CathedralArt.ground(zdef.theme,x,y,tone,alt,zdef) : zdef.theme === 'vault' ? VaultArt.ground(x,y,tone,alt,zdef.rooms,arenas) : vault ? `hsl(${226 + tone * 10}, ${9 + tone * 5}%, ${19 + tone * 7 + alt * .7}%)` : asterion ? (dirt === 1 ? `hsl(${201 + tone * 14}, 21%, ${51 + tone * 7 + alt}%)` : dirt === 2 ? `hsl(${44 + tone * 9}, 38%, ${73 + tone * 9 + alt}%)` : `hsl(${222 + tone * 17}, ${19 + tone * 10}%, ${28 + tone * 9 + alt}%)`) : city ? (dirt === 1 ? `hsl(${32 + tone * 6}, ${9 + tone * 5}%, ${46 + tone * 7 + alt * .5}%)` : dirt === 2 ? `hsl(${42 + tone * 6}, ${24 + tone * 6}%, ${(x + y) & 1 ? 79 : 75}%)` : dirt === 3 ? `hsl(${14 + tone * 6}, ${34 + tone * 6}%, ${50 + tone * 6 + alt * .5}%)` : `hsl(${96 + tone * 14}, ${46 + tone * 10}%, ${38 + tone * 8 + alt * .8 + (((x + y) >> 1) & 1) * 1.6}%)`)
        : sky ? skyGround(x, y, tone, dirt, alt)
        : orrery ? (dirt ? `hsl(${34 + tone * 7}, 19%, ${43 + tone * 8 + alt}%)` : `hsl(${232 + tone * 13}, ${17 + tone * 9}%, ${20 + tone * 10 + alt}%)`)
        : moonspore ? (dirt ? `hsl(${151 + tone * 9}, 18%, ${35 + tone * 9 + alt}%)` : `hsl(${177 + tone * 20}, ${25 + tone * 12}%, ${19 + tone * 10 + alt}%)`)
        : worldtree ? (dirt ? `hsl(${34+tone*8}, 42%, ${46+tone*8+alt}%)` : `hsl(${142+tone*18}, 51%, ${33+tone*10+alt}%)`)
        : heartwood ? (dirt ? `hsl(${35+tone*6}, 35%, ${45+tone*8+alt}%)` : `hsl(${31+tone*6}, 29%, ${34+tone*8+alt}%)`)
        : lapis ? (dirt ? `hsl(${34+tone*7}, 47%, ${63+tone*8+alt}%)` : `hsl(${35+tone*11}, ${58+tone*8}%, ${57+tone*12+alt}%)`)
        : yearwheel ? yearGround(x,y,tone,dirt,alt)
        : cairn ? (dirt ? `hsl(${31+tone*8}, 32%, ${54+tone*7+alt}%)` : `hsl(${210+tone*9}, ${9+tone*7}%, ${38+tone*9+alt}%)`)
        : frostwake ? (dirt ? `hsl(${197+tone*9}, 43%, ${72+tone*8+alt}%)` : `hsl(${198+tone*14}, ${23+tone*14}%, ${83+tone*10+alt}%)`)
        : tanglecrown ? (dirt ? `hsl(${34+tone*8}, ${37+tone*7}%, ${44+tone*8+alt}%)` : `hsl(${133+tone*19}, ${48+tone*9}%, ${29+tone*11+alt}%)`)
        : ribbonwild ? (dirt ? `hsl(${43+tone*8}, 79%, ${73+tone*5+alt}%)` : (x<49&&y>44&&y<97 ? `hsl(${103+tone*12}, ${47+tone*8}%, ${44+tone*8+alt}%)` : `hsl(${ribbonHue+tone*6}, ${52+tone*9}%, ${62+tone*9+alt}%)`))
        : sunward ? (dirt ? `hsl(${35 + tone * 9}, 43%, ${58 + tone * 8 + alt}%)` : `hsl(${100 + tone * 22}, ${47 + tone * 10}%, ${34 + tone * 13 + alt}%)`)
        : stormglass ? (dirt ? `hsl(${182 + tone * 13}, 20%, ${52 + tone * 8 + alt}%)` : `hsl(${212 + tone * 15}, ${20 + tone * 10}%, ${17 + tone * 9 + alt}%)`)
        : prism ? (dirt ? `hsl(${34 + tone * 8}, 38%, ${54 + tone * 8 + alt}%)` : `hsl(${32 + tone * 14}, ${27 + tone * 12}%, ${43 + tone * 13 + alt}%)`)
        : astral ? (dirt ? `hsl(${43 + tone * 9}, 33%, ${34 + tone * 9 + alt}%)` : `hsl(${158 + tone * 42}, ${32 + tone * 14}%, ${27 + tone * 12 + alt}%)`)
        : deep ? deepGround(x, y, tone, dirt, alt)
        : wyrd ? wyrdGround(x, y, tone, dirt, alt)
        : fen ? (dirt ? `hsl(${30 + tone * 6}, ${30 + tone * 6}%, ${27 + tone * 6 + alt}%)` : `hsl(${92 + tone * 16}, ${26 + tone * 12}%, ${21 + tone * 9 + alt * .8}%)`)
        : frost ? (dirt ? `hsl(${208 + tone * 8}, ${26 + tone * 8}%, ${66 + tone * 6 + alt}%)` : `hsl(${200 + tone * 12}, ${44 + tone * 10}%, ${84 + tone * 8 + alt * .6}%)`)
        : ember ? (dirt ? `hsl(${22 + tone * 8}, ${20 + tone * 8}%, ${30 + tone * 8 + alt}%)` : `hsl(${12 + tone * 14}, ${10 + tone * 8}%, ${15 + tone * 11 + alt}%)`)
        : dirt ? `hsl(${30 + tone * 8}, ${38 + tone * 8}%, ${48 + tone * 8 + alt}%)` : `hsl(${100 + tone * 16}, ${46 + tone * 12}%, ${36 + tone * 12 + alt}%)`;
      g.beginPath(); g.moveTo(px, py - e); g.lineTo(px + TW / 2 + e, py + TH / 2); g.lineTo(px, py + TH + e); g.lineTo(px - TW / 2 - e, py + TH / 2); g.closePath(); g.fill();
      if (zdef.theme === 'arena') continue;
      const r = rngf(x * 977 + y * 131 + 7), inTile = () => { const a = r() - .5, b = r() - .5; return [px + (a - b) * TW * .4, py + TH / 2 + (a + b) * TH * .4]; };
      if (yearwheel) {
        const season=yearSeason(x,y), colors=[['#f9b4d2','#77bd8b'],['#ffe4a0','#e3ab56'],['#f0ae63','#ab5a3e'],['#e8f7fa','#a9d7ec']][season];
        if (dirt) {g.strokeStyle=colors[0];g.lineWidth=1.4;g.beginPath();g.moveTo(px-17,py+22);g.lineTo(px,py+14);g.lineTo(px+17,py+22);g.stroke();}
        else if (r()<.42) {const [qx,qy]=inTile();g.fillStyle=colors[0];g.globalAlpha=.48;g.beginPath();g.ellipse(qx,qy,2.5+r()*3,1.5+r()*2,r()*3,0,6.283);g.fill();g.globalAlpha=1;}
      } else if (moonwell) {
        MoonwellArt.detail(g,px,py,x,y,TW,TH,dirt,zdef);
      } else if (zdef.theme === 'skybridge') {
        SkybridgeArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'nornroot') {
        NornrootArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'vault') {
        VaultArt.detail(g,px,py,x,y,TW,TH,zdef.rooms,arenas);
      } else if (zdef.theme === 'eye_below') {
        EyeBelowArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'elder_hollow') {
        ElderHollowArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'thousandfold') {
        PavilionArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'rain_crown') {
        RainCrownArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'seed_vault') {
        SeedVaultArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'sunken_astrolabe') {
        SunkenArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (zdef.theme === 'thunderheart_gate') {
        ThunderArt.detail(g,px,py,x,y,TW,TH,zdef);
      } else if (SeasonDungeonArt.isTheme(zdef.theme)) {
        SeasonDungeonArt.detail(g,zdef.theme,px,py,x,y,TW,TH,zdef);
      } else if (CathedralArt.isTheme(zdef.theme)) {
        CathedralArt.detail(g,zdef.theme,px,py,x,y,TW,TH,zdef);
      } else if (vault) {
        g.strokeStyle = 'rgba(4,5,12,.55)'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(px - TW / 2, py + TH / 2); g.lineTo(px, py); g.lineTo(px + TW / 2, py + TH / 2); g.stroke();   // flagstone seams on the two back edges
        g.strokeStyle = 'rgba(150,160,200,.07)'; g.beginPath(); g.moveTo(px - TW / 2, py + TH / 2 + 1.2); g.lineTo(px, py + TH + 1.2); g.lineTo(px + TW / 2, py + TH / 2 + 1.2); g.stroke();
        if (r() < .3) { const [qx, qy] = inTile(); g.strokeStyle = 'rgba(6,7,14,.7)'; g.lineWidth = 1.3; g.lineCap = 'round'; const a = r() * 6.283, l = 6 + r() * 9; g.beginPath(); g.moveTo(qx, qy); g.lineTo(qx + Math.cos(a) * l, qy + Math.sin(a) * l * .5); g.lineTo(qx + Math.cos(a + .9) * l * 1.4, qy + Math.sin(a + .9) * l * .7); g.stroke(); }
        if (r() < .12) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(56,90,68,.3)'; g.beginPath(); g.ellipse(qx, qy, 5 + r() * 9, 2 + r() * 4, 0, 0, 6.283); g.fill(); }
        else if (r() < .04) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(30,60,80,.55)'; g.beginPath(); g.ellipse(qx, qy, 7 + r() * 6, 3 + r() * 2, 0, 0, 6.283); g.fill(); g.fillStyle = 'rgba(150,200,230,.3)'; g.fillRect(qx - 3, qy - 1, 5, 1); }
        for (const m of arenas) {                                                    // runes inlaid in rings round each boss
          const d = Math.hypot(x + .5 - m.x, y + .5 - m.y), ringA = Math.abs(d - 6.4) < .52, ringB = Math.abs(d - 3.2) < .5;
          if (ringA || ringB) { g.fillStyle = 'rgba(90,150,220,.17)'; g.beginPath(); g.moveTo(px, py); g.lineTo(px + TW / 2, py + TH / 2); g.lineTo(px, py + TH); g.lineTo(px - TW / 2, py + TH / 2); g.closePath(); g.fill();
            g.strokeStyle = 'rgba(120,210,255,.45)'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(px - 8, py + TH / 2 + 2); g.lineTo(px, py + TH / 2 - 5); g.lineTo(px + 8, py + TH / 2 + 2); g.moveTo(px, py + TH / 2 - 5); g.lineTo(px, py + TH / 2 + 8); g.stroke(); }
        }
      } else if (asterion) {
        g.strokeStyle=dirt===2?'rgba(119,73,156,.44)':dirt?'rgba(153,236,241,.42)':'rgba(72,91,143,.5)';g.lineWidth=1.3;
        g.beginPath();g.moveTo(px,py);g.lineTo(px+TW/2,py+TH/2);g.lineTo(px,py+TH);g.lineTo(px-TW/2,py+TH/2);g.closePath();g.stroke();
        if(((x*19+y*7)%11)===0){g.fillStyle='rgba(244,226,174,.45)';g.beginPath();g.arc(px,py+TH/2,2.5,0,6.283);g.fill();}
      } else if (city) {
        const at = (u, v) => [px + (u - v) * TW / 2, py + (u + v) * TH / 2];
        if (dirt === 1) {                                                              // cobbles: a 3x3 of rounded stones
          for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) {
            const [qx, qy] = at((a + .5 + (r() - .5) * .2) / 3, (b + .5 + (r() - .5) * .2) / 3), l = 52 + r() * 14 + tone * 5;
            g.fillStyle = `hsl(${30 + r() * 12}, ${8 + r() * 6}%, ${l}%)`; g.beginPath(); g.ellipse(qx, qy, TW / 6.6, TH / 6.6, 0, 0, 6.283); g.fill();
            g.strokeStyle = 'rgba(60,52,40,.35)'; g.lineWidth = .9; g.stroke();
          }
        } else if (dirt === 2) {                                                       // marble paving: seams and a few inlays
          g.strokeStyle = 'rgba(120,105,80,.38)'; g.lineWidth = 1; g.beginPath(); g.moveTo(px, py); g.lineTo(px + TW / 2, py + TH / 2); g.lineTo(px, py + TH); g.lineTo(px - TW / 2, py + TH / 2); g.closePath(); g.stroke();
          if (((x * 7 + y * 13) % 5) === 0) { g.fillStyle = 'rgba(190,168,120,.55)'; g.beginPath(); g.moveTo(px, py + TH * .3); g.lineTo(px + TW * .2, py + TH / 2); g.lineTo(px, py + TH * .7); g.lineTo(px - TW * .2, py + TH / 2); g.closePath(); g.fill(); }
        } else if (dirt === 3) {                                                       // brick courts: running bond
          g.strokeStyle = 'rgba(70,32,22,.45)'; g.lineWidth = 1;
          for (const f of [.25, .5, .75]) { const [a1, a2] = [at(0, f), at(1, f)]; g.beginPath(); g.moveTo(a1[0], a1[1]); g.lineTo(a2[0], a2[1]); g.stroke(); }
          for (let row = 0; row < 4; row++) for (const f of [row % 2 ? .25 : .5, row % 2 ? .75 : 1]) { const [a1, a2] = [at(f, row / 4), at(f, (row + 1) / 4)]; g.beginPath(); g.moveTo(a1[0], a1[1]); g.lineTo(a2[0], a2[1]); g.stroke(); }
        } else {                                                                       // lawn
          g.lineCap = 'round';
          const tufts = Math.floor(r() * 2.2);
          for (let k = 0; k < tufts; k++) {
            const [qx, qy] = inTile(), h = 4 + r() * 4; g.lineWidth = 1.6;
            g.strokeStyle = `hsl(${102 + tone * 12}, 50%, ${27 + tone * 8}%)`; g.beginPath(); g.moveTo(qx - 2.5, qy + 1); g.lineTo(qx - 4, qy - h); g.moveTo(qx + 2.5, qy + 1); g.lineTo(qx + 4, qy - h * .9); g.stroke();
            g.strokeStyle = `hsl(${98 + tone * 12}, 58%, ${46 + tone * 8}%)`; g.beginPath(); g.moveTo(qx, qy + 1); g.lineTo(qx - .5, qy - h * 1.2); g.stroke();
          }
          if (r() < .055) {
            const [qx, qy] = inTile(), col = ['#ffffff', '#ffe066', '#ff9ad5', '#b9a0ff'][Math.floor(r() * 4)];
            g.strokeStyle = '#2f7a3a'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(qx, qy + 2); g.lineTo(qx, qy - 4); g.stroke();
            g.fillStyle = col; for (let p = 0; p < 5; p++) { const a = p / 5 * 6.283; g.beginPath(); g.arc(qx + Math.cos(a) * 2.6, qy - 5 + Math.sin(a) * 2.1, 1.9, 0, 6.283); g.fill(); }
            g.fillStyle = '#f5b82e'; g.beginPath(); g.arc(qx, qy - 5, 1.4, 0, 6.283); g.fill();
          }
        }
        if (dirt === 1 || dirt === 3) {                                                // kerbs where a street meets the lawn
          const edge = (a, b, c, d2) => { g.strokeStyle = '#6c6250'; g.lineWidth = 2.6; g.beginPath(); g.moveTo(a, b); g.lineTo(c, d2); g.stroke(); g.strokeStyle = 'rgba(255,248,226,.5)'; g.lineWidth = 1; g.beginPath(); g.moveTo(a, b + 1.6); g.lineTo(c, d2 + 1.6); g.stroke(); };
          const bare = (nx, ny) => nx >= 0 && ny >= 0 && nx < MAP && ny < MAP && !map.dirt[ny * MAP + nx];
          if (bare(x, y - 1)) edge(px, py, px + TW / 2, py + TH / 2);
          if (bare(x + 1, y)) edge(px + TW / 2, py + TH / 2, px, py + TH);
          if (bare(x, y + 1)) edge(px, py + TH, px - TW / 2, py + TH / 2);
          if (bare(x - 1, y)) edge(px - TW / 2, py + TH / 2, px, py);
        }
      } else if (sky) {
        skyDetail(g, r, inTile, px, py, x, y, tone, dirt);
      } else if (orrery) {
        for (let k = 0; k < (dirt ? 3 : 5); k++) { const [qx,qy]=inTile();g.fillStyle=k%3?'rgba(180,174,190,.28)':'rgba(224,177,105,.4)';g.beginPath();g.ellipse(qx,qy,2+r()*5,1+r()*2,0,0,6.283);g.fill(); }
        if (r()<.08) { const [qx,qy]=inTile();g.strokeStyle='rgba(243,204,144,.55)';g.lineWidth=1.2;g.beginPath();g.arc(qx,qy,4,0,Math.PI*1.6);g.stroke(); }
      } else if (moonspore) {
        for (let k = 0; k < (dirt ? 2 : 4); k++) { const [qx,qy]=inTile();g.fillStyle=k%3?'rgba(142,194,162,.24)':'rgba(208,250,166,.46)';g.beginPath();g.ellipse(qx,qy,2+r()*3,1+r()*2,0,0,6.283);g.fill(); }
        if (r()<.1) { const [qx,qy]=inTile();g.fillStyle='#c4f4af';g.beginPath();g.arc(qx,qy,1.5,0,6.283);g.fill(); }
      } else if (worldtree) {
        if(dirt){g.strokeStyle='rgba(83,58,39,.4)';g.lineWidth=2;g.beginPath();g.moveTo(px-12,py+7);g.lineTo(px+13,py+18);g.stroke();}
        else for(let k=0;k<4;k++){const [qx,qy]=inTile();g.fillStyle=k%2?'rgba(182,226,117,.32)':'rgba(37,121,77,.46)';g.beginPath();g.ellipse(qx,qy,4+r()*4,2+r()*3,r()*6.28,0,6.283);g.fill();}
        if(r()<.13){const [qx,qy]=inTile();g.fillStyle='#f9de8e';g.beginPath();g.arc(qx,qy,2.5,0,6.283);g.fill();}
      } else if (heartwood) {
        const ring=Math.hypot(x+0.5-48,y+0.5-48);g.strokeStyle=ring<33?'rgba(242,200,116,.43)':'rgba(83,51,37,.5)';g.lineWidth=1.5;g.beginPath();g.moveTo(px-13,py+13);g.quadraticCurveTo(px,py+6+ring%5,px+13,py+13);g.stroke();
        if(r()<.15){const [qx,qy]=inTile();g.fillStyle='#f9db8e';g.beginPath();g.arc(qx,qy,2,0,6.283);g.fill();}
      } else if (cairn) {
        for(let k=0;k<(dirt?4:6);k++){const [qx,qy]=inTile();g.fillStyle=dirt?'rgba(230,185,122,.4)':k%2?'rgba(197,191,173,.35)':'rgba(48,61,70,.42)';g.beginPath();g.ellipse(qx,qy,2+r()*4,1+r()*2,r()*6.28,0,6.283);g.fill();}
      } else if (frostwake) {
        for(let k=0;k<(dirt?2:4);k++){const [qx,qy]=inTile();g.fillStyle=dirt?'rgba(126,197,218,.33)':k%2?'rgba(246,255,255,.58)':'rgba(159,211,226,.30)';g.beginPath();g.ellipse(qx,qy,2+r()*5,1+r()*2,0,0,6.283);g.fill();}
        if(!dirt&&r()<.17){const [qx,qy]=inTile();g.strokeStyle='rgba(66,133,166,.32)';g.lineWidth=1;g.beginPath();g.moveTo(qx-8,qy+3);g.lineTo(qx,qy-3);g.lineTo(qx+7,qy+4);g.stroke();}
      } else if (lapis) {
        for(let k=0;k<(dirt?2:4);k++){const [qx,qy]=inTile();g.fillStyle=dirt?'rgba(255,238,193,.38)':k%3?'rgba(173,109,65,.27)':'rgba(248,218,150,.37)';g.beginPath();g.ellipse(qx,qy,3+r()*6,1+r()*2,0,0,6.283);g.fill();}
        if(!dirt&&r()<.22){const [qx,qy]=inTile();g.strokeStyle='rgba(252,225,160,.48)';g.lineWidth=1.3;g.beginPath();g.arc(qx,qy,5+r()*5,0,Math.PI*.9);g.stroke();}
      } else if (tanglecrown) {
        for(let k=0;k<(dirt?3:5);k++){const [qx,qy]=inTile();g.strokeStyle=dirt?'rgba(100,72,43,.3)':'rgba(24,101,66,.55)';g.lineWidth=1.5;g.beginPath();g.moveTo(qx,qy+3);g.lineTo(qx-2-r()*3,qy-4-r()*5);g.stroke();}
        if(!dirt&&r()<.26){const [qx,qy]=inTile();g.fillStyle=r()<.5?'#ff9cca':'#d9dc79';g.beginPath();g.ellipse(qx,qy-3,3+r()*3,2+r()*2,r()*6.28,0,6.283);g.fill();}
      } else if (ribbonwild) {
        for(let k=0;k<(dirt?2:3);k++){
          const [qx,qy]=inTile(),h=(k+Math.floor(r()*4))%4;
          g.fillStyle=['#fff4ba','#ef75a8','#6fd4d3','#b48ee8'][h];
          g.beginPath();g.ellipse(qx,qy,2+r()*2,1+r()*2,k*.7,0,6.283);g.fill();
        }
        if(!dirt&&x<49&&y>44&&y<97){for(let k=0;k<3;k++){const [qx,qy]=inTile();g.strokeStyle='rgba(44,116,50,.48)';g.lineWidth=1.4;g.beginPath();g.moveTo(qx,qy+2);g.lineTo(qx+(r()-.5)*6,qy-3-r()*5);g.stroke();}}
        if(!dirt&&r()<.11){const [qx,qy]=inTile();g.fillStyle='#fff0bd';g.beginPath();g.arc(qx,qy,2.3,0,6.283);g.fill();}
      } else if (sunward) {
        for (let k=0;k<(dirt?2:5);k++){const [qx,qy]=inTile(),h=3+r()*5;g.strokeStyle=dirt?'rgba(139,103,62,.27)':'rgba(31,105,37,.52)';g.lineWidth=1.4;g.beginPath();g.moveTo(qx,qy+2);g.lineTo(qx-2-r()*3,qy-h);g.moveTo(qx,qy+2);g.lineTo(qx+2+r()*3,qy-h*.75);g.stroke();}
        if(!dirt&&r()<.15){const [qx,qy]=inTile();g.fillStyle=r()<.5?'#f7ebbd':'#eab6cf';for(let p=0;p<5;p++){const a=p*6.283/5;g.beginPath();g.ellipse(qx+Math.cos(a)*3,qy-4+Math.sin(a)*2,2.2,1.6,0,0,6.283);g.fill();}g.fillStyle='#e6bb51';g.fillRect(qx-1,qy-5,2,2);}
      } else if (stormglass) {
        for (let k=0;k<(dirt?3:5);k++){const [qx,qy]=inTile();g.fillStyle=k%3?'rgba(150,204,212,.3)':'rgba(29,51,72,.55)';g.beginPath();g.ellipse(qx,qy,2+r()*5,1+r()*2,0,0,6.283);g.fill();}
        if(r()<.1){const [qx,qy]=inTile();g.strokeStyle='rgba(215,249,245,.68)';g.lineWidth=1.4;g.beginPath();g.moveTo(qx-6,qy+2);g.lineTo(qx,qy-3);g.lineTo(qx+6,qy+2);g.stroke();}
      } else if (prism) {
        for (let k = 0; k < (dirt ? 3 : 5); k++) { const [qx,qy] = inTile(); g.fillStyle = k%3 ? 'rgba(255,235,203,.42)' : 'rgba(110,91,118,.45)'; g.beginPath(); g.ellipse(qx,qy,2+r()*5,1+r()*2,0,0,6.283); g.fill(); }
        if (r() < .12) { const [qx,qy]=inTile(); g.strokeStyle='rgba(255,255,245,.6)'; g.lineWidth=1.4;g.beginPath();g.moveTo(qx-5,qy+2);g.lineTo(qx,qy-3);g.lineTo(qx+5,qy+2);g.stroke(); }
      } else if (astral) {
        if (dirt) {
          for (let k = 0; k < 4; k++) { const [qx, qy] = inTile(); g.fillStyle = k % 2 ? 'rgba(255,229,162,.26)' : 'rgba(27,42,56,.35)'; g.beginPath(); g.ellipse(qx, qy, 2 + r() * 4, 1 + r() * 2, 0, 0, 6.283); g.fill(); }
          if (r() < .18) { const [qx, qy] = inTile(); g.strokeStyle = 'rgba(171,230,245,.48)'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(qx - 5, qy); g.lineTo(qx, qy - 3); g.lineTo(qx + 5, qy); g.stroke(); }
        } else {
          for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(), h = 5 + r() * 8;
            g.strokeStyle = k === 0 ? '#174d49' : k === 1 ? '#62b78a' : '#a4d7ac'; g.lineWidth = k === 0 ? 2.4 : 1.6;
            g.beginPath(); g.moveTo(qx - 2, qy + 1); g.quadraticCurveTo(qx - 4, qy - h * .55, qx - 7, qy - h); g.moveTo(qx + 1, qy + 1); g.quadraticCurveTo(qx + 3, qy - h * .7, qx + 5, qy - h * 1.1); g.stroke();
          }
          if (r() < .12) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(41,100,112,.55)'; g.beginPath(); g.ellipse(qx, qy + 1, 6 + r() * 8, 2 + r() * 2, 0, 0, 6.283); g.fill(); }
          if (r() < .085) { const [qx, qy] = inTile(), petal = ['#d6b5ff','#ffb7d3','#b7f5e4'][Math.floor(r() * 3)];
            g.strokeStyle = '#3d8b72'; g.lineWidth = 1.3; g.beginPath(); g.moveTo(qx, qy); g.lineTo(qx, qy - 6); g.stroke();
            g.fillStyle = petal; for (let p = 0; p < 5; p++) { const a = p * 6.283 / 5; g.beginPath(); g.arc(qx + Math.cos(a) * 3, qy - 7 + Math.sin(a) * 2, 2.3, 0, 6.283); g.fill(); }
            g.fillStyle = '#ffdf8b'; g.fillRect(qx - 1, qy - 8, 2, 2);
          }
          if (r() < .045) { const [qx, qy] = inTile(); g.fillStyle = '#9cead9'; g.shadowColor = '#8ce6ea'; g.shadowBlur = 6; g.fillRect(qx, qy - 3, 2, 2); g.shadowBlur = 0; }
        }
      } else if (deep) {
        deepDetail(g, r, inTile, px, py, x, y, tone, dirt);
      } else if (wyrd) {
        wyrdDetail(g, r, inTile, px, py, x, y, tone, dirt);
      } else if (fen) {
        if (dirt) {                                                                    // boardwalk: planks across the tile
          for (const t of [.25, .5, .75]) { g.strokeStyle = 'rgba(20,12,6,.55)'; g.lineWidth = 1.6; g.beginPath(); g.moveTo(px + t * TW / 2, py + t * TH / 2); g.lineTo(px - TW / 2 + t * TW / 2, py + TH / 2 + t * TH / 2); g.stroke();
            g.strokeStyle = 'rgba(255,220,160,.16)'; g.lineWidth = 1; g.beginPath(); g.moveTo(px + t * TW / 2, py + t * TH / 2 + 1.6); g.lineTo(px - TW / 2 + t * TW / 2, py + TH / 2 + t * TH / 2 + 1.6); g.stroke(); }
          if (r() < .35) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(30,20,12,.7)'; g.fillRect(qx, qy, 1.6, 1.6); }
        } else {
          for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(); g.fillStyle = r() < .55 ? 'rgba(10,30,20,.28)' : 'rgba(150,190,90,.14)'; g.beginPath(); g.ellipse(qx, qy, 1.6 + r() * 4, 1 + r() * 1.6, 0, 0, 6.283); g.fill(); }
          if (r() < .05) {                                                              // a dark puddle with a glint
            const [qx, qy] = inTile(); g.fillStyle = 'rgba(14,34,40,.7)'; g.beginPath(); g.ellipse(qx, qy, 8 + r() * 5, 3.4 + r() * 2, 0, 0, 6.283); g.fill();
            g.fillStyle = 'rgba(170,220,230,.4)'; g.fillRect(qx - 3, qy - 1, 5, 1);
          } else if (r() < .07) { const [qx, qy] = inTile(); g.strokeStyle = '#44682e'; g.lineWidth = 1.6; g.lineCap = 'round'; g.beginPath(); g.moveTo(qx - 3, qy + 1); g.lineTo(qx - 4.5, qy - 7); g.moveTo(qx, qy + 1); g.lineTo(qx + .5, qy - 9); g.moveTo(qx + 3, qy + 1); g.lineTo(qx + 5, qy - 6); g.stroke(); }
          else if (r() < .03) { const [qx, qy] = inTile(); g.fillStyle = '#e9e2c8'; g.fillRect(qx - 1, qy - 4, 2, 4); g.fillStyle = '#5ee6d0'; g.shadowColor = '#5ee6d0'; g.shadowBlur = 6; g.beginPath(); g.ellipse(qx, qy - 5, 4, 2.6, 0, Math.PI, 0); g.fill(); g.shadowBlur = 0; }
          else if (r() < .03) { const [qx, qy] = inTile(); g.fillStyle = '#b9a8d8'; for (let k2 = 0; k2 < 3; k2++) g.fillRect(qx + k2 * 2 - 2, qy - 3 - (k2 % 2), 1.6, 1.6); }
        }
      } else if (frost) {
        for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(); g.fillStyle = r() < .55 ? 'rgba(90,140,190,.16)' : 'rgba(255,255,255,.5)'; g.beginPath(); g.ellipse(qx, qy, 1.5 + r() * 3.5, 1 + r() * 1.5, 0, 0, 6.283); g.fill(); }
        if (!dirt && r() < .08) {                                                     // a hairline crack in the ice crust
          const [qx, qy] = inTile(), a = r() * 6.283, l = 8 + r() * 10;
          g.strokeStyle = 'rgba(70,130,190,.55)'; g.lineWidth = 1.3; g.lineCap = 'round'; g.beginPath(); g.moveTo(qx, qy); g.lineTo(qx + Math.cos(a) * l, qy + Math.sin(a) * l * .5); g.lineTo(qx + Math.cos(a + .7) * l * 1.5, qy + Math.sin(a + .7) * l * .75); g.stroke();
        } else if (r() < .05) { const [qx, qy] = inTile(); g.fillStyle = '#8fa4bb'; g.strokeStyle = OL; g.lineWidth = 1.2; g.beginPath(); g.ellipse(qx, qy - 2, 3.4, 2.6, 0, 0, 6.283); g.fill(); g.stroke(); g.fillStyle = '#fff'; g.beginPath(); g.ellipse(qx, qy - 3.4, 3, 1.4, 0, 0, 6.283); g.fill(); }
        else if (r() < .06) { const [qx, qy] = inTile(); g.fillStyle = '#fff'; g.fillRect(qx - 1, qy - 4, 2, 2); g.fillRect(qx - 3, qy - 3, 6, 1); g.fillRect(qx - .5, qy - 6, 1, 6); }
      } else if (ember) {
        for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(); g.fillStyle = r() < .6 ? 'rgba(0,0,0,.28)' : 'rgba(200,170,150,.16)'; g.beginPath(); g.ellipse(qx, qy, 1.5 + r() * 3, 1 + r() * 1.4, 0, 0, 6.283); g.fill(); }
        if (!dirt && r() < .09) {                                                     // a glowing crack in the basalt
          const [qx, qy] = inTile(), a = r() * 6.283, l = 8 + r() * 9;
          g.strokeStyle = 'rgba(255,110,30,.75)'; g.lineWidth = 1.8; g.lineCap = 'round'; g.beginPath(); g.moveTo(qx, qy); g.lineTo(qx + Math.cos(a) * l, qy + Math.sin(a) * l * .5); g.lineTo(qx + Math.cos(a + .8) * l * 1.5, qy + Math.sin(a + .8) * l * .75); g.stroke();
          g.strokeStyle = 'rgba(255,210,100,.6)'; g.lineWidth = .8; g.beginPath(); g.moveTo(qx, qy); g.lineTo(qx + Math.cos(a) * l, qy + Math.sin(a) * l * .5); g.stroke();
        } else if (r() < .05) { const [qx, qy] = inTile(); g.fillStyle = '#3a363f'; g.strokeStyle = OL; g.lineWidth = 1.4; g.beginPath(); g.ellipse(qx, qy - 2, 4, 3, 0, 0, 6.283); g.fill(); g.stroke(); }
      } else if (dirt) {
        for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(); g.fillStyle = r() < .5 ? 'rgba(120,80,40,.35)' : 'rgba(255,225,170,.28)'; g.beginPath(); g.ellipse(qx, qy, 2 + r() * 3, 1.2 + r() * 1.5, 0, 0, 6.283); g.fill(); }
      } else {
        g.lineCap = 'round';
        const tufts = Math.floor(r() * 2.4);
        for (let k = 0; k < tufts; k++) {
          const [qx, qy] = inTile(), h = 5 + r() * 5; g.lineWidth = 1.8;
          g.strokeStyle = `hsl(${104 + tone * 14}, 52%, ${26 + tone * 8}%)`; g.beginPath(); g.moveTo(qx - 3, qy + 1); g.lineTo(qx - 4.5, qy - h); g.moveTo(qx + 3, qy + 1); g.lineTo(qx + 4.5, qy - h * .9); g.stroke();
          g.strokeStyle = `hsl(${98 + tone * 14}, 60%, ${46 + tone * 8}%)`; g.beginPath(); g.moveTo(qx, qy + 1); g.lineTo(qx - .5, qy - h * 1.25); g.stroke();
        }
        if (r() < .07) {                                                             // flowers
          const [qx, qy] = inTile(), col = ['#ffffff', '#ffe066', '#ff9ad5', '#9ad0ff'][Math.floor(r() * 4)];
          g.strokeStyle = '#2f7a3a'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(qx, qy + 2); g.lineTo(qx, qy - 5); g.stroke();
          g.fillStyle = col; for (let p = 0; p < 5; p++) { const a = p / 5 * 6.283; g.beginPath(); g.arc(qx + Math.cos(a) * 3, qy - 6 + Math.sin(a) * 2.4, 2.1, 0, 6.283); g.fill(); }
          g.fillStyle = '#f5b82e'; g.beginPath(); g.arc(qx, qy - 6, 1.6, 0, 6.283); g.fill();
        } else if (r() < .015) { const [qx, qy] = inTile(); g.fillStyle = '#fff'; g.beginPath(); g.ellipse(qx, qy - 3, 3, 3.6, 0, 0, 6.283); g.fill(); g.fillStyle = '#e8484e'; g.beginPath(); g.ellipse(qx, qy - 5, 5, 3.4, 0, Math.PI, 0); g.fill(); }
      }
      if (!vault && !moonwell) City.stoneTile(g, px, py, x, y);
      // earth cliff on the two front edges of the island
      const depth = sky ? CLIFF - 40 + hash2(x, y, 9) * 36 : CLIFF - 34 + hash2(x, y, 9) * 26;
      const face = (dir) => {
        const vx = px + dir * TW / 2, vy = py + TH / 2, bx = px, by = py + TH;
        const gr = g.createLinearGradient(0, vy, 0, vy + depth);
        if (city) { gr.addColorStop(0, dir > 0 ? '#cdb48a' : '#b79c74'); gr.addColorStop(1, dir > 0 ? '#7a6044' : '#65503a'); }
        else if (moonwell) { gr.addColorStop(0,dirt?'#def4ea':'#9acfc8');gr.addColorStop(.45,dirt?'#78b6be':'#3b8591');gr.addColorStop(1,'#153d58'); }
        else if (sky) { gr.addColorStop(0, dir > 0 ? '#c3cbe6' : '#a9b3d6'); gr.addColorStop(.45, dir > 0 ? '#7a84ae' : '#6a7399'); gr.addColorStop(1, dir > 0 ? '#2c3156' : '#23284a'); }
        else if (deep) { gr.addColorStop(0, dir > 0 ? '#1a4a5e' : '#143c4e'); gr.addColorStop(1, dir > 0 ? '#06161f' : '#04101a'); }
        else if (wyrd) { gr.addColorStop(0, dir > 0 ? '#6a4a2e' : '#583a22'); gr.addColorStop(1, dir > 0 ? '#2e2016' : '#241a12'); }
        else if (fen) { gr.addColorStop(0, dir > 0 ? '#5a4c38' : '#4a3e2e'); gr.addColorStop(1, dir > 0 ? '#2a2218' : '#201a12'); }
        else if (frost) { gr.addColorStop(0, dir > 0 ? '#a9d3ee' : '#8fbddb'); gr.addColorStop(1, dir > 0 ? '#2f5a82' : '#274b70'); }
        else if (ember) { gr.addColorStop(0, dir > 0 ? '#4a3430' : '#3c2a28'); gr.addColorStop(1, dir > 0 ? '#1e1416' : '#181012'); }
        else { gr.addColorStop(0, dir > 0 ? '#7a5433' : '#684528'); gr.addColorStop(1, dir > 0 ? '#3d2a1c' : '#33221a'); }
        g.fillStyle = gr; g.beginPath(); g.moveTo(vx, vy); g.lineTo(bx, by); g.lineTo(bx, by + depth * (.85 + hash2(x + 3, y, 4) * .3)); g.lineTo(vx, vy + depth); g.closePath(); g.fill();
        g.strokeStyle = 'rgba(0,0,0,.18)'; g.lineWidth = 2; for (let k = 1; k < 4; k++) { g.beginPath(); g.moveTo(vx, vy + depth * k / 4); g.lineTo(bx, by + depth * k / 4 * .9); g.stroke(); }
        g.strokeStyle = moonwell ? (dirt ? '#fff3cf' : '#d4f8ec') : sky ? '#f4fbff' : deep ? '#2a6a7a' : city ? '#5faa44' : wyrd ? '#b8742a' : fen ? '#4f7a36' : frost ? '#eaf7ff' : ember ? '#8a3a1c' : '#3f8a3c'; g.lineWidth = 5; g.beginPath(); g.moveTo(vx, vy + 1); g.lineTo(bx, by + 1); g.stroke();
        if (ember) { g.strokeStyle = 'rgba(255,120,40,.55)'; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + 3); g.lineTo(bx, by + 3); g.stroke(); }
        g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + depth); g.lineTo(bx, by + depth * .9); g.stroke();
      };
      if (sky || moonwell) { if (isVoid(x + 1, y)) face(1); if (isVoid(x, y + 1)) face(-1); }
      else { if (!vault && x === MAP - 1) face(1); if (!vault && y === MAP - 1) face(-1); }
    }
    return { c, G };
  }
  function getChunk(cx, cy) {
    const k = cy * 100 + cx; let ch = chunks.get(k);
    if (!ch) { ch = renderChunk(cx, cy); if (chunks.size > 30) chunks.delete(chunks.keys().next().value); }
    else chunks.delete(k);
    chunks.set(k, ch); return ch;
  }

  // ---------- state ----------
  let cv, ctx, mini, mctx, opts, onHud = () => {}, onEvent = () => {};
  let running = false, paused = false, raf = 0, last = 0, zoom = 1, dpr = 1, cssW = 1600, cssH = 900, miniBase = null;
  let hero, slimes, drops, chests, signs = [], floaters, parts, effects, bolts, marker, cam, shake, keys, pointer, msg, hudT, tAll;
  const BAG_COLORS = ['#a78257','#78996f','#6396b3','#a478b2','#c38a5e','#719ba1','#9b86c3','#be9292','#d3ae68','#dfcde7'];
  const bagColor = item => BAG_COLORS[Math.max(0, Math.min(9, Math.floor((item.requiredLevel || 1) / 10)))];
  let ebolts = [], instanceCleared = false, clearedAt = -99;   // missiles shot by ranged enemies; the dungeon's exit opens when its last boss falls
  let mageSpr = null, spriteGeneration = 0;
  let pendingNpc = null, pendingChest = null, cityRoute = [], routeTime = 0;
  // Speech bubbles over characters that just chatted: id -> {text, until, lines}.
  const bubbles = new Map();
  let bubblesDrawn = 0, bubblesLast = 0;
  let remotePlayers = new Map(), onCharacter = () => {}, inputT = 0, lastLook = '';
  const isMage = () => hero?.look?.class === 'mage';
  const isAssassin = () => hero?.look?.class === 'assassin';
  const isPriest = () => hero?.look?.class === 'priest';
  const isHunter = () => hero?.look?.class === 'hunter';
  const isModular = () => ['warrior', 'mage', 'assassin', 'priest', 'hunter'].includes(hero?.look?.class || 'warrior');
  const characterClass = () => isMage() ? MageSprite : isAssassin() ? AssassinSprite : isPriest() ? PriestSprite : isHunter() ? HunterSprite : WarriorSprite;
  const mageGear = () => MageSprite.equipment(hero.look);
  const equipmentStats = () => {
    if (Number.isFinite(hero.attack) && Number.isFinite(hero.defense)) return { attack: hero.attack, defense: hero.defense };
    if (!isModular()) return { attack: 22 + hero.level * 4, defense: 0 };
    const C = characterClass(), gear = C.equipment(hero.look);
    const usable = i => i && (i.requiredLevel || 1) <= hero.level;   // gear above the hero's level adds nothing
    const item = (kind, variant) => WORLD_ITEMS.find(i => i.class === hero.look.class && i.kind === kind && i.variant === variant);
    const worn = [...Object.values(hero.equipment || {}).map(id => WORLD_ITEMS.find(i => i.id === id)), item('armor', gear.armor), item('weapon', gear.weapon)].filter(usable);
    return { attack: worn.reduce((sum, i) => sum + (i.attack || 0), 0) + (isAssassin() ? 18 : isHunter() ? 19 : isMage() || isPriest() ? 20 : 22) + hero.level * 4, defense: worn.reduce((sum, i) => sum + (i.defense || 0), 0) };
  };

  // Looks only: the server owns health, damage, speed, XP and level. `scale` is the drawn size, `top` the sprite
  // height above the feet in sprite pixels (where the health bar sits).
  const SLIME = {
    green: { name: 'Green Slime', hp: 60, dmg: 8, speed: 1.9, scale: 1, xp: 12, col: ['#a4f59a', '#4fd25f', '#1f8a3c'] },
    blue: { name: 'Blue Slime', hp: 80, dmg: 10, speed: 2.4, scale: 1.05, xp: 16, col: ['#a8e4ff', '#4aa8ff', '#2160b8'] },
    pink: { name: 'Pink Slime', hp: 70, dmg: 9, speed: 2.1, scale: 1, xp: 15, col: ['#ffc4e6', '#ff7bbd', '#c23f86'] },
    yellow: { name: 'Golden Slime', hp: 90, dmg: 11, speed: 2.2, scale: 1.05, xp: 20, col: ['#fff2a0', '#ffd23f', '#c98a10'] },
    big: { name: 'King Slime', hp: 600, dmg: 30, speed: 2.2, scale: 1.75, xp: 75, col: ['#c8b5ff', '#8f6bff', '#4a2fb0'] },
    beetle: { name: 'Ironhide Beetle', hp: 240, dmg: 22, speed: 2.8, scale: 1.3, xp: 32, col: ['#8aafbf', '#58758a', '#324658'] },
    wisp: { name: 'Cinder Wisp', scale: .95, top: 66, col: ['#fff4b8', '#ee6a1c', '#b8331f'] },
    spider: { name: 'Magma Spider', scale: 1.05, top: 66, col: ['#7d6f80', '#3d3544', '#27222d'] },
    wraith: { name: 'Ash Wraith', scale: 1, top: 88, col: ['#746b8e', '#383250', '#15121d'] },
    golem: { name: 'Basalt Golem', scale: 1.2, top: 86, col: ['#9a939a', '#544f58', '#24212a'] },
    cinderlord: { name: 'Cinderlord', elite: true, scale: 1.55, top: 90, col: ['#ffe095', '#e96d25', '#392c32'] },
    crab: { name: 'Rime Crab', scale: 1.1, top: 53, col: ['#d8f2ff', '#6fb3dc', '#2d5f8a'] },
    wolf: { name: 'Frostfang Wolf', scale: 1.1, top: 67, col: ['#f2f6fa', '#9fb4c8', '#4a5d74'] },
    yeti: { name: 'Glacier Yeti', scale: 1.2, top: 85, col: ['#f4f8fc', '#b9cbdc', '#5e7690'] },
    wyrm: { name: 'Rime Wyrm', scale: 1.2, top: 88, col: ['#e4fbff', '#6bc6e8', '#256496'] },
    toad: { name: 'Fen Toad', scale: 1.2, top: 46, col: ['#c3e86b', '#62952f', '#27401a'] },
    croc: { name: 'Mire Crocodile', scale: 1.25, top: 32, col: ['#b3c76a', '#5b7433', '#26331f'] },
    knight: { name: 'Drowned Knight', scale: 1.15, top: 87, col: ['#cde8d4', '#6a8d7a', '#2d403c'] },
    hydra: { name: 'Mire Hydra', scale: 1.3, top: 70, col: ['#b0d6a0', '#4b7a74', '#233040'] },
    gloomroot: { name: 'Gloomroot Colossus', elite: true, scale: 1.8, top: 85, col: ['#8affd8', '#57412a', '#12100c'] },
    thrall: { elite: true, name: 'Vault Thrall', scale: .95, top: 72, col: ['#d8d2bc', '#8a8470', '#2c2a34'] },
    archer: { elite: true, name: 'Bone Archer', scale: .95, top: 76, col: ['#e6dfc4', '#9a9278', '#35303c'] },
    acolyte: { elite: true, name: 'Hollow Acolyte', scale: .95, top: 79, col: ['#c9a8ff', '#6a3fb0', '#1f1236'] },
    gatewarden: { name: 'Hrolf Bonegate', elite: true, boss: true, scale: 1.35, top: 84, col: ['#e2dcc6', '#7a8aa4', '#2a2c3c'] },
    choir: { name: 'Valka, the Hollow Choir', elite: true, boss: true, scale: 1.35, top: 87, col: ['#bdeaff', '#4a78c0', '#161c3a'] },
    colossus: { name: 'Ironwake, the Vault Colossus', elite: true, boss: true, scale: 1.4, top: 89, col: ['#9fe8ff', '#5a6074', '#20222e'] },
    hollowking: { name: 'Haldor, the Hollow King', elite: true, boss: true, scale: 1.4, top: 85, col: ['#c8ffc0', '#4a6a52', '#101a14'] },
    boar: { name: 'Rotfang Boar', scale: 1.3, top: 53, col: ['#b8977a', '#6f5340', '#33261d'] },
    crow: { name: 'Gallowcrow', scale: 1.15, top: 64, col: ['#9a84d6', '#444768', '#0d0c14'] },
    troll: { name: 'Mosshide Troll', scale: 1.5, top: 77, col: ['#98b48a', '#48634e', '#1c2620'] },
    weaver: { name: 'Wyrdweaver', scale: 1.2, top: 74, col: ['#ffd25a', '#5a41a0', '#150f28'] },
    ram: { name: 'Stormram', scale: 1.35, top: 49, col: ['#b8f0ff', '#68799b', '#252c3d'] },
    oakhorn: { name: 'Oakhorn', elite: true, scale: 1.7, top: 77, col: ['#e87a1e', '#975a34', '#2a1810'] },
    hrungnir: { name: 'Hrungnir', elite: true, scale: 1.9, top: 75, col: ['#b8f0ff', '#4a5676', '#1b2030'] },
    galehound: { name: 'Galehound', scale: 1.3, top: 58, col: ['#e4f0ff', '#7088b0', '#2a3550'] },
    prismgolem: { name: 'Prism Golem', scale: 1.6, top: 78, col: ['#d4e0fa', '#7a80c8', '#2a2a5e'] },
    skyray: { name: 'Skyray', scale: 1.55, top: 62, col: ['#8ea6dc', '#3e4c82', '#161c34'] },
    einherjar: { name: 'Hollow Einherjar', scale: 1.3, top: 66, col: ['#a8f0ff', '#6a7486', '#1a1e26'] },
    thunderroc: { name: 'Thunderroc', scale: 1.6, top: 81, col: ['#f6faff', '#a86e34', '#26304c'] },
    draugr: { name: 'Drowned Draugr', scale: 1.4, top: 62, col: ['#9ac8c0', '#456a70', '#14242e'] },
    angler: { name: 'Lantern Angler', scale: 1.3, top: 60, col: ['#9ffff0', '#2f5a78', '#0c1c2e'] },
    moray: { name: 'Gnashing Moray', scale: 1.55, top: 51, col: ['#d8e888', '#5a7a3a', '#1c2a16'] },
    siren: { name: 'Siren', scale: 1.25, top: 73, col: ['#ffb0f0', '#7a4aa0', '#1e1230'] },
    shellback: { name: 'Shellback', scale: 1.95, top: 57, col: ['#b8d8a0', '#4a6a54', '#16241c'] },
    kraken: { name: 'The Kraken', elite: true, scale: 2.5, top: 69, col: ['#c8a0f0', '#5a3a8a', '#150c28'] },
    hvitserk: { name: 'Hvitserk the Drowned', elite: true, scale: 1.8, top: 69, col: ['#8cb4c0', '#1c2c4a', '#0c1426'] },
    ghostmaw: { name: 'Ghostmaw', elite: true, scale: 2.2, top: 51, col: ['#ecf8fc', '#8099a8', '#26323c'] },
    voidmoth: { name: 'Void Moth', scale: 1.25, top: 55, col: ['#c7a8ff', '#5e43a6', '#120d2e'] },
    crystalwyrm: { name: 'Crystalwyrm', scale: 1.45, top: 58, col: ['#6de8ff', '#167caa', '#071b2c'] },
    orbitbeetle: { name: 'Orbit Beetle', scale: 1.55, top: 61, col: ['#f4a43a', '#9b4e20', '#24120a'] },
    eclipsedryad: { name: 'Eclipse Dryad', scale: 1.5, top: 66, col: ['#9ed17a', '#37694d', '#101c18'] },
    meteorgolem: { name: 'Meteor Golem', scale: 1.95, top: 72, col: ['#b39bd1', '#554c70', '#17131f'] },
    miragejackal: { name: 'Mirage Jackal', scale: 1.35, top: 74, col: ['#e7b990','#8c5fa0','#332744'] },
    shardscarab: { name: 'Shard Scarab', scale: 1.55, top: 62, col: ['#99e6dc','#377b8b','#192c3b'] },
    glassharrier: { name: 'Glass Harrier', scale: 1.4, top: 70, col: ['#d5c5ff','#8771bf','#30254d'] },
    prismsentinel: { name: 'Prism Sentinel', scale: 1.85, top: 82, col: ['#d5e9ed','#778ba6','#30344e'] },
    mirrorqueen: { name: 'The Mirror Queen', elite: true, scale: 2.0, top: 85, col: ['#e7b8ff','#814c9d','#2a173f'] },
    sunshard: { name: 'The Sunshard', elite: true, scale: 2.4, top: 87, col: ['#ffd58a','#c0724c','#402828'] },
    bronzemantis: { name: 'Bronze Mantis', scale: 1.45, top: 69, col: ['#c8a66b','#846548','#2b252a'] },
    gearling: { name: 'Gearling', scale: 1.35, top: 64, col: ['#9bc2be','#587886','#202739'] },
    orbitseer: { name: 'Orbit Seer', scale: 1.45, top: 72, col: ['#a3dce4','#53708d','#202c46'] },
    chronoguard: { name: 'Chronoguard', scale: 1.95, top: 84, col: ['#b4a7ba','#665d77','#272536'] },
    pendulummatron: { name: 'The Pendulum Matron', elite: true, scale: 2.15, top: 88, col: ['#e1b5a9','#89617f','#2f213b'] },
    epochengine: { name: 'The Epoch Engine', elite: true, scale: 2.6, top: 90, col: ['#dab47d','#86634f','#282033'] },
    glowcapgrazer: { name: 'Glowcap Grazer', scale: 1.45, top: 69, col: ['#bbffae','#638c71','#203333'] },
    silkwing: { name: 'Silkwing', scale: 1.35, top: 70, col: ['#c7f8ee','#768f9a','#263342'] },
    rootlurker: { name: 'Rootlurker', scale: 1.8, top: 82, col: ['#c9ae83','#705e56','#292c36'] },
    lanternwraith: { name: 'Lantern Wraith', scale: 1.5, top: 80, col: ['#b8ffa5','#66618a','#272d46'] },
    mireheart: { name: 'The Mireheart', elite: true, scale: 2.25, top: 89, col: ['#efb9ba','#536b57','#2b3430'] },
    silverwidow: { name: 'The Silver Widow', elite: true, scale: 2.1, top: 84, col: ['#e9b9ff','#77758d','#2d2d43'] },
    nightbloom: { name: 'The Nightbloom', elite: true, scale: 2.65, top: 91, col: ['#eafca1','#a878a3','#252b43'] },
    dew_moth: { name: 'Dew Moth', scale: 1.45, top: 72, col: ['#a8d5cf','#8276b5','#15263b'] },
    lumen_eel: { name: 'Lumen Eel', scale: 1.55, top: 76, col: ['#9af2d7','#367d91','#15263b'] },
    rootbell: { name: 'Rootbell', scale: 1.75, top: 83, col: ['#f8e8ad','#a8d5cf','#15263b'] },
    tideglass_heron: { name: 'The Tideglass Heron', elite: true, boss: true, scale: 1.9, top: 92, col: ['#a8d5cf','#367d91','#15263b'] },
    hourpetal_stag: { name: 'The Hourpetal Stag', elite: true, boss: true, scale: 2.0, top: 94, col: ['#f8e8ad','#8276b5','#15263b'] },
    moonskein_weaver: { name: 'The Moonskein Weaver', elite: true, boss: true, scale: 2.1, top: 96, col: ['#f0a6be','#8276b5','#15263b'] },
    moonwell_echo: { name: 'The Moonwell Echo', elite: true, boss: true, scale: 2.0, top: 91, col: ['#91f6e2','#7796ae','#1c2141'] },
    saltclaw: { name: 'Saltclaw', scale: 1.5, top: 66, col: ['#d5e6d6','#77aeb3','#15252f'] },
    stormgull: { name: 'Stormgull', scale: 1.45, top: 86, col: ['#f2f1db','#adc8cc','#1c2940'] },
    glassray: { name: 'Glassray', scale: 1.6, top: 73, col: ['#b7eee5','#5fa6b5','#17263d'] },
    breakersentinel: { name: 'Breaker Sentinel', scale: 1.9, top: 91, col: ['#d3d3c4','#8298a0','#192431'] },
    maelstromheart: { name: 'The Maelstrom Heart', elite: true, scale: 2.7, top: 94, col: ['#f3efff','#697fa5','#171b38'] },
    meadowhare: { name: 'Meadow Hare', scale: 1.45, top: 74, col: ['#eed4a1','#c99b69','#342e33'] },
    sunbacksnail: { name: 'Sunback Snail', scale: 1.45, top: 73, col: ['#f2ebbd','#a0b579','#333442'] },
    brushfox: { name: 'Brush Fox', scale: 1.8, top: 73, col: ['#fff0c8','#d57b49','#3d3035'] },
    spadebadger: { name: 'Spadeclaw Badger', scale: 1.9, top: 77, col: ['#e7e1c8','#969b8b','#2d3440'] },
    honeyjaw: { name: 'Old Honeyjaw', elite: true, scale: 2.65, top: 91, col: ['#ffe497','#926c45','#2e2730'] },
    wickerwarden: { name: 'The Wicker Warden', elite: true, scale: 2.8, top: 92, col: ['#fce3a2','#a98454','#312f35'] },
    ribbongecko: { name: 'Ribbon Gecko', scale: 1.65, top: 76, col: ['#31c7bd','#237d9b','#263850'] },
    balloonbeetle: { name: 'Balloon Beetle', scale: 1.8, top: 87, col: ['#e7a2f3','#b277db','#3d3158'] },
    paintedmacaw: { name: 'Painted Macaw', scale: 1.75, top: 88, col: ['#f3d75d','#52bbdf','#303453'] },
    jesterling: { name: 'Jesterling', scale: 1.7, top: 83, col: ['#f4bf78','#d36ab3','#423052'] },
    paradegryphon: { name: 'The Parade Gryphon', elite: true, scale: 2.7, top: 93, col: ['#f7bb72','#bc7cba','#383548'] },
    maskcolossus: { name: 'The Masquerade Colossus', elite: true, scale: 3.0, top: 94, col: ['#f5d48a','#ae94dc','#34324d'] },
    orchidmantis: { name: 'Orchid Mantis', scale: 1.8, top: 91, col: ['#d5ef83','#80c76c','#263d39'] },
    canopyglider: { name: 'Canopy Glider', scale: 1.85, top: 91, col: ['#c9e5a4','#59c0b5','#263d55'] },
    poolcaiman: { name: 'Blackwater Caiman', scale: 2.0, top: 79, col: ['#b9d5a1','#6ea58c','#283f37'] },
    drumgorilla: { name: 'Drum Gorilla', scale: 2.0, top: 92, col: ['#c69a70','#9d6e5d','#3b3540'] },
    jadeanaconda: { name: 'The Jade Anaconda', elite: true, scale: 2.85, top: 94, col: ['#a9e3a6','#4dc098','#253c40'] },
    crownjaguar: { name: 'The Crown Jaguar', elite: true, scale: 3.1, top: 94, col: ['#f1ce73','#ce9852','#343d39'] },
    sapbeetle: { name: 'Sap Beetle', scale: 1.7, top: 91, col: ['#e3ae59','#a6713c','#302f36'] },
    lanternhornet: { name: 'Lantern Hornet', scale: 1.65, top: 91, col: ['#d7cf74','#7da869','#283947'] },
    mosslemur: { name: 'Moss Lemur', scale: 1.7, top: 91, col: ['#c8d68a','#82a872','#263f3b'] },
    barkmimic: { name: 'Bark Mimic', scale: 2.0, top: 93, col: ['#c5a479','#8b7758','#253b40'] },
    sandhopper: { name: 'Sandhopper', scale: 1.8, top: 91, col: ['#edca82','#ca9958','#514039'] },
    dunefennec: { name: 'Dune Fennec', scale: 1.8, top: 91, col: ['#f4d5a3','#d6a278','#493c3b'] },
    glassscorpion: { name: 'Glass Scorpion', scale: 1.85, top: 91, col: ['#c7e7df','#71bed0','#263f52'] },
    sunvulture: { name: 'Sun Vulture', scale: 1.85, top: 91, col: ['#ecd5a1','#c69b76','#4a3947'] },
    dunecolossus: { name: 'The Dune Colossus', elite: true, scale: 3.0, top: 94, col: ['#ecd1a0','#d2a274','#55434d'] },
    mirageroc: { name: 'The Mirage Roc', elite: true, scale: 3.25, top: 94, col: ['#e9dfbb','#8dc3c6','#30485b'] },
    snowhare: { name: 'Snow Hare', scale: 1.8, top: 91, col: ['#f0f8ed','#c8dce4','#33465e'] },
    iceotter: { name: 'Ice Otter', scale: 1.8, top: 91, col: ['#c9ecf0','#86b3c5','#263d57'] },
    frostheron: { name: 'Frost Heron', scale: 1.85, top: 91, col: ['#f5faf5','#b4d7e0','#31435d'] },
    glaciercrab: { name: 'Glacier Crab', scale: 1.85, top: 91, col: ['#b7e6ec','#66b4d0','#213b60'] },
    bellmammoth: { name: 'The Bell Mammoth', elite: true, scale: 3.1, top: 94, col: ['#e7efeb','#afc8d5','#34445f'] },
    auroramanta: { name: 'The Aurora Manta', elite: true, scale: 3.2, top: 94, col: ['#acf1cf','#68bcb8','#243c61'] },
    crevasseleviathan: { name: 'The Crevasse Leviathan', elite: true, scale: 3.45, top: 94, col: ['#8dd2dc','#498eb2','#132d55'] },
    screeferret: { name: 'Scree Ferret', scale: 1.8, top: 91, col: ['#d2c0a0','#9d8c73','#312d3d'] },
    stoneibex: { name: 'Stone Ibex', scale: 1.9, top: 91, col: ['#dbcaa5','#978d75','#2c3339'] },
    slateraven: { name: 'Slate Raven', scale: 1.85, top: 91, col: ['#a8adbb','#657488','#1e2936'] },
    ridgeadder: { name: 'Ridge Adder', scale: 1.85, top: 91, col: ['#d0bd80','#8ca085','#2b3034'] },
    cairnbehemoth: { name: 'The Cairn Behemoth', elite: true, scale: 3.2, top: 94, col: ['#b8aa8d','#828178','#292c36'] },
    whitebarktitan: { name: 'The Whitebark Titan', elite: true, scale: 3.4, top: 94, col: ['#e5dfc8','#aaa79a','#32343a'] },
    stormcondor: { name: 'The Storm Condor', elite: true, scale: 3.5, top: 94, col: ['#c8c4af','#7b8b8c','#232c43'] },
  };
  for (const [kind,name,col,elite] of [
    ['brooknewt','Brook Newt','#7ac6ae'],['sundarter','Sun Darter','#f6ce60'],['acornmimic','Acorn Mimic','#c17b48'],['snowstoat','Snow Stoat','#d6f3f6'],
    ['bloomtortoise','Bloom Tortoise','#9bd579',true],['petalchimera','Petal Chimera','#ec91c2',true],['rainseraph','Rain Seraph','#8dd9dc',true],
    ['glasslion','Glass Lion','#ffc06d',true],['sunwheel','Sunwheel','#ffe67d',true],['firephoenix','Fire Phoenix','#f18c58',true],
    ['lanternowl','Lantern Owl','#e5a76e',true],['harvestreaper','Harvest Reaper','#ac6c4b',true],['ambermantis','Amber Mantis','#f2b861',true],
    ['rimesaber','Rime Saber','#a4d9ed',true],['snowgiant','Snow Giant','#d8eff7',true],['longnightwyrm','Longnight Wyrm','#9abbd9',true]
  ]) SLIME[kind]={name,elite,scale:elite?3.1:1.8,top:91,col:[col,col,'#2b424b']};
  const CATHEDRAL_KINDS = CATHEDRAL_ENEMIES.map(e => e.kind);
  for (const e of CATHEDRAL_ENEMIES) SLIME[e.kind] = { name:e.name, elite:true, boss:e.boss, scale:e.stats[3] * .72, top:82, col:[e.color,e.color,'#152431'] };
  if (window.Locale?.language === 'sv') for (const d of Object.values(SLIME)) d.name = Locale.translate(d.name); // nameplates, log lines and the boss bar read these
  const CRAG_KINDS = ['wisp', 'spider', 'wraith', 'golem', 'cinderlord'], RIME_KINDS = ['crab', 'wolf', 'yeti', 'wyrm'], FEN_KINDS = ['toad', 'croc', 'knight', 'hydra', 'gloomroot'];
  const WYRD_KINDS = ['boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir'], SKY_KINDS = ['galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc'], DEEP_KINDS = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw'], ASTRAL_KINDS = ['voidmoth', 'crystalwyrm', 'orbitbeetle', 'eclipsedryad', 'meteorgolem'], PRISM_KINDS = ['miragejackal','shardscarab','glassharrier','prismsentinel','mirrorqueen','sunshard'], ORRERY_KINDS = ['bronzemantis','gearling','orbitseer','chronoguard','pendulummatron','epochengine'];
  const MOONSPORE_KINDS = ['glowcapgrazer','silkwing','rootlurker','lanternwraith','mireheart','silverwidow','nightbloom'];
  const STORMGLASS_KINDS = ['saltclaw','stormgull','glassray','breakersentinel','maelstromheart'];
  const SUNWARD_KINDS = ['meadowhare','sunbacksnail','brushfox','spadebadger','honeyjaw','wickerwarden'];
  const RIBBONWILD_KINDS = ['ribbongecko','balloonbeetle','paintedmacaw','jesterling','paradegryphon','maskcolossus'];
  const TANGLECROWN_KINDS = ['orchidmantis','canopyglider','poolcaiman','drumgorilla','jadeanaconda','crownjaguar'];
  const WORLDHEART_KINDS = ['sapbeetle','lanternhornet','mosslemur','barkmimic'];
  const LAPIS_KINDS = ['sandhopper','dunefennec','glassscorpion','sunvulture','dunecolossus','mirageroc'];
  const YEAR_KINDS = ['brooknewt','sundarter','acornmimic','snowstoat','bloomtortoise','petalchimera','rainseraph','glasslion','sunwheel','firephoenix','lanternowl','harvestreaper','ambermantis','rimesaber','snowgiant','longnightwyrm'];
  const CAIRN_KINDS = ['screeferret','stoneibex','slateraven','ridgeadder','cairnbehemoth','whitebarktitan','stormcondor'];
  const FROSTWAKE_KINDS = ['snowhare','iceotter','frostheron','glaciercrab','bellmammoth','auroramanta','crevasseleviathan'];
  const MOONWELL_KINDS = ['dew_moth','lumen_eel','rootbell','tideglass_heron','hourpetal_stag','moonskein_weaver'];
  const VAULT_KINDS = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking'], BOSS_KINDS = [...VAULT_KINDS.slice(3), 'tideglass_heron','hourpetal_stag','moonskein_weaver','moonwell_echo', ...CATHEDRAL_ENEMIES.filter(e => e.boss).map(e => e.kind)];
  // Colour a level label by how it compares with the hero: grey, normal, orange, red.
  const levelColor = level => { const d = level - (hero?.level || 1); return d >= 5 ? '#ff6b6b' : d >= 3 ? '#ffa65a' : d <= -5 ? '#9fb0a0' : '#fff4ca'; };
  function newHero() {
    return { x: SPAWN.x, y: SPAWN.y, r: .3, hp: 120, maxHp: 120, level: 1, xp: 0, gold: 0, kills: 0, fx: 1, fy: 1, moving: false, walk: 0, atkT: 0, atkCd: 0, atkHit: false, hurtT: 0, lastHurt: -99, dead: false, deadT: 0, target: null, goal: null, vx: 0, vy: 0, roar: 0, dashT: 0, dashCd: 0, dashX: 0, dashY: 0, dashTrail: 0 };
  }
  function reset() {
    pendingNpc = null; pendingChest = null; cityRoute = [];
    window.Quests?.reset(); window.WorldMap?.reset(); explored = [];
    hero = newHero(); drops = []; chests = []; signs = []; floaters = []; parts = []; effects = []; bolts = []; marker = null; shake = 0; msg = null; hudT = 0; tAll = 0;
    keys = new Set(); pointer = { down: false, x: 0, y: 0 };
    cam = { x: hero.x, y: hero.y };
    slimes = []; emitHud(true);
  }
  const hubs = () => [zdef.city, ...(zdef.camps || [])].filter(Boolean);
  const hubAt = (x, y) => hubs().find(c => x >= c.x0 && x <= c.x1 && y >= c.y0 && y <= c.y1);
  const campNear = () => hubs().reduce((a, c) => !a || Math.hypot(hero.x - c.plaza.x, hero.y - c.plaza.y) < Math.hypot(hero.x - a.plaza.x, hero.y - a.plaza.y) ? c : a, null);
  function emitHud(force) { const rival = remotePlayers.get(hero.pvpTargetId); onHud({ hp: hero.hp, maxHp: hero.maxHp, resource: hero.resource, maxResource: hero.maxResource, resourceType: hero.resourceType, xp: hero.xp, xpNeed: hero.xpNeed || 100, level: hero.level, gold: hero.gold, kills: hero.kills, target: rival && !rival.dead ? { id: rival.id, player: true, name: rival.look?.name || 'Player', level: rival.level, hp: rival.hp, maxHp: rival.maxHp } : hero.target && !hero.target.dead ? { id: hero.target.id, kind: hero.target.kind, name: hero.target.d.name, level: hero.target.level, hp: hero.target.hp, maxHp: hero.target.maxHp } : null, msg, area: zone > 0 ? zdef.name : City.inside(hero.x, hero.y) ? WORLD_MAP.city.name : 'Greenmeadow', zone, camp: campNear()?.name, tagline: zdef.tagline, hub: hubAt(hero.x, hero.y)?.name ?? null, levels: zdef.levels, players: zdef.players, buffs: hero.buffs || [], sparkTravel:hero.sparkTravel, traveling: cityRoute.length > 0 && !pendingNpc, mounted:hero.mounted, mountOwned:hero.mountOwned, mount:hero.mount, inCombat:hero.inCombat }); }

  // ---------- coordinates ----------
  const camS = () => { const [x, y] = w2sRaw(cam.x, cam.y); return [Math.round(x), Math.round(y)]; };   // whole pixels: fractional offsets make big blits resample (slow)
  // The on-screen unit direction of a world direction: the ground is isometric, so a world step (fx, fy) is not drawn as (fx, fy).
  function projDir(fx, fy) { const [x, y] = w2sRaw(fx, fy), n = Math.hypot(x, y) || 1; return [x / n, y / n]; }
  function w2s(x, y, z = 0) { const [cx, cy] = camS(), [sx, sy] = w2sRaw(x, y); return [sx - cx + VW / 2 + Math.round(shakeX), sy - cy + VH / 2 + Math.round(shakeY) - z]; }
  function visibleCombatCue(x, y) {
    if (Math.hypot(x-hero.x,y-hero.y) >= 15) return false;
    const [sx,sy] = w2s(x,y);
    return sx >= -40 && sy >= -90 && sx <= VW+40 && sy <= VH+40;
  }
  function s2w(sx, sy) { const [cx, cy] = camS(), rx = sx - VW / 2 + cx, ry = sy - VH / 2 + cy; return [rx / TW + ry / TH, ry / TH - rx / TW]; }
  let shakeX = 0, shakeY = 0;
  function pointerWorld(e) { const r = cv.getBoundingClientRect(); return s2w((e.clientX - r.left) / r.width * VW, (e.clientY - r.top) / r.height * VH); }

  // ---------- input ----------
  const KEYDIR = { w: [0, -1], arrowup: [0, -1], s: [0, 1], arrowdown: [0, 1], a: [-1, 0], arrowleft: [-1, 0], d: [1, 0], arrowright: [1, 0] };
  function onKeyDown(e) {
    if (e.defaultPrevented || !running || paused || hero.sparkTravel || !Online.connected || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName || '')) return;
    const k = e.key.toLowerCase();
    if (k === 'f' && !e.repeat && !hero.dead) {
      e.preventDefault(); const npc = [...City.npcs, ...signs].filter(n => Math.hypot(n.x-hero.x,n.y-hero.y)<2.8).sort((a,b)=>Math.hypot(a.x-hero.x,a.y-hero.y)-Math.hypot(b.x-hero.x,b.y-hero.y))[0];
      if (npc) talkTo(npc); return;
    }
    if (k === 'h' && !e.repeat) { e.preventDefault(); Field.toggleMount(); return; }
    if (KEYDIR[k]) { pendingNpc = null; cityRoute = []; keys.add(k); hero.target = null; hero.goal = null; emitHud(); e.preventDefault(); }
    if ((k === ' ' && e.target?.tagName !== 'BUTTON') || k === 'j') { e.preventDefault(); if (!e.repeat) Field.useSkill('attack'); }
    if (k === 'shift' && isAssassin()) { e.preventDefault(); if (!e.repeat) Field.useSkill('shadowstep'); }
  }
  function onKeyUp(e) { keys.delete(e.key.toLowerCase()); }
  function pickSlime(mx, my, wx, wy) {
    let best = null, depth = -Infinity;
    for (const s of slimes) {
      if (s.dead) continue;
      const [sx, sy] = w2s(s.x, s.y), b = enemyHitbox(s), k = SLIME_K * s.d.scale;
      const left = s.dir < 0 ? -b.x1 : b.x0, right = s.dir < 0 ? -b.x0 : b.x1;
      if (mx < sx + left * k - 9 || mx > sx + right * k + 9 || my < sy + b.y0 * k - 9 || my > sy + b.y1 * k + 9) continue;
      if (s.x + s.y > depth) { best = s; depth = s.x + s.y; }
    }
    if (best) return best;
    let distance = 1.1;
    for (const s of slimes) { if (s.dead) continue; const d = Math.hypot(s.x - wx, s.y - wy) - s.r * .6; if (d < distance) { distance = d; best = s; } }
    return best;
  }
  const SIGN_W = 28, SIGN_TOP = 70;   // the clickable body of a boss sign, in screen pixels
  function onPointerDown(e) {
    if (!running || paused || !Online.connected || hero.dead || hero.sparkTravel) return;
    pendingNpc = null; pendingChest = null; cityRoute = [];
    const r = cv.getBoundingClientRect(), mx=(e.clientX-r.left)/r.width*VW, my=(e.clientY-r.top)/r.height*VH;
    const npc = City.npcs.find(n => { const [x,y]=w2s(n.x,n.y); return Math.abs(mx-x)<32 && my>y-City.nameplateTop(n) && my<y+12; });
    if (npc) { talkTo(npc); return; }
    const sign = signs.find(n => { const [x,y]=w2s(n.x,n.y); return Math.abs(mx-x)<=SIGN_W && my>=y-SIGN_TOP && my<=y+10; });
    if (sign) { talkTo(sign); return; }
    const chest = chests.filter(c => c.expiresAt > tAll).sort((a,b) => b.x+b.y-a.x-a.y).find(c => { const [x,y]=w2s(c.x,c.y); return Math.abs(mx-x)<=27 && my>=y-37 && my<=y+7; });
    if (chest) { openChest(chest); return; }
    pointer.down = true; cv.setPointerCapture && cv.setPointerCapture(e.pointerId);
    const [wx, wy] = pointerWorld(e); pointer.x = wx; pointer.y = wy;
    const s = pickSlime(mx, my, wx, wy);
    const rival = !s && window.Pvp?.available && [...remotePlayers.values()].filter(p => !p.dead).sort((a,b) => b.x+b.y-a.x-a.y).find(p => { const [x,y]=w2s(p.x,p.y); return Math.abs(mx-x)<34 && my>y-150 && my<y+12; });
    if (s) { hero.pvpTargetId = null; hero.target = s; hero.goal = null; Online.send({ type: 'target', id: s.id }); }
    else if (rival) { pointer.down = false; hero.pvpTargetId = rival.id; hero.target = null; hero.goal = null; }
    else { hero.pvpTargetId = null; hero.target = null; hero.goal = { x: wx, y: wy }; Online.send({ type: 'move', x: wx, y: wy }); marker = { x: clamp(wx, .8, MAP - .8), y: clamp(wy, .8, MAP - .8), t: 0 }; }
    emitHud();
  }
  // A boss sign is read with its own message; every townsperson is spoken to with `interact`.
  const askNpc = npc => Online.send(npc.sign ? {type:'sign_read',sign:npc.id} : {type:'interact',npc:npc.id});
  function talkTo(npc) {
    keys.clear(); pointer.down = false; hero.target = null; hero.pvpTargetId = null; hero.goal = null; cityRoute = []; emitHud();
    if (Math.hypot(hero.x-npc.x,hero.y-npc.y) <= 2.5) askNpc(npc);
    else { cityRoute = routeTo(npc, true); pendingNpc = { npc, until: tAll + Math.max(20, cityRoute.length * .6) }; routeTime = 0; }
  }
  // Stop first, so the server's position settles inside its own reach, and ask again until the chest is gone: the
  // client may think it is in reach a moment before the server's copy of the hero is.
  // The walk ends 1.1 tiles from the chest on the hero's side, inside both the client's and the server's reach. The
  // first try is a straight walk (the server slides the hero along walls); a second try, after the first stalled,
  // follows the city route to the chest and then closes in.
  function chestRoute(chest, careful) {
    const route = careful ? routeTo(chest, true, hero, 1.75) : [], dx = hero.x - chest.x, dy = hero.y - chest.y, d = Math.hypot(dx, dy) || 1;
    route.push({ x: chest.x + dx / d * 1.1, y: chest.y + dy / d * 1.1 });
    return route;
  }
  function askForChest(chest) { Online.send({type:'stop'}); Online.send({type:'open_chest',id:chest.id}); }
  function openChest(chest) {
    keys.clear(); pointer.down = false; hero.target = null; hero.pvpTargetId = null; hero.goal = null; cityRoute = []; emitHud();
    if (Math.hypot(hero.x-chest.x,hero.y-chest.y) <= 1.95) { askForChest(chest); pendingChest = {id:chest.id, until:tAll+4, sentAt:tAll}; }
    else { cityRoute = chestRoute(chest, false); pendingChest = {id:chest.id, until:tAll+Math.max(20,cityRoute.length*.6)}; routeTime = 0; }
  }
  // A small grid route lets the travel button walk around real map obstacles.
  // Obstacles bucketed in 4-tile cells, rebuilt when the zone's objects change, so a route across a 160-tile city tests a handful of objects per step.
  let hashFor = null, hash = null;
  const nearObjects = (x, y) => {
    if (hashFor !== objects) {
      const H = 4, w = Math.ceil(MAP / H) + 1, cells = Array.from({ length: w * w }, () => []);
      for (const o of objects) {
        const hx = (o.width ? o.width / 2 : o.r) + 1, hy = (o.width ? o.depth / 2 : o.r) + 1;
        for (let cy = Math.max(0, Math.floor((o.y - hy) / H)); cy <= Math.min(w - 1, Math.floor((o.y + hy) / H)); cy++) for (let cx = Math.max(0, Math.floor((o.x - hx) / H)); cx <= Math.min(w - 1, Math.floor((o.x + hx) / H)); cx++) cells[cy * w + cx].push(o);
      }
      hash = { cells, w, H }; hashFor = objects;
    }
    const cx = Math.floor(x / hash.H), cy = Math.floor(y / hash.H);
    return cx >= 0 && cy >= 0 && cx < hash.w && cy < hash.w ? hash.cells[cy * hash.w + cx] : objects;
  };
  function routeTo(goal, approach = false, origin = hero, approachRange = 2) {
    const free = (x,y) => x>=1 && y>=1 && x<MAP-1 && y<MAP-1 && nearObjects(x,y).every(o => o.width ? Math.abs(x-o.x)>o.width/2+.55 || Math.abs(y-o.y)>o.depth/2+.55 : Math.hypot(x-o.x,y-o.y)>o.r+.55);
    const segmentFree = (a, b) => {
      const steps = Math.max(1, Math.ceil(Math.hypot(a.x-b.x,a.y-b.y) / .1));
      for (let i=0;i<=steps;i++) {
        const x=a.x+(b.x-a.x)*i/steps, y=a.y+(b.y-a.y)*i/steps;
        if(nearObjects(x,y).some(o => o.width ? Math.abs(x-o.x)<o.width/2+.3-1e-6 && Math.abs(y-o.y)<o.depth/2+.3-1e-6 : Math.hypot(x-o.x,y-o.y)<o.r+.3-1e-6)) return false;
      }
      return true;
    };
    // Loot can leave a player against a tree, with its rounded cell blocked.
    // Connect the real position to a nearby clear cell before searching the grid.
    const sources=[];
    for(let x=Math.floor(origin.x)-3;x<=Math.ceil(origin.x)+3;x++) for(let y=Math.floor(origin.y)-3;y<=Math.ceil(origin.y)+3;y++) {
      if(free(x,y) && segmentFree(origin,{x,y})) sources.push([x,y]);
    }
    sources.sort((a,b)=>Math.hypot(a[0]-origin.x,a[1]-origin.y)-Math.hypot(b[0]-origin.x,b[1]-origin.y));
    if(!sources.length)return [];
    const start=sources[0], key=([x,y])=>y*MAP+x;
    let end=[Math.round(goal.x),Math.round(goal.y)];
    if(approach) {
      const candidates=[];
      for(let x=Math.floor(goal.x)-2;x<=Math.ceil(goal.x)+2;x++) for(let y=Math.floor(goal.y)-2;y<=Math.ceil(goal.y)+2;y++) {
        const distance=Math.hypot(x-goal.x,y-goal.y);
        if(distance<=approachRange && free(x,y))candidates.push({point:[x,y],score:distance+Math.hypot(x-origin.x,y-origin.y)*.1});
      }
      candidates.sort((a,b)=>a.score-b.score);if(!candidates.length)return [];end=candidates[0].point;
    }
    const queue=[start], prev=new Map([[key(start),null]]);
    for(let i=0;i<queue.length;i++) { const p=queue[i]; if(key(p)===key(end))break;
      for(const [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0]]) {const q=[p[0]+dx,p[1]+dy];if(free(...q)&&!prev.has(key(q))&&segmentFree({x:p[0],y:p[1]},{x:q[0],y:q[1]})){prev.set(key(q),p);queue.push(q);}}
    }
    if(!prev.has(key(end)))return [];
    const path=[];for(let p=end;p&&key(p)!==key(start);p=prev.get(key(p)))path.unshift({x:p[0],y:p[1]});
    if(Math.hypot(start[0]-origin.x,start[1]-origin.y)>.32)path.unshift({x:start[0],y:start[1]});
    return path;
  }
  function onPointerMove(e) { if (pointer.down) { const [wx, wy] = pointerWorld(e); pointer.x = wx; pointer.y = wy; } }
  function onPointerUp() { pointer.down = false; }

  // ---------- combat ----------
  function say(name, data) { onEvent(name, data); }
  // The top of whoever stands at (x, y), in screen px above their feet: a floating number starts there, so a boss gets its numbers
  // over its head and a slime over its own. `kindOf` narrows the monster search to the kind named by a hit event.
  function headAt(x, y, kindOf) {
    let best = null, bd = 1.6;
    for (const s of slimes) { if (s.dead || (kindOf && s.kind !== kindOf)) continue; const d = Math.hypot(s.x - x, s.y - y); if (d < bd) { bd = d; best = s; } }
    if (best) return Math.round((enemySource(best) ? (best.d.top ?? (best.kind === 'big' ? 36 : best.kind === 'beetle' ? 40 : 28)) * SLIME_K * best.d.scale : 62 * best.d.scale) + 8);
    return Math.hypot(hero.x - x, hero.y - y) < 1.2 || [...remotePlayers.values()].some(r => Math.hypot(r.x - x, r.y - y) < 1.2) ? 118 : 60;
  }
  // kind: hit, crit, hurt, heal, miss, pickup, banner (names and notices), level; `head` overrides the start height (px).
  function floater(x, y, text, color, big, kind = big ? 'level' : 'banner', head) {
    DamageNumbers.spawn(floaters, { x, y, text, color, kind, head: head ?? (['hit', 'crit', 'hurt', 'heal', 'miss'].includes(kind) ? headAt(x, y, kind === 'hit' || kind === 'crit' ? currentHitKind : null) : 60) });
  }
  let currentHitKind = null;
  function burst(x, y, z, n, col, spd = 3, grav = 9) { for (let i = 0; i < n; i++) { const a = Math.random() * 6.283, s = (.3 + Math.random()) * spd; parts.push({ x, y, z, vx: Math.cos(a) * s * .5, vy: Math.sin(a) * s * .5, vz: 2 + Math.random() * 5, life: .5 + Math.random() * .5, t: 0, col: Array.isArray(col) ? col[Math.floor(Math.random() * col.length)] : col, size: 2 + Math.random() * 3, g: grav }); } }
  function keyboardDirection() {
    let x = 0, y = 0;
    for (const key of keys) { const d = KEYDIR[key]; if (d) { x += d[0]; y += d[1]; } }
    const wx = (x + y) / 2, wy = (y - x) / 2, n = Math.hypot(wx, wy) || 1;
    return [wx / n, wy / n];
  }
  // The aim direction: at the selected enemy, else toward the pointer, else the way the hero already faces.
  function aim() {
    let fx = hero.fx, fy = hero.fy;
    const point = remotePlayers.get(hero.pvpTargetId) || (hero.target && !hero.target.dead ? hero.target : pointer);
    if (point.x || point.y) { const dx = point.x - hero.x, dy = point.y - hero.y, n = Math.hypot(dx, dy); if (n > .3) { fx = dx / n; fy = dy / n; } }
    return [fx, fy];
  }
  function swing() { if (hero.pvpTargetId && remotePlayers.has(hero.pvpTargetId)) { Online.send({ type: 'pvp', command: { op: 'attack', id: hero.pvpTargetId } }); return; } const [fx, fy] = aim(); Online.send({ type: 'attack', fx, fy }); }
  // Learned skills: the server checks level, cooldown and life; the client only names the skill and its aim.
  function castSkill(def) {
    let [fx, fy] = aim();
    if (def.effect.effect === 'dash') { const [dx, dy] = keyboardDirection(); if (dx || dy) { fx = dx; fy = dy; } }
    Online.send({ type: 'skill', id: def.id, fx, fy });
  }
  function shadowstep() { const [dx, dy] = keyboardDirection(); Online.send({ type: 'dash', dx, dy }); }
  const classSprite = look => (look.class === 'mage' ? MageSprite : look.class === 'assassin' ? AssassinSprite : look.class === 'priest' ? PriestSprite : look.class === 'hunter' ? HunterSprite : WarriorSprite).variant(look);
  function applyActor(actor, packet, snap = false) {
    const x = actor.x, y = actor.y;
    Object.assign(actor, packet); actor.nx = packet.x; actor.ny = packet.y;
    if (!snap && Math.hypot(x - packet.x, y - packet.y) < 4) { actor.x = x; actor.y = y; }
  }
  function keepActorsSeparated() {
    const enemies = new Set(slimes);
    const actors = [hero, ...remotePlayers.values(), ...slimes].filter(actor => !actor.dead && !actor.sparkTravel);
    for (let i = 0; i < actors.length; i++) for (let j = i + 1; j < actors.length; j++) {
      const a = actors[i], b = actors[j];
      if (!enemies.has(a) && !enemies.has(b)) continue;
      const gap = enemies.has(a) && enemies.has(b) ? (a.r || .3) + (b.r || .3) : 1;
      if ((Math.floor(a.x) === Math.floor(b.x) && Math.floor(a.y) === Math.floor(b.y)) || Math.hypot(a.x - b.x, a.y - b.y) < gap - 1e-8) {
        // Interpolation can cross an occupied tile between otherwise valid snapshots.
        // Restore the complete authoritative positions together to preserve enemy spacing.
        for (const actor of actors) { actor.x = actor.nx; actor.y = actor.ny; }
        return;
      }
    }
  }
  // The server's world clock (seconds), as of the last snapshot plus the time since. Walking townspeople are placed from it.
  const clock = { t: 0, at: 0, ok: false };
  const serverNow = () => clock.ok ? clock.t + (performance.now() - clock.at) / 1000 : performance.now() / 1000;
  function applySnapshot(packet, initial = false) {
    const own = packet.players.find(p => p.id === Online.id); if (!own) return;
    window.DayNight?.sync(packet.worldTime);
    explored = Array.isArray(own.explored) ? own.explored : null;
    if (typeof packet.time === 'number') { clock.t = packet.time; clock.at = performance.now(); clock.ok = true; }
    // The server decides the zone (a gate moved us); rebuild the ground and snap everything to the new place.
    const moved = (own.zone || 0) !== zone;
    if (moved) setZone(own.zone || 0);
    const inZone = a => (a.zone || 0) === zone;
    const selectedTarget = hero.target?.id;
    const wasDead = hero.dead, wasFallen = !!hero.fallen, oldSets = hero.setCounts || {};
    applyActor(hero, own, initial || moved || !!hero.sparkTravel !== !!own.sparkTravel);
    if (!initial && !moved) for (const source of new Set([...Object.keys(oldSets), ...Object.keys(own.setCounts || {})])) {
      const before = oldSets[source] || 0, after = own.setCounts?.[source] || 0;
      for (const tier of [2, 4, 6, 8]) if ((before < tier) !== (after < tier))
        say('setTier', { name: source.replaceAll('_', ' '), tier, active: after >= tier });
    }
    window.Weather?.sync(packet.weather, own.x, own.y, !!own.inside);
    if(hero.sparkTravel){City.close();keys.clear();pointer.down=false;cityRoute=[];pendingNpc=null;pendingChest=null;hero.target=null;hero.goal=null;}
    window.Attributes?.update(own);
    window.Mounts?.update(own); window.MountArt?.preload(own.mount);
    window.Rebirth?.update(own);
    window.Inventory?.update(own.inventory || [], own.look, own.equipment || {}, own.bags || [], own.gearInstances || [], own.setCounts || {});
    window.Quests?.setBells(own.bells || []);
    window.Quests?.update(own.quests || []);
    if (wasDead !== hero.dead) { say(hero.dead ? 'death' : 'respawn'); if (!hero.dead) window.BossMech?.setCause(''); }
    if (wasFallen !== !!hero.fallen) say(hero.fallen ? 'fallen' : 'rallied');
    if (initial || moved) { cam.x = hero.x; cam.y = hero.y; }
    const signature = JSON.stringify(own.look);
    if (signature !== lastLook) {
      lastLook = signature; onCharacter(own.look);
      const generation = spriteGeneration;
      if (mageSpr && mageSpr.constructor === classSprite(own.look)) mageSpr.set(own.look);
      else classSprite(own.look).load(own.look).then(sprite => {
        if (generation === spriteGeneration && lastLook === signature) mageSpr = sprite;
      }).catch(() => say('spriteError'));
    }
    const existing = new Map(slimes.map(s => [s.id, s]));
    slimes = packet.slimes.filter(inZone).map(data => {
      const previous = existing.get(data.id);
      const wasDead = previous?.dead, wasWindup = previous?.state === 'windup';
      const actor = previous || { ...data }; applyActor(actor, data, initial || moved);
      actor.d = SLIME[data.kind];
      if (!initial && !moved && previous) {
        const audible = visibleCombatCue(data.x,data.y);
        if (audible && !wasDead && data.dead) say('enemyDeath', { kind:data.kind, x:data.x, y:data.y, elite:!!actor.d?.elite, boss:!!actor.d?.boss, finalBoss:zdef.final_boss === data.kind });
        else if (audible && !data.dead && !wasWindup && data.state === 'windup') say('enemyAttack', { kind:data.kind, x:data.x, y:data.y, elite:!!actor.d?.elite, boss:!!actor.d?.boss });
      }
      return actor;
    });
    hero.target = selectedTarget == null ? null : slimes.find(s => s.id === selectedTarget && !s.dead) || null;
    const present = new Set();
    for (const player of packet.players) {
      if (player.id === Online.id || !inZone(player)) continue;
      present.add(player.id);
      let remote = remotePlayers.get(player.id);
      if (!remote) { remote = { ...player, sprite: null, signature: '' }; remotePlayers.set(player.id, remote); }
      applyActor(remote, player, initial || moved || !!remote.sparkTravel !== !!player.sparkTravel);
      const lookKey = JSON.stringify(player.look);
      if (remote.signature !== lookKey) {
        remote.signature = lookKey; const generation = spriteGeneration;
        if (remote.sprite && remote.sprite.constructor === classSprite(player.look)) remote.sprite.set(player.look);
        else classSprite(player.look).load(player.look, { background: true }).then(sprite => {
          if (generation === spriteGeneration && remote.signature === lookKey) remote.sprite = sprite;
        }).catch(() => say('spriteError'));
      }
    }
    for (const id of remotePlayers.keys()) if (!present.has(id)) remotePlayers.delete(id);
    if (hero.pvpTargetId && !remotePlayers.has(hero.pvpTargetId)) hero.pvpTargetId = null;
    bolts = packet.bolts.filter(inZone).map(b => ({ ...b, col: b.color }));
    window.BossMech?.update(packet.bossMech);
    ebolts = (packet.ebolts || []).filter(inZone).map(b => { const old = ebolts.find(o => o.id === b.id); return old && Math.hypot(old.x - b.x, old.y - b.y) < 2.5 ? Object.assign(old, b, { x: old.x + (b.x - old.x) * .5, y: old.y + (b.y - old.y) * .5 }) : { ...b }; });
    if (packet.instance) { if (packet.instance.cleared && !instanceCleared) { clearedAt = performance.now() / 1000; instanceCleared = true; if (mini) buildMini(); } instanceCleared = !!packet.instance.cleared; }
    drops = packet.drops.filter(inZone);
    chests = (packet.chests || []).filter(inZone).map(c => ({...c, expiresAt:tAll+c.left}));
    signs = (packet.signs || []).map(s => ({ ...s, sign: true }));   // the boss signs (BOSSMECH-SIGN-ENGINE): read like a townsperson
    if (pendingChest && !chests.some(c => c.id === pendingChest.id)) { pendingChest = null; cityRoute = []; }
    emitHud();
  }
  function networkEvent(event) {
    window.BossMech?.onEvent(event, Online.id);
    if (event.kind === 'bossmech') say('bossMech', event);
    if (event.actor === Online.id && !['death', 'respawn', 'swing', 'cast'].includes(event.kind)) say(event.crit && event.kind === 'hit' ? 'crit' : event.kind, event);
    if (event.kind === 'swing' || event.kind === 'cast') {
      const actor = event.actor === Online.id ? hero : remotePlayers.get(event.actor);
      if (actor && (event.actor === Online.id || visibleCombatCue(event.x,event.y))) say('combatSwing', { actorId:event.actor, className:actor.look?.class, x:event.x, y:event.y, own:event.actor === Online.id });
    }
    if (event.kind === 'skill') skillFx(event);
    if (event.kind === 'boltImpact') {
      const [core, glow] = SKILL_COL[event.skill] || ['#ffffff', '#9fd0ff'];
      const base = { x: event.x, y: event.y, core, glow, t: 0 };
      if (event.skill === 'fireball') {
        effects.push({ ...base, kind: 'skMageFireImpact', r: event.radius, life: .72 });
        spark(event.x, event.y, 28, [core, glow, '#ffbd51'], 8, 2.2, .6);
      } else if (event.skill === 'twinbolt' || event.skill === 'barrage') {
        effects.push({ ...base, kind: 'skMageBoltImpact', style: event.skill, life: .38 });
        spark(event.x, event.y, event.skill === 'twinbolt' ? 7 : 5, [core, glow], 5, .7, .35);
      } else if (event.skill === 'throwingknives' || event.skill === 'knifering') {
        effects.push({ ...base, kind: 'skAssassinImpact', life: .32 });
        spark(event.x, event.y, 5, [core, glow], 4, .5, .3);
      } else if (['powershot', 'multishot', 'piercingarrow', 'explosivearrow'].includes(event.skill)) {
        effects.push({ ...base, kind: event.skill === 'explosivearrow' ? 'skHunterBlast' : 'skHunterImpact',
          style: event.skill, bolt: event.bolt, r: event.radius || 0, life: event.skill === 'explosivearrow' ? .72 : .42 });
        spark(event.x, event.y, event.skill === 'explosivearrow' ? 22 : 8, [core, glow, '#fff5d9'],
          event.skill === 'explosivearrow' ? 9 : 4, event.skill === 'explosivearrow' ? 2 : .6, .5);
      }
    }
    if (event.kind === 'hit') {
      // DamageNumbers.spawn fans a run of hits out over the target's head, so the number sits on the target itself.
      currentHitKind = event.enemy || null; floater(event.x, event.y, DamageNumbers.format(event.value), event.crit ? '#ffe066' : '#fff4e0', event.crit, event.crit ? 'crit' : 'hit'); currentHitKind = null;
      burst(event.x, event.y, 12, 7, ['#fff4e0', '#cfb5fa']);
    }
    if (event.kind === 'hurt') floater(event.x, event.y, '-' + DamageNumbers.format(event.value), '#ff8b9b', false, 'hurt');
    if (event.kind === 'miss' || event.kind === 'dodge') floater(event.x, event.y, event.kind === 'miss' ? 'Miss' : 'Dodge', '#c9c9bd', false, 'miss');
    if (event.kind === 'itemPickup') {
      const item = WORLD_ITEMS.find(i => i.id === event.item), rarity = event.rarity || item?.rarity;
      floater(event.x, event.y, item?.kind === 'bag' ? `${item.name} · +${item.bagSlots} slots` : `+${event.quantity} ${event.name}`, item?.kind === 'bag' ? bagColor(item) : '#64b5ff', false, 'pickup');
      if (event.actor === Online.id) {
        say('pickup'); say('rarePickup', event);
        const tier = { uncommon: 1, rare: 2, epic: 3, legendary: 4 }[rarity] || 0;
        if (tier) burst(event.x, event.y, 8 + tier * 8, 4 + tier * 5, ['#ffffff', { 1: '#4ad66d', 2: '#64b5ff', 3: '#b45cff', 4: '#ff9a2e' }[tier]]);
      }
    }
    if (event.kind === 'shotBlocked') spark(event.x, event.y, 7, ['#f8e5b5','#d2b990','#fff4d7'], 7, 0.6, 0.45);
    if (event.kind === 'pickup') floater(event.x, event.y, '+' + DamageNumbers.format(event.value) + ' gold', '#ffe066', false, 'pickup');
    if (event.kind === 'portal') { effects.push({ kind: 'ring', x: event.x, y: event.y, t: 0 }); burst(event.x, event.y, 20, 14, ['#ffd9a0', '#ff8a3a', '#7ae8c8']); }
    if (event.kind === 'chestOpen') { if (pendingChest) { pendingChest = null; cityRoute = []; } effects.push({kind:'ring',x:event.x,y:event.y,t:0,life:.65,grow:1.1,col:'#ffe292'}); effects.push({kind:'chestOpen',x:event.x,y:event.y,t:0,life:1.3}); burst(event.x,event.y,24,18,['#ffe292','#fff6cf','#d89543'],4,5); }
    if (event.kind === 'levelup') levelUpFx(event);
    if (event.kind === 'rebirth') rebirthFx(event);
    if (event.kind === 'slam') { effects.push({ kind: 'slam', x: event.x, y: event.y, r: event.value, t: 0, life: .7 }); burst(event.x, event.y, 6, 26, ['#e8dcc0', '#a9a08a', '#ffb060'], 5, 10); kick(event.value > 4 ? 14 : 9, .45); }
    if (event.kind === 'cleared') { clearedAt = performance.now() / 1000; instanceCleared = true; if (mini) buildMini(); burst(event.x, event.y, 20, 40, ['#d4ffc8', '#9cff8f', '#ffffff'], 6, 4); effects.push({ kind: 'ring', x: event.x, y: event.y, t: 0, life: 1.6, grow: 2.4, col: '#9cff8f' }); }
    // Food and potions: a potion lands at once with a ring and its number; a meal shows its share every second.
    if (event.kind === 'consume') {
      spark(event.x, event.y, 14, ['#9dffb4', '#d8ffe0', '#f0d9a0'], 10, 1, .9);
      if (event.mana > 0) floater(event.x, event.y, '+' + event.mana + ' ' + (event.resourceType || 'mana'), '#85baff', false, 'heal');
      if (event.value > 0) { effects.push({ kind: 'skAura', x: event.x, y: event.y, core: '#d9ffe0', glow: '#3fd36a', col: '#3fd36a', a: 0, t: 0, life: 1 }); floater(event.x, event.y, '+' + DamageNumbers.format(event.value), '#7dff9a', true, 'heal'); }
    }
    // A party member healed by a priest: their own number and glow, whoever cast it.
    if (event.kind === 'healed' && event.value > 0) floater(event.x, event.y, '+' + DamageNumbers.format(event.value), '#7dff9a', true, 'heal');
    if (event.kind === 'regen') { floater(event.x, event.y, '+' + DamageNumbers.format(event.value), '#7dff9a', false, 'heal'); spark(event.x, event.y, 4, ['#9dffb4', '#d8ffe0'], 6, .6, .6); }
    if (event.kind === 'swing') {
      const actor = event.actor === Online.id ? hero : remotePlayers.get(event.actor);
      if (actor) effects.push({ kind: actor.look.class === 'assassin' ? 'dualSlash' : 'slash', x: event.x, y: event.y, a: Math.atan2(actor.fy, actor.fx), t: -.12 });
    }
  }
  // ---------- skill effects and the level-up spectacle ----------
  const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SKILL_BY_ID = Object.fromEntries(WORLD_SKILLS.map(s => [s.id, s]));
  // [bright core, glow] per skill.
  const SKILL_COL = {
    cleave: ['#fff1c2', '#ffb84a'], battlecry: ['#ffe6a0', '#ff7a2e'], shieldwall: ['#d6ecff', '#4a9bff'], whirlwind: ['#e8f6ff', '#6fc7ff'], charge: ['#ffe0b0', '#ff9a3a'],
    groundslam: ['#ffe9c0', '#d9822b'], secondwind: ['#d9ffe0', '#3fd36a'], berserk: ['#ffd0c0', '#ff3b2e'], earthshatter: ['#ffe2b0', '#c9701f'], titanswrath: ['#fff6c8', '#ffb400'],
    twinbolt: ['#f0e4ff', '#a57bff'], arcaneward: ['#e0f0ff', '#7a9bff'], fireball: ['#fff3c0', '#ff6a1a'], barrage: ['#e0f8ff', '#46c8ff'], blink: ['#f6e8ff', '#b46bff'],
    chainlightning: ['#f4fdff', '#6fe0ff'], meteor: ['#fff0c0', '#ff4a12'], lifedrain: ['#ffd6f0', '#d0286e'], arcanestorm: ['#f2e6ff', '#8f5bff'], starfall: ['#fffbe0', '#ffd84a'],
    throwingknives: ['#ffffff', '#b8c6d8'], evasion: ['#e9e4ff', '#8a78d6'], lunge: ['#f4e0ff', '#a050ff'], flurry: ['#ffffff', '#c9b2ff'], shadowveil: ['#e0d8ff', '#6a50c8'],
    cycloneblades: ['#f4ecff', '#b38cff'], assassinate: ['#ffe0e0', '#ff3b5c'], deadlyfocus: ['#fff0c8', '#ffb23a'], knifering: ['#fdf0ff', '#d89cff'], thousandcuts: ['#ffffff', '#ff5ca8'],
    mend: ['#f2fff0', '#58e08a'], smite: ['#ffffff', '#ffd95a'], wardoflight: ['#fffbe8', '#ffd46a'], prayer: ['#f4fff2', '#6fe6a0'], holynova: ['#ffffff', '#ffe27a'],
    blessing: ['#fff4d0', '#ffb84a'], guardianlight: ['#f0fff6', '#3fd88a'], searinglight: ['#ffffff', '#ffb02e'], divinehymn: ['#f6fff4', '#7dffb0'], heavenswrath: ['#ffffff', '#ffd23a'],
    powershot: ['#fff4d0', '#eeb652'], multishot: ['#fff0c5', '#c99554'], rollaway: ['#e9f3dd', '#83ba82'],
    piercingarrow: ['#edfff7', '#71e7b4'], huntersmark: ['#fff0c4', '#eb9b45'], explosivearrow: ['#fff2c8', '#ff762b'],
    rapidfire: ['#f5ffcc', '#b6e94f'], rainofarrows: ['#f0f8de', '#a5cb8b'], eaglesight: ['#f6f9e2', '#83d4dc'],
    arrowstorm: ['#fff4d0', '#ffc66c'],
  };
  const BUFF_COL = { damage: '#ff9a3a', shield: '#59a8ff', haste: '#ffe45a', dodge: '#b9a8ff', crit: '#ff5c7a', regen: '#58d68d' };
  let shakeT = 0, shakeMag = 0;
  function kick(mag, dur) { if (reducedMotion()) return; shakeMag = Math.max(shakeT > 0 ? shakeMag : 0, mag); shakeT = Math.max(shakeT, dur); }
  function spark(x, y, n, cols, up, spread, life) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, s = Math.random() * spread;
      parts.push({ x, y, z: Math.random() * 16, vx: Math.cos(a) * s, vy: Math.sin(a) * s, vz: up * (.5 + Math.random()), life: life * (.6 + Math.random() * .6), t: 0,
        col: cols[Math.floor(Math.random() * cols.length)], size: 2 + Math.random() * 3.5, g: 4 });
    }
  }
  function jagged(from, to) {
    const out = [from], n = 7, dx = to.x - from.x, dy = to.y - from.y, len = Math.hypot(dx, dy) || 1, nx = -dy / len, ny = dx / len;
    for (let i = 1; i < n; i++) { const k = i / n, o = (Math.random() - .5) * .9; out.push({ x: from.x + dx * k + nx * o, y: from.y + dy * k + ny * o }); }
    out.push(to); return out;
  }
  function skillFx(ev) {
    const def = SKILL_BY_ID[ev.skill]; if (!def) return;
    const [core, glow] = SKILL_COL[ev.skill] || ['#ffffff', '#9fd0ff'], kind = def.effect.effect, own = ev.actor === Online.id, a = Math.atan2(ev.fy, ev.fx);
    const base = { x: ev.x, y: ev.y, core, glow, a, t: 0 }, pts = (ev.points || []).map(([x, y]) => ({ x, y }));
    if (kind === 'cone') {
      effects.push({ ...base, kind: ev.skill === 'cleave' ? 'skCleave' : ev.skill === 'earthshatter' ? 'skWarFissure' : ev.skill === 'thousandcuts' ? 'skAssassinFan' : 'skCone', r: def.effect.reach,
        arc: 2 * Math.acos(def.effect.dot), life: ev.skill === 'earthshatter' ? .95 : ev.skill === 'cleave' ? .7 : ev.skill === 'thousandcuts' ? .82 : .42 });
      spark(ev.x + ev.fx * 1.2, ev.y + ev.fy * 1.2, 16, [core, glow], 5, 3, .5); if (own) kick(5, .18);
    }
    else if (kind === 'nova') {
      const r = ev.value, style = ev.skill === 'whirlwind' ? 'warWhirl' : ev.skill === 'groundslam' ? 'warSlam' : ev.skill === 'titanswrath' ? 'warTitan' :
        ev.skill === 'arcanestorm' ? 'mageStorm' : ev.skill === 'cycloneblades' ? 'assassinCyclone' : ev.skill === 'arrowstorm' ? 'arrows' : '';
      if (ev.skill === 'arrowstorm') {
        effects.push({ ...base, kind: 'skHunterStorm', r, life: .8, capstone: !!ev.capstone });
        spark(ev.x, ev.y, 30, [core, glow], 5, r * .55, .65);
        if (own) kick(8, .2);
      } else if (ev.skill === 'holynova' || ev.skill === 'heavenswrath') {
        effects.push({ ...base, kind: 'skPriestNova', r, healR: def.pulse.range, targets: pts, style: ev.skill === 'heavenswrath' ? 'wrath' : 'holy', life: ev.skill === 'heavenswrath' ? 1.25 : .95 });
        spark(ev.x, ev.y, ev.skill === 'heavenswrath' ? 38 : 24, [core, glow], 8, r * .55, .85);
        if (own) kick(ev.skill === 'heavenswrath' ? 10 : 5, .25);
      } else {
      const nova = { ...base, kind: 'skNova', r, style, life: (ev.skill === 'starfall' ? 1.5 : .5) + r * .05 };
      if (['warSlam', 'warTitan'].includes(style)) nova.cracks = Array.from({ length: 9 + Math.round(r) }, (_, i) => ({ a: i * 6.283 / (9 + Math.round(r)) + (Math.random() - .5) * .3, len: .75 + Math.random() * .3, zig: Array.from({ length: 8 }, (_, j) => [(j + 1) / 8, (Math.random() - .5) * .22]) }));
      if (ev.skill === 'starfall') nova.stars = Array.from({ length: 18 }, () => { const an = Math.random() * 6.283, d = Math.sqrt(Math.random()) * r * .9; return { x: ev.x + Math.cos(an) * d, y: ev.y + Math.sin(an) * d, delay: Math.random() * .8 }; });
      effects.push(nova);
      spark(ev.x, ev.y, 14 + Math.round(r * 5), [core, glow], 6, 2 + r * .9, .6 + r * .05);
      if (ev.skill === 'titanswrath') effects.push({ ...base, kind: 'skWarTitanCore', life: 1.1, heal: ev.heal || 0 });
      else if (r >= 4 && ev.skill !== 'starfall') effects.push({ ...base, kind: 'skNova', r: r * .65, life: .5 + r * .05, t: -.12 });
      if (own) kick(Math.min(16, 4 + r * 1.6), .15 + r * .06);
      }
    } else if (kind === 'volley') {
      const mageKind = ev.skill === 'twinbolt' || ev.skill === 'barrage' ? 'skMageVolley' : ev.skill === 'fireball' ? 'skMageFireCast' : null;
      const assassinKind = ev.skill === 'throwingknives' || ev.skill === 'knifering' ? 'skAssassinCast' : null;
      const hunterKind = def.class === 'hunter' ? 'skHunterDraw' : null;
      effects.push({ ...base, kind: mageKind || assassinKind || hunterKind || 'skFlash', style: ev.skill,
        count: ev.value, spread: def.effect.spread, life: mageKind || assassinKind || hunterKind ? .48 : .22 });
      spark(ev.x, ev.y, 8, [core, glow], 3, 2, .4);
      if (ev.value >= 8 && !assassinKind) effects.push({ ...base, kind: 'skNova', r: 1.6, life: .4 });
    }
    else if (kind === 'dash') {
      const dist = ev.value, end = { x: ev.x + ev.fx * dist, y: ev.y + ev.fy * dist };
      if (ev.skill === 'blink') {
        effects.push({ ...base, kind: 'skMageBlink', actor: ev.actor, life: .65 });
        spark(ev.x, ev.y, 14, [core, glow], 8, 1, .65);
      } else if (ev.skill === 'rollaway') {
        effects.push({ ...base, kind: 'skHunterRoll', actor: ev.actor, life: .72 });
        spark(ev.x, ev.y, 12, [core, glow], 3, 1.2, .55);
      } else if (def.effect.mult === 0) {
        effects.push({ ...base, kind: 'skBeam', life: .5 }); effects.push({ ...base, kind: 'skBeam', x: end.x, y: end.y, life: .5, t: -def.effect.time });
        spark(ev.x, ev.y, 18, [core, glow], 9, 1.5, .8); spark(end.x, end.y, 18, [core, glow], 9, 1.5, .8);
      } else { effects.push({ ...base, kind: ev.skill === 'charge' ? 'skWarCharge' : ev.skill === 'lunge' ? 'skAssassinLunge' : 'skDash', actor: ev.actor,
        ex: end.x, ey: end.y, life: .62 }); spark(ev.x, ev.y, 12, [core, glow, '#c8b090'], 3, 3, .5); if (own) kick(4, .2); }
    } else if (kind === 'strike') {
      if (ev.skill === 'lifedrain') for (const p of pts) effects.push({ ...base, kind: 'skMageDrain', from: p, to: { x: ev.x, y: ev.y }, heal: ev.heal || 0, life: .85 });
      else if (ev.skill === 'flurry') pts.forEach((p, i) => effects.push({ ...base, kind: 'skAssassinFlurry', x: p.x, y: p.y, index: i, total: pts.length, life: .29, t: -i * .105 }));
      else if (ev.skill === 'assassinate') pts.forEach(p => effects.push({ ...base, kind: 'skAssassinAssassinate', x: p.x, y: p.y, life: .72 }));
      else if (ev.skill === 'smite' || ev.skill === 'searinglight') pts.forEach(p => effects.push({ ...base, kind: ev.skill === 'smite' ? 'skPriestSmite' : 'skPriestSearing', x: p.x, y: p.y, from: p, to: { x: ev.x, y: ev.y }, heal: ev.heal || 0, life: ev.skill === 'smite' ? .72 : .92 }));
      else pts.forEach((p, i) => effects.push({ ...base, kind: 'skCut', x: p.x, y: p.y, big: pts.length === 1, ang: Math.random() * 3.14, life: .3, t: -i * (pts.length > 4 ? .035 : .06) }));
      if (own && pts.length === 1) kick(6, .2);
    } else if (kind === 'chain') {
      let from = { x: ev.x, y: ev.y };
      pts.forEach((p, i) => { effects.push({ ...base, kind: ev.skill === 'chainlightning' ? 'skMageLightning' : 'skChain', path: jagged(from, p), hop: i, life: .48, t: -i * .08 }); from = p; });
    } else if (kind === 'meteor') {
      const c = pts[0] || { x: ev.x + ev.fx * 4, y: ev.y + ev.fy * 4 };
      if (ev.skill === 'starfall') effects.push({ ...base, kind: 'skNova', x: c.x, y: c.y, r: ev.value, style: 'mageStarfield', life: 1.8,
        stars: Array.from({ length: 28 }, () => { const an = Math.random() * 6.283, d = Math.sqrt(Math.random()) * ev.value * .9; return { x: c.x + Math.cos(an) * d, y: c.y + Math.sin(an) * d, delay: Math.random() * .9 }; }) });
      else if (ev.skill === 'rainofarrows') effects.push({ ...base, kind: 'skHunterRain', x: c.x, y: c.y, r: ev.value, life: 1.15,
        arrows: Array.from({ length: 30 }, (_, i) => { const an = i * 2.39996, d = Math.sqrt((i + .5) / 30) * ev.value * .94;
          return { x: c.x + Math.cos(an) * d, y: c.y + Math.sin(an) * d, delay: .06 + (i % 7) * .045 }; }) });
      else effects.push({ ...base, kind: ev.skill === 'meteor' ? 'skMageMeteor' : 'skMeteor', x: c.x, y: c.y, r: ev.value, life: 1.1 });
      if (ev.skill !== 'rainofarrows') setTimeout(() => { spark(c.x, c.y, 40, [core, glow, '#ffe27a'], 10, 4, 1); if (own) kick(14, .5); }, 380);
    } else if (kind === 'buff') {
      const col = BUFF_COL[def.effect.kind] || glow;
      const warriorBuff = { battlecry: 'skWarCry', shieldwall: 'skWarShield', berserk: 'skWarBerserk' }[ev.skill];
      const assassinBuff = { evasion: 'dodge', shadowveil: 'haste', deadlyfocus: 'crit' }[ev.skill];
      const priestBuff = ev.skill === 'wardoflight' || ev.skill === 'blessing';
      const hunterBuff = def.class === 'hunter';
      effects.push({ ...base, kind: hunterBuff ? 'skHunterBuff' : priestBuff ? 'skPriestBuff' : warriorBuff || (ev.skill === 'arcaneward' ? 'skMageWard' : assassinBuff ? 'skAssassinBuff' : 'skAura'),
        style: hunterBuff || priestBuff ? ev.skill : assassinBuff, targets: pts, r: def.effect.range, col, life: hunterBuff || priestBuff ? 1.2 : warriorBuff || ev.skill === 'arcaneward' || assassinBuff ? 1.15 : 1 });
      spark(ev.x, ev.y, 22, [core, col], 12, 1.2, 1); floater(ev.x, ev.y, def.name, col, false);
    } else if (kind === 'heal') { effects.push({ ...base, kind: ev.skill === 'secondwind' ? 'skWarHeal' : ev.skill === 'guardianlight' ? 'skPriestSanctuary' : 'skAura', col: glow, life: 1.15 }); spark(ev.x, ev.y, 26, [core, glow], 12, 1.2, 1.1); }
    else if (kind === 'mend') {
      effects.push({ ...base, kind: ev.skill === 'mend' ? 'skPriestMend' : ev.skill === 'prayer' ? 'skPriestPrayer' : 'skPriestHymn',
        targets: pts, r: def.effect.range, life: ev.skill === 'divinehymn' ? 1.8 : ev.skill === 'prayer' ? 1.15 : .85 });
      spark(ev.x, ev.y, ev.skill === 'divinehymn' ? 26 : 12, [core, glow], 8, 1.1, .8);
    }
    if (ev.capstone) {
      const capstoneAt = ev.skill === 'starfall' ? pts[0] || base : base;
      if (ev.skill === 'thousandcuts') effects.push({ ...base, kind: 'skAssassinFan', r: def.effect.reach,
        arc: 2 * Math.acos(def.effect.dot), life: .82, t: -.12, core: '#ffe2f0', glow: '#b553bd' });
      else if (ev.skill === 'heavenswrath') effects.push({ ...base, kind: 'skPriestCrown', r: def.effect.radius, life: 1.3 });
      else if (ev.skill === 'arrowstorm') { /* the full-radius storm already carries the capstone */ }
      else effects.push({ ...base, x: capstoneAt.x, y: capstoneAt.y, kind: 'skNova', r: 2.8, style: def.class === 'warrior' ? 'cracks' : 'spiral',
        cracks: Array.from({ length: 14 }, (_, i) => ({ a: i * 6.283 / 14, len: 1, zig: Array.from({ length: 8 }, (_, j) => [(j + 1) / 8, 0]) })), life: 1.1 });
      spark(ev.x, ev.y, 48, [core, glow, '#ffffff'], 9, 3.8, 1.1);
      if (own) kick(12, .45);
    }
    // Whoever else the skill reached (healed or blessed party members) gets their own glow and sparks.
    if (kind === 'mend' || kind === 'buff' || def.pulse) for (const p of pts) {
      if (def.class !== 'priest') effects.push({ ...base, kind: 'skAura', x: p.x, y: p.y, col: BUFF_COL[def.effect.kind] || glow, life: 1 });
      spark(p.x, p.y, 12, [core, glow], 8, .8, .8);
    }
    if (ev.heal > 0) { floater(ev.x, ev.y, '+' + DamageNumbers.format(ev.heal), '#7dff9a', true, 'heal'); if (kind !== 'heal') spark(ev.x, ev.y, 12, ['#9dffb4', '#d8ffe0'], 10, 1, .9); }
    if (ev.setDouble) {
      effects.push({ ...base, kind: 'skNova', r: 2.2, life: .65, style: 'spiral' });
      spark(ev.x, ev.y, 22, ['#ffffff', '#f6c867'], 7, 2, .7);
    }
    if (ev.setSignature) {
      const sources = Object.keys(WORLD_SET_BONUSES.signatures), index = sources.indexOf(ev.setSignature);
      const hue = index < 0 ? 45 : index * 360 / sources.length;
      const h = hue / 60, chroma = .54, x = chroma * (1 - Math.abs(h % 2 - 1)), base =
        h < 1 ? [chroma, x, 0] : h < 2 ? [x, chroma, 0] : h < 3 ? [0, chroma, x] :
        h < 4 ? [0, x, chroma] : h < 5 ? [x, 0, chroma] : [chroma, 0, x];
      const col = '#' + base.map(v => Math.round((v + .43) * 255).toString(16).padStart(2, '0')).join('');
      effects.push({ ...base, kind: 'skAura', col, life: 1.2 });
      spark(ev.x, ev.y, 30, [col, '#ffffff'], 10, 2.6, 1);
      floater(ev.x, ev.y, WORLD_SET_BONUSES.signatures[ev.setSignature]?.name || 'Set bonus', col, true);
    }
  }
  // Canvas-built stand-in mount, only for an actor whose mount art has not loaded (or in test mode): the horse body in the
  // selected mount's coat colour.
  const MOUNT_COATS = { horse: '#70422b', raptor: '#4f7a3a', lizard: '#8a9a3c', sabertooth: '#b98a45', gryphon: '#cdb98a' };
  // A modular sprite seats its own rider in the mount's atlas art (client/mountart.js, MageSprite.draw); the canvas horse
  // below is the fallback while that art loads and in test mode.
  const seatedInArt = (actor, sprite) => !!(actor.mounted && !actor.dead && sprite?.frame && window.MountArt?.ready(actor.mount));
  function drawMount(g, actor) {
    if (!actor.mounted || actor.dead) return;
    const stride = actor.moving ? Math.sin(actor.walk * 2) * 7 : 0;
    g.save();
    g.fillStyle = 'rgba(9, 11, 15, .28)'; g.beginPath(); g.ellipse(0, 1, 42, 11, 0, 0, 6.283); g.fill();
    g.strokeStyle = '#3b2219'; g.lineWidth = 9; g.lineCap = 'round';
    for (const [x, phase] of [[-24, 1],[-12,-1],[17,-1],[29,1]]) { g.beginPath(); g.moveTo(x,-23); g.lineTo(x+phase*stride*.45,-1); g.stroke(); }
    g.fillStyle = window.Rebirth?.tintColor(actor.mountTint) || MOUNT_COATS[actor.mount] || MOUNT_COATS.horse; g.beginPath(); g.ellipse(0,-34,38,22,-.08,0,6.283); g.fill();
    g.beginPath(); g.moveTo(23,-43); g.lineTo(37,-68); g.lineTo(51,-64); g.lineTo(49,-39); g.closePath(); g.fill();
    g.fillStyle = '#4d2c20'; g.beginPath(); g.moveTo(35,-64); g.lineTo(35,-79); g.lineTo(42,-68); g.moveTo(46,-63); g.lineTo(50,-77); g.lineTo(54,-63); g.fill();
    g.strokeStyle = '#3b2219'; g.lineWidth = 5; g.beginPath(); g.moveTo(-32,-39); g.quadraticCurveTo(-54,-62,-46,-77); g.stroke();
    g.fillStyle = '#261a16'; g.beginPath(); g.arc(45,-56,2,0,6.283); g.fill();
    g.fillStyle = '#c9a16a'; g.fillRect(-19,-53,34,8);
    g.restore();
  }
  // A grand level-up: a pillar of light, rays, rings and a fountain of sparks on everyone's screen; the player's own
  // client adds a screen shake, and game.js adds the flash, fanfare and banner.
  function levelUpFx(ev) {
    const own = ev.actor === Online.id, golds = ['#ffe066', '#fff4c0', '#ffffff', '#ffb347', '#7fe9ff'];
    effects.push({ kind: 'luPillar', x: ev.x, y: ev.y, t: 0, life: 2.4 });
    effects.push({ kind: 'luRays', x: ev.x, y: ev.y, t: 0, life: 1.8 });
    ['#ffe066', '#ffffff', '#7fe9ff', '#ffb347'].forEach((col, i) => effects.push({ kind: 'ring', x: ev.x, y: ev.y, col, t: -i * .16, life: 1.2 + i * .1, grow: 1 + i * .35 }));
    spark(ev.x, ev.y, 90, golds, 24, 1.4, 2); spark(ev.x, ev.y, 50, golds, 8, 4.5, 1.5);
    floater(ev.x, ev.y, 'LEVEL UP!', '#ffe066', true);
    floater(ev.x, ev.y, `Level ${ev.level}`, '#ffffff', true, 'level', 108);
    if (own) kick(13, .8);
  }
  // A rebirth: a pillar and rings in the tier's colour, a fountain of sparks and a floating word; the player's own client
  // adds a screen shake (game.js adds the banner and the fanfare).
  function rebirthFx(ev) {
    const tier = Math.round(ev.value) || 1, rgb = window.Rebirth.rgb(tier), col = window.Rebirth.color(tier), own = ev.actor === Online.id;
    effects.push({ kind: 'rbPillar', x: ev.x, y: ev.y, t: 0, life: 2.6, rgb });
    [col, '#ffffff', col].forEach((c, i) => effects.push({ kind: 'ring', x: ev.x, y: ev.y, col: c, t: -i * .2, life: 1.3 + i * .15, grow: 1 + i * .4 }));
    spark(ev.x, ev.y, 70, [col, '#ffffff'], 20, 1.4, 2);
    floater(ev.x, ev.y, 'REBORN!', col, true);
    floater(ev.x, ev.y, window.Rebirth.title(tier), '#ffffff', true, 'level', 108);
    if (own) kick(11, .7);
  }
  function drawLevelFx(g, e) {
    const [sx, sy] = w2s(e.x, e.y), p = e.t / e.life;
    g.save(); g.globalCompositeOperation = 'lighter';
    if (e.kind === 'rbPillar') {
      const rise = Math.min(1, e.t / .3), top = 1000 * rise, fade = p < .5 ? 1 : 1 - (p - .5) / .5, w = 70 * (1 - p * .3) * (.94 + .06 * Math.sin(e.t * 30));
      const gr = g.createLinearGradient(0, sy - top, 0, sy); gr.addColorStop(0, `rgba(${e.rgb},0)`); gr.addColorStop(.5, `rgba(${e.rgb},.45)`); gr.addColorStop(1, 'rgba(255,255,255,.9)');
      g.globalAlpha = fade; g.fillStyle = gr; g.fillRect(sx - w / 2, sy - top, w, top);
      const gl = g.createRadialGradient(sx, sy, 4, sx, sy, 130); gl.addColorStop(0, `rgba(${e.rgb},.8)`); gl.addColorStop(1, `rgba(${e.rgb},0)`);
      g.fillStyle = gl; g.beginPath(); g.ellipse(sx, sy, 130, 65, 0, 0, 6.283); g.fill();
    } else if (e.kind === 'luPillar') {
      const rise = Math.min(1, e.t / .22), top = 1000 * rise, fade = p < .55 ? 1 : 1 - (p - .55) / .45, flick = .92 + .08 * Math.sin(e.t * 38), w = 84 * (1 - p * .35) * flick;
      const gr = g.createLinearGradient(0, sy - top, 0, sy); gr.addColorStop(0, 'rgba(255,214,90,0)'); gr.addColorStop(.5, 'rgba(255,230,140,.5)'); gr.addColorStop(1, 'rgba(255,255,255,.95)');
      g.globalAlpha = fade; g.fillStyle = gr; g.fillRect(sx - w / 2, sy - top, w, top);
      g.fillStyle = 'rgba(255,255,255,.75)'; g.fillRect(sx - w * .16, sy - top, w * .32, top);
      const gl = g.createRadialGradient(sx, sy, 4, sx, sy, 150); gl.addColorStop(0, 'rgba(255,240,170,.85)'); gl.addColorStop(1, 'rgba(255,200,60,0)');
      g.fillStyle = gl; g.beginPath(); g.ellipse(sx, sy, 150, 75, 0, 0, 6.283); g.fill();
    } else if (e.kind === 'luRays') {
      const fade = 1 - p, n = 16, r = 120 + 700 * Math.min(1, e.t / .5), spin = e.t * .9;
      g.translate(sx, sy - 46); g.scale(1, .62); g.globalAlpha = fade * .55;
      for (let i = 0; i < n; i++) {
        const ang = spin + i * 6.283 / n, wid = .07 + (i % 2) * .05;
        const gr = g.createLinearGradient(0, 0, Math.cos(ang) * r, Math.sin(ang) * r); gr.addColorStop(0, 'rgba(255,240,170,.9)'); gr.addColorStop(1, 'rgba(255,200,60,0)');
        g.fillStyle = gr; g.beginPath(); g.moveTo(0, 0); g.lineTo(Math.cos(ang - wid) * r, Math.sin(ang - wid) * r); g.lineTo(Math.cos(ang + wid) * r, Math.sin(ang + wid) * r); g.closePath(); g.fill();
      }
    }
    g.restore();
  }
  // Strokes are drawn as [width, colour, alpha, additive]: a dark outline keeps them readable on bright grass, additive
  // glow gives the light, and an opaque core carries the colour.
  const OUTLINE = '#1e0c32';
  function layers(g, list, fade, shrink, draw) {
    for (const [w, col, al, add] of list) { g.globalCompositeOperation = add ? 'lighter' : 'source-over'; g.globalAlpha = al * fade; g.strokeStyle = col; g.lineWidth = w * (1 - shrink); draw(); g.stroke(); }
    g.globalCompositeOperation = 'source-over';
  }
  function groundSkillFx(e) {
    return e.kind === 'skNova' || e.kind === 'skCleave' || e.kind === 'skWarFissure' || e.kind === 'skWarCharge' ||
      e.kind === 'skMageFireCast' || e.kind === 'skMageFireImpact' || e.kind === 'skMageMeteor' || e.kind === 'skMageBlink' ||
      e.kind === 'skAssassinLunge' || e.kind === 'skAssassinFan' || e.kind === 'skPriestBuff' ||
      e.kind === 'skPriestNova' || e.kind === 'skPriestHymn' || e.kind === 'skPriestSanctuary' ||
      ['skHunterRoll', 'skHunterBlast', 'skHunterRain', 'skHunterStorm'].includes(e.kind);
  }
  function drawStarfall(g, e, layer) {
    for (const st of e.stars) {         // stars fall above actors; the nova beneath them stays on the floor
      const q = (e.t - st.delay) / .3; if (q < 0 || q > 1.6) continue;
      const [qx, qy] = w2s(st.x, st.y), fall = Math.min(1, q);
      if (q <= 1 && layer === 'air') { const hx = qx + 140 * (1 - fall), hy = qy - 420 * (1 - fall) - 4; layers(g, [[12, OUTLINE, .3, 0], [8, e.glow, .6, 1], [3.5, '#ffffff', 1, 0]], 1, 0, () => { g.beginPath(); g.moveTo(hx + 70, hy - 210); g.lineTo(hx, hy); }); g.fillStyle = '#ffffff'; g.globalAlpha = 1; g.beginPath(); g.arc(hx, hy, 7, 0, 6.283); g.fill(); }
      else if (q > 1 && layer === 'floor') { const f2 = 1 - (q - 1) / .6; g.globalAlpha = f2; g.fillStyle = e.core; g.beginPath(); g.ellipse(qx, qy, 36 * (2 - f2), 17 * (2 - f2), 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'lighter'; g.fillStyle = e.glow; g.beginPath(); g.ellipse(qx, qy, 52 * (2 - f2), 24 * (2 - f2), 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'source-over'; }
    }
  }
  function drawAssassinKnife(g, x, y, dx, dy, scale = 1, color = '#e6d9ff') {
    const len = Math.hypot(dx, dy) || 1, ux = dx / len, uy = dy / len, px = -uy, py = ux;
    g.save(); g.lineJoin = 'round';
    g.fillStyle = '#1d142c'; g.strokeStyle = '#1d142c'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(x + ux * 28 * scale, y + uy * 28 * scale);
    g.lineTo(x - ux * 9 * scale + px * 7 * scale, y - uy * 9 * scale + py * 7 * scale);
    g.lineTo(x - ux * 18 * scale + px * 4 * scale, y - uy * 18 * scale + py * 4 * scale);
    g.lineTo(x - ux * 18 * scale - px * 4 * scale, y - uy * 18 * scale - py * 4 * scale);
    g.lineTo(x - ux * 9 * scale - px * 7 * scale, y - uy * 9 * scale - py * 7 * scale); g.closePath(); g.stroke();
    g.fillStyle = color; g.fill(); g.strokeStyle = '#ffffff'; g.lineWidth = 2;
    g.beginPath(); g.moveTo(x - ux * 8 * scale, y - uy * 8 * scale); g.lineTo(x + ux * 21 * scale, y + uy * 21 * scale); g.stroke();
    g.strokeStyle = '#af87dd'; g.lineWidth = 4; g.beginPath();
    g.moveTo(x - ux * 12 * scale + px * 10 * scale, y - uy * 12 * scale + py * 10 * scale);
    g.lineTo(x - ux * 12 * scale - px * 10 * scale, y - uy * 12 * scale - py * 10 * scale); g.stroke(); g.restore();
  }
  function drawHunterArrow(g, x, y, dx, dy, scale = 1, color = '#f3d492') {
    const n = Math.hypot(dx, dy) || 1, ux = dx / n, uy = dy / n, px = -uy, py = ux;
    g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
    g.strokeStyle = '#342519'; g.lineWidth = 5 * scale; g.beginPath();
    g.moveTo(x - ux * 30 * scale, y - uy * 30 * scale); g.lineTo(x + ux * 17 * scale, y + uy * 17 * scale); g.stroke();
    g.strokeStyle = color; g.lineWidth = 2.5 * scale; g.stroke();
    g.fillStyle = '#fff6d8'; g.strokeStyle = '#342519'; g.lineWidth = 2 * scale;
    g.beginPath(); g.moveTo(x + ux * 30 * scale, y + uy * 30 * scale);
    g.lineTo(x + ux * 13 * scale + px * 7 * scale, y + uy * 13 * scale + py * 7 * scale);
    g.lineTo(x + ux * 17 * scale, y + uy * 17 * scale);
    g.lineTo(x + ux * 13 * scale - px * 7 * scale, y + uy * 13 * scale - py * 7 * scale); g.closePath(); g.fill(); g.stroke();
    for (const side of [-1, 1]) { g.fillStyle = color; g.beginPath();
      g.moveTo(x - ux * 19 * scale, y - uy * 19 * scale);
      g.lineTo(x - ux * 32 * scale + px * side * 10 * scale, y - uy * 32 * scale + py * side * 10 * scale);
      g.lineTo(x - ux * 31 * scale, y - uy * 31 * scale); g.closePath(); g.fill(); }
    g.restore();
  }
  function drawSkillFx(g, e, layer = 'air') {
    if (e.t < 0) return;
    if (layer === 'floor' && !groundSkillFx(e)) return;
    if (layer === 'air' && groundSkillFx(e) && !['skCleave', 'skMageFireImpact', 'skMageMeteor', 'skMageBlink', 'skAssassinLunge', 'skAssassinFan', 'skPriestBuff', 'skPriestNova', 'skPriestHymn', 'skPriestSanctuary', 'skHunterRoll', 'skHunterBlast', 'skHunterRain', 'skHunterStorm'].includes(e.kind) && !e.stars) return;
    const p = e.t / e.life, fade = 1 - p, [sx, sy] = w2s(e.x, e.y), U = 62.2, V = 31.1;       // pixels per world unit along the ellipse's axes
    g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
    if (layer === 'air' && e.kind === 'skNova') { drawStarfall(g, e, 'air'); g.restore(); return; }
    if (e.kind === 'skNova') {
      const k = 1 - Math.pow(1 - Math.min(1, p * 1.6), 3), rx = U * e.r * k, ry = V * e.r * k, style = e.style;
      g.globalAlpha = fade * .3; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
      const gr = g.createRadialGradient(sx, sy, 2, sx, sy, Math.max(4, rx)); gr.addColorStop(0, e.glow + '00'); gr.addColorStop(.7, e.glow + '44'); gr.addColorStop(1, e.glow + 'aa');
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade; g.fillStyle = gr; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'source-over';
      const ring = () => { g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); };
      layers(g, [[22, OUTLINE, .3, 0], [16, e.glow, .5, 1], [8, e.core, .95, 0], [3, '#ffffff', 1, 0]], fade, p * .5, ring);
      if (style === 'warWhirl') {
        // Three steel blades circle the full damage radius, not merely the caster's feet.
        for (let blade = 0; blade < 3; blade++) {
          const end = e.t * 13 + blade * 2.094;
          layers(g, [[24, OUTLINE, .32, 0], [16, e.glow, .6, 1], [8, e.core, 1, 0], [3, '#ffffff', 1, 0]], fade, 0, () => {
            g.beginPath();
            for (let i = 0; i <= 13; i++) {
              const an = end - .95 + i * .95 / 13;
              const [x, y] = w2s(e.x + Math.cos(an) * e.r * k, e.y + Math.sin(an) * e.r * k, 33);
              i ? g.lineTo(x, y) : g.moveTo(x, y);
            }
          });
          const [tx, ty] = w2s(e.x + Math.cos(end) * e.r * k, e.y + Math.sin(end) * e.r * k, 33);
          g.globalAlpha = fade; g.fillStyle = '#ffffff'; g.beginPath(); g.moveTo(tx, ty - 10); g.lineTo(tx + 10, ty); g.lineTo(tx, ty + 10); g.lineTo(tx - 10, ty); g.fill();
        }
      } else if (style === 'mageStorm') {
        // Eight orbiting storm arms live on the floor plane and show the full five-unit hit area.
        for (let arm = 0; arm < 8; arm++) layers(g, [[15, OUTLINE, .3, 0], [9, e.glow, .55, 1], [3, e.core, 1, 0]], fade, 0, () => {
          g.beginPath();
          for (let i = 0; i <= 18; i++) {
            const f = .2 + i * .044, an = arm * .785 + e.t * 4 + f * 1.15;
            const x = sx + Math.cos(an) * rx * f, y = sy + Math.sin(an) * ry * f;
            i ? g.lineTo(x, y) : g.moveTo(x, y);
          }
        });
        for (let i = 0; i < 12; i++) {
          const an = i * 6.283 / 12 + e.t * 2, x = sx + Math.cos(an) * rx * .82, y = sy + Math.sin(an) * ry * .82;
          g.globalAlpha = fade * .9; g.fillStyle = i % 2 ? e.core : '#ffffff'; g.beginPath(); g.arc(x, y, 4, 0, 6.283); g.fill();
        }
      } else if (style === 'mageStarfield') {
        // A constellation map marks the whole distant field; falling stars are drawn in the air pass.
        for (let i = 0; i < 20; i++) {
          const an = i * 2.39996, f = Math.sqrt((i + .5) / 20) * .88;
          const x = sx + Math.cos(an) * rx * f, y = sy + Math.sin(an) * ry * f;
          g.globalAlpha = fade * .8; g.fillStyle = i % 3 ? e.core : '#ffffff';
          g.beginPath(); g.arc(x, y, i % 4 === 0 ? 4 : 2.5, 0, 6.283); g.fill();
          if (i % 3 === 0) { g.strokeStyle = e.glow; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x - 11, y); g.lineTo(x + 11, y); g.moveTo(x, y - 7); g.lineTo(x, y + 7); g.stroke(); }
        }
      } else if (style === 'assassinCyclone') {
        // The full hit radius stays on the ground plane, with six separate steel daggers.
        for (let blade = 0; blade < 6; blade++) {
          const an = blade * Math.PI / 3 + e.t * 13, r = e.r * Math.max(.15, k);
          const [x, y] = w2s(e.x + Math.cos(an) * r, e.y + Math.sin(an) * r, 6);
          const vx = -Math.sin(an), vy = Math.cos(an) * .52;
          layers(g, [[9, OUTLINE, .65, 0], [5, e.glow, .9, 1], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(x - vx * 25, y - vy * 25); g.lineTo(x + vx * 25, y + vy * 25);
          });
          g.globalAlpha = fade; g.fillStyle = '#f5efff'; g.beginPath();
          g.moveTo(x + vx * 30, y + vy * 30); g.lineTo(x + vy * 7, y - vx * 7);
          g.lineTo(x - vx * 8, y - vy * 8); g.lineTo(x - vy * 7, y + vx * 7); g.closePath(); g.fill();
        }
      } else if (style === 'spiral') {
        for (let arm = 0; arm < 4; arm++) layers(g, [[10, OUTLINE, .3, 0], [6, e.core, .9, 0], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); const a0 = e.t * 11 + arm * 1.571;
          for (let i = 0; i <= 14; i++) { const an = a0 + i * .09, f = k * (.35 + i * .045); i ? g.lineTo(sx + Math.cos(an) * rx * f, sy + Math.sin(an) * ry * f) : g.moveTo(sx + Math.cos(an) * rx * f, sy + Math.sin(an) * ry * f); }
        });
      } else if (style === 'cracks' || style === 'warSlam' || style === 'warTitan') {
        layers(g, [[9, '#2a1408', .8, 0], [4, e.glow, .95, 1], [1.8, '#ffffff', 1, 0]], Math.min(1, fade * 1.6), 0, () => {
          g.beginPath(); for (const c of e.cracks) { const len = Math.min(1, k * 1.1) * c.len; let px = sx, py = sy; g.moveTo(px, py); for (const [f, o] of c.zig) { if (f > len) break; const an = c.a + o; px = sx + Math.cos(an) * rx * f, py = sy + Math.sin(an) * ry * f; g.lineTo(px, py); } }
        });
        if (style === 'warSlam') {
          // Broken stone lifts just inside the impact edge; the ring remains the true radius.
          for (let i = 0; i < 14; i++) {
            const an = i * 6.283 / 14, [x, y] = w2s(e.x + Math.cos(an) * e.r * k * .84, e.y + Math.sin(an) * e.r * k * .84, 4 + 36 * Math.sin(Math.PI * p));
            const size = (7 + i % 3 * 4) * (1 - p * .6);
            g.globalAlpha = fade * .85; g.fillStyle = i % 2 ? '#7e6251' : '#b99467';
            g.beginPath(); g.moveTo(x, y - size); g.lineTo(x + size * .9, y + size * .4); g.lineTo(x - size * .8, y + size * .6); g.closePath(); g.fill();
          }
        } else if (style === 'warTitan') {
          // A second engraved circumference makes the capstone visibly larger than Ground Slam.
          layers(g, [[8, '#412709', .7, 0], [4, '#ffe27b', .95, 0], [1.5, '#ffffff', 1, 0]], fade, 0, () => {
            g.beginPath(); g.ellipse(sx, sy, rx * .75, ry * .75, 0, 0, 6.283);
          });
          for (let i = 0; i < 16; i++) {
            const an = i * 6.283 / 16, x = sx + Math.cos(an) * rx * .75, y = sy + Math.sin(an) * ry * .75;
            g.save(); g.translate(x, y); g.rotate(an); g.globalAlpha = fade;
            g.strokeStyle = '#fff6c8'; g.lineWidth = 3; g.beginPath(); g.moveTo(-8, -8); g.lineTo(0, 0); g.lineTo(8, -8); g.stroke(); g.restore();
          }
        }
      } else if (style === 'arrows') {
        g.globalAlpha = fade; g.strokeStyle = e.core; g.fillStyle = e.core; g.lineWidth = 3;
        for (let i = 0; i < 24; i++) { const an = i * 6.283 / 24, x = sx + Math.cos(an) * rx * k, y = sy + Math.sin(an) * ry * k;
          g.beginPath(); g.moveTo(x - Math.cos(an) * 24, y - Math.sin(an) * 24); g.lineTo(x, y); g.stroke();
          g.beginPath(); g.moveTo(x, y); g.lineTo(x - Math.cos(an - .4) * 13, y - Math.sin(an - .4) * 13); g.lineTo(x - Math.cos(an + .4) * 13, y - Math.sin(an + .4) * 13); g.closePath(); g.fill(); }
      } else {
        g.globalAlpha = fade * .7; g.strokeStyle = e.core; g.lineWidth = 2;
        for (let i = 0; i < 18; i++) { const an = i * 6.283 / 18 + e.a, r0 = .55 * k, r1 = k * 1.08; g.beginPath(); g.moveTo(sx + Math.cos(an) * rx * r0, sy + Math.sin(an) * ry * r0); g.lineTo(sx + Math.cos(an) * rx * r1, sy + Math.sin(an) * ry * r1); g.stroke(); }
      }
      if (e.stars) drawStarfall(g, e, 'floor');
    } else if (e.kind === 'skPriestMend' || e.kind === 'skPriestPrayer' || e.kind === 'skPriestHymn') {
      const targets = e.targets || [], hymn = e.kind === 'skPriestHymn', prayer = e.kind === 'skPriestPrayer';
      const origin = w2s(e.x, e.y, 65), reach = Math.min(1, e.t / (hymn ? .55 : .28));
      if (layer === 'floor') {
        // The hymn's broad reach belongs on the ground; only actual healed players receive light above it.
        const ring = Math.min(1, p * 2) * e.r;
        layers(g, [[8, OUTLINE, .27, 0], [4, e.glow, .43, 1], [1.5, e.core, .75, 0]], fade, 0, () => {
          g.beginPath(); g.ellipse(sx, sy, U * ring, V * ring, 0, 0, 6.283);
        });
      } else {
        const [ox, oy] = origin;
        if (prayer || hymn) {
          for (let i = 0; i < (hymn ? 12 : 6); i++) {
            const an = i * 6.283 / (hymn ? 12 : 6) + e.t * (hymn ? .7 : 1.8), rr = 30 + (hymn ? 30 : 13) * Math.sin(Math.PI * Math.min(1, p));
            g.globalAlpha = fade * .72; g.fillStyle = i % 2 ? e.core : e.glow;
            g.beginPath(); g.arc(ox + Math.cos(an) * rr, oy + Math.sin(an) * rr * .55 - 13 * p, hymn ? 4 : 3, 0, 6.283); g.fill();
          }
        }
        targets.forEach((target, i) => {
          const [tx, ty] = w2s(target.x, target.y, 65), same = Math.hypot(tx - ox, ty - oy) < 6;
          if (!same) layers(g, [[prayer || hymn ? 17 : 18, OUTLINE, .45, 0], [prayer || hymn ? 10 : 11, e.glow, .75, 1], [prayer || hymn ? 4 : 5, e.core, 1, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(ox, oy - 8); g.quadraticCurveTo((ox + tx) / 2, Math.min(oy, ty) - (hymn ? 100 : prayer ? 67 : 43), ox + (tx - ox) * reach, oy + (ty - oy) * reach - 8);
          });
          const q = Math.max(0, (e.t - i * (hymn ? .1 : .05)) / (hymn ? .7 : .42));
          if (q <= 1) {
            layers(g, [[9, OUTLINE, .25, 0], [5, e.glow, .72, 1], [2, e.core, 1, 0]], (1 - q) * fade, 0, () => {
              g.beginPath(); g.ellipse(tx, ty + 45 * (1 - q), 23 + q * (hymn ? 37 : 20), 11 + q * (hymn ? 16 : 9), 0, 0, 6.283);
            });
            if (hymn) {
              const gr = g.createLinearGradient(tx, ty - 126, tx, ty + 28);
              gr.addColorStop(0, e.glow + '00'); gr.addColorStop(1, e.core + '77');
              g.globalAlpha = (1 - q) * .28; g.fillStyle = gr; g.fillRect(tx - 25, ty - 126, 50, 154);
            }
            if (prayer || hymn) layers(g, [[7, OUTLINE, .35, 0], [3.5, e.core, 1, 0]], fade * (1 - q * .5), 0, () => {
              g.beginPath(); g.moveTo(tx - 13, ty); g.lineTo(tx + 13, ty);
              g.moveTo(tx, ty - 13); g.lineTo(tx, ty + 13);
            });
          }
        });
        if (!targets.length) { g.globalAlpha = fade * .5; g.strokeStyle = e.glow; g.lineWidth = 3;
          g.beginPath(); g.arc(ox, oy, 20 + p * 18, 0, 6.283); g.stroke(); }
      }
    } else if (e.kind === 'skPriestSmite' || e.kind === 'skPriestSearing') {
      const searing = e.kind === 'skPriestSearing', [x, y] = w2s(e.x, e.y, 48), land = Math.min(1, e.t / .19);
      const top = y - (searing ? 290 : 360), head = top + (y - top) * land;
      layers(g, [[searing ? 28 : 23, OUTLINE, .38, 0], [searing ? 19 : 15, e.glow, .7, 1], [searing ? 8 : 6, e.core, 1, 0], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
        g.beginPath(); g.moveTo(x + (searing ? 38 : -29) * (1 - land), top); g.lineTo(x, head);
      });
      if (e.t >= .14) {
        const q = (e.t - .14) / (e.life - .14);
        for (let i = 0; i < (searing ? 10 : 8); i++) {
          const an = i * 6.283 / (searing ? 10 : 8), r = 12 + q * (searing ? 75 : 57);
          layers(g, [[7, e.glow, .6, 1], [2.5, e.core, 1, 0]], (1 - q) * fade, 0, () => {
            g.beginPath(); g.moveTo(x + Math.cos(an) * r * .45, y + Math.sin(an) * r * .45);
            g.lineTo(x + Math.cos(an) * r, y + Math.sin(an) * r);
          });
        }
      }
      if (searing && e.heal > 0) {
        const [tx, ty] = w2s(e.to.x, e.to.y, 62), travel = Math.min(1, Math.max(0, (e.t - .18) / .34));
        if (travel > 0) layers(g, [[17, OUTLINE, .35, 0], [11, '#57db9b', .72, 1], [4, '#d8ffe4', 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo((x + tx) / 2, Math.min(y, ty) - 78, x + (tx - x) * travel, y + (ty - y) * travel);
        });
      }
    } else if (e.kind === 'skPriestBuff') {
      const ward = e.style === 'wardoflight', color = ward ? '#93dfff' : '#ffcc6d', r = e.r * Math.min(1, p * 2.3);
      if (layer === 'floor') {
        g.globalAlpha = fade * .1; g.fillStyle = color; g.beginPath(); g.ellipse(sx, sy, U * r, V * r, 0, 0, 6.283); g.fill();
        layers(g, [[10, OUTLINE, .28, 0], [6, color, .67, 1], [2.5, e.core, .95, 0]], fade, p * .35, () => {
          g.beginPath(); g.ellipse(sx, sy, U * r, V * r, 0, 0, 6.283);
        });
      } else {
        const all = [{ x: e.x, y: e.y }, ...(e.targets || [])];
        for (const target of all) {
          const [x, y] = w2s(target.x, target.y, 64), grow = Math.min(1, p * 3);
          if (target !== all[0]) layers(g, [[8, color, .4, 1], [2.5, e.core, .9, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(sx, sy - 68); g.lineTo(x, y);
          });
          layers(g, [[12, OUTLINE, .4, 0], [7, color, .75, 1], [2.5, e.core, 1, 0]], fade, 0, () => {
            g.beginPath();
            if (ward) { g.moveTo(x, y - 48 * grow); g.lineTo(x + 34 * grow, y - 26 * grow); g.lineTo(x + 26 * grow, y + 17 * grow); g.lineTo(x, y + 39 * grow); g.lineTo(x - 26 * grow, y + 17 * grow); g.lineTo(x - 34 * grow, y - 26 * grow); g.closePath(); }
            else { for (let i = 0; i <= 8; i++) { const an = i * 6.283 / 8; const xx = x + Math.cos(an) * 44 * grow, yy = y + Math.sin(an) * 44 * grow; i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); } g.moveTo(x - 18, y); g.lineTo(x + 18, y); g.moveTo(x, y - 18); g.lineTo(x, y + 18); }
          });
        }
      }
    } else if (e.kind === 'skPriestNova') {
      const grow = 1 - Math.pow(1 - Math.min(1, p * 2.5), 3);
      if (layer === 'floor') {
        for (const [r, color, delay] of [[e.r, '#ffcb65', 0], [e.healR, '#8dffc9', .12]]) {
          const q = Math.max(0, Math.min(1, (e.t - delay) / (e.life - delay)));
          if (e.t < delay) continue;
          const k = 1 - Math.pow(1 - Math.min(1, q * 2.5), 3), f = 1 - q;
          g.globalAlpha = f * (r === e.r ? .2 : .12); g.fillStyle = color;
          g.beginPath(); g.ellipse(sx, sy, U * r * k, V * r * k, 0, 0, 6.283); g.fill();
          layers(g, [[14, OUTLINE, .3, 0], [8, color, .7, 1], [3, '#ffffff', .95, 0]], f, q * .4, () => {
            g.beginPath(); g.ellipse(sx, sy, U * r * k, V * r * k, 0, 0, 6.283);
          });
        }
      } else {
        const n = e.style === 'wrath' ? 14 : 9;
        for (let i = 0; i < n; i++) {
          const an = i * 6.283 / n, r = e.r * (.5 + (i % 3) * .22) * grow;
          const [x, y] = w2s(e.x + Math.cos(an) * r, e.y + Math.sin(an) * r, 32);
          const h = (e.style === 'wrath' ? 150 : 95) * Math.sin(Math.PI * Math.min(1, p));
          layers(g, [[11, e.glow, .27, 1], [4, e.core, .76, 0]], fade * .65, 0, () => {
            g.beginPath(); g.moveTo(x, y - h); g.lineTo(x, y - 5);
          });
        }
        for (const target of e.targets || []) {
          const [x, y] = w2s(target.x, target.y, 46);
          layers(g, [[12, '#327e63', .3, 0], [7, '#8dffc9', .7, 1], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
            g.beginPath(); g.arc(x, y, 19 + p * 28, 0, 6.283);
          });
        }
      }
    } else if (e.kind === 'skPriestSanctuary') {
      if (layer === 'floor') {
        const r = 1.1 * Math.min(1, p * 3);
        layers(g, [[10, OUTLINE, .25, 0], [6, e.glow, .7, 1], [2, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); g.ellipse(sx, sy, U * r, V * r, 0, 0, 6.283);
        });
        for (let i = 0; i < 8; i++) { const an = i * .785;
          g.globalAlpha = fade * .6; g.strokeStyle = e.glow; g.lineWidth = 3; g.beginPath();
          g.moveTo(sx + Math.cos(an) * 25, sy + Math.sin(an) * 12);
          g.lineTo(sx + Math.cos(an) * 58, sy + Math.sin(an) * 29); g.stroke(); }
      } else {
        const [x, y] = w2s(e.x, e.y, 69), h = 200 * Math.min(1, p * 2);
        const gr = g.createLinearGradient(x, y - h, x, y + 40); gr.addColorStop(0, e.glow + '00'); gr.addColorStop(1, e.core + 'aa');
        g.globalAlpha = fade * .43; g.fillStyle = gr; g.beginPath(); g.moveTo(x - 23, y - h); g.lineTo(x + 23, y - h); g.lineTo(x + 65, y + 35); g.lineTo(x - 65, y + 35); g.closePath(); g.fill();
        layers(g, [[12, OUTLINE, .3, 0], [7, e.glow, .65, 1], [2, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); g.arc(x, y - 58, 38 + p * 15, 0, 6.283);
        });
      }
    } else if (e.kind === 'skPriestCrown') {
      const [x, y] = w2s(e.x, e.y, 115);
      for (let i = 0; i < 12; i++) { const an = i * 6.283 / 12, len = 50 + Math.sin(Math.PI * p) * 96;
        layers(g, [[10, OUTLINE, .3, 0], [6, e.glow, .55, 1], [2, '#ffffff', .9, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x + Math.cos(an) * 27, y + Math.sin(an) * 18);
          g.lineTo(x + Math.cos(an) * len, y + Math.sin(an) * len * .55);
        });
      }
    } else if (e.kind === 'skHunterDraw') {
      const [x, y] = w2s(e.x, e.y, 58), [dx, dy] = projDir(Math.cos(e.a), Math.sin(e.a));
      const side = [-dy, dx], pull = 22 * (1 - Math.min(1, p * 3));
      layers(g, [[11, OUTLINE, .5, 0], [6, e.glow, .7, 1], [2.5, e.core, 1, 0]], fade, 0, () => {
        g.beginPath(); g.moveTo(x + dx * 28 + side[0] * 25, y + dy * 28 + side[1] * 25);
        g.quadraticCurveTo(x + dx * (65 - pull), y + dy * (65 - pull), x + dx * 28 - side[0] * 25, y + dy * 28 - side[1] * 25);
      });
      const count = e.count || 1;
      for (let i = 0; i < count; i++) {
        const an = e.a + (i - (count - 1) / 2) * e.spread / Math.max(1, count - 1);
        const [ux, uy] = projDir(Math.cos(an), Math.sin(an)), ax = x + ux * (42 + p * 48), ay = y + uy * (42 + p * 48);
        g.globalAlpha = fade; drawHunterArrow(g, ax, ay, ux, uy,
          e.style === 'powershot' ? 1.15 : .8, e.core);
      }
    } else if (e.kind === 'skHunterImpact') {
      const [x, y] = w2s(e.x, e.y, 43), power = e.style === 'powershot', pierce = e.style === 'piercingarrow';
      layers(g, [[power ? 19 : 12, OUTLINE, .4, 0], [power ? 12 : 7, e.glow, .7, 1], [3, e.core, 1, 0]], fade, 0, () => {
        g.beginPath(); g.arc(x, y, (power ? 23 : 14) + p * (power ? 52 : 29), 0, 6.283);
        for (let i = 0; i < (pierce ? 4 : 8); i++) { const an = i * 6.283 / (pierce ? 4 : 8);
          g.moveTo(x + Math.cos(an) * (17 + p * 20), y + Math.sin(an) * (17 + p * 20));
          g.lineTo(x + Math.cos(an) * (36 + p * 48), y + Math.sin(an) * (36 + p * 48)); }
      });
      if (pierce) { g.globalAlpha = fade; drawHunterArrow(g, x + p * 72, y, 1, 0, .75, e.core); }
    } else if (e.kind === 'skHunterBlast') {
      const grow = 1 - Math.pow(1 - Math.min(1, p * 2.5), 3), rx = U * e.r * grow, ry = V * e.r * grow;
      if (layer === 'floor') {
        g.globalAlpha = fade * .32; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
        layers(g, [[17, '#542817', .55, 0], [9, e.glow, .85, 1], [3, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); });
      } else { const [x, y] = w2s(e.x, e.y, 42);
        for (let i = 0; i < 12; i++) { const an = i * 2.39996, d = 17 + p * 115;
          g.globalAlpha = fade * .8; g.fillStyle = i % 3 ? e.glow : '#fff6c8'; g.beginPath();
          g.arc(x + Math.cos(an) * d, y + Math.sin(an) * d * .65 - 30 * (1 - p), 4 + i % 3 * 2, 0, 6.283); g.fill(); }
      }
    } else if (e.kind === 'skHunterRoll') {
      const who = e.actor === Online.id ? hero : remotePlayers.get(e.actor);
      const [bx, by] = w2s(e.x, e.y, 4), [tx, ty] = who ? w2s(who.x, who.y, 4) : [bx, by];
      if (layer === 'floor') {
        layers(g, [[22, '#233223', .32, 0], [10, e.glow, .38, 1], [3, e.core, .72, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty); });
        for (let i = 0; i < 5; i++) { const f = (i + 1) / 6;
          g.globalAlpha = fade * (1 - f) * .55; g.fillStyle = e.glow; g.beginPath();
          g.ellipse(bx + (tx - bx) * f, by + (ty - by) * f, 23 - i * 2, 8 - i, 0, 0, 6.283); g.fill(); }
      } else if (who) { const [x, y] = w2s(who.x, who.y, 58);
        layers(g, [[8, OUTLINE, .35, 0], [4, e.glow, .7, 1], [2, e.core, .9, 0]], fade, 0, () => {
          g.beginPath(); g.arc(x, y, 36, -2.2 + p * 8, .9 + p * 8); });
      }
    } else if (e.kind === 'skHunterRain') {
      if (layer === 'floor') {
        g.globalAlpha = fade * .14; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, U * e.r, V * e.r, 0, 0, 6.283); g.fill();
        layers(g, [[10, OUTLINE, .4, 0], [5, e.glow, .8, 1], [2, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.ellipse(sx, sy, U * e.r, V * e.r, 0, 0, 6.283);
          g.moveTo(sx - 25, sy); g.lineTo(sx + 25, sy); g.moveTo(sx, sy - 13); g.lineTo(sx, sy + 13); });
        for (const ar of e.arrows) { const q = (e.t - ar.delay) / .33;
          if (q < 1 || q > 1.65) continue; const [x, y] = w2s(ar.x, ar.y);
          g.globalAlpha = (1.65 - q) * .55; g.fillStyle = e.core; g.beginPath(); g.ellipse(x, y, 10 + (q - 1) * 12, 5 + (q - 1) * 6, 0, 0, 6.283); g.fill(); }
      } else for (const ar of e.arrows) { const q = (e.t - ar.delay) / .33; if (q < 0 || q > 1) continue;
        const [x, y] = w2s(ar.x, ar.y, 42), fall = 1 - q;
        layers(g, [[8, OUTLINE, .35, 0], [4, e.glow, .5, 1]], 1, 0, () => {
          g.beginPath(); g.moveTo(x + 85 * fall, y - 230 * fall - 80); g.lineTo(x, y - 230 * fall); });
        drawHunterArrow(g, x, y - 230 * fall, -.35, 1, .65, e.core);
      }
    } else if (e.kind === 'skHunterStorm') {
      const reach = e.r * (1 - Math.pow(1 - Math.min(1, p * 2.5), 3));
      if (layer === 'floor') {
        g.globalAlpha = fade * .12; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, U * reach, V * reach, 0, 0, 6.283); g.fill();
        layers(g, [[15, OUTLINE, .3, 0], [8, e.glow, .65, 1], [3, e.core, .9, 0]], fade, 0, () => {
          g.beginPath(); g.ellipse(sx, sy, U * reach, V * reach, 0, 0, 6.283); });
      } else for (let i = 0; i < (e.capstone ? 48 : 36); i++) {
        const an = i * 2.39996, fraction = .38 + (i % 5) * .14;
        const dist = reach * fraction, xw = e.x + Math.cos(an) * dist, yw = e.y + Math.sin(an) * dist;
        const [x, y] = w2s(xw, yw, 30 + i % 4 * 8);
        g.globalAlpha = fade * (.6 + .4 * fraction);
        { const [ux, uy] = projDir(Math.cos(an), Math.sin(an)); drawHunterArrow(g, x, y, ux, uy, i % 3 ? .56 : .7, i % 4 ? e.core : '#fff9dd'); }
      }
    } else if (e.kind === 'skHunterBuff') {
      const [x, y] = w2s(e.x, e.y, 83), size = 30 + p * 30;
      if (e.style === 'huntersmark') {
        layers(g, [[10, OUTLINE, .45, 0], [5, e.glow, .8, 1], [2, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.arc(x, y, size, 0, 6.283);
          for (const an of [0, 1.571, 3.142, 4.713]) { g.moveTo(x + Math.cos(an) * (size + 7), y + Math.sin(an) * (size + 7));
            g.lineTo(x + Math.cos(an) * (size + 24), y + Math.sin(an) * (size + 24)); } });
      } else if (e.style === 'rapidfire') {
        for (let i = 0; i < 5; i++) { const yy = y - 64 + i * 29;
          layers(g, [[10, OUTLINE, .4, 0], [5, e.glow, .75, 1], [2, e.core, 1, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(x - 68 - p * 60, yy); g.lineTo(x + 20 + p * 60, yy);
            g.lineTo(x + p * 60, yy - 11); g.moveTo(x + 20 + p * 60, yy); g.lineTo(x + p * 60, yy + 11); }); }
      } else {
        layers(g, [[11, OUTLINE, .42, 0], [6, e.glow, .78, 1], [2.5, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x - size * 1.5, y); g.quadraticCurveTo(x, y - size, x + size * 1.5, y);
          g.quadraticCurveTo(x, y + size, x - size * 1.5, y); g.moveTo(x + 12, y); g.arc(x, y, 12, 0, 6.283); });
      }
    } else if (e.kind === 'skAssassinCast') {
      const n = e.count || 3, ring = e.spread >= 6.27, reach = .5 + Math.min(1, p * 2.5) * 1.2;
      for (let i = 0; i < n; i++) {
        const an = e.a + (ring ? i * 6.283 / n : (i - (n - 1) / 2) * e.spread / Math.max(1, n - 1));
        const dx = Math.cos(an), dy = Math.sin(an), [x, y] = w2s(e.x + dx * reach, e.y + dy * reach, 48), [ux, uy] = projDir(dx, dy);
        layers(g, [[5, e.glow, .55, 1], [2, e.core, .9, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(sx + ux * 19, sy - 48 + uy * 19); g.lineTo(x, y);
        });
        g.globalAlpha = fade; drawAssassinKnife(g, x, y, ux, uy, ring ? .67 : .8, e.core);
      }
    } else if (e.kind === 'skAssassinImpact') {
      const [x, y] = w2s(e.x, e.y, 43);
      for (let i = 0; i < 5; i++) {
        const an = i * 2.399, d = 10 + p * 29;
        layers(g, [[7, e.glow, .65, 1], [2.5, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x + Math.cos(an) * d * .35, y + Math.sin(an) * d * .35);
          g.lineTo(x + Math.cos(an) * d, y + Math.sin(an) * d);
        });
      }
    } else if (e.kind === 'skAssassinLunge') {
      const who = e.actor === Online.id ? hero : remotePlayers.get(e.actor);
      const [bx, by] = w2s(e.x, e.y, 5), [tx, ty] = who ? w2s(who.x, who.y, 5) : [bx, by];
      const moved = Math.hypot(tx - bx, ty - by) > 6;
      if (layer === 'floor') {
        layers(g, [[18, '#251438', .52, 0], [9, e.glow, .46, 1], [3, e.core, .85, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty);
        });
        for (let i = 0; i < 4; i++) {
          const f = (i + .5) / 4, x = bx + (tx - bx) * f, y = by + (ty - by) * f;
          g.globalAlpha = fade * .65; g.fillStyle = e.glow; g.beginPath(); g.ellipse(x, y, 12, 5, 0, 0, 6.283); g.fill();
        }
      } else if (moved) {
        const [x, y] = w2s(who.x, who.y, 48), dx = Math.cos(e.a), dy = Math.sin(e.a) * .55;
        layers(g, [[17, OUTLINE, .5, 0], [10, e.glow, .7, 1], [4, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x - dx * 44 + dy * 20, y - dy * 44 - dx * 20);
          g.lineTo(x + dx * 44 - dy * 20, y + dy * 44 + dx * 20);
        });
      }
    } else if (e.kind === 'skAssassinFlurry') {
      const [x, y] = w2s(e.x, e.y, 47), an = e.index * 1.571 + .55, dx = Math.cos(an), dy = Math.sin(an), len = 52;
      layers(g, [[17, OUTLINE, .5, 0], [10, e.glow, .75, 1], [4, '#ffffff', 1, 0]], fade, 0, () => {
        g.beginPath(); g.moveTo(x - dx * len, y - dy * len); g.lineTo(x + dx * len, y + dy * len);
      });
      g.globalAlpha = fade; g.fillStyle = e.core; g.font = 'bold 20px sans-serif'; g.textAlign = 'center';
      g.fillText(String(e.index + 1), x + Math.cos(an + 1.571) * 58, y + Math.sin(an + 1.571) * 58);
    } else if (e.kind === 'skAssassinAssassinate') {
      const [x, y] = w2s(e.x, e.y, 45), charge = Math.min(1, e.t / .23), blow = Math.max(0, (e.t - .22) / .5);
      if (e.t < .23) {
        layers(g, [[8, OUTLINE, .5, 0], [4, e.glow, .9, 1], [2, e.core, 1, 0]], charge, 0, () => {
          g.beginPath(); g.arc(x, y, 67 - charge * 37, 0, 6.283);
          for (let i = 0; i < 4; i++) { const an = i * 1.571; g.moveTo(x + Math.cos(an) * 42, y + Math.sin(an) * 42); g.lineTo(x + Math.cos(an) * 23, y + Math.sin(an) * 23); }
        });
      } else {
        layers(g, [[32, OUTLINE, .6, 0], [21, e.glow, .7, 1], [9, e.core, 1, 0], [3, '#ffffff', 1, 0]], 1 - blow, 0, () => {
          g.beginPath(); g.moveTo(x - 96, y + 60); g.lineTo(x + 96, y - 60);
        });
        g.globalAlpha = (1 - blow) * .45; g.fillStyle = e.glow; g.beginPath(); g.arc(x, y, 25 + blow * 55, 0, 6.283); g.fill();
      }
    } else if (e.kind === 'skAssassinBuff') {
      const [x, y] = w2s(e.x, e.y, 56), rise = Math.min(1, p * 2.4);
      if (e.style === 'dodge') {
        for (const side of [-1, 1]) for (let i = 0; i < 3; i++) {
          const ox = side * (27 + i * 16 + rise * 12), oy = -i * 25;
          layers(g, [[8, OUTLINE, .45, 0], [4, e.glow, .9, 1], [2, e.core, 1, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(x + ox - side * 10, y + oy - 10); g.lineTo(x + ox, y + oy);
            g.lineTo(x + ox - side * 10, y + oy + 10);
          });
        }
      } else if (e.style === 'haste') {
        for (let i = 0; i < 5; i++) {
          const ox = (i - 2) * 22, top = 54 + rise * (25 + i % 2 * 20);
          layers(g, [[12, OUTLINE, .45, 0], [6, e.glow, .7, 1], [2, e.core, 1, 0]], fade, 0, () => {
            g.beginPath(); g.moveTo(x + ox - 15, y + 48); g.quadraticCurveTo(x + ox + 20, y - top * .5, x + ox, y - top);
          });
        }
      } else {
        layers(g, [[13, OUTLINE, .45, 0], [7, e.glow, .7, 1], [2, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.arc(x, y, 45 - rise * 19, 0, 6.283);
          g.moveTo(x - 58, y); g.lineTo(x - 22, y); g.moveTo(x + 22, y); g.lineTo(x + 58, y);
          g.moveTo(x, y - 58); g.lineTo(x, y - 22); g.moveTo(x, y + 22); g.lineTo(x, y + 58);
        });
      }
    } else if (e.kind === 'skAssassinFan') {
      const start = e.a - e.arc / 2, [ox, oy] = w2s(e.x, e.y, 5);
      if (layer === 'floor') {
        g.globalAlpha = fade * .17; g.fillStyle = e.glow; g.beginPath(); g.moveTo(ox, oy);
        for (let i = 0; i <= 24; i++) { const an = start + e.arc * i / 24, [x, y] = w2s(e.x + Math.cos(an) * e.r, e.y + Math.sin(an) * e.r, 5); g.lineTo(x, y); }
        g.closePath(); g.fill();
        layers(g, [[4, e.glow, .7, 1], [1.5, e.core, .9, 0]], fade, 0, () => {
          g.beginPath(); for (let i = 0; i <= 24; i++) { const an = start + e.arc * i / 24, [x, y] = w2s(e.x + Math.cos(an) * e.r, e.y + Math.sin(an) * e.r, 5); i ? g.lineTo(x, y) : g.moveTo(x, y); }
        });
      } else {
        for (let i = 0; i < 15; i++) {
          const delay = i * .027, q = (e.t - delay) / .43; if (q < 0 || q > 1) continue;
          const an = start + e.arc * (i + .5) / 15, r = e.r * Math.min(1, q * 1.25);
          const [x, y] = w2s(e.x + Math.cos(an) * r, e.y + Math.sin(an) * r, 38);
          const [bx, by] = w2s(e.x + Math.cos(an) * Math.max(0, r - .65), e.y + Math.sin(an) * Math.max(0, r - .65), 38);
          layers(g, [[11, OUTLINE, .45, 0], [6, e.glow, .62, 1], [2.5, e.core, 1, 0]], (1 - q) * fade, 0, () => { g.beginPath(); g.moveTo(bx, by); g.lineTo(x, y); });
          g.globalAlpha = (1 - q) * fade; drawAssassinKnife(g, x, y, Math.cos(an), Math.sin(an) * .55, .65, i % 2 ? '#efe4ff' : '#ffb7dc');
        }
      }
    } else if (e.kind === 'skMageVolley') {
      const n = e.count || 2, spread = e.spread || .28, reach = 48 + Math.min(1, p * 3) * 90;
      for (let i = 0; i < n; i++) {
        const an = e.a + (i - (n - 1) / 2) * spread / Math.max(1, n - 1), dx = Math.cos(an), dy = Math.sin(an);
        const [x, y] = w2s(e.x + dx * reach / 62, e.y + dy * reach / 62, 48), [ux, uy] = projDir(dx, dy);
        layers(g, [[15, OUTLINE, .35, 0], [10, e.glow, .6, 1], [4, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(x - ux * 34, y - uy * 34); g.lineTo(x + ux * 14, y + uy * 14);
        });
        g.globalAlpha = fade; g.fillStyle = '#ffffff'; g.beginPath(); g.arc(x, y, n === 2 ? 5 : 3.5, 0, 6.283); g.fill();
      }
    } else if (e.kind === 'skMageFireCast') {
      const [x, y] = w2s(e.x, e.y, 68), r = 20 + 16 * Math.sin(Math.min(1, p * 2) * Math.PI);
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade;
      const fire = g.createRadialGradient(x, y, 2, x, y, r * 2); fire.addColorStop(0, '#ffffff'); fire.addColorStop(.3, e.core); fire.addColorStop(.7, e.glow + 'bb'); fire.addColorStop(1, e.glow + '00');
      g.fillStyle = fire; g.beginPath(); g.arc(x, y, r * 2, 0, 6.283); g.fill();
      for (let i = 0; i < 6; i++) {
        const an = i * 1.047 + e.t * 6; g.fillStyle = i % 2 ? e.core : '#ffffff'; g.globalAlpha = fade * .8;
        g.beginPath(); g.arc(x + Math.cos(an) * r, y + Math.sin(an) * r * .6, 3, 0, 6.283); g.fill();
      }
    } else if (e.kind === 'skMageBoltImpact') {
      const r = (e.style === 'twinbolt' ? 28 : 21) * (1 - p * .35);
      for (let i = 0; i < 6; i++) {
        const an = i * 1.047 + .2, [x, y] = w2s(e.x, e.y, 40);
        layers(g, [[8, e.glow, .55, 1], [3, e.core, 1, 0]], fade, 0, () => { g.beginPath(); g.moveTo(x + Math.cos(an) * 6, y + Math.sin(an) * 6); g.lineTo(x + Math.cos(an) * r, y + Math.sin(an) * r); });
      }
    } else if (e.kind === 'skMageWard') {
      const rise = 1 - Math.pow(1 - Math.min(1, p * 3), 3), [x, y] = w2s(e.x, e.y, 72);
      g.globalAlpha = fade * .12; g.fillStyle = e.glow; g.beginPath(); g.ellipse(x, y, 58 * rise, 86 * rise, 0, 0, 6.283); g.fill();
      layers(g, [[16, OUTLINE, .3, 0], [9, e.glow, .65, 1], [3, e.core, .95, 0]], fade, 0, () => {
        g.beginPath(); for (let i = 0; i <= 8; i++) { const an = i * 6.283 / 8, px = x + Math.cos(an) * 60 * rise, py = y + Math.sin(an) * 83 * rise; i ? g.lineTo(px, py) : g.moveTo(px, py); }
      });
    } else if (e.kind === 'skMageBlink') {
      const who = e.actor === Online.id ? hero : remotePlayers.get(e.actor), to = who || { x: e.x, y: e.y };
      const [bx, by] = w2s(e.x, e.y, 6), [tx, ty] = w2s(to.x, to.y, 6), moved = Math.hypot(tx - bx, ty - by) > 8;
      if (layer === 'floor') {
        for (const [x, y, scale] of [[bx, by, 1], ...(moved ? [[tx, ty, 1.2]] : [])]) {
          layers(g, [[8, OUTLINE, .28, 0], [5, e.glow, .7, 1], [2, e.core, 1, 0]], fade, p * .45, () => { g.beginPath(); g.ellipse(x, y, 25 * scale + p * 10, 12 * scale + p * 5, 0, 0, 6.283); });
        }
      } else if (moved) {
        layers(g, [[16, e.glow, .25, 1], [4, e.core, .8, 0]], fade, 0, () => { g.beginPath(); g.moveTo(bx, by - 48); g.lineTo(tx, ty - 48); });
        for (const [x, y] of [[bx, by], [tx, ty]]) {
          g.globalAlpha = fade * .65; g.strokeStyle = e.core; g.lineWidth = 2;
          g.beginPath(); g.moveTo(x - 12, y - 88); g.lineTo(x, y - 105); g.lineTo(x + 12, y - 88); g.stroke();
        }
      }
    } else if (e.kind === 'skMageLightning') {
      const pts = e.path.map(q => w2s(q.x, q.y, 58)), strength = Math.min(1, Math.max(0, e.t / .06)) * fade;
      layers(g, [[24, OUTLINE, .3, 0], [16, e.glow, .6, 1], [7, e.core, 1, 0], [2.5, '#ffffff', 1, 0]], strength, p * .3, () => { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); });
      for (let i = 2; i < pts.length - 1; i += 2) {
        const [x, y] = pts[i], side = i % 4 ? 1 : -1;
        layers(g, [[4, e.glow, .7, 1], [1.5, '#ffffff', 1, 0]], strength, 0, () => { g.beginPath(); g.moveTo(x, y); g.lineTo(x + side * 25, y - 18); g.lineTo(x + side * 38, y - 9); });
      }
    } else if (e.kind === 'skMageDrain') {
      const [ax, ay] = w2s(e.from.x, e.from.y, 64), [bx, by] = w2s(e.to.x, e.to.y, 64);
      layers(g, [[20, OUTLINE, .28, 0], [12, e.glow, .52, 1], [4, e.core, .9, 0]], fade, 0, () => { g.beginPath(); g.moveTo(ax, ay); g.bezierCurveTo(ax, ay - 65, bx, by - 65, bx, by); });
      for (let i = 0; i < 7; i++) {
        const q = (e.t * 2.4 + i / 7) % 1, x = (1 - q) ** 3 * ax + 3 * (1 - q) ** 2 * q * ax + 3 * (1 - q) * q ** 2 * bx + q ** 3 * bx;
        const y = (1 - q) ** 3 * ay + 3 * (1 - q) ** 2 * q * (ay - 65) + 3 * (1 - q) * q ** 2 * (by - 65) + q ** 3 * by;
        g.globalAlpha = fade * .9; g.fillStyle = i % 2 ? e.core : '#ffffff'; g.beginPath(); g.arc(x, y, 4 + i % 3, 0, 6.283); g.fill();
      }
      if (e.heal > 0) { g.strokeStyle = '#8effa8'; g.lineWidth = 3; g.globalAlpha = fade; g.beginPath(); g.arc(bx, by, 19 + p * 22, 0, 6.283); g.stroke(); }
    } else if (e.kind === 'skCleave') {
      // A broad blade swing follows the actual server cone. The subdued sector shows reach;
      // the moving, layered steel edge carries the attack without covering its targets.
      const start = e.a - e.arc / 2, sweep = Math.min(1, Math.max(0, (e.t - .045) / .27));
      const eased = 1 - Math.pow(1 - sweep, 3), tip = start + e.arc * eased;
      const [ox, oy] = w2s(e.x, e.y, 5), sectorFade = Math.min(1, e.t / .08) * Math.max(0, 1 - p);
      if (layer === 'floor') {
        g.globalAlpha = sectorFade * .28; g.fillStyle = e.glow; g.beginPath(); g.moveTo(ox, oy);
        for (let i = 0; i <= 28; i++) {
          const an = start + e.arc * i / 28, [x, y] = w2s(e.x + Math.cos(an) * e.r, e.y + Math.sin(an) * e.r, 5);
          g.lineTo(x, y);
        }
        g.closePath(); g.fill();
        g.globalAlpha = sectorFade * .65; g.strokeStyle = e.glow; g.lineWidth = 2;
        for (const an of [start, start + e.arc]) {
          const [x, y] = w2s(e.x + Math.cos(an) * e.r, e.y + Math.sin(an) * e.r, 5);
          g.beginPath(); g.moveTo(ox, oy); g.lineTo(x, y); g.stroke();
        }
      }
      if (layer === 'air' && sweep > 0 && e.t < .52) {
        const bladeFade = Math.min(1, sweep * 5) * Math.max(0, 1 - Math.max(0, e.t - .31) / .21);
        for (const [radius, width, delay] of [[1, 0, 0], [.76, .9, .14]]) {
          const end = start + e.arc * Math.max(0, eased - delay), trail = end - start;
          layers(g, [[32 - width * 9, OUTLINE, .46, 0], [23 - width * 7, e.glow, .62, 1],
            [12 - width * 4, e.core, .95, 0], [4, '#ffffff', 1, 0]], bladeFade, 0, () => {
            g.beginPath();
            for (let i = 0; i <= 20; i++) {
              const an = end - trail + trail * i / 20;
              const [x, y] = w2s(e.x + Math.cos(an) * e.r * radius, e.y + Math.sin(an) * e.r * radius, 35);
              i ? g.lineTo(x, y) : g.moveTo(x, y);
            }
          });
        }
        const [tx, ty] = w2s(e.x + Math.cos(tip) * e.r, e.y + Math.sin(tip) * e.r, 35);
        g.globalCompositeOperation = 'lighter'; g.globalAlpha = bladeFade;
        const flare = g.createRadialGradient(tx, ty, 2, tx, ty, 35);
        flare.addColorStop(0, '#ffffff'); flare.addColorStop(.35, e.core); flare.addColorStop(1, e.glow + '00');
        g.fillStyle = flare; g.beginPath(); g.arc(tx, ty, 35, 0, 6.283); g.fill();
      }
    } else if (e.kind === 'skWarFissure') {
      const grow = 1 - Math.pow(1 - Math.min(1, e.t / .32), 3);
      const [ox, oy] = w2s(e.x, e.y, 4);
      g.globalAlpha = fade * .16; g.fillStyle = e.glow; g.beginPath(); g.moveTo(ox, oy);
      for (let i = 0; i <= 24; i++) {
        const an = e.a - e.arc / 2 + e.arc * i / 24;
        const [x, y] = w2s(e.x + Math.cos(an) * e.r * grow, e.y + Math.sin(an) * e.r * grow, 4);
        g.lineTo(x, y);
      }
      g.closePath(); g.fill();
      const point = (dist, side = 0) => w2s(e.x + Math.cos(e.a) * dist - Math.sin(e.a) * side,
        e.y + Math.sin(e.a) * dist + Math.cos(e.a) * side, 5);
      layers(g, [[30, '#26140b', .82, 0], [18, '#754019', .8, 0], [9, e.glow, .8, 1], [3, e.core, 1, 0]], fade, 0, () => {
        g.beginPath();
        for (let i = 0; i <= 17; i++) {
          const dist = e.r * grow * i / 17, side = Math.sin(i * 2.6) * .09 * (i / 17), [x, y] = point(dist, side);
          i ? g.lineTo(x, y) : g.moveTo(x, y);
        }
      });
      for (const [f, side] of [[.35, -1], [.55, 1], [.72, -1], [.84, 1]]) {
        if (f > grow) continue;
        const [bx, by] = point(e.r * f), [tx, ty] = point(e.r * Math.min(grow, f + .16), side * e.r * .26 * f);
        layers(g, [[10, '#26140b', .7, 0], [4, e.glow, .9, 1], [1.5, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(bx, by); g.lineTo((bx + tx) / 2 + side * 8, (by + ty) / 2 - 9); g.lineTo(tx, ty);
        });
      }
    } else if (e.kind === 'skWarCharge') {
      const who = e.actor === Online.id ? hero : remotePlayers.get(e.actor);
      const [bx, by] = w2s(e.x, e.y, 18), [tx, ty] = who ? w2s(who.x, who.y, 18) : [bx, by];
      const len = Math.hypot(tx - bx, ty - by);
      if (len > 7) {
        layers(g, [[28, '#39200e', .4, 0], [19, e.glow, .42, 1], [7, e.core, .9, 0], [2, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty);
        });
        const dx = (tx - bx) / len, dy = (ty - by) / len;
        for (let d = 30; d < len - 10; d += 36) {
          const x = bx + dx * d, y = by + dy * d;
          g.globalAlpha = fade * .8; g.strokeStyle = e.core; g.lineWidth = 3;
          g.beginPath(); g.moveTo(x - dx * 12 - dy * 10, y - dy * 12 + dx * 10); g.lineTo(x, y);
          g.lineTo(x - dx * 12 + dy * 10, y - dy * 12 - dx * 10); g.stroke();
        }
      }
      g.globalAlpha = fade; g.strokeStyle = e.core; g.lineWidth = 5;
      g.beginPath(); g.ellipse(tx, ty, 24 + Math.min(35, len * .12), 12 + Math.min(17, len * .06), 0, 0, 6.283); g.stroke();
      const [ax, ay] = w2s(e.x + Math.cos(e.a), e.y + Math.sin(e.a), 18);
      const dirLen = Math.hypot(ax - bx, ay - by) || 1, dx = (ax - bx) / dirLen, dy = (ay - by) / dirLen;
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade * .8; g.fillStyle = e.glow;
      g.beginPath(); g.moveTo(tx + dx * 58, ty + dy * 58);
      g.lineTo(tx - dx * 28 - dy * 24, ty - dy * 28 + dx * 24);
      g.lineTo(tx - dx * 11, ty - dy * 11);
      g.lineTo(tx - dx * 28 + dy * 24, ty - dy * 28 - dx * 24); g.closePath(); g.fill();
      layers(g, [[7, e.core, .9, 0], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
        g.beginPath(); g.moveTo(tx - dx * 38, ty - dy * 38); g.lineTo(tx + dx * 38, ty + dy * 38);
      });
    } else if (e.kind === 'skWarCry') {
      const [hx, hy] = w2s(e.x, e.y, 75);
      for (let i = 0; i < 3; i++) {
        const q = (e.t - i * .16) / .72; if (q < 0 || q > 1) continue;
        const rx = 38 + q * 240, ry = 20 + q * 115;
        layers(g, [[14, '#402415', .32, 0], [9, e.glow, .65, 1], [3, e.core, .95, 0]], 1 - q, 0, () => {
          g.beginPath(); g.ellipse(hx, hy, rx, ry, 0, -.95, .95);
        });
      }
      for (let i = -2; i <= 2; i++) {
        const an = e.a + i * .23, length = 34 + Math.min(1, e.t * 3) * 90;
        layers(g, [[7, e.glow, .55, 1], [2.5, e.core, 1, 0]], fade, 0, () => {
          g.beginPath(); g.moveTo(hx + Math.cos(an) * 25, hy + Math.sin(an) * 13);
          g.lineTo(hx + Math.cos(an) * length, hy + Math.sin(an) * length * .48);
        });
      }
    } else if (e.kind === 'skWarShield') {
      const rise = 1 - Math.pow(1 - Math.min(1, e.t / .23), 3), [cx, cy] = w2s(e.x, e.y, 59 * rise);
      g.globalAlpha = fade * .26; g.fillStyle = e.glow; g.beginPath();
      g.moveTo(cx, cy - 82); g.lineTo(cx + 63, cy - 52); g.lineTo(cx + 53, cy + 31);
      g.lineTo(cx, cy + 77); g.lineTo(cx - 53, cy + 31); g.lineTo(cx - 63, cy - 52); g.closePath(); g.fill();
      layers(g, [[17, '#18304d', .7, 0], [10, e.glow, .7, 1], [4, e.core, 1, 0]], fade, 0, () => {
        g.beginPath(); g.moveTo(cx, cy - 82); g.lineTo(cx + 63, cy - 52); g.lineTo(cx + 53, cy + 31);
        g.lineTo(cx, cy + 77); g.lineTo(cx - 53, cy + 31); g.lineTo(cx - 63, cy - 52); g.closePath();
      });
      g.globalAlpha = fade; g.strokeStyle = '#ffffff'; g.lineWidth = 5;
      g.beginPath(); g.moveTo(cx, cy - 49); g.lineTo(cx, cy + 42); g.moveTo(cx - 32, cy - 7); g.lineTo(cx + 32, cy - 7); g.stroke();
    } else if (e.kind === 'skWarBerserk') {
      const [cx, cy] = w2s(e.x, e.y, 44);
      for (let i = 0; i < 9; i++) {
        const an = i * 6.283 / 9 + e.t * 3, pulse = .8 + .2 * Math.sin(e.t * 20 + i), height = (55 + i % 3 * 16) * pulse;
        const bx = cx + Math.cos(an) * 30, by = cy + Math.sin(an) * 18;
        g.globalAlpha = fade * .7; g.fillStyle = i % 2 ? e.glow : e.core;
        g.beginPath(); g.moveTo(bx - 9, by + 20); g.quadraticCurveTo(bx + 14, by - height * .35, bx, by - height);
        g.quadraticCurveTo(bx - 18, by - height * .25, bx + 9, by + 20); g.closePath(); g.fill();
      }
    } else if (e.kind === 'skWarHeal') {
      const [cx, cy] = w2s(e.x, e.y, 45), rise = Math.min(1, e.t / .28);
      for (const side of [-1, 1]) layers(g, [[18, '#14452a', .25, 0], [10, e.glow, .5, 1], [4, e.core, 1, 0]], fade, 0, () => {
        g.beginPath(); for (let i = 0; i <= 18; i++) {
          const q = i / 18, x = cx + side * (22 + 21 * Math.sin(q * 7 + e.t * 7)) * (1 - q * .25), y = cy + 37 - q * 150 * rise;
          i ? g.lineTo(x, y) : g.moveTo(x, y);
        }
      });
      g.globalAlpha = fade; g.strokeStyle = '#e6fff0'; g.lineWidth = 7;
      g.beginPath(); g.moveTo(cx, cy - 72 * rise); g.lineTo(cx, cy + 12);
      g.moveTo(cx - 26, cy - 30 * rise); g.lineTo(cx + 26, cy - 30 * rise); g.stroke();
    } else if (e.kind === 'skWarTitanCore') {
      const [cx, cy] = w2s(e.x, e.y), rise = Math.min(1, e.t / .27), height = 275 * rise;
      const light = g.createLinearGradient(0, cy - height, 0, cy);
      light.addColorStop(0, e.glow + '00'); light.addColorStop(.45, e.glow + '55'); light.addColorStop(1, e.core + 'cc');
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade * .8;
      g.fillStyle = light; g.beginPath(); g.moveTo(cx - 52, cy); g.lineTo(cx - 25, cy - height);
      g.lineTo(cx + 25, cy - height); g.lineTo(cx + 52, cy); g.closePath(); g.fill();
      if (e.heal > 0) {
        g.globalAlpha = fade; g.strokeStyle = '#8dffb1'; g.lineWidth = 7;
        g.beginPath(); g.ellipse(cx, cy - 50, 30 + e.t * 36, 18 + e.t * 22, 0, 0, 6.283); g.stroke();
      }
    } else if (e.kind === 'skCone') {
      const sweep = Math.min(1, p * 2.2), arc = e.arc || 3.8, a0 = e.a - arc / 2, a1 = a0 + arc * sweep;
      for (const [rr, list] of [[1, [[34, OUTLINE, .3, 0], [24, e.glow, .5, 1], [12, e.core, .95, 0], [4, '#ffffff', 1, 0]]], [.7, [[16, OUTLINE, .25, 0], [8, e.glow, .6, 1], [3, '#ffffff', .9, 0]]]]) layers(g, list, fade, p * .5, () => {
        g.beginPath(); for (let i = 0; i <= 18; i++) { const an = a0 + (a1 - a0) * i / 18, [qx, qy] = w2s(e.x + Math.cos(an) * e.r * rr, e.y + Math.sin(an) * e.r * rr, 26); i ? g.lineTo(qx, qy) : g.moveTo(qx, qy); }
      });
    } else if (e.kind === 'skFlash') {
      const gr = g.createRadialGradient(sx, sy - 40, 1, sx, sy - 40, 54); gr.addColorStop(0, e.core); gr.addColorStop(.4, e.glow + 'cc'); gr.addColorStop(1, e.glow + '00');
      g.globalAlpha = fade; g.fillStyle = gr; g.beginPath(); g.arc(sx, sy - 40, 54, 0, 6.283); g.fill();
    } else if (e.kind === 'skBeam') {
      const rise = Math.min(1, p * 4), w = 56 * (1 - p), top = 360 * rise, gr = g.createLinearGradient(0, sy - top, 0, sy); gr.addColorStop(0, e.glow + '00'); gr.addColorStop(.6, e.glow + 'cc'); gr.addColorStop(1, e.core);
      g.globalAlpha = fade; g.fillStyle = gr; g.fillRect(sx - w / 2, sy - top, w, top);
      g.fillStyle = '#ffffff'; g.globalAlpha = fade * .8; g.fillRect(sx - w * .12, sy - top * .8, w * .24, top * .8);
      g.strokeStyle = e.core; g.lineWidth = 4; g.globalAlpha = fade; g.beginPath(); g.ellipse(sx, sy, 20 + p * 70, 10 + p * 35, 0, 0, 6.283); g.stroke();
    } else if (e.kind === 'skDash') {
      const [ex, ey] = w2s(e.ex, e.ey, 24), [bx, by] = w2s(e.x, e.y, 24), head = Math.min(1, p * 5), tx = bx + (ex - bx) * head, ty = by + (ey - by) * head;
      layers(g, [[30, OUTLINE, .25, 0], [24, e.glow, .5, 1], [11, e.core, .95, 0], [4, '#ffffff', 1, 0]], fade, p * .6, () => { g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty); });
      layers(g, [[3, '#ffffff', .8, 0]], fade, 0, () => { g.beginPath(); for (let i = -2; i <= 2; i++) { if (!i) continue; g.moveTo(bx, by + i * 10); g.lineTo(bx + (tx - bx) * .8, by + (ty - by) * .8 + i * 10); } });
    } else if (e.kind === 'skCut') {
      const k = Math.min(1, p * 3), len = e.big ? 84 : 52, [cx, cy] = w2s(e.x, e.y, 30), c = Math.cos(e.ang), s2 = Math.sin(e.ang);
      layers(g, [[e.big ? 18 : 12, OUTLINE, .35, 0], [e.big ? 12 : 8, e.glow, .7, 1], [e.big ? 6 : 4, '#ffffff', 1, 0]], fade, 0, () => { g.beginPath(); g.moveTo(cx - c * len * (1 - k * .2), cy - s2 * len * (1 - k * .2)); g.lineTo(cx + c * len * k, cy + s2 * len * k); });
      if (e.big) layers(g, [[10, OUTLINE, .3, 0], [6, e.core, 1, 0], [3, '#ffffff', 1, 0]], fade, 0, () => { g.beginPath(); g.moveTo(cx - s2 * len * k, cy + c * len * k); g.lineTo(cx + s2 * len * k, cy - c * len * k); });
    } else if (e.kind === 'skChain') {
      const pts = e.path.map(q => w2s(q.x, q.y, 28)), flick = Math.floor(e.t * 40) % 2 ? .75 : 1;
      layers(g, [[20, OUTLINE, .3, 0], [14, e.glow, .5, 1], [6, e.core, .95, 0], [2.5, '#ffffff', 1, 0]], fade * flick, 0, () => { g.beginPath(); pts.forEach(([qx, qy], i) => i ? g.lineTo(qx, qy) : g.moveTo(qx, qy)); });
      const [hx, hy] = pts[pts.length - 1]; g.globalAlpha = fade; g.fillStyle = e.core; g.beginPath(); g.arc(hx, hy, 12 * fade + 3, 0, 6.283); g.fill(); g.fillStyle = '#ffffff'; g.beginPath(); g.arc(hx, hy, 5 * fade + 1, 0, 6.283); g.fill();
    } else if (e.kind === 'skMageFireImpact') {
      const grow = 1 - Math.pow(1 - Math.min(1, p * 2.3), 3), rx = U * e.r * grow, ry = V * e.r * grow;
      if (layer === 'floor') {
        g.globalAlpha = fade * .25; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
        layers(g, [[17, '#5b220f', .55, 0], [10, e.glow, .8, 1], [4, e.core, 1, 0]], fade, p * .4, () => { g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); });
      } else {
        for (let i = 0; i < 10; i++) {
          const an = i * 6.283 / 10, x = sx + Math.cos(an) * rx * .72, y = sy + Math.sin(an) * ry * .72;
          const h = (26 + i % 3 * 14) * (1 - p * .6);
          g.globalAlpha = fade * .75; g.fillStyle = i % 3 ? e.glow : e.core;
          g.beginPath(); g.moveTo(x - 7, y); g.quadraticCurveTo(x + 10, y - h * .5, x, y - h); g.quadraticCurveTo(x - 11, y - h * .4, x + 7, y); g.closePath(); g.fill();
        }
      }
    } else if (e.kind === 'skMageMeteor') {
      const warning = Math.min(1, e.t / .3), impact = Math.max(0, (e.t - .36) / .74), rx = U * e.r, ry = V * e.r;
      if (layer === 'floor') {
        layers(g, [[10, OUTLINE, .32, 0], [5, e.glow, .7, 1], [2, e.core, .95, 0]], fade, 0, () => { g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); });
        if (e.t < .36) {
          g.globalAlpha = .12 + warning * .18; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
          for (let i = 0; i < 8; i++) { const an = i * .785; g.strokeStyle = e.core; g.lineWidth = 3; g.globalAlpha = warning * .75;
            g.beginPath(); g.moveTo(sx + Math.cos(an) * rx * .7, sy + Math.sin(an) * ry * .7); g.lineTo(sx + Math.cos(an) * rx * .9, sy + Math.sin(an) * ry * .9); g.stroke(); }
        } else {
          const k = 1 - Math.pow(1 - Math.min(1, impact * 2), 3);
          g.globalAlpha = (1 - impact) * .3; g.fillStyle = '#492419'; g.beginPath(); g.ellipse(sx, sy, rx * k, ry * k, 0, 0, 6.283); g.fill();
          layers(g, [[20, '#552511', .42, 0], [11, e.glow, .7, 1], [4, e.core, 1, 0]], 1 - impact, 0, () => { g.beginPath(); g.ellipse(sx, sy, rx * k, ry * k, 0, 0, 6.283); });
        }
      } else if (e.t < .36) {
        const fall = warning, mx = sx + 220 * (1 - fall), my = sy - 520 * (1 - fall) - 34;
        layers(g, [[36, e.glow, .3, 1], [19, e.core, .75, 0], [7, '#ffffff', .9, 0]], 1, 0, () => { g.beginPath(); g.moveTo(mx + 110 * (1 - fall), my - 180 * (1 - fall)); g.lineTo(mx, my); });
        g.globalAlpha = 1; g.fillStyle = '#fff4cc'; g.beginPath(); g.arc(mx, my, 20, 0, 6.283); g.fill();
      } else {
        g.globalAlpha = (1 - impact) * .8; g.fillStyle = e.core;
        for (let i = 0; i < 11; i++) { const an = i * 2.399, d = 22 + impact * (44 + i % 4 * 19), x = sx + Math.cos(an) * d, y = sy + Math.sin(an) * d * .55 - (1 - impact) * (30 + i % 3 * 11);
          g.beginPath(); g.arc(x, y, 4 + i % 3 * 2, 0, 6.283); g.fill(); }
      }
    } else if (e.kind === 'skMeteor') {
      const fall = Math.min(1, e.t / .38), x0 = sx + 260, y0 = sy - 700;
      if (e.t < .38) {
        const mx = x0 + (sx - x0) * fall, my = y0 + (sy - y0) * fall;
        layers(g, [[44, OUTLINE, .25, 0], [34, e.glow, .5, 1], [18, e.core, .95, 0]], 1, 0, () => { g.beginPath(); g.moveTo(mx + 140 * (1 - fall) + 40, my - 150 * (1 - fall) - 60); g.lineTo(mx, my); });
        g.globalAlpha = 1; g.fillStyle = e.glow; g.beginPath(); g.arc(mx, my, 32, 0, 6.283); g.fill(); g.fillStyle = e.core; g.beginPath(); g.arc(mx, my, 24, 0, 6.283); g.fill(); g.fillStyle = '#ffffff'; g.beginPath(); g.arc(mx, my, 14, 0, 6.283); g.fill();
        layers(g, [[6, OUTLINE, .3 * fall, 0], [3, e.glow, .8 * fall, 1]], 1, 0, () => { g.beginPath(); g.ellipse(sx, sy, U * e.r, V * e.r, 0, 0, 6.283); });      // the warning circle
      } else {
        const q = (e.t - .38) / (e.life - .38), k = 1 - Math.pow(1 - Math.min(1, q * 1.8), 3), rx = U * e.r * k, ry = V * e.r * k, f = 1 - q;
        g.globalAlpha = f * .35; g.fillStyle = '#2a1408'; g.beginPath(); g.ellipse(sx, sy, rx * 1.05, ry * 1.05, 0, 0, 6.283); g.fill();
        const gr = g.createRadialGradient(sx, sy, 4, sx, sy, Math.max(6, rx)); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.35, e.core); gr.addColorStop(.75, e.glow + 'aa'); gr.addColorStop(1, e.glow + '00');
        g.globalAlpha = f; g.fillStyle = gr; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
        layers(g, [[14 * f + 3, OUTLINE, .3, 0], [8 * f + 1, e.core, 1, 0]], f, 0, () => { g.beginPath(); g.ellipse(sx, sy, rx * 1.1, ry * 1.1, 0, 0, 6.283); });
        const col = g.createLinearGradient(0, sy - 280 * k, 0, sy); col.addColorStop(0, e.glow + '00'); col.addColorStop(1, e.core); g.globalCompositeOperation = 'lighter'; g.globalAlpha = f * .8; g.fillStyle = col; g.fillRect(sx - 44 * f - 8, sy - 280 * k, 88 * f + 16, 280 * k);
      }
    } else if (e.kind === 'skAura') {
      const rise = 1 - Math.pow(1 - Math.min(1, p * 1.5), 2);
      for (let i = 0; i < 3; i++) { const q = clamp(p * 1.4 - i * .18, 0, 1); if (q <= 0 || q >= 1) continue; layers(g, [[8 * (1 - q) + 3, OUTLINE, .3, 0], [5 * (1 - q) + 1, i ? e.core : e.col, .95, 0]], 1 - q, 0, () => { g.beginPath(); g.ellipse(sx, sy - q * 110, 38 + q * 14, 18 + q * 7, 0, 0, 6.283); }); }
      const gr = g.createLinearGradient(0, sy - 140 * rise, 0, sy); gr.addColorStop(0, e.col + '00'); gr.addColorStop(1, e.col + '99'); g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade; g.fillStyle = gr; g.fillRect(sx - 36, sy - 140 * rise, 72, 140 * rise);
    }
    g.restore();
  }
  function drawGroundSlam(g, e) {
    const p = e.t / e.life, [sx, sy] = w2s(e.x, e.y), R = Math.max(.2, p) * e.r;
    g.save(); g.globalAlpha = (1 - p) * .9; g.strokeStyle = '#ffd9a0'; g.lineWidth = 7 * (1 - p) + 2; g.beginPath(); g.ellipse(sx, sy, R * 62.225, R * 31.112, 0, 0, 6.283); g.stroke();
    g.globalAlpha = (1 - p) * .25; g.fillStyle = '#e8d0a0'; g.beginPath(); g.ellipse(sx, sy, R * 62.225, R * 31.112, 0, 0, 6.283); g.fill(); g.restore();
  }
  // A glowing ring at the feet of anyone with an active buff, flickering when it is about to end.
  function drawBuffRings(g, who, t) {
    if (!who.buffs?.length || who.dead) return;
    const [sx, sy] = w2s(who.x, who.y);
    who.buffs.forEach((b, i) => {
      const col = BUFF_COL[b.kind] || '#ffffff', pulse = .55 + .25 * Math.sin(t * 4 + i * 1.7), ending = b.left < 1.5 && Math.floor(t * 8) % 2;
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = ending ? .2 : pulse * .75; g.strokeStyle = col; g.lineWidth = 3;
      g.beginPath(); g.ellipse(sx, sy, 34 + i * 8, 16 + i * 4, 0, 0, 6.283); g.stroke();
      g.globalAlpha = (ending ? .08 : .2) * pulse; g.fillStyle = col; g.fill(); g.restore();
      if (b.id === 'battlecry' || b.id === 'shieldwall' || b.id === 'berserk') {
        g.save(); g.globalCompositeOperation = 'lighter';
        const tint = b.id === 'shieldwall' ? '#a8d8ff' : b.id === 'berserk' ? '#ff665a' : '#ffd087';
        const spin = b.id === 'berserk' ? t * 2.4 : 0;
        for (let n = 0; n < 4; n++) {
          const an = n * 1.571 + spin, x = sx + Math.cos(an) * 46, y = sy + Math.sin(an) * 22;
          g.globalAlpha = (ending ? .2 : .5) * pulse; g.strokeStyle = tint; g.lineWidth = 3;
          g.beginPath();
          if (b.id === 'shieldwall') { g.moveTo(x - 9, y - 8); g.lineTo(x + 9, y - 8); g.lineTo(x + 7, y + 4); g.lineTo(x, y + 10); g.lineTo(x - 7, y + 4); g.closePath(); }
          else if (b.id === 'battlecry') { g.moveTo(x - 10, y + 6); g.lineTo(x, y - 8); g.lineTo(x + 10, y + 6); }
          else { g.moveTo(x - 7, y + 8); g.lineTo(x, y - 13); g.lineTo(x + 7, y + 8); }
          g.stroke();
        }
        g.restore();
      }
      if (b.id === 'evasion' || b.id === 'shadowveil' || b.id === 'deadlyfocus') {
        g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = (ending ? .18 : .52) * pulse;
        g.strokeStyle = b.id === 'evasion' ? '#b9a8ff' : b.id === 'shadowveil' ? '#7356c1' : '#ffbd68';
        g.lineWidth = 2.5;
        if (b.id === 'evasion') {
          for (const side of [-1, 1]) { const x = sx + side * (43 + Math.sin(t * 5) * 4);
            g.beginPath(); g.moveTo(x - side * 9, sy - 15); g.lineTo(x, sy);
            g.lineTo(x - side * 9, sy + 15); g.stroke(); }
        } else if (b.id === 'shadowveil') {
          for (let n = 0; n < 3; n++) {
            const x = sx - 39 - n * 11 - (t * 16 % 11), y = sy + (n - 1) * 8;
            g.beginPath(); g.moveTo(x + 16, y - 8); g.quadraticCurveTo(x - 4, y, x + 16, y + 8); g.stroke();
          }
        } else {
          g.beginPath(); g.arc(sx, sy, 24, 0, 6.283);
          for (const an of [0, 1.571, 3.142, 4.713]) {
            g.moveTo(sx + Math.cos(an) * 29, sy + Math.sin(an) * 29);
            g.lineTo(sx + Math.cos(an) * 37, sy + Math.sin(an) * 37);
          }
          g.stroke();
        }
        g.restore();
      }
    });
  }
  function drawMageWardShell(g, who, t) {
    if (who.look?.class !== 'mage' || who.dead || !who.buffs?.some(b => b.id === 'arcaneward')) return;
    const pulse = .65 + .2 * Math.sin(t * 5);
    g.save(); g.globalCompositeOperation = 'lighter';
    g.globalAlpha = .06 * pulse; g.fillStyle = '#7a9bff'; g.beginPath(); g.ellipse(0, -68, 58, 82, 0, 0, 6.283); g.fill();
    g.globalAlpha = .55 * pulse; g.strokeStyle = '#cce7ff'; g.lineWidth = 2.5;
    g.beginPath(); for (let i = 0; i <= 8; i++) { const a = i * 6.283 / 8, x = Math.cos(a) * 59, y = -68 + Math.sin(a) * 83; i ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke();
    g.globalAlpha = .32 * pulse; g.strokeStyle = '#8baeff'; g.lineWidth = 1.5;
    for (let i = 0; i < 4; i++) { const a = i * 1.571 + t * .28; g.beginPath(); g.moveTo(Math.cos(a) * 46, -68 + Math.sin(a) * 65); g.lineTo(Math.cos(a + .35) * 58, -68 + Math.sin(a + .35) * 82); g.stroke(); }
    g.restore();
  }
  function drawPriestBuffShell(g, who, t) {
    if (who.dead || !who.buffs?.length) return;
    const ending = id => who.buffs.find(b => b.id === id)?.left < 1.5 && Math.floor(t * 8) % 2;
    if (who.buffs.some(b => b.id === 'wardoflight')) {
      const pulse = .5 + .13 * Math.sin(t * 4);
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = ending('wardoflight') ? .16 : pulse;
      g.strokeStyle = '#a7e6ff'; g.lineWidth = 2.7; g.beginPath();
      g.moveTo(0, -137); g.lineTo(42, -113); g.lineTo(45, -39); g.lineTo(0, 4);
      g.lineTo(-45, -39); g.lineTo(-42, -113); g.closePath(); g.stroke();
      g.globalAlpha *= .18; g.fillStyle = '#a7e6ff'; g.fill(); g.restore();
    }
    if (who.buffs.some(b => b.id === 'blessing')) {
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = ending('blessing') ? .13 : .44 + .1 * Math.sin(t * 3);
      g.strokeStyle = '#ffcf6b'; g.lineWidth = 2.4;
      for (const side of [-1, 1]) for (let n = 0; n < 2; n++) {
        const x = side * (42 + n * 13), y = -83 + n * 27;
        g.beginPath(); g.moveTo(x - side * 8, y + 7); g.lineTo(x, y - 9); g.lineTo(x + side * 8, y + 7); g.stroke();
      }
      g.restore();
    }
  }
  function drawHunterBuffShell(g, who, t) {
    if (who.look?.class !== 'hunter' || who.dead || !who.buffs?.length) return;
    for (const b of who.buffs) {
      if (!['huntersmark', 'rapidfire', 'eaglesight'].includes(b.id)) continue;
      const pulse = .45 + .14 * Math.sin(t * 4), ending = b.left < 1.5 && Math.floor(t * 8) % 2;
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = ending ? .14 : pulse;
      g.strokeStyle = b.id === 'huntersmark' ? '#ffbf67' : b.id === 'rapidfire' ? '#d7f889' : '#a8eef2';
      g.lineWidth = 2.5;
      if (b.id === 'huntersmark') {
        g.beginPath(); g.arc(0, -83, 57, 0, 6.283);
        for (const an of [0, 1.571, 3.142, 4.713]) { g.moveTo(Math.cos(an) * 68, -83 + Math.sin(an) * 68);
          g.lineTo(Math.cos(an) * 82, -83 + Math.sin(an) * 82); } g.stroke();
      } else if (b.id === 'rapidfire') {
        for (let i = 0; i < 3; i++) { const y = -117 + i * 37, x = -51 - (t * 33 % 21);
          g.beginPath(); g.moveTo(x, y); g.lineTo(x + 35, y); g.lineTo(x + 24, y - 8);
          g.moveTo(x + 35, y); g.lineTo(x + 24, y + 8); g.stroke(); }
      } else {
        g.beginPath(); g.moveTo(-53, -92); g.quadraticCurveTo(0, -134, 53, -92);
        g.quadraticCurveTo(0, -50, -53, -92); g.moveTo(12, -92); g.arc(0, -92, 12, 0, 6.283); g.stroke();
      }
      g.restore();
    }
  }
  function interpolate(actor, dt) {
    if (Number.isFinite(actor.nx)) { const k = Math.min(1, dt * 14); actor.x += (actor.nx - actor.x) * k; actor.y += (actor.ny - actor.y) * k; }
    if (actor.moving) actor.walk += dt * 11;
    if (actor.atkT > 0) actor.atkT += dt;
    if (actor.dead) actor.deadT += dt;
    if (actor.hurtT > 0) actor.hurtT = Math.max(0, actor.hurtT - dt);
  }
  function update(dt) {
    tAll += dt;
    window.Skillbar?.update();
    if (Online.connected) {
      inputT -= dt;
      if (inputT <= 0) {
        const [dx, dy] = paused || hero.sparkTravel ? [0, 0] : keyboardDirection();
        inputT = dx || dy ? .05 : .25;
        Online.send({ type: 'input', dx, dy });
        if (!paused && !hero.sparkTravel && pointer.down && !hero.target) Online.send({ type: 'move', x: pointer.x, y: pointer.y });
      }
      if (!paused && pendingNpc) {
        const {npc,until}=pendingNpc;
        if(hero.dead || tAll>until) {pendingNpc=null;cityRoute=[];Online.send({type:'stop'});}
        else if(Math.hypot(hero.x-npc.x,hero.y-npc.y)<=2.5) {pendingNpc=null;cityRoute=[];askNpc(npc);}
        else if(npc.route && tAll-routeTime>1) {                       // a walker has moved on: take a fresh route to where it is now
          const end=cityRoute[cityRoute.length-1];
          if(!end || Math.hypot(end.x-npc.x,end.y-npc.y)>2.2) {cityRoute=routeTo(npc,true);routeTime=tAll;}
        }
      }
      if (!paused && pendingChest) {
        const chest = chests.find(c => c.id === pendingChest.id && c.expiresAt > tAll);
        if (hero.dead || tAll > pendingChest.until || !chest) { pendingChest = null; cityRoute = []; Online.send({type:'stop'}); }
        else if (Math.hypot(hero.x-chest.x,hero.y-chest.y) <= 1.95) {
          cityRoute = [];
          if (pendingChest.sentAt === undefined) pendingChest.until = Math.max(pendingChest.until, tAll + 4);
          if (pendingChest.sentAt === undefined || tAll - pendingChest.sentAt > .6) { pendingChest.sentAt = tAll; askForChest(chest); }
        }
        else if (!cityRoute.length && tAll - (pendingChest.routedAt ?? -9) > .5) {
          // Out of reach again (the hero drifted, or the first request was early): walk back to it.
          cityRoute = chestRoute(chest, pendingChest.routedAt !== undefined); pendingChest.routedAt = tAll; routeTime = 0;
          pendingChest.until = Math.max(pendingChest.until, tAll + 8);
        }
      }
      if(!paused && cityRoute.length) {
        if(hero.dead)cityRoute=[];
        else if(Math.hypot(hero.x-cityRoute[0].x,hero.y-cityRoute[0].y)<.32){cityRoute.shift();routeTime=0;}
        else if(tAll-routeTime>.35){Online.send({type:'move',...cityRoute[0]});routeTime=tAll;}
      }
      interpolate(hero, dt); for (const remote of remotePlayers.values()) interpolate(remote, dt);
      for (const slime of slimes) { interpolate(slime, dt); if (slime.dead) slime.dieT += dt; }
      keepActorsSeparated();
    }
    for (const p of parts) { p.t += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vz -= p.g * dt; p.z = Math.max(0, p.z + p.vz * dt * 6); }
    parts = parts.filter(p => p.t < p.life);
    floaters = DamageNumbers.step(floaters, dt);
    for (const e of effects) e.t += dt; effects = effects.filter(e => e.t < (e.life ?? (e.kind === 'ring' ? .9 : .32)));
    if (marker) { marker.t += dt; if (marker.t > 1.2) marker = null; }
    // A teleport or a zone change moves the hero far from the camera: jump there instead of gliding across the map.
    if (Math.hypot(hero.x - cam.x, hero.y - cam.y) > 4) { cam.x = hero.x; cam.y = hero.y; }
    else { const k = 1 - Math.pow(.0006, dt); cam.x += (hero.x - cam.x) * k; cam.y += (hero.y - cam.y) * k; }
    if (shakeT > 0) { shakeT -= dt; const k = shakeMag * Math.min(1, shakeT / .25); shakeX = (Math.random() - .5) * 2 * k; shakeY = (Math.random() - .5) * 2 * k; }
    else { shakeX = shakeY = 0; shakeMag = 0; }
    for (const b of ebolts) { b.x += b.fx * b.speed * dt; b.y += b.fy * b.speed * dt; if (b.size >= .8 && Math.random() < .5) parts.push({ x: b.x, y: b.y, z: 38, vx: (Math.random() - .5) * .6, vy: (Math.random() - .5) * .6, vz: .6, life: .28, t: 0, col: b.color, size: 2 + Math.random() * 2.4, g: 1 }); }
    for (const b of bolts) if (b.size >= 14 && Math.random() < .9) parts.push({ x: b.x, y: b.y, z: 40, vx: (Math.random() - .5), vy: (Math.random() - .5), vz: 1 + Math.random() * 3, life: .35, t: 0, col: b.col, size: 3 + Math.random() * 4, g: 4 });
  }

  // ---------- drawing the actors ----------
  const OPT = () => opts || { hairSwatch: ['#c0501e'], skinSwatch: ['#f0a386'], runeSwatch: ['#59d9ff'] };
  const ARMOR = ['#b8321f', '#2f6fd0', '#2f9a4a'];
  function drawSlime(g, s, t) {
    const d = s.d, R = 30 * d.scale, hopK = clamp(s.hop / 1.6, 0, 1), air = s.hopV > 0 ? 1 : s.hop > 0 ? .4 : 0;
    let sx = 1, sy = 1;
    if (s.state === 'windup') { const k = 1 - s.st / (s.windupTime || .45); sx = 1 + k * .28; sy = 1 - k * .3; }
    else if (air) { sx = 1 - hopK * .14; sy = 1 + hopK * .22; }
    else { const b = Math.sin(t * 3 + s.seed) * .04; sx = 1 + b; sy = 1 - b; }
    const w = R * 1.2 * sx, h = R * 1.05 * sy, z = s.hop * 16;
    g.save(); g.translate(0, -z);
    const path = () => { g.beginPath(); g.moveTo(-w, 0); g.bezierCurveTo(-w * 1.08, -h * .95, -w * .55, -h * 1.5, 0, -h * 1.5); g.bezierCurveTo(w * .55, -h * 1.5, w * 1.08, -h * .95, w, 0); g.bezierCurveTo(w * .62, R * .2, -w * .62, R * .2, -w, 0); g.closePath(); };
    const gr = g.createLinearGradient(0, -h * 1.5, 0, R * .2); gr.addColorStop(0, d.col[0]); gr.addColorStop(.55, d.col[1]); gr.addColorStop(1, d.col[2]);
    path(); g.fillStyle = gr; g.fill();
    g.lineWidth = 3.4; g.strokeStyle = OL; g.lineJoin = 'round'; g.stroke();
    // inner glow, gloss and bubbles
    g.save(); path(); g.clip();
    g.fillStyle = 'rgba(255,255,255,.22)'; g.beginPath(); g.ellipse(0, R * .1, w * .9, R * .35, 0, 0, 6.283); g.fill();
    g.fillStyle = 'rgba(255,255,255,.75)'; g.beginPath(); g.ellipse(-w * .38, -h * 1.05, w * .22, h * .16, -.6, 0, 6.283); g.fill();
    g.beginPath(); g.arc(-w * .12, -h * .92, 2.2 * d.scale, 0, 6.283); g.fill();
    g.fillStyle = 'rgba(255,255,255,.28)'; for (let i = 0; i < 3; i++) { g.beginPath(); g.arc(w * (.15 + i * .18), -h * (.35 + (i % 2) * .22), 2.6 + i, 0, 6.283); g.fill(); }
    g.restore();
    // face
    const lx = s.dir * .8, ey = -h * .62, blink = s.blink < 0;
    for (const ex of [-w * .36, w * .36]) {
      if (blink) { g.strokeStyle = OL; g.lineWidth = 2.6; g.beginPath(); g.moveTo(ex - 5, ey); g.lineTo(ex + 5, ey); g.stroke(); continue; }
      g.fillStyle = '#fff'; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(ex, ey, 6.2 * d.scale ** .6, 7.6 * d.scale ** .6, 0, 0, 6.283); g.fill(); g.stroke();
      g.fillStyle = OL; g.beginPath(); g.ellipse(ex + lx, ey + 1.2, 3.2, 4.4, 0, 0, 6.283); g.fill();
      g.fillStyle = '#fff'; g.beginPath(); g.arc(ex + lx - 1, ey - 1.2, 1.3, 0, 6.283); g.fill();
    }
    g.strokeStyle = OL; g.lineWidth = 2.6; g.lineCap = 'round'; g.beginPath();
    if (s.state === 'windup' || s.state === 'lunge') { g.fillStyle = '#5a1a2a'; g.ellipse(0, -h * .28, 6, 5, 0, 0, 6.283); g.fill(); g.stroke(); }
    else { g.moveTo(-4, -h * .3); g.quadraticCurveTo(0, -h * .18, 4, -h * .3); g.stroke(); }
    g.fillStyle = 'rgba(255,120,150,.5)'; g.beginPath(); g.ellipse(-w * .62, -h * .38, 4.2, 2.6, 0, 0, 6.283); g.ellipse(w * .62, -h * .38, 4.2, 2.6, 0, 0, 6.283); g.fill();
    if (s.flash > 0) { path(); g.fillStyle = `rgba(255,255,255,${Math.min(.85, s.flash * 5)})`; g.fill(); }
    if (s.kind === 'big') {                                        // a little crown for the big ones
      g.fillStyle = '#ffd23f'; g.strokeStyle = OL; g.lineWidth = 2.6; g.beginPath(); g.moveTo(-14, -h * 1.5 + 2); g.lineTo(-16, -h * 1.5 - 14); g.lineTo(-7, -h * 1.5 - 6); g.lineTo(0, -h * 1.5 - 17); g.lineTo(7, -h * 1.5 - 6); g.lineTo(16, -h * 1.5 - 14); g.lineTo(14, -h * 1.5 + 2); g.closePath(); g.fill(); g.stroke();
    }
    g.restore();
  }
  // Word-wraps text into at most four lines of `max` pixels in the context's current font; the last line ends in an ellipsis when cut.
  function wrapBubble(g, text, max) {
    const lines = []; let line = '';
    for (const word of text.split(/\s+/).filter(Boolean)) {
      let w = word;
      while (g.measureText(w).width > max) {              // a word wider than the bubble is broken
        let n = w.length; while (n > 1 && g.measureText(w.slice(0, n)).width > max) n--;
        if (line) { lines.push(line); line = ''; }
        lines.push(w.slice(0, n)); w = w.slice(n);
      }
      const next = line ? line + ' ' + w : w;
      if (g.measureText(next).width > max) { lines.push(line); line = w; } else line = next;
    }
    if (line) lines.push(line);
    if (lines.length > 4) { lines.length = 4; lines[3] = lines[3].replace(/.{0,2}$/, '') + '…'; }
    return lines;
  }
  // A white speech bubble whose tail points down at (sx, sy + 8); `left` seconds remain, the last half second fades it.
  function drawBubble(g, b, sx, sy, left) {
    g.save(); g.globalAlpha = Math.min(1, left / .5); g.font = '17px "Jua", sans-serif'; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    if (!b.lines) b.lines = wrapBubble(g, b.text, 230);
    const lh = 20, pad = 9, w = Math.max(...b.lines.map(l => g.measureText(l).width)) + pad * 2, h = b.lines.length * lh + pad * 2 - 4, r = 9;
    const x = clamp(sx - w / 2, 6, VW - w - 6), y = sy - h, tx = clamp(sx, x + r + 6, x + w - r - 6);
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, tx + 7, y + h, r);
    g.lineTo(tx + 7, y + h); g.lineTo(tx, y + h + 9); g.lineTo(tx - 7, y + h); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
    g.fillStyle = '#fffdf0'; g.strokeStyle = '#151c35'; g.lineWidth = 2.5; g.fill(); g.stroke();
    b.box = { l: x, r: x + w, t: y - 0, b: y + h, lines: b.lines.length }; bubblesDrawn++;
    g.fillStyle = b.party ? '#1d5a8a' : '#1b1b2e';
    b.lines.forEach((l, i) => g.fillText(l, x + pad, y + pad + 14 + i * lh - 2));
    g.restore();
  }
  function drawHero(g, h, t) {
    const o = OPT(), c = hero.look || {};
    const beard = o.hairSwatch[c.hairColor || 0] || '#c0501e', skin = o.skinSwatch[c.skin || 0] || '#f0a386', rune = o.runeSwatch[c.rune || 0] || '#59d9ff', armor = ARMOR[c.armor || 0] || ARMOR[0];
    const face = ((h.fx - h.fy) >= -0.02) ? 1 : -1;
    const walking = h.moving && !h.dead, ph = h.walk, bob = walking ? Math.abs(Math.sin(ph)) * 4 : Math.sin(t * 2.2) * 1.2;
    const atk = h.atkT > 0 ? h.atkT / .42 : 0, swingA = atk ? lerp(-2.2, 1.1, clamp(atk * 1.6, 0, 1)) : (walking ? -.95 + Math.sin(ph) * .08 : -.95 + Math.sin(t * 1.6) * .03);
    const lunge = atk ? Math.sin(clamp(atk * 1.4, 0, 1) * Math.PI) * 10 : 0;
    g.save();
    if (h.dead) { const k = clamp(h.deadT * 2.2, 0, 1); g.rotate(k * 1.45 * face); g.translate(0, k * 4); }
    g.scale(face, 1); g.translate(lunge, 0);
    if (h.hurtT > 0) g.translate(-3, 0);
    const skinD = shade(skin, -.16), beardD = shade(beard, -.28), beardL = shade(beard, .25);
    g.lineJoin = 'round'; g.lineCap = 'round'; g.strokeStyle = OL; g.lineWidth = 3.4;
    const step = walking ? Math.sin(ph) * 5 : 0;
    // boots and legs
    for (const [x, off] of [[-10, step], [10, -step]]) {
      g.fillStyle = '#5a3826'; g.beginPath(); g.roundRect(x - 8, -22 - bob * .3, 16, 16, 5); g.fill(); g.stroke();
      g.fillStyle = '#3b2418'; g.beginPath(); g.roundRect(x - 10 + off * .3, -9 + Math.max(0, -off) * .3, 21, 11, 5); g.fill(); g.stroke();
      g.strokeStyle = '#efe6d6'; g.lineWidth = 3; g.beginPath(); g.moveTo(x - 8, -21 - bob * .3); g.lineTo(x + 8, -21 - bob * .3); g.stroke(); g.strokeStyle = OL; g.lineWidth = 3.4;
    }
    g.translate(0, -bob);
    // back arm
    g.fillStyle = skin; g.beginPath(); g.arc(-24, -34, 7, 0, 6.283); g.fill(); g.stroke();
    // torso
    g.fillStyle = '#7a4a2e'; g.beginPath(); g.ellipse(0, -38, 27, 24, 0, 0, 6.283); g.fill(); g.stroke();
    g.fillStyle = '#93745c'; g.beginPath(); g.ellipse(0, -46, 19, 13, 0, 0, 6.283); g.fill();
    g.fillStyle = '#d0d6e0'; for (const rx of [-11, 11]) { g.beginPath(); g.arc(rx, -47, 2, 0, 6.283); g.fill(); }
    g.fillStyle = '#4a2c1c'; g.beginPath(); g.roundRect(-27, -29, 54, 8, 3); g.fill(); g.stroke();
    g.fillStyle = '#f5c542'; g.beginPath(); g.roundRect(-6, -31, 12, 12, 3); g.fill(); g.stroke();
    // head, beard, hair
    g.fillStyle = skin; g.beginPath(); g.arc(0, -66, 20, 0, 6.283); g.fill(); g.stroke();
    g.fillStyle = beard; g.beginPath(); g.moveTo(-19, -66); g.bezierCurveTo(-26, -44, -14, -24, 0, -18); g.bezierCurveTo(14, -24, 26, -44, 19, -66); g.bezierCurveTo(12, -58, -12, -58, -19, -66); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = beardL; g.lineWidth = 2; g.beginPath(); g.moveTo(-8, -54); g.quadraticCurveTo(-11, -38, -5, -26); g.moveTo(8, -54); g.quadraticCurveTo(11, -38, 5, -26); g.stroke();
    g.strokeStyle = OL; g.lineWidth = 3.4;
    for (const bx of [-9, 9]) { g.fillStyle = beardD; g.beginPath(); g.ellipse(bx, -19, 4.5, 6, 0, 0, 6.283); g.fill(); g.stroke(); g.fillStyle = '#9aa3b5'; g.fillRect(bx - 4, -27, 8, 3); }
    g.fillStyle = beard; g.beginPath(); g.moveTo(-3, -60); g.bezierCurveTo(-14, -66, -19, -57, -18, -53); g.bezierCurveTo(-11, -56, -6, -55, -3, -57); g.closePath(); g.moveTo(3, -60); g.bezierCurveTo(14, -66, 19, -57, 18, -53); g.bezierCurveTo(11, -56, 6, -55, 3, -57); g.closePath(); g.fill(); g.stroke();
    if (h.roar > 0 || atk) { g.fillStyle = '#4a1420'; g.beginPath(); g.ellipse(0, -55, 6, 5, 0, 0, 6.283); g.fill(); }
    g.fillStyle = '#f09a7c'; g.beginPath(); g.arc(1, -62, 5.2, 0, 6.283); g.fill(); g.stroke();
    g.fillStyle = OL; for (const ex of [-8, 8]) { g.beginPath(); g.ellipse(ex, -70, 2.4, 3.4, 0, 0, 6.283); g.fill(); }
    g.fillStyle = '#fff'; for (const ex of [-8, 8]) { g.beginPath(); g.arc(ex - .7, -71.2, 1, 0, 6.283); g.fill(); }
    g.strokeStyle = beardD; g.lineWidth = 3.6; g.beginPath(); g.moveTo(-14, -77); g.lineTo(-4, -74); g.moveTo(14, -77); g.lineTo(4, -74); g.stroke();
    g.strokeStyle = OL; g.lineWidth = 3.4; g.fillStyle = beard; g.beginPath(); g.moveTo(-20, -70); g.bezierCurveTo(-24, -92, 24, -92, 20, -70); g.bezierCurveTo(12, -78, -12, -78, -20, -70); g.closePath(); g.fill(); g.stroke();
    // pauldrons
    for (const [x, s] of [[-27, -1], [27, 1]]) {
      g.fillStyle = '#c4ccd9'; g.beginPath(); g.moveTo(x + s * 4, -60); g.lineTo(x + s * 10, -76); g.lineTo(x + s * 14, -58); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = armor; g.beginPath(); g.arc(x, -52, 13, 0, 6.283); g.fill(); g.stroke();
      g.strokeStyle = '#aab3c4'; g.lineWidth = 3; g.beginPath(); g.arc(x, -52, 9.5, 0, 6.283); g.stroke(); g.strokeStyle = OL; g.lineWidth = 3.4;
    }
    // axe arm: pivot at the front shoulder
    g.save(); g.translate(23, -44); g.rotate(swingA);
    g.strokeStyle = OL; g.lineWidth = 8; g.beginPath(); g.moveTo(0, 8); g.lineTo(0, -56); g.stroke();
    g.strokeStyle = '#8a5a34'; g.lineWidth = 4.2; g.beginPath(); g.moveTo(0, 8); g.lineTo(0, -56); g.stroke();
    g.strokeStyle = '#f5c542'; g.lineWidth = 3; g.beginPath(); g.moveTo(-3, -6); g.lineTo(3, -6); g.moveTo(-3, -30); g.lineTo(3, -30); g.stroke();
    g.fillStyle = '#c8d2e6'; g.strokeStyle = OL; g.lineWidth = 3.4;
    g.beginPath(); g.moveTo(0, -48); g.quadraticCurveTo(20, -52, 26, -36); g.quadraticCurveTo(16, -34, 4, -40); g.closePath(); g.fill(); g.stroke();
    g.beginPath(); g.moveTo(0, -48); g.quadraticCurveTo(-20, -52, -26, -36); g.quadraticCurveTo(-16, -34, -4, -40); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = rune; g.lineWidth = 2.4; g.shadowColor = rune; g.shadowBlur = 8; g.beginPath(); g.moveTo(-15, -45); g.lineTo(-9, -40); g.moveTo(15, -45); g.lineTo(9, -40); g.stroke(); g.shadowBlur = 0;
    g.fillStyle = skin; g.strokeStyle = OL; g.lineWidth = 3.4; g.beginPath(); g.arc(0, -2, 8, 0, 6.283); g.fill(); g.stroke();
    g.restore();
    g.restore();
  }

  // ---------- slimes as sprites (assets/slimes_<kind>.png + slimes.txt, drawn by tools/make_slime_sprites.py) ----------
  let slimeSrc = null, beetleSrc = null, cragSrc = null, rimeSrc = null, fenSrc = null, wyrdSrc = null, vaultSrc = null, skySrc = null, deepSrc = null, astralSrc = null, prismSrc = null, orrerySrc = null, moonsporeSrc = null, stormglassSrc = null, sunwardSrc = null, ribbonwildSrc = null, tanglecrownSrc = null, worldheartSrc = null, lapisSrc = null, frostwakeSrc = null, cairnSrc = null, bankSrc = null, yearSrc = null, moonwellSrc = null, moonwellGardenSrc = null, cathedralSrc = null;    // {meta, img: {kind: Image}}
  const enemySource = s => CATHEDRAL_KINDS.includes(s.kind) ? cathedralSrc : YEAR_KINDS.includes(s.kind) ? yearSrc : CAIRN_KINDS.includes(s.kind) ? cairnSrc : FROSTWAKE_KINDS.includes(s.kind) ? frostwakeSrc : LAPIS_KINDS.includes(s.kind) ? lapisSrc : WORLDHEART_KINDS.includes(s.kind) ? worldheartSrc : TANGLECROWN_KINDS.includes(s.kind) ? tanglecrownSrc : RIBBONWILD_KINDS.includes(s.kind) ? ribbonwildSrc : SUNWARD_KINDS.includes(s.kind) ? sunwardSrc : STORMGLASS_KINDS.includes(s.kind) ? stormglassSrc : s.kind === 'moonwell_echo' ? moonwellSrc : MOONWELL_KINDS.includes(s.kind) ? moonwellGardenSrc : s.kind === 'beetle' ? beetleSrc : CRAG_KINDS.includes(s.kind) ? cragSrc : RIME_KINDS.includes(s.kind) ? rimeSrc : FEN_KINDS.includes(s.kind) ? fenSrc : WYRD_KINDS.includes(s.kind) ? wyrdSrc : SKY_KINDS.includes(s.kind) ? skySrc : DEEP_KINDS.includes(s.kind) ? deepSrc : ASTRAL_KINDS.includes(s.kind) ? astralSrc : PRISM_KINDS.includes(s.kind) ? prismSrc : ORRERY_KINDS.includes(s.kind) ? orrerySrc : MOONSPORE_KINDS.includes(s.kind) ? moonsporeSrc : VAULT_KINDS.includes(s.kind) ? vaultSrc : slimeSrc;
  const SLIME_K = 2.1, DIE_SHOW = 1.7;                      // sprite pixel -> screen px; seconds a dead slime stays on screen
  const enemyBounds = new WeakMap();
  function enemyHitbox(s) {
    const src = enemySource(s), img = src?.img[s.kind];
    if (!img) return { x0: -16, x1: 16, y0: -(s.d.top || 28), y1: 5 };
    let b = enemyBounds.get(img);
    if (b) return b;
    const [fw, fh] = src.meta.frame, [ax, ay] = src.meta.anchor, row = src.meta.clips.idle.row;
    const c = document.createElement('canvas'); c.width = fw; c.height = fh;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(img, 0, row * fh, fw, fh, 0, 0, fw, fh);
    const pixels = g.getImageData(0, 0, fw, fh).data;
    let x0 = fw, y0 = fh, x1 = -1, y1 = -1;
    for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) if (pixels[(y * fw + x) * 4 + 3] > 16) {
      x0 = Math.min(x0, x); x1 = Math.max(x1, x + 1); y0 = Math.min(y0, y); y1 = Math.max(y1, y + 1);
    }
    b = x1 < 0 ? { x0: -16, x1: 16, y0: -28, y1: 5 } : { x0: x0 - ax, x1: x1 - ax, y0: y0 - ay, y1: y1 - ay };
    enemyBounds.set(img, b);
    return b;
  }
  function drawTargetPortrait(target, canvas) {
    if (target.player) {
      const g=canvas.getContext('2d'), remote=remotePlayers.get(target.id); g.clearRect(0,0,96,96);
      if (remote?.sprite) { const sprite=remote.sprite, frame=sprite.frame('idle',MageSprite.direction(remote.fx,remote.fy),0); g.imageSmoothingEnabled=false; g.drawImage(frame,...(sprite.meta.portrait||[56,18,48,48]),0,0,96,96); return true; }
      g.fillStyle='#352c49'; g.fillRect(0,0,96,96); g.fillStyle='#f8e0a4'; g.font='bold 50px sans-serif'; g.textAlign='center'; g.fillText(target.name.slice(0,1).toUpperCase(),48,65); return false;
    }
    const g = canvas.getContext('2d'), s = { kind: target.kind, d: SLIME[target.kind] }, src = enemySource(s), img = src?.img[target.kind];
    g.clearRect(0, 0, canvas.width, canvas.height);
    if (!img) {
      g.fillStyle = s.d?.col?.[1] || '#be8a88';
      g.beginPath(); g.arc(48, 50, 28, 0, Math.PI * 2); g.fill();
      return false;
    }
    const b = enemyHitbox(s), [fw, fh] = src.meta.frame, [ax, ay] = src.meta.anchor;
    const x = Math.max(0, Math.floor(b.x0 + ax)), y = Math.max(0, Math.floor(b.y0 + ay));
    const w = Math.min(fw - x, Math.ceil(b.x1 - b.x0)), h = Math.min(fh - y, Math.ceil(b.y1 - b.y0));
    if (w > 0 && h > 0) {
      const scale = Math.min(78 / w, 78 / h), dw = w * scale, dh = h * scale;
      g.imageSmoothingEnabled = false;
      g.drawImage(img, x, src.meta.clips.idle.row * fh + y, w, h, (96 - dw) / 2, (96 - dh) / 2, dw, dh);
    }
    return true;
  }
  // Test mode (window.__valhallaTestSprites): one small coloured block per enemy kind instead of the atlas PNGs. The clip
  // table is the real one's shape (same names, frame counts and rates), so every animation state still finds its frame.
  const stubEnemies = (kinds, colours) => {
    const clips = { idle: { fps: 6, n: 6, row: 0 }, walk: { fps: 10, n: 8, row: 1 }, attack: { fps: 12, n: 8, row: 2 }, hurt: { fps: 10, n: 4, row: 3 }, die: { fps: 8, n: 8, row: 4 } };
    const meta = { frame: [12, 12], anchor: [6, 11], kinds, clips }, img = {};
    for (const k of kinds) {
      const c = document.createElement('canvas'); c.width = 8 * 12; c.height = 5 * 12; const g = c.getContext('2d');
      g.fillStyle = colours[k] || '#c33';
      for (let row = 0; row < 5; row++) for (let n = 0; n < 8; n++) g.fillRect(n * 12 + 2, row * 12 + 3, 8, 8);
      img[k] = c;
    }
    return { meta, img };
  };
  const stubOn = () => window.__valhallaTestSprites === true;
  function loadSlimeSprites(cfg) {
    if (slimeSrc) return;
    if (stubOn()) { slimeSrc = stubEnemies(['green', 'blue', 'pink', 'yellow', 'big'], { green: '#4c4', blue: '#48f', pink: '#f6a', yellow: '#ee3', big: '#a5f' }); return; }
    fetch(cfg.json).then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = cfg.png.replace('%k', k); })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); slimeSrc = { meta, img }; })).catch(() => { slimeSrc = null; });
  }
  function loadBeetleSprites() {
    if (beetleSrc) return;
    if (stubOn()) { beetleSrc = stubEnemies(['beetle'], { beetle: '#963' }); return; }
    fetch('assets/ironhide.txt').then(r => r.json()).then(meta => new Promise((resolve, reject) => {
      const img = new Image(); img.onload = () => resolve({ meta, img: { beetle: img } });
      img.onerror = reject; img.src = 'assets/ironhide.png';
    })).then(src => { beetleSrc = src; }).catch(() => { beetleSrc = null; });
  }
  // Emberfall Crags monsters: one atlas per kind (assets/crags_<kind>.png, scripts/make_crag_sprites.py), the
  // same five clips and frame meanings as the Ironhide Beetle.
  function loadCragSprites() {
    if (cragSrc) return;
    if (stubOn()) { cragSrc = stubEnemies(CRAG_KINDS, { wisp: '#6ef', spider: '#555', wraith: '#a6f', golem: '#e83', cinderlord: '#fa4' }); return; }
    fetch('assets/crags.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/crags_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); cragSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { cragSrc = null; });
  }
  // Gloamfen monsters: assets/fen_<kind>.png (scripts/make_fen_sprites.py), the same clips again.
  function loadFenSprites() {
    if (fenSrc) return;
    if (stubOn()) { fenSrc = stubEnemies(FEN_KINDS, { toad: '#7c4', croc: '#5a3', knight: '#8ca', hydra: '#a6c', gloomroot: '#4fa' }); return; }
    fetch('assets/fen.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/fen_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); fenSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { fenSrc = null; });
  }
  // Undervault monsters: assets/vault_<kind>.png (scripts/make_vault_sprites.py), the same clips again. Until an atlas loads
  // (or when none exists) enemySource is null and the procedural slime body is drawn.
  function loadVaultSprites() {
    if (vaultSrc) return;
    if (stubOn()) { vaultSrc = stubEnemies(VAULT_KINDS, { thrall: '#cba', archer: '#dc8', acolyte: '#a7f', gatewarden: '#fd8', choir: '#8df', colossus: '#9cf', hollowking: '#9f8' }); return; }
    fetch('assets/vault.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/vault_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); vaultSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { vaultSrc = null; });
  }
  // Wyrdwood monsters: assets/wyrd_<kind>.png (scripts/make_wyrd_sprites.py), the same clips again.
  function loadWyrdSprites() {
    if (wyrdSrc) return;
    if (stubOn()) { wyrdSrc = stubEnemies(WYRD_KINDS, { boar: '#a64', crow: '#446', troll: '#6a5', weaver: '#a6e', ram: '#9cf', oakhorn: '#e83', hrungnir: '#8af' }); return; }
    fetch('assets/wyrd.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/wyrd_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); wyrdSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { wyrdSrc = null; });
  }
  // Bifrost Reach monsters: assets/sky_<kind>.png (scripts/make_sky_sprites.py), the same clips again.
  function loadSkySprites() {
    if (skySrc) return;
    if (stubOn()) { skySrc = stubEnemies(SKY_KINDS, { galehound: '#9bd', prismgolem: '#a9f', skyray: '#58c', einherjar: '#8cd', thunderroc: '#fc6' }); return; }
    fetch('assets/sky.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/sky_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); skySrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { skySrc = null; });
  }
  // Ran's Deep monsters: assets/deep_<kind>.png (scripts/make_deep_sprites.py), the same clips again.
  function loadDeepSprites() {
    if (deepSrc) return;
    if (stubOn()) { deepSrc = stubEnemies(DEEP_KINDS, { draugr: '#6aa', angler: '#7fe', moray: '#bd5', siren: '#e8d', shellback: '#7a8', kraken: '#a7e', hvitserk: '#cb4', ghostmaw: '#dff' }); return; }
    fetch('assets/deep.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/deep_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); deepSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { deepSrc = null; });
  }
  function loadAstralSprites() {
    if (astralSrc) return;
    if (stubOn()) { astralSrc = stubEnemies(ASTRAL_KINDS, { voidmoth: '#a8f', crystalwyrm: '#6ef', orbitbeetle: '#fa4', eclipsedryad: '#8d6', meteorgolem: '#b9f' }); return; }
    fetch('assets/astral.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/astral_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); astralSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { astralSrc = null; });
  }
  function loadPrismSprites() {
    if (prismSrc) return;
    if (stubOn()) { prismSrc = stubEnemies(PRISM_KINDS, {miragejackal:'#c9a',shardscarab:'#7dc',glassharrier:'#a9e',prismsentinel:'#ace',mirrorqueen:'#d8f',sunshard:'#fc9'}); return; }
    fetch('assets/prism.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/prism_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); prismSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { prismSrc = null; });
  }
  function loadOrrerySprites() {
    if (orrerySrc) return;
    if (stubOn()) { orrerySrc = stubEnemies(ORRERY_KINDS, {bronzemantis:'#ca6',gearling:'#9cb',orbitseer:'#ade',chronoguard:'#bac',pendulummatron:'#eaa',epochengine:'#db8'}); return; }
    fetch('assets/orrery.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/orrery_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); orrerySrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { orrerySrc = null; });
  }
  function loadMoonsporeSprites() {
    if (moonsporeSrc) return;
    if (stubOn()) { moonsporeSrc = stubEnemies(MOONSPORE_KINDS, {glowcapgrazer:'#bfa',silkwing:'#cfe',rootlurker:'#ca8',lanternwraith:'#bfa',mireheart:'#eba',silverwidow:'#ebf',nightbloom:'#efa'}); return; }
    fetch('assets/moonspore.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/moonspore_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); moonsporeSrc = { meta, img }; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { moonsporeSrc = null; });
  }
  function loadStormglassSprites() {
    if (stormglassSrc) return;
    if (stubOn()) { stormglassSrc=stubEnemies(STORMGLASS_KINDS,{saltclaw:'#9dc',stormgull:'#eff',glassray:'#8ef',breakersentinel:'#cca',maelstromheart:'#c9f'}); return; }
    fetch('assets/stormglass.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/stormglass_${k}.png`;
    }))).then(imgs=>{stormglassSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{stormglassSrc=null;});
  }
  function loadSunwardSprites() {
    if (sunwardSrc) return;
    const kinds=[...SUNWARD_KINDS,'sun_miller','sun_keeper','sun_travel'];
    if (stubOn()) { sunwardSrc=stubEnemies(kinds,{meadowhare:'#ca9',sunbacksnail:'#ac9',brushfox:'#d85',spadebadger:'#aab',honeyjaw:'#b86',wickerwarden:'#db9',sun_miller:'#8ab',sun_keeper:'#8a8',sun_travel:'#acb'}); return; }
    fetch('assets/sunward.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/sunward_${k}.png`;
    }))).then(imgs=>{sunwardSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{sunwardSrc=null;});
  }
  function loadRibbonwildSprites() {
    if (ribbonwildSrc) return;
    const kinds=[...RIBBONWILD_KINDS,'ribbon_host','ribbon_keeper','ribbon_travel'];
    if (stubOn()) { ribbonwildSrc=stubEnemies(kinds,{ribbongecko:'#3cc',balloonbeetle:'#b7d',paintedmacaw:'#5bd',jesterling:'#e8a',paradegryphon:'#d9b',maskcolossus:'#ad9',ribbon_host:'#e8a',ribbon_keeper:'#a9d',ribbon_travel:'#7dc'}); return; }
    fetch('assets/ribbonwild.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/ribbonwild_${k}.png`;
    }))).then(imgs=>{ribbonwildSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{ribbonwildSrc=null;});
  }
  function loadTanglecrownSprites() {
    if (tanglecrownSrc) return;
    const kinds=[...TANGLECROWN_KINDS,'tangle_warden','tangle_scholar','tangle_travel'];
    if (stubOn()) { tanglecrownSrc=stubEnemies(kinds,{orchidmantis:'#ae8',canopyglider:'#7cb',poolcaiman:'#7a9',drumgorilla:'#a87',jadeanaconda:'#4b9',crownjaguar:'#da7',tangle_warden:'#5a8',tangle_scholar:'#8aa',tangle_travel:'#8ca'}); return; }
    fetch('assets/tanglecrown.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/tanglecrown_${k}.png`;
    }))).then(imgs=>{tanglecrownSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{tanglecrownSrc=null;});
  }
  function loadWorldheartSprites() {
    if (worldheartSrc) return;
    const kinds=[...WORLDHEART_KINDS,'heart_matriarch','heart_archivist','heart_oracle','heart_travel'];
    if (stubOn()) { worldheartSrc=stubEnemies(kinds,{sapbeetle:'#da9',lanternhornet:'#dd9',mosslemur:'#ad9',barkmimic:'#b98',heart_matriarch:'#9c8',heart_archivist:'#9cc',heart_oracle:'#9dc',heart_travel:'#cda'}); return; }
    fetch('assets/worldheart.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/worldheart_${k}.png`;
    }))).then(imgs=>{worldheartSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))};})).catch(()=>{worldheartSrc=null;});
  }
  function loadLapisSprites() {
    if (lapisSrc) return;
    const kinds=[...LAPIS_KINDS,'lapis_keeper','lapis_cartographer','lapis_warden','lapis_seer','lapis_travel'];
    if (stubOn()) { lapisSrc=stubEnemies(kinds,{sandhopper:'#db9',dunefennec:'#eaa',glassscorpion:'#7bc',sunvulture:'#ca9',dunecolossus:'#da9',mirageroc:'#8bd',lapis_keeper:'#8bd',lapis_cartographer:'#bab',lapis_warden:'#da9',lapis_seer:'#9bd',lapis_travel:'#8cb'}); return; }
    fetch('assets/lapis.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/lapis_${k}.png`;
    }))).then(imgs=>{lapisSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{lapisSrc=null;});
  }
  function loadFrostwakeSprites() {
    if (frostwakeSrc) return;
    const kinds=[...FROSTWAKE_KINDS,'frostwake_captain','frostwake_surveyor','frostwake_bellkeeper','frostwake_skywatcher','frostwake_ribkeeper','frostwake_travel'];
    if (stubOn()) { frostwakeSrc=stubEnemies(kinds,{snowhare:'#eef',iceotter:'#9ce',frostheron:'#def',glaciercrab:'#7bd',bellmammoth:'#cdf',auroramanta:'#8dc',crevasseleviathan:'#7ae'}); return; }
    fetch('assets/frostwake.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/frostwake_${k}.png`;
    }))).then(imgs=>{frostwakeSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{frostwakeSrc=null;});
  }
  function loadCairnSprites() {
    if (cairnSrc) return;
    const kinds=[...CAIRN_KINDS,'cairn_warden','cairn_surveyor','cairn_stonesinger','cairn_grovekeeper','cairn_windseer','cairn_travel'];
    if (stubOn()) { cairnSrc=stubEnemies(kinds,{screeferret:'#cba',stoneibex:'#ba9',slateraven:'#789',ridgeadder:'#9a8',cairnbehemoth:'#b9a',whitebarktitan:'#edc',stormcondor:'#8bb'}); return; }
    fetch('assets/cairn.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/cairn_${k}.png`;
    }))).then(imgs=>{cairnSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{cairnSrc=null;});
  }
  // The treasure chest (CHEST-ART): closed (6 frames, a glint), opening (6) and opened (2) in one 64x64 atlas. Without it
  // (it failed to load) drawChest keeps its vector chest. It is one small file, so the tests' stub sprites do not replace it.
  let chestSrc = null;
  function loadChestSprites() {
    if (chestSrc) return;
    fetch('assets/chest.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => new Promise((res, rej) => {
      const i = new Image(); i.onload = () => res({ meta, img: i }); i.onerror = rej; i.src = 'assets/chest.png';
    })).then(src => { chestSrc = src; }).catch(() => { chestSrc = null; });
  }
  // One frame of the chest atlas with its feet on (sx, sy).
  function drawChestFrame(g, row, n, sx, sy) {
    const [w, h] = chestSrc.meta.frame, [ax, ay] = chestSrc.meta.anchor;
    g.save(); g.imageSmoothingEnabled = false; g.drawImage(chestSrc.img, n * w, row * h, w, h, Math.round(sx - ax), Math.round(sy - ay), w, h); g.restore();
  }
  const BANK_KINDS=['bank_alderhaven','bank_skaldholm','bank_nacrehold','bank_astralhollow','bank_asterion'];
  function loadBankSprites() {
    if (bankSrc) return;
    if (stubOn()) { bankSrc=stubEnemies(BANK_KINDS,{}); return; }
    fetch('assets/bank.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/${k}.png`;
    }))).then(imgs=>{bankSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))};})).catch(()=>{bankSrc=null;});
  }
  function loadYearSprites() {
    if (yearSrc) return;
    const kinds=[...YEAR_KINDS,...['sp','su','au','wi'].flatMap(k=>['year_'+k+'_keeper','year_'+k+'_travel'])];
    if(stubOn()){yearSrc=stubEnemies(kinds,{});return;}
    fetch('assets/yearwheel.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/yearwheel_${k}.png?v=cel1`;
    }))).then(imgs=>{yearSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{yearSrc=null;});
  }
  function loadMoonwellSprites() {
    if (moonwellSrc) return;
    if (stubOn()) { moonwellSrc = stubEnemies(['moonwell_echo'], {moonwell_echo:'#9fe'}); return; }
    fetch('assets/moonwell.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/moonwell_echo.png`; })))
      .then(imgs => { moonwellSrc = { meta, img: {moonwell_echo: imgs[0]} }; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { moonwellSrc = null; });
  }
  function loadMoonwellGardenSprites() {
    if (moonwellGardenSrc) return;
    if (stubOn()) { moonwellGardenSrc = stubEnemies(MOONWELL_KINDS,{dew_moth:'#bde',lumen_eel:'#9ed',rootbell:'#fda',tideglass_heron:'#ade',hourpetal_stag:'#fdb',moonskein_weaver:'#eac'}); return; }
    fetch('assets/moonwell_garden.txt').then(r=>r.ok?r.json():Promise.reject()).then(meta=>Promise.all(meta.kinds.map(k=>new Promise((res,rej)=>{
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/moonwell_${k}.png`;
    }))).then(imgs=>{const img={};meta.kinds.forEach((k,n)=>img[k]=imgs[n]);moonwellGardenSrc={meta,img}; for (const k of meta.kinds) if (SLIME[k] && meta.tops?.[k]) SLIME[k].top = meta.tops[k];})).catch(()=>{moonwellGardenSrc=null;});
  }
  // Rimeveil Glacier monsters: assets/rime_<kind>.png (scripts/make_rime_sprites.py), the same clips as the Crags.
  function loadRimeSprites() {
    if (rimeSrc) return;
    if (stubOn()) { rimeSrc = stubEnemies(RIME_KINDS, { crab: '#6bd', wolf: '#cde', yeti: '#fff', wyrm: '#4ae' }); return; }
    fetch('assets/rime.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/rime_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); rimeSrc = { meta, img }; for (const k of meta.kinds) if (meta.tops?.[k]) SLIME[k].top = meta.tops[k]; })).catch(() => { rimeSrc = null; });
  }
  function loadCathedralSprites() {
    if (cathedralSrc) return;
    if (stubOn()) { cathedralSrc = stubEnemies(CATHEDRAL_KINDS,Object.fromEntries(CATHEDRAL_ENEMIES.map(e => [e.kind,e.color]))); return; }
    fetch('assets/cathedral.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res,rej) => {
      const artKind=CATHEDRAL_ENEMIES.find(e=>e.kind===k)?.artFrom || k;
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/cathedral_${artKind}.png`;
    }))).then(imgs => {
      cathedralSrc={meta,img:Object.fromEntries(meta.kinds.map((k,n)=>[k,imgs[n]]))};
      for (const kind of meta.kinds) if (meta.tops?.[kind]) SLIME[kind].top=meta.tops[kind];
    })).catch(()=>{cathedralSrc=null;});
  }
  function slimeFrame(s, t) {                               // -> [clip, frame index]; priority: dying, hurt, attack, airborne/landing, idle
    const C = enemySource(s).meta.clips;
    if (s.dead) return ['die', Math.min(C.die.n - 1, Math.floor(s.dieT * C.die.fps))];
    if (s.hurtT > 0) return ['hurt', Math.min(C.hurt.n - 1, Math.floor((.4 - s.hurtT) * C.hurt.fps))];
    if (s.state === 'windup') return ['attack', clamp(Math.floor((1 - s.st / (s.windupTime || .45)) * 3), 0, 2)];
    if (s.state === 'lunge') return ['attack', 3 + Math.min(2, Math.floor((1 - s.st / .3) * 3))];
    if (s.recT > 0) return ['attack', 6 + Math.min(1, Math.floor((1 - s.recT / .22) * 2))];
    if (s.hop > 0 || s.hopV > 0) return ['walk', s.hopV > 0 ? (s.hop < .25 ? 2 : 3) : 4];
    if (s.landT > 0) return ['walk', 5 + Math.min(2, Math.floor((1 - s.landT / .25) * 3))];
    if (s.blink < 0) return ['idle', 3];
    return ['idle', [0, 1, 2, 1, 0, 5][Math.floor(t * C.idle.fps + s.seed) % 6]];
  }
  function drawSlimeSprite(g, s, t) {
    const src = enemySource(s), m = src.meta, [fw, fh] = m.frame, [ax, ay] = m.anchor, [clip, n] = slimeFrame(s, t), c = m.clips[clip], K = SLIME_K * s.d.scale;
    g.save();
    if (s.dead) g.globalAlpha = clamp((DIE_SHOW - s.dieT) / .5, 0, 1);
    g.imageSmoothingEnabled = false; g.scale(s.dir < 0 ? -K : K, K);
    g.drawImage(src.img[s.kind], n * fw, c.row * fh, fw, fh, -ax, -ay, fw, fh);
    g.restore();
  }

  // ---------- the hero as a sprite (assets/hero_sprites.*, cut by tools/make_hero_sprites.py) ----------
  let heroSrc = null, heroSpr = null;                       // heroSrc: {img, meta}; heroSpr: recoloured copy for the current character
  function yiq(r, g, b, a) { const y = .299 * r + .587 * g + .114 * b, i = .596 * r - .274 * g - .322 * b, q = .211 * r - .523 * g + .312 * b, c = Math.cos(a), s = Math.sin(a), i2 = i * c - q * s, q2 = i * s + q * c; return [y + .956 * i2 + .621 * q2, y - .272 * i2 - .647 * q2, y - 1.106 * i2 + 1.703 * q2]; }
  function recolorSheet(img, look) {                        // cape follows the armour choice, the slash follows the rune colour
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const o = opts || {}, ah = (o.armorHues || [0])[look.armor || 0] || 0, rh = (o.runeHues || [0])[look.rune || 0] || 0;
    if (!ah && !rh) return c;
    const d = g.getImageData(0, 0, c.width, c.height), p = d.data;
    for (let i = 0; i < p.length; i += 4) {
      if (!p[i + 3]) continue; const r = p[i], gg = p[i + 1], b = p[i + 2], mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), sat = (mx - mn) / (mx || 1);
      let ang = 0;
      if (ah && r > gg * 1.6 && r > b * 1.6 && r > 90 && sat > .4) ang = ah;
      else if (rh && gg > 150 && b > 170 && r < gg - 25 && sat > .28) ang = rh;
      if (!ang) continue;
      const n = yiq(r / 255, gg / 255, b / 255, ang); p[i] = clamp(n[0] * 255, 0, 255); p[i + 1] = clamp(n[1] * 255, 0, 255); p[i + 2] = clamp(n[2] * 255, 0, 255);
    }
    g.putImageData(d, 0, 0); return c;
  }
  function loadHeroSprites(cfg, look, done) {
    const apply = () => { heroSpr = { sheet: recolorSheet(heroSrc.img, look || {}), meta: heroSrc.meta }; if (done) done(heroSrc.meta); };
    if (heroSrc) { apply(); return; }
    Promise.all([new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = cfg.png; }), fetch(cfg.json).then(r => r.json())])
      .then(([img, meta]) => { heroSrc = { img, meta }; apply(); }).catch(() => { heroSpr = null; });
  }
  function drawHeroSprite(g, h, t) {
    const m = heroSpr.meta, K = .7, dxs = h.fx - h.fy, dys = h.fx + h.fy, south = dys >= 0, right = dxs >= 0;
    const atk = h.atkT > 0 ? h.atkT / .42 : 0, walking = h.moving && !h.dead;
    let frames, flip = false;
    if (atk) { frames = south ? m.clips.atkSE : m.clips.atkN; flip = !right; }
    else { frames = south ? (right ? m.clips.walkSE : m.clips.walkSW) : m.clips.walkN; flip = !south && !right; }
    const idx = atk ? Math.min(frames.length - 1, Math.floor(atk * frames.length)) : walking ? Math.floor(h.walk * .8) % frames.length : 0;
    const f = m.frames[frames[idx]], bob = walking || atk ? 0 : Math.sin(t * 2.2) * 1.2;
    g.save();
    if (h.dead) { const k = clamp(h.deadT * 2.2, 0, 1); g.rotate(k * 1.35 * (right ? 1 : -1)); g.globalAlpha = 1 - k * .35; g.translate(0, k * 6); }
    g.scale(flip ? -K : K, K); g.translate(0, bob / K);
    g.drawImage(heroSpr.sheet, f.x, f.y, f.w, f.h, -f.ax, -f.ay, f.w, f.h);
    g.restore();
  }

  // ---------- the Warrior as an 8-direction sprite (assets/warrior_sprites.*, rendered by tools/make_warrior_sprites.py) ----------
  // Atlas: row = clips[c].row0 + dir, column = frame; dir order S SW W NW N NE E SE (screen directions); frames are 160x160 with the feet at meta.anchor.
  let warSrc = null, warSpr = null;                         // warSrc: {img, meta}; warSpr: {sheet, meta} recoloured for the current character
  const WAR_K = 1.5;                                        // sprite pixel -> screen px
  const lumOf = c => .299 * c[0] + .587 * c[1] + .114 * c[2];
  function recolorWarrior(img, meta, look) {                // creation choices recolour the atlas by exact ramp colours (hair/brow, skin, red armour, rune glow)
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const o = opts || {}, R = meta.ramps || {}, ah = (o.armorHues || [0])[look.armor || 0] || 0, rh = (o.runeHues || [0])[look.rune || 0] || 0;
    const hair = (o.hairColors || [])[look.hairColor || 0], skin = (o.skinColors || [])[look.skin || 0];
    const hex = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16)), word = c3 => (0xff000000 | (c3[2] << 16) | (c3[1] << 8) | c3[0]) >>> 0;
    const map = new Map(), put = (from, to) => map.set(word(hex(from)), word(to.map(v => clamp(Math.round(v), 0, 255))));
    const tint = (name, target) => { const ramp = R[name]; if (!ramp || !target) return; const t3 = hex(target), base = lumOf(hex(ramp[2])); for (const col of ramp) { const k = lumOf(hex(col)) / base, f = k < 1 ? k : 1 + (k - 1) * .35; put(col, t3.map(v => v * f)); } };   // highlights are damped so light hair keeps its shading
    const turn = (name, a) => { const ramp = R[name]; if (!ramp || !a) return; for (const col of ramp) { const [r, gg, b] = hex(col); put(col, yiq(r / 255, gg / 255, b / 255, a).map(v => v * 255)); } };
    tint('hair', hair); tint('brow', hair); tint('skin', skin); turn('red', ah); turn('rune', rh);
    if (!map.size) return c;
    const d = g.getImageData(0, 0, c.width, c.height), w = new Uint32Array(d.data.buffer);
    for (let i = 0; i < w.length; i++) { if (w[i] === 0) continue; const r = map.get(w[i]); if (r !== undefined) w[i] = r; }
    g.putImageData(d, 0, 0); return c;
  }
  function loadWarriorSprites(cfg, look) {
    const apply = () => { warSpr = { sheet: recolorWarrior(warSrc.img, warSrc.meta, look || {}), meta: warSrc.meta }; };
    if (warSrc) { apply(); return; }
    Promise.all([new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = cfg.png; }), fetch(cfg.json).then(r => r.json())])
      .then(([img, meta]) => { warSrc = { img, meta }; if (!isModular()) apply(); }).catch(() => { warSpr = null; });
  }
  function warFrame(h, t) {                                 // -> [clip, frame index]; priority: dead, hurt, attack, walk, idle
    const C = warSpr.meta.clips;
    if (h.dead) return ['die', Math.min(C.die.n - 1, Math.floor(h.deadT * C.die.fps))];
    if (h.hurtT > 0) return ['hurt', clamp(Math.floor((1 - h.hurtT / .25) * C.hurt.n), 0, C.hurt.n - 1)];
    if (h.atkT > 0) return ['attack', Math.min(C.attack.n - 1, Math.floor(h.atkT / .42 * C.attack.n))];
    if (h.moving) return ['walk', Math.floor(h.walk * 1.1) % C.walk.n];
    return ['idle', Math.floor(t * C.idle.fps) % C.idle.n];
  }
  function drawWarriorSprite(g, h, t) {
    const m = warSpr.meta, [fw, fh] = m.frame, [ax, ay] = m.anchor, [clip, i] = warFrame(h, t), c = m.clips[clip];
    const gx = (h.fx - h.fy) / Math.SQRT2, gy = (h.fx + h.fy) / Math.SQRT2, dir = ((Math.round(-Math.atan2(gx, gy) / (Math.PI / 4)) % 8) + 8) % 8;   // 0 = facing the camera
    g.save();
    if (h.dead && !h.fallen) g.globalAlpha = clamp((3.2 - h.deadT) / .6, 0, 1);
    g.imageSmoothingEnabled = false; g.scale(WAR_K, WAR_K);
    g.drawImage(warSpr.sheet, i * fw, (c.row0 + dir) * fh, fw, fh, -ax, -ay, fw, fh);
    g.restore();
  }

  // ---------- render ----------
  function drawSkyEmber(g, t) {
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#150b12'); gr.addColorStop(.55, '#3a1514'); gr.addColorStop(1, '#8a3414');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    const [cx, cy] = camS();
    for (let i = 0; i < 12; i++) {                       // dark smoke banks drifting below the cliffs
      const px = ((i * 397 + t * (4 + (i % 4) * 2) - cx * .2) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = (i * 211 % VH) - cy * .1 * ((i % 3) + 1) * .3 + 110 * ((i % 3) - 1) + 500, sc = .9 + (i % 4) * .35;
      g.fillStyle = 'rgba(20,10,14,.55)';
      g.beginPath(); g.ellipse(px, py, 150 * sc, 30 * sc, 0, 0, 6.283); g.ellipse(px - 80 * sc, py + 8 * sc, 90 * sc, 24 * sc, 0, 0, 6.283); g.ellipse(px + 84 * sc, py + 10 * sc, 100 * sc, 24 * sc, 0, 0, 6.283); g.fill();
      g.fillStyle = 'rgba(255,100,30,.10)'; g.beginPath(); g.ellipse(px, py + 20 * sc, 140 * sc, 10 * sc, 0, 0, 6.283); g.fill();
    }
    g.fillStyle = '#ffb347';
    for (let i = 0; i < 34; i++) {                       // embers rising on the heat
      const x = (i * 83.7 + Math.sin(t * .6 + i) * 24) % VW, y = VH - ((t * (16 + (i % 7) * 7) + i * 131) % VH);
      g.globalAlpha = .25 + .5 * ((i * 37) % 10) / 10 * Math.min(1, y / 200); g.fillRect(x, y, 2 + (i % 3), 2 + (i % 3));
    }
    g.globalAlpha = 1;
  }
  // Rimeveil Glacier: a clear polar night, stars, drifting mist and slow green-violet aurora curtains.
  function drawSkyFrost(g, t) {
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#050d1f'); gr.addColorStop(.5, '#0f2a45'); gr.addColorStop(1, '#3c6f8c');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    for (let i = 0; i < 46; i++) {                       // stars, twinkling on their own phases
      const x = (i * 211.7) % VW, y = (i * 97.3) % (VH * .6);
      g.globalAlpha = .35 + .55 * Math.abs(Math.sin(t * (.4 + (i % 5) * .15) + i)); g.fillStyle = i % 7 ? '#e8f4ff' : '#bfe0ff'; g.fillRect(x, y, 1 + (i % 3 === 0), 1 + (i % 3 === 0));
    }
    g.globalAlpha = 1;
    const curtains = [[.2, 150, '#4dffb4', .1], [.32, 110, '#7ab8ff', .6], [.14, 130, '#b58cff', 1.2]];
    curtains.forEach(([base, depth, col, phase], n) => {
      const pts = []; for (let i = 0; i <= 16; i++) { const x = i / 16 * VW; pts.push([x, VH * base + Math.sin(i * .6 + t * (.22 + n * .07) + phase * 5) * 38 + Math.sin(i * 1.3 - t * .17) * 14]); }
      const gg = g.createLinearGradient(0, VH * (base - .1), 0, VH * base + depth); gg.addColorStop(0, 'rgba(0,0,0,0)'); gg.addColorStop(.35, col + '66'); gg.addColorStop(.7, col + '33'); gg.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gg; g.beginPath(); g.moveTo(pts[0][0], pts[0][1] - 90); pts.forEach(p => g.lineTo(p[0], p[1] - 90 + Math.sin(p[0] * .02 + t * .5) * 12)); for (let i = pts.length - 1; i >= 0; i--) g.lineTo(pts[i][0], pts[i][1] + depth); g.closePath(); g.fill();
    });
    const [cx, cy] = camS();
    g.fillStyle = 'rgba(190,225,255,.10)';
    for (let i = 0; i < 9; i++) {                        // mist banks below the ice
      const px = ((i * 397 + t * (3 + (i % 4)) - cx * .2) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = (i * 211 % VH) - cy * .03 + 420 + (i % 3) * 60, sc = .9 + (i % 4) * .3;
      g.beginPath(); g.ellipse(px, py, 160 * sc, 26 * sc, 0, 0, 6.283); g.ellipse(px - 90 * sc, py + 8 * sc, 90 * sc, 20 * sc, 0, 0, 6.283); g.fill();
    }
  }
  // Gloamfen: a violet dusk with a huge pale moon, drifting ground mist and a few early stars.
  function drawSkyFen(g, t) {
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#0d0a22'); gr.addColorStop(.45, '#2a2348'); gr.addColorStop(.8, '#4a4468'); gr.addColorStop(1, '#6a6a78');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    for (let i = 0; i < 38; i++) {
      const x = (i * 197.3) % VW, y = (i * 83.1) % (VH * .55);
      g.globalAlpha = .25 + .45 * Math.abs(Math.sin(t * (.3 + (i % 5) * .1) + i)); g.fillStyle = '#e8eaff'; g.fillRect(x, y, 1 + (i % 4 === 0), 1 + (i % 4 === 0));
    }
    g.globalAlpha = 1;
    const mx = VW * .78, my = VH * .17, glow = g.createRadialGradient(mx, my, 20, mx, my, 260);
    glow.addColorStop(0, 'rgba(255,244,200,.45)'); glow.addColorStop(1, 'rgba(255,244,200,0)'); g.fillStyle = glow; g.fillRect(mx - 280, my - 280, 560, 560);
    g.fillStyle = '#fff4d0'; g.beginPath(); g.arc(mx, my, 62, 0, 6.283); g.fill();
    g.fillStyle = 'rgba(190,176,140,.45)'; for (const [dx, dy, r] of [[-20, -14, 14], [18, 12, 18], [-6, 26, 9], [26, -22, 8]]) { g.beginPath(); g.arc(mx + dx, my + dy, r, 0, 6.283); g.fill(); }
    const [cx, cy] = camS();
    g.fillStyle = 'rgba(150,180,170,.12)';
    for (let i = 0; i < 10; i++) {
      const px = ((i * 397 + t * (4 + (i % 4)) - cx * .2) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = (i * 211 % VH) - cy * .03 + 430 + (i % 3) * 60, sc = .9 + (i % 4) * .3;
      g.beginPath(); g.ellipse(px, py, 170 * sc, 26 * sc, 0, 0, 6.283); g.ellipse(px - 90 * sc, py + 8 * sc, 90 * sc, 20 * sc, 0, 0, 6.283); g.fill();
    }
  }
  // Skaldholm: a warm late afternoon. Blue overhead, peach at the horizon, a low sun with a halo and gilded clouds.
  function drawSkyCity(g, t) {
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#3f86d8'); gr.addColorStop(.45, '#8dbdee'); gr.addColorStop(.8, '#f4d6b0'); gr.addColorStop(1, '#fbe6bf');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    const sx = VW * .17, sy = VH * .8, halo = g.createRadialGradient(sx, sy, 10, sx, sy, 420);
    halo.addColorStop(0, 'rgba(255,240,190,.85)'); halo.addColorStop(.35, 'rgba(255,214,150,.35)'); halo.addColorStop(1, 'rgba(255,200,140,0)');
    g.fillStyle = halo; g.fillRect(0, 0, VW, VH);
    g.fillStyle = '#fff6d4'; g.beginPath(); g.arc(sx, sy, 38, 0, 6.283); g.fill();
    const [cx, cy] = camS();
    for (let i = 0; i < 14; i++) {
      const px = ((i * 397 + t * (5 + (i % 4) * 3) - cx * .25) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = (i * 211 % VH) - cy * .12 * ((i % 3) + 1) * .3 + 120 * ((i % 3) - 1) + 470, sc = .8 + (i % 4) * .35;
      g.fillStyle = i % 3 ? 'rgba(255,244,226,.62)' : 'rgba(255,214,170,.55)';
      g.beginPath(); g.ellipse(px, py, 130 * sc, 28 * sc, 0, 0, 6.283); g.ellipse(px - 70 * sc, py + 8 * sc, 80 * sc, 22 * sc, 0, 0, 6.283); g.ellipse(px + 76 * sc, py + 10 * sc, 90 * sc, 22 * sc, 0, 0, 6.283); g.fill();
    }
  }
  // Over the city (screen space): drifting blossom petals and the odd pigeon crossing the sky.
  function drawBlossom(g, t) {
    for (let i = 0; i < 34; i++) {
      const x = ((i * 173.1 + Math.sin(t * .6 + i) * 40 + t * (14 + i % 5 * 4)) % VW + VW) % VW, y = (i * 59.3 + t * (18 + (i % 4) * 7)) % VH;
      g.globalAlpha = .55 + (i % 3) * .15; g.fillStyle = i % 4 ? '#ffd0dc' : '#fff0d0';
      g.save(); g.translate(x, y); g.rotate(t * (.8 + i % 3 * .4) + i); g.beginPath(); g.ellipse(0, 0, 3.4, 1.8, 0, 0, 6.283); g.fill(); g.restore();
    }
    g.globalAlpha = 1; g.strokeStyle = 'rgba(70,64,80,.7)'; g.lineWidth = 2; g.lineCap = 'round';
    for (let i = 0; i < 6; i++) {
      const u = ((t * .028 + i * .17) % 1), x = -40 + u * (VW + 80), y = 120 + i * 58 + Math.sin(u * 9 + i) * 24, flap = Math.sin(t * 9 + i * 2) * 5;
      g.beginPath(); g.moveTo(x - 9, y + flap); g.quadraticCurveTo(x - 3, y - 4, x, y); g.quadraticCurveTo(x + 3, y - 4, x + 9, y + flap); g.stroke();
    }
  }
  // Fireflies drifting over the fen (screen space): slow wandering dots that pulse yellow-green.
  function drawFireflies(g, t) {
    for (let i = 0; i < 42; i++) {
      const x = ((i * 151.3 + Math.sin(t * .31 + i * 1.7) * 60 + t * 3) % VW + VW) % VW, y = (i * 97.7 + Math.cos(t * .27 + i) * 46) % VH;
      const a = Math.max(0, Math.sin(t * (.9 + (i % 5) * .23) + i * 2.3)); if (a < .08) continue;
      g.globalAlpha = a * .85; g.fillStyle = '#e6ff70'; g.shadowColor = '#d6f05a'; g.shadowBlur = 9; g.fillRect(x, y, 2.4, 2.4);
    }
    g.shadowBlur = 0; g.globalAlpha = 1;
  }
  // The mere: water discs are ground decals (and obstacles, kind 'water'), drawn in whole-lake passes so overlapping
  // discs merge into one lake: muddy rim, algae edge, black-teal depths, then moving ripples, lily pads and glints.
  function drawWater(g, t) {
    const rows = [];
    for (const o of objects) if (o.kind === 'water') { const [sx, sy] = w2s(o.x, o.y); if (sx > -140 && sx < VW + 140 && sy > -90 && sy < VH + 90) rows.push([o, sx, sy]); }
    if (!rows.length) return;
    const ex = o => o.r * TW * .7071, ey = o => o.r * TH * .7071;
    const pass = (grow, fill) => { for (const [o, sx, sy] of rows) { g.fillStyle = typeof fill === 'function' ? fill(o) : fill; g.beginPath(); g.ellipse(sx, sy + (grow < 0 ? 1 : 0), ex(o) * grow, ey(o) * grow, 0, 0, 6.283); g.fill(); } };
    const shimmer = o => .5 + .5 * Math.sin(t * .8 + o.x * .45 + o.y * .33);
    const river = zdef.theme === 'wyrd', meadow = zone === 0 || zdef.theme === 'sunward';
    pass(1.36, meadow ? '#a1ad65' : river ? '#3c2c1c' : '#2c2a1c');
    pass(1.2, meadow ? '#74a57b' : river ? '#6a7a3a' : '#3c5a30');
    pass(1.04, o => meadow ? `hsl(${192 + shimmer(o) * 7}, 58%, ${46 + shimmer(o) * 5}%)` : river ? `hsl(${200 + shimmer(o) * 8}, 46%, ${30 + shimmer(o) * 5}%)` : `hsl(${176 + shimmer(o) * 8}, 34%, ${14 + shimmer(o) * 3}%)`);
    pass(.8, o => meadow ? `hsl(${199 + shimmer(o) * 7}, 60%, ${36 + shimmer(o) * 5}%)` : river ? `hsl(${206 + shimmer(o) * 10}, 52%, ${24 + shimmer(o) * 5}%)` : `hsl(${184 + shimmer(o) * 10}, 40%, ${10 + shimmer(o) * 3}%)`);
    for (const [o, sx, sy] of rows) {
      const k = (o.x * 7 + o.y * 13) | 0;
      if (k % 3 === 0) {                                                            // an expanding ripple ring
        const ph = (t * .35 + (k % 7) * .13) % 1; g.strokeStyle = `rgba(150,210,210,${.38 * (1 - ph)})`; g.lineWidth = 1.4; g.beginPath(); g.ellipse(sx + Math.sin(k) * 10, sy + Math.cos(k) * 4, 6 + ph * 26, 2.6 + ph * 11, 0, 0, 6.283); g.stroke();
      }
      if (meadow) {
        const gl = .35 + .22 * Math.sin(t * 1.3 + k);
        g.strokeStyle = `rgba(235,255,255,${gl})`; g.lineWidth = 1.5; g.beginPath();
        g.moveTo(sx - ex(o) * .4, sy - ey(o) * .1); g.lineTo(sx + ex(o) * .12, sy - ey(o) * .1); g.stroke();
        continue;
      }
      if (river) {                                                                  // the current: a pale streak sliding east, and a drifting autumn leaf
        if (k % 3 === 1) { const ph = (t * .25 + (k % 9) * .11) % 1; g.strokeStyle = `rgba(210,235,245,${.4 * Math.sin(ph * Math.PI)})`; g.lineWidth = 1.5; g.beginPath(); g.moveTo(sx - 12 + ph * 24, sy - 1); g.lineTo(sx + 2 + ph * 24, sy - 1); g.stroke(); }
        if (k % 4 === 2) { const ph = (t * .08 + (k % 11) * .09) % 1; g.fillStyle = ['#c0481e', '#e8802a', '#eab833'][k % 3]; g.beginPath(); g.ellipse(sx - ex(o) + ph * ex(o) * 2, sy + Math.sin(ph * 9 + k) * 2, 3.4, 1.8, ph * 3, 0, 6.283); g.fill(); }
        continue;
      }
      if (k % 5 === 1) {                                                            // a lily pad, now and then with a bloom
        const lx = sx + Math.cos(k * 2) * ex(o) * .5, ly = sy + Math.sin(k * 3) * ey(o) * .5;
        g.fillStyle = '#35602c'; g.strokeStyle = '#142a14'; g.lineWidth = 1.2; g.beginPath(); g.ellipse(lx, ly, 10, 4.2, 0, 0.3, 6.0); g.lineTo(lx, ly); g.closePath(); g.fill(); g.stroke();
        if (k % 4 === 1) { g.fillStyle = '#f0a8d0'; g.beginPath(); g.ellipse(lx + 2, ly - 2, 3, 2, 0, 0, 6.283); g.fill(); }
      }
      if (k % 7 === 2) { const gl = Math.max(0, Math.sin(t * 1.6 + k)); g.fillStyle = `rgba(210,240,250,${gl * .55})`; g.fillRect(sx - 4, sy - 2, 8, 1.4); }
    }
  }
  // ---------- Bifrost Reach: floating islands over a storm, rainbow-shard bridges ----------
  const RAINBOW = ['#ff5a7a', '#ffb050', '#fff070', '#60e0a0', '#50b8ff', '#b070ff'];
  function skyGround(x, y, tone, dirt, alt) {
    if (dirt) {                                                                       // a bridge: pale glass catching every colour of the spectrum
      const hue = (x * 17 + y * 29) % 360;
      return `hsl(${hue}, 78%, ${74 + tone * 8 + alt * .4}%)`;
    }
    return `hsl(${154 + tone * 22}, ${40 + tone * 14}%, ${57 + tone * 10 + alt}%)`;  // windswept turquoise grass
  }
  function skyDetail(g, r, inTile, px, py, x, y, tone, dirt) {
    if (dirt) {
      g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(px - TW / 2 + 8, py + TH / 2); g.lineTo(px, py + 5); g.lineTo(px + TW / 2 - 8, py + TH / 2); g.stroke();
      if (r() < .4) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(255,255,255,.7)'; g.fillRect(qx - 1, qy - 1, 2, 2); }
      g.strokeStyle = 'rgba(80,90,160,.25)'; g.lineWidth = 1; g.beginPath(); g.moveTo(px, py + 2); g.lineTo(px, py + TH - 2); g.stroke();
      return;
    }
    g.lineCap = 'round';
    for (let k = 0; k < 2; k++) {                                                      // a few combed tufts and a wisp of low cloud
      const [qx, qy] = inTile();
      if (r() < .5) { const h = 4 + r() * 5; g.lineWidth = 1.6; g.strokeStyle = `hsl(${150 + tone * 20}, 50%, ${34 + tone * 8}%)`; g.beginPath(); g.moveTo(qx - 2, qy + 1); g.lineTo(qx - 5, qy - h); g.moveTo(qx + 2, qy + 1); g.lineTo(qx + 4, qy - h * .9); g.stroke(); }
      else if (r() < .35) { g.fillStyle = 'rgba(255,255,255,.2)'; g.beginPath(); g.ellipse(qx, qy, 6 + r() * 8, 2 + r() * 2, 0, 0, 6.283); g.fill(); }
    }
    if (r() < .06) { const [qx, qy] = inTile(), col = ['#ffffff', '#ffd0f0', '#c8e4ff', '#fff0a0'][Math.floor(r() * 4)]; g.strokeStyle = '#3a8a6a'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(qx, qy + 2); g.lineTo(qx, qy - 4); g.stroke(); g.fillStyle = col; for (let p = 0; p < 5; p++) { const a = p / 5 * 6.283; g.beginPath(); g.arc(qx + Math.cos(a) * 2.8, qy - 5 + Math.sin(a) * 2.2, 1.8, 0, 6.283); g.fill(); } g.fillStyle = '#f5b82e'; g.beginPath(); g.arc(qx, qy - 5, 1.3, 0, 6.283); g.fill(); }
  }
  // Above the storm: a clear gold-and-blue sky, and far below the islands a sea of dark cloud with lightning moving inside it.
  function drawSkySky(g, t) {
    const [cx, cy] = camS(), hz = VH * .6;
    const gr = g.createLinearGradient(0, 0, 0, VH);
    gr.addColorStop(0, '#244596'); gr.addColorStop(.3, '#4f88dc'); gr.addColorStop(.5, '#a8d0f4'); gr.addColorStop(.6, '#ffe0b4'); gr.addColorStop(.62, '#6a5a86'); gr.addColorStop(.8, '#2c2848'); gr.addColorStop(1, '#14122a');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    const sx = VW * .78 - cx * .02, sy = VH * .2 - cy * .01, sun = g.createRadialGradient(sx, sy, 8, sx, sy, 340);
    sun.addColorStop(0, 'rgba(255,248,215,.95)'); sun.addColorStop(.12, 'rgba(255,236,170,.6)'); sun.addColorStop(1, 'rgba(255,210,140,0)'); g.fillStyle = sun; g.fillRect(sx - 360, sy - 360, 720, 720);
    g.save(); g.globalAlpha = .08; g.fillStyle = '#fff';                                    // slanting shafts of light
    for (let i = 0; i < 5; i++) { const bx = sx - 520 + i * 210; g.beginPath(); g.moveTo(sx - 14, sy); g.lineTo(sx + 14, sy); g.lineTo(bx + 90, VH * .62); g.lineTo(bx - 90, VH * .62); g.closePath(); g.fill(); }
    g.restore();
    for (let i = 0; i < 6; i++) {                                                       // distant islands in the haze
      const px = ((i * 331 - cx * .08) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = VH * (.34 + (i % 3) * .08) - cy * .04, s = .6 + (i % 3) * .3;
      g.fillStyle = 'rgba(150,170,215,.55)'; g.beginPath(); g.ellipse(px, py, 70 * s, 12 * s, 0, 0, 6.283); g.fill();
      g.beginPath(); g.moveTo(px - 60 * s, py + 4 * s); g.lineTo(px + 60 * s, py + 4 * s); g.lineTo(px + 8 * s, py + 46 * s); g.lineTo(px - 14 * s, py + 30 * s); g.closePath(); g.fill();
    }
    // high, bright cloud
    g.fillStyle = 'rgba(255,255,255,.6)';
    for (let i = 0; i < 8; i++) {
      const px = ((i * 397 + t * (5 + (i % 3) * 2) - cx * .16) % (VW + 600) + VW + 600) % (VW + 600) - 300, py = VH * (.1 + (i % 4) * .1) - cy * .05, sc = .8 + (i % 3) * .4;
      g.beginPath(); g.ellipse(px, py, 150 * sc, 22 * sc, 0, 0, 6.283); g.ellipse(px - 80 * sc, py + 6 * sc, 90 * sc, 18 * sc, 0, 0, 6.283); g.ellipse(px + 90 * sc, py + 7 * sc, 100 * sc, 18 * sc, 0, 0, 6.283); g.fill();
    }
    // the storm below: banks of dark cloud that slide with the camera, lit from inside
    const L = lightningAt(t);
    for (let layer = 0; layer < 3; layer++) {
      g.fillStyle = ['rgba(70,62,104,.8)', 'rgba(48,42,80,.85)', 'rgba(30,26,58,.9)'][layer];
      for (let i = 0; i < 9; i++) {
        const sp = .22 + layer * .14, px = ((i * 283 + layer * 91 + t * (6 + layer * 3) - cx * sp) % (VW + 700) + VW + 700) % (VW + 700) - 350, py = hz + 30 + layer * 90 - cy * (.1 + layer * .06) + (i % 3) * 14, sc = 1 + (i % 3) * .3;
        g.beginPath(); g.ellipse(px, py, 230 * sc, 52 * sc, 0, 0, 6.283); g.ellipse(px - 150 * sc, py + 18 * sc, 150 * sc, 40 * sc, 0, 0, 6.283); g.ellipse(px + 160 * sc, py + 20 * sc, 160 * sc, 42 * sc, 0, 0, 6.283); g.fill();
      }
    }
    if (L.flash > 0) {
      g.save(); g.globalCompositeOperation = 'lighter';
      const rng = rngf(L.k * 7919 + 5), fx = VW * (.1 + rng() * .8), fy = VH * (.74 + rng() * .1), fl = g.createRadialGradient(fx, fy, 10, fx, fy, 420);
      fl.addColorStop(0, `rgba(190,170,255,${.7 * L.flash})`); fl.addColorStop(1, 'rgba(120,100,220,0)'); g.fillStyle = fl; g.fillRect(0, hz, VW, VH - hz);
      g.strokeStyle = `rgba(235,230,255,${L.flash})`; g.lineWidth = 3; g.lineJoin = 'round'; g.beginPath(); let x = fx, y = hz + 40; g.moveTo(x, y);
      for (let i = 0; i < 7; i++) { x += (rng() - .5) * 50; y += 26 + rng() * 14; g.lineTo(x, y); } g.stroke();
      g.restore();
    }
  }
  // Wisps of cloud drifting past in front, and sparks of bridge-glass.
  function drawSkyWeather(g, t) {
    g.save();
    for (let i = 0; i < 7; i++) {
      const x = ((i * 313 + t * (38 + (i % 3) * 14)) % (VW + 600) + VW + 600) % (VW + 600) - 300, y = (i * 137 + 40 + Math.sin(t * .2 + i) * 20) % VH, sc = 1 + (i % 3) * .5;
      g.globalAlpha = .1; g.fillStyle = '#fff'; g.beginPath(); g.ellipse(x, y, 190 * sc, 12 * sc, 0, 0, 6.283); g.fill();
    }
    g.globalAlpha = 1; g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 26; i++) { const a = Math.max(0, Math.sin(t * 1.7 + i * 2.3)); if (a < .2) continue; const x = (i * 211.7 + Math.sin(t * .3 + i) * 30) % VW, y = (i * 97.3 + t * 12) % VH; g.fillStyle = `hsla(${(i * 47 + t * 30) % 360}, 100%, 80%, ${a * .6})`; g.fillRect(x, y, 2, 2); }
    g.restore();
  }
  // A ward's rune circle on the ground. Dim blue when you have no use for it, amber while you are holding it (with an arc for the
  // progress), gold once it holds. The circle is as wide as the place the server checks.
  function drawWardRings(g, t) {
    for (const o of objects) {
      if (o.kind !== 'wardstone') continue;
      const place = (zdef.places || []).find(p => p.id === o.place); if (!place) continue;
      const [sx, sy] = w2s(place.x, place.y); if (sx < -300 || sx > VW + 300 || sy < -200 || sy > VH + 200) continue;
      const h = window.Quests?.hold?.(o.place) || { state: 'none', have: 0, need: 1 }, inside = Math.hypot(hero.x - place.x, hero.y - place.y) <= place.r;
      const rx = place.r * TW * .7071, ry = place.r * TH * .7071, col = h.state === 'done' ? '255,215,90' : h.state === 'active' ? (inside ? '255,170,60' : '255,200,120') : '110,200,255';
      g.save(); g.translate(sx, sy);
      const fill = g.createRadialGradient(0, 0, 4, 0, 0, rx); fill.addColorStop(0, `rgba(${col},${h.state === 'active' && inside ? .26 : .1})`); fill.addColorStop(1, `rgba(${col},.02)`);
      g.fillStyle = fill; g.beginPath(); g.ellipse(0, 0, rx, ry, 0, 0, 6.283); g.fill();
      g.lineWidth = 3; g.strokeStyle = `rgba(${col},${.45 + .25 * Math.sin(t * 2)})`; g.beginPath(); g.ellipse(0, 0, rx, ry, 0, 0, 6.283); g.stroke();
      g.lineWidth = 1.6; g.strokeStyle = `rgba(${col},.5)`; g.beginPath(); g.ellipse(0, 0, rx * .8, ry * .8, 0, 0, 6.283); g.stroke();
      for (let i = 0; i < 12; i++) { const a = i / 12 * 6.283 + t * (h.state === 'active' ? .5 : .1); g.fillStyle = `rgba(${col},.8)`; g.fillRect(Math.cos(a) * rx * .9 - 2, Math.sin(a) * ry * .9 - 2, 4, 3); }
      if (h.state === 'active' || h.state === 'done') {
        const f = h.state === 'done' ? 1 : clamp(h.have / h.need, 0, 1);
        g.lineWidth = 6; g.lineCap = 'round'; g.strokeStyle = `rgba(${col},.95)`; g.shadowColor = `rgb(${col})`; g.shadowBlur = 12; g.beginPath(); g.ellipse(0, 0, rx * 1.04, ry * 1.04, 0, -Math.PI / 2, -Math.PI / 2 + 6.283 * f); g.stroke(); g.shadowBlur = 0;
        if (h.state === 'active' && inside) { g.font = '700 22px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#2a2040'; const text = `${h.have} / ${h.need} s`; g.strokeText(text, 0, ry + 34); g.fillStyle = '#fff2c8'; g.fillText(text, 0, ry + 34); }
      }
      g.restore();
    }
  }
  // ---------- Ran's Deep: sea-floor sand, a dark sea beyond the outer wall, light shafts, bubbles and the tidebells' ground circles ----------
  const beyondDeepWall = (x, y) => { const b = zdef.bounds; return !!b && (x + .5 < b.x0 || x + .5 > b.x1 || y + .5 < b.y0 || y + .5 > b.y1); };
  function deepGround(x, y, tone, dirt, alt) {
    if (zdef.theme === 'nacre') return dirt === 2 ? `hsl(${174 + tone * 8}, 28%, ${72 + tone * 7}%)` : dirt ? `hsl(${184 + tone * 7}, 25%, ${56 + tone * 8}%)` : `hsl(${182 + tone * 12}, 32%, ${31 + tone * 9}%)`;
    if (beyondDeepWall(x, y)) return `hsl(208, 55%, ${5 + tone * 3}%)`;                   // black water outside the outer wall
    if (dirt) return `hsl(${46 + tone * 8}, ${24 + tone * 8}%, ${64 + tone * 8 + alt * .5}%)`;   // the trail: pale shell-sand
    return `hsl(${178 + tone * 16}, ${22 + tone * 10}%, ${22 + (y / MAP) * 16 + tone * 8 + alt * .7}%)`;   // teal-grey sand, deeper (darker) towards the north
  }
  function deepDetail(g, r, inTile, px, py, x, y, tone, dirt) {
    if (beyondDeepWall(x, y)) return;
    g.lineCap = 'round';
    if (r() < .55) {                                                                  // a ripple in the sand: two short curved strokes
      const [qx, qy] = inTile(), l = 9 + r() * 9;
      g.strokeStyle = dirt ? 'rgba(110,90,50,.2)' : 'rgba(0,28,44,.28)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(qx - l, qy + 1); g.quadraticCurveTo(qx, qy - 3, qx + l, qy + 1); g.stroke();
      g.strokeStyle = 'rgba(210,245,255,.12)'; g.lineWidth = 1; g.beginPath(); g.moveTo(qx - l, qy - .5); g.quadraticCurveTo(qx, qy - 4.5, qx + l, qy - .5); g.stroke();
    }
    const q = r();
    if (q < .07) { const [qx, qy] = inTile(); g.fillStyle = ['#f4e8d8', '#f0c8c0', '#e8e0f4'][Math.floor(r() * 3)]; g.strokeStyle = 'rgba(20,40,50,.6)'; g.lineWidth = 1; g.beginPath(); g.ellipse(qx, qy - 1, 3.4, 2.2, r() * 3, 0, 6.283); g.fill(); g.stroke(); }   // a shell
    else if (q < .13) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(60,76,92,.9)'; g.beginPath(); g.ellipse(qx, qy - 1, 2.6 + r() * 2, 1.8, 0, 0, 6.283); g.fill(); g.fillStyle = 'rgba(190,210,220,.4)'; g.fillRect(qx - 1.4, qy - 2.4, 2.2, .9); }   // a pebble
    else if (q < .2) { const [qx, qy] = inTile(), h = 5 + r() * 6; g.strokeStyle = `hsl(${140 + r() * 30}, 45%, ${28 + tone * 10}%)`; g.lineWidth = 1.6; g.beginPath(); g.moveTo(qx - 2, qy + 1); g.quadraticCurveTo(qx - 5, qy - h * .5, qx - 3, qy - h); g.moveTo(qx + 1, qy + 1); g.quadraticCurveTo(qx + 4, qy - h * .6, qx + 2, qy - h * 1.1); g.stroke(); }   // seaweed
    else if (q < .215) { const [qx, qy] = inTile(); g.fillStyle = '#e88a5a'; g.strokeStyle = 'rgba(60,20,10,.7)'; g.lineWidth = 1; g.beginPath(); for (let k = 0; k < 10; k++) { const a = k * .628 - 1.57, rr = k % 2 ? 2.2 : 6; g.lineTo(qx + Math.cos(a) * rr * 1.1, qy + Math.sin(a) * rr * .55); } g.closePath(); g.fill(); g.stroke(); }   // a starfish
    else if (q < .225) { const [qx, qy] = inTile(); g.strokeStyle = '#d8d0b8'; g.lineWidth = 2; g.beginPath(); g.moveTo(qx - 5, qy); g.lineTo(qx + 5, qy - 2); g.stroke(); g.fillStyle = '#d8d0b8'; g.beginPath(); g.arc(qx - 5, qy, 1.8, 0, 6.283); g.arc(qx + 5, qy - 2, 1.8, 0, 6.283); g.fill(); }   // a bone
  }
  // Beyond the walls there is only deep water: a gradient, shafts of light from the surface and drifting marine snow.
  function drawSkyDeep(g, t) {
    const [cx, cy] = camS();
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#0a5a78'); gr.addColorStop(.45, '#073a56'); gr.addColorStop(1, '#020c18');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    g.save(); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 6; i++) { const bx = ((i * 331 - cx * .05) % (VW + 400) + VW + 400) % (VW + 400) - 200, sway = Math.sin(t * .25 + i) * 40; g.fillStyle = `rgba(150,230,240,${.05 - i * .004})`; g.beginPath(); g.moveTo(bx - 30 + sway, 0); g.lineTo(bx + 30 + sway, 0); g.lineTo(bx + 190, VH); g.lineTo(bx - 110, VH); g.closePath(); g.fill(); }
    g.restore();
  }
  // Marine snow, rising bubbles, slow shafts of light and a few shoals of fish, over everything; a darker rim and a green-blue tint.
  function drawDeepWeather(g, t) {
    const [cx, cy] = camS();
    g.save();
    g.fillStyle = 'rgba(6,74,104,.17)'; g.fillRect(0, 0, VW, VH);
    g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 4; i++) {                                                                  // shafts of light, swaying
      const bx = ((i * 463 + t * 6 - cx * .12) % (VW + 600) + VW + 600) % (VW + 600) - 300, sway = Math.sin(t * .3 + i * 1.7) * 50;
      g.fillStyle = `rgba(170,240,245,${.035 + .01 * Math.sin(t * .5 + i)})`; g.beginPath(); g.moveTo(bx - 40 + sway, -20); g.lineTo(bx + 40 + sway, -20); g.lineTo(bx + 250, VH + 20); g.lineTo(bx - 150, VH + 20); g.closePath(); g.fill();
    }
    for (let i = 0; i < 10; i++) {                                                                 // caustic light drifting over the floor
      const x = ((i * 241 + t * (10 + i % 3 * 4) - cx * .5) % (VW + 300) + VW + 300) % (VW + 300) - 150, y = ((i * 173 + Math.sin(t * .4 + i) * 40 - cy * .5) % (VH + 200) + VH + 200) % (VH + 200) - 100;
      const rx = 90 + (i % 4) * 30; g.fillStyle = 'rgba(200,255,245,.028)'; g.beginPath(); g.ellipse(x, y, rx, rx * .4, Math.sin(t * .3 + i) * .3, 0, 6.283); g.fill();
    }
    g.globalCompositeOperation = 'source-over';
    for (let i = 0; i < 28; i++) {                                                                 // bubbles
      const f = ((t * (.05 + (i % 5) * .018) + i * .137) % 1), x = ((i * 97.3 - cx * .35 + Math.sin(f * 9 + i) * 14) % VW + VW) % VW, y = VH + 20 - f * (VH + 60), r = 1.6 + (i % 4) * 1.1;
      g.globalAlpha = Math.min(1, f * 5) * (1 - f * .5) * .5; g.strokeStyle = 'rgba(230,250,255,.9)'; g.lineWidth = 1.2; g.beginPath(); g.arc(x, y, r, 0, 6.283); g.stroke();
      g.fillStyle = 'rgba(255,255,255,.35)'; g.beginPath(); g.arc(x - r * .3, y - r * .3, r * .3, 0, 6.283); g.fill();
    }
    g.globalAlpha = 1;
    g.fillStyle = 'rgba(190,225,230,.28)';                                                         // marine snow
    for (let i = 0; i < 40; i++) { const x = ((i * 211.7 + Math.sin(t * .3 + i) * 26 - cx * .6) % VW + VW) % VW, y = ((i * 97.3 + t * (6 + i % 4 * 2) - cy * .6) % VH + VH) % VH; g.fillRect(x, y, 1.6, 1.6); }
    for (let s = 0; s < 3; s++) {                                                                  // shoals: a handful of small fish crossing in a loose bunch
      const dir = s % 2 ? -1 : 1, base = ((t * (22 + s * 7) * dir + s * 700 - cx * .3 * dir) % (VW + 600) + VW + 600) % (VW + 600) - 300, y0 = VH * (.18 + s * .26) + Math.sin(t * .2 + s) * 20;
      g.fillStyle = 'rgba(12,40,58,.55)';
      for (let k = 0; k < 7; k++) { const x = base + dir * (k % 3) * 14 - dir * Math.floor(k / 3) * 9, y = y0 + (k - 3) * 6 + Math.sin(t * 2 + k) * 2, tail = Math.sin(t * 9 + k) * 2; g.beginPath(); g.moveTo(x + dir * 7, y); g.quadraticCurveTo(x, y - 3.2, x - dir * 6, y + tail * .4); g.quadraticCurveTo(x, y + 3.2, x + dir * 7, y); g.fill(); g.beginPath(); g.moveTo(x - dir * 5, y); g.lineTo(x - dir * 9, y - 3 + tail); g.lineTo(x - dir * 9, y + 3 + tail); g.closePath(); g.fill(); }
    }
    const v = g.createRadialGradient(VW / 2, VH / 2, VH * .35, VW / 2, VH / 2, VH * .95); v.addColorStop(0, 'rgba(2,16,30,0)'); v.addColorStop(1, 'rgba(2,16,30,.55)');   // a darker rim
    g.fillStyle = v; g.fillRect(0, 0, VW, VH);
    g.restore();
  }
  // A tidebell's circle on the ground (as wide as the place the server checks): dim blue when you have no use for it, amber while a
  // chime quest of yours waits for it, bright blue with a shrinking arc and the seconds left while it rings, gold once the chain has rung.
  function drawChimeRings(g, t) {
    for (const o of objects) {
      if (o.kind !== 'tidebell') continue;
      const place = (zdef.places || []).find(p => p.id === o.place); if (!place) continue;
      const [sx, sy] = w2s(place.x, place.y); if (sx < -300 || sx > VW + 300 || sy < -200 || sy > VH + 200) continue;
      const c = window.Quests?.chime?.(o.place) || { state: 'none' }, inside = Math.hypot(hero.x - place.x, hero.y - place.y) <= place.r;
      const rx = place.r * TW * .7071, ry = place.r * TH * .7071, col = c.state === 'done' ? '255,215,110' : c.state === 'ringing' ? '120,232,255' : c.state === 'waiting' ? '255,190,110' : '100,190,230';
      g.save(); g.translate(sx, sy);
      const fill = g.createRadialGradient(0, 0, 4, 0, 0, rx); fill.addColorStop(0, `rgba(${col},${c.state === 'ringing' ? .3 : c.state === 'waiting' && inside ? .24 : .1})`); fill.addColorStop(1, `rgba(${col},.02)`);
      g.fillStyle = fill; g.beginPath(); g.ellipse(0, 0, rx, ry, 0, 0, 6.283); g.fill();
      const live = c.state === 'waiting' || c.state === 'ringing' || c.state === 'done';
      g.lineWidth = live ? 5 : 3; g.strokeStyle = `rgba(${col},${(live ? .72 : .45) + .22 * Math.sin(t * 2.2)})`; g.beginPath(); g.ellipse(0, 0, rx, ry, 0, 0, 6.283); g.stroke();
      g.lineWidth = live ? 2.4 : 1.6; g.strokeStyle = `rgba(${col},${live ? .7 : .5})`; g.beginPath(); g.ellipse(0, 0, rx * .78, ry * .78, 0, 0, 6.283); g.stroke();
      if (c.state === 'ringing') {
        const f = clamp((c.left || 0) / (c.burn || 1), 0, 1);
        g.lineWidth = 6; g.lineCap = 'round'; g.strokeStyle = `rgba(${col},.95)`; g.shadowColor = `rgb(${col})`; g.shadowBlur = 12; g.beginPath(); g.ellipse(0, 0, rx * 1.05, ry * 1.05, 0, -Math.PI / 2, -Math.PI / 2 + 6.283 * f); g.stroke(); g.shadowBlur = 0;
        g.font = '700 22px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#06283a'; const text = `${Math.ceil(c.left || 0)} s · ${c.have} / ${c.need} ringing`; g.strokeText(text, 0, ry + 34); g.fillStyle = '#d8f8ff'; g.fillText(text, 0, ry + 34);
      }
      g.restore();
    }
  }
  // ---------- the Wyrdwood: ground, river bridge, storm sky and weather ----------
  const moorK = y => clamp((104 - y) / 10, 0, 1);              // 0 in the south forest, 1 on the Highmoor
  function wyrdGround(x, y, tone, dirt, alt) {
    const m = moorK(y + .5);
    if (dirt) return `hsl(${lerp(32, 40, m) + tone * 6}, ${lerp(34, 10, m)}%, ${lerp(38, 46, m) + tone * 6 + alt}%)`;
    return `hsl(${lerp(26, 88, m) + tone * 10}, ${lerp(40, 22, m) + tone * 6}%, ${lerp(24, 27, m) + tone * 8 + alt * .7}%)`;
  }
  function wyrdDetail(g, r, inTile, px, py, x, y, tone, dirt) {
    const m = moorK(y + .5);
    g.lineCap = 'round';
    if (dirt) { for (let k = 0; k < 3; k++) { const [qx, qy] = inTile(); g.fillStyle = r() < .5 ? 'rgba(70,44,20,.35)' : 'rgba(255,225,170,.2)'; g.beginPath(); g.ellipse(qx, qy, 2 + r() * 3, 1.2 + r() * 1.5, 0, 0, 6.283); g.fill(); } return; }
    if (m < .5) {                                                                   // forest floor: fallen leaves, moss, the odd toadstool
      const n = 1 + Math.floor(r() * 3);
      for (let k = 0; k < n; k++) { const [qx, qy] = inTile(); g.fillStyle = ['#b8421e', '#e2761f', '#e8b02a', '#8a3a1a', '#c8892a'][Math.floor(r() * 5)]; g.beginPath(); g.ellipse(qx, qy, 2.4 + r() * 1.8, 1.2 + r(), r() * 3, 0, 6.283); g.fill(); }
      if (r() < .05) { const [qx, qy] = inTile(); g.fillStyle = '#e8e0c8'; g.fillRect(qx - 1, qy - 4, 2, 4); g.fillStyle = '#c42a38'; g.beginPath(); g.ellipse(qx, qy - 5, 4, 2.6, 0, Math.PI, 0); g.fill(); g.fillStyle = '#f7f0dc'; g.fillRect(qx - 1, qy - 6, 1.4, 1.4); }
      else if (r() < .09) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(58,96,38,.4)'; g.beginPath(); g.ellipse(qx, qy, 5 + r() * 7, 2 + r() * 2.4, 0, 0, 6.283); g.fill(); }
      else if (r() < .07) { const [qx, qy] = inTile(), h = 4 + r() * 4; g.strokeStyle = '#8a7a34'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(qx - 2, qy + 1); g.lineTo(qx - 3.5, qy - h); g.moveTo(qx + 2, qy + 1); g.lineTo(qx + 3.5, qy - h * .9); g.stroke(); }
    } else {                                                                        // moor: heather, tussocks, small stones
      if (r() < .3) { const [qx, qy] = inTile(), h = 4 + r() * 4; g.strokeStyle = `hsl(${74 + tone * 14}, 24%, ${30 + tone * 8}%)`; g.lineWidth = 1.6; g.beginPath(); g.moveTo(qx - 2.5, qy + 1); g.lineTo(qx - 4, qy - h); g.moveTo(qx + 2.5, qy + 1); g.lineTo(qx + 4, qy - h * .9); g.moveTo(qx, qy + 1); g.lineTo(qx, qy - h * 1.2); g.stroke(); }
      if (r() < .16) { const [qx, qy] = inTile(); g.fillStyle = r() < .5 ? '#8a5ab0' : '#b080d0'; for (let k = 0; k < 3; k++) g.fillRect(qx + k * 2 - 2, qy - 2 - (k % 2), 1.7, 1.7); }
      if (r() < .05) { const [qx, qy] = inTile(); g.fillStyle = '#7f8590'; g.strokeStyle = OL; g.lineWidth = 1.1; g.beginPath(); g.ellipse(qx, qy - 2, 3.4, 2.5, 0, 0, 6.283); g.fill(); g.stroke(); g.fillStyle = '#a9afb8'; g.fillRect(qx - 2, qy - 3.4, 2.4, 1); }
      else if (r() < .02) { const [qx, qy] = inTile(); g.fillStyle = 'rgba(60,82,110,.55)'; g.beginPath(); g.ellipse(qx, qy, 8 + r() * 5, 3.2 + r() * 2, 0, 0, 6.283); g.fill(); g.fillStyle = 'rgba(190,215,235,.35)'; g.fillRect(qx - 3, qy - 1, 5, 1); }
    }
  }
  // The Troll Bridge: a plank deck over the gap in the river, with rails (the zone lists `bridges`; the server only has the gap).
  function drawBridges(g, t) {
    for (const b of zdef.bridges || []) {
      const dx = b.x1 - b.x0, dy = b.y1 - b.y0, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len, half = b.w / 2 + .45;
      const P = (u, v, z = 0) => w2s(b.x0 + ux * u - uy * half * v, b.y0 + uy * u + ux * half * v, z);
      const quad = (pts, fill, stroke) => { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fillStyle = fill; g.fill(); if (stroke) { g.strokeStyle = stroke; g.lineWidth = 2; g.lineJoin = 'round'; g.stroke(); } };
      quad([P(-.4, -1, -2), P(len + .4, -1, -2), P(len + .4, 1, -2), P(-.4, 1, -2)], 'rgba(10,18,20,.45)', null);        // the shadow on the water
      quad([P(0, 1, 5), P(len, 1, 5), P(len, 1, -9), P(0, 1, -9)], '#4a3320', OL);                                  // the near side beam
      quad([P(0, -1, 5), P(len, -1, 5), P(len, 1, 5), P(0, 1, 5)], '#8f6d44', OL);                                  // the deck
      g.lineWidth = 1.4; g.strokeStyle = 'rgba(40,24,10,.5)';
      for (let u = .5; u < len; u += .75) { const a = P(u, -1, 5), c = P(u, 1, 5); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke(); }
      g.strokeStyle = 'rgba(255,225,170,.18)'; for (let u = .5; u < len; u += 1.5) { const a = P(u, -.8, 5), c = P(u + .5, -.8, 5); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke(); }
      for (const v of [-1, 1]) {                                                                                       // rails: posts and two bars
        for (let u = 0; u <= len + .01; u += 2.4) { const a = P(u, v, 5), c = P(u, v, 34); g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke(); g.strokeStyle = '#6a4a2a'; g.lineWidth = 3.4; g.stroke(); }
        for (const z of [34, 20]) { const a = P(0, v, z), c = P(len, v, z); g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(c[0], c[1]); g.stroke(); g.strokeStyle = z > 30 ? '#8a6238' : '#75522e'; g.lineWidth = 3.2; g.stroke(); }
      }
      for (const u of [0, len]) for (const v of [-1, 1]) { const a = P(u, v, 34); g.fillStyle = '#c9a870'; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.arc(a[0], a[1] - 3, 4, 0, 6.283); g.fill(); g.stroke(); }
    }
  }
  const lightningAt = t => { const k = Math.floor(t / 7.3), ph = t - k * 7.3; return { k, ph, flash: ph < .12 ? 1 - ph / .12 : ph > .3 && ph < .4 ? .55 * (1 - (ph - .3) / .1) : 0 }; };
  const stormLevel = () => clamp((100 - hero.y) / 55, 0, 1);       // 0 in the forest, 1 on the heights
  function drawSkyWyrd(g, t) {
    const st = stormLevel();
    const gr = g.createLinearGradient(0, 0, 0, VH);
    gr.addColorStop(0, `hsl(${lerp(236, 250, st)}, ${lerp(32, 22, st)}%, ${lerp(24, 13, st)}%)`); gr.addColorStop(.5, `hsl(${lerp(12, 262, st)}, ${lerp(46, 18, st)}%, ${lerp(38, 28, st)}%)`); gr.addColorStop(1, `hsl(${lerp(28, 280, st)}, ${lerp(70, 14, st)}%, ${lerp(52, 38, st)}%)`);
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    const sunA = 1 - st;
    if (sunA > .02) { const sx = VW * .2, sy = VH * .3, glow = g.createRadialGradient(sx, sy, 10, sx, sy, 300); glow.addColorStop(0, `rgba(255,190,110,${.5 * sunA})`); glow.addColorStop(1, 'rgba(255,170,90,0)'); g.fillStyle = glow; g.fillRect(sx - 320, sy - 320, 640, 640); g.fillStyle = `rgba(255,214,150,${.9 * sunA})`; g.beginPath(); g.arc(sx, sy, 46, 0, 6.283); g.fill(); }
    const [cx, cy] = camS();
    g.fillStyle = `rgba(${lerp(70, 22, st)},${lerp(48, 22, st)},${lerp(60, 36, st)},${.28 + st * .3})`;
    for (let i = 0; i < 12; i++) {
      const px = ((i * 397 + t * (5 + (i % 4) * 2) - cx * .2) % (VW + 600) + VW + 600) % (VW + 600) - 300, py = (i * 173 % (VH * .7)) - cy * .04 + 80 + (i % 3) * 70, sc = 1 + (i % 4) * .35;
      g.beginPath(); g.ellipse(px, py, 200 * sc, 34 * sc, 0, 0, 6.283); g.ellipse(px - 110 * sc, py + 10 * sc, 120 * sc, 26 * sc, 0, 0, 6.283); g.ellipse(px + 120 * sc, py + 12 * sc, 130 * sc, 26 * sc, 0, 0, 6.283); g.fill();
    }
    const L = lightningAt(t);
    if (L.flash > 0 && st > .05) {                                   // a forked bolt from the cloud base, somewhere across the sky
      const rng = rngf(L.k * 7919 + 13), x0 = VW * (.15 + rng() * .7);
      g.strokeStyle = `rgba(215,236,255,${L.flash})`; g.lineWidth = 3; g.shadowColor = '#9fd0ff'; g.shadowBlur = 18; g.lineJoin = 'round';
      g.beginPath(); let x = x0, y = 40; g.moveTo(x, y); for (let i = 0; i < 9; i++) { x += (rng() - .5) * 60; y += 38 + rng() * 22; g.lineTo(x, y); if (i === 3) { const bx = x, by = y; g.moveTo(bx, by); g.lineTo(bx + 40 * (rng() - .3), by + 90); g.moveTo(x, y); } } g.stroke(); g.shadowBlur = 0;
    }
  }
  function drawWyrdWeather(g, t) {
    const st = stormLevel();
    g.save();
    for (let i = 0; i < 44; i++) {                                    // falling leaves, fewer in the storm
      if (i / 44 > 1 - st * .7) continue;
      const sp = 22 + (i % 5) * 7, x = ((i * 151.7 + Math.sin(t * .8 + i) * 40 + t * 26) % (VW + 80) + VW + 80) % (VW + 80) - 40, y = (i * 67.3 + t * sp) % (VH + 40) - 20, a = t * 1.3 + i;
      g.globalAlpha = .75; g.fillStyle = ['#c0481e', '#e8802a', '#eab833', '#9a3a1a'][i % 4];
      g.beginPath(); g.ellipse(x, y, 4.2, 2.1, a, 0, 6.283); g.fill();
    }
    g.globalAlpha = 1;
    if (st > .08) {                                                   // rain on the heights
      g.strokeStyle = `rgba(190,210,235,${.32 * st})`; g.lineWidth = 1.2; g.beginPath();
      for (let i = 0; i < 150 * st; i++) { const x = ((i * 97.3 + t * 160) % (VW + 200)) - 100, y = (i * 53.9 + t * 760) % (VH + 60) - 30; g.moveTo(x, y); g.lineTo(x - 7, y + 18); }
      g.stroke();
    }
    const L = lightningAt(t);
    if (L.flash > 0) { g.fillStyle = `rgba(215,232,255,${L.flash * (.1 + .3 * st)})`; g.fillRect(0, 0, VW, VH); }
    g.restore();
  }
  // Snow falling over the world (screen space) on the glacier.
  function drawSnowfall(g, t) {
    g.fillStyle = '#f4fbff';
    for (let i = 0; i < 70; i++) {
      const sp = 26 + (i % 5) * 9, x = ((i * 137.3 + Math.sin(t * .7 + i) * 22 + t * 11) % VW + VW) % VW, y = (i * 61.7 + t * sp) % VH, s = 1.4 + (i % 3) * .8;
      g.globalAlpha = .45 + (i % 4) * .13; g.fillRect(x, y, s, s);
    }
    g.globalAlpha = 1;
  }
  function drawSky(g, t) {
    if (zdef.theme === 'arena') { g.fillStyle = '#191723'; g.fillRect(0, 0, VW, VH); return; }
    if (zdef.theme === 'skybridge') { SkybridgeArt.backdrop(g, VW, VH, t); return; }
    if (DungeonVisual.styles[zdef.theme]) { DungeonVisual.backdrop(g,zdef.theme,VW,VH,t); return; }
    if (zdef.theme === 'nornroot' || zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme)) { g.fillStyle = '#03040a'; g.fillRect(0, 0, VW, VH); return; }
    if (zdef.theme === 'moonwell') {
      const water=g.createLinearGradient(0,0,0,VH);water.addColorStop(0,'#0e2945');water.addColorStop(.56,'#194f68');water.addColorStop(1,'#235e70');g.fillStyle=water;g.fillRect(0,0,VW,VH);
      const [cx,cy]=camS();
      for(let layer=0;layer<2;layer++)for(let i=0;i<10;i++){
        const x=((i*317+layer*163-cx*(layer?.22:.09))%(VW+400)+VW+400)%(VW+400)-200;
        const y=((i*193+layer*307-cy*(layer?.16:.05))%(VH+300)+VH+300)%(VH+300)-150;
        g.fillStyle=layer?'rgba(173,244,225,.07)':'rgba(205,229,243,.05)';g.beginPath();g.ellipse(x,y,190-layer*45,37-layer*8,-.25,0,6.283);g.fill();
      }
      const glow=g.createRadialGradient(VW*.72,VH*.25,10,VW*.72,VH*.25,340);glow.addColorStop(0,'rgba(248,232,173,.36)');glow.addColorStop(1,'rgba(248,232,173,0)');g.fillStyle=glow;g.fillRect(0,0,VW,VH);
      g.fillStyle='#f8e8ad';g.shadowColor='#f8e8ad';g.shadowBlur=40;g.beginPath();g.arc(VW*.72,VH*.25,49,0,6.283);g.fill();g.shadowBlur=0;
      for(let i=0;i<12;i++) {
        const y=VH*.37+i*VH*.047,x=VW*.72+Math.sin(t*.7+i*1.8)*16;
        g.fillStyle=`rgba(242,244,209,${.16-i*.009})`;
        g.beginPath();g.ellipse(x,y,16+i*3,2.5+(i%3),0,0,6.283);g.fill();
      }
      for(let i=0;i<28;i++){const x=((i*257-cx*.13)%(VW+50)+VW+50)%(VW+50),y=((i*149-cy*.08)%(VH+50)+VH+50)%(VH+50);g.fillStyle=`rgba(231,251,237,${.25+.15*Math.sin(t*1.3+i)})`;g.beginPath();g.arc(x,y,1.5+i%3,0,6.283);g.fill();}
      return;
    }
    if (zdef.theme === 'ember') return drawSkyEmber(g, t);
    if (zdef.theme === 'frost') return drawSkyFrost(g, t);
    if (zdef.theme === 'fen') return drawSkyFen(g, t);
    if (zdef.theme === 'wyrd') return drawSkyWyrd(g, t);
    if (zdef.theme === 'sky') return drawSkySky(g, t);
    if (zdef.theme === 'astral') return drawSkyAstral(g, t);
    if (zdef.theme === 'prismwaste') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#322344');gr.addColorStop(.6,'#b17a84');gr.addColorStop(1,'#ffe2ad');g.fillStyle=gr;g.fillRect(0,0,VW,VH);return; }
    if (zdef.theme === 'orrery') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#171c38');gr.addColorStop(.6,'#51435b');gr.addColorStop(1,'#c79e72');g.fillStyle=gr;g.fillRect(0,0,VW,VH);return; }
    if (zdef.theme === 'moonspore') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#0e1c33');gr.addColorStop(.55,'#254c55');gr.addColorStop(1,'#608c75');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#d9f5bb';g.beginPath();g.arc(VW*.77,VH*.19,18,0,6.283);g.fill();return; }
    if (zdef.theme === 'worldtree') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#58b8a8');gr.addColorStop(.58,'#b2d9ad');gr.addColorStop(1,'#ebdfa4');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff2b2';g.beginPath();g.arc(VW*.77,VH*.16,44,0,6.283);g.fill();return;}
    if (zdef.theme === 'heartwood') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#283c38');gr.addColorStop(.6,'#6e6046');gr.addColorStop(1,'#c7a471');g.fillStyle=gr;g.fillRect(0,0,VW,VH);for(let i=0;i<7;i++){g.strokeStyle='rgba(245,218,147,.12)';g.lineWidth=22;g.beginPath();g.arc(VW*.5,VH*.9,130+i*93,Math.PI,Math.PI*2);g.stroke();}return;}
    if (zdef.theme === 'yearwheel') {
      const colors=[['#79c7b4','#b1e5c8','#f5d4de'],['#5ca9c4','#f2c67b','#ffe8ab'],['#687fa4','#db9169','#f1c078'],['#193d69','#8cb8d2','#edf8fa']][yearSeason(cam.x,cam.y)];
      const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,colors[0]);gr.addColorStop(.58,colors[1]);gr.addColorStop(1,colors[2]);g.fillStyle=gr;g.fillRect(0,0,VW,VH);
      g.fillStyle=colors[2];g.globalAlpha=.65;g.beginPath();g.arc(VW*.79,VH*.2,42,0,6.283);g.fill();g.globalAlpha=1;
      for(let i=0;i<8;i++){let x=(i*257+t*7)%(VW+260)-130,y=95+i%3*71;g.fillStyle='rgba(255,255,255,.22)';g.beginPath();g.ellipse(x,y,92,18,0,0,6.283);g.fill();}return;
    }
    if (zdef.theme === 'cairnspine') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#273448');gr.addColorStop(.56,'#847e77');gr.addColorStop(1,'#d3ba92');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#435262';for(let i=0;i<8;i++){let x=i*230-90,y=VH*.64;g.beginPath();g.moveTo(x-170,y+70);g.lineTo(x-40,y-80-i%3*28);g.lineTo(x+25,y-150-i%2*30);g.lineTo(x+160,y+70);g.fill();}return;}
    if (zdef.theme === 'frostwake') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#193c69');gr.addColorStop(.58,'#5989ae');gr.addColorStop(1,'#d5ecf2');g.fillStyle=gr;g.fillRect(0,0,VW,VH);for(let i=0;i<6;i++){const x=i*270+t*9-240;g.strokeStyle=i%2?'rgba(137,250,195,.22)':'rgba(172,204,255,.19)';g.lineWidth=45;g.beginPath();g.moveTo(x,-30);g.bezierCurveTo(x+130,VH*.12,x-80,VH*.33,x+120,VH*.55);g.stroke();}for(let i=0;i<36;i++){const x=(i*151+t*11)%VW,y=(i*103+t*9)%VH;g.fillStyle='rgba(255,255,255,.57)';g.beginPath();g.arc(x,y,1+i%2,0,6.283);g.fill();}return;}
    if (zdef.theme === 'lapiserg') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#5facc2');gr.addColorStop(.56,'#c8dfd4');gr.addColorStop(1,'#ffe5ae');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff0ac';g.shadowColor='#ffe8b0';g.shadowBlur=42;g.beginPath();g.arc(VW*.78,VH*.23,44,0,6.283);g.fill();g.shadowBlur=0;for(let i=0;i<5;i++){const x=((i*323+t*3)%(VW+420))-210,y=VH*.64+i%2*55;g.fillStyle='rgba(190,132,85,.23)';g.beginPath();g.ellipse(x,y,210,32,0,0,6.283);g.fill();}return;}
    if (zdef.theme === 'tanglecrown') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#69b6b1');gr.addColorStop(.58,'#bedac2');gr.addColorStop(1,'#f4e7b5');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff1ae';g.shadowColor='#f4efbf';g.shadowBlur=40;g.beginPath();g.arc(VW*.76,VH*.19,37,0,6.283);g.fill();g.shadowBlur=0;for(let i=0;i<7;i++){const x=((i*277+t*4)%(VW+310))-155,y=80+(i%3)*54;g.fillStyle='rgba(50,126,96,.29)';g.beginPath();g.ellipse(x,y,126,20,0,0,6.283);g.fill();}return;}
    if (zdef.theme === 'ribbonwild') {const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#79c9ed');gr.addColorStop(.54,'#c8b3ef');gr.addColorStop(1,'#ffe9bd');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff4bd';g.shadowColor='#ffeaa7';g.shadowBlur=45;g.beginPath();g.arc(VW*.76,VH*.19,43,0,6.283);g.fill();g.shadowBlur=0;for(let i=0;i<8;i++){const x=((i*283+t*(5+i%3))%(VW+290))-145,y=66+(i%4)*70;g.fillStyle=['#f680ad','#ffe08b','#70d4d9','#bea1ed'][i%4];g.beginPath();g.moveTo(x,y-12);g.lineTo(x+17,y);g.lineTo(x,y+12);g.lineTo(x-17,y);g.closePath();g.fill();g.strokeStyle='rgba(255,255,255,.6)';g.beginPath();g.moveTo(x,y+12);g.lineTo(x-8,y+35);g.stroke();}return;}
    if (zdef.theme === 'sunward') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#69b7e8');gr.addColorStop(.6,'#b6def1');gr.addColorStop(1,'#e7f0d1');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff1b0';g.shadowColor='#fff4c6';g.shadowBlur=48;g.beginPath();g.arc(VW*.78,VH*.18,43,0,6.283);g.fill();g.shadowBlur=0;for(let i=0;i<5;i++){const x=((i*321+t*7)%(VW+360))-180,y=65+(i%3)*77;g.fillStyle='rgba(255,255,255,.68)';g.beginPath();g.ellipse(x,y,90,19,0,0,6.283);g.ellipse(x-38,y+6,53,15,0,0,6.283);g.ellipse(x+48,y+5,59,17,0,0,6.283);g.fill();}return; }
    if (zdef.theme === 'stormglass') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#111b35');gr.addColorStop(.57,'#355a73');gr.addColorStop(1,'#8fb8b5');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.strokeStyle='rgba(217,250,247,.3)';g.lineWidth=4;g.beginPath();g.moveTo(1250,65);g.lineTo(1180,130);g.lineTo(1220,148);g.lineTo(1150,240);g.stroke();return; }
    if (zdef.theme === 'asterion') { const gr=g.createLinearGradient(0,0,0,VH);gr.addColorStop(0,'#111439');gr.addColorStop(.55,'#39547b');gr.addColorStop(1,'#a489ae');g.fillStyle=gr;g.fillRect(0,0,VW,VH);g.fillStyle='#fff2bd';g.shadowColor='#f4d9bb';g.shadowBlur=40;g.beginPath();g.arc(VW*.77,VH*.18,31,0,6.283);g.fill();g.shadowBlur=0;return; }
    if (zdef.theme === 'deep' || zdef.theme === 'nacre') return drawSkyDeep(g, t);
    if (zdef.theme === 'city') return drawSkyCity(g, t);
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#5aa0e8'); gr.addColorStop(.6, '#9fd0f5'); gr.addColorStop(1, '#d4ecff');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH);
    g.fillStyle = 'rgba(255,255,255,.55)';
    const [cx, cy] = camS();
    for (let i = 0; i < 14; i++) {                       // soft clouds drifting below and around the island
      const px = ((i * 397 + t * (6 + (i % 4) * 3) - cx * .25) % (VW + 500) + VW + 500) % (VW + 500) - 250, py = (i * 211 % VH) - cy * .12 * ((i % 3) + 1) * .3 + 120 * ((i % 3) - 1) + 480;
      const sc = .8 + (i % 4) * .35;
      g.beginPath(); g.ellipse(px, py, 130 * sc, 28 * sc, 0, 0, 6.283); g.ellipse(px - 70 * sc, py + 8 * sc, 80 * sc, 22 * sc, 0, 0, 6.283); g.ellipse(px + 76 * sc, py + 10 * sc, 90 * sc, 22 * sc, 0, 0, 6.283); g.fill();
    }
  }
  function drawSkyAstral(g, t) {
    const gr = g.createLinearGradient(0, 0, 0, VH); gr.addColorStop(0, '#070b2b'); gr.addColorStop(.55, '#17174d'); gr.addColorStop(1, '#32184e');
    g.fillStyle = gr; g.fillRect(0, 0, VW, VH); g.save(); g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 70; i++) { const x = (i * 173.7) % VW, y = (i * 97.1 + Math.sin(t * .2 + i) * 3) % (VH * .72), a = .35 + .35 * Math.sin(t * 1.4 + i); g.fillStyle = `rgba(210,220,255,${a})`; g.fillRect(x, y, 1.5 + (i % 3), 1.5 + (i % 2)); }
    g.restore();
  }
  function visibleChunks() {
    const cs = [s2w(0, 0), s2w(VW, 0), s2w(0, VH), s2w(VW, VH)], x0 = Math.min(...cs.map(c => c[0])) - 2, x1 = Math.max(...cs.map(c => c[0])) + 2, y0 = Math.min(...cs.map(c => c[1])) - 2, y1 = Math.max(...cs.map(c => c[1])) + 2;
    const out = [], n = MAP / CH;
    for (let cy = clamp(Math.floor(y0 / CH), 0, n - 1); cy <= clamp(Math.floor(y1 / CH), 0, n - 1); cy++) for (let cx = clamp(Math.floor(x0 / CH), 0, n - 1); cx <= clamp(Math.floor(x1 / CH), 0, n - 1); cx++) out.push([cx, cy]);
    return out.sort((a, b) => (a[0] + a[1]) - (b[0] + b[1]));
  }
  // Lava rivers are ground decals: a crust, a moving glow, then a hot core. They are also obstacles (kind 'lava').
  function drawLava(g, t) {
    const rows = [];
    for (const o of objects) if (o.kind === 'lava') { const [sx, sy] = w2s(o.x, o.y); if (sx > -140 && sx < VW + 140 && sy > -90 && sy < VH + 90) rows.push([o, sx, sy]); }
    const ex = o => o.r * TW * .7071, ey = o => o.r * TH * .7071;
    // Whole-river passes, widest first, so overlapping discs merge into one channel instead of separate beads.
    const pass = (grow, fill) => { for (const [o, sx, sy] of rows) { g.fillStyle = typeof fill === 'function' ? fill(o) : fill; g.beginPath(); g.ellipse(sx, sy + (grow < 0 ? 1 : 0), ex(o) * grow, ey(o) * grow, 0, 0, 6.283); g.fill(); } };
    const glow = o => .5 + .5 * Math.sin(t * 1.4 + o.x * .55 + o.y * .4);
    pass(1.3, '#2a1214');
    pass(1.08, '#7d1f12');
    pass(.9, o => `hsl(${10 + glow(o) * 10}, 100%, ${40 + glow(o) * 8}%)`);
    pass(.68, o => `hsl(${22 + glow(o) * 12}, 100%, ${50 + glow(o) * 8}%)`);
    pass(.42, o => `hsl(${38 + glow(o) * 10}, 100%, ${60 + glow(o) * 10}%)`);
    for (const [o, sx, sy] of rows) {                            // bubbles rising off the surface
      const b = (t * .5 + o.x * .37 + o.y * .21) % 1;
      if (b < .5) { g.fillStyle = `rgba(255,236,160,${.8 - b * 1.4})`; g.beginPath(); g.arc(sx + Math.sin(o.x * 5) * ex(o) * .4, sy - b * 28, 2.2 + b * 3, 0, 6.283); g.fill(); }
    }
  }
  // A boss sign (BOSSMECH-SIGN-ENGINE): a wooden board on a post with a gold "!" that glints, so it is noticed. The
  // words are not here; the server sends them when the sign is read. Pixel art through PixelFlow is still to come.
  function drawSign(g, sign, sx, sy, near) {
    const glint = reducedMotion() ? .5 : .5 + .5 * Math.sin(tAll * 3 + sign.x);
    g.save(); g.translate(sx, sy); g.lineJoin = 'round'; g.lineWidth = 2.5; g.strokeStyle = '#2b1b12';
    g.fillStyle = '#6b4526'; g.fillRect(-4, -34, 8, 34); g.strokeRect(-4, -34, 8, 34);
    g.fillStyle = '#a26d3a'; g.beginPath(); g.roundRect(-26, -66, 52, 34, 4); g.fill(); g.stroke();
    g.strokeStyle = '#7a4d27'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(-24, -54); g.lineTo(24, -54); g.moveTo(-24, -44); g.lineTo(24, -44); g.stroke();
    g.fillStyle = '#3a2412'; for (const x of [-21, 21]) for (const y of [-62, -37]) g.fillRect(x - 1.5, y - 1.5, 3, 3);
    g.font = 'bold 32px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineWidth = 4; g.strokeStyle = '#2b1b12'; g.fillStyle = '#ffd866';
    g.strokeText('!', 0, -49); g.fillText('!', 0, -49);
    if (glint > .75) { g.globalAlpha = (glint - .75) * 3; g.fillStyle = '#fff6cf'; g.beginPath(); g.arc(14, -60, 3.2, 0, 7); g.fill(); g.globalAlpha = 1; }
    if (near) { g.font = 'bold 13px sans-serif'; g.lineWidth = 3; g.strokeStyle = '#281d20'; g.fillStyle = '#fff1c8'; g.strokeText('F · Read', 0, -78); g.fillText('F · Read', 0, -78); }
    g.restore();
  }
  function drawChest(g, chest, sx, sy) {
    const left = Math.max(0, Math.ceil(chest.expiresAt - tAll));
    if (chestSrc) {
      drawChestFrame(g, 0, reducedMotion() ? 0 : Math.floor(tAll * 6 + chest.x * 7) % 6, sx, sy);
      g.save(); g.translate(sx, sy); g.font = 'bold 13px sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = '#281d20'; g.fillStyle = left <= 30 ? '#ff9a83' : '#fff1c8';
      const text = `${Math.floor(left / 60)}:${String(left % 60).padStart(2,'0')}`; g.strokeText(text,0,-40); g.fillText(text,0,-40); g.restore();
      return;
    }
    g.save(); g.translate(sx, sy); g.lineJoin = 'round'; g.lineWidth = 2.5; g.strokeStyle = '#2d1b17';
    g.fillStyle = '#8f5129'; g.beginPath(); g.moveTo(-24,-22); g.lineTo(0,-29); g.lineTo(24,-22); g.lineTo(24,1); g.lineTo(0,8); g.lineTo(-24,1); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#b97837'; g.beginPath(); g.moveTo(-24,-22); g.lineTo(0,-29); g.lineTo(24,-22); g.lineTo(0,-15); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#704025'; g.beginPath(); g.moveTo(0,-15); g.lineTo(24,-22); g.lineTo(24,1); g.lineTo(0,8); g.closePath(); g.fill(); g.stroke();
    g.strokeStyle = '#e9c56f'; g.lineWidth = 4; g.beginPath(); g.moveTo(-20,-18); g.lineTo(-20,0); g.moveTo(20,-18); g.lineTo(20,1); g.moveTo(0,-15); g.lineTo(0,7); g.stroke();
    g.fillStyle = '#ffe08b'; g.strokeStyle = '#6b401a'; g.lineWidth = 2; g.fillRect(-5,-13,10,10); g.strokeRect(-5,-13,10,10);
    g.font = 'bold 13px sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = '#281d20'; g.fillStyle = left <= 30 ? '#ff9a83' : '#fff1c8';
    const label = `${Math.floor(left / 60)}:${String(left % 60).padStart(2,'0')}`; g.strokeText(label,0,-40); g.fillText(label,0,-40); g.restore();
  }
  // A gate: two stone posts, a lintel and a swirling plane between them. The server owns the actual move.
  function drawPortal(g, p, sx, sy, t) {
    if (p.look === 'skybridge') return SkybridgeArt.portal(g,p,sx,sy,t);
    if (p.look === 'nornroot') return NornrootArt.portal(g,p,sx,sy,t);
    if (p.look === 'eye_below') return EyeBelowArt.portal(g,p,sx,sy,t);
    if (p.look === 'elder_hollow') return ElderHollowArt.portal(g,p,sx,sy,t);
    if (p.look === 'thousandfold') return PavilionArt.portal(g,p,sx,sy,t);
    if (p.look === 'rain_crown') return RainCrownArt.portal(g,p,sx,sy,t);
    if (p.look === 'seed_vault') return SeedVaultArt.portal(g,p,sx,sy,t);
    if (p.look === 'sunken_astrolabe') return SunkenArt.portal(g,p,sx,sy,t);
    if (p.look === 'thunderheart_gate') return ThunderArt.portal(g,p,sx,sy,t);
    if (SeasonDungeonArt.isTheme(p.look)) return SeasonDungeonArt.portal(g,p,sx,sy,t,p.look);
    if (p.look === 'cathedral') return CathedralArt.portal(g,p,sx,sy,t,ZONES[p.to] || zdef);
    if (p.look === 'stairs_down') { const d = ZONES[p.to]; return VaultArt.stairsDown(g, sx, sy, t, d?.min_level ? `Stairs to ${d.name} · Lv ${d.min_level}+` : 'Stairs down'); }
    if (p.look === 'stairs_up') return VaultArt.stairsUp(g, sx, sy, t);
    if (p.look === 'exit') return VaultArt.exitPortal(g, sx, sy, t, t - clearedAt);
    if (p.look === 'maelstrom') { const d = ZONES[p.to]; return DeepArt.maelstrom(g, sx, sy, t, d?.levels ? `${d.name} · Lv ${d.levels[0]}–${d.levels[1]}` : d?.name || 'The Maelstrom', zdef.theme === 'deep'); }
    const dest = ZONES[p.to] || ZONES[0], warm = dest.theme === 'ember', cold = dest.theme === 'frost', bog = dest.theme === 'fen', gold = dest.theme === 'city', leaf = dest.theme === 'wyrd', dsky = dest.theme === 'sky', astral = dest.theme === 'astral', prism = dest.theme === 'prismwaste', orrery = dest.theme === 'orrery', moonspore = dest.theme === 'moonspore';
    const hue = dest.theme === 'worldtree' ? 116 : dest.theme === 'heartwood' ? 43 : dest.theme === 'lapiserg' ? 39 : dest.theme === 'frostwake' ? 184 : dest.theme === 'cairnspine' ? 42 : dest.theme === 'tanglecrown' ? 143 : dest.theme === 'ribbonwild' ? 327 : dest.theme === 'sunward' ? 103 : dest.theme === 'stormglass' ? 183 : moonspore ? 145 : orrery ? 42 : prism ? 32 : astral ? 268 : dsky ? 215 : warm ? 18 : cold ? 195 : bog ? 88 : gold ? 44 : leaf ? 28 : 165, half = 1.5;
    const post = (u) => {                                    // an iso column centred u world units along x
      const px = sx + u * TW / 2, py = sy + u * TH / 2, w = 17, h = 112;
      g.fillStyle = 'rgba(0,0,0,.28)'; g.beginPath(); g.ellipse(px, py + 2, 30, 11, 0, 0, 6.283); g.fill();
      g.lineJoin = 'round'; g.lineWidth = 3; g.strokeStyle = OL;
      g.fillStyle = dsky ? '#9aa6d0' : warm ? '#4a3b44' : cold ? '#7f93ad' : bog ? '#6a7a5c' : leaf ? '#7a5a38' : gold ? '#c9bfa2' : '#8a8f9c'; g.beginPath(); g.moveTo(px - w, py - 4); g.lineTo(px, py + 8); g.lineTo(px, py + 8 - h); g.lineTo(px - w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = dsky ? '#6c789e' : warm ? '#30262f' : cold ? '#586c86' : bog ? '#46543e' : leaf ? '#5a4028' : gold ? '#a39a80' : '#6a6f7c'; g.beginPath(); g.moveTo(px + w, py - 4); g.lineTo(px, py + 8); g.lineTo(px, py + 8 - h); g.lineTo(px + w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = dsky ? '#d8e0f6' : warm ? '#6a5663' : cold ? '#b4cde3' : bog ? '#8a9c74' : leaf ? '#a8825a' : gold ? '#e6dcc0' : '#b9bdc8'; g.beginPath(); g.moveTo(px, py + 8 - h); g.lineTo(px + w, py - 4 - h); g.lineTo(px, py - 16 - h); g.lineTo(px - w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
      g.shadowColor = `hsl(${hue}, 100%, 60%)`; g.shadowBlur = 10; g.strokeStyle = `hsl(${hue + 12}, 100%, ${60 + 10 * Math.sin(t * 3 + u)}%)`; g.lineWidth = 2.4;
      g.beginPath(); g.moveTo(px - 8, py - 30); g.lineTo(px - 8, py - 62); g.lineTo(px - 3, py - 74); g.moveTo(px + 8, py - 30); g.lineTo(px + 8, py - 54); g.stroke(); g.shadowBlur = 0;
    };
    post(-half);
    // the plane: x runs along the gate, z is height; screen = (u*TW/2, u*TH/2 - z)
    g.save(); g.transform(TW / 2, TH / 2, 0, -1, sx, sy);
    const grd = g.createRadialGradient(0, 56, 4, 0, 56, 62);
    grd.addColorStop(0, `hsla(${hue + 30}, 100%, 88%, .95)`); grd.addColorStop(.5, `hsla(${hue}, 100%, 55%, .85)`); grd.addColorStop(1, `hsla(${hue - 10}, 90%, 30%, .55)`);
    g.fillStyle = grd; g.beginPath(); g.ellipse(0, 56, half - .2, 56, 0, 0, 6.283); g.fill();
    g.lineCap = 'round';
    for (let i = 0; i < 4; i++) {                              // swirling rings
      const a = t * (1.3 + i * .25) + i * 1.7;
      g.strokeStyle = `hsla(${hue + 20 + i * 10}, 100%, ${72 + i * 6}%, ${.65 - i * .1})`; g.lineWidth = .06;
      g.beginPath(); g.ellipse(0, 56, (half - .2) * (.25 + i * .22), 56 * (.25 + i * .22), 0, a, a + 3.6); g.stroke();
    }
    g.restore();
    post(half);
    g.save(); g.shadowColor = `hsl(${hue}, 100%, 60%)`; g.shadowBlur = 8; g.font = '15px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = OL; g.fillStyle = `hsl(${hue + 20}, 100%, 85%)`;
    const label = dest.levels ? `${dest.name} · Lv ${dest.levels[0]}–${dest.levels[1]}` : dest.name;
    g.strokeText(label, sx, sy - 142); g.fillText(label, sx, sy - 142); g.restore();
  }
  function shadow(g, x, y, rx, ry, a = .28) { const [sx, sy] = w2s(x, y), shift = window.DayNight?.shadowOffset || 0; g.fillStyle = `rgba(20,30,10,${a})`; g.beginPath(); g.ellipse(sx + shift, sy + shift * .25, rx, ry, 0, 0, 6.283); g.fill(); }
  const LOOT_PILLARS = {
    uncommon: { color: '#4ad66d', core: '#d5ffe0', tier: 1 },
    rare: { color: '#4aa3ff', core: '#dceeff', tier: 2 },
    epic: { color: '#b45cff', core: '#f1dcff', tier: 3 },
    legendary: { color: '#ff9a2e', core: '#fff0c8', tier: 4 },
  };
  function drawLootPillar(g, drop, item, sx, sy, t) {
    const rarity = drop.gear?.rarity || item?.rarity, style = LOOT_PILLARS[rarity];
    if (!drop.item || !style) return;
    const { color, core, tier } = style, height = 54 + tier * 18, width = 10 + tier * 3;
    const seed = Number(drop.id || 0) * 0.37, pulse = 1 + Math.sin(t * 3 + seed) * .08;
    g.save(); g.translate(sx + 12, sy); g.globalCompositeOperation = 'lighter';
    // A narrow, tapered shaft gives the motes a visible column without covering the drop or nearby actors.
    const beam = g.createLinearGradient(0, -height, 0, 5);
    beam.addColorStop(0, `${color}00`); beam.addColorStop(.35, `${color}17`);
    beam.addColorStop(1, `${color}55`);
    g.fillStyle = beam; g.beginPath(); g.moveTo(-width * .35, -height);
    g.lineTo(width * pulse, 2); g.quadraticCurveTo(0, 8, -width * pulse, 2);
    g.closePath(); g.fill();
    g.strokeStyle = color; g.lineWidth = 1.5; g.globalAlpha = .48;
    g.beginPath(); g.ellipse(0, 1, width * 1.3 * pulse, 5 * pulse, 0, 0, Math.PI * 2); g.stroke();
    g.globalAlpha = 1;
    const count = 7 + tier * 5;
    for (let i = 0; i < count; i++) {
      const phase = (t * (.38 + tier * .035) + i * .618034 + seed * .17) % 1;
      const angle = i * 2.39996 + t * (1 + tier * .12) + seed;
      const drift = (5 + tier * 2.5) * (.45 + phase * .7);
      const x = Math.sin(angle) * drift, y = -5 - phase * height;
      const fade = Math.sin(Math.PI * phase) * (.48 + tier * .09);
      g.globalAlpha = fade; g.fillStyle = i % 4 === 0 ? core : color;
      const size = (i % 5 === 0 ? 2.5 : 1.2) + tier * .22;
      if (i % 5 === 0) {
        g.beginPath(); g.moveTo(x, y - size * 1.7); g.lineTo(x + size * .65, y);
        g.lineTo(x, y + size * 1.7); g.lineTo(x - size * .65, y); g.closePath(); g.fill();
      } else { g.beginPath(); g.arc(x, y, size, 0, Math.PI * 2); g.fill(); }
    }
    g.restore();
  }
  function draw(t) {
    const g = ctx, k = dpr * zoom; g.setTransform(k, 0, 0, k, 0, 0);
    drawSky(g, t);
    // ground
    const [cx, cy] = camS();
    g.imageSmoothingEnabled = Math.abs(chunkScale - dpr * zoom) > .01;      // a 1:1 blit needs no filtering
    const sxo = Math.round(shakeX), syo = Math.round(shakeY);
    for (const [chx, chy] of visibleChunks()) {
      const G = chunkGeom(chx, chy), dx = G.ox - cx + VW / 2 + sxo, dy = G.oy - cy + VH / 2 + syo;
      if (dx > VW || dy > VH || dx + G.w < 0 || dy + G.h < 0) continue;      // the world box of the screen is much bigger than the screen itself
      g.drawImage(getChunk(chx, chy).c, dx, dy, G.w, G.h);
    }
    g.imageSmoothingEnabled = true;
    City.drawPlaza(g, w2s);
    if (zdef.theme === 'ember') drawLava(g, t);
    if (zone === 0 || zdef.theme === 'fen' || zdef.theme === 'wyrd' || zdef.theme === 'sunward') drawWater(g, t);
    if (zdef.theme === 'wyrd') drawBridges(g, t);
    if (zdef.theme === 'sky') drawWardRings(g, t);
    if (zdef.theme === 'deep') drawChimeRings(g, t);
    window.BossMech?.drawFloor(g, t, bossMechView());
    // ground decals: splats, target marker, slash, shadows
    for (const who of [hero, ...remotePlayers.values()]) drawBuffRings(g, who, t);
    for (const e of effects) if (e.kind === 'splat') { const [sx, sy] = w2s(e.x, e.y), a = clamp(1 - (e.t - 3) / 3, 0, 1) * .5; g.fillStyle = e.col; g.globalAlpha = a; g.beginPath(); g.ellipse(sx, sy, 26 * e.s, 12 * e.s, 0, 0, 6.283); g.fill(); g.globalAlpha = 1; }
    for (const e of effects) {
      if (e.kind === 'slam') drawGroundSlam(g, e);
      else if (groundSkillFx(e)) drawSkillFx(g, e, 'floor');
    }
    if (marker) { const [sx, sy] = w2s(marker.x, marker.y), p = (marker.t * 2) % 1; g.strokeStyle = `rgba(255,236,150,${1 - p * .6})`; g.lineWidth = 3; g.beginPath(); g.ellipse(sx, sy, 10 + p * 12, 5 + p * 6, 0, 0, 6.283); g.stroke(); }
    // build the depth-sorted list of everything standing on the ground
    const list = [], onScreen = (sx, sy, m) => sx > -m && sx < VW + m && sy > -m * 1.6 && sy < VH + m * 1.6;
    const set = spriteSet();
    for (const o of objects) {
      if (o.kind === 'lava' || o.kind === 'water' || o.kind === 'post' || o.kind === 'void') continue;
      const [sx, sy] = w2s(o.x, o.y);
      if (onScreen(sx, sy, Math.max(200, City.art[o.kind]?.box?.[3] || 0))) { list.push({ d: o.x + o.y, o, sx, sy }); if (o.kind === 'tree' || o.kind === 'pine') shadow(g, o.x, o.y, 46, 17, .22); else if (o.kind === 'bush') shadow(g, o.x, o.y, 30, 10, .22); else if (set[o.kind] || (zdef.theme === 'wyrd' && ['rock', 'spire', 'crag', 'elderash', 'ribcage', 'gallows'].includes(o.kind))) shadow(g, o.x, o.y, 26, 9, .25); }
    }
    for (const portal of zdef.portals) { if (portal.after_clear && !instanceCleared) continue; const [sx, sy] = w2s(portal.x, portal.y); if (onScreen(sx, sy, 220)) list.push({ d: portal.x + portal.y + (portal.look ? .3 : 0), portal, sx, sy }); }
    const escorted = id => { for (const r of remotePlayers.values()) if (r.escort && r.escort.npc === id && r.escort.owner === Online.id) return true; return false; };   // a stranded person walks with their rescuer
    for (const n of City.npcs) { if (n.escort && escorted(n.id)) continue; const [sx,sy]=w2s(n.x,n.y); if(onScreen(sx,sy,150)) list.push({d:n.x+n.y,npc:n,sx,sy}); }
    for (const s of slimes) if (!s.dead || (enemySource(s) && s.dieT < DIE_SHOW)) { const [sx, sy] = w2s(s.x, s.y); if (onScreen(sx, sy, 100)) { shadow(g, s.x, s.y, 28 * s.d.scale * (1 - s.hop * .12), 11 * s.d.scale, s.dead ? .3 * clamp(1 - (s.dieT - .5) / .6, 0, 1) : .3); list.push({ d: s.x + s.y, s, sx, sy }); } }
    for (const chest of chests) if (chest.expiresAt > tAll) { const [sx, sy] = w2s(chest.x, chest.y); if (onScreen(sx, sy, 70)) { shadow(g,chest.x,chest.y,27,9,.35); list.push({d:chest.x+chest.y,chest,sx,sy}); } }
    for (const sign of signs) { const [sx, sy] = w2s(sign.x, sign.y); if (onScreen(sx, sy, 90)) { shadow(g, sign.x, sign.y, 22, 8, .3); list.push({ d: sign.x + sign.y, sign, sx, sy }); } }
    for (const d of drops) { const [sx, sy] = w2s(d.x, d.y); if (onScreen(sx, sy, 165)) list.push({ d: d.x + d.y, drop: d, sx, sy }); }
    { const [sx, sy] = w2s(hero.x, hero.y); shadow(g, hero.x, hero.y, 30, 12, .32); list.push({ d: hero.sparkTravel ? Infinity : hero.x + hero.y + .001, hero, sx, sy }); }
    for (const remote of remotePlayers.values()) {
      const [sx, sy] = w2s(remote.x, remote.y);
      if (onScreen(sx, sy, 160)) { shadow(g, remote.x, remote.y, 30, 12, .28); list.push({ d: remote.sparkTravel ? Infinity : remote.x + remote.y + .001, remote, sx, sy }); }
    }
    list.sort((a, b) => a.d - b.d);
    const [hsx, hsy] = w2s(hero.x, hero.y), hd = hero.x + hero.y;
    for (const it of list) {
      if (it.o) {
        const o = it.o;
        if (!set[o.kind]) {
          const cover=['house','chapel','gate','tent','tower','rampart','meetingstone','grandfountain','vaultwall','pillar','cathedralwall','cathedralcolumn','tree','pine','elderash','ribcage','gallows','skypine','prism','column','spirelight','pylon','hallgate','wardstone','windcairn','nacrehouse','nacrecathedral','nacrepalace','nacrearchive','nacreinn','nacrefountain','reefwall','tidebell','sunkencolumn','shiprib','coral','vent','clockwall','blackspire','hourpillar','stillpoint','epoch_crown'].includes(o.kind) && it.d>hd && Math.abs(it.sx-hsx)<150 && hsy>it.sy-300 && hsy<it.sy+65;
          City.drawObject(g,o,it.sx,it.sy,cover ? .5 : 1);
          City.animateObject(g,o,it.sx,it.sy,t);
          if(o.kind==='fountain') { for(let i=0;i<7;i++){const phase=(t*.7+i*.17)%1;g.globalAlpha=Math.sin(phase*Math.PI)*.7;g.fillStyle='#e0ffff';g.beginPath();g.ellipse(it.sx+Math.sin(i*4)*45,it.sy-9-phase*24,2,3,0,0,Math.PI*2);g.fill();}g.globalAlpha=1;}
          continue;
        }
        const spr = set[o.kind][o.v % 4];
        // trees in front of the hero fade so he never disappears behind a canopy
        const cover = o.kind === 'tree' && it.d > hd && Math.abs(it.sx - hsx) < 80 && it.sy - 190 < hsy && it.sy > hsy - 20;
        if (cover) g.globalAlpha = .45;
        g.drawImage(spr.c, it.sx - spr.ax, it.sy - spr.ay + (o.kind === 'rock' ? 4 : 0), spr.w, spr.h); g.globalAlpha = 1;
      } else if (it.portal) { drawPortal(g, it.portal, it.sx, it.sy, t);
      } else if (it.npc) { City.drawNpc(g,it.npc,it.sx,it.sy,t,Math.hypot(hero.x-it.npc.x,hero.y-it.npc.y)<2.8);
      } else if (it.chest) { drawChest(g,it.chest,it.sx,it.sy);
      } else if (it.sign) { drawSign(g,it.sign,it.sx,it.sy,Math.hypot(hero.x-it.sign.x,hero.y-it.sign.y)<2.8);
      } else if (it.s) {
        const s = it.s, src = enemySource(s); g.save(); g.translate(it.sx, it.sy); if (src) drawSlimeSprite(g, s, t); else drawSlime(g, s, t);
        const barY = src ? -(s.d.top ?? (s.kind === 'big' ? 36 : s.kind === 'beetle' ? 40 : 28)) * SLIME_K * s.d.scale : -62 * s.d.scale - s.hop * 16;
        if (!s.dead && s.hp < s.maxHp) { const w = 52 * s.d.scale ** .7; g.fillStyle = 'rgba(20,10,30,.8)'; g.fillRect(-w / 2 - 2, barY - 2, w + 4, 8); g.fillStyle = '#ff5a6e'; g.fillRect(-w / 2, barY, w * s.hp / s.maxHp, 4); }
        if (!s.dead && (hero.target === s || Math.hypot(hero.x - s.x, hero.y - s.y) < 7)) {
          const label = `Lv ${s.level ?? '?'} ${s.d.name || s.kind}${s.d.elite ? ' · Elite' : ''}`;
          g.font = '16px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = OL; g.fillStyle = levelColor(s.level);
          g.strokeText(label, 0, barY - 8); g.fillText(label, 0, barY - 8);
        }
        if (!s.dead && hero.target === s) { g.strokeStyle = '#ffe066'; g.lineWidth = 2.5; g.beginPath(); g.ellipse(0, 2, 32 * s.d.scale, 13 * s.d.scale, 0, 0, 6.283); g.stroke(); }
        g.restore();
      } else if (it.drop) {
        const d = it.drop, item = WORLD_ITEMS.find(i => i.id === d.item);
        drawLootPillar(g, d, item, it.sx, it.sy, t);
        g.save(); g.translate(it.sx + (d.item ? 12 : -8), it.sy - d.z); g.fillStyle = item?.kind==='bag'?bagColor(item):d.col; g.strokeStyle = OL; g.lineWidth = 2.4;
        if(item?.kind==='bag') {
          g.shadowColor=bagColor(item);g.shadowBlur=13;
          g.fillRect(-10,-7,20,16);g.strokeRect(-10,-7,20,16);
          g.beginPath();g.arc(0,-7,5,Math.PI,0);g.stroke();g.shadowBlur=0;
          g.fillStyle='#fff7dd';g.font='bold 10px sans-serif';g.textAlign='center';g.fillText(String(item.bagSlots),0,5);
          g.restore();continue;
        }
        if (item && (d.gear?.rarity || item.rarity) !== 'common') { g.shadowColor = d.col; g.shadowBlur = 12; }
        g.beginPath();
        if (d.item) { g.moveTo(0,-12); g.lineTo(10,-2); g.lineTo(0,8); g.lineTo(-10,-2); g.closePath(); }
        else { g.moveTo(0, -9); g.bezierCurveTo(8, -1, 8, 6, 0, 6); g.bezierCurveTo(-8, 6, -8, -1, 0, -9); }
        g.fill(); g.stroke(); g.shadowBlur = 0;
        if (item?.class) { g.fillStyle = '#112b49'; g.font = 'bold 12px sans-serif'; g.textAlign = 'center'; g.fillText(item.kind === 'weapon' ? '⚔' : '◆', 0, 3); }
        else { g.fillStyle = 'rgba(255,255,255,.7)'; g.beginPath(); g.arc(-2.4, -1, 1.8, 0, 6.283); g.fill(); }
        if (d.gear && hero && Math.hypot(hero.x-d.x, hero.y-d.y) < 8) {
          const gear = d.gear, a = Object.fromEntries(Object.keys(gear.bonusStats || {}).map(k => [k, (gear.bonusStats?.[k] || 0) + (gear.rolledStats?.[k] || 0)]));
          const label = `${gear.rarity === 'epic' ? 'Epic · ' : ''}${item?.name || 'Gear'} · ${gear.attack} ATK · ${gear.defense} DEF · ${a.stamina || 0} STA · ${a.accuracy || 0} ACC · ${a.dexterity || 0} DEX`;
          g.font = '12px sans-serif'; g.textAlign = 'center'; g.lineWidth = 3;
          g.strokeStyle = '#24120b'; g.fillStyle = gear.rarity === 'epic' ? '#b45cff' : '#ffb65b'; g.strokeText(label, 0, -24); g.fillText(label, 0, -24);
        }
        g.restore();
      } else if (it.remote) {
        const remote = it.remote; g.save(); g.translate(it.sx, it.sy);
        if (!remote.sparkTravel && !remote.dead) window.Rebirth?.drawAura(g, remote.reborn?.tier, remote.mounted ? 1.25 : 1);
        if (remote.sparkTravel) Spark.draw(g,remote,t);
        else if (remote.sprite) { const seated = seatedInArt(remote, remote.sprite); if(!seated)drawMount(g,remote); if(remote.mounted&&!seated)g.translate(0,-23); remote.sprite.draw(g, remote, t); if(remote.mounted&&!seated)g.translate(0,23); }
        else { g.fillStyle = '#cfb5fa'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
        drawMageWardShell(g, remote, t); drawPriestBuffShell(g, remote, t); drawHunterBuffShell(g, remote, t);
        g.font = '18px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#151c35'; g.fillStyle = remote.pvpFlag ? '#ff9b9b' : remote.escort ? '#ffd24a' : window.Social?.isPartyMember(remote.id) ? '#9dffb2' : window.Rebirth?.color(remote.reborn?.tier || 0) || '#fff4ca';
        const nameText = remote.escort ? remote.look.name + ' · Escort' : remote.look.name + (remote.pvpFlag ? ' · PvP' : '');
        g.strokeText(nameText, 0, -128); g.fillText(nameText, 0, -128);
        if (remote.reborn?.tier) { const label = window.Rebirth.title(remote.reborn.tier); g.font = '13px "Jua", sans-serif'; g.fillStyle = window.Rebirth.color(remote.reborn.tier); g.lineWidth = 3; g.strokeText(label, 0, -144); g.fillText(label, 0, -144); }
        if (hero.pvpTargetId === remote.id) { g.strokeStyle = '#ffe066'; g.lineWidth = 2.5; g.beginPath(); g.ellipse(0, 2, 30, 12, 0, 0, 6.283); g.stroke(); }
        g.fillStyle = '#16263dcc'; g.fillRect(-25, -116, 50, 5); g.fillStyle = remote.escort ? '#ffcf5a' : '#8ee7a5'; g.fillRect(-25, -116, 50 * remote.hp / remote.maxHp, 5);
        g.restore();
      } else if (it.hero) { g.save(); g.translate(it.sx, it.sy); if (hero.gm && hero.hidden) g.globalAlpha = .35; if (hero.sparkTravel) Spark.draw(g,hero,t); else { if (!hero.dead) window.Rebirth?.drawAura(g, hero.reborn?.tier, hero.mounted ? 1.25 : 1); const seated = isModular() && seatedInArt(hero, mageSpr); if(!seated)drawMount(g,hero); if(hero.mounted&&!seated)g.translate(0,-23); if (isModular()) {
        if (mageSpr) mageSpr.draw(g, hero, t);
        else { g.fillStyle = '#8acfff'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
      } else { if (!warSpr && hero.hurtT > 0 && Math.floor(hero.hurtT * 40) % 2) g.globalAlpha = .6; if (warSpr) drawWarriorSprite(g, hero, t); else if (heroSpr) drawHeroSprite(g, hero, t); else { g.scale(1.3, 1.3); drawHero(g, hero, t); } } } drawMageWardShell(g, hero, t); drawPriestBuffShell(g, hero, t); drawHunterBuffShell(g, hero, t); if (hero.gm && hero.hidden) { g.globalAlpha = .8; g.strokeStyle = '#ffd24a'; g.lineWidth = 2; g.beginPath(); g.ellipse(0, 1, 26, 11, 0, 0, Math.PI * 2); g.stroke(); } g.restore(); }
    }
    // speech bubbles go over everything, so a tree or a roof never hides what somebody said
    bubblesLast = bubblesDrawn; bubblesDrawn = 0;
    if (bubbles.size) {
      const now = performance.now();
      for (const [id, b] of bubbles) {
        if (b.until <= now) { bubbles.delete(id); continue; }
        const who = id === Online.id ? hero : remotePlayers.get(id); if (!who || who.dead) continue;
        const [bx, by] = w2s(who.x, who.y); if (bx > -200 && bx < VW + 200 && by > -50 && by < VH + 250) drawBubble(g, b, bx, by - (who === hero ? 138 : 152), (b.until - now) / 1000);
      }
    }
    // Light is applied after the world and before attacks, loot labels and other combat feedback.
    window.DayNight?.draw(g, VW, VH, nightLights, w2s);
    window.Weather?.draw(g, VW, VH, t);
    // slash arc on the ground plane (over everything: it is the axe's motion)
    for (const e of effects) if ((e.kind === 'slash' || e.kind === 'dualSlash') && (heroSpr || e.t < 0)) continue; else if (e.kind === 'slash') {
      const p = e.t / .32, a0 = e.a - 1.25, a1 = a0 + 2.5 * Math.min(1, p * 1.8);
      g.save(); g.lineCap = 'round';
      for (const [w, col, al] of [[16, '#59d9ff', .3], [8, '#bff6ff', .7], [3, '#ffffff', 1]]) {
        g.globalAlpha = al * (1 - p); g.strokeStyle = col; g.lineWidth = w * (1 - p * .5); g.beginPath();
        for (let i = 0; i <= 14; i++) { const a = lerp(a0, a1, i / 14), [sx, sy] = w2s(e.x + Math.cos(a) * 1.5, e.y + Math.sin(a) * 1.5, 26); i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); }
        g.stroke();
      }
      g.restore();
    } else if (e.kind === 'dualSlash') {
      const fade = Math.max(0, 1 - e.t / .3);
      for (const side of [-1, 1]) {
        const [ax, ay] = w2s(e.x + Math.cos(e.a - side * .5) * .5, e.y + Math.sin(e.a - side * .5) * .5, side < 0 ? 45 : 62);
        const [bx, by] = w2s(e.x + Math.cos(e.a + side * .6) * 1.4, e.y + Math.sin(e.a + side * .6) * 1.4, side < 0 ? 62 : 45);
        g.save(); g.globalAlpha = fade; g.strokeStyle = '#cfb5fa'; g.lineWidth = 6 * fade; g.lineCap = 'round'; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
        g.strokeStyle = '#fff1ff'; g.lineWidth = 2; g.stroke(); g.restore();
      }
    } else if (e.kind === 'shadow' && mageSpr && isAssassin()) {
      const [sx, sy] = w2s(e.x, e.y), [ax, ay] = mageSpr.meta.anchor;
      g.save(); g.globalAlpha = Math.max(0, .35 * (1 - e.t / .32)); g.imageSmoothingEnabled = false;
      g.drawImage(mageSpr.frame('walk', e.dir, e.frame), sx - ax * 1.3, sy - ay * 1.3, 160 * 1.3, 160 * 1.3); g.restore();
    } else if (e.kind === 'chestOpen') {
      if (!chestSrc) continue;
      const [sx, sy] = w2s(e.x, e.y), fade = Math.min(1, (e.life - e.t) / .4);   // the lid swings back, the pile shimmers, then it is gone
      g.save(); g.globalAlpha = fade; g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(sx, sy, 27, 9, 0, 0, 6.283); g.fill();
      if (e.t < .5) drawChestFrame(g, 1, Math.min(5, Math.floor(e.t * 12)), sx, sy); else drawChestFrame(g, 2, Math.floor((e.t - .5) * 4) % 2, sx, sy);
      g.restore();
    } else if (e.kind === 'ring') {
      if (e.t < 0) continue;
      const p = e.t / (e.life ?? .9), [sx, sy] = w2s(e.x, e.y), m = e.grow || 1;
      if (e.col) { g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = 1 - p; g.strokeStyle = e.col; } else g.strokeStyle = `rgba(255,224,102,${1 - p})`;
      g.lineWidth = 6 * (1 - p) + 1; g.beginPath(); g.ellipse(sx, sy, 30 + p * 120 * m, 14 + p * 56 * m, 0, 0, 6.283); g.stroke(); if (e.col) g.restore();
    }
    for (const e of effects) if (e.kind === 'luPillar' || e.kind === 'luRays' || e.kind === 'rbPillar') drawLevelFx(g, e); else if (e.kind.startsWith('sk')) drawSkillFx(g, e);
    for (const b of bolts) {
      const [sx, sy] = w2s(b.x, b.y, 42), [tx, ty] = w2s(b.x - b.fx * .45, b.y - b.fy * .45, 42), [ux, uy] = projDir(b.fx, b.fy);
      const w = b.size || 9;
      if (['powershot', 'multishot', 'piercingarrow', 'explosivearrow'].includes(b.skill)) {
        const power = b.skill === 'powershot', pierce = b.skill === 'piercingarrow', explosive = b.skill === 'explosivearrow';
        const color = explosive ? '#ff8a3a' : pierce ? '#8cf0bb' : power ? '#ffd27a' : '#e8c27a';
        g.save(); g.lineCap = 'round'; g.globalCompositeOperation = 'lighter';
        g.strokeStyle = color; g.globalAlpha = explosive ? .75 : .5; g.lineWidth = power ? 15 : pierce ? 12 : 9;
        g.beginPath(); g.moveTo(tx - ux * (power ? 62 : 34), ty - uy * (power ? 62 : 34)); g.lineTo(sx, sy); g.stroke();
        g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
        drawHunterArrow(g, sx, sy, ux, uy, power ? 1.35 : explosive ? 1.15 : pierce ? 1.05 : .85, color);
        if (explosive) { g.fillStyle = '#fff2bd'; g.beginPath(); g.arc(sx - ux * 27, sy - uy * 27, 5, 0, 6.283); g.fill(); }
        g.restore(); continue;
      }
      if (b.skill === 'throwingknives' || b.skill === 'knifering') {
        g.save(); g.lineCap = 'round'; g.globalCompositeOperation = 'lighter';
        g.strokeStyle = b.skill === 'knifering' ? '#d89cff' : '#c9d5e5'; g.globalAlpha = .65; g.lineWidth = 8;
        g.beginPath(); g.moveTo(tx - ux * 30, ty - uy * 30); g.lineTo(sx, sy); g.stroke();
        g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
        drawAssassinKnife(g, sx, sy, ux, uy, .85, b.skill === 'knifering' ? '#f3d8ff' : '#dfe6ee');
        g.restore(); continue;
      }
      if (b.skill === 'twinbolt' || b.skill === 'barrage' || b.skill === 'fireball') {
        g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
        if (b.skill === 'fireball') {
          const r = 17 + Math.sin(t * 24 + b.id) * 2, fire = g.createRadialGradient(sx, sy, 2, sx, sy, r * 2.8);
          fire.addColorStop(0, '#ffffff'); fire.addColorStop(.25, '#fff3c0'); fire.addColorStop(.55, '#ff6a1a'); fire.addColorStop(1, '#ff6a1a00');
          g.globalCompositeOperation = 'lighter'; g.fillStyle = fire; g.beginPath(); g.arc(sx, sy, r * 2.8, 0, 6.283); g.fill();
          g.strokeStyle = '#ff8a3a'; g.globalAlpha = .7; g.lineWidth = 25; g.beginPath(); g.moveTo(tx - ux * 18, ty - uy * 18); g.lineTo(sx, sy); g.stroke();
          g.fillStyle = '#fff8d9'; g.globalAlpha = 1; g.beginPath(); g.arc(sx, sy, r * .65, 0, 6.283); g.fill();
        } else {
          const cyan = b.skill === 'barrage', col = cyan ? '#46c8ff' : '#a57bff';
          g.strokeStyle = col; g.globalCompositeOperation = 'lighter'; g.globalAlpha = .5; g.lineWidth = cyan ? 16 : 21;
          g.beginPath(); g.moveTo(tx, ty); g.lineTo(sx, sy); g.stroke();
          g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1; g.fillStyle = '#ffffff'; g.strokeStyle = col; g.lineWidth = 3;
          g.beginPath(); g.moveTo(sx + ux * 19, sy + uy * 19); g.lineTo(sx - uy * 7, sy + ux * 7);
          g.lineTo(sx - ux * 18, sy - uy * 18); g.lineTo(sx + uy * 7, sy - ux * 7); g.closePath(); g.fill(); g.stroke();
        }
        g.restore(); continue;
      }
      g.save(); g.strokeStyle = b.col; g.lineWidth = w; g.lineCap = 'round'; g.globalAlpha = .65;
      g.beginPath(); g.moveTo(tx, ty); g.lineTo(sx, sy); g.stroke();
      if (w >= 14) { g.globalAlpha = .35; g.fillStyle = b.col; g.beginPath(); g.arc(sx, sy, w * 1.2, 0, Math.PI * 2); g.fill(); }
      g.globalAlpha = 1; g.fillStyle = '#f3fcff'; g.beginPath(); g.arc(sx, sy, Math.max(3, w * .55), 0, Math.PI * 2); g.fill(); g.restore();
    }
    for (const b of ebolts) {                                          // missiles of ranged enemies: an arrow is a thin shaft, a spell a glowing orb with a tail
      const [sx, sy] = w2s(b.x, b.y, 38), [tx, ty] = w2s(b.x - b.fx * (b.kind === 'archer' ? .9 : .55), b.y - b.fy * (b.kind === 'archer' ? .9 : .55), 38);
      g.save(); g.lineCap = 'round';
      if (b.kind === 'archer') { g.strokeStyle = '#2a2018'; g.lineWidth = 5; g.beginPath(); g.moveTo(tx, ty); g.lineTo(sx, sy); g.stroke(); g.strokeStyle = b.color; g.lineWidth = 2.6; g.stroke(); g.fillStyle = '#e8e8f0'; g.beginPath(); g.arc(sx, sy, 3.2, 0, 6.283); g.fill(); }
      else {
        const R = 8 + b.size * 6;
        g.globalCompositeOperation = 'lighter'; g.strokeStyle = b.color; g.globalAlpha = .55; g.lineWidth = R * 1.1; g.beginPath(); g.moveTo(tx, ty); g.lineTo(sx, sy); g.stroke();
        const gr = g.createRadialGradient(sx, sy, 1, sx, sy, R * 2); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.3, b.color); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.globalAlpha = .95; g.fillStyle = gr; g.beginPath(); g.arc(sx, sy, R * 2, 0, 6.283); g.fill();
      }
      g.restore();
    }
    for (const p of parts) { const [sx, sy] = w2s(p.x, p.y, p.z); g.globalAlpha = 1 - p.t / p.life; g.fillStyle = p.col; g.beginPath(); g.arc(sx, sy, p.size, 0, 6.283); g.fill(); } g.globalAlpha = 1;
    { const reduced = reducedMotion();                                   // numbers: pop, eased climb with a sideways arc, hold, late fade (DamageNumbers.pose)
      g.textAlign = 'center'; g.textBaseline = 'alphabetic'; g.lineJoin = 'round';
      for (const f of floaters) {
        const p = DamageNumbers.pose(f, reduced); if (!p.visible) continue;
        const [sx, sy] = w2s(f.x, f.y, f.head + p.dz), size = Math.round(DamageNumbers.KINDS[f.kind].size * p.scale);
        g.globalAlpha = p.alpha; g.font = `${size}px "Lilita One", "Jua", Impact, sans-serif`; g.lineWidth = Math.max(3, size / 5); g.strokeStyle = 'rgba(20,10,30,.9)';
        const ty = Math.max(size + 4, sy);                              // a giant's head can be above the screen: keep its number readable
        g.strokeText(f.text, sx + p.dx, ty); g.fillStyle = f.color; g.fillText(f.text, sx + p.dx, ty);
      } g.globalAlpha = 1; }
    if (zdef.theme === 'frost') drawSnowfall(g, t);
    if (zdef.theme === 'fen') drawFireflies(g, t);
    if (zdef.theme === 'wyrd') drawWyrdWeather(g, t);
    if (zdef.theme === 'sky') drawSkyWeather(g, t);
    if (zdef.theme === 'deep' || zdef.theme === 'nacre') drawDeepWeather(g, t);
    if (zdef.theme === 'city') drawBlossom(g, t);
    if (zdef.theme === 'skybridge') SkybridgeArt.weather(g,t,VW,VH);
    if (zdef.theme === 'eye_below') EyeBelowArt.weather(g,t,VW,VH);
    if (zdef.theme === 'elder_hollow') ElderHollowArt.weather(g,t,VW,VH);
    if (zdef.theme === 'thousandfold') PavilionArt.weather(g,t,VW,VH);
    if (zdef.theme === 'rain_crown') RainCrownArt.weather(g,t,VW,VH);
    if (zdef.theme === 'seed_vault') SeedVaultArt.weather(g,t,VW,VH);
    if (zdef.theme === 'sunken_astrolabe') SunkenArt.weather(g,t,VW,VH);
    if (zdef.theme === 'thunderheart_gate') ThunderArt.weather(g,t,VW,VH);
    if (SeasonDungeonArt.isTheme(zdef.theme)) SeasonDungeonArt.weather(g,zdef.theme,t,VW,VH);
    if (CathedralArt.isTheme(zdef.theme)) CathedralArt.weather(g,zdef.theme,t,VW,VH);
    if (zdef.theme === 'skybridge' || zdef.theme === 'nornroot' || zdef.theme === 'vault' || zdef.theme === 'eye_below' || zdef.theme === 'elder_hollow' || zdef.theme === 'thousandfold' || zdef.theme === 'rain_crown' || zdef.theme === 'seed_vault' || zdef.theme === 'sunken_astrolabe' || zdef.theme === 'thunderheart_gate' || SeasonDungeonArt.isTheme(zdef.theme) || CathedralArt.isTheme(zdef.theme)) { drawDarkness(g, t); drawBossBar(g); }
    if (zdef.theme === 'moonwell') drawBossBar(g);
    window.BossMech?.drawHud(g, VW, VH, t, bossMechView());
    drawMini();
  }
  // What the boss-mechanics drawing needs from the field: the projection, the room a point is in, and where a character or boss stands.
  const bossMechView = () => ({
    w2s,
    roomAt: (x, y) => (zdef.rooms || []).find(([x0, y0, x1, y1]) => x >= x0 && x < x1 && y >= y0 && y < y1) || null,
    pos: id => id === Online.id ? hero : remotePlayers.get(id) || null,
    boss: id => slimes.find(s => s.id === id) || null,
  });
  // ---------- the Undervault's darkness and its boss bar ----------
  // The vault has no sky: a dark veil covers the screen and every light cuts a pool out of it (the hero, torches, braziers, the
  // stairs and the exit, missiles in flight).
  let darkCv = null, darkG = null;
  function drawDarkness(g, t) {
    if (!darkCv) { darkCv = document.createElement('canvas'); darkCv.width = VW; darkCv.height = VH; darkG = darkCv.getContext('2d'); }
    const d = darkG; d.globalCompositeOperation = 'source-over'; d.clearRect(0, 0, VW, VH); d.fillStyle = zdef.theme === 'skybridge' ? 'rgba(9,16,34,.36)' : zdef.theme === 'nornroot' ? 'rgba(9,22,18,.26)' : zdef.theme === 'eye_below' ? 'rgba(2,15,28,.65)' : zdef.theme === 'elder_hollow' ? 'rgba(12,24,12,.30)' : zdef.theme === 'thousandfold' ? 'rgba(24,11,31,.32)' : zdef.theme === 'rain_crown' ? 'rgba(4,28,26,.49)' : zdef.theme === 'seed_vault' ? 'rgba(19,28,8,.34)' : zdef.theme === 'sunken_astrolabe' ? 'rgba(8,24,32,.49)' : zdef.theme === 'thunderheart_gate' ? 'rgba(7,19,38,.50)' : zdef.theme === 'blooming_labyrinth' ? 'rgba(14,27,17,.29)' : zdef.theme === 'solar_crucible' ? 'rgba(39,17,9,.43)' : zdef.theme === 'cathedral_left' ? 'rgba(4,24,29,.49)' : zdef.theme === 'cathedral_right' ? 'rgba(24,9,24,.51)' : zdef.theme === 'cathedral_main' ? 'rgba(8,10,30,.54)' : CathedralArt.isTheme(zdef.theme) ? 'rgba(3,9,24,.56)' : zdef.theme === 'vault' ? 'rgba(7,12,20,.63)' : 'rgba(3,4,10,.84)'; d.fillRect(0, 0, VW, VH);
    d.globalCompositeOperation = 'destination-out';
    const pool = (x, y, r, a) => {
      if (x < -r || x > VW + r || y < -r || y > VH + r) return;
      const gr = d.createRadialGradient(x, y, r * .06, x, y, r); gr.addColorStop(0, `rgba(0,0,0,${a})`); gr.addColorStop(.5, `rgba(0,0,0,${a * .62})`); gr.addColorStop(1, 'rgba(0,0,0,0)');
      d.fillStyle = gr; d.beginPath(); d.ellipse(x, y, r, r * .6, 0, 0, 6.283); d.fill();
    };
    const [hx, hy] = w2s(hero.x, hero.y); pool(hx, hy - 36, 540, .97);
    for (const o of objects) {
      if (o.kind !== 'brazier' && o.kind !== 'torch' && o.kind !== 'cathedrallamp' && o.kind !== 'eye_lamp' && o.kind !== 'eye_lens' && o.kind !== 'elder_lantern' && o.kind !== 'elder_crown' && o.kind !== 'elder_seed' && o.kind !== 'pavilion_lantern' && o.kind !== 'rain_brazier' && o.kind !== 'seed_lamp' && o.kind !== 'astro_lamp' && o.kind !== 'thunder_pylon' && o.kind !== 'amber_lantern' && o.kind !== 'solstice_lantern' && o.kind !== 'bloom_lamp' && o.kind !== 'bloom_altar' && o.kind !== 'solar_brazier' && o.kind !== 'solar_forge' && o.kind !== 'span_brazier' && o.kind !== 'span_prism' && o.kind !== 'span_arch') continue;
      const [sx, sy] = w2s(o.x, o.y), fl = .9 + .1 * Math.sin(t * 7 + o.x * 3);
      pool(sx, sy - 56, (o.kind === 'brazier' ? 320 : 230) * fl, .9);
    }
    for (const p of zdef.portals) { if (p.after_clear && !instanceCleared) continue; const [sx, sy] = w2s(p.x, p.y); pool(sx, sy - 30, p.look === 'exit' ? 340 : 300, .95); }
    for (const s of slimes) { if (s.dead) continue; const [sx, sy] = w2s(s.x, s.y); pool(sx, sy - 40, s.d?.boss ? 330 : 170, s.d?.boss ? .92 : .8); }   // enemies are always seen, wherever they stand
    for (const b of ebolts) { const [sx, sy] = w2s(b.x, b.y, 38); pool(sx, sy, 120 + b.size * 60, .75); }
    for (const b of bolts) { const [sx, sy] = w2s(b.x, b.y, 42); pool(sx, sy, 110, .6); }
    for (const e of effects) if (e.kind === 'slam') { const [sx, sy] = w2s(e.x, e.y); pool(sx, sy, 200 + e.r * 40, .7 * (1 - e.t / e.life)); }
    g.drawImage(darkCv, 0, 0, VW, VH);
  }
  // A boss in sight shows its name and health across the top of the screen.
  function drawBossBar(g) {
    let boss = null, best = 1e9;
    for (const s of slimes) if (s.d?.boss && !s.dead) { const d = Math.hypot(s.x - hero.x, s.y - hero.y); if ((d < 16 || s.state === 'chase' || s.state === 'windup' || s.state === 'lunge') && d < best) { best = d; boss = s; } }
    if (!boss) return;
    const w = 520, x = (VW - w) / 2, y = 128, f = clamp(boss.hp / boss.maxHp, 0, 1);
    g.save(); g.textAlign = 'center'; g.font = '20px "Jua", sans-serif'; g.lineWidth = 4; g.strokeStyle = 'rgba(8,6,16,.95)'; g.fillStyle = '#ffe2a0';
    const label = `${boss.d.name} · Lv ${boss.level ?? '?'}`; g.strokeText(label, VW / 2, y); g.fillText(label, VW / 2, y);
    g.fillStyle = 'rgba(12,8,20,.85)'; g.fillRect(x - 3, y + 6, w + 6, 18); g.fillStyle = '#5a1020'; g.fillRect(x, y + 9, w, 12); g.fillStyle = f > .3 ? '#d8344a' : '#ff7a3a'; g.fillRect(x, y + 9, w * f, 12);
    g.fillStyle = 'rgba(255,255,255,.28)'; g.fillRect(x, y + 9, w * f, 3); g.strokeStyle = '#c8a45a'; g.lineWidth = 2; g.strokeRect(x - 3, y + 6, w + 6, 18);
    g.fillStyle = '#fff4ca'; g.font = '13px "Jua", sans-serif'; g.fillText(`${Math.min(Math.ceil(boss.hp), Math.round(boss.maxHp)).toLocaleString('en')} / ${Math.round(boss.maxHp).toLocaleString('en')}`, VW / 2, y + 20);
    g.restore();
  }
  // ---------- fog of war ----------
  // Every zone is FOG x FOG cells; the server (Character::explore) marks the cell the hero stands in and sends the masks
  // with each snapshot (bit row * FOG + column, one mask per zone). The minimap and the world map show only those cells.
  // `explored` is null when a server sends no masks, which means no fog; [] until the first snapshot means all fog.
  const FOG = 3, fogMasks = new Map();
  let explored = [];
  const fogCell = (zi, x, y) => { const f = v => Math.min(FOG - 1, Math.max(0, Math.floor(v / ZONES[zi].size * FOG))); return f(y) * FOG + f(x); };
  const seen = (zi, x, y) => !explored || (((explored[zi] || 0) >> fogCell(zi, x, y)) & 1) === 1;
  // Draws the fog of zone `zi` over the w x h area of g. Fog is drawn as mist: pale cloud with fractal noise for body, thinning to
  // wisps where it meets explored ground. The mask is built once per bit pattern (CLOUD pixels a side) and stretched with smoothing.
  const CLOUD = FOG * 64; let cloudNoise = null;
  function noiseField(seed) {
    const h = (ix, iy) => { let n = (ix * 374761393 + iy * 668265263 + seed * 1274126177) | 0; n = Math.imul(n ^ (n >>> 13), 1274126177); return ((n ^ (n >>> 16)) >>> 0) / 4294967295; };
    const sm = t => t * t * (3 - 2 * t), out = new Float32Array(CLOUD * CLOUD);
    for (let y = 0; y < CLOUD; y++) for (let x = 0; x < CLOUD; x++) {
      let v = 0, amp = .5, tot = 0;
      for (let o = 0, f = 6; o < 5; o++, f *= 2, amp *= .5) {
        const px = x / CLOUD * f, py = y / CLOUD * f, ix = Math.floor(px), iy = Math.floor(py), fx = sm(px - ix), fy = sm(py - iy);
        const a = h(ix, iy), b = h(ix + 1, iy), c = h(ix, iy + 1), d = h(ix + 1, iy + 1);
        v += amp * (a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy); tot += amp;
      }
      out[y * CLOUD + x] = v / tot;
    }
    return out;
  }
  function paintFog(g, w, h, zi) {
    if (!explored) return;
    const bits = explored[zi] || 0; let mask = fogMasks.get(bits);
    if (!mask) {
      if (!cloudNoise) cloudNoise = [noiseField(1), noiseField(7)];
      const [shape, body] = cloudNoise, N = CLOUD, cell = N / FOG, [c, mg] = canvasOf(N, N, 1), img = mg.createImageData(N, N);
      const fogged = (cx, cy) => (bits >> (Math.min(FOG - 1, Math.max(0, cy)) * FOG + Math.min(FOG - 1, Math.max(0, cx)))) & 1 ? 0 : 1;
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const gx = x / cell - .5, gy = y / cell - .5, cx = Math.floor(gx), cy = Math.floor(gy), tx = gx - cx, ty = gy - cy;
        const a = fogged(cx, cy), b = fogged(cx + 1, cy), cc = fogged(cx, cy + 1), d = fogged(cx + 1, cy + 1);
        const cover = a + (b - a) * tx + (cc - a) * ty + (a - b - cc + d) * tx * ty;               // 1 deep in fog, 0 on explored ground
        const n = shape[y * N + x], t = Math.min(1, Math.max(0, (cover + (n - .5) * .9 - .3) / .4));
        const alpha = t * t * (3 - 2 * t), m = body[y * N + x], shade = .55 + m * .9;                // cloud body: lighter puffs, bluer hollows
        const i = (y * N + x) * 4;
        img.data[i] = Math.min(255, 150 + shade * 62); img.data[i + 1] = Math.min(255, 164 + shade * 56); img.data[i + 2] = Math.min(255, 186 + shade * 46);
        img.data[i + 3] = Math.round(alpha * (238 + m * 17));
      }
      mg.putImageData(img, 0, 0); mask = c; fogMasks.set(bits, mask);
    }
    g.save(); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(mask, 0, 0, w, h); g.restore();
  }
  function buildMini() {
    const [c, g] = canvasOf(144, 144, 1), k = 144 / MAP, ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city' || zdef.theme === 'asterion', vault = zdef.theme === 'skybridge' || zdef.theme === 'nornroot' || zdef.theme === 'vault' || zdef.theme === 'eye_below' || zdef.theme === 'elder_hollow' || zdef.theme === 'thousandfold' || zdef.theme === 'rain_crown' || zdef.theme === 'seed_vault' || zdef.theme === 'sunken_astrolabe' || zdef.theme === 'thunderheart_gate' || SeasonDungeonArt.isTheme(zdef.theme) || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', prism = zdef.theme === 'prismwaste', orrery = zdef.theme === 'orrery', moonspore = zdef.theme === 'moonspore', stormglass = zdef.theme === 'stormglass', sunward = zdef.theme === 'sunward', ribbonwild = zdef.theme === 'ribbonwild', tanglecrown = zdef.theme === 'tanglecrown', worldtree = zdef.theme === 'worldtree', heartwood = zdef.theme === 'heartwood', lapis = zdef.theme === 'lapiserg', frostwake = zdef.theme === 'frostwake', cairn = zdef.theme === 'cairnspine', yearwheel = zdef.theme === 'yearwheel', moonwell = zdef.theme === 'moonwell', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    g.fillStyle = zdef.theme === 'skybridge' ? '#19223b' : zdef.theme === 'nornroot' ? '#273c32' : moonwell ? '#153d58' : CathedralArt.isTheme(zdef.theme) ? '#080e20' : deep ? '#0b3550' : sky ? '#1a1838' : worldtree ? '#2d8866' : heartwood ? '#795b41' : frostwake ? '#c9e4ee' : cairn ? '#656b71' : lapis ? '#d5ac6c' : tanglecrown ? '#287a5b' : ribbonwild ? '#e58fb4' : sunward ? '#5baa49' : stormglass ? '#263b51' : zdef.theme === 'elder_hollow' ? '#192b1f' : zdef.theme === 'thousandfold' ? '#40264d' : zdef.theme === 'rain_crown' ? '#1c5251' : zdef.theme === 'seed_vault' ? '#415532' : zdef.theme === 'sunken_astrolabe' ? '#244653' : zdef.theme === 'thunderheart_gate' ? '#263e62' : zdef.theme === 'blooming_labyrinth' ? '#274531' : zdef.theme === 'solar_crucible' ? '#65402d' : moonspore ? '#1c4244' : orrery ? '#37394e' : prism ? '#ad887e' : astral ? '#39776f' : vault ? '#07080e' : city ? '#5f9b4a' : wyrd ? '#6a5430' : fen ? '#2f4a2c' : frost ? '#cfe3f0' : ember ? '#2b1f22' : '#3f9b48'; g.fillRect(0, 0, 144, 144);
    if (yearwheel) for(const [x,y,col] of [[0,0,'#d7edf5'],[72,0,'#bd7951'],[0,72,'#73bc77'],[72,72,'#dbb45a']]) {g.fillStyle=col;g.fillRect(x,y,72,72);}
    if (ribbonwild) for(let y=0;y<MAP;y++)for(let x=0;x<MAP;x++){const hue=[344,44,177,272][Math.floor(((Math.atan2(y-67,x-72)+Math.PI*2+Math.PI/4)%(Math.PI*2))/(Math.PI/2))];g.fillStyle=`hsl(${hue},57%,68%)`;g.fillRect(x*k,y*k,k+.5,k+.5);}
    if (sky || moonwell) { for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.floor[y * MAP + x]) { g.fillStyle = moonwell ? MoonwellArt.minimap(x,y,map.dirt[y*MAP+x],zdef) : map.dirt[y * MAP + x] ? '#f0c8f4' : '#8ad4b8'; g.fillRect(x * k, y * k, k + .5, k + .5); } }
    else for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.dirt[y * MAP + x]) { g.fillStyle = zdef.theme === 'skybridge' ? '#8dd8f2' : zdef.theme === 'nornroot' ? '#c29b59' : DungeonVisual.styles[zdef.theme] ? DungeonVisual.minimap(zdef.theme,x,y,zdef) : CathedralArt.isTheme(zdef.theme) ? CathedralArt.style(zdef.theme).left : yearwheel ? ['#e8c498','#e9bd7d','#bf8c6b','#b8d9e9'][yearSeason(x,y)] : deep ? '#c8c29a' : zdef.theme === 'elder_hollow' ? '#597251' : zdef.theme === 'thousandfold' ? '#ae779d' : zdef.theme === 'rain_crown' ? '#6aa895' : zdef.theme === 'seed_vault' ? '#b6a676' : zdef.theme === 'sunken_astrolabe' ? '#c0ac79' : zdef.theme === 'thunderheart_gate' ? '#b6d4e6' : zdef.theme === 'blooming_labyrinth' ? '#e2b7cf' : zdef.theme === 'solar_crucible' ? '#e8ba77' : zdef.theme === 'amber_archive' ? '#eac286' : zdef.theme === 'silent_solstice' ? '#b8d5e8' : zdef.theme === 'vault' ? VaultArt.minimap(x,y,zdef.rooms) : vault ? '#3a3f55' : city ? (map.dirt[y * MAP + x] === 2 ? '#ece2c8' : map.dirt[y * MAP + x] === 3 ? '#b8765a' : '#b6a98c') : worldtree ? '#c19a60' : heartwood ? '#b58a5b' : frostwake ? '#8fc6d8' : cairn ? '#b49a75' : lapis ? '#efd49b' : tanglecrown ? '#b99a62' : ribbonwild ? '#ffe2a2' : sunward ? '#d8bd83' : stormglass ? '#9ebdc1' : moonspore ? '#a5c4a8' : orrery ? '#ad907b' : prism ? '#ead7a8' : astral ? '#d7bc84' : wyrd ? '#b89860' : fen ? '#8a6a40' : frost ? '#9fb7cc' : ember ? '#6a5040' : '#c9a26a'; g.fillRect(x * k, y * k, k + .5, k + .5); }
    if (wyrd) { const gr = g.createLinearGradient(0, 0, 0, 144); gr.addColorStop(0, 'rgba(120,128,92,.95)'); gr.addColorStop(.42, 'rgba(120,128,92,.9)'); gr.addColorStop(.56, 'rgba(120,128,92,0)'); g.fillStyle = gr; g.fillRect(0, 0, 144, 144); for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.dirt[y * MAP + x]) { g.fillStyle = '#c4b290'; if (y < MAP * .5) g.fillRect(x * k, y * k, k + .5, k + .5); } }
    if (zdef.city && !city && zdef.theme !== 'nacre') for (const c of [zdef.city, ...(zdef.camps || [])]) {
      g.fillStyle=yearwheel ? ['#a1d9a1','#ecc583','#d59468','#b7d9e8'][yearSeason(c.plaza.x,c.plaza.y)] : deep ? '#4a7a82' : sky ? '#cdd2f2' : worldtree ? '#77b475' : heartwood ? '#b18b5f' : frostwake ? '#aad9e7' : cairn ? '#bdab8e' : lapis ? '#e6bb78' : tanglecrown ? '#6dab70' : ribbonwild ? '#e9a8c7' : sunward ? '#76ad56' : stormglass ? '#55798a' : moonspore ? '#719b83' : orrery ? '#a58a77' : prism ? '#c5a58d' : astral ? '#8fa9b2' : wyrd ? '#8a6a44' : fen ? '#6a5238' : frost ? '#8fa6bd' : ember ? '#88705d' : '#d8cbb0'; g.fillRect(c.x0*k,c.y0*k,(c.x1-c.x0)*k,(c.y1-c.y0)*k);
      g.fillStyle=wyrd ? '#ffd9a0' : fen ? '#ffe08a' : frost ? '#ffd27a' : ember ? '#ffb65c' : '#68bcc6'; g.beginPath();g.arc(c.plaza.x*k,c.plaza.y*k,3,0,Math.PI*2);g.fill();
    }
    for (const o of objects) {
      if (o.kind === 'post' || o.kind === 'void') continue;
      if (moonwell) {g.fillStyle=o.kind==='moonmirror'?'#f8e8ad':o.kind==='moonlily'?'#c6e4d6':'#9af2d7';g.fillRect(o.x*k-.7,o.y*k-.7,1.4,1.4);continue;}
      if (orrery) { g.fillStyle = o.kind === 'clockwall' ? '#c8aa80' : o.kind === 'blackspire' ? '#778399' : o.kind === 'stillpoint' ? '#d3b683' : '#9b8693'; g.fillRect(o.x*k-.7,o.y*k-.7,1.4,1.4); continue; }
      if (moonspore) { g.fillStyle = o.kind === 'mooncaps' ? '#c4f4af' : o.kind === 'gloomstalk' ? '#426e62' : o.kind === 'lamphouse' ? '#9ac3a7' : '#83bfa1'; g.fillRect(o.x*k-.7,o.y*k-.7,1.4,1.4); continue; }
      if (zdef.theme === 'stormglass') {g.fillStyle=o.kind==='eye_arch'?'#d5f6f2':o.kind==='meetingstone'?'#59d9ff':o.kind==='stormlamp'?'#9fe8ee':'#729ba6';g.fillRect(o.x*k-.7,o.y*k-.7,1.4,1.4);continue;}
      if (worldtree) {g.fillStyle=o.kind==='worldheart_trunk'?'#d5ae6e':o.kind==='hollow_arch'?'#e3d296':o.kind==='hanging_pod'?'#93cc83':'#5db979';g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (heartwood) {g.fillStyle=o.kind==='heartwood_vault'?'#ffe09f':o.kind==='heartwood_core'?'#a4e5a5':'#c59a68';g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (yearwheel) {g.fillStyle=o.kind.includes('gate')?'#ffe9b7':o.kind.includes('lodge')?'#f3e2b0':o.kind.includes('pool')?'#80dedc':['#87bf8d','#f4bb65','#d77d53','#a8dce9'][yearSeason(o.x,o.y)];g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (cairn) {g.fillStyle=o.kind==='cairn_thunder_gate'?'#e7c180':o.kind==='cairn_dead_tree'?'#d8d3c5':o.kind==='cairn_boulder'?'#4a5661':'#a39785';g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (frostwake) {g.fillStyle=o.kind==='frostwake_crevasse'?'#27769f':o.kind==='frostwake_frozen_pool'?'#68b7d0':o.kind==='frostwake_snow_pine'?'#438496':o.kind==='frostwake_obelisk'?'#9af1d3':'#c6e8ef';g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (lapis) {g.fillStyle=o.kind==='lapis_astrolabe'?'#e9d2a3':o.kind==='lapis_oasis'?'#56c2c5':o.kind==='lapis_date_palm'?'#6a9c6d':'#d8ae79';g.fillRect(o.x*k-1,o.y*k-1,2,2);continue;}
      if (tanglecrown) {g.fillStyle=o.kind==='rain_crown_temple'?'#f1d78b':o.kind==='jungle_water'||o.kind==='jade_pool'?'#59bac0':o.kind==='kapok_tree'||o.kind==='strangler_fig'?'#255d4b':o.kind==='banyan_lodge'?'#c4ab77':'#70b77c';g.fillRect(o.x*k-.9,o.y*k-.9,1.8,1.8);continue;}
      if (ribbonwild) {g.fillStyle=o.kind==='grand_pavilion_gate'?'#fff0b5':o.kind==='silk_pavilion'?'#f6d166':o.kind==='fan_topiary'?'#52bfc9':o.kind==='parade_standard'||o.kind==='mask_dais'?'#e670a0':'#edb7cc';g.fillRect(o.x*k-.9,o.y*k-.9,1.8,1.8);continue;}
      if (sunward) {if(o.kind==='water'){g.fillStyle='#73bad0';g.beginPath();g.arc(o.x*k,o.y*k,Math.max(1.3,o.r*k),0,6.283);g.fill();continue;}g.fillStyle=o.kind==='elder_hollow_gate'?'#ffe28a':o.kind==='meetingstone'?'#59d9ff':o.kind.includes('tree')?'#316e35':o.kind==='vale_cottage'||o.kind==='watermill'?'#f0d7a2':'#8cac56';g.fillRect(o.x*k-.8,o.y*k-.8,1.6,1.6);continue;}
      if (prism) { g.fillStyle = o.kind === 'mirrorwall' ? '#e8d9ef' : o.kind === 'sunspire' ? '#ffe3ae' : o.kind === 'shade_tent' ? '#a5798f' : '#a9909a'; g.fillRect(o.x*k-.7,o.y*k-.7,1.4,1.4); continue; }
      if (astral) { g.fillStyle = o.kind === 'crystal' || o.kind === 'obelisk' ? '#a4e9e3' : o.kind === 'astraltree' ? '#244f64' : o.kind === 'starstone' ? '#637994' : o.kind === 'astrolamp' ? '#ffe2a0' : o.kind === 'starbloom' ? '#d8afe9' : '#5eaa91'; g.fillRect(o.x * k - .55, o.y * k - .55, 1.1, 1.1); continue; }
      if (vault) { if (o.kind === 'eye_lamp' || o.kind === 'eye_lens' || o.kind === 'eye_rune') { g.fillStyle = '#9de9dc'; g.fillRect(o.x*k-1,o.y*k-1,2,2); } if (o.kind === 'elder_lantern' || o.kind === 'elder_crown' || o.kind === 'elder_seed') { g.fillStyle = '#d9e9a6'; g.fillRect(o.x*k-1,o.y*k-1,2,2); } if (o.kind === 'brazier' || o.kind === 'cathedrallamp') { g.fillStyle = '#ff9a3a'; g.fillRect(o.x * k - 1, o.y * k - 1, 2, 2); } continue; }
      if (deep && zdef.theme !== 'nacre') {                                                                   // coral walls as footprints, bells as gold dots, the rest as specks
        if (o.kind === 'reefwall') { g.fillStyle = '#d86a78'; g.fillRect((o.x - o.width / 2) * k, (o.y - o.depth / 2) * k, Math.max(1, o.width * k), Math.max(1, o.depth * k)); }
        else if (o.kind === 'tidebell') { g.fillStyle = '#ffd36a'; g.beginPath(); g.arc(o.x * k, o.y * k, 2, 0, 6.283); g.fill(); }
        else if (o.width) { g.fillStyle = o.color || '#8a7a62'; g.fillRect((o.x - o.width / 2) * k, (o.y - o.depth / 2) * k, Math.max(1, o.width * k), Math.max(1, o.depth * k)); }
        else if (o.kind === 'kelp' || o.kind === 'coral' || o.kind === 'anemone') { g.fillStyle = o.kind === 'kelp' ? '#2a8a5a' : '#e0708a'; g.fillRect(o.x * k - .5, o.y * k - .5, 1.2, 1.2); }
        continue;
      }
      if ((city || zdef.theme === 'nacre') && o.width) {                                                          // buildings and walls as footprints
        g.fillStyle = o.kind === 'rampart' ? '#6f7078' : o.kind === 'tower' ? '#3f6a8a' : o.kind === 'stall' ? '#e0a040' : o.kind === 'house' || o.kind === 'chapel' || o.kind === 'nacrehouse' || o.kind === 'nacrestall' ? o.color : '#8a7a62';
        g.fillRect((o.x - o.width / 2) * k, (o.y - o.depth / 2) * k, Math.max(1, o.width * k), Math.max(1, o.depth * k)); continue;
      }
      if ((city || zdef.theme === 'nacre') && (o.kind === 'grandfountain' || o.kind === 'nacrefountain' || o.kind === 'meetingstone' || o.kind === 'fountain')) { g.fillStyle = o.kind === 'meetingstone' ? '#59d9ff' : '#58a8d8'; g.beginPath(); g.arc(o.x * k, o.y * k, Math.max(2, o.r * k), 0, 6.283); g.fill(); continue; }
      g.fillStyle = o.kind === 'lava' ? '#ff6a2a' : o.kind === 'ice' ? '#4f93c8' : o.kind === 'water' ? (zone === 0 ? '#4fa9c8' : wyrd ? '#2f6f9a' : '#244f5c') : o.kind === 'crag' ? '#4a4a58' : o.kind === 'pine' ? '#1f4a3a' : o.kind === 'beacon' ? '#ff9a2e' : o.kind === 'gallows' || o.kind === 'ribcage' ? '#d8d0b8' : o.kind === 'elderash' ? '#8a5a2a' : o.kind === 'thicket' ? '#6a2f58' : o.kind === 'tree' ? (wyrd ? '#a8451e' : fen ? '#1b4a2a' : frost ? '#1f5a52' : ember ? '#150f13' : '#1f6b3a') : o.kind === 'spire' ? (wyrd ? '#d8d8c8' : fen ? '#b8c0b0' : frost ? '#8ccdf0' : '#4b3b5e') : o.kind === 'rock' ? (wyrd ? '#7a7a80' : fen ? '#6b7a68' : frost ? '#7f93aa' : ember ? '#6a6672' : '#8a93a8') : (fen ? '#3f6a35' : frost ? '#3a7a70' : ember ? '#5a3a30' : '#2f8a45');
      g.beginPath(); g.arc(o.x * k, o.y * k, o.kind === 'lava' ? 2.2 : o.kind === 'water' ? 1.6 : o.kind === 'ice' || o.kind === 'thicket' ? 1.7 : o.kind === 'tree' ? 2.1 : 1.2, 0, 6.283); g.fill();
    }
    for (const p of zdef.portals) { if (p.after_clear && !instanceCleared) continue; g.strokeStyle = ZONES[p.to]?.theme === 'ember' ? '#ff8a3a' : ZONES[p.to]?.theme === 'frost' ? '#8fd8ff' : ZONES[p.to]?.theme === 'fen' ? '#b8e060' : ZONES[p.to]?.theme === 'wyrd' ? '#e0963a' : ZONES[p.to]?.theme === 'sky' ? '#9fc4ff' : ['deep','nacre'].includes(ZONES[p.to]?.theme) ? '#4fe0e8' : ZONES[p.to]?.theme === 'city' ? '#ffd36a' : '#7ae8c8'; g.lineWidth = 2; g.beginPath(); g.arc(p.x * k, p.y * k, 4, 0, 6.283); g.stroke(); }
    miniBase = c;
  }
  function drawMini() {
    if (!mctx || !miniBase) return;
    const s = mini.width / MAP; mctx.clearRect(0, 0, mini.width, mini.height); mctx.drawImage(miniBase, 0, 0, mini.width, mini.height);
    paintFog(mctx, mini.width, mini.height, zone);
    for (const n of City.npcs) { if (n.travelStop || !seen(zone, n.x, n.y)) continue; mctx.fillStyle='#f5d477';mctx.fillRect(n.x*s-1,n.y*s-1,2,2); }
    // Travel masters are navigation landmarks: their spark remains visible even through unexplored mist.
    for (const n of City.npcs) if (n.travelStop) {
      const x = n.x * s, y = n.y * s;
      mctx.fillStyle = '#bdffec'; mctx.strokeStyle = '#10242e'; mctx.lineWidth = 1.5;
      mctx.beginPath(); mctx.moveTo(x, y - 5); mctx.lineTo(x + 1.5, y - 1.5); mctx.lineTo(x + 5, y); mctx.lineTo(x + 1.5, y + 1.5);
      mctx.lineTo(x, y + 5); mctx.lineTo(x - 1.5, y + 1.5); mctx.lineTo(x - 5, y); mctx.lineTo(x - 1.5, y - 1.5); mctx.closePath(); mctx.fill(); mctx.stroke();
    }
    for (const remote of remotePlayers.values()) {
      if (!seen(zone, remote.x, remote.y)) continue; mctx.fillStyle = window.Social?.isPartyMember(remote.id) ? '#7dff9b' : '#b3dfff'; mctx.beginPath(); mctx.arc(remote.x * s, remote.y * s, 2.5, 0, 6.283); mctx.fill(); }
    for (const sl of slimes) if (!sl.dead && seen(zone, sl.x, sl.y)) { mctx.fillStyle = sl.kind === 'big' ? '#c8b5ff' : '#ff6b8a'; mctx.beginPath(); mctx.arc(sl.x * s, sl.y * s, 2, 0, 6.283); mctx.fill(); }
    mctx.fillStyle = '#fff'; mctx.strokeStyle = '#1c1428'; mctx.lineWidth = 1.5; mctx.beginPath(); mctx.arc(hero.x * s, hero.y * s, 3.6, 0, 6.283); mctx.fill(); mctx.stroke();
  }

  // ---------- lifecycle ----------
  function resize() {
    if (!cv) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2); cssW = cv.clientWidth || 1600; cssH = cv.clientHeight || 900; zoom = cssW / VW;
    cv.width = Math.round(cssW * dpr); cv.height = Math.round(cssH * dpr);
    const cs = Math.min(1.5, dpr * zoom); if (Math.abs(cs - chunkScale) > .05) { chunkScale = cs; chunks.clear(); }
  }
  function loop(now) {
    if (!running) return; raf = requestAnimationFrame(loop);
    if (!last) last = now;                                  // the first frame's timestamp can precede start()
    const dt = clamp((now - last) / 1000, 0, .05); last = now;
    update(dt);
    City.update(serverNow());
    window.DayNight?.tick(dt);
    window.Weather?.tick(dt, hero.x, hero.y, !!hero.inside);
    draw(now / 1000);
  }
  const Field = {
    start(o) {
      cv = o.canvas; ctx = cv.getContext('2d'); mini = o.mini; mctx = mini ? mini.getContext('2d') : null; opts = o.opts; onHud = o.onHud || onHud; onEvent = o.onEvent || onEvent;
      if (!sprites.tree.length) buildSprites();
      setZone(0); reset(); slimes = []; remotePlayers.clear(); lastLook = ''; onCharacter = o.onCharacter || (() => {}); hero.look = { ...(o.char || {}) }; resize();
      ++spriteGeneration; mageSpr = null; warSpr = null; heroSpr = null;
      if (o.sprites) loadHeroSprites(o.sprites, o.char, o.onSprites);
      if (o.warriorSprites && !isModular()) loadWarriorSprites(o.warriorSprites, o.char);
      if (o.slimeSprites) loadSlimeSprites(o.slimeSprites);
      loadBeetleSprites(); loadCragSprites(); loadRimeSprites(); loadFenSprites(); loadWyrdSprites(); loadSkySprites(); loadDeepSprites(); loadAstralSprites(); loadPrismSprites(); loadOrrerySprites(); loadMoonsporeSprites(); loadStormglassSprites(); loadSunwardSprites(); loadRibbonwildSprites(); loadTanglecrownSprites(); loadWorldheartSprites(); loadLapisSprites(); loadFrostwakeSprites(); loadCairnSprites(); loadBankSprites(); loadChestSprites(); loadYearSprites(); loadMoonwellSprites(); loadMoonwellGardenSprites(); loadVaultSprites(); loadCathedralSprites();
      if (!Field._bound) {
        Field._bound = true;
        addEventListener('keydown', onKeyDown); addEventListener('keyup', onKeyUp); addEventListener('resize', resize);
        cv.addEventListener('pointerdown', onPointerDown); cv.addEventListener('pointermove', onPointerMove); addEventListener('pointerup', onPointerUp);
        cv.addEventListener('contextmenu', e => e.preventDefault());
      }
      Online.start({ look: hero.look,
        onWelcome: packet => applySnapshot(packet.snapshot, true),
        onSnapshot: packet => applySnapshot(packet), onEvent: networkEvent,
        onDisconnect: () => { Field.clearInput(); hero.moving = false; },
      });
      running = true; paused = false; last = 0; cancelAnimationFrame(raf); raf = requestAnimationFrame(loop);
    },
    stop() { window.Inventory?.hideTooltip(); window.Skillbar?.close(false); window.Quests?.close(false); City.close(false); Online.stop(); running = false; spriteGeneration++; remotePlayers.clear(); cancelAnimationFrame(raf); },
    clearInput() { pendingNpc=null; pendingChest=null; cityRoute=[]; keys?.clear(); if (pointer) pointer.down = false; },
    setPaused(p) { paused = p; Field.clearInput(); Online.send({ type: 'stop' }); },
    visitNpc(id) {
      if (paused || !Online.connected || hero.dead) return;
      const npc = City.npcs.find(n => n.id === id);
      if (npc) talkTo(npc);
    },
    visitCity() {
      if(paused || !Online.connected || hero.dead)return;
      if (!zdef.city) return;
      Field.clearInput(); pendingNpc=null; hero.target=null; hero.goal=null;
      cityRoute=routeTo(zone === 0 ? {x:36,y:79} : campNear()?.entry || zdef.spawn);routeTime=0;
    },
    toggleMount() {
      if (!running || paused || !Online.connected || hero.dead || hero.sparkTravel || !hero.mountOwned) return;
      Online.send({ type: 'mount', mounted: !hero.mounted });
    },
    equip(change) {
      if (!isModular()) return;
      const prefix = hero.look.class;
      const armor = change[prefix + 'Armor'], weapon = change[prefix + 'Weapon'];
      Online.send({ type: 'equip', ...(armor !== undefined ? { armor } : {}), ...(weapon !== undefined ? { weapon } : {}) });
    },
    useSkill(id) {
      if (!running || paused || !Online.connected || hero.dead) return false;
      if (id === 'attack' && hero.atkCd <= 0 && hero.dashT <= 0) { swing(); return true; }
      if (id === 'shadowstep' && isAssassin() && hero.dashCd <= 0 && hero.dashT <= 0 && hero.resource >= 20) { shadowstep(); return true; }
      const def = SKILL_BY_ID[id];
      if (def && def.class === hero.look.class && hero.level >= def.level && !(hero.skillCd?.[id] > 0) && hero.dashT <= 0 && hero.resource >= def.cost) { castSkill(def); return true; }
      return false;
    },
    get canAct() { return running && !paused && Online.connected && !hero.dead; },
    // The server checks ownership, health, the meal and the potion cooldown; this only sends the request.
    useItem(id) {
      if (!running || !Online.connected || hero.dead) return false;
      return Online.send({ type: 'use_item', item: id });
    },
    floatHero(text, color = '#ffe066') { if (running && !hero.dead) floater(hero.x, hero.y, text, color, false, 'banner', 118); },
    equipSlot(slot, item) {
      if (!running || !Online.connected || hero.dead) return false;
      return Online.send({ type: 'equip', slots: { [slot]: item } });
    },
    get remotePlayers() { return [...remotePlayers.values()]; },
    targetPlayer(id) { if (!remotePlayers.has(id)) return false; hero.pvpTargetId = id; hero.target = null; hero.goal = null; emitHud(); return true; },
    // Shows `text` in a speech bubble over the character `id` for a few seconds (longer for longer messages).
    bubble(id, text, party = false) {
      text = String(text || '').trim(); if (!id || !text) return;
      bubbles.set(id, { text, party, lines: null, until: performance.now() + 3500 + Math.min(text.length, 120) * 45 });
    },
    // Test hooks: the live bubble text and box for a character, and how many bubbles the last frame drew.
    bubbleText(id) { const b = bubbles.get(id); return b && b.until > performance.now() ? b.text : null; },
    bubbleBox(id) { return bubbles.get(id)?.box || null; },
    bubbleDrawn() { return bubblesLast; },
    enemyName(kind) { return SLIME[kind]?.name || null; },
    drawTargetPortrait,
    get equipmentStats() { return equipmentStats(); },
    get warriorSprites() { return !isMage() && !isAssassin() && !isPriest() && !isHunter() ? mageSpr : null; },
    get mageSprites() { return isMage() ? mageSpr : null; },
    get assassinSprites() { return isAssassin() ? mageSpr : null; },
    get priestSprites() { return isPriest() ? mageSpr : null; },
    get hunterSprites() { return isHunter() ? mageSpr : null; },
    get hero() { return hero; }, get signs() { return signs; }, get slimes() { return slimes; }, get meadowPaths() { return PATHS; },
    get explored() { return explored; }, fog: { grid: FOG, seen, paint: paintFog, cell: fogCell },
    get beetleSprites() { return beetleSrc; }, get cragSprites() { return cragSrc; }, get rimeSprites() { return rimeSrc; }, get fenSprites() { return fenSrc; }, get wyrdSprites() { return wyrdSrc; }, get skySprites() { return skySrc; }, get deepSprites() { return deepSrc; }, get astralSprites() { return astralSrc; }, get prismSprites() { return prismSrc; }, get orrerySprites() { return orrerySrc; }, get moonsporeSprites() { return moonsporeSrc; }, get stormglassSprites() { return stormglassSrc; }, get sunwardSprites() { return sunwardSrc; }, get ribbonwildSprites() { return ribbonwildSrc; }, get tanglecrownSprites() { return tanglecrownSrc; }, get worldheartSprites() { return worldheartSrc; }, get lapisSprites() { return lapisSrc; }, get frostwakeSprites() { return frostwakeSrc; }, get cairnSprites() { return cairnSrc; }, get bankSprites() { return bankSrc; }, get yearSprites() { return yearSrc; }, get moonwellSprites() { return moonwellSrc; }, get moonwellGardenSprites() { return moonwellGardenSrc; }, get cathedralSprites() { return cathedralSrc; }, get vaultSprites() { return vaultSrc; },
    get zone() { return zone; }, get zoneName() { return zdef.name; }, get zoneTheme() { return zdef.theme; }, place: id => (zdef.places || []).find(p => p.id === id) || null,
    _debug: { get floaters() { return floaters; }, get chests() { return chests; }, get chestSprites() { return chestSrc; }, get drops() { return drops; }, get pendingChest() { return pendingChest; }, get cityRoute() { return cityRoute; }, get effects() { return effects; }, get bolts() { return bolts; }, get ebolts() { return ebolts; }, get cleared() { return instanceCleared; }, event: networkEvent, get objects() { return objects; }, get zones() { return ZONES; }, w2s, s2w, routeTo, drawLootPillar, enemyFrame: s => slimeFrame(s, tAll), enemyHitbox },
  };
  window.Field = Field;
})();
