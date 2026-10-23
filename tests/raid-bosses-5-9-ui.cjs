// Wardens 5–9: real server casts, original art, mobile signs and rendered floor.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const root=path.resolve(__dirname,'..'),world=new TestWorld();
const map=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))).zones[45];
const signs=JSON.parse(fs.readFileSync(path.join(root,'world/boss-signs.txt')));
let browser,checks=0;const results=[];
const check=(value,message)=>{assert.ok(value,message);checks++;};
(async()=>{
 world.godMode=true;world.levelSpread=0;world.startLevel=99;await world.start();
 browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#name').fill('Forge Observer');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const leader=await page.evaluate(()=>Online.id),send=a=>page.evaluate(a=>Online.send(a),a),debug=command=>send({type:'debug',command});
 const names=Array.from({length:9},(_,i)=>'Forge'+(i+1));
 for(const [i,bot]of names.entries()){
  await world.connect({bot,class:['warrior','mage','assassin','priest','hunter'][i%5]});await send({type:'social',command:{op:'party_invite',name:bot}});
  await world.waitFor(()=>world.bots.get(bot).social?.incoming.some(i=>i.id===leader),10000,'Invite '+bot);await world.social(bot,{op:'party_accept',id:leader});
  if(!i){await send({type:'social',command:{op:'party_raid',on:true}});await page.waitForFunction(()=>Social.state.party?.raid);}
 }
 await page.waitForFunction(()=>Social.state.party?.members.length===10);check(true,'Ten connected fighters');
 if(process.env.MUTATE_FLOOR)await page.evaluate(()=>BossMech.drawFloor=()=>{});
 const stage=async(x,y)=>{
  await debug({op:'teleport',zone:46,x,y});await page.waitForFunction(()=>Field.zone===46);
  await Promise.all(names.map(bot=>world.debug(bot,{op:'teleport',zone:46,x,y:y+1})));await page.waitForFunction(()=>Field.remotePlayers.length===9);await page.waitForTimeout(3500);
 };
 const settleRolls=async()=>{
  const ids=await page.locator('#loot-rolls .roll-card').evaluateAll(nodes=>nodes.map(n=>Number(n.dataset.roll)));
  for(const id of ids){await send({type:'roll',id,choice:'pass'});await Promise.all(names.map(bot=>world.action(bot,{type:'roll',id,choice:'pass'})));}
 };
 const selected=(process.env.RAID_UI_BOSSES||'').split(',').filter(Boolean);
 for(const hall of map.forgeHalls.slice(4,9).filter(h=>!selected.length||selected.includes(h.boss))){
  const kind=hall.boss;await stage(hall.x,hall.y+2);
  await page.waitForFunction(k=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===k),kind,{timeout:15000});
  if(kind==='cf_dagfinn'){
   const id=await page.evaluate(k=>Field.slimes.find(s=>s.kind===k).id,kind);await debug({op:'kill_enemy',id});
  }
  await page.waitForFunction(k=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===k&&f.cast),kind,{timeout:30000});
  const state=await page.evaluate(k=>BossMech.fights.find(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===k),kind);
  check(state.tele.length>0,kind+' has authoritative floor warnings');
  if(kind==='cf_dagfinn')check(state.tele.filter(t=>t.need===3).length===2&&state.tele.some(t=>t.label==='Lava divide'),'Two counted valves and divided floor');
  if(kind==='cf_thorbjorg')check(state.tele.filter(t=>t.bearer).length===3&&state.tele.filter(t=>t.receiver).length===3,'Three moving brands with receivers and fuses');
  if(kind==='cf_ragnhild')check(state.tele.filter(t=>t.beat).length===36,'Thirty-six numbered tiles cover the floor');
  if(kind==='cf_orm')check(state.tele.filter(t=>t.well).length===10&&state.tele.some(t=>t.needWater===6),'Ten water wells and six-throw counter');
  if(kind==='cf_hildr')check(state.tele.some(t=>t.reflect===false&&t.color==='#fffaf0'),'White mirror warning');
  const pixels=await page.evaluate(kind=>{
   const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),saved=BossMech.fights,t=performance.now()/1000,hud=BossMech.drawHud;
   BossMech.drawHud=()=>{};BossMech.update(saved.filter(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===kind));Field._debug.drawFrame(t);const a=g.getImageData(0,0,cv.width,cv.height).data;
   BossMech.update([]);Field._debug.drawFrame(t);const b=g.getImageData(0,0,cv.width,cv.height).data;BossMech.update(saved);BossMech.drawHud=hud;Field._debug.drawFrame(t);
   let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>35)n++;return n;
  },kind);check(pixels>150,kind+' ground changes actual scene pixels: '+pixels);
  const labels=await page.evaluate(()=>{
   const g=document.getElementById('fieldcv').getContext('2d'),fill=g.fillText,labels=[];g.fillText=function(s,...a){labels.push(s);return fill.call(this,s,...a);};
   try{Field._debug.drawFrame(performance.now()/1000);}finally{g.fillText=fill;}return labels;
  });check(state.tele.some(t=>t.label&&labels.some(s=>s.startsWith(t.label))),kind+' labels are drawn above actors');
  if(!STUB){await page.waitForFunction(k=>Field.cathedralSprites?.img[k]?.complete,kind,{timeout:60000});check(await page.evaluate(k=>Field.cathedralSprites.meta.sprites[k]&&Field.cathedralSprites.img[k].naturalWidth===768,kind),kind+' editable original atlas loads');}
  await page.screenshot({path:path.join(world.runDir,kind+'-cast-desktop.png')});await page.setViewportSize({width:844,height:390});await page.screenshot({path:path.join(world.runDir,kind+'-cast-phone.png')});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(world.runDir,kind+'-cast-portrait.png')});await page.setViewportSize({width:1440,height:900});
  const sign=await page.evaluate(k=>Field.signs.find(s=>s.id===k),kind);check(!!sign,kind+' approach sign exists');
  await debug({op:'teleport',zone:46,x:sign.x,y:sign.y});await page.waitForTimeout(250);await send({type:'sign_read',sign:kind});await page.locator('#sign-panel').waitFor({state:'visible'});
  const words=await page.locator('#sign-panel').textContent();check(words.includes(signs[kind].title)&&words.includes(signs[kind].todo),kind+' sign explains its actual mechanic');
  await page.screenshot({path:path.join(world.runDir,kind+'-sign-desktop.png')});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(world.runDir,kind+'-sign-phone.png')});await page.keyboard.press('Escape');await page.setViewportSize({width:1440,height:900});
  if(kind==='cf_dagfinn'&&!STUB){
   const putValves=async()=>{
    const valves=await page.evaluate(()=>BossMech.fights.flatMap(f=>f.tele).filter(t=>t.need===3));
    check(valves.length===2,'Dagfinn keeps both valve stations in the live packet');
    const spots=valves.map(t=>t.shapes[0]);await debug({op:'teleport',zone:46,x:spots[0].x,y:spots[0].y});
    await Promise.all(names.map((bot,i)=>world.debug(bot,{op:'teleport',zone:46,x:spots[i<4?0:1].x,y:spots[i<4?0:1].y})));
    await page.waitForFunction(()=>{const t=BossMech.fights.flatMap(f=>f.tele).filter(t=>t.need===3);return t.length===2&&t.every(t=>t.count>=3);},null,{timeout:10000});
    check(true,'Both server valve counts contain at least three living fighters');
    await page.waitForFunction(()=>{const t=BossMech.fights.flatMap(f=>f.tele).filter(t=>t.need===3);return t.length===2&&t.every(t=>t.held>=19);},null,{timeout:45000});
    check(true,'Both actual continuous holds reach nineteen seconds before completion');
    await page.waitForFunction(()=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind==='cf_dagfinn'&&!f.cast),null,{timeout:10000});
   };
   await putValves();await debug({op:'kill_enemy',id:state.boss});
   await page.waitForFunction(()=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind==='cf_dagfinn'&&f.cast?.name==='Two Valves'));
   check(await page.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return Math.abs(s.hp/s.maxHp-.4)<.001;},state.boss),'A large strike stops at the second valve threshold');
   await putValves();await debug({op:'kill_enemy',id:state.boss});await page.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,state.boss);
   const lift=map.portals.find(p=>p.id==='cf_lift_out');await debug({op:'teleport',zone:46,x:lift.x,y:lift.y});
   await page.waitForFunction(p=>Math.hypot(Field.hero.x-p.tx,Field.hero.y-p.ty)<1,lift,{timeout:10000});
   check(true,'Killing Dagfinn opens the real lift without regathering the ten at the entrance');
   await settleRolls();await page.screenshot({path:path.join(world.runDir,'cf_dagfinn-shortcut.png')});
  }
  if(kind==='cf_orm'){
   const wells=state.tele.filter(t=>t.well).map(t=>t.shapes[0]);
   await debug({op:'teleport',zone:46,x:wells[0].x,y:wells[0].y});
   await Promise.all(names.map((bot,i)=>world.debug(bot,{op:'teleport',zone:46,x:wells[i+1].x,y:wells[i+1].y})));
   await page.waitForFunction(()=>BossMech.fights.flatMap(f=>f.tele).filter(t=>t.carrier).length===10,null,{timeout:10000});
   check(await page.evaluate(()=>BossMech.fights.flatMap(f=>f.tele).filter(t=>t.carrier).every(t=>t.speed===.6)),'All ten real actors collect server-owned flasks at 60% speed');
   const target=await page.evaluate(id=>{const s=Field.slimes.find(s=>s.id===id);return {x:s.x,y:s.y};},state.boss);
   await debug({op:'teleport',zone:46,...target});await Promise.all(names.slice(0,5).map(bot=>world.debug(bot,{op:'teleport',zone:46,...target})));
   await page.waitForFunction(()=>BossMech.fights.some(f=>f.cast?.name==='Quenched'),null,{timeout:10000});
   check(await page.evaluate(()=>BossMech.fights.flatMap(f=>f.tele).some(t=>t.quenched&&t.water>=6)),'Six actual deliveries quench Orm');
   await page.screenshot({path:path.join(world.runDir,'cf_orm-quenched.png')});
  }
  if(kind!=='cf_dagfinn'){
   await debug({op:'kill_enemy',id:state.boss});await page.waitForFunction(id=>Field.slimes.find(s=>s.id===id)?.dead,state.boss);await settleRolls();
  }
  results.push({kind,pixels,labels,cast:state.cast,tele:state.tele});
 }
 check(await page.evaluate(()=>WORLD_MAP.zones[45].sealedTemplate),'Entrance remains sealed');
 const sv=await browser.newPage();await sv.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sv.goto(world.url);
 check(await sv.evaluate(()=>['Two Valves','Brand Relay','Four on the Floor','Water Carriers','Mirror Plate','HOLD FIRE','Valve {0}','Water: {0}/{1}'].every(s=>Locale.translate(s)!==s)),'Hand-written Swedish covers all five mechanics, counters and hold-fire instruction');await sv.close();
 check(!errors.length,JSON.stringify(errors));fs.writeFileSync(path.join(world.runDir,'wardens-5-9-ui.json'),JSON.stringify({checks,real:!STUB,results,errors},null,2));console.log(JSON.stringify({passed:true,checks,artifacts:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
