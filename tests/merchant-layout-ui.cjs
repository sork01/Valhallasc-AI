const {run,debug}=require('./lib/touch.cjs');
const suite={name:'merchant-layout',async test({player,check,sleep,width,height,out}){
 const page=await player('MerchantLayout'), n=await page.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='smith'));
 await debug(page,{op:'teleport',zone:0,x:n.x,y:n.y+1});await page.waitForFunction(n=>Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,n);
 await page.evaluate(()=>Field.visitNpc('smith'));await page.waitForFunction(()=>Shop.open&&document.querySelector('.merchant-workspace[aria-busy="false"]'));
 for(const scale of [.6,.8,1.5]){
  await page.evaluate(scale=>{Prefs.set({uiScale:scale});Settings.applyScale();},scale);await sleep(150);
  const r=await page.evaluate(()=>{
   const b=s=>{const r=document.querySelector(s).getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right};};
   const footer=document.querySelector('#npc-x').getBoundingClientRect();
   return {tabs:b('.merchant-tabs'),frame:b('#npc-dialogue > .gossip-window'),bags:b('#merchant-bags .bag-window'),footer:b('.gossip-footer'),hit:document.elementFromPoint(footer.x+footer.width/2,footer.y+footer.height/2)?.id};
  });
  check(r.tabs.top>=r.footer.bottom-2&&r.tabs.bottom<=r.frame.bottom+1,`scale ${scale}: folder tabs sit at the bottom edge below footer actions: ${JSON.stringify(r)}`);
  check(r.hit==='npc-x',`scale ${scale}: header X remains reachable`);
  check(r.frame.left>=0&&r.frame.right<=r.bags.left&&r.bags.right<=width&&r.frame.top>=0&&r.bags.top>=0&&r.frame.bottom<=height&&r.bags.bottom<=height,`scale ${scale}: separate windows fit`);
 }
 await page.evaluate(()=>{Prefs.set({uiScale:.8});Settings.applyScale();});await page.screenshot({path:`${out}/merchant-final-${width}x${height}.png`});
 await page.locator('#npc-x').tap();check(await page.locator('#npc-dialogue').isHidden(),'X closes both merchant panes');
 await page.locator('#inventory-open').tap();
 check(await page.locator('#equipment .bag-window').evaluate(n=>getComputedStyle(n).scale==='none'),'restored bags inherit workspace scale once');
 check(await page.locator('.win-grip[data-window="merchant-bags"]').count()===0,'temporary merchant bag grip is removed');
 await page.context().close();
}};
module.exports=suite;if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
