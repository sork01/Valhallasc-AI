// Current-location markers on irregular province edges, using real private positions.
const path=require('node:path');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');require(path.join(root,'tests/lib/touch.cjs')).requireMemoryLimit();
const {chromium}=require(path.join(root,'tests/lib/playwright.cjs'));const {TestWorld}=require(path.join(root,'scripts/testing/driver.cjs'));
(async()=>{const world=new TestWorld();let browser;try{await world.start();browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1280,height:800},reducedMotion:'reduce'});
await page.addInitScript(()=>{window.__valhallaTestSprites=true;window.AudioContext=undefined;window.webkitAudioContext=undefined;localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null}));});
await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('AtlasDot');await page.locator('#go').click({timeout:60000});await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0);
await page.evaluate(()=>Online.send({type:'debug',command:{op:'explore_all'}}));await page.waitForFunction(()=>Field.explored?.[46]===511);
for(const zone of [0,6,19,23]){
const p=await page.evaluate(zone=>[WORLD_MAP,...WORLD_MAP.zones][zone].portals.find(p=>p.walk),zone);
await page.evaluate(([zone,p])=>Online.send({type:'debug',command:{op:'teleport',zone,x:p.x,y:p.y}}),[zone,p]);await page.waitForFunction(zone=>Field.zone===zone,zone);await page.evaluate(()=>WorldMap.show());
await page.waitForFunction(zone=>document.querySelector(`.wm-tile[data-zone="${zone}"]`)?.dataset.here==='true',zone);
const good=await page.evaluate(zone=>{const stage=document.querySelector('#wm-world').getBoundingClientRect(),dot=document.querySelector(`.wm-tile[data-zone="${zone}"] .wm-you`),b=dot.getBoundingClientRect(),x=((b.left+b.right)/2-stage.left)/stage.width*WORLD_MAP.atlas.width,y=((b.top+b.bottom)/2-stage.top)/stage.height*WORLD_MAP.atlas.height,poly=WORLD_MAP.atlas.regions.find(r=>r.zone===zone).polygon;let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])inside=!inside;}return !dot.hidden&&inside;},zone);assert.ok(good,`Current-location marker remains inside province ${zone}`);await page.locator('#wm-close').click();}
console.log('4 current-location marker checks passed');}finally{await browser?.close();await world.stop();}})().catch(e=>{console.error(e);process.exitCode=1});
