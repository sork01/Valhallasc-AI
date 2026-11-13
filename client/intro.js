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
  function heroAt(t, ship) {
    const aft = ease((t - 53.2) / 3), u = lerp(HERO_U, PLANK_U, aft), gang = ease((t - 56.2) / 2.8);
    const lift = bump(t, 47.2, 48.8, 50.4, 52) * 9, swell = bob(t) * (1 - gang);
    return {
      x: lerp(ship.x, D.start.x, gang), y: lerp(ship.y0 + u * LEN, D.start.y, gang), z: lerp(deckZ(u) + 2, 7, gang) + swell + lift,
      walk: t > 53.2 && t < 56.2 ? [0, 1] : t >= 56.2 && t < 59 ? [1, 0] : null, face: t < 56.2 ? [0, -1] : [1, 0],
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
  function sky(g, w, h, t, warm) {
    const forge = bump(t, 3, 5.5, 20, 24), hall = bump(t, 12.5, 15, 22, 25), roots = bump(t, 24, 26.5, 36, 40);
    // The ember glow along the edges.
    const glow = g.createRadialGradient(w / 2, h / 2, Math.min(w, h) * .35, w / 2, h / 2, Math.max(w, h) * .75);
    glow.addColorStop(0, 'rgba(255,90,30,0)'); glow.addColorStop(1, `rgba(255,70,20,${.5 * warm})`); g.fillStyle = glow; g.fillRect(0, 0, w, h);
    const px = w * .22, py = h * .26;
    if (forge > .01) {   // a far mountain with a ring of fire: the first forge under the roots
      g.save(); g.globalAlpha = forge; g.fillStyle = '#26151a'; g.beginPath(); g.moveTo(w * .03, h * .5); g.lineTo(px - 30, py + 14); g.lineTo(px, py - 12); g.lineTo(px + 40, py + 16); g.lineTo(w * .44, h * .5); g.closePath(); g.fill();
      const rg = g.createRadialGradient(px, py - 6, 4, px, py - 6, 120); rg.addColorStop(0, 'rgba(255,210,120,.95)'); rg.addColorStop(.3, 'rgba(255,120,40,.55)'); rg.addColorStop(1, 'rgba(255,80,20,0)'); g.fillStyle = rg; g.fillRect(px - 130, py - 130, 260, 260);
      g.strokeStyle = `rgba(255,${170 + Math.round(Math.sin(t * 6) * 30)},70,.95)`; g.lineWidth = 5; g.beginPath(); g.ellipse(px, py - 6, 30 + Math.sin(t * 3) * 2, 10, 0, 0, Math.PI * 2); g.stroke(); g.restore();
    }
    if (hall > .01) {    // the gods' hall: a pale gold light with an empty seat
      const hx = w * .8, gr = g.createLinearGradient(hx, 0, hx, h * .46); gr.addColorStop(0, `rgba(255,236,170,${.6 * hall})`); gr.addColorStop(1, 'rgba(255,236,170,0)');
      g.fillStyle = gr; g.beginPath(); g.moveTo(hx - 16, 0); g.lineTo(hx + 16, 0); g.lineTo(hx + 90, h * .46); g.lineTo(hx - 90, h * .46); g.closePath(); g.fill();
      g.save(); g.globalAlpha = hall * .95; g.fillStyle = '#2a2030'; g.fillRect(hx - 9, h * .27, 18, 24); g.fillRect(hx - 13, h * .27 + 24, 26, 6); g.fillRect(hx - 13, h * .27 + 30, 4, 12); g.fillRect(hx + 9, h * .27 + 30, 4, 12); g.restore();
    }
    // The nine chains from the hall to the forge: they appear one by one, then fail one by one.
    for (let i = 0; i < 9; i++) {
      const born = 14.5 + i * .35, dies = 26.5 + i * .9, a = ease((t - born) / .6) * (1 - ease((t - dies) / .8));
      if (a < .02) continue;
      const sx = w * (.18 + i * .075), fall = Math.max(0, t - dies), cx0 = (sx + px) / 2 + Math.sin(i) * 30, cy0 = h * (.08 + (i % 3) * .02);
      g.save(); g.globalAlpha = a * .9;
      // A thin cable under the links so the chain reads as one line, then big links, each turned a quarter from the last.
      const at = u => [(1 - u) * (1 - u) * sx + 2 * u * (1 - u) * cx0 + u * u * px, 2 * u * (1 - u) * cy0 + u * u * (py - 6)];
      if (fall < .3) { g.strokeStyle = 'rgba(120,132,160,.55)'; g.lineWidth = 3; g.beginPath(); for (let k = 0; k <= 20; k++) { const [x, y] = at(k / 20); k ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); }
      g.fillStyle = '#dfe6f2'; g.strokeStyle = '#4f5a78'; g.lineWidth = 2;
      for (let k = 0; k <= 12; k++) {
        const [x, y] = at(k / 12), [x2, y2] = at(Math.min(1, (k + 1) / 12)), ang = Math.atan2(y2 - y, x2 - x);
        g.save(); g.translate(x + (fall * 14) * (rnd(i + k) - .5), y + fall * fall * 70 * rnd(i * 3 + k)); g.rotate(ang);
        g.beginPath(); g.ellipse(0, 0, k % 2 ? 6 : 10, k % 2 ? 6 : 4.5, 0, 0, Math.PI * 2); g.fill(); g.stroke(); g.restore();
      }
      g.restore();
    }
    if (roots > .01) {   // the roots that hold up the sky begin to burn
      g.save(); g.lineCap = 'round';
      for (let i = 0; i < 7; i++) {
        const x = w * (.1 + i * .13), len = h * (.14 + rnd(i) * .1) * roots;
        g.strokeStyle = '#3a2216'; g.lineWidth = 6; g.beginPath(); g.moveTo(x, 0); g.quadraticCurveTo(x + Math.sin(t + i) * 16, len * .5, x + (rnd(i + 5) - .5) * 40, len); g.stroke();
        g.strokeStyle = `rgba(255,${130 + Math.round(Math.sin(t * 7 + i) * 50)},40,${.85 * roots})`; g.lineWidth = 2.5; g.stroke();
      }
      g.restore();
    }
    const s = keyed(t, SPARKS);
    g.save(); for (let i = 0; i < 70; i++) {
      const u = (t * (.08 + rnd(i) * .1) + rnd(i + 9)) % 1, x = rnd(i + 3) * w + Math.sin(t + i) * 20, y = h * (1.02 - u * 1.1);
      g.globalAlpha = s * (1 - u) * (.4 + rnd(i + 7) * .6); g.fillStyle = i % 3 ? '#ffb14a' : '#ffe08a'; g.beginPath(); g.arc(x, y, 1.2 + rnd(i + 11) * 2.2, 0, Math.PI * 2); g.fill();
    } g.restore();
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
    dur: DUR, captions: LINES, music: 'assets/music_intro.mp3',
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
      sky(g, w, h, t, warm);
      // A soft vignette for the film look; it lifts as the scene settles into the game's own view.
      const vig = .42 * (1 - e);
      if (vig > .01) { const v = g.createRadialGradient(w / 2, h / 2, Math.min(w, h) * .38, w / 2, h / 2, Math.hypot(w, h) * .6); v.addColorStop(0, 'rgba(4,6,14,0)'); v.addColorStop(1, `rgba(4,6,14,${vig})`); g.fillStyle = v; g.fillRect(0, 0, w, h); }
      c.flash = c.still ? 0 : Math.max(0, 1 - Math.abs(t - 48.8) / .22) * .85;
      c.veil = 0;
      return { abs: { x: px, y: py, k: f.k }, alpha: ease(t / 1.2), walk: H.walk, face: H.face };
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
