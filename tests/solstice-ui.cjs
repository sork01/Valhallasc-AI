// Focused Summer Solstice browser checks, private storage and actual rendered artwork.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:960},hasTouch:true,reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='decor')await p.route('**/seasonal.js',r=>r.fulfill({contentType:'application/javascript',body:fs.readFileSync(path.join(__dirname,'../client/seasonal.js'),'utf8').replace('solstice()?areas[zone]?.solsticeDecor||[]','solstice()?[]')}));
 await p.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:false,lowGraphicsSet:true,touchGraphicsSuggested:true}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('SunGuest');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:25000}),send=m=>p.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 await wait(()=>Online.connected&&Field.hero.hp>0);
 const stand=async(z,x,y)=>{await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:z,x,y});await wait(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[z,x,y]);await p.waitForTimeout(250);await p.evaluate(()=>ZoneJourney.clear());};
 const npc=async(id)=>{const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(n.zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await p.waitForTimeout(600);await send({type:'interact',npc:id,...(offer?{offer}:{})});await p.waitForTimeout(200);};
 if(process.env.CHECK_ONLY==='presentation'){
  await debug({op:'season_time',unix:1813183200});await wait(()=>Seasonal.isActive('solstice'));
  const table=await p.evaluate(()=>WORLD_MAP.solsticeDecor.find(o=>o.kind==='solsticeTable'));await stand(0,table.x+1,table.y+1);await p.waitForFunction(()=>NpcArt.readyFor(City.npcs));
  await debug({op:'set_time',hour:12,freeze:true});await wait(()=>Math.abs(DayNight.hour-12)<.1);
  check(await p.evaluate(()=>['solsticePole','solsticeTable','solsticeBirch'].every(k=>Seasonal.decor(0).some(o=>o.kind===k))),'Alderhaven renders its pole, birch and summer table together');
  await p.evaluate(()=>{City.close();Field._debug.drawFrame(3);});await p.screenshot({path:path.join(w.runDir,'solstice-alderhaven-table-day.png')});
 }
 if(!['phone','presentation'].includes(process.env.CHECK_ONLY)){
 await debug({op:'season_time',unix:1813183199});await wait(()=>!Seasonal.active);
 check(await p.evaluate(()=>Solstice.objects(2).length===0&&!Quests.offered('baker').some(q=>q.id.startsWith('solstice'))),'The day before the season has no pole, dressing or quests');
 await debug({op:'season_time',unix:1813183200});await wait(()=>Seasonal.isActive('solstice'));
 check(await p.evaluate(()=>__snap.solstice!==null&&__snap.easter===null&&__snap.christmas===null),'The exact Stockholm start activates Summer Solstice alone');
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].every((z,i)=>[0,4,9,17,24].includes(i)?z.solsticeDecor?.length>=20:!z.solsticeDecor)),'Midsummer scenery is dense and restricted to four city bounds');
 check(await p.evaluate(()=>[0,4,9,17].every(z=>Seasonal.decor(z).some(o=>o.kind==='solsticePole'))),'The production seasonal renderer exposes a midsummer pole in every city');
 for(const [z,name]of[[0,'alderhaven'],[4,'skaldholm'],[9,'nacrehold'],[17,'asterion']]){
  const a=await p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z],z),q=a.quests.find(q=>q.season==='solstice'&&q.id!=='solstice_hunt');
  await npc(q.npc);const gold=await p.evaluate(()=>__self().gold);await interact(q.npc,'quest:accept:'+q.id);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),q.id);
  for(const o of q.objectives){if(o.kind==='talk'){await npc(o.target);await interact(o.target);}else{const place=a.places.find(v=>v.id===o.target);await stand(z,place.x,place.y);}}
  await wait(id=>__self().quests.find(q=>q.id===id).counts.every(n=>n>=1),q.id);await npc(q.npc);await interact(q.npc,'quest:claim:'+q.id);await wait(id=>__self().seasonalClaims[id]===2027,q.id);
  check(await p.evaluate(([g,r])=>__self().gold===g+r,[gold,q.rewardGold]),`${name}: real talk/visit objectives pay the exact annual reward`);
  await interact(q.npc,'quest:accept:'+q.id);check(await p.evaluate(([id,host])=>!Quests.offered(host).some(q=>q.id===id),[q.id,q.npc]),`${name}: annual errand cannot pay twice`);
  const pole=a.solsticeDecor.find(o=>o.kind==='solsticePole');await stand(z,pole.x+2,pole.y+2);
  check(await p.evaluate(()=>Seasonal.decor(Field.zone).some(o=>o.kind==='solsticePole'&&o.danceRadius===2.5)),`${name}: actual seasonal renderer includes the pole and clear dancing circle`);
  for(const [hour,suffix]of[[12,'day'],[22,'night']]){await debug({op:'set_time',hour,freeze:true});await wait(h=>Math.abs(DayNight.hour-h)<.1,hour);await p.evaluate(()=>{City.close();Field._debug.drawFrame(3);});await p.screenshot({path:path.join(w.runDir,`solstice-${name}-${suffix}.png`)});}
 }
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>Quests.offered(n).some(q=>q.id==='solstice_hunt'))),'All four hosts offer the same daily hunt');
 await npc('city_bard');await interact('city_bard','quest:accept:solstice_hunt');await wait(()=>__self().quests.some(q=>q.id==='solstice_hunt'&&!q.claimed));
 await p.evaluate(()=>{City.close();Quests.track('solstice_hunt');});
 check(await p.evaluate(()=>Quests.mapMarkers(2).some(m=>m.quest==='solstice_hunt'&&m.x===112&&m.y===100)),'The tracked hunt points to the real Sunwoven Midsummer Pole');
 await debug({op:'set_gold',gold:1000000});await wait(()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){await interact('city_bard','solstice:hire:'+cls);await wait(n=>__snap.players.filter(p=>p.hired).length===n,i+1);}
 await stand(2,110.5,100);await wait(()=>__snap.players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4);
 await p.evaluate(()=>Field.visitNpc('solstice_pole'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="solstice:summon"]').click();await wait(()=>__snap.solstice.active);
 check(await p.evaluate(()=>__snap.solstice.level===99&&__snap.slimes.some(s=>s.kind==='birchcrown'&&!s.dead)),'The pole summons the Guardian at the frozen highest fighter level');
 await p.evaluate(()=>City.close());await wait(()=>Solstice.source);await p.screenshot({path:path.join(w.runDir,'solstice-birchcrown.png')});
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='birchcrown').id);await debug({op:'kill_enemy',id:enemy});await wait(()=>__self().quests.find(q=>q.id==='solstice_hunt').counts[0]===1);
 check(await p.evaluate(()=>__self().seasonalRolls.solstice_hunt===20270617),'The credited kill consumes the independent personal daily mount attempt');
 await debug({op:'give_mount',mount:'sunwoven'}); // Persistence fixture; Rust verifies the actual 5% outcomes.
 await npc('nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await interact('nacre_gardener','quest:claim:solstice_hunt');await wait(()=>__self().seasonalClaims.solstice_hunt===20270617);
 check(await p.evaluate(g=>__self().gold===g+300&&__self().mounts.includes('sunwoven'),gold),'Another city host pays the shared reward and preserves mount ownership');
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>!Quests.offered(n).some(q=>q.id==='solstice_hunt'))),'Changing hosts cannot reopen the same daily hunt');
 await debug({op:'season_time',unix:1813269600});await wait(()=>__snap.seasons.find(s=>s.id==='solstice').day===20270618);
 check(await p.evaluate(()=>Quests.offered('baker').some(q=>q.id==='solstice_hunt')),'Stockholm midnight opens the next daily hunt');
 await npc('baker');await interact('baker','quest:accept:solstice_hunt');await wait(()=>__self().quests.some(q=>q.id==='solstice_hunt'&&!q.claimed));
 await debug({op:'season_time',unix:1813960799});await wait(()=>__snap.seasons[0]?.day===20270625);
 check(await p.evaluate(()=>Seasonal.isActive('solstice')),'The whole fourth day after solstice remains active');
 await debug({op:'season_time',unix:1813960800});await wait(()=>!Seasonal.active&&__snap.solstice===null&&!__self().quests.some(q=>q.id==='solstice_hunt'&&!q.claimed));await stand(2,110.5,100);
 check(await p.evaluate(()=>Solstice.objects(2).length===0&&!City.npcs.some(n=>n.id==='solstice_pole')&&[0,4,9,17].every(z=>Seasonal.decor(z).length===0)),'Expiry removes the pole, encounter, unfinished quest and all city dressing');
 const id=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();if(await p.locator('#scene-create').isVisible())await p.locator('#go').click({timeout:60000});await wait(()=>Online.connected&&Field.hero.hp>0);
 check(await p.evaluate(id=>Online.id===id&&__self().mounts.includes('sunwoven')&&__self().seasonalRolls.solstice_hunt===20270617,id),'Reconnect preserves the same character, mount and consumed attempt');
 }
 // A Swedish landscape phone, with the normal quest window and translated summon button.
 await p.evaluate(()=>{const s=JSON.parse(localStorage.getItem('valhallasc.save.v1'));s.lang='sv';localStorage.setItem('valhallasc.save.v1',JSON.stringify(s));});await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();await wait(()=>Online.connected);await p.setViewportSize({width:844,height:390});
 await debug({op:'season_time',unix:1813183200});await wait(()=>Seasonal.isActive('solstice'));await stand(2,110.5,100);await p.evaluate(()=>Field.visitNpc('solstice_pole'));
 check(await p.locator('[data-offer="solstice:summon"] .gossip-label').textContent()==='Framkalla den Björkkrönte väktaren','Swedish phone presents the translated summon action');
 check(await p.evaluate(()=>Locale.translate('Sunwoven Stag')==='Solvävd hjort'&&Locale.translate('Summer Solstice')==='Sommarsolståndet'),'Swedish presents the mount and season names');
 const box=await p.locator('[data-offer="solstice:summon"]').boundingBox();check(box&&box.x>=0&&box.y>=0&&box.x+box.width<=844&&box.y+box.height<=390,'The real Swedish phone summon button fits the viewport');
 await p.screenshot({path:path.join(w.runDir,'solstice-swedish-phone.png')});
 check(errors.length===0,'No browser errors: '+errors.join('; '));fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`solstice-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
