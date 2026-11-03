// Easter, permanent seasonal titles and the actual seasonal city render. Private world only.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:960},hasTouch:true,reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='decor')await p.route('**/seasonal.js',route=>route.fulfill({contentType:'application/javascript',body:fs.readFileSync(path.join(__dirname,'../client/seasonal.js'),'utf8').replace('easter()?areas[zone]?.easterDecor||[]','easter()?[]')}));
 await p.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:false,lowGraphicsSet:true}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;if(v.type==='achievements')window.__ach=v;}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Sork');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:20000}),send=m=>p.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 await wait(()=>Online.connected&&Field.hero.hp>0);
 const stand=async(z,x,y)=>{await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Achievements.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:z,x,y});await wait(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[z,x,y]);await p.waitForTimeout(250);await p.evaluate(()=>ZoneJourney.clear());};
 const area=z=>p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z],z);
 const npc=async(id)=>{const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(n.zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await p.waitForTimeout(600);await send({type:'interact',npc:id,...(offer?{offer}:{})});await p.waitForTimeout(200);};
 await debug({op:'season_time',unix:1806015599});await wait(()=>!Seasonal.active);
 check(await p.evaluate(()=>!Seasonal.isActive('easter')&&Easter.objects(2).length===0&&!Quests.offered('baker').some(q=>q.id.startsWith('easter'))),'March 25: Easter dressing, shrine and quests are absent');
 await debug({op:'season_time',unix:1806015600});await wait(()=>Seasonal.isActive('easter'));
 check(await p.evaluate(()=>!Seasonal.isActive('halloween')&&__snap.halloween===null&&__snap.easter!==null),'March 26 activates only Easter, with its own ritual state');
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].every((z,i)=>[0,4,9,17].includes(i)?z.easterDecor?.length>=20:!z.easterDecor)),'Easter city dressing is dense and restricted to the four major cities');
 const names={0:'alderhaven',4:'skaldholm',9:'nacrehold',17:'asterion'};
 if(!['hunt','titles'].includes(process.env.CHECK_ONLY))for(const z of [0,4,9,17]){
  const a=await area(z),q=a.quests.find(q=>q.season==='easter'&&q.id!=='easter_hunt');
  await npc(q.npc);const gold=await p.evaluate(()=>__self().gold);await interact(q.npc,'quest:accept:'+q.id);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),q.id);
  for(const o of q.objectives){if(o.kind==='talk'){await npc(o.target);await interact(o.target);}else{const place=a.places.find(v=>v.id===o.target);await stand(z,place.x,place.y);}}
  await wait(id=>__self().quests.find(q=>q.id===id).counts.every(n=>n>=1),q.id);
  await npc(q.npc);await interact(q.npc,'quest:claim:'+q.id);await wait(id=>__self().seasonalClaims[id]===2027,q.id);
  check(await p.evaluate(([g,r])=>__self().gold===g+r,[gold,q.rewardGold]),`${a.name}: actual talk/visit objectives and exact annual quest reward`);
  await interact(q.npc,'quest:accept:'+q.id);check(await p.evaluate(id=>!Quests.offered([WORLD_MAP,...WORLD_MAP.zones][Field.zone].quests.find(q=>q.id===id).npc).some(q=>q.id===id),q.id),`${a.name}: the annual quest cannot be rewarded twice`);
  const tree=a.easterDecor.find(o=>o.kind==='easterGrandEgg')||a.easterDecor.find(o=>o.kind==='easterEgg');
  await debug({op:'set_time',hour:18,freeze:true});await stand(z,tree.x+2,tree.y+2);await wait(()=>NpcArt.readyFor(City.npcs));await p.waitForTimeout(500);
  const drawn=await p.evaluate(()=>{const kinds=[],orig=City.drawObject;City.drawObject=function(g,o,...a){if(o.kind.startsWith('easter'))kinds.push(o.kind);return orig.call(this,g,o,...a);};try{Field._debug.drawFrame(3);return kinds;}finally{City.drawObject=orig;}});
  check(drawn.length>=3&&!drawn.some(k=>k.startsWith('festival')),`${a.name}: several festive props draw in the real city view`);
  await p.evaluate(()=>{City.close();Quests.close();});await debug({op:'set_time',hour:12,freeze:true});await wait(()=>DayNight.nightMix===0);await p.screenshot({path:path.join(w.runDir,`valhallasc-easter-${names[z]}-day.png`)});
  await debug({op:'set_time',hour:22,freeze:true});await wait(()=>DayNight.nightMix>.9);await p.screenshot({path:path.join(w.runDir,`valhallasc-easter-${names[z]}-night.png`)});
  await p.setViewportSize({width:844,height:390});await p.screenshot({path:path.join(w.runDir,`valhallasc-easter-${names[z]}-phone.png`)});await p.setViewportSize({width:1440,height:960});
 }
 if(['hunt','titles'].includes(process.env.CHECK_ONLY))for(const [qid,host]of[['easter_alder','baker'],['easter_skald','city_bard'],['easter_nacre','nacre_gardener'],['easter_aster','asterion_singer']]){
  await npc(host);await interact(host,'quest:accept:'+qid);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),qid);await debug({op:'quest',id:qid,action:'complete'});await interact(host,'quest:claim:'+qid);await wait(id=>__self().seasonalClaims[id]===2027,qid);
 }
 await p.evaluate(()=>Achievements.open());await wait(()=>window.__ach?.entries);
 check(await p.evaluate(()=>__ach.entries.find(a=>a.id==='eggstraordinary').complete===false&&__ach.maximum===2325),'Four city errands alone do not grant Eggstraordinary Easter');
 if(process.env.CHECK_ONLY==='titles'){
  await npc('baker');await interact('baker','quest:accept:easter_hunt');await wait(()=>__self().quests.some(q=>q.id==='easter_hunt'&&!q.claimed));await debug({op:'quest',id:'easter_hunt',action:'complete'});await interact('baker','quest:claim:easter_hunt');await wait(()=>__self().seasonalClaims.easter_hunt===20270326);
  await wait(()=>document.querySelector('#achievement-toast-name').textContent.includes('Eggstraordinary Easter'));check(true,'The normal achievement celebration receives the Eggstraordinary Easter award');
 await send({type:'select_title',achievement:'eggstraordinary'});await wait(()=>document.querySelector('#hud-name').textContent==='Sork the Springbringer');
 }else{
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>Quests.offered(n).some(q=>q.id==='easter_hunt'))),'All four city hosts offer the same daily Bloomwarden hunt');
 await npc('city_bard');await interact('city_bard','quest:accept:easter_hunt');await wait(()=>__self().quests.some(q=>q.id==='easter_hunt'&&!q.claimed));
 await p.evaluate(()=>{City.close();Quests.track('easter_hunt');});
 check(await p.evaluate(()=>Quests.mapMarkers(2).some(m=>m.quest==='easter_hunt'&&m.x===112&&m.y===100)),'The daily quest marker points at the actual Springtide Egg Basket');
 await debug({op:'set_gold',gold:1000000});await wait(()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){await interact('city_bard','easter:hire:'+cls);await wait(n=>__snap.players.filter(p=>p.hired).length===n,i+1);}
 await stand(2,110.5,100);await wait(()=>__snap.players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4);
 await p.evaluate(()=>Field.visitNpc('easter_shrine'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="easter:summon"]').click();await wait(()=>__snap.slimes.some(s=>s.kind==='bloomwarden'&&!s.dead));
 check(await p.evaluate(()=>__snap.easter.active&&__snap.easter.level===99),'Pressing the actual shrine summons the five-fighter elite at the highest party level');
 await p.evaluate(()=>City.close());await wait(()=>Easter.source);await p.screenshot({path:path.join(w.runDir,'valhallasc-easter-bloomwarden.png')});
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='bloomwarden').id);await debug({op:'kill_enemy',id:enemy});await wait(()=>__self().quests.find(q=>q.id==='easter_hunt').counts[0]===1);
 check(await p.evaluate(()=>__self().seasonalRolls.easter_hunt===20270326),'The kill grants quest credit and consumes the personal 5% bunny roll');
 await debug({op:'give_mount',mount:'springtide'}); // Seed ownership for persistence; deterministic reward checks are in Rust.
 await npc('nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await interact('nacre_gardener','quest:claim:easter_hunt');await wait(()=>__self().seasonalClaims.easter_hunt===20270326);
 check(await p.evaluate(g=>__self().gold===g+300&&__self().mounts.includes('springtide'),gold),'A different city host pays the daily reward and preserves the seeded bunny');
 await wait(()=>document.querySelector('#achievement-toast-name').textContent.includes('Eggstraordinary Easter'));check(true,'The normal achievement celebration receives the Eggstraordinary Easter award');
 await send({type:'select_title',achievement:'eggstraordinary'});await wait(()=>document.querySelector('#hud-name').textContent==='Sork the Springbringer');
 check(await p.evaluate(()=>__self().look.name==='Sork'),'All five claimed Easter quests unlock the exact Springbringer suffix without changing Sork');
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>!Quests.offered(n).some(q=>q.id==='easter_hunt'))),'Changing city hosts cannot repeat today’s quest');

 await debug({op:'season_time',unix:1806102000});await wait(()=>__snap.seasons.find(s=>s.id==='easter').day===20270327);
 check(await p.evaluate(()=>Quests.offered('baker').some(q=>q.id==='easter_hunt')),'Stockholm midnight opens the next daily hunt');
 await npc('baker');await interact('baker','quest:accept:easter_hunt');await wait(()=>__self().quests.some(q=>q.id==='easter_hunt'&&!q.claimed));
 }
 await debug({op:'season_time',unix:1806962400});await wait(()=>!Seasonal.active&&__snap.easter===null&&!__self().quests.some(q=>q.id==='easter_hunt'&&!q.claimed));
 await stand(2,110.5,100);
 check(await p.evaluate(()=>Easter.objects(2).length===0&&!City.npcs.some(n=>n.id==='easter_shrine')&&[0,4,9,17].every(z=>Seasonal.decor(z).length===0)),'April 6 removes the shrine, encounter, unfinished quest and all Easter dressing');
 check(await p.evaluate(()=>__self().mounts.includes('springtide')&&document.querySelector('#hud-name').textContent==='Sork the Springbringer'),'Owned mount and earned suffix survive the event’s end');
 await p.evaluate(()=>Achievements.open());await send({type:'achievements'});await wait(()=>__ach?.entries.find(a=>a.id==='eggstraordinary')?.complete);
 check(await p.evaluate(()=>__ach.entries.find(a=>a.id==='eggstraordinary').points===25&&__ach.entries.find(a=>a.id==='eggstraordinary').title==='the Springbringer'),'Eggstraordinary Easter has 25 points and the exact suffix title');
 await p.setViewportSize({width:844,height:390});check(await p.locator('#achievement-title-select option[value="eggstraordinary"]').textContent()==='the Springbringer','Phone title selector offers the earned suffix');await p.setViewportSize({width:1440,height:960});
 const id=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();if(await p.locator('#scene-create').isVisible())await p.locator('#go').click({timeout:60000});await wait(()=>Online.connected&&Field.hero.hp>0);
 check(await p.evaluate(id=>Online.id===id&&__self().mounts.includes('springtide')&&document.querySelector('#hud-name').textContent==='Sork the Springbringer',id),'Reconnect preserves the same character, permanent mount and selected seasonal title');
 check(await p.evaluate(()=>Achievements.displayName({look:{name:'Sork'},achievementTitle:'the Merry'})==='Sork the Merry'&&Achievements.displayName({look:{name:'Sork'},achievementTitle:'the Springbringer'})==='Sork the Springbringer'),'Merry and Springbringer both use the existing single-space suffix renderer');
 const other=await browser.newPage({viewport:{width:844,height:390},hasTouch:true});
 await other.addInitScript(()=>{window.AudioContext=undefined;window.__names=[];const fill=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(s,...a){if(String(s).includes('Sork'))window.__names.push(String(s));return fill.call(this,s,...a);};localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false}));});
 await other.goto(w.url);await other.locator('#start').click();await other.locator('#login-guest').click();await other.locator('#cls-warrior').click();await other.locator('#name').fill('SpringWitness');await other.locator('#go').click({timeout:60000});await other.waitForFunction(()=>Online.connected&&Field.hero.hp>0);
 await other.evaluate(()=>Online.send({type:'debug',command:{op:'teleport',zone:2,x:110.5,y:100}}));
 await other.waitForFunction(()=>window.__names.includes('Sork the Springbringer'),null,{timeout:20000});check(true,'A second real browser paints Sork the Springbringer on the remote world nameplate');await other.close();
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(w.url);
 check(await sv.evaluate(()=>Locale.language==='sv'&&Locale.translate('the Springbringer')==='vårbringaren'&&Locale.translate('The Bloomwarden')==='Blomväktaren'&&Locale.translate('Springtide Bunny')==='Vårtidens kanin'),'The actual Swedish client presents the permanent suffix, elite and bunny');await sv.close();
 check(errors.length===0,'No browser errors: '+errors.join('; '));
 fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`easter-ui: ${checks} checks; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
