// One new outdoor zone only: real travel, exported art, maps and both music routes.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport,getDefaultEnvironment}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'emberwake-private-ui',version:'1'});
let browser,started=false;
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',
    env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/debug/valhalla-server')}}));
  const world=await call('start_world',{godMode:true,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',args:['--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[],bad=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&/emberwake|cathedral_ew_|cathedral\.txt/.test(r.url()))bad.push([r.url(),r.status()]);});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:.45,sfxVol:0})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#name').fill('Ember Artist');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&window.EmberwakeArt&&Field.hero,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
  const teleport=async(zone,x,y)=>{
    await debug({op:'teleport',zone,x,y});
    await page.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[zone,x,y],{timeout:15000});
  };
  const shot=async name=>{
    await page.waitForTimeout(250);
    await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('area-title')).opacity)<.05);
    await page.waitForTimeout(850);
    await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,`emberwake-${name}-${STUB?'stub':'real'}.png`)});
  };
  if(process.env.PHOTO_ONLY==='1'){
    await debug({op:'set_level',level:99});await page.waitForFunction(()=>Field.hero.level===99);
    await page.locator('#levelup-banner').waitFor({state:'hidden'});
    await debug({op:'set_time',hour:12,freeze:true});await debug({op:'set_weather',kind:'clear'});
    await teleport(45,104,92);
    await shot('lava');
    await teleport(45,124,15);
    await page.waitForFunction(()=>Field.cathedralSprites?.meta.kinds.filter(k=>k.startsWith('ew_')).length===7);
    await page.setViewportSize({width:844,height:390});
    assert.ok(!await page.locator('.rotate').isVisible(),'Touch landscape shows the game');
    await shot('door-mobile');
    console.log(JSON.stringify({passed:true,photo:true,artifacts:world.artifacts}));return;
  }
  await debug({op:'explore_all'});

  await page.locator('#levelup-banner').waitFor({state:'hidden'});
  await debug({op:'set_level',level:99});
  await page.waitForFunction(()=>Field.hero.level===99);
  await page.locator('#levelup-banner').waitFor({state:'hidden'});
  await teleport(17,90,25);await shot('asterion');
  await page.evaluate(()=>Online.send({type:'move',x:90,y:18}));
  await page.waitForFunction(()=>Field.zone===45,null,{timeout:20000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  await debug({op:'set_time',hour:12,freeze:true});
  await debug({op:'set_weather',kind:'clear'});
  await page.waitForFunction(()=>valhalla.emberwakeMusic?.loaded&&valhalla.emberwakeNightMusic?.loaded,null,{timeout:60000});
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.emberwakeMusic.duration-32*4*60/110)<.05),'Day loop decodes');
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.emberwakeNightMusic.duration-80)<.05),'Night loop decodes');
  assert.equal(await page.evaluate(()=>Field.zoneTheme),'emberwake');
  assert.ok(await page.locator('#world-weather').textContent().then(t=>!t.includes('Indoors')),'The caldera has outdoor weather');
  assert.ok(await page.evaluate(()=>WORLD_MAP.zones[44].objects.some(o=>o.kind==='meetingstone')),'The hire service has a visible Meeting Stone');
  if(!STUB)await page.waitForFunction(()=>Field.cathedralSprites?.meta.kinds.filter(k=>k.startsWith('ew_')).length===7);
  assert.equal(await page.evaluate(()=>WORLD_MAP.zones[44].slimes.filter(s=>CATHEDRAL_ENEMIES.find(e=>e.kind===s.kind)?.elite).length),3);
  for(const [name,x,y]of [['arrival',22,137],['causeway',71,96],['lava',104,92],['shackle',108,118],['bellows',43,50],['door',124,15]]){
    await teleport(45,x,y);await shot(name);
  }
  const art=await page.evaluate(async()=>{
    const meta=await(await fetch('assets/cathedral.txt')).json();
    const result=[];
    for(const kind of meta.kinds.filter(k=>k.startsWith('ew_'))){
      const img=new Image();img.src='assets/cathedral_'+kind+'.png';await img.decode();
      result.push({kind,w:img.width,h:img.height,editable:!!meta.sprites[kind],top:meta.tops[kind]});
    }return result;
  });
  assert.equal(art.length,7);assert.ok(art.every(i=>i.w===768&&i.h===480&&i.editable&&i.top));
  await page.evaluate(()=>WorldMap.show());
  await page.locator('.wm-tile[data-zone="45"]').click();
  await page.waitForFunction(()=>WorldMap.zone===45&&WorldMap.view==='zone');
  await page.screenshot({path:path.join(world.artifacts,'emberwake-map.png')});
  await page.locator('#wm-close').click();
  // Explicit authoritative day/night clock sync exercises both routes.
  for(const [hour,night]of [[12,false],[23,true]]){
    await debug({op:'set_time',hour,freeze:true});
    await page.waitForFunction(night=>night?DayNight.nightMix>.99:DayNight.nightMix<.01,night,{timeout:15000});
    await page.waitForTimeout(1600);
    assert.ok(await page.evaluate(night=>night?valhalla.emberwakeNightMusic.running:valhalla.emberwakeMusic.running,night));
    await shot(night?'door-night':'door-day');
  }
  await page.evaluate(()=>Prefs.set({musicVol:.3,sound:true}));await page.waitForTimeout(1800);
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.emberwakeNightMusic.output.gain.value-.09)<.01));
  await page.evaluate(()=>Prefs.set({sound:false}));await page.waitForTimeout(1800);
  assert.ok(await page.evaluate(()=>valhalla.emberwakeNightMusic.output.gain.value<.001));
  await page.setViewportSize({width:844,height:390});
  assert.ok(!await page.locator('.rotate').isVisible(),'Touch landscape shows the game');
  await shot('door-mobile');
  await teleport(45,20,140);await page.evaluate(()=>Online.send({type:'move',x:14,y:140}));
  await page.waitForFunction(()=>Field.zone===17,null,{timeout:20000});
  assert.ok(await page.evaluate(()=>!valhalla.emberwakeMusic.running&&!valhalla.emberwakeNightMusic.running));
  assert.deepEqual(bad,[]);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,mode:STUB?'stub':'real',artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}
  await client.close();
});
