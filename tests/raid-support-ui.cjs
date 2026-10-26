// Raid strength only: actual contracts, copy isolation, live stats and visible UI.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..'),client=new Client({name:'raid-support-ui',version:'1'});
let browser,world,checks=0;
const check=(v,t)=>{assert.ok(v,t);checks++;};
const call=async(name,args={})=>{const r=await client.callTool({name,arguments:args});assert.ok(!r.isError,JSON.stringify(r.content));return r.structuredContent;};
(async()=>{
 await client.connect(new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe',env:{...process.env}}));
 world=await call('start_world',{startLevel:99,levelSpread:0,godMode:true});
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
 await page.goto(world.url);await page.locator('#start').click();await page.locator('#login-guest').click();
 await page.locator('#name').fill('Raid Strength');await page.locator('#go').click({timeout:60000});
 await page.waitForFunction(()=>Online.connected&&Field.hero,null,{timeout:60000});
 const base=await page.evaluate(()=>Field.hero.attack);
 const debug=command=>page.evaluate(command=>Online.send({type:'debug',command}),command);
 const interact=async offer=>{
  // Real NPC services reject another transaction within half a second.
  await page.waitForTimeout(650);
  return page.evaluate(offer=>Online.send({type:'interact',npc:'cf_quartermaster',offer}),offer);
 };
 await debug({op:'teleport',zone:46,x:35,y:303});
 await page.waitForFunction(()=>Field.zone===46&&Field.hero.raidSupport?.others===0);
 check(await page.evaluate(base=>Field.hero.attack===base,base),'A solo hero gets no bonus');
 await debug({op:'set_gold',gold:2000000});
 const classes=['mage','assassin','priest','hunter','warrior','mage','assassin','priest','hunter'];
 for(const [n,cls] of classes.entries()){
  await interact('merc_'+cls);
  await page.waitForFunction(n=>Field.hero.raidSupport?.others===n+1,n,{timeout:10000});
  check(await page.evaluate(({n,base})=>Field.hero.attack===base*(1+(n+1)*2)&&Field.hero.raidSupport.damageReductionPercent===(n+1)*5,{n,base}),'Mercenary '+(n+1)+' updates actual attack and reduction');
 }
 check(await page.evaluate(()=>Field.remotePlayers.length===9&&Field.remotePlayers.every(p=>p.raidSupport?.others===9)),'All nine mercenaries receive the full bonus too');
 await page.keyboard.press('e');await page.locator('#equipment').waitFor({state:'visible'});
 await page.locator('.raid-strength').waitFor();
 check((await page.locator('.raid-strength').textContent()).includes('+1800% attack · 45% damage reduction (9 allies)'),'Character UI shows the full raid bonus');
 await page.locator('.raid-strength').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(world.artifacts,'raid-support-desktop.png')});
 await page.setViewportSize({width:844,height:390});await page.locator('.raid-strength').scrollIntoViewIfNeeded();
 check(await page.locator('.raid-strength').isVisible(),'Raid bonus remains reachable on mobile');
 await page.screenshot({path:path.join(world.artifacts,'raid-support-mobile.png')});
 await page.keyboard.press('Escape');
 await call('connect_bot',{bot:'OtherCopy',class:'mage'});
 await call('teleport',{bot:'OtherCopy',to:{zone:46,x:35,y:303}});
 check(await page.evaluate(()=>Field.hero.raidSupport.others===9&&Field.remotePlayers.length===9),'Another raid copy does not add a fighter');
 const other=await call('inspect_world',{bot:'OtherCopy',events:0});
 check(other.snapshot?.raidSupport?.others===0,'The other copy remains solo');
 await interact('merc_dismiss');
 await page.waitForFunction(()=>Field.hero.raidSupport?.others===0&&Field.remotePlayers.length===0);
 check(await page.evaluate(base=>Field.hero.attack===base,base),'Dismissing mercenaries immediately removes their attack bonus');
 await interact('merc_mage');await page.waitForFunction(()=>Field.hero.raidSupport?.others===1);
 await debug({op:'teleport',zone:45,x:127,y:25});
 await page.waitForFunction(()=>Field.zone===45&&!Field.hero.raidSupport);
 check(await page.evaluate(base=>Field.hero.attack===base,base),'Leaving the raid restores base attack');
 check(await page.locator('.raid-strength').count()===0,'The raid-only UI disappears outside');
 const sw=await browser.newPage();await sw.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'sv',sound:false})));await sw.goto(world.url);
 check(await sw.evaluate(()=>Locale.translate('Raid strength: +1800% attack · 45% damage reduction (9 allies)')==='Raidstyrka: +1800% attack · 45% skademinskning (9 allierade)'),'Swedish raid bonus text');await sw.close();
 check(errors.length===0,JSON.stringify(errors));
 fs.writeFileSync(path.join(world.artifacts,'raid-support-ui.json'),JSON.stringify({checks,base,fullAttack:base*19,errors},null,2));
 console.log(JSON.stringify({passed:true,checks,artifacts:world.artifacts}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close();if(world)try{await call('stop_world');}catch{}await client.close();
});
