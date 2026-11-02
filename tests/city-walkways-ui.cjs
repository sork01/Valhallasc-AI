// All four major cities: actual street approaches, wall apertures and reciprocal crossings.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(ok,text)=>{assert.ok(ok,text);console.log(++checks+': '+text);};
(async()=>{try{
 w.startLevel=99;await w.start();browser=await chromium.launch({headless:true});
 for(const zone of [0,4,9,17]){
  const p=await browser.newPage({viewport:{width:1280,height:900},hasTouch:true,reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
  await p.addInitScript(()=>{
   window.AudioContext=undefined;
   localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true,dpsMeter:false}));
   const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{const v=JSON.parse(e.data);if(v.type==='welcome'||v.type==='snapshot')window.__snap=v.snapshot||v;});}};
  });
  await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('CityEntry'+zone);await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0);
  const send=message=>p.evaluate(m=>Online.send(m),message);
  const move=async([x,y])=>{await send({type:'move',x,y});await p.waitForFunction(([z,x,y])=>{const s=__snap.players.find(p=>p.id===Online.id);return s?.zone===z&&Math.hypot(s.x-x,s.y-y)<.45;},[zone,x,y],{timeout:18000});await send({type:'stop'});};
  const at=async([x,y])=>{await p.evaluate(([z,x,y])=>{Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone:z,x,y}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},[zone,x,y]);await p.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<.5,[zone,x,y]);await p.evaluate(()=>ZoneJourney.clear());};
  const z=await p.evaluate(zone=>[WORLD_MAP,...WORLD_MAP.zones][zone],zone);
  check(z.cityEntrances.length===({0:2,4:4,9:5,17:1})[zone],`${z.city.name}: every walking entrance is covered`);
  for(const e of z.cityEntrances){
   const portal=z.portals.find(p=>p.id===e.portal),first=e.points[0],dir=portal?.walk;
   const start=portal?[first[0]-dir[0]*6,first[1]-dir[1]*6]:first;
   await at(start);
   for(const point of e.points.slice(1))await move(point);
   check(true,`${z.city.name}/${e.id}: normal movement follows the full paved approach into the street`);
   if(portal){
    check((e.axis==='y'?portal.x:portal.y)===e.street,`${e.id}: crossing is centred on its city street`);
    const camera=e.opening?[e.opening.x-dir[0]*4,e.opening.y-dir[1]*4]:[first[0]-dir[0]*10,first[1]-dir[1]*10];
    if(e.points.length===2)await move(camera);
    else for(const point of e.points.slice(1,-1).reverse())await move(point);
    await p.evaluate(()=>ZoneJourney.clear());await p.screenshot({path:path.join(w.runDir,`${zone}-${e.id}-desktop.png`)});
    if(e===z.cityEntrances[0]||e.opening){await p.setViewportSize({width:844,height:390});await p.waitForTimeout(150);await p.screenshot({path:path.join(w.runDir,`${zone}-${e.id}-phone.png`)});await p.setViewportSize({width:1280,height:900});}
    // Follow the route back out, cross, then return using the real reciprocal gate.
    await send({type:'move',x:portal.x,y:portal.y});await p.waitForFunction(to=>Field.zone===to,portal.to,{timeout:18000});await send({type:'stop'});
    const back=await p.evaluate(zone=>[WORLD_MAP,...WORLD_MAP.zones][Field.zone].portals.find(p=>p.to===zone),zone);
    await send({type:'move',x:back.x,y:back.y});await p.waitForFunction(zone=>Field.zone===zone,zone,{timeout:18000});await send({type:'stop'});await p.waitForTimeout(200);
    check(await p.evaluate(([z,id])=>{const own=__snap.players.find(p=>p.id===Online.id),gate=[WORLD_MAP,...WORLD_MAP.zones][z].portals.find(p=>p.id===id);return own.zone===z&&Math.hypot(own.x-gate.x,own.y-gate.y)>3;},[zone,portal.id]),`${e.id}: reciprocal travel returns safely without bouncing`);
   }else{
    await p.evaluate(()=>ZoneJourney.clear());await p.screenshot({path:path.join(w.runDir,`${zone}-${e.id}-desktop.png`)});
    for(const point of e.points.slice(0,-1).reverse())await move(point);
    check((e.points[0][1]-e.opening.y)*(e.points.at(-1)[1]-e.opening.y)<0,`${e.id}: existing wall opening remains aligned and walkable both ways`);
   }
  }
  await p.close();
 }
 check(errors.length===0,'No browser errors');console.log(`city-walkways-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
