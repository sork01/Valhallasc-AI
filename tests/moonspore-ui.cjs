// Private Chromium: the Moonfall Arch, original art, maps and return journey.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-moonspore-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
// Counts come from world/map.txt (the file the client and server are built from), not from a snapshot of an old layout.
const mapData=JSON.parse(require('node:fs').readFileSync(path.join(root,'world/map.txt'),'utf8'));
const mapZone=n=>(n===0?mapData:mapData.zones[n-1]);
const zoneCount=mapData.zones.length+1, moon=mapZone(16);
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,env:{...process.env},stderr:'pipe'});
  await client.connect(transport);
  const world=await call('start_world',{startLevel:60,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error' && !/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('CanopyUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected && !!Field.moonsporeSprites && !!Field.moonsporeSprites.img.nightbloom,null,{timeout:60000});
  const data=await page.evaluate(()=>{
    const z=Field._debug.zones[16],kinds=Field.moonsporeSprites.meta.kinds;
    return {count:Field._debug.zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,
      spawns:z.slimes.length,npcs:z.npcs.length,objects:z.objects.length,kinds,
      art:['mooncaps','gloomstalk','moonstone','sporefern','glowmoss','sporelamp','lamphouse','moonwell','moonaltar'].every(k=>!!City.art[k]),
      sizes:kinds.map(k=>[Field.moonsporeSprites.img[k].naturalWidth,Field.moonsporeSprites.img[k].naturalHeight]),
      frames:kinds.map(k=>Field.frameOf(Field.moonsporeSprites,k)),
      map:WorldMap._layout.length,legend:kinds.every(k=>WorldMap._kinds[k]?.[1]>=55),
      gate:Field._debug.zones[15].portals.find(p=>p.id==='orrery_moonspore_gate'),
      travel:z.npcs.find(n=>n.id==='travel_lamplight')};
  });
  check(data.count===zoneCount && data.name==='The Moonspore Canopy' && data.theme==='moonspore' && data.levels.join(',')==='55,60','Zone and level range load');
  check(data.kinds.length===7 && (STUB || data.sizes.every(([w,h],i)=>w===data.frames[i].w*8 && h===data.frames[i].h*5)),'Seven complete enemy atlases load');
  check(data.art && data.map===zoneCount && data.legend,'Scenery and world-map legend load');
  check(data.npcs===moon.npcs.length && data.quests===moon.quests.length && data.spawns===moon.slimes.length && data.objects>=400,`Refuge, quests and spawns load (npcs ${data.npcs}, quests ${data.quests}, spawns ${data.spawns})`);
  check(data.gate?.to===16 && data.travel?.travelLinks.includes('travel_stillpoint'),'Orrery gate and reciprocal Travel Master load');
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:19,command}),command);
  // The Orrery-Moonspore link is a seam (Orrery 15 is shaped, 2026-11-08): cross the line at x 83, y 340 on foot.
  // Zone 16 = zone 15 + (113,-334), so the arrival is (196,10) and the return lands at (83,336) (the old gate ids and coordinates are void).
  await debug({op:'teleport',zone:15,x:83,y:334});
  await page.waitForFunction(()=>Field.zone===15 && Math.abs(Field.hero.y-334)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:83,y:344}));
  await page.waitForFunction(()=>Field.zone===16,null,{timeout:30000});
  await page.waitForFunction(()=>Math.hypot(Field.hero.x-196,Field.hero.y-10)<3,null,{timeout:15000}).catch(()=>{});
  const refugeNpcs=moon.npcs.filter(n=>n.art!=='spirit_guide').length;
  check(await page.evaluate(n=>Field.zoneTheme==='moonspore' && Math.hypot(Field.hero.x-196,Field.hero.y-10)<3 && City.npcs.length===n,refugeNpcs),`Seam reaches Lamplight Refuge (hero ${await page.evaluate(()=>[Field.hero.x,Field.hero.y].map(v=>v.toFixed(1)).join(','))})`);
  await page.screenshot({path:path.join(world.artifacts,'moonspore-arrival.png')});
  await debug({op:'teleport',zone:16,x:196,y:20});
  await page.waitForFunction(()=>Field.zone===16 && Math.abs(Field.hero.y-20)<2,null,{timeout:10000});
  await page.screenshot({path:path.join(world.artifacts,'moonspore-rings.png')});
  await page.evaluate(()=>Online.send({type:'move',x:196,y:2}));
  await page.waitForFunction(()=>Field.zone===15,null,{timeout:30000});
  await page.waitForFunction(()=>Math.hypot(Field.hero.x-83,Field.hero.y-336)<3,null,{timeout:15000}).catch(()=>{});
  check(await page.evaluate(()=>Field.zone===15 && Math.hypot(Field.hero.x-83,Field.hero.y-336)<3),`Return seam reaches Orrery without bounce (hero ${await page.evaluate(()=>[Field.hero.x,Field.hero.y].map(v=>v.toFixed(1)).join(','))})`);
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Moonspore UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
