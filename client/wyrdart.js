'use strict';
// Original canvas artwork for the Wyrdwood (zone 6), registered with city.js (`City.art[kind] = { box, draw, animate }`): the
// autumn oaks and storm pines, ferns and heather, mossy boulders, rune-carved standing stones, the dark crags of the two ridges,
// the great Elder Ash of Hollowmoot, the three signal beacons (lit once your quest has lit them), the Hanged King's gallows
// and the bones of an old giant. Each entry draws once into a sprite; `animate` adds the moving parts (flames, runes).
// The scene's origin is the object's foot point; negative y is up; sprites are drawn at logical px (the cache doubles them).
(() => {
  const OL = '#1c1428';
  const rngf = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const outline = (g, circles, col, grow) => { g.fillStyle = col; for (const c of circles) { g.beginPath(); g.ellipse(c.x, c.y, c.r + grow, (c.ry || c.r) + grow, 0, 0, 6.283); g.fill(); } };
  const orb = (g, c, pal) => {
    const ry = c.ry || c.r, gr = g.createRadialGradient(c.x - c.r * .3, c.y - ry * .4, Math.min(c.r, ry) * .1, c.x, c.y, Math.max(c.r, ry));
    gr.addColorStop(0, pal[0]); gr.addColorStop(.6, pal[1]); gr.addColorStop(1, pal[2]); g.fillStyle = gr; g.beginPath(); g.ellipse(c.x, c.y, c.r, ry, 0, 0, 6.283); g.fill();
  };
  const blobs = (g, list, pal) => { outline(g, list, OL, 4); for (const b of list) orb(g, b, pal); };
  const lit = id => !!window.Quests?.visited?.(id);

  // ---- trees ---------------------------------------------------------------------------------------------------------
  const AUTUMN = [['#ff9a66', '#d0401f', '#7a1c14'], ['#ffd06a', '#e5802a', '#8a3a16'], ['#fff29a', '#e8b82e', '#8a6414'], ['#e2f08a', '#94b03c', '#3a5a22']];
  City.art.tree = {
    box: [360, 470, 180, 400],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(900 + v * 31), pal = AUTUMN[v], ax = 0, ay = -4;
      g.lineJoin = 'round'; g.lineCap = 'round';
      const tg = g.createLinearGradient(ax - 16, 0, ax + 16, 0); tg.addColorStop(0, '#5a3a22'); tg.addColorStop(.55, '#8a5e38'); tg.addColorStop(1, '#4a2f1a');
      g.fillStyle = tg; g.strokeStyle = OL; g.lineWidth = 4;
      g.beginPath(); g.moveTo(ax - 24, ay); g.quadraticCurveTo(ax - 10, ay - 24, ax - 11, ay - 62); g.lineTo(ax - 12, ay - 120); g.lineTo(ax + 12, ay - 120); g.quadraticCurveTo(ax + 10, ay - 62, ax + 12, ay - 26); g.quadraticCurveTo(ax + 16, ay - 8, ax + 26, ay); g.closePath(); g.fill(); g.stroke();
      g.strokeStyle = 'rgba(30,16,6,.45)'; g.lineWidth = 2.4; for (let i = 0; i < 4; i++) { const yy = ay - 30 - i * 22; g.beginPath(); g.moveTo(ax - 6 + rng() * 4, yy); g.lineTo(ax - 4 + rng() * 6, yy - 14); g.stroke(); }
      g.fillStyle = '#4f7a34'; g.beginPath(); g.ellipse(ax - 8, ay - 40, 5, 16, .1, 0, 6.283); g.fill();
      const cy = ay - 128, list = [{ x: -44, y: cy + 16, r: 40 }, { x: 46, y: cy + 18, r: 40 }, { x: 0, y: cy - 24, r: 52 }, { x: -28, y: cy - 2, r: 46 }, { x: 28, y: cy - 4, r: 46 }, { x: 0, y: cy + 28, r: 38 }];
      blobs(g, list, pal);
      g.fillStyle = 'rgba(255,255,255,.22)'; for (let i = 0; i < 16; i++) { const a = rng() * 6.283, d = rng() * 60; g.beginPath(); g.ellipse(Math.cos(a) * d - 8, cy - 8 + Math.sin(a) * d * .7, 5, 2.4, rng() * 3, 0, 6.283); g.fill(); }
      g.fillStyle = pal[2]; for (let i = 0; i < 12; i++) { const a = rng() * 6.283, d = 20 + rng() * 40; g.beginPath(); g.ellipse(Math.cos(a) * d + 6, cy + 12 + Math.sin(a) * d * .6, 4, 2, rng() * 3, 0, 6.283); g.fill(); }
      g.fillStyle = pal[1]; for (let i = 0; i < 5; i++) { g.beginPath(); g.ellipse(-30 + i * 15 + rng() * 6, ay + 2 + rng() * 5, 5, 2.4, rng() * 3, 0, 6.283); g.fill(); }   // fallen leaves round the root
    },
  };
  City.art.pine = {
    box: [360, 520, 180, 460],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(1300 + v * 29), tiers = 4 + (v % 2), w0 = 54 + v * 4, ay = -4;
      g.lineJoin = 'round';
      g.fillStyle = '#4a3322'; g.strokeStyle = OL; g.lineWidth = 3.4; g.beginPath(); g.rect(-9, ay - 56, 18, 56); g.fill(); g.stroke();
      for (let t = 0; t < tiers; t++) {
        const base = ay - 38 - t * 52, h = 78, w = w0 * (1 - t / (tiers + .4)) + 12;
        const gr = g.createLinearGradient(-w, 0, w, 0); gr.addColorStop(0, '#5f9484'); gr.addColorStop(.5, '#2f5f55'); gr.addColorStop(1, '#14302c');
        g.fillStyle = gr; g.strokeStyle = OL; g.lineWidth = 3.6;
        g.beginPath(); g.moveTo(0, base - h); g.quadraticCurveTo(w * .55, base - h * .45, w + 4, base - 2); g.quadraticCurveTo(w * .5, base + 12, 0, base + 6); g.quadraticCurveTo(-w * .5, base + 12, -w - 4, base - 2); g.quadraticCurveTo(-w * .55, base - h * .45, 0, base - h); g.closePath(); g.fill(); g.stroke();
        g.strokeStyle = 'rgba(190,230,214,.3)'; g.lineWidth = 2; for (let k = 0; k < 4; k++) { const x = -w * .7 + k * w * .45 + rng() * 6; g.beginPath(); g.moveTo(x, base - 6); g.lineTo(x + 5, base - 30 - rng() * 10); g.stroke(); }
      }
    },
  };
  City.art.bush = {
    box: [200, 190, 100, 160],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(1700 + v * 13), heather = v >= 2;
      g.lineCap = 'round';
      g.fillStyle = 'rgba(30,24,10,.35)'; g.beginPath(); g.ellipse(0, -2, 34, 9, 0, 0, 6.283); g.fill();
      const n = 12 + v;
      for (let i = 0; i < n; i++) {
        const x = -28 + i * (56 / (n - 1)) + (rng() - .5) * 5, h = 24 + rng() * 26, bend = (rng() - .5) * 26;
        g.strokeStyle = OL; g.lineWidth = 5.4; g.beginPath(); g.moveTo(x, -3); g.quadraticCurveTo(x + bend * .3, -h * .6, x + bend, -h); g.stroke();
        g.strokeStyle = heather ? (i % 2 ? '#6a8a3a' : '#8aa04a') : (i % 2 ? '#6a7a2a' : '#a09a3a'); g.lineWidth = 3; g.beginPath(); g.moveTo(x, -3); g.quadraticCurveTo(x + bend * .3, -h * .6, x + bend, -h); g.stroke();
        if (heather) { g.fillStyle = i % 3 ? '#9a5ac8' : '#c48ae8'; for (let k = 0; k < 3; k++) { g.beginPath(); g.arc(x + bend + (k - 1) * 2.2, -h - k * 1.4, 2.4, 0, 6.283); g.fill(); } }
        else if (i % 4 === 1) { g.fillStyle = '#d0501e'; g.beginPath(); g.ellipse(x + bend, -h, 3.4, 1.8, 1, 0, 6.283); g.fill(); }
      }
    },
  };
  City.art.rock = {
    box: [220, 170, 110, 140],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(2100 + v * 17), s = 1 + v * .1, ay = -6;
      const pts = [[-34, 0], [-38, -16], [-20, -38], [6, -44], [30, -30], [38, -10], [28, 0]].map(([x, y]) => [x * s * (.92 + rng() * .16), ay + y * s * (.92 + rng() * .16)]);
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; const gr = g.createLinearGradient(-40, ay - 40, 40, ay); gr.addColorStop(0, '#9a9ea8'); gr.addColorStop(1, '#4e5260'); g.fillStyle = gr;
      g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = 'rgba(255,255,255,.22)'; g.beginPath(); g.moveTo(pts[1][0] + 3, pts[1][1] + 2); g.lineTo(pts[2][0], pts[2][1] + 2); g.lineTo(pts[3][0], pts[3][1] + 2); g.lineTo(0, ay - 24); g.closePath(); g.fill();
      g.fillStyle = '#4f8a34'; g.beginPath(); g.ellipse(-8, ay - 36 * s, 18, 6.4, -.2, 0, 6.283); g.fill(); g.fillStyle = '#7ab04e'; g.beginPath(); g.ellipse(-11, ay - 38 * s, 9, 3, -.2, 0, 6.283); g.fill();
      g.fillStyle = '#d0501e'; g.beginPath(); g.ellipse(16, ay - 4, 8, 2.6, .2, 0, 6.283); g.fill();
    },
  };
  // A rune-carved standing stone: leaning slightly, moss at the foot, amber runes that breathe.
  City.art.spire = {
    box: [200, 280, 100, 240],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(2500 + v * 19), h = 96 + v * 18, w = 15 + v * 1.4, lean = (v % 2 ? 1 : -1) * 5, ay = -4;
      g.lineJoin = 'round';
      const body = () => { g.beginPath(); g.moveTo(-w - 2, ay); g.lineTo(-w + lean, ay - h + 6); g.lineTo(lean - 2, ay - h - 8); g.lineTo(w + lean - 2, ay - h + 4); g.lineTo(w + 2, ay); g.closePath(); };
      const gr = g.createLinearGradient(-w, 0, w, 0); gr.addColorStop(0, '#b8b6aa'); gr.addColorStop(.5, '#8a8a82'); gr.addColorStop(1, '#4f5058');
      body(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.6; g.stroke();
      g.save(); body(); g.clip(); g.strokeStyle = 'rgba(30,30,36,.35)'; g.lineWidth = 1.6; for (let i = 0; i < 6; i++) { const yy = ay - 14 - i * (h / 7) - rng() * 6; g.beginPath(); g.moveTo(-w, yy); g.lineTo(w, yy - 5); g.stroke(); } g.restore();
      g.fillStyle = '#4f7a34'; g.beginPath(); g.ellipse(-w + 4, ay - 8, 10, 6, 0, 0, 6.283); g.fill(); g.beginPath(); g.ellipse(w - 6, ay - 4, 8, 4, 0, 0, 6.283); g.fill();
    },
    animate(g, o, sx, sy, t) {
      const v = (o.v || 0) % 4, h = 96 + v * 18, lean = (v % 2 ? 1 : -1) * 5, pulse = .35 + .35 * Math.sin(t * 1.4 + o.x * .7 + o.y * .3);
      g.save(); g.translate(sx + lean * .5, sy - 8); g.strokeStyle = `rgba(255,190,90,${pulse})`; g.shadowColor = '#ffb04a'; g.shadowBlur = 8; g.lineWidth = 2.2; g.lineCap = 'round';
      for (let i = 0; i < 3; i++) { const y = -h * (.3 + i * .22); g.beginPath(); g.moveTo(-5, y); g.lineTo(0, y - 8); g.lineTo(5, y); g.moveTo(0, y - 8); g.lineTo(0, y + 4); g.stroke(); }
      g.restore();
    },
  };
  // A ridge block: a cluster of dark granite slabs. Neighbouring discs overlap into one cliff wall.
  City.art.crag = {
    box: [260, 260, 130, 210],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(2900 + v * 23), ay = -6;
      g.lineJoin = 'round';
      const slabs = [[-52, 54, 40], [-26, 60, 76], [2, 64, 96 + v * 8], [30, 58, 70], [54, 52, 42]].map(([x, w, h]) => [x, w, h + rng() * 14]);
      for (const [x, w, h] of slabs) {
        const top = ay - h;
        g.beginPath(); g.moveTo(x - w * .5, ay); g.lineTo(x - w * .42, top + 10); g.lineTo(x - w * .1, top - 6); g.lineTo(x + w * .26, top + 4); g.lineTo(x + w * .5, top + 18); g.lineTo(x + w * .52, ay); g.closePath();
        const gr = g.createLinearGradient(x - w * .5, 0, x + w * .5, 0); gr.addColorStop(0, '#6a6e7e'); gr.addColorStop(.5, '#3e4252'); gr.addColorStop(1, '#232632');
        g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3.6; g.stroke();
        g.fillStyle = 'rgba(190,200,225,.28)'; g.beginPath(); g.moveTo(x - w * .42, top + 10); g.lineTo(x - w * .1, top - 6); g.lineTo(x + w * .26, top + 4); g.lineTo(x - w * .05, top + 16); g.closePath(); g.fill();
        g.strokeStyle = 'rgba(10,10,20,.4)'; g.lineWidth = 1.6; g.beginPath(); g.moveTo(x - w * .1, top + 4); g.lineTo(x - w * .16, ay - h * .4); g.moveTo(x + w * .2, top + 10); g.lineTo(x + w * .12, ay - h * .3); g.stroke();
      }
      g.fillStyle = '#5a7a38'; g.beginPath(); g.ellipse(-30, ay - 4, 16, 5, 0, 0, 6.283); g.fill(); g.beginPath(); g.ellipse(34, ay - 3, 12, 4, 0, 0, 6.283); g.fill();
    },
  };

  // ---- Hollowmoot's Elder Ash ----------------------------------------------------------------------------------------
  City.art.elderash = {
    box: [900, 1080, 450, 940],
    draw(g, o) {
      const rng = rngf(777), ay = 0;
      g.lineJoin = 'round'; g.lineCap = 'round';
      g.fillStyle = 'rgba(20,14,6,.28)'; g.beginPath(); g.ellipse(18, 18, 250, 96, 0, 0, 6.283); g.fill();
      const trunk = () => { g.beginPath(); g.moveTo(-190, ay + 6); g.quadraticCurveTo(-150, ay - 70, -118, ay - 190); g.quadraticCurveTo(-104, ay - 330, -92, ay - 520); g.lineTo(96, ay - 520); g.quadraticCurveTo(110, ay - 330, 124, ay - 190); g.quadraticCurveTo(160, ay - 70, 206, ay + 6); g.quadraticCurveTo(10, ay + 52, -190, ay + 6); g.closePath(); };
      const tg = g.createLinearGradient(-190, 0, 206, 0); tg.addColorStop(0, '#8a8a74'); tg.addColorStop(.35, '#6a6a58'); tg.addColorStop(.75, '#46463a'); tg.addColorStop(1, '#2c2c24');
      trunk(); g.fillStyle = tg; g.fill(); g.strokeStyle = OL; g.lineWidth = 6; g.stroke();
      g.save(); trunk(); g.clip();
      g.strokeStyle = 'rgba(20,20,14,.4)'; g.lineWidth = 3; for (let i = 0; i < 20; i++) { const x = -150 + i * 17 + rng() * 6; g.beginPath(); g.moveTo(x, ay - 10); g.bezierCurveTo(x + 8, ay - 150, x - 8, ay - 330, x + 6, ay - 520); g.stroke(); }
      g.fillStyle = '#4f7a34'; for (let i = 0; i < 14; i++) { g.beginPath(); g.ellipse(-130 + rng() * 240, ay - 40 - rng() * 400, 16 + rng() * 14, 7 + rng() * 5, rng() * 3, 0, 6.283); g.fill(); }
      g.restore();
      // the hollow: a tall arched doorway into the trunk, lit from inside, with a lintel of roots
      const dx = 14, dy = ay - 6;
      g.fillStyle = OL; g.beginPath(); g.moveTo(dx - 46, dy); g.lineTo(dx - 46, dy - 90); g.quadraticCurveTo(dx, dy - 150, dx + 46, dy - 90); g.lineTo(dx + 46, dy); g.closePath(); g.fill();
      const dg = g.createLinearGradient(0, dy - 140, 0, dy); dg.addColorStop(0, '#ffb04a'); dg.addColorStop(1, '#8a3a12'); g.fillStyle = dg;
      g.beginPath(); g.moveTo(dx - 38, dy); g.lineTo(dx - 38, dy - 88); g.quadraticCurveTo(dx, dy - 138, dx + 38, dy - 88); g.lineTo(dx + 38, dy); g.closePath(); g.fill();
      g.fillStyle = 'rgba(255,230,160,.55)'; g.beginPath(); g.ellipse(dx, dy - 60, 18, 40, 0, 0, 6.283); g.fill();
      g.strokeStyle = '#3a2a1a'; g.lineWidth = 7; g.beginPath(); g.moveTo(dx - 52, dy - 2); g.quadraticCurveTo(dx - 52, dy - 120, dx, dy - 148); g.quadraticCurveTo(dx + 52, dy - 120, dx + 52, dy - 2); g.stroke();
      // knot-hole windows, each with a lantern
      for (const [wx, wy] of [[-74, ay - 190], [84, ay - 230], [-60, ay - 330], [60, ay - 380], [-30, ay - 440]]) {
        g.fillStyle = OL; g.beginPath(); g.ellipse(wx, wy, 17, 23, 0, 0, 6.283); g.fill(); g.fillStyle = '#ffc060'; g.beginPath(); g.ellipse(wx, wy + 2, 11, 17, 0, 0, 6.283); g.fill();
        g.strokeStyle = '#3a2a1a'; g.lineWidth = 3; g.beginPath(); g.moveTo(wx, wy - 14); g.lineTo(wx, wy + 18); g.stroke();
      }
      // roots
      for (const sgn of [-1, 1]) for (let k = 0; k < 3; k++) { g.strokeStyle = OL; g.lineWidth = 22 - k * 4; g.beginPath(); g.moveTo(sgn * (120 + k * 20), ay - 40); g.quadraticCurveTo(sgn * (190 + k * 40), ay + 4, sgn * (230 + k * 50), ay + 24 + k * 6); g.stroke(); g.strokeStyle = '#5a4a38'; g.lineWidth = 14 - k * 3; g.stroke(); }
      // the crown: a vast autumn canopy
      const cy = ay - 560, list = [];
      for (let i = 0; i < 16; i++) { const a = i / 16 * 6.283; list.push({ x: Math.cos(a) * 190, y: cy + Math.sin(a) * 60, r: 110, ry: 80 }); }
      for (let i = 0; i < 8; i++) { const a = i / 8 * 6.283 + .3; list.push({ x: Math.cos(a) * 100, y: cy - 60 + Math.sin(a) * 30, r: 130, ry: 100 }); }
      list.push({ x: 0, y: cy - 90, r: 150, ry: 110 });
      outline(g, list, OL, 5);
      list.forEach((b, i) => orb(g, b, AUTUMN[(i * 7 + (i >> 2)) % 3 === 0 ? 1 : i % 4 === 0 ? 0 : 2]));
      g.fillStyle = 'rgba(255,240,170,.3)'; for (let i = 0; i < 60; i++) { const a = rng() * 6.283, d = rng() * 200; g.beginPath(); g.ellipse(Math.cos(a) * d, cy - 40 + Math.sin(a) * d * .5, 7, 3, rng() * 3, 0, 6.283); g.fill(); }
      for (let i = 0; i < 24; i++) { const a = rng() * 6.283, d = 80 + rng() * 150; g.fillStyle = '#7a1c14'; g.beginPath(); g.ellipse(Math.cos(a) * d, cy + 10 + Math.sin(a) * d * .4, 6, 2.6, rng() * 3, 0, 6.283); g.fill(); }
    },
    animate(g, o, sx, sy, t) {                                    // a lantern glow in the doorway and drifting seeds
      g.save(); g.translate(sx + 14, sy - 70); const gl = g.createRadialGradient(0, 0, 4, 0, 0, 70 + 4 * Math.sin(t * 3)); gl.addColorStop(0, 'rgba(255,200,110,.42)'); gl.addColorStop(1, 'rgba(255,170,80,0)'); g.fillStyle = gl; g.fillRect(-80, -80, 160, 160); g.restore();
    },
  };

  // ---- the beacons -----------------------------------------------------------------------------------------------------
  City.art.beacon = {
    box: [300, 360, 150, 290],
    draw(g, o) {
      const big = !!o.great, R = big ? 1.5 : 1, rng = rngf(big ? 31 : 17);
      g.lineJoin = 'round';
      g.fillStyle = 'rgba(20,16,10,.3)'; g.beginPath(); g.ellipse(6, 8, 74 * R, 26 * R, 0, 0, 6.283); g.fill();
      for (let tier = 0; tier < 3; tier++) {                                                      // a cairn of stacked stones
        const w = (62 - tier * 14) * R, h = 20 * R, y = -tier * h * .9;
        for (let k = 0; k < 7; k++) { const a = k / 7 * 6.283 + tier * .5, x = Math.cos(a) * w * .5, yy = y + Math.sin(a) * w * .22; g.fillStyle = ['#7a7e88', '#5f6470', '#8f939c'][(k + tier) % 3]; g.strokeStyle = OL; g.lineWidth = 2.6; g.beginPath(); g.ellipse(x, yy - h * .4, 13 * R, 9 * R, 0, 0, 6.283); g.fill(); g.stroke(); }
      }
      const top = -50 * R;
      g.strokeStyle = OL; g.lineWidth = 9; g.beginPath(); g.moveTo(0, top); g.lineTo(0, top - 56 * R); g.stroke(); g.strokeStyle = '#4a4036'; g.lineWidth = 5; g.stroke();
      const bowl = () => { g.beginPath(); g.moveTo(-28 * R, top - 56 * R); g.quadraticCurveTo(-24 * R, top - 36 * R, 0, top - 34 * R); g.quadraticCurveTo(24 * R, top - 36 * R, 28 * R, top - 56 * R); g.closePath(); };
      bowl(); g.fillStyle = '#2f2c34'; g.fill(); g.strokeStyle = OL; g.lineWidth = 4; g.stroke();
      g.fillStyle = '#6a5a4a'; g.beginPath(); g.ellipse(0, top - 56 * R, 28 * R, 8 * R, 0, 0, 6.283); g.fill(); g.stroke();
      g.fillStyle = '#2a2018'; g.beginPath(); g.ellipse(0, top - 56 * R, 21 * R, 5.5 * R, 0, 0, 6.283); g.fill();
      g.strokeStyle = '#8a8a96'; g.lineWidth = 2; for (let k = 0; k < 4; k++) { g.beginPath(); g.moveTo(-18 * R + k * 12 * R, top - 52 * R); g.lineTo(-16 * R + k * 12 * R, top - 40 * R); g.stroke(); }
      void rng;
    },
    animate(g, o, sx, sy, t) {
      const big = !!o.great, R = big ? 1.5 : 1, on = big || lit(o.place), bx = sx, by = sy - 106 * R;
      if (!on) {                                                                                   // dark: a wisp of cold smoke and an ember or two
        g.save(); g.globalAlpha = .35; g.fillStyle = '#8a8a96'; for (let i = 0; i < 3; i++) { const ph = (t * .4 + i * .33) % 1; g.beginPath(); g.ellipse(bx + Math.sin(t + i) * 3, by - ph * 34, 5 + ph * 5, 3 + ph * 3, 0, 0, 6.283); g.fill(); } g.restore(); return;
      }
      g.save(); g.globalCompositeOperation = 'lighter';
      const gl = g.createRadialGradient(bx, by - 10, 6, bx, by - 10, 140 * R); gl.addColorStop(0, 'rgba(255,170,70,.5)'); gl.addColorStop(1, 'rgba(255,120,40,0)'); g.fillStyle = gl; g.fillRect(bx - 150 * R, by - 150 * R, 300 * R, 300 * R);
      g.restore();
      for (let i = 0; i < 6; i++) {
        const ph = (t * (1.3 + i * .12) + i * .17) % 1, w = (20 - i * 2.5) * R * (1 - ph * .55), h = (34 + i * 7) * R * (.7 + .3 * Math.sin(t * 9 + i * 2)), ox = Math.sin(t * 5 + i * 1.7) * 3 * R;
        g.fillStyle = ['#c8301a', '#f0601c', '#ffa030', '#ffd860', '#fff2b0', '#ffffff'][i]; g.beginPath(); g.moveTo(bx - w + ox, by); g.quadraticCurveTo(bx - w * .6 + ox, by - h * .6, bx + ox * 2, by - h); g.quadraticCurveTo(bx + w * .6 + ox, by - h * .6, bx + w + ox, by); g.closePath(); g.fill();
      }
      g.fillStyle = '#ffd860'; for (let i = 0; i < 5; i++) { const ph = (t * .8 + i * .21) % 1; g.globalAlpha = 1 - ph; g.fillRect(bx + Math.sin(i * 3 + t) * 16 * R, by - 20 * R - ph * 70 * R, 2, 2); } g.globalAlpha = 1;
    },
  };

  // ---- the Hanged King's gallows ----------------------------------------------------------------------------------------
  City.art.gallows = {
    box: [300, 330, 150, 290],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(4100 + v), s = 1 + (v % 2) * .12;
      g.lineJoin = 'round'; g.lineCap = 'round';
      g.fillStyle = 'rgba(20,14,8,.3)'; g.beginPath(); g.ellipse(4, 6, 60, 20, 0, 0, 6.283); g.fill();
      const beam = (x0, y0, x1, y1, w) => { g.strokeStyle = OL; g.lineWidth = w + 5; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); g.strokeStyle = '#6a4a2c'; g.lineWidth = w; g.stroke(); g.strokeStyle = '#8a6a44'; g.lineWidth = w * .35; g.beginPath(); g.moveTo(x0 - w * .2, y0); g.lineTo(x1 - w * .2, y1); g.stroke(); };
      beam(-34, -2, -34, -150 * s, 13); beam(-34, -150 * s, 40, -150 * s, 11); beam(-34, -120 * s, -4, -150 * s, 8);
      g.fillStyle = '#7a8a8a'; g.strokeStyle = OL; g.lineWidth = 2.6; g.beginPath(); g.ellipse(-34, -2, 22, 7, 0, 0, 6.283); g.fill(); g.stroke();
      // the noose, swaying a little (static here), and a crow on the beam
      const nx = 22, ny = -150 * s;
      g.strokeStyle = OL; g.lineWidth = 5.4; g.beginPath(); g.moveTo(nx, ny); g.quadraticCurveTo(nx + 2 + v, ny + 36, nx, ny + 60); g.stroke(); g.strokeStyle = '#b89a62'; g.lineWidth = 2.6; g.stroke();
      g.strokeStyle = OL; g.lineWidth = 5; g.beginPath(); g.ellipse(nx, ny + 70, 8, 10, 0, 0, 6.283); g.stroke(); g.strokeStyle = '#b89a62'; g.lineWidth = 2.2; g.stroke();
      if (v % 2 === 0) {
        const cx = -8, cy = ny - 2; g.fillStyle = '#1a1a2b'; g.strokeStyle = OL; g.lineWidth = 2.4;
        g.beginPath(); g.ellipse(cx, cy - 10, 12, 8, -.2, 0, 6.283); g.fill(); g.stroke(); g.beginPath(); g.arc(cx + 11, cy - 17, 5.4, 0, 6.283); g.fill(); g.stroke();
        g.fillStyle = '#c4aa78'; g.beginPath(); g.moveTo(cx + 15, cy - 18); g.lineTo(cx + 24, cy - 15); g.lineTo(cx + 15, cy - 14); g.closePath(); g.fill(); g.fillStyle = '#ff4a3a'; g.fillRect(cx + 11, cy - 19, 2, 2);
        g.strokeStyle = '#1a1a2b'; g.lineWidth = 3; g.beginPath(); g.moveTo(cx - 10, cy - 8); g.lineTo(cx - 24, cy - 2); g.stroke();
      }
      void rng;
    },
  };

  // ---- an old giant's bones ----------------------------------------------------------------------------------------------
  City.art.ribcage = {
    box: [360, 300, 180, 250],
    draw(g, o) {
      const v = (o.v || 0) % 4, n = 4 + (v % 2), ay = -4;
      g.lineCap = 'round'; g.lineJoin = 'round';
      g.fillStyle = 'rgba(20,16,10,.28)'; g.beginPath(); g.ellipse(0, 6, 120, 26, 0, 0, 6.283); g.fill();
      g.strokeStyle = OL; g.lineWidth = 13; g.beginPath(); g.moveTo(-96, ay); g.lineTo(96, ay - 4); g.stroke(); g.strokeStyle = '#d8d0b4'; g.lineWidth = 7; g.stroke();     // the spine
      for (let i = 0; i < n; i++) {
        const x = -80 + i * (160 / (n - 1)), h = 150 - Math.abs(i - (n - 1) / 2) * 24 - (v % 3) * 8, lean = (i - (n - 1) / 2) * 6;
        for (const dir of [1]) {
          g.strokeStyle = OL; g.lineWidth = 12; g.beginPath(); g.moveTo(x, ay); g.bezierCurveTo(x - 20 * dir + lean, ay - h * .7, x + 28 * dir + lean, ay - h * 1.02, x + 62 * dir + lean, ay - h * .62); g.stroke();
          g.strokeStyle = '#e8e0c8'; g.lineWidth = 7; g.stroke();
          g.strokeStyle = 'rgba(120,108,80,.55)'; g.lineWidth = 2; g.beginPath(); g.moveTo(x - 3, ay - 8); g.bezierCurveTo(x - 22 + lean, ay - h * .7, x + 24 + lean, ay - h * .98, x + 58 + lean, ay - h * .62); g.stroke();
        }
      }
      g.fillStyle = '#4f7a34'; for (let i = 0; i < 4; i++) { g.beginPath(); g.ellipse(-70 + i * 46, ay + 1, 14, 5, 0, 0, 6.283); g.fill(); }
    },
  };
})();
