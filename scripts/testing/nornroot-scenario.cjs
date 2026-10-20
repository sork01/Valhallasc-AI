// Real private protocol coverage for the level-25 Wyrdwood dungeon. No progression grind.
module.exports = (kit, map) => ({
  description: 'Nornroot Barrow: level gate, both exits, party isolation, three quests, boss loot and saved rewards.',
  startLevel:25, levelSpread:0, godMode:true,
  async run(w,check) {
    const hero='BarrowRunner', ally='BarrowAlly', other='BarrowOther', low='BarrowLow';
    const barrow=map.zones[40],parent=map.zones[5];
    const q=(bot,id)=>w.player(bot).quests.find(q=>q.id===id);
    const enter=async bot=>{
      await kit.teleport(w,bot,{zone:6,x:84,y:70});
      await w.action(bot,{type:'move',x:84,y:66});
      await w.waitFor(()=>w.player(bot).zone===41,12000,`${bot} enters the Barrow`);
      await w.action(bot,{type:'stop'});
    };
    for(const bot of [hero,ally,other,low])await w.connect({bot,class:'warrior'});
    await w.debug(low,{op:'set_level',level:24});
    await kit.teleport(w,low,{zone:6,x:84,y:70});
    const before=new Set(w.events);
    await w.action(low,{type:'move',x:84,y:66});
    await w.waitFor(()=>w.events.some(e=>!before.has(e)&&e.bot===low&&e.type==='error'&&/level 25/.test(e.text)),12000,'Level 24 is refused');
    await w.action(low,{type:'stop'});
    check(w.player(low).zone===6,'Level-24 heroes stay in Wyrdwood');
    await w.social(hero,{op:'party_invite',bot:ally});
    await w.social(ally,{op:'party_accept',bot:hero});
    for(const bot of [hero,ally]){
      for(const [npc,id] of [['barrow_guide','barrow_entry'],['barrow_guide','barrow_amber'],['barrow_scribe','barrow_threads']]){
        await kit.teleport(w,bot,{npc});
        await kit.talkTo(w,bot,npc,`quest:accept:${id}`);
        await w.waitFor(()=>!!q(bot,id),5000,`Accept ${id}`);
      }
    }
    await enter(hero);await enter(ally);await enter(other);
    await kit.teleport(w,hero,{npc:'barrow_witness'});
    await kit.talkTo(w,hero,'barrow_witness');
    await w.waitFor(()=>q(hero,'barrow_entry')?.counts[0]===1,5000,'Speak to the Last Witness');
    await kit.teleport(w,hero,{zone:41,x:56,y:99});
    const ids=bot=>new Set(w.views.get(bot).slimes.map(s=>s.id));
    check([...ids(hero)].every(id=>ids(ally).has(id))&&[...ids(hero)].every(id=>!ids(other).has(id)),
      'Party members share enemies and another party has separate enemies');
    check(w.views.get(hero).slimes.filter(s=>!s.dead).length===15,'Twelve ordinary foes and three guardians occupy the dungeon');
    // Keep the ally in the copy while exercising the entrance return and actual claim.
    await w.action(hero,{type:'move',x:49,y:99});
    await w.waitFor(()=>w.player(hero).zone===6,15000,'Entrance return to Wyrdwood');
    await kit.teleport(w,hero,{npc:'barrow_guide'});
    await kit.talkTo(w,hero,'barrow_guide','quest:claim:barrow_entry');
    await w.waitFor(()=>q(hero,'barrow_entry')?.claimed,5000,'Claim entry quest');
    await enter(hero);
    // Exercise every ordinary material through the real kill path.
    for(const kind of ['barrow_scarab','barrow_hound','barrow_spinner']){
      const enemy=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);
      await w.debug(hero,{op:'kill_enemy',id:enemy.id});
      await w.waitFor(()=>w.views.get(hero).drops.some(d=>d.item===`${kind}_relic`),5000,`${kind} material`);
      check(true,`${kind} awards its own material`);
    }
    // Final first: the other two guardians must still be defeated before the exit works.
    for(const [i,kind] of ['barrow_fatebound','barrow_doorward','barrow_threadkeeper'].entries()){
      const enemy=w.views.get(hero).slimes.find(s=>s.kind===kind&&!s.dead);
      await w.debug(hero,{op:'kill_enemy',id:enemy.id});
      await w.waitFor(()=>w.views.get(hero).slimes.find(s=>s.id===enemy.id)?.dead,5000,`${kind} defeated`);
      check(w.views.get(hero).instance.cleared===(i===2),'Clear waits for all three guardians');
      const drops=w.views.get(hero).drops.filter(d=>d.item&&d.item.endsWith('_l25_norn'));
      const rolls=w.events.filter(e=>e.type==='roll'&&e.op==='start'&&e.bot===hero);
      check(drops.length+rolls.filter(r=>r.item?.endsWith('_l25_norn')).length>0,'Boss kills produce exclusive Fatewoven level-25 gear');
    }
    await w.waitFor(()=>q(hero,'barrow_amber')?.counts[0]===1&&q(ally,'barrow_amber')?.counts[0]===1&&
      q(hero,'barrow_threads')?.counts[0]===1&&q(ally,'barrow_threads')?.counts[0]===1,5000,'Party copy quest credit');
    check(!w.views.get(other).instance.cleared&&w.views.get(other).slimes.filter(s=>!s.dead).length===15,'Other party retains its live enemies and uncleared exit');
    await kit.teleport(w,hero,{zone:41,x:56,y:14});
    await w.action(hero,{type:'move',x:56,y:10});
    await w.waitFor(()=>w.player(hero).zone===6,12000,'Clear exit returns to Wyrdwood');
    for(const [npc,id] of [['barrow_guide','barrow_amber'],['barrow_scribe','barrow_threads']]){
      await kit.teleport(w,hero,{npc});await kit.talkTo(w,hero,npc,`quest:claim:${id}`);
      await w.waitFor(()=>q(hero,id)?.claimed,5000,`Claim ${id}`);
    }
    const rewards=['pants_wayfarer_l25_norn','accessory_amber_l25_norn'];
    check(rewards.every(item=>w.player(hero).inventory.some(i=>i.item===item)),'Both boss quests award level-25 Fatewoven gear');
    await w.restart();
    check(w.player(hero).zone===6&&rewards.every(item=>w.player(hero).inventory.some(i=>i.item===item))&&
      ['barrow_entry','barrow_amber','barrow_threads'].every(id=>q(hero,id)?.claimed),'Return, quest claims and rewards survive restart');
    check(barrow.name==='Nornroot Barrow'&&parent.portals.some(p=>p.to===41),'The dungeon entrance is in Wyrdwood');
  }
});
