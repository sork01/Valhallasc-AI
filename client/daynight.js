'use strict';
// One shared server clock for outdoor light. The scene tint is a single canvas fill;
// ground chunks, characters, loot, and combat effects are never repainted for time of day.
(() => {
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const indoorThemes = new Set(['vault', 'orrery', 'arena', 'heartwood', 'deep']);
  const isOutdoor = z => !!z && !(z.players > 0 || z.copies > 0 || z.template != null || indoorThemes.has(z.theme));
  const clock = { hour: 12, speed: 0, at: 0, synced: false };
  let zone = null, outdoorBlend = 0, lastLabel = '', lastPaint = 0, glow = null, veil = null, veilG = null;
  const hour = () => (clock.hour + (performance.now() - clock.at) / 1000 * clock.speed) % 24;
  const phase = h => h < 5 || h >= 20 ? 'Night' : h < 7 ? 'Dawn' : h < 18 ? 'Day' : 'Dusk';
  const night = h => h < 5 ? 1 : h < 7 ? (7 - h) / 2 : h < 18 ? 0 : h < 20 ? (h - 18) / 2 : 1;
  const warm = h => Math.max(0, 1 - Math.abs(h - 6) / 1.5, 1 - Math.abs(h - 18.5) / 1.5);
  // [shadow veil RGB, dusk/dawn warmth RGB, cool moonlight multiply RGB]
  const palette = theme => {
    if (theme === 'ember' || theme === 'emberwake' || theme === 'solar_crucible') return ['14,16,36', '235,105,49', '66,54,104'];
    if (theme === 'frost' || theme === 'frostwake' || theme === 'cairnspine') return ['10,22,56', '237,179,108', '52,86,164'];
    if (theme === 'fen' || theme === 'worldtree' || theme === 'tanglecrown' || theme === 'moonspore') return ['7,22,36', '208,145,84', '42,80,112'];
    if (theme === 'lapiserg') return ['16,14,48', '242,139,71', '68,60,152'];
    if (theme === 'yearwheel') return ['14,18,46', '242,161,93', '62,74,148'];
    if (theme === 'wyrd') return ['12,18,40', '224,140,86', '54,68,124'];
    return ['10,17,44', '246,157,98', '56,80,150'];
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
  // Emitter [dx, dy] from each object's ground origin (sx, sy) to its flame, bulb, or lit facade.
  const LIGHT_ANCHORS = {
    lamp: [0, -120],
    astrolamp: [0, -123],
    glasslamp: [0, -143],
    pearllamp: [0, -78],
    sporelamp: [0, -94],
    stormlamp: [0, -98],
    leaf_lantern: [0, -106],
    frostwake_lantern: [0, -146],
    year_lantern: [0, -194],
    ew_lantern: [19, -127],
    confetti_lantern: [0, -134],
    brazier: [0, -68],
    torch: [0, -88],
    campfire: [0, -24],
    lamphouse: [0, -164],
    house: [0, -52],
    aetherhouse: [0, -34],
    astralhouse: [0, -18],
    nacrehouse: [0, -36],
    nacreinn: [0, -24],
    meadow_cottage: [0, -16],
    meadow_mill: [0, -24],
  };
  function lightAnchor(light) {
    const k = light?.kind;
    if (!k) return [0, -46];
    if (LIGHT_ANCHORS[k]) return LIGHT_ANCHORS[k];
    if (k.includes('campfire')) return [0, -24];
    if (k.includes('brazier')) return [0, -68];
    if (k.includes('torch')) return [0, -88];
    if (k.includes('lamp') || k.includes('lantern')) return [0, -120];
    if (k.includes('cottage') || k.includes('inn') || k.includes('house') || k.includes('shop')) return [0, -36];
    return [0, -46];
  }
  function glowSprite() {
    if (glow) return glow;
    glow = document.createElement('canvas'); glow.width = glow.height = 128;
    const g = glow.getContext('2d'), grad = g.createRadialGradient(64, 64, 3, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255,231,145,.65)'); grad.addColorStop(.35, 'rgba(255,173,72,.22)'); grad.addColorStop(1, 'rgba(255,173,72,0)');
    g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
    return glow;
  }
  function draw(g, width, height, lights, project, focus) {
    if (!clock.synced || outdoorBlend < .002) return;
    const h = hour(), n = night(h), w = warm(h), amount = window.Prefs?.night ?? 1;
    // Near a border you can cross, the neighbour's light and glow mix in by the same weight as the ground (.5 at the line), so the
    // light does not snap when the server moves you across.
    const sb = window.Field?.seamBlend, wN = sb ? sb.w : 0, [dark1, warm1, mul1] = palette(zone?.theme), [dark2, warm2, mul2] = sb ? palette(sb.theme) : [dark1, warm1, mul1];
    const mixRgb = (a, b) => a.split(',').map((v, i) => Math.round(+v + (+b.split(',')[i] - +v) * wN)).join(',');
    const darkColor = mixRgb(dark1, dark2), warmColor = mixRgb(warm1, warm2), mulColor = mixRgb(mul1, mul2);
    const nightDepth = n * outdoorBlend * amount;
    const lowGfx = !!window.Prefs?.lowGraphics;
    const visibleLights = [];
    if (!lowGfx && n > .01 && lights?.length) {
      for (const light of lights) {
        const [ax, ay] = lightAnchor(light);
        const [bx, by] = project(light.x, light.y);
        const lx = bx + ax, ly = by + ay;
        if (lx > -140 && lx < width + 140 && ly > -140 && ly < height + 140) {
          visibleLights.push([lx, ly]);
          if (visibleLights.length >= 32) break;
        }
      }
    }
    g.save();
    const warmAlpha = .075 * w * outdoorBlend;
    if (warmAlpha > .002) { g.fillStyle = `rgba(${warmColor},${warmAlpha})`; g.fillRect(0, 0, width, height); }
    if (nightDepth > .002) {
      g.globalCompositeOperation = 'multiply';
      g.fillStyle = `rgba(${mulColor},${(.56 * nightDepth).toFixed(4)})`;
      g.fillRect(0, 0, width, height);
      g.globalCompositeOperation = 'source-over';
    }
    if (lowGfx) {
      const darkAlpha = .44 * nightDepth;
      if (darkAlpha > .002) { g.fillStyle = `rgba(${darkColor},${darkAlpha.toFixed(4)})`; g.fillRect(0, 0, width, height); }
      g.restore(); return;
    }
    if (nightDepth > .002) {
      const vw = Math.max(1, Math.round(width * .5)), vh = Math.max(1, Math.round(height * .5));
      if (!veil) { veil = document.createElement('canvas'); veilG = veil.getContext('2d'); }
      if (veil.width !== vw || veil.height !== vh) { veil.width = vw; veil.height = vh; }
      const v = veilG;
      v.globalCompositeOperation = 'source-over';
      v.clearRect(0, 0, vw, vh);
      v.fillStyle = `rgba(${darkColor},${(.44 * nightDepth).toFixed(4)})`;
      v.fillRect(0, 0, vw, vh);
      const vig = v.createRadialGradient(vw * .5, vh * .5, Math.min(vw, vh) * .34, vw * .5, vh * .5, Math.hypot(vw, vh) * .56);
      vig.addColorStop(0, `rgba(${darkColor},0)`);
      vig.addColorStop(1, `rgba(${darkColor},${(.24 * nightDepth).toFixed(4)})`);
      v.fillStyle = vig; v.fillRect(0, 0, vw, vh);
      if (visibleLights.length || focus?.hero || focus?.target) {
        v.globalCompositeOperation = 'destination-out';
        const cut = (sx, sy, r, peak) => {
          const cx = sx * .5, cy = sy * .5, cr = r * .5;
          const gr = v.createRadialGradient(cx, cy, cr * .08, cx, cy, cr);
          gr.addColorStop(0, `rgba(0,0,0,${peak})`);
          gr.addColorStop(.5, `rgba(0,0,0,${peak * .52})`);
          gr.addColorStop(1, 'rgba(0,0,0,0)');
          v.fillStyle = gr; v.beginPath(); v.arc(cx, cy, cr, 0, Math.PI * 2); v.fill();
        };
        const lightCut = .92 * Math.min(1, n * 1.15);
        for (const [lx, ly] of visibleLights) cut(lx, ly, 120, lightCut);
        if (focus?.hero) cut(focus.hero[0], focus.hero[1] - 34, 195, .36);
        if (focus?.target) cut(focus.target[0], focus.target[1] - 24, 95, .36);
      }
      g.drawImage(veil, 0, 0, width, height);
    }
    if (n > .3) {
      const alpha = n * outdoorBlend * .75;
      g.fillStyle = `rgba(234,246,255,${alpha})`;
      for (let i = 0; i < 28; i++) {
        const x = (i * 619 + 127) % width, y = (i * 137 + 19) % Math.max(1, height * .25);
        g.fillRect(x, y, i % 5 === 0 ? 2 : 1, i % 5 === 0 ? 2 : 1);
      }
    }
    // A zone's own night glow (fades in over its lower part; weight k when two zones mix).
    const nightGlow = (theme, k) => {
      if (n <= .2 || k < .01) return;
      if (theme === 'frostwake') {
        g.fillStyle = `rgba(99,245,204,${.1 * n * outdoorBlend * k})`;
        g.beginPath(); g.ellipse(width * .53, height * .08, width * .42, height * .09, -.13, 0, Math.PI * 2); g.fill();
      } else if (theme === 'ember' || theme === 'emberwake') {
        const gr = g.createLinearGradient(0, height * .6, 0, height);
        gr.addColorStop(0, 'rgba(255,107,44,0)'); gr.addColorStop(1, `rgba(255,107,44,${.11 * n * outdoorBlend * k})`);
        g.fillStyle = gr; g.fillRect(0, height * .6, width, height * .4);
      } else if (['fen', 'worldtree', 'moonspore'].includes(theme)) {
        g.fillStyle = `rgba(127,255,188,${.34 * n * outdoorBlend * k})`;
        for (let i = 0; i < 8; i++) g.fillRect((i * 179 + 43) % width, height * (.55 + (i % 4) * .09), 3, 3);
      }
    };
    nightGlow(zone?.theme, 1 - wN);
    if (sb) nightGlow(sb.theme, wN);
    const daylight = h >= 6 && h < 18;
    const progress = daylight ? (h - 6) / 12 : ((h - 18 + 24) % 24) / 12;
    const orbX = width * (.13 + .74 * progress), orbY = height * (.19 - .11 * Math.sin(progress * Math.PI));
    if (!daylight && n > .15) {
      const mh = g.createRadialGradient(orbX, orbY, 4, orbX, orbY, 34);
      mh.addColorStop(0, `rgba(210,226,255,${(.32 * n * outdoorBlend).toFixed(4)})`);
      mh.addColorStop(1, 'rgba(210,226,255,0)');
      g.fillStyle = mh; g.beginPath(); g.arc(orbX, orbY, 34, 0, Math.PI * 2); g.fill();
    }
    g.globalAlpha = outdoorBlend * (daylight ? .65 : .85 * n);
    g.fillStyle = daylight ? '#fff2b7' : '#edf2ff';
    g.beginPath(); g.arc(orbX, orbY, daylight ? 15 : 11, 0, Math.PI * 2); g.fill();
    const glowAlpha = Math.max(0, n * outdoorBlend * (.58 + .27 * amount));
    if (glowAlpha > .01 && visibleLights.length) {
      const sprite = glowSprite();
      g.globalCompositeOperation = 'lighter';
      g.globalAlpha = glowAlpha;
      for (const [lx, ly] of visibleLights) g.drawImage(sprite, lx - 64, ly - 64);
      g.globalCompositeOperation = 'source-over';
    }
    g.restore();
  }
  window.DayNight = { sync, setZone, tick, draw, isOutdoor, get hour() { return hour(); }, get outdoorBlend() { return outdoorBlend; },
    get nightMix() { return clock.synced && isOutdoor(zone) ? night(hour()) : 0; },
    get shadowOffset() { return isOutdoor(zone) && hour() >= 7 && hour() <= 18 ? (12 - hour()) * 1.4 : 0; } };
})();
