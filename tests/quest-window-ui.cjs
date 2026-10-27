const { run, replace, debug, record } = require('./lib/touch.cjs');
const suite = {
  name: 'quest-window',
  mutate(page) {
    if (process.env.MUTATE === 'accept') return replace(page, 'city.js', "window.Quests?.update(packet.quests); close(); return;", "window.Quests?.update(packet.quests); return;");
    return replace(page, 'quests.js', 'b.innerHTML = Inventory.icon(item);', "b.textContent = item.name;");
  },
  async test({ player, check, sleep, width, height, out }) {
    const page = await player('QuestWindows');
    async function visit(zone, id) {
      const n = await page.evaluate(({zone,id}) => [WORLD_MAP,...WORLD_MAP.zones][zone].npcs.find(n => n.id === id), {zone,id});
      await debug(page,{op:'teleport',zone,x:n.x,y:n.y+1});
      await page.waitForFunction(({zone,n})=>Field.zone===zone&&Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,{zone,n});
      await page.evaluate(id=>Field.visitNpc(id),id); await page.locator('#npc-dialogue').waitFor({state:'visible'});
      await sleep(600);
    }
    await page.locator('#inventory-open').tap();
    const bagSize = (await page.locator('#inventory-list .item-tile').first().boundingBox()).width;
    await page.keyboard.press('Escape');
    await visit(0,'gatekeeper'); await page.locator('#npc-quests [data-quest="slime_patrol"]').tap();
    const reward = page.locator('#npc-quests .quest-reward-icon');
    const r = await reward.boundingBox();
    check(r && Math.abs(r.width-bagSize)<1 && Math.abs(r.height-bagSize)<1 && r.width>=43.9,'reward uses bag-sized square');
    check(await reward.locator('[data-icon], svg').count()>0,'reward renders the bag artwork');
    check(await reward.textContent()==='', 'item names are absent from the reward list');
    await reward.hover(); await page.locator('#item-tooltip').waitFor({state:'visible'});
    check(await page.locator('#item-tooltip').textContent().then(t=>t.includes('Moonstone')&&t.includes('Defense')||t.includes('defense')), 'hover shows normal reward stats');
    await reward.tap(); check(await page.locator('#item-tooltip').isVisible(),'touch shows reward tooltip');
    await page.locator('#npc-quests [data-action="accept"]').focus(); await page.keyboard.press('Enter');
    await page.locator('#npc-dialogue').waitFor({state:'hidden'});
    await page.evaluate(()=>Quests.show());
    check(await page.locator('#quest-list [data-quest="slime_patrol"]').count()===1,'accepted quest appears in journal without another click');
    await page.locator('#quest-list [data-quest="slime_patrol"] > summary').tap();
    await page.locator('#quest-list [data-quest="slime_patrol"] .quest-reward-icon').waitFor({state:'visible'});
    check(await page.locator('#quest-list [data-quest="slime_patrol"] .quest-reward-icon').count()===1,'journal uses the same reward icon');
    await page.keyboard.press('Escape');
    await visit(0,'guide'); await page.locator('#npc-quests [data-quest="arena_alder_40"]').tap();
    await debug(page,{op:'set_level',level:1}); await page.waitForFunction(()=>Field.hero.level===1);
    await page.locator('#npc-quests [data-action="accept"]').tap();
    await page.waitForFunction(()=>document.querySelector('#npc-notice').textContent.includes('You are level 1'));
    check(await page.locator('#npc-dialogue').isVisible(),'server-refused acceptance leaves conversation open with its reason');
    await page.keyboard.press('Escape'); await debug(page,{op:'set_level',level:40});
    await debug(page,{op:'quest',id:'astral_welcome',action:'complete'});
    await visit(13,'astral_steward'); await page.locator('#npc-quests [data-quest="astral_welcome"]').tap();
    const ids = await page.evaluate(()=>WORLD_MAP.zones[12].quests.find(q=>q.id==='astral_welcome').rewardChoices.mage);
    const choices = page.locator('#npc-quests .quest-reward-icon[data-action="claim"]');
    check((await choices.evaluateAll(nodes=>nodes.map(n=>n.dataset.item))).join(',')===ids.join(','),'only own-class reward choices appear');
    const materials = await page.evaluate(()=>WORLD_ITEMS.filter(i=>i.kind==='material').slice(0,16).map(i=>i.id));
    for(const item of materials) await debug(page,{op:'give_item',item,quantity:1,force:true});
    await sleep(700); await record(page);
    await choices.first().tap();
    check(await page.locator('#item-tooltip').isVisible() && await page.evaluate(()=>!touchSent.some(m=>m.offer?.startsWith('quest:claim:'))),'first touch previews a choice without claiming');
    await choices.first().tap();
    await page.waitForFunction(()=>document.querySelector('#npc-notice').textContent.toLowerCase().includes('bag'));
    check(await page.locator('#npc-quests [data-quest="astral_welcome"][data-status="ready"]').count()===1,'full bag keeps reward ready');
    for(const item of materials) await debug(page,{op:'take_item',item,quantity:1});
    await sleep(650); await page.locator('#npc-quests [data-quest="astral_welcome"]').tap(); await choices.first().tap(); await choices.first().tap();
    await page.waitForFunction(id=>Inventory.quantity(id)>0,ids[0]);
    check(await page.locator('#npc-dialogue').isVisible(),'successful claim retains the conversation');
    await page.screenshot({path:`${out}/quest-window-${width}x${height}.png`}); await page.context().close();
  }
};
module.exports=suite;
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
