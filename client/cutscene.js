'use strict';
// Crossing cutscenes (CUTSCENE-*, docs/cutscenes.md). The first time a hero climbs up to Bifrost, comes down from it, dives into the sea or
// comes back up, the server sends {type:'cutscene', scenes:[...]} (world/cutscene.rs decides and remembers). This file plays them: a locked
// scene of about six seconds that covers the canvas, paints the real hero (the same drawing the world uses, with the lead shoes put on and
// taken off by the scene), rushes clouds, wind and bubbles past them, shows captions and plays synthesised sounds. Nothing here is sent to
// the server and nothing is played unless a `cutscene` packet arrives, so the file is inert until then. The hero is already at the arrival
// point; the world is hidden behind the scene and fades back in at the end.
(() => {
  const tr = s => window.Locale?.translate(s) || s;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ease = v => { v = clamp(v, 0, 1); return v * v * (3 - 2 * v); };
  const lerp = (a, b, v) => a + (b - a) * v;
  const rnd = i => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const mix = (a, b, v) => `rgb(${a.map((c, i) => Math.round(lerp(c, b[i], v))).join(',')})`;
  const FADE_IN = .35, FADE_OUT = .6;

  // ---- drawing helpers -----------------------------------------------------------------------------------------------------------------
  const vgrad = (g, h, stops) => { const gr = g.createLinearGradient(0, 0, 0, h); stops.forEach(([p, c]) => gr.addColorStop(p, c)); return gr; };
  function puff(g, x, y, r, stretch, alpha) {
    g.save(); g.globalAlpha = alpha; g.translate(x, y); g.scale(1, stretch);
    const lobes = [[0, 0, r, r * .34], [-r * .5, r * .06, r * .55, r * .26], [r * .5, r * .05, r * .6, r * .24]];
    g.fillStyle = 'rgba(150,185,225,.55)';   // the shaded underside
    g.beginPath(); for (const [lx, ly, rx, ry] of lobes) g.ellipse(lx + r * .04, ly + ry * .35, rx, ry, 0, 0, Math.PI * 2); g.fill();
    const gr = g.createRadialGradient(-r * .1, -r * .12, r * .1, 0, 0, r * 1.05); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.7, '#f1f7ff'); gr.addColorStop(1, '#dbe9fa');
    g.fillStyle = gr; g.beginPath(); for (const [lx, ly, rx, ry] of lobes) g.ellipse(lx, ly, rx, ry, 0, 0, Math.PI * 2); g.fill();
    g.restore();
  }
  // Wind or rain-like streaks that move along y at `speed` (px per second of scene distance `s`), longer the faster the scene.
  function streaks(g, w, h, s, v, up, count, colour, seed = 0) {
    g.save(); g.lineCap = 'round';
    for (let i = 0; i < count; i++) {
      const layer = .5 + rnd(i + seed) * 1.5, span = h + 260, dir = up ? -1 : 1;
      const y = (((rnd(i * 3 + seed + 9) * span + dir * s * layer) % span) + span) % span - 130, x = rnd(i * 7 + seed + 3) * w;
      const len = 14 + v * 120 * layer;
      g.globalAlpha = (.12 + rnd(i * 5 + seed) * .35) * clamp(v * 1.6, 0, 1); g.strokeStyle = colour; g.lineWidth = 1 + layer;
      g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - dir * len); g.stroke();
    }
    g.restore();
  }
  function bubbles(g, w, h, el, count, power) {
    g.save(); g.lineWidth = 1.5;
    for (let i = 0; i < count; i++) {
      const u = ((el * (.12 + rnd(i) * .2) + rnd(i * 2 + 1)) % 1), x = rnd(i * 3 + 2) * w + Math.sin(el * 2 + i) * 14, y = h * (1.05 - u * 1.15), r = 2 + rnd(i * 5) * 5;
      g.globalAlpha = (.18 + rnd(i * 9) * .4) * power * Math.sin(Math.PI * clamp(u, 0, 1));
      g.strokeStyle = '#dff8ff'; g.fillStyle = 'rgba(190,235,255,.18)'; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); g.stroke();
    }
    g.restore();
  }
  function rays(g, w, h, el, power) {
    if (power <= .01) return; g.save();
    for (let i = 0; i < 6; i++) {
      const x = w * (.1 + i * .17) + Math.sin(el * .6 + i) * 40, wd = 40 + rnd(i) * 60;
      const gr = g.createLinearGradient(x, 0, x + 80, h); gr.addColorStop(0, `rgba(210,245,255,${.22 * power})`); gr.addColorStop(1, 'rgba(210,245,255,0)');
      g.fillStyle = gr; g.beginPath(); g.moveTo(x - wd * .3, 0); g.lineTo(x + wd * .3, 0); g.lineTo(x + 90 + wd, h); g.lineTo(x + 20, h); g.fill();
    }
    g.restore();
  }
  function ripple(g, x, y, age, w, alpha) {
    if (age < 0 || age > 1.4) return; const k = age / 1.4;
    g.save(); g.globalAlpha = alpha * (1 - k); g.strokeStyle = '#eafcff'; g.lineWidth = 2.5 * (1 - k) + .5;
    g.beginPath(); g.ellipse(x, y, 20 + k * w, (20 + k * w) * .28, 0, 0, Math.PI * 2); g.stroke(); g.restore();
  }
  function droplets(g, x, y, age, count, power) {
    if (age < 0 || age > 1.3) return; g.save(); g.fillStyle = '#e9fbff';
    for (let i = 0; i < count; i++) {
      const a = -Math.PI / 2 + (rnd(i) - .5) * 2.1, sp = 120 + rnd(i * 3) * 220 * power, px = x + Math.cos(a) * sp * age, py = y + Math.sin(a) * sp * age + 520 * age * age;
      g.globalAlpha = clamp(1 - age / 1.3, 0, 1) * .9; g.beginPath(); g.arc(px, py, 2.2 + rnd(i * 7) * 2.4, 0, Math.PI * 2); g.fill();
    }
    g.restore();
  }
  function boot(g, x, y, rot, alpha = 1) {
    g.save(); g.translate(x, y); g.rotate(rot); g.globalAlpha = alpha; g.lineJoin = 'round'; g.lineWidth = 2;
    const gr = g.createLinearGradient(0, -9, 0, 3); gr.addColorStop(0, '#9aa6b8'); gr.addColorStop(.55, '#5d6778'); gr.addColorStop(1, '#3a4150');
    g.fillStyle = gr; g.strokeStyle = '#1f2430';
    g.beginPath(); g.moveTo(-7, 3); g.lineTo(-7, -6); g.quadraticCurveTo(-6, -9, -2, -9); g.lineTo(2, -9); g.quadraticCurveTo(5, -8, 8, -4); g.quadraticCurveTo(11, 0, 8, 3); g.closePath(); g.fill(); g.stroke();
    g.fillStyle = '#2b313e'; g.fillRect(-7, 0, 15, 3); g.restore();
  }
  function sand(g, w, h, top, alpha = 1) {
    g.save(); g.globalAlpha = alpha; const gr = g.createLinearGradient(0, top, 0, h); gr.addColorStop(0, '#8d8460'); gr.addColorStop(1, '#4d4a3a');
    g.fillStyle = gr; g.beginPath(); g.moveTo(0, top + 10); for (let x = 0; x <= w; x += 40) g.lineTo(x, top + Math.sin(x * .02) * 6 + 4); g.lineTo(w, h); g.lineTo(0, h); g.closePath(); g.fill();
    for (let i = 0; i < 7; i++) { const x = rnd(i + 40) * w, y = top + 18 + rnd(i + 70) * (h - top) * .5; g.fillStyle = '#5b5845'; g.beginPath(); g.ellipse(x, y, 14 + rnd(i) * 18, 7 + rnd(i) * 6, 0, 0, Math.PI * 2); g.fill(); }
    g.restore();
  }
  function kelp(g, w, top, el, alpha) {
    g.save(); g.globalAlpha = alpha; g.strokeStyle = '#2c6b4f'; g.lineWidth = 6; g.lineCap = 'round';
    for (let i = 0; i < 6; i++) { const x = rnd(i + 11) * w, hh = 70 + rnd(i + 5) * 90; g.beginPath(); g.moveTo(x, top + 10); for (let k = 1; k <= 5; k++) g.lineTo(x + Math.sin(el * 1.4 + i + k * .8) * (k * 5), top + 10 - hh * k / 5); g.stroke(); }
    g.restore();
  }

  // ---- the four scenes -----------------------------------------------------------------------------------------------------------------
  // Each `draw(c)` paints the backdrop and returns the hero's pose {dx, dy, sx, sy, rot, shoes}; the last moment is the identity pose, so the
  // hero is exactly where the world has them when the scene fades out. c = { g, w, h, el, hx, hy, still }.
  const IDENT = { dx: 0, dy: 0, sx: 1, sy: 1, rot: 0 };
  // Distance travelled when the speed profile v(el) is integrated (the scene is short; a fine fixed step is plenty).
  const travelled = (v, el) => { let s = 0; for (let t = 0; t < el; t += 1 / 40) s += v(t) / 40; return s; };

  const updraft = up => {
    const dur = up ? 6 : 5.6;
    const v = el => up
      ? (el < .9 ? ease(el / .9) : el < 4.2 ? 1 : el < 5.5 ? lerp(1, .12, ease((el - 4.2) / 1.3)) : .12)
      : (el < .6 ? .2 + ease(el / .6) * .8 : el < 3.6 ? 1 : el < 4.6 ? lerp(1, .5, ease((el - 3.6) / 1)) : .5 * (1 - ease((el - 4.6) / .4)));
    return {
      id: up ? 'sky_up' : 'sky_down', dur,
      captions: up ? [[.2, 'The updraft catches you!'], [2.3, 'Faster and faster!'], [4.5, 'Bifrost Reach, high above the clouds.']]
        : [[.2, 'You let go of the sky.'], [2.4, 'The ground rushes up to meet you.'], [4.6, 'A soft landing.']],
      sounds: up ? [[0, 'rush_up']] : [[0, 'rush_down'], [4.55, 'thud']],
      shoes: () => false,
      draw(c) {
        const { g, w, h, el, hx, hy } = c, sp = v(el), s = travelled(v, el) * 520;
        // Sky: from ground haze to deep daylight blue when climbing, the other way when falling.
        const alt = up ? ease(el / 5.2) : 1 - ease(el / 4.4);
        g.fillStyle = vgrad(g, h, [[0, mix([150, 200, 240], [30, 70, 160], alt)], [1, mix([225, 242, 255], [150, 205, 250], alt)]]); g.fillRect(0, 0, w, h);
        // Cloud banks stream past, stretched along the way they move.
        for (let layer = 0; layer < 3; layer++) for (let i = 0; i < 7; i++) {
          const span = h + 420, dir = up ? 1 : -1, k = .5 + layer * .55;
          const y = (((rnd(i * 13 + layer * 29) * span + dir * s * k) % span) + span) % span - 210, x = rnd(i * 17 + layer * 5) * (w + 200) - 100 + Math.sin(el + i) * 10;
          puff(g, x, y, 90 + layer * 50 + rnd(i) * 70, 1 + sp * (1.6 + layer * .6), .55 + layer * .15);
        }
        streaks(g, w, h, s, sp, !up, 70, up ? '#ffffff' : '#e8f4ff');
        // The ground comes up to meet a falling hero, and islands drift by below a climbing one at the end.
        if (!up) {
          const rise = ease((el - 2.6) / 1.9);
          if (rise > 0) {
            const top = lerp(h + 60, hy + 8, rise); g.save(); g.fillStyle = vgrad(g, h, [[0, '#7fbf6a'], [1, '#3e7d3a']]);
            g.beginPath(); g.ellipse(w / 2, top + Math.max(0, h - top) * 1.6, w * lerp(1.6, 1.15, rise), Math.max(2, (h - top) * 1.7 + 20), 0, 0, Math.PI * 2); g.fill();
            g.fillStyle = 'rgba(255,255,255,.06)'; for (let i = 0; i < 9; i++) g.fillRect(rnd(i) * w, top + rnd(i * 3) * (h - top), 30, 3); g.restore();
          }
          ripple(g, hx, hy + 6, el - 4.55, 170, .6);
        } else {
          for (let i = 0; i < 3; i++) {
            const k = ease((el - 4.2 - i * .25) / 1.6); if (k <= 0 || k >= 1) continue;
            g.save(); g.globalAlpha = (1 - k) * .55; g.fillStyle = '#3d6f7d'; g.beginPath(); g.ellipse(w * (.2 + i * .3), lerp(h + 60, h * .72, k), 90 + i * 24, 18, 0, 0, Math.PI * 2); g.fill(); g.restore();
          }
        }
        // A spiral of leaves winds round the hero as the updraft takes hold.
        const spiral = up ? clamp(1 - Math.abs(el - .7) / 1.4, 0, 1) : 0;
        if (spiral > 0) for (let i = 0; i < 16; i++) {
          const a = el * 5 + i * .6, r = 30 + i * 6, y = hy - 30 - i * 9 + Math.sin(a) * 4;
          g.save(); g.globalAlpha = spiral * .9; g.fillStyle = i % 3 ? '#9ddc6b' : '#f0d36b'; g.translate(hx + Math.cos(a) * r, y); g.rotate(a); g.beginPath(); g.ellipse(0, 0, 6, 3, 0, 0, Math.PI * 2); g.fill(); g.restore();
        }
        // The flash when the climb ends or the fall begins.
        c.flash = up ? clamp(1 - Math.abs(el - 5.3) / .35, 0, 1) * .75 : clamp(1 - el / .55, 0, 1) * .8;
        c.shake = c.still ? 0 : up ? (el > .8 && el < 4.4 ? 2.2 : 0) : (el < 3.8 ? 1.4 : clamp((4.9 - el) / .35, 0, 1) * 5 * (el > 4.55 ? 1 : 0));
        // The hero: stretched and tilted at speed, hovering, then settling back.
        if (up) {
          const lift = ease(el / .9) * (1 - ease((el - 4.2) / 1.3));
          return { dx: 0, dy: -34 * lift + Math.sin(el * 3) * 2 * lift, sx: 1 - .06 * lift, sy: 1 + .1 * lift, rot: Math.sin(el * 2.1) * .05 * lift };
        }
        const fall = clamp(el / .5, 0, 1) * (1 - ease((el - 3.9) / .7));
        const squash = el > 4.55 ? Math.sin(clamp((el - 4.55) / .5, 0, 1) * Math.PI) * .12 : 0;
        return { dx: 0, dy: -38 * fall, sx: 1 - .05 * fall + squash, sy: 1 + .1 * fall - squash, rot: Math.sin(el * 2.6) * .07 * fall };
      },
    };
  };

  const dive = {
    id: 'dive', dur: 6.5,
    captions: [[.35, 'Equipping lead shoes'], [2.1, 'You plunge into the sea!'], [3.5, 'Down, down, down...'], [5.55, 'You touch the seabed.']],
    sounds: [[.5, 'clank'], [1.85, 'splash'], [2.0, 'bubbles'], [5.6, 'thud']],
    shoes: el => el > .5,
    draw(c) {
      const { g, w, h, el, hx, hy } = c, surfaceY = hy + 64, fall = el - 1.2, splashAt = 1.2 + Math.sqrt(2 * 64 / 560);
      const depth = ease((el - 1.9) / 3.4), sink = ease((el - 1.9) / 2.6) * (h + 120);
      const sy0 = surfaceY - sink;   // where the surface line sits once the camera follows the hero down
      // Above the water: sky, then the surface line sliding up out of view as the hero sinks.
      g.fillStyle = mix([40, 150, 205], [6, 26, 52], depth); g.fillRect(0, 0, w, h);
      if (sy0 > -40) {
        g.fillStyle = vgrad(g, Math.max(sy0, 1), [[0, '#79c4f4'], [1, '#def3ff']]); g.fillRect(0, 0, w, Math.max(0, sy0));
        g.save(); g.strokeStyle = 'rgba(255,255,255,.55)'; g.lineWidth = 2; g.beginPath();
        for (let x = 0; x <= w; x += 18) g.lineTo(x, sy0 + Math.sin(x * .05 + el * 3) * 2.4); g.stroke(); g.restore();
        if (el < 2) { // the pier plank the hero stands on, dropping away
          const drop = clamp(fall, 0, 1); g.save(); g.translate(hx, hy + 5 + Math.max(0, fall) * 120 * drop); g.rotate(drop * .5);
          g.fillStyle = '#8a6a43'; g.strokeStyle = '#4a3622'; g.lineWidth = 2; g.fillRect(-48, -4, 96, 10); g.strokeRect(-48, -4, 96, 10); g.restore();
        }
      }
      rays(g, w, h, el, (1 - depth) * clamp((el - 1.9) / .6, 0, 1));
      bubbles(g, w, h, el, 38, clamp((el - 1.9) / .6, 0, 1) * (1 - ease((el - 5.4) / .4)));
      droplets(g, hx, sy0, el - splashAt, 34, 1); ripple(g, hx, sy0, el - splashAt, 220, .8); ripple(g, hx, sy0, el - splashAt - .15, 150, .5);
      // The seabed rises under the hero at the end.
      const bed = ease((el - 4.6) / 1.0); if (bed > 0) { const top = lerp(h + 20, hy + 6, bed); sand(g, w, h, top); kelp(g, w, top, el, .9); }
      c.veil = el > splashAt ? .22 * (1 - ease((el - 5.2) / .6)) : 0;
      c.flash = clamp(1 - Math.abs(el - .5) / .12, 0, 1) * .35 + clamp(1 - Math.abs(el - splashAt) / .16, 0, 1) * .6;
      c.shake = c.still ? 0 : (el > splashAt && el < splashAt + .55 ? 6 * (1 - (el - splashAt) / .55) : 0) + (el > 5.6 && el < 5.95 ? 3.5 * (1 - (el - 5.6) / .35) : 0);
      // Hero: stands, drops with the plank, then sinks swaying, then stands on the sand.
      if (el < splashAt) return { dx: 0, dy: fall > 0 ? Math.min(64, 560 * fall * fall / 2) : 0, sx: 1, sy: 1, rot: fall > 0 ? .25 * clamp(fall / .5, 0, 1) : 0 };
      const settle = ease((el - 5.2) / .6), sway = Math.sin(el * 1.8) * (1 - settle);
      const into = ease((el - splashAt) / .5);
      return { dx: sway * 10, dy: lerp(64, 30, into) * (1 - settle) + Math.sin(el * 2.3) * 4 * (1 - settle), sx: 1, sy: 1, rot: .25 * (1 - into) * (1 - settle) + sway * .09 };
    },
  };

  const surface = {
    id: 'surface', dur: 6.2,
    captions: [[.3, 'Removing lead shoes'], [2.0, 'You float up towards the light.'], [4.85, 'You break the surface!']],
    sounds: [[.4, 'clank'], [.9, 'bubbles'], [4.85, 'splash']],
    shoes: el => el < .6,
    draw(c) {
      const { g, w, h, el, hx, hy } = c, rise = ease((el - 1.2) / 3.7), breachAt = 4.85;
      const light = ease((el - 1.2) / 3.4);
      g.fillStyle = mix([6, 26, 52], [48, 150, 205], light); g.fillRect(0, 0, w, h);
      const surfaceY = lerp(-120, hy + 22, ease((el - 3.7) / 1.15));   // the surface line comes down to meet the hero
      if (el > 3.7) {
        g.fillStyle = vgrad(g, Math.max(surfaceY, 1), [[0, '#8fd3fa'], [1, '#e6f6ff']]); g.fillRect(0, 0, w, Math.max(0, surfaceY - 2));
        g.save(); g.strokeStyle = 'rgba(255,255,255,.6)'; g.lineWidth = 2; g.beginPath(); for (let x = 0; x <= w; x += 18) g.lineTo(x, surfaceY + Math.sin(x * .05 + el * 3) * 2.4); g.stroke(); g.restore();
      }
      // The seabed sinks away behind a rising hero; the two shoes lie where they fell.
      const bedTop = hy + 6 + rise * h * 1.4;
      if (bedTop < h + 40) { sand(g, w, h, bedTop); kelp(g, w, bedTop, el, .9); }
      const fell = clamp((el - .55) / .5, 0, 1);
      if (fell > 0 && bedTop < h + 40) for (const side of [-1, 1]) {
        const x = hx + side * (14 + fell * 34), y = lerp(hy - 6, bedTop + 4, ease(fell));
        boot(g, x, y, side * (.3 + fell * 1.1));
      }
      rays(g, w, h, el, light * clamp(1 - (el - 4.4) / .6, 0, 1));
      bubbles(g, w, h, el, 40, clamp((el - .8) / .6, 0, 1) * (1 - ease((el - 5.4) / .5)));
      droplets(g, hx, surfaceY, el - breachAt, 34, 1); ripple(g, hx, surfaceY, el - breachAt, 220, .8); ripple(g, hx, surfaceY, el - breachAt - .15, 150, .5);
      c.veil = el < breachAt ? .22 : .22 * (1 - ease((el - breachAt) / .5));
      c.flash = clamp(1 - Math.abs(el - breachAt) / .15, 0, 1) * .6;
      c.shake = c.still ? 0 : (el > breachAt && el < breachAt + .5 ? 5 * (1 - (el - breachAt) / .5) : 0);
      // Hero: stands with shoes, then floats up (the world scrolls down), then pops out of the surface and settles.
      const float = ease((el - 1.2) / .8) * (1 - ease((el - breachAt) / .9)), pop = el > breachAt ? Math.sin(clamp((el - breachAt) / .9, 0, 1) * Math.PI) * 26 : 0;
      return { dx: Math.sin(el * 1.7) * 9 * float, dy: -22 * float + Math.sin(el * 2.2) * 4 * float - pop, sx: 1, sy: 1, rot: Math.sin(el * 1.7) * .1 * float };
    },
  };

  const SCENES = { sky_up: updraft(true), sky_down: updraft(false), dive, surface };

  // ---- sounds (synthesised, through the game's effect bus so mute and volume apply) ---------------------------------------------------------
  const sound = (kind, delay) => { try { window.CutsceneAudio?.play(kind, delay); } catch { /* sound is a nicety */ } };

  // ---- the player ---------------------------------------------------------------------------------------------------------------------
  let queue = [], cur = null, curSkip = false, holdStart = null, lastFrame = 0, startAt = 0, box = null, caption = null, skipHint = null, lastCaption = -1, locked = false, shown = 0, shoeState = false, layer = null, view = null;
  // Browser shortcuts (reload, dev tools, zoom) still work; every game key is swallowed before any other handler sees it.
  // A scene the player may skip (the opening, from the second character on) is skipped by holding any key or a finger on it for a second.
  const blockKey = e => {
    if (e.ctrlKey || e.metaKey || /^F\d+$/.test(e.key || '')) return;
    if (curSkip) { if (e.type === 'keydown' && holdStart === null) holdStart = performance.now(); else if (e.type === 'keyup') holdStart = null; }
    e.preventDefault(); e.stopImmediatePropagation();
  };
  // Recorded narration uses the same audio context/effects bus as the scene.
  const hush = () => window.CutsceneAudio?.stopNarration();
  function lock(on) {
    if (on === locked) return; locked = on;
    for (const type of ['keydown', 'keyup', 'keypress']) (on ? addEventListener : removeEventListener)(type, blockKey, true);
    if (on) window.Field?.cutsceneBegin?.();
  }
  function build() {
    if (box) return box;
    const stage = document.getElementById('stage') || document.body;
    box = document.createElement('div'); box.id = 'cutscene'; box.className = 'cutscene'; box.hidden = true; box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite');
    box.innerHTML = '<canvas class="cs-view"></canvas><i class="cs-bar cs-top"></i><i class="cs-bar cs-bottom"></i><p class="cs-caption"></p><p class="cs-skip" hidden></p>';
    box.addEventListener('pointerdown', () => { if (curSkip && holdStart === null) holdStart = performance.now(); });
    for (const type of ['pointerup', 'pointercancel', 'pointerleave']) box.addEventListener(type, () => { holdStart = null; });
    for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click', 'dblclick', 'contextmenu', 'touchstart', 'touchmove', 'wheel']) box.addEventListener(type, e => { e.preventDefault(); e.stopPropagation(); }, { passive: false });
    stage.append(box); caption = box.querySelector('.cs-caption'); skipHint = box.querySelector('.cs-skip'); view = box.querySelector('.cs-view'); return box;
  }
  function begin(id, skippable) {
    hush();
    cur = SCENES[id]; curSkip = !!skippable; holdStart = null; lastFrame = performance.now(); startAt = performance.now(); lastCaption = -1; shown++;
    window.CutsceneAudio?.prepareNarration(cur.narration || []);
    cur.fired = new Set(); build().hidden = false; box.dataset.scene = id; box.classList.add('on'); caption.textContent = ''; caption.classList.remove('on'); skipHint.hidden = true;
    // The zone change reaches the client before this packet, so the plain "Ascending into the sky" notice may already be up: the scene tells it instead.
    window.ZoneJourney?.clear?.();
    lock(true);
  }
  function finish() {
    cur = null; curSkip = false; holdStart = null; queue = []; lock(false); hush();
    if (box) { box.classList.remove('on'); box.hidden = true; delete box.dataset.scene; if (caption) caption.textContent = ''; }
  }
  function next() { const e = queue.shift(); if (e) begin(e.id, e.skippable); else finish(); }

  // `opts.skippable` lets the player skip these scenes (the server says so for the opening cutscene of a second character).
  function play(scenes, opts) {
    const ids = (Array.isArray(scenes) ? scenes : []).filter(id => SCENES[id]);
    if (!ids.length) return;
    const idle = !cur; queue.push(...ids.map(id => ({ id, skippable: !!opts?.skippable })));
    if (idle) next();
  }
  // Further scenes (the opening, client/intro.js) join the table the same way the four crossings are written.
  const register = (id, scene) => { SCENES[id] = { id, ...scene }; };
  function reset() { finish(); }

  function draw(g, w, h, t, paintHero, hx, hy, hero, still) {
    if (!cur) return;
    let el = (performance.now() - startAt) / 1000;
    if (el >= cur.dur) { next(); if (!cur) return; el = (performance.now() - startAt) / 1000; }
    const now = performance.now(), dt = clamp((now - lastFrame) / 1000, 0, .1); lastFrame = now;
    // Holding a key or a finger on a skippable scene for a second ends it (and the rest of the queue).
    if (curSkip) {
      const held = holdStart === null ? 0 : (now - holdStart) / 1000;
      if (held >= 1) { finish(); return; }
      skipHint.hidden = el < 2.5; skipHint.textContent = tr(held > 0 ? 'Skipping...' : 'Hold a key or your finger to skip'); skipHint.style.setProperty('--skip', String(held));
    }
    const S = cur, c = { g, w, h, el, dt, hx, hy, still: !!still, flash: 0, shake: 0 };
    // Captions and sounds fire once, in order.
    for (const [index, [at, text, hold]] of S.captions.entries()) if (el >= at && lastCaption < at) {
      lastCaption = at; caption.textContent = tr(text); caption.style.animationDuration = (hold || 2.6) + 's'; caption.classList.remove('on'); void caption.offsetWidth; caption.classList.add('on');
      if (S.narration?.[index]) window.CutsceneAudio?.narrate(S.narration[index], el - at);
    }
    S.sounds.forEach(([at, kind], i) => { if (el >= at && !S.fired.has(i)) { S.fired.add(i); sound(kind, 0); } });
    const fi = S.fadeIn ?? FADE_IN, fo = S.fadeOut ?? FADE_OUT, fadeIn = ease(el / fi), fadeOut = 1 - ease((el - (S.dur - fo)) / fo), cover = Math.min(fadeIn, fadeOut);
    // The backdrop is painted on its own layer (the helpers set the alpha themselves), so the fades only blend the scene with the world.
    layer ||= document.createElement('canvas');
    if (layer.width !== w || layer.height !== h) { layer.width = w; layer.height = h; }
    const lg = layer.getContext('2d'); lg.setTransform(1, 0, 0, 1, 0, 0); lg.globalAlpha = 1; lg.clearRect(0, 0, w, h);
    c.g = lg;
    const pose = S.draw(c) || IDENT;
    g.save(); g.globalAlpha = cover; g.drawImage(layer, 0, 0); g.restore();
    g.save();
    if (c.shake) g.translate((Math.random() - .5) * c.shake * 2, (Math.random() - .5) * c.shake * 2);
    const mounted = hero.mounted; hero.mounted = false;
    const hold = S.shoes(el), walk = hero.walk, moving = hero.moving, fx = hero.fx, fy = hero.fy;
    if (!pose.hidden) {
      // A close-up: the hero grows about their feet while the scene plays and settles back to life size for the fade-out. A scene that sets
      // `pose.abs` places the hero on its own camera instead (the opening), and `pose.walk` makes them walk that way.
      const zoom = S.noZoom ? 1 : 1 + .5 * ease(el / .7) * (1 - ease((el - (S.dur - 1.0)) / .8));
      if (pose.abs) g.translate(pose.abs.x, pose.abs.y), g.scale(pose.abs.k, pose.abs.k);
      else g.translate(hx + (pose.dx || 0), hy + (pose.dy || 0)), g.scale(zoom * (pose.sx ?? 1), zoom * (pose.sy ?? 1)), g.translate(0, -45), g.rotate(pose.rot || 0), g.translate(0, 45);
      g.globalAlpha = pose.alpha ?? 1;
      if (pose.walk) { hero.moving = true; hero.fx = pose.walk[0]; hero.fy = pose.walk[1]; hero.walk = (walk || 0) + dt * 11; }
      else if (pose.abs) hero.moving = false;
      shoeState = hold; try { paintHero(g, t); } finally { hero.mounted = mounted; if (!pose.walk) hero.walk = walk; hero.moving = moving; hero.fx = fx; hero.fy = fy; }
    } else hero.mounted = mounted;
    g.restore();
    if (c.veil > 0) { g.save(); g.globalAlpha = c.veil * cover; g.fillStyle = '#1b6fb0'; g.fillRect(0, 0, w, h); g.restore(); }
    if (c.flash > 0 && !still) { g.save(); g.globalAlpha = clamp(c.flash, 0, 1) * cover; g.fillStyle = '#f4fcff'; g.fillRect(0, 0, w, h); g.restore(); }
    // The finished frame is shown on an opaque canvas inside the overlay, which covers the HUD pieces drawn as page elements.
    if (view) { if (view.width !== w || view.height !== h) { view.width = w; view.height = h; } view.getContext('2d').drawImage(g.canvas, 0, 0, g.canvas.width, g.canvas.height, 0, 0, w, h); }
  }
  window.Cutscene = {
    play, reset, draw, register, clamp, ease, lerp, rnd,
    get active() { return !!cur; },
    shoes() { return shoeState; },
    // For tests: what is playing and how far along it is.
    get state() { return cur ? { scene: cur.id, el: (performance.now() - startAt) / 1000, dur: cur.dur, queued: queue.map(e => e.id), played: shown, skippable: curSkip } : null; },
    scenes: Object.fromEntries(Object.entries(SCENES).map(([k, v]) => [k, v.dur])),
  };
})();
