// Only the new pack content; direct private fixtures avoid progression/grinding.
module.exports=(kit,map)=>({
 description:'Raid packs: sealed door, isolated 40 elite spawns, materials, unique shared purple gear and persistence.',
 startLevel:99,levelSpread:0,godMode:true,
 async run(w,check){
  const hero='CinderScout',other='CinderWitness',area=map.zones[45];
  await w.connect({bot:hero,class:'mage'});
  await kit.teleport(w,hero,{zone:46,x:30,y:303});
  await kit.teleport(w,hero,{zone:46,x:84,y:272});
  await w.connect({bot:other,class:'warrior'});await kit.teleport(w,other,{zone:46,x:84,y:272});
  const enemies=w.views.get(hero).slimes;
  check(enemies.length===40,'Ten real four-enemy packs');
  check(enemies.every(s=>s.elite),'Every pack enemy is a dungeon elite');
  check(new Set(enemies.map(s=>s.kind)).size===4,'Four ordinary raid kinds');
  check(area.sealedTemplate,'Public entrance remains sealed');
  check(w.views.get(other).slimes.every(s=>!enemies.some(e=>e.id===s.id)),'Another group has separate pack actors');
  for(const kind of ['cf_brute','cf_crawler','cf_caster','cf_sentry']){
   const s=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);
   await kit.teleport(w,hero,{zone:46,x:s.x+2,y:s.y});
   await w.debug(hero,{op:'kill_enemy',id:s.id});
   await w.waitFor(()=>w.views.get(hero).drops.some(d=>d.item===kind+'_relic'),5000,'Material '+kind);
   check(true,'Actual kill pays '+kind+' material');
  }
  check(area.quests.length===0,'No special elites or elite side quests');
  check(w.views.get(other).slimes.every(s=>!s.dead),'Other copy retains every enemy');
  // Fixed fixtures inspect gear once each. Never farm the 3% roll.
  const fs=require('node:fs'),path=require('node:path');
  const pieces=JSON.parse(fs.readFileSync(path.join(__dirname,'../../world/items.txt'))).filter(i=>i.source==='chained_forge_packs');
  check(pieces.length===3&&pieces.every(i=>i.rarity==='epic'&&i.requiredLevel===99&&!i.class),'Only original class-neutral level-99 purple pieces');
  for(const piece of pieces)await w.debug(hero,{op:'give_item',item:piece.id,quantity:1});
  await kit.teleport(w,hero,{zone:46,x:30,y:303});
  await w.action(hero,{type:'move',x:22,y:303});await w.waitFor(()=>w.player(hero).zone===45,15000,'Return to Emberwake');
  await w.action(hero,{type:'stop'});await w.restart();
  check(pieces.every(i=>w.player(hero).inventory.some(s=>s.item===i.id)),'Unique purple loot survives restart');
 }
});
