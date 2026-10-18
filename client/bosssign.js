'use strict';
// The sign before a final boss (docs/boss-mechanics.md, BOSSMECH-SIGN-ENGINE). The server owns the words: `Field` asks to
// read the sign with `sign_read`, and this draws whatever the answer says in a small window that does not pause the
// game. Esc, the cross, the Close button and walking away close it. The picture strip uses the four telegraph colours
// of `BossMech`, so a sign and the fight it explains speak the same language.
(() => {
  const $ = id => document.getElementById(id);
  const RANGE = 2.8 + .4;      // the server's reach plus a margin, so a rounding difference never closes the window
  const CAPTIONS = {
    red: 'Red hurts.',
    blue: 'Blue is safe.',
    path: 'A dashed line is a path that is about to be used.',
    green: 'Green is the way through.',
  };
  let current = null, previousFocus = null, watch = 0;
  const isOpen = () => !$('sign-panel').hidden;
  const svg = (tag, attrs) => { const n = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const k in attrs) n.setAttribute(k, attrs[k]); return n; };

  // A boss's red panel sketches its actual floor pattern; the other panels explain the shared colour language.
  function picture(color, sign) {
    const hex = window.BossMech?.colors?.[color] || '#fff';
    const art = svg('svg', { viewBox: '0 0 64 40', width: 64, height: 40, 'aria-hidden': 'true', focusable: 'false' });
    if (color === 'red') {
      const blue = window.BossMech?.colors?.blue || '#3f9bea';
      const green = window.BossMech?.colors?.green || '#4fc26b';
      const path = window.BossMech?.colors?.path || '#f1e3b4';
      if (sign === 'hierophant') {
        art.append(svg('rect', { x: 2, y: 2, width: 60, height: 36, rx: 3, fill: hex, 'fill-opacity': .55 }));
        for (const [x, y] of [[14, 12], [42, 13], [32, 30]]) art.append(svg('circle', { cx: x, cy: y, r: 8, fill: blue, 'fill-opacity': .8, stroke: blue, 'stroke-width': 2 }));
        return art;
      }
      if (sign === 'moonwell_echo') {
        art.append(svg('line', { x1: 4, y1: 7, x2: 60, y2: 32, stroke: hex, 'stroke-width': 8, 'stroke-opacity': .7 }));
        art.append(svg('line', { x1: 4, y1: 7, x2: 60, y2: 32, stroke: path, 'stroke-width': 2, 'stroke-dasharray': '5 4' }));
        art.append(svg('circle', { cx: 47, cy: 12, r: 7, fill: 'none', stroke: hex, 'stroke-width': 2 }));
        return art;
      }
      if (sign === 'elder_heart') {
        for (const x of [12, 52]) {
          art.append(svg('line', { x1: x, y1: 2, x2: x, y2: 15, stroke: hex, 'stroke-width': 5 }));
          art.append(svg('line', { x1: x, y1: 25, x2: x, y2: 38, stroke: hex, 'stroke-width': 5 }));
          art.append(svg('line', { x1: x, y1: 16, x2: x, y2: 24, stroke: green, 'stroke-width': 5 }));
        }
        art.append(svg('line', { x1: 18, y1: 20, x2: 46, y2: 20, stroke: path, 'stroke-width': 2, 'stroke-dasharray': '4 3' }));
        return art;
      }
      if (sign === 'pavilion_sovereign') {
        art.append(svg('polygon', { points: '2,2 45,2 19,38 2,38', fill: hex, 'fill-opacity': .7 }));
        art.append(svg('line', { x1: 45, y1: 2, x2: 19, y2: 38, stroke: path, 'stroke-width': 3, 'stroke-dasharray': '5 4' }));
        return art;
      }
      if (sign === 'rain_crown_sovereign') {
        for (const [x, y] of [[13, 14], [34, 14], [47, 28]]) {
          art.append(svg('circle', { cx: x, cy: y, r: 10, fill: hex, 'fill-opacity': .35, stroke: hex, 'stroke-width': 2 }));
          art.append(svg('circle', { cx: x, cy: y, r: 2, fill: '#f8e8c6' }));
        }
        return art;
      }
      if (sign === 'eye_unblinking') {
        art.append(svg('circle', { cx: 32, cy: 20, r: 5, fill: hex }));
        for (const [x, y] of [[17, 10], [47, 10], [17, 30], [47, 30]]) {
          art.append(svg('circle', { cx: x, cy: y, r: 5, fill: blue, stroke: '#d9e8db', 'stroke-width': 2 }));
        }
        for (const [x, y] of [[5, 20], [59, 20]]) art.append(svg('line', { x1: 32, y1: 20, x2: x, y2: y, stroke: hex, 'stroke-width': 2 }));
        return art;
      }
      if (sign === 'astro_axis') {
        art.append(svg('circle', { cx: 32, cy: 20, r: 5, fill: '#e9ce87' }));
        for (const a of [-Math.PI / 2, Math.PI / 6, Math.PI * 5 / 6]) {
          art.append(svg('line', { x1: 32, y1: 20, x2: 32 + Math.cos(a) * 28, y2: 20 + Math.sin(a) * 17, stroke: hex, 'stroke-width': 5, 'stroke-linecap': 'round' }));
        }
        return art;
      }
    }
    if (color === 'red') art.append(svg('circle', { cx: 32, cy: 20, r: 16, fill: hex, 'fill-opacity': .5, stroke: hex, 'stroke-width': 3 }));
    else if (color === 'blue') art.append(svg('circle', { cx: 32, cy: 20, r: 15, fill: 'none', stroke: hex, 'stroke-width': 4 }), svg('circle', { cx: 32, cy: 20, r: 6, fill: hex, 'fill-opacity': .45 }));
    else if (color === 'path') art.append(svg('line', { x1: 6, y1: 32, x2: 58, y2: 8, stroke: hex, 'stroke-width': 4, 'stroke-dasharray': '8 6', 'stroke-linecap': 'round' }));
    else art.append(svg('rect', { x: 4, y: 14, width: 20, height: 12, fill: '#6b5a3a' }), svg('rect', { x: 40, y: 14, width: 20, height: 12, fill: '#6b5a3a' }), svg('rect', { x: 24, y: 14, width: 16, height: 12, fill: hex, 'fill-opacity': .6, stroke: hex, 'stroke-width': 2 }));
    return art;
  }
  function show(packet) {
    previousFocus = document.activeElement;
    $('sign-title').textContent = packet.title;
    for (const part of ['what', 'todo', 'tip']) $('sign-' + part).textContent = packet[part];
    const strip = $('sign-pictures');
    strip.replaceChildren(...packet.colors.map(color => {
      const figure = document.createElement('figure'); figure.dataset.color = color;
      const caption = document.createElement('figcaption'); caption.textContent = CAPTIONS[color] || '';
      figure.append(picture(color, packet.sign), caption); return figure;
    }));
    $('sign-panel').hidden = false;
    clearInterval(watch); watch = setInterval(() => { if (!stillNear()) close(); }, 250);
    $('sign-close').focus({ preventScroll: true });
  }
  // The window belongs to one sign. It closes when the hero is defeated, walks away or disconnects.
  function stillNear() {
    const hero = window.Field?.hero;
    if (!hero || hero.dead || !window.Online?.connected || !current) return false;
    return Math.hypot(hero.x - current.x, hero.y - current.y) <= RANGE;
  }
  function onPacket(packet) {
    const sign = window.Field?.signs?.find(s => s.id === packet.sign);
    if (!sign) return;
    current = sign;
    show(packet);
  }
  function close(resume = true) {
    if (!isOpen()) return;
    clearInterval(watch); $('sign-panel').hidden = true; current = null;
    if (resume) previousFocus?.focus?.({ preventScroll: true });
  }
  $('sign-x').addEventListener('click', () => close());
  $('sign-close').addEventListener('click', () => close());
  // Escape closes the window; the other keys still reach the game, so a hero can simply walk away.
  addEventListener('keydown', event => {
    if (isOpen() && event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
  }, true);

  window.BossSign = { onPacket, close, reset: () => close(false), get visible() { return isOpen(); } };
})();
