'use strict';
(() => {
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  const radius = 3;
  const halo = [];
  for (let y = -radius; y <= radius; y++) for (let x = -radius; x <= radius; x++) {
    const distance = Math.hypot(x, y);
    if (distance > 0 && distance <= radius) halo.push([x, y, Math.round(115 * (1 - distance / (radius + .5)))]);
  }

  function streaks(g, x, y, direction, size) {
    g.lineWidth = 1.4;
    g.beginPath();
    g.moveTo(x, y); g.lineTo(x + direction * size * 6, y - size * 3);
    g.moveTo(x - direction * 1.5, y + 3); g.lineTo(x + direction * size * 4, y + 3 - size * 2);
    g.stroke();
  }

  function splinter(g, x, y, direction, size) {
    g.beginPath();
    g.moveTo(x + direction * size * 4, y - size * 2);
    g.lineTo(x - direction * size, y + size * 2);
    g.lineTo(x, y - size * 2.5);
    g.closePath();
    g.fill();
  }

  function arc(g, x, y, direction, size) {
    g.beginPath();
    g.moveTo(x - direction * size * 3, y + size * 3);
    g.lineTo(x, y); g.lineTo(x - direction * size * 1.5, y - size);
    g.lineTo(x + direction * size * 4, y - size * 4);
    g.moveTo(x, y); g.lineTo(x + direction * size * 3, y + size);
    g.lineWidth = 2.4;
    g.stroke();
    g.strokeStyle = '#d4f8ff';
    g.lineWidth = 1;
    g.stroke();
  }

  const crystalColors = ['#b6f1ff', '#f7b6fd', '#c9c4ff'];
  function crystal(g, x, y, direction, size, age, index) {
    const turn = direction * Math.cos(age * Math.PI * 2) * size * 2;
    g.fillStyle = crystalColors[index % crystalColors.length];
    g.beginPath();
    g.moveTo(x + turn, y - size * 4); g.lineTo(x + size * 1.8, y);
    g.lineTo(x - turn, y + size * 4); g.lineTo(x - size * 1.8, y);
    g.closePath();
    g.fill();
    g.lineWidth = 1;
    g.stroke();
  }

  function stone(g, x, y, direction, size) {
    g.beginPath();
    g.moveTo(x - size * 2, y); g.lineTo(x - size, y - size * 2);
    g.lineTo(x + size, y - size * 1.5); g.lineTo(x + size * 2, y + size);
    g.lineTo(x, y + size * 2); g.closePath();
    g.fillStyle = '#ae794f';
    g.fill();
    g.lineWidth = 1.1;
    g.stroke();
    g.fillStyle = '#ffd09d';
    g.fillRect(x - direction * 4, y - 3, size, size);
    g.fillRect(x - direction * 6, y - 5, size * .7, size * .7);
  }

  const themes = new Map([
    ['double_tap', { rgb: [255, 202, 54], light: '#ffedac', rate: 1.55, spread: 10, rise: 9, particle: streaks }],
    ['shieldbreaker', { rgb: [255, 62, 74], light: '#ff8b83', rate: 1.1, spread: 18, rise: 13, particle: splinter }],
    ['lightning_rod', { rgb: [61, 181, 255], light: '#54b9ff', rate: 2, spread: 7, rise: 6, particle: arc }],
    ['prism_echo', { rgb: [177, 91, 255], light: '#e8c7ff', rate: .85, spread: 12, rise: 16, particle: crystal }],
    ['cairnstrike', { rgb: [230, 134, 65], light: '#d8a075', rate: 1, spread: 15, rise: 8, gravity: 24, particle: stone }],
  ]);

  // Cache a trimmed glow and emission points from the visible weapon pixels in each pose.
  function prepare(image, mask, theme) {
    const { width, height, data } = image;
    let left = width, right = -1, top = height, bottom = -1;
    const pixels = [], edges = [];
    for (let p = 0; p < mask.length; p++) {
      if (!mask[p]) continue;
      const x = p % width, y = Math.floor(p / width);
      left = Math.min(left, x); right = Math.max(right, x);
      top = Math.min(top, y); bottom = Math.max(bottom, y);
      pixels.push(p);
      if (x === 0 || x === width - 1 || y === 0 || y === height - 1 ||
          !data[(p - 1) * 4 + 3] || !data[(p + 1) * 4 + 3] ||
          !data[(p - width) * 4 + 3] || !data[(p + width) * 4 + 3]) edges.push(p);
    }
    if (!pixels.length) return null;

    // Give the halo room beyond the atlas cell, and keep it off opaque non-weapon pixels.
    left -= radius; top -= radius;
    const glow = document.createElement('canvas');
    glow.width = right - left + radius + 1; glow.height = bottom - top + radius + 1;
    const g = glow.getContext('2d'), light = g.createImageData(glow.width, glow.height);
    const [r, green, b] = theme.rgb;
    function paint(x, y, alpha) {
      const dst = ((y - top) * glow.width + x - left) * 4;
      if (alpha <= light.data[dst + 3]) return;
      light.data[dst] = r; light.data[dst + 1] = green; light.data[dst + 2] = b; light.data[dst + 3] = alpha;
    }
    for (const p of pixels) {
      const x = p % width, y = Math.floor(p / width);
      paint(x, y, 155);
      for (const [dx, dy, alpha] of halo) {
        const tx = x + dx, ty = y + dy;
        if (tx >= 0 && tx < width && ty >= 0 && ty < height && data[(ty * width + tx) * 4 + 3]) continue;
        paint(tx, ty, alpha);
      }
    }
    g.putImageData(light, 0, 0);
    const emitters = edges.length ? edges : pixels;
    const count = Math.min(16, emitters.length);
    const points = Array.from({ length: count }, (_, i) => {
      const p = emitters[Math.floor(i * emitters.length / count)];
      return [p % width + .5, Math.floor(p / width) + .5];
    });
    return { glow, left, top, mask, theme, points };
  }

  function draw(g, art, x, y, t, attacking) {
    if (!art) return;
    const { glow, left, top, theme, points } = art;
    const still = reducedMotion?.matches, opacity = g.globalAlpha;
    g.save();
    g.globalCompositeOperation = 'screen';
    g.globalAlpha = opacity * (still ? .88 : .88 + .12 * Math.sin(t * Math.PI * 2));
    g.drawImage(glow, x + left, y + top);
    if (!still) {
      const reach = attacking ? 1.4 : 1;
      for (let i = 0; i < 7; i++) {
        const cycle = t * theme.rate + i * .381, step = Math.floor(cycle), age = cycle - step;
        const point = ((step + i * 5) % points.length + points.length) % points.length;
        const [sx, sy] = points[point];
        const direction = i % 2 ? -1 : 1;
        const px = x + sx + direction * age * theme.spread * reach;
        const py = y + sy - age * theme.rise * reach + (theme.gravity || 0) * age * age;
        g.globalAlpha = opacity * Math.min(1, age * 10) * (1 - age);
        g.fillStyle = g.strokeStyle = theme.light;
        theme.particle(g, px, py, direction, .85 + i % 3 * .19, age, i);
      }
    }
    g.restore();
  }

  window.WeaponEnchantArt = { theme: id => themes.get(id), prepare, draw };
})();
