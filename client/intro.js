'use strict';
// The opening cutscene (INTRO-*, docs/intro-cutscene.md): about a minute on the Grey Gull, the ship that lies at Greenmeadow's pier, sailing to land on
// a moving camera, while a narrator tells why the hero was summoned: Eldmarr, the first forge, the broken promise, the nine chains. It plays once for a
// brand-new character (the server sends `cutscene` ['intro']), skippable from an account's second character, and again from Settings > Replay intro.
// The ship, pier and skipper are the game's own drawing (meadowdock.js, City.drawNpc) on a custom camera in the game's 2:1 projection, so the last
// shot (the hero stepping onto the pier, zoom 1) is exactly the game's first view and the scene fades into the world without a cut. The sky tells
// the history: ember glow, sparks, nine chains, a fire ring over a mountain, the sea warming from blue to red. Narration is shown as subtitles and read
// with the owner's seven recorded ElevenLabs narration clips. The hero stands at the bow from the first frame (owner, 2026-11-13); the old magic finds
// them there, and the camera is one continuous move (a spline through `SHOTS`), opening and peaking in a close-up of the hero.
(() => {
  const CS = window.Cutscene, D = window.WORLD_MAP?.dock;
  if (!CS || !D) return;
  const { clamp, ease, lerp, rnd } = CS;
  const TW = 88, TH = 44;                          // the game's tile size in px (field.js)
  const DUR = 62, ARRIVE = 54.5;
  const SHIP = D.ship, LEN = SHIP.y1 - SHIP.y0, MID = (SHIP.y0 + SHIP.y1) / 2;
  const SKIPPER = (window.WORLD_MAP.npcs || []).find(n => n.id === 'dock_skipper');
  D.bollards ||= [SHIP.y0 + 1.6, SHIP.y1 - 1.4];
  const deckZ = u => 30 + 26 * (2 * u - 1) ** 4 - 16;   // the ship's deck height above the waterline at fraction u of its length (meadowdock.js)
  // The hero stands well forward: clear of the sail's near end on screen (the hero is painted over the scene, so the sail cannot cover them).
  const HERO_U = .12, PLANK_U = (SHIP.plank - SHIP.y0) / LEN, SKIPPER_U = .86;
  const bob = t => Math.sin(t * .9) * 1.6;              // the swell lifting the hull (meadowdock.js `ship`)

  // ---- the voyage -----------------------------------------------------------------------------------------------------------------------
  // Offsets of the ship from its mooring: it comes in from the south-west and slows to a stop alongside the pier.
  const shipAt = t => { const q = 1 - clamp(t / ARRIVE, 0, 1); return { dx: -22 * q * q, dy: 150 * Math.pow(q, 1.7) }; };

  // Camera keys: [time, zoom, across the ship (tiles), along the ship from its centre (tiles, negative towards the bow), height (px)]. The camera is
  // ONE continuous move: a Hermite spline through the keys (tangents from the neighbouring keys, zoom in log space), so it never stops at a key the way
  // a per-shot ease does. It opens tight on the hero at the bow, cranes back to show the ship under the burning sky, glides down the hull to the
  // skipper, lifts high for the failing chains, sweeps round the bow and pushes in hard on the hero as the magic finds them.
  const HERO_Y = (HERO_U - .5) * LEN, SKIP_Y = (SKIPPER_U - .5) * LEN;
  const SHOTS = [
    [0, 2.3, 0, HERO_Y, 62], [5, 1.7, .5, HERO_Y + .5, 56], [11, .5, -3, -6, 20], [17, .8, 2.6, 3, 30], [23, 1.75, .2, SKIP_Y, 58],
    [29, .6, -1.6, 0, 74], [36, 1.05, 1.6, -5.2, 30], [42, 1.6, .5, HERO_Y - .3, 52], [47.5, 2.6, 0, HERO_Y, 66], [50.5, 2.85, 0, HERO_Y, 68], [53, 1.5, .8, -1.5, 30],
  ].map(s => [s[0], Math.log(s[1]), s[2], s[3], s[4]]);
  const slope = (j, c) => j <= 0 || j >= SHOTS.length - 1 ? 0 : (SHOTS[j + 1][c] - SHOTS[j - 1][c]) / (SHOTS[j + 1][0] - SHOTS[j - 1][0]);
  function camera(t, cx, cy, still) {
    let i = 0; while (i < SHOTS.length - 2 && t > SHOTS[i + 1][0]) i++;
    const a = SHOTS[i], b = SHOTS[i + 1], d = b[0] - a[0], u = clamp((t - a[0]) / d, 0, 1), u2 = u * u, u3 = u2 * u;
    const at = c => (2 * u3 - 3 * u2 + 1) * a[c] + (u3 - 2 * u2 + u) * d * slope(i, c) + (3 * u2 - 2 * u3) * b[c] + (u3 - u2) * d * slope(i + 1, c);
    // A slow drift on top, like a camera on another boat riding the same swell (not with reduced motion).
    const sway = still ? 0 : 1 - ease((t - 53) / 3);
    let f = { k: Math.exp(at(1)), x: cx + at(2) + Math.sin(t * .23) * .22 * sway, y: cy + at(3) + Math.cos(t * .17) * .28 * sway, z: at(4) + Math.sin(t * .9 + 1) * 2.2 * sway };
    if (t > 53) {   // the last shot settles on the pier at the game's own zoom
      const e = ease((t - 53) / 6.5), last = { k: 1, x: D.start.x, y: D.start.y, z: 0 };
      f = { k: lerp(f.k, last.k, e), x: lerp(f.x, last.x, e), y: lerp(f.y, last.y, e), z: lerp(f.z, last.z, e) };
    }
    return f;
  }
  // Where the hero stands (world x, y and height in px) and what they do: at the bow looking ahead for the whole voyage, lifted a little by the
  // summoning light, then aft along the deck to the gangplank and down it to the pier start.
  // The hero's place on the ship's own frame (the ship's drift is not walking): the deck, then the gangplank down to the pier.
  const rel = t => {
    const aft = ease((t - 53.2) / 3), u = lerp(HERO_U, PLANK_U, aft), gang = ease((t - 56.2) / 2.8);
    return [lerp(SHIP.x, D.start.x, gang), lerp(SHIP.y0 + u * LEN, D.start.y, gang)];
  };
  // How fast the hero actually walks (tiles/s along the ground) and in which direction: from the path itself, so the legs follow the ground covered.
  // The walk eases in and out, and at either end the speed falls to nothing: there the hero stands (idle) instead of treading on the spot.
  const WALK_MIN = .35, EPS = .04;
  function stride(t) {
    const [x0, y0] = rel(t - EPS), [x1, y1] = rel(t + EPS), d = Math.hypot(x1 - x0, y1 - y0), speed = d / (2 * EPS);
    return { speed, dir: d > 1e-9 ? [(x1 - x0) / d, (y1 - y0) / d] : null };
  }
  function heroAt(t, ship) {
    const aft = ease((t - 53.2) / 3), u = lerp(HERO_U, PLANK_U, aft), gang = ease((t - 56.2) / 2.8);
    const lift = bump(t, 47.2, 48.8, 50.4, 52) * 9, swell = bob(t) * (1 - gang);
    const move = stride(t), walking = t > 53.2 && t < 59 && move.speed >= WALK_MIN && move.dir;
    // Facing: ahead for the voyage, then the way the walk goes (aft along the deck, then down the plank).
    const [pxn, pyn] = rel(56.2), plank = Math.hypot(D.start.x - pxn, D.start.y - pyn) || 1;
    const face = t < 53.2 ? [0, -1] : t < 56.2 ? [0, 1] : [(D.start.x - pxn) / plank, (D.start.y - pyn) / plank];
    return {
      x: lerp(ship.x, D.start.x, gang), y: lerp(ship.y0 + u * LEN, D.start.y, gang), z: lerp(deckZ(u) + 2, 7, gang) + swell + lift,
      walk: walking ? move.dir : null, speed: walking ? move.speed : 0, face: walking ? move.dir : face,
    };
  }
  function projector(w, h, f, fix) {
    const ox = (f.x - f.y) * TW / 2, oy = (f.x + f.y) * TH / 2;
    return (x, y, z = 0) => [((x - y) * TW / 2 - ox) * f.k + w / 2 + fix[0], ((x + y) * TH / 2 - oy) * f.k + h / 2 - (z - f.z) * f.k + fix[1]];
  }

  // ---- the story in the sky ------------------------------------------------------------------------------------------------------------
  const keyed = (t, pts) => { for (let i = 0; i < pts.length - 1; i++) if (t <= pts[i + 1][0]) return lerp(pts[i][1], pts[i + 1][1], ease((t - pts[i][0]) / (pts[i + 1][0] - pts[i][0]))); return pts[pts.length - 1][1]; };
  const bump = (t, a, b, c, d) => ease((t - a) / (b - a)) * (1 - ease((t - c) / (d - c)));
  const WARM = [[0, 0], [3, 0], [8, .35], [14, .55], [22, .5], [24, .6], [34, .62], [44, .5], [48, .12], [52, 0], [62, 0]];
  const SPARKS = [[0, .1], [10, .35], [24, .8], [34, .9], [44, .4], [50, .05], [62, 0]];
  const mixc = (a, b, v) => `rgb(${a.map((c, i) => Math.round(lerp(c, b[i], v))).join(',')})`;

  function sea(g, w, h, t, P, f, warm) {
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, mixc([20, 66, 108], [118, 38, 26], warm)); gr.addColorStop(1, mixc([40, 128, 168], [182, 78, 38], warm));
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    // Wave strokes pinned to the world (hashed cells of 4 tiles), so the camera really moves over water.
    const R = Math.min(34, (w / (TW * f.k) + h / (TH * f.k)) * .55 + 2), x0 = Math.floor((f.x - R) / 4), x1 = Math.ceil((f.x + R) / 4), y0 = Math.floor((f.y - R) / 4), y1 = Math.ceil((f.y + R) / 4);
    g.lineCap = 'round';
    for (let ix = x0; ix <= x1; ix++) for (let iy = y0; iy <= y1; iy++) {
      const s = ix * 73.1 + iy * 151.7, [sx, sy] = P((ix + rnd(s)) * 4, (iy + rnd(s + 1)) * 4, 0), r = (9 + rnd(s + 2) * 9) * f.k, ph = t * .8 + rnd(s + 3) * 6.3, a = .12 + .12 * Math.sin(ph);
      if (sx < -40 || sx > w + 40 || sy < -20 || sy > h + 20) continue;
      g.strokeStyle = warm > .3 ? `rgba(255,${190 - Math.round(warm * 60)},120,${a})` : `rgba(235,250,255,${a})`; g.lineWidth = Math.max(1, 1.3 * f.k);
      g.beginPath(); g.ellipse(sx, sy, r, r * .28, 0, Math.PI * .1, Math.PI * .9); g.stroke();
    }
  }
  function coast(g, w, h, P, t) {
    // Greenmeadow's strand, north of the pier: grass, then sand, then the foam line. Only visible once the camera comes close (the last twenty seconds).
    const shore = x => 282 + Math.sin(x * .09) * 1.4 + Math.sin(x * .031) * 2.2;
    const band = (from, to, col) => {
      g.beginPath();
      for (let x = 150; x <= 250; x += 4) { const [sx, sy] = P(x, shore(x) + from, 0); x === 150 ? g.moveTo(sx, sy) : g.lineTo(sx, sy); }
      for (let x = 250; x >= 150; x -= 4) { const [sx, sy] = P(x, shore(x) + to, 0); g.lineTo(sx, sy); }
      g.closePath(); g.fillStyle = col; g.fill();
    };
    band(-6, -70, '#7fae62'); band(0, -6, '#d9c892'); band(.5, -.6, '#efe6c4');
    g.save(); g.strokeStyle = 'rgba(245,252,255,.8)'; g.lineWidth = 2; g.lineCap = 'round';
    for (let x = 152; x <= 250; x += 5) { const [sx, sy] = P(x, shore(x) + .9 + Math.sin(t * 1.4 + x) * .3, 0); g.beginPath(); g.moveTo(sx - 12, sy); g.lineTo(sx + 12, sy + 1); g.stroke(); }
    g.restore();
  }
  function wake(g, P, f, ship, t) {
    g.save(); g.lineCap = 'round';
    for (let j = 0; j < 14; j++) for (const side of [-1, 1]) {
      const wx = ship.x + side * (.7 + j * .3 + Math.sin(t * 2 + j) * .08), wy = ship.y1 + .5 + j * .95, [sx, sy] = P(wx, wy, 0), a = (1 - j / 14) * .55;
      g.strokeStyle = `rgba(245,252,255,${a})`; g.lineWidth = Math.max(1, (3.2 - j * .16) * f.k);
      g.beginPath(); g.moveTo(sx - 7 * f.k, sy - 1); g.lineTo(sx + 7 * f.k, sy + 1); g.stroke();
    }
    for (let k = -2; k <= 2; k++) { const [sx, sy] = P(ship.x + k * .4, ship.y0 - .3 + Math.abs(k) * .2, 0); g.fillStyle = 'rgba(250,254,255,.65)'; g.beginPath(); g.ellipse(sx, sy, 14 * f.k, 5 * f.k, 0, 0, Math.PI * 2); g.fill(); }
    g.restore();
  }

  // Sky overlays in screen space: the forge, the hall, the nine chains, burning roots, sparks, an ember glow on the edges.
  function sky(g, w, h, t, warm, far) {   // far: the forge, the hall and the chains, drawn behind the ship; otherwise the glow, roots and sparks in front of it
    const forge = bump(t, 3, 5.5, 33, 37), hall = bump(t, 12.5, 15, 33, 36), roots = bump(t, 24, 26.5, 36, 40);
    const px = w * .22, py = h * .26;
    if (!far) {   // the ember glow along the edges
      const glow = g.createRadialGradient(w / 2, h / 2, Math.min(w, h) * .35, w / 2, h / 2, Math.max(w, h) * .75);
      glow.addColorStop(0, 'rgba(255,90,30,0)'); glow.addColorStop(1, `rgba(255,70,20,${.5 * warm})`); g.fillStyle = glow; g.fillRect(0, 0, w, h);
    }
    if (far && forge > .01) {   // the first forge: a real volcano with a lava crater, lava on its flanks, smoke, and a lit foot on the water
      const sc = h / 600, hw = w * .27, base = h * .54, erupt = bump(t, 20, 27, 33, 37), pulse = .5 + Math.sin(t * 3.1) * .5;
      const top = x => { const d = Math.abs(x - px) / hw; return d >= 1 ? base : Math.max(py, base - (base - py) * Math.pow(1 - d, 1.45) + (rnd(Math.round(x / 6)) - .5) * 5 * sc); };
      g.save(); g.globalAlpha = forge;
      // A paler ridge behind, so the cone has depth.
      g.fillStyle = '#3a2328'; g.beginPath(); g.moveTo(px - hw * 1.5, base); for (let x = px - hw * 1.5; x <= px + hw * 1.5; x += 8) g.lineTo(x, base - (base - py) * .55 * Math.pow(Math.max(0, 1 - Math.abs(x - (px + hw * .55)) / (hw * 1.0)), 1.3)); g.lineTo(px + hw * 1.5, base); g.closePath(); g.fill();
      // The cone, lit from the crater.
      const cone = g.createLinearGradient(0, py, 0, base); cone.addColorStop(0, '#6a2f20'); cone.addColorStop(.35, '#3a1d1c'); cone.addColorStop(1, '#1b1115');
      g.fillStyle = cone; g.beginPath(); g.moveTo(px - hw, base); for (let x = px - hw; x <= px + hw; x += 4) g.lineTo(x, top(x)); g.lineTo(px + hw, base); g.closePath(); g.fill();
      // Rock ribs down the flanks.
      g.strokeStyle = 'rgba(20,10,12,.55)'; g.lineWidth = 2 * sc; for (let i = 0; i < 9; i++) { const sx = px + (i - 4) * hw * .13, ex = px + (i - 4) * hw * .3; g.beginPath(); g.moveTo(sx, top(sx) + 6 * sc); g.lineTo(ex, base); g.stroke(); }
      // Lava rivers from the rim, brighter as it erupts.
      for (let i = 0; i < 5; i++) {
        const dir = (i - 2) * .32 + (rnd(i) - .5) * .1, len = (.45 + rnd(i + 3) * .4 + erupt * .25), sx = px + dir * hw * .22;
        let x = sx, y = py + 4 * sc; g.beginPath(); g.moveTo(x, y);
        for (let k = 1; k <= 8; k++) { const f = k / 8; x = sx + dir * hw * .9 * f * len + Math.sin(f * 7 + i * 2) * 7 * sc; y = py + (base - py) * Math.min(1, f * len) * .98; g.lineTo(x, y); }
        g.strokeStyle = `rgba(255,${110 + Math.round(pulse * 40)},30,${.5 + erupt * .4})`; g.lineWidth = (4.5 - i % 2) * sc; g.lineCap = 'round'; g.shadowColor = 'rgba(255,110,30,.9)'; g.shadowBlur = 10 * sc; g.stroke();
        g.shadowBlur = 0; g.strokeStyle = 'rgba(255,225,140,.85)'; g.lineWidth = 1.4 * sc; g.stroke();
      }
      // The crater: a glowing lava lake with a flickering rim of flame.
      const cr = 34 * sc, glow = g.createRadialGradient(px, py - 4 * sc, 2, px, py - 4 * sc, 150 * sc); glow.addColorStop(0, 'rgba(255,215,130,.95)'); glow.addColorStop(.25, 'rgba(255,125,40,.6)'); glow.addColorStop(1, 'rgba(255,80,20,0)');
      g.fillStyle = glow; g.fillRect(px - 160 * sc, py - 160 * sc, 320 * sc, 320 * sc);
      g.fillStyle = '#2a1114'; g.beginPath(); g.ellipse(px, py, cr * 1.15, 11 * sc, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = `rgb(255,${150 + Math.round(pulse * 50)},50)`; g.beginPath(); g.ellipse(px, py, cr, 8 * sc, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#fff0b0'; g.beginPath(); g.ellipse(px, py - sc, cr * .55, 3.5 * sc, 0, 0, Math.PI * 2); g.fill();
      for (let i = 0; i < 7; i++) {
        const fx = px + (i - 3) * cr * .28, fh = (16 + rnd(i + 20) * 20 + erupt * 26) * sc * (.7 + .3 * Math.sin(t * 8 + i * 1.7)), fw = 6 * sc;
        const fl = g.createLinearGradient(0, py, 0, py - fh); fl.addColorStop(0, 'rgba(255,230,140,.95)'); fl.addColorStop(1, 'rgba(255,80,20,0)');
        g.fillStyle = fl; g.beginPath(); g.moveTo(fx - fw, py); g.quadraticCurveTo(fx - fw * .4, py - fh * .6, fx + Math.sin(t * 5 + i) * 4 * sc, py - fh); g.quadraticCurveTo(fx + fw * .4, py - fh * .6, fx + fw, py); g.closePath(); g.fill();
      }
      // Smoke and ash drifting up and to the right, thicker in the eruption.
      for (let i = 0; i < 14; i++) {
        const u = (t * .07 + i / 14) % 1, sx2 = px + u * w * .16 + Math.sin(t * .8 + i) * 8 * sc, sy2 = py - 14 * sc - u * h * .3, r = (14 + u * 42) * sc;
        g.fillStyle = `rgba(${52 + Math.round((1 - u) * 60)},${34 + Math.round((1 - u) * 22)},38,${(1 - u) * (.28 + erupt * .3)})`; g.beginPath(); g.arc(sx2, sy2, r, 0, Math.PI * 2); g.fill();
      }
      // The foot: sea haze over the base and the glow on the water.
      g.save(); g.translate(px, base + 2 * sc); g.scale(1, .2); const haze = g.createRadialGradient(0, 0, hw * .2, 0, 0, hw * 1.7); haze.addColorStop(0, 'rgba(110,60,56,.97)'); haze.addColorStop(.6, 'rgba(110,60,56,.8)'); haze.addColorStop(1, 'rgba(110,60,56,0)'); g.fillStyle = haze; g.beginPath(); g.arc(0, 0, hw * 1.7, 0, Math.PI * 2); g.fill(); g.restore();
      for (let i = 0; i < 12; i++) { const rx = px + (rnd(i + 40) - .5) * hw * .8, ry = base + 6 * sc + i * 5 * sc, rw = (26 - i * 1.4) * sc * (.7 + .3 * Math.sin(t * 2 + i)); g.fillStyle = `rgba(255,${130 + i * 6},60,${.3 - i * .02})`; g.beginPath(); g.ellipse(rx, ry, rw, 1.6 * sc, 0, 0, Math.PI * 2); g.fill(); }
      g.restore();
    }
    if (far && hall > .01) {    // the gods' hall: a pale gold light with an empty seat
      const hx = w * .8, gr = g.createLinearGradient(hx, 0, hx, h * .46); gr.addColorStop(0, `rgba(255,236,170,${.6 * hall})`); gr.addColorStop(1, 'rgba(255,236,170,0)');
      g.fillStyle = gr; g.beginPath(); g.moveTo(hx - 16, 0); g.lineTo(hx + 16, 0); g.lineTo(hx + 90, h * .46); g.lineTo(hx - 90, h * .46); g.closePath(); g.fill();
      g.save(); g.globalAlpha = hall * .95; g.fillStyle = '#2a2030'; g.fillRect(hx - 9, h * .27, 18, 24); g.fillRect(hx - 13, h * .27 + 24, 26, 6); g.fillRect(hx - 13, h * .27 + 30, 4, 12); g.fillRect(hx + 9, h * .27 + 30, 4, 12); g.restore();
    }
    // The nine chains: heavy iron from the crater to the gods' empty seat. They appear one by one, glow red-hot, then snap one by one.
    if (far) {
      const sc = h / 600, seatX = w * .8, seatY = h * .3, cx = px, cy = py;
      for (let i = 0; i < 9; i++) {
        const born = 14.5 + i * .35, dies = 26.5 + i * .9, a = ease((t - born) / .6);
        if (a < .02 || t > dies + 2.4) continue;
        const fall = Math.max(0, t - dies), heat = ease((t - (dies - 3)) / 3), cut = .3 + rnd(i + 60) * .4;
        const x0 = cx + (i - 4) * 6 * sc, y0 = cy - 2 * sc + (i - 4) * 1.5 * sc, x1 = seatX + (i - 4) * 3 * sc, y1 = seatY + 22 * sc + (i - 4) * 15 * sc, sag = (i - 4) * 13 * sc + 8 * sc + Math.sin(t * 1.3 + i) * 2 * sc;
        const at = u => [x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + Math.sin(u * Math.PI) * sag];
        const n = Math.round(Math.hypot(x1 - x0, y1 - y0) / (8.5 * sc));
        g.save(); g.globalAlpha = a * (1 - ease((fall - 1.4) / 1)); g.lineJoin = 'round';
        for (let k = 0; k <= n; k++) {
          const u = k / n, [x, y] = at(u), [x2, y2] = at(Math.min(1, u + 1 / n)), ang = Math.atan2(y2 - y, x2 - x), side = u < cut ? -1 : 1;
          const off = fall > 0 ? fall * fall * 46 * sc * (side < 0 ? 1 + (cut - u) * 2 : .6 + rnd(i * 7 + k) * .8) : 0, sw = fall > 0 ? fall * 34 * sc * (rnd(k + i * 5) - .5) : 0;
          g.save(); g.translate(x + sw, y + off); g.rotate(ang + (fall > 0 ? side * fall * .9 * (rnd(k + 3) - .3) : 0));
          const iron = [Math.round(52 + heat * 203), Math.round(56 + heat * 70), Math.round(68 - heat * 30)], hot = heat > .05;
          if (hot) { g.shadowColor = `rgba(255,110,30,${heat})`; g.shadowBlur = 8 * sc * heat; }
          if (k % 2 === 0) {   // a link seen face-on: an iron ring with a pale highlight on the upper edge
            g.strokeStyle = `rgb(${iron})`; g.lineWidth = 2.6 * sc; g.beginPath(); g.ellipse(0, 0, 5.4 * sc, 3.2 * sc, 0, 0, Math.PI * 2); g.stroke();
            g.shadowBlur = 0; g.strokeStyle = `rgba(${170 + heat * 80},${178 - heat * 40},${200 - heat * 120},.8)`; g.lineWidth = 1 * sc; g.beginPath(); g.ellipse(0, -.5 * sc, 5.4 * sc, 3.2 * sc, 0, Math.PI * 1.05, Math.PI * 1.95); g.stroke();
          } else {   // a link seen edge-on: a short bar through the ring either side of it
            g.fillStyle = `rgb(${iron})`; g.fillRect(-3.6 * sc, -1.4 * sc, 7.2 * sc, 2.8 * sc); g.shadowBlur = 0; g.fillStyle = `rgba(${170 + heat * 80},${178 - heat * 40},${200 - heat * 120},.7)`; g.fillRect(-3.6 * sc, -1.4 * sc, 7.2 * sc, .9 * sc);
          }
          g.restore();
        }
        // Where it snaps: a flash and a burst of sparks.
        if (fall > 0 && fall < 1.2) {
          const [bx, by] = at(cut); g.globalAlpha = 1 - fall / 1.2;
          for (let k = 0; k < 14; k++) { const ang = rnd(k + i * 9) * Math.PI * 2, r = fall * (30 + rnd(k + 5) * 50) * sc; g.fillStyle = k % 2 ? '#ffb14a' : '#fff0a0'; g.beginPath(); g.arc(bx + Math.cos(ang) * r, by + Math.sin(ang) * r + fall * fall * 30 * sc, (1.2 + rnd(k) * 1.6) * sc, 0, Math.PI * 2); g.fill(); }
        }
        g.restore();
      }
    }
    if (far && roots > .01) {   // the roots that hold up the sky begin to burn: thick, gnarled, branching, cracked with lava, flames along them and embers falling
      const sc = h / 600;
      const build = (x0, y0, len, ang, seed) => { const pts = []; let x = x0, y = y0, a = ang; const N = 12; for (let k = 0; k <= N; k++) { pts.push([x, y, k / N]); a += (rnd(seed + k) - .5) * .5 + Math.sin(t * .5 + seed + k * .4) * .012; x += Math.sin(a) * len / N; y += Math.cos(a) * len / N; } return pts; };
      const root = (pts, wd0, seed, fire) => {
        g.lineCap = 'round';
        for (let k = 0; k < pts.length - 1; k++) {   // bark with a lit edge
          const [x, y, u] = pts[k], [x2, y2] = pts[k + 1], wd = wd0 * (1 - u * .85);
          g.strokeStyle = '#2b1810'; g.lineWidth = wd; g.beginPath(); g.moveTo(x, y); g.lineTo(x2, y2); g.stroke();
          g.strokeStyle = 'rgba(128,82,52,.5)'; g.lineWidth = wd * .22; g.beginPath(); g.moveTo(x - wd * .24, y); g.lineTo(x2 - wd * .24, y2); g.stroke();
        }
        g.shadowColor = 'rgba(255,110,30,.95)'; g.shadowBlur = 9 * sc;
        for (let k = 0; k < pts.length - 1; k++) {   // glowing cracks along the middle, flickering
          const [x, y, u] = pts[k], [x2, y2] = pts[k + 1], wd = wd0 * (1 - u * .85), flick = .55 + .45 * Math.sin(t * 7 + seed * 3 + k * 1.9);
          g.strokeStyle = `rgba(255,${120 + Math.round(flick * 80)},40,${.9 * flick * roots * fire})`; g.lineWidth = Math.max(1.2 * sc, wd * .16); g.beginPath(); g.moveTo(x + Math.sin(k + seed) * wd * .12, y); g.lineTo(x2 + Math.sin(k + 1 + seed) * wd * .12, y2); g.stroke();
        }
        g.shadowBlur = 0;
        for (let k = 1; k < pts.length; k++) {   // flame tongues licking up the root
          if (rnd(seed + k * 3) < .35) continue;
          const [x, y, u] = pts[k], wd = wd0 * (1 - u * .85), flick = .6 + .4 * Math.sin(t * 8.5 + seed + k * 2.3), fh = (20 + rnd(seed + k) * 34) * sc * flick * roots * fire, fw = Math.max(5 * sc, wd * .7), fx = x + (rnd(seed + k + 5) - .5) * wd * .5;
          const fl = g.createLinearGradient(0, y, 0, y - fh); fl.addColorStop(0, 'rgba(255,225,130,.8)'); fl.addColorStop(.45, 'rgba(255,120,35,.5)'); fl.addColorStop(1, 'rgba(255,70,20,0)');
          g.fillStyle = fl; g.beginPath(); g.moveTo(fx - fw, y); g.bezierCurveTo(fx - fw * 1.1, y - fh * .4, fx - fw * .3, y - fh * .75, fx + Math.sin(t * 5 + k + seed) * 5 * sc, y - fh); g.bezierCurveTo(fx + fw * .3, y - fh * .75, fx + fw * 1.1, y - fh * .4, fx + fw, y); g.closePath(); g.fill();
        }
        const [tx, ty] = pts[pts.length - 1], tg = g.createRadialGradient(tx, ty, 1, tx, ty, 16 * sc); tg.addColorStop(0, `rgba(255,200,110,${.9 * roots * fire})`); tg.addColorStop(1, 'rgba(255,90,20,0)'); g.fillStyle = tg; g.beginPath(); g.arc(tx, ty, 16 * sc, 0, Math.PI * 2); g.fill();   // the burning tip
        for (let j = 0; j < 5; j++) {   // embers dropping from the tip and the branches
          const u = (t * (.16 + rnd(seed + j) * .08) + rnd(seed + j + 9)) % 1, [ex, ey] = pts[pts.length - 1 - (j % 4)];
          g.fillStyle = `rgba(255,${170 + j * 15},70,${(1 - u) * .9 * roots * fire})`; g.beginPath(); g.arc(ex + Math.sin(t * 1.3 + j + seed) * 6 * sc + (rnd(seed + j) - .5) * 14 * sc, ey + u * h * .32, (1.6 + rnd(seed + j + 2) * 1.8) * sc, 0, Math.PI * 2); g.fill();
        }
      };
      g.save();
      for (let i = 0; i < 6; i++) {
        const seed = i * 17 + 3, x0 = w * (.07 + i * .17) + (rnd(seed) - .5) * w * .05, len = h * (.36 + rnd(seed + 2) * .14) * roots, wd0 = (32 + rnd(seed + 4) * 14) * sc;
        const main = build(x0, -8 * sc, len, (rnd(seed + 6) - .5) * .25, seed);
        root(main, wd0, seed, 1);
        for (const [bk, side] of [[4, -1], [8, 1]]) {   // two side roots, thinner, with their own fire
          const [bx, by] = main[bk]; if (rnd(seed + bk) < .2) continue;
          root(build(bx, by, len * (.34 + rnd(seed + bk + 1) * .14), side * (.7 + rnd(seed + bk + 2) * .5), seed + bk * 7), wd0 * .5 * (1 - main[bk][2] * .6), seed + bk, .8);
        }
      }
      g.restore();
    }
    const s = far ? 0 : keyed(t, SPARKS);
    if (s > 0) { g.save(); for (let i = 0; i < 70; i++) {
      const u = (t * (.08 + rnd(i) * .1) + rnd(i + 9)) % 1, x = rnd(i + 3) * w + Math.sin(t + i) * 20, y = h * (1.02 - u * 1.1);
      g.globalAlpha = s * (1 - u) * (.4 + rnd(i + 7) * .6); g.fillStyle = i % 3 ? '#ffb14a' : '#ffe08a'; g.beginPath(); g.arc(x, y, 1.2 + rnd(i + 11) * 2.2, 0, Math.PI * 2); g.fill();
    } g.restore(); }
  }

  // The summoning: a ring of light opens on the deck round the hero and a column of light climbs from it.
  function summon(g, w, h, t, sx, sy, k) {
    const a = bump(t, 46.6, 48.6, 51, 52.8); if (a < .01) return;
    const r = lerp(8, 78, ease((t - 46.6) / 2.4)) * k;
    g.save();
    const col = g.createLinearGradient(0, sy - h, 0, sy); col.addColorStop(0, 'rgba(255,245,205,0)'); col.addColorStop(1, `rgba(255,245,205,${.85 * a})`);
    g.fillStyle = col; g.fillRect(sx - r * .55, sy - h, r * 1.1, h);
    for (let i = 0; i < 3; i++) { g.strokeStyle = `rgba(255,${225 - i * 20},${150 + i * 30},${a * (1 - i * .22)})`; g.lineWidth = Math.max(2, (4 - i) * k); g.beginPath(); g.ellipse(sx, sy, r * (1 - i * .24), r * (1 - i * .24) * .3, 0, 0, Math.PI * 2); g.stroke(); }
    for (let i = 0; i < 18; i++) {   // runes turning on the ring
      const ang = t * 1.6 + i * Math.PI / 9, rx = sx + Math.cos(ang) * r * 1.08, ry = sy + Math.sin(ang) * r * 1.08 * .3;
      g.fillStyle = `rgba(255,236,170,${a})`; g.fillRect(rx - 2 * k, ry - 3 * k, 4 * k, 6 * k);
    }
    for (let i = 0; i < 26; i++) { const u = (t * .6 + rnd(i)) % 1; g.fillStyle = `rgba(255,240,200,${a * (1 - u)})`; g.beginPath(); g.arc(sx + (rnd(i + 4) - .5) * r * 1.6, sy - u * h * .5, (1.5 + rnd(i + 8) * 2) * k, 0, Math.PI * 2); g.fill(); }
    g.restore();
  }

  // ---- the narration (English here, Swedish by hand in scripts/sv-translations.txt) --------------------------------------------------
  const LINES = [
    [1.0, 'Before the first harvest, a forge was lit beneath the roots of the world. Its keeper, Eldmarr the Ember-Lord, kept the great roots alive through the long winter.', 11.4],
    [12.5, 'The gods raised their hall upon his fire and promised him a seat at their table. They never gave it. They bound him in stone with nine chains.', 10.9],
    [24, 'But a fire cannot be chained forever. For a hundred years it has risen, and the roots that hold up the sky have begun to burn.', 9.4],
    [34.5, 'No god may raise a hand against him, for all are bound by oath. So the old magic reached beyond the edge of the world, for someone who owed it nothing.', 11.7],
    [46.8, 'And it found you.', 2],
    [51, 'You did not ask for this. But the Grey Gull is nearing land, and the world is waiting.', 6.7],
    [58, 'Welcome to Veyrheim, hero.', 3.5],
  ];

  // ---- the scene -------------------------------------------------------------------------------------------------------------------------
  CS.register('intro', {
    dur: DUR, captions: LINES, music: 'assets/music_intro.mp3?v=saga-1.15.4',
    narration: LINES.map((_, i) => `assets/intro-narration-${i + 1}.mp3`), noZoom: true, fadeIn: 1.2, fadeOut: 2.2,
    sounds: [[0, 'sea_bed'], [2.5, 'creak'], [9, 'creak'], [12, 'ember'], [19, 'creak'], [28, 'creak'], [46.8, 'chord'], [53, 'creak'], [57, 'thud']],
    shoes: () => false,
    draw(c) {
      const { g, w, h, el: t, hx, hy } = c;
      const off = shipAt(t), ship = { x: SHIP.x + off.dx, y0: SHIP.y0 + off.dy, y1: SHIP.y1 + off.dy };
      const f = camera(t, ship.x, MID + off.dy, c.still);
      // Near the end the projection is nudged so the pier start lands exactly on the hero's real screen position: the fade into the world is then seamless.
      const raw = projector(w, h, f, [0, 0]), at = raw(D.start.x, D.start.y, 0), e = ease((t - 53) / 6.5);
      const P = projector(w, h, f, [(hx - at[0]) * e, (hy - at[1]) * e]);
      const warm = keyed(t, WARM);
      sea(g, w, h, t, P, f, warm);
      if (t > 30) coast(g, w, h, P, t);
      wake(g, P, f, ship, t);
      sky(g, w, h, t, warm, true);
      const d2 = { ...D, ship: { ...SHIP, x: ship.x, y0: ship.y0, y1: ship.y1 } };
      if (t > 36) window.MeadowDock.pier(g, D, P, t);
      window.MeadowDock.ship(g, d2, P, t);
      if (off.dy < 1.2) window.MeadowDock.moor(g, d2, P);
      // Skipper Halvard at the steering oar, all the way.
      if (SKIPPER) {
        const [sx, sy] = P(ship.x + .2, ship.y0 + SKIPPER_U * LEN, deckZ(SKIPPER_U) + 3 + bob(t)), npc = { ...SKIPPER, x: -999, y: -999, key: false, offers: [], buys: null, moving: false, fx: 0, fy: 1 };
        window.NpcArt?.readyFor?.([npc]);
        g.save(); g.translate(sx, sy); g.scale(f.k, f.k); try { window.City?.drawNpc(g, npc, 0, 0, t, false, false); } catch { /* art still loading */ } g.restore();
      }
      // The hero on the deck from the first frame, and the summoning that finds them there.
      const H = heroAt(t, ship), [px, py] = P(H.x, H.y, H.z), [rx, ry] = P(H.x, H.y, deckZ(HERO_U) + 2 + bob(t));
      summon(g, w, h, t, rx, ry, f.k);
      sky(g, w, h, t, warm, false);
      // A soft vignette for the film look; it lifts as the scene settles into the game's own view.
      const vig = .42 * (1 - e);
      if (vig > .01) { const v = g.createRadialGradient(w / 2, h / 2, Math.min(w, h) * .38, w / 2, h / 2, Math.hypot(w, h) * .6); v.addColorStop(0, 'rgba(4,6,14,0)'); v.addColorStop(1, `rgba(4,6,14,${vig})`); g.fillStyle = v; g.fillRect(0, 0, w, h); }
      c.flash = c.still ? 0 : Math.max(0, 1 - Math.abs(t - 48.8) / .22) * .85;
      c.veil = 0;
      // The hero is painted over the finished scene, but the sail stands nearer the camera than anyone forward of the mast: the ship is drawn once
      // more, clipped to the sail's own outline (the same points as meadowdock.js `ship`), so the sail covers what it should.
      const over = G => {
        const um = .47, hz = 30 + 26 * (2 * um - 1) ** 4 + bob(t), sw = SHIP.beam / 2 * 1.35, sway = Math.sin(t * .7) * 3;
        G.beginPath();
        for (let i = 0; i <= 8; i++) { const [x, y] = P(ship.x - sw + 2 * sw * i / 8, ship.y0 + um * LEN, hz + 205); i ? G.lineTo(x, y) : G.moveTo(x, y); }
        for (let i = 8; i >= 0; i--) { const q = i / 8, belly = Math.sin(q * Math.PI) * 9, [x, y] = P(ship.x - sw + 2 * sw * q, ship.y0 + (um + .012) * LEN, hz + 70); G.lineTo(x + belly * .4 + sway, y + belly); }
        G.closePath(); G.clip(); window.MeadowDock.ship(G, d2, P, t);
      };
      return { abs: { x: px, y: py, k: f.k }, alpha: ease(t / 1.2), walk: H.walk, speed: H.speed, face: H.face, over };
    },
  });

  // For tests: the camera and the hero's place at any time of the scene.
  window.IntroScene = { heroU: HERO_U, camera: t => { const o = shipAt(t); return camera(t, SHIP.x + o.dx, MID + o.dy, true); }, heroAt: t => { const o = shipAt(t); return heroAt(t, { x: SHIP.x + o.dx, y0: SHIP.y0 + o.dy }); }, dur: DUR };

  // ---- Settings > Replay intro --------------------------------------------------------------------------------------------------------
  const button = document.getElementById('set-replay-intro');
  if (button) button.addEventListener('click', () => {
    if (!window.Online?.connected) return;
    document.getElementById('set-back')?.click();
    setTimeout(() => CS.play(['intro'], { skippable: true }), 250);
  });
})();
