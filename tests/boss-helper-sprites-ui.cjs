// Real-client check of the own art of the six boss-mechanic helpers (they used to borrow another kind's sprite via `artFrom`):
// each stands asleep where place_boss_adds.py put it (sleepers are not drawn, and spawn_enemy only moves awake slots), its own atlas loads, and the catalog no longer borrows. `ZONES=33` picks zones.
process.env.REAL_SPRITES = process.env.REAL_SPRITES || '1';
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const all = [
  { zone: 10, src: 'cathedralSprites', tag: 'cathedral', kinds: ['choirsinger'] },
  { zone: 11, src: 'cathedralSprites', tag: 'cathedral', kinds: ['reliquarypearl'] },
  { zone: 33, src: 'cathedralSprites', tag: 'cathedral', kinds: ['seed_sprout', 'seed_treant'] },
  { zone: 37, src: 'cathedralSprites', tag: 'cathedral', kinds: ['solar_cinder'] },
  { zone: 38, src: 'cathedralSprites', tag: 'cathedral', kinds: ['amber_cocoon'] },
];
// ZONES=22,25 limits the run to those zones (the new thing only).
const only = (process.env.ZONES || '').split(',').filter(Boolean).map(Number);
const zones = only.length ? all.filter(z => only.includes(z.zone)) : all;
const client = new Client({name:'boss-helper-sprites-ui',version:'1.0.0'});
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
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('HelperArt');
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
      assert.equal(await page.evaluate(k => CATHEDRAL_ENEMIES.find(e => e.kind === k).artFrom, kind), undefined, `${kind} draws its own art, not a borrowed one`);
      assert.equal(art.width,768,`${kind} atlas width`);
      assert.equal(art.height,480,`${kind} atlas height`);
      assert.ok(art.tops>20&&art.clip[0],`${kind} has a fitted health-bar height and draws a frame`);
      // the atlas is the helper's own drawing: not the pixels of the kind it used to borrow, and not empty
      const BORROWED = { choirsinger: 'tidecantor', reliquarypearl: 'pearlwidow', seed_sprout: 'seed_mote', seed_treant: 'seed_rootguard', solar_cinder: 'solar_cinder' === kind ? 'solar_heart' : '', amber_cocoon: 'amber_sentinel' };
      const same = await page.evaluate(async ({ kind, other }) => {
        const hash = async name => { const img = new Image(); img.src = `assets/cathedral_${name}.png`; await img.decode(); const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0); const d = g.getImageData(0, 0, 96, 96).data; let h = 7, opaque = 0; for (let i = 0; i < d.length; i++) { h = (h * 31 + d[i]) >>> 0; if (i % 4 === 3 && d[i]) opaque++; } return { h, opaque }; };
        const [mine, theirs] = [await hash(kind), await hash(other)];
        return { same: mine.h === theirs.h, opaque: mine.opaque };
      }, { kind, other: BORROWED[kind] });
      assert.equal(same.same, false, `${kind} is not the borrowed art`);
      assert.ok(same.opaque > 400, `${kind} idle frame has a body`);
      count++;
    }
  }
  assert.equal(errors.length,0,errors.join('; '));
  console.log(`PASS Boss helper sprites: ${count} real-client checks`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
