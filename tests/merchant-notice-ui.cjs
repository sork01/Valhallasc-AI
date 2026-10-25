const {run,replace,debug}=require('./lib/touch.cjs');
const suite={
 name:'merchant-notice',
 mutate(page){
  if(process.env.MUTATE==='clear')return replace(page,'shop.js','if (packet.notice) lastNotice=packet.notice;',"lastNotice=packet.notice || '';");
  return replace(page,'shop.js',"const status = $('npc-notice');","container.prepend(make('p', data?.notice || '', 'sell-notice')); const status = $('npc-notice');");
 },
 async test({player,check,sleep,width,height,out}){
  const page=await player('MerchantNotice');
  await debug(page,{op:'give_item',item:'slime_gel',quantity:3});await debug(page,{op:'give_item',item:'blue_gel',quantity:2});
  const npc=await page.evaluate(()=>WORLD_MAP.npcs.find(n=>n.id==='smith'));
  await debug(page,{op:'teleport',zone:0,x:npc.x,y:npc.y+1});await page.waitForFunction(n=>Math.hypot(Field.hero.nx-n.x,Field.hero.ny-n.y-1)<.5,npc);
  await page.evaluate(()=>Field.visitNpc('smith'));await page.waitForFunction(()=>Shop.open&&document.querySelector('.merchant-workspace[aria-busy="false"]'));
  await page.evaluate(()=>{
   window.noticePackets=[];const receive=Shop.onPacket;Shop.onPacket=p=>{noticePackets.push({changed:p.changed,notice:p.notice});receive(p);};
   window.merchantFrames=[];window.trackMerchant=true;
   window.merchantBoxes=()=>['#merchant-stock','.merchant-tools','.merchant-tabs','#npc-dialogue > .gossip-window','#npc-notice'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [r.x,r.y,r.width,r.height];});
   function sample(){merchantFrames.push({boxes:merchantBoxes(),text:document.querySelector('#npc-notice').textContent});if(trackMerchant&&merchantFrames.length<400)requestAnimationFrame(sample);}requestAnimationFrame(sample);
  });
  const baseline=await page.evaluate(()=>merchantBoxes());
  check(baseline[4][3]>=35&&baseline[4][1]>baseline[1][1],'message space is reserved below merchant controls before a sale');
  for(const item of ['slime_gel','blue_gel']){
   await page.locator(`#inventory-list [data-item="${item}"] .item-tile`).tap();
   await page.waitForFunction(id=>Inventory.quantity(id)===0,item);
   await page.waitForFunction(()=>/sold.*gold/i.test(document.querySelector('#npc-notice').textContent));
   const receipt=await page.locator('#npc-notice').textContent();
   check(/gold/.test(receipt),'successful sale displays its gold receipt');
   const before=await page.evaluate(()=>noticePackets.length);
   await page.evaluate(()=>Online.send({type:'shop_open',npc:'smith'}));
   await page.waitForFunction(before=>noticePackets.length>before&&noticePackets.at(-1).notice==='',before);
   await sleep(750);
   check(await page.locator('#npc-notice').textContent()===receipt,'empty inventory refresh preserves the readable sale receipt');
   await sleep(650);
  }
  const samples=await page.evaluate(()=>{trackMerchant=false;return merchantFrames;});
  const shifted=samples.filter(s=>s.boxes.some((r,i)=>r.some((v,j)=>Math.abs(v-baseline[i][j])>1)));
  check(!shifted.length,`sale and refresh never move stock, tools, tabs or message area (${samples.length} frames): ${JSON.stringify(shifted.slice(0,2))}`);
  check(await page.locator('.merchant-workspace .sell-notice').count()===0,'receipt never inserts a row above the catalog');
  await page.screenshot({path:`${out}/merchant-notice-${width}x${height}.png`});
  await page.locator('#npc-close').tap();await page.evaluate(()=>Field.visitNpc('smith'));
  await page.waitForFunction(()=>Shop.open&&document.querySelector('.merchant-workspace[aria-busy="false"]'));
  check(await page.locator('#npc-notice').textContent()==='','a new merchant visit clears the previous receipt');
  await page.context().close();
 }
};
module.exports=suite;if(require.main===module)run([suite]).catch(e=>{console.error(e);process.exitCode=1;});
