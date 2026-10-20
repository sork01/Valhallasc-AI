// One new dungeon only: real client travel, readable art, sign, music and controls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport,getDefaultEnvironment}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'blackhour-private-ui',version:'1'});
let browser,started=false;
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',
    env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/debug/valhalla-server')}}));
  const world=await call('start_world',{godMode:true,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true,args:['--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[],bad=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400&&/blackhour|null_|cathedral\.txt/.test(r.url()))bad.push([r.url(),r.status()]);});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:true,musicVol:.45,sfxVol:0})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#name').fill('Null Artist');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&window.BlackhourArt&&Field.hero,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
  const teleport=async(zone,x,y)=>{
    await debug({op:'teleport',zone,x,y});
    await page.waitForFunction(([z,x,y])=>Field.zone===z&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[zone,x,y],{timeout:15000});
  };
  const shot=async name=>{
    await page.waitForTimeout(650);
    await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,`blackhour-${name}-${STUB?'stub':'real'}.png`)});
  };
  await debug({op:'set_level',level:99});await debug({op:'explore_all'});
  await page.waitForFunction(()=>Field.hero.level===99);
  await page.locator('#levelup-banner').waitFor({state:'hidden'});
  const gear=await page.evaluate(()=>WORLD_ITEMS.filter(i=>i.source==='blackhour'&&(!i.class||i.class==='warrior')).map(i=>({id:i.id,slot:({armor:'chest',weapon:'hands',accessory:'accessory1'})[i.kind]||i.kind})));
  assert.equal(gear.length,8);
  for(const piece of gear){
    await debug({op:'give_item',item:piece.id,quantity:1});
    await page.waitForFunction(id=>Field.hero.inventory?.some(s=>s.item===id),piece.id);
  }
  await page.evaluate(gear=>Online.send({type:'equip',slots:Object.fromEntries(gear.map(p=>[p.slot,p.id]))}),gear);
  await page.waitForFunction(()=>Field.hero.setCounts?.blackhour===8);
  if(!STUB)await page.waitForFunction(()=>Field.warriorSprites?.equipment?.armor==='regearnull'&&Field.warriorSprites?.source?.parts?.weapon_regearnull);
  await teleport(28,214,200);await shot('entrance');
  await page.evaluate(()=>Online.send({type:'move',x:208,y:200}));
  await page.waitForFunction(()=>Field.zone===44,null,{timeout:15000});
  await page.evaluate(()=>Online.send({type:'stop'}));
  await page.waitForFunction(()=>valhalla.blackhourMusic?.running&&valhalla.blackhourMusic.loaded,null,{timeout:30000});
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.blackhourMusic.duration-64*4*60/132)<.05),'The new 4/4 music decodes at the correct loop length');
  assert.ok(await page.evaluate(()=>DayNight.nightMix<.01),'Dungeon keeps indoor light and its own score');
  assert.ok(await page.evaluate(()=>CSS.supports('color',BlackhourArt.ground(80,143,.5,0,WORLD_MAP.zones[43]))),'Foundry floor colors are valid independently of prior canvas state');
  assert.ok(await page.evaluate(()=>Field.slimes.filter(s=>s.kind.startsWith('null_')).length===15&&Field.slimes.filter(s=>s.kind.startsWith('null_')).every(s=>s.d.scale>1.8&&s.d.scale<=2.6)),'All fifteen enemies are giant without a screen-filling visual multiplier');
  assert.ok(await page.evaluate(()=>WORLD_MAP.zones[43].name==='The Black Hour Foundry'&&!WORLD_MAP.zones[43].sealedTemplate&&WORLD_MAP.zones[27].portals.some(p=>p.to===44)),'Open client map, correct Yearwheel entrance and stable zone ID');
  if(!STUB)assert.equal(await page.evaluate(async()=>{
    const meta=await(await fetch('assets/cathedral.txt')).json();let n=0;
    for(const kind of meta.kinds.filter(k=>k.startsWith('null_'))){
      const i=new Image();i.src=`assets/cathedral_${kind}.png`;await i.decode();
      if(i.width===768&&i.height===480&&meta.sprites[kind]&&meta.tops[kind])n++;
    }return n;
  }),6,'All six editable enemy atlases decode');
  for(const [name,x,y] of [['entry',80,143],['rim',55,125],['bell',35,80],['bellframe',35,67],['current',125,80],['turbine',125,67],['sump',80,64],['clock',80,27],['clockwork',80,15]]){
    await teleport(44,x,y);await shot(name);
  }
  const mapOpen=await page.evaluate(()=>({opened:WorldMap.show(),connected:Online.connected,dead:Field.hero.dead,
    hidden:Object.fromEntries(['scene-game','pause','equipment','npc-dialogue'].map(id=>[id,document.getElementById(id).hidden])),
    skill:Skillbar.open,quests:Quests.open,social:Social.open,city:City.open,settings:Settings.active}));
  assert.ok(mapOpen.opened,JSON.stringify(mapOpen));
  await page.locator('.wm-tile[data-zone="44"]').click();
  await page.waitForFunction(()=>WorldMap.zone===44&&WorldMap.view==='zone');
  assert.ok(await page.evaluate(()=>WORLD_MAP.zones[43].blackhourFloor[100][80]===' '&&WORLD_MAP.zones[43].blackhourFloor[143][80]==='='),'World-map floor follows the physical clock and sump');
  await page.screenshot({path:path.join(world.artifacts,'blackhour-map.png')});
  await page.locator('#wm-close').click();
  const sign=await page.evaluate(()=>Field.signs.find(s=>s.id==='null_hour'));
  assert.ok(sign,'The server provides the final boss sign');
  await teleport(44,sign.x,sign.y);
  await page.evaluate(()=>Online.send({type:'sign_read',sign:'null_hour'}));
  await page.locator('#sign-panel').waitFor({state:'visible'});
  assert.match(await page.locator('#sign-panel').innerText(),/red strip/);
  await page.screenshot({path:path.join(world.artifacts,`blackhour-sign-${STUB?'stub':'real'}.png`)});
  await page.keyboard.press('Escape');
  await page.evaluate(()=>Prefs.set({musicVol:.3,sound:true}));await page.waitForTimeout(700);
  assert.ok(await page.evaluate(()=>Math.abs(valhalla.blackhourMusic.output.gain.value-.09)<.005),'Saved music volume reaches this score');
  await page.evaluate(()=>Prefs.set({sound:false}));await page.waitForTimeout(700);
  assert.ok(await page.evaluate(()=>valhalla.blackhourMusic.output.gain.value<.001),'Mute reaches this score');
  await teleport(44,78,143);await page.evaluate(()=>Online.send({type:'move',x:72,y:143}));
  await page.waitForFunction(()=>Field.zone===28,null,{timeout:15000});
  assert.ok(await page.evaluate(()=>!valhalla.blackhourMusic.running&&valhalla.yearMusic.running),'Returning selects The Yearwheel music');
  assert.deepEqual(bad,[]);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,mode:STUB?'stub':'real',artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}
  await client.close();
});
