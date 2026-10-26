// Focused canvas checks for Crags' shared molten terrain and the complete Skaldholm fountain sprite.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs'),{chromium}=require('./lib/playwright.cjs');
const world=new TestWorld();let browser,checks=0;const check=(value,message)=>{assert.ok(value,message);checks++;};
(async()=>{
  world.godMode=true;world.startLevel=99;await world.start();browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'no-preference'}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#name').fill('Scenery Observer');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.hero);
  const debug=command=>page.evaluate(command=>GM.request(command),command);
  await debug({op:'set_time',hour:12,freeze:true});await debug({op:'set_weather',kind:'clear'});
  const fountain=await page.evaluate(()=>{
    const def=City.art.grandfountain,o=WORLD_MAP.zones[3].objects.find(o=>o.kind==='grandfountain');
    const canvas=()=>{const c=document.createElement('canvas');c.width=1200;c.height=1000;return c;};
    const actual=canvas(),reference=canvas(),a=actual.getContext('2d'),r=reference.getContext('2d');
    // Use matching 2x rasterisation, the same as City.drawObject's sprite cache.
    const full=document.createElement('canvas');full.width=2400;full.height=2000;const g=full.getContext('2d');g.scale(2,2);g.translate(600,540);def.draw(g,o,City.kit);r.drawImage(full,0,0,1200,1000);
    City.drawObject(a,o,600,540);
    const ap=a.getImageData(0,0,1200,1000).data,rp=r.getImageData(0,0,1200,1000).data;
    let missing=0,bottom=0,minY=1000,maxY=0;
    for(let y=0;y<1000;y++)for(let x=0;x<1200;x++){const i=(y*1200+x)*4;if(rp[i+3]>0){minY=Math.min(minY,y);maxY=Math.max(maxY,y);if(y>700)bottom++;if(ap[i+3]+2<rp[i+3])missing++;}}
    return {missing,bottom,minY,maxY,box:def.box};
  });
  check(fountain.bottom>1000,'reference contains the lower basin and shadow');check(fountain.missing===0,'cached fountain preserves every drawn pixel: '+JSON.stringify(fountain));
  await debug({op:'teleport',zone:4,x:90,y:92});await page.waitForFunction(()=>Field.zone===4);await page.waitForTimeout(1500);
  await page.screenshot({path:path.join(world.runDir,'skaldholm-fountain.png')});
  const numbers=await page.evaluate(()=>{
    const h=Field.hero,list=Field._debug.floaters;list.splice(0);
    Field._debug.event({kind:'hit',actor:'distant-player',x:h.x-40,y:h.y-40,value:9876});
    const distantSpawn=list.some(f=>f.text==='9,876');
    Field._debug.event({kind:'hit',actor:'nearby-player',x:h.x,y:h.y,value:5432});
    const nearbySpawn=list.some(f=>f.text==='5,432');
    // A previously visible number can move outside the camera before it expires.
    DamageNumbers.spawn(list,{x:h.x-40,y:h.y-40,text:'9,876',kind:'hit',head:118});
    for(const f of list)f.t=.2;
    const g=document.querySelector('#fieldcv').getContext('2d'),original=g.fillText,drawn=[];
    g.fillText=function(text,...args){if(['5,432','9,876'].includes(text))drawn.push(text);return original.call(this,text,...args);};
    try{Field._debug.drawFrame(7);}finally{g.fillText=original;}
    return {distantSpawn,nearbySpawn,drawn};
  });
  check(!numbers.distantSpawn&&numbers.nearbySpawn,'remote hits do not crowd out nearby damage numbers');
  check(numbers.drawn.includes('5,432')&&!numbers.drawn.includes('9,876'),'off-screen damage is never clamped into the viewport: '+JSON.stringify(numbers));

  await page.evaluate(()=>{window.__moltenCalls=0;const original=EmberwakeArt.molten;EmberwakeArt.molten=(...args)=>{if(args[5].theme==='ember')window.__moltenCalls++;return original(...args);};});
  await debug({op:'teleport',zone:1,x:45,y:59});await page.waitForFunction(()=>Field.zone===1);await page.waitForTimeout(1500);
  check(await page.evaluate(()=>window.__moltenCalls>0),'Crags ground uses the shared molten renderer');
  const terrain=await page.evaluate(()=>{
    const z=WORLD_MAP.zones[0],lava=z.objects.filter(o=>o.kind==='lava'),ew={...z,theme:'emberwake',objects:lava.map(o=>({...o,kind:'ew_lava'}))};
    const draw=zone=>{const c=document.createElement('canvas');c.width=1000;c.height=1000;const g=c.getContext('2d');EmberwakeArt.molten(g,{x0:40,y0:57,ox:-1450,oy:2200},12,88,44,zone);return g.getImageData(0,0,1000,1000).data;};
    const a=draw(z),b=draw(ew);let pixels=0,differences=0;for(let i=0;i<a.length;i++){if(i%4===3&&a[i])pixels++;if(a[i]!==b[i])differences++;}return {pixels,differences};
  });
  check(terrain.pixels>1000&&terrain.differences===0,'Crags and Emberwake render identical texture for identical footprints: '+JSON.stringify(terrain));
  const motion=await page.evaluate(()=>{
    const z=WORLD_MAP.zones[0],c=document.createElement('canvas');c.width=800;c.height=500;const g=c.getContext('2d'),cx=(45-67)*44,cy=(45+67)*22;
    const draw=t=>{g.clearRect(0,0,800,500);EmberwakeArt.moltenMotion(g,800,500,t,z,cx,cy);return g.getImageData(0,0,800,500).data;};const a=draw(1),b=draw(7);let changed=0,painted=0;for(let i=0;i<a.length;i++){if(a[i]!==b[i])changed++;if(i%4===3&&a[i])painted++;}return {changed,painted};
  });check(motion.painted>10&&motion.changed>50,'Crags lava has the same animated fissures: '+JSON.stringify(motion));
  await page.screenshot({path:path.join(world.runDir,'crags-lava.png')});check(errors.length===0,JSON.stringify(errors));
  fs.writeFileSync(path.join(world.runDir,'scenery-fixes.json'),JSON.stringify({checks,fountain,terrain,motion},null,2));console.log(JSON.stringify({passed:true,checks,artifacts:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
