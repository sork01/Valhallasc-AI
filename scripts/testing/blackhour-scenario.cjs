// Foundry only: real protocol setup, kills and claims, no gear/progression grind.
module.exports=(kit,map)=>({
 description:'Black Hour Foundry: level gate, private copies, both exits, epic drops, quests and persistence.',
 startLevel:99,levelSpread:0,godMode:true,
 async run(w,check){
  const hero='NullRunner',ally='NullAlly',other='NullOther',low='NullLow';
  const q=(bot,id)=>w.player(bot).quests.find(q=>q.id===id);
  const enter=async bot=>{
   await kit.teleport(w,bot,{zone:28,x:214,y:200});await w.action(bot,{type:'move',x:208,y:200});
   await w.waitFor(()=>w.player(bot).zone===44,15000,'Enter the Foundry');await w.action(bot,{type:'stop'});
  };
  for(const bot of [hero,ally,other,low])await w.connect({bot,class:'warrior'});
  await w.debug(low,{op:'set_level',level:98});await kit.teleport(w,low,{zone:28,x:214,y:200});
  const before=new Set(w.events);await w.action(low,{type:'move',x:208,y:200});
  await w.waitFor(()=>w.events.some(e=>!before.has(e)&&e.bot===low&&e.type==='error'&&/level 99/.test(e.text)),15000,'Level 98 refused');
  await w.action(low,{type:'stop'});check(w.player(low).zone===28,'Level-98 heroes remain in Yearwheel');
  await w.social(hero,{op:'party_invite',bot:ally});await w.social(ally,{op:'party_accept',bot:hero});
  for(const bot of [hero,ally])for(const [npc,id]of [['null_guide','null_entry'],['null_guide','null_bell'],['null_rigger','null_current']]){
   await kit.teleport(w,bot,{npc});await kit.talkTo(w,bot,npc,`quest:accept:${id}`);await w.waitFor(()=>!!q(bot,id),5000,'Accept '+id);
  }
  await enter(hero);await enter(ally);await enter(other);
  const ids=bot=>new Set(w.views.get(bot).slimes.map(s=>s.id));
  check([...ids(hero)].every(id=>ids(ally).has(id))&&[...ids(hero)].every(id=>!ids(other).has(id)),'Party shares its copy; another party has separate enemies');
  check(w.views.get(hero).slimes.filter(s=>!s.dead).length===15,'Four giant packs and three bosses load');
  await kit.teleport(w,hero,{npc:'null_witness'});await kit.talkTo(w,hero,'null_witness');
  await w.waitFor(()=>q(hero,'null_entry')?.counts[0]===1,5000,'Talk objective');
  await kit.teleport(w,hero,{zone:44,x:78,y:143});await w.action(hero,{type:'move',x:72,y:143});
  await w.waitFor(()=>w.player(hero).zone===28,12000,'Entrance return');
  await kit.teleport(w,hero,{npc:'null_guide'});await kit.talkTo(w,hero,'null_guide','quest:claim:null_entry');
  await w.waitFor(()=>q(hero,'null_entry')?.claimed,5000,'Entry claim');await enter(hero);
  for(const kind of ['null_hauler','null_breaker','null_coil']){
   const s=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);await w.debug(hero,{op:'kill_enemy',id:s.id});
   await w.waitFor(()=>w.views.get(hero).drops.some(d=>d.item===kind+'_relic'),5000,'Material '+kind);
   check(true,kind+' drops its own material');
  }
  const fs=require('node:fs'),path=require('node:path');
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../../world/items.txt'))),gear=new Map(catalog.filter(i=>i.source==='blackhour').map(i=>[i.id,i]));
  for(const [n,kind]of ['null_hour','null_bell','null_conductor'].entries()){
   const s=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);await w.debug(hero,{op:'kill_enemy',id:s.id});
   await w.waitFor(()=>w.views.get(hero).slimes.find(e=>e.id===s.id)?.dead,5000,'Kill '+kind);
   check(w.views.get(hero).instance.cleared===(n===2),'Final-first kill still waits for both side bosses');
   const rolls=w.events.filter(e=>e.bot===hero&&e.type==='roll'&&e.op==='start'&&gear.has(e.item));
   check(rolls.length>0&&rolls.every(r=>gear.get(r.item).rarity==='epic'),'Boss pools produce exclusive purple level-99 Nullforged gear');
  }
  await w.waitFor(()=>[hero,ally].every(bot=>['null_bell','null_current'].every(id=>q(bot,id)?.counts[0]===1)),5000,'Party quest credit');
  check(!w.views.get(other).instance.cleared&&w.views.get(other).slimes.filter(s=>!s.dead).length===15,'Other copy stays alive and uncleared');
  await kit.teleport(w,hero,{zone:44,x:80,y:18});await w.action(hero,{type:'move',x:80,y:13});
  await w.waitFor(()=>w.player(hero).zone===28,12000,'Clear exit');
  for(const [npc,id]of [['null_guide','null_bell'],['null_rigger','null_current']]){
   await kit.teleport(w,hero,{npc});await kit.talkTo(w,hero,npc,`quest:claim:${id}`);await w.waitFor(()=>q(hero,id)?.claimed,5000,'Claim '+id);
  }
  const rewards=['null_pants','null_accessory'];check(rewards.every(id=>w.player(hero).inventory.some(i=>i.item===id)),'Both boss quests award the epic shared pieces');
  await w.restart();check(w.player(hero).zone===28&&rewards.every(id=>w.player(hero).inventory.some(i=>i.item===id))&&['null_entry','null_bell','null_current'].every(id=>q(hero,id)?.claimed),'Rewards, claims and return survive server restart');
  check(map.zones[43].name==='The Black Hour Foundry'&&map.zones[27].portals.some(p=>p.to===44),'The entry is at Yearwheel’s Equinox Crossing');
 }
});
