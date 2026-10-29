'use strict';
// Presentation only: crossings still happen immediately in the authoritative world.
(() => {
  const sea = z => z?.theme === 'deep' || z?.theme === 'nacre';
  const sky = z => z?.theme === 'sky';
  const tr = s => window.Locale?.translate(s) || s;
  let active = null, timer;
  function route(from, to) {
    if (sky(to) && !sky(from)) return { kind: 'sky', up: true, text: 'Ascending into the sky', detail: 'The clouds fall away beneath you.' };
    if (sea(to) && !sea(from)) return { kind: 'sea', up: false, text: 'Descending to the ocean floor', detail: 'The surface fades far above you.' };
    if (sea(to) && sea(from)) return { kind: 'sea', up: null, text: 'Along the ocean floor', detail: 'Beneath the waves, the seabed continues.' };
    if (sky(from) && !sky(to)) return { kind: 'sky', up: false, text: 'Descending from the sky', detail: 'Leaving the clouds for the land below.' };
    if (sea(from) && !sea(to)) return { kind: 'sea', up: true, text: 'Rising to the surface', detail: 'Leaving the ocean floor behind.' };
    return null;
  }
  const location = z => sky(z) ? 'High in the sky · above the clouds' : sea(z) ? 'Ocean floor · deep beneath the surface' : '';
  function clear() {
    active = null; clearTimeout(timer);
    const notice = document.getElementById('zone-journey'); if (notice) notice.hidden = true;
  }
  function enter(from, to, initial) {
    clear();
    const badge = document.getElementById('zone-altitude'), label = location(to);
    if (badge) { badge.textContent = tr(label); badge.hidden = !label; }
    const trip = route(from, to);
    // Reconnecting to a saved location is not another climb or dive.
    if (initial || !trip) return;
    active = { ...trip, at: performance.now() };
    const notice = document.getElementById('zone-journey');
    if (notice) {
      notice.dataset.kind = trip.kind;
      notice.querySelector('b').textContent = (trip.up === null ? '↔  ' : trip.up ? '↑  ' : '↓  ') + tr(trip.text);
      notice.querySelector('span').textContent = tr(trip.detail);
      notice.hidden = false;
    }
    timer = setTimeout(clear, 4600);
  }
  // Soft cloud banks below the islands give the void a visible floor far below.
  function cloud(g, x, y, r) {
    g.beginPath(); g.ellipse(x, y, r, r * .16, 0, 0, Math.PI * 2);
    g.ellipse(x - r * .5, y + r * .04, r * .55, r * .13, 0, 0, Math.PI * 2);
    g.ellipse(x + r * .48, y + r * .03, r * .6, r * .12, 0, 0, Math.PI * 2); g.fill();
  }
  function belowClouds(g, w, h, t, cx, cy, still) {
    g.save();
    for (let layer = 0; layer < 2; layer++) {
      g.fillStyle = layer ? 'rgba(240,249,255,.58)' : 'rgba(158,202,236,.5)';
      for (let i = 0; i < 8; i++) {
        const span = w + 650, drift = still ? 0 : t * (5 + layer * 4);
        const x = ((i * 317 + layer * 143 + drift - cx * (.08 + layer * .05)) % span + span) % span - 325;
        const y = h * (.34 + layer * .29) + Math.sin(i * 2.7) * 80 - Math.sin(cy * .0003) * 35;
        cloud(g, x, y, 160 + i % 3 * 34);
      }
    }
    g.restore();
  }
  // Foreground travel moves opposite the traveller: down for climbing, up for diving.
  // Keep the centre clear, use no camera shake/zoom, and suppress motion entirely when requested.
  function draw(g, w, h, still) {
    if (!active || still || active.up === null) return;
    const age = (performance.now() - active.at) / 1000;
    if (age >= 3.4) return;
    const fade = Math.min(1, age * 3) * Math.min(1, (3.4 - age) / 1.1), sign = active.up ? 1 : -1;
    g.save(); g.globalAlpha = fade;
    const wash = g.createLinearGradient(0, 0, 0, h);
    wash.addColorStop(0, active.kind === 'sky' ? 'rgba(198,229,255,.22)' : 'rgba(8,99,139,.26)');
    wash.addColorStop(1, 'rgba(8,30,60,0)'); g.fillStyle = wash; g.fillRect(0, 0, w, h);
    if (active.kind === 'sky') {
      g.fillStyle = 'rgba(244,250,255,.58)';
      for (let i = 0; i < 10; i++) {
        const x = i % 2 ? w * .94 : w * .06;
        const y = ((i * 173 + sign * age * (190 + i % 3 * 45)) % (h + 300) + h + 300) % (h + 300) - 150;
        cloud(g, x + Math.sin(i * 3) * 90, y, 150 + i % 3 * 35);
      }
    } else {
      // The bright underside of the surface recedes upward during the dive.
      const surface = g.createLinearGradient(0, 0, 0, h * .5);
      surface.addColorStop(0, `rgba(132,238,255,${.36 * Math.max(0, 1 - age / 2.8)})`);
      surface.addColorStop(1, 'rgba(40,159,195,0)'); g.fillStyle = surface; g.fillRect(0, 0, w, h * .5);
      g.strokeStyle = 'rgba(169,240,252,.45)'; g.lineWidth = 3;
      const surfaceY = active.up ? -h * .3 + age * h * .15 : h * .28 - age * h * .28;
      for (let i = 0; i < 5; i++) {
        g.beginPath(); g.ellipse(w * .5, surfaceY + i * 13, w * (.3 + i * .04), 20 + i * 7, 0, 0, Math.PI * 2); g.stroke();
      }
      g.strokeStyle = 'rgba(196,246,255,.8)'; g.lineWidth = 2;
      for (let i = 0; i < 38; i++) {
        const x = i % 2 ? w - 30 - (i * 47 % (w * .23)) : 30 + (i * 47 % (w * .23));
        const y = ((i * 97 + sign * age * (220 + i % 4 * 55)) % (h + 80) + h + 80) % (h + 80) - 40;
        g.beginPath(); g.arc(x + Math.sin(i + age) * 9, y, 3 + i % 5 * 2, 0, Math.PI * 2); g.stroke();
      }
    }
    g.restore();
  }
  // Authored route coordinates and collision stay intact; show the height change at the approach.
  function approach(g, p, from, to, project, t, still) {
    const trip = route(from, to); if (!trip || trip.up === null) return false;
    const [dx, dy] = p.walk, [sx, sy] = project(p.x, p.y), up = trip.up;
    const skyStone = trip.kind === 'sky', steps = 8, run = .7, rise = 26, width = 1.05;
    const ax = dx * (up ? 1 : -1), ay = dy * (up ? 1 : -1);
    // Turn the flight at its foot landing when necessary, keeping its risers
    // facing the camera rather than hiding them behind the tall end wall.
    const ux = ax + ay > 0 ? -ay : ax, uy = ax + ay > 0 ? -ax : ay, vx = -uy, vy = ux;
    // All surfaces share actual isometric corners. The 208 px climb is taller
    // than the ground-plane projection, so the upper end visibly rises.
    const point = (u, v, z) => {
      const ox = -dx * 1.6 - (up ? 0 : ux * steps * run), oy = -dy * 1.6 - (up ? 0 : uy * steps * run);
      const [x,y] = project(p.x + ox + ux * u + vx * v, p.y + oy + uy * u + vy * v);
      return [x, y - z];
    };
    const face = (points, color, stroke = true) => {
      g.beginPath(); points.forEach(([x,y],i) => i ? g.lineTo(x,y) : g.moveTo(x,y)); g.closePath();
      g.fillStyle = color; g.fill(); if (stroke) g.stroke();
    };
    const rail = (side) => {
      const low = point(0,side * width, rise + 40), high = point(steps * run,side * width,steps * rise + 40);
      g.lineCap = 'round';
      for (let i = 0; i <= steps; i += 2) {
        const z = Math.max(1,i) * rise, railZ = rise + 40 + (steps-1) * rise * i / steps;
        const a = point(i*run,side*width,z), b = point(i*run,side*width,railZ);
        g.strokeStyle = '#30364d'; g.lineWidth = 7; g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke();
        g.strokeStyle = skyStone ? '#e4c678' : '#85d3d6'; g.lineWidth = 4; g.stroke();
        g.fillStyle = skyStone ? '#fff1b5' : '#c4ffff'; g.beginPath(); g.arc(b[0],b[1],4.5,0,Math.PI*2); g.fill();
      }
      g.strokeStyle = '#30364d'; g.lineWidth = 9; g.beginPath(); g.moveTo(...low); g.lineTo(...high); g.stroke();
      g.strokeStyle = skyStone ? '#e4c678' : '#85d3d6'; g.lineWidth = 5; g.stroke();
      g.strokeStyle = skyStone ? '#fff0b4' : '#d2ffff'; g.lineWidth = 1.5; g.stroke();
    };
    g.save(); g.lineJoin = 'round'; g.lineWidth = 1.8; g.strokeStyle = '#30364d';
    face([point(-.65,-width,0),point(-.65,width,0),point(0,width,0),point(0,-width,0)], skyStone ? '#cbd8ef' : '#80bec8');
    // Solid stepped side walls carry the entire flight down to its foundation.
    const nearSide = vx + vy > 0 ? 1 : -1;
    rail(-nearSide);
    g.strokeStyle = '#30364d'; g.lineWidth = 1.8;
    for (const side of [-nearSide, nearSide]) {
      const profile = [point(0,side*width,0)];
      for (let i = 0; i < steps; i++) profile.push(point(i*run,side*width,(i+1)*rise),point((i+1)*run,side*width,(i+1)*rise));
      profile.push(point(steps*run,side*width,0));
      face(profile, skyStone ? (side === nearSide ? '#75829f' : '#96a3c0') : (side === nearSide ? '#286977' : '#408b96'));
      // Masonry joints make the side read as a load-bearing wall.
      g.strokeStyle = skyStone ? '#aab6ce' : '#69a4ab'; g.lineWidth = 1;
      for (let i = 2; i < steps; i += 2) {
        const a = point(i*run,side*width,0), b = point(i*run,side*width,i*rise);
        g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke();
      }
      g.strokeStyle = '#30364d'; g.lineWidth = 1.8;
    }
    // Paint the farther blocks first for all four map directions.
    const order = Array.from({length:steps},(_,i)=>i);
    if (ux + uy > 0) order.reverse();
    for (const i of order) {
      const u = i*run, h = (i+1)*rise;
      face([point(u,-width,h-rise),point(u,width,h-rise),point(u,width,h),point(u,-width,h)], skyStone ? '#a1adc6' : '#4f9ba5');
      face([point(u,-width,h),point(u,width,h),point(u+run,width,h),point(u+run,-width,h)], skyStone ? (i%2 ? '#edf2ff' : '#dae5fa') : (i%2 ? '#b6eaeb' : '#8fcdd4'));
      const a = point(u,-width,h), b = point(u,width,h);
      g.strokeStyle = skyStone ? '#ffffff' : '#e3ffff'; g.lineWidth = 2.5;
      g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke();
      g.strokeStyle = '#30364d'; g.lineWidth = 1.8;
    }
    rail(nearSide);
    const upper = point(steps*run,0,steps*rise), lower = point(0,0,0);
    const labelX = (upper[0] + lower[0]) / 2, labelY = Math.min(upper[1], lower[1]) - 92;
    g.font = '22px "Jua",sans-serif'; g.textAlign = 'center'; g.lineWidth = 5;
    g.strokeStyle = '#102d46'; g.fillStyle = '#ecfaff';
    const label = (up ? '↑  ' : '↓  ') + tr(trip.text);
    g.strokeText(label, labelX, labelY); g.fillText(label, labelX, labelY);
    g.font = '17px "Jua",sans-serif'; g.strokeText(to.name, labelX, labelY + 26); g.fillText(to.name, labelX, labelY + 26);
    if (trip.kind === 'sky') {
      g.fillStyle = 'rgba(224,242,255,.3)'; cloud(g, upper[0], upper[1] + 12, 65);
    } else {
      g.strokeStyle = 'rgba(171,238,255,.75)'; g.lineWidth = 2;
      for (let i = 0; i < 8; i++) {
        const phase = still ? i / 8 : (t * .35 + i / 8) % 1;
        g.beginPath(); g.arc(sx + (i % 3 - 1) * 24, sy + 15 - phase * 100, 3 + i % 3, 0, Math.PI * 2); g.stroke();
      }
    }
    g.restore(); return true;
  }
  window.ZoneJourney = { route, location, enter, clear, draw, approach, belowClouds };
})();
