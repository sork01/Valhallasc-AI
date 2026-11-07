// Greenmeadow's landing dock (zone shapes pilot; scripts/greenmeadow_dock.py): a timber pier from the Saltgrass Strand out over
// the shallows and the ship that brought new heroes, moored along its west side. Both are drawn in world space in the ground
// pass, under every actor: the ship lies west of the pier (behind it on screen) and the pier is flat, so nothing on the
// pier ever stands behind either of them.
(() => {
  const OL = '#1c1428';
  const poly = (g, pts, fill, stroke, lw = 2) => {
    g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath();
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.lineJoin = 'round'; g.stroke(); }
  };
  const line = (g, pts, color, lw) => { g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.strokeStyle = color; g.lineWidth = lw; g.lineCap = 'round'; g.lineJoin = 'round'; g.stroke(); };
  const DECK = 7;            // the pier's planks stand this many pixels above the water

  function post(g, w2s, x, y, top, r = 5) {
    const [bx, by] = w2s(x, y, -9), [tx, ty] = w2s(x, y, top);
    g.fillStyle = 'rgba(12,30,36,.35)'; g.beginPath(); g.ellipse(bx, by + 2, r + 4, (r + 4) / 2, 0, 0, Math.PI * 2); g.fill();
    poly(g, [[bx - r, by], [tx - r, ty], [tx + r, ty], [bx + r, by]], '#5b3f26', OL, 2);
    g.fillStyle = '#3a2a1c'; g.fillRect(bx - r + 1, by - 7, r * 2 - 2, 6);                          // wet, weedy foot
    g.fillStyle = '#4f7a52'; g.fillRect(bx - r + 1, by - 9, r * 2 - 2, 2);
    g.fillStyle = '#8a6844'; g.beginPath(); g.ellipse(tx, ty, r, r / 2, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = OL; g.lineWidth = 1.5; g.stroke();
    g.fillStyle = 'rgba(255,230,180,.25)'; g.fillRect(tx - r + 2, ty + 2, 2, by - ty - 10);
  }

  function pier(g, d, w2s, t) {
    const x0 = d.x0, x1 = d.x1, y0 = d.y0, y1 = d.y1, P = (x, y, z = DECK) => w2s(x, y, z);
    const zAt = y => y < y0 + 1.6 ? 2 + (y - y0) / 1.6 * (DECK - 2) : DECK;                          // a short ramp up from the sand
    // shadow on the water and the far-side piles (behind the planks)
    poly(g, [P(x0 - .3, y0 + 3, -2), P(x1 + .5, y0 + 3, -2), P(x1 + .5, y1 + .5, -2), P(x0 - .3, y1 + .5, -2)], 'rgba(10,26,32,.32)');
    for (let y = y0 + 4.5; y < y1; y += 2.2) post(g, w2s, x0 + .2, y, DECK + 3, 4);
    // the near side beam (+x) and the end beam (+y) hang down to the water
    poly(g, [P(x1, y0, zAt(y0)), P(x1, y1, DECK), P(x1, y1, -7), P(x1, y0 + 3.2, -7), P(x1, y0 + 1.6, 0)], '#4a3320', OL);
    poly(g, [P(x0, y1, DECK), P(x1, y1, DECK), P(x1, y1, -7), P(x0, y1, -7)], '#3f2b1b', OL);
    // the deck: boards laid across the pier
    poly(g, [P(x0, y0, zAt(y0)), P(x1, y0, zAt(y0)), P(x1, y0 + 1.6), P(x1, y1), P(x0, y1), P(x0, y0 + 1.6)], '#93704a', OL);
    for (let y = y0, i = 0; y < y1 - .01; y += .5, i++) {
      const tone = [0, 6, -4, 3, -7, 2][i % 6], a = Math.min(y + .5, y1);
      poly(g, [P(x0 + .05, y, zAt(y)), P(x1 - .05, y, zAt(y)), P(x1 - .05, a, zAt(a)), P(x0 + .05, a, zAt(a))], `hsl(33, ${38 + tone}%, ${43 + tone}%)`);
      line(g, [P(x0 + .05, a, zAt(a)), P(x1 - .05, a, zAt(a))], 'rgba(40,24,10,.55)', 1.2);
      if (i % 3 === 1) for (const nx of [x0 + .25, x1 - .25]) { const [px, py] = P(nx, y + .25, zAt(y + .25)); g.fillStyle = '#3b2c22'; g.fillRect(px - 1, py - 1, 2, 2); }
    }
    line(g, [P(x0 + .12, y0 + 1.6), P(x0 + .12, y1)], 'rgba(255,230,180,.25)', 2);                      // worn tread along the edges
    line(g, [P(x1 - .12, y0 + 1.6), P(x1 - .12, y1)], 'rgba(40,24,10,.35)', 2);
    // near-side piles stand in front of the beam; bollards on the ship's side
    for (let y = y0 + 4.5; y < y1; y += 2.2) post(g, w2s, x1 - .15, y, DECK + 3, 4);
    post(g, w2s, x1 - .15, y1 - .1, DECK + 3, 4);
    post(g, w2s, x0 + .2, y1 - .1, DECK + 3, 4);
    for (const by of d.bollards) {
      const [bx, bz] = P(x0 + .35, by, DECK);
      poly(g, [[bx - 5, bz], [bx - 4, bz - 13], [bx + 4, bz - 13], [bx + 5, bz]], '#4b4540', OL, 1.5);
      g.fillStyle = '#6d655c'; g.beginPath(); g.ellipse(bx, bz - 13, 6, 3, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = OL; g.lineWidth = 1.5; g.stroke();
    }
    // a coil of rope and a net-mending stool by the root
    const [cx, cy] = P(x1 - .6, y0 + 3.3);
    for (let k = 0; k < 3; k++) { g.strokeStyle = k % 2 ? '#c9b07a' : '#a88c58'; g.lineWidth = 2.4; g.beginPath(); g.ellipse(cx, cy - k * 2, 9 - k, 4.5 - k / 2, 0, 0, Math.PI * 2); g.stroke(); }
    // the sea laps at the piles
    g.strokeStyle = 'rgba(225,246,250,.55)'; g.lineWidth = 1.4;
    for (let y = y0 + 4.5; y < y1; y += 2.2) for (const x of [x0 + .2, x1 - .15]) {
      const [px, py] = w2s(x, y, -9), s = (Math.sin(t * 1.7 + y * 1.3 + x) + 1) / 2;
      g.beginPath(); g.ellipse(px, py + 1, 7 + s * 3, 3 + s * 1.5, 0, 0, Math.PI * 2); g.stroke();
    }
  }

  function ship(g, d, w2s, t) {
    const s = d.ship, L = s.y1 - s.y0, B = s.beam / 2, bob = Math.sin(t * .9) * 1.6;
    const half = u => B * Math.pow(Math.max(0, 1 - (2 * u - 1) ** 2), .55);
    const H = u => 30 + 26 * (2 * u - 1) ** 4;                                        // the sheer rises to both stems
    const P = (u, v, z) => w2s(s.x + v, s.y0 + u * L, z + bob);
    const N = 28, us = Array.from({ length: N + 1 }, (_, i) => i / N);
    // shadow and the darker water round the hull
    g.fillStyle = 'rgba(8,24,34,.38)';
    poly(g, [...us.map(u => P(u, half(u) + .6, -1)), ...us.slice().reverse().map(u => P(u, -half(u) - .3, -1))], 'rgba(8,24,34,.34)');
    // the far side's inner planking, the deck, cargo
    poly(g, [...us.map(u => P(u, -half(u), H(u))), ...us.slice().reverse().map(u => P(u, -half(u) * .86, H(u) - 16))], '#5e3f26', OL);
    poly(g, [...us.map(u => P(u, -half(u) * .86, H(u) - 16)), ...us.slice().reverse().map(u => P(u, half(u) * .86, H(u) - 16))], '#7c5a38');
    for (let u = .12; u < .9; u += .055) line(g, [P(u, -half(u) * .84, H(u) - 16), P(u, half(u) * .84, H(u) - 16)], 'rgba(40,24,10,.45)', 1.2);
    for (let u = .14; u < .88; u += .085) {                                              // rowing benches
      const z = H(u) - 9; poly(g, [P(u, -half(u) * .8, z), P(u, half(u) * .8, z), P(u + .018, half(u) * .8, z), P(u + .018, -half(u) * .8, z)], '#a07a4c', OL, 1);
    }
    const crate = (u, v, sz, c) => { const z = H(u) - 16, [x, y] = P(u, v, z); poly(g, [[x - sz, y], [x - sz, y - sz * 1.3], [x + sz, y - sz * 1.3], [x + sz, y]], c, OL, 1.5); line(g, [[x - sz, y - sz * .65], [x + sz, y - sz * .65]], 'rgba(40,24,10,.5)', 1); };
    crate(.66, -.2, 9, '#9c7646'); crate(.7, .55, 7, '#8a6a3e');
    const barrel = (u, v) => { const z = H(u) - 16, [x, y] = P(u, v, z); g.fillStyle = '#7a5532'; g.fillRect(x - 6, y - 15, 12, 15); g.strokeStyle = OL; g.lineWidth = 1.5; g.strokeRect(x - 6, y - 15, 12, 15); g.fillStyle = '#3d3a38'; g.fillRect(x - 6, y - 12, 12, 2); g.fillRect(x - 6, y - 5, 12, 2); };
    barrel(.3, .3); barrel(.34, -.4);
    // the mast and its sail (across the ship), behind the near hull
    const um = .47, [mx, my] = P(um, 0, H(um) - 16), [tx, ty] = P(um, 0, H(um) + 235);
    const top = P(um, 0, H(um) + 228);
    line(g, [top, P(0, 0, H(0) + 52)], 'rgba(40,28,18,.8)', 1.4);                        // forestay and backstay
    line(g, [top, P(1, 0, H(1) + 44)], 'rgba(40,28,18,.8)', 1.4);
    for (const v of [-1, 1]) for (const du of [-.05, .05]) line(g, [top, P(um + du, v * half(um + du), H(um + du))], 'rgba(40,28,18,.7)', 1.1);
    poly(g, [[mx - 4, my], [tx - 3, ty], [tx + 3, ty], [mx + 4, my]], '#6b4a2c', OL, 2);
    const yardZ = H(um) + 205, footZ = H(um) + 70, sw = B * 1.35, sway = Math.sin(t * .7) * 3;
    const sail = (a, b) => { const k = 8, pts = []; for (let i = 0; i <= k; i++) { const v = -sw + (2 * sw) * (a + (b - a) * i / k); pts.push(P(um, v, yardZ)); } for (let i = k; i >= 0; i--) { const f = a + (b - a) * i / k, v = -sw + 2 * sw * f, belly = Math.sin(f * Math.PI) * 9; const [x, y] = P(um + .012, v, footZ); pts.push([x + belly * .4 + sway, y + belly]); } return pts; };
    for (let i = 0; i < 6; i++) poly(g, sail(i / 6, (i + 1) / 6), i % 2 ? '#efe2c4' : '#b8382f');
    poly(g, sail(0, 1), null, OL, 2.2);
    line(g, [P(um, -sw - .3, yardZ), P(um, sw + .3, yardZ)], '#4e3520', 5);
    line(g, [P(um, -sw - .3, yardZ), P(um, sw + .3, yardZ)], '#7a5734', 2.5);
    // the near hull side: lapped strakes from the waterline to the rail
    const side = [...us.map(u => P(u, half(u), H(u))), ...us.slice().reverse().map(u => P(u, half(u) * .78, 0))];
    poly(g, side, '#6b4426', OL, 2.4);
    for (let k = 1; k <= 4; k++) {
      const f = k / 5; line(g, us.map(u => P(u, half(u) * (1 - .22 * f), H(u) * (1 - f))), k % 2 ? 'rgba(30,18,10,.55)' : 'rgba(255,214,160,.18)', 1.6);
    }
    line(g, us.map(u => P(u, half(u), H(u))), '#a77b4c', 3);                            // the gunwale
    for (let u = .2; u <= .8; u += .075) {                                              // shields on the rail
      const [x, y] = P(u, half(u) + .05, H(u) - 4), c = ['#c4473b', '#e8c45a', '#3f6fa8', '#ece4d0'][Math.round(u / .075) % 4];
      g.fillStyle = c; g.beginPath(); g.ellipse(x, y, 9, 8, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = OL; g.lineWidth = 1.6; g.stroke();
      g.fillStyle = '#8a8f96'; g.beginPath(); g.arc(x, y, 2.6, 0, Math.PI * 2); g.fill();
    }
    // stems: a dragon at the bow (towards the beach), a curl at the stern
    const stem = (u, dir, h) => { const pts = []; for (let i = 0; i <= 10; i++) { const f = i / 10; pts.push(P(u + dir * .03 * Math.sin(f * 1.4), 0, H(u) + f * h)); } return pts; };
    const bow = stem(0, -1, 58), stern = stem(1, 1, 50);
    line(g, bow, OL, 9); line(g, bow, '#7a5230', 5.5);
    line(g, stern, OL, 9); line(g, stern, '#7a5230', 5.5);
    const [hx, hy] = bow[bow.length - 1];
    poly(g, [[hx - 3, hy + 2], [hx + 10, hy - 6], [hx + 18, hy - 2], [hx + 9, hy + 4], [hx + 2, hy + 8]], '#7a5230', OL, 2);   // the dragon's head
    g.fillStyle = '#e8c45a'; g.fillRect(hx + 8, hy - 3, 2.5, 2.5);
    const [ex, ey] = stern[stern.length - 1];
    g.beginPath(); g.arc(ex - 6, ey + 1, 6, -Math.PI * .1, Math.PI * 1.3); g.strokeStyle = OL; g.lineWidth = 8; g.stroke(); g.strokeStyle = '#7a5230'; g.lineWidth = 4.5; g.stroke();
    // the steering oar on the starboard quarter
    line(g, [P(.86, half(.86) + .1, H(.86) + 8), P(.95, half(.95) + .5, -6)], '#5b3f26', 4);
    // waterline ripples along the near side
    g.strokeStyle = 'rgba(230,248,252,.6)'; g.lineWidth = 1.5;
    for (let u = .08; u < .95; u += .11) { const [x, y] = P(u, half(u) * .8 + .25, -bob), o = Math.sin(t * 2 + u * 20) * 3; g.beginPath(); g.moveTo(x - 8 + o, y + 1); g.quadraticCurveTo(x + o, y - 2, x + 8 + o, y + 1); g.stroke(); }
  }

  function moor(g, d, w2s) {
    const s = d.ship, L = s.y1 - s.y0, B = s.beam / 2, bob = 0;
    const half = u => B * Math.pow(Math.max(0, 1 - (2 * u - 1) ** 2), .55);
    const H = u => 30 + 26 * (2 * u - 1) ** 4;
    const P = (u, v, z) => w2s(s.x + v, s.y0 + u * L, z + bob);
    // the gangplank to the pier, and mooring lines to the bollards
    const pu = (s.plank - s.y0) / L, a = P(pu, half(pu) - .1, H(pu) - 2), b = w2s(d.x0 + .4, s.plank, DECK), a2 = P(pu + .07, half(pu + .07) - .1, H(pu + .07) - 2), b2 = w2s(d.x0 + .4, s.plank + .8, DECK);
    poly(g, [a, b, b2, a2], '#a8814f', OL, 2);
    for (let k = 1; k < 5; k++) { const f = k / 5; line(g, [[a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], [a2[0] + (b2[0] - a2[0]) * f, a2[1] + (b2[1] - a2[1]) * f]], 'rgba(40,24,10,.55)', 1.4); }
    for (const [u, by] of [[.08, d.bollards[0]], [.94, d.bollards[1]]]) {
      const [rx, ry] = P(u, half(u), H(u)), [qx, qy] = w2s(d.x0 + .35, by, DECK + 11);
      g.beginPath(); g.moveTo(rx, ry); g.quadraticCurveTo((rx + qx) / 2, Math.max(ry, qy) + 16, qx, qy); g.strokeStyle = '#c9b07a'; g.lineWidth = 2; g.stroke();
    }
  }

  window.MeadowDock = {
    draw(g, zdef, w2s, t) {
      const d = zdef.dock; if (!d) return;
      const s = d.ship;
      d.bollards = d.bollards || [s.y0 + 1.6, s.y1 - 1.4];
      const [cx, cy] = w2s((d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2), W = g.canvas.width, Hh = g.canvas.height;
      if (cx < -900 || cx > W + 900 || cy < -700 || cy > Hh + 700) return;
      ship(g, d, w2s, t);
      pier(g, d, w2s, t);
      moor(g, d, w2s);
    },
  };
})();
