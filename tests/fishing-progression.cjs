// Real recipe/cast/food packets against a private database. No browser or catch grind.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),load=n=>JSON.parse(fs.readFileSync(path.join(root,'world',n)));
const world=load('map.txt'),rods=load('rods.txt'),recipes=load('fishing-workshop.txt').filter(r=>r.id.startsWith('rod:'));
const w=new TestWorld(),bot='RodProgress';w.startLevel=99;w.levelSpread=0;
const rodStacks=()=>w.player(bot).inventory.filter(s=>rods.some(r=>r.item===s.item));
async function talk(zone,offer){
 const area=zone===0?world:world.zones[zone-1],npc=area.npcs.find(n=>n.id.startsWith('fisher_'));
 await w.debug(bot,{op:'teleport',zone,x:npc.x,y:npc.y});await w.advance(550);
 const start=w.events.length;await w.action(bot,{type:'interact',npc:npc.id,offer});
 return w.waitFor(()=>w.events.slice(start).find(e=>e.bot===bot&&e.type==='dialogue'),5000,'recipe reply');
}
async function shore(zone){
 // Shop presence is a UI packet outside the driver's action schema.
 w.bots.get(bot).socket.send(JSON.stringify({type:'shop_presence',open:false}));
 const area=zone===0?world:world.zones[zone-1];
 const point=area.fishingSpots.map(p=>({...p,clearance:Math.min(...area.slimes.filter(s=>!s.sleeping).map(s=>Math.hypot(p.shore.x-s.x,p.shore.y-s.y)))})).sort((a,b)=>b.clearance-a.clearance)[0];
 await w.debug(bot,{op:'teleport',zone,...point.shore});
 await w.action(bot,{type:'input',dx:point.facing.x,dy:point.facing.y});
 await w.waitFor(()=>Math.hypot(w.player(bot).x-point.shore.x,w.player(bot).y-point.shore.y)>.01);
 await w.action(bot,{type:'stop'});await w.debug(bot,{op:'teleport',zone,...point.shore});await w.advance(1100);
}
(async()=>{
 await w.start();await w.connect({bot,class:'warrior',gender:'male'});await w.debug(bot,{op:'set_gold',gold:1_000_000});
 await talk(0,'buy_twig_rod');await w.waitFor(()=>rodStacks().length===1);
 for(const r of recipes){
  for(const [item,quantity] of r.ingredients.slice(1))await w.debug(bot,{op:'give_item',item,quantity});
  const reply=await talk(r.zones[0],r.id);assert(reply.inventory.some(s=>s.item===r.item&&s.quantity===1),reply.notice);
  await w.waitFor(()=>rodStacks().some(s=>s.item===r.item));assert.equal(rodStacks().length,1,'only the upgraded rod remains');
 }
 for(const zone of [0,1,45,28]){
  await shore(zone);await w.action(bot,{type:'fish'});await w.waitFor(()=>w.player(bot).fishing,5000,`Worldwire casts in zone ${zone}`);
  assert.equal(w.player(bot).fishing.lava,zone===1||zone===45);await w.action(bot,{type:'fish'});await w.waitFor(()=>!w.player(bot).fishing);
 }
 await w.debug(bot,{op:'take_item',item:'rod_worldwire_rod',quantity:1});await w.debug(bot,{op:'give_item',item:'rod_twig_rod',quantity:1});
 await shore(28);const start=w.events.length;await w.action(bot,{type:'fish'});
 await w.waitFor(()=>w.events.slice(start).some(e=>e.bot===bot&&e.text==='This water requires Worldwire Rod (level 80).'));
 await w.debug(bot,{op:'take_item',item:'rod_twig_rod',quantity:1});await w.debug(bot,{op:'give_item',item:'rod_worldwire_rod',quantity:1});
 await w.debug(bot,{op:'give_item',item:'dish_shore_grill',quantity:1});await w.debug(bot,{op:'give_item',item:'dish_cold_feast',quantity:1});
 await w.action(bot,{type:'use_item',item:'dish_shore_grill'});await w.waitFor(()=>w.player(bot).buffs.some(b=>b.id==='meal:dish_shore_grill'));
 let p=w.player(bot),b=p.buffs.find(b=>b.id==='meal:dish_shore_grill');assert.equal(b.kind,'haste');assert.equal(b.amount,undefined,'buff magnitude stays private; Rust gameplay checks verify its effect');assert.equal(b.time,600);assert(p.mealCd>0);
 await w.action(bot,{type:'use_item',item:'dish_cold_feast'});await w.advance(200);p=w.player(bot);
 assert.equal(p.inventory.find(s=>s.item==='dish_cold_feast').quantity,1,'shared meal timer prevents consuming a second dish');assert.equal(p.buffs.filter(b=>b.id.startsWith('meal:')).length,1);
 const inventory=JSON.stringify(p.inventory);await w.disconnect(bot);await w.connect({bot,class:'warrior',gender:'male'});
 assert.equal(JSON.stringify(w.player(bot).inventory),inventory);assert(w.player(bot).mealCd>0,'saved meal cooldown survives relog');assert.equal(rodStacks().length,1);
 console.log('Private progression probe: seven upgrades consume their predecessors, one rod casts in ordinary water/both lava areas/Yearwheel, named gate, real food bonus/shared timer and saved inventory pass.');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await w.stop();});
