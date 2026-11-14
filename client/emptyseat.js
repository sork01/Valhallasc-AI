'use strict';
// Authored quest scenes share authoritative quest counts and timed memory state. The overlay never sends progress.
window.EmptySeat = (() => {
  let hero = null, area = null;
  const tr = s => window.Locale?.translate(s) || s;
  function sites() {
    if (!hero || hero.dead || !area) return [];
    const out = [];
    for (const q of area.quests || []) {
      if (!q.story) continue;
      const p = hero.quests?.find(p => p.id === q.id && !p.claimed);
      if (!p) continue;
      const first = q.objectives.findIndex((o, i) => (p.counts[i] || 0) < o.count);
      q.objectives.forEach((o, i) => {
        if ((p.counts[i] || 0) >= o.count || (['memory', 'echo'].includes(o.kind) && i !== first)) return;
        for (const place of area.places || []) {
          if (o.kind === 'chime' ? place.chain !== o.target : place.id !== o.target) continue;
          out.push({ ...place, kind: o.kind, label: o.label, quest: q.id });
        }
      });
    }
    return out;
  }
  function lines(g, text, width) {
    const out = []; let line = '';
    for (const word of text.split(/\s+/)) {
      const next = line ? `${line} ${word}` : word;
      if (line && g.measureText(next).width > width) { out.push(line); line = word; }
      else line = next;
    }
    if (line) out.push(line);
    return out;
  }
  function scene() { return EMPTY_SEAT_SCENES.find(s => s.id === hero?.storyMemory?.id); }
  function giant(g, x, y, visual) {
    // Memory actors borrow the editable Eldmarr atlas. They are echoes, outside the combat actor list.
    const src = window.Field?.cathedralSprites, img = src?.img.cf_eldmarr;
    g.save(); g.translate(x, y); g.globalAlpha = .5;
    if (img?.complete && img.naturalWidth) {
      const { w, h, ax, ay } = window.Field.frameOf(src, 'cf_eldmarr');
      g.drawImage(img, 0, src.meta.clips.idle.row*h, w, h, -ax*2.6, -ay*2.6, w*2.6, h*2.6);
    } else {
      g.fillStyle = '#f2bd80'; g.beginPath(); g.ellipse(0,-90,43,70,0,0,Math.PI*2);g.fill();
      g.beginPath();g.arc(0,-176,26,0,Math.PI*2);g.fill();
    }
    g.globalAlpha = .85;g.strokeStyle='#b9e8e0';g.lineWidth=3;
    if (visual === 'chains') {
      for(let i=0;i<9;i++) {const a=i*Math.PI*2/9;g.beginPath();g.moveTo(0,-90);g.lineTo(Math.cos(a)*145,-75+Math.sin(a)*50);g.stroke();}
    } else if (visual === 'table') {
      g.fillStyle='#7d5450';g.fillRect(-65,12,130,12);
      for(let i=0;i<10;i++){g.strokeRect(-62+i*13,2,7,11);}
      g.strokeRect(80,-30,30,40);g.strokeRect(80,-70,30,35);
    } else {
      g.strokeStyle='#9ed9b5';
      for(let i=0;i<6;i++){g.beginPath();g.moveTo(0,0);g.quadraticCurveTo((i-2.5)*22,20,(i-2.5)*42,36);g.stroke();}
      g.fillStyle='#ffcf78';g.beginPath();g.ellipse(0,3,26,14,0,0,Math.PI*2);g.fill();
    }
    g.restore();
  }
  // Ring stones: a few small cut stones round a place, laid out from the place's seed so every ring sits a little differently.
  const glow = new Map(), stones = new Map();
  const rings = () => (area?.places || []).filter(p => p.ring && p.id.startsWith('es_'));
  function stonesOf(p) {
    let out = stones.get(p.id); if (out) return out;
    let seed = (p.ring.seed + 1) >>> 0; const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
    const n = p.ring.stones, turn = rnd() * Math.PI * 2; out = [];
    for (let i = 0; i < n; i++) {
      const a = turn + i * Math.PI * 2 / n + (rnd() - .5) * .2, rad = p.r + (rnd() - .5) * .26;
      out.push({ x: p.x + Math.cos(a) * rad, y: p.y + Math.sin(a) * rad, w: 24 + rnd() * 14, h: 16 + rnd() * 16, skew: (rnd() - .5) * 4, tone: rnd(), taper: .6 + rnd() * .24 });
    }
    stones.set(p.id, out); return out;
  }
  function mix(a, b, t) {
    const n = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)); if (t <= 0) return a;
    const x = n(a), y = n(b); return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * Math.min(1, t)).toString(16).padStart(2, '0')).join('');
  }
  return {
    sync(own, zone) {
      hero = own; area = zone ? WORLD_MAP.zones[zone-1] : WORLD_MAP;
      const title = document.getElementById('area-title'); if (title) title.hidden = !!scene();
    },
    sites, scene,
    litOf: id => glow.get(id) ?? 0,      // 0..1: how lit a ring is (1 while the hero stands inside an active site); read by the tests
    ringPlaces: () => rings(),
    // The standing-stone rings are part of the zone: every es_ place carries `ring` (written by scripts/empty_seat.py), and the stones are drawn
    // for the whole campaign, active or not. They are never obstacles; the walkable circle is still the place's own radius `r`.
    drawFloor(g, project) {
      const live = new Map(sites().map(p => [p.id, p])), calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      for (const p of rings()) {
        const site = live.get(p.id), inside = !!site && Math.hypot(hero.x - p.x, hero.y - p.y) <= p.r;
        // The glow eases in and out (at once with reduced motion); it is a colour change only, never an animation.
        const lit = glow.get(p.id) ?? 0, next = calm ? +inside : lit + ((inside ? 1 : 0) - lit) * .18;
        glow.set(p.id, Math.abs(next - +inside) < .02 ? +inside : next);
        const [x, y] = project(p.x, p.y), [rx, ry] = project(p.x + p.r, p.y), u = Math.abs(rx - x), v = Math.abs(ry - y);
        const l = glow.get(p.id), tint = site?.kind === 'echo' ? '#d49ffa' : '#ffd493';
        g.save();
        if (l > 0) {   // warm light pooled on the ground inside the ring
          g.globalCompositeOperation = 'lighter'; g.globalAlpha = .34 * l; g.fillStyle = tint;
          g.beginPath(); g.ellipse(x, y, u * Math.SQRT2 * .98, v * Math.SQRT2 * .98, 0, 0, Math.PI * 2); g.fill();
          g.globalCompositeOperation = 'source-over';
        }
        // A flat stone slab at the centre with the empty chair cut into it.
        g.globalAlpha = 1; g.fillStyle = '#4f4c58'; g.beginPath(); g.ellipse(x, y + 3, 33, 16.5, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = mix('#8d8a94', tint, .5 * l); g.beginPath(); g.ellipse(x, y, 33, 16.5, 0, 0, Math.PI * 2); g.fill();
        g.strokeStyle = mix('#4a4752', tint, .85 * l); g.lineWidth = 2.5; g.lineJoin = 'round';
        g.beginPath(); g.moveTo(x - 9, y - 9); g.lineTo(x + 3, y - 14); g.lineTo(x + 11, y - 9); g.lineTo(x - 1, y - 4); g.closePath();
        g.moveTo(x - 9, y - 9); g.lineTo(x - 9, y + 2); g.moveTo(x - 1, y - 4); g.lineTo(x - 1, y + 7); g.moveTo(x + 11, y - 9); g.lineTo(x + 11, y + 1); g.stroke();
        if (site) {   // caption and hint only for a site the current chapter asks for
          g.font = 'bold 14px sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#211c2b'; g.fillStyle = '#ffe5b1';
          g.strokeText(tr(site.name), x, y - 43); g.fillText(tr(site.name), x, y - 43);
          if (inside && !scene()) {
            const hint = site.kind === 'echo' ? 'The echo answers your presence.' : site.kind === 'memory' ? 'Stand still and listen.' : site.kind === 'chime' ? 'Ring all three together.' : 'Keep the circle alive.';
            g.font = '13px sans-serif'; g.strokeText(tr(hint), x, y + 35); g.fillText(tr(hint), x, y + 35);
          }
        }
        g.restore();
      }
    },
    // The stones stand in the depth-sorted scenery list, so a hero walks behind the far ones and in front of the near ones.
    ringItems(project, onScreen) {
      const out = [];
      for (const p of rings()) {
        const lit = glow.get(p.id) ?? 0;
        for (const st of stonesOf(p)) {
          const [sx, sy] = project(st.x, st.y);
          if (onScreen(sx, sy, 60)) out.push({ d: st.x + st.y, stone: st, ring: p, lit, sx, sy });
        }
      }
      return out;
    },
    drawStone(g, it) {
      const { stone: st, lit, sx, sy } = it, w = st.w, hw = w / 2, hd = w / 4, h = st.h, gold = '#ffcf78';
      const top = mix(st.tone < .5 ? '#cfccd6' : '#bdbac6', '#ffe39a', .85 * lit), left = mix('#9d9aaa', '#f2b858', .75 * lit), right = mix('#767382', '#c98530', .7 * lit);
      g.save(); g.translate(sx, sy);
      g.fillStyle = 'rgba(12,9,18,.34)'; g.beginPath(); g.ellipse(3, 2, w * .66, w * .27, 0, 0, Math.PI * 2); g.fill();
      if (lit > .02) {   // light spilling onto the ground, towards the ring's centre
        const cx = Math.sign(it.ring.x - st.x) * 1, cy = Math.sign(it.ring.y - st.y) * .5;
        g.globalCompositeOperation = 'lighter'; g.globalAlpha = .4 * lit; g.fillStyle = gold;
        g.beginPath(); g.ellipse((cx - cy) * 7, (cx + cy) * 5, w * .55, w * .22, 0, 0, Math.PI * 2); g.fill();
        g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
      }
      // A tapering standing stone: a shaded body, a rounded base and an elliptical top face.
      const sk = st.skew, tw = hw * st.taper, grad = g.createLinearGradient(-hw, 0, hw, 0);
      grad.addColorStop(0, left); grad.addColorStop(.55, mix(left, right, .5)); grad.addColorStop(1, right);
      g.fillStyle = grad; g.beginPath(); g.moveTo(-hw, 0); g.lineTo(-tw + sk, -h); g.lineTo(tw + sk, -h); g.lineTo(hw, 0); g.ellipse(0, 0, hw, hd, 0, 0, Math.PI); g.closePath(); g.fill();
      g.fillStyle = top; g.beginPath(); g.ellipse(sk, -h, tw, tw / 2, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = 'rgba(24,20,32,.5)'; g.lineWidth = 1; g.stroke();
      g.beginPath(); g.moveTo(sk - tw * .3, -h * .55); g.lineTo(sk - tw * .05, -h * .3); g.stroke();      // a crack, so it reads as rock
      g.restore();
    },
    drawVision(g, project, vw, vh) {
      const s=scene();if(!s||!hero||hero.dead)return;
      const place=area?.places?.find(p=>p.id===s.id);if(!place)return;
      if(['hearth','table','chains'].includes(s.visual)) {const [x,y]=project(place.x+7,place.y-7);giant(g,x,y,s.visual);}
      // Width follows the canvas. No controls or movement are captured by a memory.
      const unit=Math.max(1,vw/(document.getElementById('fieldcv')?.clientWidth||vw));
      const w=Math.min(620*unit,vw-24*unit), x=(vw-w)/2, pad=16*unit;
      g.save();g.textAlign='left';g.textBaseline='alphabetic';g.font=`${15*unit}px sans-serif`;
      const text=lines(g,tr(s.description),w-2*pad),h=(70+text.length*21)*unit;
      const y=Math.max(10*unit,Math.min(vh*.13,vh-h-20*unit));
      g.fillStyle='rgba(24,19,32,.94)';g.fillRect(x,y,w,h);g.strokeStyle='#d8b27c';g.lineWidth=2*unit;g.strokeRect(x,y,w,h);
      g.fillStyle='#ffe0a6';g.font=`bold ${17*unit}px sans-serif`;g.fillText(tr(s.label),x+pad,y+25*unit,w-2*pad);
      g.font=`${15*unit}px sans-serif`;g.fillStyle='#f3ebe2';text.forEach((line,i)=>g.fillText(line,x+pad,y+(50+i*21)*unit));
      const progress=Math.min(1,hero.storyMemory.elapsed/s.seconds);g.fillStyle='#6a5262';g.fillRect(x+pad,y+h-16*unit,w-2*pad,4*unit);g.fillStyle='#ffd59d';g.fillRect(x+pad,y+h-16*unit,(w-2*pad)*progress,4*unit);
      g.restore();
    }
  };
})();
