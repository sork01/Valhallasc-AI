'use strict';
// Heartwood is a city INSIDE the world-tree (owner, 2026-11-09: "buildings that could be found inside a big tree"): everything here is grown or carved wood, never masonry. Burl-pod homes
// that bulge out of the inner trunk wall, a hall of carved shelves, a forge round a vent of glowing pith, a loom on root posts, a seed chapel of curled root petals, the iris door of the Seed Vault.
// Every structure is isometric (City.kit iso/prism on its map width x depth, door on the +y wall through wallPlane), never a flat front elevation (owner rule, 2026-11-09).
(() => {
  const {iso, poly, line, ellipse, prism, wallPlane} = City.kit, TAU = Math.PI * 2;
  const BARK = [['#b08a5a', '#8e6c44', '#6d5133'], ['#a88256', '#866340', '#664a2f'], ['#b8925f', '#96754b', '#745738'], ['#a37c4f', '#826040', '#62472d']];
  const shadow = (g, w, d) => { const rx = (w + d) * 22 + 10; ellipse(g, 6, 12, rx, rx * .3, 'rgba(24,14,6,.3)', null); };
  const bark = v => BARK[((v % 4) + 4) % 4];
  // grain: thin dark lines up the two visible faces
  function grain(g, w, d, z0, z1, n) {
    for (let i = 1; i < n; i++) {
      const t = i / n;
      line(g, [iso(-w / 2 + w * t, d / 2, z0), iso(-w / 2 + w * t, d / 2, z1)], 'rgba(52,34,18,.32)', 1.3);
      line(g, [iso(w / 2, -d / 2 + d * t, z0), iso(w / 2, -d / 2 + d * t, z1)], 'rgba(40,26,14,.32)', 1.3);
    }
  }
  // a round burl knob bulging from a face
  function burl(g, p, r, c) { ellipse(g, p[0], p[1], r, r * .86, c[1], 'rgba(40,26,14,.5)'); ellipse(g, p[0] - r * .25, p[1] - r * .3, r * .5, r * .36, c[0], null); }
  // an arched doorway cut into the +y wall: dark hollow, an amber lit room beyond, a root lintel
  function door(g, x, y, z, rw, rh) {
    g.save(); wallPlane(g, ...iso(x, y, z), 'y');
    ellipse(g, 0, -rh * .55, rw + 3, rh * .62 + 3, '#4a331f', null);
    ellipse(g, 0, -rh * .55, rw, rh * .6, '#241608', null);
    ellipse(g, 1, -rh * .45, rw * .62, rh * .44, '#f0be62', null);
    ellipse(g, 2, -rh * .38, rw * .34, rh * .26, '#fff0b8', null);
    line(g, [[-rw - 3, -rh * .2], [-rw * .6, -rh * 1.05], [rw * .6, -rh * 1.05], [rw + 3, -rh * .2]], '#7c5c38', 4);
    g.restore();
  }
  // a round amber-glass window on the +x wall
  function window_(g, x, y, z, r) {
    g.save(); wallPlane(g, ...iso(x, y, z), 'x');
    ellipse(g, 0, 0, r + 3, r + 3, '#5a3f26', null);
    ellipse(g, 0, 0, r, r, '#e8b24e', null);
    ellipse(g, -r * .2, -r * .2, r * .5, r * .5, '#fff0b0', null);
    line(g, [[-r, 0], [r, 0]], '#5a3f26', 1.5); line(g, [[0, -r], [0, r]], '#5a3f26', 1.5);
    g.restore();
  }
  // a living dome: stacked rings of bark, a cap of moss and a few leaves
  function dome(g, w, d, z, h, v) {
    const c = iso(0, 0, z), rx = (w + d) * 15.5, ry = rx * .5, b = bark(v);
    ellipse(g, c[0], c[1], rx, ry, b[1], 'rgba(40,26,14,.55)');
    for (let i = 1; i <= 4; i++) {
      const k = 1 - i * .2;
      ellipse(g, c[0], c[1] - h * i / 4, rx * k, ry * k, i % 2 ? b[0] : b[1], 'rgba(40,26,14,.4)');
    }
    ellipse(g, c[0], c[1] - h * 1.02, rx * .22, ry * .22, '#6fb36e', null);
    for (let j = 0; j < 4; j++) ellipse(g, c[0] + (j - 1.5) * rx * .12, c[1] - h * 1.02 - 3 + (j % 2) * 3, 6, 3.4, j % 2 ? '#8fcf7e' : '#58a265', null);
  }

  // ---- a burl-pod home: a plinth of roots, a barrel of living bark with burls, a dome, an arched door and an amber window
  const home = (g, o, big) => {
    const w = o.width || 4.6, d = o.depth || 3.8, h = big ? 128 : 92, b = bark(o.v);
    shadow(g, w, d);
    prism(g, w + .5, d + .5, 8, '#6f5236', '#4f3a26', '#3b2b1c');                    // the root plinth
    prism(g, w, d, h, b[0], b[1], b[2], 8);
    grain(g, w, d, 8, 8 + h, 7);
    burl(g, iso(-w / 2 + .9, d / 2, 8 + h * .72), 11, b); burl(g, iso(w / 2, -d / 2 + .8, 8 + h * .35), 9, b); burl(g, iso(w / 2, d / 2 - .7, 8 + h * .78), 8, b);
    prism(g, w * .62, .5, 5, '#c8a470', '#9c7a4c', '#7a5c38', 8 + h * .46);       // a bark-plank balcony over the door
    dome(g, w + .2, d + .2, 8 + h, 30 + (o.v % 2) * 8, o.v);
    door(g, 0, d / 2 + .01, 8, 17, 46);
    window_(g, w / 2 + .01, -.2, 8 + h * .55, 10);
    // a hanging sap-lamp by the door
    line(g, [iso(-w / 2 + .5, d / 2 + .05, 8 + h * .5), iso(-w / 2 + .5, d / 2 + .05, 8 + h * .38)], '#5a3f26', 1.5);
    const l = iso(-w / 2 + .5, d / 2 + .05, 8 + h * .34); ellipse(g, l[0], l[1], 5, 7, '#f6d77a', '#7c5c38');
  };
  City.art.heart_burl = {box: [640, 520, 320, 420], draw: (g, o) => home(g, o, false)};
  City.art.heart_burl_tall = {box: [640, 600, 320, 500], draw: (g, o) => home(g, o, true)};

  // ---- a market stall: four root poles, a woven leaf awning tilted over a plank counter, baskets
  City.art.heart_stall = {box: [420, 340, 210, 270], draw(g, o) {
    const w = o.width || 3, d = o.depth || 2, b = bark(o.v);
    shadow(g, w, d);
    prism(g, w, d * .6, 22, b[0], b[1], b[2], 0);
    for (const [x, y, hh] of [[-w / 2, -d / 2, 92], [w / 2, -d / 2, 92], [-w / 2, d / 2, 70], [w / 2, d / 2, 70]]) { g.save(); g.translate(...iso(x, y)); prism(g, .22, .22, hh, '#b08a5a', '#8e6c44', '#6d5133'); g.restore(); }
    const a = iso(-w / 2 - .2, d / 2 + .3, 70), bb = iso(w / 2 + .2, d / 2 + .3, 70), c = iso(w / 2 + .2, -d / 2 - .1, 92), e = iso(-w / 2 - .2, -d / 2 - .1, 92);
    poly(g, [a, bb, c, e], ['#7fbf72', '#d6a74a', '#6fa8b0'][o.v % 3], '#3f5a3a', 2);
    for (let i = 1; i < 6; i++) { const t = i / 6; line(g, [[a[0] + (bb[0] - a[0]) * t, a[1] + (bb[1] - a[1]) * t], [e[0] + (c[0] - e[0]) * t, e[1] + (c[1] - e[1]) * t]], 'rgba(30,50,26,.4)', 1.4); }
    for (let i = 0; i < 4; i++) { const p = iso(-w / 2 + .5 + i * (w - 1) / 3, d * .08, 26); ellipse(g, p[0], p[1], 8, 5.5, ['#e8a24c', '#a9d26a', '#d85a4a', '#f2d26a'][(i + o.v) % 4], '#3a2a18'); }
  }};

  // ---- the Amber Library: a long hall of carved bark, its +y wall cut with tall amber-glass slits, a living dome roof
  City.art.amber_library = {box: [960, 760, 480, 600], draw(g, o) {
    const w = o.width || 8, d = o.depth || 6, h = 140, b = bark(1);
    shadow(g, w, d);
    prism(g, w + .5, d + .5, 8, '#6f5236', '#4f3a26', '#3b2b1c');
    prism(g, w, d, h, b[0], b[1], b[2], 8);
    grain(g, w, d, 8, 8 + h, 11);
    for (let i = 0; i < 4; i++) {                                                      // tall amber slits in the +y wall
      g.save(); wallPlane(g, ...iso(-w / 2 + 1.2 + i * (w - 2.4) / 3, d / 2 + .01, 8 + h * .5), 'y');
      ellipse(g, 0, 0, 9, 34, '#3a2714', null); ellipse(g, 0, 1, 6, 30, ['#f2b94e', '#f6d577', '#e8a43e', '#f9e09a'][i], null);
      for (let k = -2; k <= 2; k++) line(g, [[-6, k * 11], [6, k * 11]], '#5a3f26', 1.4);
      g.restore();
    }
    for (let i = 0; i < 3; i++) window_(g, w / 2 + .01, -d / 2 + 1.2 + i * (d - 2.4) / 2, 8 + h * .55, 9);
    door(g, 0, d / 2 + .02, 8, 19, 48);
    burl(g, iso(w / 2, d / 2 - 1.2, 8 + h * .82), 10, b);
    dome(g, w + .3, d + .3, 8 + h, 44, 1);
    for (let j = 0; j < 4; j++) { const p = iso(-w / 2 + 1 + j * (w - 2) / 3, d / 2 + .5, 8 + h + 4); ellipse(g, p[0], p[1], 7, 9, ['#f6d77a', '#a8e0ad', '#f6d77a', '#a8e0ad'][j], '#7c5c38'); }       // hanging glow fruit under the eave
  }};

  // ---- the Pith Forge: a squat hall round a vent of glowing pith, a hollow-log chimney with a green-gold flame
  City.art.pith_forge = {box: [760, 720, 380, 570], draw(g, o) {
    const w = o.width || 6, d = o.depth || 5, h = 74, b = bark(2);
    shadow(g, w, d);
    prism(g, w + .5, d + .5, 8, '#6f5236', '#4f3a26', '#3b2b1c');
    prism(g, w, d, h, b[0], b[1], b[2], 8);
    grain(g, w, d, 8, 8 + h, 9);
    door(g, -w / 4, d / 2 + .01, 8, 16, 42);
    g.save(); wallPlane(g, ...iso(w / 4, d / 2 + .01, 8 + h * .35), 'y');           // the glowing forge mouth
    ellipse(g, 0, 0, 20, 14, '#2a1a0e', null); ellipse(g, 0, 1, 15, 10, '#e8742a', null); ellipse(g, 0, 2, 9, 6, '#ffd070', null);
    g.restore();
    const c = iso(w * .12, -d * .12, 8 + h);                                         // the hollow-log chimney
    prism(g, 1.3, 1.3, 90, '#a88256', '#866340', '#664a2f', 8 + h);
    const t = iso(w * .12, -d * .12, 8 + h + 90);
    ellipse(g, t[0], t[1], 25, 12, '#3a2a18', null); ellipse(g, t[0], t[1] + 1, 18, 8, '#8fe0a0', null); ellipse(g, t[0], t[1] - 5, 9, 12, '#f6e27a', null);
    for (let i = 0; i < 3; i++) line(g, [iso(-w / 2 + .6, d / 2 + .02, 20 + i * 18), iso(w / 2 - .6, d / 2 + .02, 26 + i * 18)], '#7a5c38', 2);        // sap pipes
    window_(g, w / 2 + .01, -.4, 8 + h * .5, 9);
  }};

  // ---- the Root Loom: a timber frame of four root posts and two beams over the +y wall, a woven panel of coloured threads between them
  City.art.root_loom = {box: [620, 520, 310, 400], draw(g, o) {
    const w = o.width || 5, d = o.depth || 3.4, h = 96;
    shadow(g, w, d);
    prism(g, w, d, 6, '#8a6a45', '#6d5133', '#533d27');
    for (const [x, y] of [[-w / 2 + .2, d / 2 - .2], [w / 2 - .2, d / 2 - .2], [-w / 2 + .2, -d / 2 + .2], [w / 2 - .2, -d / 2 + .2]]) { g.save(); g.translate(...iso(x, y)); prism(g, .34, .34, h, '#b08a5a', '#8e6c44', '#6d5133', 6); g.restore(); }
    prism(g, w, .34, 9, '#c4a070', '#9a7a4c', '#7a5c38', 6 + h - 9);
    prism(g, .34, d, 9, '#c4a070', '#9a7a4c', '#7a5c38', 6 + h - 9);
    g.save(); wallPlane(g, ...iso(0, d / 2 - .2, 6 + h * .5), 'y');
    for (let i = -7; i <= 7; i++) line(g, [[i * 12, -h * .42], [i * 12 + (i % 2) * 2, h * .38]], ['#d85a4a', '#e8b24e', '#6fb36e', '#6fa8b0', '#c98ad0'][((i % 5) + 5) % 5], 3);
    for (let k = -3; k <= 3; k++) line(g, [[-w * 18, k * 11], [w * 18, k * 11]], 'rgba(60,40,20,.4)', 1.6);
    g.restore();
    dome(g, w * .46, d * .46, 6 + h, 12, 3);
  }};

  // ---- the Seed Chapel: a round chapel, its walls curling up into root petals round an amber rosette
  City.art.seed_chapel = {box: [760, 820, 380, 680], draw(g, o) {
    const w = o.width || 5.4, d = o.depth || 5.4, h = 92, b = bark(3);
    shadow(g, w, d);
    prism(g, w + .5, d + .5, 8, '#6f5236', '#4f3a26', '#3b2b1c');
    prism(g, w, d, h, b[0], b[1], b[2], 8);
    grain(g, w, d, 8, 8 + h, 8);
    const c = iso(0, 0, 8 + h);
    for (let i = 0; i < 8; i++) {                                                      // curled petals of root rising from the rim
      const a = i * TAU / 8, px = Math.cos(a) * (w + d) * 12, py = Math.sin(a) * (w + d) * 6;
      poly(g, [[c[0] + px, c[1] + py], [c[0] + px * .5 - 8, c[1] + py * .5 - 60], [c[0] + px * .1, c[1] - 120], [c[0] + px * .5 + 8, c[1] + py * .5 - 62]], i % 2 ? '#9fbf78' : '#7fa860', '#3f5a3a', 2);
    }
    ellipse(g, c[0], c[1] - 118, 10, 7, '#f6e27a', null);
    g.save(); wallPlane(g, ...iso(0, d / 2 + .01, 8 + h * .55), 'y');
    ellipse(g, 0, 0, 30, 30, '#3a2714', null); ellipse(g, 0, 0, 24, 24, '#f0be62', null); ellipse(g, 0, 0, 12, 12, '#fff0b8', null);
    for (let k = 0; k < 8; k++) { const a = k * TAU / 8; line(g, [[Math.cos(a) * 12, Math.sin(a) * 12], [Math.cos(a) * 24, Math.sin(a) * 24]], '#5a3f26', 1.6); }
    g.restore();
    door(g, 0, d / 2 + .02, 8, 14, 36);
  }};

  // ---- the Seed Vault's door: a thick bark wall with an iris of bark petals set into its +y face, lit amber when it opens
  City.art.heartwood_vault = {box: [900, 760, 450, 640], draw(g, o) {
    const w = o.width || 8, d = o.depth || 2.2, h = 150;
    shadow(g, w, d);
    prism(g, w, d, h, '#a88256', '#866340', '#664a2f');
    grain(g, w, d, 0, h, 12);
    g.save(); wallPlane(g, ...iso(0, d / 2 + .01, h * .5), 'y');
    ellipse(g, 0, 0, 62, 70, '#3a2a18', null); ellipse(g, 0, 0, 54, 62, o.open ? '#241608' : '#78603e', null);
    if (o.open) { ellipse(g, 0, 0, 40, 48, '#f0be62', null); ellipse(g, 0, 2, 26, 34, '#fff0b8', null); }
    for (let i = 0; i < 8; i++) {
      const a = i * TAU / 8;
      g.save(); g.rotate(a); if (o.open) g.translate(0, -28);
      poly(g, [[-8, -52], [8, -52], [18, -8], [0, 14], [-18, -8]], i % 2 ? '#8cad6f' : '#6f9763', '#d7bf81', 1.6);
      g.restore();
    }
    g.restore();
    for (const s of [-1, 1]) for (let j = 0; j < 3; j++) { const p = iso(s * (w / 2 - .5), d / 2 + .02, 30 + j * 40); ellipse(g, p[0], p[1], 5, 8, '#f1cf7c', '#7c5c38'); }
  }, animate(g, o, sx, sy, t) {
    if (!o.open) return;
    g.save(); g.globalAlpha = .14 + .08 * Math.sin(t * 1.4); ellipse(g, sx, sy - 80, 52, 64, '#fff0a8', null); g.restore();
  }};

  // ---- the Hollow Arch: a thick wall of living bark with an arched way cut through its +y face, a lintel of root and hanging leaves (isometric; the portal stands in front of it)
  City.art.hollow_arch = {box: [760, 700, 380, 600], depthOffset: -2.5, draw(g, o) {
    const w = o.width || 6, d = o.depth || 2, h = 150, b = bark(0);
    shadow(g, w, d);
    prism(g, w + .4, d + .4, 8, '#6f5236', '#4f3a26', '#3b2b1c');
    prism(g, w, d, h, b[0], b[1], b[2], 8);
    grain(g, w, d, 8, 8 + h, 13);
    g.save(); wallPlane(g, ...iso(0, d / 2 + .01, 8), 'y');
    g.beginPath(); g.moveTo(-40, 0); g.lineTo(-40, -74); g.ellipse(0, -74, 40, 50, 0, Math.PI, 0); g.lineTo(40, 0); g.closePath(); g.fillStyle = '#241608'; g.fill();
    g.beginPath(); g.moveTo(-30, 0); g.lineTo(-30, -72); g.ellipse(0, -72, 30, 38, 0, Math.PI, 0); g.lineTo(30, 0); g.closePath(); g.fillStyle = '#e8b24e'; g.fill();
    g.beginPath(); g.moveTo(-18, 0); g.lineTo(-18, -70); g.ellipse(0, -70, 18, 24, 0, Math.PI, 0); g.lineTo(18, 0); g.closePath(); g.fillStyle = '#fff0b8'; g.fill();
    g.beginPath(); g.moveTo(-44, 0); g.lineTo(-44, -76); g.ellipse(0, -76, 44, 56, 0, Math.PI, 0); g.lineTo(44, 0); g.strokeStyle = '#7c5c38'; g.lineWidth = 5; g.stroke();
    g.restore();
    for (let j = -4; j <= 4; j++) { const p = iso(j * w / 9, d / 2 + .05, 8 + h - 6 - Math.abs(j) % 2 * 8); ellipse(g, p[0], p[1], 7, 4, j % 2 ? '#8fcf7e' : '#58a265', null); line(g, [iso(j * w / 9, d / 2 + .05, 8 + h), p], '#4f8f6a', 1.6); }
    for (const sx of [-1, 1]) { const p = iso(sx * (w / 2 - .4), d / 2 + .05, 8 + h * .55); ellipse(g, p[0], p[1], 6, 9, '#f6d77a', '#7c5c38'); }
  }};

  // ---- small furnishings: a root bench, a sap-lamp post
  City.art.heart_lamp = {box: [120, 220, 60, 190], draw(g, o) {
    prism(g, .3, .3, 70, '#a88256', '#866340', '#664a2f');
    const p = iso(0, 0, 82); ellipse(g, p[0], p[1], 12, 16, '#f6d77a', '#7c5c38'); ellipse(g, p[0] - 3, p[1] - 4, 4, 6, '#fff8cc', null);
  }};
})();
