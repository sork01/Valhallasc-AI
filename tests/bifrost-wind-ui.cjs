// Focused regression: the landing is bounded, ascent rises, and return descends.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
require('./lib/touch.cjs').requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const candidate = process.env.BIFROST_CANDIDATE;
const world = new TestWorld(); world.godMode = true; world.startLevel = 99;
let browser, checks = 0;
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (candidate) {
    await page.context().grantPermissions(['local-network-access'], { origin: world.url });
    for (const file of ['index.html','world.js','zonejourney.js','sv-data.js','release-notes.txt']) await page.route(file === 'index.html' ? world.url : '**/'+file,
      r => r.fulfill({ body: fs.readFileSync(path.join(candidate,file)), contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.html') ? 'text/html' : 'application/json' }));
  }
  const version = fs.readFileSync(path.join(candidate || path.join(root,'client'),'index.html'),'utf8').match(/class="version">([^<]+)</)[1];
  await page.addInitScript(version => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.whats-new.v1', version);
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang:'en', sound:false, dpsMeter:false, char:null, draft:null }));
  }, version);
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('BifrostWind'); await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, {timeout:60000});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  const stop = () => page.evaluate(() => { Field.clearInput(); Online.send({type:'stop'}); });
  const teleport = async (zone,x,y) => {
    await stop();
    await page.evaluate(command => Online.send({type:'debug',command}), {op:'teleport',zone,x,y});
    await page.waitForFunction(({zone,x,y}) => Field.zone === zone && Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<.2, {zone,x,y});
  };
  for (const [name,x,y,dx,dy] of [['east',48.5,71.5,1,0],['west',30.5,73.5,-1,0],['north',40.5,70.5,0,-1],['south',40.5,82.5,0,1]]) {
    await teleport(7,x,y);
    await page.evaluate(([dx,dy]) => Field.setTouchDirection(dx-dy,dx+dy),[dx,dy]);
    const samples = await page.evaluate(async () => {
      const rows=Field._debug.zones[7].sky, result=[];
      for(let i=0;i<12;i++) {
        const h=Field.hero; result.push({zone:Field.zone,x:h.nx,y:h.ny,tile:rows[Math.floor(h.ny)]?.[Math.floor(h.nx)]});
        await new Promise(resolve=>setTimeout(resolve,60));
      }
      return result;
    });
    await stop();
    check(samples.every(p => p.zone===7 && p.tile && p.tile!==' '), `Held movement cannot leave the ${name} platform edge: ${JSON.stringify(samples)}`);
    // A 0.3-radius player may move 0.2 tiles from these half-tile starts.
    check(samples.every(p => (p.x-x)*dx+(p.y-y)*dy <= .21), `The ${name} boundary stops movement at the platform rim`);
  }
  const art = await page.evaluate(() => {
    const c=document.createElement('canvas');c.width=800;c.height=600;const g=c.getContext('2d'),zs=Field._debug.zones;
    const sample=(from,to,time,still) => {
      g.clearRect(0,0,800,600);const ellipses=[],texts=[],original=g.ellipse,text=g.fillText;
      g.ellipse=function(x,y,...args){ellipses.push(y);return original.call(this,x,y,...args);};
      g.fillText=function(s,...args){texts.push(s);return text.call(this,s,...args);};
      try { ZoneJourney.approach(g,{x:0,y:0,walk:[1,0]},zs[from],zs[to],()=>[400,300],time,still); }
      finally {g.ellipse=original;g.fillText=text;}
      const pixels=g.getImageData(0,0,800,600).data;let visible=0,hash=0;
      for(let i=0;i<pixels.length;i+=4){if(pixels[i+3]>30)visible++;hash=(Math.imul(hash,31)+pixels[i]+pixels[i+1]+pixels[i+2]+pixels[i+3])|0;}
      return {ellipses,texts,visible,hash};
    };
    return {up:sample(6,7,2,true),down:sample(7,6,2,true),water:sample(7,8,2,true),still:sample(6,7,20,true)};
  });
  check(art.up.visible > 3000 && art.up.ellipses.some(y => y < -150) && art.up.texts.some(t=>t.includes('Ride the updraft')), 'Lower end has a visible rising wind column and updraft label');
  check(art.down.visible > 3000 && art.down.ellipses.every(y => y >= -20) && art.down.texts.some(t=>t.includes('Descend through the clouds')), 'Bifrost return is a downward opening at floor level with no upward flight');
  check(art.water.ellipses.every(y=>y>=-20) && art.water.texts.some(t=>t.includes('Dive into the depths')), 'Ocean descent is a low swirling water passage');
  check(art.up.hash === art.still.hash, 'Reduced-motion wind stays still');
  for (const [from,to] of [[6,7],[7,6]]) {
    const gate = await page.evaluate(([from,to])=>Field._debug.zones[from].portals.find(p=>p.to===to),[from,to]);
    await teleport(from,gate.x-gate.walk[0]*4,gate.y-gate.walk[1]*4); await page.waitForTimeout(1300);
    await page.screenshot({path:path.join(world.runDir,`wind-approach-${from}-${to}.png`)});
    const labels = await page.evaluate(() => {
      const g=document.getElementById('fieldcv').getContext('2d'),orig=g.fillText,labels=[];
      g.fillText=function(text,...args){labels.push(text);return orig.call(this,text,...args);};
      try{Field._debug.drawFrame(4);return labels;}finally{g.fillText=orig;}
    });
    check(labels.some(t=>t.includes(from===6?'Ride the updraft':'Descend through the clouds')), 'Actual game approach has the correct wind direction from '+from);
    await page.evaluate(gate=>Field.setTouchDirection(gate.walk[0]-gate.walk[1],gate.walk[0]+gate.walk[1]),gate);
    await page.waitForFunction(to=>Field.zone===to,to,{timeout:20000}); await stop();
    check((await page.locator('#zone-journey').innerText()).includes(from===6?'Ascending into the sky':'Descending from the sky'), 'Authoritative wind crossing announces the correct height change');
  }
  check(errors.length===0,'No browser errors: '+errors.join('; '));
  console.log(`bifrost-wind-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
