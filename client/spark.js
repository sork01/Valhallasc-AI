'use strict';
// PixelFlow spark animation shared by travellers and the travel masters' beacons.
(() => {
  const atlas = new Image(); atlas.src = 'assets/spark.png';
  function draw(g, actor, t, beacon = false) {
    const angle = beacon ? 0 : Math.atan2((actor.fx + actor.fy) * 22, (actor.fx - actor.fy) * 44);
    g.save(); g.translate(0, beacon ? -119 : -86 + Math.sin(t * 7) * 3);
    const glow = g.createRadialGradient(0, 0, 2, 0, 0, beacon ? 22 : 48);
    glow.addColorStop(0, '#fff4cbb0'); glow.addColorStop(.3, '#7cebe56b'); glow.addColorStop(1, '#68cfe000');
    g.fillStyle = glow; g.fillRect(-48, -48, 96, 96);
    g.rotate(angle); g.imageSmoothingEnabled = false;
    const scale = beacon ? .65 : 1.5, size = 64 * scale;
    if (atlas.complete && atlas.naturalWidth) g.drawImage(atlas, (Math.floor(t * 12) % 12) * 64, 0, 64, 64, -size / 2, -size / 2, size, size);
    g.restore();
  }
  window.Spark = { draw, atlas };
})();
