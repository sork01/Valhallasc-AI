'use strict';
// Original canvas artwork for Ran's Deep (zone 8), registered with city.js (`City.art[kind] = { box, draw, animate }`): the living
// coral walls of the Net, swaying kelp, coral heads, giant clams, ship ribs, anchors, barnacled rocks, vents that breathe bubbles,
// pearl lamps, glowing anemones, sunken columns and the tidebells (the bells a `chime` quest rings: their ground circle is drawn by
// field.js, the bell itself swings here while it rings). `DeepArt.maelstrom` draws the waterspout that joins Bifrost Reach and the
// deep. Each entry draws once into a sprite; `animate` adds the moving parts. The scene's origin is the object's foot point;
// negative y is up; sprites are drawn at logical px (the cache doubles them).
(() => {
  const { iso, poly, prism } = City.kit;
  const OL = '#0a2433';
  const rngf = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const chime = id => window.Quests?.chime?.(id) || { state: 'none' };
  const CORAL = [['#ffb0a0', '#e0566e', '#8c2f55'], ['#ffd09a', '#e0803a', '#8a4020'], ['#e4b4f8', '#9a5ac8', '#5a2f88'], ['#a8f4de', '#3fb0a0', '#1d6a6a']];
  const WALL = [['#f4948a', '#d86a78', '#9a3f5e'], ['#f2b27a', '#cc8040', '#8e4c2c'], ['#cf9ae6', '#a468c8', '#6a3d94']];   // top, lit face, shaded face
  const shadow = (g, rx, ry, a = .3) => { g.fillStyle = `rgba(0,20,36,${a})`; g.beginPath(); g.ellipse(3, 4, rx, ry, 0, 0, 6.283); g.fill(); };
  const grad = (g, x0, y0, x1, y1, stops) => { const gr = g.createLinearGradient(x0, y0, x1, y1); stops.forEach(([p, c]) => gr.addColorStop(p, c)); return gr; };

  // ---- coral heads: used on the wall tops and as free-standing clumps --------------------------------------------------------------
  function coralHead(g, x, y, s, pal, rng, kind) {
    g.lineJoin = g.lineCap = 'round';
    if (kind === 0) {                                                       // a brain: a dome with winding grooves
      g.beginPath(); g.moveTo(x - s, y); g.bezierCurveTo(x - s, y - s * 1.15, x + s, y - s * 1.15, x + s, y); g.closePath();
      const gr = g.createRadialGradient(x - s * .3, y - s * .6, 1, x, y - s * .3, s * 1.1); gr.addColorStop(0, pal[0]); gr.addColorStop(.6, pal[1]); gr.addColorStop(1, pal[2]);
      g.fillStyle = gr; g.fill(); g.strokeStyle = OL; g.lineWidth = 2; g.stroke();
      g.strokeStyle = 'rgba(70,20,50,.45)'; g.lineWidth = 1.6;
      for (let i = 0; i < 4; i++) { const yy = y - s * (.2 + i * .2); g.beginPath(); g.moveTo(x - s * (.8 - i * .15), yy); g.bezierCurveTo(x - s * .3, yy - 4, x + s * .1, yy + 4, x + s * (.8 - i * .15), yy - 1); g.stroke(); }
    } else if (kind === 1) {                                                // staghorn: forking branches with bright tips
      for (let b = 0; b < 4; b++) {
        const dx = (b - 1.5) * s * .5, len = s * (1.1 + rng() * .8), lean = (b - 1.5) * .35 + (rng() - .5) * .3;
        const tx = x + dx + Math.sin(lean) * len, ty = y - Math.cos(lean) * len;
        g.strokeStyle = OL; g.lineWidth = 8; g.beginPath(); g.moveTo(x + dx, y); g.quadraticCurveTo(x + dx + lean * 10, y - len * .5, tx, ty); g.stroke();
        g.strokeStyle = pal[1]; g.lineWidth = 5; g.stroke();
        g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(x + dx + lean * 9, y - len * .55); g.lineTo(tx + 8 * Math.sign(lean || 1), ty + len * .25); g.stroke();
        g.strokeStyle = pal[1]; g.lineWidth = 3; g.stroke();
        g.fillStyle = pal[0]; g.beginPath(); g.arc(tx, ty, 3.2, 0, 6.283); g.fill();
      }
    } else if (kind === 2) {                                                // a sea fan: a veined half disc
      g.beginPath(); g.moveTo(x, y); g.lineTo(x - s * 1.05, y - s * .95); g.quadraticCurveTo(x, y - s * 1.7, x + s * 1.05, y - s * .95); g.closePath();
      g.fillStyle = grad(g, x, y, x, y - s * 1.6, [[0, pal[2]], [.6, pal[1]], [1, pal[0]]]); g.fill(); g.strokeStyle = OL; g.lineWidth = 2; g.stroke();
      g.strokeStyle = 'rgba(255,255,255,.3)'; g.lineWidth = 1.2;
      for (let i = -3; i <= 3; i++) { g.beginPath(); g.moveTo(x, y - 2); g.lineTo(x + i * s * .3, y - s * (1.15 - Math.abs(i) * .08)); g.stroke(); }
    } else {                                                                // organ tubes
      for (let i = 0; i < 5; i++) {
        const tx = x + (i - 2) * s * .42, h = s * (.7 + rng() * .8);
        g.fillStyle = grad(g, tx - 5, 0, tx + 5, 0, [[0, pal[0]], [.5, pal[1]], [1, pal[2]]]); g.strokeStyle = OL; g.lineWidth = 1.8;
        g.beginPath(); g.rect(tx - 5, y - h, 10, h); g.fill(); g.stroke();
        g.fillStyle = '#25101e'; g.beginPath(); g.ellipse(tx, y - h, 5, 2.4, 0, 0, 6.283); g.fill(); g.stroke();
      }
    }
  }
  // ---- the coral walls of the Net ---------------------------------------------------------------------------------------------------
  City.art.reefwall = {
    box: [320, 330, 160, 245],
    draw(g, o) {
      const w = o.width, d = o.depth, v = (o.v || 0) % 3, pal = WALL[v], rng = rngf(Math.round(w * 97 + d * 31) + v * 977), H = 74 + v * 6;
      g.lineJoin = 'round';
      shadow(g, (w + d) * 24, (w + d) * 11, .34);
      prism(g, w, d, H, pal[0], pal[1], pal[2]);
      g.strokeStyle = OL; g.lineWidth = 2;                                    // the outline of the block
      const e = iso(-w / 2, d / 2, H), c = iso(w / 2, d / 2, H), b = iso(w / 2, -d / 2, H), a = iso(-w / 2, -d / 2, H), e0 = iso(-w / 2, d / 2, 0), c0 = iso(w / 2, d / 2, 0), b0 = iso(w / 2, -d / 2, 0);
      g.beginPath(); g.moveTo(...e0); g.lineTo(...e); g.lineTo(...a); g.lineTo(...b); g.lineTo(...b0); g.lineTo(...c0); g.closePath(); g.stroke();
      g.beginPath(); g.moveTo(...e); g.lineTo(...c); g.lineTo(...b); g.moveTo(...c); g.lineTo(...c0); g.stroke();
      // pits and polyps on both visible faces
      for (let i = 0; i < 4 + Math.round(w + d); i++) {
        const onLeft = rng() < .55, u = rng(), z = 10 + rng() * (H - 22), p = onLeft ? iso(-w / 2 + u * w, d / 2, z) : iso(w / 2, -d / 2 + u * d, z), s = 4 + rng() * 6;
        g.fillStyle = 'rgba(40,10,40,.5)'; g.beginPath(); g.ellipse(p[0], p[1], s, s * .55, 0, 0, 6.283); g.fill();
        g.fillStyle = 'rgba(255,230,230,.32)'; g.beginPath(); g.ellipse(p[0] - 1, p[1] - 1.5, s * .7, s * .3, 0, 0, 6.283); g.fill();
      }
      g.strokeStyle = 'rgba(255,255,255,.2)'; g.lineWidth = 1.4;              // growth lines
      for (let i = 1; i < 4; i++) { const z = H * i / 4; g.beginPath(); g.moveTo(...iso(-w / 2, d / 2, z)); g.lineTo(...iso(w / 2, d / 2, z)); g.lineTo(...iso(w / 2, -d / 2, z)); g.stroke(); }
      // barnacles and green weed at the foot
      g.fillStyle = 'rgba(40,110,80,.45)';
      for (let i = 0; i < 3 + Math.round(w); i++) { const p = rng() < .6 ? iso(-w / 2 + rng() * w, d / 2, 3 + rng() * 10) : iso(w / 2, -d / 2 + rng() * d, 3 + rng() * 10); g.beginPath(); g.ellipse(p[0], p[1], 6 + rng() * 8, 3 + rng() * 3, 0, 0, 6.283); g.fill(); }
      // a crown of coral on the top
      const heads = 2 + Math.round((w + d) / 3);
      for (let i = 0; i < heads; i++) {
        const t = (i + .5) / heads, px = w >= d ? -w / 2 + t * w : (rng() - .5) * w * .5, py = w >= d ? (rng() - .5) * d * .5 : -d / 2 + t * d, p = iso(px, py, H - 1);
        coralHead(g, p[0], p[1] + 3, 11 + rng() * 6, CORAL[Math.floor(rng() * 4)], rng, Math.floor(rng() * 4));
      }
    },
  };

  // ---- kelp: a holdfast in the sprite, the fronds are drawn live so they sway ------------------------------------------------------------
  City.art.kelp = {
    box: [200, 340, 100, 320],
    draw(g, o) {
      const rng = rngf(100 + (o.v || 0) * 17);
      g.fillStyle = 'rgba(0,20,30,.3)'; g.beginPath(); g.ellipse(2, 3, 20, 7, 0, 0, 6.283); g.fill();
      for (let i = 0; i < 4; i++) { g.fillStyle = ['#5c5a66', '#6a6676', '#4a4856'][i % 3]; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(-12 + i * 8 + rng() * 4, -2 - rng() * 3, 9, 5, 0, 0, 6.283); g.fill(); g.stroke(); }
    },
    animate(g, o, sx, sy, t) {
      const v = (o.v || 0) % 4, n = 3 + (v % 2), h0 = 150 + v * 22;
      g.save(); g.translate(sx, sy - 4); g.lineCap = 'round';
      for (let i = 0; i < n; i++) {
        const base = (i - (n - 1) / 2) * 9, h = h0 * (.7 + .3 * ((i * 37 + v * 11) % 10) / 10), ph = o.x * 1.7 + o.y * 1.1 + i * 1.3, segs = 9;
        const pts = [[base, 0]];
        for (let k = 1; k <= segs; k++) { const f = k / segs; pts.push([base + Math.sin(t * 1.1 + ph + f * 2.6) * 16 * f * f + (i - 1) * 6 * f, -h * f]); }
        for (const [w, col] of [[9, OL], [6, ['#2e7a48', '#3f8a3a', '#5a8a2e', '#2f8a6a'][v]], [2, 'rgba(210,255,190,.45)']]) {
          g.strokeStyle = col; g.lineWidth = w * (col === OL ? 1 : 1);
          g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
          for (let k = 1; k < pts.length; k++) g.lineTo(pts[k][0], pts[k][1]);
          g.stroke();
        }
        g.fillStyle = '#7ab040'; for (let k = 3; k < segs; k += 3) { g.beginPath(); g.ellipse(pts[k][0] + 5, pts[k][1], 5, 2.4, .6, 0, 6.283); g.fill(); }   // gas bladders
      }
      g.restore();
    },
  };
  City.art.coral = {
    box: [220, 230, 110, 200],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(300 + v * 23);
      shadow(g, 36, 10, .28);
      g.fillStyle = '#5a566a'; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(0, -2, 26, 9, 0, 0, 6.283); g.fill(); g.stroke();
      coralHead(g, -8, -4, 20, CORAL[v], rng, v);
      coralHead(g, 14, -2, 13, CORAL[(v + 1) % 4], rng, (v + 2) % 4);
    },
  };
  City.art.clam = {
    box: [180, 140, 90, 110],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(500 + v);
      shadow(g, 36, 10, .3);
      const shell = ['#e8dcc8', '#e8c8c0', '#c8d8e0', '#d8d0f0'][v];
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 2.4;
      g.fillStyle = '#7a3a58'; g.beginPath(); g.ellipse(0, -10, 28, 9, 0, 0, 6.283); g.fill(); g.stroke();                       // the mantle
      g.fillStyle = '#c85a82'; g.beginPath(); g.ellipse(0, -12, 21, 5.4, 0, 0, 6.283); g.fill();
      g.fillStyle = grad(g, -30, 0, 30, 0, [[0, shell], [.5, '#fff8ec'], [1, '#a89888']]);
      g.beginPath(); g.moveTo(-30, -8); g.bezierCurveTo(-34, -46, 34, -46, 30, -8); g.quadraticCurveTo(0, 2, -30, -8); g.closePath(); g.fill(); g.stroke();     // the upper valve
      g.strokeStyle = 'rgba(120,100,90,.5)'; g.lineWidth = 1.6; for (let i = -3; i <= 3; i++) { g.beginPath(); g.moveTo(i * 3, -6); g.quadraticCurveTo(i * 8, -24, i * 9.5, -38 + Math.abs(i) * 3); g.stroke(); }
      if (v !== 3) { g.fillStyle = '#fffaf0'; g.strokeStyle = '#8a8070'; g.lineWidth = 1; g.beginPath(); g.arc(4, -10, 3.6, 0, 6.283); g.fill(); g.stroke(); }
    },
    animate(g, o, sx, sy, t) { if ((o.v || 0) % 4 === 3) return; const a = Math.max(0, Math.sin(t * 1.5 + o.x * 2.1)); g.save(); g.globalCompositeOperation = 'lighter'; g.globalAlpha = a * .7; g.fillStyle = '#fff'; g.fillRect(sx + 1, sy - 15, 5, 1.4); g.fillRect(sx + 3, sy - 17.5, 1.4, 5); g.restore(); },
  };
  City.art.shiprib = {
    box: [300, 300, 150, 262],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(700 + v * 13), lean = (v - 1.5) * .09;
      shadow(g, 46, 12, .28);
      g.lineCap = 'round'; g.lineJoin = 'round';
      const wood = ['#6a4a34', '#7a5a40', '#5a4030', '#745238'][v];
      g.fillStyle = '#4a3a2c'; g.strokeStyle = OL; g.lineWidth = 2.4; g.beginPath(); g.rect(-50, -9, 100, 10); g.fill(); g.stroke();      // keel plank
      const ribs = 3 + (v % 2);
      for (let i = 0; i < ribs; i++) {
        const x = -34 + i * (68 / (ribs - 1)), h = 118 - Math.abs(i - (ribs - 1) / 2) * 20 - rng() * 14, bend = (x < 0 ? -1 : 1) * (22 + rng() * 10);
        for (const [w, col] of [[15, OL], [10, wood], [3, 'rgba(255,230,190,.3)']]) {
          g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(x, -6); g.quadraticCurveTo(x + bend * .2 + lean * 90, -h * .6, x + bend + lean * 160, -h); g.stroke();
        }
      }
      g.fillStyle = 'rgba(210,225,215,.7)'; for (let i = 0; i < 12; i++) { g.beginPath(); g.arc(-44 + rng() * 88, -10 - rng() * 70, 1.8 + rng() * 1.6, 0, 6.283); g.fill(); }   // barnacles
      g.fillStyle = 'rgba(40,120,80,.55)'; for (let i = 0; i < 4; i++) { g.beginPath(); g.ellipse(-30 + rng() * 60, -4, 9, 4, 0, 0, 6.283); g.fill(); }
    },
  };
  City.art.anchor = {
    box: [160, 210, 80, 180],
    draw(g, o) {
      shadow(g, 24, 8, .3);
      g.lineCap = g.lineJoin = 'round';
      const iron = '#5a5e6a';
      for (const [w, col] of [[12, OL], [7, iron], [2, 'rgba(255,255,255,.2)']]) {
        g.strokeStyle = col; g.lineWidth = w;
        g.beginPath(); g.moveTo(2, -6); g.lineTo(2, -118); g.stroke();                       // shank
        g.beginPath(); g.moveTo(-18, -96); g.lineTo(22, -96); g.stroke();                    // stock
        g.beginPath(); g.moveTo(-26, -34); g.quadraticCurveTo(-12, 8, 2, -6); g.quadraticCurveTo(16, 8, 30, -34); g.stroke();   // arms
        g.beginPath(); g.arc(2, -126, 7, 0, 6.283); g.stroke();                              // ring
      }
      g.fillStyle = '#7a4a2a'; for (let i = 0; i < 6; i++) { g.beginPath(); g.ellipse(2 + (i % 2 ? 4 : -4), -20 - i * 16, 4, 2.4, 0, 0, 6.283); g.fill(); }
      g.fillStyle = 'rgba(40,120,80,.55)'; g.beginPath(); g.ellipse(2, -8, 16, 5, 0, 0, 6.283); g.fill();
    },
  };
  City.art.deeprock = {
    box: [220, 180, 110, 150],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(900 + v * 17), s = 1 + v * .12;
      shadow(g, 36 * s, 10, .3);
      const pts = [[-34, 0], [-38, -16], [-22, -38], [4, -46], [30, -30], [38, -9], [28, 0]].map(([x, y]) => [x * s * (.92 + rng() * .16), y * s * (.92 + rng() * .16)]);
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 3.4; g.fillStyle = grad(g, -38, -46, 38, 0, [[0, '#8a96a8'], [.55, '#5a6678'], [1, '#2c3648']]);
      g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = 'rgba(220,235,225,.7)'; for (let i = 0; i < 14; i++) { g.beginPath(); g.arc((rng() - .5) * 56 * s, -8 - rng() * 30, 1.6 + rng() * 1.8, 0, 6.283); g.fill(); }
      g.fillStyle = 'rgba(46,130,90,.55)'; g.beginPath(); g.ellipse(-8 * s, -42 * s, 17, 5, 0, 0, 6.283); g.fill();
    },
  };
  City.art.vent = {
    box: [180, 260, 90, 220],
    draw(g, o) {
      shadow(g, 28, 9, .3);
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 3;
      g.fillStyle = grad(g, -26, 0, 26, 0, [[0, '#4a4a58'], [.5, '#2c2c3a'], [1, '#17171f']]);
      g.beginPath(); g.moveTo(-26, 0); g.lineTo(-17, -52); g.lineTo(-10, -86); g.lineTo(-4, -96); g.lineTo(8, -88); g.lineTo(15, -48); g.lineTo(26, 0); g.closePath(); g.fill(); g.stroke();
      g.fillStyle = '#1a1018'; g.beginPath(); g.ellipse(2, -92, 8, 3.4, 0, 0, 6.283); g.fill();
      g.fillStyle = 'rgba(255,170,90,.5)'; g.beginPath(); g.ellipse(2, -93, 5, 2, 0, 0, 6.283); g.fill();
      g.fillStyle = 'rgba(240,225,170,.5)'; for (let i = 0; i < 6; i++) { g.beginPath(); g.arc(-20 + i * 7, -10 - (i % 3) * 14, 2, 0, 6.283); g.fill(); }   // sulphur crust
    },
    animate(g, o, sx, sy, t) {
      g.save(); g.globalAlpha = .6;
      for (let i = 0; i < 9; i++) { const f = ((t * .45 + i / 9 + o.x * .13) % 1), y = sy - 94 - f * 150, x = sx + 2 + Math.sin(f * 9 + i * 2.1) * 9 * f, r = 2.2 + f * 3.4; g.globalAlpha = (1 - f) * .75; g.strokeStyle = '#d8f4ff'; g.lineWidth = 1.4; g.beginPath(); g.arc(x, y, r, 0, 6.283); g.stroke(); g.fillStyle = 'rgba(255,255,255,.2)'; g.fill(); }
      g.restore();
    },
  };
  City.art.pearllamp = {
    box: [110, 230, 55, 195],
    draw(g, o) {
      const v = (o.v || 0) % 3;
      shadow(g, 14, 5, .3);
      g.lineCap = 'round';
      g.strokeStyle = OL; g.lineWidth = 7; g.beginPath(); g.moveTo(0, -2); g.quadraticCurveTo(-8 + v * 6, -34, 0, -66); g.stroke();
      g.strokeStyle = '#6a8a7a'; g.lineWidth = 3.6; g.stroke();
      g.fillStyle = '#7a8a8a'; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(0, -3, 11, 4, 0, 0, 6.283); g.fill(); g.stroke();
      g.fillStyle = '#2a4a46'; g.beginPath(); g.ellipse(0, -68, 11, 4.4, 0, 0, 6.283); g.fill(); g.stroke();       // the cup
    },
    animate(g, o, sx, sy, t) {
      const p = .75 + .25 * Math.sin(t * 1.8 + o.x * 3.1 + o.y), x = sx, y = sy - 78;
      g.save(); g.globalCompositeOperation = 'lighter';
      const halo = g.createRadialGradient(x, y, 2, x, y, 64); halo.addColorStop(0, `rgba(200,255,240,${.5 * p})`); halo.addColorStop(1, 'rgba(60,200,200,0)'); g.fillStyle = halo; g.beginPath(); g.arc(x, y, 64, 0, 6.283); g.fill();
      g.restore();
      const gr = g.createRadialGradient(x - 3, y - 4, 1, x, y, 11); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.5, '#d0fff0'); gr.addColorStop(1, '#6ad0c0');
      g.fillStyle = gr; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.arc(x, y, 10.5, 0, 6.283); g.fill(); g.stroke();
    },
  };
  City.art.anemone = {
    box: [160, 150, 80, 120],
    draw(g, o) {
      shadow(g, 22, 7, .25);
      g.fillStyle = '#4a4a5a'; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(0, -2, 17, 6, 0, 0, 6.283); g.fill(); g.stroke();
    },
    animate(g, o, sx, sy, t) {
      const v = (o.v || 0) % 4, hue = [165, 190, 290, 320][v], n = 11, pulse = .6 + .4 * Math.sin(t * 1.3 + o.x * 2.7);
      g.save(); g.translate(sx, sy - 4); g.lineCap = 'round';
      g.globalCompositeOperation = 'lighter';
      const halo = g.createRadialGradient(0, -18, 2, 0, -18, 42); halo.addColorStop(0, `hsla(${hue},100%,70%,${.28 * pulse})`); halo.addColorStop(1, `hsla(${hue},100%,60%,0)`); g.fillStyle = halo; g.beginPath(); g.arc(0, -18, 42, 0, 6.283); g.fill();
      g.globalCompositeOperation = 'source-over';
      for (let i = 0; i < n; i++) {
        const a = (i / n - .5) * 2.4, len = 24 + (i % 3) * 5, sway = Math.sin(t * 1.6 + i * 1.7 + o.x) * 4;
        const tx = Math.sin(a) * len * .8 + sway, ty = -Math.cos(a) * len;
        g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(Math.sin(a) * 6, -3); g.quadraticCurveTo(Math.sin(a) * len * .5 + sway * .3, -len * .55, tx, ty); g.stroke();
        g.strokeStyle = `hsl(${hue + i * 6},80%,${58 + pulse * 10}%)`; g.lineWidth = 3.4; g.stroke();
        g.fillStyle = `hsl(${hue + 40},100%,${82 + pulse * 10}%)`; g.beginPath(); g.arc(tx, ty, 2.8, 0, 6.283); g.fill();
      }
      g.restore();
    },
  };
  City.art.sunkencolumn = {
    box: [150, 280, 75, 240],
    draw(g, o) {
      const v = (o.v || 0) % 4, rng = rngf(1100 + v * 19), h = [150, 110, 190, 90][v], tilt = (v - 1.5) * .03;
      shadow(g, 24, 8, .3);
      g.lineJoin = 'round'; g.strokeStyle = OL; g.lineWidth = 2.6;
      const stone = grad(g, -16, 0, 16, 0, [[0, '#c8d0c8'], [.5, '#9ca8a4'], [1, '#56625f']]);
      g.fillStyle = '#7a8480'; g.beginPath(); g.rect(-20, -12, 40, 12); g.fill(); g.stroke();                       // plinth
      g.fillStyle = stone; g.beginPath(); g.moveTo(-14, -12); g.lineTo(-13 + tilt * h, -h); g.lineTo(11 + tilt * h, -h + 3 + rng() * 6); g.lineTo(14, -12); g.closePath(); g.fill(); g.stroke();   // the shaft, broken at the top
      g.strokeStyle = 'rgba(40,50,48,.45)'; g.lineWidth = 1.6; for (const f of [-6, 0, 6]) { g.beginPath(); g.moveTo(f, -14); g.lineTo(f + tilt * h, -h + 8); g.stroke(); }
      g.fillStyle = 'rgba(225,235,225,.65)'; for (let i = 0; i < 10; i++) { g.beginPath(); g.arc((rng() - .5) * 24, -16 - rng() * (h - 30), 1.6 + rng() * 1.6, 0, 6.283); g.fill(); }
      g.fillStyle = 'rgba(46,130,90,.55)'; g.beginPath(); g.ellipse(0, -12, 20, 6, 0, 0, 6.283); g.fill();
      if (v === 0 || v === 2) { g.strokeStyle = OL; g.lineWidth = 6; g.beginPath(); g.moveTo(8, -h + 6); g.quadraticCurveTo(22, -h * .6, 14, -h * .35); g.stroke(); g.strokeStyle = '#3f8a3a'; g.lineWidth = 3; g.stroke(); }
    },
  };

  // ---- the tidebell: a whalebone arch; the bell swings while it rings -----------------------------------------------------------------
  City.art.tidebell = {
    box: [230, 330, 115, 290],
    draw(g, o) {
      shadow(g, 38, 12, .32);
      g.lineCap = 'round';
      const ivory = ['#fff6e4', '#e8d8b8', '#a89874'];
      for (const side of [-1, 1]) {
        for (const [w, col] of [[17, OL], [12, ivory[1]], [5, ivory[0]], [2, 'rgba(120,100,70,.5)']]) {
          g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.moveTo(side * 38, -2); g.bezierCurveTo(side * 52, -80, side * 30, -160, 0, -178); g.stroke();
        }
        g.fillStyle = ivory[2]; g.strokeStyle = OL; g.lineWidth = 2; g.beginPath(); g.ellipse(side * 38, -3, 11, 4.4, 0, 0, 6.283); g.fill(); g.stroke();
      }
      g.strokeStyle = OL; g.lineWidth = 11; g.beginPath(); g.moveTo(-8, -176); g.lineTo(8, -176); g.stroke();
      g.strokeStyle = '#7a5a34'; g.lineWidth = 6; g.stroke();                                                      // the beam the bell hangs from
      g.fillStyle = 'rgba(40,120,80,.5)'; for (const x of [-40, 40]) { g.beginPath(); g.ellipse(x, -8, 12, 5, 0, 0, 6.283); g.fill(); }
      g.fillStyle = 'rgba(220,235,225,.6)'; for (let i = 0; i < 8; i++) { g.beginPath(); g.arc((i % 2 ? 1 : -1) * (36 + i * 2), -20 - i * 14, 2, 0, 6.283); g.fill(); }
    },
    animate(g, o, sx, sy, t) {
      const c = chime(o.place), ringing = c.state === 'ringing', fresh = ringing ? Math.min(1, (c.left || 0) / (c.burn || 1)) : 0;
      const swing = ringing ? Math.sin(t * 9) * (.12 + .26 * fresh) : c.state === 'waiting' ? Math.sin(t * 1.3) * .03 : 0;
      const glow = ringing ? .35 + .65 * fresh : c.state === 'done' ? .3 : c.state === 'waiting' ? .12 + .08 * Math.sin(t * 2.4) : 0;
      g.save(); g.translate(sx, sy - 176);
      if (glow > 0) {
        g.globalCompositeOperation = 'lighter';
        const h = g.createRadialGradient(0, 38, 4, 0, 38, 110); const col = c.state === 'done' ? '255,220,120' : ringing ? '170,240,255' : '255,190,110';
        h.addColorStop(0, `rgba(${col},${.55 * glow})`); h.addColorStop(1, `rgba(${col},0)`); g.fillStyle = h; g.beginPath(); g.arc(0, 38, 110, 0, 6.283); g.fill();
        g.globalCompositeOperation = 'source-over';
      }
      g.rotate(swing); g.lineJoin = 'round';
      g.strokeStyle = '#6a5030'; g.lineWidth = 3; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, 16); g.stroke();                       // the rope
      const bell = new Path2D(); bell.moveTo(-9, 20); bell.bezierCurveTo(-11, 40, -26, 56, -30, 68); bell.lineTo(30, 68); bell.bezierCurveTo(26, 56, 11, 40, 9, 20); bell.closePath();
      g.fillStyle = grad(g, -30, 0, 30, 0, [[0, ringing ? '#fff0b0' : '#e8c070'], [.45, ringing ? '#ffd860' : '#c08a38'], [1, '#6a4418']]);
      g.fill(bell); g.strokeStyle = OL; g.lineWidth = 2.6; g.stroke(bell);
      g.strokeStyle = 'rgba(255,255,255,.45)'; g.lineWidth = 2; g.beginPath(); g.moveTo(-8, 28); g.quadraticCurveTo(-16, 46, -22, 60); g.stroke();
      g.fillStyle = '#4a2c10'; g.beginPath(); g.ellipse(0, 70, 30, 6, 0, 0, 6.283); g.fill(); g.stroke();
      g.fillStyle = '#2a1608'; g.beginPath(); g.arc(Math.sin(t * 9 + 1) * (ringing ? 5 : 1), 74, 5, 0, 6.283); g.fill();                    // the clapper
      g.restore();
      if (ringing) {                                                                                                                 // sound rings leaving the bell
        g.save(); g.globalCompositeOperation = 'lighter';
        for (let i = 0; i < 3; i++) { const p = (t * .9 + i / 3) % 1; g.globalAlpha = (1 - p) * .55 * (.4 + .6 * fresh); g.strokeStyle = '#bff4ff'; g.lineWidth = 3 * (1 - p) + 1; g.beginPath(); g.ellipse(sx, sy - 118, 18 + p * 120, 10 + p * 66, 0, 0, 6.283); g.stroke(); }
        g.restore();
      }
    },
  };

  // ---- the Maelstrom: a waterspout that stands between Bifrost Reach and the sea floor -----------------------------------------------------
  window.DeepArt = {
    // `fromDeep`: the view from the sea floor (the spout rises to the surface); otherwise from the Eyrie (it falls out of the storm).
    maelstrom(g, sx, sy, t, label, fromDeep) {
      g.save(); g.translate(sx, sy);
      g.fillStyle = 'rgba(0,20,40,.32)'; g.beginPath(); g.ellipse(0, 4, 74, 26, 0, 0, 6.283); g.fill();
      const H = 200, layers = 22;
      for (let i = layers; i >= 0; i--) {                                                                                          // the funnel, wider towards the top
        const f = i / layers, y = -f * H, rx = 22 + f * 52 + Math.sin(f * 7 - t * 2) * 3, ry = rx * .5, a = .42 - f * .2;
        g.fillStyle = `hsla(${186 + f * 14}, 78%, ${34 + f * 24}%, ${a})`; g.beginPath(); g.ellipse(Math.sin(t * .8 + f * 3) * 4 * f, y, rx, ry, 0, 0, 6.283); g.fill();
      }
      g.lineCap = 'round'; g.lineWidth = 3;
      for (let i = 0; i < 16; i++) {                                                                                               // spiral streaks
        const f = (i * .0625 + t * .22) % 1, y = -f * H, rx = 20 + f * 56, a = t * 3.2 + i * 2.2 + f * 6;
        g.strokeStyle = `rgba(214,250,255,${.55 * (1 - f * .6)})`; g.beginPath(); g.ellipse(Math.sin(t * .8 + f * 3) * 4 * f, y, rx, rx * .5, 0, a, a + 1.5); g.stroke();
      }
      g.fillStyle = 'rgba(240,255,255,.7)';
      for (let i = 0; i < 12; i++) { const a = t * 2.4 + i * .52, r = 38 + (i % 3) * 10; g.beginPath(); g.ellipse(Math.cos(a) * r, Math.sin(a) * r * .5 + 2, 4 + (i % 2) * 2, 2, 0, 0, 6.283); g.fill(); }   // foam at the foot
      if (fromDeep) { g.fillStyle = 'rgba(190,240,255,.55)'; g.beginPath(); g.ellipse(0, -H, 76, 36, 0, 0, 6.283); g.fill(); }                                      // the bright surface above
      else { g.fillStyle = 'rgba(40,36,76,.8)'; g.beginPath(); g.ellipse(0, -H - 4, 86, 40, 0, 0, 6.283); g.fill(); }                                                // the storm it falls from
      g.restore();
      g.save(); g.shadowColor = 'hsl(186,100%,60%)'; g.shadowBlur = 8; g.font = '15px "Jua", sans-serif'; g.textAlign = 'center'; g.lineWidth = 3; g.strokeStyle = OL; g.fillStyle = 'hsl(190,100%,88%)';
      g.strokeText(label, sx, sy - H - 36); g.fillText(label, sx, sy - H - 36); g.restore();
    },
  };
})();
