'use strict';
// Floating combat text: where each number starts, how it moves and fades, and how a rapid run of hits fans out.
// Pure maths (no canvas, no DOM) so the path can be tested on its own; field.js owns the list and draws what pose() returns.
// A number is {text, kind, head, t, lane, z0, side}; `t` is its age in seconds and starts below 0 while it waits for its stagger.
(() => {
  // size: font px; rise: px climbed over `life`; pop: peak scale of the pop-in; hold: fraction of life at full opacity;
  // arc: sideways drift in px; shake: crit tremble in px; ease: 1 = fast then slow, 0 = a straight line.
  const KINDS = {
    hit:    { size: 24, rise: 58, life: 1.0,  pop: 1.25, hold: .5,  arc: 22, shake: 0, ease: .75 },
    crit:   { size: 38, rise: 78, life: 1.3,  pop: 1.55, hold: .55, arc: 26, shake: 3, ease: .8 },
    hurt:   { size: 26, rise: 52, life: 1.1,  pop: 1.2,  hold: .5,  arc: 14, shake: 0, ease: .75 },
    heal:   { size: 26, rise: 44, life: 1.3,  pop: 1.08, hold: .6,  arc: 10, shake: 0, ease: .45 },
    miss:   { size: 18, rise: 34, life: .7,   pop: 1.05, hold: .35, arc: 12, shake: 0, ease: .85 },
    pickup: { size: 22, rise: 42, life: 1.5,  pop: 1.1,  hold: .6,  arc: 0,  shake: 0, ease: .5 },
    banner: { size: 24, rise: 50, life: 1.1,  pop: 1,    hold: .3,  arc: 0,  shake: 0, ease: 0 },
    level:  { size: 34, rise: 50, life: 1.1,  pop: 1,    hold: .3,  arc: 0,  shake: 0, ease: 0 },
  };
  const SPACING = .08, MAX_ALIVE = 40, GAP = 3, LANE_W = 80, MAX_LIFT = 160;
  const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
  const easeOut = p => 1 - (1 - p) * (1 - p) * (1 - p);
  // 1,234 below ten thousand, 12.3k and 1.2M above: a number stays about five characters wide however big it gets.
  function format(value) {
    const n = Math.round(Number(value));
    if (!Number.isFinite(n)) return String(value);
    const a = Math.abs(n);
    if (a < 10000) return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    if (a < 1e6) return (n / 1e3).toFixed(a < 1e5 ? 1 : 0).replace(/\.0$/, '') + 'k';
    return (n / 1e6).toFixed(a < 1e7 ? 2 : 1).replace(/\.?0+$/, '') + 'M';
  }
  // The state of a number `f.t` seconds into its life: offsets from the anchor (px, up is +dz), scale and opacity.
  function pose(f, reduced = false) {
    const k = KINDS[f.kind] || KINDS.banner;
    if (f.t < 0 || f.t >= k.life) return { dx: 0, dz: 0, scale: 1, alpha: 0, visible: false };
    const p = f.t / k.life, fade = clamp01((p - k.hold) / (1 - k.hold));
    if (reduced) return { dx: 0, dz: 0, scale: 1, alpha: 1 - fade, visible: true };                 // fades in place: no arc, no pop, no climb
    const pop = f.t < .12 ? .45 + (k.pop - .45) * easeOut(f.t / .12) : k.pop + (1 - k.pop) * clamp01((f.t - .12) / .1);
    const rise = k.rise * (k.ease * easeOut(p) + (1 - k.ease) * p);
    const shake = k.shake && f.t < .25 ? Math.sin(f.t * 110) * k.shake * (1 - f.t / .25) : 0;
    return { dx: f.lane * LANE_W + f.side * k.arc * easeOut(p) + shake, dz: (f.z0 || 0) + rise, scale: pop, alpha: 1 - fade, visible: true };
  }
  // The box a number occupies, relative to its anchor (screen px, y down): for the overlap checks.
  function box(f, reduced = false) {
    const k = KINDS[f.kind] || KINDS.banner, s = pose(f, reduced), w = Math.max(1, String(f.text).length) * k.size * .52 * s.scale, h = k.size * s.scale;
    return { x0: s.dx - w / 2, x1: s.dx + w / 2, y0: -s.dz - h, y1: -s.dz };
  }
  const touches = (a, b) => a.x0 < b.x1 + GAP && b.x0 < a.x1 + GAP && a.y0 < b.y1 + GAP && b.y0 < a.y1 + GAP;
  // Add a number to `list` (mutated). The lane and the starting height are the first free spot beside and above the numbers
  // still alive over the same head, so a run of hits fans out instead of stacking; the list is capped by fast-fading the oldest.
  function spawn(list, spec, rand = Math.random) {
    const kind = KINDS[spec.kind] ? spec.kind : 'banner', k = KINDS[kind];
    const f = { x: spec.x, y: spec.y, head: spec.head || 0, text: String(spec.text), color: spec.color, kind, t: -(spec.delay || 0), lane: 0, z0: 0, side: rand() < .5 ? -1 : 1 };
    const mates = list.filter(o => Math.hypot(o.x - f.x, o.y - f.y) < .6 && Math.abs(o.head - f.head) < 12 && o.t < (KINDS[o.kind] || KINDS.banner).life - .05);
    if (mates.length) f.t = -Math.max(0, spec.delay || 0, Math.max(...mates.map(o => -o.t)) + SPACING);   // a run of hits starts at least SPACING apart
    if (mates.length && k.arc) {
      // The lowest start over each lane that clears every mate while both are moving. Follow both paths over the next 0.8 s
      // (the newcomer is invisible until its delay is over, and that is when they are near); the mates' boxes are worked out once.
      const taus = [], mateBoxes = [];
      for (let tau = 0; tau <= .8; tau += .04) { taus.push(tau); mateBoxes.push(mates.map(o => ({ ...o, t: o.t + tau })).filter(o => pose(o).visible).map(o => box(o))); }
      const c = { ...f };
      let best = null;
      for (const lane of [0, 1, -1, 2, -2]) {
        c.lane = lane; c.side = lane < 0 ? -1 : lane > 0 ? 1 : f.side;
        for (let z0 = 0; z0 <= (best ? best.z0 - 4 : MAX_LIFT); z0 += 4) {
          c.z0 = z0;
          let free = true;
          for (let i = 0; i < taus.length && free; i++) {
            c.t = taus[i] + f.t; if (c.t < 0 || !mateBoxes[i].length) continue;
            const a = box(c); for (const b of mateBoxes[i]) if (touches(a, b)) { free = false; break; }
          }
          if (free) { best = { lane, side: c.side, z0 }; break; }
        }
        if (best && best.z0 === 0) break;
      }
      if (best) { f.lane = best.lane; f.side = best.side; f.z0 = best.z0; }
    }
    list.push(f);
    const alive = list.filter(o => o.t < (KINDS[o.kind] || KINDS.banner).life);
    if (alive.length > MAX_ALIVE) for (const o of alive.slice(0, alive.length - MAX_ALIVE)) o.t = Math.max(o.t, (KINDS[o.kind] || KINDS.banner).life - .18);   // the oldest fade out fast
    return f;
  }
  // Advance every number by dt and drop the finished ones; returns the surviving list.
  function step(list, dt) {
    for (const f of list) f.t += dt;
    return list.filter(f => f.t < (KINDS[f.kind] || KINDS.banner).life);
  }
  const api = { KINDS, MAX_ALIVE, format, pose, box, spawn, step };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else window.DamageNumbers = api;
})();
