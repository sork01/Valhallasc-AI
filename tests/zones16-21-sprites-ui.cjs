// Focused real-client check for the redrawn Moonspore, Moonwell, Stormglass, Sunward and Ribbonwild enemies (31 kinds).
process.env.REAL_SPRITES = process.env.REAL_SPRITES || '1';
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const zones = [
  { zone: 16, src: 'moonsporeSprites', tag: 'moonspore', kinds: ['glowcapgrazer','silkwing','rootlurker','lanternwraith','mireheart','silverwidow','nightbloom'] },
  { zone: 18, src: 'moonwellGardenSprites', tag: 'moonwell', kinds: ['dew_moth','lumen_eel','rootbell','tideglass_heron','hourpetal_stag','moonskein_weaver'] },
  { zone: 18, src: 'moonwellSprites', tag: 'moonwell', kinds: ['moonwell_echo'] },
  { zone: 19, src: 'stormglassSprites', tag: 'stormglass', kinds: ['saltclaw','stormgull','glassray','breakersentinel','maelstromheart'] },
  { zone: 20, src: 'sunwardSprites', tag: 'sunward', kinds: ['meadowhare','sunbacksnail','brushfox','spadebadger','honeyjaw','wickerwarden'] },
  { zone: 21, src: 'ribbonwildSprites', tag: 'ribbonwild', kinds: ['ribbongecko','balloonbeetle','paintedmacaw','jesterling','paradegryphon','maskcolossus'] },
];
const client = new Client({name:'zones16-21-sprites-ui',version:'1.0.0'});
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
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('Zone16Art');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected,null,{timeout:20000});
  await page.evaluate(()=>Online.send({type:'debug',ref:1,command:{op:'set_god_mode',enabled:true}}));
  let count = 0;
  for (const z of zones) {
    const spawns=await page.evaluate(({zone,kinds})=>WORLD_MAP.zones[zone-1].slimes.filter(s=>kinds.includes(s.kind)),z);
    for (const kind of z.kinds) {
      const spawn=spawns.find(s=>s.kind===kind);
      assert.ok(spawn,`${kind} has a zone ${z.zone} spawn`);
      await page.evaluate(({zone,x,y})=>Online.send({type:'debug',ref:1,command:{op:'teleport',zone,x,y}}),
        {zone:z.zone,x:spawn.x+3,y:spawn.y+3});
      await page.waitForFunction(({kind})=>Field.slimes.some(s=>s.kind===kind),{kind},{timeout:15000}); // zone 18 is an instance: its private copy has another zone id
      await page.waitForFunction(src=>!!Field[src],z.src,{timeout:30000});
      await page.waitForFunction(({src,kind})=>Field[src].img[kind]?.complete,{src:z.src,kind},{timeout:30000});
      await page.waitForTimeout(350);
      const art=await page.evaluate(({src,kind})=>({
        width:Field[src].img[kind].naturalWidth,
        height:Field[src].img[kind].naturalHeight,
        tops:Field[src].meta.tops?.[kind],
        clip:Field._debug.enemyFrame(Field.slimes.find(s=>s.kind===kind))
      }),{src:z.src,kind});
      assert.equal(art.width,768,`${kind} atlas width`);
      assert.equal(art.height,480,`${kind} atlas height`);
      assert.ok(art.tops>20&&art.clip[0],`${kind} has a fitted health-bar height and draws a frame`);
      await page.screenshot({path:path.join(world.artifacts,`${z.tag}-${kind}.png`)});
      count++;
    }
  }
  assert.equal(errors.length,0,errors.join('; '));
  console.log(`PASS Zones 16-21 sprites: ${count} real-client captures, ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
