// Sigrun only: numbered targets, authoritative immunity and real rendered art.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const root=path.resolve(__dirname,'..'),world=new TestWorld();
const data=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))).zones[45];
const defs=JSON.parse(fs.readFileSync(path.join(root,'world/boss-mechanics.txt')));
let browser,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
(async()=>{
 world.godMode=true;world.levelSpread=0;world.startLevel=99;await world.start();
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#name').fill('Warden Watcher');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const leader=await page.evaluate(()=>Online.id);
 const send=action=>page.evaluate(a=>Online.send(a),action);
 const debug=command=>send({type:'debug',command});
 const names=Array.from({length:9},(_,i)=>'Warden'+(i+1)),classes=['warrior','mage','assassin','priest','hunter'];
 for(const [i,bot]of names.entries()){
  await world.connect({bot,class:classes[i%5]});
  await send({type:'social',command:{op:'party_invite',name:bot}});
  await world.waitFor(()=>world.bots.get(bot).social?.incoming.some(i=>i.id===leader),10000,'Invitation '+bot);
  await world.social(bot,{op:'party_accept',id:leader});
  if(i===0){await send({type:'social',command:{op:'party_raid',on:true}});await page.waitForFunction(()=>Social.state.party?.raid);}
 }
 await page.waitForFunction(()=>Social.state.party?.members.length===10);
 check(true,'Ten real fighters share a raid');
 if(process.env.MUTATE_FLOOR)await page.evaluate(()=>{BossMech.drawFloor=()=>{};});
 const idToBot=new Map(names.map(n=>[world.bots.get(n).id,n]));
 const teleport=async(id,x,y)=>{
  if(id===leader){await debug({op:'teleport',zone:46,x,y});return;}
  await world.debug(idToBot.get(id),{op:'teleport',zone:46,x,y});
 };
 const stage=async(x,y)=>{
  await debug({op:'teleport',zone:46,x,y});
  await page.waitForFunction(()=>Field.zone===46);
  await Promise.all(names.map(bot=>world.debug(bot,{op:'teleport',zone:46,x,y:y+1})));
  await page.waitForFunction(()=>Field.remotePlayers.length===9);
 };

 const h=data.forgeHalls[3],kind='cf_sigrun';
 await stage(h.x,h.y+2);
 const fight=()=>page.evaluate(()=>BossMech.fights.find(f=>Field.slimes.find(s=>s.id===f.boss)?.kind==='cf_sigrun'));
 await page.waitForFunction(()=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind==='cf_sigrun'&&f.shield),null,{timeout:25000});
 let state=await fight();const ingots=state.tele.filter(t=>t.ingot);
 check(ingots.length===6,'Six numbered objects appear in the live server packet');
 check(ingots.map(t=>t.ingot).join(',')==='1,2,3,4,5,6','Numbers preserve their authored order');
 check(ingots.filter(t=>t.current).length===1&&ingots[0].current,'Only the lowest number is current');
 check(state.cast.name==='Ingot Order'&&state.cast.total===25,'Named 25-second deadline');
 check(ingots[0].tele==='red'&&ingots.slice(1).every(t=>t.tele==='dashed line'),'Current target and waiting targets have distinct shapes and labels');
 const hp=await page.evaluate(id=>Field.slimes.find(s=>s.id===id).hp,state.boss);
 await debug({op:'kill_enemy',id:state.boss});await debug({op:'kill_enemy',id:ingots[2].target});
 await page.waitForTimeout(300);
 check((await fight()).shield.alive===6,'Trying a later number cannot bypass the server shield');
 check(await page.evaluate(([id,hp])=>Field.slimes.find(s=>s.id===id).hp===hp,[state.boss,hp]),'Even the private kill command obeys Sigrun immunity');
 const pixels=await page.evaluate(()=>{
  const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),saved=BossMech.fights,t=performance.now()/1000,hud=BossMech.drawHud;
  BossMech.drawHud=()=>{};Field._debug.drawFrame(t);const a=g.getImageData(0,0,cv.width,cv.height).data;
  BossMech.update([]);Field._debug.drawFrame(t);const b=g.getImageData(0,0,cv.width,cv.height).data;
  BossMech.update(saved);BossMech.drawHud=hud;Field._debug.drawFrame(t);
  let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>35)n++;return n;
 });check(pixels>300,'Actual ground telegraphs change scene pixels ('+pixels+')');
 const labels=await page.evaluate(()=>{
  const g=document.getElementById('fieldcv').getContext('2d'),fill=g.fillText,labels=[];
  g.fillText=function(s,...args){labels.push(s);return fill.call(this,s,...args);};
  try{Field._debug.drawFrame(performance.now()/1000);}finally{g.fillText=fill;}return labels;
 });check(labels.includes('Ingot 1')&&labels.includes('Ingot 6')&&labels.includes('Hit this one!')&&labels.includes('Wait for its number'),'Canvas draws readable numbered instructions above the actors');
 if(!STUB){
  await page.waitForFunction(()=>['cf_sigrun','cf_ingot'].every(k=>Field.cathedralSprites?.img[k]?.complete),null,{timeout:60000});
  check(await page.evaluate(()=>['cf_sigrun','cf_ingot'].every(k=>Field.cathedralSprites.meta.sprites[k]&&Field.cathedralSprites.img[k].naturalWidth===768)),'Boss and ingots have original editable atlases');
 }
 await page.screenshot({path:path.join(world.runDir,'sigrun-cast-desktop.png')});
 await page.setViewportSize({width:844,height:390});await page.waitForTimeout(180);
 await page.screenshot({path:path.join(world.runDir,'sigrun-cast-phone.png')});
 check((await fight()).cast.total===25,'Deadline remains visible at phone size');
 await page.setViewportSize({width:1440,height:900});
 await debug({op:'kill_enemy',id:ingots[0].target});
 await page.waitForFunction(()=>BossMech.fights.some(f=>f.tele.some(t=>t.ingot===2&&t.current)));
 state=await fight();check(state.shield.alive===5&&state.cast.left>23,'Killing number 1 gives number 2 a fresh timer');
 await page.screenshot({path:path.join(world.runDir,'sigrun-next-number.png')});
 const sign=await page.evaluate(()=>Field.signs.find(s=>s.id==='cf_sigrun'));
 check(!!sign,'Approach sign exists in the actual raid copy');
 await debug({op:'teleport',zone:46,x:sign.x,y:sign.y});await page.waitForTimeout(250);
 await send({type:'sign_read',sign:kind});await page.locator('#sign-panel').waitFor({state:'visible'});
 const words=await page.locator('#sign-panel').textContent();
 check(words.includes('25 seconds')&&words.includes('40%')&&words.includes('All ten'),'Sign explains numbers, deadline and escalation');
 await page.screenshot({path:path.join(world.runDir,'sigrun-sign-desktop.png')});
 await page.setViewportSize({width:844,height:390});await page.screenshot({path:path.join(world.runDir,'sigrun-sign-phone.png')});await page.keyboard.press('Escape');
 check(await page.evaluate(()=>!WORLD_MAP.zones[45].sealedTemplate),'Public raid entrance is open');
 const sw=await browser.newPage();await sw.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sw.goto(world.url);
 check(await sw.evaluate(()=>Locale.translate('Ingot Order')==='Tackornas ordning'&&Locale.translate('Ingot {0}')==='Tacka {0}'&&Locale.translate('Hit this one!')==='Slå på den här!'),'Hand-written Swedish ability and numbered instructions');await sw.close();
 check(errors.length===0,JSON.stringify(errors));
 fs.writeFileSync(path.join(world.runDir,'sigrun-ui.json'),JSON.stringify({checks,real:!STUB,pixels,labels,errors},null,2));
 console.log(JSON.stringify({passed:true,checks,artifacts:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
