'use strict';
// One shared server clock for outdoor light. The scene tint is a single canvas fill;
// ground chunks, characters, loot, and combat effects are never repainted for time of day.
(() => {
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const indoorThemes = new Set(['vault', 'orrery', 'arena', 'heartwood', 'deep']);
  const isOutdoor = z => !!z && !(z.players > 0 || z.copies > 0 || z.template != null || indoorThemes.has(z.theme));
  const clock = { hour: 12, speed: 0, at: 0, synced: false };
  let zone = null, outdoorBlend = 0, lastLabel = '', lastPaint = 0, glow = null;
  const hour = () => (clock.hour + (performance.now() - clock.at) / 1000 * clock.speed) % 24;
  const phase = h => h < 5 || h >= 20 ? 'Night' : h < 7 ? 'Dawn' : h < 18 ? 'Day' : 'Dusk';
  const night = h => h < 5 ? 1 : h < 7 ? (7 - h) / 2 : h < 18 ? 0 : h < 20 ? (h - 18) / 2 : 1;
  const warm = h => Math.max(0, 1 - Math.abs(h - 6) / 1.5, 1 - Math.abs(h - 18.5) / 1.5);
  const palette = theme => {
    if (theme === 'ember' || theme === 'solar_crucible') return ['17,26,53', '235,105,49'];
    if (theme === 'frost' || theme === 'frostwake' || theme === 'cairnspine') return ['16,37,76', '237,179,108'];
    if (theme === 'fen' || theme === 'worldtree' || theme === 'tanglecrown' || theme === 'moonspore') return ['13,36,49', '208,145,84'];
    if (theme === 'lapiserg') return ['27,26,68', '242,139,71'];
    if (theme === 'yearwheel') return ['25,32,69', '242,161,93'];
    return ['18,29,67', '246,157,98'];
  };
  function sync(value) {
    if (!value || !Number.isFinite(value.hour) || !Number.isFinite(value.hoursPerSecond)) return;
    clock.hour = ((value.hour % 24) + 24) % 24;
    clock.speed = value.hoursPerSecond;
    clock.at = performance.now(); clock.synced = true;
  }
  function setZone(z) { zone = z; }
  function tick(dt) {
    const target = isOutdoor(zone) ? 1 : 0;
    outdoorBlend += (target - outdoorBlend) * clamp(dt / 1.2);
    if (!clock.synced || performance.now() - lastPaint < 500) return;
    lastPaint = performance.now();
    const h = hour(), label = `${isOutdoor(zone) ? (h < 6 || h >= 18 ? '☾' : '☀') : '⌂'} ${String(Math.floor(h)).padStart(2, '0')}:${String(Math.floor((h % 1) * 60)).padStart(2, '0')}`;
    if (label === lastLabel) return;
    lastLabel = label;
    const el = document.getElementById('world-clock');
    if (el) { el.textContent = label; const title = `World time · ${phase(h)}${isOutdoor(zone) ? '' : ' · indoor light'} · one day every 20 minutes`; el.title = window.Locale?.translate(title) || title; }
  }
  function glowSprite() {
    if (glow) return glow;
    glow = document.createElement('canvas'); glow.width = glow.height = 128;
    const g = glow.getContext('2d'), grad = g.createRadialGradient(64, 64, 3, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255,231,145,.65)'); grad.addColorStop(.35, 'rgba(255,173,72,.22)'); grad.addColorStop(1, 'rgba(255,173,72,0)');
    g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
    return glow;
  }
  function draw(g, width, height, lights, project) {
    if (!clock.synced || outdoorBlend < .002) return;
    const h = hour(), n = night(h), w = warm(h), amount = window.Prefs?.night ?? 1;
    const [darkColor, warmColor] = palette(zone?.theme);
    g.save();
    const warmAlpha = .075 * w * outdoorBlend;
    if (warmAlpha > .002) { g.fillStyle = `rgba(${warmColor},${warmAlpha})`; g.fillRect(0, 0, width, height); }
    const darkAlpha = .27 * n * outdoorBlend * amount;
    if (darkAlpha > .002) { g.fillStyle = `rgba(${darkColor},${darkAlpha})`; g.fillRect(0, 0, width, height); }
    if (window.Prefs?.lowGraphics) { g.restore(); return; }
    if (n > .3) {
      const alpha = n * outdoorBlend * .6;
      g.fillStyle = `rgba(234,246,255,${alpha})`;
      for (let i = 0; i < 22; i++) {
        const x = (i * 619 + 127) % width, y = (i * 137 + 19) % Math.max(1, height * .25);
        g.fillRect(x, y, i % 5 === 0 ? 2 : 1, i % 5 === 0 ? 2 : 1);
      }
    }
    if (n > .2 && zone?.theme === 'frostwake') {
      g.fillStyle = `rgba(99,245,204,${.08 * n * outdoorBlend})`;
      g.beginPath(); g.ellipse(width * .53, height * .08, width * .42, height * .09, -.13, 0, Math.PI * 2); g.fill();
    } else if (n > .2 && zone?.theme === 'ember') {
      g.fillStyle = `rgba(255,107,44,${.06 * n * outdoorBlend})`;
      g.fillRect(0, height * .7, width, height * .3);
    } else if (n > .2 && ['fen', 'worldtree', 'moonspore'].includes(zone?.theme)) {
      g.fillStyle = `rgba(127,255,188,${.3 * n * outdoorBlend})`;
      for (let i = 0; i < 8; i++) g.fillRect((i * 179 + 43) % width, height * (.55 + (i % 4) * .09), 3, 3);
    }
    const daylight = h >= 6 && h < 18;
    const progress = daylight ? (h - 6) / 12 : ((h - 18 + 24) % 24) / 12;
    const orbX = width * (.13 + .74 * progress), orbY = height * (.19 - .11 * Math.sin(progress * Math.PI));
    g.globalAlpha = outdoorBlend * (daylight ? .65 : .72 * n);
    g.fillStyle = daylight ? '#fff2b7' : '#e5ecff';
    g.beginPath(); g.arc(orbX, orbY, daylight ? 15 : 11, 0, Math.PI * 2); g.fill();
    g.globalAlpha = Math.max(0, n * outdoorBlend * .7);
    if (g.globalAlpha > .01 && lights?.length) {
      const sprite = glowSprite();
      let shown = 0;
      for (const light of lights) {
        const [x, y] = project(light.x, light.y);
        if (x > -80 && x < width + 80 && y > -100 && y < height + 100) { g.drawImage(sprite, x - 64, y - 110); if (++shown >= 32) break; }
      }
    }
    g.restore();
  }
  window.DayNight = { sync, setZone, tick, draw, isOutdoor, get hour() { return hour(); }, get outdoorBlend() { return outdoorBlend; },
    get nightMix() { return clock.synced && isOutdoor(zone) ? night(hour()) : 0; },
    get shadowOffset() { return isOutdoor(zone) && hour() >= 7 && hour() <= 18 ? (12 - hour()) * 1.4 : 0; } };
})();
