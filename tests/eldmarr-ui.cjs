// Eldmarr only: real private casts, original art, ten actors, mobile readability and clear.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const root=path.resolve(__dirname,'..'),world=new TestWorld();let browser,checks=0;const results=[];
const check=(ok,message)=>{assert.ok(ok,message);checks++;};
(async()=>{
 world.godMode=true;world.levelSpread=0;world.startLevel=99;await world.start();
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:.1,sfxVol:.1})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#name').fill('Eldmarr Observer');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const leader=await page.evaluate(()=>Online.id),send=a=>page.evaluate(a=>Online.send(a),a),debug=command=>send({type:'debug',command});
 const names=Array.from({length:9},(_,i)=>'Seat'+(i+1));
 for(const [i,bot]of names.entries()){
  await world.connect({bot,class:['warrior','mage','assassin','priest','hunter'][i%5]});await send({type:'social',command:{op:'party_invite',name:bot}});
  await world.waitFor(()=>world.bots.get(bot).social?.incoming.some(i=>i.id===leader),10000,'Invite '+bot);await world.social(bot,{op:'party_accept',id:leader});
  if(!i){await send({type:'social',command:{op:'party_raid',on:true}});await page.waitForFunction(()=>Social.state.party?.raid);}
 }
 await page.waitForFunction(()=>Social.state.party?.members.length===10);check(true,'Ten real connected fighters');
 const map=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))).zones[45],hall=map.forgeHalls[9];
 const put=async(bot,p)=>bot===null?debug({op:'teleport',zone:46,...p}):world.debug(bot,{op:'teleport',zone:46,...p});
 await put(null,{x:hall.x,y:hall.y+2});await page.waitForFunction(()=>Field.zone===46);
 await Promise.all(names.map(bot=>put(bot,{x:hall.x,y:hall.y+2})));
 await page.waitForFunction(()=>Field.remotePlayers.length===9);
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===1&&f.tele.some(t=>t.label==='Cracking Floor')),null,{timeout:30000});
 if(process.env.MUTATE_FLOOR)await page.evaluate(()=>BossMech.drawFloor=()=>{});
 const fight=()=>page.evaluate(()=>BossMech.fights.find(f=>f.throne));
 const capture=async name=>{
  const state=await fight();const pixels=await page.evaluate(()=>{
   const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),saved=BossMech.fights,t=performance.now()/1000,hud=BossMech.drawHud;
   BossMech.drawHud=()=>{};Field._debug.drawFrame(t);const a=g.getImageData(0,0,cv.width,cv.height).data;
   BossMech.update([]);Field._debug.drawFrame(t);const b=g.getImageData(0,0,cv.width,cv.height).data;
   BossMech.update(saved);BossMech.drawHud=hud;Field._debug.drawFrame(t);
   let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>35)n++;return n;
  });check(pixels>150,name+' actual floor pixels: '+pixels);
  const labels=await page.evaluate(()=>{const g=document.getElementById('fieldcv').getContext('2d'),original=g.fillText,labels=[];g.fillText=function(s,...a){labels.push(s);return original.call(this,s,...a);};try{Field._debug.drawFrame(performance.now()/1000);}finally{g.fillText=original;}return labels;});
  check(labels.some(s=>s.startsWith('Chains broken:')),'Chain count is visible during '+name);
  await page.screenshot({path:path.join(world.runDir,name+'-desktop.png')});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(world.runDir,name+'-portrait.png')});await page.setViewportSize({width:844,height:390});await page.screenshot({path:path.join(world.runDir,name+'-landscape.png')});await page.setViewportSize({width:1440,height:900});
  results.push({name,pixels,labels,state});return state;
 };
 let state=await capture('forge-floor');check(state.tele.some(t=>t.total===8&&t.name==='The Forge Floor'),'Eight-second crack warnings');
 if(!STUB){await page.waitForFunction(()=>Field.cathedralSprites?.img.cf_eldmarr?.complete,null,{timeout:60000});check(await page.evaluate(()=>Field.cathedralSprites.img.cf_eldmarr.naturalWidth===768&&CATHEDRAL_ENEMIES.find(e=>e.kind==='cf_eldmarr').boss),'Original final-boss atlas loads');}
 await page.waitForFunction(()=>valhalla.eldmarrMusic?.running&&valhalla.eldmarrMusic.loaded,null,{timeout:20000});check(true,'Actual Eldmarr encounter selects final-boss music');
 const id=state.boss;
 const strike=()=>debug({op:'kill_enemy',id});
 await strike();await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===2&&f.throne.breathing>0));
 check((await fight()).cast.name==='The Forge Takes a Breath','First safe breathing window');
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===2&&f.tele.filter(t=>t.coldWell).length===4&&f.tele.some(t=>t.heat>0)),null,{timeout:20000});
 state=await capture('rising-heat');check(state.tele.filter(t=>t.coldWell).every(t=>t.capacity===3),'Four wells show three-person capacity');
 check(state.tele.filter(t=>typeof t.heat==='number').length===10,'All ten actual heat meters arrive');
 check(results.at(-1).labels.some(s=>s.startsWith('Heat:')),'Heat readouts draw above actors');
 await strike();await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===3&&f.throne.breathing>0));check((await fight()).throne.broken===6,'Second safe window breaks six chains');
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===3&&f.tele.filter(t=>t.seat).length===10),null,{timeout:35000});
 state=await capture('seat-warning');let seats=state.tele.filter(t=>t.seat);
 check(seats.every(t=>t.capacity===1&&t.total===9),'Ten capacity-one plates with nine-second warning');
 check(new Set(seats.flatMap(t=>t.players)).size===10,'Each connected fighter gets their own seat number');
 // Let this first cast finish harmlessly in the private god-mode world; then
 // exercise a real warning and actual server counts in the combined finale.
 await strike();await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===4&&f.throne.broken===9));
 state=await capture('unbound');check(state.throne.phase===4&&state.throne.broken===9,'All nine chains break for the final phase');
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===4&&f.tele.filter(t=>t.seat).length===10),null,{timeout:20000});
 state=await fight();seats=state.tele.filter(t=>t.seat);
 const destinations=new Map(seats.flatMap(t=>t.players.map(id=>[id,{x:t.shapes[0].x,y:t.shapes[0].y}])));
 await put(null,destinations.get(leader));await Promise.all(names.map(bot=>put(bot,destinations.get(world.bots.get(bot).id))));
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.throne?.phase===4&&f.tele.filter(t=>t.seat).length===10&&f.tele.filter(t=>t.seat).every(t=>t.count===1)),null,{timeout:5000});
 check(true,'All ten real actors occupy separate server-counted plates');
 await capture('occupied-seats');
 await strike();await page.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,id);await page.waitForFunction(()=>!BossMech.fights.some(f=>f.throne));
 await page.waitForFunction(()=>valhalla.raidMusic?.running&&!valhalla.eldmarrMusic?.running,null,{timeout:20000});check(true,'Actual kill returns to dungeon music');
 check(await page.evaluate(()=>Field._debug.chests?.some(c=>c.x===111&&c.y===29)),'Final kill creates the reward chest');
 check(await page.evaluate(()=>Field._debug.cleared),'The actual final kill clears the copy and unlocks its exit');
 const cards=await page.locator('#loot-rolls .roll-card').count();check(cards>=4,'Final kill offers orange armour and signature weapon rolls');
 check(await page.evaluate(()=>WORLD_MAP.zones[45].sealedTemplate),'Public entrance remains sealed');
 const sign=JSON.parse(fs.readFileSync(path.join(root,'world/boss-signs.txt'))).cf_eldmarr;
 await put(null,{x:sign.x,y:sign.y});await send({type:'sign_read',sign:'cf_eldmarr'});await page.locator('#sign-panel').waitFor({state:'visible'});
 check((await page.locator('#sign-panel').textContent()).includes(sign.todo),'Sign explains all three actual mechanics');
 await page.screenshot({path:path.join(world.runDir,'eldmarr-sign-desktop.png')});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(world.runDir,'eldmarr-sign-phone.png')});
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(world.url);
 check(await sv.evaluate(()=>['The Forge Floor','Rising Heat','A Seat for Everyone','The Forge Takes a Breath','Cold Well','Chains broken: {0}/9','Heat: {0}%','Cool down! {0}s'].every(s=>Locale.translate(s)!==s)),'Hand-written Swedish covers mechanics, meters and numbered roles');await sv.close();
 check(!errors.length,JSON.stringify(errors));fs.writeFileSync(path.join(world.runDir,'eldmarr-ui.json'),JSON.stringify({checks,real:!STUB,results,errors},null,2));console.log(JSON.stringify({passed:true,checks,artifacts:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
