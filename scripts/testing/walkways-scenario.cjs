// Real MCP transport, normal movement and private persistence; no combat grind.
module.exports=(kit,map)=>({
 description:'Organic world walking crossings: bidirectional travel, continued click movement, no teleport effects, zone isolation and persistence.',
 startLevel:99,levelSpread:0,godMode:true,
 async run(w,check){
  const zones=[map,...map.zones],hero='RoadRunner',other='RoadObserver';
  await w.connect({bot:hero,class:'warrior'});await w.connect({bot:other,class:'warrior'});
  for(const [from,to] of [[0,1],[1,0],[6,7],[7,6],[17,19],[19,17]]){
   const p=zones[from].portals.find(p=>p.to===to);check(!!p?.walk,`Route ${from}->${to} is a walking path`);
   await kit.teleport(w,hero,{zone:from,x:p.x-p.walk[0]*6,y:p.y-p.walk[1]*6});
   await w.advance(1300);const before=new Set(w.events);
   await w.action(hero,{type:'move',x:p.x+p.walk[0]*3,y:p.y+p.walk[1]*3});
   await w.waitFor(()=>w.player(hero).zone===to,12000,`Walk ${from}->${to}`);
   await w.waitFor(()=>{const a=w.player(hero);return(a.x-p.tx)*p.walk[0]+(a.y-p.ty)*p.walk[1]>.5;},5000,'Click movement continues after crossing');
   await w.action(hero,{type:'stop'});
   check(w.player(hero).zone===to,`Actual travel reaches ${to}`);
   check(w.events.filter(e=>!before.has(e)&&e.bot===hero).every(e=>e.kind!=='portal'),'Walking has no teleport flare');
  }
  check(w.player(other).zone===0&&w.player(hero).zone===17,'Separate-zone observer stays put');
  check(w.views.get(other).players.every(p=>p.id!==w.player(hero).id),'Observer receives no remote-zone player');
  const zone=w.player(hero).zone;await w.restart();check(w.player(hero).zone===zone,'Walking destination survives save/rejoin');
 }
});
