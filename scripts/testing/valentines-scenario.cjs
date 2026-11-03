// Private protocol fixtures only: no grinding or encounter balance measurements.
module.exports = kit => ({
  description: 'Valentine: shared city daily quest, five hired fighters, ritual summon, guaranteed unicorn reward, cross-city claim, persistence and event expiry.',
  startLevel:20, levelSpread:0,
  async run(w,check) {
    const bot='RoseHunt', id='valentine_hunt';
    const q=()=>w.player(bot).quests.find(q=>q.id===id);
    await w.connect({bot,class:'warrior'});
    await w.debug(bot,{op:'season_time',unix:1802214000});
    await w.waitFor(()=>w.views.get(bot).seasons?.[0]?.day===20270210);
    await kit.teleport(w,bot,{npc:'city_bard'});
    await kit.talkTo(w,bot,'city_bard',`quest:accept:${id}`);
    await w.waitFor(()=>q()&&!q().claimed);
    check(q().counts[0]===0,'A second-city host accepts the shared daily hunt');
    await w.debug(bot,{op:'set_gold',gold:1000000});
    for(const cls of ['priest','mage','hunter','warrior']) {
      await w.advance(600);
      await w.action(bot,{type:'interact',npc:'city_bard',offer:`valentine:hire:${cls}`});
      await w.waitFor(()=>w.views.get(bot).players.filter(p=>p.hired).length===['priest','mage','hunter','warrior'].indexOf(cls)+1);
    }
    await w.debug(bot,{op:'teleport',zone:2,x:110.5,y:100});
    await w.waitFor(()=>w.views.get(bot).players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4,15000,'Hired fighters gather');
    await w.action(bot,{type:'interact',npc:'valentine_shrine',offer:'valentine:summon'});
    await w.waitFor(()=>w.views.get(bot).valentine?.active);
    check(w.views.get(bot).valentine.level===20,'The real Roseheart Shrine summons at the five fighters’ highest level');
    const enemy=w.views.get(bot).slimes.find(s=>s.kind==='briarheart'&&!s.dead);
    check(!!enemy,'The authored dormant elite becomes visible only after summoning');
    await w.debug(bot,{op:'kill_enemy',id:enemy.id});
    await w.waitFor(()=>q().counts[0]===1);
    check(!w.player(bot).mounts.includes('roseheart'),'A credited kill readies the guaranteed quest reward without a random mount drop');
    await kit.teleport(w,bot,{npc:'nacre_gardener'});
    const gold=w.player(bot).gold;
    await kit.talkTo(w,bot,'nacre_gardener',`quest:claim:${id}`);
    await w.waitFor(()=>q().claimed&&w.player(bot).seasonalClaims[id]===20270210);
    check(w.player(bot).gold===gold+300&&w.player(bot).mounts.includes('roseheart'),'A third-city host pays the shared reward and guaranteed unicorn');
    await kit.teleport(w,bot,{npc:'asterion_singer'});
    await kit.talkTo(w,bot,'asterion_singer',`quest:accept:${id}`);
    await w.advance(300);
    check(q().claimed,'A fourth-city host cannot reopen the same day’s hunt');
    await w.restart();
    check(w.player(bot).seasonalClaims[id]===20270210&&w.player(bot).mounts.includes('roseheart'),'Daily claim and guaranteed unicorn ownership survive a server restart');
    await w.debug(bot,{op:'season_time',unix:1802991600});
    await w.waitFor(()=>w.views.get(bot).seasons.length===0);
    check(w.views.get(bot).valentine===null,'February 19 removes the ritual encounter state');
    await w.debug(bot,{op:'teleport',zone:2,x:110.5,y:100});
    await w.action(bot,{type:'interact',npc:'valentine_shrine',offer:'valentine:summon'});
    await w.advance(300);
    check(!w.views.get(bot).valentine&&!w.views.get(bot).slimes.some(s=>s.kind==='briarheart'&&!s.dead&&s.state!=='waiting'),'A forged off-season summon cannot create the elite');
  }
});
