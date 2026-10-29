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
    g.save(); g.lineJoin = 'round';
    for (let i = 0; i < 7; i++) {
      const f = i / 6, [x, y] = project(p.x + dx * (f * 5 - 2), p.y + dy * (f * 5 - 2));
      const lift = (up ? f : 1 - f) * 50;
      g.strokeStyle = trip.kind === 'sky' ? '#8276ab' : '#28788d'; g.lineWidth = 10;
      g.beginPath(); g.moveTo(x - 32, y - lift + 9); g.lineTo(x + 32, y - lift + 9); g.stroke();
      g.strokeStyle = trip.kind === 'sky' ? '#e9e2ff' : '#8ce0e9'; g.lineWidth = 5;
      g.beginPath(); g.moveTo(x - 32, y - lift); g.lineTo(x + 32, y - lift); g.stroke();
    }
    g.font = '22px "Jua",sans-serif'; g.textAlign = 'center'; g.lineWidth = 5;
    g.strokeStyle = '#102d46'; g.fillStyle = '#ecfaff';
    const label = (up ? '↑  ' : '↓  ') + tr(trip.text);
    g.strokeText(label, sx, sy - 108); g.fillText(label, sx, sy - 108);
    g.font = '17px "Jua",sans-serif'; g.strokeText(to.name, sx, sy - 82); g.fillText(to.name, sx, sy - 82);
    if (trip.kind === 'sky') {
      g.fillStyle = 'rgba(224,242,255,.5)'; cloud(g, sx, sy + 25, 85);
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
