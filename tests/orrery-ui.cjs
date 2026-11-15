// Private Chromium: real Obsidian Orrery art, maps and its seamless crossing from the Prismwaste (zone 14 to zone 15).
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-orrery-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
// map data: the Prismwaste is zone 14 (zones[13]) and the Orrery zone 15 (zones[14]); the seam to the Orrery is the Prismwaste's prism_orrery_gate
const W=JSON.parse(fs.readFileSync(path.join(root,'world/map.txt'),'utf8'));
const ZP=W.zones[13], ZO=W.zones[14];
const onFloor=(z,x,y)=>(z.shapeFloor[Math.floor(y)]||'')[Math.floor(x)]==='#';
const seam=ZP.portals.find(p=>p.id==='prism_orrery_gate');
const [shx,shy]=seam.seam.shift, pts=seam.seam.points, K=7, a=pts[K], b=pts[K+1], len=Math.hypot(b[0]-a[0],b[1]-a[1]);
const q=[(a[0]+b[0])/2,(a[1]+b[1])/2], nrm=[-(b[1]-a[1])/len,(b[0]-a[0])/len];
const inward=onFloor(ZP,q[0]+nrm[0]*4,q[1]+nrm[1]*4)?nrm:[-nrm[0],-nrm[1]];
const start=[q[0]+inward[0]*3,q[1]+inward[1]*3];
// the same arrow-key mapping as the design suites: world +x = Right+Down
const keysFor=([dx,dy])=>[Math.abs(dx-dy)>.35?(dx-dy>0?'ArrowRight':'ArrowLeft'):null,Math.abs(dx+dy)>.35?(dx+dy>0?'ArrowDown':'ArrowUp'):null].filter(Boolean);
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  await client.connect(transport);
  const world=await call('start_world',{startLevel:55,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error' && !/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('ClockUI');await page.locator('#go').click({timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:19,command}),command);
  // a new hero starts on the Greenmeadow pier: the Orrery's sprites load only once the hero is in zone 15, so teleport first
  await page.waitForFunction(()=>Online.connected && Field.hero?.hp>0,null,{timeout:60000});
  await debug({op:'teleport',zone:15,x:79,y:301});
  await page.waitForFunction(()=>Field.zone===15 && Math.hypot(Field.hero.nx-79,Field.hero.ny-301)<2,null,{timeout:20000});
  await page.waitForFunction(()=>!!Field.orrerySprites && !!Field.orrerySprites.img.epochengine,null,{timeout:60000});
  const data=await page.evaluate(()=>{
    const zones=Field._debug.zones,z=zones[15],kinds=Field.orrerySprites.meta.kinds;
    return {count:zones.length,name:z.name,theme:z.theme,levels:z.levels,quests:z.quests.length,
      spawns:z.slimes.length,npcs:z.npcs.length,objects:z.objects.length,kinds,
      art:['clockwall','blackspire','cogstone','timegrass','hourpillar','stillpoint','epoch_crown'].every(k=>!!City.art[k]),
      sizes:kinds.map(k=>[Field.orrerySprites.img[k].naturalWidth,Field.orrerySprites.img[k].naturalHeight]),
      frames:kinds.map(k=>Field.frameOf(Field.orrerySprites,k)),
      map:WorldMap._layout.length,legend:kinds.every(k=>WorldMap._kinds[k]?.[1]>=50),gate:zones[14].portals.find(p=>p.id==='prism_orrery_gate')};
  });
  const seamTo=ZP.portals.filter(p=>p.seam).map(p=>p.to);
  check(data.count>15 && data.name===ZO.name && data.theme==='orrery' && data.levels.join(',')===ZO.levels.join(','),'Zone and level range load');
  check(data.kinds.length===6 && (STUB || data.sizes.every(([w,h],i)=>w===data.frames[i].w*8 && h===data.frames[i].h*5)),'Six complete enemy atlases load');
  check(data.art && data.map>0 && data.legend,'Scenery and map legend load');
  check(data.npcs===ZO.npcs.length && data.quests===ZO.quests.length && data.spawns===ZO.slimes.length && data.objects>=300,'Refuge, quests and monster bands load');
  check(data.gate?.to===15 && seamTo.includes(15),'the Prismwaste reaches the Orrery over the seam');
  await page.screenshot({path:path.join(world.artifacts,'orrery-arrival.png')});
  await debug({op:'teleport',zone:15,x:64,y:52});
  await page.waitForFunction(()=>Field.zone===15,null,{timeout:10000});
  await page.waitForTimeout(800);
  await page.screenshot({path:path.join(world.artifacts,'orrery-rings.png')});
  // the seam: from the Prismwaste's side, walk into the Orrery's ground (no banner, no bounce back)
  await debug({op:'teleport',zone:14,x:start[0],y:start[1]});
  await page.waitForFunction(([x,y])=>Field.zone===14 && Math.hypot(Field.hero.nx-x,Field.hero.ny-y)<2,[start[0],start[1]],{timeout:20000});
  await page.waitForTimeout(1500);
  const keys=keysFor([-inward[0],-inward[1]]);
  for(const key of keys) await page.keyboard.down(key);
  await page.waitForFunction(()=>Field.zone===15,null,{timeout:30000});
  for(const key of keys) await page.keyboard.up(key);
  await page.waitForTimeout(500);
  check(await page.evaluate(()=>Field.zone===15 && Field.zoneTheme==='orrery'),'the seam carries the hero from the Prismwaste into the Orrery');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Orrery UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
