'use strict';
// Boss mechanics on the screen (BOSSMECH-CLIENT). The server owns every rule and sends `bossMech` with each snapshot: one entry per
// running fight with its telegraphs (shape, colour, time left), the cast, the break bar, the shield, marked and frozen players and a
// banner (docs/boss-mechanics.md, "The engine"). This module only draws what it is told:
//   - the floor pass: red = hurts, blue = stand here, a dashed pale-gold line = a path about to be used, green = the gap in a wall;
//   - the screen pass: the boss's cast bar with its countdown, a one-line banner, the shield and break counters, a "Stunned" tag;
//   - the death cause on the defeat screen.
// Shapes are projected as polygons, so one routine draws a circle, ring, cone, lane, half-arena or room whatever the camera does.
// No filters, no blur, no per-frame allocation beyond the points of a shape; reduced motion switches the pulsing and the dash
// crawl off (the shapes, the colours and the countdown stay).
(() => {
  const RED = '#e0453b', BLUE = '#3f9bea', GOLD = '#f1e3b4', GREEN = '#4fc26b', AMBER = '#ffb028';
  const text = s => (window.Locale ? window.Locale.translate(s) : s);
  const fill = (s, a, b) => s.replace('{0}', a).replace('{1}', b);
  const reduced = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const now = () => performance.now() / 1000;
  let fights = [], stamp = 0, cause = '';

  const update = list => { fights = Array.isArray(list) ? list : []; stamp = now(); };
  const reset = () => { fights = []; setCause(''); };
  const left = tele => Math.max(0, (tele.left || 0) - (now() - stamp));

  // ---- shapes --------------------------------------------------------------------------------------------------------------
  const arc = (x, y, r, n = 40) => { const out = []; for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2; out.push([x + Math.cos(a) * r, y + Math.sin(a) * r]); } return out; };
  // A half-plane (the dangerous side is where (p - xy) . n > 0) cut to a box, one Sutherland-Hodgman pass.
  function halfPolygon(s, box) {
    const [x0, y0, x1, y1] = box, side = p => (p[0] - s.x) * s.nx + (p[1] - s.y) * s.ny;
    const ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], out = [];
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i], b = ring[(i + 1) % ring.length], da = side(a), db = side(b);
      if (da > 0) out.push(a);
      if ((da > 0) !== (db > 0)) { const k = da / (da - db); out.push([a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]); }
    }
    return out;
  }
  // The polygons of a shape in world units (a ring is two: the outer one and the hole, filled with the even-odd rule).
  function polygons(s, roomAt) {
    switch (s.t) {
      case 'circle': return s.inner > 0 ? [arc(s.x, s.y, s.r), arc(s.x, s.y, s.inner)] : [arc(s.x, s.y, s.r)];
      case 'cone': {
        const pts = [[s.x, s.y]];
        for (let i = 0; i <= 18; i++) { const a = s.dir - s.half + i / 18 * s.half * 2; pts.push([s.x + Math.cos(a) * s.length, s.y + Math.sin(a) * s.length]); }
        return [pts];
      }
      case 'lane': {
        const dx = s.x2 - s.x1, dy = s.y2 - s.y1, len = Math.hypot(dx, dy) || 1, ox = -dy / len * s.half, oy = dx / len * s.half;
        return [[[s.x1 + ox, s.y1 + oy], [s.x2 + ox, s.y2 + oy], [s.x2 - ox, s.y2 - oy], [s.x1 - ox, s.y1 - oy]]];
      }
      case 'half': return [halfPolygon(s, roomAt?.(s.x, s.y) || [s.x - 16, s.y - 16, s.x + 16, s.y + 16])];
      case 'rect': return [[[s.x0, s.y0], [s.x1, s.y0], [s.x1, s.y1], [s.x0, s.y1]]];
      default: return [];
    }
  }
  function path(g, polys, w2s) {
    g.beginPath();
    for (const poly of polys) {
      if (poly.length < 3) continue;
      poly.forEach((p, i) => { const [sx, sy] = w2s(p[0], p[1]); if (i) g.lineTo(sx, sy); else g.moveTo(sx, sy); });
      g.closePath();
    }
  }
  const centre = s => s.t === 'lane' ? [(s.x1 + s.x2) / 2, (s.y1 + s.y2) / 2] : s.t === 'rect' ? [(s.x0 + s.x1) / 2, (s.y0 + s.y1) / 2] : [s.x, s.y];

  // ---- the floor pass ------------------------------------------------------------------------------------------------------
  // opts: w2s, roomAt(x, y) -> [x0, y0, x1, y1] | null, pos(characterId) -> {x, y} | null
  function drawFloor(g, t, opts) {
    if (!fights.length) return;
    const { w2s, roomAt, pos } = opts, calm = reduced();
    g.save();
    for (const f of fights) {
      for (const tele of f.tele || []) drawTele(g, tele, t, w2s, roomAt, calm);
      for (const id of f.marked || []) { const p = pos(id); if (p) ring(g, w2s, p.x, p.y, 1.1, RED, t, calm); }
      for (const id of f.frozen || []) { const p = pos(id); if (p) ring(g, w2s, p.x, p.y, 1.2, AMBER, t, calm); }
      const st = f.static;                      // Static: a hero near the limit shows the circle their blast would fill
      if (st) for (const [id, n] of Object.entries(st.charges || {})) { const p = n >= st.warnAt ? pos(id) : null; if (p) ring(g, w2s, p.x, p.y, st.radius || 5, RED, t, calm); }
    }
    g.restore();
  }
  function ring(g, w2s, x, y, r, colour, t, calm) {
    const pulse = calm ? 1 : .75 + .25 * Math.sin(t * 8);
    path(g, [arc(x, y, r, 24)], w2s);
    g.globalAlpha = .85 * pulse; g.lineWidth = 3; g.strokeStyle = colour; g.setLineDash([]); g.stroke();
    g.globalAlpha = .2 * pulse; g.fillStyle = colour; g.fill();
  }
  function drawTele(g, tele, t, w2s, roomAt, calm) {
    const live = left(tele), total = tele.total || 0, p = total > 0 ? Math.min(1, Math.max(0, 1 - live / total)) : 1;
    const polys = (tele.shapes || []).flatMap(s => polygons(s, roomAt));
    if (!polys.length) return;
    g.setLineDash([]); g.lineDashOffset = 0;
    if (tele.tele === 'cover') {                       // a pillar that shelters from a gaze: it cracks, then breaks
      path(g, polys, w2s);
      g.globalAlpha = tele.standing ? .9 : .35; g.lineWidth = 3; g.strokeStyle = tele.standing ? (tele.hits ? '#d9c28a' : '#9fc3e0') : '#6c7480';
      if (!tele.standing) g.setLineDash([6, 6]);
      g.stroke(); g.setLineDash([]);
      if (tele.standing && tele.shapes[0]?.t === 'circle') {
        const s = tele.shapes[0], [bx, by] = w2s(s.x, s.y), [tx, ty] = w2s(s.x, s.y, 52);
        g.globalAlpha = .9; g.lineWidth = 8; g.strokeStyle = tele.hits ? '#a9896b' : '#688b9b';
        g.beginPath(); g.moveTo(bx, by); g.lineTo(tx, ty); g.stroke();
        g.lineWidth = 2; g.strokeStyle = tele.hits ? '#f0d191' : '#b6e7e3';
        g.beginPath(); g.ellipse(tx, ty, 8, 13, 0, 0, Math.PI * 2); g.stroke();
        if (tele.hits) { g.beginPath(); g.moveTo(tx - 4, ty - 9); g.lineTo(tx + 3, ty); g.lineTo(tx - 2, ty + 10); g.stroke(); }
      }
      return;
    }
    const colour = tele.color || (tele.tele === 'blue' ? BLUE : tele.tele === 'green gap' ? GREEN : tele.tele === 'dashed line' ? GOLD : RED);
    const echo = !!tele.echo, danger = tele.tele === 'red';
    // A cast fills in as it runs: the body gets denser, and a circle also grows from its centre to its edge.
    const body = echo ? .1 : danger ? (total > 0 ? .13 + .3 * p : .5) : tele.tele === 'blue' ? (tele.lit ? .34 : .2) : tele.tele === 'green gap' ? .38 : .1;
    path(g, polys, w2s);
    g.globalAlpha = body; g.fillStyle = colour; g.fill('evenodd');
    if (danger && !echo && total > 0 && p < 1) {
      const grown = (tele.shapes || []).filter(s => s.t === 'circle').flatMap(s => polygons({ ...s, r: s.inner + (s.r - s.inner) * p }, null));
      if (grown.length) { path(g, grown, w2s); g.globalAlpha = .2 + .15 * p; g.fill('evenodd'); }
    }
    path(g, polys, w2s);
    const urgent = danger && !echo && total > 0 && live < 1 && !calm ? .5 + .5 * Math.sin(t * 24) : 1;
    g.globalAlpha = (echo ? .45 : .9) * urgent; g.lineWidth = tele.tele === 'dashed line' ? 3 : 2.5; g.strokeStyle = colour;
    if (tele.dashed || echo) { g.setLineDash([12, 8]); g.lineDashOffset = calm ? 0 : -t * 30; }
    g.stroke(); g.setLineDash([]); g.lineDashOffset = 0;
    if (tele.reversing && tele.reverseLeft > 0) {
      const lane = tele.shapes[0], hub = lane?.t === 'lane' ? { x: lane.x1, y: lane.y1 } : null;
      if (hub) {
        const [sx, sy] = w2s(hub.x, hub.y, 40);
        g.save(); g.globalAlpha = 1; g.strokeStyle = GOLD; g.lineWidth = 3;
        g.beginPath(); g.arc(sx, sy, 13, 0, Math.PI * 2); g.stroke();
        for (let n = 0; n < 8; n++) {
          const a = n * Math.PI / 4;
          g.beginPath(); g.moveTo(sx + 16 * Math.cos(a), sy + 16 * Math.sin(a));
          g.lineTo(sx + 23 * Math.cos(a), sy + 23 * Math.sin(a)); g.stroke();
        }
        g.restore();
      }
    }
    if (tele.tele === 'blue' && tele.progress > 0 && !tele.lit) {   // a brazier being lit: a bright arc round it
      const s = tele.shapes[0], n = Math.max(2, Math.round(40 * tele.progress)), pts = [];
      for (let i = 0; i <= n; i++) { const a = -Math.PI / 2 + i / 40 * Math.PI * 2; pts.push([s.x + Math.cos(a) * s.r, s.y + Math.sin(a) * s.r]); }
      g.beginPath(); pts.forEach((q, i) => { const [sx, sy] = w2s(q[0], q[1]); if (i) g.lineTo(sx, sy); else g.moveTo(sx, sy); });
      g.globalAlpha = 1; g.lineWidth = 5; g.strokeStyle = '#bfe4ff'; g.stroke();
    }
    if (tele.role && !tele.chain && tele.shapes[0]?.t === 'circle') {
      const s = tele.shapes[0], [sx, sy] = w2s(s.x, s.y);
      g.globalAlpha = 1; g.lineWidth = tele.current ? 4 : 2;
      g.strokeStyle = tele.current ? GOLD : '#a6dcff'; g.fillStyle = '#354755';
      // Iron posts and anvils remain distinct at game scale.
      if (tele.capacity && !tele.need) {
        g.fillRect(sx - 5, sy - 24, 10, 22); g.strokeRect(sx - 5, sy - 24, 10, 22);
        g.beginPath(); g.ellipse(sx, sy - 24, 8, 4, 0, 0, Math.PI * 2); g.fill(); g.stroke();
      } else {
        g.beginPath(); g.moveTo(sx - 15, sy - 12); g.lineTo(sx + 15, sy - 12); g.lineTo(sx + 8, sy - 5);
        g.lineTo(sx + 6, sy + 2); g.lineTo(sx - 6, sy + 2); g.lineTo(sx - 8, sy - 5); g.closePath(); g.fill(); g.stroke();
      }

    }
    if (tele.arrow && tele.shapes[0]?.t === 'lane') {
      const s = tele.shapes[0], [ax, ay] = w2s(s.x1, s.y1), [bx, by] = w2s(s.x2, s.y2);
      const a = Math.atan2(by - ay, bx - ax);
      g.globalAlpha = 1; g.strokeStyle = GOLD; g.lineWidth = 4;
      g.beginPath(); g.moveTo(bx - Math.cos(a - .6) * 20, by - Math.sin(a - .6) * 20);
      g.lineTo(bx, by); g.lineTo(bx - Math.cos(a + .6) * 20, by - Math.sin(a + .6) * 20); g.stroke();
    }
    if (tele.gaze && live > 0 && !calm) {              // the eye that is about to look: a small pulsing mark at its source
      const s = tele.shapes[0], [sx, sy] = w2s(s.x, s.y, 36);
      g.globalAlpha = .6 + .4 * Math.sin(t * 10); g.fillStyle = RED; g.beginPath(); g.arc(sx, sy, 7, 0, 7); g.fill();
    }
  }

  // ---- the screen pass -----------------------------------------------------------------------------------------------------
  // opts: w2s, boss(id) -> {x, y} | null, pos(characterId) -> {x, y} | null
  function drawHud(g, VW, VH, t, opts) {
    if (!fights.length) return;
    const { w2s, boss, pos } = opts, calm = reduced();
    g.save(); g.textAlign = 'center'; g.lineJoin = 'round';
    const label = (s, x, y, size, colour) => { g.font = `${size}px "Jua", sans-serif`; g.lineWidth = 4; g.strokeStyle = 'rgba(8,6,16,.95)'; g.fillStyle = colour; g.strokeText(s, x, y); g.fillText(s, x, y); };
    let y = 168;
    for (const f of fights) {
      const w = Math.min(360, VW - 40), x = (VW - w) / 2;
      const cast = f.cast && f.cast.total > 0 ? f.cast : null;
      if (cast) {
        const live = Math.max(0, cast.left - (now() - stamp)), p = Math.min(1, Math.max(0, 1 - live / cast.total));
        const flash = live < 1 && !calm ? .5 + .5 * Math.sin(t * 24) : 1;
        label(text(cast.name), VW / 2, y, 18, '#ffe2a0');
        g.globalAlpha = 1; g.fillStyle = 'rgba(12,8,20,.85)'; g.fillRect(x - 3, y + 5, w + 6, 16);
        g.fillStyle = '#4a1218'; g.fillRect(x, y + 8, w, 10);
        g.globalAlpha = flash; g.fillStyle = RED; g.fillRect(x, y + 8, w * p, 10);
        g.globalAlpha = 1; g.fillStyle = 'rgba(255,255,255,.3)'; g.fillRect(x, y + 8, w * p, 3);
        g.strokeStyle = '#c8a45a'; g.lineWidth = 2; g.strokeRect(x - 3, y + 5, w + 6, 16);
        label(live.toFixed(1), x + w + 28, y + 19, 15, '#fff4ca');
        y += 36;
      }
      if (f.break && f.break.needed > 0) {
        const b = f.break, k = Math.min(1, b.dealt / b.needed);
        label(text('Deal damage to stop it!'), VW / 2, y, 15, '#ffe2a0');
        g.fillStyle = 'rgba(12,8,20,.85)'; g.fillRect(x - 3, y + 5, w + 6, 16);
        g.fillStyle = '#3d3010'; g.fillRect(x, y + 8, w, 10); g.fillStyle = GOLD; g.fillRect(x, y + 8, w * k, 10);
        g.strokeStyle = '#c8a45a'; g.lineWidth = 2; g.strokeRect(x - 3, y + 5, w + 6, 16);
        y += 34;
      }
      if (f.shield) {
        const s = f.shield;
        label(`${text('Invulnerable')} · ${text(s.name)}`, VW / 2, y, 16, '#9fd8ff');
        label(fill(text('{0} of {1} left'), s.alive, s.adds), VW / 2, y + 20, 15, '#ffffff');
        y += 40;
        const b = boss?.(f.boss);
        if (b) {                                          // a pale bubble round the boss: nothing hurts it now
          const [sx, sy] = w2s(b.x, b.y, 52);
          g.globalAlpha = .55 + (calm ? 0 : .15 * Math.sin(t * 5)); g.lineWidth = 3; g.strokeStyle = '#9fd8ff';
          g.beginPath(); g.ellipse(sx, sy, 62, 74, 0, 0, 7); g.stroke();
          g.globalAlpha = .12; g.fillStyle = '#9fd8ff'; g.fill(); g.globalAlpha = 1;
        }
      }
      if (f.stunned > 0) { const b = boss?.(f.boss); if (b) { const [sx, sy] = w2s(b.x, b.y, 130); label(`${text('Stunned')} ${Math.max(0, f.stunned - (now() - stamp)).toFixed(1)}`, sx, sy, 16, GOLD); } }
      if (f.banner && f.banner !== f.cast?.name) label(text(f.banner), VW / 2, y + 4, 20, '#fff4ca');
      for (const tele of f.tele || []) {
        if (tele.label && tele.shapes?.length) {
          const [x,y] = centre(tele.shapes[0]), [sx,sy] = w2s(x,y,54);
          let words = text(tele.label);
          if (tele.need) words += ` · ${tele.count}/${tele.need}`;
          if (tele.holdTotal) words += ` · ${Number(tele.held).toFixed(1)}/${tele.holdTotal}s`;
          if (tele.fuse != null) words += ` · ${Number(tele.fuse).toFixed(1)}s`;
          label(words,sx,sy,tele.beat ? 22 : 15,tele.reflect ? '#fffaf0' : tele.tele === 'blue' ? '#b9e7ff' : '#ffe2a0');
        }
        if (tele.ingot && tele.shapes?.[0]?.t === 'circle') {
          const s = tele.shapes[0], [sx, sy] = w2s(s.x, s.y, 48);
          label(fill(text('Ingot {0}'), tele.ingot), sx, sy - 18, 18, tele.current ? GOLD : '#b8c7cf');
          label(text(tele.current ? 'Hit this one!' : 'Wait for its number'), sx, sy, 13, tele.current ? '#ffb19b' : '#b8c7cf');
        }
        if (!tele.role || tele.chain) continue;
        const station = tele.shapes?.[0];
        if (station?.t === 'circle') {
          const [sx, sy] = w2s(station.x, station.y), limit = tele.need || tele.capacity;
          const enough = tele.need ? tele.count >= tele.need : tele.count <= tele.capacity;
          label(`#${tele.role}  ${tele.count}/${limit}`, sx, sy - 33, 16, enough ? '#c5edff' : '#ffb19b');
        }
        for (const id of tele.players || []) {
          const p = pos(id);
          if (p) { const [sx, sy] = w2s(p.x, p.y, 112); label(`#${tele.role}`, sx, sy, 17, tele.current ? GOLD : '#b8e5ff'); }
        }
      }
      for (const id of f.marked || []) { const p = pos(id); if (p) { const [sx, sy] = w2s(p.x, p.y, 96); label(text('Marked!'), sx, sy, 15, '#ff8d80'); } }
      for (const id of f.frozen || []) { const p = pos(id); if (p) { const [sx, sy] = w2s(p.x, p.y, 96); label(text('Frozen!'), sx, sy, 15, '#ffd070'); } }
      const st = f.static;
      if (st) {
        for (const [id, n] of Object.entries(st.charges || {})) {
          const p = n > 0 ? pos(id) : null;
          if (p) { const [sx, sy] = w2s(p.x, p.y, 96); label(fill(text('{0} of {1} sparks'), n, st.limit), sx, sy, 15, n >= st.warnAt ? '#ff8d80' : '#ffe9a0'); }
        }
        for (const id of Object.keys(st.grounded || {})) { const p = pos(id); if (p) { const [sx, sy] = w2s(p.x, p.y, 96); label(text('Grounded'), sx, sy, 15, '#9fd8ff'); } }
      }
    }
    g.restore();
  }

  // ---- the death cause -----------------------------------------------------------------------------------------------------
  function setCause(name) {
    cause = name || '';
    const box = typeof document !== 'undefined' && document.getElementById('dead-cause');
    if (box) { box.textContent = cause ? fill('Killed by {0}', cause, '') : ''; box.hidden = !cause; }
  }
  // A network event: a death with a `cause` names what killed the player.
  function onEvent(event, me) {
    if (event.kind === 'death' && event.actor === me && event.cause) setCause(event.cause);
    if (event.kind === 'respawn' && event.actor === me) setCause('');
  }

  window.BossMech = {
    update, reset, drawFloor, drawHud, onEvent, setCause,
    colors: { red: RED, blue: BLUE, path: GOLD, green: GREEN },   // the four telegraph colours, shared with the boss signs
    get active() { return fights.length > 0; }, get fights() { return fights; }, get cause() { return cause; },
    _polygons: polygons, _left: left,
  };
})();
