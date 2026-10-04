'use strict';
// Original canvas artwork for Bifrost Reach (zone 7), registered with city.js (`City.art[kind] = { box, draw, animate }`): windswept
// sky-pines, puffs of cloud, pale floating rocks, prism crystals, broken Bifrost columns, the three ward-stones (their rune circles
// are ground decals drawn by field.js), the Windcairn, the Lightning Spire, the Bifrost Pylon, the Hall Gate and the roc's nest.
// Each entry draws once into a sprite; `animate` adds the moving parts (glints, banners, lightning). The scene's origin is the
// object's foot point; negative y is up.
(() => {
  const OL = '#1c1c3a';
  const rngf = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const lit = id => !!window.Quests?.visited?.(id);
  const hold = id => window.Quests?.hold?.(id) || { have: 0, need: 0, state: 'none' };
  const ell = (g, x, y, rx, ry, fill, stroke, lw = 3) => { g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, 6.283); g.fillStyle = fill; g.fill(); if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); } };
  const STONE = ['#eef2ff', '#b9c4e4', '#6e7aa6'];
  const stoneGrad = (g, x0, x1) => { const gr = g.createLinearGradient(x0, 0, x1, 0); gr.addColorStop(0, STONE[0]); gr.addColorStop(.5, STONE[1]); gr.addColorStop(1, STONE[2]); return gr; };
  const shadow = (g, rx, ry) => { g.fillStyle = 'rgba(30,40,80,.28)'; g.beginPath(); g.ellipse(4, 6, rx, ry, 0, 0, 6.283); g.fill(); };

  // ---- trees: a slender trunk bent by the wind and a flat, layered crown --------------------------------------------------
  const PINES = [['#d8fff0', '#52c0a0', '#1f6a60'], ['#f0ffd0', '#8ad060', '#3a7a34'], ['#e0f0ff', '#6aa8e8', '#2a5aa0'], ['#fff0f8', '#e08ac0', '#8a3a7a']];
  City.art.skypine = {
    box: [300, 420, 150, 380],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(100 + v * 31), pal = PINES[v], lean = (v % 2 ? 1 : -1) * 22;
      g.scale(.78, .78); g.lineJoin = 'round'; g.lineCap = 'round';
      shadow(g, 40, 12);
      const trunk = [[0, -2], [lean * .25, -50], [lean * .8, -100], [lean, -150]];
      g.strokeStyle = OL; g.lineWidth = 17; g.beginPath(); g.moveTo(...trunk[0]); g.bezierCurveTo(...trunk[1], ...trunk[2], ...trunk[3]); g.stroke();
      g.strokeStyle = '#8a6a5a'; g.lineWidth = 11; g.stroke(); g.strokeStyle = '#c4a090'; g.lineWidth = 3; g.beginPath(); g.moveTo(-3, -8); g.bezierCurveTo(lean * .2 - 3, -50, lean * .7 - 3, -100, lean - 3, -145); g.stroke();
      for (let i = 0; i < 4; i++) {                                         // layered pads of foliage, each one wider lower down
        const y = -150 + i * 30, x = lean * (1 - i * .2) + (rng() - .5) * 6, rx = 34 + i * 17, ry = 12 + i * 3.4;
        ell(g, x, y + 5, rx + 4, ry + 4, OL);
        const gr = g.createRadialGradient(x - rx * .3, y - ry * .5, 4, x, y, rx); gr.addColorStop(0, pal[0]); gr.addColorStop(.55, pal[1]); gr.addColorStop(1, pal[2]);
        ell(g, x, y, rx, ry, gr);
        g.fillStyle = 'rgba(255,255,255,.4)'; g.beginPath(); g.ellipse(x - rx * .25, y - ry * .35, rx * .45, ry * .3, -.1, 0, 6.283); g.fill();
      }
      g.fillStyle = 'rgba(255,255,255,.7)'; for (let i = 0; i < 5; i++) { g.beginPath(); g.ellipse(lean + (rng() - .5) * 100, -70 + rng() * 60, 14 + rng() * 10, 3, 0, 0, 6.283); g.fill(); }   // a wisp of mist through the branches
    },
  };
  City.art.cloudpuff = {
    box: [200, 140, 100, 110],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(300 + v * 11);
      g.fillStyle = 'rgba(60,80,150,.18)'; g.beginPath(); g.ellipse(2, 3, 34, 8, 0, 0, 6.283); g.fill();
      const puffs = [[-20, -10, 15], [0, -17, 19], [20, -9, 15], [-8, -6, 14], [10, -5, 14]].map(([x, y, r]) => [x + (rng() - .5) * 4, y, r * (.9 + v * .06)]);
      g.fillStyle = '#9fb0e0'; for (const [x, y, r] of puffs) { g.beginPath(); g.arc(x, y + 1.5, r + 2.5, 0, 6.283); g.fill(); }
      for (const [x, y, r] of puffs) { const gr = g.createRadialGradient(x - r * .3, y - r * .4, 2, x, y, r); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.7, '#e4ecff'); gr.addColorStop(1, '#b4c4ee'); g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 6.283); g.fill(); }
    },
    animate(g, o, sx, sy, t) { const a = .5 + .5 * Math.sin(t * 1.2 + o.x * 3); g.save(); g.globalAlpha = .25 * a; g.fillStyle = '#fff'; g.beginPath(); g.ellipse(sx + Math.sin(t * .5 + o.y) * 6, sy - 26 - a * 5, 9, 3, 0, 0, 6.283); g.fill(); g.restore(); },
  };
  City.art.skyrock = {
    box: [220, 180, 110, 150],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(500 + v * 17), s = 1 + v * .1, ay = -6;
      shadow(g, 32 * s, 9);
      const pts = [[-30, 0], [-36, -14], [-20, -34], [4, -42], [28, -28], [36, -8], [26, 0]].map(([x, y]) => [x * s * (.92 + rng() * .16), ay + y * s * (.92 + rng() * .16)]);
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 4; const gr = g.createLinearGradient(-36, ay - 40, 36, ay); gr.addColorStop(0, '#f2f5ff'); gr.addColorStop(.6, '#aab6d8'); gr.addColorStop(1, '#5e6a96'); g.fillStyle = gr;
      g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
      g.strokeStyle = 'rgba(120,230,255,.7)'; g.lineWidth = 2; g.beginPath(); g.moveTo(pts[1][0] + 6, pts[1][1] + 6); g.lineTo(pts[3][0], pts[3][1] + 12); g.lineTo(pts[4][0] - 4, pts[4][1] + 10); g.stroke();     // a vein of the old bridge
      ell(g, -6, ay - 38 * s, 16, 5.4, '#7acab0'); ell(g, -9, ay - 40 * s, 8, 2.6, '#a6e8d0');
    },
  };

  // ---- Bifrost crystal and masonry ------------------------------------------------------------------------------------------
  const crystal = (g, x, y, w, h, hue) => {
    const pts = [[x - w / 2, y], [x - w * .42, y - h * .82], [x, y - h], [x + w * .42, y - h * .82], [x + w / 2, y]];
    g.lineJoin = 'round';
    g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath();
    const gr = g.createLinearGradient(x - w / 2, y, x + w / 2, y - h); gr.addColorStop(0, `hsl(${hue}, 90%, 38%)`); gr.addColorStop(.5, `hsl(${hue + 30}, 90%, 70%)`); gr.addColorStop(1, `hsl(${hue + 60}, 95%, 92%)`);
    g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 3; g.stroke();
    g.fillStyle = 'rgba(255,255,255,.55)'; g.beginPath(); g.moveTo(x - w * .3, y - 4); g.lineTo(x - w * .3, y - h * .74); g.lineTo(x - w * .08, y - h * .9); g.lineTo(x - w * .1, y - 4); g.closePath(); g.fill();
  };
  City.art.prism = {
    box: [240, 320, 120, 270],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(900 + v * 13), hue = [190, 280, 330, 50][v];
      shadow(g, 40, 11);
      const list = [[-26, 1, 24, 56 + rng() * 14], [26, 0, 22, 48 + rng() * 14], [-6, 4, 30, 96 + rng() * 26], [14, 3, 20, 70 + rng() * 12]];
      for (const [x, dy, w, h] of list) crystal(g, x, -4 + dy, w, h, hue + rng() * 30);
    },
    animate(g, o, sx, sy, t) {
      g.save(); g.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 3; i++) { const k = (o.x * 3 + o.y * 5 + i * 7) | 0, a = Math.max(0, Math.sin(t * 2.2 + k)); if (a < .05) continue; g.fillStyle = `rgba(255,255,255,${a * .9})`; const x = sx + Math.sin(k) * 16, y = sy - 20 - ((k * 13) % 70); g.fillRect(x - 1, y - 5, 2, 10); g.fillRect(x - 5, y - 1, 10, 2); }
      g.restore();
    },
  };
  City.art.column = {
    box: [220, 340, 110, 300],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(1300 + v * 29), h = 70 + v * 24, w = 21, ay = -4;
      shadow(g, 36, 10);
      g.lineJoin = 'round';
      g.fillStyle = stoneGrad(g, -30, 30); g.strokeStyle = OL; g.lineWidth = 3.6; g.beginPath(); g.rect(-30, ay - 12, 60, 12); g.fill(); g.stroke();
      const top = ay - 12 - h;
      g.fillStyle = stoneGrad(g, -w, w); g.beginPath(); g.moveTo(-w, ay - 12); g.lineTo(-w + 2, top + 8); g.lineTo(-w * .4, top - 4); g.lineTo(w * .1, top + 6); g.lineTo(w * .6, top - 8); g.lineTo(w, top + 4); g.lineTo(w, ay - 12); g.closePath(); g.fill(); g.stroke();
      g.strokeStyle = 'rgba(60,70,120,.4)'; g.lineWidth = 2; for (let i = -2; i <= 2; i++) { g.beginPath(); g.moveTo(i * 8, ay - 14); g.lineTo(i * 8 + 1, top + 10); g.stroke(); }
      const gr = g.createLinearGradient(-w, 0, w, 0); ['#ff5a7a', '#ffb050', '#fff070', '#60e0a0', '#50b8ff', '#b070ff'].forEach((c, i, a) => gr.addColorStop(i / (a.length - 1), c));
      g.strokeStyle = gr; g.lineWidth = 3; g.beginPath(); g.moveTo(-w + 2, ay - 18 - rng() * 10); g.lineTo(w - 2, ay - 22 - h * .4); g.stroke();       // a stripe of the old rainbow
      if (v % 2) { g.fillStyle = stoneGrad(g, 0, 40); g.strokeStyle = OL; g.lineWidth = 3; g.beginPath(); g.moveTo(24, ay); g.lineTo(46, ay - 2); g.lineTo(44, ay - 18); g.lineTo(28, ay - 20); g.closePath(); g.fill(); g.stroke(); }
    },
  };

  // ---- the three wards -------------------------------------------------------------------------------------------------------
  City.art.wardstone = {
    box: [220, 400, 110, 360],
    draw(g, o) {
      shadow(g, 40, 12);
      g.lineJoin = 'round';
      for (let tier = 0; tier < 2; tier++) { const w = 46 - tier * 10; g.fillStyle = stoneGrad(g, -w, w); g.strokeStyle = OL; g.lineWidth = 3.4; g.beginPath(); g.moveTo(-w, -tier * 14); g.lineTo(-w + 4, -14 - tier * 14); g.lineTo(w - 4, -14 - tier * 14); g.lineTo(w, -tier * 14); g.closePath(); g.fill(); g.stroke(); }
      const body = () => { g.beginPath(); g.moveTo(-17, -26); g.lineTo(-13, -150); g.lineTo(0, -166); g.lineTo(13, -150); g.lineTo(17, -26); g.closePath(); };
      body(); g.fillStyle = stoneGrad(g, -17, 17); g.fill(); g.strokeStyle = OL; g.lineWidth = 3.6; g.stroke();
      g.fillStyle = '#6a76a2'; g.beginPath(); g.moveTo(0, -166); g.lineTo(13, -150); g.lineTo(17, -26); g.lineTo(5, -30); g.closePath(); g.fill();
    },
    animate(g, o, sx, sy, t) {
      const h = hold(o.place), on = h.state === 'active', done = h.state === 'done', pulse = .5 + .5 * Math.sin(t * (on ? 5 : 1.6));
      const col = done ? '255,215,90' : on ? '255,170,70' : '110,200,255';
      g.save(); g.translate(sx, sy);
      g.strokeStyle = `rgba(${col},${.4 + .5 * pulse})`; g.shadowColor = `rgb(${col})`; g.shadowBlur = 10; g.lineWidth = 2.4; g.lineCap = 'round';
      for (let i = 0; i < 4; i++) { const y = -52 - i * 26; g.beginPath(); g.moveTo(-6, y); g.lineTo(0, y - 9); g.lineTo(6, y); g.moveTo(0, y - 9); g.lineTo(0, y + 5); g.stroke(); }
      g.shadowBlur = 0;
      const cy = -190 - Math.sin(t * 1.4) * 4;                                   // the crown crystal floats above the tip
      g.globalCompositeOperation = 'lighter';
      const gl = g.createRadialGradient(0, cy, 2, 0, cy, 56 + 12 * pulse); gl.addColorStop(0, `rgba(${col},.8)`); gl.addColorStop(1, `rgba(${col},0)`); g.fillStyle = gl; g.fillRect(-70, cy - 70, 140, 140);
      g.globalCompositeOperation = 'source-over';
      g.fillStyle = done ? '#fff0a0' : on ? '#ffd090' : '#c8f0ff'; g.strokeStyle = OL; g.lineWidth = 2.4; g.beginPath(); g.moveTo(0, cy - 16); g.lineTo(10, cy); g.lineTo(0, cy + 16); g.lineTo(-10, cy); g.closePath(); g.fill(); g.stroke();
      g.restore();
    },
  };
  City.art.windcairn = {
    box: [240, 380, 120, 320],
    draw(g, o) {
      shadow(g, 52, 16);
      g.lineJoin = 'round';
      const stones = [[-30, -8, 24, 14], [4, -10, 30, 16], [34, -7, 20, 12], [-14, -26, 26, 14], [16, -27, 26, 14], [0, -43, 24, 13], [2, -58, 18, 11]];
      stones.forEach(([x, y, rx, ry], i) => ell(g, x, y, rx, ry, ['#d4dcf4', '#aab6d8', '#e8eeff'][i % 3], OL, 3));
      g.strokeStyle = OL; g.lineWidth = 8; g.beginPath(); g.moveTo(2, -62); g.lineTo(2, -176); g.stroke(); g.strokeStyle = '#8a6a5a'; g.lineWidth = 4; g.stroke();
      ell(g, 2, -178, 6, 6, '#ffd870', OL, 2);
    },
    animate(g, o, sx, sy, t) {
      const on = lit(o.place), k = Math.sin(t * 3), flutter = (i) => Math.sin(t * 5 + i * .8) * 4;
      g.save(); g.translate(sx + 2, sy - 164); g.lineJoin = 'round';
      g.fillStyle = on ? '#ffd24a' : '#7a8ab8'; g.strokeStyle = OL; g.lineWidth = 2.4;
      g.beginPath(); g.moveTo(0, 0); for (let i = 1; i <= 6; i++) g.lineTo(i * 8, flutter(i) + i * 1.2); g.lineTo(48, 24 + flutter(7)); for (let i = 5; i >= 0; i--) g.lineTo(i * 8, 22 + flutter(i)); g.closePath(); g.fill(); g.stroke();
      if (on) { g.globalCompositeOperation = 'lighter'; const gl = g.createRadialGradient(20, 12, 4, 20, 12, 90); gl.addColorStop(0, 'rgba(255,220,120,.5)'); gl.addColorStop(1, 'rgba(255,200,80,0)'); g.fillStyle = gl; g.fillRect(-70, -80, 180, 180); }
      g.restore(); void k;
    },
  };
  City.art.spirelight = {
    box: [300, 620, 150, 560],
    draw(g, o) {
      shadow(g, 52, 16);
      g.lineJoin = 'round';
      const body = () => { g.beginPath(); g.moveTo(-34, 0); g.lineTo(-22, -190); g.lineTo(-10, -330); g.lineTo(0, -430); g.lineTo(10, -330); g.lineTo(22, -190); g.lineTo(34, 0); g.closePath(); };
      const gr = g.createLinearGradient(-34, 0, 34, 0); gr.addColorStop(0, '#6a6e96'); gr.addColorStop(.5, '#3e4268'); gr.addColorStop(1, '#1e2038');
      body(); g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 4; g.stroke();
      g.save(); body(); g.clip(); g.strokeStyle = 'rgba(180,190,255,.2)'; g.lineWidth = 2; for (let i = 0; i < 9; i++) { g.beginPath(); g.moveTo(-34, -i * 46); g.lineTo(34, -i * 46 - 14); g.stroke(); } g.restore();
      g.fillStyle = '#8a92c4'; g.beginPath(); g.moveTo(0, -430); g.lineTo(10, -330); g.lineTo(22, -190); g.lineTo(6, -200); g.closePath(); g.fill();
    },
    animate(g, o, sx, sy, t) {
      const on = lit(o.place), tipx = sx, tipy = sy - 430, rng = rngf(Math.floor(t * 9) * 977 + 31);
      g.save(); g.globalCompositeOperation = 'lighter';
      const gl = g.createRadialGradient(tipx, tipy, 4, tipx, tipy, on ? 120 : 70); gl.addColorStop(0, on ? 'rgba(160,220,255,.7)' : 'rgba(120,160,255,.4)'); gl.addColorStop(1, 'rgba(120,160,255,0)'); g.fillStyle = gl; g.fillRect(tipx - 130, tipy - 130, 260, 260);
      g.strokeStyle = on ? 'rgba(235,250,255,.95)' : 'rgba(170,200,255,.7)'; g.lineWidth = on ? 3 : 2; g.shadowColor = '#9fd0ff'; g.shadowBlur = 14; g.lineJoin = 'round';
      for (let b = 0; b < (on ? 3 : 1); b++) { g.beginPath(); let x = tipx, y = tipy; g.moveTo(x, y); for (let i = 0; i < 8; i++) { x += (rng() - .5) * 36; y -= 26 + rng() * 14; g.lineTo(x, y); } g.stroke(); }     // the lightning here rises into the sky
      g.restore();
    },
  };
  City.art.pylon = {
    box: [400, 600, 200, 540],
    draw(g, o) {
      shadow(g, 70, 22);
      g.lineJoin = 'round';
      g.fillStyle = stoneGrad(g, -58, 58); g.strokeStyle = OL; g.lineWidth = 4; g.beginPath(); g.moveTo(-58, 0); g.lineTo(-48, -26); g.lineTo(48, -26); g.lineTo(58, 0); g.closePath(); g.fill(); g.stroke();
      const sh = () => { g.beginPath(); g.moveTo(-30, -26); g.lineTo(-24, -300); g.lineTo(-10, -330); g.lineTo(8, -296); g.lineTo(14, -340); g.lineTo(26, -280); g.lineTo(30, -26); g.closePath(); };
      sh(); g.fillStyle = stoneGrad(g, -30, 30); g.fill(); g.stroke();
      g.save(); sh(); g.clip();
      const gr = g.createLinearGradient(0, -330, 0, -26); ['#ff5a7a', '#ffb050', '#fff070', '#60e0a0', '#50b8ff', '#b070ff'].forEach((c, i, a) => gr.addColorStop(i / (a.length - 1), c));
      g.fillStyle = gr; g.globalAlpha = .45; g.fillRect(-30, -340, 60, 320); g.restore();
    },
    animate(g, o, sx, sy, t) {
      g.save(); g.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 6; i++) {                                              // shards of the broken bridge circling the pylon
        const a = t * .9 + i * 1.047, x = sx + Math.cos(a) * 62, y = sy - 220 + Math.sin(a) * 18 - i * 14 + Math.sin(t + i) * 6, hue = (i * 60 + t * 40) % 360;
        g.fillStyle = `hsla(${hue}, 100%, 70%, ${Math.sin(a) > 0 ? .95 : .45})`; g.beginPath(); g.moveTo(x, y - 9); g.lineTo(x + 5, y); g.lineTo(x, y + 9); g.lineTo(x - 5, y); g.closePath(); g.fill();
      }
      const gl = g.createRadialGradient(sx, sy - 300, 4, sx, sy - 300, 90); gl.addColorStop(0, 'rgba(200,230,255,.55)'); gl.addColorStop(1, 'rgba(160,200,255,0)'); g.fillStyle = gl; g.fillRect(sx - 100, sy - 400, 200, 200);
      g.restore();
    },
  };
  City.art.hallgate = {
    box: [480, 420, 240, 360],
    draw(g, o) {
      shadow(g, 110, 18);
      g.lineJoin = 'round';
      const pillar = (x) => { g.fillStyle = stoneGrad(g, x - 20, x + 20); g.strokeStyle = OL; g.lineWidth = 4; g.beginPath(); g.rect(x - 20, -270, 40, 270); g.fill(); g.stroke(); g.strokeStyle = 'rgba(70,80,130,.4)'; g.lineWidth = 2; for (let i = -1; i <= 1; i++) { g.beginPath(); g.moveTo(x + i * 10, -4); g.lineTo(x + i * 10, -260); g.stroke(); } };
      pillar(-100); pillar(100);
      g.fillStyle = stoneGrad(g, -130, 130); g.strokeStyle = OL; g.lineWidth = 4; g.beginPath(); g.moveTo(-126, -270); g.lineTo(-96, -330); g.lineTo(96, -330); g.lineTo(126, -270); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = '#2a2c4c'; g.beginPath(); g.moveTo(-80, 0); g.lineTo(-80, -190); g.quadraticCurveTo(0, -270, 80, -190); g.lineTo(80, 0); g.closePath(); g.fill(); g.stroke();
      g.strokeStyle = '#d8c070'; g.lineWidth = 3; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -230); g.stroke();
      for (const sgn of [-1, 1]) { g.fillStyle = '#e8d890'; g.strokeStyle = OL; g.lineWidth = 2.4; g.beginPath(); g.moveTo(sgn * 12, -300); for (let i = 1; i <= 5; i++) g.lineTo(sgn * (12 + i * 16), -300 - i * 5 + (i % 2) * 8); g.lineTo(sgn * 22, -284); g.closePath(); g.fill(); g.stroke(); }     // a valkyrie's wings over the door
    },
    animate(g, o, sx, sy, t) {
      const on = lit(o.place), a = .25 + .2 * Math.sin(t * 1.5);
      g.save(); g.globalCompositeOperation = 'lighter'; const gl = g.createRadialGradient(sx, sy - 100, 4, sx, sy - 100, 110); gl.addColorStop(0, `rgba(${on ? '255,230,150' : '120,170,255'},${on ? .55 : a})`); gl.addColorStop(1, 'rgba(120,170,255,0)'); g.fillStyle = gl; g.fillRect(sx - 120, sy - 220, 240, 240); g.restore();
    },
  };
  City.art.nest = {
    box: [460, 300, 230, 250],
    draw(g, o) {
      const rng = rngf(77);
      shadow(g, 120, 30);
      g.lineCap = 'round';
      for (let i = 0; i < 46; i++) {                                              // a ring of scorched branches and pale bones
        const a = rng() * 6.283, d = 70 + rng() * 40, x = Math.cos(a) * d, y = Math.sin(a) * d * .42 - 14 - rng() * 22, l = 30 + rng() * 34, b = rng() * 3;
        g.strokeStyle = OL; g.lineWidth = 8; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(b) * l, y + Math.sin(b) * l * .4); g.stroke();
        g.strokeStyle = rng() < .25 ? '#e6e0cc' : ['#6a4a3a', '#8a6a4a', '#4a3226'][i % 3]; g.lineWidth = 4.4; g.stroke();
      }
      ell(g, 0, -20, 74, 24, '#3a2a22', OL, 4);
      for (const [x, y] of [[-20, -30], [22, -26]]) { const gr = g.createRadialGradient(x - 6, y - 12, 2, x, y, 24); gr.addColorStop(0, '#fffde8'); gr.addColorStop(1, '#a8b0d0'); g.fillStyle = gr; g.strokeStyle = OL; g.lineWidth = 3; g.beginPath(); g.ellipse(x, y - 10, 17, 22, 0, 0, 6.283); g.fill(); g.stroke(); g.fillStyle = 'rgba(70,100,180,.4)'; for (let i = 0; i < 6; i++) { g.beginPath(); g.arc(x + (rng() - .5) * 20, y - 10 + (rng() - .5) * 28, 2.2, 0, 6.283); g.fill(); } }
    },
    animate(g, o, sx, sy, t) {
      const k = Math.floor(t * 3), rng = rngf(k * 131 + 7); if (rng() > .55) return;
      g.save(); g.globalCompositeOperation = 'lighter'; g.strokeStyle = 'rgba(190,230,255,.9)'; g.lineWidth = 1.8; g.beginPath(); let x = sx - 30 + rng() * 60, y = sy - 46; g.moveTo(x, y); for (let i = 0; i < 4; i++) { x += (rng() - .5) * 14; y -= 10 + rng() * 6; g.lineTo(x, y); } g.stroke(); g.restore();
    },
  };
})();
