// Raid molten surface only: real render, world anchoring, shore/floor separation and Emberwake comparison.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..'),client=new Client({name:'chained-forge-lava',version:'1'});
let browser,started=false,checks=0;
const check=(value,message)=>{assert.ok(value,message);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
 await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...process.env}}));
 const world=await call('start_world',{godMode:true,startLevel:99,levelSpread:0});started=true;
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(process.env.MUTATE)await page.route('**/chainedforgeart.js',async route=>{const r=await route.fetch();await route.fulfill({response:r,body:(await r.text())+"\nwindow.ChainedForgeArt.background=(g,w,h)=>{g.fillStyle='#63251f';g.fillRect(0,0,w,h);};"});});
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();await page.locator('#name').fill('Molten Artist');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero&&window.ChainedForgeArt,null,{timeout:60000});
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
 const teleport=async(zone,x,y)=>{await debug({op:'teleport',zone,x,y});await page.waitForFunction(([zone,x,y])=>Field.zone===zone&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[zone,x,y],{timeout:20000});await page.waitForTimeout(350);};
 await teleport(46,30,303);await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('area-title')).opacity)<.05);
 // Sample the actual field canvas where the authoritative floor mask says there is no walkway.
 const surface=()=>page.evaluate(()=>{
  const c=document.getElementById('fieldcv'),g=c.getContext('2d'),scale=g.getTransform().a,p=g.getImageData(0,0,c.width,c.height).data,z=WORLD_MAP.zones[45];
  let total=0,hot=0,crust=0;
  for(let y=12;y<c.height-12;y+=6)for(let x=12;x<c.width-12;x+=6){
   const [wx,wy]=Field._debug.s2w(x/scale,y/scale),ix=Math.floor(wx),iy=Math.floor(wy);
   let near=false;for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++)if(ChainedForgeArt.floor(z,ix+dx,iy+dy))near=true;
   if(near)continue;const k=(y*c.width+x)*4,r=p[k],green=p[k+1],b=p[k+2];total++;
   if(r>180&&green>65&&green<210&&b<130)hot++;
   if(r<110&&green<100&&b<110)crust++;
  }return {total,hot,crust,hotRatio:hot/total,crustRatio:crust/total};
 });
 const sample=await surface();check(sample.total>500,'Enough visible unwalkable terrain');
 check(sample.hotRatio>.08,'Glowing molten fissures cover the outside: '+JSON.stringify(sample));
 check(sample.crustRatio>.2,'Dark crust plates remain between the fissures');
 // Equal world positions produce equal texture pixels under two different camera positions.
 const anchor=await page.evaluate(()=>{
  const z=WORLD_MAP.zones[45],make=()=>{const c=document.createElement('canvas');c.width=800;c.height=500;return c;},a=make(),b=make();
  ChainedForgeArt.background(a.getContext('2d'),800,500,0,z,400,1320);
  ChainedForgeArt.background(b.getContext('2d'),800,500,0,z,488,1320);
  const ga=a.getContext('2d'),gb=b.getContext('2d');let equal=0,total=0;
  for(let y=50;y<450;y+=7)for(let x=120;x<740;x+=7){const u=ga.getImageData(x,y,1,1).data,v=gb.getImageData(x-88,y,1,1).data;total++;if(u.every((n,i)=>Math.abs(n-v[i])<=1))equal++;}
  return {equal,total};
 });check(anchor.equal/anchor.total>.99,'Molten texture stays anchored when the camera moves: '+JSON.stringify(anchor));
 // Refactoring the shared color sampler must preserve the original river exactly.
 const old=execFileSync('git',['show','bfc25d3:client/emberwakeart.js'],{cwd:root,encoding:'utf8'});
 const comparison=await page.evaluate(source=>{
  const current=EmberwakeArt;(0,eval)(source);const original=EmberwakeArt;window.EmberwakeArt=current;
  const z={size:8,objects:[{kind:'ew_lava',x:4,y:4,r:3.2}]},G={x0:0,y0:0,ox:-400,oy:-40};
  const render=art=>{const c=document.createElement('canvas');c.width=800;c.height=500;art.molten(c.getContext('2d'),G,8,88,44,z);return c.getContext('2d').getImageData(0,0,800,500).data;};
  const a=render(current),b=render(original);let differences=0,painted=0;for(let i=0;i<a.length;i++){if(a[i]!==b[i])differences++;if(i%4===3&&a[i])painted++;}return {differences,painted};
 },old);check(comparison.painted>10000&&comparison.differences===0,'Emberwake river is pixel-identical to its previous renderer');
 const shots=[['muster',30,303],['bridge',145,277],['throne',108,18],['outer-edge',266,21]];
 for(const view of [{width:1440,height:900,label:'desktop'},{width:844,height:390,label:'mobile'}]){
  await page.setViewportSize({width:view.width,height:view.height});
  for(const [name,x,y]of shots){
   await teleport(46,x,y);await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,`chained-forge-molten-${name}-${view.label}.png`)});
  }
 }
 await page.setViewportSize({width:1440,height:900});await teleport(45,104,92);
 await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,'emberwake-river-reference.png')});
 check(errors.length===0,'No page errors: '+JSON.stringify(errors));
 fs.writeFileSync(path.join(world.artifacts,'chained-forge-lava-result.txt'),JSON.stringify({passed:true,checks,sample,anchor,comparison,errors},null,2));
 console.log(JSON.stringify({passed:true,checks,sample,artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}await client.close();});
