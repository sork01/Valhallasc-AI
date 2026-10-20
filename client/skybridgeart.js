'use strict';
// The Shattered Span: Seven broken arches above the tempest.
// White-and-gold Asgardian marble viaducts, glowing Bifrost rainbow glass causeways,
// celestial auroras, floating bridge fragments, and howling high-altitude storms.
(() => {
  const {iso, poly, line, prism} = City.kit;
  const TAU = Math.PI * 2;
  const stroke = (g, points, color, width = 2) => {
    g.beginPath();
    points.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
    g.strokeStyle = color;
    g.lineWidth = width;
    g.stroke();
  };
  const ellipse = (g, x, y, rx, ry, fill, strokeColor, lw = 2) => {
    g.beginPath();
    g.ellipse(x, y, rx, ry, 0, 0, TAU);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (strokeColor) { g.strokeStyle = strokeColor; g.lineWidth = lw; g.stroke(); }
  };
  const RAYS = ['#ff7a98', '#ffa868', '#f6ec80', '#72e8a8', '#64d8f0', '#9484ff', '#df80ff'];

  // ---- 1. SPAN WALL (Celestial bridge abutment with buttress fins, cornices & sapphire runes) ----
  City.art.span_wall = {
    box: [460, 480, 230, 360],
    draw(g, o) {
      const w = o.width, d = o.depth;
      // Main marble mass
      prism(g, w, d, 92, '#d6e4f2', '#8aa4c2', '#455976');
      // Stepped upper cornice
      prism(g, w * 1.05, d * 1.05, 12, '#f0f5fc', '#a2bccc', '#5a708e', 92);
      // Lower plinth
      prism(g, w * 1.03, d * 1.03, 8, '#b8ccdf', '#738fae', '#3c4e66', 0);

      // Gold vertical astragals and lapis inlay ribs
      for (let i = -1; i <= 1; i++) {
        const x = i * w * .28;
        stroke(g, [iso(x, d / 2, 8), iso(x, d / 2, 86)], '#dfb668', 5);
        stroke(g, [iso(x - .08, d / 2, 14), iso(x + .08, d / 2, 80)], '#7ce8ff', 2);
      }
      // Horizontal frieze bands
      for (const h of [28, 62]) {
        stroke(g, [iso(-w / 2, d / 2, h), iso(w / 2, d / 2, h)], '#364966', 2.5);
        stroke(g, [iso(-w / 2, d / 2, h + 2), iso(w / 2, d / 2, h + 2)], '#f0d488', 1.2);
      }
      // Central carved valkyrie diamond relief
      const p = iso(0, d / 2, 48);
      poly(g, [[p[0] - 14, p[1]], [p[0], p[1] - 16], [p[0] + 14, p[1]], [p[0], p[1] + 16]], '#567ba8', '#f6da92', 2.5);
      ellipse(g, p[0], p[1], 5, 5, '#8ef4ff');
    }
  };

  // ---- 2. STANDING CELESTIAL ARCH (Colossal Bifrost viaduct arch with rainbow glass spandrel) ----
  City.art.span_arch = {
    box: [460, 420, 230, 360],
    draw(g, o) {
      // Twin soaring marble pillars
      for (const s of [-1, 1]) {
        g.save();
        g.translate(s * 115, 0);
        // Base plinth
        prism(g, .7, .7, 18, '#b8cce0', '#728ca8', '#405268');
        // Fluted column
        prism(g, .52, .52, 175, '#e4effa', '#8faac8', '#485e7a', 18);
        // Gold capital
        prism(g, .68, .68, 14, '#f4d890', '#c29a4e', '#6a4e22', 193);
        g.restore();
      }
      // Upper connecting arch lintel & lower curved band
      stroke(g, [[-115, -193], [115, -193]], '#dfb668', 16);
      stroke(g, [[-110, -82], [110, -82]], '#68b8e0', 10);
      // Seven radiant rainbow glass rays spanning the arch
      for (let i = -3; i <= 3; i++) {
        stroke(g, [[i * 28, -185], [i * 18, -86]], RAYS[i + 3], 4);
      }
      // Central Keystone escutcheon
      poly(g, [[-60, -135], [0, -182], [60, -135], [0, -88]], '#416694', '#f6da92', 4);
      ellipse(g, 0, -135, 18, 18, '#8ef4ff', '#dfb668', 2);
    },
    animate(g, o, t) {
      // Floating glowing keystone diamond pulsing with starlight
      const bob = Math.sin(t * 2.2) * 4;
      g.save();
      g.translate(0, -135 + bob);
      g.shadowColor = '#7ce8ff';
      g.shadowBlur = 18 + 6 * Math.sin(t * 3);
      poly(g, [[-8, 0], [0, -12], [8, 0], [0, 12]], '#ffffff', '#7ce8ff', 1.5);
      g.restore();
    }
  };

  // ---- 3. THE SHATTERED ARCH (Fractured bridge arch with floating crystal shards & lightning) ----
  City.art.span_broken_arch = {
    box: [460, 420, 230, 360],
    draw(g, o) {
      // Intact West pillar
      g.save();
      g.translate(-115, 0);
      prism(g, .7, .7, 18, '#b8cce0', '#728ca8', '#405268');
      prism(g, .52, .52, 175, '#e4effa', '#8faac8', '#485e7a', 18);
      prism(g, .68, .68, 14, '#f4d890', '#c29a4e', '#6a4e22', 193);
      g.restore();
      // Broken arch fragment jutting out from left
      stroke(g, [[-115, -193], [-35, -190]], '#dfb668', 16);
      stroke(g, [[-110, -82], [-45, -92]], '#68b8e0', 10);
      for (let i = 0; i < 3; i++) stroke(g, [[(-3 + i) * 28, -185], [(-3 + i) * 18, -86]], RAYS[i], 4);

      // Truncated East pillar (sheared off halfway up)
      g.save();
      g.translate(115, 0);
      prism(g, .7, .7, 18, '#b8cce0', '#728ca8', '#405268');
      prism(g, .52, .52, 78, '#e4effa', '#8faac8', '#485e7a', 18);
      // Jagged fracture break on right column
      poly(g, [[-24, -96], [0, -112], [18, -98], [24, -108], [-10, -96]], '#dfb668', '#455976', 2);
      g.restore();

      // Jagged sheared edge of the main arch
      poly(g, [[-35, -202], [-15, -190], [-38, -178]], '#455976', '#f6da92', 2);
    },
    animate(g, o, t) {
      // Levitating fractured masonry blocks & prismatic crystals floating in the gap
      g.save();
      for (let i = 0; i < 5; i++) {
        const a = t * .8 + i * 1.25;
        const x = -10 + i * 24 + Math.sin(a) * 6;
        const y = -160 + (i % 2 ? -18 : 12) + Math.cos(a) * 7;
        // Floating stone chunk
        g.fillStyle = i % 2 ? '#b8cce0' : '#8aa4c2';
        g.strokeStyle = '#dfb668';
        g.lineWidth = 1.5;
        g.beginPath();
        g.rect(x - 9, y - 7, 18, 14);
        g.fill();
        g.stroke();
        // Levitating crystal shard inside
        g.shadowColor = RAYS[(i * 2) % 7];
        g.shadowBlur = 12;
        ellipse(g, x, y, 4, 8, RAYS[(i * 2) % 7]);
      }
      // Occasional crackling lightning arc bridging the shattered gap
      if (Math.sin(t * 3.5) > .7) {
        g.strokeStyle = 'rgba(160, 235, 255, .85)';
        g.lineWidth = 2;
        g.beginPath();
        g.moveTo(-35, -190);
        g.lineTo(5, -182 + Math.sin(t * 15) * 8);
        g.lineTo(55, -140 + Math.cos(t * 12) * 8);
        g.lineTo(115, -96);
        g.stroke();
      }
      g.restore();
    }
  };

  // ---- 4. BRIDGE BALUSTRADE (Pierced marble parapet with golden balusters & crystal finials) ----
  City.art.span_balustrade = {
    box: [240, 220, 120, 160],
    draw(g, o) {
      // Marble plinth
      prism(g, 1.8, .45, 12, '#b8cce0', '#728ca8', '#405268');
      // Railing posts
      for (const s of [-1, 1]) {
        g.save();
        g.translate(s * 52, 0);
        prism(g, .35, .35, 42, '#e4effa', '#8faac8', '#485e7a', 12);
        // Post cap & gold finial
        prism(g, .45, .45, 8, '#f4d890', '#c29a4e', '#6a4e22', 54);
        ellipse(g, 0, -66, 6, 9, '#7ce8ff', '#dfb668', 1.5);
        g.restore();
      }
      // Top marble handrail
      stroke(g, [[-58, -54], [58, -54]], '#f0f5fc', 9);
      stroke(g, [[-58, -51], [58, -51]], '#dfb668', 3);
      // Pierced baluster uprights
      for (let i = -2; i <= 2; i++) {
        stroke(g, [[i * 18, -12], [i * 18, -48]], '#8aa4c2', 4);
        stroke(g, [[i * 18, -24], [i * 18, -36]], '#7ce8ff', 2);
      }
    }
  };

  // ---- 5. BRIDGE PIER (Massive viaduct abutment corbel anchoring the span into the clouds) ----
  City.art.span_pier = {
    box: [320, 360, 160, 270],
    draw(g) {
      prism(g, 1.4, 1.4, 110, '#b8c8da', '#6a7f9e', '#3e4e68');
      prism(g, 1.6, 1.6, 18, '#dce8f6', '#86a0be', '#526888', 110);
      for (const s of [-1, 1]) {
        stroke(g, [[s * 48, -20], [s * 48, -105]], '#dfb668', 6);
        stroke(g, [[s * 48, -40], [s * 62, -85], [s * 48, -100]], '#7ce8ff', 2.5);
      }
      ellipse(g, 0, -75, 14, 14, '#4a6e98', '#f6da92', 2);
      ellipse(g, 0, -75, 7, 7, '#92f2ff');
    }
  };

  // ---- 6. SPAN BRAZIER (Marble font with animated swirling prismatic starlight flame) ----
  City.art.span_brazier = {
    box: [180, 240, 90, 200],
    draw(g) {
      prism(g, .6, .6, 42, '#b8c8da', '#6a7f9e', '#3e4e68');
      prism(g, .8, .8, 10, '#dce8f6', '#86a0be', '#526888', 42);
      ellipse(g, 0, -62, 22, 9, '#dfb464', '#785622', 2);
      ellipse(g, 0, -82, 10, 28, '#7ce8ff');
      ellipse(g, -2, -86, 4, 18, '#fff6d2');
    },
    animate(g, o, t) {
      g.save();
      const pulse = Math.sin(t * 3 + o.x) * 4;
      g.shadowColor = '#7ce8ff';
      g.shadowBlur = 24 + pulse;
      ellipse(g, 0, -84 + pulse * .3, 7, 20, '#ccf8ff');
      // Orbiting starlight ember sparks
      for (let i = 0; i < 3; i++) {
        const a = t * 2.5 + i * 2.09;
        const ex = Math.cos(a) * 16, ey = -86 + Math.sin(a) * 6;
        ellipse(g, ex, ey, 2.5, 2.5, RAYS[(i * 2 + 1) % 7]);
      }
      g.restore();
    }
  };

  // ---- 7. SPAN PRISM (Astronomical brass-and-marble resonator with spinning crystal) ----
  City.art.span_prism = {
    box: [200, 240, 100, 200],
    draw(g) {
      prism(g, .85, .85, 18, '#bccde0', '#6e84a3', '#41526e');
      stroke(g, [[0, -18], [0, -125]], '#deb668', 8);
      ellipse(g, 0, -45, 24, 9, '#c6964e', '#5a421a', 2);
      ellipse(g, 0, -98, 22, 8, '#84e4ff', '#dfb668', 2);
      for (let j = 0; j < 7; j++) stroke(g, [[-16, -46 - j * 7], [16, -50 - j * 7]], j % 2 ? '#88e8ff' : '#d8a4f8', 3);
    },
    animate(g, o, t) {
      g.save();
      const a = t * 1.4 + o.x;
      const w = 12 * Math.cos(a);
      g.shadowColor = '#92f2ff';
      g.shadowBlur = 18;
      poly(g, [[-w, -125], [0, -150], [w, -125], [0, -108]], '#92f2ff', '#ffffff', 2);
      g.restore();
    }
  };

  // ---- 8. SPAN OBELISK (Asgardian runestone with glowing blue channel runes) ----
  City.art.span_obelisk = {
    box: [280, 250, 140, 190],
    draw(g) {
      prism(g, 1, 1.8, 42, '#bed0e2', '#7389a8', '#465975');
      prism(g, 1.15, 2.0, 10, '#dceaf8', '#8fa6c4', '#5e7494', 42);
      // Inlaid glowing rune channel
      stroke(g, [[0, -60], [0, -102]], '#88ecff', 5);
      stroke(g, [[-8, -75], [8, -75]], '#88ecff', 3);
      stroke(g, [[-6, -90], [6, -90]], '#88ecff', 3);
      ellipse(g, 0, -112, 12, 10, '#dfb668', '#f8e8ad', 2);
    },
    animate(g, o, t) {
      g.save();
      const pulse = .6 + .4 * Math.sin(t * 2.6 + o.y);
      g.fillStyle = `rgba(140, 236, 255, ${pulse * .7})`;
      g.shadowColor = '#7ce8ff';
      g.shadowBlur = 14 * pulse;
      ellipse(g, 0, -112, 6, 5, g.fillStyle);
      g.restore();
    }
  };

  // ---- 9. FLOATING BRIDGE SHARD (Masonry fragment suspended in mid-air over the chasm) ----
  City.art.span_floating_shard = {
    box: [220, 200, 110, 160],
    draw(g, o) {
      const v = (o.v || 0) % 3;
      poly(g, [[-28, -32], [0, -56], [32, -38], [24, -14], [-12, -10]], '#98b4cc', '#dfb668', 2.5);
      poly(g, [[-28, -32], [24, -14], [8, 8], [-34, -10]], '#5a7392', '#364966', 2);
      ellipse(g, 0, -32, 9, 14, RAYS[v * 2], '#ffffff', 1.5);
    },
    animate(g, o, t) {
      const bob = Math.sin(t * 1.8 + o.x) * 6;
      g.save();
      g.translate(0, bob);
      g.shadowColor = '#7ce8ff';
      g.shadowBlur = 12;
      ellipse(g, 0, -32, 5, 8, '#ffffff');
      g.restore();
    }
  };

  // ---- 10. DYNAMIC SKY & STORM BACKDROP (Called by field.js drawSky) ----
  function backdrop(g, w, h, t) {
    // 1. Celestial tempest sky gradient: deep cosmic indigo down to glowing horizon
    const skyGrad = g.createLinearGradient(0, 0, 0, h);
    skyGrad.addColorStop(0, '#060a16');
    skyGrad.addColorStop(.4, '#101934');
    skyGrad.addColorStop(.75, '#192b4a');
    skyGrad.addColorStop(1, '#1f3c5e');
    g.fillStyle = skyGrad;
    g.fillRect(0, 0, w, h);

    g.save();
    // 2. Stars twinkling in the deep upper heavens
    for (let i = 0; i < 28; i++) {
      const sx = (i * 197.3) % w;
      const sy = (i * 113.7) % (h * .55);
      const twinkle = .4 + .6 * Math.sin(t * 1.8 + i * 2.1);
      g.fillStyle = `rgba(220, 245, 255, ${twinkle * .75})`;
      g.fillRect(sx, sy, 2, 2);
    }

    // 3. Ethereal Bifrost Auroral Ribbons arching over the bridge
    g.globalCompositeOperation = 'lighter';
    for (let r = 0; r < 4; r++) {
      const aX = w * .15 + r * (w * .22);
      const sway = Math.sin(t * .4 + r) * 35;
      const gr = g.createLinearGradient(0, 0, 0, h * .6);
      gr.addColorStop(0, 'rgba(0,0,0,0)');
      gr.addColorStop(.45, RAYS[(r * 2) % 7] + '33');
      gr.addColorStop(.8, RAYS[(r * 2 + 2) % 7] + '22');
      gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gr;
      g.beginPath();
      g.moveTo(aX - 80 + sway, 0);
      g.bezierCurveTo(aX + 40, h * .25, aX - 60 - sway, h * .45, aX + 80, h * .65);
      g.bezierCurveTo(aX + 160 + sway, h * .45, aX + 80, h * .25, aX + 20 - sway, 0);
      g.fill();
    }

    // 4. Parallax Storm Cloud Banks below the bridge
    g.globalCompositeOperation = 'source-over';
    for (let layer = 0; layer < 2; layer++) {
      const speed = 18 + layer * 14;
      const cyBase = h * (.55 + layer * .18);
      g.fillStyle = layer === 0 ? 'rgba(20, 32, 58, .75)' : 'rgba(14, 22, 42, .88)';
      for (let c = 0; c < 9; c++) {
        const cx = ((c * 260 + t * speed) % (w + 400)) - 200;
        const cy = cyBase + Math.sin(t * .3 + c) * 16;
        ellipse(g, cx, cy, 180 + layer * 40, 48 + layer * 16, g.fillStyle);
      }
    }

    // 5. Periodic Atmospheric Lightning flashes illuminating the clouds
    const flashTimer = Math.sin(t * 1.1) * Math.sin(t * 2.7);
    if (flashTimer > .82) {
      const alpha = (flashTimer - .82) * 2.2;
      g.fillStyle = `rgba(180, 230, 255, ${alpha * .22})`;
      g.fillRect(0, 0, w, h);
    }
    g.restore();
  }

  // ---- 11. ATMOSPHERIC STORM WEATHER (High-altitude wind streaks & rainbow crystal motes) ----
  function weather(g, t, w, h) {
    g.save();
    // 1. High-altitude howling wind streaks rushing across the screen
    g.strokeStyle = 'rgba(190, 235, 255, .18)';
    g.lineWidth = 1.6;
    for (let i = 0; i < 22; i++) {
      const speed = 180 + (i % 4) * 45;
      const x = ((i * 173.3 + t * speed) % (w + 300)) - 150;
      const y = (i * 89.1 + Math.sin(t * .5 + i) * 20) % h;
      const len = 70 + (i % 3) * 35;
      g.beginPath();
      g.moveTo(x, y);
      g.lineTo(x + len, y - 6);
      g.stroke();
    }

    // 2. Swirling Rainbow Crystal Motes tumbling in the wind
    g.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 26; i++) {
      const speed = 40 + (i % 5) * 20;
      const x = ((i * 139 + t * speed) % (w + 40)) - 20;
      const y = (i * 97 + Math.sin(t * 1.8 + i) * 30 + t * 14) % h;
      const a = .4 + .5 * Math.sin(t * 2 + i);
      const col = RAYS[i % 7];
      g.fillStyle = col;
      g.globalAlpha = a * .65;
      g.fillRect(x, y, 2.5, 2.5);
    }
    g.restore();
  }

  // ---- 12. TILE GROUND COLOR (Bifrost Rainbow Causeway, White Marble & Fractured Edges) ----
  function room(x, y, z) {
    return (z.rooms || []).findIndex(([x0, y0, x1, y1]) => x >= x0 && x < x1 && y >= y0 && y < y1);
  }

  function ground(x, y, tone, alt, z) {
    const i = room(x, y, z), r = z.rooms?.[i];
    if (!r) return 'rgba(0,0,0,0)'; // Transparent: reveals live storm backdrop & clouds underneath

    const dx = Math.abs(x - 56);
    const edge = (x === r[0] || y === r[1] || x === r[2] - 1 || y === r[3] - 1);
    const cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2;
    const distCenter = Math.hypot(x + .5 - cx, y + .5 - cy);

    // Fractured breakages along outer viaduct edges
    if (edge) return '#1b2a44';

    // The Central Rainbow Bifrost Causeway down the middle of the bridge
    if (dx <= 1.5) {
      const hue = Math.floor((y * 12 + tPhase(x, y)) % 360);
      return `hsl(${hue}, 75%, ${58 + tone * 6 + alt * .5}%)`;
    }

    // Plazas of the Seven Arches: concentric gold & lapis medallions
    if (i < 6) {
      if (Math.abs(distCenter - 4) < .8 || Math.abs(distCenter - 7) < .8) return '#dfb668'; // Gold ring inlay
      if (distCenter < 3.2) return '#2e4c74'; // Lapis inner disc
      if (Math.abs(Math.abs(x - cx) - Math.abs(y - cy)) < .7) return '#68b8e0'; // Azure compass spokes
    }

    // Polished Asgardian White-and-Azure Celestial Marble flagstones
    const marbleHue = 210 + (i % 3) * 6;
    const marbleLight = 62 + tone * 7 + ((x + y) % 2 ? 2.5 : -2.5) + alt * .6;
    return `hsl(${marbleHue}, 28%, ${marbleLight}%)`;
  }

  function tPhase(x, y) {
    return (x * 17 + y * 23) % 40;
  }

  // ---- 13. TILE DETAIL (Inlaid Gold Seams, Valkyrie Crests & Glowing Crystal Fissures) ----
  function detail(g, px, py, x, y, tw, th, z) {
    const i = room(x, y, z), r = z.rooms?.[i];
    if (!r) return;
    const cy = py + th / 2;
    const edge = (x === r[0] || y === r[1] || x === r[2] - 1 || y === r[3] - 1);

    // Runic border outline on room edge tiles with glowing cyan fracture
    if (edge) {
      stroke(g, [[px - tw * .28, cy], [px, py + th * .25], [px + tw * .28, cy]], '#7ce8ff', 2);
      stroke(g, [[px - tw / 2, cy], [px, py], [px + tw / 2, cy]], '#dfb668', 2.2);
      return;
    }

    // Interlocking marble flagstone bevels
    stroke(g, [[px - tw / 2, cy], [px, py], [px + tw / 2, cy]], 'rgba(40, 65, 95, .22)', 1.4);

    // Central Rainbow Causeway: golden curb rails flanking the glass
    if (Math.abs(x - 56) <= 1.5) {
      stroke(g, [[px - tw * .38, cy], [px, py + th * .15], [px + tw * .38, cy]], '#fff0aa', 1.8);
      stroke(g, [[px - tw * .25, cy], [px, py + th * .35], [px + tw * .25, cy]], '#7ce8ff', 1.4);
      return;
    }

    // Inlaid celestial starbursts and diamond runes on plaza flagstones
    if ((x * 7 + y * 11) % 9 === 0) {
      stroke(g, [[px - 14, cy], [px, cy - 7], [px + 14, cy], [px, cy + 7], [px - 14, cy]], '#dfb668', 1.5);
      ellipse(g, px, cy, 3, 3, '#7ce8ff');
    }
  }

  // ---- 14. RAINBOW GATEWAY PORTAL ----
  function portal(g, p, sx, sy, t) {
    g.save();
    g.translate(sx, sy);
    // Soaring twin Bifrost portal pylons
    for (const s of [-1, 1]) {
      poly(g, [[s * 52, 0], [s * 46, -112], [s * 26, -145], [s * 18, -128], [s * 32, -88], [s * 34, 0]], '#5a789c', '#f0d088', 3.5);
    }
    poly(g, [[-50, -115], [-35, -152], [35, -152], [50, -115]], '#7290b2', '#f6dc92', 3.5);

    // Luminous swirling rainbow portal pool
    const gr = g.createRadialGradient(0, -62, 2, 0, -62, 64);
    gr.addColorStop(0, '#ffffff');
    gr.addColorStop(.35, '#8ef2ff');
    gr.addColorStop(.7, '#7a96d8');
    gr.addColorStop(1, '#162238');
    ellipse(g, 0, -63, 34, 58, gr);

    // Prismatic energy rays ascending through the gate
    for (let i = -3; i <= 3; i++) {
      const rayCol = RAYS[i + 3];
      stroke(g, [[i * 9, -112], [i * 9 + Math.sin(t * 2 + i) * 3, -16]], rayCol, 1.8);
    }

    // Portal banner label
    g.font = '15px "Jua", sans-serif';
    g.textAlign = 'center';
    g.lineWidth = 4;
    g.strokeStyle = '#141e30';
    g.fillStyle = '#eaf8ff';
    const name = window.Locale?.translate(p.name) || p.name;
    g.strokeText(name, 0, -164);
    g.fillText(name, 0, -164);
    g.restore();
  }

  window.SkybridgeArt = {
    backdrop,
    weather,
    ground,
    detail,
    portal
  };
})();
