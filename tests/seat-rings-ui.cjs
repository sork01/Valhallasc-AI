// Empty Seat standing-stone rings + the "Main Questline" tag (ES-STONE-RINGS, MAIN-QUESTLINE-LABEL).
// Run: REAL_SPRITES=1 bash scripts/test-touch-bounded.sh tests/seat-rings-ui.cjs   (MUTATE=rings|tag must fail)
const assert=require('node:assert/strict'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const {chromium}=require('./lib/playwright.cjs');
const world=new TestWorld();let browser,page,checks=0;
const check=(v,t)=>{assert.ok(v,t);checks++;console.log(t);};
(async()=>{
 world.startLevel=99;world.godMode=true;world.levelSpread=0;await world.start();
 browser=await chromium.launch({headless:true});
 page=await browser.newPage({viewport:{width:1024,height:768},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#cls-hunter').click();await page.locator('#name').fill('RingTester');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero.level===99);
 const send=p=>page.evaluate(p=>Online.send(p),p),debug=command=>send({type:'debug',command});
 const close=()=>page.evaluate(()=>{City.close();Quests.close();});
 const tp=async(zone,x,y)=>{await close();await debug({op:'teleport',zone,x,y});await page.waitForFunction(p=>Field.zone===p.zone&&Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.2,{zone,x,y});};
 const site=id=>page.evaluate(id=>{for(const [zone,z]of[WORLD_MAP,...WORLD_MAP.zones].entries()){const p=z.places?.find(p=>p.id===id);if(p)return{zone,...p};}},id);
 // --- data: every campaign place carries a ring, and no ring is an obstacle (it lives on the place, not in `objects`)
 const all=await page.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].flatMap(z=>(z.places||[]).filter(p=>p.id.startsWith('es_'))));
 check(all.length>=30&&all.every(p=>p.ring&&p.ring.stones===12&&Number.isFinite(p.ring.seed)),`All ${all.length} Empty Seat places carry a 12-stone ring`);
 // --- accept chapter 1 (the quest is what makes the site "active")
 const q=await page.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>(z.quests||[]).map(q=>({...q,zone}))).find(q=>q.id==='es_01'));
 const n=await page.evaluate(({zone,npc})=>[WORLD_MAP,...WORLD_MAP.zones][zone].npcs.find(n=>n.id===npc),q);
 await tp(q.zone,n.x+1,n.y);await page.waitForTimeout(550);await send({type:'interact',npc:q.npc,offer:'quest:accept:es_01'});
 await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='es_01'));
 // --- the tag: tracker and journal page, main questline only
 if(process.env.MUTATE==='tag')await page.evaluate(()=>document.querySelectorAll('.tracker-main,.quest-main').forEach(e=>e.remove()));
 await page.waitForSelector('#quest-tracker [data-quest="es_01"]');
 check(await page.locator('#quest-tracker [data-quest="es_01"] .tracker-main').textContent()==='Main Questline','Tracker shows the Main Questline tag on the campaign quest');
 check(await page.evaluate(()=>[...document.querySelectorAll('#quest-tracker .tracker-quest')].every(r=>!!r.querySelector('.tracker-main')===/^es_(go_)?\d+$/.test(r.dataset.quest))),'Only campaign quests carry the tag in the tracker');
 check(await page.evaluate(()=>{const r=document.querySelector('#quest-tracker [data-quest="es_01"]');return r.firstElementChild.classList.contains('tracker-main')&&r.firstElementChild.getBoundingClientRect().bottom<=r.querySelector('.tracker-title').getBoundingClientRect().top+1;}),'The tag sits above the title');
 await close();await page.evaluate(()=>Quests.show());await page.locator('.quest-entry[data-quest="es_01"], .journal-quest[data-quest="es_01"]').first().click().catch(()=>{});
 await page.waitForSelector('.journal-detail[data-quest="es_01"]');
 check(await page.locator('.journal-detail[data-quest="es_01"] .quest-main').textContent()==='Main Questline','Journal page shows the Main Questline tag');
 check(await page.evaluate(()=>{const e=document.querySelector('.journal-detail[data-quest="es_01"] .quest-main'),c=getComputedStyle(e);return c.display==='block'&&e.getBoundingClientRect().height>8&&c.color!=='rgba(0, 0, 0, 0)';}),'The journal tag is visible');
 await page.evaluate(()=>{Quests.close();});
 // --- the ring at the first campaign circle
 const p=await site('es_01_m');await tp(p.zone,p.x,p.y);
 await page.waitForFunction(id=>EmptySeat.sites().some(s=>s.id===id),'es_01_m');
 const draw=()=>page.evaluate(()=>{const c=document.getElementById('fieldcv'),g=c.getContext('2d');Field._debug.drawFrame(performance.now()/1000);return Array.from(g.getImageData(0,0,c.width,c.height).data);});
 const diffWithout=async()=>page.evaluate(()=>{
  const c=document.getElementById('fieldcv'),g=c.getContext('2d'),t=performance.now()/1000,keep=EmptySeat.ringItems,keepFloor=EmptySeat.drawFloor;
  Field._debug.drawFrame(t);const a=g.getImageData(0,0,c.width,c.height).data;
  EmptySeat.ringItems=()=>[];Field._debug.drawFrame(t);const b=g.getImageData(0,0,c.width,c.height).data;EmptySeat.ringItems=keep;
  let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>30)n++;return n;});
 if(process.env.MUTATE==='rings')await page.evaluate(()=>{EmptySeat.ringItems=()=>[];});
 const items=await page.evaluate(()=>EmptySeat.ringItems((x,y)=>[x*10,y*10],()=>true));
 check(items.length>=12&&items.filter(i=>i.ring.id==='es_01_m').length===12,'The circle is drawn as 12 stones in the depth-sorted scenery list');
 const lit=await page.evaluate(()=>{Field._debug.drawFrame(performance.now()/1000);return EmptySeat.litOf('es_01_m');});
 check(lit>.95,`Standing inside the active ring lights it (${lit.toFixed(2)})`);
 const px=await diffWithout();
 check(px>1500,`The stones are really painted on the canvas (${px} changed pixels without them)`);
 const shot=async name=>{ // a clean look at the ring: no memory panel, tutorial tip or windows over it
  await page.evaluate(()=>{window.__vision=window.__vision||EmptySeat.drawVision;EmptySeat.drawVision=()=>{};document.querySelectorAll('#tutorial-tip,#dps-meter,#announce').forEach(e=>e.style.display='none');Field._debug.drawFrame(performance.now()/1000);});
  await page.screenshot({path:path.join(world.runDir,name),clip:{x:262,y:230,width:500,height:300}});
  await page.evaluate(()=>{EmptySeat.drawVision=window.__vision;});};
 await shot('seat-ring-lit.png');
 // the glow follows the hero out of the ring
 await tp(p.zone,p.x+(p.zone===0?4.5:4.5),p.y);
 const away=await page.evaluate(()=>{Field._debug.drawFrame(performance.now()/1000);return EmptySeat.litOf('es_01_m');});
 check(away<.05,`Outside the ring the stones go dark (${away.toFixed(2)})`);
 await shot('seat-ring-dark.png');
 // stones are scenery only: walk straight through the ring
 await tp(p.zone,p.x,p.y);
 await send({type:'move',x:p.x+3,y:p.y});await page.waitForTimeout(2500);   // a click-walk straight across the ring's edge
 const moved=await page.evaluate(id=>{const s=EmptySeat.ringPlaces().find(p=>p.id===id);return Math.hypot(Field.hero.x-s.x,Field.hero.y-s.y);},'es_01_m');
 check(moved>2.8,`The hero walks out through the stones (${moved.toFixed(1)} tiles from the centre, ring radius 2.1)`);
 check(errors.length===0,'No browser errors');
 console.log(`${checks} ring and tag checks passed: ${world.runDir}`);
})().catch(async e=>{console.error(e);if(page)await page.screenshot({path:path.join(world.runDir,'seat-rings-failure.png')}).catch(()=>{});process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
