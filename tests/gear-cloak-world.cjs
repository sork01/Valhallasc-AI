// Private-world equip, vendor, movement and mobile equipment checks; no grinding.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const root=path.resolve(__dirname,'..'),out=path.join(root,'test-results/cloaks');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const world=new TestWorld();world.startLevel=50;world.godMode=true;world.levelSpread=0;
 let browser;
 try{
  await world.start();browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#cls-mage').click();await page.locator('#gender-female').click();await page.locator('#name').fill('CloakCheck');await page.locator('#go').click({timeout:90000});
  // Inspect the portrait panel under the game's existing rotate-device curtain, only in this private test.
  await page.addStyleTag({content:'.rotate {display:none!important}'});
  await page.waitForFunction(()=>Online.connected&&Field.mageSprites&&Field.hero?.look.gender==='female',null,{timeout:90000});
  assert.equal(await page.evaluate(()=>Field.hero.look.cloak),'none','new characters have no starter cloak');
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:Math.floor(Math.random()*1e9),command}),command);
  await debug({op:'teleport',zone:0,x:9,y:9});await debug({op:'give_item',item:'cloak_l50_rare',quantity:1});
  await page.waitForFunction(()=>Inventory.quantity('cloak_l50_rare')===1);
  await page.keyboard.press('e');await page.locator('#field-cloak').selectOption('cloak_l50_rare');
  await page.waitForFunction(()=>Field.hero.look.cloak==='cloak_l50_rare'&&Field.mageSprites.look.cloak==='cloak_l50_rare');
  await page.evaluate(async()=>{await Field.mageSprites.source.ensure('cloak_mantle');Field.mageSprites.cache.clear();});
  const equipped=await page.evaluate(()=>({hp:Field.hero.maxHp,look:Field.hero.look,frame:Field.mageSprites.frame('idle',4,0).toDataURL()}));
  await page.locator('#field-cloak').selectOption('none');await page.waitForFunction(()=>Field.hero.look.cloak==='none');
  const bare=await page.evaluate(()=>Field.mageSprites.frame('idle',4,0).toDataURL());assert.notEqual(equipped.frame,bare,'equipping changes real worn pixels');
  await page.locator('#field-cloak').selectOption('cloak_l50_rare');await page.waitForFunction(()=>Field.hero.look.cloak==='cloak_l50_rare');
  assert.equal(await page.locator('#equipped-slots .equipped-slot').count(),10);assert.equal(await page.locator('[data-slot="cloak"] [data-icon="cloak_l50_rare"]').count(),1);
  for(const size of [{width:1440,height:900},{width:390,height:844}]){
   await page.setViewportSize(size);await page.screenshot({path:path.join(out,`private-equipment-${size.width}.png`)});
   const fits=await page.locator('[data-slot="cloak"] .gear-icon').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;});assert.ok(fits,`cloak slot fits at ${size.width}`);
  }
  await page.setViewportSize({width:1440,height:900});await page.locator('#equipment-close').click();await page.locator('#equipment').waitFor({state:'hidden'});
  const start=await page.evaluate(()=>({x:Field.hero.x,y:Field.hero.y}));await page.keyboard.down('ArrowRight');await page.waitForTimeout(700);await page.keyboard.up('ArrowRight');await page.waitForTimeout(150);
  const moved=await page.evaluate(()=>({x:Field.hero.x,y:Field.hero.y,cloak:Field.hero.look.cloak}));
  assert.ok(Math.hypot(moved.x-start.x,moved.y-start.y)>.5,'the equipped wearer really moves');assert.equal(moved.cloak,'cloak_l50_rare');
  await debug({op:'set_gold',gold:100000});const smith=await page.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='smith'));
  await debug({op:'teleport',zone:0,x:smith.x,y:smith.y-1});await page.waitForTimeout(300);
  await page.evaluate(()=>Online.send({type:'interact',npc:'smith'}));await page.locator('[data-offer="buy_cloak_uncommon"]').click();
  await page.waitForFunction(()=>Inventory.quantity('cloak_l50_uncommon')===1);assert.ok(await page.evaluate(()=>Field.hero.gold<100000),'vendor charges for the level-appropriate cloak');
  await page.locator('#npc-x').click();await page.screenshot({path:path.join(out,'private-equipped-world.png')});
  assert.deepEqual(errors,[]);console.log('PASS: female Mage, real worn art, equipment, movement, tiered vendor and mobile window in a private world');
 }finally{await browser?.close();await world.stop();}
})().catch(e=>{console.error(e);process.exitCode=1;});
