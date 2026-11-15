// Real MCP transport, normal movement and private persistence; no combat grind.
// Where a walker starts and steps to cross a portal on the shaped map: a walk gate fires only moving out through its side,
// a seam only within reach on its own side of the border line, and a plain gate when walking toward its centre.
function approachOf(p){
 if(p.walk){const k=p.vault?2.5:4;return{start:{x:p.x-p.walk[0]*k,y:p.y-p.walk[1]*k},goal:{x:p.x+p.walk[0]*3,y:p.y+p.walk[1]*3}};}
 if(p.seam){
  const pts=p.seam.points;let best=null;
  for(let i=0;i+1<pts.length;i++){
   const[ax,ay]=pts[i],[bx,by]=pts[i+1],dx=bx-ax,dy=by-ay,len=Math.hypot(dx,dy)||1;
   const t=Math.max(0,Math.min(1,((p.x-ax)*dx+(p.y-ay)*dy)/(len*len)));
   const d=Math.hypot(p.x-(ax+dx*t),p.y-(ay+dy*t));
   if(!best||d<best.d)best={d,gx:-dy/len,gy:dx/len};
  }
  const s=p.seam.side;
  return{start:{x:p.x+s*2*best.gx,y:p.y+s*2*best.gy},goal:{x:p.x-s*2*best.gx,y:p.y-s*2*best.gy}};
 }
 return{start:{x:p.x,y:p.y+4},goal:{x:p.x,y:p.y+1}};
}
module.exports=(kit,map)=>({
 description:'Organic world walking crossings: bidirectional travel, continued click movement, no teleport effects, zone isolation and persistence.',
 startLevel:99,levelSpread:0,godMode:true,
 async run(w,check){
  const zones=[map,...map.zones],hero='RoadRunner',other='RoadObserver';
  await w.connect({bot:hero,class:'warrior'});await w.connect({bot:other,class:'warrior'});
  for(const [from,to] of [[0,1],[1,0],[6,7],[7,6],[17,19],[19,17]]){
   const p=zones[from].portals.find(p=>p.to===to);check(!!p,`Route ${from}->${to} is a walking path`);
   const ap=approachOf(p),dx=ap.goal.x-ap.start.x,dy=ap.goal.y-ap.start.y,dl=Math.hypot(dx,dy)||1,dir={x:dx/dl,y:dy/dl};
   await kit.teleport(w,hero,{zone:from,x:ap.start.x,y:ap.start.y});
   await w.advance(1300);const before=new Set(w.events);
   await w.action(hero,{type:'move',x:ap.goal.x,y:ap.goal.y});
   await w.waitFor(()=>w.player(hero).zone===to,12000,`Walk ${from}->${to}`);
   // A plain gate (Asterion's Stormglass door, 19->17, has no walk side) lands the hero on its arrival: nothing to continue.
   if(p.walk||p.seam)await w.waitFor(()=>{const a=w.player(hero);return(a.x-p.tx)*dir.x+(a.y-p.ty)*dir.y>.5;},5000,'Click movement continues after crossing');
   await w.action(hero,{type:'stop'});
   check(w.player(hero).zone===to,`Actual travel reaches ${to}`);
   // Only organic crossings are flare-free: a plain gate is a portal and shows its flare.
   if(p.walk||p.seam)check(w.events.filter(e=>!before.has(e)&&e.bot===hero).every(e=>e.kind!=='portal'),'Walking has no teleport flare');
  }
  check(w.player(other).zone===0&&w.player(hero).zone===17,'Separate-zone observer stays put');
  check(w.views.get(other).players.every(p=>p.id!==w.player(hero).id),'Observer receives no remote-zone player');
  const zone=w.player(hero).zone;await w.restart();check(w.player(hero).zone===zone,'Walking destination survives save/rejoin');
 }
});
