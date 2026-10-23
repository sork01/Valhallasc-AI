// RAID-PACKS only: real-client dungeon elites, original art and shared loot.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..'),client=new Client({name:'raid-packs-ui',version:'1'});
let browser,world,checks=0;
const check=(v,t)=>{assert.ok(v,t);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
 await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...process.env}}));
 world=await call('start_world',{startLevel:99,levelSpread:0,godMode:true});
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 const errors=[],bad=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400&&/cf_|cfpack|cathedral\.txt/.test(r.url()))bad.push(r.url());});
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#name').fill('Pack Artist');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
 await debug({op:'teleport',zone:46,x:145,y:271});
 await page.waitForFunction(()=>Field.zone===46&&Field.slimes.length>=40,null,{timeout:30000});
 check(await page.evaluate(()=>WORLD_MAP.zones[45].slimes.filter(s=>['cf_brute','cf_crawler','cf_caster','cf_sentry'].includes(s.kind)).length===40&&WORLD_MAP.zones[45].quests.length===0),'Forty pack elites, no side elites or quests');
 check(await page.evaluate(()=>Field.slimes.every(s=>s.elite)),'Every pack actor has an elite nameplate');
 check(await page.evaluate(()=>WORLD_MAP.zones[45].sealedTemplate),'Entrance remains sealed');
 if(!STUB)await page.waitForFunction(()=>Field.cathedralSprites?.meta.kinds.filter(k=>['cf_brute','cf_crawler','cf_caster','cf_sentry'].includes(k)).length===4,null,{timeout:60000});
 for(const kind of ['cf_brute','cf_crawler','cf_caster','cf_sentry']){
  const art=await page.evaluate(kind=>{
   const s=Field.slimes.find(s=>s.kind===kind),f=Field._debug.enemyFrame(s);
   return {elite:s.elite,frame:!!f[0],name:Field.enemyName(kind),top:Field.cathedralSprites?.meta.tops[kind],
    width:Field.cathedralSprites?.img[kind]?.naturalWidth,editable:!!Field.cathedralSprites?.meta.sprites[kind]};
  },kind);
  check(art.elite&&art.frame&&art.name!==kind,kind+' uses its named elite renderer');
  if(!STUB)check(art.width===768&&art.top>25&&art.editable,kind+' has original fitted PixelFlow art');
 }
 await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('area-title')).opacity)<.05);
 // Compare the actual scene with one selected pack actor hidden. Reduced
 // motion and two synchronous draw calls keep the comparison about that actor.
 const pixels=await page.evaluate(()=>{
  const cv=document.getElementById('fieldcv'),g=cv.getContext('2d'),actors=Field.slimes;
  const actor=actors.find(s=>s.kind==='cf_sentry'&&!s.dead&&Math.hypot(s.x-145,s.y-277)<18);
  if(!actor)throw Error('nearby sentry');
  const t=performance.now()/1000;Field._debug.drawFrame(t);const a=g.getImageData(0,0,cv.width,cv.height).data;
  const dead=actor.dead;actor.dead=true;const state=actor.state;actor.state='waiting';
  Field._debug.drawFrame(t);const b=g.getImageData(0,0,cv.width,cv.height).data;
  actor.dead=dead;actor.state=state;Field._debug.drawFrame(t);
  let n=0;for(let i=0;i<a.length;i+=4)if(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>30)n++;
  return n;
 });check(pixels>250,'An elite sprite visibly changes the actual scene: '+pixels+' pixels');
 await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,'raid-pack-desktop.png')});
 await page.setViewportSize({width:844,height:390});await page.waitForTimeout(300);
 await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,'raid-pack-mobile.png')});
 check(!await page.locator('.rotate').isVisible(),'Landscape touch view renders the pack');
 const icons=await page.evaluate(async()=>{
  const items=WORLD_ITEMS.filter(i=>i.source==='chained_forge_packs'),im=new Image();im.src='assets/items.png';await im.decode();
  const cv=document.createElement('canvas');cv.width=48;cv.height=48;const g=cv.getContext('2d');
  return items.map(i=>{const cell=ITEM_ICONS.at[i.id];if(!cell)return false;g.clearRect(0,0,48,48);g.drawImage(im,cell[0]*48,cell[1]*48,48,48,0,0,48,48);
   return !i.class&&i.rarity==='epic'&&i.requiredLevel===99&&g.getImageData(0,0,48,48).data.some((v,n)=>n%4===3&&v);});
 });check(icons.length===3&&icons.every(Boolean),'Three unique shared purple items have visible inventory icons');
 const sw=await browser.newPage();await sw.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sw.goto(world.url);
 check(await sw.evaluate(()=>Locale.translate('Slaghammer Brute')==='Slägghuggare'&&Locale.translate('Cinderwork Clamp Ring')==='Glödsmedens klämring'),'Hand-written Swedish names');await sw.close();
 check(errors.length===0,JSON.stringify(errors));check(bad.length===0,'No missing new art');
 fs.writeFileSync(path.join(world.artifacts,'raid-packs-ui.txt'),JSON.stringify({checks,real:!STUB,pixels,errors,bad},null,2));
 console.log(JSON.stringify({passed:true,checks,artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close();if(world)try{await call('stop_world');}catch{}await client.close();
});
