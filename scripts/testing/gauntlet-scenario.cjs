// Real private protocol coverage for the arena gauntlet quests (docs/arena-quests.md) at levels 20 and 99, two heroes in
// separate runs at once. No fight is ground out: winning a whole run is covered by the Rust tests (`gauntlet_tests.rs`), so this
// plays the protocol up to the first landed blow, leaves, and then hands in a finished trial.
module.exports = (kit, map) => ({
  description: 'Arena gauntlet quests: accept, one trial per level, private rings, countdown, the opponent, a landed blow, leaving, the weapon turn-in and a restart.',
  startLevel:20, levelSpread:0,
  async run(w,check) {
    const low='ArenaLow', high='ArenaHigh', giver='city_steward';
    const trials=[[low,20,'arena_skald_20'],[high,99,'arena_skald_99']];
    const quest=(bot,id)=>w.player(bot).quests.find(q=>q.id===id);
    const run=bot=>[...w.events].reverse().find(e=>e.bot===bot&&e.type==='pvp')?.gauntlet||null;
    const weapon=(id,bot)=>kit.quests.find(q=>q.id===id).rewardChoices[w.player(bot).look.class][0];
    for(const [bot,level] of trials){
      await w.connect({bot,class:'warrior'});
      await w.debug(bot,{op:'set_level',level});
    }
    // Accept at Skaldholm's steward; the same level from another giver is refused (once per level per character).
    for(const [bot,level,id] of trials){
      await kit.teleport(w,bot,{npc:giver});
      await kit.talkTo(w,bot,giver,`quest:accept:${id}`);
      await w.waitFor(()=>!!quest(bot,id),5000,`Accept ${id}`);
      check(quest(bot,id).counts[0]===0,`${id} starts at 0 of 5`);
    }
    await kit.teleport(w,low,{npc:'guide'});
    await kit.talkTo(w,low,'guide','quest:accept:arena_alder_20');
    await w.advance(700);
    check(!quest(low,'arena_alder_20'),'The level 20 trial is refused from a second giver');
    // The giver sends each hero into its own ring.
    for(const [bot] of trials){
      await kit.teleport(w,bot,{npc:giver});
      await w.advance(700);
      await w.action(bot,{type:'interact',npc:giver,offer:'gauntlet'});
      await w.waitFor(()=>w.player(bot).zone===40,15000,`${bot} enters the Arena`);
      await w.waitFor(()=>run(bot),5000,`${bot} gets the run state`);
    }
    for(const [bot,level,id] of trials){
      const g=run(bot);
      check(g.quest===id&&g.level===level&&g.fight===1&&g.of===5,`${bot}: fight 1 of 5 of ${id}`);
      check(g.countdown>0&&g.countdown<=10&&!g.opponent&&!!g.next,`${bot}: a countdown runs before the first fight and names the class`);
    }
    // Opponents arrive after the countdown, are marked, named after their class and live in separate copies.
    for(const [bot] of trials)await w.waitFor(()=>run(bot)?.opponent,25000,`${bot} meets an opponent`);
    const foe=bot=>run(bot).opponent;
    for(const [bot,level] of trials){
      const o=foe(bot);
      check(/^Arena /.test(o.name)&&o.name.toLowerCase().endsWith(o.class),`${bot}: the opponent is named after its class (${o.name})`);
      await w.waitFor(()=>w.views.get(bot).players.some(p=>p.id===o.id),5000,`${bot} sees its opponent`);
      const seen=w.views.get(bot).players.find(p=>p.id===o.id);
      check(seen.gauntlet===true&&seen.level===level,`${bot}: the snapshot marks the opponent and gives it level ${level}`);
    }
    check(foe(low).id!==foe(high).id&&!w.views.get(low).players.some(p=>p.id===foe(high).id)&&!w.views.get(high).players.some(p=>p.id===foe(low).id),
      'Two runs at once use separate rings and opponents');
    // A basic blow goes through the PvP rules: walk up and swing until the opponent's health drops.
    for(const [bot] of trials){
      const id=foe(bot).id,mine=()=>w.player(bot),theirs=()=>w.views.get(bot).players.find(p=>p.id===id);
      await w.waitFor(async()=>{
        const o=theirs();if(!o||o.hp<o.maxHp)return !!o;
        if(Math.hypot(o.x-mine().x,o.y-mine().y)>1.3)await w.action(bot,{type:'move',x:o.x,y:o.y});
        await w.action(bot,{type:'pvp',command:{op:'attack',id}});
        return false;
      },30000,`${bot} lands a blow`);
      check(theirs().hp<theirs().maxHp,`${bot}: a blow takes the opponent's health down`);
    }
    // Leaving ends the run: back at the giver, full health, progress at 0 of 5, nothing paid.
    for(const [bot,,id] of trials){
      await w.action(bot,{type:'pvp',command:{op:'arena_leave'}});
      await w.waitFor(()=>w.player(bot).zone===4&&!run(bot),10000,`${bot} leaves the ring`);
      check(w.player(bot).hp===w.player(bot).maxHp&&quest(bot,id).counts[0]===0&&!quest(bot,id).claimed,`${bot}: leaving restores health and resets the trial`);
    }
    // A won trial is handed in at the giver for the blue weapon of the quest's level, experience and gold.
    for(const [bot,level,id] of trials){
      await w.debug(bot,{op:'quest',id,action:'complete'});
      const item=weapon(id,bot),gold=w.player(bot).gold,def=kit.quests.find(q=>q.id===id);
      check(item.endsWith('_blue')&&def.rewardGold>0,`${id} offers a blue weapon (${item})`);
      await kit.teleport(w,bot,{npc:giver});
      await kit.talkTo(w,bot,giver,`quest:claim:${id}:${item}`);
      await w.waitFor(()=>quest(bot,id)?.claimed,5000,`Claim ${id}`);
      check(w.player(bot).inventory.some(i=>i.item===item)&&w.player(bot).gold>=gold+def.rewardGold,`${bot}: the turn-in pays the weapon and ${def.rewardGold} gold`);
    }
    await w.restart();
    for(const [bot,,id] of trials)check(quest(bot,id)?.claimed&&w.player(bot).inventory.some(i=>i.item===weapon(id,bot)),`${bot}: the claim and the weapon survive a restart`);
    check(map.zones[39].name==='Arena'||map.zones[39].name?.includes('Arena'),'Zone 40 is the Arena');
  }
});
