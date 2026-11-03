// New Year only, private server: dates, actual UI hunt/claim, fireworks pixels and screenshots.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
let replaying=process.env.CHECK_FROM==='rewards';
const check=(v,s)=>{if(replaying)return;assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:960},hasTouch:true,reducedMotion:'no-preference'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;window.__ach=null;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:false,lowGraphicsSet:true}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;if(v.type==='achievements')window.__ach=v;}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Newyear Check');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:30000}),send=m=>p.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 await wait(()=>Online.connected&&Field.hero.hp>0);
 const stand=async(z,x,y,tolerance=2.8)=>{await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Achievements.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:z,x,y});await wait(([z,x,y,tolerance])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<tolerance,[z,x,y,tolerance]);await p.waitForTimeout(300);await p.evaluate(()=>ZoneJourney.clear());};
 const npc=async(id)=>{const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(n.zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await p.waitForTimeout(650);await send({type:'interact',npc:id,...(offer?{offer}:{})});await p.waitForTimeout(250);};
 const capture=async(name,t=2.11)=>{const png=await p.evaluate(t=>{Field._debug.drawFrame(t);return document.querySelector('#fieldcv').toDataURL();},t);fs.writeFileSync(path.join(w.runDir,name),Buffer.from(png.split(',')[1],'base64'));};
 if(!['visual','rewards'].includes(process.env.CHECK_FROM)){
 await debug({op:'season_time',unix:1798498799});await wait(()=>Seasonal.isActive('christmas'));
 check(await p.evaluate(()=>!Seasonal.isActive('newyear')&&NewYear.objects(2).length===0&&NewYear.fireworksPlan(0,{x:36,y:83},2,false,1440,960).length===0),'December 28: New Year summon and fireworks are absent');
 await debug({op:'season_time',unix:1798498800});await wait(()=>Seasonal.isActive('newyear'));
 check(await p.evaluate(()=>!Seasonal.isActive('christmas')&&__snap.christmas===null&&__snap.newyear!==null),'December 29: New Year replaces Christmas at Stockholm midnight');
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].flatMap(a=>a.quests).filter(q=>q.season==='newyear').length===1&&['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>Quests.offered(n).some(q=>q.id==='newyear_hunt'))),'Exactly one shared New Year quest is offered in all four cities');
 }else{await debug({op:'season_time',unix:1798498800});await wait(()=>Seasonal.isActive('newyear'));}
 if(process.env.CHECK_FROM!=='rewards'){
 for(const [z,name]of[[0,'alderhaven'],[4,'skaldholm'],[9,'nacrehold'],[17,'asterion']]){
  const centre=await p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z].city.plaza,z);
  await debug({op:'set_time',hour:19,freeze:true});await stand(z,centre.x,centre.y,8);await wait(()=>NpcArt.readyFor(City.npcs));await p.waitForTimeout(500);
  const stats=await p.evaluate(z=>{const a=[WORLD_MAP,...WORLD_MAP.zones][z],c=a.city,inTown={x:(c.x0+c.x1)/2,y:(c.y0+c.y1)/2},outside={x:c.x1+1,y:c.y1+1};const cv=document.createElement('canvas');cv.width=1440;cv.height=960;const g=cv.getContext('2d');const draw=NewYear.drawFireworks(g,z,inTown,2.11,1440,960,false);let lit=0;const data=g.getImageData(0,0,1440,960).data;for(let i=3;i<data.length;i+=4)if(data[i]>0)lit++;return{dense:NewYear.fireworksPlan(z,inTown,2,false,1440,960).length,sparse:NewYear.fireworksPlan(z,outside,2,false,1440,960).length,draw,lit};},z);
  check(stats.dense===10&&stats.sparse===2&&stats.draw.bursts>=5&&stats.draw.rays<=240&&stats.lit>1000,`${name}: dense city fireworks, sparse beyond the real boundary, visible sparks within the fixed rendering budget`);
  await capture(`valhallasc-newyear-${name}.png`);
 }
 await p.emulateMedia({reducedMotion:'reduce'});
 const still=await p.evaluate(()=>{const c=[WORLD_MAP,...WORLD_MAP.zones][17].city,h={x:c.plaza.x,y:c.plaza.y};const a=NewYear.fireworksPlan(17,h,0,true,1440,960),b=NewYear.fireworksPlan(17,h,100,true,1440,960);return{same:JSON.stringify(a)===JSON.stringify(b),count:a.length,allZones:[WORLD_MAP,...WORLD_MAP.zones].every((_,z)=>NewYear.fireworksPlan(z,{x:-1,y:-1},2,false,1440,960).length===2)};});
 check(still.same&&still.count===4&&still.allZones,'Reduced motion is still and subdued; sparse fireworks cover every zone, including dungeon templates');
 await p.setViewportSize({width:844,height:390});await capture('valhallasc-newyear-phone.png');await p.setViewportSize({width:1440,height:960});await p.emulateMedia({reducedMotion:'no-preference'});
 }
 await npc('city_bard');await interact('city_bard','quest:accept:newyear_hunt');await wait(()=>__self().quests.some(q=>q.id==='newyear_hunt'&&!q.claimed));
 await p.evaluate(()=>Quests.track('newyear_hunt'));
 check(await p.evaluate(()=>Quests.mapMarkers(2).some(m=>m.quest==='newyear_hunt'&&m.x===112&&m.y===100)),'The quest tracks the actual Festival Launchpad');
 await debug({op:'set_gold',gold:1000000});await wait(()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){await interact('city_bard','newyear:hire:'+cls);await wait(n=>__snap.players.filter(p=>p.hired).length===n,i+1);}
 await stand(2,110.5,100);await wait(()=>__snap.players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4);
 check(await p.evaluate(()=>!City.npcs.some(n=>n.id==='christmas_tree')&&City.npcs.some(n=>n.id==='newyear_launchpad')),'The New Year launchpad uses the winter clearing without the retired Christmas tree');
 await capture('valhallasc-newyear-outdoors.png');
 await p.evaluate(()=>Field.visitNpc('newyear_launchpad'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="newyear:summon"]').click();await wait(()=>__snap.slimes.some(s=>s.kind==='starrocketeer'&&!s.dead));
 check(await p.evaluate(()=>__snap.newyear.active&&__snap.newyear.level===99),'The actual summon UI starts the five-fighter elite at the highest party level');
 await p.evaluate(()=>City.close());await wait(()=>NewYear.source);await capture('valhallasc-newyear-rocketeer.png');
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='starrocketeer').id);await debug({op:'kill_enemy',id:enemy});await wait(()=>__self().seasonalRolls.newyear_hunt===20261229&&__self().quests.find(q=>q.id==='newyear_hunt').counts[0]===1);
 replaying=false;
 await p.evaluate(()=>Achievements.open());await wait(()=>window.__ach?.entries);
 check(await p.evaluate(()=>!__ach.entries.find(a=>a.id==='newyear').complete),'A ready, unclaimed hunt does not award the achievement');
 await npc('nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await interact('nacre_gardener','quest:claim:newyear_hunt');await wait(()=>__self().seasonalClaims.newyear_hunt===20261229);
 await p.evaluate(()=>Achievements.open());await wait(()=>__ach?.entries.find(a=>a.id==='newyear').complete);
 check(await p.evaluate(g=>__self().gold===g+300&&__ach.maximum===2275&&__ach.entries.find(a=>a.id==='newyear').points===25,gold),'A different city host pays the shared quest and awards the 25-point achievement');
 await p.screenshot({path:path.join(w.runDir,'valhallasc-newyear-achievement.png')});
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>!Quests.offered(n).some(q=>q.id==='newyear_hunt'))),'Changing hosts cannot repeat today’s quest');
 await debug({op:'give_mount',mount:'rocket'});await wait(()=>__self().mounts.includes('rocket'));
 await send({type:'select_mount',mount:'rocket'});await p.evaluate(()=>MountArt.preload('rocket'));await wait(()=>MountArt.ready('rocket'));
 await stand(2,110.5,100);await send({type:'mount',mounted:true});await wait(()=>__self().mounted);await capture('valhallasc-newyear-rocket.png');
 await debug({op:'season_time',unix:1798758000});await wait(()=>__snap.seasons.find(s=>s.id==='newyear')?.day===20270101);
 check(await p.evaluate(()=>__snap.seasons.find(s=>s.id==='newyear').year===2026&&Quests.offered('baker').some(q=>q.id==='newyear_hunt')),'January 1 retains the December season year and opens a new daily allowance');
 await npc('baker');await interact('baker','quest:accept:newyear_hunt');await wait(()=>__self().quests.some(q=>q.id==='newyear_hunt'&&!q.claimed));
 await debug({op:'season_time',unix:1798930799});await wait(()=>__snap.seasons.find(s=>s.id==='newyear')?.day===20270102);
 check(await p.evaluate(()=>Seasonal.isActive('newyear')),'January 2 remains active through its final second');
 await debug({op:'season_time',unix:1798930800});await wait(()=>!Seasonal.isActive('newyear')&&__snap.newyear===null);
 check(await p.evaluate(()=>NewYear.objects(2).length===0&&NewYear.fireworksPlan(2,{x:103,y:100},3,false,1440,960).length===0&&!__self().quests.some(q=>q.id==='newyear_hunt'&&!q.claimed)&&__self().mounts.includes('rocket')),'January 3 retires unfinished content and fireworks while keeping the rocket');
 const id=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();if(await p.locator('#scene-create').isVisible())await p.locator('#go').click({timeout:60000});await wait(()=>Online.connected&&Field.hero.hp>0);
 await p.evaluate(()=>Achievements.open());await wait(()=>__ach?.entries.find(a=>a.id==='newyear').complete);
 check(await p.evaluate(id=>Online.id===id&&__self().mounts.includes('rocket')&&__self().seasonalRolls.newyear_hunt===20261229,id),'Reconnect preserves permanent achievement, rocket and spent daily attempt');
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(w.url);
 check(await sv.evaluate(()=>Locale.translate('Starflight Rocket')==='Stjärnflyktsraket'&&Locale.translate('Ring in the New Year')==='Ring in det nya året'&&Locale.translate('The Starfire Rocketeer')==='Stjärneldsraketören'),'Swedish translates the New Year elite, mount and achievement');await sv.close();
 check(errors.length===0,'No real-client browser errors: '+errors.join('; '));
 fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`newyear-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
