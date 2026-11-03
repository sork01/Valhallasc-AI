// Christmas, permanent seasonal titles and the actual seasonal city render. Private world only.
process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 w.startLevel=99;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:960},hasTouch:true,reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,lowGraphics:false,lowGraphicsSet:true}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;if(v.type==='achievements')window.__ach=v;}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Christmas Check');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:20000}),send=m=>p.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 await wait(()=>Online.connected&&Field.hero.hp>0);
 const stand=async(z,x,y)=>{await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Achievements.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:z,x,y});await wait(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[z,x,y]);await p.waitForTimeout(250);await p.evaluate(()=>ZoneJourney.clear());};
 const area=z=>p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z],z);
 const npc=async(id)=>{const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(n.zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await p.waitForTimeout(600);await send({type:'interact',npc:id,...(offer?{offer}:{})});await p.waitForTimeout(200);};
 await debug({op:'season_time',unix:1797289199});await wait(()=>!Seasonal.active);
 check(await p.evaluate(()=>!Seasonal.isActive('christmas')&&Christmas.objects(2).length===0&&!Quests.offered('baker').some(q=>q.id.startsWith('christmas'))),'December 14: Christmas dressing, tree and quests are absent');
 await debug({op:'season_time',unix:1797289200});await wait(()=>Seasonal.isActive('christmas'));
 check(await p.evaluate(()=>!Seasonal.isActive('halloween')&&__snap.halloween===null&&__snap.christmas!==null),'December 15 activates only Christmas, with its own ritual state');
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].every((z,i)=>[0,4,9,17].includes(i)?z.christmasDecor?.length>=20:!z.christmasDecor)),'Christmas city dressing is dense and restricted to the four major cities');
 const names={0:'alderhaven',4:'skaldholm',9:'nacrehold',17:'asterion'};
 if(!['hunt','titles'].includes(process.env.CHECK_ONLY))for(const z of [0,4,9,17]){
  const a=await area(z),q=a.quests.find(q=>q.season==='christmas'&&q.id!=='christmas_hunt');
  await npc(q.npc);const gold=await p.evaluate(()=>__self().gold);await interact(q.npc,'quest:accept:'+q.id);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),q.id);
  for(const o of q.objectives){if(o.kind==='talk'){await npc(o.target);await interact(o.target);}else{const place=a.places.find(v=>v.id===o.target);await stand(z,place.x,place.y);}}
  await wait(id=>__self().quests.find(q=>q.id===id).counts.every(n=>n>=1),q.id);
  await npc(q.npc);await interact(q.npc,'quest:claim:'+q.id);await wait(id=>__self().seasonalClaims[id]===2026,q.id);
  check(await p.evaluate(([g,r])=>__self().gold===g+r,[gold,q.rewardGold]),`${a.name}: actual talk/visit objectives and exact annual quest reward`);
  await interact(q.npc,'quest:accept:'+q.id);check(await p.evaluate(id=>!Quests.offered([WORLD_MAP,...WORLD_MAP.zones][Field.zone].quests.find(q=>q.id===id).npc).some(q=>q.id===id),q.id),`${a.name}: the annual quest cannot be rewarded twice`);
  const tree=a.christmasDecor.find(o=>o.kind==='christmasGrandTree')||a.christmasDecor.find(o=>o.kind==='christmasTree');
  await debug({op:'set_time',hour:18,freeze:true});await stand(z,tree.x+2,tree.y+2);await wait(()=>NpcArt.readyFor(City.npcs));await p.waitForTimeout(500);
  const drawn=await p.evaluate(()=>{const kinds=[],orig=City.drawObject;City.drawObject=function(g,o,...a){if(o.kind.startsWith('christmas'))kinds.push(o.kind);return orig.call(this,g,o,...a);};try{Field._debug.drawFrame(3);return kinds;}finally{City.drawObject=orig;}});
  check(drawn.length>=3&&!drawn.some(k=>k.startsWith('festival')),`${a.name}: several festive props draw in the real city view`);
  await p.evaluate(()=>{City.close();Quests.close();});await p.screenshot({path:path.join(w.runDir,`valhallasc-christmas-${names[z]}.png`)});
  await p.setViewportSize({width:844,height:390});await p.screenshot({path:path.join(w.runDir,`christmas-${names[z]}-phone.png`)});await p.setViewportSize({width:1440,height:960});
 }
 if(['hunt','titles'].includes(process.env.CHECK_ONLY))for(const [qid,host]of[['christmas_alder','baker'],['christmas_skald','city_bard'],['christmas_nacre','nacre_gardener'],['christmas_aster','asterion_singer']]){
  await npc(host);await interact(host,'quest:accept:'+qid);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),qid);await debug({op:'quest',id:qid,action:'complete'});await interact(host,'quest:claim:'+qid);await wait(id=>__self().seasonalClaims[id]===2026,qid);
 }
 await p.evaluate(()=>Achievements.open());await wait(()=>window.__ach?.entries);
 check(await p.evaluate(()=>__ach.entries.find(a=>a.id==='merry').complete===false&&__ach.maximum===2275),'Four city errands alone do not grant the Merry title');
 if(process.env.CHECK_ONLY==='titles'){
  await npc('baker');await interact('baker','quest:accept:christmas_hunt');await wait(()=>__self().quests.some(q=>q.id==='christmas_hunt'&&!q.claimed));await debug({op:'quest',id:'christmas_hunt',action:'complete'});await interact('baker','quest:claim:christmas_hunt');await wait(()=>__self().seasonalClaims.christmas_hunt===20261215);
  await send({type:'select_title',achievement:'merry'});await wait(()=>document.querySelector('#hud-name').textContent==='Christmas Check the Merry');await debug({op:'give_mount',mount:'reindeer'});await wait(()=>__self().mounts.includes('reindeer'));
 }else{
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>Quests.offered(n).some(q=>q.id==='christmas_hunt'))),'All four city hosts offer the same daily Grinch hunt');
 await npc('city_bard');await interact('city_bard','quest:accept:christmas_hunt');await wait(()=>__self().quests.some(q=>q.id==='christmas_hunt'&&!q.claimed));
 await p.evaluate(()=>{City.close();Quests.track('christmas_hunt');});
 check(await p.evaluate(()=>Quests.mapMarkers(2).some(m=>m.quest==='christmas_hunt'&&m.x===112&&m.y===100)),'The daily quest marker points at the actual great Christmas tree');
 await debug({op:'set_gold',gold:1000000});await wait(()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){await interact('city_bard','christmas:hire:'+cls);await wait(n=>__snap.players.filter(p=>p.hired).length===n,i+1);}
 await stand(2,110.5,100);await wait(()=>__snap.players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4);
 await p.evaluate(()=>Field.visitNpc('christmas_tree'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="christmas:summon"]').click();await wait(()=>__snap.slimes.some(s=>s.kind==='grinch'&&!s.dead));
 check(await p.evaluate(()=>__snap.christmas.active&&__snap.christmas.level===99),'Pressing the actual tree summons the five-fighter elite at the highest party level');
 await p.evaluate(()=>City.close());await wait(()=>Christmas.source);await p.screenshot({path:path.join(w.runDir,'christmas-grinch-summoned.png')});
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='grinch').id);await debug({op:'kill_enemy',id:enemy});await wait(()=>__self().seasonalRolls.christmas_hunt===20261215&&__self().quests.find(q=>q.id==='christmas_hunt').counts[0]===1);
 check(true,'The authoritative kill records one personal daily mount attempt and quest credit');
 await npc('nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await interact('nacre_gardener','quest:claim:christmas_hunt');await wait(()=>__self().seasonalClaims.christmas_hunt===20261215);
 check(await p.evaluate(g=>__self().gold===g+300,gold),'A different city host pays the single shared daily reward');
 await send({type:'select_title',achievement:'merry'});await wait(()=>document.querySelector('#hud-name').textContent==='Christmas Check the Merry');
 check(await p.evaluate(()=>__self().look.name==='Christmas Check'),'All five claimed Christmas quests unlock the suffix title without changing the character name');
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>!Quests.offered(n).some(q=>q.id==='christmas_hunt'))),'Changing city hosts cannot repeat today’s quest');
 await debug({op:'give_mount',mount:'reindeer'});await wait(()=>__self().mounts.includes('reindeer'));
 await debug({op:'season_time',unix:1797375600});await wait(()=>__snap.seasons.find(s=>s.id==='christmas').day===20261216);
 check(await p.evaluate(()=>Quests.offered('baker').some(q=>q.id==='christmas_hunt')),'Stockholm midnight opens the next daily hunt');
 await npc('baker');await interact('baker','quest:accept:christmas_hunt');await wait(()=>__self().quests.some(q=>q.id==='christmas_hunt'&&!q.claimed));
 }
 await debug({op:'season_time',unix:1798498800});await wait(()=>!Seasonal.active&&__snap.christmas===null&&!__self().quests.some(q=>q.id==='christmas_hunt'&&!q.claimed));
 await stand(2,110.5,100);
 check(await p.evaluate(()=>Christmas.objects(2).length===0&&!City.npcs.some(n=>n.id==='christmas_tree')&&[0,4,9,17].every(z=>Seasonal.decor(z).length===0)),'December 29 removes the tree, encounter, unfinished quest and all Christmas dressing');
 check(await p.evaluate(()=>__self().mounts.includes('reindeer')&&document.querySelector('#hud-name').textContent==='Christmas Check the Merry'),'Owned mount and earned suffix survive the event’s end');
 const id=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();if(await p.locator('#scene-create').isVisible())await p.locator('#go').click({timeout:60000});await wait(()=>Online.connected&&Field.hero.hp>0);
 check(await p.evaluate(id=>Online.id===id&&__self().mounts.includes('reindeer')&&document.querySelector('#hud-name').textContent==='Christmas Check the Merry',id),'Reconnect preserves the same character, permanent mount and selected seasonal title');
 await debug({op:'season_time',unix:1792969200});await wait(()=>Seasonal.isActive('halloween'));
 for(const [qid,host]of[['halloween_alder','baker'],['halloween_skald','city_bard'],['halloween_nacre','nacre_gardener'],['halloween_aster','asterion_singer'],['halloween_hunt','baker']]){
  await npc(host);await interact(host,'quest:accept:'+qid);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),qid);await debug({op:'quest',id:qid,action:'complete'});await interact(host,'quest:claim:'+qid);await wait(id=>!!__self().seasonalClaims[id],qid);
 }
 await send({type:'select_title',achievement:'hallowed'});await wait(()=>document.querySelector('#hud-name').textContent==='Christmas Check the Hallowed');
 check(await p.evaluate(()=>__self().look.name==='Christmas Check'),'The five claimed Halloween quests unlock the exact Hallowed suffix');
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(w.url);
 check(await sv.evaluate(()=>Locale.language==='sv'&&Locale.translate('the Merry')==='den julglade'&&Locale.translate('the Hallowed')==='den helgade'&&Locale.translate('Grinch')==='Grinchen'&&Locale.translate('Red-nosed Reindeer')==='Rödnäsad ren'),'The actual Swedish client translates both suffixes, the elite and the mount');await sv.close();
 check(errors.length===0,'No browser errors: '+errors.join('; '));
 fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`christmas-ui: ${checks} checks; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
