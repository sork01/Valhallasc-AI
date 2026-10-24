module.exports = (kit,map) => ({
  description:'Ember Key: real camp acceptance, interrupted channel, personal shard and permanent raid door gate.',
  startLevel:99,levelSpread:0,godMode:true,
  async run(w,check) {
    const bot='EmberSeeker',q=map.zones[44].quests.find(q=>q.id==='raid_key');
    await w.connect({bot,class:'hunter'});
    await kit.teleport(w,bot,{npc:'raid_key_keeper'});
    await kit.talkTo(w,bot,'raid_key_keeper','quest:accept:raid_key');
    check(w.player(bot).quests.some(p=>p.id==='raid_key'&&!p.claimed),'Level-99 hero accepts at the Emberwake camp');
    const c=map.crosses[0];await kit.teleport(w,bot,{zone:0,x:c.x,y:c.y+1});
    await w.action(bot,{type:'raid_cross',id:c.id});
    await w.waitFor(()=>w.views.get(bot).raidCrosses?.[0]?.channel,5000,'Three-second channel starts');
    check(true,'Cross broadcasts its channel');
    await w.action(bot,{type:'move',x:c.x,y:c.y+1.5});await w.advance(500);await w.action(bot,{type:'stop'});
    await w.waitFor(()=>!w.views.get(bot).raidCrosses[0].channel,5000,'Movement interrupts channel');
    check(!w.views.get(bot).slimes.some(s=>s.kind==='ember_firelord'&&!s.dead),'Interrupted channel spawns no herald');
    await kit.teleport(w,bot,{zone:0,x:c.x,y:c.y+1});
    await w.action(bot,{type:'raid_cross',id:c.id});
    const boss=await w.waitFor(()=>w.views.get(bot).slimes.find(s=>s.kind==='ember_firelord'&&!s.dead),10000,'Firelord rises');
    check(boss.level===99,'The summoned herald is level 99');
    const before={gold:w.player(bot).gold,xp:w.player(bot).xp};
    await kit.teleport(w,bot,{zone:0,x:boss.x,y:boss.y});await w.debug(bot,{op:'kill_enemy',id:boss.id});
    await w.waitFor(()=>w.player(bot).inventory.some(i=>i.item===c.shard),5000,'Private shard is collected');
    check(w.player(bot).gold===before.gold&&w.player(bot).xp===before.xp,'Firelord pays no gold or XP');
    check(w.views.get(bot).drops.every(d=>d.item===c.shard),'Firelord pays no ordinary loot');
    for(const o of q.objectives.slice(1,9))await w.debug(bot,{op:'give_item',item:o.target,quantity:1,force:true});
    await kit.teleport(w,bot,{zone:45,x:133,y:25.6});await w.action(bot,{type:'move',x:133,y:24});await w.advance(1000);await w.action(bot,{type:'stop'});
    check(w.player(bot).zone===45,'Nine pieces cannot open the raid door');
    await w.debug(bot,{op:'give_item',item:q.objectives[9].target,quantity:1,force:true});
    await kit.teleport(w,bot,{npc:'raid_key_keeper'});await kit.talkTo(w,bot,'raid_key_keeper','quest:claim:raid_key');
    await w.waitFor(()=>w.player(bot).quests.some(q=>q.id==='raid_key'&&q.claimed),5000,'Ember Key is forged');
    check(w.player(bot).inventory.some(i=>i.item==='ember_key'),'Quest grants the Ember Key');
    check(q.objectives.every(o=>w.player(bot).inventory.some(i=>i.item===o.target)),'All ten shards remain after claiming');
    await kit.teleport(w,bot,{zone:45,x:133,y:25.6});await w.action(bot,{type:'move',x:133,y:24});
    await w.waitFor(()=>w.player(bot).zone===46,15000,'Completed quest opens muster door');await w.action(bot,{type:'stop'});
    check(true,'A keyed hero enters the raid muster');
  }
});
