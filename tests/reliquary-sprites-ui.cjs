// Focused real-client check for the seven Coral Reliquary enemy atlases.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const kinds = ['reliccrab','relicwarden','pearlwidow','glasscantor','coralregent','tidecantor','tidetemplar'];
const client = new Client({name:'reliquary-sprites-ui',version:'1.0.0'});
let browser, world;
const call = async(name,args={}) => {
  const r=await client.callTool({name,arguments:args});
  assert.ok(!r.isError,JSON.stringify(r.content));
  return r.structuredContent;
};
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,
    args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',
    env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/release/valhalla-server')}}));
  world=await call('start_world',{startLevel:50,levelSpread:0});
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);
  await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('ReliquaryArt');
  await page.locator('#go').click({timeout:60000});
  try {
    await page.waitForFunction(()=>Online.connected,null,{timeout:20000});
  } catch (error) {
    console.error('Client state',await page.evaluate(()=>({connected:window.Online?.connected,
      atlas:!!window.Field?.cathedralSprites,text:document.body.innerText.slice(-900)})),errors);
    await page.screenshot({path:path.join(world.artifacts,'reliquary-login-failure.png')});
    throw error;
  }
  await page.evaluate(()=>Online.send({type:'debug',ref:1,command:{op:'set_god_mode',enabled:true}}));
  const spawns=await page.evaluate(kinds=>WORLD_MAP.zones[10].slimes.filter(s=>
    kinds.includes(s.kind)),kinds);
  for(const kind of kinds){
    const spawn=spawns.find(s=>s.kind===kind);
    assert.ok(spawn,`${kind} has a zone 11 spawn`);
    await page.evaluate(({x,y})=>Online.send({type:'debug',ref:1,command:{op:'teleport',zone:11,x,y}}),
      {x:spawn.x+3,y:spawn.y+3});
    await page.waitForFunction(kind=>Field.zone===11&&Field.slimes.some(s=>s.kind===kind),kind,{timeout:15000});
    await page.waitForFunction(()=>!!Field.cathedralSprites,null,{timeout:30000});
    await page.waitForFunction(kind=>Field.cathedralSprites.img[kind]?.complete,kind,{timeout:30000});
    await page.waitForTimeout(350);
    const art=await page.evaluate(kind=>({
      width:Field.cathedralSprites.img[kind].naturalWidth,
      height:Field.cathedralSprites.img[kind].naturalHeight,
      top:Field.cathedralSprites.meta.tops[kind],
      clip:Field._debug.enemyFrame(Field.slimes.find(s=>s.kind===kind))
    }),kind);
    assert.equal(art.width,768,`${kind} atlas width`);
    assert.equal(art.height,480,`${kind} atlas height`);
    assert.ok(art.top>20&&art.clip[0],`${kind} draws a fitted frame`);
    await page.screenshot({path:path.join(world.artifacts,`reliquary-${kind}.png`)});
  }
  assert.equal(errors.length,0,errors.join('; '));
  console.log(`PASS Reliquary sprites: ${kinds.length} real-client captures, ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
