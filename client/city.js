'use strict';
// Original canvas artwork, inspired by Prontera's stone plazas and timber houses.
(() => {
  const city = WORLD_MAP.city, npcs = WORLD_MAP.npcs || [], cache = new Map();
  const iso = (x, y, z = 0) => [(x - y) * 44, (x + y) * 22 - z];
  const inside = (x, y) => city && x >= city.x0 && x <= city.x1 && y >= city.y0 && y <= city.y1;
  function poly(g, points, fill, stroke = '#54483e', line = 2) {
    g.beginPath(); points.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath();
    g.fillStyle = fill; g.fill(); if (stroke) { g.strokeStyle = stroke; g.lineWidth = line; g.lineJoin = 'round'; g.stroke(); }
  }
  function line(g, points, color, width = 2) {
    g.beginPath(); points.forEach(([x,y],i) => i ? g.lineTo(x,y) : g.moveTo(x,y)); g.strokeStyle = color; g.lineWidth = width; g.stroke();
  }
  function ellipse(g,x,y,rx,ry,col,stroke) { g.beginPath(); g.ellipse(x,y,rx,ry,0,0,Math.PI*2); g.fillStyle=col; g.fill(); if(stroke){g.strokeStyle=stroke;g.lineWidth=2;g.stroke();} }
  function prism(g, w, d, h, top, left, right, z = 0) {
    const a=iso(-w/2,-d/2,z+h), b=iso(w/2,-d/2,z+h), c=iso(w/2,d/2,z+h), e=iso(-w/2,d/2,z+h);
    poly(g,[e,c,iso(w/2,d/2,z),iso(-w/2,d/2,z)],left);
    poly(g,[b,c,iso(w/2,d/2,z),iso(w/2,-d/2,z)],right);
    poly(g,[a,b,c,e],top);
  }
  function text(g, value, x, y, size=17, color='#fff2d5') {
    g.font=`${size}px "Jua", sans-serif`; g.textAlign='center'; g.lineWidth=4; g.strokeStyle='#463d36';g.strokeText(value,x,y);g.fillStyle=color;g.fillText(value,x,y);
  }
  function stoneTile(g, px, py, x, y) {
    const inCity=inside(x+.5,y+.5), road=y>=69 && y<city.y0 && Math.abs(x+.5-36)<1.6;
    if (!inCity && !road) return false;
    const garden=inCity && Math.abs(x+.5-36)>7 && (y<78 || y>88);
    if(garden) { poly(g,[[px,py],[px+44,py+22],[px,py+44],[px-44,py+22]],'#779969',null);return true; }
    const plaza=Math.hypot(x+.5-city.plaza.x,y+.5-city.plaza.y)<city.radius;
    for(let a=0;a<4;a++) for(let b=0;b<4;b++) {
      const p=iso(a/4,b/4), tone=((x*17+y*31+a*7+b*13)%9);
      const color=plaza?`hsl(40, 22%, ${72+tone}%)`:`hsl(38, 13%, ${62+tone}%)`;
      poly(g,[[px+p[0],py+p[1]],[px+p[0]+11,py+p[1]+5.5],[px+p[0],py+p[1]+11],[px+p[0]-11,py+p[1]+5.5]],color,'#aa9f8b',.65);
    }
    return true;
  }
  function building(g,o) {
    const w=o.width,d=o.depth,h=o.kind==='chapel'?150:117, roof=o.color;
    ellipse(g,12,35,135,42,'#37362833');
    prism(g,w+.25,d+.25,12,'#c9beb0','#a89b8b','#918879');
    prism(g,w,d,h,'#e8dbb9','#efdfbb','#ccbfa2',12);
    // Timber frames on the two street-facing walls.
    for (const side of ['x','y']) {
      const point=(t,z)=>side==='x'?iso(t,d/2,z):iso(w/2,t,z);
      const half=side==='x'?w/2:d/2;
      for(const z of [25,69,h+8])line(g,[point(-half,z),point(half,z)],'#76533d',7);
      for(const t of [-half,0,half])line(g,[point(t,13),point(t,h+12)],'#76533d',7);
      line(g,[point(-half,72),point(-.1,h+5)],'#99704c',4);line(g,[point(.1,h+5),point(half,72)],'#99704c',4);
      // Inset windows with glowing panes and wooden shutters.
      for(const t of [-.9,.9]) {
        const z=94, span=.33;
        poly(g,[point(t-span,z+19),point(t+span,z+19),point(t+span,z-16),point(t-span,z-16)],'#537787','#795638',3);
        line(g,[point(t,z+19),point(t,z-16)],'#e8d4a0',2);line(g,[point(t-span,z),point(t+span,z)],'#e8d4a0',2);
        for(const edge of [-1,1])poly(g,[point(t+edge*.38,z+21),point(t+edge*.55,z+21),point(t+edge*.55,z-18),point(t+edge*.38,z-18)],'#7e967a');
      }
    }
    // Street door, lintel and stoop.
    const door=t=>iso(t,d/2+.02,0);
    poly(g,[door(-.4),door(.4),iso(.4,d/2+.02,62),iso(-.4,d/2+.02,62)],'#77513b','#4f3c30',3);
    line(g,[iso(-.3,d/2+.04,8),iso(-.3,d/2+.04,53)],'#a77b4d',2);
    const knob=iso(.24,d/2+.05,29);ellipse(g,...knob,3,3,'#eacb75');
    prism(g,1.25,.5,8,'#e2d4ba','#bcac93','#a59b89');
    // Tall gabled roof. The ridge runs in the x direction.
    const rw=w+.65,rd=d+.65,rise=o.kind==='chapel'?90:69;
    const a=iso(-rw/2,-rd/2,h+12),b=iso(rw/2,-rd/2,h+12),c=iso(rw/2,rd/2,h+12),e=iso(-rw/2,rd/2,h+12);
    const r0=iso(-rw/2,0,h+12+rise),r1=iso(rw/2,0,h+12+rise);
    poly(g,[b,c,r1],'#ddcbb0','#6a5042',3);
    poly(g,[a,b,r1,r0],roof,'#6a5042',3);poly(g,[r0,r1,c,e],roof,'#6a5042',3);
    // Rows of individually staggered terracotta/slate shingles.
    for(let row=1;row<8;row++) {
      const t=row/8;
      line(g,[iso(-rw/2,rd/2*t,h+12+rise*(1-t)),iso(rw/2,rd/2*t,h+12+rise*(1-t))],'#f4d3b855',1.4);
      for(let col=0;col<10;col++) {
        const x=-rw/2+(col+(row%2)*.5)*rw/10;
        line(g,[iso(x,rd/2*(t-.12),h+12+rise*(1-t+.12)),iso(x,rd/2*t,h+12+rise*(1-t))],'#573d3844',1);
      }
    }
    line(g,[r0,r1],'#eacbaa',5);
    // Chimney and guild pennant.
    g.save();const chimney=iso(-.9,-.5,h+50);g.translate(...chimney);prism(g,.4,.4,58,'#d8bc9a','#a2866c','#796b5b');g.restore();
    if(o.kind==='chapel') {
      g.save();g.translate(...iso(.6,0,h+rise+12));prism(g,.65,.65,62,'#aeb9bd','#d9d4c1','#aaa99e');
      poly(g,[[-35,-77],[0,-118],[35,-77],[0,-59]],roof);line(g,[[0,-118],[0,-142]],'#d5b56d',5);line(g,[[-11,-134],[11,-134]],'#d5b56d',4);g.restore();
    } else {
      const [bx,by]=iso(w/2+.04,-.7,h+6);line(g,[[bx,by],[bx,by+56]],'#574b3c',3);poly(g,[[bx,by+7],[bx+22,by+12],[bx+20,by+41],[bx+10,by+35],[bx,by+40]],'#d7b15f');
    }
    const sign=iso(0,d/2+.13,79);g.fillStyle='#594739';g.fillRect(sign[0]-90,sign[1]-11,180,25);text(g,o.label,sign[0],sign[1]+7,15,'#ffe7ad');
    // Pots of flowers on the doorstep.
    for(const side of [-1,1]) {const [x,y]=iso(side*1.3,d/2+.15);poly(g,[[x-8,y-3],[x+8,y-3],[x+5,y+12],[x-5,y+12]],'#ad7054');ellipse(g,x,y-7,15,9,'#5b8850');for(let k=0;k<4;k++)ellipse(g,x-9+k*6,y-11-(k%2)*4,3,3,['#edb6c0','#f1d57e'][k%2]);}
  }
  function fountain(g) {
    ellipse(g,10,12,95,39,'#3b493430');
    ellipse(g,0,8,78,37,'#918c83','#6c716c');ellipse(g,0,0,78,37,'#e3d9c0','#8c938e');ellipse(g,0,0,65,29,'#6ea8b2','#a8bfc0');ellipse(g,-8,-5,46,19,'#8dc9ce');
    prism(g,.65,.65,67,'#e7e5cf','#c5c9bc','#9caeaa');ellipse(g,0,-66,35,15,'#e2dfcd','#8c9d9c');ellipse(g,0,-69,28,10,'#77bac7');
    prism(g,.3,.3,40,'#ece8d4','#d5d7c8','#acbcb6',68);ellipse(g,0,-108,9,6,'#e1ded0');
    for(const dx of [-25,25])line(g,[[dx,-66],[dx*1.3,-34],[dx*1.6,-5]],'#cbf3efb0',3);
  }
  function objectArt(g,o) {
    if(o.kind==='house'||o.kind==='chapel')return building(g,o);
    if(o.kind==='fountain')return fountain(g);
    if(o.kind==='wall') {prism(g,o.width,o.depth,39,'#d7d3bc','#afa993','#949c91');for(let i=-1;i<=1;i++){g.save();g.translate(...iso(o.width>o.depth?i*o.width/3:0,o.depth>o.width?i*o.depth/3:0,39));prism(g,.32,.32,12,'#e4dfc9','#c0b8a0','#a9ac9d');g.restore();}return;}
    if(o.kind==='gate') {prism(g,1.1,1.1,119,'#dad5be','#b9b4a1','#939e95');prism(g,1.35,1.35,17,'#e7dec3','#bab79f','#9ca899',119);line(g,[[0,-148],[0,-215]],'#70593f',4);poly(g,[[0,-214],[32,-205],[25,-182],[0,-188]],'#ac6570');text(g,'✦',13,-194,14);return;}
    if(o.kind==='lamp') {ellipse(g,0,0,13,6,'#8a8f7c');line(g,[[0,0],[0,-106]],'#465d58',6);line(g,[[-16,-105],[16,-105]],'#465d58',4);poly(g,[[-13,-108],[-9,-133],[9,-133],[13,-108]],'#ffdea0','#526960',3);poly(g,[[-16,-135],[0,-147],[16,-135]],'#60736a');return;}
    if(o.kind==='flowers') {prism(g,1,.7,11,'#8c9d69','#b9b19a','#989f89');for(let i=0;i<16;i++){const x=Math.sin(i*13)*23,y=Math.cos(i*9)*9;line(g,[[x,y],[x,y-16]],'#58824d',2);ellipse(g,x,y-16,4,3,['#f4d99b','#e69fb4','#c7c0df'][i%3]);}return;}
    if(o.kind==='bench') {prism(g,1.5,.45,17,'#b69364','#8c704e','#6f6551');line(g,[[-33,-18],[-33,-43],[30,-16],[30,7]],'#6b705e',5);line(g,[[-33,-39],[30,-10]],'#b69364',13);return;}
    if(o.kind==='stall') {
      prism(g,1.8,1.2,37,'#cbac78','#a78960','#857053');
      for(const side of [-1,1])line(g,[iso(side*.9,.6),iso(side*.9,.6,95)],'#836649',5);
      for(let i=0;i<8;i++){const x=-1+i*.25;poly(g,[iso(x,-.7,106),iso(x+.25,-.7,106),iso(x+.25,.85,86),iso(x,.85,86)],i%2?'#efdfc1':o.color,null);}
      line(g,[iso(-1,.85,86),iso(1,.85,86)],'#745d48',3);
      for(let i=0;i<7;i++){const [x,y]=iso(-.6+i*.2,.2,44);ellipse(g,x,y,6,4,o.label==='Market'?'#b9cf95':'#eac085','#a88959');}
      text(g,o.label,0,-112,17);return;
    }
  }
  function drawObject(g,o,sx,sy,fade=1) {
    const key=JSON.stringify([o.kind,o.width,o.depth,o.color,o.label]);let sprite=cache.get(key);
    if(!sprite){const c=document.createElement('canvas');c.width=720;c.height=940;const cg=c.getContext('2d');cg.scale(2,2);cg.translate(180,400);objectArt(cg,o);sprite=c;cache.set(key,c);}
    g.save();g.globalAlpha=fade;g.drawImage(sprite,sx-180,sy-400,360,470);g.restore();
  }
  function drawNpc(g,n,sx,sy,t,near) {
    g.save();g.translate(sx,sy);const bob=Math.sin(t*2+n.x)*1.2;
    ellipse(g,0,1,21,9,'#233d3833');
    if(near){g.strokeStyle='#ffe2a2';g.lineWidth=2;g.beginPath();g.ellipse(0,0,27,12,0,0,Math.PI*2);g.stroke();}
    g.translate(0,bob);line(g,[[-8,-26],[-9,-5]],'#584d46',10);line(g,[[8,-26],[9,-5]],'#584d46',10);
    poly(g,[[-15,-64],[15,-64],[20,-25],[-20,-25]],n.color,'#4a4543',2.5);
    if(['baker','smith','innkeeper','apothecary'].includes(n.id))poly(g,[[-8,-57],[8,-57],[12,-26],[-12,-26]],'#e7d6b4');
    line(g,[[-15,-57],[-24,-33]],n.color,11);line(g,[[15,-57],[24,-33]],n.color,11);ellipse(g,-24,-30,5,6,'#eac3a0');ellipse(g,24,-30,5,6,'#eac3a0');
    ellipse(g,0,-77,18,20,'#edc5a1','#634d42');
    poly(g,[[-18,-80],[-17,-93],[-6,-100],[12,-96],[19,-84],[10,-84],[6,-92],[-5,-83]],n.id==='healer'?'#eae8df':n.id==='smith'?'#8a6550':'#755841');
    ellipse(g,-6,-77,2,2.8,'#443c39');ellipse(g,6,-77,2,2.8,'#443c39');line(g,[[-4,-66],[0,-64],[4,-66]],'#a86b5d',1.5);
    if(n.id==='gatekeeper'){poly(g,[[-19,-91],[-12,-105],[12,-105],[20,-91]],'#a4b5c0');line(g,[[29,-8],[29,-107]],'#7a6954',3);poly(g,[[25,-108],[29,-123],[33,-108]],'#d6d9ce');}
    if(n.id==='baker'){ellipse(g,-9,-103,10,9,'#f6ecd2');ellipse(g,8,-103,12,10,'#f6ecd2');g.fillStyle='#f6ecd2';g.fillRect(-17,-103,34,12);}
    const mark=window.Quests?.marker(n.id);if(mark)text(g,mark,0,-154,25,'#ffdf88');
    text(g,n.name,0,-128,17);text(g,near?'[ E ] Talk':n.role,0,-110,13,near?'#ffdf88':'#e0dfcd');g.restore();
  }
  function drawPlaza(g,w2s) {
    const [x,y]=w2s(city.plaza.x,city.plaza.y);
    for(const radius of [city.radius,city.radius-.2,2.3]) {g.beginPath();g.ellipse(x,y,radius*62.225,radius*31.112,0,0,Math.PI*2);g.strokeStyle='#eee2c5';g.lineWidth=radius===2.3?3:6;g.stroke();}
    for(let i=0;i<4;i++){const a=i*Math.PI/2;poly(g,[[x+Math.cos(a)*167,y+Math.sin(a)*83],[x+Math.cos(a+.13)*123,y+Math.sin(a+.13)*61],[x+Math.cos(a)*102,y+Math.sin(a)*51],[x+Math.cos(a-.13)*123,y+Math.sin(a-.13)*61]],'#b0a794',null);}
  }
  let current=null,previousFocus=null;
  const $=id=>document.getElementById(id);
  function dialogue(packet) {
    if(!Online.connected || Field.hero.dead)return;
    window.Quests?.close(false);
    previousFocus=current?previousFocus:document.activeElement;current=packet.npc;
    Field.setPaused(true);$('npc-dialogue').hidden=false;
    $('npc-name').textContent=current.name;$('npc-role').textContent=current.role;
    $('npc-text').textContent=current.dialogue;$('npc-notice').textContent=packet.notice;
    $('npc-gold').textContent=`Your purse: ${packet.gold} gold`;
    window.Quests?.update(packet.quests || []);
    window.Quests?.npc(current.id, $('npc-quests'));
    $('npc-offers').replaceChildren(...current.offers.map(offer=>{
      const b=document.createElement('button');b.type='button';b.className='btn ghost';b.dataset.offer=offer.id;
      b.textContent=offer.label+(offer.cost?` · ${offer.cost} gold`:' · free');
      b.disabled=packet.gold<offer.cost;
      b.addEventListener('click',()=>{if(Online.send({type:'interact',npc:current.id,offer:offer.id})) b.disabled=true;});return b;
    }));
    $('npc-close').focus({preventScroll:true});
  }
  function close(resume=true) {if(!current)return;current=null;$('npc-dialogue').hidden=true;if(resume){Field.setPaused(false);previousFocus?.focus?.({preventScroll:true});}}
  $('npc-close').addEventListener('click',()=>close());
  $('npc-dialogue').addEventListener('keydown',event=>{
    if(event.key==='Tab') {const buttons=[...$('npc-dialogue').querySelectorAll('button:not(:disabled)')];const first=buttons[0],last=buttons.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}}
  });
  window.City={inside,stoneTile,drawObject,drawNpc,drawPlaza,npcs,dialogue,close,get open(){return !!current;}};
})();
