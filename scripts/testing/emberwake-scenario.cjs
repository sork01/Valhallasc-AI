// New zone only: real movement, both gates, quests, kill drops and persistence.
module.exports=(kit,map)=>({
  description:'Emberwake Caldera: walk from Asterion to the sealed raid door, quests, outdoor loot and return.',
  startLevel:99,levelSpread:0,godMode:true,
  async run(w,check){
    const bot='EmberWalker',area=map.zones[44];
    const q=id=>w.player(bot).quests.find(q=>q.id===id);
    await w.connect({bot,class:'warrior'});
    await kit.teleport(w,bot,{zone:17,x:90,y:42});
    await kit.walkTo(w,bot,{x:90,y:25});
    await w.action(bot,{type:'move',x:90,y:18});
    await w.waitFor(()=>w.player(bot).zone===45,15000,'Asterion gate');
    await w.action(bot,{type:'stop'});
    check(Math.hypot(w.player(bot).x-22,w.player(bot).y-137)<2,'Asterion gate reaches a safe caldera arrival');
    check(w.views.get(bot).slimes.length===area.slimes.length,'Only Emberwake enemies are in the view');
    await kit.talkTo(w,bot,'ew_guide','quest:accept:ew_warm');
    await w.waitFor(()=>q('ew_warm'),5000,'Accept the road introduction');
    await kit.talkTo(w,bot,'ew_keeper');
    await w.waitFor(()=>q('ew_warm')?.counts[0]===1,5000,'Meet the linkkeeper');
    await kit.talkTo(w,bot,'ew_guide','quest:claim:ew_warm');
    await w.waitFor(()=>q('ew_warm')?.claimed,5000,'Claim introduction');
    await kit.talkTo(w,bot,'ew_guide','quest:accept:ew_road');
    await w.waitFor(()=>q('ew_road'),5000,'Accept road quest');
    // Stage completed kills instead of grinding six large level-99 enemies.
    await w.debug(bot,{op:'quest',id:'ew_road',action:'complete'});
    await kit.talkTo(w,bot,'ew_guide','quest:claim:ew_road');
    await w.waitFor(()=>q('ew_road')?.claimed,5000,'Claim road quest');
    await kit.talkTo(w,bot,'ew_guide','quest:accept:ew_voice');
    await w.waitFor(()=>q('ew_voice'),5000,'Accept Eldmarr quest');
    for(const [x,y]of area.paths[0].slice(1))await kit.walkTo(w,bot,{x,y},120000);
    check(w.player(bot).zone===45&&Math.hypot(w.player(bot).x-133,w.player(bot).y-26)<2,'The whole chain road can be walked to the raid door');
    const seal=await kit.talkTo(w,bot,'ew_seal');
    check(JSON.stringify(seal).includes('sealed'),'The Nine-Chain Door explains that the raid is sealed');
    await kit.talkTo(w,bot,'ew_echo');
    await w.waitFor(()=>q('ew_voice')?.counts[0]===1,5000,'Hear Eldmarr');
    check(!area.portals.some(p=>p.id==='ew_raid'),'There is no traversable raid portal before RAID-OPEN');
    for(const kind of ['ew_ashback','ew_glasswing','ew_slagjaw','ew_cinderhorn']){
      const enemy=w.views.get(bot).slimes.find(s=>s.kind===kind&&!s.dead);
      await w.debug(bot,{op:'kill_enemy',id:enemy.id});
      await w.waitFor(()=>w.views.get(bot).drops.some(d=>d.item===kind+'_relic'),5000,kind+' material');
      check(true,kind+' pays its authored material through the normal kill path');
    }
    await kit.teleport(w,bot,{npc:'ew_keeper'});
    await kit.talkTo(w,bot,'ew_keeper','quest:accept:ew_link');
    await w.waitFor(()=>q('ew_link'),5000,'Accept elite quest');
    const elite=w.views.get(bot).slimes.find(s=>s.kind==='ew_chainmaw');
    await w.debug(bot,{op:'kill_enemy',id:elite.id});
    await w.waitFor(()=>q('ew_link')?.counts[0]===1,5000,'Elite kill credit');
    await kit.talkTo(w,bot,'ew_keeper','quest:claim:ew_link');
    await w.waitFor(()=>q('ew_link')?.claimed,5000,'Claim elite quest');
    await kit.talkTo(w,bot,'ew_guide','quest:claim:ew_voice');
    await w.waitFor(()=>q('ew_voice')?.claimed,5000,'Claim Eldmarr quest');
    await kit.walkTo(w,bot,{x:20,y:140});await w.action(bot,{type:'move',x:14,y:140});
    await w.waitFor(()=>w.player(bot).zone===17,15000,'Return gate');
    await w.action(bot,{type:'stop'});
    check(Math.hypot(w.player(bot).x-90,w.player(bot).y-25)<2,'Return lands outside Asterion gate without bouncing');
    await w.restart();
    check(w.player(bot).zone===17&&['ew_warm','ew_road','ew_voice','ew_link'].every(id=>q(id)?.claimed),'Quest claims and safe return survive restart');
  }
});
