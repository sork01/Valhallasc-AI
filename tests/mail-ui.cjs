const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,STUB}=require('./lib/playwright.cjs');
const {TestWorld}=require('../scripts/testing/driver.cjs');
const box=JSON.parse(fs.readFileSync(path.join(__dirname,'../world/mailboxes.txt')))[0];
const items=JSON.parse(fs.readFileSync(path.join(__dirname,'../world/items.txt')));
const bound=items.find(i=>i.class==='warrior'&&!i.starter&&i.kind==='weapon');
const neutral=items.find(i=>['necklace','cloak','accessory','headgear'].includes(i.kind)&&!i.class&&!i.starter&&i.rarity!=='gm');
let checks=0;const ok=(v,label)=>{assert.ok(v,label);checks++;};
(async()=>{
 const w=new TestWorld();let browser;
 try{
  await w.start();await w.connect({bot:'PostFriend'});
  const botAsk=async(request)=>{const old=new Set(w.events);w.bots.get('PostFriend').socket.send(JSON.stringify({type:'mail',npc:box.id,request}));return w.waitFor(()=>w.events.find(e=>!old.has(e)&&e.bot==='PostFriend'&&e.type==='mail'));};
  await w.debug('PostFriend',{op:'teleport',zone:box.zone,x:box.x,y:box.y});
  for(const [label,lang,viewport] of [['desktop','en',{width:1440,height:900}],['phone','sv',{width:844,height:390}]].filter(([label])=>!process.env.MAIL_UI_VIEW||process.env.MAIL_UI_VIEW===label)){
   const before=checks;
   browser=await chromium.launch({headless:true});
   const page=await browser.newPage({viewport,hasTouch:label==='phone',isMobile:label==='phone',reducedMotion:'reduce'});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.addInitScript(lang=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang,sound:false,char:null,draft:null})),lang);
   if (process.env.MUTATE === 'bound') await page.route('**/mail.js', async route => { const response=await route.fetch();const body=(await response.text()).replace('option.disabled = !!a.reason || !a.quantity','option.disabled = false');await route.fulfill({response,body}); });
   await page.goto(w.url);await page.locator('#start').click();await page.locator('#login-guest').click();
   await page.locator('#cls-warrior').click();await page.locator('#name').fill(`Post${label}`);await page.locator('#go').click({timeout:60000});
   await page.waitForFunction(()=>Online.connected&&Field.hero.id);
   if(await page.locator('#low-gfx-dismiss').isVisible())await page.locator('#low-gfx-dismiss').click();
   const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:17,command}),command);
   await debug({op:'set_gold',gold:500});await debug({op:'give_item',item:'slime_gel',quantity:5});await debug({op:'give_item',item:bound.id,quantity:1});await debug({op:'give_item',item:neutral.id,quantity:1});
   await debug({op:'teleport',zone:box.zone,x:box.x,y:box.y});
   await page.waitForFunction(b=>Math.hypot(Field.hero.x-b.x,Field.hero.y-b.y)<.5&&Field.hero.gold===500,box);
   await page.evaluate(id=>Online.send({type:'interact',npc:id}),box.id);
   await page.locator('[data-offer="mail"]').click();await page.locator('#mail-panel').waitFor({state:'visible'});
   ok(await page.locator('#npc-dialogue').isHidden(),`${label}: gossip closed`);
   ok(!await page.evaluate(()=>Field.canAct),`${label}: mail keeps movement stopped`);
   const art=await page.evaluate(async()=>{const image=new Image();image.src='assets/mailbox.png';await image.decode();const c=document.createElement('canvas');c.width=96;c.height=112;const g=c.getContext('2d');g.translate(48,104);Mail.draw(g);const actual=g.getImageData(0,0,96,112).data;g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,96,112);g.drawImage(image,0,0);const source=g.getImageData(0,0,96,112).data;return {equal:actual.every((v,i)=>v===source[i]),solid:source.filter((v,i)=>i%4===3&&v>0).length};});
   ok(art.equal&&art.solid>1000,`${label}: native mailbox bitmap renders without sprite stubs`);
   await page.locator('#mail-compose-tab').click();await page.locator('#mail-recipient').fill('postfriend');await page.locator('#mail-lookup').click();
   await page.waitForFunction(()=>document.querySelector('#mail-recipient-result').textContent==='PostFriend');checks++;
   const options=await page.locator('#mail-item option').evaluateAll(nodes=>nodes.map(n=>({text:n.textContent,disabled:n.disabled})));
   ok(options.some(o=>o.disabled&&o.text.includes(lang==='sv'?'Bunden klassutrustning':'Bound class gear')),`${label}: bound reason visible`);
   await page.locator('#mail-subject').fill(`A gift ${label}`);await page.locator('#mail-body').fill('Inbox\n<img src=x onerror=alert(1)>');await page.locator('#mail-gold').fill('25');
   const option=await page.evaluate(()=>document.querySelector('#mail-item option[data-item="slime_gel"]')?.value);
   assert.ok(option!=null);await page.locator('#mail-item').selectOption(option);await page.locator('#mail-quantity').fill('2');await page.locator('#mail-add').click();
   const gearOption=await page.locator(`#mail-item option[data-item="${neutral.id}"]`).getAttribute('value');await page.locator('#mail-item').selectOption(gearOption);await page.locator('#mail-quantity').fill('1');await page.locator('#mail-add').click();
   ok(await page.locator('#mail-attached > div').count()===2,`${label}: explicit neutral gear copy attached`);
   await page.locator('#mail-review').click();await page.locator('#mail-confirm').waitFor({state:'visible'});
   ok((await page.locator('#mail-confirm-recipient').textContent())==='PostFriend',`${label}: recipient confirmation`);
   await page.locator('#mail-send-confirm').click();await page.waitForFunction(()=>document.querySelector('#mail-notice').dataset.state==='ok'&&document.querySelector('#mail-compose-view').hidden);
   await page.waitForFunction(()=>Inventory.quantity('slime_gel')===3&&Field.hero.gold===475);checks++;
   let p=await botAsk({op:'open'});const l=p.letters.find(l=>l.subject===`A gift ${label}`);assert.ok(l);
   ok(l.contents.gold===25&&l.contents.items[0].quantity===2&&l.contents.gear.length===1,`${label}: UI sent authoritative attachments`);
   await botAsk({op:'return',id:l.id});
   await page.waitForFunction(()=>document.querySelector('#mail-unread').textContent.includes('1'));checks++;
   await page.locator('#mail-inbox-tab').click();await page.locator(`#mail-letters [data-letter="${l.id}"]`).click();
   await page.waitForFunction(()=>!document.querySelector('#mail-reader').hidden);
   ok((await page.locator('#mail-body-view').textContent())==='Inbox\n<img src=x onerror=alert(1)>',`${label}: player text is plain and untranslated`);
   ok(await page.locator('#mail-body-view img').count()===0,`${label}: no HTML execution`);
   ok(await page.locator('#mail-delete').isDisabled(),`${label}: cannot delete pending attachments`);
   await page.locator('#mail-collect').click();await page.waitForFunction(()=>Inventory.quantity('slime_gel')===5&&Field.hero.gold===500);checks++;
   await page.locator('#mail-delete').click();await page.waitForFunction(()=>!document.querySelector('#mail-letters [data-letter]'));checks++;
   await page.locator('#mail-compose-tab').click();
   if(lang==='sv'){
    ok((await page.locator('#mail-title').textContent())==='Brevlåda','Swedish heading');
    ok((await page.locator('#mail-review').textContent())==='Granska brevet','Swedish compose');
   }
   const fit=await page.locator('.mail-window').evaluate(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,w:innerWidth,h:innerHeight,scale:getComputedStyle(n).scale,contentHeight:document.querySelector('.mail-content').getBoundingClientRect().height,grip:!!document.querySelector('.win-grip[data-window="mail-panel"]')};});
   ok(fit.left>=-1&&fit.right<=fit.w+1&&fit.top>=-1&&fit.bottom<=fit.h+1,`${label}: scaled window inside viewport ${JSON.stringify(fit)}`);
   if(label==='phone')ok(fit.contentHeight>=100,`phone: form keeps usable scrolling space ${fit.contentHeight}`);
   ok(fit.grip,`${label}: normal resize grip`);
   await page.screenshot({path:path.join(w.runDir,`mail-${label}-${lang}.png`)});
   await page.locator('#mail-close').click();await page.waitForFunction(()=>Field.canAct);checks++;
   // The minimap mail icon has the unread marker and opens a nearby mailbox.
   await page.evaluate(()=>{const real=Mail.onUnread;Mail.onUnread=(c,t)=>real(c,Math.max(t??0,1));Mail.onUnread(0,1);});   // the icon only exists while you have mail
   await page.locator('#mail-open').click();await page.locator('#mail-panel').waitFor({state:'visible'});
   ok(await page.locator('#pause').isHidden(),`${label}: menu closes behind mail`);
   await debug({op:'teleport',zone:0,x:box.x-12,y:box.y});await page.locator('#mail-panel').waitFor({state:'hidden'});checks++;
   ok(errors.length===0,`${label}: browser errors ${errors.join('; ')}`);
   fs.writeFileSync(path.join(w.runDir,`mail-${label}.json`),JSON.stringify({checks:checks-before,passed:true,lang,viewport},null,2));console.log(`mail-ui ${label}: ${checks-before} checks passed`);
   await page.evaluate(()=>Online.stop());await browser.close();browser=null;
  }
  fs.writeFileSync(path.join(w.runDir,'mail-ui.json'),JSON.stringify({checks,STUB,passed:true},null,2));
  console.log(`mail-ui: ${checks} checks in the requested viewports; artifacts ${w.runDir}`);
 }catch(e){if(browser){const page=browser.contexts()[0]?.pages()[0];await page?.screenshot({path:path.join(w.runDir,'mail-failure.png')}).catch(()=>{});}throw e;}finally{await browser?.close();await w.stop();}
})().catch(e=>{console.error(e);process.exitCode=1;});
