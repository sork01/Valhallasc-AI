// Actual sky arrivals must stand on rendered floor and keep walking there.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const candidate=process.env.BIFROST_CANDIDATE, world=new TestWorld(); world.godMode=true; world.startLevel=99;
let browser,checks=0;
const check=(ok,label)=>{assert.ok(ok,label);console.log(`${++checks}: ${label}`);};
(async()=>{
  await world.start(); browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(candidate){
    await page.context().grantPermissions(['local-network-access'],{origin:world.url});
    for(const file of ['index.html','world.js','sv-data.js','release-notes.txt'])await page.route(file==='index.html'?world.url:'**/'+file,r=>r.fulfill({body:fs.readFileSync(path.join(candidate,file)),contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':'application/json'}));
  }
  const version=fs.readFileSync(path.join(candidate||path.join(__dirname,'../client'),'index.html'),'utf8').match(/class="version">([^<]+)</)[1];
  await page.addInitScript(version=>{
    window.AudioContext=undefined;window.webkitAudioContext=undefined;
    localStorage.setItem('valhallasc.whats-new.v1',version);
    localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:false,char:null,draft:null}));
  },version);
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('BifrostArrival');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
  if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
  for(const from of [6,9]){
    const gate=await page.evaluate(from=>Field._debug.zones[from].portals.find(p=>p.to===7),from);
    await page.evaluate(()=>{Field.clearInput();Online.send({type:'stop'});});
    await page.evaluate(({from,gate})=>Online.send({type:'debug',command:{op:'teleport',zone:from,x:gate.x-gate.walk[0]*6,y:gate.y-gate.walk[1]*6}}),{from,gate});
    await page.waitForFunction(from=>Field.zone===from,from);await page.waitForTimeout(1300);
    await page.evaluate(gate=>Field.setTouchDirection(gate.walk[0]-gate.walk[1],gate.walk[0]+gate.walk[1]),gate);
    await page.waitForFunction(()=>Field.zone===7,null,{timeout:20000});
    const arrival=await page.evaluate(()=>({x:Field.hero.nx,y:Field.hero.ny}));
    check(Math.hypot(arrival.x-gate.tx,arrival.y-gate.ty)<1,'Actual crossing uses the corrected Bifrost arrival from '+from);
    const samples=await page.evaluate(async()=>{
      const rows=Field._debug.zones[7].sky, results=[];
      for(let i=0;i<12;i++){
        const h=Field.hero;
        results.push({x:h.x,y:h.y,visible:rows[Math.floor(h.y)]?.[Math.floor(h.x)],authoritative:rows[Math.floor(h.ny)]?.[Math.floor(h.nx)]});
        await new Promise(resolve=>setTimeout(resolve,60));
      }
      return results;
    });
    check(samples.every(s=>s.visible&&s.visible!==' '&&s.authoritative&&s.authoritative!==' '),'Every displayed and authoritative position remains on visible island/bridge floor: '+JSON.stringify(samples));
    check(Math.hypot(samples.at(-1).x-samples[0].x,samples.at(-1).y-samples[0].y)>1,'Can keep walking after the landing from '+from);
    await page.evaluate(()=>{Field.clearInput();Online.send({type:'stop'});});
    check((await page.locator('#zone-altitude').innerText()).includes('High in the sky'),'Sky setting remains clearly labeled');
    await page.screenshot({path:path.join(world.runDir,`bifrost-arrival-from-${from}.png`)});
  }
  check(errors.length===0,'No browser errors: '+errors.join('; '));
  console.log(`bifrost-arrival-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
