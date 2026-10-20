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
      if (sign === 'barrow_fatebound') {
        art.append(svg('circle', { cx:32, cy:20, r:13, fill:'none', stroke:hex, 'stroke-width':9, 'stroke-opacity':.75 }));
        art.append(svg('circle', { cx:32, cy:20, r:4, fill:'#e8d5a3', 'fill-opacity':.8 }));
        return art;
      }
      if (sign === 'span_archon') {
        art.append(svg('polygon', { points: '12,20 56,5 56,35', fill: hex, 'fill-opacity': .68, stroke: hex, 'stroke-width': 2 }));
        art.append(svg('circle', { cx: 12, cy: 20, r: 5, fill: '#fff4c8', stroke: '#7ddfff', 'stroke-width': 2 }));
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
      if (sign === 'choirmother') {         // the bell's circle, and four singers waiting outside it
        art.append(svg('circle', { cx: 32, cy: 20, r: 15, fill: hex, 'fill-opacity': .5, stroke: hex, 'stroke-width': 3 }));
        for (const [x, y] of [[6, 6], [58, 6], [6, 34], [58, 34]]) art.append(svg('circle', { cx: x, cy: y, r: 4, fill: '#aef0e6', stroke: '#2d5a62', 'stroke-width': 1.5 }));
        return art;
      }
      if (sign === 'seed_worldseed') {      // three seeds, each ringed by a red clock that fills until it blooms
        for (const [x, y, k] of [[13, 14, .75], [34, 12, .45], [48, 29, .9]]) {
          art.append(svg('circle', { cx: x, cy: y, r: 9, fill: 'none', stroke: hex, 'stroke-opacity': .3, 'stroke-width': 3 }));
          art.append(svg('circle', { cx: x, cy: y, r: 9, fill: 'none', stroke: hex, 'stroke-width': 3, 'stroke-dasharray': (56.5 * k) + ' 60', transform: ['rotate(-90', x, y].join(' ') + ')' }));
          art.append(svg('circle', { cx: x, cy: y, r: 3.5, fill: '#e9d78e' }));
        }
        return art;
      }
      if (sign === 'thunder_heart') {       // the red circle round a hero who has too many sparks
        art.append(svg('circle', { cx: 32, cy: 20, r: 16, fill: hex, 'fill-opacity': .4, stroke: hex, 'stroke-width': 3 }));
        art.append(svg('polyline', { points: '35,8 27,22 33,22 29,33', fill: 'none', stroke: '#fff1a8', 'stroke-width': 3, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
        return art;
      }
      if (sign === 'bloom_heart') {         // a marked friend with a ring, and the beam leaving them
        art.append(svg('polyline', { points: '10,30 34,6 58,30', fill: 'none', stroke: hex, 'stroke-width': 4, 'stroke-opacity': .75, 'stroke-linejoin': 'round' }));
        art.append(svg('circle', { cx: 10, cy: 30, r: 7, fill: 'none', stroke: hex, 'stroke-width': 2 }));
        art.append(svg('circle', { cx: 10, cy: 30, r: 2, fill: '#f8e8c6' }));
        return art;
      }
      if (sign === 'solar_heart') {         // Sol, Cinder and the red line between them
        art.append(svg('line', { x1: 14, y1: 20, x2: 50, y2: 20, stroke: hex, 'stroke-width': 6, 'stroke-opacity': .8 }));
        art.append(svg('circle', { cx: 10, cy: 20, r: 8, fill: '#ffcf6c' }));
        art.append(svg('circle', { cx: 54, cy: 20, r: 8, fill: '#c8b6ab' }));
        return art;
      }
      if (sign === 'amber_memory') {        // an orb on its way, and a friend inside an amber cocoon
        art.append(svg('circle', { cx: 12, cy: 12, r: 5, fill: hex, 'fill-opacity': .8 }));
        art.append(svg('line', { x1: 3, y1: 4, x2: 9, y2: 9, stroke: hex, 'stroke-width': 2, 'stroke-opacity': .5 }));
        art.append(svg('ellipse', { cx: 44, cy: 22, rx: 11, ry: 15, fill: '#e7b45f', 'fill-opacity': .75, stroke: '#a8742c', 'stroke-width': 2 }));
        art.append(svg('circle', { cx: 44, cy: 20, r: 4, fill: '#f8e8c6' }));
        return art;
      }
      if (sign === 'solstice_heart') {      // night over the room, with two lit circles that keep it away
        art.append(svg('rect', { x: 2, y: 2, width: 60, height: 36, rx: 3, fill: hex, 'fill-opacity': .5 }));
        const blue = window.BossMech?.colors?.blue || '#3f9bea';
        for (const [x, y] of [[16, 12], [48, 28]]) art.append(svg('circle', { cx: x, cy: y, r: 9, fill: blue, 'fill-opacity': .85, stroke: '#f8e8c6', 'stroke-width': 2 }));
        return art;
      }
    }
    if (color === 'blue') {
      const lit = '#f8e8c6';
      if (sign === 'coralregent') {         // the shell with its pearls, each in a blue ring
        art.append(svg('circle', { cx: 32, cy: 20, r: 11, fill: '#f3d9e6', 'fill-opacity': .6 }));
        for (const [x, y] of [[11, 12], [53, 12], [32, 34]]) art.append(svg('circle', { cx: x, cy: y, r: 5.5, fill: '#f6d6e3', stroke: hex, 'stroke-width': 3 }));
        return art;
      }
      if (sign === 'thunder_heart') {       // a grounding rod in each corner
        for (const [x, y] of [[8, 8], [56, 8], [8, 32], [56, 32]]) {
          art.append(svg('circle', { cx: x, cy: y, r: 6, fill: 'none', stroke: hex, 'stroke-width': 3 }));
          art.append(svg('line', { x1: x, y1: y - 3, x2: x, y2: y + 3, stroke: lit, 'stroke-width': 2 }));
        }
        return art;
      }
      if (sign === 'solstice_heart') {      // four braziers; the lit ones glow
        [[14, 11, 1], [50, 11, 0], [14, 29, 0], [50, 29, 1]].forEach(([x, y, on]) => {
          art.append(svg('circle', { cx: x, cy: y, r: 8, fill: on ? hex : 'none', 'fill-opacity': .4, stroke: hex, 'stroke-width': 3, 'stroke-dasharray': on ? '' : '3 3' }));
          art.append(svg('circle', { cx: x, cy: y, r: 2.5, fill: on ? '#ffd27a' : '#6b5a3a' }));
        });
        return art;
      }
    }
    if (color === 'red') art.append(svg('circle', { cx: 32, cy: 20, r: 16, fill: hex, 'fill-opacity': .5, stroke: hex, 'stroke-width': 3 }));
    else if (color === 'blue') art.append(svg('circle', { cx: 32, cy: 20, r: 15, fill: 'none', stroke: hex, 'stroke-width': 4 }), svg('circle', { cx: 32, cy: 20, r: 6, fill: hex, 'fill-opacity': .45 }));
    else if (color === 'path' && sign === 'bloom_heart') art.append(svg('polyline', { points: '6,32 24,6 42,32 58,10', fill: 'none', stroke: hex, 'stroke-width': 3.5, 'stroke-dasharray': '7 5', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
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
