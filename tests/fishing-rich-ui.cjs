require('./lib/touch.cjs').requireMemoryLimit();
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs'),{frameJson}=require('./lib/frames.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),world=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))),w=new TestWorld();w.startLevel=99;
let browser,page,latest;const errors=[];
(async()=>{
 await w.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 page=await browser.newPage({viewport:{width:960,height:600},reducedMotion:'reduce'});
 page.on('pageerror',e=>errors.push(e.message));page.on('websocket',ws=>ws.on('framereceived',f=>{const p=frameJson(f.payload);if(p.type==='snapshot'||p.type==='welcome')latest=p.snapshot||p;}));
 if(process.env.MUTATE==='layer') {
  let field=fs.readFileSync(path.join(root,'client/field.js'),'utf8');
  const call='    drawFishing(g, true);      // rich markers must be above the painted water, below people';assert(field.includes(call));
  field=field.replace(call,'').replace('    City.drawPlaza(g, w2s);','    drawFishing(g, true);\n    City.drawPlaza(g, w2s);');
  await page.route('**/field.js',r=>r.fulfill({contentType:'application/javascript',body:field}));
 }
 if(process.env.MUTATE==='tooltip') {
  const source=fs.readFileSync(path.join(root,'client/fishing.js'),'utf8').replace('function drawRichTooltip(project, width, height) {','function drawRichTooltip(project, width, height) { return;');
  await page.route('**/fishing.js',r=>r.fulfill({contentType:'application/javascript',body:source}));
 }
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
 await page.goto(w.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('RichSpotCheck');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.warriorSprites);await page.locator('#connection-overlay').waitFor({state:'hidden'});
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
 await page.evaluate(()=>window.Tutorial?.disable?.());if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
 await debug({op:'give_item',item:'rod_twig_rod',quantity:1});await debug({op:'set_time',hour:12,freeze:true});await debug({op:'set_weather',kind:'clear'});
 await w.waitFor(()=>latest?.fishingSpots?.length);
 const active=latest.fishingSpots.map(p=>({...p,depth:Math.max(...world.objects.filter(o=>o.kind==='water').map(o=>o.r-Math.hypot(o.x-p.x,o.y-p.y)))})).sort((a,b)=>b.depth-a.depth)[0];
 assert(active.depth>1,'An active inland spot lies inside painted water');
 const candidate=world.fishingSpots.find(p=>Math.hypot(p.x-active.x,p.y-active.y)<.001);assert(candidate);
 await debug({op:'teleport',zone:0,...candidate.shore});await page.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.05,candidate.shore);
 await page.waitForTimeout(700);
 const pixels=await page.evaluate(point=>{
  const fishing=Fishing.drawFishing,clock=performance.now,frozen=clock.call(performance),cv=document.getElementById('fieldcv'),g=cv.getContext('2d');let hide=false,at;
  performance.now=()=>frozen;
  Fishing.drawFishing=function(ctx,project,width,height,ground,...args){if(ground)at={p:project(point.x,point.y),width,height};if(ground&&hide)return;return fishing.call(this,ctx,project,width,height,ground,...args);};
  try {
   Field._debug.drawFrame(1);
   const sample=off=>{hide=off;Field._debug.drawFrame(1);const x=Math.round(at.p[0]/at.width*cv.width),y=Math.round(at.p[1]/at.height*cv.height);return g.getImageData(x-12,y-12,24,24).data;};
   const a=sample(true),b=sample(false);let changed=0;for(let i=0;i<a.length;i+=4)if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])changed++;
   return {changed,at};
  }finally{Fishing.drawFishing=fishing;performance.now=clock;}
 },active);
 await page.screenshot({path:path.join(w.runDir,'rich-spot-water.png')});
 assert(pixels.changed>20,`Rich fish marker must remain visible above Greenmeadow water (${pixels.changed} changed pixels)`);
 const box=await page.locator('#fieldcv').boundingBox();
 await page.mouse.move(box.x+pixels.at.p[0]/pixels.at.width*box.width,box.y+pixels.at.p[1]/pixels.at.height*box.height);
 await page.locator('#rich-fishing-tooltip').waitFor({state:'visible',timeout:5000});
 assert((await page.locator('#rich-fishing-tooltip').innerText()).includes('5–10 fish'));
 await page.screenshot({path:path.join(w.runDir,'rich-spot-hover.png')});
 await page.evaluate(p=>{Field.clearInput();Field.setTouchDirection(p.facing.x-p.facing.y,p.facing.x+p.facing.y);},candidate);
 await page.waitForFunction(p=>Math.hypot(Field.hero.fx-p.facing.x,Field.hero.fy-p.facing.y)<.01,candidate,{timeout:5000});
 await page.evaluate(()=>{Field.clearInput();Online.send({type:'input',dx:0,dy:0});});await debug({op:'teleport',zone:0,...candidate.shore});
 await page.waitForFunction(p=>Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.05&&!Field.hero.moving,candidate.shore);
 await page.keyboard.press('r');await page.waitForFunction(()=>Fishing.richActive,null,{timeout:5000});
 await page.screenshot({path:path.join(w.runDir,'rich-spot-line.png')});
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({passed:true,changedPixels:pixels.changed,activeSpot:active,artifacts:w.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await w.stop();});
