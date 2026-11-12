// One real zone per bounded process, focusing on newly assigned people.
process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const zone = Number(process.env.ZONE || 0);
const worldMap = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt')));
const plan = JSON.parse(fs.readFileSync(path.join(root, 'docs/npc-named-plan.txt')));
const wanted = plan.people.filter(p => p.zone === zone);
assert(wanted.length);
const z = zone ? worldMap.zones[zone-1] : worldMap;
const first = z.npcs.find(n => n.id === wanted[0].id);
let browser;
const world = new TestWorld();
(async () => {
  try {
    world.godMode = true; await world.start();
    browser = await chromium.launch({ headless:true, args:['--disable-gpu'] });
    const page = await browser.newPage({ viewport:{width:960,height:600}, reducedMotion:'reduce' });
    const errors=[]; page.on('pageerror',e=>errors.push(e.message));
    if (process.env.MUTATE_STYLE) {
      const src=fs.readFileSync(path.join(root,'client/npc-art.js'),'utf8');
      assert(src.includes('const isNew = !!fresh && !!fresh.sprites[who.art]'));
      await page.route('**/npc-art.js*',r=>r.fulfill({contentType:'application/javascript',body:src.replace('const isNew = !!fresh && !!fresh.sprites[who.art]','const isNew = false')}));
    }
    await page.addInitScript(()=>{
      window.AudioContext=window.webkitAudioContext=undefined;
      localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true,dpsMeter:false}));
    });
    await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
    await page.locator('#cls-warrior').click();await page.locator('#name').fill('NpcRelease');await page.locator('#go').click({timeout:60000});
    await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
    await page.evaluate(({zone,first})=>Online.send({type:'debug',command:{op:'teleport',zone,x:first.x+2,y:first.y+2}}),{zone,first});
    await page.waitForFunction(zone=>Field.zone===zone&&City.npcs.length>0,zone,{timeout:40000});
    assert(await page.evaluate(id=>NpcArt.styleOf({id})==='player',wanted[0].id),'New assignment selects player-style art');
    await page.waitForFunction(ids=>NpcArt.readyFor(City.npcs.filter(n=>ids.includes(n.id))),wanted.map(p=>p.id),{timeout:40000});
    const results=await page.evaluate(wanted=>wanted.map(p=>{
      const n=City.npcs.find(n=>n.id===p.id);if(!n)return {id:p.id,missing:true};
      const who=NpcArt.manifest.npcs[n.id],spec=NpcArt.fresh.designs[who.art];
      const render=()=>{
        const cv=document.createElement('canvas');cv.width=220;cv.height=280;const g=cv.getContext('2d',{willReadFrequently:true});
        City.drawNpc(g,{...n,x:-999,y:-999,key:false,offers:[],buys:null,moving:false,fx:1,fy:0},110,230,.37,false,false);
        return g.getImageData(0,0,cv.width,cv.height).data;
      };
      const pixels=render();let opaque=0;for(let i=3;i<pixels.length;i+=4)if(pixels[i]>200)opaque++;
      let recolour=true;
      if(spec.general){const keep=who.color;who.color=keep==='#ff2020'?'#2020ff':'#ff2020';const changed=render();who.color=keep;let diff=0;for(let i=0;i<pixels.length;i+=4)if(pixels[i]!==changed[i]||pixels[i+1]!==changed[i+1]||pixels[i+2]!==changed[i+2])diff++;recolour=diff>30;}
      return {id:n.id,art:who.art,style:NpcArt.styleOf(n),opaque,head:NpcArt.head(n,.37,false),top:NpcArt.top(n),recolour,species:spec.species||'human'};
    }),wanted);
    for(const r of results){assert(!r.missing,r.id+' present in real zone');assert.equal(r.style,'player',r.id);assert(r.opaque>300,r.id+' visible through City.drawNpc');assert(r.head&&Number.isFinite(r.head.y),r.id+' head');assert(r.top>30,r.id+' nameplate');assert(r.recolour,r.id+' own cloth colour');}
    assert.deepEqual(errors,[]);
    await page.evaluate(()=>{City.close();ZoneJourney.clear();Field._debug.drawFrame(3);});
    const out=path.join(root,'test-results/npc-full-release/scenes');fs.mkdirSync(out,{recursive:true});
    await page.screenshot({path:path.join(out,`zone-${zone}.png`)});
    fs.writeFileSync(path.join(out,`zone-${zone}.json`),JSON.stringify(results,null,2)+'\n');
    console.log(`PASS zone ${zone}: ${results.length} newly assigned people visible with player art, head sockets, names and recolours`);
  }finally{await browser?.close();await world.stop();}
})().catch(e=>{console.error(e);process.exitCode=1;});
