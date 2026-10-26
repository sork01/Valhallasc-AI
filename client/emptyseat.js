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
      const [w, h] = src.meta.frame, [ax, ay] = src.meta.anchor;
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
  return {
    sync(own, zone) {
      hero = own; area = zone ? WORLD_MAP.zones[zone-1] : WORLD_MAP;
      const title = document.getElementById('area-title'); if (title) title.hidden = !!scene();
    },
    sites, scene,
    drawFloor(g, project) {
      for (const p of sites()) {
        const [x, y] = project(p.x, p.y), [rx, ry] = project(p.x+p.r, p.y);
        const active = Math.hypot(hero.x-p.x,hero.y-p.y)<=p.r;
        g.save();g.strokeStyle=p.kind==='echo'?'#d49ffa':'#ffd493';g.fillStyle=active?'rgba(255,205,135,.2)':'rgba(151,200,228,.12)';g.lineWidth=3;
        g.beginPath();g.ellipse(x,y,Math.abs(rx-x)*Math.SQRT2,Math.abs(ry-y)*Math.SQRT2,0,0,Math.PI*2);g.fill();g.stroke();
        // A small empty chair marks the campaign, including on Low graphics and with reduced motion.
        g.strokeRect(x-9,y-32,18,16);g.beginPath();g.moveTo(x-9,y-16);g.lineTo(x-9,y-5);g.moveTo(x+9,y-16);g.lineTo(x+9,y-5);g.stroke();
        g.font='bold 14px sans-serif';g.textAlign='center';g.lineWidth=4;g.strokeStyle='#211c2b';g.fillStyle='#ffe5b1';
        g.strokeText(tr(p.name),x,y-43);g.fillText(tr(p.name),x,y-43);
        if(active && !scene()) {
          const hint = p.kind==='echo'?'The echo answers your presence.':p.kind==='memory'?'Stand still and listen.':p.kind==='chime'?'Ring all three together.':'Keep the circle alive.';
          g.font='13px sans-serif';g.strokeText(tr(hint),x,y+35);g.fillText(tr(hint),x,y+35);
        }
        g.restore();
      }
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
