// Private visual review for the eleven later dungeon interiors.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-later-dungeon-visual', version: '1' });
let browser, started = false;
async function call(name,args={}) {
  const result=await client.callTool({name,arguments:args});
  assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...getDefaultEnvironment(),VALHALLA_BINARY:process.env.VALHALLA_BINARY||path.join(root,'target/release/valhalla-server')}});
  transport.stderr.on('data',chunk=>process.stderr.write(chunk));
  await client.connect(transport);
  const world=await call('start_world',{godMode:true,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#name').fill('Interior Artist');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&window.DungeonVisual&&window.Field,null,{timeout:60000});
  const zones=await page.evaluate(()=>WORLD_MAP.zones.slice(28,39).map((z,i)=>({
    id:i+29,theme:z.theme,spawn:z.spawn,rooms:z.rooms,
    landmark:z.objects.find(o=>/^(eye_lens|elder_crown|pavilion_throne|rain_crown_altar|seed_altar|astro_orrery|thunder_altar|bloom_altar|solar_forge|amber_lectern|solstice_altar)$/.test(o.kind)),
  })));
  assert.equal(zones.length,11);
  const signatures=new Set();
  for(const z of zones){
    assert.ok(z.rooms.length>=5,`${z.theme}: room geometry`);
    const center=r=>({x:(r[0]+r[2])/2,y:(r[1]+r[3])/2});
    const room=center(z.rooms[1]);
    const surface=await page.evaluate(([theme,z,room])=>{
      const sample=(x,y)=>DungeonVisual.ground(theme,x,y,.5,0,z);
      const r=z.rooms[1],marks=[];
      for(let yy=1;yy<=5;yy++)for(let xx=1;xx<=5;xx++)
        marks.push(sample(Math.floor(r[0]+(r[2]-r[0])*xx/6),Math.floor(r[1]+(r[3]-r[1])*yy/6)));
      return {profile:!!DungeonVisual.styles[theme],court:sample(room.x,room.y),entry:sample(z.spawn.x,z.spawn.y),marks};
    },[z.theme,z,room]);
    assert.ok(surface.profile,`${z.theme}: surface profile`);
    assert.ok(new Set(surface.marks).size>=2,`${z.theme}: inlaid court geometry`);
    signatures.add(surface.court);
    assert.ok(z.landmark,`${z.theme}: unique room landmark`);
    for(const [label,p] of [['entry',z.spawn],['court',room],['landmark',{x:z.landmark.x,y:z.landmark.y+4}]]){
      await page.evaluate(command=>Online.send({type:'debug',command}),{op:'teleport',zone:z.id,x:p.x,y:p.y});
      await page.waitForFunction(([id,x,y])=>Field.zone===id&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<2,[z.id,p.x,p.y],{timeout:10000});
      await page.waitForTimeout(180);
      const png=await page.evaluate(()=>document.getElementById('fieldcv').toDataURL('image/png'));
      fs.writeFileSync(path.join(world.artifacts,`interior-${z.id}-${label}.png`),Buffer.from(png.split(',')[1],'base64'));
      assert.deepEqual(errors,[],`${z.theme} ${label}: browser errors`);
    }
  }
  assert.ok(signatures.size>=9,'the eleven dungeons use distinct chamber materials');
  // Keep comparison frames beside the new rooms in the same private world.
  for(const id of [5,10,11,12,18]){
    const z=await page.evaluate(id=>WORLD_MAP.zones[id-1],id);
    await page.evaluate(command=>Online.send({type:'debug',command}),{op:'teleport',zone:id,x:z.spawn.x,y:z.spawn.y});
    await page.waitForFunction(([id,x,y])=>Field.zone===id&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<2,[id,z.spawn.x,z.spawn.y],{timeout:10000});
    await page.waitForTimeout(180);
    const png=await page.evaluate(()=>document.getElementById('fieldcv').toDataURL('image/png'));
    fs.writeFileSync(path.join(world.artifacts,`interior-compare-${id}.png`),Buffer.from(png.split(',')[1],'base64'));
  }
  assert.deepEqual(errors,[],`browser errors: ${errors.join('; ')}`);
  console.log(`Eleven interiors, thirty-three views plus five earlier dungeon comparisons: ${world.artifacts}`);
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
  if(browser)await browser.close();
  if(started){try{await call('stop_world');}catch(_){}}
  await client.close();
});
