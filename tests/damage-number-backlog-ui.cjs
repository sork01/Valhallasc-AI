// Combat text on the real field clock, including a paused frame and a critical hit.
const assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
const {TestWorld}=require('../scripts/testing/driver.cjs'),{chromium}=require('./lib/playwright.cjs');
const {requireMemoryLimit}=require('./lib/touch.cjs');
let browser;const world=new TestWorld();
(async()=>{
 requireMemoryLimit();world.godMode=true;await world.start();browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:844,height:390},reducedMotion:'no-preference'});
 if(process.env.MUTATE){/* the old backlog: the numbers age by one clamped frame step (0.05 s), not by the real elapsed time */const src=require('fs').readFileSync(path.resolve(__dirname,'../client/field.js'),'utf8');const from='floaters = DamageNumbers.step(floaters, textDt);';assert.ok(src.includes(from),'mutation anchor present');await page.route('**/field.js',r=>r.fulfill({contentType:'text/javascript',body:src.replace(from,'floaters = DamageNumbers.step(floaters, dt);')}));}
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
  const time = performance.now() + 10000;
  window.__fieldFrame(time);
  const after = Field._debug.floaters.length;

  const {x, y} = Field.hero;
  Field._debug.event({kind: 'hit', crit: true, value: 8123, x, y, actor: Online.id});
  const crit = Field._debug.floaters.find(f => f.kind === 'crit');
  const frames = [];
  const proto = CanvasRenderingContext2D.prototype, fill = proto.fillText;
  proto.fillText = function (text, sx, sy) {
    if (text === '8,123') {
      const [ax, ay] = Field._debug.w2s(x, y, crit.head);
      frames.push({x: sx - ax, y: sy - ay, size: parseFloat(this.font), alpha: this.globalAlpha});
    }
    return fill.apply(this, arguments);
  };
  try {
    for (const ms of [90, 260, 1150, 1350, 1550]) window.__fieldFrame(time + ms);
  } finally {
    proto.fillText = fill;
  }
  return {before, after, frames};
 });
 assert.equal(result.before,1,'one fresh number exists before the paused frame');
 assert.equal(result.after,0,'ten real seconds without hits cannot leave old damage text waiting to appear');
 assert.equal(result.frames.length, 4, 'the crit is drawn through its fade and then expires');
 const [pop, settled, held, fading] = result.frames;
 assert.ok(pop.size > settled.size * 1.4, 'the actual crit briefly pops to a larger size');
 assert.ok(Math.abs(settled.x - held.x) < .01 && Math.abs(settled.y - held.y) < .01, 'the drawn crit holds its position');
 assert.equal(held.size, settled.size, 'the crit holds at its resting size');
 assert.equal(held.alpha, 1, 'the crit stays fully opaque through its hold');
 assert.ok(fading.alpha > 0 && fading.alpha < 1, 'the crit fades at the end');
 console.log('Damage numbers: the field expires old text and draws a quick pop, stationary hold and fade for crits');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
