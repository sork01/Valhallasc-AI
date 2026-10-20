// Real private protocol coverage for the level-35 Rán’s Deep dungeon. No progression grind.
module.exports = (kit, map) => ({
  description: 'The Drowned Longship: level gate, both exits, party isolation, three quests, boss loot and saved rewards.',
  startLevel:35, levelSpread:0, godMode:true,
  async run(w,check) {
    const hero='KeelRunner', ally='KeelAlly', other='KeelOther', low='KeelLow';
    const longship=map.zones[42],parent=map.zones[7];
    const q=(bot,id)=>w.player(bot).quests.find(q=>q.id===id);
    const enter=async bot=>{
      await kit.teleport(w,bot,{zone:8,x:54,y:151});
      await w.action(bot,{type:'move',x:54,y:146});
      await w.waitFor(()=>w.player(bot).zone===43,12000,`${bot} enters the Keel`);
      await w.action(bot,{type:'stop'});
    };
    for(const bot of [hero,ally,other,low])await w.connect({bot,class:'warrior'});
    await w.debug(low,{op:'set_level',level:34});
    await kit.teleport(w,low,{zone:8,x:54,y:151});
    const before=new Set(w.events);
    await w.action(low,{type:'move',x:54,y:146});
    await w.waitFor(()=>w.events.some(e=>!before.has(e)&&e.bot===low&&e.type==='error'&&/level 35/.test(e.text)),12000,'Level 34 is refused');
    await w.action(low,{type:'stop'});
    check(w.player(low).zone===8,'Level-34 heroes stay in Rán’s Deep');
    await w.social(hero,{op:'party_invite',bot:ally});
    await w.social(ally,{op:'party_accept',bot:hero});
    for(const bot of [hero,ally]){
      for(const [npc,id] of [['keel_guide','keel_entry'],['keel_guide','keel_cargo'],['keel_rigger','keel_rigging']]){
        await kit.teleport(w,bot,{npc});
        await kit.talkTo(w,bot,npc,`quest:accept:${id}`);
        await w.waitFor(()=>!!q(bot,id),5000,`Accept ${id}`);
      }
    }
    await enter(hero);await enter(ally);await enter(other);
    await kit.teleport(w,hero,{npc:'keel_witness'});
    await kit.talkTo(w,hero,'keel_witness');
    await w.waitFor(()=>q(hero,'keel_entry')?.counts[0]===1,5000,'Speak to the Last Witness');
    await kit.teleport(w,hero,{zone:43,x:64,y:110});
    const ids=bot=>new Set(w.views.get(bot).slimes.map(s=>s.id));
    check([...ids(hero)].every(id=>ids(ally).has(id))&&[...ids(hero)].every(id=>!ids(other).has(id)),
      'Party members share enemies and another party has separate enemies');
    check(w.views.get(hero).slimes.filter(s=>!s.dead).length===15,'Twelve ordinary foes and three guardians occupy the dungeon');
    // Keep the ally in the copy while exercising the entrance return and actual claim.
    await w.action(hero,{type:'move',x:56,y:110});
    await w.waitFor(()=>w.player(hero).zone===8,15000,'Entrance return to Rán’s Deep');
    await kit.teleport(w,hero,{npc:'keel_guide'});
    await kit.talkTo(w,hero,'keel_guide','quest:claim:keel_entry');
    await w.waitFor(()=>q(hero,'keel_entry')?.claimed,5000,'Claim entry quest');
    await enter(hero);
    // Exercise every ordinary material through the real kill path.
    for(const kind of ['keel_crab','keel_deckhand','keel_lantern']){
      const enemy=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);
      await w.debug(hero,{op:'kill_enemy',id:enemy.id});
      await w.waitFor(()=>w.views.get(hero).drops.some(d=>d.item===`${kind}_relic`),5000,`${kind} material`);
      check(true,`${kind} awards its own material`);
    }
    // Final first: the other two guardians must still be defeated before the exit works.
    for(const [i,kind] of ['keel_captain','keel_cargomaw','keel_bosun'].entries()){
      const enemy=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);
      await w.debug(hero,{op:'kill_enemy',id:enemy.id});
      await w.waitFor(()=>w.views.get(hero).slimes.find(s=>s.id===enemy.id)?.dead,5000,`${kind} defeated`);
      check(w.views.get(hero).instance.cleared===(i===2),'Clear waits for all three guardians');
      const drops=w.views.get(hero).drops.filter(d=>d.item&&d.item.endsWith('_l35_keel'));
      const rolls=w.events.filter(e=>e.type==='roll'&&e.op==='start'&&e.bot===hero);
      check(drops.length+rolls.filter(r=>r.item?.endsWith('_l35_keel')).length>0,'Boss kills produce exclusive Keelbound level-35 gear');
    }
    await w.waitFor(()=>q(hero,'keel_cargo')?.counts[0]===1&&q(ally,'keel_cargo')?.counts[0]===1&&
      q(hero,'keel_rigging')?.counts[0]===1&&q(ally,'keel_rigging')?.counts[0]===1,5000,'Party copy quest credit');
    check(!w.views.get(other).instance.cleared&&w.views.get(other).slimes.filter(s=>!s.dead).length===15,'Other party retains its live enemies and uncleared exit');
    await kit.teleport(w,hero,{zone:43,x:64,y:17});
    await w.action(hero,{type:'move',x:64,y:13});
    await w.waitFor(()=>w.player(hero).zone===8,12000,'Clear exit returns to Rán’s Deep');
    for(const [npc,id] of [['keel_guide','keel_cargo'],['keel_rigger','keel_rigging']]){
      await kit.teleport(w,hero,{npc});await kit.talkTo(w,hero,npc,`quest:claim:${id}`);
      await w.waitFor(()=>q(hero,id)?.claimed,5000,`Claim ${id}`);
    }
    const rewards=['pants_wayfarer_l35_keel','accessory_amber_l35_keel'];
    check(rewards.every(item=>w.player(hero).inventory.some(i=>i.item===item)),'Both boss quests award level-35 Keelbound gear');
    await w.restart();
    check(w.player(hero).zone===8&&rewards.every(item=>w.player(hero).inventory.some(i=>i.item===item))&&
      ['keel_entry','keel_cargo','keel_rigging'].every(id=>q(hero,id)?.claimed),'Return, quest claims and rewards survive restart');
    check(longship.name==='The Drowned Longship'&&parent.portals.some(p=>p.to===43),'The dungeon entrance is in Rán’s Deep');
  }
});
