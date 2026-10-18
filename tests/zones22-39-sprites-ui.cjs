// Focused real-client check for the cel-shaded redraw of zones 22 and up (`ZONES=22,25` picks zones).
process.env.REAL_SPRITES = process.env.REAL_SPRITES || '1';
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const all = [
  { zone: 22, src: 'tanglecrownSprites', tag: 'tanglecrown', kinds: ['orchidmantis','canopyglider','poolcaiman','drumgorilla','jadeanaconda','crownjaguar'] },
  { zone: 25, src: 'lapisSprites', tag: 'lapis', kinds: ['dunecolossus','dunefennec','glassscorpion','mirageroc','sandhopper','sunvulture'] },
  { zone: 26, src: 'frostwakeSprites', tag: 'frostwake', kinds: ['auroramanta','bellmammoth','crevasseleviathan','frostheron','glaciercrab','iceotter','snowhare'] },
  { zone: 27, src: 'cairnSprites', tag: 'cairn', kinds: ['cairnbehemoth','ridgeadder','screeferret','slateraven','stoneibex','stormcondor','whitebarktitan'] },
  { zone: 28, src: 'yearSprites', tag: 'yearwheel', kinds: ['acornmimic','ambermantis','bloomtortoise','brooknewt','firephoenix','glasslion','harvestreaper','lanternowl','longnightwyrm','petalchimera','rainseraph','rimesaber','snowgiant','snowstoat','sundarter','sunwheel'] },
  { zone: 29, src: 'cathedralSprites', tag: 'cathedral', kinds: ['eye_drifter','eye_lurker','eye_adept','eye_lenswarden','eye_undertide','eye_unblinking'] },
  { zone: 30, src: 'cathedralSprites', tag: 'cathedral', kinds: ['elder_thornling','elder_moth','elder_barkguard','elder_gatekeeper','elder_matron','elder_heart'] },
  { zone: 31, src: 'cathedralSprites', tag: 'cathedral', kinds: ['pavilion_foldling','pavilion_inkmoth','pavilion_silkguard','pavilion_mirror','pavilion_weaver','pavilion_sovereign'] },
  { zone: 32, src: 'cathedralSprites', tag: 'cathedral', kinds: ['rain_crown_droplet','rain_crown_oracle','rain_crown_guard','rain_crown_gatekeeper','rain_crown_sibyl','rain_crown_sovereign'] },
  { zone: 33, src: 'cathedralSprites', tag: 'cathedral', kinds: ['seed_mote','seed_amberwing','seed_rootguard','seed_warden','seed_germinator','seed_worldseed'] },
  { zone: 34, src: 'cathedralSprites', tag: 'cathedral', kinds: ['astro_gearling','astro_starling','astro_sentinel','astro_warden','astro_navigator','astro_axis'] },
  { zone: 35, src: 'cathedralSprites', tag: 'cathedral', kinds: ['thunder_spark','thunder_ray','thunder_guard','thunder_conductor','thunder_bastion','thunder_heart'] },
  { zone: 36, src: 'cathedralSprites', tag: 'cathedral', kinds: ['bloom_spore','bloom_moth','bloom_guard','bloom_thornkeeper','bloom_mirror','bloom_heart'] },
  { zone: 37, src: 'cathedralSprites', tag: 'cathedral', kinds: ['solar_emberling','solar_sunmoth','solar_crucible_guard','solar_ashwarden','solar_heliomancer','solar_heart'] },
  { zone: 38, src: 'cathedralSprites', tag: 'cathedral', kinds: ['amber_page','amber_moth','amber_sentinel','amber_curator','amber_chronicle','amber_memory'] },
  { zone: 39, src: 'cathedralSprites', tag: 'cathedral', kinds: ['solstice_flurry','solstice_owl','solstice_guard','solstice_watcher','solstice_harbinger','solstice_heart'] },
];
// ZONES=22,25 limits the run to those zones (the new thing only).
const only = (process.env.ZONES || '').split(',').filter(Boolean).map(Number);
const zones = only.length ? all.filter(z => only.includes(z.zone)) : all;
const client = new Client({name:'zones22-39-sprites-ui',version:'1.0.0'});
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
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('Zone22Art');
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
  console.log(`PASS Zones 22+ sprites: ${count} real-client captures, ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();if(world)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
