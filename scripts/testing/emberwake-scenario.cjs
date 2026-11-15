// New zone only: real movement, both gates, quests, kill drops and persistence.
// The Caldera is entered by walking across the Orrery's shared border (a seam), not through a gate on Asterion.
// A seam fires only moving across its line on its own side, so start 2 tiles back on that side (as scenarios.cjs does).
function crossingPath(gate) {
  const pts = gate.seam.points;
  let best = null;
  for (let i = 0; i + 1 < pts.length; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[i + 1];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1;
    const t = Math.max(0, Math.min(1, ((gate.x - ax) * dx + (gate.y - ay) * dy) / (len * len)));
    const d = Math.hypot(gate.x - (ax + dx * t), gate.y - (ay + dy * t));
    if (!best || d < best.d) best = { d, gx: -dy / len, gy: dx / len };
  }
  // Start on the walker's own side and walk to a goal past the line (see scenarios.cjs crossingPath).
  const s = gate.seam.side;
  return {
    start: { x: gate.x - s * 2 * best.gx, y: gate.y - s * 2 * best.gy },
    goal: { x: gate.x + s * 2 * best.gx, y: gate.y + s * 2 * best.gy },
  };
}
module.exports=(kit,map)=>({
  description:'Emberwake Caldera: walk from Asterion to the raid door, quests, outdoor loot and return.',
  startLevel:99,levelSpread:0,godMode:true,
  async run(w,check){
    const bot='EmberWalker',area=map.zones[44];
    const q=id=>w.player(bot).quests.find(q=>q.id===id);
    await w.connect({bot,class:'warrior'});
    const entry=map.zones[14].portals.find(p=>p.id==='atlas_15_45'), home=area.portals.find(p=>p.id==='atlas_45_15');
    const enter=crossingPath(entry);
    await kit.teleport(w,bot,{zone:15,x:enter.start.x,y:enter.start.y});
    await w.advance(700); // a teleport holds portals for PORTAL_DELAY (0.5 s): wait before walking into the seam
    await w.action(bot,{type:'move',x:enter.goal.x,y:enter.goal.y});
    await w.waitFor(()=>w.player(bot).zone===45,15000,'Cross the Orrery border into the Caldera');
    await w.action(bot,{type:'stop'});
    check(Math.hypot(w.player(bot).x-entry.tx,w.player(bot).y-entry.ty)<2,'The Orrery border reaches a safe caldera arrival');
    // Snapshots cull distant enemies, so the view holds some of the Caldera's floor, never the Orrery's.
    await w.waitFor(()=>w.views.get(bot).slimes.length>0,5000,'Caldera enemies arrive in view');
    check(w.views.get(bot).slimes.every(s=>s.zone===45),'Only Emberwake enemies are in the view');
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
    // The raid door is ew_raid (322,80) now: walk the real collision to a point in front of it.
    const door=area.portals.find(p=>p.id==='ew_raid');
    await kit.walkTo(w,bot,{x:door.x,y:door.y+3},120000);
    check(w.player(bot).zone===45&&Math.hypot(w.player(bot).x-door.x,w.player(bot).y-(door.y+3))<2,'The whole chain road can be walked to the raid door');
    const seal=await kit.talkTo(w,bot,'ew_seal');
    check(JSON.stringify(seal).includes('Quartermaster Halla'),'The Nine-Chain Door explains how to assemble ten fighters');
    await kit.talkTo(w,bot,'ew_echo');
    await w.waitFor(()=>q('ew_voice')?.counts[0]===1,5000,'Hear Eldmarr');
    check(area.portals.some(p=>p.id==='ew_raid'&&!map.zones[p.to-1].sealedTemplate),'The raid portal is open');
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
    const back=crossingPath(home);
    await kit.teleport(w,bot,{zone:45,x:back.start.x,y:back.start.y});
    await w.advance(700);
    await w.action(bot,{type:'move',x:back.goal.x,y:back.goal.y});
    await w.waitFor(()=>w.player(bot).zone===15,15000,'Return across the border to the Orrery');
    await w.action(bot,{type:'stop'});
    check(Math.hypot(w.player(bot).x-home.tx,w.player(bot).y-home.ty)<2,'Return lands at the Orrery arrival without bouncing');
    await w.restart();
    check(w.player(bot).zone===15&&['ew_warm','ew_road','ew_voice','ew_link'].every(id=>q(id)?.claimed),'Quest claims and safe return survive restart');
  }
});
