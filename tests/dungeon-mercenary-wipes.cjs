'use strict';
// Private protocol regression: the old executable loses its hires during the
// 35-second death/revival window. No browser, public connection or DB edits.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const kit = require('../scripts/testing/tools.cjs');
const world = new TestWorld(), bot = 'DungeonOwner';
const data = JSON.parse(fs.readFileSync(path.join(__dirname,'../world/map.txt'),'utf8'));
const zones = [data,...data.zones];
const hires = () => (world.views.get(bot)?.players || []).filter(p => p.hired);
let checks = 0;
const check = (condition, label) => { assert.ok(condition,label); checks++; };
(async () => {
  await world.start();
  await world.connect({bot,class:'warrior'});
  await world.debug(bot,{op:'set_level',level:20});
  await world.debug(bot,{op:'set_gold',gold:1000000});
  const smith = 'dungeon_repair_5';
  await kit.teleport(world,bot,{npc:smith});
  for(const cls of ['mage','priest','hunter','assassin']) {
    const reply=await kit.talkTo(world,bot,smith,`merc_${cls}`);
    assert.match(reply.notice,/joins your party/);
  }
  await world.waitFor(()=>hires().length===4,5000,'four dungeon hires');
  const ids=hires().map(p=>p.id).sort(),purse=world.player(bot).gold;
  await world.debug(bot,{op:'die'});
  check(world.player(bot).dead,'the hirer really died');
  const started=world.views.get(bot).time;
  let samples=0,lastTick=-1,revived=false;
  await world.waitFor(()=>{
    const view=world.views.get(bot);
    if(view.tick===lastTick)return false;
    lastTick=view.tick;samples++;
    assert.deepEqual(hires().map(p=>p.id).sort(),ids,'death must not end a dungeon hire contract');
    assert(hires().every(p=>p.hp>0&&!p.dead),'the hirer dying must not doom the dungeon hires');
    if(!world.player(bot).dead&&world.player(bot).hp>0)revived=true;
    return view.time-started>=35;
  },50000,'retain the same hires beyond the old 30-second deadline');
  check(revived,'the hirer revived in the instance');
  check(world.player(bot).zone===5&&!world.player(bot).ghost&&!world.player(bot).corpse,
    'revival keeps the hirer inside the dungeon without a ghost run');
  check(samples>=100,'snapshots cover the death, revival and old deadline');
  check(world.player(bot).gold===purse,'retrying requires no new hire payment');
  check(hires().length===4,'all four original hires remain');
  console.log(`Owner death/revival: the same four hires remain after 35 simulation seconds (${samples} snapshots).`);

  // Kill through the ordinary authoritative kill path; the final boss still
  // closes every contract, even though ordinary packs remain in the copy.
  const final=zones[5].slimes.find(s=>s.kind===zones[5].final_boss);
  await kit.teleport(world,bot,{zone:5,x:final.x+3,y:final.y});
  await world.waitFor(()=>world.views.get(bot)?.slimes?.some(s=>s.kind===final.kind&&!s.dead),5000,'final boss visible');
  const boss=world.views.get(bot).slimes.find(s=>s.kind===final.kind&&!s.dead);
  await world.debug(bot,{op:'kill_enemy',id:boss.id});
  await world.waitFor(()=>hires().length===0,5000,'final boss completion ends hires');
  check(true,'the final boss still ends the contract');

  await world.debug(bot,{op:'set_level',level:25});
  await kit.teleport(world,bot,{npc:'dungeon_repair_41'});
  const reply=await kit.talkTo(world,bot,'dungeon_repair_41','merc_priest');
  assert.match(reply.notice,/joins your party/);
  await world.waitFor(()=>hires().length===1,5000,'Nornroot hire');
  const id=hires()[0].id;
  await world.debug(bot,{op:'die'});
  await world.waitFor(()=>!world.player(bot).dead&&world.player(bot).hp>0,7000,'Nornroot revival');
  check(hires().some(p=>p.id===id),'the Nornroot hire survives the death too');
  await kit.teleport(world,bot,{spawn:0});
  await world.waitFor(()=>hires().length===0,5000,'leaving the dungeon ends its hire');
  check(true,'leaving still ends the contract');
  const health=await(await fetch(world.url+'health')).json();
  check(health.online===1,'only the real player is counted online');
  world.saveReport({passed:true,checks,deathSnapshots:samples,retainedHires:ids.length,waitSimulationSeconds:35});
  console.log(`Dungeon hire death/revival: ${checks} checks passed; ${world.runDir}`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>world.stop());
