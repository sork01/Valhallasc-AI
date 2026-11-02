// Private protocol fixtures only: no grinding or encounter balance measurements.
module.exports = kit => ({
  description: 'Christmas: shared city daily quest, five hired fighters, ritual summon, personal daily roll, cross-city claim, persistence and event expiry.',
  startLevel:20, levelSpread:0,
  async run(w,check) {
    const bot='MerryHunt', id='christmas_hunt';
    const q=()=>w.player(bot).quests.find(q=>q.id===id);
    await w.connect({bot,class:'warrior'});
    await w.debug(bot,{op:'season_time',unix:1797289200});
    await w.waitFor(()=>w.views.get(bot).seasons?.[0]?.day===20261215);
    await kit.teleport(w,bot,{npc:'city_bard'});
    await kit.talkTo(w,bot,'city_bard',`quest:accept:${id}`);
    await w.waitFor(()=>q()&&!q().claimed);
    check(q().counts[0]===0,'A second-city host accepts the shared daily hunt');
    await w.debug(bot,{op:'set_gold',gold:1000000});
    for(const cls of ['priest','mage','hunter','warrior']) {
      await w.advance(600);
      await w.action(bot,{type:'interact',npc:'city_bard',offer:`christmas:hire:${cls}`});
      await w.waitFor(()=>w.views.get(bot).players.filter(p=>p.hired).length===['priest','mage','hunter','warrior'].indexOf(cls)+1);
    }
    await w.debug(bot,{op:'teleport',zone:2,x:110.5,y:100});
    await w.waitFor(()=>w.views.get(bot).players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4,15000,'Hired fighters gather');
    await w.action(bot,{type:'interact',npc:'christmas_tree',offer:'christmas:summon'});
    await w.waitFor(()=>w.views.get(bot).christmas?.active);
    check(w.views.get(bot).christmas.level===20,'The real Christmas tree summons at the five fighters’ highest level');
    const enemy=w.views.get(bot).slimes.find(s=>s.kind==='grinch'&&!s.dead);
    check(!!enemy,'The authored dormant elite becomes visible only after summoning');
    await w.debug(bot,{op:'kill_enemy',id:enemy.id});
    await w.waitFor(()=>q().counts[0]===1&&w.player(bot).seasonalRolls[id]===20261215);
    check(true,'A credited kill consumes exactly one personal daily mount attempt');
    await kit.teleport(w,bot,{npc:'nacre_gardener'});
    const gold=w.player(bot).gold;
    await kit.talkTo(w,bot,'nacre_gardener',`quest:claim:${id}`);
    await w.waitFor(()=>q().claimed&&w.player(bot).seasonalClaims[id]===20261215);
    check(w.player(bot).gold===gold+300,'A third-city host pays the shared reward');
    await kit.teleport(w,bot,{npc:'asterion_singer'});
    await kit.talkTo(w,bot,'asterion_singer',`quest:accept:${id}`);
    await w.advance(300);
    check(q().claimed,'A fourth-city host cannot reopen the same day’s hunt');
    await w.restart();
    check(w.player(bot).seasonalClaims[id]===20261215&&w.player(bot).seasonalRolls[id]===20261215,'Independent claim and roll ledgers survive a server restart');
    await w.debug(bot,{op:'season_time',unix:1798498800});
    await w.waitFor(()=>w.views.get(bot).seasons.length===0);
    check(w.views.get(bot).christmas===null,'December 29 removes the ritual encounter state');
    await w.debug(bot,{op:'teleport',zone:2,x:110.5,y:100});
    await w.action(bot,{type:'interact',npc:'christmas_tree',offer:'christmas:summon'});
    await w.advance(300);
    check(!w.views.get(bot).christmas&&!w.views.get(bot).slimes.some(s=>s.kind==='grinch'&&!s.dead&&s.state!=='waiting'),'A forged off-season summon cannot create the elite');
  }
});
