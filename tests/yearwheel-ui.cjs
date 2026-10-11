// Private browser captures of all four Yearwheel seasons and the sealed thresholds.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
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
  await page.waitForFunction(()=>Online.connected&&!!Field.yearSprites?.img.longnightwyrm,null,{timeout:60000});
  const data=await page.evaluate(()=>{const z=Field._debug.zones,a=z[28],src=Field.yearSprites;return {count:z.length,name:a.name,theme:a.theme,size:a.size,levels:a.levels,npcs:a.npcs.length,quests:a.quests.length,enemies:a.slimes.length,doors:a.futureInstances,portals:a.portals.length,kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),art:['year_bloom_gate','year_solar_gate','year_amber_gate','year_solstice_gate','year_axle','year_bloomtree','year_sunpine','year_amberoak','year_frostbirch'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,travel:a.npcs.filter(n=>n.travelStop)};});
  check(data.count===29&&data.name==='The Yearwheel'&&data.theme==='yearwheel'&&data.size===400&&data.levels.join(',')==='95,99','The 400-square level 95–99 zone loads');
  check(data.npcs===28&&data.quests===24&&data.enemies===156,'Four hubs, quests and seasonal encounters load');
  check(data.doors.length===4&&data.doors.every(d=>d.status==='sealed')&&data.portals===1,'Four instance entrances are sealed');
  check(data.kinds.length===24&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Twenty-four PixelFlow atlases load');
  check(data.art&&data.layout===29&&data.travel.length===4,'Seasonal scenery and travel masters load');
  let ref=1001;async function stage(x,y,label){check(await page.evaluate(([x,y,ref])=>Online.send({type:'debug',ref,command:{op:'teleport',zone:28,x,y}}),[x,y,ref++]),`Stage ${label}`);await page.waitForFunction(([x,y])=>Field.zone===28&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<4,[x,y],{timeout:15000});await page.waitForTimeout(900);await page.screenshot({path:path.join(world.artifacts,`yearwheel-${label}.png`)});}
  for(const [x,y,label] of [[76,324,'springmere'],[320,316,'solhaven'],[321,78,'harvestwatch'],[78,78,'rimehold'],[36,217,'blooming-labyrinth'],[340,236,'solar-crucible'],[340,139,'amber-archive'],[35,138,'silent-solstice'],[200,200,'equinox-crossing']])await stage(x,y,label);
  check(await page.evaluate(()=>Field.zoneTheme==='yearwheel'&&City.npcs.length===28),'The four-season field renders live');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Yearwheel UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
