// Private browser: live colorful zone, exported PixelFlow atlases and open pavilion.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
// map data: the Ribbonwild is zone 21 (zones[20]); counts come from world/map.txt, not from older runs
const MAP=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'),'utf8')).zones[20];
const client=new Client({name:'valhallasc-ribbonwild-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:75,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const capture=async name=>{const png=await page.evaluate(()=>document.querySelector('#fieldcv').toDataURL('image/png'));fs.writeFileSync(path.join(world.artifacts,name),Buffer.from(png.split(',')[1],'base64'));};
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('RibbonwildUI');await page.locator('#go').click({timeout:60000});
  // a new hero starts on the Greenmeadow pier; this zone's sprites load only once the hero is in zone 21, so teleport first
  await page.waitForFunction(()=>Online.connected&&Field.hero?.hp>0,null,{timeout:60000});
  await page.evaluate(()=>Online.send({type:'debug',ref:400,command:{op:'teleport',zone:21,x:195,y:190}}));
  await page.waitForFunction(()=>Field.zone===21&&Math.hypot(Field.hero.nx-195,Field.hero.ny-190)<2,null,{timeout:20000});
  await page.waitForFunction(()=>!!Field.ribbonwildSprites?.img.maskcolossus,null,{timeout:60000});
  const data=await page.evaluate(()=>{const zones=Field._debug.zones,z=zones[21],src=Field.ribbonwildSprites;return {count:zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,npcs:z.npcs.length,spawns:z.slimes.length,kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>{const f=Field.frameOf(src,k);return [src.img[k].naturalWidth,src.img[k].naturalHeight,f.w*8,f.h*5];}),art:['pinwheel','fan_topiary','festival_bloom','silk_pavilion','grand_pavilion_gate'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,seal:z.futureInstance,gate:zones[20].portals.find(p=>p.id==='sun_ribbon_gate'),travel:z.npcs.find(n=>n.id==='travel_jubilee'),host:z.npcs.find(n=>n.id==='ribbon_host'),keeper:z.npcs.find(n=>n.id==='ribbon_keeper')};});
  check(data.count>21&&data.name===MAP.name&&data.theme==='ribbonwild'&&data.levels.join(',')===MAP.levels.join(','),'Level 70–75 zone loads');
  check(data.kinds.length===9&&(STUB||data.sizes.every(([w,h,ew,eh])=>w===ew&&h===eh)),'Nine PixelFlow atlases load');
  check(data.art&&data.layout>=30,'Festival art and world map load');
  check(data.npcs===MAP.npcs.length&&data.quests===MAP.quests.length&&data.spawns===MAP.slimes.length,'Quest hub and encounters load');
  check(data.seal?.status==='open'&&data.seal?.name==='The Thousandfold Pavilion'&&data.gate?.to===21,'Epic entrance is open and reachable');
  check(data.travel?.travelLinks.includes('travel_millbridge')&&data.travel?.art==='ribbon_travel'&&data.host?.art==='ribbon_host'&&data.keeper?.art==='ribbon_keeper','Three distinct NPC atlases load');
  let ref=401;const debug=async command=>check(await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,ref++]),`Send ${command.op}`);
  await page.waitForTimeout(1200);
  await page.screenshot({path:path.join(world.artifacts,'ribbonwild-hub.png')});await capture('ribbonwild-hub-clean.png');
  const HUB=['ribbon_host','ribbon_medic','ribbon_tailor','ribbon_keeper','ribbon_naturalist','ribbon_merchant','ribbon_stone','travel_jubilee'];
  check(await page.evaluate(ids=>Field.zoneTheme==='ribbonwild'&&ids.every(id=>City.npcs.some(n=>n.id===id)),HUB),'Jubilee Crossroads paints in live zone (its eight people are drawn)');
  await debug({op:'teleport',zone:21,x:293,y:192});
  await page.waitForFunction(()=>Field.zone===21&&Math.hypot(Field.hero.x-293,Field.hero.y-192)<2,null,{timeout:15000});
  await page.waitForTimeout(1500);
  await page.screenshot({path:path.join(world.artifacts,'ribbonwild-pavilion.png')});await capture('ribbonwild-pavilion-clean.png');
  check(await page.evaluate(()=>Field._debug.zones[21].portals.some(p=>p.to===31)&&Field.zone===21),'Pavilion has a playable portal');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Ribbonwild UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
