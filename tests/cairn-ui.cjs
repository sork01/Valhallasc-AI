// Private real-browser checks and real game captures of The Cairnspine.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-cairn-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(v,message)=>{assert.ok(v,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:90,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const capture=async name=>{const png=await page.evaluate(()=>document.querySelector('#fieldcv').toDataURL('image/png'));fs.writeFileSync(path.join(world.artifacts,name),Buffer.from(png.split(',')[1],'base64'));};
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('FrostUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.cairnSprites?.img.stormcondor,null,{timeout:60000});
  const data=await page.evaluate(()=>{const z=Field._debug.zones,a=z[27],src=Field.cairnSprites;return {count:z.length,name:a.name,theme:a.theme,levels:a.levels,npcs:a.npcs.length,quests:a.quests.length,enemies:a.slimes.length,boulders:a.objects.filter(o=>o.kind==='cairn_boulder').length,trees:a.objects.filter(o=>o.kind==='cairn_dead_tree').length,gates:[z[26].portals.find(p=>p.id==='frostwake_cairn_gate'),a.portals.find(p=>p.id==='cairn_frostwake_gate')],kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),art:['cairn_boulder','cairn_dead_tree','cairn_watchhall','cairn_thunder_gate'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,travel:a.npcs.find(n=>n.id==='travel_boulderwatch')};});
  check(data.count===29&&data.name==='The Cairnspine'&&data.theme==='cairnspine'&&data.levels.join(',')==='90,95','Level 90–95 mountain loads');
  check(data.npcs===10&&data.quests===10&&data.enemies===43&&data.boulders>=100&&data.trees>=70,'Hub, quests, elite territories, boulders and leafless trees load');
  check(data.kinds.length===13&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Thirteen PixelFlow atlases load');
  check(data.art&&data.layout===29,'Mountain scenery and world-map placement load');
  check(data.gates.every(Boolean)&&data.gates[0].to===27&&data.gates[1].to===26,'Reciprocal High Pass gates load');
  check(data.travel?.travelLinks.includes('travel_frostwake')&&data.travel?.art==='cairn_travel','Travel Master Asta has unique art and return service');
  let ref=701;const debug=async command=>check(await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,ref++]),`Send ${command.op}`);
  async function stage(x,y,label){await debug({op:'teleport',zone:27,x,y});await page.waitForFunction(([x,y])=>Field.zone===27&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<3,[x,y],{timeout:15000});await page.waitForTimeout(950);await page.screenshot({path:path.join(world.artifacts,`cairn-${label}.png`)});await capture(`cairn-${label}-clean.png`);}
  await stage(30,145,'hub');check(await page.evaluate(()=>Field.zoneTheme==='cairnspine'&&City.npcs.length===10),'Boulderwatch paints live');
  await stage(57,70,'singing-cairn');
  await stage(107,80,'whitebark-grove');
  await stage(136,13,'thunderheart-gate');
  check(await page.evaluate(()=>Field._debug.zones[27].slimes.filter(s=>['cairnbehemoth','whitebarktitan','stormcondor'].includes(s.kind)).length===3),'Three unique elite kinds are placed');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Cairnspine UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
