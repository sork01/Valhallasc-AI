// Valentines, permanent seasonal titles and the actual seasonal city render. Private world only.
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
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Sork');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:20000}),send=m=>p.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 await wait(()=>Online.connected&&Field.hero.hp>0);
 const stand=async(z,x,y)=>{await p.evaluate(()=>{City.close();Quests.close();WorldMap.close();Achievements.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone:z,x,y});await wait(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.3,[z,x,y]);await p.waitForTimeout(250);await p.evaluate(()=>ZoneJourney.clear());};
 const area=z=>p.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z],z);
 const npc=async(id)=>{const n=await p.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>z.npcs.filter(n=>n.id===id).map(n=>({...n,zone})))[0],id);await stand(n.zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await p.waitForTimeout(600);await send({type:'interact',npc:id,...(offer?{offer}:{})});await p.waitForTimeout(200);};
 await debug({op:'season_time',unix:1802213999});await wait(()=>!Seasonal.active);
 check(await p.evaluate(()=>!Seasonal.isActive('valentine')&&Valentines.objects(2).length===0&&!Quests.offered('baker').some(q=>q.id.startsWith('valentine'))),'February 9: Valentines dressing, shrine and quests are absent');
 await debug({op:'season_time',unix:1802214000});await wait(()=>Seasonal.isActive('valentine'));
 check(await p.evaluate(()=>!Seasonal.isActive('halloween')&&__snap.halloween===null&&__snap.valentine!==null),'February 10 activates only Valentines, with its own ritual state');
 check(await p.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].every((z,i)=>[0,4,9,17,24].includes(i)?z.valentineDecor?.length>=20:!z.valentineDecor)),'Valentines city dressing is dense and restricted to the four major cities');
 const names={0:'alderhaven',4:'skaldholm',9:'nacrehold',17:'asterion'};
 if(!['hunt','titles'].includes(process.env.CHECK_ONLY))for(const z of [0,4,9,17]){
  const a=await area(z),q=a.quests.find(q=>q.season==='valentine'&&q.id!=='valentine_hunt');
  await npc(q.npc);const gold=await p.evaluate(()=>__self().gold);await interact(q.npc,'quest:accept:'+q.id);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),q.id);
  for(const o of q.objectives){if(o.kind==='talk'){await npc(o.target);await interact(o.target);}else{const place=a.places.find(v=>v.id===o.target);await stand(z,place.x,place.y);}}
  await wait(id=>__self().quests.find(q=>q.id===id).counts.every(n=>n>=1),q.id);
  await npc(q.npc);await interact(q.npc,'quest:claim:'+q.id);await wait(id=>__self().seasonalClaims[id]===2027,q.id);
  check(await p.evaluate(([g,r])=>__self().gold===g+r,[gold,q.rewardGold]),`${a.name}: actual talk/visit objectives and exact annual quest reward`);
  await interact(q.npc,'quest:accept:'+q.id);check(await p.evaluate(id=>!Quests.offered([WORLD_MAP,...WORLD_MAP.zones][Field.zone].quests.find(q=>q.id===id).npc).some(q=>q.id===id),q.id),`${a.name}: the annual quest cannot be rewarded twice`);
  const tree=a.valentineDecor.find(o=>o.kind==='valentineGrandHeart')||a.valentineDecor.find(o=>o.kind==='valentineHeart');
  await debug({op:'set_time',hour:18,freeze:true});await stand(z,tree.x+2,tree.y+2);await wait(()=>NpcArt.readyFor(City.npcs));await p.waitForTimeout(500);
  const drawn=await p.evaluate(()=>{const kinds=[],orig=City.drawObject;City.drawObject=function(g,o,...a){if(o.kind.startsWith('valentine'))kinds.push(o.kind);return orig.call(this,g,o,...a);};try{Field._debug.drawFrame(3);return kinds;}finally{City.drawObject=orig;}});
  check(drawn.length>=3&&!drawn.some(k=>k.startsWith('festival')),`${a.name}: several festive props draw in the real city view`);
  await p.evaluate(()=>{City.close();Quests.close();});await p.screenshot({path:path.join(w.runDir,`valhallasc-valentine-${names[z]}.png`)});
  await p.setViewportSize({width:844,height:390});await p.screenshot({path:path.join(w.runDir,`valentine-${names[z]}-phone.png`)});await p.setViewportSize({width:1440,height:960});
 }
 if(['hunt','titles'].includes(process.env.CHECK_ONLY))for(const [qid,host]of[['valentine_alder','baker'],['valentine_skald','city_bard'],['valentine_nacre','nacre_gardener'],['valentine_aster','asterion_singer']]){
  await npc(host);await interact(host,'quest:accept:'+qid);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),qid);await debug({op:'quest',id:qid,action:'complete'});await interact(host,'quest:claim:'+qid);await wait(id=>__self().seasonalClaims[id]===2027,qid);
 }
 await p.evaluate(()=>Achievements.open());await wait(()=>window.__ach?.entries);
 check(await p.evaluate(()=>__ach.entries.find(a=>a.id==='lovefool').complete===false&&__ach.maximum===2325),'Four city errands alone do not grant Lovefool');
 if(process.env.CHECK_ONLY==='titles'){
  await npc('baker');await interact('baker','quest:accept:valentine_hunt');await wait(()=>__self().quests.some(q=>q.id==='valentine_hunt'&&!q.claimed));await debug({op:'quest',id:'valentine_hunt',action:'complete'});await interact('baker','quest:claim:valentine_hunt');await wait(()=>__self().seasonalClaims.valentine_hunt===20270210);
  await wait(()=>document.querySelector('#achievement-toast-name').textContent.includes('Lovefool'));check(true,'The normal achievement celebration receives the Lovefool award');
 await send({type:'select_title',achievement:'lovefool'});await wait(()=>document.querySelector('#hud-name').textContent==='Lovefool Sork');
 }else{
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>Quests.offered(n).some(q=>q.id==='valentine_hunt'))),'All four city hosts offer the same daily Briarheart hunt');
 await npc('city_bard');await interact('city_bard','quest:accept:valentine_hunt');await wait(()=>__self().quests.some(q=>q.id==='valentine_hunt'&&!q.claimed));
 await p.evaluate(()=>{City.close();Quests.track('valentine_hunt');});
 check(await p.evaluate(()=>Quests.mapMarkers(2).some(m=>m.quest==='valentine_hunt'&&m.x===112&&m.y===100)),'The daily quest marker points at the actual Roseheart Shrine');
 await debug({op:'set_gold',gold:1000000});await wait(()=>__self().gold===1000000);
 for(const [i,cls]of['priest','mage','hunter','warrior'].entries()){await interact('city_bard','valentine:hire:'+cls);await wait(n=>__snap.players.filter(p=>p.hired).length===n,i+1);}
 await stand(2,110.5,100);await wait(()=>__snap.players.filter(p=>p.hired&&p.zone===2&&p.hp>0&&Math.hypot(p.x-103,p.y-100)<=12).length===4);
 await p.evaluate(()=>Field.visitNpc('valentine_shrine'));await p.locator('#npc-dialogue').waitFor({state:'visible'});await p.locator('[data-offer="valentine:summon"]').click();await wait(()=>__snap.slimes.some(s=>s.kind==='briarheart'&&!s.dead));
 check(await p.evaluate(()=>__snap.valentine.active&&__snap.valentine.level===99),'Pressing the actual shrine summons the five-fighter elite at the highest party level');
 await p.evaluate(()=>City.close());await wait(()=>Valentines.source);await p.screenshot({path:path.join(w.runDir,'valentine-briarheart-summoned.png')});
 const enemy=await p.evaluate(()=>__snap.slimes.find(s=>s.kind==='briarheart').id);await debug({op:'kill_enemy',id:enemy});await wait(()=>__self().quests.find(q=>q.id==='valentine_hunt').counts[0]===1);
 check(await p.evaluate(()=>!__self().mounts.includes('roseheart')),'The kill grants quest credit; the unicorn is awarded on claim');
 await npc('nacre_gardener');const gold=await p.evaluate(()=>__self().gold);await interact('nacre_gardener','quest:claim:valentine_hunt');await wait(()=>__self().seasonalClaims.valentine_hunt===20270210);
 check(await p.evaluate(g=>__self().gold===g+300&&__self().mounts.includes('roseheart'),gold),'A different city host pays the daily reward and guaranteed unicorn');
 await wait(()=>document.querySelector('#achievement-toast-name').textContent.includes('Lovefool'));check(true,'The normal achievement celebration receives the Lovefool award');
 await send({type:'select_title',achievement:'lovefool'});await wait(()=>document.querySelector('#hud-name').textContent==='Lovefool Sork');
 check(await p.evaluate(()=>__self().look.name==='Sork'),'All five claimed Valentine quests unlock the exact Lovefool prefix without changing Sork');
 check(await p.evaluate(()=>['baker','city_bard','nacre_gardener','asterion_singer'].every(n=>!Quests.offered(n).some(q=>q.id==='valentine_hunt'))),'Changing city hosts cannot repeat today’s quest');

 await debug({op:'season_time',unix:1802300400});await wait(()=>__snap.seasons.find(s=>s.id==='valentine').day===20270211);
 check(await p.evaluate(()=>Quests.offered('baker').some(q=>q.id==='valentine_hunt')),'Stockholm midnight opens the next daily hunt');
 await npc('baker');await interact('baker','quest:accept:valentine_hunt');await wait(()=>__self().quests.some(q=>q.id==='valentine_hunt'&&!q.claimed));
 }
 await debug({op:'season_time',unix:1802991600});await wait(()=>!Seasonal.active&&__snap.valentine===null&&!__self().quests.some(q=>q.id==='valentine_hunt'&&!q.claimed));
 await stand(2,110.5,100);
 check(await p.evaluate(()=>Valentines.objects(2).length===0&&!City.npcs.some(n=>n.id==='valentine_shrine')&&[0,4,9,17].every(z=>Seasonal.decor(z).length===0)),'February 19 removes the shrine, encounter, unfinished quest and all Valentines dressing');
 check(await p.evaluate(()=>__self().mounts.includes('roseheart')&&document.querySelector('#hud-name').textContent==='Lovefool Sork'),'Owned mount and earned prefix survive the event’s end');
 await p.evaluate(()=>Achievements.open());await send({type:'achievements'});await wait(()=>__ach?.entries.find(a=>a.id==='lovefool')?.complete);
 check(await p.evaluate(()=>__ach.entries.find(a=>a.id==='lovefool').points===25&&__ach.entries.find(a=>a.id==='lovefool').titlePosition==='prefix'),'Lovefool has 25 points and authoritative prefix metadata');
 await p.setViewportSize({width:844,height:390});check(await p.locator('#achievement-title-select option[value="lovefool"]').textContent()==='Lovefool','Phone title selector offers the earned prefix');await p.setViewportSize({width:1440,height:960});
 const id=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();if(await p.locator('#scene-create').isVisible())await p.locator('#go').click({timeout:60000});await wait(()=>Online.connected&&Field.hero.hp>0);
 check(await p.evaluate(id=>Online.id===id&&__self().mounts.includes('roseheart')&&document.querySelector('#hud-name').textContent==='Lovefool Sork',id),'Reconnect preserves the same character, permanent mount and selected seasonal title');
 check(await p.evaluate(()=>Achievements.displayName({look:{name:'Sork'},achievementTitle:'the Merry'})==='Sork the Merry'&&Achievements.displayName({look:{name:'Sork'},achievementTitle:'Lovefool',achievementTitlePosition:'prefix'})==='Lovefool Sork'),'Existing suffix placement and exact single-space prefix rendering coexist');
 const other=await browser.newPage({viewport:{width:844,height:390},hasTouch:true});
 await other.addInitScript(()=>{window.AudioContext=undefined;window.__names=[];const fill=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(s,...a){if(String(s).includes('Sork'))window.__names.push(String(s));return fill.call(this,s,...a);};localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false}));});
 await other.goto(w.url);await other.locator('#start').click();await other.locator('#login-guest').click();await other.locator('#cls-warrior').click();await other.locator('#name').fill('RoseWitness');await other.locator('#go').click({timeout:60000});await other.waitForFunction(()=>Online.connected&&Field.hero.hp>0);
 await other.evaluate(()=>Online.send({type:'debug',command:{op:'teleport',zone:2,x:110.5,y:100}}));
 await other.waitForFunction(()=>window.__names.includes('Lovefool Sork'),null,{timeout:20000});check(true,'A second real browser paints Lovefool Sork on the remote world nameplate');await other.close();
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(w.url);
 check(await sv.evaluate(()=>Locale.language==='sv'&&Locale.translate('Lovefool')==='Lovefool'&&Locale.translate('The Briarheart')==='Törnhjärtat'&&Locale.translate('Roseheart Unicorn')==='Rosenhjärtats enhörning'),'The actual Swedish client presents the permanent prefix, elite and unicorn');await sv.close();
 check(errors.length===0,'No browser errors: '+errors.join('; '));
 fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`valentine-ui: ${checks} checks; ${w.runDir}`);
 }finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
