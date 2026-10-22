// RAID-MAP: real private client, every hall at desktop and landscape touch size.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'chained-forge-map-check',version:'1'});
let browser,started=false,checks=0;
const check=(value,label)=>{assert.ok(value,label);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
 await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...process.env}}));
 const world=await call('start_world',{godMode:true,levelSpread:0,startLevel:99});started=true;
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/home/serveperry/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 const errors=[],bad=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&/chainedforge|world\.js/.test(r.url()))bad.push(r.url());});
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#name').fill('Forge Artist');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&window.ChainedForgeArt&&Field.hero,null,{timeout:60000});
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
 const teleport=async(x,y)=>{await debug({op:'teleport',zone:46,x,y});await page.waitForFunction(([x,y])=>Field.zone===46&&Math.hypot(Field.hero.x-x,Field.hero.y-y)<1.5,[x,y],{timeout:20000});};
 await teleport(30,303);
 check(await page.evaluate(()=>Field.zoneTheme==='chained_forge'),'New raid theme loads');
 check(await page.evaluate(()=>DayNight.nightMix===0),'Enclosed raid has no night mix');
 check(await page.locator('#world-weather').textContent().then(t=>t.includes('Indoors')),'Raid is indoors');
 await page.waitForFunction(()=>Number(getComputedStyle(document.getElementById('area-title')).opacity)<.05,null,{timeout:15000});
 await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,'chained-forge-muster.png')});
 // The real quartermaster's dialogue and contract offers.
 await teleport(35,303);
 await page.evaluate(()=>Online.send({type:'interact',npc:'cf_quartermaster'}));
 await page.waitForFunction(()=>document.getElementById('npc-dialogue').textContent.includes('Quartermaster Halla'));
 check(await page.locator('#npc-dialogue').textContent().then(t=>t.includes('Hire a Warrior')),'Quartermaster exposes raid contracts');
 await page.keyboard.press('Escape');
 const halls=await page.evaluate(()=>WORLD_MAP.zones[45].forgeHalls);
 for(const size of [{width:1440,height:900,label:'desktop'},{width:844,height:390,label:'mobile'}]){
  await page.setViewportSize({width:size.width,height:size.height});
  for(const h of halls){
   await teleport(h.x-3,h.y-h.ry+3);await page.waitForTimeout(250);
   check(await page.evaluate(id=>WORLD_MAP.zones[45].forgeHalls.some(h=>h.id===id&&ChainedForgeArt.floor(WORLD_MAP.zones[45],h.x,h.y)),h.id),size.label+' floor '+h.id);
   await page.locator('#fieldcv').screenshot({path:path.join(world.artifacts,`chained-forge-${h.id}-${size.label}-${STUB?'stub':'real'}.png`)});
  }
 }
 // Remove only scenery from the live renderer, then compare actual field pixels.
 await page.waitForTimeout(600);
 await page.evaluate(()=>{
  const cv=document.getElementById('fieldcv');window.__forgeBefore=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
  window.__forgeObjects=Field._debug.objects.slice();
  const kept=Field._debug.objects.filter(o=>!o.kind.startsWith('cf_'));
  Field._debug.objects.splice(0,Field._debug.objects.length,...kept);
 });
 await page.waitForTimeout(300);
 const changed=await page.evaluate(()=>{
  const cv=document.getElementById('fieldcv'),after=cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
  let count=0;for(let i=0;i<after.length;i+=4)if(Math.abs(after[i]-__forgeBefore[i])+Math.abs(after[i+1]-__forgeBefore[i+1])+Math.abs(after[i+2]-__forgeBefore[i+2])>45)count++;
  Field._debug.objects.splice(0,Field._debug.objects.length,...__forgeObjects);return count;
 });check(changed>2000,'Raid scenery visibly changes the actual field render: '+changed+' pixels');
 await page.setViewportSize({width:1440,height:900});
 await page.evaluate(()=>WorldMap.show());
 check(await page.evaluate(()=>WORLD_MAP.zones[45].sealedTemplate),'The published entrance remains sealed');
 check(await page.locator('.wm-tile[data-zone="46"]').count()===0,'Sealed raid is hidden on the world atlas');
 check(await page.evaluate(()=>WorldMap._layout.length===Field._debug.zones.length),'Every file zone has an atlas placement');
 await page.screenshot({path:path.join(world.artifacts,'chained-forge-atlas-sealed.png')});
 await page.keyboard.press('Escape');
 // Probe localization in a fresh Swedish document, as language is fixed on load.
 const sw=await browser.newPage();await sw.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sw.goto(world.url);
 check(await sw.evaluate(()=>Locale.translate('The Chained Forge')==='Den fjättrade smedjan'),'Swedish raid name');
 check(await sw.evaluate(()=>Locale.translate('Quartermaster Halla')==='Kvartermästare Halla'),'Swedish quartermaster');await sw.close();
 check(bad.length===0,'No missing raid assets');check(errors.length===0,JSON.stringify(errors));
 fs.writeFileSync(path.join(world.artifacts,'chained-forge-ui-result.txt'),JSON.stringify({checks,real:!STUB,errors,bad},null,2));
 console.log(JSON.stringify({passed:true,checks,artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(started)try{await call('stop_world');}catch{}await client.close();});
