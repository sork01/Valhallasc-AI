// Private browser and Rust server: both Prismwaste gates, art and zone display.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-prism-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  await client.connect(transport);
  const world=await call('start_world',{startLevel:50,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error' && !/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('PrismUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected && !!Field.prismSprites && !!Field.prismSprites.img.sunshard,null,{timeout:60000});
  const catalog=await page.evaluate(()=>{
    const z=Field._debug.zones[14],kinds=Field.prismSprites.meta.kinds;
    return {count:Field._debug.zones.length,name:z.name,theme:z.theme,level:z.levels,npcs:z.npcs.length,quests:z.quests.length,
      spawns:z.slimes.length,objects:z.objects.length,kinds,art:['mirrorwall','sunspire','glassstone','saltbrush','lens_pillar','shade_tent','broken_crown'].every(k=>!!City.art[k]),
      sizes:kinds.map(k=>[Field.prismSprites.img[k].naturalWidth,Field.prismSprites.img[k].naturalHeight]),
      map:WorldMap._layout.length,legend:kinds.every(k=>WorldMap._kinds[k]?.[1]>=45),gate:Field._debug.zones[13].portals.find(p=>p.id==='astral_prism_gate')};
  });
  check(catalog.count===15 && catalog.name==='The Prismwaste' && catalog.theme==='prismwaste' && catalog.level.join(',')==='45,50','The new zone and level range load');
  check((STUB || catalog.sizes.every(([w,h])=>w===768 && h===480)) && catalog.kinds.length===6,'Six 34-frame enemy atlases load');
  check(catalog.art && catalog.map===15 && catalog.legend,'Scenery art and world-map legend are complete');
  check(catalog.npcs===6 && catalog.quests===10 && catalog.spawns===42 && catalog.objects>=300,'The refuge, quests and monster bands load');
  check(catalog.gate?.to===14,'Astralhollow exposes the outbound Starbreak');
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:19,command}),command);
  await debug({op:'teleport',zone:13,x:64,y:21});
  await page.waitForFunction(()=>Field.zone===13 && Math.abs(Field.hero.y-21)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:64,y:12}));
  await page.waitForFunction(()=>Field.zone===14,null,{timeout:30000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  check(await page.evaluate(()=>Field.zoneTheme==='prismwaste' && Math.hypot(Field.hero.x-64,Field.hero.y-116)<2 && City.npcs.length===6),'The real gate arrives inside the Last Shade refuge');
  await page.screenshot({path:path.join(world.artifacts,'prism-arrival.png')});
  await debug({op:'teleport',zone:14,x:64,y:61});
  await page.waitForFunction(()=>Field.zone===14 && Math.abs(Field.hero.y-61)<2,null,{timeout:10000});
  await page.screenshot({path:path.join(world.artifacts,'prism-ridges.png')});
  await debug({op:'teleport',zone:14,x:64,y:116});
  await page.waitForFunction(()=>Field.zone===14 && Math.abs(Field.hero.y-116)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:64,y:120}));
  await page.waitForFunction(()=>Field.zone===13,null,{timeout:30000});
  check(await page.evaluate(()=>Field.zone===13 && Math.hypot(Field.hero.x-64,Field.hero.y-21)<2),'The return gate reaches Astralhollow without bouncing');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Prismwaste UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
