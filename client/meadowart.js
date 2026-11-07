'use strict';
// Greenmeadow's own buildings (owner, 2026-11-07: the hamlet cottages and the mill were flat front-on pictures borrowed from Sunward Vale,
// the "roofless" Hollowend chapel was drawn as a whole timber house). Every building here is isometric like Fold Hall and Alderhaven, and its
// walls stand on the collision footprint (o.width x o.depth).
//   meadow_cottage  o.style picks the hamlet's way of building: stone (Stonefold: fieldstone, slate), fisher (Saltby: tarred planks,
//                   pantiles, nets), thatch (Applewick: limewash, timber, thatch). o.v (0-3) picks the variant: odd v turns the ridge so the
//                   gable faces the street, and v moves the door and changes roof and door colours.
//   meadow_mill     the watermill at the Three Meres: stone ground floor, boarded loft, wheel on its east wall.
//   chapel_ruin     Hollowend Chapel: roofless, the west gable still standing with an empty window, the other walls fallen low.
// Sunward Vale keeps vale_cottage and watermill (client/sunwardart.js).
(() => {
  const seed = (i, v) => { const s = Math.sin(i * 127.1 + v * 311.7) * 43758.5453; return s - Math.floor(s); };
  const trace = (g, pts) => { pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); };
  const shape = (g, outer, holes, fill, stroke, w = 2.5) => {
    g.beginPath(); trace(g, outer); for (const h of holes) trace(g, h);
    g.fillStyle = fill; g.fill('evenodd');
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = w; g.lineJoin = 'round'; g.stroke(); }
  };
  const clipTo = (g, pts, draw) => { g.save(); g.beginPath(); trace(g, pts); g.clip(); draw(); g.restore(); };
  const quad = (F, t0, t1, z0, z1) => [F(t0, z0), F(t1, z0), F(t1, z1), F(t0, z1)];

  const STYLE = {
    stone: { wall: ['#bdb6a5', '#a49d8c'], stones: ['#c9c2b0', '#b3ad9c', '#d3cbb7', '#a9a393'], mortar: '#857e70', plinth: ['#9a9486', '#8a8477', '#7a756a'],
      roof: ['#5d6873', '#6c6872', '#55676a', '#646f78'], roofLine: '#3a434c', course: 'slate', trim: '#efe6d2', door: ['#6d4a33', '#4f6b52', '#7a3b33', '#4d5d76'],
      h: 86, rise: 82, chimney: ['#b9b2a2', '#9d9686', '#88826f'] },
    fisher: { wall: [['#454a52', '#373b42'], ['#8e3b2e', '#76301f'], ['#5f7684', '#4f6370'], ['#454a52', '#373b42']], trim: '#f1ece0',
      roof: ['#b0573f', '#9c4c38', '#b8664a', '#a5523e'], roofLine: '#5e3328', course: 'pantile', door: ['#2f5a6e', '#e3dccb', '#2f5a6e', '#6e3a2c'],
      plinth: ['#a7a08f', '#8d8777', '#7c7668'], h: 80, rise: 72, chimney: ['#a65c48', '#8a4b3b', '#743f32'] },
    thatch: { wall: ['#f1e7cd', '#ddd2b6'], timber: '#6e4c35', trim: '#f6efdc', roof: ['#c9a25a', '#bd954f', '#d2ae67', '#c49a55'], roofLine: '#7a5a2e',
      course: 'thatch', door: ['#4d7a4a', '#3d5f86', '#9a3f35', '#6b5a8a'], shutter: ['#4d7a4a', '#3d5f86', '#9a3f35', '#6b5a8a'],
      plinth: ['#b9ad92', '#9c917a', '#877d69'], h: 78, rise: 98, chimney: ['#b5654c', '#984f3c', '#7f4232'] },
  };

  function windowAt(g, K, F, t, z0, z1, half, S, o, shutters) {
    K.poly(g, quad(F, t - half - .07, t + half + .07, z0 - 5, z1 + 5), S.trim, '#5a4a3c', 2);
    K.poly(g, quad(F, t - half, t + half, z0, z1), '#56798a', null);
    K.poly(g, quad(F, t - half, t - half * .1, z1 - 6, z1 - 14), 'rgba(220,240,240,.35)', null);
    K.line(g, [F(t, z0), F(t, z1)], S.trim, 2.5); K.line(g, [F(t - half, (z0 + z1) / 2), F(t + half, (z0 + z1) / 2)], S.trim, 2.5);
    if (shutters) for (const e of [-1, 1]) K.poly(g, quad(F, t + e * (half + .1), t + e * (half + .42), z0 - 3, z1 + 3), shutters, '#3f3428', 1.5);
  }
  function doorAt(g, K, F, t, S, o, arched) {
    const col = S.door[o.v % 4], top = 62;
    const outline = [F(t - .42, 0), F(t + .42, 0), F(t + .42, top - 8), F(t + .2, top), F(t - .2, top), F(t - .42, top - 8)];
    K.poly(g, arched ? outline : quad(F, t - .42, t + .42, 0, top), col, '#3a2e25', 3);
    K.line(g, [F(t - .48, top + 4), F(t + .48, top + 4)], arched ? '#8f897b' : '#5c4433', 6);
    for (const k of [-.2, .2]) K.line(g, [F(t + k, 6), F(t + k, top - 10)], 'rgba(0,0,0,.18)', 2);
    const [kx, ky] = F(t + .25, 30); K.ellipse(g, kx, ky, 3, 3, '#e6c36f');
  }

  // A cottage on a w x d footprint. ridgeX: the ridge runs along x and the gable is the right (+x) wall; otherwise the ridge runs along y
  // and the gable is the left (+y, street) wall, with the door under it.
  function cottage(g, o, K) {
    const S = STYLE[o.style] || STYLE.thatch, v = (o.v | 0) % 4, w = o.width || 5, d = o.depth || 4;
    const ridgeX = v % 2 === 0, h = S.h + (v === 2 ? 8 : 0), rise = S.rise + (v === 3 ? 10 : 0);
    const over = S.course === 'thatch' ? .5 : .35, rw = w + 2 * over, rd = d + 2 * over;
    const L = (t, z) => K.iso(t, d / 2, z), R = (t, z) => K.iso(w / 2, t, z);
    const wallCol = o.style === 'fisher' ? S.wall[v] : S.wall;
    K.ellipse(g, 14, 30, 160, 52, 'rgba(32,43,22,.26)');
    K.prism(g, w + .3, d + .3, 10, ...S.plinth);
    // Walls, with the gable triangle on the gable side.
    const apexL = h + rise * (w / 2) / (rw / 2), apexR = h + rise * (d / 2) / (rd / 2);
    const left = ridgeX ? quad(L, -w / 2, w / 2, 8, h) : [L(-w / 2, 8), L(w / 2, 8), L(w / 2, h), L(0, apexL), L(-w / 2, h)];
    const right = ridgeX ? [R(-d / 2, 8), R(d / 2, 8), R(d / 2, h), R(0, apexR), R(-d / 2, h)] : quad(R, -d / 2, d / 2, 8, h);
    for (const [pts, F, half, col] of [[left, L, w / 2, wallCol[0]], [right, R, d / 2, wallCol[1]]]) {
      K.poly(g, pts, col, null);
      clipTo(g, pts, () => {
        if (S.course === 'slate') {          // fieldstone: staggered rounded stones in mortar
          for (let row = 0, z = 10; z < 240; row++, z += 13) for (let t = -half - (row % 2) * .3; t < half; t += .62) {
            const k = row * 31 + Math.round((t + 9) * 10), c = S.stones[Math.floor(seed(k, v + 1) * 4)];
            K.poly(g, quad(F, t + .04, t + .58, z + 1, z + 12), c, S.mortar, 1.2);
          }
          K.poly(g, pts, F === L ? 'rgba(0,0,0,0)' : 'rgba(40,40,60,.12)', null);
        } else if (S.course === 'pantile') {   // tarred weatherboards with a light edge on each board
          for (let z = 10; z < 240; z += 9) { K.line(g, [F(-half, z), F(half, z)], 'rgba(0,0,0,.35)', 1.6); K.line(g, [F(-half, z + 2), F(half, z + 2)], 'rgba(255,255,255,.08)', 1); }
          if (F === R) K.poly(g, pts, 'rgba(20,20,40,.12)', null);
        } else {                               // limewash between dark timbers
          for (const z of [10, h * .52, h]) K.line(g, [F(-half, z), F(half, z)], S.timber, 6);
          for (let t = -half; t <= half + .01; t += half / 2) K.line(g, [F(t, 10), F(t, h)], S.timber, 6);
          if (F === R) K.poly(g, pts, 'rgba(60,40,20,.10)', null);
        }
      });
      K.poly(g, pts, 'rgba(0,0,0,0)', '#4a3c32', 2.5);
    }
    if (o.style === 'fisher') for (const [F, half] of [[L, w / 2], [R, d / 2]]) for (const t of [-half, half]) K.line(g, [F(t, 9), F(t, h)], S.trim, 4);   // white corner boards
    // Door and windows: the door on the street wall, windows on both walls where the door is not.
    const doorT = ridgeX ? [-.9, 0, 1.0, 0][v] : [0, -.2, 0, .3][v];
    doorAt(g, K, L, doorT, S, o, o.style === 'stone');
    const shut = S.shutter ? S.shutter[(v + 1) % 4] : null, wz0 = o.style === 'thatch' ? 30 : 32, wz1 = wz0 + 32;
    for (const t of [-w / 2 + .85, w / 2 - .85]) if (Math.abs(t - doorT) > 1.25) windowAt(g, K, L, t, wz0, wz1, .34, S, o, shut);
    for (const t of (d > 3.4 ? [-.85, .85] : [0])) windowAt(g, K, R, t, wz0, wz1, .32, S, o, shut);
    if (!ridgeX) windowAt(g, K, L, 0, h + 16, h + 40, .26, S, o, null);   // loft window in the street gable
    else windowAt(g, K, R, 0, h + 14, h + 36, .24, S, o, null);
    // Step in front of the door.
    g.save(); g.translate(...K.iso(doorT, d / 2 + .28)); K.prism(g, 1.05, .5, 7, ...S.plinth); g.restore();
    // Roof: P(u, s) is the visible plane (u along the ridge 0..1, s from eave 0 to ridge 1), Q the hidden one.
    const P = ridgeX ? (u, s) => K.iso(-rw / 2 + u * rw, rd / 2 * (1 - s), h + rise * s) : (u, s) => K.iso(rw / 2 * (1 - s), -rd / 2 + u * rd, h + rise * s);
    const Q = ridgeX ? (u, s) => K.iso(-rw / 2 + u * rw, -rd / 2 * (1 - s), h + rise * s) : (u, s) => K.iso(-rw / 2 * (1 - s), -rd / 2 + u * rd, h + rise * s);
    const roof = S.roof[v], hidden = [Q(0, 0), Q(1, 0), Q(1, 1), Q(0, 1)], plane = [P(0, 0), P(1, 0), P(1, 1), P(0, 1)];
    K.poly(g, hidden, roof, S.roofLine, 2.5);
    K.poly(g, plane, roof, S.roofLine, 3);
    clipTo(g, plane, () => {
      if (S.course === 'slate') {
        for (let r = 1; r < 9; r++) { const s = r / 9; K.line(g, [P(0, s), P(1, s)], 'rgba(20,28,36,.55)', 1.6);
          for (let c = 0; c < 14; c++) { const u = (c + (r % 2) * .5) / 14; K.line(g, [P(u, s - 1 / 9), P(u, s)], 'rgba(20,28,36,.35)', 1); } }
        for (let i = 0; i < 18; i++) { const u = seed(i, v + 7), s = seed(i + 40, v + 3) * .9; const [x, y] = P(u, s); K.ellipse(g, x, y, 5, 2.2, 'rgba(255,255,255,.08)'); }
      } else if (S.course === 'pantile') {
        for (let c = 0; c <= 16; c++) { const u = c / 16; K.line(g, [P(u, 0), P(u, 1)], 'rgba(255,210,170,.32)', 3); K.line(g, [P(u + .018, 0), P(u + .018, 1)], 'rgba(60,20,10,.35)', 1.5); }
        for (let r = 1; r < 7; r++) K.line(g, [P(0, r / 7), P(1, r / 7)], 'rgba(60,20,10,.28)', 1.2);
      } else {
        for (let i = 0; i < 140; i++) { const u = seed(i, v + 2), s = seed(i + 300, v + 5); K.line(g, [P(u, s), P(u + .004, Math.max(0, s - .12))], i % 3 ? 'rgba(120,85,35,.45)' : 'rgba(250,225,150,.45)', 1.5); }
        for (let r = 1; r < 4; r++) K.line(g, [P(0, r / 4), P(1, r / 4)], 'rgba(110,80,35,.35)', 2);
      }
    });
    if (S.course === 'thatch') {             // a rounded eave lip and a patterned ridge roll
      K.line(g, [P(0, .02), P(1, .02)], '#9b7a40', 9); K.line(g, [P(0, .05), P(1, .05)], '#d9b96f', 3);
      K.line(g, [Q(1, 0), P(1, 1), P(1, 0)], '#8a6a3a', 9); K.line(g, [Q(1, .03), P(1, .97), P(1, .03)], '#d2b36c', 2.5);   // the thick cut edge of the thatch over the gable
      K.line(g, [P(0, .93), P(1, .93)], '#a88446', 10);
      for (let i = 0; i < 12; i++) K.line(g, [P(i / 12, .88), P((i + .5) / 12, .97), P((i + 1) / 12, .88)], '#7a5a2e', 2);
    } else {
      K.line(g, [P(0, 1), P(1, 1)], o.style === 'fisher' ? '#8a4030' : '#475260', 6);
      K.line(g, [P(1, 0), P(1, 1)], S.roofLine, 4); K.line(g, [P(0, 0), P(0, 1)], S.roofLine, 3);
    }
    // Chimney on the ridge near the far end.
    const [cx, cy] = ridgeX ? [-rw / 2 + .3 * rw, -.15] : [-.15, -rd / 2 + .28 * rd];
    g.save(); g.translate(...K.iso(cx, cy, h + rise - 14)); K.prism(g, .55, .55, 48, ...S.chimney);
    K.prism(g, .7, .7, 7, ...S.chimney, 48); g.restore();
    // Each hamlet's yard things.
    if (o.style === 'fisher') {
      const net = quad(R, -d / 2 + .3, -d / 2 + 1.6, 18, 64);
      K.poly(g, net, 'rgba(110,140,120,.30)', null);
      for (let i = 0; i <= 8; i++) { const a = i / 8; K.line(g, [R(-d / 2 + .3 + a * 1.3, 64), R(-d / 2 + .3 + Math.min(1.3, a * 1.3 + .4), 18)], 'rgba(230,225,200,.7)', 1);
        K.line(g, [R(-d / 2 + .3 + a * 1.3, 64), R(-d / 2 + .3 + Math.max(0, a * 1.3 - .4), 18)], 'rgba(230,225,200,.7)', 1); }
      for (const k of [0, 1]) { const [x, y] = R(-d / 2 + .3 + k * 1.3, 64); K.ellipse(g, x, y, 3, 3, '#d9d1b8'); }
      for (const t of [w / 2 - .6, w / 2 - .4]) K.line(g, [K.iso(t, d / 2 + .25, 0), L(t - .25, 74)], '#b08a5a', 4);   // oars against the street wall
      const [ox, oy] = K.iso(w / 2 - .5, d / 2 + .3, 74); K.poly(g, [[ox - 3, oy], [ox + 3, oy], [ox + 6, oy - 14], [ox - 6, oy - 14]], '#b08a5a', '#6a5038', 1);
      g.save(); g.translate(...K.iso(w / 2 + .5, d / 2 - .6)); K.prism(g, .6, .45, 18, '#c8a36a', '#9c7b4c', '#7c6240');
      for (let i = 0; i < 4; i++) K.line(g, [K.iso(-.3 + i * .2, .23, 1), K.iso(-.3 + i * .2, .23, 17)], '#5b4630', 1.5); g.restore();
    } else if (o.style === 'stone') {
      g.save(); g.translate(...K.iso(w / 2 + .45, d / 2 - .9));   // a woodpile against the side wall
      K.prism(g, .5, 1.4, 6, '#7c6a52', '#5f5040', '#4e4234');
      for (let r = 0; r < 4; r++) for (let i = 0; i < 6 - r; i++) { const [x, y] = K.iso(.25, -.55 + (i + r * .5) * .22, 10 + r * 9); K.ellipse(g, x, y, 5, 5, '#c79a63', '#6c4e33'); }
      g.restore();
      for (const t of [-w / 2 + .85, w / 2 - .85]) if (Math.abs(t - doorT) > 1.25) { K.poly(g, quad(L, t - .42, t + .42, wz0 - 12, wz0 - 4), '#7a5a3e', '#4a3c32', 1.5);
        for (let i = 0; i < 5; i++) { const [x, y] = L(t - .34 + i * .17, wz0 - 6); K.ellipse(g, x, y - 4, 4, 3, ['#e9b5c2', '#f2d36c', '#c9d6f0'][i % 3]); } }
    } else {
      for (let i = 0; i < 22; i++) {           // a rose climbing the street wall beside the door
        const t = doorT + (doorT > 0 ? -.75 : .75) + (seed(i, v) - .5) * .45, z = 10 + seed(i + 50, v) * 70, [x, y] = L(t, z);
        K.ellipse(g, x, y, 6, 5, i % 2 ? '#5f8a3e' : '#6f9b48'); if (i % 3 === 0) K.ellipse(g, x + 1, y - 2, 3, 3, '#e07a8c');
      }
      g.save(); g.translate(...K.iso(doorT + (doorT > 0 ? .95 : -.95), d / 2 + .45)); K.prism(g, .55, .4, 14, '#c49a5a', '#9e7a44', '#7f6236');
      for (let i = 0; i < 5; i++) { const [x, y] = K.iso(-.18 + i * .09, 0, 18); K.ellipse(g, x, y, 4, 4, i % 2 ? '#c9473a' : '#d9b748'); } g.restore();
    }
  }

  // The watermill: stone ground floor, boarded loft, wheel on the east (+x) wall over a short race.
  function mill(g, o, K) {
    const w = o.width || 6, d = o.depth || 4, h1 = 62, h = 132, rise = 86, rw = w + .7, rd = d + .8;
    const L = (t, z) => K.iso(t, d / 2, z), R = (t, z) => K.iso(w / 2, t, z);
    K.ellipse(g, 16, 30, 185, 58, 'rgba(28,43,21,.24)');
    K.prism(g, w + .3, d + .3, 10, '#9a9486', '#8a8477', '#7a756a');
    const apex = h + rise * (d / 2) / (rd / 2);
    const left = quad(L, -w / 2, w / 2, 8, h), right = [R(-d / 2, 8), R(d / 2, 8), R(d / 2, h), R(0, apex), R(-d / 2, h)];
    for (const [pts, F, half, stone, board] of [[left, L, w / 2, '#bdb6a5', '#d9c7a2'], [right, R, d / 2, '#a8a190', '#c2b08c']]) {
      K.poly(g, pts, board, null);
      clipTo(g, pts, () => {
        K.poly(g, quad(F, -half, half, 8, h1), stone, null);
        for (let row = 0, z = 10; z < h1; row++, z += 13) for (let t = -half - (row % 2) * .3; t < half; t += .62)
          K.poly(g, quad(F, t + .04, t + .58, z + 1, z + 12), ['#c9c2b0', '#b3ad9c', '#d3cbb7', '#a9a393'][Math.floor(seed(row * 17 + Math.round((t + 9) * 10), 3) * 4)], '#857e70', 1.2);
        for (let z = h1 + 4; z < 260; z += 10) K.line(g, [F(-half, z), F(half, z)], 'rgba(90,60,30,.35)', 1.5);
        K.line(g, [F(-half, h1 + 2), F(half, h1 + 2)], '#6e4c35', 6);
        if (F === R) K.poly(g, pts, 'rgba(40,40,60,.12)', null);
      });
      K.poly(g, pts, 'rgba(0,0,0,0)', '#4a3c32', 2.5);
    }
    doorAt(g, K, L, -1.2, { door: ['#6d4a33'], trim: '#efe6d2' }, { v: 0 }, true);
    for (const t of [.6, 2.0]) windowAt(g, K, L, t, 26, 50, .3, { trim: '#efe6d2' }, o, null);
    for (const t of [-1.6, 0, 1.6]) windowAt(g, K, L, t, 86, 112, .3, { trim: '#efe6d2' }, o, null);
    windowAt(g, K, R, 0, h + 12, h + 34, .24, { trim: '#efe6d2' }, o, null);
    // Loft door with a hoist beam over the street wall.
    K.poly(g, quad(L, .8, 1.5, 76, 120), '#6d4a33', '#3a2e25', 2);
    K.line(g, [L(1.15, 128), K.iso(1.15, d / 2 + .9, 128)], '#5c4433', 6); K.line(g, [K.iso(1.15, d / 2 + .85, 126), K.iso(1.15, d / 2 + .85, 92)], '#d9c79a', 1.5);
    // Roof (ridge along x), red tiles.
    const P = (u, s) => K.iso(-rw / 2 + u * rw, rd / 2 * (1 - s), h + rise * s), Q = (u, s) => K.iso(-rw / 2 + u * rw, -rd / 2 * (1 - s), h + rise * s);
    K.poly(g, [Q(0, 0), Q(1, 0), Q(1, 1), Q(0, 1)], '#a66342', '#5e3328', 2.5);
    const plane = [P(0, 0), P(1, 0), P(1, 1), P(0, 1)]; K.poly(g, plane, '#a66342', '#5e3328', 3);
    clipTo(g, plane, () => { for (let c = 0; c <= 20; c++) { const u = c / 20; K.line(g, [P(u, 0), P(u, 1)], 'rgba(255,210,170,.30)', 3); }
      for (let r = 1; r < 8; r++) K.line(g, [P(0, r / 8), P(1, r / 8)], 'rgba(60,20,10,.3)', 1.2); });
    K.line(g, [P(0, 1), P(1, 1)], '#7e3a2a', 6); K.line(g, [P(1, 0), P(1, 1)], '#5e3328', 4);
    // The race and the wheel: W(x, a, r) is a point of the wheel in the plane x = w/2 + x.
    const W = (x, a, r) => K.iso(w / 2 + x, Math.cos(a) * r, 56 + Math.sin(a) * r * 49);
    K.poly(g, [K.iso(w / 2 + .05, -d / 2 - .4, 0), K.iso(w / 2 + 1.05, -d / 2 - .4, 0), K.iso(w / 2 + 1.05, d / 2 + .6, 0), K.iso(w / 2 + .05, d / 2 + .6, 0)], '#5f9fb8', '#6b5a44', 3);
    K.line(g, [K.iso(w / 2 + .55, -d / 2 - .3, 1), K.iso(w / 2 + .55, d / 2 + .5, 1)], 'rgba(235,250,255,.6)', 2);
    const ring = (x, r) => Array.from({ length: 33 }, (_, i) => W(x, i / 32 * Math.PI * 2, r));
    K.line(g, ring(.25, 1.32), '#4c3a26', 7);
    for (let i = 0; i < 16; i++) { const a = i / 16 * Math.PI * 2; K.poly(g, [W(.25, a, 1.36), W(.75, a, 1.36), W(.75, a, .98), W(.25, a, .98)], '#8a6a44', '#4c3a26', 1.5); }
    for (let i = 0; i < 8; i++) { const a = i / 8 * Math.PI * 2; K.line(g, [W(.75, a, .16), W(.75, a, 1.3)], '#6b5237', 6); }
    K.line(g, ring(.75, 1.32), '#5f4a30', 8); K.line(g, ring(.75, .98), '#5f4a30', 5);
    const [hx, hy] = W(.8, 0, 0); K.ellipse(g, hx, hy, 9, 9, '#3f3020', '#2a2016');
    K.line(g, [W(.5, Math.PI * .5, 1.45), K.iso(w / 2 + .5, 0, 135), K.iso(w / 2 - .1, 0, 135)], '#6b5237', 7);   // the chute over the wheel top
    for (const k of [-.3, 0, .3]) { const [x, y] = K.iso(w / 2 + .55 + k * .3, .4 + k, 3); K.ellipse(g, x, y, 10, 4, 'rgba(240,252,255,.75)'); }
    // A spare millstone leaning by the door.
    const [mx, my] = K.iso(-w / 2 + .1, d / 2 + .5, 22); K.ellipse(g, mx, my, 16, 22, '#b3ad9c', '#6c675c'); K.ellipse(g, mx, my, 4, 5, '#6c675c');
  }

  // Hollowend Chapel, roofless: the inner faces of the west gable (x = -w/2) and the north wall (y = -d/2) show, the street-side walls are low.
  function ruin(g, o, K) {
    const w = o.width || 6, d = o.depth || 5, T = .38;
    const B = (t, z) => K.iso(-w / 2, t, z), N = (t, z) => K.iso(t, -d / 2, z), L = (t, z) => K.iso(t, d / 2, z), R = (t, z) => K.iso(w / 2, t, z);
    const stone = (F, pts, half, base, k, holes = []) => {
      g.save(); g.beginPath(); trace(g, pts); for (const h of holes) trace(g, h); g.clip('evenodd');
      {
        for (let row = 0, z = 4; z < 260; row++, z += 14) for (let t = -half - (row % 2) * .32; t < half; t += .64)
          K.poly(g, quad(F, t + .04, t + .6, z + 1, z + 13), ['#b9b29f', '#a8a190', '#c4bca8', '#9d9686'][Math.floor(seed(row * 29 + Math.round((t + 9) * 10), k) * 4)], '#7a7466', 1.2);
        K.poly(g, pts, base, null);
      }
      g.restore();
      K.poly(g, pts, 'rgba(0,0,0,0)', '#4f483d', 2.5);
    };
    const ivy = (F, t0, t1, z0, z1, k) => { for (let i = 0; i < 26; i++) { const [x, y] = F(t0 + seed(i, k) * (t1 - t0), z0 + seed(i + 70, k) * (z1 - z0)); K.ellipse(g, x, y, 6, 5, i % 3 ? '#4f7a36' : '#64903f'); } };
    // Wall caps: profile [[t, z], ...] along a face F whose thickness goes in direction off (tiles, in the face's normal axis).
    const cap = (F, G, prof) => { for (let i = 0; i + 1 < prof.length; i++) { const [t0, z0] = prof[i], [t1, z1] = prof[i + 1]; K.poly(g, [F(t0, z0), F(t1, z1), G(t1, z1), G(t0, z0)], '#d8d0bc', '#6d665a', 1.5); } };
    K.ellipse(g, 10, 26, 175, 60, 'rgba(24,40,22,.28)');
    // Grass and broken flagstones on the old floor.
    K.poly(g, [K.iso(-w / 2, -d / 2), K.iso(w / 2, -d / 2), K.iso(w / 2, d / 2), K.iso(-w / 2, d / 2)], '#6f8f4f', null);
    for (let i = 0; i < 26; i++) { const x = -w / 2 + .4 + seed(i, 3) * (w - .8), y = -d / 2 + .4 + seed(i + 9, 4) * (d - .8);
      K.poly(g, [K.iso(x - .3, y - .25), K.iso(x + .3, y - .25), K.iso(x + .3, y + .25), K.iso(x - .3, y + .25)], seed(i, 8) > .4 ? '#a7a291' : '#93907f', '#6f6c5f', 1); }
    // North wall, inner face, falling away to the east with two empty windows.
    const nProf = [[-w / 2, 150], [-1.6, 132], [-1.1, 138], [-.4, 104], [.4, 96], [1.2, 70], [1.9, 76], [2.4, 44], [w / 2, 38]];
    const north = [N(-w / 2, 0), N(w / 2, 0), ...nProf.slice().reverse().map(([t, z]) => N(t, z))];
    const arch = (F, t, z0, z1, half) => [F(t - half, z0), F(t + half, z0), F(t + half, z1), F(t + half * .55, z1 + 18), F(t, z1 + 26), F(t - half * .55, z1 + 18), F(t - half, z1)];
    const nHoles = [arch(N, -1.3, 44, 98, .32), arch(N, .2, 40, 74, .3)];
    shape(g, north, nHoles, '#b5ae9b', null); stone(N, north, w / 2, 'rgba(70,60,40,.12)', 5, nHoles);
    for (const hole of nHoles) K.poly(g, hole, 'rgba(0,0,0,0)', '#4f483d', 3);
    cap(N, (t, z) => K.iso(t, -d / 2 - T, z), nProf);
    // West gable, inner face: still standing to its point, with the tall empty window and a bell-cote.
    const gProf = [[-d / 2, 150], [-1.4, 178], [-.6, 214], [-.1, 236], [.3, 228], [.9, 196], [1.5, 168], [d / 2, 142]];
    const gable = [B(-d / 2, 0), B(d / 2, 0), ...gProf.slice().reverse().map(([t, z]) => B(t, z))];
    const gHole = [B(-.45, 70), B(.45, 70), B(.45, 150), B(.28, 172), B(0, 186), B(-.28, 172), B(-.45, 150)];
    shape(g, gable, [gHole], '#b5ae9b', null); stone(B, gable, d / 2, 'rgba(255,255,255,.04)', 6, [gHole]);
    K.poly(g, gHole, 'rgba(0,0,0,0)', '#4f483d', 3);
    K.line(g, [B(-.45, 150), B(.45, 150)], '#cfc7b2', 3); K.line(g, [B(0, 70), B(0, 150)], '#cfc7b2', 3);  // the stone mullion
    cap(B, (t, z) => K.iso(-w / 2 - T, t, z), gProf);
    g.save(); g.translate(...B(-.05, 230)); K.prism(g, .45, .7, 34, '#d8d0bc', '#b5ae9b', '#9d9686'); g.restore();
    ivy(B, 1.2, d / 2, 10, 150, 9); ivy(N, -w / 2 + .2, -1.6, 20, 120, 10);
    // Rubble and the old altar stone.
    g.save(); g.translate(...K.iso(-w / 2 + 1.2, 0)); K.prism(g, .8, 1.5, 22, '#cfc7b2', '#aaa390', '#948d7c'); g.restore();
    for (let i = 0; i < 14; i++) { const x = -w / 2 + .8 + seed(i, 11) * (w - 1.4), y = -d / 2 + .6 + seed(i + 5, 12) * (d - 1.2);
      g.save(); g.translate(...K.iso(x, y)); K.prism(g, .3 + seed(i, 13) * .25, .25 + seed(i, 14) * .2, 8 + seed(i, 15) * 10, '#c4bca8', '#a39c8a', '#8c8576'); g.restore(); }
    // Street walls: low and broken, with the doorway gap on the south side.
    const sW = [[-w / 2, 64], [-2.4, 70], [-1.9, 52], [-1.2, 58], [-.75, 40]], sE = [[.75, 34], [1.3, 48], [1.9, 30], [2.5, 44], [w / 2, 88]];
    for (const prof of [sW, sE]) { const pts = [L(prof[0][0], 0), L(prof[prof.length - 1][0], 0), ...prof.slice().reverse().map(([t, z]) => L(t, z))];
      K.poly(g, pts, '#bdb6a3', null); stone(L, pts, w / 2, 'rgba(0,0,0,0)', 7); cap(L, (t, z) => K.iso(t, d / 2 - T, z), prof); }
    const eProf = [[-d / 2, 88], [-1.7, 110], [-1.2, 104], [-.6, 52], [.4, 40], [1.2, 56], [d / 2, 70]];
    const east = [R(-d / 2, 0), R(d / 2, 0), ...eProf.slice().reverse().map(([t, z]) => R(t, z))];
    K.poly(g, east, '#a8a190', null); stone(R, east, d / 2, 'rgba(40,40,60,.12)', 8); cap(R, (t, z) => K.iso(w / 2 - T, t, z), eProf);
    ivy(L, 1.1, w / 2, 4, 40, 13); ivy(R, .5, d / 2, 4, 50, 14);
    // Fallen blocks outside the doorway.
    for (const [x, y] of [[.2, d / 2 + .7], [-.6, d / 2 + 1.1], [w / 2 + .6, .6]]) { g.save(); g.translate(...K.iso(x, y)); K.prism(g, .55, .4, 14, '#c4bca8', '#a39c8a', '#8c8576'); g.restore(); }
    if (o.label) K.text(g, o.label, 0, -330, 17);
  }

  City.art.meadow_cottage = { box: [520, 470, 260, 335], draw: cottage };
  City.art.meadow_mill = { box: [600, 480, 280, 330], draw: mill };
  City.art.chapel_ruin = { box: [580, 540, 290, 380], draw: ruin };
})();
