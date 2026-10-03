'use strict';
// Original canvas artwork for the Undervault, the dungeon under Skaldholm: stone walls, pillars, braziers, wall torches,
// sarcophagi, bones, and the two stairways (down in the city, up in the dungeon). Objects register with city.js
// (`City.art[kind] = { box, draw, animate }`); the stairways are drawn by field.js through `VaultArt`. World units are
// tiles; iso() maps them to the 2:1 screen. `Light` lists the light sources the field's darkness pass lights up.
(() => {
  const { iso, poly, line, ellipse, prism, text } = City.kit;
  const RX = 62.225, RY = 31.112;                         // screen radii of a circle of world radius 1
  const rng = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const glow = (g, color, blur, fn) => { g.save(); g.shadowColor = color; g.shadowBlur = blur; fn(); g.restore(); };
  const ring = (g, r, z, fill, stroke, lw = 2) => {      // a world-space circle of radius r at height z
    g.beginPath(); g.ellipse(0, -z, r * RX, r * RY, 0, 0, Math.PI * 2);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
  };
  // A stone drum: a cylinder of world radius r from z0 up to z1, lit from the left.
  const drum = (g, r, z0, z1, top, side, edge = '#262a38') => {
    g.beginPath(); g.ellipse(0, -z0, r * RX, r * RY, 0, 0, Math.PI); g.lineTo(-r * RX, -z1); g.ellipse(0, -z1, r * RX, r * RY, 0, Math.PI, 0, true); g.closePath();
    const grd = g.createLinearGradient(-r * RX, 0, r * RX, 0); grd.addColorStop(0, side[0]); grd.addColorStop(.5, side[1]); grd.addColorStop(1, side[2]);
    g.fillStyle = grd; g.fill(); g.strokeStyle = edge; g.lineWidth = 2; g.stroke();
    ring(g, r, z1, top, edge, 2);
  };
  const lerpColor = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const rgb = c => `rgb(${c[0]},${c[1]},${c[2]})`;

  // ---- walls: a course of ashlar blocks on both visible faces, each block a little lighter or darker --------------------------------
  // `from` and `to` are the face's two ends in tile units relative to the prism's centre, `across` fixes the other coordinate.
  function blocks(g, o, along, across, length, H, base, rand, rows = 5) {
    const rowH = H / rows;
    for (let k = 0; k < rows; k++) {
      let u = (k % 2 ? -.5 : 0) * .9;
      while (u < length) {
        const len = .8 + rand() * .55, a = Math.max(u, 0), b = Math.min(u + len, length);
        if (b > a + .05) {
          const shade = (rand() - .5) * 14, c = base.map(v => Math.max(0, Math.min(255, v + shade))), z0 = k * rowH, z1 = z0 + rowH;
          const P = (t, z) => along === 'x' ? iso(-length / 2 + t, across, z) : iso(across, -length / 2 + t, z);
          poly(g, [P(a, z0), P(b, z0), P(b, z1), P(a, z1)], rgb(c), 'rgba(12,14,24,.7)', 1.4);
        }
        u += len;
      }
    }
  }
  City.art.vaultwall = {
    box: [440, 520, 220, 410],
    draw(g, o) {
      const w = o.width, d = o.depth, H = 92, rand = rng((o.v || 0) * 977 + Math.round(w * 31 + d * 17) + 5);
      g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(8, 8, (w + d) * 24, (w + d) * 11, 0, 0, 6.283); g.fill();
      prism(g, w, d, H, '#7a8298', '#4c5368', '#333849');
      blocks(g, o, 'x', d / 2, w, H, [76, 84, 104], rand);                // the face turned to the south-west (towards the viewer's left)
      blocks(g, o, 'y', w / 2, d, H, [52, 58, 76], rand);                 // the face turned to the south-east
      // the cap stones: a lit rim round the top
      const a = iso(-w / 2, -d / 2, H), b = iso(w / 2, -d / 2, H), c = iso(w / 2, d / 2, H), e = iso(-w / 2, d / 2, H);
      g.strokeStyle = 'rgba(190,200,225,.55)'; g.lineWidth = 2; g.beginPath(); g.moveTo(...e); g.lineTo(...c); g.lineTo(...b); g.stroke();
      g.strokeStyle = 'rgba(22,24,36,.7)'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.lineTo(...c); g.lineTo(...e); g.closePath(); g.stroke();
      // damp and moss at the foot
      g.fillStyle = 'rgba(62,92,70,.32)';
      for (let i = 0; i < 4 + Math.round(w + d); i++) {
        const t = rand(), onX = rand() < .6, p = onX ? iso(-w / 2 + t * w, d / 2, 2 + rand() * 12) : iso(w / 2, -d / 2 + t * d, 2 + rand() * 12);
        g.beginPath(); g.ellipse(p[0], p[1], 7 + rand() * 9, 3 + rand() * 4, 0, 0, 6.283); g.fill();
      }
      // a crack and, on some pieces, a rune that glows faintly
      g.strokeStyle = 'rgba(10,12,20,.75)'; g.lineWidth = 1.6; g.lineJoin = 'round';
      if (rand() < .4) { const t = rand() * w, p = iso(-w / 2 + t, d / 2, 70); g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0] + 4, p[1] + 14); g.lineTo(p[0] - 3, p[1] + 26); g.lineTo(p[0] + 5, p[1] + 40); g.stroke(); }
      if ((o.v || 0) === 3 && w >= d) {
        const p = iso(0, d / 2, 46);
        glow(g, '#59d9ff', 8, () => { g.strokeStyle = 'rgba(140,230,255,.75)'; g.lineWidth = 2.2; g.lineCap = 'round'; g.beginPath(); g.moveTo(p[0] - 8, p[1] + 4); g.lineTo(p[0], p[1] - 10); g.lineTo(p[0] + 8, p[1] + 4); g.moveTo(p[0], p[1] - 10); g.lineTo(p[0], p[1] + 18); g.moveTo(p[0] - 6, p[1] + 5); g.lineTo(p[0] + 6, p[1] + 5); g.stroke(); });
      }
    },
  };

  // ---- pillars --------------------------------------------------------------------------------------------------------------------
  City.art.pillar = {
    box: [200, 330, 100, 280],
    draw(g, o) {
      g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(8, 8, 70, 28, 0, 0, 6.283); g.fill();
      const stone = [['#8a92a8', '#6d7590', '#444a62'], ['#7f879d', '#656c86', '#3e4359']][(o.v || 0) % 2];
      drum(g, .88, 0, 12, '#8f97ad', stone);                                        // plinth
      drum(g, .6, 12, 112, '#8a92a8', stone);                                       // shaft
      g.strokeStyle = 'rgba(20,24,38,.5)'; g.lineWidth = 2;                         // fluting
      for (const f of [-.3, 0, .3]) { const x = f * RX * .6 * 2; g.beginPath(); g.moveTo(x, -14); g.lineTo(x * .98, -112); g.stroke(); }
      drum(g, .76, 112, 124, '#9aa2b8', stone);                                     // capital
      drum(g, .9, 124, 134, '#a3abc0', stone);
      // a ring of faint runes round the shaft
      glow(g, '#59d9ff', 6, () => { g.strokeStyle = 'rgba(120,220,255,.5)'; g.lineWidth = 1.6; g.beginPath(); g.ellipse(0, -62, .6 * RX, .6 * RY, 0, .15, Math.PI - .15); g.stroke(); });
      if ((o.v || 0) === 1) {                                                       // a crack and a broken edge
        g.strokeStyle = 'rgba(14,16,26,.8)'; g.lineWidth = 1.8; g.beginPath(); g.moveTo(-8, -60); g.lineTo(-2, -72); g.lineTo(-10, -86); g.lineTo(-4, -100); g.stroke();
      }
    },
  };

  // ---- fire: a brazier and a torch stand. The flame is drawn live (`animate`). -------------------------------------------------------
  function flame(g, x, y, s, t, seed) {
    const a = Math.sin(t * 9 + seed) * .12, b = Math.sin(t * 13 + seed * 2) * .1, h = 36 * s * (1 + a);
    g.save(); g.translate(x, y);
    for (const [col, k] of [['rgba(255,110,30,.95)', 1], ['rgba(255,176,60,.95)', .72], ['rgba(255,236,170,.95)', .42]]) {
      g.fillStyle = col; g.beginPath(); g.moveTo(-11 * s * k, 0); g.bezierCurveTo(-13 * s * k, -h * .35 * k, -4 * s * k + b * 8, -h * .72 * k, b * 10 * s, -h * k);
      g.bezierCurveTo(5 * s * k + b * 6, -h * .66 * k, 13 * s * k, -h * .32 * k, 11 * s * k, 0); g.closePath(); g.fill();
    }
    g.restore();
  }
  function lightPool(g, x, y, r, a) {
    g.save(); g.globalCompositeOperation = 'lighter';
    const gr = g.createRadialGradient(x, y, 2, x, y, r); gr.addColorStop(0, `rgba(255,170,80,${a})`); gr.addColorStop(.45, `rgba(255,120,40,${a * .35})`); gr.addColorStop(1, 'rgba(255,100,30,0)');
    g.fillStyle = gr; g.beginPath(); g.ellipse(x, y, r, r * .55, 0, 0, 6.283); g.fill(); g.restore();
  }
  City.art.brazier = {
    box: [200, 260, 100, 200],
    draw(g, o) {
      g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(6, 6, 44, 17, 0, 0, 6.283); g.fill();
      for (const dx of [-26, 0, 26]) line(g, [[dx * .5, -46], [dx, 0]], '#252833', 6);
      g.fillStyle = '#2d313e'; g.strokeStyle = '#14161e'; g.lineWidth = 3;
      g.beginPath(); g.moveTo(-40, -52); g.lineTo(40, -52); g.lineTo(26, -30); g.lineTo(-26, -30); g.closePath(); g.fill(); g.stroke();
      ellipse(g, 0, -52, 40, 15, '#3a3f50', '#14161e');
      ellipse(g, 0, -53, 32, 11, '#e0561e');
      for (let i = 0; i < 5; i++) ellipse(g, -16 + i * 8, -54 + (i % 2) * 2, 6, 3, i % 2 ? '#ffb040' : '#ff7a28');
    },
    animate(g, o, sx, sy, t) {
      lightPool(g, sx, sy - 40, 150, .22 + .05 * Math.sin(t * 7 + o.x));
      flame(g, sx, sy - 54, 1.15, t, o.x * 3.1 + o.y);
      g.save(); g.globalAlpha = .8; g.fillStyle = '#ffd9a0';
      for (let i = 0; i < 4; i++) { const p = (t * .5 + i / 4 + o.x) % 1; g.globalAlpha = (1 - p) * .8; g.fillRect(sx + Math.sin(i * 5 + t * 2) * 14, sy - 66 - p * 58, 2, 2); }
      g.restore(); g.globalAlpha = 1;
    },
  };
  City.art.torch = {
    box: [120, 220, 60, 170],
    draw(g, o) {
      g.fillStyle = 'rgba(0,0,0,.3)'; g.beginPath(); g.ellipse(4, 4, 22, 9, 0, 0, 6.283); g.fill();
      line(g, [[0, 0], [0, -74]], '#1c1e28', 8); line(g, [[0, 0], [0, -74]], '#4a4e60', 4);
      line(g, [[-10, -4], [10, -4]], '#2d313e', 6);
      g.fillStyle = '#2d313e'; g.strokeStyle = '#14161e'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(-11, -80); g.lineTo(11, -80); g.lineTo(7, -68); g.lineTo(-7, -68); g.closePath(); g.fill(); g.stroke();
    },
    animate(g, o, sx, sy, t) {
      lightPool(g, sx, sy - 72, 110, .18 + .04 * Math.sin(t * 8 + o.x * 2));
      flame(g, sx, sy - 80, .8, t, o.x * 2.3 + o.y * 1.7);
    },
  };

  // ---- sarcophagus and bones ------------------------------------------------------------------------------------------------------------
  City.art.sarcophagus = {
    box: [240, 240, 120, 180],
    draw(g, o) {
      const lid = (o.v || 0) % 2 ? ['#8a90a2', '#5f6578', '#474c5d'] : ['#7c8498', '#585e72', '#40455a'];
      g.fillStyle = 'rgba(0,0,0,.35)'; g.beginPath(); g.ellipse(8, 8, 84, 32, 0, 0, 6.283); g.fill();
      prism(g, 1.7, .9, 24, lid[0], lid[1], lid[2]);
      prism(g, 1.5, .72, 10, '#99a0b4', '#6a7088', '#4c5167', 24);
      // a carved figure on the lid, arms crossed, and a rune at its head
      const p = (x, y) => iso(x, y, 34);
      line(g, [p(-.55, 0), p(.55, 0)], 'rgba(30,34,50,.7)', 4); line(g, [p(.2, -.18), p(.2, .18)], 'rgba(30,34,50,.7)', 3);
      ellipse(g, ...p(-.62, 0), 6, 4, 'rgba(30,34,50,.6)');
      if ((o.v || 0) === 2) { g.strokeStyle = 'rgba(14,16,26,.85)'; g.lineWidth = 2; const q = iso(.5, .3, 30); g.beginPath(); g.moveTo(...q); g.lineTo(q[0] + 8, q[1] + 10); g.lineTo(q[0] + 2, q[1] + 22); g.stroke(); }
    },
  };
  City.art.bones = {
    box: [90, 70, 45, 50],
    draw(g, o) {
      const r = rng((o.v || 0) * 53 + 3), bone = '#d6cfb6', dark = '#4a4636';
      const stick = (x0, y0, x1, y1) => { line(g, [[x0, y0], [x1, y1]], dark, 6); line(g, [[x0, y0], [x1, y1]], bone, 3.4); ellipse(g, x0, y0, 3.2, 2.6, bone, dark); ellipse(g, x1, y1, 3.2, 2.6, bone, dark); };
      stick(-20 + r() * 6, 2, 14, -6 + r() * 6); stick(-12, -8, 20, 6 + r() * 4);
      if ((o.v || 0) % 2 === 0) {                                                      // a skull
        ellipse(g, 6, -12, 11, 9, bone, dark); ellipse(g, 6, -3, 7, 4, '#cbc4aa', dark);
        ellipse(g, 2, -13, 2.6, 3, '#1c1a14'); ellipse(g, 10, -13, 2.6, 3, '#1c1a14');
      } else { for (let i = 0; i < 3; i++) { g.strokeStyle = dark; g.lineWidth = 5; g.beginPath(); g.arc(-4 + i * 9, -2, 9, Math.PI * 1.05, Math.PI * 1.95); g.stroke(); g.strokeStyle = bone; g.lineWidth = 2.6; g.stroke(); } }
    },
  };

  // ---- the stairways, drawn by field.js's drawPortal --------------------------------------------------------------------------------------
  // Stairs down (in Skaldholm, beside the Meeting Stone): a stone-rimmed stairwell whose steps run north, away from you, down into
  // a dark tunnel mouth with a blue glow. You step on from the south. It is centred on the portal; the posts around it are collision only.
  function stairsDown(g, sx, sy, t, title = 'Stairs to the Undervault') {
    g.save(); g.translate(sx, sy);
    const P = (x, y, z = 0) => iso(x, y, z), X0 = -1.7, X1 = 1.7, Y0 = -2.0, Y1 = 1.2;
    const face = (pts, fill, stroke = null) => poly(g, pts, fill, stroke, 1.2);
    // paving round the opening
    face([P(-2.25, -2.6), P(2.25, -2.6), P(2.25, 1.75), P(-2.25, 1.75)], '#a39b88', '#4a4234');
    // the dark pit, the far wall going down into a tunnel mouth, and the west wall's inner face
    face([P(X0, Y0), P(X1, Y0), P(X1, Y1), P(X0, Y1)], '#05060a');
    const wall = g.createLinearGradient(0, P(0, Y0, 0)[1], 0, P(0, Y0, -60)[1]); wall.addColorStop(0, '#62697c'); wall.addColorStop(1, '#10131c');
    face([P(X0, Y0, 0), P(X1, Y0, 0), P(X1, Y0, -64), P(X0, Y0, -64)], wall, null);
    face([P(X0, Y0, 0), P(X0, Y1, 0), P(X0, Y1, -52), P(X0, Y0, -52)], '#2b3042', null);
    glow(g, '#59d9ff', 24 + 8 * Math.sin(t * 1.7), () => { const q = P(0, Y0, -44); g.fillStyle = 'rgba(80,190,255,.32)'; g.beginPath(); g.ellipse(q[0], q[1], 54, 20, 0, 0, 6.283); g.fill(); });
    // the tunnel mouth itself: an arch of black
    { const l = P(-.95, Y0, -64), r = P(.95, Y0, -64), top = P(0, Y0, -8); g.fillStyle = '#020306'; g.beginPath(); g.moveTo(...l); g.lineTo(l[0], P(0, Y0, -26)[1]); g.quadraticCurveTo(top[0], top[1] - 14, r[0], P(0, Y0, -26)[1]); g.lineTo(...r); g.closePath(); g.fill(); }
    // steps, deepest first: each further north and lower, darker the deeper it goes
    const steps = 7, run = (Y1 - Y0) / steps;
    for (let k = steps - 1; k >= 0; k--) {
      const y1 = Y1 - k * run, y0 = y1 - run, z = -k * 6, shade = 1 - k / (steps + .5);
      const tread = lerpColor([30, 34, 48], [176, 172, 184], shade), riser = lerpColor([10, 12, 18], [84, 82, 98], shade);
      face([P(X0, y1, z), P(X1, y1, z), P(X1, y1, z - 6), P(X0, y1, z - 6)], rgb(riser));
      face([P(X0, y0, z), P(X1, y0, z), P(X1, y1, z), P(X0, y1, z)], rgb(tread), 'rgba(8,8,14,.5)');
    }
    // parapets: north (behind), west and east, and short stubs either side of the way in
    const parapet = (cx, cy, w, d, h = 17) => { g.save(); g.translate(...P(cx, cy)); prism(g, w, d, h, '#bdb5a4', '#948c7a', '#726a5a'); g.restore(); };
    parapet(0, -2.3, 4.9, .6); parapet(-1.98, -.4, .5, 3.4); parapet(1.98, -.4, .5, 3.4);
    // the lantern pillars either side of the way in
    for (const side of [-1, 1]) {
      g.save(); g.translate(...P(side * 1.95, 1.55));
      prism(g, .55, .55, 62, '#bdb5a4', '#948c7a', '#726a5a');
      prism(g, .7, .7, 8, '#c9c1b0', '#9c9482', '#7a7262', 62);
      g.fillStyle = '#ffd890'; g.strokeStyle = '#3a3226'; g.lineWidth = 2; g.beginPath(); g.moveTo(-8, -78); g.lineTo(8, -78); g.lineTo(6, -96); g.lineTo(-6, -96); g.closePath(); g.fill(); g.stroke();
      g.restore();
      glow(g, '#ffb860', 16, () => { const q = P(side * 1.95, 1.55, 87); g.fillStyle = 'rgba(255,200,120,.4)'; g.beginPath(); g.arc(q[0], q[1], 9, 0, 6.283); g.fill(); });
    }
    const label = P(0, -2.6, 36);
    text(g, title, label[0], label[1] - 6, 16, '#a9ecff');
    g.restore();
  }
  // Stairs up (in the dungeon's first hall): steps climbing west into a doorway in the wall, daylight spilling down them.
  function stairsUp(g, sx, sy, t) {
    g.save(); g.translate(sx, sy);
    const P = (x, y, z = 0) => iso(x, y, z);
    // a pale pool of daylight on the floor in front of the stairs
    g.save(); g.globalCompositeOperation = 'lighter';
    const q = P(1.4, 0, 0), gr = g.createRadialGradient(q[0], q[1], 4, q[0], q[1], 200); gr.addColorStop(0, 'rgba(255,236,190,.34)'); gr.addColorStop(1, 'rgba(255,236,190,0)');
    g.fillStyle = gr; g.beginPath(); g.ellipse(q[0], q[1], 200, 105, 0, 0, 6.283); g.fill(); g.restore();
    const steps = 5, run = .62, rise = 7, x0 = 1.9;
    // the doorway of light in the wall at the top of the stairs (the +x face of the wall)
    const doorX = x0 - steps * run, top0 = steps * rise;
    glow(g, '#ffe3a0', 26 + 6 * Math.sin(t * 1.3), () => {
      g.fillStyle = 'rgba(255,240,200,.96)'; g.beginPath();
      const a = P(doorX, -1.05, top0), b = P(doorX, 1.05, top0), c = P(doorX, 1.05, top0 + 38), d = P(doorX, -1.05, top0 + 38), m = P(doorX, 0, top0 + 62);
      g.moveTo(...a); g.lineTo(...b); g.lineTo(...c); g.quadraticCurveTo(m[0], m[1] - 8, d[0], d[1]); g.closePath(); g.fill();
    });
    for (let k = steps - 1; k >= 0; k--) {
      const x1 = x0 - k * run, z0 = k * rise, shade = .3 + .7 * (k / steps);
      const tread = lerpColor([86, 90, 108], [252, 242, 216], shade), riser = lerpColor([46, 50, 66], [208, 194, 162], shade);
      poly(g, [P(x1, -1.4, z0), P(x1, 1.4, z0), P(x1, 1.4, z0 + rise), P(x1, -1.4, z0 + rise)], rgb(riser), 'rgba(12,12,20,.5)', 1.2);
      poly(g, [P(x1 - run, -1.4, z0 + rise), P(x1, -1.4, z0 + rise), P(x1, 1.4, z0 + rise), P(x1 - run, 1.4, z0 + rise)], rgb(tread), 'rgba(12,12,20,.4)', 1.2);
    }
    for (const side of [-1, 1]) { g.save(); g.translate(...P(x0 - steps * run / 2 + .3, side * 1.7)); prism(g, steps * run + .8, .45, 36, '#8a90a6', '#5c637a', '#40465a'); g.restore(); }
    const label = P(.4, -2.1, 100);
    text(g, 'Stairs up', label[0], label[1], 16, '#ffe9b0');
    g.restore();
  }
  // The magic portal that opens when the Hollow King falls (grows in over a second and a half, then swirls).
  function exitPortal(g, sx, sy, t, age = 9) {
    const k = Math.max(0, Math.min(1, age / 1.6)), e = 1 - (1 - k) * (1 - k);
    g.save(); g.translate(sx, sy);
    const R = 1.5 * e;
    glow(g, '#9cff8f', 26, () => { ring(g, R, 0, 'rgba(20,50,30,.7)', '#b8ffa8', 3); });
    for (let i = 0; i < 4; i++) {
      const a = t * (1.1 + i * .3) + i * 1.9, rr = R * (.35 + i * .2);
      g.save(); g.globalCompositeOperation = 'lighter'; g.strokeStyle = `rgba(${150 + i * 25},255,${170 + i * 20},${.5 - i * .08})`; g.lineWidth = 3;
      g.beginPath(); g.ellipse(0, 0, rr * RX, rr * RY, 0, a, a + 3.4); g.stroke(); g.restore();
    }
    g.save(); g.globalCompositeOperation = 'lighter';
    const col = g.createLinearGradient(0, -190 * e, 0, 0); col.addColorStop(0, 'rgba(160,255,160,0)'); col.addColorStop(1, 'rgba(160,255,170,.45)');
    g.fillStyle = col; g.beginPath(); g.ellipse(0, -90 * e, R * RX * .8, 100 * e, 0, 0, 6.283); g.fill(); g.restore();
    for (let i = 0; i < 10; i++) {                                    // motes rising off the portal
      const s = (t * .3 + i / 10) % 1, a = i * 2.3 + t * .6;
      g.globalAlpha = Math.sin(s * Math.PI) * .8 * e; g.fillStyle = '#d4ffc8';
      g.fillRect(Math.cos(a) * R * RX * .8 * (1 - s * .4) - 1, -s * 150 + Math.sin(a) * R * RY * .8, 2.6, 2.6);
    }
    g.globalAlpha = 1;
    if (e > .6) text(g, 'The Way Out', 0, -166, 17, '#d4ffc8');
    g.restore();
  }
  window.VaultArt = { stairsDown, stairsUp, exitPortal, flame, lightPool };
})();
