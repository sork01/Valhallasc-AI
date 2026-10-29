// Same-version follow-up: ground selection, female synthesis and unified vendor stock.
const root = require('node:path').resolve(__dirname, '..');
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require(root+'/tests/lib/playwright.cjs');
const {requireMemoryLimit,debug,sleep}=require(root+'/tests/lib/touch.cjs');
const {TestWorld}=require(root+'/scripts/testing/driver.cjs');
requireMemoryLimit();
const world=new TestWorld();world.startLevel=99;world.godMode=true;
let browser,checks=0;const check=(v,label)=>{assert.ok(v,label);checks++;console.log('ok:',label);};
(async()=>{
 await world.start();browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const candidate=process.env.FOLLOWUP_CANDIDATE||root+'/client';
 for(const file of ['field.js','game.js','city.js','shop.js']){
  let source=fs.readFileSync(candidate+'/'+file,'utf8');
  if(file==='field.js'&&process.env.MUTATE==='ring'){
   const start=source.indexOf('    // Selection belongs to the floor'),end=source.indexOf('    // build the depth-sorted list',start);
   source=source.slice(0,start)+source.slice(end);
   const actor='const s = it.s, src = enemySource(s); g.save(); g.translate(it.sx, it.sy); if (src) drawSlimeSprite(g, s, t); else drawSlime(g, s, t);';
   source=source.replace(actor,actor+" if (!s.dead && hero.target === s) { g.strokeStyle = '#ffe066'; g.lineWidth = 2.5; g.beginPath(); g.ellipse(0, 2, 32 * s.d.scale, 13 * s.d.scale, 0, 0, 6.283); g.stroke(); }");
  }
  await page.route('**/'+file,r=>r.fulfill({body:source,contentType:'text/javascript'}));
 }
 await page.addInitScript(()=>{
  localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,combatSounds:'synthesized',musicVol:0,weatherAudio:0}));
  window.voiceTap={oscillators:[],filters:[]};
  const osc=AudioContext.prototype.createOscillator,filter=AudioContext.prototype.createBiquadFilter;
  AudioContext.prototype.createOscillator=function(){const o=osc.call(this),set=o.frequency.setValueAtTime.bind(o.frequency);o.frequency.setValueAtTime=(v,t)=>{o.initialPitch??=v;return set(v,t);};voiceTap.oscillators.push(o);return o;};
  AudioContext.prototype.createBiquadFilter=function(){const f=filter.call(this);voiceTap.filters.push(f);return f;};
 });
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#cls-warrior').click();await page.locator('#gender-female').click();await page.locator('#name').fill('FollowupCheck');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);
 await debug(page,{op:'set_gold',gold:2000000});
 await debug(page,{op:'teleport',zone:0,x:80,y:80});await page.waitForFunction(()=>Math.hypot(Field.hero.x-80,Field.hero.y-80)<1);
 for(const [kind,bank,x] of [['crab','rimeSprites',84],['toad','fenSprites',76]]){
  await debug(page,{op:'spawn_enemy',kind,x,y:80,level:1});
  await page.waitForFunction(([kind,bank])=>Field[bank]?.img[kind]&&Field.slimes.some(s=>s.kind===kind&&!s.dead&&Math.hypot(s.x-80,s.y-80)<8),[kind,bank]);
  const trace=await page.evaluate(([kind,bank])=>{
   const s=Field.slimes.find(s=>s.kind===kind&&!s.dead&&Math.hypot(s.x-80,s.y-80)<8);Field.hero.target=s;
   const g=document.getElementById('fieldcv').getContext('2d'),stroke=g.stroke,draw=g.drawImage,events=[];
   g.stroke=function(...args){if(this.strokeStyle==='#ffe066')events.push('ring');return stroke.apply(this,args);};
   g.drawImage=function(image,...args){if(image===Field[bank].img[kind])events.push('enemy');return draw.call(this,image,...args);};
   try{Field._debug.drawFrame(performance.now()/1000);}finally{g.stroke=stroke;g.drawImage=draw;Field.hero.target=null;}
   return events;
  },[kind,bank]);
  check(trace.includes('ring')&&trace.includes('enemy')&&trace.indexOf('ring')<trace.indexOf('enemy'),kind+' selection ring paints below its sprite');
 }
 async function visit(id,zone=0){
  await page.evaluate(()=>City.close());
  const npc=await page.evaluate(([id,zone])=>Field._debug.zones[zone].npcs.find(n=>n.id===id),[id,zone]);
  assert.ok(npc,'fixture NPC '+id);
  await debug(page,{op:'teleport',zone,x:npc.x,y:npc.y+1});await page.waitForFunction(([zone,npc])=>Field.zone===zone&&Math.hypot(Field.hero.nx-npc.x,Field.hero.ny-npc.y-1)<.5,[zone,npc]);
  await sleep(650);await page.evaluate(id=>Field.visitNpc(id),id);
  await page.waitForFunction(()=>City.open&&!document.getElementById('npc-dialogue').hidden);
  check(await page.locator('#npc-offers [data-view="buy"]').count()===1 && await page.locator('#npc-offers [data-view="buy"] .gossip-label').textContent()==='Buy',id+' always offers Buy on the greeting');
  check(!await page.evaluate(()=>Shop.open),id+' opens at quests/services');
  return npc;
 }
 async function buy(){await page.locator('#npc-offers [data-view="buy"]').click();await page.waitForFunction(()=>Shop.open&&document.querySelector('.merchant-workspace[aria-busy="false"]'));}
 await visit('apothecary');
 check(await page.locator('#npc-offers [data-offer="buy_health_potion"]').count()===0,'item purchases do not appear as separate greeting buttons');
 check(await page.locator('#npc-offers [data-offer="tonic"]').count()===1,'healing remains a service');
 await buy();check(await page.locator('#merchant-stock [data-offer]').count()===2,'both potion families are under Buy');
 const potion=await page.locator('#merchant-stock [data-offer="buy_health_potion"]').getAttribute('data-item');
 const before=await page.evaluate(id=>({count:Inventory.quantity(id),gold:Field.hero.gold}),potion);
 await page.locator('#merchant-stock [data-offer="buy_health_potion"]').click();
 await page.waitForFunction(([id,count,gold])=>Inventory.quantity(id)===count+1&&Field.hero.gold<gold,[potion,before.count,before.gold]);
 check(await page.evaluate(()=>Shop.open),'a real purchase keeps Buy open');
 const merchant=await visit('merchant');check(await page.locator('#npc-offers [data-view="bags"]').count()===0,'bags use the same Buy option');await buy();
 const stock=new Set();
 for(let i=0;i<4;i++){
  for(const id of await page.locator('#merchant-stock [data-offer]').evaluateAll(es=>es.map(e=>e.dataset.offer)))stock.add(id);
  if(await page.locator('.merchant-pages [aria-label="Next page"]').isDisabled())break;
  await page.locator('.merchant-pages [aria-label="Next page"]').click();
 }
 const expected=merchant.offers.filter(o=>(o.item||o.bag||o.mount)&&(!o.id.startsWith('buy_green_weapon_')||o.id==='buy_green_weapon_warrior')).map(o=>o.id);
 check(expected.every(id=>stock.has(id))&&stock.size===expected.length,'all merchant goods and bag tiers appear across Buy pages');
 await page.locator('#npc-back').click();check(await page.locator('#npc-offers [data-view="buy"]').count()===1,'Back returns to Buy and services');
 await visit('gearwright');check(await page.locator('#npc-offers [data-offer="crystal_common"]').count()===0,'crystals no longer have individual greeting buttons');await buy();
 check(await page.locator('#merchant-stock [data-offer]').count()===5,'all refinement crystals are under Buy');
 await visit('city_stable',4);check(await page.locator('#npc-offers [data-offer="buy_mount"]').count()===0,'mount purchase is also under Buy');await buy();
 check(await page.locator('#merchant-stock [data-offer="buy_mount"]').count()===1,'Buy lists the riding horse');
 await page.locator('#merchant-stock [data-offer="buy_mount"]').click();await page.waitForFunction(()=>Field.hero.mounts.includes('horse'));
 check(true,'buying a mount uses the authoritative purchase action');
 await page.evaluate(()=>{City.close();Field.stop();});await sleep(1200);
 const voices=await page.evaluate(()=>{
  const result=[],look={...Field.hero.look};
  for(const cls of ['warrior','mage','assassin','priest','hunter'])for(const gender of ['male','female'])for(const event of ['hurt','death']){
   Field.hero.look.class=cls;Field.hero.look.gender=gender;voiceTap.oscillators=[];voiceTap.filters=[];
   __combatAudioTest.play(event);
   result.push({cls,gender,event,pitch:voiceTap.oscillators.find(o=>o.type==='sawtooth')?.initialPitch,formants:voiceTap.filters.filter(f=>f.type==='bandpass').map(f=>f.frequency.value),vibrato:voiceTap.oscillators.some(o=>Math.abs(o.frequency.value-6.2)<.01)});
  }
  Field.hero.look=look;return result;
 });
 for(const cls of ['warrior','mage','assassin','priest','hunter'])for(const event of ['hurt','death']){
  const male=voices.find(v=>v.cls===cls&&v.gender==='male'&&v.event===event),female=voices.find(v=>v.cls===cls&&v.gender==='female'&&v.event===event);
  check(female.pitch>male.pitch*1.5&&female.formants.join()!==male.formants.join()&&female.vibrato,cls+' female '+event+' has distinct pitch, resonances and vibrato');
 }
 await sleep(1300);
 const wave=await page.evaluate(async()=>{
  const bus=__combatAudioTest.bus(),analyser=bus.context.createAnalyser();analyser.fftSize=2048;bus.connect(analyser);const data=new Float32Array(2048);let peak=0;
  Field.hero.look.gender='female';__combatAudioTest.play('hurt');
  for(let i=0;i<35;i++){await new Promise(r=>setTimeout(r,10));analyser.getFloatTimeDomainData(data);for(const v of data)peak=Math.max(peak,Math.abs(v));}
  analyser.disconnect();return peak;
 });
 check(wave>.005&&wave<.95,'female synthesized hurt is audible without clipping: '+wave);
 check(errors.length===0,'no browser errors: '+errors.join('; '));
 console.log(JSON.stringify({checks,runDir:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();await world.stop();});
