// Focused merchant frame checks. The shared helper refuses uncapped execution.
const { run, replace, debug, record } = require('./lib/touch.cjs');
const suite = {
  name: 'merchant-frame',
  mutate(page) {
    if (process.env.MUTATE === 'layout') return replace(page,'online.css','#npc-dialogue.merchant-mode { grid-template-rows: minmax(0, 1fr); grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);','#npc-dialogue.merchant-mode { grid-template-rows: minmax(0, 1fr); grid-template-columns: minmax(0, 1fr);');
    return replace(page,'shop.js','if (!precious.length)','if (true)');
  },
  async test({player,check,sleep,width,height,out}) {
    const page=await player('MerchantFrame',{characterClass:'warrior'});
    await page.evaluate(()=>{window.shopPackets=[];const receive=Shop.onPacket;Shop.onPacket=p=>{shopPackets.push(p);receive(p);};});
    await debug(page,{op:'set_level',level:99}); await debug(page,{op:'set_gold',gold:1000000}); await debug(page,{op:'set_rebirth',tiers:[0,1,0,0,0]});
    const ids={gray:'warrior_headgear_crimson_l5_gray',green:'warrior_armor_azure',blue:'headgear_upgrade',purple:'warrior_weapon_royal_l10_purple',orange:'orange_03'};
    const quest=await page.evaluate(()=>WORLD_ITEMS.find(i=>i.kind==='material'&&i.sell===0).id);
    for(const [item,quantity] of [[ids.gray,2],[ids.green,1],[ids.blue,1],[ids.purple,1],[ids.orange,1],[quest,1],['slime_gel',7],['necklace_upgrade',1]])await debug(page,{op:'give_item',item,quantity,force:true});
    await page.waitForFunction(id=>Inventory.quantity(id)===2,ids.gray);
    await page.evaluate(id=>Online.send({type:'equip',slots:{headgear:id,necklace:'necklace_upgrade'}}),ids.gray);
    await page.waitForFunction(id=>Field.hero.equipment.headgear===id,ids.gray);
    console.log('merchant: items equipped');
    await debug(page,{op:'die'}); await page.waitForFunction(()=>Field.hero.dead);
    await debug(page,{op:'set_hp',hp:1e9}); await page.waitForFunction(()=>!Field.hero.dead);
    async function visit(id) {
      const n=await page.evaluate(id=>WORLD_MAP.npcs.find(n=>n.id===id),id);
      await debug(page,{op:'teleport',zone:0,x:n.x,y:n.y+1});
      await page.waitForFunction(n=>Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,n);
      await sleep(600); console.log('merchant: visiting '+id);
      await page.evaluate(id=>Field.visitNpc(id),id);
      await page.waitForFunction(()=>Shop.open&&document.querySelector('.merchant-workspace[aria-busy="false"]'));
    }
    console.log('merchant: setup complete');
    await visit('smith');
    console.log('merchant: frame opened');
    async function geometry(label) {
      const boxes=await page.evaluate(()=>['#stage','#npc-dialogue > .gossip-window','#merchant-bags .bag-window'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};}));
      const [stage,left,right]=boxes;
      check(left.width>100&&right.width>100&&left.right<=right.x&&[left,right].every(r=>r.x>=stage.x-1&&r.y>=stage.y-1&&r.right<=stage.right+1&&r.bottom<=stage.bottom+1),`${label}: merchant left and bags right fit: ${JSON.stringify(boxes)}`);
    }
    await geometry('default scale');
    const smallTargets=await page.locator('.merchant-workspace button, #merchant-bags button, #merchant-bags input, #npc-dialogue .gossip-titlebar button, #npc-dialogue .gossip-footer button').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length).map(n=>({label:n.textContent||n.getAttribute('aria-label'),r:n.getBoundingClientRect()})).filter(({r})=>r.width<43.9||r.height<43.9).map(({label,r})=>({label,w:r.width,h:r.height})));
    check(!smallTargets.length,`merchant controls meet 44px floors: ${JSON.stringify(smallTargets)}`);
    await page.locator('#inventory-list [data-item="slime_gel"] .item-tile').hover();
    await page.locator('#item-tooltip').waitFor({state:'visible'});
    check(await page.locator('#item-tooltip').textContent().then(t=>t.includes('Sell for 23 gold')),'bag tooltip quotes the exact rebirth-adjusted stack price');
    check(await page.locator('#merchant-portrait').isVisible(),'circular NPC portrait accompanies the name');
    check(await page.locator('#merchant-stock > *').count()===10,'stock uses ten rectangular slots');
    check(await page.locator('.merchant-grid').evaluate(n=>getComputedStyle(n).gridTemplateColumns.split(' ').length)===2,'stock has two columns');
    check(await page.evaluate(()=>shopPackets.at(-1).available.filter(r=>r.item==='warrior_headgear_crimson_l5_gray').length)===1,'server excludes the equipped copy');
    check(await page.evaluate(id=>!shopPackets.at(-1).available.some(r=>r.item===id),quest),'quest item is protected');
    const quote=await page.evaluate(()=>shopPackets.at(-1));
    const junk=quote.available.filter(r=>r.rarity==='common'&&(r.gear||r.item==='slime_gel'));
    const total=junk.reduce((sum,r)=>sum+Math.floor((r.base*r.quantity*110+50)/100),0),before=await page.evaluate(()=>Field.hero.gold);
    await record(page); await page.locator('#sell-junk').tap();
    await page.waitForFunction(total=>shopPackets.some(p=>p.changed&&p.paid===total),total);
    await page.waitForFunction(gold=>Field.hero.gold===gold,before+total);
    check(await page.evaluate(ids=>Inventory.quantity(ids.gray)===1&&Inventory.quantity(ids.green)===1&&Inventory.quantity(ids.blue)===1&&Inventory.quantity(ids.purple)===1&&Inventory.quantity(ids.orange)===1,ids),'junk sells only loose gray gear and materials, preserving green and up');
    check(await page.locator('#merchant-last-buyback').getAttribute('data-item')!==null,'last sold item appears in the buyback square');
    await sleep(650);
    const tile=id=>page.locator(`#inventory-list [data-item="${id}"] .item-tile`);
    await tile(ids.orange).tap(); await page.locator('#sell-warning').waitFor({state:'visible',timeout:4000});
    check(await page.evaluate(()=>document.activeElement.id)==='sell-cancel','orange sale defaults to Cancel');
    await page.locator('#sell-cancel').tap();
    check(await page.evaluate(()=>touchSent.filter(p=>p.type==='sell_batch').length)===1,'cancelling valuable sale sends no batch');
    const purpleCopy=quote.available.find(r=>r.item===ids.purple).gear;
    await tile(ids.purple).tap(); await page.locator('#sell-warning').waitFor({state:'visible'}); await page.locator('#sell-yes').tap();
    await page.waitForFunction(id=>Inventory.quantity(id)===0,ids.purple); await sleep(650);
    await tile(ids.blue).dragTo(page.locator('#npc-inventory'));
    await page.waitForFunction(id=>Inventory.quantity(id)===0,ids.blue);
    check(true,'dragging a bag item sells it through the server');
    await page.locator('.merchant-tabs [data-tab="back"]').tap();
    await page.locator(`#sell-buyback [data-item="${ids.purple}"]`).waitFor(); await sleep(650);
    await page.locator(`#sell-buyback [data-item="${ids.purple}"]`).tap();
    await page.waitForFunction(id=>Inventory.quantity(id)===1,ids.purple);
    await page.waitForFunction(copy=>Field.hero.gearInstances.some(g=>g.id===copy.id),purpleCopy);
    check(await page.evaluate(({id,copy})=>JSON.stringify(Field.hero.gearInstances.find(g=>g.item===id))===JSON.stringify(copy),{id:ids.purple,copy:purpleCopy}),'buyback restores the exact gear copy');
    await page.locator('[data-action="repair-one"]').tap();
    await page.locator('.repair-row [data-action="repair"]').first().tap();
    await page.waitForFunction(()=>document.querySelectorAll('.repair-row').length===1);
    await page.locator('[data-action="repair-all"]').tap();
    await page.waitForFunction(()=>document.querySelectorAll('.repair-row').length===0);
    check(await page.locator('[data-action="repair-all"]').isDisabled(),'repair-one and Repair All use server quotes and clear worn gear');
    await page.locator('.merchant-tabs [data-tab="merchant"]').tap();
    await sleep(650); const buy=page.locator('#merchant-stock .merchant-slot').first(),buyId=await buy.getAttribute('data-item'),owned=await page.evaluate(id=>Inventory.quantity(id),buyId);
    await buy.tap(); await page.waitForFunction(({id,owned})=>Inventory.quantity(id)===owned+1,{id:buyId,owned});
    check(true,'merchant stock buys the displayed item');
    for(const scale of [.6,1.5]) {await page.evaluate(scale=>{Prefs.set({uiScale:scale});Settings.applyScale();},scale);await sleep(250);await geometry(`UI scale ${scale}`);}
    await page.evaluate(()=>{Prefs.set({uiScale:.8});Settings.applyScale();});
    await page.screenshot({path:`${out}/merchant-${width}x${height}.png`});
    await page.locator('#bags-close').tap(); await page.locator('#npc-dialogue').waitFor({state:'hidden'});
    check(await page.locator('#equipment .bag-window').count()===1,'closing restores the original bag window');
    await visit('merchant');
    check(await page.locator('#merchant-stock .merchant-slot').count()===10,'first merchant page has ten items');
    await page.locator('.merchant-pages [aria-label="Next page"]').tap();
    check(await page.locator('#merchant-stock .merchant-slot').count()>0&&await page.locator('#merchant-stock .merchant-slot').count()<10,'remaining stock appears on the next page');
    await page.locator('.merchant-tabs [data-tab="back"]').tap();
    check(await page.locator('#sell-buyback .merchant-slot').count()===0,'buyback remains separate per merchant');
    await page.locator('#npc-x').tap(); await page.context().close();
    if(width===844) {
      const sv=await player('MerchantSvenska',{lang:'sv'}); const n=await sv.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='smith'));
      await debug(sv,{op:'teleport',zone:0,x:n.x,y:n.y+1});await sv.waitForFunction(n=>Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,n);await sv.evaluate(()=>Field.visitNpc('smith'));
      await sv.locator('.merchant-tabs [data-tab="merchant"]').waitFor();
      check(await sv.locator('.merchant-tabs [data-tab="merchant"]').textContent()==='Handlare'&&await sv.locator('.merchant-tabs [data-tab="back"]').textContent()==='Återköp','merchant tabs have Swedish labels');await sv.context().close();
    }
  }
};
module.exports=suite;
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
