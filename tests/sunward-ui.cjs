// Private Chromium: real page, green Sunward art, named PixelFlow NPCs and the sealed Elder Hollow.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-sunward-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:70,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const capture=async name=>{
    const png=await page.evaluate(()=>document.querySelector('#fieldcv').toDataURL('image/png'));
    fs.writeFileSync(path.join(world.artifacts,name),Buffer.from(png.split(',')[1],'base64'));
  };
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('SunwardUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.sunwardSprites?.img.wickerwarden,null,{timeout:60000});
  const data=await page.evaluate(()=>{
    const zones=Field._debug.zones,z=zones[20],src=Field.sunwardSprites;
    return {count:zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,npcs:z.npcs.length,
      spawns:z.slimes.length,kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),
      art:['oak_tree','birch_tree','apple_tree','willow_tree','vale_cottage','watermill','stone_bridge','elder_hollow_gate'].every(k=>!!City.art[k]),
      layout:WorldMap._layout.length,legend:src.meta.kinds.slice(0,6).every(k=>WorldMap._kinds[k]?.[1]>=65),
      seal:z.futureInstance,gate:zones[19].portals.find(p=>p.id==='stormglass_sun_gate'),
      travel:z.npcs.find(n=>n.id==='travel_millbridge'),miller:z.npcs.find(n=>n.id==='sun_miller'),keeper:z.npcs.find(n=>n.id==='sun_keeper'),trees:z.objects.filter(o=>['oak_tree','birch_tree','apple_tree','willow_tree'].includes(o.kind)).length};
  });
  check(data.count===21&&data.name==='Sunward Vale'&&data.theme==='sunward'&&data.levels.join(',')==='65,70','Zone 20 and levels load');
  check(data.kinds.length===9&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Six enemy and three NPC PixelFlow atlases load');
  check(data.art&&data.layout===21&&data.legend&&data.trees>=170,'Real trees, mill, bridges and world map catalog load');
  check(data.npcs===8&&data.quests===9&&data.spawns===42,'Camp, quest hub and encounters load');
  check(data.seal?.status==='sealed'&&data.seal?.name==='The Elder Hollow'&&data.gate?.to===20,'Instance entrance is sealed and Sunward Cut exists');
  check(data.travel?.travelLinks.includes('travel_breakwater')&&data.travel?.art==='sun_travel'&&data.miller?.art==='sun_miller'&&data.keeper?.art==='sun_keeper','Three distinct PixelFlow NPCs load');
  let ref=301;
  const debug=async command=>{check(await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,ref++]),`Send ${command.op}`);};
  await debug({op:'teleport',zone:20,x:32,y:113});
  await page.waitForFunction(()=>Field.zone===20&&Math.hypot(Field.hero.x-32,Field.hero.y-113)<2,null,{timeout:15000});
  await page.waitForTimeout(1200);
  await page.screenshot({path:path.join(world.artifacts,'sunward-camp.png')});
  await capture('sunward-camp-clean.png');
  check(await page.evaluate(()=>Field.zoneTheme==='sunward'&&City.npcs.length===8),'Millbridge paints in the live zone');
  await debug({op:'teleport',zone:20,x:105,y:13});
  await page.waitForFunction(()=>Field.zone===20&&Math.hypot(Field.hero.x-105,Field.hero.y-13)<2,null,{timeout:15000});
  await page.waitForTimeout(1600);
  await page.screenshot({path:path.join(world.artifacts,'sunward-elder-hollow.png')});
  await capture('sunward-elder-hollow-clean.png');
  check(await page.evaluate(()=>Field._debug.zones[20].portals.length===1&&Field.zone===20),'The Elder Hollow has no playable dungeon portal');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Sunward UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
