// Private browser captures of the four Yearwheel seasons and their thresholds.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const MAP=JSON.parse(fs.readFileSync(path.join(__dirname,'..','world','map.txt'),'utf8')),MZ=MAP.zones[27];   // The Yearwheel (zone 28): counts come from the map
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-yearwheel-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(v,message)=>{assert.ok(v,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:95,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('YearUI');await page.locator('#go').click({timeout:60000});
  // a new hero starts on the Saltby pier; the Yearwheel's sprites load only once the hero is in it, so teleport first
  await page.waitForFunction(()=>Online.connected&&!!Field.hero,null,{timeout:60000});
  await page.evaluate(()=>Online.send({type:'debug',ref:1000,command:{op:'teleport',zone:28,x:308,y:768}}));
  await page.waitForFunction(()=>Field.zone===28&&!!Field.yearSprites?.img.longnightwyrm,null,{timeout:60000});
  const data=await page.evaluate(()=>{const z=Field._debug.zones,a=z[28],src=Field.yearSprites;return {count:z.length,name:a.name,theme:a.theme,size:a.size,levels:a.levels,npcs:a.npcs.length,quests:a.quests.length,enemies:a.slimes.length,doors:a.futureInstances,portals:a.portals.length,kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),art:['year_bloom_gate','year_solar_gate','year_amber_gate','year_solstice_gate','year_axle','year_bloomtree','year_sunpine','year_amberoak','year_frostbirch'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,travel:a.npcs.filter(n=>n.travelStop)};});
  check(data.count>=40&&data.name==='The Yearwheel'&&data.theme==='yearwheel'&&data.size===MZ.size&&data.levels.join(',')==='95,99',`The ${MZ.size}-square level 95–99 zone loads`);
  check(data.npcs===MZ.npcs.length&&data.quests===MZ.quests.length&&data.enemies===MZ.slimes.length,`Four hubs, Foundry guides (${data.npcs} people), ${data.quests} quests and ${data.enemies} seasonal encounters load`);
  check(data.doors.length===4&&data.doors.every(d=>d.status==='open')&&data.portals===6,'Four seasonal dungeons and the Foundry entrance load');
  check(data.kinds.length===24&&(STUB||data.sizes.every(([w,h])=>w>0&&h>0)),'Twenty-four PixelFlow atlases load');   // per-kind frames: no fixed atlas size
  check(data.art&&data.layout===MAP.zones.length+1&&data.travel.length===MZ.npcs.filter(n=>n.travelStop).length,`Seasonal scenery, the world map and ${data.travel.length} travel masters load`);   // the map has a tile per zone plus Greenmeadow
  let ref=1001;async function stage(x,y,label){check(await page.evaluate(([x,y,ref])=>Online.send({type:'debug',ref,command:{op:'teleport',zone:28,x,y}}),[x,y,ref++]),`Stage ${label}`);await page.waitForFunction(([x,y])=>Field.zone===28&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<4,[x,y],{timeout:15000});await page.waitForTimeout(900);await page.screenshot({path:path.join(world.artifacts,`yearwheel-${label}.png`)});}
  for(const [x,y,label] of [[308,768,'springmere'],[620,660,'solhaven'],[620,300,'harvestwatch'],[320,300,'rimehold'],[243,607,'blooming-labyrinth'],[692,602,'solar-crucible'],[691,411,'amber-archive'],[273,393,'silent-solstice'],[440,498,'equinox-crossing']])await stage(x,y,label);   // the map's hub centres, Yearwheel gates and crossing (zone 28 is 888 tiles)
  const live=await page.evaluate(()=>({theme:Field.zoneTheme,people:City.npcs.length}));   // City.npcs is filtered by the season, so it is not the map's count
  check(live.theme==='yearwheel'&&live.people>0,`The four-season field renders live (${live.people} people in view of this season)`);
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Yearwheel UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
