// Private live-browser check and real captures of Veyrroot outside and inside its tree.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-worldheart-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:80,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const capture=async name=>{const png=await page.evaluate(()=>document.querySelector('#fieldcv').toDataURL('image/png'));fs.writeFileSync(path.join(world.artifacts,name),Buffer.from(png.split(',')[1],'base64'));};
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('VeyrrootUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.worldheartSprites?.img.heart_oracle,null,{timeout:60000});
  const data=await page.evaluate(()=>{const zones=Field._debug.zones,a=zones[23],b=zones[24],src=Field.worldheartSprites;return {count:zones.length,outer:a.name,inner:b.name,themes:[a.theme,b.theme],levels:[a.levels,b.levels],npcs:[a.npcs.length,b.npcs.length],quests:[a.quests.length,b.quests.length],enemies:a.slimes.length,seal:b.futureInstance,gates:[zones[22].portals.find(p=>p.id==='tangle_worldheart_gate'),a.portals.find(p=>p.id==='canopy_hollow_gate'),b.portals.find(p=>p.id==='hollow_canopy_gate')],kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),art:['worldheart_trunk','hollow_arch','heartwood_core','heartwood_vault'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,travel:a.npcs.find(n=>n.id==='travel_veyrroot')};});
  check(data.count===27&&data.outer==='Veyrroot Canopy'&&data.inner==='Veyrroot Heartwood'&&data.themes.join(',')==='worldtree,heartwood','Outside and inside city maps load');
  check(data.levels.every(v=>v.join(',')==='80,80')&&data.enemies===0,'Level-80 canopy city has no enemies');
  check(data.npcs[0]===8&&data.npcs[1]===4&&data.quests.join(',')==='7,2','City NPCs and quests load on both floors');
  check(data.kinds.length===8&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Eight PixelFlow atlases load');
  check(data.art&&data.layout===29,'Living-tree art and world-map placements load');
  check(data.gates.every(Boolean)&&data.gates[0].to===23&&data.gates[1].to===24&&data.gates[2].to===23,'Jungle, canopy and hollow gates load');
  check(data.travel?.travelLinks.includes('travel_banyan')&&data.travel?.art==='heart_travel','Travel Master Lio has unique art and return service');
  check(data.seal?.status==='sealed'&&data.seal?.name==='The Seed Vault','Heartwood instance entrance is sealed');
  let ref=501;const debug=async command=>check(await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,ref++]),`Send ${command.op}`);
  async function stage(zone,x,y,label){await debug({op:'teleport',zone,x,y});await page.waitForFunction(([zone,x,y])=>Field.zone===zone&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<3,[zone,x,y],{timeout:15000});await page.waitForTimeout(950);await page.screenshot({path:path.join(world.artifacts,`worldheart-${label}.png`)});await capture(`worldheart-${label}-clean.png`);}
  await stage(23,55,88,'market');
  check(await page.evaluate(()=>Field.zoneTheme==='worldtree'&&City.npcs.length===8),'Open-air canopy market paints live');
  await stage(23,56,39,'great-tree');
  await stage(24,48,52,'heartwood');
  check(await page.evaluate(()=>Field.zoneTheme==='heartwood'&&City.npcs.length===4),'Hollow heartwood paints live');
  await stage(24,48,10,'seed-vault');
  check(await page.evaluate(()=>Field._debug.zones[24].portals.length===1&&Field.zone===24),'Seed Vault has no playable dungeon portal');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Worldheart UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
