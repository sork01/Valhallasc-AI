'use strict';
(() => {
  let learned, veins = [], patches = [];

  function sync(packet, own) {
    learned = own.gathering;
    veins = packet.miningVeins || [];
    patches = packet.flowerPatches || [];
  }
  function reset() {
    learned = null;
    veins = [];
    patches = [];
  }

  function draw(g, scale, vx, vy, width) {
    if (learned?.ore && window.Prefs?.trackOre !== false) drawMarkers(g, scale, vx, vy, width, 'ore', veins);
    if (learned?.flowers && window.Prefs?.trackFlowers !== false) drawMarkers(g, scale, vx, vy, width, 'flowers', patches);
  }

  function drawMarkers(g, scale, vx, vy, width, mode, markers) {
    if (!markers.length) return;
    const cx = vx * scale + width / 2, cy = vy * scale + width / 2;
    const edge = width / 2 - 7;
    let nearest = null, hasVisible = false;
    g.save();
    g.fillStyle = mode === 'ore' ? '#ffd17a' : '#ffa6db';
    g.strokeStyle = '#161926';
    g.lineWidth = 2;
    g.lineJoin = 'round';
    for (const {x, y} of markers) {
      const mx = x * scale, my = y * scale, dx = mx - cx, dy = my - cy;
      if (Math.max(Math.abs(dx), Math.abs(dy)) > edge) {
        const distance = dx * dx + dy * dy;
        if (!nearest || distance < nearest.distance) nearest = {dx, dy, distance};
        continue;
      }
      hasVisible = true;
      g.beginPath();
      if (mode === 'ore') {
        g.moveTo(mx, my - 5); g.lineTo(mx + 5, my); g.lineTo(mx, my + 5); g.lineTo(mx - 5, my); g.closePath();
      } else {
        g.arc(mx, my, 5, 0, Math.PI * 2);
      }
      g.fill(); g.stroke();
      if (mode === 'flowers') {
        g.beginPath(); g.arc(mx, my, 1.6, 0, Math.PI * 2); g.stroke();
      }
    }
    // Give the direction of the closest resource when the zoom hides every marker.
    if (!hasVisible && nearest) {
      const {dx, dy} = nearest, factor = edge / Math.max(Math.abs(dx), Math.abs(dy));
      g.translate(cx + dx * factor, cy + dy * factor);
      g.rotate(Math.atan2(dy, dx));
      g.beginPath(); g.moveTo(5, 0); g.lineTo(-4, 4); g.lineTo(-4, -4); g.closePath();
      g.fill(); g.stroke();
    }
    g.restore();
  }
  window.GatheringMap = {sync, reset, draw};
})();
