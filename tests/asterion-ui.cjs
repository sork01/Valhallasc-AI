// Private Chromium check of Asterion's original architecture, distinct moving NPCs and Moonwell descent.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-asterion-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  transport.stderr?.on('data',chunk=>process.stderr.write(chunk));
  await client.connect(transport);
  const world=await call('start_world',{startLevel:60,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[],debugPackets=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('websocket',ws=>ws.on('framereceived',frame=>{try{const p=JSON.parse(frame.payload);if(p.type==='debug')debugPackets.push(p);}catch{}}));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('AsterionUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&Field.moonwellSprites?.img.moonwell_echo&&Field.moonwellGardenSprites?.img.moonskein_weaver,null,{timeout:60000});
  const data=await page.evaluate(()=>{
    const city=Field._debug.zones[17],well=Field._debug.zones[18],houses=city.objects.filter(o=>o.kind==='aetherhouse');
    return {zones:Field._debug.zones.length,city:city.name,theme:city.theme,size:city.size,
      houses:houses.length,labels:new Set(houses.map(o=>o.label)).size,npcs:city.npcs.length,
      walkers:city.npcs.filter(n=>n.route).length,looks:new Set(city.npcs.filter(n=>n.look?.prop).map(n=>n.look.prop)).size,
      quests:city.quests.length,art:['aetherhouse','astrolabe','moonobelisk','glasslamp'].every(k=>!!City.art[k]),
      travel:city.npcs.find(n=>n.id==='travel_asterion')?.travelLinks,
      stone:city.npcs.find(n=>n.id==='asterion_stone')?.art,
      well:[well.name,well.theme,well.copies,well.min_level,well.final_boss,well.slimes.length,well.slimes.filter(s=>['tideglass_heron','hourpetal_stag','moonskein_weaver','moonwell_echo'].includes(s.kind)).length],
      gardenArt:['moonlily','moonmirror','moonreed'].every(k=>!!City.art[k]),
      gardenSprite:Field.moonwellGardenSprites.img.moonskein_weaver.naturalWidth,
      sprite:[Field.moonwellSprites.img.moonwell_echo.naturalWidth,Field.moonwellSprites.img.moonwell_echo.naturalHeight],
      map:WorldMap._layout.length,legend:WorldMap._kinds.moonwell_echo?.[1],music:!!window.createAsterionMusic};
  });
  check(data.zones===19&&data.city==='Asterion'&&data.theme==='asterion'&&data.size===180,'The full city loads as zone 17');
  check(data.houses>=120&&data.labels===data.houses,'Every one of the glass-roof houses has a unique address');
  check(data.npcs===21&&data.walkers===10&&data.looks>=8,'Moving townspeople carry distinct clothes and props');
  check(data.quests===6&&data.travel?.includes('travel_lamplight')&&data.stone==='stone','Quest hub, Travel Master and interactive Meeting Stone load');
  check(data.art&&data.map===19&&data.legend===60&&data.music,'Art, world map and dybase2 music hook load');
  check(data.well.join(',')==='The Moonwell,moonwell,4,60,moonwell_echo,20,4'&&data.gardenArt,'Floating Moonwell garden and four bosses load');
  check(STUB||data.sprite.join(',')==='768,480','PixelFlow boss atlas loads in its five-clip format');
  check(STUB||data.gardenSprite===768,'Six new five-clip monster atlases load');
  let debugRef=117;
  const debug=command=>page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,debugRef++]);
  const stage=async(zone,x,y)=>{const sent=await debug({op:'teleport',zone,x,y});check(sent,`Send private teleport to ${zone}:${x},${y}`);try{await page.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<2,[zone,x,y],{timeout:15000,polling:100});}catch(error){const at=await page.evaluate(()=>({connected:Online.connected,zone:Field.zone,x:Field.hero.x,y:Field.hero.y}));throw Error(`Teleport to ${zone}:${x},${y} ended at ${JSON.stringify(at)}; debug ${JSON.stringify(debugPackets.at(-1))}: ${error.message}`);}await page.waitForTimeout(500);};
  await stage(17,90,153);
  await page.waitForFunction(()=>valhalla.hmusic?.loaded&&valhalla.hmusic.running,null,{timeout:15000,polling:100});
  check(await page.evaluate(()=>valhalla.hmusic.duration>68&&valhalla.hmusic.duration<69),'The dybase2 Asterion score decodes and plays in the city');
  await page.screenshot({path:path.join(world.artifacts,'asterion-arrival.png')});
  check(await page.evaluate(()=>Field.zoneTheme==='asterion'&&City.npcs.length===21),'Asterion is rendered with its town population');
  await stage(17,90,99);
  await page.screenshot({path:path.join(world.artifacts,'asterion-astrolabe.png')});
  const moving=await page.evaluate(()=>City.npcs.filter(n=>n.route).map(n=>[n.id,n.x,n.y]));
  await page.waitForTimeout(600);
  check(await page.evaluate(before=>City.npcs.filter(n=>n.route).some(n=>{const p=before.find(x=>x[0]===n.id);return Math.hypot(n.x-p[1],n.y-p[2])>.1}),moving),'NPCs move along their server-timed routes');
  await stage(17,123,84);
  await page.screenshot({path:path.join(world.artifacts,'asterion-meeting-stone.png')});
  await stage(17,127,97);
  await page.evaluate(()=>Online.send({type:'move',x:125,y:93}));
  await page.waitForFunction(()=>Field.zone===18,null,{timeout:20000});
  check(await page.evaluate(()=>Field.zoneTheme==='moonwell'&&Field.slimes.some(s=>s.kind==='moonwell_echo')),'The stairs lead into the water garden');
  await page.waitForFunction(()=>valhalla.mmusic?.running&&!valhalla.hmusic?.running,null,{timeout:10000,polling:100});
  check(await page.evaluate(()=>valhalla.mmusic.running&&!valhalla.hmusic.running),'The garden has its own luminous score');
  await stage(18,102,104);
  await page.waitForTimeout(4300);
  await page.screenshot({path:path.join(world.artifacts,'moonwell-boss.png')});
  await stage(18,18,64);
  await page.evaluate(()=>Online.send({type:'move',x:14,y:64}));
  await page.waitForFunction(()=>Field.zone===17,null,{timeout:15000});
  check(await page.evaluate(()=>Field.zoneName==='Asterion'),'The stairs return to the city');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Asterion UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
