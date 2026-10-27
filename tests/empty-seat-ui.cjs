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
 await page.locator('#cls-hunter').click();await page.locator('#name').fill('SeatTester');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero.level===99);
 const send=p=>page.evaluate(p=>Online.send(p),p),debug=command=>send({type:'debug',command});
 const close=()=>page.evaluate(()=>{City.close();Quests.close();});
 const tp=async(zone,x,y)=>{await close();await debug({op:'teleport',zone,x,y});await page.waitForFunction(p=>Field.zone===p.zone&&Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.2,{zone,x,y});};
 const site=async id=>page.evaluate(id=>{for(const [zone,z]of[WORLD_MAP,...WORLD_MAP.zones].entries()){const p=z.places?.find(p=>p.id===id);if(p)return{zone,...p};}},id);
 const go=async id=>{const p=await site(id);await tp(p.zone,p.x,p.y);};
 const talk=async id=>{
  const q=await page.evaluate(id=>[WORLD_MAP,...WORLD_MAP.zones].flatMap((z,zone)=>(z.quests||[]).map(q=>({...q,zone}))).find(q=>q.id===id),id);
  const n=await page.evaluate(({zone,npc})=>[WORLD_MAP,...WORLD_MAP.zones][zone].npcs.find(n=>n.id===npc),q);
  await tp(q.zone,n.x+1,n.y);await page.waitForTimeout(550);await send({type:'interact',npc:q.npc});
  await page.locator('#npc-dialogue').waitFor({state:'visible'});
  if(await page.locator('#npc-back').isVisible())await page.locator('#npc-back').click();
  return q;
 };
 const prepare=async id=>{ // Prerequisite fixtures avoid grinding through unrelated earlier chapters.
  const n=Number(id.slice(3));for(let i=1;i<n;i++) {
   if(await page.evaluate(i=>Field.hero.quests.some(q=>q.id===`es_${String(i).padStart(2,'0')}`&&q.claimed),i))continue;
   await debug({op:'quest',id:`es_${String(i).padStart(2,'0')}`,action:'finish'});
   // Fixture rewards are removed between prerequisite claims to avoid filling a real bag.
   const reward=await page.evaluate(i=>[WORLD_MAP,...WORLD_MAP.zones].flatMap(z=>z.quests||[]).find(q=>q.id===`es_${String(i).padStart(2,'0')}`).rewardChoices.hunter[0],i);
   await debug({op:'take_item',item:reward,quantity:1});
  }
  await page.waitForFunction(n=>Field.hero.quests.some(q=>q.id===`es_${String(n-1).padStart(2,'0')}`&&q.claimed),n);
 };
 const q1=await talk('es_01');await page.locator('[data-quest="es_01"][data-status="available"]').click();
 check((await page.locator('#npc-quests').textContent()).includes('Bram found warm ash'),'First chapter introduces the mystery through Bram');
 check(await page.locator('#npc-quests .quest-location').count()===1,'Quest page shows its campaign chapter once');
 check(await page.locator('#npc-quests .quest-reward-icon').count()===2,'Quest window offers two own-class green pieces');
 await page.locator('#npc-quests [data-action="accept"]').click();await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='es_01'));
 await go('es_01_m');await page.waitForFunction(()=>EmptySeat.scene()?.id==='es_01_m');
 check(await page.evaluate(()=>Quests.mapMarkers(0).some(m=>m.state==='tracked')||EmptySeat.sites().some(p=>p.id==='es_01_m')),'Campaign circle is discoverable from accepted objectives');
 check(await page.evaluate(()=>document.getElementById('area-title').hidden),'Arrival banner yields to the memory caption');
 check(await page.evaluate(()=>{
  const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),original=g.fillText,calls=[];
  g.fillText=function(...args){calls.push({align:this.textAlign,size:parseFloat(this.font.match(/[\d.]+px/)[0])*this.getTransform().a});return original.apply(this,args);};
  const transform=g.getTransform();
  try { EmptySeat.drawVision(g,(x,y)=>[x,y],cv.width/transform.a,cv.height/transform.d); } finally { g.fillText=original; }
  return calls.length>2&&calls.every(c=>c.align==='left'&&c.size>=14.8);
 }),'Memory paragraphs stay left aligned and at least 15 screen pixels high');
 if(process.env.MUTATE==='draw')await page.evaluate(()=>EmptySeat.drawVision=()=>{});
 const pixels=await page.evaluate(()=>{
  const c=document.getElementById('fieldcv'),g=c.getContext('2d'),draw=EmptySeat.drawVision,t=performance.now()/1000;
  Field._debug.drawFrame(t);const a=g.getImageData(0,0,c.width,c.height).data;
  EmptySeat.drawVision=()=>{};Field._debug.drawFrame(t);const b=g.getImageData(0,0,c.width,c.height).data;EmptySeat.drawVision=draw;
  let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>40)n++;return n;
 });check(pixels>3000,'Readable memory panel draws above the world with reduced motion');
 await page.keyboard.down('d');await page.waitForTimeout(200);await page.keyboard.up('d');
 await page.waitForFunction(()=>!Field.hero.storyMemory);check(true,'Walking interrupts the memory');
 await go('es_01_m');await page.waitForFunction(()=>Field.hero.quests.find(q=>q.id==='es_01').counts[0]===1,null,{timeout:25000});
 await talk('es_01');await page.locator('[data-quest="es_01"][data-status="ready"]').click();
 const reward=await page.locator('#npc-quests .quest-reward-icon').first().getAttribute('data-item');
 await page.locator('#npc-quests .quest-reward-icon').first().click();await page.waitForFunction(()=>Field.hero.quests.find(q=>q.id==='es_01').claimed);
 check(await page.evaluate(id=>Field.hero.inventory.some(i=>i.item===id),reward),'Real quest claim grants the selected green piece');
 await close();await page.evaluate(()=>Quests.show());
 await page.locator('.quest-completed > summary').click();await page.locator('.quest-entry[data-quest="es_01"] > summary').click();
 await page.locator('.quest-entry[data-quest="es_01"] .quest-memories').waitFor({state:'attached'});
 check((await page.locator('.quest-entry[data-quest="es_01"]').textContent()).includes('Take my winter instead'),'Completed journal preserves the recovered memory');
 await close();await talk('es_02');await page.waitForTimeout(550);await send({type:'interact',npc:'crags_scout',offer:'quest:accept:es_02'});
 await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='es_02'));await go('es_02_m');
 await page.waitForFunction(()=>Field.slimes.some(s=>s.kind==='es_foe_02'&&!s.dead));
 check(await page.evaluate(()=>Field.enemyName('es_foe_02')==='Cinder Without a Hearth'),'New encounter spawns the named quest enemy');
 const enemy=await page.evaluate(()=>Field.slimes.find(s=>s.kind==='es_foe_02'&&!s.dead).id);
 const before=await page.evaluate(()=>({xp:Field.hero.xp,gold:Field.hero.gold}));await debug({op:'kill_enemy',id:enemy});
 await page.waitForFunction(()=>Field.hero.quests.find(q=>q.id==='es_02').counts[0]===1);
 check(await page.evaluate(b=>Field.hero.xp===b.xp&&Field.hero.gold===b.gold,before),'Summoned enemy advances its quest without farmable gold or XP');
 await prepare('es_14');await talk('es_14');await page.waitForTimeout(550);await send({type:'interact',npc:'asterion_archon',offer:'quest:accept:es_14'});
 await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='es_14'));await go('es_14_2');
 check(await page.evaluate(()=>!EmptySeat.sites().some(p=>p.id==='es_14_2')),'Flashback presents the rescue before the betrayal');
 await go('es_14_0');await page.waitForFunction(()=>EmptySeat.scene()?.id==='es_14_0');
 check(await page.evaluate(()=>EmptySeat.scene().description.includes('lays his fire beneath the roots')),'Playable flashback shows Eldmarr saving the roots');
 await page.screenshot({path:path.join(world.runDir,'empty-seat-first-hearth.png')});
 await prepare('es_26');await talk('es_26');await page.locator('[data-quest="es_26"][data-status="available"]').click();
 check(await page.locator('#npc-quests .quest-reward-icon[data-rarity="epic"]').count()===2,'Last quest before the raid previews two purple choices');
 check(await page.evaluate(()=>[WORLD_MAP,...WORLD_MAP.zones].flatMap(z=>z.quests||[]).filter(q=>q.story).length===28),'All 28 chapters are published in the journal catalog');
 await page.locator('#npc-quests .quest-reward-icon').first().scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(world.runDir,'empty-seat-purple-reward.png')});
 check(errors.length===0,'No browser errors');console.log(`${checks} Empty Seat checks passed: ${world.runDir}`);
})().catch(async e=>{console.error(e);if(page){await page.screenshot({path:path.join(world.runDir,'empty-seat-failure.png')}).catch(()=>{});console.error(await page.locator('#npc-dialogue').textContent().catch(()=>''));}process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
