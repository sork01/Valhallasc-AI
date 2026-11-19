// Private websocket protocol/persistence check; no production database or timed fishing/grinding.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),w=new TestWorld(),bot='Rodsmith';
(async()=>{
  await w.start();await w.connect({bot,class:'warrior',gender:'male'});
  const world=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt')));
  const npc=world.npcs.find(n=>n.id==='fisher_meadow_0'),smith=world.npcs.find(n=>n.id==='smith');
  await w.debug(bot,{op:'set_level',level:10});await w.debug(bot,{op:'set_gold',gold:1000});
  await w.debug(bot,{op:'teleport',zone:0,x:npc.x,y:npc.y});
  async function interact(offer,npcId=npc.id){
    const start=w.events.length;await w.action(bot,{type:'interact',npc:npcId,...(offer?{offer}:{})});
    return w.waitFor(()=>w.events.slice(start).find(e=>e.type==='dialogue'),5000,'Fisher dialogue');
  }
  let packet=await interact();
  assert(packet.fisherQuote.some(r=>r.id==='rod:2'&&r.ingredients.some(([id,n])=>id==='fish_pier_sprat'&&n===5)));
  packet=await interact('buy_twig_rod');assert.equal(packet.gold,950);
  await w.debug(bot,{op:'give_item',item:'fish_pier_sprat',quantity:6});await w.debug(bot,{op:'give_item',item:'slime_gel',quantity:1});
  await w.debug(bot,{op:'teleport',zone:0,x:smith.x,y:smith.y});
  await w.advance(550);packet=await interact('rod:2',smith.id);
  assert.match(packet.notice,/does not offer that recipe/);assert.equal(packet.gold,950);
  assert(packet.inventory.some(s=>s.item==='rod_twig_rod'&&s.quantity===1));
  assert(packet.inventory.some(s=>s.item==='fish_pier_sprat'&&s.quantity===6));
  assert(!packet.inventory.some(s=>s.item==='rod_willow_rod'));
  await w.debug(bot,{op:'teleport',zone:0,x:npc.x,y:npc.y});
  await w.advance(550);packet=await interact('rod:2');
  assert.equal(packet.gold,700);assert(packet.inventory.some(s=>s.item==='rod_willow_rod'&&s.quantity===1));
  assert(!packet.inventory.some(s=>s.item==='rod_twig_rod'));
  await w.advance(550);packet=await interact('cook:fish_pier_sprat');
  assert(packet.inventory.some(s=>s.item==='dish_shore_grill'&&s.quantity===1));
  await w.waitFor(()=>w.player(bot).inventory.some(s=>s.item==='dish_shore_grill'));
  const inv=JSON.stringify(w.player(bot).inventory),gold=packet.gold;
  await w.disconnect(bot);await w.connect({bot,class:'warrior',gender:'male'});
  assert.equal(JSON.stringify(w.player(bot).inventory),inv);assert.equal(w.player(bot).gold,gold);
  const ticks=[],arrivals=[];
  const sample=data=>{const packet=JSON.parse(data);if(packet.type==='snapshot'){ticks.push(packet.tick);arrivals.push(performance.now());}};
  w.bots.get(bot).socket.on('message',sample);await w.waitFor(()=>ticks.length>=30,3800,'30 snapshots');w.bots.get(bot).socket.off('message',sample);
  const elapsed=Math.round(arrivals[29]-arrivals[0]);assert(elapsed<=3000,`${elapsed}ms`);assert(ticks.slice(1).every((t,i)=>t-ticks[i]===2));
  console.log(`Fisher protocol/persistence pass; 30 snapshots in ${elapsed} ms, tick gaps of 2`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>w.stop());
