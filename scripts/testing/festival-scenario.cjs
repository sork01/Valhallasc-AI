module.exports=kit=>({
 description:'Festival Spirit: real guided dance, two full circuits, forged/off-season refusals, interruption, permanent expiry and restart.',startLevel:20,levelSpread:0,
 async run(w,check){
  const bot='Festival',id='festival_dance_solstice_0',self=()=>w.player(bot);
  await w.connect({bot,class:'warrior'});await w.debug(bot,{op:'season_time',unix:1813183200});await w.debug(bot,{op:'teleport',zone:0,x:33.8,y:83});await w.waitFor(()=>self().zone===0);
  await w.action(bot,{type:'interact',npc:id,offer:'festival:complete'});await w.advance(400);check(self().festivalBuff.until===0&&!self().festivalDance,'A forged completion offer cannot grant the buff');
  await w.action(bot,{type:'interact',npc:'festival_dance_christmas_0',offer:'festival:dance'});await w.advance(400);check(!self().festivalDance&&self().festivalBuff.until===0,'A different season cannot start its dance');
  await w.action(bot,{type:'interact',npc:id,offer:'festival:dance'});await w.waitFor(()=>self().festivalDance?.laps>.15);check(self().festivalBuff.until===0,'Partial real circuits grant nothing');
  await w.action(bot,{type:'input',dx:1,dy:0});await w.waitFor(()=>!self().festivalDance);await w.action(bot,{type:'stop'});check(self().festivalBuff.until===0,'Manual movement cancels partial progress');
  await w.debug(bot,{op:'teleport',zone:0,x:33.8,y:83});await w.action(bot,{type:'interact',npc:id,offer:'festival:dance'});await w.waitFor(()=>self().festivalDance?.laps>1,20000);check(self().festivalBuff.until===0,'One full lap still grants nothing');
  await w.waitFor(()=>self().festivalDance===null&&self().festivalBuff.left>7190,20000);check(self().festivalBuff.left<=7200&&self().festivalBuff.season==='solstice','Two complete circuits grant exactly one two-hour Festival Spirit');
  const until=self().festivalBuff.until;await w.debug(bot,{op:'teleport',zone:0,x:33.8,y:83});await w.action(bot,{type:'interact',npc:id,offer:'festival:dance'});await w.waitFor(()=>self().festivalDance?.laps>.1);await w.restart();
  check(self().festivalBuff.until===until&&self().festivalBuff.left>0,'Buff expiry survives a real private server restart');check(self().festivalDance===null,'Incomplete circuit progress never resumes after restart');
 }
});
