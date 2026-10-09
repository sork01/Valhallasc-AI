// Private Chromium: live causeway, Stormglass art and the sealed Eye Below.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-stormglass-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  await client.connect(transport);
  const world=await call('start_world',{startLevel:65,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  let page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('StormglassUI');await page.locator('#go').click({timeout:60000});
  try { await page.waitForFunction(()=>Online.connected&&!!Field.stormglassSprites?.img.maelstromheart,null,{timeout:30000}); }
  catch(error){
    const state=await page.evaluate(async()=>({connected:Online.connected,source:!!Field.stormglassSprites,meta:(await fetch('assets/stormglass.txt')).status,
      images:await Promise.all(['saltclaw','stormgull','glassray','breakersentinel','maelstromheart'].map(k=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve([k,i.naturalWidth]);i.onerror=()=>resolve([k,'error']);i.src=`assets/stormglass_${k}.png`;setTimeout(()=>resolve([k,'timeout']),3000);}))) }));
    throw Error(`${error.message}; ${JSON.stringify({state,errors})}`);
  }
  const data=await page.evaluate(()=>{
    const zones=Field._debug.zones,z=zones[19],source=Field.stormglassSprites;
    return {count:zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,npcs:z.npcs.length,
      spawns:z.slimes.length,objects:z.objects.length,kinds:source.meta.kinds,sizes:source.meta.kinds.map(k=>[source.img[k].naturalWidth,source.img[k].naturalHeight]),
      art:['saltpillar','blackpebble','seafoam','stormreed','stormglass_spire','stormlamp','breakwater_hut','tide_bell','eye_arch'].every(k=>!!City.art[k]),
      map:WorldMap._layout.length,legend:source.meta.kinds.every(k=>WorldMap._kinds[k]?.[1]>=60),
      seal:z.futureInstance,gate:zones[17].portals.find(p=>p.id==='asterion_stormglass_gate'),
      travel:z.npcs.find(n=>n.id==='travel_breakwater')};
  });
  check(data.count===20&&data.name==='The Stormglass Shore'&&data.theme==='stormglass'&&data.levels.join(',')==='60,65','The shore and level range load');
  check(data.kinds.length===5&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Five complete monster atlases load');
  check(data.art&&data.map===20&&data.legend,'Original scenery and world-map legend load');
  check(data.npcs===8&&data.quests===8&&data.spawns===41&&data.objects>=390,'Camp, quests and enemy fields load');
  check(data.seal?.status==='sealed'&&data.seal?.name==='The Eye Below'&&data.gate?.to===19,'The Eye is sealed and the Asterion causeway exists');
  check(data.travel?.travelLinks.includes('travel_asterion'),'The Travel Master knows Asterion');
  let debugRef=219;
  const debug=async command=>{
    const sent=await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,debugRef++]);
    check(sent,`Send private ${command.op} shortcut`);
  };
  await debug({op:'teleport',zone:17,x:164,y:88});
  await page.waitForFunction(()=>Field.zone===17&&Math.abs(Field.hero.x-164)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:170,y:88}));
  await page.waitForFunction(()=>Field.zone===19,null,{timeout:30000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  check(await page.evaluate(()=>Field.zoneTheme==='stormglass'&&Math.hypot(Field.hero.x-13,Field.hero.y-105)<2&&City.npcs.length===8),'Causeway reaches Breakwater Camp');
  await debug({op:'teleport',zone:19,x:30,y:108});
  await page.waitForFunction(()=>Math.hypot(Field.hero.x-30,Field.hero.y-108)<2,null,{timeout:10000});
  await page.waitForTimeout(1600);
  await page.screenshot({path:path.join(world.artifacts,'stormglass-camp.png')});
  check(await page.evaluate(()=>Field._debug.zones[19].portals.length===1&&Field.zone===19),'The entrance has no dungeon portal');
  await debug({op:'teleport',zone:19,x:13,y:105});
  await page.waitForFunction(()=>Math.hypot(Field.hero.x-13,Field.hero.y-105)<2,null,{timeout:10000});
  await page.evaluate(()=>Online.send({type:'move',x:7,y:105}));
  try { await page.waitForFunction(()=>Field.zone===17,null,{timeout:30000}); }
  catch(error){const state=await page.evaluate(()=>({connected:Online.connected,hero:Field.hero,zone:Field.zone,overlay:document.getElementById('connection-overlay')?.textContent}));throw Error(`${error.message}; ${JSON.stringify(state)}`);}
  check(await page.evaluate(()=>Math.hypot(Field.hero.x-160,Field.hero.y-88)<2),'Return causeway arrives clear of its gate');
  await page.close();
  page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('EyeWatcherUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.stormglassSprites?.img.maelstromheart,null,{timeout:60000});
  await page.evaluate(()=>{window.__stormglassSent={};const send=Online.send;Online.send=function(message){__stormglassSent[message.type]=(__stormglassSent[message.type]||0)+1;return send(message);};});
  await debug({op:'teleport',zone:19,x:99,y:19});
  await page.waitForFunction(()=>Field.zone===19&&Math.hypot(Field.hero.x-99,Field.hero.y-19)<3,null,{timeout:15000});
  await page.waitForTimeout(4400);
  await page.screenshot({path:path.join(world.artifacts,'stormglass-eye.png')});
  const eyeState=await page.evaluate(()=>({connected:Online.connected,sent:window.__stormglassSent,overlay:document.getElementById('connection-overlay')?.textContent}));
  check(eyeState.connected,`Eye visitor stays connected: ${JSON.stringify(eyeState)}`);
  check(await page.evaluate(()=>Field.zoneTheme==='stormglass'&&Field._debug.zones[19].futureInstance?.status==='sealed'),'A second visitor sees the sealed Eye in the live zone');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Stormglass UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
