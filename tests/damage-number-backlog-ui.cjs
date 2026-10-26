// Only delayed combat text: real field animation clock after a paused frame.
const assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const {TestWorld}=require('../scripts/testing/driver.cjs'),{chromium}=require('./lib/playwright.cjs');
const {requireMemoryLimit}=require('./lib/touch.cjs');
let browser;const world=new TestWorld();
(async()=>{
 requireMemoryLimit();world.godMode=true;await world.start();browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:844,height:390},reducedMotion:'reduce'});
 if(process.env.MUTATE)await page.route('**/field.js',r=>r.fulfill({contentType:'text/javascript',body:execFileSync('git',['show','HEAD:client/field.js'],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'})}));
 await page.addInitScript(()=>{
  window.AudioContext=window.webkitAudioContext=undefined;
  localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,lowGraphics:true,lowGraphicsSet:true}));
  const raf=requestAnimationFrame;
  window.requestAnimationFrame=function(cb){if(cb.name==='loop'){window.__fieldFrame=cb;if(window.__pauseField)return 0;}return raf(cb);};
 });
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#name').fill('Text Clock');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero&&window.__fieldFrame);
 await page.evaluate(()=>window.__pauseField=true);await page.waitForTimeout(120);
 const result=await page.evaluate(()=>{
  const list=Field._debug.floaters;list.splice(0);
  DamageNumbers.spawn(list,{x:Field.hero.x,y:Field.hero.y,text:'9876',kind:'hit',head:118});
  const before=list.length;
  window.__fieldFrame(performance.now()+10000);
  return {before,after:Field._debug.floaters.length};
 });
 assert.equal(result.before,1,'one fresh number exists before the paused frame');
 assert.equal(result.after,0,'ten real seconds without hits cannot leave old damage text waiting to appear');
 console.log('Damage-number backlog: real field expires old text after a paused frame');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
