const { run, replace, debug, record } = require('./lib/touch.cjs');
const suite = {
  name: 'quest-window',
  mutate(page) {
    if (process.env.MUTATE === 'accept') return replace(page, 'city.js', "window.Quests?.update(packet.quests); close(); return;", "window.Quests?.update(packet.quests); return;");
    return replace(page, 'quests.js', 'b.innerHTML = Inventory.icon(item);', "b.textContent = item.name;");
  },
  async test({ player, check, sleep, width, height, out }) {
    const page = await player('QuestWindows',process.env.QUEST_DESKTOP?{isMobile:false,hasTouch:false}:{});
    const press = async target => {
      if (!process.env.QUEST_DESKTOP && !await target.isVisible()) {
        const id = await target.evaluate(n => n.closest('.pause')?.id);
        const list = page.locator(`#${id} .quest-mobile-tabs [data-quest-pane="list"]`);
        if (await list.isVisible()) await list.tap();
      }
      return process.env.QUEST_DESKTOP ? target.click() : target.tap();
    };
    async function visit(zone, id) {
      const n = await page.evaluate(({zone,id}) => [WORLD_MAP,...WORLD_MAP.zones][zone].npcs.find(n => n.id === id), {zone,id});
      await debug(page,{op:'teleport',zone,x:n.x,y:n.y+1});
      await page.waitForFunction(({zone,n})=>Field.zone===zone&&Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,{zone,n});
      await page.evaluate(id=>Field.visitNpc(id),id); await page.locator('#npc-dialogue').waitFor({state:'visible'});
      await sleep(600);
    }
    await press(page.locator('#inventory-open'));
    const bagSize = (await page.locator('#inventory-list .item-tile').first().boundingBox()).width;
    await page.keyboard.press('Escape');
    await visit(0,'gatekeeper');
    const gossip=await page.evaluate(()=>{
      const shown=q=>!!document.querySelector(q)?.getClientRects().length, paper=document.getElementById('npc-quest-page'), row=document.querySelector('#npc-quest-list [data-quest="slime_patrol"]'), bye=document.getElementById('npc-quest-close').getBoundingClientRect(), frame=document.querySelector('#npc-dialogue .gossip-window').getBoundingClientRect();
      return shown('#npc-text') && shown('#npc-portrait') && paper.contains(row) && row.querySelector('.gossip-icon').textContent==='!' && bye.width>0 && bye.right>frame.right-frame.width*.15 && document.getElementById('npc-quest-close').textContent.trim().length>0;
    });
    check(gossip,'the greeting shows the portrait, quest rows on the parchment and Goodbye at the bottom right');
    await page.screenshot({path:`${out}/npc-gossip-${width}x${height}.png`});
    await press(page.locator('#npc-quest-list [data-quest="slime_patrol"]'));
    const layout=await page.evaluate(()=>{
      const root=document.getElementById('npc-dialogue'), shell=root.querySelector('.gossip-window'), list=document.getElementById('npc-quest-list').getBoundingClientRect(), body=root.querySelector('.gossip-parchment').getBoundingClientRect(), actions=document.getElementById('npc-quest-actions').getBoundingClientRect(), frame=shell.getBoundingClientRect(), cv=document.getElementById('fieldcv').getBoundingClientRect();
      const phone=matchMedia('(pointer: coarse) and (max-width: 900px), (pointer: coarse) and (max-height: 500px)').matches;
      const accept=root.querySelector('[data-action="accept"]').getBoundingClientRect(), decline=root.querySelector('[data-action="decline"]').getBoundingClientRect();
      return !shell.classList.contains('quest-panel') && list.width===0 && body.width>frame.width*.9 && accept.left<frame.left+frame.width*.2 && decline.right>frame.right-frame.width*.2 && !document.getElementById('npc-quest-close').getClientRects().length && actions.top>=body.bottom-1 && frame.left>=cv.left-1 && frame.right<=cv.right+1 && frame.top>=cv.top-1 && frame.bottom<=cv.bottom+1;
    });
    check(layout,'the quest page is one parchment column with Accept at the bottom left and Decline at the bottom right, within the viewport');
    check(await page.evaluate(()=>[...document.querySelectorAll('#npc-quests .quest-detail h5')].map(h=>h.textContent).join('|')===[Locale.translate('Quest Objectives'),Locale.translate('Rewards')].join('|')),'the page reads title, story, Quest Objectives, Rewards');
    await page.waitForFunction(()=>!document.getElementById('announce').children.length);
    await page.screenshot({path:`${out}/quest-accept-classic-${width}x${height}.png`});
    const reward = page.locator('#npc-quests .quest-reward-icon');
    const r = await reward.boundingBox();
    check(r && Math.abs(r.width-r.height)<1 && r.width>=(process.env.QUEST_DESKTOP?39.9:43.9) && bagSize>0,'reward icon is a square of touchable size');
    check(await page.locator('#npc-quests .quest-reward-cell .quest-reward-name').textContent().then(t=>t.includes('Moonstone')),'the reward sits on a plate with its name beside the icon');
    check(await reward.locator('[data-icon], svg').count()>0,'reward renders the bag artwork');
    check(await reward.textContent()==='', 'item names are absent from the reward list');
    await reward.hover(); await page.locator('#item-tooltip').waitFor({state:'visible'});
    check(await page.locator('#item-tooltip').textContent().then(t=>t.includes('Moonstone')&&t.includes('Defense')||t.includes('defense')), 'hover shows normal reward stats');
    await press(reward); check(await page.locator('#item-tooltip').isVisible(),'touch shows reward tooltip');
    await page.locator('#npc-dialogue [data-action="accept"]').focus(); await page.keyboard.press('Enter');
    await page.locator('#npc-dialogue').waitFor({state:'hidden'});
    await page.evaluate(()=>Quests.show());
    check(await page.locator('#quest-list [data-quest="slime_patrol"]').count()===1,'accepted quest appears in journal without another click');
    await press(page.locator('#quest-list [data-quest="slime_patrol"]'));
    await page.locator('#quest-page [data-quest="slime_patrol"] .quest-reward-icon').waitFor({state:'visible'});
    check(await page.locator('#quest-page [data-quest="slime_patrol"] .quest-reward-icon').count()===1,'journal uses the same reward icon');
    await page.keyboard.press('Escape');
    await debug(page,{op:'quest',id:'slime_patrol',action:'complete'});
    await visit(0,'gatekeeper'); await press(page.locator('#npc-quest-list [data-quest="slime_patrol"]'));
    check(await page.locator('#npc-quest-actions [data-action="claim"]').isVisible(),'ready quests use Complete Quest in the fixed red footer');
    await page.screenshot({path:`${out}/quest-turnin-classic-${width}x${height}.png`});
    await press(page.locator('#npc-quest-actions [data-action="claim"]'));
    await page.waitForFunction(()=>Field.hero.quests.find(q=>q.id==='slime_patrol')?.claimed);
    check(await page.evaluate(()=>Inventory.quantity('necklace_moonstone_l1_green')>0),'styled turn-in grants its real item reward through the server');
    await page.keyboard.press('Escape');
    await visit(0,'guide'); await press(page.locator('#npc-quest-list [data-quest="arena_alder_40"]'));
    await debug(page,{op:'set_level',level:1}); await page.waitForFunction(()=>Field.hero.level===1);
    await press(page.locator('#npc-dialogue [data-action="accept"]'));
    await page.waitForFunction(()=>document.querySelector('#npc-notice').textContent.includes('You are level 1'));
    check(await page.locator('#npc-dialogue').isVisible(),'server-refused acceptance leaves conversation open with its reason');
    await page.keyboard.press('Escape'); await debug(page,{op:'set_level',level:40});
    await debug(page,{op:'quest',id:'astral_welcome',action:'complete'});
    await visit(13,'astral_steward'); await press(page.locator('#npc-quest-list [data-quest="astral_welcome"]'));
    const ids = await page.evaluate(()=>WORLD_MAP.zones[12].quests.find(q=>q.id==='astral_welcome').rewardChoices.mage);
    const choices = page.locator('#npc-quests .quest-reward-icon[data-action="claim"]');
    check((await choices.evaluateAll(nodes=>nodes.map(n=>n.dataset.item))).join(',')===ids.join(','),'only own-class reward choices appear');
    const materials = await page.evaluate(()=>WORLD_ITEMS.filter(i=>i.kind==='material').slice(0,16).map(i=>i.id));
    for(const item of materials) await debug(page,{op:'give_item',item,quantity:1,force:true});
    await sleep(700); await record(page);
    if(process.env.QUEST_DESKTOP) await choices.first().hover(); else await press(choices.first());
    check(await page.locator('#item-tooltip').isVisible() && await page.evaluate(()=>!touchSent.some(m=>m.offer?.startsWith('quest:claim:'))),'preview shows a choice without claiming');
    await press(choices.first());
    await page.waitForFunction(()=>document.querySelector('#npc-notice').textContent.toLowerCase().includes('bag'));
    check(await page.locator('#npc-quests .quest-detail[data-quest="astral_welcome"]').count()===1,'refused turn-in keeps its parchment, choices and reason visible');
    check(await page.locator('#npc-quest-list [data-quest="astral_welcome"][data-status="ready"]').count()===1,'full bag keeps reward ready');
    for(const item of materials) await debug(page,{op:'take_item',item,quantity:1});
    await sleep(650); if(await page.locator('#npc-quest-list [data-quest="astral_welcome"]').isVisible()) await press(page.locator('#npc-quest-list [data-quest="astral_welcome"]')); await press(choices.first()); if(!process.env.QUEST_DESKTOP) await press(choices.first());
    await page.waitForFunction(id=>Inventory.quantity(id)>0,ids[0]);
    check(await page.locator('#npc-dialogue').isVisible(),'successful claim retains the conversation');
    await page.screenshot({path:`${out}/quest-window-${width}x${height}.png`});
    await page.keyboard.press('Escape'); await visit(0,'merchant');
    await press(page.locator('#npc-offers [data-view="buy"]'));
    check(await page.locator('#npc-dialogue').evaluate(n=>n.classList.contains('merchant-mode') && !n.querySelector('.gossip-window').classList.contains('quest-panel')) && await page.locator('.merchant-slot').first().isVisible(),'returning to merchant services restores the shop and its visible stock');
    await page.context().close();
  }
};
module.exports=suite;
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
