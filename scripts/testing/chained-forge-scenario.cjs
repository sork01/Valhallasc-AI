// RAID-MAP only: the released door opens into the physically separated muster.
module.exports=(kit,map)=>({
 description:'The Chained Forge floor: open door, inside-only contracts, ten-fighter gate, all ten halls and safe return.',
 startLevel:99,levelSpread:0,godMode:true,
 async run(w,check){
  const bot='ForgeWalker',area=map.zones[45];
  await w.connect({bot,class:'warrior'});
  await kit.teleport(w,bot,{zone:45,x:133,y:27});
  await w.action(bot,{type:'move',x:133,y:24});await w.advance(1600);await w.action(bot,{type:'stop'});
  check(w.player(bot).zone===46,'The authored raid door admits a level-99 player to muster');
  await kit.teleport(w,bot,{zone:46,x:30,y:303});
  check(w.views.get(bot).instance?.template===46||w.player(bot).zone===46,'Private staging enters a raid copy');
  await w.debug(bot,{op:'set_gold',gold:2000000});
  await w.action(bot,{type:'move',x:30,y:296});await w.advance(1800);await w.action(bot,{type:'stop'});
  check(w.player(bot).y>294,'The inner gate refuses a group of one');
  await kit.teleport(w,bot,{npc:'cf_quartermaster'});
  for(const cls of ['warrior','warrior','mage','mage','assassin','assassin','priest','priest','hunter'])
    await kit.talkTo(w,bot,'cf_quartermaster','merc_'+cls);
  await w.waitFor(()=>w.views.get(bot).players.filter(p=>p.look.name.startsWith('Merc ')).length===9,10000,'Nine raid hires');
  check(w.player(bot).gold===965000,'Nine contracts charge the normal level-99 price');
  check(w.views.get(bot).players.length===10,'Ten fighters gather inside the raid, no outdoor overflow');
  check(map.zones[44].npcs.every(n=>(n.offers||[]).every(o=>!o.raid)),'Outdoor services cannot issue nine-fighter raid contracts');
  await w.connect({bot:'ForgeObserver',class:'mage'});
  await kit.teleport(w,'ForgeObserver',{zone:46,x:30,y:303});
  const observerId=w.player('ForgeObserver').id,heroId=w.player(bot).id;
  check(!w.views.get(bot).players.some(p=>p.id===observerId)&&!w.views.get('ForgeObserver').players.some(p=>p.id===heroId),'Separate groups get isolated raid copies');

  await w.action(bot,{type:'move',x:30,y:296});
  await w.waitFor(()=>Math.hypot(w.player(bot).x-62,w.player(bot).y-290)<3,15000,'The ten-fighter gate');
  await w.action(bot,{type:'stop'});check(true,'The inner gate admits the complete company');
  const times=[];
  for(const h of area.forgeHalls){
    const began=Date.now();
    for(const [x,y]of h.route.slice(1))await kit.walkTo(w,bot,{x,y},90000);
    check(Math.hypot(w.player(bot).x-h.x,w.player(bot).y-h.y)<.6,'Walked the real collision to '+h.name);
    times.push({hall:h.id,seconds:(Date.now()-began)/1000});
    require('node:fs').writeFileSync(require('node:path').join(w.runDir,'chained-forge-walk-times.txt'),JSON.stringify(times,null,2));
  }
  check(area.slimes.filter(s=>['cf_brute','cf_crawler','cf_caster','cf_sentry'].includes(s.kind)).length===40,'RAID-PACKS populates forty pack actors beside the Warden encounters');
  await kit.teleport(w,bot,{zone:46,x:30,y:303});
  await w.action(bot,{type:'move',x:22,y:303});await w.waitFor(()=>w.player(bot).zone===45,15000,'Raid exit');
  await w.action(bot,{type:'stop'});
  await w.waitFor(()=>!w.views.get(bot).players.some(p=>p.look.name.startsWith('Merc ')),5000,'Contracts end outside');
  check(Math.hypot(w.player(bot).x-127,w.player(bot).y-25)<2,'Exit is clear of the door and does not bounce');
  check(!w.views.get(bot).players.some(p=>p.look.name.startsWith('Merc ')),'Raid contracts end before entering the outdoor company');
  console.error('Chained Forge measured walking: '+JSON.stringify(times));
 }
});
