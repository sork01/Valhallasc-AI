// Private browser and Rust server: the Prismwaste's art, zone display and its seamless crossing with Astralhollow (zone 13 and zone 14).
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-prism-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
// map data: Astralhollow is zone 13 (zones[12]), the Prismwaste zone 14 (zones[13]); the crossing is the Prismwaste's prism_astral_gate seam
const W=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'),'utf8'));
const ZP=W.zones[13], ZA=W.zones[12];
const onFloor=(z,x,y)=>(z.shapeFloor[Math.floor(y)]||'')[Math.floor(x)]==='#';
const seam=ZP.portals.find(p=>p.id==='prism_astral_gate');
const [shx,shy]=seam.seam.shift, pts=seam.seam.points, K=7, a=pts[K], b=pts[K+1], len=Math.hypot(b[0]-a[0],b[1]-a[1]);
const q=[(a[0]+b[0])/2,(a[1]+b[1])/2], nrm=[-(b[1]-a[1])/len,(b[0]-a[0])/len];
const inward=onFloor(ZP,q[0]+nrm[0]*4,q[1]+nrm[1]*4)?nrm:[-nrm[0],-nrm[1]];      // into the Prismwaste
const prismSide=[q[0]+inward[0]*3,q[1]+inward[1]*3];                              // 3 tiles into the Prismwaste
const astralSide=[q[0]+shx-inward[0]*3,q[1]+shy-inward[1]*3];                     // 3 tiles into Astralhollow, same crossing point
const keysFor=([dx,dy])=>[Math.abs(dx-dy)>.35?(dx-dy>0?'ArrowRight':'ArrowLeft'):null,Math.abs(dx+dy)>.35?(dx+dy>0?'ArrowDown':'ArrowUp'):null].filter(Boolean);
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:50,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error' && !/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('PrismUI');await page.locator('#go').click({timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:19,command}),command);
  // a new hero starts on the Greenmeadow pier: this zone's sprites load only once the hero is in it, so teleport first (the Last Shade refuge)
  await page.waitForFunction(()=>Online.connected && Field.hero?.hp>0,null,{timeout:60000});
  await debug({op:'teleport',zone:14,x:86,y:172});
  await page.waitForFunction(()=>Field.zone===14 && Math.hypot(Field.hero.nx-86,Field.hero.ny-172)<2,null,{timeout:20000});
  await page.waitForFunction(()=>!!Field.prismSprites && !!Field.prismSprites.img.sunshard,null,{timeout:60000});
  const catalog=await page.evaluate(()=>{
    const z=Field._debug.zones[14],kinds=Field.prismSprites.meta.kinds;
    return {count:Field._debug.zones.length,name:z.name,theme:z.theme,level:z.levels,npcs:z.npcs.length,quests:z.quests.length,
      spawns:z.slimes.length,objects:z.objects.length,kinds,art:['mirrorwall','sunspire','glassstone','saltbrush','lens_pillar','shade_tent','broken_crown'].every(k=>!!City.art[k]),
      expectedSizes:kinds.map(k=>{const fr=Field.frameOf(Field.prismSprites,k);return [fr.w*8,fr.h*5]}),
      sizes:kinds.map(k=>[Field.prismSprites.img[k].naturalWidth,Field.prismSprites.img[k].naturalHeight]),
      map:WorldMap._layout.length,legend:kinds.every(k=>WorldMap._kinds[k]?.[1]>=45),gate:Field._debug.zones[13].portals.find(p=>p.to===14)};
  });
  check(catalog.count>14 && catalog.name===ZP.name && catalog.theme==='prismwaste' && catalog.level.join(',')===ZP.levels.join(','),'The new zone and level range load');
  check((STUB || catalog.sizes.every(([w,h],i)=>w===catalog.expectedSizes[i][0] && h===catalog.expectedSizes[i][1])) && catalog.kinds.length===6,'Six 34-frame enemy atlases load');
  check(catalog.art && catalog.map>0 && catalog.legend,'Scenery art and world-map legend are complete');
  check(catalog.npcs===ZP.npcs.length && catalog.quests===ZP.quests.length && catalog.spawns===ZP.slimes.length && catalog.objects>=300,'The refuge, quests and monster bands load');
  check(catalog.gate?.to===14,'Astralhollow exposes the crossing into the Prismwaste');
  await page.screenshot({path:path.join(world.artifacts,'prism-arrival.png')});
  await debug({op:'teleport',zone:14,x:64,y:61});
  await page.waitForFunction(()=>Field.zone===14 && Math.abs(Field.hero.y-61)<2,null,{timeout:10000});
  await page.screenshot({path:path.join(world.artifacts,'prism-ridges.png')});
  // the seam: from Astralhollow walk into the Prismwaste, then back, with no bounce (arrow keys, as the design suites do)
  await debug({op:'teleport',zone:13,x:astralSide[0],y:astralSide[1]});
  await page.waitForFunction(([x,y])=>Field.zone===13 && Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<2,astralSide,{timeout:20000});
  await page.waitForTimeout(1500);
  let keys=keysFor(inward);
  for(const key of keys) await page.keyboard.down(key);
  await page.waitForFunction(()=>Field.zone===14,null,{timeout:30000});
  for(const key of keys) await page.keyboard.up(key);
  await page.waitForTimeout(500);
  check(await page.evaluate(()=>Field.zone===14 && Field.zoneTheme==='prismwaste'),'the seam carries the hero from Astralhollow into the Prismwaste');
  await debug({op:'teleport',zone:14,x:prismSide[0],y:prismSide[1]});
  await page.waitForFunction(([x,y])=>Field.zone===14 && Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<2,prismSide,{timeout:20000});
  await page.waitForTimeout(1500);
  keys=keysFor([-inward[0],-inward[1]]);
  for(const key of keys) await page.keyboard.down(key);
  await page.waitForFunction(()=>Field.zone===13,null,{timeout:30000});
  for(const key of keys) await page.keyboard.up(key);
  await page.waitForTimeout(500);
  check(await page.evaluate(()=>Field.zone===13),'the return seam reaches Astralhollow without bouncing');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Prismwaste UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
