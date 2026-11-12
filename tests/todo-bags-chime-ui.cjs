const assert=require('node:assert/strict'),fs=require('node:fs');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
require('./lib/touch.cjs').requireMemoryLimit();
const world=new TestWorld();let browser,checks=0;
const check=(ok,message)=>{assert.ok(ok,message);console.log(++checks+'. '+message);};
async function debug(page,command){await page.evaluate(command=>Online.send({type:'debug',command}),command);await page.waitForTimeout(200);}
async function fillBag(page) {
 const fill=await page.evaluate(()=>WORLD_ITEMS.filter(i=>i.kind==='material').map(i=>i.id).slice(0,20));
 for(const item of fill){if(await page.evaluate(()=>Field.hero.bagUsed>=Field.hero.bagCapacity))break;await debug(page,{op:'give_item',item,quantity:1});}
 check(await page.evaluate(()=>Field.hero.bagUsed===Field.hero.bagCapacity),'Fixture fills the real bag without grinding');
}
async function pickupRefusal(page) {
 const material=await page.evaluate(()=>WORLD_ITEMS.find(i=>i.kind==='material'&&!Field.hero.inventory.some(s=>s.item===i.id)).id);
 // The debug drop creates a world pile; it does not take an item out of the bag.
 await debug(page,{op:'drop_item',item:material,quantity:1});
 await page.waitForFunction(()=>document.getElementById('error-messages').textContent.includes('Nobody nearby has bag room'));
 check(true,'Ground loot with no bag room appears in the same red error stack');
 check(await page.evaluate(()=>Field.hero.bagUsed===Field.hero.bagCapacity),'Refused pickup keeps the bag unchanged');
 await page.screenshot({path:world.runDir+'/ground-bag-refusal.png'});
}
(async()=>{try{
 await world.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});const page=await browser.newPage({viewport:{width:1100,height:720}}), errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({sound:false,combatSounds:'synthesized',musicVol:0,weatherAudio:0,lang:'en'})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('BagChimeCheck');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
 if(process.env.PART==='pickup'){
  await fillBag(page);await debug(page,{op:'teleport',zone:0,x:30,y:30});await pickupRefusal(page);
  check(errors.length===0,'No browser errors');console.log(`${checks} focused pickup checks passed; ${world.runDir}`);return;
 }
 await page.evaluate(()=>{window.chimes=0;const play=QuestAudio.play;QuestAudio.play=()=>{chimes++;play();};});
 await debug(page,{op:'quest',id:'welcome',action:'accept'});check(await page.evaluate(()=>chimes===0),'Accepting a quest is silent');
 await debug(page,{op:'quest',id:'welcome',action:'complete'});await page.waitForFunction(()=>chimes===1);
 check(await page.locator('#announce').textContent().then(s=>s.includes('Quest completed: A Home in Alderhaven')),'One chime accompanies the named completion banner');
 await page.waitForTimeout(400);check(await page.evaluate(()=>chimes===1),'Repeated snapshots do not replay the chime');
 check(await page.evaluate(()=>{Quests.reset();Quests.update(Field.hero.quests);return chimes===1;}),'Loading already-completed progress is silent');
 const audio=await page.evaluate(()=>{
  const proto=AudioContext.prototype,original=proto.createOscillator;let starts=0;
  proto.createOscillator=function(){const o=original.call(this),start=o.start.bind(o);o.start=(...a)=>{starts++;return start(...a);};return o;};
  Prefs.set({sound:true,combatSounds:'synthesized',sfxVol:.3});QuestAudio.play();const sounding=starts;
  Prefs.set({sound:false});QuestAudio.play();const muted=starts-sounding;proto.createOscillator=original;return{sounding,muted};
 });check(audio.sounding===2&&audio.muted===0,'The chime uses WebAudio and respects the sound switch');
 await debug(page,{op:'quest',id:'slime_patrol',action:'accept'});await debug(page,{op:'quest',id:'slime_patrol',action:'complete'});
 await fillBag(page);
 await debug(page,{op:'teleport',zone:0,...await page.evaluate(()=>{const n=WORLD_MAP.npcs.find(n=>n.id==='gatekeeper');return{x:n.x,y:n.y};})});
 await page.evaluate(()=>Field.visitNpc('gatekeeper'));await page.locator('#npc-dialogue').waitFor({state:'visible'});
 await page.locator('#npc-quest-list [data-quest="slime_patrol"]').click();
 const before=await page.evaluate(()=>JSON.stringify([Field.hero.gold,Field.hero.xp,Field.hero.inventory,Field.hero.quests]));
 await page.locator('#npc-quest-actions [data-action="claim"]').click();
 await page.waitForFunction(()=>[...document.querySelectorAll('#error-messages .announce-line')].some(n=>n.textContent==='Insufficient bag space'));
 check(await page.evaluate(()=>document.getElementById('error-messages').getBoundingClientRect().top<document.getElementById('fieldcv').getBoundingClientRect().top+100),'Refused quest reward appears in the top error stack');
 check(await page.evaluate(before=>JSON.stringify([Field.hero.gold,Field.hero.xp,Field.hero.inventory,Field.hero.quests])===before,before),'Refusal grants no reward or partial quest state');
 check(await page.locator('#npc-quest-actions [data-action="claim"]').isVisible(),'Refused turn-in keeps the quest available to claim');
 await page.screenshot({path:world.runDir+'/quest-bag-refusal.png'});
 await page.keyboard.press('Escape');
 await pickupRefusal(page);
 check(errors.length===0,'No browser errors');console.log(`${checks} focused checks passed; ${world.runDir}`);
 }finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
