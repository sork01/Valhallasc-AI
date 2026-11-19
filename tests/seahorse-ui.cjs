// Focused private quest/mount picker and real seahorse rendering. Run only on an approved browser host.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const w=new TestWorld();let browser;
(async()=>{
 await w.start();browser=await chromium.launch({headless:true,args:['--disable-gpu']});
 const page=await browser.newPage({viewport:{width:900,height:600}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
 if(process.env.MUTATE==='picker') await page.route('**/mounts.js',route=>{const source=fs.readFileSync(path.join(__dirname,'../client/mounts.js'),'utf8');assert(source.includes("{id:'seahorse'"));return route.fulfill({contentType:'text/javascript',body:source.replace(/    \{id:'seahorse'.*\n/,'')});});
 await page.goto(w.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-warrior').click();await page.locator('#name').fill('SeahorseRider');await page.locator('#go').click({timeout:90000});
 await page.waitForFunction(()=>Online.connected&&Field.hero.id,null,{timeout:90000});
 await page.evaluate(()=>{Online.send({type:'debug',ref:1,command:{op:'set_level',level:35}});Online.send({type:'debug',ref:2,command:{op:'give_mount',mount:'seahorse'}});Online.send({type:'debug',ref:3,command:{op:'teleport',zone:8,x:100,y:200}});});
 await page.waitForFunction(()=>Field.zone===8&&Field.hero.mounts?.includes('seahorse'));
 await page.evaluate(()=>Online.send({type:'select_mount',mount:'seahorse'}));
 await page.waitForFunction(()=>Field.hero.mount==='seahorse');
 await page.evaluate(()=>Online.send({type:'mount',mounted:true}));
 await page.waitForFunction(()=>Field.hero.mounted&&MountArt.ready('seahorse'));
 await page.waitForFunction(()=>document.getElementById('connection-overlay')?.hidden!==false);
 await page.screenshot({path:path.join(w.runDir,'seahorse-world.png')});
 const card=page.locator('.mount-card[data-mount="seahorse"]');
 await page.keyboard.press('e');await page.locator('#character-tab-mounts').click();await card.scrollIntoViewIfNeeded();
 assert.equal(await card.count(),1);assert((await card.textContent()).includes('Underwater only'));
 const meta=await page.evaluate(()=>MountArt.meta('seahorse'));assert.equal(Object.keys(meta.sprites).length,16);
 const quest=await page.evaluate(()=>WORLD_MAP.zones[7].quests.find(q=>q.id==='deep_seahorse'));
 assert.equal(quest.npc,'deep_healer');assert.equal(quest.rewardMount,'seahorse');assert.equal(quest.objectives.length,2);
 const hashes=await page.evaluate(async()=>{
  const sprite=await WarriorSprite.load({gender:'male'}),out=[];
  for(let d=0;d<8;d++){
   const c=document.createElement('canvas');c.width=220;c.height=260;const g=c.getContext('2d');g.translate(110,195);
   const a=-d*Math.PI/4;sprite.draw(g,{mounted:true,mount:'seahorse',moving:true,walk:3,fx:(Math.cos(a)+Math.sin(a))/2,fy:(Math.cos(a)-Math.sin(a))/2,x:0,y:0},1,1.3);
   out.push(Array.from(g.getImageData(0,0,220,260).data).reduce((h,v)=>(h*31+v)>>>0,7));
  }return out;
 });assert.equal(new Set(hashes).size,8);
 const shot=path.join(w.runDir,'seahorse.png');await page.screenshot({path:shot});
 assert.deepEqual(errors,[]);console.log('Seahorse browser: private mount, picker hint and eight real rider facings pass; screenshot',shot);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await w.stop();});
