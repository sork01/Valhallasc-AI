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
  const ZONES = [{ name: 'Greenmeadow', theme: 'meadow', size: WORLD_MAP.size, spawn: WORLD_MAP.spawn, objects: WORLD_MAP.objects, portals: WORLD_MAP.portals || [], paths: null, levels: null },
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
    const paths = zdef.paths || PATHS, ember = zdef.theme === 'ember';
    for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) {
      const i = y * MAP + x, cx = x + .5, cy = y + .5;
      map.tone[i] = vnoise(cx * .16, cy * .16, ember ? 11 : 1) * .65 + vnoise(cx * .55, cy * .55, ember ? 12 : 2) * .35;
      let d = 99; for (const p of paths) for (let k = 0; k < p.length - 1; k++) d = Math.min(d, segDist(cx, cy, p[k][0], p[k][1], p[k + 1][0], p[k + 1][1]));
      if (!ember) d = Math.min(d, Math.hypot(cx - 36, cy - 36) - 2.4);
      map.dirt[i] = d < 1.15 + vnoise(cx * .5, cy * .5, 3) * .6 ? 1 : 0;
    }
    objects = zdef.objects.map(o => ({ ...o }));
  }
  // Switch to another zone: new ground, obstacles and minimap. Everything tied to the old zone's coordinates goes.
  function setZone(z) {
    zone = ZONES[z] ? z : 0; zdef = ZONES[zone];
    buildMap(); chunks.clear();
    if (mini) buildMini();
    if (hero) { pendingNpc = null; cityRoute = []; hero.target = null; hero.goal = null; }
    floaters = []; parts = []; effects = []; bolts = []; drops = []; marker = null; slimes = []; remotePlayers.clear();
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
  function buildSprites() {
    for (let v = 0; v < 4; v++) {
      sprites.tree[v] = makeTree(v); sprites.bush[v] = makeBush(v); sprites.rock[v] = makeRock(v);
      emberSprites.tree[v] = makeCharTree(v); emberSprites.bush[v] = makeEmberBush(v); emberSprites.rock[v] = makeBasalt(v); emberSprites.spire[v] = makeSpire(v);
    }
  }
  const spriteSet = () => zdef.theme === 'ember' ? emberSprites : sprites;

  // ---------- ground chunks ----------
  const chunks = new Map(); let chunkScale = 1;
  const CLIFF = 120, PADX = 10, PADTOP = 40;
  function chunkGeom(cx, cy) { const x0 = cx * CH, y0 = cy * CH; return { x0, y0, ox: (x0 - (y0 + CH)) * TW / 2 - TW / 2 - PADX, oy: (x0 + y0) * TH / 2 - PADTOP, w: CH * TW + TW + PADX * 2, h: CH * TH + TH + PADTOP + CLIFF }; }
  function renderChunk(cx, cy) {
    const G = chunkGeom(cx, cy), [c, g] = canvasOf(G.w, G.h, chunkScale);
    const ember = zdef.theme === 'ember';
    for (let ty = 0; ty < CH; ty++) for (let tx = 0; tx < CH; tx++) {
      const x = G.x0 + tx, y = G.y0 + ty; if (x >= MAP || y >= MAP) continue;
      const i = y * MAP + x, px = (x - y) * TW / 2 - G.ox, py = (x + y) * TH / 2 - G.oy, tone = map.tone[i], dirt = map.dirt[i];
      const alt = ((x + y) & 1) ? 1.4 : -1.4, e = .7;
      g.fillStyle = ember ? (dirt ? `hsl(${22 + tone * 8}, ${20 + tone * 8}%, ${30 + tone * 8 + alt}%)` : `hsl(${12 + tone * 14}, ${10 + tone * 8}%, ${15 + tone * 11 + alt}%)`)
        : dirt ? `hsl(${30 + tone * 8}, ${38 + tone * 8}%, ${48 + tone * 8 + alt}%)` : `hsl(${100 + tone * 16}, ${46 + tone * 12}%, ${36 + tone * 12 + alt}%)`;
      g.beginPath(); g.moveTo(px, py - e); g.lineTo(px + TW / 2 + e, py + TH / 2); g.lineTo(px, py + TH + e); g.lineTo(px - TW / 2 - e, py + TH / 2); g.closePath(); g.fill();
      const r = rngf(x * 977 + y * 131 + 7), inTile = () => { const a = r() - .5, b = r() - .5; return [px + (a - b) * TW * .4, py + TH / 2 + (a + b) * TH * .4]; };
      if (ember) {
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
      if (zone === 0) City.stoneTile(g, px, py, x, y);
      // earth cliff on the two front edges of the island
      const depth = CLIFF - 34 + hash2(x, y, 9) * 26;
      const face = (dir) => {
        const vx = px + dir * TW / 2, vy = py + TH / 2, bx = px, by = py + TH;
        const gr = g.createLinearGradient(0, vy, 0, vy + depth);
        if (ember) { gr.addColorStop(0, dir > 0 ? '#4a3430' : '#3c2a28'); gr.addColorStop(1, dir > 0 ? '#1e1416' : '#181012'); }
        else { gr.addColorStop(0, dir > 0 ? '#7a5433' : '#684528'); gr.addColorStop(1, dir > 0 ? '#3d2a1c' : '#33221a'); }
        g.fillStyle = gr; g.beginPath(); g.moveTo(vx, vy); g.lineTo(bx, by); g.lineTo(bx, by + depth * (.85 + hash2(x + 3, y, 4) * .3)); g.lineTo(vx, vy + depth); g.closePath(); g.fill();
        g.strokeStyle = 'rgba(0,0,0,.18)'; g.lineWidth = 2; for (let k = 1; k < 4; k++) { g.beginPath(); g.moveTo(vx, vy + depth * k / 4); g.lineTo(bx, by + depth * k / 4 * .9); g.stroke(); }
        g.strokeStyle = ember ? '#8a3a1c' : '#3f8a3c'; g.lineWidth = 5; g.beginPath(); g.moveTo(vx, vy + 1); g.lineTo(bx, by + 1); g.stroke();
        if (ember) { g.strokeStyle = 'rgba(255,120,40,.55)'; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + 3); g.lineTo(bx, by + 3); g.stroke(); }
        g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.moveTo(vx, vy + depth); g.lineTo(bx, by + depth * .9); g.stroke();
      };
      if (x === MAP - 1) face(1);
      if (y === MAP - 1) face(-1);
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
  let mageSpr = null, spriteGeneration = 0;
  let pendingNpc = null, cityRoute = [], routeTime = 0;
  let remotePlayers = new Map(), onCharacter = () => {}, inputT = 0, lastLook = '';
  const isMage = () => hero?.look?.class === 'mage';
  const isAssassin = () => hero?.look?.class === 'assassin';
  const isModular = () => ['warrior', 'mage', 'assassin'].includes(hero?.look?.class || 'warrior');
  const characterClass = () => isMage() ? MageSprite : isAssassin() ? AssassinSprite : WarriorSprite;
  const mageGear = () => MageSprite.equipment(hero.look);
  const equipmentStats = () => {
    if (Number.isFinite(hero.attack) && Number.isFinite(hero.defense)) return { attack: hero.attack, defense: hero.defense };
    if (!isModular()) return { attack: 22 + hero.level * 4, defense: 0 };
    const C = characterClass(), gear = C.equipment(hero.look);
    const item = (kind, variant) => WORLD_ITEMS.find(i => i.class === hero.look.class && i.kind === kind && i.variant === variant);
    const extras = Object.values(hero.equipment || {}).map(id => WORLD_ITEMS.find(i => i.id === id)).filter(Boolean);
    return { attack: extras.reduce((sum, i) => sum + (i.attack || 0), 0) + (isAssassin() ? 18 : isMage() ? 20 : 22) + hero.level * 4 + (item('weapon', gear.weapon)?.attack || 0), defense: extras.reduce((sum, i) => sum + (i.defense || 0), 0) + (item('armor', gear.armor)?.defense || 0) };
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
  };
  const CRAG_KINDS = ['wisp', 'spider', 'wraith', 'golem'];
  // Colour a level label by how it compares with the hero: grey, normal, orange, red.
  const levelColor = level => { const d = level - (hero?.level || 1); return d >= 5 ? '#ff6b6b' : d >= 3 ? '#ffa65a' : d <= -5 ? '#9fb0a0' : '#fff4ca'; };
  function newHero() {
    return { x: SPAWN.x, y: SPAWN.y, r: .3, hp: 120, maxHp: 120, level: 1, xp: 0, gold: 0, kills: 0, fx: 1, fy: 1, moving: false, walk: 0, atkT: 0, atkCd: 0, atkHit: false, hurtT: 0, lastHurt: -99, dead: false, deadT: 0, target: null, goal: null, vx: 0, vy: 0, roar: 0, dashT: 0, dashCd: 0, dashX: 0, dashY: 0, dashTrail: 0 };
  }
  const xpNeed = lv => Math.round(160 * Math.pow(lv, 1.35));
  function reset() {
    pendingNpc = null; cityRoute = [];
    window.Quests?.reset();
    hero = newHero(); drops = []; floaters = []; parts = []; effects = []; bolts = []; marker = null; shake = 0; msg = null; hudT = 0; tAll = 0;
    keys = new Set(); pointer = { down: false, x: 0, y: 0 };
    cam = { x: hero.x, y: hero.y };
    slimes = []; emitHud(true);
  }
  function emitHud(force) { onHud({ hp: hero.hp, maxHp: hero.maxHp, xp: hero.xp, xpNeed: hero.xpNeed ?? xpNeed(hero.level), level: hero.level, gold: hero.gold, kills: hero.kills, msg, area: zone > 0 ? zdef.name : City.inside(hero.x, hero.y) ? WORLD_MAP.city.name : 'Greenmeadow', zone, levels: zdef.levels, buffs: hero.buffs || [], traveling: cityRoute.length > 0 && !pendingNpc }); }

  // ---------- coordinates ----------
  const camS = () => { const [x, y] = w2sRaw(cam.x, cam.y); return [Math.round(x), Math.round(y)]; };   // whole pixels: fractional offsets make big blits resample (slow)
  function w2s(x, y, z = 0) { const [cx, cy] = camS(), [sx, sy] = w2sRaw(x, y); return [sx - cx + VW / 2 + Math.round(shakeX), sy - cy + VH / 2 + Math.round(shakeY) - z]; }
  function s2w(sx, sy) { const [cx, cy] = camS(), rx = sx - VW / 2 + cx, ry = sy - VH / 2 + cy; return [rx / TW + ry / TH, ry / TH - rx / TW]; }
  let shakeX = 0, shakeY = 0;
  function pointerWorld(e) { const r = cv.getBoundingClientRect(); return s2w((e.clientX - r.left) / r.width * VW, (e.clientY - r.top) / r.height * VH); }

  // ---------- input ----------
  const KEYDIR = { w: [0, -1], arrowup: [0, -1], s: [0, 1], arrowdown: [0, 1], a: [-1, 0], arrowleft: [-1, 0], d: [1, 0], arrowright: [1, 0] };
  function onKeyDown(e) {
    if (e.defaultPrevented || !running || paused || !Online.connected || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName || '')) return;
    const k = e.key.toLowerCase();
    if (k === 'f' && !e.repeat && !hero.dead && zone === 0) {
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
    if (!running || paused || !Online.connected || hero.dead) return;
    pendingNpc = null; cityRoute = [];
    const r = cv.getBoundingClientRect(), mx=(e.clientX-r.left)/r.width*VW, my=(e.clientY-r.top)/r.height*VH;
    const npc = zone === 0 && City.npcs.find(n => { const [x,y]=w2s(n.x,n.y); return Math.abs(mx-x)<32 && my>y-105 && my<y+12; });
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
  function routeTo(goal, approach = false, origin = hero) {
    const free = (x,y) => x>=1 && y>=1 && x<MAP-1 && y<MAP-1 && objects.every(o => o.width ? Math.abs(x-o.x)>o.width/2+.55 || Math.abs(y-o.y)>o.depth/2+.55 : Math.hypot(x-o.x,y-o.y)>o.r+.55);
    const segmentFree = (a, b) => {
      const steps = Math.max(1, Math.ceil(Math.hypot(a.x-b.x,a.y-b.y) / .1));
      for (let i=0;i<=steps;i++) {
        const x=a.x+(b.x-a.x)*i/steps, y=a.y+(b.y-a.y)*i/steps;
        if(objects.some(o => o.width ? Math.abs(x-o.x)<o.width/2+.3-1e-6 && Math.abs(y-o.y)<o.depth/2+.3-1e-6 : Math.hypot(x-o.x,y-o.y)<o.r+.3-1e-6)) return false;
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
  const classSprite = look => look.class === 'mage' ? MageSprite : look.class === 'assassin' ? AssassinSprite : WarriorSprite;
  function applyActor(actor, packet, snap = false) {
    const x = actor.x, y = actor.y;
    Object.assign(actor, packet); actor.nx = packet.x; actor.ny = packet.y;
    if (!snap && Math.hypot(x - packet.x, y - packet.y) < 4) { actor.x = x; actor.y = y; }
  }
  function keepActorsSeparated() {
    const enemies = new Set(slimes);
    const actors = [hero, ...remotePlayers.values(), ...slimes].filter(actor => !actor.dead);
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
  function applySnapshot(packet, initial = false) {
    const own = packet.players.find(p => p.id === Online.id); if (!own) return;
    // The server decides the zone (a gate moved us); rebuild the ground and snap everything to the new place.
    const moved = (own.zone || 0) !== zone;
    if (moved) setZone(own.zone || 0);
    const inZone = a => (a.zone || 0) === zone;
    const selectedTarget = hero.target?.id;
    const wasDead = hero.dead;
    applyActor(hero, own, initial || moved);
    window.Attributes?.update(own);
    window.Inventory?.update(own.inventory || [], own.look, own.equipment || {}, own.bags || []);
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
      applyActor(remote, player, initial || moved);
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
  };
  const BUFF_COL = { damage: '#ff9a3a', shield: '#59a8ff', haste: '#ffe45a', dodge: '#b9a8ff', crit: '#ff5c7a' };
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
        const [dx, dy] = paused ? [0, 0] : keyboardDirection();
        Online.send({ type: 'input', dx, dy });
        if (!paused && pointer.down && !hero.target) Online.send({ type: 'move', x: pointer.x, y: pointer.y });
      }
      if (!paused && pendingNpc) {
        const {npc,until}=pendingNpc;
        if(hero.dead || tAll>until) {pendingNpc=null;cityRoute=[];Online.send({type:'stop'});}
        else if(Math.hypot(hero.x-npc.x,hero.y-npc.y)<=2.5) {pendingNpc=null;cityRoute=[];Online.send({type:'interact',npc:npc.id});}
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
  let slimeSrc = null, beetleSrc = null, cragSrc = null;    // {meta, img: {kind: Image}}
  const enemySource = s => s.kind === 'beetle' ? beetleSrc : CRAG_KINDS.includes(s.kind) ? cragSrc : slimeSrc;
  const SLIME_K = 2.1, DIE_SHOW = 1.7;                      // sprite pixel -> screen px; seconds a dead slime stays on screen
  function loadSlimeSprites(cfg) {
    if (slimeSrc) return;
    fetch(cfg.json).then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = cfg.png.replace('%k', k); })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); slimeSrc = { meta, img }; })).catch(() => { slimeSrc = null; });
  }
  function loadBeetleSprites() {
    if (beetleSrc) return;
    fetch('assets/ironhide.txt').then(r => r.json()).then(meta => new Promise((resolve, reject) => {
      const img = new Image(); img.onload = () => resolve({ meta, img: { beetle: img } });
      img.onerror = reject; img.src = 'assets/ironhide.png';
    })).then(src => { beetleSrc = src; }).catch(() => { beetleSrc = null; });
  }
  // Emberfall Crags monsters: one atlas per kind (assets/crags_<kind>.png, scripts/make_crag_sprites.py), the
  // same five clips and frame meanings as the Ironhide Beetle.
  function loadCragSprites() {
    if (cragSrc) return;
    fetch('assets/crags.txt').then(r => r.json()).then(meta => Promise.all(meta.kinds.map(k => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = `assets/crags_${k}.png`; })))
      .then(imgs => { const img = {}; meta.kinds.forEach((k, n) => img[k] = imgs[n]); cragSrc = { meta, img }; })).catch(() => { cragSrc = null; });
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
  function drawSky(g, t) {
    if (zdef.theme === 'ember') return drawSkyEmber(g, t);
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
    const dest = ZONES[p.to] || ZONES[0], warm = dest.theme === 'ember';
    const hue = warm ? 18 : 165, half = 1.5;
    const post = (u) => {                                    // an iso column centred u world units along x
      const px = sx + u * TW / 2, py = sy + u * TH / 2, w = 17, h = 112;
      g.fillStyle = 'rgba(0,0,0,.28)'; g.beginPath(); g.ellipse(px, py + 2, 30, 11, 0, 0, 6.283); g.fill();
      g.lineJoin = 'round'; g.lineWidth = 3; g.strokeStyle = OL;
      g.fillStyle = warm ? '#4a3b44' : '#8a8f9c'; g.beginPath(); g.moveTo(px - w, py - 4); g.lineTo(px, py + 8); g.lineTo(px, py + 8 - h); g.lineTo(px - w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = warm ? '#30262f' : '#6a6f7c'; g.beginPath(); g.moveTo(px + w, py - 4); g.lineTo(px, py + 8); g.lineTo(px, py + 8 - h); g.lineTo(px + w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = warm ? '#6a5663' : '#b9bdc8'; g.beginPath(); g.moveTo(px, py + 8 - h); g.lineTo(px + w, py - 4 - h); g.lineTo(px, py - 16 - h); g.lineTo(px - w, py - 4 - h); g.closePath(); g.fill(); g.stroke();
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
    if (zone === 0) City.drawPlaza(g, w2s);
    if (zdef.theme === 'ember') drawLava(g, t);
    // ground decals: splats, target marker, slash, shadows
    for (const who of [hero, ...remotePlayers.values()]) drawBuffRings(g, who, t);
    for (const e of effects) if (e.kind === 'splat') { const [sx, sy] = w2s(e.x, e.y), a = clamp(1 - (e.t - 3) / 3, 0, 1) * .5; g.fillStyle = e.col; g.globalAlpha = a; g.beginPath(); g.ellipse(sx, sy, 26 * e.s, 12 * e.s, 0, 0, 6.283); g.fill(); g.globalAlpha = 1; }
    if (marker) { const [sx, sy] = w2s(marker.x, marker.y), p = (marker.t * 2) % 1; g.strokeStyle = `rgba(255,236,150,${1 - p * .6})`; g.lineWidth = 3; g.beginPath(); g.ellipse(sx, sy, 10 + p * 12, 5 + p * 6, 0, 0, 6.283); g.stroke(); }
    // build the depth-sorted list of everything standing on the ground
    const list = [], onScreen = (sx, sy, m) => sx > -m && sx < VW + m && sy > -m * 1.6 && sy < VH + m * 1.6;
    const set = spriteSet();
    for (const o of objects) {
      if (o.kind === 'lava' || o.kind === 'post') continue;
      const [sx, sy] = w2s(o.x, o.y);
      if (onScreen(sx, sy, 200)) { list.push({ d: o.x + o.y, o, sx, sy }); if (o.kind === 'tree') shadow(g, o.x, o.y, 46, 17, .22); else if (o.kind === 'bush') shadow(g, o.x, o.y, 30, 10, .22); else if (set[o.kind]) shadow(g, o.x, o.y, 26, 9, .25); }
    }
    for (const portal of zdef.portals) { const [sx, sy] = w2s(portal.x, portal.y); if (onScreen(sx, sy, 220)) list.push({ d: portal.x + portal.y, portal, sx, sy }); }
    if (zone === 0) for (const n of City.npcs) { const [sx,sy]=w2s(n.x,n.y); if(onScreen(sx,sy,150)) list.push({d:n.x+n.y,npc:n,sx,sy}); }
    for (const s of slimes) if (!s.dead || (enemySource(s) && s.dieT < DIE_SHOW)) { const [sx, sy] = w2s(s.x, s.y); if (onScreen(sx, sy, 100)) { shadow(g, s.x, s.y, 28 * s.d.scale * (1 - s.hop * .12), 11 * s.d.scale, s.dead ? .3 * clamp(1 - (s.dieT - .5) / .6, 0, 1) : .3); list.push({ d: s.x + s.y, s, sx, sy }); } }
    for (const d of drops) { const [sx, sy] = w2s(d.x, d.y); if (onScreen(sx, sy, 60)) list.push({ d: d.x + d.y, drop: d, sx, sy }); }
    { const [sx, sy] = w2s(hero.x, hero.y); shadow(g, hero.x, hero.y, 30, 12, .32); list.push({ d: hero.x + hero.y + .001, hero, sx, sy }); }
    for (const remote of remotePlayers.values()) {
      const [sx, sy] = w2s(remote.x, remote.y);
      if (onScreen(sx, sy, 160)) { shadow(g, remote.x, remote.y, 30, 12, .28); list.push({ d: remote.x + remote.y + .001, remote, sx, sy }); }
    }
    list.sort((a, b) => a.d - b.d);
    const [hsx, hsy] = w2s(hero.x, hero.y), hd = hero.x + hero.y;
    for (const it of list) {
      if (it.o) {
        const o = it.o;
        if (!set[o.kind]) {
          const cover=['house','chapel','gate'].includes(o.kind) && it.d>hd && Math.abs(it.sx-hsx)<150 && hsy>it.sy-300 && hsy<it.sy+65;
          City.drawObject(g,o,it.sx,it.sy,cover ? .5 : 1);
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
          const label = `Lv ${s.level ?? '?'} ${s.d.name || s.kind}`;
          g.font = '16px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = OL; g.fillStyle = levelColor(s.level);
          g.strokeText(label, 0, barY - 8); g.fillText(label, 0, barY - 8);
        }
        if (!s.dead && hero.target === s) { g.strokeStyle = '#ffe066'; g.lineWidth = 2.5; g.beginPath(); g.ellipse(0, 2, 32 * s.d.scale, 13 * s.d.scale, 0, 0, 6.283); g.stroke(); }
        g.restore();
      } else if (it.drop) {
        const d = it.drop, item = WORLD_ITEMS.find(i => i.id === d.item);
        g.save(); g.translate(it.sx + (d.item ? 12 : -8), it.sy - d.z); g.fillStyle = d.col; g.strokeStyle = OL; g.lineWidth = 2.4;
        if (item?.rarity === 'rare') { g.shadowColor = d.col; g.shadowBlur = 12; }
        g.beginPath();
        if (d.item) { g.moveTo(0,-12); g.lineTo(10,-2); g.lineTo(0,8); g.lineTo(-10,-2); g.closePath(); }
        else { g.moveTo(0, -9); g.bezierCurveTo(8, -1, 8, 6, 0, 6); g.bezierCurveTo(-8, 6, -8, -1, 0, -9); }
        g.fill(); g.stroke(); g.shadowBlur = 0;
        if (item?.class) { g.fillStyle = '#112b49'; g.font = 'bold 12px sans-serif'; g.textAlign = 'center'; g.fillText(item.kind === 'weapon' ? '⚔' : '◆', 0, 3); }
        else { g.fillStyle = 'rgba(255,255,255,.7)'; g.beginPath(); g.arc(-2.4, -1, 1.8, 0, 6.283); g.fill(); }
        g.restore();
      } else if (it.remote) {
        const remote = it.remote; g.save(); g.translate(it.sx, it.sy);
        if (remote.sprite) remote.sprite.draw(g, remote, t);
        else { g.fillStyle = '#cfb5fa'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
        g.font = '18px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#151c35'; g.fillStyle = window.Social?.isPartyMember(remote.id) ? '#9dffb2' : '#fff4ca';
        g.strokeText(remote.look.name, 0, -128); g.fillText(remote.look.name, 0, -128);
        g.fillStyle = '#16263dcc'; g.fillRect(-25, -116, 50, 5); g.fillStyle = '#8ee7a5'; g.fillRect(-25, -116, 50 * remote.hp / remote.maxHp, 5);
        g.restore();
      } else if (it.hero) { g.save(); g.translate(it.sx, it.sy); if (isModular()) {
        if (mageSpr) mageSpr.draw(g, hero, t);
        else { g.fillStyle = '#8acfff'; g.font = '24px sans-serif'; g.textAlign = 'center'; g.fillText('✦', 0, -40); }
      } else { if (!warSpr && hero.hurtT > 0 && Math.floor(hero.hurtT * 40) % 2) g.globalAlpha = .6; if (warSpr) drawWarriorSprite(g, hero, t); else if (heroSpr) drawHeroSprite(g, hero, t); else { g.scale(1.3, 1.3); drawHero(g, hero, t); } } g.restore(); }
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
    for (const p of parts) { const [sx, sy] = w2s(p.x, p.y, p.z); g.globalAlpha = 1 - p.t / p.life; g.fillStyle = p.col; g.beginPath(); g.arc(sx, sy, p.size, 0, 6.283); g.fill(); } g.globalAlpha = 1;
    for (const f of floaters) { const [sx, sy] = w2s(f.x, f.y, f.z + 30); g.globalAlpha = clamp(1.4 - f.t * 1.3, 0, 1); g.font = `${f.big ? 34 : 24}px "Lilita One", "Jua", Impact, sans-serif`; g.textAlign = 'center'; g.lineWidth = 5; g.strokeStyle = 'rgba(20,10,30,.9)'; g.strokeText(f.text, sx, sy); g.fillStyle = f.color; g.fillText(f.text, sx, sy); } g.globalAlpha = 1;
    drawMini();
  }
  function buildMini() {
    const [c, g] = canvasOf(144, 144, 1), k = 144 / MAP, ember = zdef.theme === 'ember';
    g.fillStyle = ember ? '#2b1f22' : '#3f9b48'; g.fillRect(0, 0, 144, 144);
    for (let y = 0; y < MAP; y++) for (let x = 0; x < MAP; x++) if (map.dirt[y * MAP + x]) { g.fillStyle = ember ? '#6a5040' : '#c9a26a'; g.fillRect(x * k, y * k, k + .5, k + .5); }
    if (zone === 0) {
      g.fillStyle='#d8cbb0'; g.fillRect(WORLD_MAP.city.x0*k,WORLD_MAP.city.y0*k,(WORLD_MAP.city.x1-WORLD_MAP.city.x0)*k,(WORLD_MAP.city.y1-WORLD_MAP.city.y0)*k);
      g.fillStyle='#68bcc6'; g.beginPath();g.arc(36*k,83*k,3,0,Math.PI*2);g.fill();
    }
    for (const o of objects) {
      if (o.kind === 'post') continue;
      g.fillStyle = o.kind === 'lava' ? '#ff6a2a' : o.kind === 'tree' ? (ember ? '#150f13' : '#1f6b3a') : o.kind === 'spire' ? '#4b3b5e' : o.kind === 'rock' ? (ember ? '#6a6672' : '#8a93a8') : (ember ? '#5a3a30' : '#2f8a45');
      g.beginPath(); g.arc(o.x * k, o.y * k, o.kind === 'lava' ? 2.2 : o.kind === 'tree' ? 2.1 : 1.2, 0, 6.283); g.fill();
    }
    for (const p of zdef.portals) { g.strokeStyle = ZONES[p.to]?.theme === 'ember' ? '#ff8a3a' : '#7ae8c8'; g.lineWidth = 2; g.beginPath(); g.arc(p.x * k, p.y * k, 4, 0, 6.283); g.stroke(); }
    miniBase = c;
  }
  function drawMini() {
    if (!mctx || !miniBase) return;
    const s = mini.width / MAP; mctx.clearRect(0, 0, mini.width, mini.height); mctx.drawImage(miniBase, 0, 0, mini.width, mini.height);
    if (zone === 0) for (const n of City.npcs) { mctx.fillStyle='#f5d477';mctx.fillRect(n.x*s-1,n.y*s-1,2,2); }
    for (const remote of remotePlayers.values()) { mctx.fillStyle = window.Social?.isPartyMember(remote.id) ? '#7dff9b' : '#b3dfff'; mctx.beginPath(); mctx.arc(remote.x * s, remote.y * s, 2.5, 0, 6.283); mctx.fill(); }
    for (const sl of slimes) if (!sl.dead) { mctx.fillStyle = sl.kind === 'big' ? '#c8b5ff' : '#ff6b8a'; mctx.beginPath(); mctx.arc(sl.x * s, sl.y * s, 2, 0, 6.283); mctx.fill(); }
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
      loadBeetleSprites(); loadCragSprites();
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
      if (zone !== 0) { floater(hero.x, hero.y, 'Return to Greenmeadow first', '#ffe066', false); return; }
      const npc = City.npcs.find(n => n.id === id);
      if (npc) talkTo(npc);
    },
    visitCity() {
      if(paused || !Online.connected || hero.dead)return;
      if (zone !== 0) { floater(hero.x, hero.y, 'Return to Greenmeadow first', '#ffe066', false); return; }
      Field.clearInput(); pendingNpc=null; hero.target=null; hero.goal=null;
      cityRoute=routeTo({x:36,y:79});routeTime=0;
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
      if (id === 'shadowstep' && isAssassin() && hero.dashCd <= 0) { shadowstep(); return true; }
      const def = SKILL_BY_ID[id];
      if (def && def.class === hero.look.class && hero.level >= def.level && !(hero.skillCd?.[id] > 0) && hero.dashT <= 0) { castSkill(def); return true; }
      return false;
    },
    get canAct() { return running && !paused && Online.connected && !hero.dead; },
    equipSlot(slot, item) {
      if (!running || !Online.connected || hero.dead) return false;
      return Online.send({ type: 'equip', slots: { [slot]: item } });
    },
    get remotePlayers() { return [...remotePlayers.values()]; },
    get equipmentStats() { return equipmentStats(); },
    get warriorSprites() { return !isMage() && !isAssassin() ? mageSpr : null; },
    get mageSprites() { return isMage() ? mageSpr : null; },
    get assassinSprites() { return isAssassin() ? mageSpr : null; },
    get hero() { return hero; }, get slimes() { return slimes; },
    get beetleSprites() { return beetleSrc; }, get cragSprites() { return cragSrc; },
    get zone() { return zone; }, get zoneName() { return zdef.name; },
    _debug: { get effects() { return effects; }, event: networkEvent, get objects() { return objects; }, get zones() { return ZONES; }, w2s, s2w, routeTo, enemyFrame: s => slimeFrame(s, tAll) },
  };
  window.Field = Field;
})();
