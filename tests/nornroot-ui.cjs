// One new dungeon only: real client travel, readable art, sign, music and controls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport,getDefaultEnvironment}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'nornroot-private-ui',version:'1'});
let browser,started=false;
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',
    env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/debug/valhalla-server')}}));
  const world=await call('start_world',{godMode:true,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[],bad=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&/nornroot|barrow_|cathedral\.txt/.test(r.url()))bad.push([r.url(),r.status()]);});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:.45,sfxVol:0})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#name').fill('Barrow Artist');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&window.NornrootArt&&Field.hero,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
  const teleport=async(zone,x,y)=>{
    await debug({op:'teleport',zone,x,y});
    await page.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[zone,x,y],{timeout:15000});
  };
  const shot=async name=>{
    await page.waitForTimeout(650);
    await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,`nornroot-${name}-${STUB?'stub':'real'}.png`)});
  };
  await debug({op:'set_level',level:25});await debug({op:'explore_all'});
  await page.waitForFunction(()=>Field.hero.level===25);
  await page.locator('#levelup-banner').waitFor({state:'hidden'});
  const gear=await page.evaluate(()=>WORLD_ITEMS.filter(i=>i.source==='nornroot'&&(!i.class||i.class==='warrior')).map(i=>({id:i.id,slot:({armor:'chest',weapon:'hands',accessory:'accessory1'})[i.kind]||i.kind})));
  assert.equal(gear.length,8);
  for(const piece of gear){
    await debug({op:'give_item',item:piece.id,quantity:1});
    await page.waitForFunction(id=>Field.hero.inventory?.some(s=>s.item===id),piece.id);
  }
  await page.evaluate(gear=>Online.send({type:'equip',slots:Object.fromEntries(gear.map(p=>[p.slot,p.id]))}),gear);
  await page.waitForFunction(()=>Field.hero.setCounts?.nornroot===8);
  if(!STUB)await page.waitForFunction(()=>Field.warriorSprites?.equipment?.armor==='fatewoven'&&Field.warriorSprites?.source?.parts?.weapon_fatewoven);
  await teleport(6,84,71);await shot('entrance');
  await page.evaluate(()=>Online.send({type:'move',x:84,y:66}));
  await page.waitForFunction(()=>Field.zone===41,null,{timeout:15000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  await page.waitForFunction(()=>valhalla.nornrootMusic?.running&&valhalla.nornrootMusic.loaded,null,{timeout:30000});
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.nornrootMusic.duration-24*5*60/88)<.05),'The new 5/4 music decodes at the correct loop length');
  assert.ok(await page.evaluate(()=>DayNight.nightMix<.01),'Dungeon keeps indoor light and its own score');
  assert.ok(await page.evaluate(()=>WORLD_MAP.zones[40].name==='Nornroot Barrow'&&WORLD_MAP.zones[5].portals.some(p=>p.to===41)),'Correct Wyrdwood entrance and stable zone ID');
  if(!STUB)assert.equal(await page.evaluate(async()=>{
    const meta=await(await fetch('assets/cathedral.txt')).json();let n=0;
    for(const kind of meta.kinds.filter(k=>k.startsWith('barrow_'))){
      const i=new Image();i.src=`assets/cathedral_${kind}.png`;await i.decode();
      if(i.width===768&&i.height===480&&meta.sprites[kind]&&meta.tops[kind])n++;
    }return n;
  }),6,'All six editable enemy atlases decode');
  for(const [name,x,y] of [['threshold',56,99],['amber-court',25,58],['thread-court',87,58],['loom',60,13]]){
    await teleport(41,x,y);await shot(name);
  }
  const sign=await page.evaluate(()=>Field.signs.find(s=>s.id==='barrow_fatebound'));
  assert.ok(sign,'The server provides the final boss sign');
  await teleport(41,sign.x,sign.y);
  await page.evaluate(()=>Online.send({type:'sign_read',sign:'barrow_fatebound'}));
  await page.locator('#sign-panel').waitFor({state:'visible'});
  assert.match(await page.locator('#sign-panel').innerText(),/clear middle/);
  assert.equal(await page.locator('#sign-panel circle[fill="none"]').count(),1,'The sign shows the ring and its clear middle');
  await page.screenshot({path:path.join(world.artifacts,`nornroot-sign-${STUB?'stub':'real'}.png`)});
  await page.keyboard.press('Escape');
  await page.evaluate(()=>Prefs.set({musicVol:.3,sound:true}));await page.waitForTimeout(700);
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.nornrootMusic.output.gain.value-.09)<.005),'Saved music volume reaches this score');
  await page.evaluate(()=>Prefs.set({sound:false}));await page.waitForTimeout(700);
  assert.ok(await page.evaluate(()=>valhalla.nornrootMusic.output.gain.value<.001),'Mute reaches this score');
  await teleport(41,53,99);await page.evaluate(()=>Online.send({type:'move',x:49,y:99}));
  await page.waitForFunction(()=>Field.zone===6,null,{timeout:15000});
  assert.ok(await page.evaluate(()=>!valhalla.nornrootMusic.running&&valhalla.wmusic.running),'Returning selects Wyrdwood music');
  assert.deepEqual(bad,[]);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,mode:STUB?'stub':'real',artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}
  await client.close();
});
