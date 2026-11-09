// Focused private checks: unique-name UI, four-city dressing and the daily summoned Halloween encounter.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
require('./lib/touch.cjs').requireMemoryLimit();
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const world=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,label)=>{assert.ok(v,label);console.log(++checks+': '+label);};
const wait=(p,fn,arg)=>p.waitForFunction(fn,arg,{timeout:20000});
const send=(p,m)=>p.evaluate(m=>Online.send(m),m);
const debug=(p,command)=>send(p,{type:'debug',command});
async function create(name,duplicate=false){
 const p=await browser.newPage({viewport:{width:1280,height:800},hasTouch:true,reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
  window.__valhallaTestSprites=true;window.AudioContext=window.webkitAudioContext=undefined;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:true,lowGraphicsSet:true}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='welcome'||v.type==='snapshot')window.__snap=v.snapshot||v;}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await p.goto(world.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill(name);await p.locator('#go').click({timeout:60000});
 if(duplicate)await p.locator('#name-change-form').waitFor({state:'visible'});else await wait(p,()=>Online.connected&&Field.hero.hp>0);
 return p;
}
async function stand(p,zone,x,y){
 await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Field.clearInput();Online.send({type:'stop'});});
 await debug(p,{op:'teleport',zone,x,y});await wait(p,([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[zone,x,y]);await p.waitForTimeout(250);await p.evaluate(()=>ZoneJourney.clear());
}
async function npc(p,id){const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(p,n.zone,n.x,n.y);return n;}
(async()=>{try{
 world.startLevel=99;world.godMode=true;await world.start();browser=await chromium.launch({headless:true});
 let p=await create('HuntTaken');const original=await p.evaluate(()=>Online.id);await p.close();
 p=await create('hUNTTaken',true);check((await p.locator('#connection-text').textContent()).includes('already taken'),'A case-varied name owned by an offline guest is refused in character creation');
 await p.locator('#new-character-name').fill('HuntHero');await p.locator('#name-change-form button').click();await wait(p,()=>Online.connected&&Field.hero.hp>0);
 check(await p.evaluate(id=>Online.id!==id&&__self().look.name==='HuntHero',original),'Choosing a free name enters normally without overwriting the older character');
 await debug(p,{op:'season_time',unix:1792969200});await wait(p,()=>Seasonal.active&&__snap.seasons[0].day===20261026);
 // Real decoration draw and NPC accessories, only in the four city bounds.
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].every((z,i)=>[0,4,9,17,24].includes(i)?z.seasonDecor?.length>=24:!z.seasonDecor)), 'Only the four main cities have seasonal prop metadata');
 for(const zone of [0,4,9,17]){
  const o=await p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z].seasonDecor.find(o=>!o.z),zone);await stand(p,zone,o.x,o.y);
  const data=await p.evaluate(()=>{const drawn=[],draw=City.drawObject;City.drawObject=function(g,o,...a){if(o.kind.startsWith('festival'))drawn.push(o.kind);return draw.call(this,g,o,...a);};try{Field._debug.drawFrame(3);return drawn;}finally{City.drawObject=draw;}});
  check(data.length>=3,`City ${zone}: several pieces of dressing are visible outside the old plaza cluster`);
  await p.screenshot({path:path.join(world.runDir,`dressing-${zone}-desktop.png`)});
  await p.setViewportSize({width:844,height:390});await debug(p,{op:'set_time',hour:0,freeze:true});await wait(p,()=>DayNight.hour<.01);await p.screenshot({path:path.join(world.runDir,`dressing-${zone}-phone-night.png`)});await p.setViewportSize({width:1280,height:800});
 }
 const villageNpc=await p.evaluate(()=>WORLD_MAP.zones[2].npcs.find(n=>n.art!=='scenery'));await stand(p,3,villageNpc.x,villageNpc.y);
 const outside=await p.evaluate(()=>{const n=City.npcs.find(n=>n.art!=='scenery'),c=document.createElement('canvas');c.width=300;c.height=300;const g=c.getContext('2d');Seasonal.drawNpc(g,n,3,100);return{props:Seasonal.decor(3).length,pixels:g.getImageData(0,0,300,300).data.some(v=>v)};});
 check(outside.props===0&&!outside.pixels,'Lanternmere has neither city festival props nor NPC costume overlays');
 // Shared daily quest offered at all four hosts, with the actual guide to the ritual.
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(id=>Quests.offered(id).some(q=>q.id==='halloween_hunt'))),'Every city host offers the same daily quest');
 await npc(p,'city_bard');await send(p,{type:'interact',npc:'city_bard',offer:'quest:accept:halloween_hunt'});await wait(p,()=>__self().quests.some(q=>q.id==='halloween_hunt'&&!q.claimed));
 await p.evaluate(()=>{City.close();Quests.track('halloween_hunt');});
 check(await p.evaluate(()=>Quests.mapMarkers(3).some(m=>m.quest==='halloween_hunt'&&m.npc===undefined&&m.x===105&&m.y===32)),'The tracked daily hunt points at the real haunted lantern');
 await debug(p,{op:'set_gold',gold:1000000});await wait(p,()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){
  await p.waitForTimeout(600);await send(p,{type:'interact',npc:'city_bard',offer:'halloween:hire:'+cls});await wait(p,n=>__snap.players.filter(p=>p.hired).length===n,i+1);
 }
 check(true,'A non-Alderhaven host hires four real fighters for the same shared daily quest');
 await stand(p,3,105,31);await wait(p,()=>__snap.players.filter(p=>p.hired&&p.zone===3&&p.hp>0&&Math.hypot(p.x-105,p.y-23)<=12).length===4);
 await p.evaluate(()=>Field.visitNpc('halloween_lantern'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="halloween:summon"]').click();
 await wait(p,()=>__snap.slimes.some(s=>s.kind==='hollow_rider'&&!s.dead));
 check(await p.evaluate(()=>__snap.halloween.level===99&&__snap.halloween.active),'The real lantern summons a level-99 elite for the five level-99 fighters');
 await p.evaluate(()=>City.close());await p.screenshot({path:path.join(world.runDir,'hollow-rider-summoned.png')});
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='hollow_rider').id);await debug(p,{op:'kill_enemy',id:enemy});
 await wait(p,()=>__self().seasonalRolls.halloween_hunt===20261026&&__self().quests.find(q=>q.id==='halloween_hunt').counts[0]===1);
 check(true,'An authoritative kill completes the daily hunt and persists the personal daily mount attempt');
 await npc(p,'nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await p.waitForTimeout(600);await send(p,{type:'interact',npc:'nacre_gardener',offer:'quest:claim:halloween_hunt'});await wait(p,()=>__self().seasonalClaims.halloween_hunt===20261026);
 check(await p.evaluate(g=>__self().gold===g+250,gold),'A different city host pays the daily reward exactly once');
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(id=>!Quests.offered(id).some(q=>q.id==='halloween_hunt'))),'All four city hosts share the same completed daily allowance');
 await debug(p,{op:'season_time',unix:1793055600});await wait(p,()=>__snap.seasons[0].day===20261027);
 check(await p.evaluate(()=>Quests.offered('asterion_singer').some(q=>q.id==='halloween_hunt')),'Stockholm midnight opens a new daily quest');
 await npc(p,'asterion_singer');await send(p,{type:'interact',npc:'asterion_singer',offer:'quest:accept:halloween_hunt'});await wait(p,()=>__self().quests.some(q=>q.id==='halloween_hunt'&&!q.claimed));
 await debug(p,{op:'give_mount',mount:'nightmare'});await wait(p,()=>__self().mounts.includes('nightmare'));
 await debug(p,{op:'season_time',unix:1794265200});await wait(p,()=>!Seasonal.active&&__snap.halloween===null&&!__self().quests.some(q=>q.id==='halloween_hunt'&&!q.claimed));
 check(await p.evaluate(()=>[0,4,9,17,3].every(z=>Seasonal.decor(z).length===0)&&__self().mounts.includes('nightmare')),'November 10 removes event dressing/quests while the earned mount stays owned');
 await stand(p,3,105,31);check(await p.evaluate(()=>!City.npcs.some(n=>n.id==='halloween_lantern')&&Halloween.objects(3).length===0),'The ritual lantern and its interaction disappear outside the season');
 // Authenticated rename of an existing flagged character; all progress survives.
 const id=await p.evaluate(()=>Online.id);await debug(p,{op:'set_gold',gold:123456});await wait(p,()=>__self().gold===123456);
 cp.execFileSync('python3',['-c',"import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('UPDATE characters SET name_key=NULL,rename_required=1 WHERE id=?',(sys.argv[2],)); c.commit()",world.db,id]);
 await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#name-change-form').waitFor({state:'visible'});
 check((await p.locator('#connection-text').textContent()).includes('needs a new name'),'A flagged existing guest gets the required rename flow before entering');
 await p.locator('#new-character-name').fill('HuntTaken');await p.locator('#name-change-form button').click();await wait(p,()=>document.querySelector('#connection-text').textContent.includes('already taken'));
 await p.locator('#new-character-name').fill('HuntRenewed');await p.locator('#name-change-form button').click();await wait(p,()=>Online.connected&&__self().look.name==='HuntRenewed');
 check(await p.evaluate(id=>Online.id===id&&__self().gold===123456&&__self().mounts.includes('nightmare'),id),'Rename keeps the same character, gold and owned mount after refusing a collision');
 await p.screenshot({path:path.join(world.runDir,'renamed-character.png')});await p.close();
 check(errors.length===0,'No browser errors: '+errors.join('; '));console.log(`halloween-hunt-ui: ${checks} checks; ${world.runDir}`);
}finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
