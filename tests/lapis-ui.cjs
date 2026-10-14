// Private live-browser check and real captures of the Lapis Erg oases and astrolabe.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'valhallasc-lapis-ui',version:'1.0.0'});
let browser,started=false,checks=0;
const check=(v,message)=>{assert.ok(v,message);checks++;};
async function call(name,args={}){const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,`${name}: ${JSON.stringify(r.content)}`);return r.structuredContent;}
(async()=>{
  await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'}));
  const world=await call('start_world',{startLevel:80,levelSpread:0});started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const capture=async name=>{const png=await page.evaluate(()=>document.querySelector('#fieldcv').toDataURL('image/png'));fs.writeFileSync(path.join(world.artifacts,name),Buffer.from(png.split(',')[1],'base64'));};
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!/401|Failed to load resource/.test(m.text()))errors.push(m.text());});
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('LapisUI');await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.lapisSprites?.img.mirageroc,null,{timeout:60000});
  const data=await page.evaluate(()=>{const z=Field._debug.zones,a=z[25],src=Field.lapisSprites;return {count:z.length,name:a.name,theme:a.theme,levels:a.levels,npcs:a.npcs.length,quests:a.quests.length,enemies:a.slimes.length,oases:a.objects.filter(o=>o.kind==='lapis_oasis').length,seal:a.futureInstance,gates:[z[23].portals.find(p=>p.id==='canopy_lapis_gate'),a.portals.find(p=>p.id==='lapis_canopy_gate')],kinds:src.meta.kinds,sizes:src.meta.kinds.map(k=>[src.img[k].naturalWidth,src.img[k].naturalHeight]),art:['lapis_oasis','lapis_astrolabe','lapis_date_palm','lapis_caravan_tent'].every(k=>!!City.art[k]),layout:WorldMap._layout.length,travel:a.npcs.find(n=>n.id==='travel_azure_wells')};});
  check(data.count>=40&&data.name==='The Lapis Erg'&&data.theme==='lapiserg'&&data.levels.join(',')==='80,85','Level 80–85 desert loads');
  check(data.npcs===9&&data.quests===12&&data.enemies===42&&data.oases===3,'Oases, quest hub and encounters load');
  check(data.kinds.length===11&&(STUB||data.sizes.every(([w,h])=>w===768&&h===480)),'Eleven PixelFlow atlases load');
  check(data.art&&data.layout===35,'Desert scenery and world-map placement load');
  check(data.gates.every(Boolean)&&data.gates[0].to===25&&data.gates[1].to===23,'Reciprocal Sunroad gates load');
  check(data.travel?.travelLinks.includes('travel_veyrroot')&&data.travel?.art==='lapis_travel','Travel Master Nadir has unique art and return service');
  check(data.seal?.status==='open'&&data.seal?.name==='The Sunken Astrolabe','Instance entrance is open');
  let ref=601;const debug=async command=>check(await page.evaluate(([command,ref])=>Online.send({type:'debug',ref,command}),[command,ref++]),`Send ${command.op}`);
  async function stage(x,y,label){await debug({op:'teleport',zone:25,x,y});await page.waitForFunction(([x,y])=>Field.zone===25&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<3,[x,y],{timeout:15000});await page.waitForTimeout(950);await page.screenshot({path:path.join(world.artifacts,`lapis-${label}.png`)});await capture(`lapis-${label}-clean.png`);}
  await stage(29,127,'hub');check(await page.evaluate(()=>Field.zoneTheme==='lapiserg'&&City.npcs.length===9),'Azure Wells paints live');
  await stage(67,72,'mirror-oasis');
  await stage(116,95,'east-oasis');
  await stage(132,29,'astrolabe');
  check(await page.evaluate(()=>Field._debug.zones[25].portals.some(p=>p.id==='lapis_astrolabe_gate'&&p.to===34)&&Field.zone===25),'Astrolabe has a playable dungeon portal');
  check(errors.length===0,`No browser errors: ${errors.join('; ')}`);
  console.log(`Lapis UI: ${checks} checks; screenshots in ${world.artifacts}`);
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();});
