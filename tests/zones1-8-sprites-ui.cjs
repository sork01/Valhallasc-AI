// Focused real-client check for the redrawn enemies of zones 1-8 (ZONES=1,2 picks some; default all).
process.env.REAL_SPRITES = process.env.REAL_SPRITES || '1';
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const all = [
  { zone: 1, src: 'cragSprites', tag: 'crags' }, { zone: 2, src: 'rimeSprites', tag: 'rime' },
  { zone: 3, src: 'fenSprites', tag: 'fen' }, { zone: 5, src: 'vaultSprites', tag: 'vault' },
  { zone: 6, src: 'wyrdSprites', tag: 'wyrd' }, { zone: 7, src: 'skySprites', tag: 'sky' },
  { zone: 8, src: 'deepSprites', tag: 'deep' },
];
const want = (process.env.ZONES || '').split(',').filter(Boolean).map(Number);
const zones = all.filter(z => !want.length || want.includes(z.zone));
const client = new Client({name:'zones1-8-sprites-ui',version:'1.0.0'});
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
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('Zones18Art');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected,null,{timeout:20000});
  await page.evaluate(()=>Online.send({type:'debug',ref:1,command:{op:'set_god_mode',enabled:true}}));
  let count = 0;
  for (const z of zones) {
    await page.waitForFunction(src=>!!Field[src],z.src,{timeout:30000}).catch(()=>{});
    if (!(await page.evaluate(src=>!!Field[src],z.src))) { await page.evaluate(()=>Online.send({type:'debug',ref:1,command:{op:'teleport',zone:1,x:20,y:20}})); await page.waitForFunction(src=>!!Field[src],z.src,{timeout:30000}); }
    const kinds=await page.evaluate(src=>Field[src].meta.kinds,z.src);
    const spawns=await page.evaluate(({zone,kinds})=>WORLD_MAP.zones[zone-1].slimes.filter(s=>kinds.includes(s.kind)),{zone:z.zone,kinds});
    for (const kind of kinds) {
      const spawn=spawns.find(s=>s.kind===kind);
      assert.ok(spawn,`${kind} has a zone ${z.zone} spawn`);
      await page.evaluate(({zone,x,y})=>Online.send({type:'debug',ref:1,command:{op:'teleport',zone,x,y}}),
        {zone:z.zone,x:spawn.x+3,y:spawn.y+3});
      await page.waitForFunction(({zone,kind})=>Field.zone===zone&&Field.slimes.some(s=>s.kind===kind),{zone:z.zone,kind},{timeout:15000});
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
      assert.ok(art.tops>40&&art.clip[0],`${kind} has a fitted health-bar height and draws a frame`);
      await page.screenshot({path:path.join(world.artifacts,`${z.tag}-${kind}.png`)});
      count++;
    }
  }
  assert.equal(errors.length,0,errors.join('; '));
  console.log(`PASS Zones 1-8 sprites: ${count} real-client captures, ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
