'use strict';
window.RaidKey = (() => {
  const image = new Image(); image.src = 'assets/raid_cross.png';
  const tinted = new WeakMap();
  let hero = null, crosses = [], states = [], pending = [], enabled = false;
  const tr = s => window.Locale?.translate(s) || s;
  function tint(img, color) {
    let colors = tinted.get(img); if (!colors) { colors = new Map(); tinted.set(img, colors); }
    if (!colors.has(color)) {
      const canvas = document.createElement('canvas'); canvas.width = img.naturalWidth || img.width; canvas.height = img.naturalHeight || img.height;
      const g = canvas.getContext('2d'); g.drawImage(img, 0, 0);
      g.globalCompositeOperation = 'multiply'; g.fillStyle = color; g.fillRect(0, 0, canvas.width, canvas.height);
      g.globalCompositeOperation = 'destination-in'; g.drawImage(img, 0, 0); colors.set(color, canvas);
    }
    return colors.get(color);
  }
  function eligible(c) {
    return enabled && hero && !hero.dead && hero.level >= 99 && !hero.mounted &&
      hero.quests?.some(q => q.id === 'raid_key' && !q.claimed) &&
      !hero.inventory?.some(i => i.item === c.shard && i.quantity > 0) &&
      !pending.includes(c.shard);
  }
  function ready(c) { const s = states.find(s => s.id === c.id); return eligible(c) && !s?.alive && !s?.channel; }
  function nearest() { return crosses.filter(c => ready(c) && Math.hypot(hero.x-c.x,hero.y-c.y) <= 2.6).sort((a,b)=>Math.hypot(hero.x-a.x,hero.y-a.y)-Math.hypot(hero.x-b.x,hero.y-b.y))[0]; }
  function summon(c) {
    if (!ready(c) || Math.hypot(hero.x-c.x,hero.y-c.y)>2.6 || !window.Field?.canAct) return false;
    Field.clearInput(); Field.hero.target = null; Field.hero.goal = null;
    return Online.send({ type: 'raid_cross', id: c.id });
  }
  return {
    sync(packet, own, zone) {
      pending = (packet.drops || []).filter(d=>d.owner===own.id).map(d=>d.item);
      hero = own; enabled = Array.isArray(packet.raidCrosses); states = packet.raidCrosses || [];
      crosses = (zone ? WORLD_MAP.zones[zone-1] : WORLD_MAP).crosses || [];
    },
    get crosses() { return crosses; }, get imageReady() { return image.complete && image.naturalWidth > 0; },
    tint, eligible, ready, nearest,
    interact() { const c = nearest(); return c ? summon(c) : false; },
    click(mx, my, project) {
      const c = crosses.find(c => { const [x,y] = project(c.x,c.y); return Math.abs(mx-x)<34 && my>y-116 && my<y+8; });
      if (!c) return false; if (ready(c)) summon(c); return true;
    },
    draw(g, c, x, y) {
      const s = states.find(s => s.id === c.id), channel = s?.channel;
      g.save();
      g.fillStyle = 'rgba(20,14,20,.25)'; g.beginPath(); g.ellipse(x,y,34,11,0,0,Math.PI*2); g.fill();
      if (channel) {
        g.shadowColor = c.color; g.shadowBlur = 22; g.strokeStyle = c.color; g.lineWidth = 4;
        g.beginPath(); g.ellipse(x,y-4,40,17,0,0,Math.PI*2); g.stroke();
      }
      if (image.complete && image.naturalWidth) g.drawImage(tint(image,c.color),x-48,y-120);
      g.shadowBlur = 0;
      if (channel) {
        g.fillStyle = '#241c26'; g.fillRect(x-42,y-139,84,9);
        g.fillStyle = c.color; g.fillRect(x-40,y-137,80*(1-channel.left/3),5);
        g.font = 'bold 13px sans-serif'; g.textAlign = 'center'; g.fillStyle = '#fff0d1';
        g.fillText(tr('Communing…') + ' ' + channel.left.toFixed(1),x,y-146);
      } else if (ready(c) && Math.hypot(hero.x-c.x,hero.y-c.y)<=2.6) {
        const text = tr('Commune with the cross') + ' · ' + Keys.label('interact',false);
        g.font = 'bold 14px sans-serif'; g.textAlign = 'center'; g.lineWidth = 4; g.strokeStyle = '#201724';
        g.strokeText(text,x,y-128); g.fillStyle = '#ffe5aa'; g.fillText(text,x,y-128);
      }
      g.restore();
    }
  };
})();
