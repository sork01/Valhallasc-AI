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
  const ZONES = [{ name: 'Greenmeadow', theme: 'meadow', size: WORLD_MAP.size, spawn: WORLD_MAP.spawn, objects: WORLD_MAP.objects, city: WORLD_MAP.city, npcs: WORLD_MAP.npcs, portals: WORLD_MAP.portals || [], paths: null, levels: null },
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
  const PATHS = [
    [[36, 79], [36, 71], [36, 62], [33, 52], [38, 44], [36, 36], [42, 28], [50, 22], [54, 12]],
    [[36, 36], [26, 32], [16, 26], [10, 16]],
  ];
  const map = { dirt: new Uint8Array(0), tone: new Float32Array(0) };
  let objects = [];
  function buildMap() {
    MAP = zdef.size; SPAWN = zdef.spawn;
    map.dirt = new Uint8Array(MAP * MAP); map.tone = new Float32Array(MAP * MAP);
    const paths = zdef.paths || PATHS, ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city', vault = zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) {
      const i = y * MAP + x, cx = x + .5, cy = y + .5;
      map.tone[i] = vnoise(cx * .16, cy * .16, ember ? 11 : frost ? 21 : fen ? 31 : city ? 41 : vault ? 51 : wyrd ? 61 : sky ? 71 : astral ? 91 : deep ? 81 : 1) * .65 + vnoise(cx * .55, cy * .55, ember ? 12 : frost ? 22 : fen ? 32 : city ? 42 : vault ? 52 : wyrd ? 62 : sky ? 72 : astral ? 92 : deep ? 82 : 2) * .35;
      let d = 99; for (const p of paths) for (let k = 0; k < p.length - 1; k++) d = Math.min(d, segDist(cx, cy, p[k][0], p[k][1], p[k + 1][0], p[k + 1][1]));
      if (!ember && !frost && !fen && !city && !vault && !wyrd && !sky && !astral && !deep) d = Math.min(d, Math.hypot(cx - 36, cy - 36) - 2.4);
      map.dirt[i] = d < 1.15 + vnoise(cx * .5, cy * .5, 3) * .6 ? 1 : 0;
    }
    if (city || zdef.theme === 'nacre') paintRoads(zdef.roads);
    if (vault) paintRooms(zdef.rooms);
    map.floor = null;
    if (sky) paintSky(zdef.sky);
    objects = zdef.objects.map(o => ({ ...o }));
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
  const isVoid = (x, y) => !!map.floor && (x < 0 || y < 0 || x >= MAP || y >= MAP || !map.floor[y * MAP + x]);
  // Switch to another zone: new ground, obstacles and minimap. Everything tied to the old zone's coordinates goes.
  function setZone(z) {
    zone = ZONES[z] ? z : 0; zdef = ZONES[zone];
    buildMap(); chunks.clear();
    if (mini) buildMini();
    if (hero) { pendingNpc = null; cityRoute = []; hero.target = null; hero.goal = null; }
    floaters = []; parts = []; effects = []; bolts = []; ebolts = []; drops = []; marker = null; slimes = []; remotePlayers.clear(); bubbles.clear();
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
  const spriteSet = () => zdef.theme === 'wyrd' || zdef.theme === 'sky' || zdef.theme === 'deep' || zdef.theme === 'nacre' || zdef.theme === 'astral' || CathedralArt.isTheme(zdef.theme) ? WYRD_NONE : zdef.theme === 'ember' ? emberSprites : zdef.theme === 'frost' ? frostSprites : zdef.theme === 'fen' ? fenSprites : sprites;

  // ---------- ground chunks ----------
  const chunks = new Map(); let chunkScale = 1;
  const CLIFF = 120, PADX = 10, PADTOP = 40;
  function chunkGeom(cx, cy) { const x0 = cx * CH, y0 = cy * CH; return { x0, y0, ox: (x0 - (y0 + CH)) * TW / 2 - TW / 2 - PADX, oy: (x0 + y0) * TH / 2 - PADTOP, w: CH * TW + TW + PADX * 2, h: CH * TH + TH + PADTOP + CLIFF }; }
  function renderChunk(cx, cy) {
    const G = chunkGeom(cx, cy), [c, g] = canvasOf(G.w, G.h, chunkScale);
    const ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city', vault = zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    const arenas = vault ? (zdef.slimes || []).filter(m => BOSS_KINDS.includes(m.kind)) : [];
    for (let ty = 0; ty < CH; ty++) for (let tx = 0; tx < CH; tx++) {
      const x = G.x0 + tx, y = G.y0 + ty; if (x >= MAP || y >= MAP) continue;
      const i = y * MAP + x, px = (x - y) * TW / 2 - G.ox, py = (x + y) * TH / 2 - G.oy, tone = map.tone[i], dirt = map.dirt[i];
      if (vault && !dirt) continue;                                                  // solid rock: stays black
      if (sky && !map.floor[i]) continue;                                            // open sky: nothing to draw
      const alt = ((x + y) & 1) ? 1.4 : -1.4, e = .7;
      g.fillStyle = CathedralArt.isTheme(zdef.theme) ? CathedralArt.ground(zdef.theme,x,y,tone,alt) : vault ? `hsl(${226 + tone * 10}, ${9 + tone * 5}%, ${19 + tone * 7 + alt * .7}%)` : city ? (dirt === 1 ? `hsl(${32 + tone * 6}, ${9 + tone * 5}%, ${46 + tone * 7 + alt * .5}%)` : dirt === 2 ? `hsl(${42 + tone * 6}, ${24 + tone * 6}%, ${(x + y) & 1 ? 79 : 75}%)` : dirt === 3 ? `hsl(${14 + tone * 6}, ${34 + tone * 6}%, ${50 + tone * 6 + alt * .5}%)` : `hsl(${96 + tone * 14}, ${46 + tone * 10}%, ${38 + tone * 8 + alt * .8 + (((x + y) >> 1) & 1) * 1.6}%)`)
        : sky ? skyGround(x, y, tone, dirt, alt)
        : astral ? (dirt ? `hsl(${43 + tone * 9}, 33%, ${34 + tone * 9 + alt}%)` : `hsl(${158 + tone * 42}, ${32 + tone * 14}%, ${27 + tone * 12 + alt}%)`)
        : deep ? deepGround(x, y, tone, dirt, alt)
        : wyrd ? wyrdGround(x, y, tone, dirt, alt)
        : fen ? (dirt ? `hsl(${30 + tone * 6}, ${30 + tone * 6}%, ${27 + tone * 6 + alt}%)` : `hsl(${92 + tone * 16}, ${26 + tone * 12}%, ${21 + tone * 9 + alt * .8}%)`)
        : frost ? (dirt ? `hsl(${208 + tone * 8}, ${26 + tone * 8}%, ${66 + tone * 6 + alt}%)` : `hsl(${200 + tone * 12}, ${44 + tone * 10}%, ${84 + tone * 8 + alt * .6}%)`)
        : ember ? (dirt ? `hsl(${22 + tone * 8}, ${20 + tone * 8}%, ${30 + tone * 8 + alt}%)` : `hsl(${12 + tone * 14}, ${10 + tone * 8}%, ${15 + tone * 11 + alt}%)`)
        : dirt ? `hsl(${30 + tone * 8}, ${38 + tone * 8}%, ${48 + tone * 8 + alt}%)` : `hsl(${100 + tone * 16}, ${46 + tone * 12}%, ${36 + tone * 12 + alt}%)`;
      g.beginPath(); g.moveTo(px, py - e); g.lineTo(px + TW / 2 + e, py + TH / 2); g.lineTo(px, py + TH + e); g.lineTo(px - TW / 2 - e, py + TH / 2); g.closePath(); g.fill();
      const r = rngf(x * 977 + y * 131 + 7), inTile = () => { const a = r() - .5, b = r() - .5; return [px + (a - b) * TW * .4, py + TH / 2 + (a + b) * TH * .4]; };
      if (CathedralArt.isTheme(zdef.theme)) {
        CathedralArt.detail(g,zdef.theme,px,py,x,y,TW,TH);
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
      if (!vault) City.stoneTile(g, px, py, x, y);
      // earth cliff on the two front edges of the island
      const depth = sky ? CLIFF - 40 + hash2(x, y, 9) * 36 : CLIFF - 34 + hash2(x, y, 9) * 26;
      const face = (dir) => {
        const vx = px + dir * TW / 2, vy = py + TH / 2, bx = px, by = py + TH;
        const gr = g.createLinearGradient(0, vy, 0, vy + depth);
        if (city) { gr.addColorStop(0, dir > 0 ? '#cdb48a' : '#b79c74'); gr.addColorStop(1, dir > 0 ? '#7a6044' : '#65503a'); }
        else if (sky) { gr.addColorStop(0, dir > 0 ? '#c3cbe6' : '#a9b3d6'); gr.addColorStop(.45, dir > 0 ? '#7a84ae' : '#6a7399'); gr.addColorStop(1, dir > 0 ? '#2c3156' : '#23284a'); }
        else if (deep) { gr.addColorStop(0, dir > 0 ? '#1a4a5e' : '#143c4e'); gr.addColorStop(1, dir > 0 ? '#06161f' : '#04101a'); }
        else if (wyrd) { gr.addColorStop(0, dir > 0 ? '#6a4a2e' : '#583a22'); gr.addColorStop(1, dir > 0 ? '#2e2016' : '#241a12'); }
        else if (fen) { gr.addColorStop(0, dir > 0 ? '#5a4c38' : '#4a3e2e'); gr.addColorStop(1, dir > 0 ? '#2a2218' : '#201a12'); }
        else if (frost) { gr.addColorStop(0, dir > 0 ? '#a9d3ee' : '#8fbddb'); gr.addColorStop(1, dir > 0 ? '#2f5a82' : '#274b70'); }
        else if (ember) { gr.addColorStop(0, dir > 0 ? '#4a3430' : '#3c2a28'); gr.addColorStop(1, dir > 0 ? '#1e1416' : '#181012'); }
        else { gr.addColorStop(0, dir > 0 ? '#7a5433' : '#684528'); gr.addColorStop(1, dir > 0 ? '#3d2a1c' : '#33221a'); }
        g.fillStyle = gr; g.beginPath(); g.moveTo(vx, vy); g.lineTo(bx, by); g.lineTo(bx, by + depth * (.85 + hash2(x + 3, y, 4) * .3)); g.lineTo(vx, vy + depth); g.closePath(); g.fill();
        g.strokeStyle = 'rgba(0,0,0,.18)'; g.lineWidth = 2; for (let k = 1; k < 4; k++) { g.beginPath(); g.moveTo(vx, vy + depth * k / 4); g.lineTo(bx, by + depth * k / 4 * .9); g.stroke(); }
        g.strokeStyle = sky ? '#f4fbff' : deep ? '#2a6a7a' : city ? '#5faa44' : wyrd ? '#b8742a' : fen ? '#4f7a36' : frost ? '#eaf7ff' : ember ? '#8a3a1c' : '#3f8a3c'; g.lineWidth = 5; g.beginPath(); g.moveTo(vx, vy + 1); g.lineTo(bx, by + 1); g.stroke();
        if (ember) { g.strokeStyle = 'rgba(255,120,40,.55)'; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + 3); g.lineTo(bx, by + 3); g.stroke(); }
        g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + depth); g.lineTo(bx, by + depth * .9); g.stroke();
      };
      if (sky) { if (isVoid(x + 1, y)) face(1); if (isVoid(x, y + 1)) face(-1); }
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
  let hero, slimes, drops, floaters, parts, effects, bolts, marker, cam, shake, keys, pointer, msg, hudT, tAll;
  let ebolts = [], instanceCleared = false, clearedAt = -99;   // missiles shot by ranged enemies; the dungeon's exit opens when its last boss falls
  let mageSpr = null, spriteGeneration = 0;
  let pendingNpc = null, cityRoute = [], routeTime = 0;
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
  };
  const CATHEDRAL_KINDS = CATHEDRAL_ENEMIES.map(e => e.kind);
  for (const e of CATHEDRAL_ENEMIES) SLIME[e.kind] = { name:e.name, elite:true, boss:e.boss, scale:e.stats[3] * .72, top:82, col:[e.color,e.color,'#152431'] };
  const CRAG_KINDS = ['wisp', 'spider', 'wraith', 'golem', 'cinderlord'], RIME_KINDS = ['crab', 'wolf', 'yeti', 'wyrm'], FEN_KINDS = ['toad', 'croc', 'knight', 'hydra', 'gloomroot'];
  const WYRD_KINDS = ['boar', 'crow', 'troll', 'weaver', 'ram', 'oakhorn', 'hrungnir'], SKY_KINDS = ['galehound', 'prismgolem', 'skyray', 'einherjar', 'thunderroc'], DEEP_KINDS = ['draugr', 'angler', 'moray', 'siren', 'shellback', 'kraken', 'hvitserk', 'ghostmaw'], ASTRAL_KINDS = ['voidmoth', 'crystalwyrm', 'orbitbeetle', 'eclipsedryad', 'meteorgolem'];
  const VAULT_KINDS = ['thrall', 'archer', 'acolyte', 'gatewarden', 'choir', 'colossus', 'hollowking'], BOSS_KINDS = [...VAULT_KINDS.slice(3), ...CATHEDRAL_ENEMIES.filter(e => e.boss).map(e => e.kind)];
  // Colour a level label by how it compares with the hero: grey, normal, orange, red.
  const levelColor = level => { const d = level - (hero?.level || 1); return d >= 5 ? '#ff6b6b' : d >= 3 ? '#ffa65a' : d <= -5 ? '#9fb0a0' : '#fff4ca'; };
  function newHero() {
    return { x: SPAWN.x, y: SPAWN.y, r: .3, hp: 120, maxHp: 120, level: 1, xp: 0, gold: 0, kills: 0, fx: 1, fy: 1, moving: false, walk: 0, atkT: 0, atkCd: 0, atkHit: false, hurtT: 0, lastHurt: -99, dead: false, deadT: 0, target: null, goal: null, vx: 0, vy: 0, roar: 0, dashT: 0, dashCd: 0, dashX: 0, dashY: 0, dashTrail: 0 };
  }
  function reset() {
    pendingNpc = null; cityRoute = [];
    window.Quests?.reset(); window.WorldMap?.reset(); explored = [];
    hero = newHero(); drops = []; floaters = []; parts = []; effects = []; bolts = []; marker = null; shake = 0; msg = null; hudT = 0; tAll = 0;
    keys = new Set(); pointer = { down: false, x: 0, y: 0 };
    cam = { x: hero.x, y: hero.y };
    slimes = []; emitHud(true);
  }
  const hubs = () => [zdef.city, ...(zdef.camps || [])].filter(Boolean);
  const hubAt = (x, y) => hubs().find(c => x >= c.x0 && x <= c.x1 && y >= c.y0 && y <= c.y1);
  const campNear = () => hubs().reduce((a, c) => !a || Math.hypot(hero.x - c.plaza.x, hero.y - c.plaza.y) < Math.hypot(hero.x - a.plaza.x, hero.y - a.plaza.y) ? c : a, null);
  function emitHud(force) { onHud({ hp: hero.hp, maxHp: hero.maxHp, resource: hero.resource, maxResource: hero.maxResource, resourceType: hero.resourceType, xp: hero.xp, xpNeed: hero.xpNeed || 100, level: hero.level, gold: hero.gold, kills: hero.kills, msg, area: zone > 0 ? zdef.name : City.inside(hero.x, hero.y) ? WORLD_MAP.city.name : 'Greenmeadow', zone, camp: campNear()?.name, tagline: zdef.tagline, hub: hubAt(hero.x, hero.y)?.name ?? null, levels: zdef.levels, players: zdef.players, buffs: hero.buffs || [], sparkTravel:hero.sparkTravel, traveling: cityRoute.length > 0 && !pendingNpc }); }

  // ---------- coordinates ----------
  const camS = () => { const [x, y] = w2sRaw(cam.x, cam.y); return [Math.round(x), Math.round(y)]; };   // whole pixels: fractional offsets make big blits resample (slow)
  function w2s(x, y, z = 0) { const [cx, cy] = camS(), [sx, sy] = w2sRaw(x, y); return [sx - cx + VW / 2 + Math.round(shakeX), sy - cy + VH / 2 + Math.round(shakeY) - z]; }
  function s2w(sx, sy) { const [cx, cy] = camS(), rx = sx - VW / 2 + cx, ry = sy - VH / 2 + cy; return [rx / TW + ry / TH, ry / TH - rx / TW]; }
  let shakeX = 0, shakeY = 0;
  function pointerWorld(e) { const r = cv.getBoundingClientRect(); return s2w((e.clientX - r.left) / r.width * VW, (e.clientY - r.top) / r.height * VH); }

  // ---------- input ----------
  const KEYDIR = { w: [0, -1], arrowup: [0, -1], s: [0, 1], arrowdown: [0, 1], a: [-1, 0], arrowleft: [-1, 0], d: [1, 0], arrowright: [1, 0] };
  function onKeyDown(e) {
    if (e.defaultPrevented || !running || paused || hero.sparkTravel || !Online.connected || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName || '')) return;
    const k = e.key.toLowerCase();
    if (k === 'f' && !e.repeat && !hero.dead) {
      e.preventDefault(); const npc = City.npcs.filter(n => Math.hypot(n.x-hero.x,n.y-hero.y)<2.8).sort((a,b)=>Math.hypot(a.x-hero.x,a.y-hero.y)-Math.hypot(b.x-hero.x,b.y-hero.y))[0];
      if (npc) talkTo(npc); return;
    }
    if (KEYDIR[k]) { pendingNpc = null; cityRoute = []; keys.add(k); hero.target = null; hero.goal = null; e.preventDefault(); }
    if ((k === ' ' && e.target?.tagName !== 'BUTTON') || k === 'j') { e.preventDefault(); if (!e.repeat) Field.useSkill('attack'); }
    if (k === 'shift' && isAssassin()) { e.preventDefault(); if (!e.repeat) Field.useSkill('shadowstep'); }
  }
  function onKeyUp(e) { keys.delete(e.key.toLowerCase()); }
  function pickSlime(wx, wy) {
    let best = null, bd = 1.1;
    for (const s of slimes) { if (s.dead) continue; const d = Math.hypot(s.x - wx, s.y - wy) - s.r * .6; if (d < bd) { bd = d; best = s; } }
    return best;
  }
  function onPointerDown(e) {
    if (!running || paused || !Online.connected || hero.dead || hero.sparkTravel) return;
    pendingNpc = null; cityRoute = [];
    const r = cv.getBoundingClientRect(), mx=(e.clientX-r.left)/r.width*VW, my=(e.clientY-r.top)/r.height*VH;
    const npc = City.npcs.find(n => { const [x,y]=w2s(n.x,n.y); return Math.abs(mx-x)<32 && my>y-City.nameplateTop(n) && my<y+12; });
    if (npc) { talkTo(npc); return; }
    pointer.down = true; cv.setPointerCapture && cv.setPointerCapture(e.pointerId);
    const [wx, wy] = pointerWorld(e); pointer.x = wx; pointer.y = wy;
    const s = pickSlime(wx, wy);
    if (s) { hero.target = s; hero.goal = null; Online.send({ type: 'target', id: s.id }); } else { hero.target = null; hero.goal = { x: wx, y: wy }; Online.send({ type: 'move', x: wx, y: wy }); marker = { x: clamp(wx, .8, MAP - .8), y: clamp(wy, .8, MAP - .8), t: 0 }; }
  }
  function talkTo(npc) {
    keys.clear(); pointer.down = false; hero.target = null; hero.goal = null; cityRoute = [];
    if (Math.hypot(hero.x-npc.x,hero.y-npc.y) <= 2.5) Online.send({type:'interact',npc:npc.id});
    else { cityRoute = routeTo(npc, true); pendingNpc = { npc, until: tAll + Math.max(20, cityRoute.length * .6) }; routeTime = 0; }
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
  function routeTo(goal, approach = false, origin = hero) {
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
        if(distance<=2 && free(x,y))candidates.push({point:[x,y],score:distance+Math.hypot(x-origin.x,y-origin.y)*.1});
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
  function floater(x, y, text, color, big) { floaters.push({ x, y, z: 30, text, color, big, t: 0 }); }
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
    const point = hero.target && !hero.target.dead ? hero.target : pointer;
    if (point.x || point.y) { const dx = point.x - hero.x, dy = point.y - hero.y, n = Math.hypot(dx, dy); if (n > .3) { fx = dx / n; fy = dy / n; } }
    return [fx, fy];
  }
  function swing() { const [fx, fy] = aim(); Online.send({ type: 'attack', fx, fy }); }
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
    explored = Array.isArray(own.explored) ? own.explored : null;
    if (typeof packet.time === 'number') { clock.t = packet.time; clock.at = performance.now(); clock.ok = true; }
    // The server decides the zone (a gate moved us); rebuild the ground and snap everything to the new place.
    const moved = (own.zone || 0) !== zone;
    if (moved) setZone(own.zone || 0);
    const inZone = a => (a.zone || 0) === zone;
    const selectedTarget = hero.target?.id;
    const wasDead = hero.dead;
    applyActor(hero, own, initial || moved || !!hero.sparkTravel !== !!own.sparkTravel);
    if(hero.sparkTravel){City.close();keys.clear();pointer.down=false;cityRoute=[];pendingNpc=null;hero.target=null;hero.goal=null;}
    window.Attributes?.update(own);
    window.Inventory?.update(own.inventory || [], own.look, own.equipment || {}, own.bags || []);
    window.Quests?.setBells(own.bells || []);
    window.Quests?.update(own.quests || []);
    if (wasDead !== hero.dead) say(hero.dead ? 'death' : 'respawn');
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
      const actor = existing.get(data.id) || { ...data }; applyActor(actor, data, initial || moved);
      actor.d = SLIME[data.kind]; return actor;
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
        else classSprite(player.look).load(player.look).then(sprite => {
          if (generation === spriteGeneration && remote.signature === lookKey) remote.sprite = sprite;
        }).catch(() => say('spriteError'));
      }
    }
    for (const id of remotePlayers.keys()) if (!present.has(id)) remotePlayers.delete(id);
    bolts = packet.bolts.filter(inZone).map(b => ({ ...b, col: b.color }));
    ebolts = (packet.ebolts || []).filter(inZone).map(b => { const old = ebolts.find(o => o.id === b.id); return old && Math.hypot(old.x - b.x, old.y - b.y) < 2.5 ? Object.assign(old, b, { x: old.x + (b.x - old.x) * .5, y: old.y + (b.y - old.y) * .5 }) : { ...b }; });
    if (packet.instance) { if (packet.instance.cleared && !instanceCleared) { clearedAt = performance.now() / 1000; instanceCleared = true; if (mini) buildMini(); } instanceCleared = !!packet.instance.cleared; }
    drops = packet.drops.filter(inZone);
    emitHud();
  }
  function networkEvent(event) {
    if (event.actor === Online.id && !['death', 'respawn'].includes(event.kind)) say(event.crit && event.kind === 'hit' ? 'crit' : event.kind, event);
    if (event.kind === 'skill') skillFx(event);
    if (event.kind === 'hit') {
      // A little scatter keeps the numbers of a many-hit skill readable.
      floater(event.x + (Math.random() - .5) * .6, event.y + (Math.random() - .5) * .6, String(event.value), event.crit ? '#ffe066' : '#fff4e0', event.crit);
      burst(event.x, event.y, 12, 7, ['#fff4e0', '#cfb5fa']);
    }
    if (event.kind === 'hurt') floater(event.x, event.y, '-' + event.value, '#ff8b9b', false);
    if (event.kind === 'miss' || event.kind === 'dodge') floater(event.x, event.y, event.kind === 'miss' ? 'Miss' : 'Dodge', '#e5e5d2', false);
    if (event.kind === 'itemPickup') { floater(event.x, event.y, `+${event.quantity} ${event.name}`, '#64b5ff', false); if(event.actor === Online.id) say('pickup'); }
    if (event.kind === 'pickup') floater(event.x, event.y, '+' + event.value + ' gold', '#ffe066', false);
    if (event.kind === 'portal') { effects.push({ kind: 'ring', x: event.x, y: event.y, t: 0 }); burst(event.x, event.y, 20, 14, ['#ffd9a0', '#ff8a3a', '#7ae8c8']); }
    if (event.kind === 'levelup') levelUpFx(event);
    if (event.kind === 'slam') { effects.push({ kind: 'slam', x: event.x, y: event.y, r: event.value, t: 0, life: .7 }); burst(event.x, event.y, 6, 26, ['#e8dcc0', '#a9a08a', '#ffb060'], 5, 10); kick(event.value > 4 ? 14 : 9, .45); }
    if (event.kind === 'cleared') { clearedAt = performance.now() / 1000; instanceCleared = true; if (mini) buildMini(); burst(event.x, event.y, 20, 40, ['#d4ffc8', '#9cff8f', '#ffffff'], 6, 4); effects.push({ kind: 'ring', x: event.x, y: event.y, t: 0, life: 1.6, grow: 2.4, col: '#9cff8f' }); }
    // Food and potions: a potion lands at once with a ring and its number; a meal shows its share every second.
    if (event.kind === 'consume') {
      spark(event.x, event.y, 14, ['#9dffb4', '#d8ffe0', '#f0d9a0'], 10, 1, .9);
      if (event.mana > 0) floater(event.x, event.y, '+' + event.mana + ' mana', '#85baff', false);
      if (event.value > 0) { effects.push({ kind: 'skAura', x: event.x, y: event.y, core: '#d9ffe0', glow: '#3fd36a', col: '#3fd36a', a: 0, t: 0, life: 1 }); floater(event.x, event.y, '+' + event.value, '#7dff9a', true); }
    }
    // A party member healed by a priest: their own number and glow, whoever cast it.
    if (event.kind === 'healed' && event.value > 0) floater(event.x, event.y, '+' + event.value, '#7dff9a', true);
    if (event.kind === 'regen') { floater(event.x, event.y, '+' + event.value, '#7dff9a', false); spark(event.x, event.y, 4, ['#9dffb4', '#d8ffe0'], 6, .6, .6); }
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
    if (kind === 'cone') { effects.push({ ...base, kind: 'skCone', r: def.effect.reach, life: .42 }); spark(ev.x + ev.fx * 1.2, ev.y + ev.fy * 1.2, 16, [core, glow], 5, 3, .5); if (own) kick(5, .18); }
    else if (kind === 'nova') {
      const r = ev.value, style = ['whirlwind', 'cycloneblades', 'arcanestorm'].includes(ev.skill) ? 'spiral' : ['groundslam', 'earthshatter', 'titanswrath'].includes(ev.skill) ? 'cracks' : '';
      const nova = { ...base, kind: 'skNova', r, style, life: (ev.skill === 'starfall' ? 1.5 : .5) + r * .05 };
      if (style === 'cracks') nova.cracks = Array.from({ length: 9 + Math.round(r) }, (_, i) => ({ a: i * 6.283 / (9 + Math.round(r)) + (Math.random() - .5) * .3, len: .75 + Math.random() * .3, zig: Array.from({ length: 8 }, (_, j) => [(j + 1) / 8, (Math.random() - .5) * .22]) }));
      if (ev.skill === 'starfall') nova.stars = Array.from({ length: 18 }, () => { const an = Math.random() * 6.283, d = Math.sqrt(Math.random()) * r * .9; return { x: ev.x + Math.cos(an) * d, y: ev.y + Math.sin(an) * d, delay: Math.random() * .8 }; });
      effects.push(nova);
      spark(ev.x, ev.y, 14 + Math.round(r * 5), [core, glow], 6, 2 + r * .9, .6 + r * .05);
      if (r >= 4 && ev.skill !== 'starfall') effects.push({ ...base, kind: 'skNova', r: r * .65, life: .5 + r * .05, t: -.12 });
      if (own) kick(Math.min(16, 4 + r * 1.6), .15 + r * .06);
    } else if (kind === 'volley') { effects.push({ ...base, kind: 'skFlash', life: .22 }); spark(ev.x, ev.y, 8, [core, glow], 3, 2, .4); if (ev.value >= 8) effects.push({ ...base, kind: 'skNova', r: 1.6, life: .4 }); }
    else if (kind === 'dash') {
      const dist = ev.value, end = { x: ev.x + ev.fx * dist, y: ev.y + ev.fy * dist };
      if (def.effect.mult === 0) {
        effects.push({ ...base, kind: 'skBeam', life: .5 }); effects.push({ ...base, kind: 'skBeam', x: end.x, y: end.y, life: .5, t: -def.effect.time });
        spark(ev.x, ev.y, 18, [core, glow], 9, 1.5, .8); spark(end.x, end.y, 18, [core, glow], 9, 1.5, .8);
      } else { effects.push({ ...base, kind: 'skDash', ex: end.x, ey: end.y, life: .5 }); spark(ev.x, ev.y, 12, [core, glow, '#c8b090'], 3, 3, .5); if (own) kick(4, .2); }
    } else if (kind === 'strike') {
      if (ev.skill === 'lifedrain') for (const p of pts) effects.push({ ...base, kind: 'skChain', path: jagged(p, { x: ev.x, y: ev.y }), life: .5 });
      else pts.forEach((p, i) => effects.push({ ...base, kind: 'skCut', x: p.x, y: p.y, big: pts.length === 1, ang: Math.random() * 3.14, life: .3, t: -i * (pts.length > 4 ? .035 : .06) }));
      if (own && pts.length === 1) kick(6, .2);
    } else if (kind === 'chain') {
      let from = { x: ev.x, y: ev.y };
      pts.forEach((p, i) => { effects.push({ ...base, kind: 'skChain', path: jagged(from, p), life: .45, t: -i * .06 }); from = p; });
    } else if (kind === 'meteor') {
      const c = pts[0] || { x: ev.x + ev.fx * 4, y: ev.y + ev.fy * 4 };
      effects.push({ ...base, kind: 'skMeteor', x: c.x, y: c.y, r: ev.value, life: 1.1 });
      setTimeout(() => { spark(c.x, c.y, 40, [core, glow, '#ffe27a'], 10, 4, 1); if (own) kick(14, .5); }, 380);
    } else if (kind === 'buff') {
      const col = BUFF_COL[def.effect.kind] || glow; effects.push({ ...base, kind: 'skAura', col, life: 1 }); spark(ev.x, ev.y, 22, [core, col], 12, 1.2, 1); floater(ev.x, ev.y, def.name, col, false);
    } else if (kind === 'heal') { effects.push({ ...base, kind: 'skAura', col: glow, life: 1 }); spark(ev.x, ev.y, 26, [core, glow], 12, 1.2, 1.1); }
    else if (kind === 'mend') { effects.push({ ...base, kind: 'skFlash', life: .22 }); spark(ev.x, ev.y, 8, [core, glow], 6, .8, .6); }
    // Whoever else the skill reached (healed or blessed party members) gets their own glow and sparks.
    if (kind === 'mend' || kind === 'buff' || def.pulse) for (const p of pts) { effects.push({ ...base, kind: 'skAura', x: p.x, y: p.y, col: BUFF_COL[def.effect.kind] || glow, life: 1 }); spark(p.x, p.y, 16, [core, glow], 10, 1, .9); }
    if (ev.heal > 0) { floater(ev.x, ev.y, '+' + ev.heal, '#7dff9a', true); if (kind !== 'heal') spark(ev.x, ev.y, 12, ['#9dffb4', '#d8ffe0'], 10, 1, .9); }
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
    floaters.push({ x: ev.x, y: ev.y, z: 78, text: `Level ${ev.level}`, color: '#ffffff', big: true, t: 0 });
    if (own) kick(13, .8);
  }
  function drawLevelFx(g, e) {
    const [sx, sy] = w2s(e.x, e.y), p = e.t / e.life;
    g.save(); g.globalCompositeOperation = 'lighter';
    if (e.kind === 'luPillar') {
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
  function drawSkillFx(g, e) {
    if (e.t < 0) return;
    const p = e.t / e.life, fade = 1 - p, [sx, sy] = w2s(e.x, e.y), U = 62.2, V = 31.1;       // pixels per world unit along the ellipse's axes
    g.save(); g.lineCap = 'round'; g.lineJoin = 'round';
    if (e.kind === 'skNova') {
      const k = 1 - Math.pow(1 - Math.min(1, p * 1.6), 3), rx = U * e.r * k, ry = V * e.r * k, style = e.style;
      g.globalAlpha = fade * .3; g.fillStyle = e.glow; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill();
      const gr = g.createRadialGradient(sx, sy, 2, sx, sy, Math.max(4, rx)); gr.addColorStop(0, e.glow + '00'); gr.addColorStop(.7, e.glow + '44'); gr.addColorStop(1, e.glow + 'aa');
      g.globalCompositeOperation = 'lighter'; g.globalAlpha = fade; g.fillStyle = gr; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'source-over';
      const ring = () => { g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); };
      layers(g, [[22, OUTLINE, .3, 0], [16, e.glow, .5, 1], [8, e.core, .95, 0], [3, '#ffffff', 1, 0]], fade, p * .5, ring);
      if (style === 'spiral') {       // whirling arms: whirlwind, cyclone blades, arcane storm
        for (let arm = 0; arm < 4; arm++) layers(g, [[10, OUTLINE, .3, 0], [6, e.core, .9, 0], [2.5, '#ffffff', 1, 0]], fade, 0, () => {
          g.beginPath(); const a0 = e.t * 11 + arm * 1.571;
          for (let i = 0; i <= 14; i++) { const an = a0 + i * .09, f = k * (.35 + i * .045); i ? g.lineTo(sx + Math.cos(an) * rx * f, sy + Math.sin(an) * ry * f) : g.moveTo(sx + Math.cos(an) * rx * f, sy + Math.sin(an) * ry * f); }
        });
      } else if (style === 'cracks') {   // the ground splits: groundslam, earthshatter, titan's wrath
        layers(g, [[9, '#2a1408', .8, 0], [4, e.glow, .95, 1], [1.8, '#ffffff', 1, 0]], Math.min(1, fade * 1.6), 0, () => {
          g.beginPath(); for (const c of e.cracks) { const len = Math.min(1, k * 1.1) * c.len; let px = sx, py = sy; g.moveTo(px, py); for (const [f, o] of c.zig) { if (f > len) break; const an = c.a + o; px = sx + Math.cos(an) * rx * f, py = sy + Math.sin(an) * ry * f; g.lineTo(px, py); } }
        });
      } else {
        g.globalAlpha = fade * .7; g.strokeStyle = e.core; g.lineWidth = 2;
        for (let i = 0; i < 18; i++) { const an = i * 6.283 / 18 + e.a, r0 = .55 * k, r1 = k * 1.08; g.beginPath(); g.moveTo(sx + Math.cos(an) * rx * r0, sy + Math.sin(an) * ry * r0); g.lineTo(sx + Math.cos(an) * rx * r1, sy + Math.sin(an) * ry * r1); g.stroke(); }
      }
      if (e.stars) for (const st of e.stars) {         // starfall: stars drop across the whole area
        const q = (e.t - st.delay) / .3; if (q < 0 || q > 1.6) continue;
        const [qx, qy] = w2s(st.x, st.y), fall = Math.min(1, q);
        if (q <= 1) { const hx = qx + 140 * (1 - fall), hy = qy - 420 * (1 - fall) - 4; layers(g, [[12, OUTLINE, .3, 0], [8, e.glow, .6, 1], [3.5, '#ffffff', 1, 0]], 1, 0, () => { g.beginPath(); g.moveTo(hx + 70, hy - 210); g.lineTo(hx, hy); }); g.fillStyle = '#ffffff'; g.globalAlpha = 1; g.beginPath(); g.arc(hx, hy, 7, 0, 6.283); g.fill(); }
        else { const f2 = 1 - (q - 1) / .6; g.globalAlpha = f2; g.fillStyle = e.core; g.beginPath(); g.ellipse(qx, qy, 36 * (2 - f2), 17 * (2 - f2), 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'lighter'; g.fillStyle = e.glow; g.beginPath(); g.ellipse(qx, qy, 52 * (2 - f2), 24 * (2 - f2), 0, 0, 6.283); g.fill(); g.globalCompositeOperation = 'source-over'; }
      }
    } else if (e.kind === 'skCone') {
      const sweep = Math.min(1, p * 2.2), a0 = e.a - 1.9, a1 = a0 + 3.8 * sweep;
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
  // A glowing ring at the feet of anyone with an active buff, flickering when it is about to end.
  function drawBuffRings(g, who, t) {
    if (!who.buffs?.length || who.dead) return;
    const [sx, sy] = w2s(who.x, who.y);
    who.buffs.forEach((b, i) => {
      const col = BUFF_COL[b.kind] || '#ffffff', pulse = .55 + .25 * Math.sin(t * 4 + i * 1.7), ending = b.left < 1.5 && Math.floor(t * 8) % 2;
      g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = ending ? .2 : pulse * .75; g.strokeStyle = col; g.lineWidth = 3;
      g.beginPath(); g.ellipse(sx, sy, 34 + i * 8, 16 + i * 4, 0, 0, 6.283); g.stroke();
      g.globalAlpha = (ending ? .08 : .2) * pulse; g.fillStyle = col; g.fill(); g.restore();
    });
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
        inputT = .05;
        const [dx, dy] = paused || hero.sparkTravel ? [0, 0] : keyboardDirection();
        Online.send({ type: 'input', dx, dy });
        if (!paused && !hero.sparkTravel && pointer.down && !hero.target) Online.send({ type: 'move', x: pointer.x, y: pointer.y });
      }
      if (!paused && pendingNpc) {
        const {npc,until}=pendingNpc;
        if(hero.dead || tAll>until) {pendingNpc=null;cityRoute=[];Online.send({type:'stop'});}
        else if(Math.hypot(hero.x-npc.x,hero.y-npc.y)<=2.5) {pendingNpc=null;cityRoute=[];Online.send({type:'interact',npc:npc.id});}
        else if(npc.route && tAll-routeTime>1) {                       // a walker has moved on: take a fresh route to where it is now
          const end=cityRoute[cityRoute.length-1];
          if(!end || Math.hypot(end.x-npc.x,end.y-npc.y)>2.2) {cityRoute=routeTo(npc,true);routeTime=tAll;}
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
    for (const f of floaters) { f.t += dt; f.z += dt * 46; } floaters = floaters.filter(f => f.t < 1.1);
    for (const e of effects) e.t += dt; effects = effects.filter(e => e.t < (e.life ?? (e.kind === 'ring' ? .9 : .32)));
    if (marker) { marker.t += dt; if (marker.t > 1.2) marker = null; }
    const k = 1 - Math.pow(.0006, dt); cam.x += (hero.x - cam.x) * k; cam.y += (hero.y - cam.y) * k;
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
  let slimeSrc = null, beetleSrc = null, cragSrc = null, rimeSrc = null, fenSrc = null, wyrdSrc = null, vaultSrc = null, skySrc = null, deepSrc = null, astralSrc = null, cathedralSrc = null;    // {meta, img: {kind: Image}}
  const enemySource = s => CATHEDRAL_KINDS.includes(s.kind) ? cathedralSrc : s.kind === 'beetle' ? beetleSrc : CRAG_KINDS.includes(s.kind) ? cragSrc : RIME_KINDS.includes(s.kind) ? rimeSrc : FEN_KINDS.includes(s.kind) ? fenSrc : WYRD_KINDS.includes(s.kind) ? wyrdSrc : SKY_KINDS.includes(s.kind) ? skySrc : DEEP_KINDS.includes(s.kind) ? deepSrc : ASTRAL_KINDS.includes(s.kind) ? astralSrc : VAULT_KINDS.includes(s.kind) ? vaultSrc : slimeSrc;
  const SLIME_K = 2.1, DIE_SHOW = 1.7;                      // sprite pixel -> screen px; seconds a dead slime stays on screen
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
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); cragSrc = { meta, img }; })).catch(() => { cragSrc = null; });
  }
  // Gloamfen monsters: assets/fen_<kind>.png (scripts/make_fen_sprites.py), the same clips again.
  function loadFenSprites() {
    if (fenSrc) return;
    if (stubOn()) { fenSrc = stubEnemies(FEN_KINDS, { toad: '#7c4', croc: '#5a3', knight: '#8ca', hydra: '#a6c', gloomroot: '#4fa' }); return; }
    fetch('assets/fen.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/fen_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); fenSrc = { meta, img }; })).catch(() => { fenSrc = null; });
  }
  // Undervault monsters: assets/vault_<kind>.png (scripts/make_vault_sprites.py), the same clips again. Until an atlas loads
  // (or when none exists) enemySource is null and the procedural slime body is drawn.
  function loadVaultSprites() {
    if (vaultSrc) return;
    if (stubOn()) { vaultSrc = stubEnemies(VAULT_KINDS, { thrall: '#cba', archer: '#dc8', acolyte: '#a7f', gatewarden: '#fd8', choir: '#8df', colossus: '#9cf', hollowking: '#9f8' }); return; }
    fetch('assets/vault.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/vault_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); vaultSrc = { meta, img }; })).catch(() => { vaultSrc = null; });
  }
  // Wyrdwood monsters: assets/wyrd_<kind>.png (scripts/make_wyrd_sprites.py), the same clips again.
  function loadWyrdSprites() {
    if (wyrdSrc) return;
    if (stubOn()) { wyrdSrc = stubEnemies(WYRD_KINDS, { boar: '#a64', crow: '#446', troll: '#6a5', weaver: '#a6e', ram: '#9cf', oakhorn: '#e83', hrungnir: '#8af' }); return; }
    fetch('assets/wyrd.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/wyrd_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); wyrdSrc = { meta, img }; })).catch(() => { wyrdSrc = null; });
  }
  // Bifrost Reach monsters: assets/sky_<kind>.png (scripts/make_sky_sprites.py), the same clips again.
  function loadSkySprites() {
    if (skySrc) return;
    if (stubOn()) { skySrc = stubEnemies(SKY_KINDS, { galehound: '#9bd', prismgolem: '#a9f', skyray: '#58c', einherjar: '#8cd', thunderroc: '#fc6' }); return; }
    fetch('assets/sky.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/sky_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); skySrc = { meta, img }; })).catch(() => { skySrc = null; });
  }
  // Ran's Deep monsters: assets/deep_<kind>.png (scripts/make_deep_sprites.py), the same clips again.
  function loadDeepSprites() {
    if (deepSrc) return;
    if (stubOn()) { deepSrc = stubEnemies(DEEP_KINDS, { draugr: '#6aa', angler: '#7fe', moray: '#bd5', siren: '#e8d', shellback: '#7a8', kraken: '#a7e', hvitserk: '#cb4', ghostmaw: '#dff' }); return; }
    fetch('assets/deep.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/deep_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); deepSrc = { meta, img }; })).catch(() => { deepSrc = null; });
  }
  function loadAstralSprites() {
    if (astralSrc) return;
    if (stubOn()) { astralSrc = stubEnemies(ASTRAL_KINDS, { voidmoth: '#a8f', crystalwyrm: '#6ef', orbitbeetle: '#fa4', eclipsedryad: '#8d6', meteorgolem: '#b9f' }); return; }
    fetch('assets/astral.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/astral_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); astralSrc = { meta, img }; })).catch(() => { astralSrc = null; });
  }
  // Rimeveil Glacier monsters: assets/rime_<kind>.png (scripts/make_rime_sprites.py), the same clips as the Crags.
  function loadRimeSprites() {
    if (rimeSrc) return;
    if (stubOn()) { rimeSrc = stubEnemies(RIME_KINDS, { crab: '#6bd', wolf: '#cde', yeti: '#fff', wyrm: '#4ae' }); return; }
    fetch('assets/rime.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/rime_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); rimeSrc = { meta, img }; })).catch(() => { rimeSrc = null; });
  }
  function loadCathedralSprites() {
    if (cathedralSrc) return;
    if (stubOn()) { cathedralSrc = stubEnemies(CATHEDRAL_KINDS,Object.fromEntries(CATHEDRAL_ENEMIES.map(e => [e.kind,e.color]))); return; }
    fetch('assets/cathedral.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res,rej) => {
      const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=`assets/cathedral_${k}.png`;
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
    if (h.dead) g.globalAlpha = clamp((3.2 - h.deadT) / .6, 0, 1);
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
    const river = zdef.theme === 'wyrd';
    pass(1.36, river ? '#3c2c1c' : '#2c2a1c');
    pass(1.2, river ? '#6a7a3a' : '#3c5a30');
    pass(1.04, o => river ? `hsl(${200 + shimmer(o) * 8}, 46%, ${30 + shimmer(o) * 5}%)` : `hsl(${176 + shimmer(o) * 8}, 34%, ${14 + shimmer(o) * 3}%)`);
    pass(.8, o => river ? `hsl(${206 + shimmer(o) * 10}, 52%, ${24 + shimmer(o) * 5}%)` : `hsl(${184 + shimmer(o) * 10}, 40%, ${10 + shimmer(o) * 3}%)`);
    for (const [o, sx, sy] of rows) {
      const k = (o.x * 7 + o.y * 13) | 0;
      if (k % 3 === 0) {                                                            // an expanding ripple ring
        const ph = (t * .35 + (k % 7) * .13) % 1; g.strokeStyle = `rgba(150,210,210,${.38 * (1 - ph)})`; g.lineWidth = 1.4; g.beginPath(); g.ellipse(sx + Math.sin(k) * 10, sy + Math.cos(k) * 4, 6 + ph * 26, 2.6 + ph * 11, 0, 0, 6.283); g.stroke();
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
    if (zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme)) { g.fillStyle = '#03040a'; g.fillRect(0, 0, VW, VH); return; }
    if (zdef.theme === 'ember') return drawSkyEmber(g, t);
    if (zdef.theme === 'frost') return drawSkyFrost(g, t);
    if (zdef.theme === 'fen') return drawSkyFen(g, t);
    if (zdef.theme === 'wyrd') return drawSkyWyrd(g, t);
    if (zdef.theme === 'sky') return drawSkySky(g, t);
    if (zdef.theme === 'astral') return drawSkyAstral(g, t);
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
  // A gate: two stone posts, a lintel and a swirling plane between them. The server owns the actual move.
  function drawPortal(g, p, sx, sy, t) {
    if (p.look === 'cathedral') return CathedralArt.portal(g,p,sx,sy,t,ZONES[p.to] || zdef);
    if (p.look === 'stairs_down') { const d = ZONES[p.to]; return VaultArt.stairsDown(g, sx, sy, t, d?.min_level ? `Stairs to ${d.name} · Lv ${d.min_level}+` : 'Stairs down'); }
    if (p.look === 'stairs_up') return VaultArt.stairsUp(g, sx, sy, t);
    if (p.look === 'exit') return VaultArt.exitPortal(g, sx, sy, t, t - clearedAt);
    if (p.look === 'maelstrom') { const d = ZONES[p.to]; return DeepArt.maelstrom(g, sx, sy, t, d?.levels ? `${d.name} · Lv ${d.levels[0]}–${d.levels[1]}` : d?.name || 'The Maelstrom', zdef.theme === 'deep'); }
    const dest = ZONES[p.to] || ZONES[0], warm = dest.theme === 'ember', cold = dest.theme === 'frost', bog = dest.theme === 'fen', gold = dest.theme === 'city', leaf = dest.theme === 'wyrd', dsky = dest.theme === 'sky', astral = dest.theme === 'astral';
    const hue = astral ? 268 : dsky ? 215 : warm ? 18 : cold ? 195 : bog ? 88 : gold ? 44 : leaf ? 28 : 165, half = 1.5;
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
  function shadow(g, x, y, rx, ry, a = .28) { const [sx, sy] = w2s(x, y); g.fillStyle = `rgba(20,30,10,${a})`; g.beginPath(); g.ellipse(sx, sy, rx, ry, 0, 0, 6.283); g.fill(); }
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
    if (zdef.theme === 'fen' || zdef.theme === 'wyrd') drawWater(g, t);
    if (zdef.theme === 'wyrd') drawBridges(g, t);
    if (zdef.theme === 'sky') drawWardRings(g, t);
    if (zdef.theme === 'deep') drawChimeRings(g, t);
    // ground decals: splats, target marker, slash, shadows
    for (const who of [hero, ...remotePlayers.values()]) drawBuffRings(g, who, t);
    for (const e of effects) if (e.kind === 'splat') { const [sx, sy] = w2s(e.x, e.y), a = clamp(1 - (e.t - 3) / 3, 0, 1) * .5; g.fillStyle = e.col; g.globalAlpha = a; g.beginPath(); g.ellipse(sx, sy, 26 * e.s, 12 * e.s, 0, 0, 6.283); g.fill(); g.globalAlpha = 1; }
    if (marker) { const [sx, sy] = w2s(marker.x, marker.y), p = (marker.t * 2) % 1; g.strokeStyle = `rgba(255,236,150,${1 - p * .6})`; g.lineWidth = 3; g.beginPath(); g.ellipse(sx, sy, 10 + p * 12, 5 + p * 6, 0, 0, 6.283); g.stroke(); }
    // build the depth-sorted list of everything standing on the ground
    const list = [], onScreen = (sx, sy, m) => sx > -m && sx < VW + m && sy > -m * 1.6 && sy < VH + m * 1.6;
    const set = spriteSet();
    for (const o of objects) {
      if (o.kind === 'lava' || o.kind === 'water' || o.kind === 'post' || o.kind === 'void') continue;
      const [sx, sy] = w2s(o.x, o.y);
      if (onScreen(sx, sy, 200)) { list.push({ d: o.x + o.y, o, sx, sy }); if (o.kind === 'tree' || o.kind === 'pine') shadow(g, o.x, o.y, 46, 17, .22); else if (o.kind === 'bush') shadow(g, o.x, o.y, 30, 10, .22); else if (set[o.kind] || (zdef.theme === 'wyrd' && ['rock', 'spire', 'crag', 'elderash', 'ribcage', 'gallows'].includes(o.kind))) shadow(g, o.x, o.y, 26, 9, .25); }
    }
    for (const portal of zdef.portals) { if (portal.after_clear && !instanceCleared) continue; const [sx, sy] = w2s(portal.x, portal.y); if (onScreen(sx, sy, 220)) list.push({ d: portal.x + portal.y + (portal.look ? .3 : 0), portal, sx, sy }); }
    const escorted = id => { for (const r of remotePlayers.values()) if (r.escort && r.escort.npc === id && r.escort.owner === Online.id) return true; return false; };   // a stranded person walks with their rescuer
    for (const n of City.npcs) { if (n.escort && escorted(n.id)) continue; const [sx,sy]=w2s(n.x,n.y); if(onScreen(sx,sy,150)) list.push({d:n.x+n.y,npc:n,sx,sy}); }
    for (const s of slimes) if (!s.dead || (enemySource(s) && s.dieT < DIE_SHOW)) { const [sx, sy] = w2s(s.x, s.y); if (onScreen(sx, sy, 100)) { shadow(g, s.x, s.y, 28 * s.d.scale * (1 - s.hop * .12), 11 * s.d.scale, s.dead ? .3 * clamp(1 - (s.dieT - .5) / .6, 0, 1) : .3); list.push({ d: s.x + s.y, s, sx, sy }); } }
    for (const d of drops) { const [sx, sy] = w2s(d.x, d.y); if (onScreen(sx, sy, 60)) list.push({ d: d.x + d.y, drop: d, sx, sy }); }
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
          const cover=['house','chapel','gate','tent','tower','rampart','meetingstone','grandfountain','vaultwall','pillar','cathedralwall','cathedralcolumn','tree','pine','elderash','ribcage','gallows','skypine','prism','column','spirelight','pylon','hallgate','wardstone','windcairn','nacrehouse','nacrecathedral','nacrepalace','nacrearchive','nacreinn','nacrefountain','reefwall','tidebell','sunkencolumn','shiprib','coral','vent'].includes(o.kind) && it.d>hd && Math.abs(it.sx-hsx)<150 && hsy>it.sy-300 && hsy<it.sy+65;
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
        g.save(); g.translate(it.sx + (d.item ? 12 : -8), it.sy - d.z); g.fillStyle = d.col; g.strokeStyle = OL; g.lineWidth = 2.4;
        if (item && item.rarity !== 'common') { g.shadowColor = d.col; g.shadowBlur = 12; }
        g.beginPath();
        if (d.item) { g.moveTo(0,-12); g.lineTo(10,-2); g.lineTo(0,8); g.lineTo(-10,-2); g.closePath(); }
        else { g.moveTo(0, -9); g.bezierCurveTo(8, -1, 8, 6, 0, 6); g.bezierCurveTo(-8, 6, -8, -1, 0, -9); }
        g.fill(); g.stroke(); g.shadowBlur = 0;
        if (item?.class) { g.fillStyle = '#112b49'; g.font = 'bold 12px sans-serif'; g.textAlign = 'center'; g.fillText(item.kind === 'weapon' ? '⚔' : '◆', 0, 3); }
        else { g.fillStyle = 'rgba(255,255,255,.7)'; g.beginPath(); g.arc(-2.4, -1, 1.8, 0, 6.283); g.fill(); }
        g.restore();
      } else if (it.remote) {
        const remote = it.remote; g.save(); g.translate(it.sx, it.sy);
        if (remote.sparkTravel) Spark.draw(g,remote,t);
        else if (remote.sprite) remote.sprite.draw(g, remote, t);
        else { g.fillStyle = '#cfb5fa'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
        g.font = '18px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#151c35'; g.fillStyle = remote.escort ? '#ffd24a' : window.Social?.isPartyMember(remote.id) ? '#9dffb2' : '#fff4ca';
        const nameText = remote.escort ? remote.look.name + ' · Escort' : remote.look.name;
        g.strokeText(nameText, 0, -128); g.fillText(nameText, 0, -128);
        g.fillStyle = '#16263dcc'; g.fillRect(-25, -116, 50, 5); g.fillStyle = remote.escort ? '#ffcf5a' : '#8ee7a5'; g.fillRect(-25, -116, 50 * remote.hp / remote.maxHp, 5);
        g.restore();
      } else if (it.hero) { g.save(); g.translate(it.sx, it.sy); if (hero.sparkTravel) Spark.draw(g,hero,t); else if (isModular()) {
        if (mageSpr) mageSpr.draw(g, hero, t);
        else { g.fillStyle = '#8acfff'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
      } else { if (!warSpr && hero.hurtT > 0 && Math.floor(hero.hurtT * 40) % 2) g.globalAlpha = .6; if (warSpr) drawWarriorSprite(g, hero, t); else if (heroSpr) drawHeroSprite(g, hero, t); else { g.scale(1.3, 1.3); drawHero(g, hero, t); } } g.restore(); }
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
    } else if (e.kind === 'ring') {
      if (e.t < 0) continue;
      const p = e.t / (e.life ?? .9), [sx, sy] = w2s(e.x, e.y), m = e.grow || 1;
      if (e.col) { g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = 1 - p; g.strokeStyle = e.col; } else g.strokeStyle = `rgba(255,224,102,${1 - p})`;
      g.lineWidth = 6 * (1 - p) + 1; g.beginPath(); g.ellipse(sx, sy, 30 + p * 120 * m, 14 + p * 56 * m, 0, 0, 6.283); g.stroke(); if (e.col) g.restore();
    }
    for (const e of effects) if (e.kind === 'luPillar' || e.kind === 'luRays') drawLevelFx(g, e); else if (e.kind.startsWith('sk')) drawSkillFx(g, e);
    for (const b of bolts) {
      const [sx, sy] = w2s(b.x, b.y, 42), [tx, ty] = w2s(b.x - b.fx * .45, b.y - b.fy * .45, 42);
      const w = b.size || 9;
      g.save(); g.strokeStyle = b.col; g.lineWidth = w; g.lineCap = 'round'; g.globalAlpha = .65;
      g.beginPath(); g.moveTo(tx, ty); g.lineTo(sx, sy); g.stroke();
      if (w >= 14) { g.globalAlpha = .35; g.fillStyle = b.col; g.beginPath(); g.arc(sx, sy, w * 1.2, 0, Math.PI * 2); g.fill(); }
      g.globalAlpha = 1; g.fillStyle = '#f3fcff'; g.beginPath(); g.arc(sx, sy, Math.max(3, w * .55), 0, Math.PI * 2); g.fill(); g.restore();
    }
    for (const e of effects) if (e.kind === 'slam') {                  // a boss's ground-pound: a ring racing out to the edge of its reach, over a flash of dust
      const p = e.t / e.life, [sx, sy] = w2s(e.x, e.y), R = Math.max(.2, p) * e.r;
      g.save(); g.globalAlpha = (1 - p) * .9; g.strokeStyle = '#ffd9a0'; g.lineWidth = 7 * (1 - p) + 2; g.beginPath(); g.ellipse(sx, sy, R * 62.225, R * 31.112, 0, 0, 6.283); g.stroke();
      g.globalAlpha = (1 - p) * .25; g.fillStyle = '#e8d0a0'; g.beginPath(); g.ellipse(sx, sy, R * 62.225, R * 31.112, 0, 0, 6.283); g.fill(); g.restore();
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
    for (const f of floaters) { const [sx, sy] = w2s(f.x, f.y, f.z + 30); g.globalAlpha = clamp(1.4 - f.t * 1.3, 0, 1); g.font = `${f.big ? 34 : 24}px "Lilita One", "Jua", Impact, sans-serif`; g.textAlign = 'center'; g.lineWidth = 5; g.strokeStyle = 'rgba(20,10,30,.9)'; g.strokeText(f.text, sx, sy); g.fillStyle = f.color; g.fillText(f.text, sx, sy); } g.globalAlpha = 1;
    if (zdef.theme === 'frost') drawSnowfall(g, t);
    if (zdef.theme === 'fen') drawFireflies(g, t);
    if (zdef.theme === 'wyrd') drawWyrdWeather(g, t);
    if (zdef.theme === 'sky') drawSkyWeather(g, t);
    if (zdef.theme === 'deep' || zdef.theme === 'nacre') drawDeepWeather(g, t);
    if (zdef.theme === 'city') drawBlossom(g, t);
    if (CathedralArt.isTheme(zdef.theme)) CathedralArt.weather(g,zdef.theme,t,VW,VH);
    if (zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme)) { drawDarkness(g, t); drawBossBar(g); }
    drawMini();
  }
  // ---------- the Undervault's darkness and its boss bar ----------
  // The vault has no sky: a dark veil covers the screen and every light cuts a pool out of it (the hero, torches, braziers, the
  // stairs and the exit, missiles in flight).
  let darkCv = null, darkG = null;
  function drawDarkness(g, t) {
    if (!darkCv) { darkCv = document.createElement('canvas'); darkCv.width = VW; darkCv.height = VH; darkG = darkCv.getContext('2d'); }
    const d = darkG; d.globalCompositeOperation = 'source-over'; d.clearRect(0, 0, VW, VH); d.fillStyle = CathedralArt.isTheme(zdef.theme) ? 'rgba(3,9,24,.56)' : 'rgba(3,4,10,.84)'; d.fillRect(0, 0, VW, VH);
    d.globalCompositeOperation = 'destination-out';
    const pool = (x, y, r, a) => {
      if (x < -r || x > VW + r || y < -r || y > VH + r) return;
      const gr = d.createRadialGradient(x, y, r * .06, x, y, r); gr.addColorStop(0, `rgba(0,0,0,${a})`); gr.addColorStop(.5, `rgba(0,0,0,${a * .62})`); gr.addColorStop(1, 'rgba(0,0,0,0)');
      d.fillStyle = gr; d.beginPath(); d.ellipse(x, y, r, r * .6, 0, 0, 6.283); d.fill();
    };
    const [hx, hy] = w2s(hero.x, hero.y); pool(hx, hy - 36, 540, .97);
    for (const o of objects) {
      if (o.kind !== 'brazier' && o.kind !== 'torch' && o.kind !== 'cathedrallamp') continue;
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
    g.fillStyle = '#fff4ca'; g.font = '13px "Jua", sans-serif'; g.fillText(`${Math.ceil(boss.hp).toLocaleString('en')} / ${Math.round(boss.maxHp).toLocaleString('en')}`, VW / 2, y + 20);
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
    const [c, g] = canvasOf(144, 144, 1), k = 144 / MAP, ember = zdef.theme === 'ember', frost = zdef.theme === 'frost', fen = zdef.theme === 'fen', city = zdef.theme === 'city', vault = zdef.theme === 'vault' || CathedralArt.isTheme(zdef.theme), wyrd = zdef.theme === 'wyrd', sky = zdef.theme === 'sky', astral = zdef.theme === 'astral', deep = zdef.theme === 'deep' || zdef.theme === 'nacre';
    g.fillStyle = CathedralArt.isTheme(zdef.theme) ? '#080e20' : deep ? '#0b3550' : sky ? '#1a1838' : astral ? '#39776f' : vault ? '#07080e' : city ? '#5f9b4a' : wyrd ? '#6a5430' : fen ? '#2f4a2c' : frost ? '#cfe3f0' : ember ? '#2b1f22' : '#3f9b48'; g.fillRect(0, 0, 144, 144);
    if (sky) { for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.floor[y * MAP + x]) { g.fillStyle = map.dirt[y * MAP + x] ? '#f0c8f4' : '#8ad4b8'; g.fillRect(x * k, y * k, k + .5, k + .5); } }
    else for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.dirt[y * MAP + x]) { g.fillStyle = CathedralArt.isTheme(zdef.theme) ? CathedralArt.style(zdef.theme).left : deep ? '#c8c29a' : vault ? '#3a3f55' : city ? (map.dirt[y * MAP + x] === 2 ? '#ece2c8' : map.dirt[y * MAP + x] === 3 ? '#b8765a' : '#b6a98c') : astral ? '#d7bc84' : wyrd ? '#b89860' : fen ? '#8a6a40' : frost ? '#9fb7cc' : ember ? '#6a5040' : '#c9a26a'; g.fillRect(x * k, y * k, k + .5, k + .5); }
    if (wyrd) { const gr = g.createLinearGradient(0, 0, 0, 144); gr.addColorStop(0, 'rgba(120,128,92,.95)'); gr.addColorStop(.42, 'rgba(120,128,92,.9)'); gr.addColorStop(.56, 'rgba(120,128,92,0)'); g.fillStyle = gr; g.fillRect(0, 0, 144, 144); for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.dirt[y * MAP + x]) { g.fillStyle = '#c4b290'; if (y < MAP * .5) g.fillRect(x * k, y * k, k + .5, k + .5); } }
    if (zdef.city && !city && zdef.theme !== 'nacre') for (const c of [zdef.city, ...(zdef.camps || [])]) {
      g.fillStyle=deep ? '#4a7a82' : sky ? '#cdd2f2' : astral ? '#8fa9b2' : wyrd ? '#8a6a44' : fen ? '#6a5238' : frost ? '#8fa6bd' : ember ? '#88705d' : '#d8cbb0'; g.fillRect(c.x0*k,c.y0*k,(c.x1-c.x0)*k,(c.y1-c.y0)*k);
      g.fillStyle=wyrd ? '#ffd9a0' : fen ? '#ffe08a' : frost ? '#ffd27a' : ember ? '#ffb65c' : '#68bcc6'; g.beginPath();g.arc(c.plaza.x*k,c.plaza.y*k,3,0,Math.PI*2);g.fill();
    }
    for (const o of objects) {
      if (o.kind === 'post' || o.kind === 'void') continue;
      if (astral) { g.fillStyle = o.kind === 'crystal' || o.kind === 'obelisk' ? '#a4e9e3' : o.kind === 'astraltree' ? '#244f64' : o.kind === 'starstone' ? '#637994' : o.kind === 'astrolamp' ? '#ffe2a0' : o.kind === 'starbloom' ? '#d8afe9' : '#5eaa91'; g.fillRect(o.x * k - .55, o.y * k - .55, 1.1, 1.1); continue; }
      if (vault) { if (o.kind === 'brazier' || o.kind === 'cathedrallamp') { g.fillStyle = '#ff9a3a'; g.fillRect(o.x * k - 1, o.y * k - 1, 2, 2); } continue; }
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
      g.fillStyle = o.kind === 'lava' ? '#ff6a2a' : o.kind === 'ice' ? '#4f93c8' : o.kind === 'water' ? (wyrd ? '#2f6f9a' : '#244f5c') : o.kind === 'crag' ? '#4a4a58' : o.kind === 'pine' ? '#1f4a3a' : o.kind === 'beacon' ? '#ff9a2e' : o.kind === 'gallows' || o.kind === 'ribcage' ? '#d8d0b8' : o.kind === 'elderash' ? '#8a5a2a' : o.kind === 'thicket' ? '#6a2f58' : o.kind === 'tree' ? (wyrd ? '#a8451e' : fen ? '#1b4a2a' : frost ? '#1f5a52' : ember ? '#150f13' : '#1f6b3a') : o.kind === 'spire' ? (wyrd ? '#d8d8c8' : fen ? '#b8c0b0' : frost ? '#8ccdf0' : '#4b3b5e') : o.kind === 'rock' ? (wyrd ? '#7a7a80' : fen ? '#6b7a68' : frost ? '#7f93aa' : ember ? '#6a6672' : '#8a93a8') : (fen ? '#3f6a35' : frost ? '#3a7a70' : ember ? '#5a3a30' : '#2f8a45');
      g.beginPath(); g.arc(o.x * k, o.y * k, o.kind === 'lava' ? 2.2 : o.kind === 'water' ? 1.6 : o.kind === 'ice' || o.kind === 'thicket' ? 1.7 : o.kind === 'tree' ? 2.1 : 1.2, 0, 6.283); g.fill();
    }
    for (const p of zdef.portals) { if (p.after_clear && !instanceCleared) continue; g.strokeStyle = ZONES[p.to]?.theme === 'ember' ? '#ff8a3a' : ZONES[p.to]?.theme === 'frost' ? '#8fd8ff' : ZONES[p.to]?.theme === 'fen' ? '#b8e060' : ZONES[p.to]?.theme === 'wyrd' ? '#e0963a' : ZONES[p.to]?.theme === 'sky' ? '#9fc4ff' : ['deep','nacre'].includes(ZONES[p.to]?.theme) ? '#4fe0e8' : ZONES[p.to]?.theme === 'city' ? '#ffd36a' : '#7ae8c8'; g.lineWidth = 2; g.beginPath(); g.arc(p.x * k, p.y * k, 4, 0, 6.283); g.stroke(); }
    miniBase = c;
  }
  function drawMini() {
    if (!mctx || !miniBase) return;
    const s = mini.width / MAP; mctx.clearRect(0, 0, mini.width, mini.height); mctx.drawImage(miniBase, 0, 0, mini.width, mini.height);
    paintFog(mctx, mini.width, mini.height, zone);
    for (const n of City.npcs) { if (!seen(zone, n.x, n.y)) continue; mctx.fillStyle='#f5d477';mctx.fillRect(n.x*s-1,n.y*s-1,2,2); }
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
      loadBeetleSprites(); loadCragSprites(); loadRimeSprites(); loadFenSprites(); loadWyrdSprites(); loadSkySprites(); loadDeepSprites(); loadAstralSprites(); loadVaultSprites(); loadCathedralSprites();
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
    clearInput() { pendingNpc=null; cityRoute=[]; keys?.clear(); if (pointer) pointer.down = false; },
    setPaused(p) { paused = p; if(p){pendingNpc=null;cityRoute=[];} Field.clearInput(); Online.send({ type: 'stop' }); },
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
    floatHero(text, color = '#ffe066') { if (running && !hero.dead) floater(hero.x, hero.y, text, color, false); },
    equipSlot(slot, item) {
      if (!running || !Online.connected || hero.dead) return false;
      return Online.send({ type: 'equip', slots: { [slot]: item } });
    },
    get remotePlayers() { return [...remotePlayers.values()]; },
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
    get equipmentStats() { return equipmentStats(); },
    get warriorSprites() { return !isMage() && !isAssassin() && !isPriest() && !isHunter() ? mageSpr : null; },
    get mageSprites() { return isMage() ? mageSpr : null; },
    get assassinSprites() { return isAssassin() ? mageSpr : null; },
    get priestSprites() { return isPriest() ? mageSpr : null; },
    get hunterSprites() { return isHunter() ? mageSpr : null; },
    get hero() { return hero; }, get slimes() { return slimes; }, get meadowPaths() { return PATHS; },
    get explored() { return explored; }, fog: { grid: FOG, seen, paint: paintFog, cell: fogCell },
    get beetleSprites() { return beetleSrc; }, get cragSprites() { return cragSrc; }, get rimeSprites() { return rimeSrc; }, get fenSprites() { return fenSrc; }, get wyrdSprites() { return wyrdSrc; }, get skySprites() { return skySrc; }, get deepSprites() { return deepSrc; }, get astralSprites() { return astralSrc; }, get cathedralSprites() { return cathedralSrc; }, get vaultSprites() { return vaultSrc; },
    get zone() { return zone; }, get zoneName() { return zdef.name; }, get zoneTheme() { return zdef.theme; }, place: id => (zdef.places || []).find(p => p.id === id) || null,
    _debug: { get effects() { return effects; }, get ebolts() { return ebolts; }, get cleared() { return instanceCleared; }, event: networkEvent, get objects() { return objects; }, get zones() { return ZONES; }, w2s, s2w, routeTo, enemyFrame: s => slimeFrame(s, tAll) },
  };
  window.Field = Field;
})();
