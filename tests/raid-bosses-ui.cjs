// Only the first three Wardens: ten real clients, authoritative role packets,
// PixelFlow artwork, readable signs and paired rendered-pixel assertions.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const root=path.resolve(__dirname,'..'),world=new TestWorld();
const data=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'))).zones[45];
const defs=JSON.parse(fs.readFileSync(path.join(root,'world/boss-mechanics.txt')));
let browser,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
(async()=>{
 world.godMode=true;world.levelSpread=0;world.startLevel=99;await world.start();
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#name').fill('Warden Watcher');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const leader=await page.evaluate(()=>Online.id);
 const send=action=>page.evaluate(a=>Online.send(a),action);
 const debug=command=>send({type:'debug',command});
 const names=Array.from({length:9},(_,i)=>'Warden'+(i+1)),classes=['warrior','mage','assassin','priest','hunter'];
 for(const [i,bot]of names.entries()){
  await world.connect({bot,class:classes[i%5]});
  await send({type:'social',command:{op:'party_invite',name:bot}});
  await world.waitFor(()=>world.bots.get(bot).social?.incoming.some(i=>i.id===leader),10000,'Invitation '+bot);
  await world.social(bot,{op:'party_accept',id:leader});
  if(i===0){await send({type:'social',command:{op:'party_raid',on:true}});await page.waitForFunction(()=>Social.state.party?.raid);}
 }
 await page.waitForFunction(()=>Social.state.party?.members.length===10);
 check(true,'Ten real fighters share a raid');
 if(process.env.MUTATE_FLOOR)await page.evaluate(()=>{BossMech.drawFloor=()=>{};});
 const idToBot=new Map(names.map(n=>[world.bots.get(n).id,n]));
 const teleport=async(id,x,y)=>{
  if(id===leader){await debug({op:'teleport',zone:46,x,y});return;}
  await world.debug(idToBot.get(id),{op:'teleport',zone:46,x,y});
 };
 const stage=async(x,y)=>{
  await debug({op:'teleport',zone:46,x,y});
  await page.waitForFunction(()=>Field.zone===46);
  await Promise.all(names.map(bot=>world.debug(bot,{op:'teleport',zone:46,x,y:y+1})));
  await page.waitForFunction(()=>Field.remotePlayers.length===9);
 };
 const report=[];
 for(const h of data.forgeHalls.slice(0,3)){
  await stage(h.x,h.y+2);
  await page.waitForFunction(kind=>BossMech.fights.some(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===kind&&f.cast),h.boss,{timeout:25000});
  const state=await page.evaluate(kind=>BossMech.fights.find(f=>Field.slimes.find(s=>s.id===f.boss)?.kind===kind),h.boss);
  check(state.cast.total>=5,h.boss+' has the complete lethal warning');
  const stations=state.tele.filter(t=>t.players&&!t.chain);
  check(new Set(stations.flatMap(t=>t.players)).size===10,h.boss+' assigns every real fighter');
  check(stations.every(t=>t.tele==='blue'&&t.shapes[0].t==='circle'),h.boss+' shows blue group stations');
  if(h.boss==='cf_kettil')check(state.tele.filter(t=>t.chain).length===5,'Five actual partner lines');
  if(h.boss==='cf_ysolt')check(state.tele.some(t=>t.arrow)&&stations.every(t=>t.capacity===3),'Wind arrow and four bounded posts');
  if(h.boss==='cf_hallgrim')check(stations.length===3&&stations.every(t=>t.need===3),'Three counted anvils');
  for(const t of stations){
   const s=t.shapes[0];await Promise.all(t.players.map((id,i)=>teleport(id,s.x+(i-1)*.35,s.y+.2)));
  }
  await page.waitForTimeout(250);
  // The same renderer at the same time, with only the boss telegraph layer changed.
  const pixels=await page.evaluate(()=>{
   const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),saved=BossMech.fights,t=performance.now()/1000,hud=BossMech.drawHud;
   BossMech.drawHud=()=>{};
   Field._debug.drawFrame(t);const a=g.getImageData(0,0,cv.width,cv.height).data;
   BossMech.update([]);Field._debug.drawFrame(t);const b=g.getImageData(0,0,cv.width,cv.height).data;
   BossMech.update(saved);BossMech.drawHud=hud;Field._debug.drawFrame(t);
   let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>35)n++;
   return n;
  });check(pixels>300,h.boss+' telegraph changes the real scene ('+pixels+' pixels)');
  if(!STUB){
   await page.waitForFunction(k=>Field.cathedralSprites?.img[k]?.complete,h.boss,{timeout:60000});
   const art=await page.evaluate(k=>({id:Field.cathedralSprites.meta.sprites[k],width:Field.cathedralSprites.img[k].naturalWidth,name:Field.enemyName(k)}),h.boss);
   check(art.id&&art.width===768&&!art.name.startsWith('cf_'),h.boss+' has its own editable named atlas');
  }
  await page.screenshot({path:path.join(world.runDir,h.boss+'-cast-desktop.png')});
  await page.setViewportSize({width:844,height:390});await page.waitForTimeout(180);
  await page.screenshot({path:path.join(world.runDir,h.boss+'-cast-phone.png')});
  check(await page.evaluate(()=>BossMech.fights.some(f=>f.cast)),'Cast remains visible at phone width');
  await page.setViewportSize({width:1440,height:900});
  if(h.boss==='cf_kettil'){
   await page.waitForFunction(()=>BossMech.fights.some(f=>f.banner?.startsWith('Chains tight')),null,{timeout:12000});
   await page.screenshot({path:path.join(world.runDir,h.boss+'-heave.png')});
   check(true,'Standing leash has its own active-phase banner');
  }
  report.push({kind:h.boss,pixels,stations:stations.length,cast:state.cast});
  console.log(h.boss+': cast, assignments, original art and paired pixels passed');
  // Read the server-owned sign from its actual approach. This also clears the pull.
  const signs=await page.evaluate(()=>Field.signs||[]);
  const sign=signs.find(s=>s.id===h.boss);
  check(!!sign,h.boss+' has a sign in this copy');
  await debug({op:'teleport',zone:46,x:sign.x,y:sign.y});await page.waitForTimeout(200);
  await send({type:'sign_read',sign:h.boss});
  await page.locator('#sign-panel').waitFor({state:'visible'});
  check((await page.locator('#sign-panel').textContent()).includes(h.boss==='cf_kettil'?'chain':h.boss==='cf_ysolt'?'wind':'anvil'),h.boss+' sign explains its actual mechanic');
  await page.screenshot({path:path.join(world.runDir,h.boss+'-sign.png')});await page.keyboard.press('Escape');
 }
 check(await page.evaluate(()=>!WORLD_MAP.zones[45].sealedTemplate),'Raid entrance is open');
 const sw=await browser.newPage();await sw.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sw.goto(world.url);
 check(await sw.evaluate(()=>Locale.translate('Taut Chain')==='Sträckt kedja'&&Locale.translate('Gale of the Bellows')==='Bälgens stormvind'&&Locale.translate('Hammerfall')==='Hammarslag'),'Hand-written Swedish ability names');await sw.close();
 check(errors.length===0,JSON.stringify(errors));
 fs.writeFileSync(path.join(world.runDir,'raid-bosses-ui.txt'),JSON.stringify({checks,real:!STUB,report,errors},null,2));
 console.log(JSON.stringify({passed:true,checks,artifacts:world.runDir}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{await browser?.close();await world.stop();});
