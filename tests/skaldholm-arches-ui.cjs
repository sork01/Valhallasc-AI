// Only the reported wall openings: visible stone faces, street alignment and real movement.
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];
const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
(async()=>{try{
 await w.start();browser=await chromium.launch({headless:true});const p=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.AudioContext=undefined;window.__valhallaTestSprites=true;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true,dpsMeter:false}));});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('Arch Check');await p.locator('#go').click({timeout:60000});await p.waitForFunction(()=>Online.connected&&Field.hero.hp>0);
 const at=async(x,y)=>{await p.evaluate(([x,y])=>{Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone:4,x,y}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});},[x,y]);await p.waitForFunction(([x,y])=>Field.zone===4&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<.8,[x,y]);await p.evaluate(()=>ZoneJourney.clear());};
 const faces=await p.evaluate(()=>[false,true].map(vertical=>{
  const c=document.createElement('canvas');c.width=800;c.height=550;const g=c.getContext('2d');
  const project=(x,y,h=0)=>[400+(x-y)*44,420+(x+y)*22-h];ExitPaths.arch(g,{x:0,y:0,vertical},project);
  const samples=[];for(const degrees of [22.5,45,67.5,90,112.5,135,157.5]){
   const angle=degrees*Math.PI/180,u=Math.cos(angle)*5.1,v=.9,h=108+Math.sin(angle)*170;
   const [x,y]=project(vertical?v:u,vertical?u:v,h);const rgba=[...g.getImageData(Math.round(x),Math.round(y),1,1).data];samples.push(rgba);
  }
  return {vertical,samples};
 }));
 check(faces.every(f=>f.samples.every(c=>c[0]>180&&c[1]>170&&c[2]>145&&c[3]===255)),'Both arch orientations have a continuous light stone face without dark overlapping roof triangles');
 const south=await p.evaluate(()=>{const z=WORLD_MAP.zones[3],a=z.exitArches.find(a=>a.portal==='path_4_0');return {x:a.x,y:a.y,street:z.roads.find(r=>r.x0===110&&r.x1===114),route:z.exitRoutes.find(r=>r.portal===a.portal).points};});
 check(south.x===(south.street.x0+south.street.x1)/2&&south.y===140,'The southern arch is centred on the actual Raven Row paving');
 check(south.route.some(([x,y])=>x===112&&y<140)&&south.route.some(([x,y])=>x===112&&y>140),'The highlighted approach runs through the arch into the street');
 for(const [name,x,y]of[['left',20,89.5],['bottom',112,144]]){
  await at(x,y);await p.waitForTimeout(300);await p.screenshot({path:path.join(w.runDir,name+'-desktop.png')});
  await p.setViewportSize({width:844,height:390});await p.waitForTimeout(300);await p.screenshot({path:path.join(w.runDir,name+'-phone.png')});await p.setViewportSize({width:1280,height:900});
 }
 for(const [name,x,y,tx,ty]of[['left',21,89.5,11,89.5],['bottom',112,134,112,146]]){
  await at(x,y);await p.evaluate(([x,y])=>Online.send({type:'move',x,y}),[tx,ty]);await p.waitForFunction(([x,y])=>Field.zone===4&&Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<.6,[tx,ty],{timeout:15000});
  await p.evaluate(()=>Online.send({type:'stop'}));check(true,`${name}: normal server-authoritative walking crosses the visible opening`);
 }
 check(errors.length===0,'No browser errors');console.log(`skaldholm-arches-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
