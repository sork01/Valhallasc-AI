// Reference: FileDrop pvw69993.png. Real private-server state; no encounter grinding.
const { run, debug, record } = require('./lib/touch.cjs');
const suite = {
  name: 'quest-journal',
  async test({ player, check, width, height, out }) {
    const page = await player('JournalTester',process.env.JOURNAL_DESKTOP ? {isMobile:false,hasTouch:false}:{});
    const plaza=await page.evaluate(()=>WORLD_MAP.city.plaza);
    await debug(page,{op:'teleport',zone:0,...plaza});
    await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='crags_onward'));
    const row = id => page.locator(`#quest-list .journal-quest[data-quest="${id}"]`);
    const press = async target => {
      if (!process.env.JOURNAL_DESKTOP && !await target.isVisible()) {
        const id = await target.evaluate(n => n.closest('.pause')?.id);
        const list = page.locator(`#${id} .quest-mobile-tabs [data-quest-pane="list"]`);
        if (await list.isVisible()) await list.tap();
      }
      return process.env.JOURNAL_DESKTOP ? target.click() : target.tap();
    };
    const control = name => page.locator(`#quest-controls [data-action="${name}"]`);
    async function quest(id, action) {
      console.log(`fixture: ${action} ${id}`);
      await debug(page, { op:'quest', id, action });
      await page.waitForFunction(({id,action}) => {
        const p=Field.hero.quests.find(q=>q.id===id); if(!p)return false;
        if(action==='finish')return p.claimed;
        if(action==='accept')return !p.claimed;
        const q=[WORLD_MAP,...WORLD_MAP.zones].flatMap(a=>a.quests).find(q=>q.id===id);
        return q.objectives.every((o,i)=>p.counts[i]>=o.count);
      },{id,action});
    }
    await quest('meadow_bounty','finish');
    await debug(page,{op:'quest',id:'slime_patrol',action:'reset'});
    await page.waitForFunction(()=>!Field.hero.quests.some(q=>q.id==='slime_patrol'));
    for (const id of ['welcome','slime_patrol','crags_welcome']) await quest(id,'accept');
    await page.evaluate(()=>Quests.show());
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    check(await page.locator('#quest-close').evaluate(n=>n===document.activeElement),'journal takes keyboard focus');
    const layout=await page.evaluate(()=>{
      const rect=id=>document.getElementById(id).getBoundingClientRect(), list=rect('quest-list'), parchment=rect('quest-page'), frame=document.querySelector('.quest-panel').getBoundingClientRect(), cv=rect('fieldcv'), footer=document.querySelector('.journal-footer').getBoundingClientRect();
      return { side:matchMedia('(pointer: coarse) and (max-width: 900px), (pointer: coarse) and (max-height: 500px)').matches ? list.width>frame.width*.9 && parchment.width===0 : list.right<=parchment.left+1, within:frame.left>=cv.left-1 && frame.right<=cv.right+1 && frame.top>=cv.top-1 && frame.bottom<=cv.bottom+1, footer:footer.top>=parchment.bottom-1, scroll:['quest-list','quest-page'].every(id=>getComputedStyle(document.getElementById(id)).overflowY==='auto') };
    });
    console.log('layout:',JSON.stringify(layout));
    if(!layout.side || !layout.within || !layout.footer || !layout.scroll) await page.screenshot({path:`${out}/quest-journal-layout-failure-${width}x${height}.png`});
    check(layout.side && layout.within && layout.footer && layout.scroll,'quest list and parchment use the responsive layout with independent scrolling and a bottom action bar');
    check(await page.locator('#quest-list [data-group="zone:0"]').count()===1 && await page.locator('#quest-list [data-group="zone:1"]').count()===1,'unfinished quests are grouped by region');
    check(await page.locator('.quest-completed').evaluate(n=>!n.open && n===n.parentElement.lastElementChild),'completed history starts folded at the bottom');
    await press(row('slime_patrol'));
    check(await page.locator('#quest-page h4').textContent()==='Trouble at the Gate' && await page.locator('#quest-page article').count()===1,'selecting a title fills exactly one parchment page');
    check(await row('slime_patrol').getAttribute('aria-pressed')==='true' && await row('slime_patrol').locator('.quest-objectives').count()===0,'selected row is highlighted and the list contains no expanding quest bodies');
    check(await page.locator('#quest-page .quest-reward-icon').count()===1 && await page.locator('#quest-page .journal-objectives').textContent().then(t=>t.includes('0/6')),'parchment shows actual objectives and reward artwork');
    const reward=page.locator('#quest-page .quest-reward-icon'); await reward.scrollIntoViewIfNeeded(); await press(reward);
    check(await page.locator('#item-tooltip').isVisible(),'reward icons retain their normal pointer tooltip');
    await press(row('slime_patrol'));
    await press(control('track'));
    check(await page.evaluate(()=>Quests.tracked==='slime_patrol') && await control('track').textContent()==='Tracking','bottom Track action updates the existing quest guidance');
    await quest('slime_patrol','complete');
    check(await page.locator('#quest-page h4').textContent()==='Trouble at the Gate' && await page.locator('#quest-page .journal-objectives .complete').count()===1,'live completion preserves the selected page and updates objective state');
    check(await row('slime_patrol').evaluate(n=>n.closest('.quest-ready') && n.closest('.quest-ready').previousElementSibling?.dataset.group?.startsWith('zone:')),'ready tracked quests move below unfinished quests');
    await page.evaluate(()=>document.getElementById('quest-page').scrollTop=0);
    await page.waitForFunction(()=>!document.getElementById('announce').children.length);
    await page.screenshot({path:`${out}/quest-journal-${width}x${height}.png`});
    const listTab = page.locator('#quest-journal .quest-mobile-tabs [data-quest-pane="list"]'); if(await listTab.isVisible())await press(listTab);
    await row('welcome').focus(); await page.keyboard.press('ArrowDown');
    check(await page.evaluate(()=>document.activeElement.matches('.journal-quest[aria-pressed="true"]') || document.activeElement.id==='quest-page' && matchMedia('(pointer: coarse) and (max-width: 900px), (pointer: coarse) and (max-height: 500px)').matches),'arrow keys select and read visible quest rows');
    await press(row('slime_patrol')); await press(control('abandon'));
    check(await page.locator('#quest-page [role="alert"]').isVisible() && await control('abandon').textContent()==='Confirm abandon','Abandon requires an inline confirmation');
    await press(page.locator('#quest-page').getByRole('button',{name:'Cancel',exact:true}));
    check(await page.evaluate(()=>Field.hero.quests.some(q=>q.id==='slime_patrol'&&!q.claimed)),'Cancel preserves the selected quest');
    const before=await page.evaluate(()=>({xp:Field.hero.xp,gold:Field.hero.gold}));
    await press(control('abandon')); await press(control('abandon'));
    await page.waitForFunction(()=>!Field.hero.quests.some(q=>q.id==='slime_patrol'));
    check(await row('slime_patrol').count()===0 && await page.evaluate(b=>Field.hero.xp===b.xp&&Field.hero.gold===b.gold&&Quests.tracked===null,before),'confirmed abandonment removes the quest and tracking without rewards');
    await press(row('crags_onward')); await press(control('abandon')); await press(control('abandon'));
    await page.waitForFunction(()=>Field.hero.abandonedQuests?.includes('crags_onward'));
    const recovery=page.locator('.quest-abandoned'); await press(recovery.locator(':scope > summary')); await press(recovery.locator('[data-quest="crags_onward"]'));
    await press(control('restore'));
    await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='crags_onward'&&!q.claimed));
    check(await page.locator('.quest-abandoned [data-quest="crags_onward"]').count()===0 && await row('crags_onward').count()===1,'abandoned automatic quests remain recoverable through the new page');
    await press(page.locator('.quest-completed > summary')); await press(row('meadow_bounty'));
    check(await control('abandon').isDisabled() && await control('track').isDisabled() && await page.locator('#quest-page [data-status="completed"]').count()===1,'completed repeatable history is readable with actions disabled');
    await press(row('welcome')); await press(control('map'));
    check(!await page.locator('#quest-journal').isVisible() && await page.locator('#worldmap').isVisible() && await page.evaluate(()=>Quests.tracked==='welcome'),'Show Map opens existing guidance for the selected quest');
    await page.evaluate(()=>{WorldMap.close();Quests.show();});
    await press(page.locator('#quest-x')); check(!await page.locator('#quest-journal').isVisible(),'header X closes the journal');
    await page.evaluate(()=>Quests.show()); await record(page);
    const outside=await page.locator('#quest-journal').boundingBox();
    if(process.env.JOURNAL_DESKTOP) await page.mouse.click(outside.x+2,outside.y+2); else await page.touchscreen.tap(outside.x+2,outside.y+2);
    check(!await page.locator('#quest-journal').isVisible() && await page.evaluate(()=>!touchSent.some(m=>m.type==='move'||m.type==='target')),'outside dismissal does not move or attack');
    await page.context().close();
    if(width===1024){
      const sv=await player('JournalSvenska',{lang:'sv'});
      await debug(sv,{op:'quest',id:'slime_patrol',action:'accept'});
      await sv.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='slime_patrol'));
      await sv.evaluate(()=>Quests.show());
      await press(sv.locator('#quest-list [data-quest="slime_patrol"]'));
      check(await sv.locator('.journal-tab').textContent()==='Alla uppdrag' && await sv.locator('#quest-page h5').first().textContent()==='Beskrivning' && await sv.locator('#quest-controls [data-action="map"]').textContent()==='Visa karta','new journal headings and controls translate in the actual Swedish client');
      await sv.context().close();
    }
  }
};
module.exports=suite;
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
