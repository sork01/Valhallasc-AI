'use strict';
// The server calendar owns the ritual, encounter and personal daily chance.
(() => {
 let state=null,rolls={},day=0,source=null,loading=null;
 const lantern={kind:'halloweenLantern',x:105,y:32,r:0};
 City.art.halloweenLantern={box:[180,230,90,195],draw(g){
  const {prism,ellipse,line}=City.kit;
  ellipse(g,0,0,59,21,'#291c3855');prism(g,1.1,1.1,22,'#656276','#494257','#2b293d');
  line(g,[[0,-22],[0,-124],[28,-124],[28,-102]],'#483344',9);
  ellipse(g,28,-76,27,29,'#a94f28','#2c2238',3);ellipse(g,28,-76,20,25,'#f5a93d');
  line(g,[[13,-81],[20,-86],[22,-76]],'#39273b',4);line(g,[[43,-81],[36,-86],[34,-76]],'#39273b',4);
  line(g,[[16,-65],[28,-58],[40,-65]],'#ffe7a3',4);
  line(g,[[-18,-24],[-18,-42],[18,-42],[18,-24]],'#c09263',3);
 }};
 window.Halloween={
  sync(next,nextRolls,seasons){state=next;rolls=nextRolls||{};day=seasons?.find(s=>s.id==='halloween')?.day||0;},
  get source(){return source;},
  load(){if(source)return Promise.resolve();if(loading)return loading;
   if(window.__valhallaTestSprites){const c=document.createElement('canvas');c.width=768;c.height=480;const g=c.getContext('2d');g.fillStyle='#e38837';for(let y=0;y<5;y++)for(let x=0;x<8;x++)g.fillRect(x*96+26,y*96+20,44,68);source={meta:{frame:[96,96],anchor:[48,90],clips:{idle:{fps:6,n:6,row:0},walk:{fps:10,n:8,row:1},attack:{fps:12,n:8,row:2},hurt:{fps:10,n:4,row:3},die:{fps:8,n:8,row:4}}},img:{hollow_rider:c}};return Promise.resolve();}
   loading=fetch('assets/halloween.txt').then(r=>r.json()).then(async meta=>{const img=new Image();img.src='assets/halloween_hollow_rider.png';await img.decode();source={meta,img:{hollow_rider:img}};}).catch(()=>{}).finally(()=>{loading=null;});return loading;
  },
  objects(zone){return state&&zone===3?[lantern]:[];},
  drawFloor(g,zone,w2s){if(!state||zone!==3)return;const[x,y]=w2s(state.x,state.y);g.save();g.fillStyle='#24172a55';g.strokeStyle=state.active?'#f5b15f':'#a97baf';g.lineWidth=4;
   g.beginPath();g.ellipse(x,y,state.radius*62.225,state.radius*31.112,0,0,Math.PI*2);g.fill();g.stroke();g.lineWidth=2;
   for(let i=0;i<12;i++){const a=i*Math.PI/6,[px,py]=w2s(state.x+Math.cos(a)*8.3,state.y+Math.sin(a)*8.3);g.fillStyle=i%2?'#eba04c':'#9872af';g.fillRect(px-4,py-3,8,6);}
   g.restore();
  },
  drawLabel(g,zone,w2s){if(!state||zone!==3)return;const[x,y]=w2s(105,32,160);g.save();g.font='20px "Jua",sans-serif';g.textAlign='center';g.strokeStyle='#221a32';g.lineWidth=5;g.fillStyle='#ffe0a3';
   const lines=[state.active?`The Hollow Rider · Level ${state.level}`:'Five fighters · average party level',rolls.halloween_hunt===day?'Daily mount roll used · resets at Stockholm midnight':'Daily Nightmare Steed chance: 1% per hero'];
   lines.forEach((t,i)=>{const text=window.Locale?.translate(t)||t;g.strokeText(text,x,y+i*25);g.fillText(text,x,y+i*25);});g.restore();
  }
 };
})();
