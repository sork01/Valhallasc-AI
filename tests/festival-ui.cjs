process.env.REAL_SPRITES='1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const{chromium}=require('./lib/playwright.cjs'),{TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser,checks=0;const errors=[];const check=(v,s)=>{assert.ok(v,s);console.log(++checks+': '+s);};
const seasons=[['halloween',1793055600],['christmas',1797289200],['newyear',1798498800],['valentine',1802214000],['easter',1806015600],['solstice',1813183200]];
(async()=>{try{
 w.startLevel=20;w.godMode=true;await w.start();browser=await chromium.launch({headless:true});
 const p=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{window.AudioContext=window.webkitAudioContext=undefined;if(!localStorage.getItem('valhallasc.save.v1'))localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,dpsMeter:true,lowGraphics:true,lowGraphicsSet:true,touchGraphicsSuggested:true}));const WS=window.WebSocket;window.WebSocket=class extends WS{constructor(...a){super(...a);this.addEventListener('message',e=>{try{const v=JSON.parse(e.data);if(v.type==='snapshot'||v.type==='welcome')window.__snap=v.snapshot||v;}catch{}});}};window.__self=()=>window.__snap?.players.find(p=>p.id===window.Online?.id);});
 await p.goto(w.url);await p.locator('#start').click();await p.locator('#login-guest').click();await p.locator('#cls-warrior').click();await p.locator('#name').fill('FestivalGuest');await p.locator('#go').click({timeout:60000});
 const wait=(fn,arg)=>p.waitForFunction(fn,arg,{timeout:30000}),debug=command=>p.evaluate(command=>Online.send({type:'debug',command}),command);
 await wait(()=>Online.connected&&Field.hero.hp>0);
 for(const [season,unix]of (process.env.CHECK_ONLY==='phone'?[seasons[5]]:seasons)){
  await debug({op:'season_time',unix});await wait(id=>Seasonal.isActive(id),season);
  await p.evaluate(()=>{City.close();Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone:0,x:33.8,y:83}});});
  await wait(()=>Field.zone===0&&Math.hypot(Field.hero.nx-33.8,Field.hero.ny-83)<.2);await p.waitForTimeout(200);await p.evaluate(()=>ZoneJourney.clear());
  const id=`festival_dance_${season}_0`;
  check(await p.evaluate(id=>City.npcs.some(n=>n.id===id)&&Festival.objects(0).length===1,id),`${season}: only its own dance centerpiece is visible`);
  await p.evaluate(id=>Field.visitNpc(id),id);await p.locator('[data-offer="festival:dance"]').waitFor({state:'visible'});await p.locator('[data-offer="festival:dance"]').click();await wait(()=>!!__self().festivalDance);
  check(await p.locator('#festival-dance-progress').isVisible(),`${season}: clicking the real offer starts visible lap progress`);
  const start=await p.evaluate(()=>({x:__self().x,y:__self().y,until:__self().festivalBuff.until}));
  await wait(()=>__self().festivalDance?.laps>.45);check(await p.evaluate(s=>Math.hypot(__self().x-s.x,__self().y-s.y)>1&&__self().festivalBuff.until===s.until,start),`${season}: real server movement precedes any new buff grant`);
  check(await p.evaluate(()=>{const b=document.querySelector('#festival-dance-progress button'),r=b.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return hit===b||b.contains(hit);}),'The dance cancel control paints above other HUD panels');
  await p.screenshot({path:path.join(w.runDir,`festival-${season}-dancing.png`)});
  await wait(()=>__self().festivalDance===null&&__self().festivalBuff.left>=7190);
  check(await p.evaluate(id=>__self().festivalBuff.season===id&&__self().festivalBuff.left<=7200,season),`${season}: two full circuits earn or refresh exactly one two-hour buff`);
  const chip=p.locator('[data-buff="festivalspirit"]');await chip.waitFor({state:'visible'});await chip.click();
  check((await chip.locator('.festival-buff-detail').textContent()).includes('+10% attack and +50% experience'),`${season}: touch tooltip gives both exact bonuses`);
  await p.screenshot({path:path.join(w.runDir,`festival-${season}-buff.png`)});await chip.click();
 }
 // Cancellation uses the real progress control, and cannot refresh the earned buff.
 const before=await p.evaluate(()=>__self().festivalBuff.until);
 await p.evaluate(()=>{City.close();Online.send({type:'debug',command:{op:'teleport',zone:0,x:33.8,y:83}});});await p.waitForTimeout(500);await p.evaluate(()=>Field.visitNpc('festival_dance_solstice_0'));await p.locator('[data-offer="festival:dance"]').click();await wait(()=>!!__self().festivalDance);
 await p.locator('#festival-dance-progress button').click();await wait(()=>__self().festivalDance===null);check(await p.evaluate(t=>__self().festivalBuff.until===t,before),'Cancelling a partial dance does not refresh or remove the earned buff');
 const identity=await p.evaluate(()=>Online.id);await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();await wait(()=>Online.connected&&__self());check(await p.evaluate(([id,t])=>Online.id===id&&__self().festivalBuff.until===t&&__self().festivalDance===null,[identity,before]),'Reconnect preserves expiry and never resumes a partial dance');
 await p.evaluate(()=>{const s=JSON.parse(localStorage.getItem('valhallasc.save.v1'));s.lang='sv';localStorage.setItem('valhallasc.save.v1',JSON.stringify(s));});await p.reload();await p.locator('#start').click();await p.locator('#login-guest').click();await wait(()=>Online.connected&&__self());await p.setViewportSize({width:844,height:390});
 const chip=p.locator('[data-buff="festivalspirit"]');await chip.click();check((await chip.locator('.festival-buff-detail').textContent()).includes('+10 % attack och +50 % erfarenhet'),'Swedish phone shows both buff bonuses');const box=await chip.locator('.festival-buff-detail').boundingBox();check(box.x>=0&&box.x+box.width<=844&&box.y>=0&&box.y+box.height<=390,'Tap tooltip fits the phone viewport');check(await p.evaluate(()=>{const d=document.querySelector('.festival-buff-detail:not([hidden])'),r=d.getBoundingClientRect();return [0.2,0.5,0.8].every(y=>{const hit=document.elementFromPoint(r.x+r.width*.5,r.y+r.height*y);return hit===d||d.contains(hit);});}),'The phone buff explanation paints above the quest tracker');await p.evaluate(()=>document.getElementById('dps-close')?.click());await p.screenshot({path:path.join(w.runDir,'festival-buff-swedish-phone.png')});
 if(process.env.CAPTURE_ALL==='1'){
  await p.setViewportSize({width:1280,height:800});
  for(const[season,unix]of seasons){
   await debug({op:'season_time',unix});await wait(id=>Seasonal.isActive(id),season);
   await p.evaluate(()=>{City.close();Field.clearInput();Online.send({type:'stop'});Online.send({type:'debug',command:{op:'teleport',zone:0,x:33.8,y:83}});Online.send({type:'debug',command:{op:'set_time',hour:12,freeze:true}});});await wait(()=>Math.hypot(__self().x-33.8,__self().y-83)<.2);await p.evaluate(()=>ZoneJourney.clear());
   await p.evaluate(id=>Online.send({type:'interact',npc:id,offer:'festival:dance'}),`festival_dance_${season}_0`);await wait(()=>__self().festivalDance?.laps>.45);
   await p.screenshot({path:path.join(w.runDir,`festival-${season}-dancing.png`)});await p.locator('#festival-dance-progress button').click();await wait(()=>__self().festivalDance===null);
   const b=p.locator('[data-buff="festivalspirit"]');if(await b.getAttribute('aria-expanded')!=='true')await b.click();await p.screenshot({path:path.join(w.runDir,`festival-${season}-buff.png`)});await b.click();
  }
 }
 check(errors.length===0,'No browser errors: '+errors.join('; '));fs.writeFileSync(path.join(w.runDir,'summary.json'),JSON.stringify({checks,errors},null,2));console.log(`festival-ui: ${checks} checks; ${w.runDir}`);
}finally{await browser?.close();await w.stop();}})().catch(e=>{console.error(e);process.exitCode=1;});
