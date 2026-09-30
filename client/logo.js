'use strict';
/* The title logo: "VALHALLA RUMBLE" as chunky frozen-rune letters with a gold trim,
   3D extrusion, snow caps, icicles, frost sparkles, wings and a Korean ribbon.
   Drawn as SVG so it stays sharp at any size and the text stays real text. */
(() => {
  const svg = document.getElementById('logo');
  if (!svg) return;
  let seed = 5;
  const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const r = (a, b) => a + rnd() * (b - a);
  const f = n => Math.round(n * 10) / 10;
  const FONT = '"Lilita One", "Jua", Impact, "Arial Rounded MT Bold", sans-serif';
  const L1 = { id: 't1', text: 'VALHALLA', y: 172, size: 196, sp: 5 };
  const L2 = { id: 't2', text: 'RUMBLE', y: 318, size: 140, sp: 8 };

  const star = (cx, cy, r1, r2) => {
    let p = '';
    for (let i = 0; i < 8; i++) { const a = -Math.PI / 2 + i * Math.PI / 4, rr = i % 2 ? r2 : r1; p += `${f(cx + Math.cos(a) * rr)},${f(cy + Math.sin(a) * rr)} `; }
    return p;
  };
  const scallop = (y, amp, n) => {
    const w = 1000 / n;
    let d = `M0 0 H1000 V${y}`;
    for (let i = 0; i < n; i++) d += ` q${f(-w / 2)} ${f(amp * (i % 2 ? .55 : 1))} ${f(-w)} 0`;
    return d + ' Z';
  };
  // one wing facing left, origin at the shoulder
  const WING = 'M0 0 C-50 -46 -130 -62 -214 -34 Q-190 -22 -172 -12 Q-200 -2 -204 12 Q-176 16 -156 22 Q-178 36 -176 50 Q-146 44 -124 42 Q-140 60 -138 76 Q-104 66 -84 58 Q-92 80 -88 96 Q-58 82 -44 68 Q-20 50 0 16 Z';
  const WING_LINES = 'M-8 6 L-172 -12 M-8 10 L-156 22 M-8 14 L-124 42 M-6 18 L-84 58';

  const textEl = l => `<text id="${l.id}" x="500" y="${l.y}" text-anchor="middle" font-family='${FONT}' font-size="${l.size}" letter-spacing="${l.sp}">${l.text}</text>`;
  const extrude = l => Array.from({ length: 15 }, (_, i) =>
    `<use href="#${l.id}" y="${f((i + 1) * 1.6)}" fill="#0a1a44" stroke="#0a1a44" stroke-width="18" stroke-linejoin="round"/>`).join('');
  const face = (l, capTop, capH) => `
    ${extrude(l)}
    <use href="#${l.id}" fill="none" stroke="#5c3f08" stroke-width="22" stroke-linejoin="round"/>
    <use href="#${l.id}" fill="none" stroke="url(#lGold)" stroke-width="15" stroke-linejoin="round"/>
    <use href="#${l.id}" fill="url(#lIce)" stroke="#2a5a9c" stroke-width="2.5" stroke-linejoin="round"/>
    <g clip-path="url(#c-${l.id})">
      <rect x="0" y="${capTop + capH * .5}" width="1000" height="${capH * .5}" fill="#1c5ec0" opacity=".28"/>
      <path d="${scallop(capTop + capH * .3, 12, 15)}" fill="#f8fcff"/>
      <path d="${scallop(capTop + capH * .3 + 6, 12, 15)}" fill="none" stroke="#9fd6f5" stroke-width="3" opacity=".8" transform="translate(0 0)"/>
      <rect x="0" y="${capTop + capH * .34}" width="1000" height="${capH * .09}" fill="#fff" opacity=".35"/>
      <g class="sweep-wrap"><rect class="sweep" x="-160" y="0" width="90" height="420" fill="url(#lShine)" transform="skewX(-22)"/></g>
    </g>`;

  svg.innerHTML = `
  <defs>
    <linearGradient id="lIce" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".3" stop-color="#d6f3ff"/><stop offset=".68" stop-color="#68c0f4"/><stop offset="1" stop-color="#2c74cf"/></linearGradient>
    <linearGradient id="lGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff0a0"/><stop offset=".5" stop-color="#f2be3a"/><stop offset="1" stop-color="#b9801a"/></linearGradient>
    <linearGradient id="lShine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <linearGradient id="lIcicle" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8f8ff"/><stop offset="1" stop-color="#6cc4f6"/></linearGradient>
    <linearGradient id="lRibbon" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2450b0"/><stop offset="1" stop-color="#0f2666"/></linearGradient>
    <radialGradient id="lGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#7fe8ff" stop-opacity=".75"/><stop offset=".55" stop-color="#3fb4ea" stop-opacity=".25"/><stop offset="1" stop-color="#3fb4ea" stop-opacity="0"/></radialGradient>
    ${textEl(L1)}${textEl(L2)}
    <clipPath id="c-t1"><use href="#t1"/></clipPath><clipPath id="c-t2"><use href="#t2"/></clipPath>
    <g id="lwing" stroke="#5c3f08" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"><path d="${WING}" fill="url(#lGold)"/><path d="${WING_LINES}" fill="none" stroke-width="3.5" opacity=".75"/></g>
  </defs>

  <ellipse class="lglow" cx="500" cy="190" rx="520" ry="170" fill="url(#lGlow)"/>

  <g class="wings">
    <use href="#lwing" transform="translate(292 236) scale(1.12)"/>
    <use href="#lwing" transform="translate(708 236) scale(-1.12 1.12)"/>
  </g>

  <g id="ribbon">
    <path d="M226 372 L292 372 L292 430 L226 430 L252 401 Z" fill="#0b1c52" stroke="#e0a92a" stroke-width="4" stroke-linejoin="round"/>
    <path d="M774 372 L708 372 L708 430 L774 430 L748 401 Z" fill="#0b1c52" stroke="#e0a92a" stroke-width="4" stroke-linejoin="round"/>
    <path d="M270 362 H730 V420 H270 Z" fill="url(#lRibbon)" stroke="#e0a92a" stroke-width="5" stroke-linejoin="round"/>
    <text id="ko" x="503" y="392" text-anchor="middle" dominant-baseline="central" font-family='"Jua","Noto Sans KR","Malgun Gothic",sans-serif' font-size="46" letter-spacing="6" fill="#fff3c4" stroke="#5c3f08" stroke-width="7" paint-order="stroke" stroke-linejoin="round" lang="ko">발할라 럼블</text>
  </g>

  <g id="line1">${face(L1, 26, 140)}</g>
  <g id="line2">${face(L2, 220, 98)}</g>
  <g id="ic1"></g><g id="ic2"></g>
  <g id="sparks"></g>`;

  // Icicles hang from measured glyph positions, so they need the real font.
  const FR = { V: [.5], A: [.2, .8], L: [.3, .72], H: [.2, .8], R: [.25, .75], U: [.5], M: [.15, .85], B: [.3, .7], E: [.35, .75] };
  const icicles = (id, l, into, lo, hi) => {
    const t = svg.querySelector('#' + id); const g = svg.querySelector('#' + into);
    let s = '';
    for (let i = 0; i < l.text.length; i++) {
      let ex; try { ex = t.getExtentOfChar(i); } catch (e) { continue; }
      for (const fx of (FR[l.text[i]] || [.5])) {
        const x = ex.x + ex.width * fx + r(-4, 4), w = r(7, 12), len = r(lo, hi), top = l.y + 6;
        s += `<path d="M${f(x - w)} ${top} Q${f(x - w * .3)} ${f(top + len * .6)} ${f(x + r(-1.5, 1.5))} ${f(top + len)} Q${f(x + w * .3)} ${f(top + len * .6)} ${f(x + w)} ${top} Z" fill="url(#lIcicle)" stroke="#2a5a9c" stroke-width="2.5" stroke-linejoin="round"/>`;
      }
    }
    g.innerHTML = s;
  };
  const sparks = () => {
    let s = '';
    for (let i = 0; i < 9; i++) {
      const x = r(150, 850), y = r(40, 290), z = r(6, 13);
      s += `<polygon class="tw" style="animation-delay:${f(r(0, 3))}s" points="${star(x, y, z, z * .18)}" fill="#fff"/>`;
    }
    svg.querySelector('#sparks').innerHTML = s;
  };
  const build = () => { icicles('t1', L1, 'ic1', 34, 62); icicles('t2', L2, 'ic2', 20, 34); sparks(); };
  build();
  if (document.fonts && document.fonts.load) {
    Promise.all([document.fonts.load('200px "Lilita One"', 'VALHALLA'), document.fonts.load('46px "Jua"', '발할라')])
      .then(() => { seed = 5; build(); }).catch(() => {});
  }
})();
