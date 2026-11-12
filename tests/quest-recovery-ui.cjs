const {run,debug} = require('./lib/touch.cjs');
const suite = {
 name:'quest-recovery',
 async test({player,check,sleep,width,height,out}) {
  const page=await player('QuestRecovery');
  await debug(page,{op:'teleport',zone:4,x:104.2,y:125.4});
  await page.waitForFunction(()=>Field.zone===4 && Field.hero.quests.some(q=>q.id==='crags_onward'));
  async function journal() { await page.evaluate(()=>{City.close();Quests.close();Quests.show();}); }
  async function abandon(id) {
   await journal();
   const entry=page.locator(`#quest-list > :not(.quest-abandoned) .journal-quest[data-quest="${id}"]`);
   await entry.tap();
   await page.locator('#quest-controls [data-action="abandon"]').tap();
   await page.locator('#quest-controls [data-action="abandon"]').tap();
   await page.waitForFunction(id=>!Field.hero.quests.some(q=>q.id===id&&!q.claimed),id);
  }
  async function recover(id) {
   await abandon(id); await sleep(300); await journal();
   check(await page.locator(`#quest-list > :not(.quest-abandoned) .journal-quest[data-quest="${id}"]`).count()===0,'automatic quest stays abandoned until restored');
   const group=page.locator('.quest-abandoned');
   check(await group.count()===1 && !await group.evaluate(n=>n.open),'journal has a collapsed recovery section');
   await group.locator(':scope > summary').tap();
   const entry=group.locator(`.journal-quest[data-quest="${id}"]`);
   check(await entry.count()===1,'abandoned quest remains findable by title');
   await entry.tap();
   const restore=page.locator('#quest-controls [data-action="restore"]');await restore.waitFor({state:'visible'});
   const before=await page.evaluate(()=>({xp:Field.hero.xp,gold:Field.hero.gold,x:Field.hero.nx,y:Field.hero.ny,zone:Field.zone}));
   await restore.scrollIntoViewIfNeeded();
   await page.screenshot({path:`${out}/quest-recovery-${id}-${width}x${height}.png`});
   await restore.tap();
   await page.waitForFunction(id=>Field.hero.quests.some(q=>q.id===id&&!q.claimed),id);
   check(await page.evaluate(b=>Field.zone===b.zone&&Field.hero.xp===b.xp&&Field.hero.gold===b.gold&&Math.hypot(Field.hero.nx-b.x,Field.hero.ny-b.y)<.1,before),'restore works remotely without movement or rewards');
   check(await page.locator(`#quest-list > :not(.quest-abandoned) .journal-quest[data-quest="${id}"]`).count()===1,'restored quest returns to active journal');
   check(await page.locator(`.quest-abandoned [data-quest="${id}"]`).count()===0,'recovered quest leaves abandoned section');
  }
  await recover('crags_onward');
  await page.evaluate(()=>Quests.close());
  await debug(page,{op:'quest',id:'es_01',action:'finish'});
  await page.waitForFunction(()=>Field.hero.quests.some(q=>q.id==='es_go_02'&&!q.claimed));
  await recover('es_go_02');
  await page.evaluate(()=>Quests.close());
  await page.context().close();
  const sv=await player('RecoverySvenska',{lang:'sv'});
  // The catalog must also translate the actual recovery controls.
  check(await sv.evaluate(()=>Locale.translate('Restore quest')==='Återställ uppdrag'&&Locale.translate('Abandoned automatic quests (1)')==='Övergivna automatiska uppdrag (1)'),'recovery controls have Swedish translations');
  await sv.context().close();
 }
};
module.exports=suite;
if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
