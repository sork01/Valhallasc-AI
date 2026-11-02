// Four owner-reported city/travel tasks. Private server; bounded through test-touch-bounded.sh.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
require('./lib/touch.cjs').requireMemoryLimit();
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),world=new TestWorld();
let browser,checks=0;
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{
 world.startLevel=99;world.godMode=true;await world.start();browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800},hasTouch:true,reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE==='clip')await page.route('**/vaultart.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(root,'client/vaultart.js'),'utf8').replace('g.closePath();g.clip();','g.closePath();/* broken aperture */')}));
 await page.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;window.__valhallaTestSprites=true;
  if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true,dpsMeter:false}));
  const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;window.__packets=(window.__packets||[]).concat(v.type==='dialogue'?[v]:[]).slice(-10);}catch{}});}};
  window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);
 });
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('Festival Check');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
 const send=m=>page.evaluate(m=>Online.send(m),m),debug=command=>send({type:'debug',command});
 const wait=(fn,arg)=>page.waitForFunction(fn,arg,{timeout:15000});
 const at=async(zone,x,y)=>{await page.evaluate(()=>{City.close();Field.clearInput();Online.send({type:'stop'});});await debug({op:'teleport',zone,x,y});await wait(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<1.2,[zone,x,y]);await page.waitForTimeout(250);await page.evaluate(()=>ZoneJourney.clear());};
 const season=async(unix,on)=>{await debug({op:'season_time',unix});await wait(on=>Seasonal.active===on,on);};
 const area=zone=>page.evaluate(z=>[WORLD_MAP,...WORLD_MAP.zones][z],zone);
 const npc=async(zone,id)=>{const n=await page.evaluate(([z,id])=>[WORLD_MAP,...WORLD_MAP.zones][z].npcs.find(n=>n.id===id),[zone,id]);await at(zone,n.x,n.y);return n;};
 const interact=async(id,offer)=>{await send({type:'interact',npc:id,...(offer?{offer}:{})});await page.waitForTimeout(200);};
 // Pixel proof that every below-ground operation is clipped to the aperture.
 const clipped=await page.evaluate(()=>{
  const c=document.createElement('canvas');c.width=900;c.height=650;const g=c.getContext('2d');
  const mask=document.createElement('canvas');mask.width=c.width;mask.height=c.height;const m=mask.getContext('2d');m.translate(450,250);m.beginPath();
  for(const [i,p]of[[-1.7,-2],[1.7,-2],[1.7,1.2],[-1.7,1.2]].entries()){const q=City.kit.iso(...p);i?m.lineTo(...q):m.moveTo(...q);}m.closePath();m.fill();const md=m.getImageData(0,0,c.width,c.height).data;
  const original={};for(const name of ['save','restore','clip','fill','stroke','fillRect'])original[name]=g[name];let active=false,count=0,leaks=0,stack=[];
  g.save=function(){stack.push(active);return original.save.call(this);};g.restore=function(){active=stack.pop()||false;return original.restore.call(this);};
  g.clip=function(...a){active=true;count++;return original.clip.apply(this,a);};
  for(const name of ['fill','stroke','fillRect'])g[name]=function(...a){const before=active?this.getImageData(0,0,c.width,c.height).data:null;const r=original[name].apply(this,a);if(before){const d=this.getImageData(0,0,c.width,c.height).data;for(let k=0;k<d.length;k+=4)if(!md[k+3]&&[0,1,2,3].some(j=>d[k+j]!==before[k+j]))leaks++;}return r;};
  VaultArt.stairsDown(g,450,250,3);return{count,leaks};
 });
 check(clipped.count===1&&clipped.leaks<30,`Undervault: below-ground drawing is clipped inside its opening (${JSON.stringify(clipped)})`);
 const festivalQuests=[];for(const zone of [0,4,9,17]){const z=await area(zone);festivalQuests.push([zone,z.quests.find(q=>q.season)]);}
 if(!['art','travel'].includes(process.env.CHECK_ONLY)){
 // Both sides of each annual boundary, without a client date dependency.
 await season(1792969199,false);check(await page.evaluate(()=>Seasonal.decor(0).length===0&&!Quests.offered('baker').some(q=>q.season)), 'October 25: no decorations or festival offers');
 await season(1792969200,true);check(await page.evaluate(()=>Seasonal.decor(0).length>=9&&Quests.offered('baker').some(q=>q.id==='halloween_alder')), 'October 26: decorations and the city quest appear');
 for(const [zone,q] of festivalQuests){
  const z=await area(zone);
  await npc(zone,q.npc);const gold=await page.evaluate(()=>__self().gold);
  await interact(q.npc,'quest:accept:'+q.id);await wait(id=>__self().quests.some(q=>q.id===id&&!q.claimed),q.id);
  for(const o of q.objectives){
   if(o.kind==='talk'){await npc(zone,o.target);await interact(o.target);}
   else{const p=z.places.find(p=>p.id===o.target);await at(zone,p.x,p.y);}
  }
  await wait(id=>{const q=__self().quests.find(q=>q.id===id);return q.counts.every(n=>n>=1);},q.id);
  await npc(zone,q.npc);await interact(q.npc,'quest:claim:'+q.id);await wait(id=>__self().seasonalClaims[id]===2026,q.id);
  check(await page.evaluate(([id,gold,reward])=>__self().quests.some(q=>q.id===id&&q.claimed)&&__self().gold===gold+reward,[q.id,gold,q.rewardGold]),`${z.name}: real talk/visit objectives and one exact quest reward`);
  await interact(q.npc,'quest:accept:'+q.id);await interact(q.npc,'quest:claim:'+q.id);
  check(await page.evaluate(([id,gold,reward])=>!Quests.offered([WORLD_MAP,...WORLD_MAP.zones][Field.zone].quests.find(q=>q.id===id).npc).some(q=>q.id===id)&&__self().gold===gold+reward,[q.id,gold,q.rewardGold]),`${z.name}: repeat claim cannot pay again this year`);
 }
 await season(1825023600,true); // next year
 await npc(0,'baker');await interact('baker','quest:accept:halloween_alder');await wait(()=>__self().quests.some(q=>q.id==='halloween_alder'&&!q.claimed));
 check(await page.evaluate(()=>__self().seasonalStarted===undefined||__self().seasonalClaims.halloween_alder===2026),'The next year offers a new run while preserving last year’s reward history');
 await season(1825801199,true);
 await season(1825801200,false);
 check(await page.evaluate(()=>!__self().quests.some(q=>q.id==='halloween_alder'&&!q.claimed)&&Seasonal.decor(4).length===0), 'November 10: unfinished run retires and decorations disappear while playing');
 const resumedId=await page.evaluate(()=>Online.id);
 await page.reload();await page.locator('#start').click();await page.locator('#login-guest').click();if(await page.locator('#scene-create').isVisible())await page.locator('#go').click({timeout:60000});await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
 check(await page.evaluate(id=>Online.id===id&&!Seasonal.active&&!Quests.offered('baker').some(q=>q.season)&&__self().seasonalClaims.halloween_skald===2026,resumedId), 'Reload/reconnect retains the same character, annual reward history and off-season state');
 }
 await season(1792969200,true);
 if(process.env.CHECK_ONLY!=='travel'){
 // Native props and accessories participate in the real field draw, using production NPC atlases.
 for(const [zone,q] of festivalQuests){
  const z=await area(zone),o=z.seasonDecor[0];await page.setViewportSize({width:1280,height:800});await debug({op:'set_time',hour:12,freeze:true});await at(zone,o.x,o.y);
  await page.waitForFunction(()=>NpcArt.readyFor(City.npcs),null,{timeout:20000});
  const result=await page.evaluate(()=>{
   const drawn=[],o=City.drawObject,n=Seasonal.drawNpc;City.drawObject=function(g,x,...a){if(x.kind.startsWith('festival'))drawn.push(x.kind);return o.call(this,g,x,...a);};
   Seasonal.drawNpc=function(g,npc,...a){if(Seasonal.hat(npc))drawn.push('costumed-host');return n.call(this,g,npc,...a);};
   try{Field._debug.drawFrame(3);return drawn;}finally{City.drawObject=o;Seasonal.drawNpc=n;}
  });
  check(result.some(k=>k.startsWith('festival')),`${z.name}: seasonal scenery is drawn in the actual city`);
  await npc(zone,q.npc);
  const pixels=await page.evaluate(id=>{const n=City.npcs.find(n=>n.id===id),c=document.createElement('canvas');c.width=500;c.height=500;const g=c.getContext('2d'),original=Seasonal.drawNpc;try{Seasonal.drawNpc=()=>{};City.drawNpc(g,n,250,340,3,false);const a=g.getImageData(0,0,500,500).data;g.clearRect(0,0,500,500);Seasonal.drawNpc=original;City.drawNpc(g,n,250,340,3,false);const b=g.getImageData(0,0,500,500).data;let diff=0;for(let i=0;i<a.length;i+=4)if([0,1,2,3].some(j=>a[i+j]!==b[i+j]))diff++;return diff;}finally{Seasonal.drawNpc=original;}},q.npc);
  check(pixels>100,`${z.name}: production NPC atlas retains visible seasonal accessories`);
  await page.screenshot({path:path.join(world.runDir,`halloween-city-${zone}.png`)});
  await page.setViewportSize({width:844,height:390});await debug({op:'set_time',hour:0,freeze:true});await wait(()=>DayNight.hour<.01);await page.screenshot({path:path.join(world.runDir,`halloween-city-${zone}-phone-night.png`)});
 }
 }
 await page.setViewportSize({width:1280,height:800});await debug({op:'set_time',hour:12,freeze:true});
 await at(4,104.2,125.4);await page.screenshot({path:path.join(world.runDir,'undervault-opening.png')});
 await page.evaluate(()=>Field._debug.visitPortal(Field._debug.zones[4].portals.find(p=>p.id==='undervault_stairs')));
 await wait(()=>Field.zone===5||Field._debug.zones[Field.zone]?.name==='The Undervault');
 check(await page.evaluate(()=>Field.zone!==4),'Undervault stairs still admit the player into a private dungeon');
 await page.waitForTimeout(1700);await page.evaluate(()=>Field._debug.visitPortal(Field._debug.zones[Field.zone].portals.find(p=>p.to===4&&!p.after_clear)));await wait(()=>Field.zone===4);
 check(await page.evaluate(()=>Math.hypot(Field.hero.nx-104.2,Field.hero.ny-125.4)<2),'Undervault return lands safely beside the same stairs');
 await at(7,107.5,106.5);await page.evaluate(()=>Field.setTouchDirection(1,0));await wait(()=>Field.zone!==7||Field.hero.nx>115);await page.evaluate(()=>Field.setTouchDirection(0,0));
 check(await page.evaluate(()=>Field.zone===7&&Field.hero.nx>114),'Walking past the old narrow-path location stays in Bifrost');
 await at(7,116.5,113.5);await page.screenshot({path:path.join(world.runDir,'bifrost-nacre-landing.png')});
 const sign=await page.evaluate(()=>{const p=Field._debug.zones[7].portals.find(p=>p.to===9),[x,y]=Field._debug.w2s(p.x,p.y,132),r=document.querySelector('#fieldcv').getBoundingClientRect();return{x:r.left+x*r.width/1600,y:r.top+y*r.width/1600};});
 await page.touchscreen.tap(sign.x,sign.y);await wait(()=>Field.zone===9);
 await page.waitForTimeout(1700);await page.evaluate(()=>Field._debug.visitPortal(Field._debug.zones[9].portals.find(p=>p.to===7)));await wait(()=>Field.zone===7);
 check(await page.evaluate(()=>Math.hypot(Field.hero.nx-116.5,Field.hero.ny-113.5)<2),'Nacrehold return arrives on the new broad Bifrost landing');
 // Readable real-frame destination labels and paving on representative terrain, night/day and phone.
 for(const [width,height]of[[1280,800],[844,390]]){
  await page.setViewportSize({width,height});
  for(const zone of [0,4,7,9,26]){
   const z=await area(zone),p=z.portals.find(p=>p.walk);await at(zone,p.x-p.walk[0]*8,p.y-p.walk[1]*8);
   for(const hour of [12,0]){
    await debug({op:'set_time',hour,freeze:true});await wait(h=>Math.abs(DayNight.hour-h)<.01,hour);
    const labels=await page.evaluate(()=>{
      const cv=document.querySelector('#fieldcv'),g=cv.getContext('2d'),fill=g.fillText,found=[];
      g.fillText=function(t,x,y,...a){if(this.fillStyle==='#fff0c9'){const tr=this.getTransform(),point=tr.transformPoint({x,y});found.push({t,font:parseFloat(this.font)*tr.a,x:point.x,y:point.y,w:this.measureText(t).width*tr.a,alpha:this.globalAlpha});}return fill.call(this,t,x,y,...a);};
      try{Field._debug.drawFrame(3);const data=g.getImageData(0,0,cv.width,cv.height).data;return found.map(b=>{let bright=0;for(let y=Math.max(0,Math.floor(b.y-b.font));y<Math.min(cv.height,b.y+b.font);y++)for(let x=Math.max(0,Math.floor(b.x-b.w/2));x<Math.min(cv.width,b.x+b.w/2);x++){const i=(y*cv.width+x)*4;if(data[i]>235&&data[i+1]>215&&data[i+2]>175)bright++;}return{...b,bright};});}finally{g.fillText=fill;}
    });
    check(labels.some(t=>t.t.startsWith(p.name)&&t.font>=12.9&&t.alpha===1&&t.bright>20),`${width}px ${z.name} at ${hour}: visible high-contrast destination text at least 13 pixels tall`);
    await page.screenshot({path:path.join(world.runDir,`exit-${zone}-${width}-${hour}.png`)});
   }
  }
 }
 check(errors.length===0,'No browser errors: '+errors.join('; '));console.log(`cities-seasonal-ui: ${checks} checks; ${world.runDir}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
