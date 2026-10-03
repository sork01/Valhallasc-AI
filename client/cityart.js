'use strict';
// Original canvas artwork for Skaldholm's landmarks, registered with city.js: the city wall (rampart, tower), the Grand
// Fountain, the Meeting Stone, banners, statues, a well and barrels. Each entry draws once into a sprite; `animate` adds the
// moving parts (jets, glowing runes) every frame. World units are tiles; iso() maps them to the 2:1 screen.
(() => {
  const { iso, poly, line, ellipse, prism, text } = City.kit;
  const RX = 62.225, RY = 31.112;                        // screen radii of a circle of world radius 1
  const ring = (g, r, z, fill, stroke, lw = 2) => {      // a world-space circle of radius r at height z
    g.beginPath(); g.ellipse(0, -z, r * RX, r * RY, 0, 0, Math.PI * 2);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
  };
  // A stone drum: a cylinder of world radius r from z0 up to z1, lit from the left.
  const drum = (g, r, z0, z1, top, side, edge = '#6c716c') => {
    g.beginPath(); g.ellipse(0, -z0, r * RX, r * RY, 0, 0, Math.PI); g.lineTo(-r * RX, -z1); g.ellipse(0, -z1, r * RX, r * RY, 0, Math.PI, 0, true); g.closePath();
    const grd = g.createLinearGradient(-r * RX, 0, r * RX, 0); grd.addColorStop(0, side[0]); grd.addColorStop(.55, side[1]); grd.addColorStop(1, side[2]);
    g.fillStyle = grd; g.fill(); g.strokeStyle = edge; g.lineWidth = 2; g.stroke();
    ring(g, r, z1, top, edge, 2);
  };
  const glow = (g, color, blur, fn) => { g.save(); g.shadowColor = color; g.shadowBlur = blur; fn(); g.restore(); };

  // ---- the city wall ---------------------------------------------------------------------------------------------------
  City.art.rampart = {
    draw(g, o) {
      const w = o.width, d = o.depth, H = 108, horizontal = w >= d, L = horizontal ? w : d;
      g.fillStyle = 'rgba(30,40,20,.22)'; g.beginPath(); g.ellipse(10, 14, (w + d) * 27, (w + d) * 13, 0, 0, 6.283); g.fill();
      prism(g, w, d, H, '#e6dfc9', '#d4ccb2', '#a9a38c');
      // courses of ashlar on both visible faces
      for (let z = 18; z < H; z += 18) {
        line(g, [iso(-w / 2, d / 2, z), iso(w / 2, d / 2, z)], 'rgba(90,84,66,.45)', 1.4);
        line(g, [iso(w / 2, -d / 2, z), iso(w / 2, d / 2, z)], 'rgba(70,66,52,.45)', 1.4);
      }
      for (let k = 0, z = 0; z < H - 6; z += 18, k++) {
        for (let t = (k % 2 ? .6 : 0); t < L; t += 1.2) {
          const a = horizontal ? iso(-w / 2 + t, d / 2, z) : iso(w / 2, -d / 2 + t, z), b = horizontal ? iso(-w / 2 + t, d / 2, z + 18) : iso(w / 2, -d / 2 + t, z + 18);
          line(g, [a, b], 'rgba(90,84,66,.35)', 1.2);
        }
      }
      // merlons along the top, back to front
      const n = Math.floor(L / 1.2);
      for (let i = 0; i < n; i++) {
        const c = -L / 2 + (i + .5) * (L / n);
        g.save(); g.translate(...(horizontal ? iso(c, 0, H) : iso(0, c, H)));
        if (horizontal) prism(g, L / n * .55, d, 20, '#eee8d4', '#d9d1b8', '#b0aa92'); else prism(g, w, L / n * .55, 20, '#eee8d4', '#d9d1b8', '#b0aa92');
        g.restore();
      }
    },
  };
  City.art.tower = {
    box: [360, 520, 180, 450],
    draw(g, o) {
      const s = o.width, H = 176, roof = o.color && o.color !== '' ? o.color : '#4a7a9a';
      g.fillStyle = 'rgba(30,40,20,.24)'; g.beginPath(); g.ellipse(12, 16, 130, 52, 0, 0, 6.283); g.fill();
      prism(g, s, s, H, '#e6dfc9', '#d4ccb2', '#a2a089');
      for (let z = 20; z < H; z += 20) {
        line(g, [iso(-s / 2, s / 2, z), iso(s / 2, s / 2, z)], 'rgba(90,84,66,.4)', 1.4);
        line(g, [iso(s / 2, -s / 2, z), iso(s / 2, s / 2, z)], 'rgba(70,66,52,.4)', 1.4);
      }
      // arrow slits and a lintel band
      for (const z of [64, 112]) {
        poly(g, [iso(-.2, s / 2 + .01, z + 17), iso(.2, s / 2 + .01, z + 17), iso(.2, s / 2 + .01, z - 17), iso(-.2, s / 2 + .01, z - 17)], '#2f3438', null);
        poly(g, [iso(s / 2 + .01, -.2, z + 17), iso(s / 2 + .01, .2, z + 17), iso(s / 2 + .01, .2, z - 17), iso(s / 2 + .01, -.2, z - 17)], '#232a2e', null);
      }
      prism(g, s + .5, s + .5, 14, '#d8d2bb', '#bfb7a0', '#9b977f', H);                      // the balcony
      const z0 = H + 14, apex = iso(0, 0, z0 + 84);
      const a = iso(-s / 2 - .2, s / 2 + .2, z0), b = iso(s / 2 + .2, s / 2 + .2, z0), c = iso(s / 2 + .2, -s / 2 - .2, z0);
      poly(g, [a, b, apex], roof, '#2a3440', 2.5);                                            // the roof, two faces
      poly(g, [b, c, apex], shade(roof, -.28), '#2a3440', 2.5);
      for (let i = 1; i < 5; i++) { const f = i / 5; line(g, [[a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f], apex], 'rgba(255,255,255,.14)', 1.4); }
      line(g, [apex, [apex[0], apex[1] - 46]], '#6a5a3c', 3);
      poly(g, [[apex[0], apex[1] - 46], [apex[0] + 36, apex[1] - 38], [apex[0] + 4, apex[1] - 26]], '#e0b03a', '#7a5a14', 2);
    },
  };
  function shade(hex, k) {                                  // darken (k<0) or lighten a #rrggbb colour
    const n = parseInt(hex.slice(1), 16), t = k < 0 ? 0 : 255, p = Math.abs(k);
    return '#' + [n >> 16, (n >> 8) & 255, n & 255].map(v => Math.round(v + (t - v) * p).toString(16).padStart(2, '0')).join('');
  }

  // ---- the Grand Fountain ----------------------------------------------------------------------------------------------
  const FOUNTAIN = { R: 6.3, tiers: [{ r: 3.1, z: 30, w: 2.6 }, { r: 1.7, z: 92, w: 1.45 }], top: 168 };
  City.art.grandfountain = {
    box: [820, 700, 410, 540],
    draw(g, o) {
      const R = o.r || FOUNTAIN.R;
      ring(g, R + .75, 0, 'rgba(30,50,30,.20)');
      // the great basin: a stone wall, the rim, then water
      drum(g, R, 0, 26, '#e8e1cb', ['#d5ceb8', '#c3bba3', '#8d8873']);
      ring(g, R - .55, 26, '#b9b19a', null);
      ring(g, R - .75, 24, '#5da8b6', null);
      const water = g.createRadialGradient(-50, -34, 10, 0, -24, (R - .75) * RX);
      water.addColorStop(0, '#9ad8de'); water.addColorStop(.6, '#5da8b6'); water.addColorStop(1, '#3f8896');
      ring(g, R - .75, 24, water, null);
      for (let i = 0; i < 5; i++) { g.strokeStyle = 'rgba(255,255,255,.22)'; g.lineWidth = 1.5; g.beginPath(); g.ellipse(0, -24, (R - 1.2 - i * .85) * RX, (R - 1.2 - i * .85) * RY, 0, .1 * i, 2.4 + .1 * i); g.stroke(); }
      // carved panels round the rim
      for (let i = 0; i < 14; i++) {
        const a = i * Math.PI * 2 / 14 + .2, x = Math.cos(a) * R * RX * .98, y = -13 + Math.sin(a) * R * RY * .98;
        if (Math.sin(a) > 0) { g.fillStyle = 'rgba(80,76,60,.25)'; g.fillRect(x - 11, y - 8, 22, 16); g.strokeStyle = 'rgba(255,255,255,.3)'; g.lineWidth = 1; g.strokeRect(x - 11, y - 8, 22, 16); }
      }
      // the tiers and the column
      let top = 24;
      for (const t of FOUNTAIN.tiers) {
        drum(g, t.r * .55, top - 2, t.z, '#d4ccb2', ['#cfc8b2', '#b8b09a', '#85806c']);
        drum(g, t.r, t.z, t.z + 12, '#e8e1cb', ['#dad3bd', '#c8c0a8', '#8d8873']);
        ring(g, t.r - .32, t.z + 12, '#5da8b6', null);
        ring(g, t.r - .45, t.z + 11, '#8cd0d8', null);
        top = t.z + 12;
      }
      drum(g, .62, top, FOUNTAIN.top, '#eee8d4', ['#e2dbc4', '#cdc5ac', '#948f78']);
      // a winged guardian in bronze and gold on the top of the column
      g.save(); g.translate(0, -FOUNTAIN.top);
      glow(g, '#ffd36a', 14, () => {
        poly(g, [[-30, -50], [-14, -30], [-20, -62], [-34, -80]], '#e6bb55', '#8a6a1c', 2);
        poly(g, [[30, -50], [14, -30], [20, -62], [34, -80]], '#e6bb55', '#8a6a1c', 2);
        poly(g, [[-7, -32], [7, -32], [10, -2], [-10, -2]], '#cf9d38', '#7a5a14', 2);
        ellipse(g, 0, -42, 8, 9, '#f1cf72', '#7a5a14');
        poly(g, [[-9, -50], [0, -62], [9, -50], [0, -46]], '#d8a840', '#7a5a14', 1.5);
        line(g, [[13, -8], [13, -92]], '#caa046', 3); poly(g, [[9, -92], [13, -104], [17, -92]], '#f6dd88', '#7a5a14', 1.5);
      });
      g.restore();
    },
    // jets arc from the column head over the tiers into the basin; sparkles ride the water
    animate(g, o, sx, sy, t) {
      const R = o.r || FOUNTAIN.R;
      g.save(); g.translate(sx, sy);
      g.fillStyle = '#e8ffff';
      for (let j = 0; j < 10; j++) {
        const a = j * Math.PI * 2 / 10 + .3, reach = 3.3 + (j % 2) * .9, peak = 118 + (j % 3) * 14, z0 = 104;
        for (let k = 0; k < 7; k++) {
          const s = ((t * .55 + k / 7 + j * .13) % 1);
          const r = reach * s, z = z0 + peak * 4 * s * (1 - s) - (z0 - 26) * s * s * s;
          g.globalAlpha = Math.min(1, Math.sin(Math.min(s, .999) * Math.PI) * 1.6) * .85;
          g.beginPath(); g.arc(Math.cos(a) * r * RX, -z + Math.sin(a) * r * RY, 2.4 - s * .6, 0, 6.283); g.fill();
        }
      }
      for (let j = 0; j < 6; j++) {                       // the lower tier spills outward into the basin
        const a = j * Math.PI / 3 + t * .1;
        for (let k = 0; k < 5; k++) {
          const s = ((t * .5 + k / 5 + j * .17) % 1), r = 3.0 + (R - 3.7) * s, z = 44 + 22 * 4 * s * (1 - s) - 20 * s;
          g.globalAlpha = Math.sin(s * Math.PI) * .7;
          g.beginPath(); g.arc(Math.cos(a) * r * RX, -z + Math.sin(a) * r * RY, 2, 0, 6.283); g.fill();
        }
      }
      for (let i = 0; i < 16; i++) {                      // glints on the water
        const a = i * 2.4 + t * .15, rr = (1.2 + (i % 5) * .9);
        g.globalAlpha = Math.max(0, Math.sin(t * 1.7 + i * 1.9)) * .75;
        g.fillRect(Math.cos(a) * rr * RX - 4, -24 + Math.sin(a) * rr * RY, 8, 1.6);
      }
      g.restore(); g.globalAlpha = 1;
    },
  };

  // ---- the Meeting Stone ----------------------------------------------------------------------------------------------
  // After the one in World of Warcraft: a tall weathered monolith in a circle of stone, its runes glowing blue.
  const stoneRunes = (g, color, width, alpha) => {
    g.save(); g.globalAlpha = alpha; g.strokeStyle = color; g.lineWidth = width; g.lineCap = 'round'; g.lineJoin = 'round';
    for (const [x, y0] of [[-10, -64], [8, -108], [-12, -150], [6, -192]]) {
      g.beginPath(); g.moveTo(x - 7, y0); g.lineTo(x, y0 - 10); g.lineTo(x + 7, y0); g.moveTo(x, y0 - 10); g.lineTo(x, y0 - 24); g.moveTo(x - 5, y0 - 17); g.lineTo(x + 5, y0 - 17); g.stroke();
    }
    g.restore();
  };
  City.art.meetingstone = {
    box: [460, 620, 230, 470],
    draw(g) {
      ring(g, 3.9, 0, 'rgba(20,30,50,.25)');
      drum(g, 3.5, 0, 10, '#9aa0b0', ['#9ea4b4', '#868c9e', '#5a6073'], '#3e4455');
      drum(g, 3.0, 10, 20, '#aab0c0', ['#a9afbf', '#8f95a8', '#626880'], '#3e4455');
      ring(g, 2.5, 20, '#8b92a6', '#3e4455', 2);
      // runes etched round the top step
      glow(g, '#59d9ff', 9, () => {
        g.strokeStyle = '#7fe6ff'; g.lineWidth = 2; g.lineCap = 'round';
        for (let i = 0; i < 18; i++) {
          const a = i * Math.PI * 2 / 18, x = Math.cos(a) * 2.75 * RX, y = -20 + Math.sin(a) * 2.75 * RY;
          g.beginPath(); g.moveTo(x - 2.5, y - 2); g.lineTo(x + 2.5, y + 2); g.moveTo(x + 2.5, y - 2); g.lineTo(x - 2.5, y + 2 - (i % 3)); g.stroke();
        }
        g.beginPath(); g.ellipse(0, -20, 2.25 * RX, 2.25 * RY, 0, 0, Math.PI * 2); g.stroke();
      });
      // three lesser stones leaning in
      for (const [dx, dy, h, lean, tone] of [[-92, 6, 86, -9, 0], [96, 10, 74, 8, 1], [4, -34, 98, 2, 2]]) {
        g.save(); g.translate(dx, dy - 20);
        poly(g, [[-13, 0], [-9 + lean, -h], [lean, -h - 8], [13, 0]], ['#6f7587', '#656b7d', '#5b6174'][tone], '#33394a', 2);
        poly(g, [[13, 0], [lean, -h - 8], [10 + lean, -h + 4], [20, -4]], '#454b5d', '#33394a', 2);
        g.restore();
      }
      // the monolith: a tapering slab with a broken, leaning crown
      g.save(); g.translate(0, -20);
      poly(g, [[-34, 0], [-27, -120], [-24, -224], [-10, -268], [6, -252], [24, -236], [28, -120], [34, 0]], '#6c7386', '#2f3546', 3);
      poly(g, [[34, 0], [28, -120], [24, -236], [6, -252], [14, -150], [40, -6]], '#4a5064', '#2f3546', 3);
      poly(g, [[-34, 0], [-27, -120], [-24, -224], [-17, -150]], '#868ea2', null);                  // lit left edge
      g.strokeStyle = 'rgba(30,34,50,.55)'; g.lineWidth = 2;
      g.beginPath(); g.moveTo(-8, -180); g.lineTo(-14, -150); g.lineTo(-9, -128); g.moveTo(10, -90); g.lineTo(4, -64); g.stroke();
      glow(g, '#59d9ff', 12, () => stoneRunes(g, '#7fe6ff', 3, .85));
      g.fillStyle = 'rgba(120,150,110,.5)'; g.beginPath(); g.ellipse(-22, -8, 14, 6, 0, 0, Math.PI * 2); g.fill();   // moss at the foot
      g.restore();
    },
    animate(g, o, sx, sy, t) {
      g.save(); g.translate(sx, sy - 20);
      const pulse = .5 + .5 * Math.sin(t * 1.6);
      glow(g, '#59d9ff', 16 + pulse * 14, () => stoneRunes(g, '#c8f6ff', 2.4, .35 + .5 * pulse));
      // a ring of light that climbs the stone
      const u = (t * .22) % 1, ry = 8 + 4 * Math.sin(u * 6.28);
      glow(g, '#59d9ff', 12, () => { g.globalAlpha = Math.sin(u * Math.PI) * .8; g.strokeStyle = '#9fe9ff'; g.lineWidth = 2.4; g.beginPath(); g.ellipse(0, -30 - u * 210, 36 - u * 22, ry * .6, 0, 0, Math.PI * 2); g.stroke(); });
      for (let i = 0; i < 12; i++) {                      // motes rising off the dais
        const s = (t * .16 + i / 12) % 1, a = i * 2.1 + t * .4;
        g.globalAlpha = Math.sin(s * Math.PI) * .75; g.fillStyle = '#b8f0ff';
        g.fillRect(Math.cos(a) * (46 + 40 * (i % 3)) * (1 - s * .5) - 1, -s * 250 + Math.sin(a) * 16, 2.4, 2.4);
      }
      g.restore(); g.globalAlpha = 1;
    },
  };

  // ---- small things --------------------------------------------------------------------------------------------------
  City.art.banner = {
    box: [200, 330, 100, 280],
    draw(g, o) {
      const col = o.color || '#9a2f3a';
      ellipse(g, 0, 2, 14, 6, 'rgba(0,0,0,.25)');
      line(g, [[0, 0], [0, -230]], '#6a5a46', 5);
      ellipse(g, 0, -234, 6, 6, '#e0b03a', '#7a5a14');
      poly(g, [[3, -222], [52, -214], [50, -138], [27, -122], [3, -138]], col, '#3a2a30', 2.5);
      line(g, [[9, -208], [44, -202]], '#e8c860', 3); line(g, [[9, -146], [44, -150]], '#e8c860', 3);
      poly(g, [[27, -196], [36, -172], [27, -150], [18, -172]], '#f4e8c8', '#8a7a56', 1.5);
    },
  };
  City.art.statue = {
    box: [200, 330, 100, 280],
    draw(g, o) {
      const kind = (o.v || 0) % 4;
      ellipse(g, 0, 3, 28, 12, 'rgba(0,0,0,.25)');
      prism(g, .9, .9, 30, '#d8d2bb', '#bfb7a0', '#9b977f');
      g.save(); g.translate(0, -34);
      const stone = '#b9b8b0', dark = '#8d8c85';
      poly(g, [[-12, 0], [-10, -52], [10, -52], [12, 0]], stone, '#4e4d48', 2);
      poly(g, [[12, 0], [10, -52], [16, -46], [17, -4]], dark, '#4e4d48', 2);
      ellipse(g, 0, -64, 9, 10, stone, '#4e4d48');
      if (kind === 0) { line(g, [[-17, -16], [-17, -86]], '#7d8187', 4); poly(g, [[-21, -86], [-17, -98], [-13, -86]], '#c9ccd2', '#4e4d48', 1.5); }
      else if (kind === 1) { poly(g, [[-18, -40], [-6, -44], [-6, -30], [-18, -26]], '#8d7a5a', '#4e4d48', 1.5); }
      else if (kind === 2) { g.strokeStyle = '#8d8c85'; g.lineWidth = 3; g.beginPath(); g.arc(-14, -34, 14, -1.2, 1.2); g.stroke(); }
      else { poly(g, [[-14, -78], [-8, -90], [0, -80], [8, -90], [14, -78], [10, -70], [-10, -70]], '#d0a838', '#7a5a14', 1.5); }
      g.restore();
    },
  };
  City.art.well = {
    box: [200, 300, 100, 250],
    draw(g) {
      ellipse(g, 6, 8, 46, 18, 'rgba(30,40,20,.25)');
      drum(g, .95, 0, 26, '#8aa8b0', ['#cdc6ae', '#b5ad95', '#857f69'], '#5e5a4a');
      ring(g, .72, 26, '#1f3a46', null);
      for (const sx of [-1, 1]) line(g, [[sx * 36, -22], [sx * 36, -100]], '#6a4a2c', 6);
      line(g, [[-36, -98], [36, -98]], '#6a4a2c', 6);
      poly(g, [[-46, -96], [0, -128], [46, -96], [0, -104]], '#a55a46', '#4a2a22', 2.5);
      line(g, [[0, -98], [0, -62]], '#d8c8a0', 2); poly(g, [[-6, -62], [6, -62], [5, -48], [-5, -48]], '#7a5a3c', '#3a2a1c', 1.5);
    },
  };
  City.art.barrels = {
    box: [200, 220, 100, 160],
    draw(g, o) {
      ellipse(g, 4, 4, 38, 14, 'rgba(0,0,0,.22)');
      const barrel = (x, y, s) => {
        g.save(); g.translate(x, y); g.scale(s, s);
        poly(g, [[-13, 0], [-15, -18], [-13, -36], [13, -36], [15, -18], [13, 0]], '#9a6a3c', '#3e2814', 2);
        ellipse(g, 0, -36, 13, 5, '#b8884e', '#3e2814');
        for (const y2 of [-8, -28]) line(g, [[-14, y2], [14, y2]], '#4a3a30', 3);
        g.restore();
      };
      barrel(-12, 0, 1); barrel(14, 4, .9);
      g.save(); g.translate(...iso(.55, -.35)); prism(g, .5, .5, 18, '#c8a46c', '#a98350', '#8a6a3c'); g.restore();
    },
  };
})();
