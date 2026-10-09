// Private Chromium: real Hourglass Pass, art, maps and return travel.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-orrery-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  await client.connect(transport);
  const world=await call('start_world',{startLevel:55,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error' && !/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('ClockUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected && !!Field.orrerySprites && !!Field.orrerySprites.img.epochengine,null,{timeout:60000});
  const data=await page.evaluate(()=>{
    const z=Field._debug.zones[15],kinds=Field.orrerySprites.meta.kinds;
    return {count:Field._debug.zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,
      spawns:z.slimes.length,npcs:z.npcs.length,objects:z.objects.length,kinds,
      art:['clockwall','blackspire','cogstone','timegrass','hourpillar','stillpoint','epoch_crown'].every(k=>!!City.art[k]),
      sizes:kinds.map(k=>[Field.orrerySprites.img[k].naturalWidth,Field.orrerySprites.img[k].naturalHeight]),
      map:WorldMap._layout.length,legend:kinds.every(k=>WorldMap._kinds[k]?.[1]>=50),gate:Field._debug.zones[14].portals.find(p=>p.id==='prism_orrery_gate')};
  });
  check(data.count===20 && data.name==='The Obsidian Orrery' && data.theme==='orrery' && data.levels.join(',')==='50,55','Zone and level range load');
  check(data.kinds.length===6 && (STUB || data.sizes.every(([w,h])=>w===768 && h===480)),'Six complete enemy atlases load');
  check(data.art && data.map===20 && data.legend,'Scenery and map legend load');
  check(data.npcs===6 && data.quests===10 && data.spawns===42 && data.objects>=300,'Refuge, quests and monster bands load');
  check(data.gate?.to===15,'Prismwaste has the outgoing Hourglass Pass');
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:19,command}),command);
  await debug({op:'teleport',zone:14,x:108,y:49});
  await page.waitForFunction(()=>Field.zone===14 && Math.abs(Field.hero.x-108)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:117,y:49}));
  await page.waitForFunction(()=>Field.zone===15,null,{timeout:30000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  check(await page.evaluate(()=>Field.zoneTheme==='orrery' && Math.hypot(Field.hero.x-16,Field.hero.y-112)<2 && City.npcs.length===6),'The gate reaches the Stillpoint');
  await page.screenshot({path:path.join(world.artifacts,'orrery-arrival.png')});
  await debug({op:'teleport',zone:15,x:64,y:52});
  await page.waitForFunction(()=>Field.zone===15 && Math.abs(Field.hero.y-52)<2,null,{timeout:10000});
  await page.screenshot({path:path.join(world.artifacts,'orrery-rings.png')});
  await debug({op:'teleport',zone:15,x:14,y:112});
  await page.waitForFunction(()=>Field.zone===15 && Math.abs(Field.hero.x-14)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:9,y:112}));
  await page.waitForFunction(()=>Field.zone===14,null,{timeout:30000});
  check(await page.evaluate(()=>Field.zone===14 && Math.hypot(Field.hero.x-107,Field.hero.y-49)<2),'Return gate reaches Prismwaste without bounce');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Orrery UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
