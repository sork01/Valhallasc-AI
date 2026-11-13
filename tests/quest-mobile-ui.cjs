// Quest-only touch layout checks against the private server, without grinding.
const { run, debug, record } = require('./lib/touch.cjs');
const phone = (w,h) => !process.env.QUEST_MOUSE && (w<=900 || h<=500);
async function swipe(page, selector) {
  const r=await page.locator(selector).boundingBox(), session=await page.context().newCDPSession(page);
  const x=r.x+r.width*.65, y=r.y+r.height*.82;
  await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
  for(let i=1;i<=12;i++) {
    await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-r.height*.65*i/12}]});
    await page.waitForTimeout(20);
  }
  await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await session.detach();await page.waitForTimeout(250);
}
const suite={name:'quest-mobile',async test({player,check,width,height,out}){
 const isPhone=phone(width,height), mouse=!!process.env.QUEST_MOUSE, press=n=>mouse?n.click():n.tap();
 const page=await player('QuestMobile',{lang:process.env.QUEST_LANG||'en',...(mouse?{isMobile:false,hasTouch:false}:{})});
 const packets=[];page.on('websocket',ws=>ws.on('framereceived',({payload})=>packets.push(JSON.parse(payload.toString()))));
 async function quest(id,action){await debug(page,{op:'quest',id,action});await page.waitForFunction(({id,action})=>{const p=Field.hero.quests.find(q=>q.id===id);if(!p)return false;if(action==='accept')return !p.claimed;const q=[WORLD_MAP,...WORLD_MAP.zones].flatMap(z=>z.quests||[]).find(q=>q.id===id);return q.objectives.every((o,i)=>p.counts[i]>=o.count);},{id,action});}
 async function settled(){await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
 async function layout(root,list,detail) {
  await settled();const result=await page.evaluate(({root,list,detail})=>{
   const shell=document.querySelector(root),pane=document.querySelector(detail), nav=document.querySelector(list),s=document.getElementById('stage').getBoundingClientRect(),r=shell.getBoundingClientRect(),p=pane.getBoundingClientRect(),n=nav.getBoundingClientRect(),footer=shell.querySelector('.journal-footer').getBoundingClientRect();
   const tabs=shell.querySelector('.quest-mobile-tabs');
   return{fits:r.left>=s.left-1&&r.right<=s.right+1&&r.top>=s.top-1&&r.bottom<=s.bottom+1,noOuterScroll:shell.scrollHeight<=shell.clientHeight+1,tabs:!!tabs.getClientRects().length,list:!!nav.getClientRects().length,detail:!!pane.getClientRects().length,pageWide:p.width>=r.width*.9,listWide:n.width>=r.width*.9,reading:p.height,footerFixed:footer.bottom<=r.bottom+1&&footer.top>=p.bottom-1,targets:[...shell.querySelectorAll('button,summary')].filter(b=>{const r=b.getBoundingClientRect();return r.width&&r.height&&r.top>=s.top&&r.bottom<=s.bottom&&getComputedStyle(b).visibility!=='hidden';}).every(b=>{const r=b.getBoundingClientRect();return r.height>=43.8&&r.width>=43.8;})};
  },{root,list,detail});console.log('layout',root,JSON.stringify(result));
  check(result.fits&&result.noOuterScroll,'quest frame fits the stage without scrolling its header or footer');
  check(result.tabs===isPhone,'phone navigation is shown only on short or narrow touch screens');
  if(!mouse)check(result.targets,'visible quest buttons and group headings remain 44 physical pixels');
  if(isPhone)check(result.list!==result.detail&&(result.list?result.listWide:result.pageWide),'the active phone pane fills the window width');
  else check(result.list&&result.detail,'larger/tablet and desktop layouts retain both panes');
  if(result.detail)check(result.reading>=140&&result.footerFixed,'readable parchment and actions stay above the fixed footer');
 }
 if(isPhone && process.env.QUEST_LANG==='sv')check(await page.evaluate(()=>Locale.translate('Quest list')==='Uppdragslista'),'new mobile navigation has the hand-written Swedish translation');
 await quest('slime_patrol','accept');await quest('welcome','accept');
 await page.evaluate(()=>Quests.show());
 const j='#quest-journal', jShell=j+' .quest-panel',jList=j+' [data-quest-pane="list"]',jDetail=j+' [data-quest-pane="detail"]';
 await layout(jShell,'#quest-list','#quest-page');
 await press(page.locator('#quest-list [data-quest="slime_patrol"]'));
 await layout(jShell,'#quest-list','#quest-page');
 check(await page.locator('#quest-page h4').textContent().then(t=>!!t),'tapping a quest opens its description');
 await record(page);
 if(isPhone){
  check(await page.evaluate(()=>document.activeElement===document.getElementById('quest-page')),'phone selection moves focus onto the visible parchment');
  await swipe(page,'#quest-page');check(await page.locator('#quest-page').evaluate(n=>n.scrollTop>30),'a real touch swipe scrolls the quest parchment');
  const scroll=await page.locator('#quest-page').evaluate(n=>n.scrollTop);
  await press(page.locator(jList));await press(page.locator(jDetail));
  check(await page.locator('#quest-page').evaluate((n,scroll)=>n.scrollTop>=scroll-3,scroll),'switching panes preserves reading position');
  check(await page.evaluate(()=>!touchSent.some(m=>m.type==='quest_abandon'||m.offer?.startsWith('quest:claim:'))),'scrolling and switching panes sends no quest action');
 }
 await press(page.locator('#quest-controls [data-action="track"]'));
 check(await page.evaluate(()=>Quests.tracked==='slime_patrol'),'phone Track action still selects authoritative guidance');
 await quest('slime_patrol','complete');
 check(await page.locator('#quest-page').isVisible()&&await page.locator('#quest-page .complete').count()>0,'live progress keeps the selected mobile detail open');
 await page.waitForFunction(()=>!document.getElementById('announce').children.length);
 await page.screenshot({path:`${out}/quest-mobile-journal-${width}x${height}-${process.env.QUEST_LANG||'en'}.png`});
 if(isPhone){await press(page.locator(jList));await press(page.locator('#quest-list [data-quest="welcome"]'));}
 await press(page.locator('#quest-controls [data-action="abandon"]'));
 check(await page.locator('#quest-page [role="alert"]').isVisible(),'mobile abandon still requires confirmation');
 await press(page.locator('#quest-page [role="alert"] button'));
 check(await page.evaluate(()=>Field.hero.quests.some(q=>q.id==='welcome'&&!q.claimed)),'cancelling abandonment keeps the quest');
 await press(page.locator('#quest-close'));check(!await page.locator(j).isVisible(),'the persistent Close button dismisses the journal');
 const npc=await page.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='gatekeeper'));
 await debug(page,{op:'teleport',zone:0,x:npc.x,y:npc.y+1});await page.evaluate(()=>Field.visitNpc('gatekeeper'));await page.locator('#npc-dialogue').waitFor({state:'visible'});
 const n='#npc-dialogue';
 // The conversation is one parchment column at every size: the greeting with its quest rows, or one quest's page over fixed footer buttons.
 async function npcLayout(questPage) {
  await settled();const result=await page.evaluate(()=>{
   const shell=document.querySelector('#npc-dialogue .gossip-window'),s=document.getElementById('stage').getBoundingClientRect(),r=shell.getBoundingClientRect(),p=document.getElementById('npc-quest-page').getBoundingClientRect(),footer=shell.querySelector('.gossip-footer').getBoundingClientRect(),face=document.getElementById('npc-portrait').getBoundingClientRect();
   const shown=q=>!!document.querySelector(q)?.getClientRects().length;
   return{fits:r.left>=s.left-1&&r.right<=s.right+1&&r.top>=s.top-1&&r.bottom<=s.bottom+1,journalFrame:shell.classList.contains('quest-panel'),tabs:shown('#npc-dialogue .quest-mobile-tabs'),rows:shown('#npc-quest-list .journal-quest'),goodbye:shown('#npc-quest-close'),greeting:shown('#npc-text'),pageWide:p.width>=r.width*.9,reading:p.height,footerFixed:footer.bottom<=r.bottom+1&&footer.top>=p.bottom-1,face:face.width>=40&&face.height>=40,
    targets:[...shell.querySelectorAll('button')].filter(b=>{const r=b.getBoundingClientRect();return r.width&&r.height&&r.top>=s.top&&r.bottom<=s.bottom;}).every(b=>{const r=b.getBoundingClientRect();return r.height>=43.8&&r.width>=43.8;})};
  });console.log('npc layout',JSON.stringify(result));
  check(result.fits&&!result.journalFrame&&!result.tabs&&result.pageWide&&result.face,'the conversation is one parchment column with the speaker portrait, inside the stage');
  check(questPage?!result.rows&&!result.goodbye&&!result.greeting:result.rows&&result.goodbye&&result.greeting,questPage?'a quest page replaces the greeting and its rows':'the greeting lists quests as rows above a Goodbye button');
  check(result.reading>=140&&result.footerFixed,'readable parchment and actions stay above the fixed footer');
  if(!mouse)check(result.targets,'visible conversation buttons remain 44 physical pixels');
 }
 await npcLayout(false);
 await press(page.locator('#npc-quest-list [data-quest="slime_patrol"]'));await npcLayout(true);
 check(await page.locator('#npc-quest-actions [data-action="claim"]').isVisible(),'turn-in action stays visible in the phone footer');
 await page.waitForFunction(()=>!document.getElementById('announce').children.length);
 await page.screenshot({path:`${out}/quest-mobile-turnin-${width}x${height}-${process.env.QUEST_LANG||'en'}.png`});
 await press(page.locator('#npc-quest-actions [data-action="claim"]'));
 await page.waitForFunction(()=>Field.hero.quests.find(q=>q.id==='slime_patrol')?.claimed);
 check(await page.evaluate(()=>Inventory.quantity('necklace_moonstone_l1_green')>0),'touch turn-in awards the real quest item');
 await press(page.locator('#npc-quest-close'));
 await debug(page,{op:'quest',id:'slime_patrol',action:'reset'});
 await page.evaluate(()=>Field.visitNpc('gatekeeper'));await page.locator('#npc-dialogue').waitFor({state:'visible'});
 await press(page.locator('#npc-quest-list [data-quest="slime_patrol"]'));
 const accept=page.locator('#npc-quest-actions [data-action="accept"]');
 check(await accept.isVisible(),'Accept stays reachable without scrolling the parchment');
 if(isPhone){await swipe(page,'#npc-quest-page');check(await accept.isVisible(),'swiping NPC text keeps the Accept action fixed');await press(page.locator('#npc-quest-actions [data-action="decline"]'));check(await page.locator('#npc-quest-list').isVisible(),'Decline returns to the greeting and its quest rows');await press(page.locator('#npc-quest-list [data-quest="slime_patrol"]'));}
 await press(accept);await page.locator(n).waitFor({state:'hidden'});
 check(await page.evaluate(()=>Field.hero.quests.some(q=>q.id==='slime_patrol'&&!q.claimed)),'touch acceptance closes only after the server accepts');
 await page.context().close();
}};
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
module.exports=suite;
