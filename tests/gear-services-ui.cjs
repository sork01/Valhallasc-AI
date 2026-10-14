// Focused private Chromium check for Alda's explicit copy previews and confirmations.
const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'gear-services-ui',version:'1'});
let browser,started=false;
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
(async()=>{
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,stderr:'pipe'});
  transport.stderr?.on('data',chunk=>process.stderr.write(chunk));
  await client.connect(transport);
  const world=await call('start_world');started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);
  await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('GearwrightUI');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.warriorSprites,null,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:Math.floor(Math.random()*1e9),command}),command);
  await debug({op:'set_gold',gold:10000});
  await page.waitForFunction(()=>Field.hero.gold===10000,null,{timeout:15000});
  await debug({op:'give_item',item:'warrior_weapon_sword_l5_gray',quantity:2});
  await page.waitForFunction(()=>Inventory.quantity('warrior_weapon_sword_l5_gray')>=2,null,{timeout:15000});
  await debug({op:'give_item',item:'refinement_crystal_uncommon',quantity:1});
  await page.waitForFunction(()=>Inventory.quantity('refinement_crystal_uncommon')>=1,null,{timeout:15000});
  await debug({op:'teleport',zone:0,x:36,y:91});
  await page.waitForTimeout(500);
  await page.evaluate(()=>Online.send({type:'interact',npc:'gearwright'}));
  await page.locator('#npc-dialogue').waitFor({state:'visible',timeout:15000});
  assert.equal(await page.locator('[data-offer="merge"]').count(),1);
  assert.equal(await page.locator('[data-offer="refine"]').count(),1);
  await page.locator('[data-offer="merge"]').click();
  assert.equal(await page.locator('#npc-inventory .gear-service-select').count(),2);
  await page.getByRole('button',{name:'Preview merge'}).click();
  await page.getByText(/Output: uncommon/).waitFor({timeout:10000});
  await page.getByRole('button',{name:'Confirm merge'}).click();
  await page.getByText(/Merged into an? uncommon/i).waitFor({timeout:10000});
  await page.locator('#npc-back').click();
  await page.locator('[data-offer="refine"]').click();
  const select=page.locator('#npc-inventory .gear-service-select');
  const merged=await select.locator('option').evaluateAll(options=>options.find(o=>o.textContent.includes('uncommon')&&o.textContent.includes('Weathered'))?.value);
  assert.ok(merged,'Merged copy appears in refinement list');
  await select.selectOption(merged);
  await page.getByRole('button',{name:'Preview refinement'}).click();
  await page.getByText(/Cost: 200 gold and 1 Uncommon Refinement Crystal/).waitFor({timeout:10000});
  await page.getByRole('button',{name:'Confirm refinement'}).click();
  await page.getByText(/Refined .* to rank 1/).waitFor({timeout:10000});
  // Orange copies use their own editor-exported art and retain individually visible stats.
  await page.locator('#npc-close').click();
  const ordinaryFrame=await page.evaluate(()=>Field.warriorSprites.frame('idle',0,0).toDataURL());
  await debug({op:'give_item',item:'orange_01',quantity:2});
  await page.waitForFunction(()=>Inventory.quantity('orange_01')===2,null,{timeout:15000});
  await page.locator('#equipment-open').click();
  const orange=page.locator('#inventory-list [data-item="orange_01"]');
  assert.equal(await orange.getAttribute('data-rarity'),'legendary');
  assert.equal(await orange.locator('.orange-item-art').count(),1);
  await orange.locator('button').click();
  assert.equal(await page.locator('#bag-details .orange-copy-stats').count(),2);
  assert.match(await page.locator('#bag-details').textContent(),/110 defense.*90 stamina.*8 accuracy.*18 dexterity/i);
  await page.locator('#bag-details [data-action="equip"]').first().click();
  await page.waitForFunction(()=>Field.hero.look.warriorArmor==='orange_01',null,{timeout:15000});
  assert.equal(await page.locator('[data-slot="chest"] .orange-item-art').count(),1);
  await page.waitForFunction(()=>Field.warriorSprites?.worn?.armor==='orange_01',null,{timeout:15000});
  assert.equal(await page.evaluate(()=>Field.warriorSprites.equipment.armor),'azure','Orange armor uses a fitted animated atlas layer');
  assert.notEqual(await page.evaluate(()=>Field.warriorSprites.frame('idle',0,0).toDataURL()),ordinaryFrame);
  await page.locator('[data-slot="chest"] .gear-icon').click();
  assert.match(await page.locator('#bag-details').textContent(),/Equipped/);
  const familyFrames=[];
  for(const number of [11,16,21,26,31]){
    const id=`orange_${number}`;
    await debug({op:'give_item',item:id,quantity:1});
    await page.waitForFunction(id=>Inventory.quantity(id)===1,id,{timeout:15000});
    await page.waitForFunction(id=>[...document.querySelector('#field-warriorArmor').options].some(o=>o.value===id),id,{timeout:15000});
    await page.locator('#field-warriorArmor').selectOption(id);
    await page.waitForFunction(id=>Field.hero.look.warriorArmor===id&&Field.warriorSprites?.worn?.armor===id,id,{timeout:15000});
    const drawn=await page.evaluate(()=>({art:Field.warriorSprites.equipment.armor,
      image:Field.warriorSprites.frame('idle',0,0).toDataURL()}));
    assert.equal(drawn.art,'azure',`${id} uses the class's fitted atlas armor`);
    familyFrames.push(drawn.image);
    assert.equal(await page.locator('[data-slot="chest"] .orange-item-art').getAttribute('data-icon'),id);
  }
  assert.equal(new Set(familyFrames).size,5,'Five families have different worn colors');
  const fitted=await page.evaluate(()=>{
    const sprite=Field.warriorSprites, prior={...Field.hero.look};
    sprite.set({...prior,warriorArmor:'orange_11',warriorWeapon:'orange_12',
      head:'orange_13',shoulders:'orange_14',gloves:'orange_15'});
    const parts={...sprite.equipment},image=sprite.frame('idle',0,0).toDataURL();
    sprite.set(prior);
    return {parts,image};
  });
  assert.deepEqual(Object.fromEntries(['armor','weapon','head','shoulders','gloves'].map(slot=>[slot,fitted.parts[slot]])),
    {armor:'azure',weapon:'royal',head:'azure',shoulders:'azure',gloves:'azure'},
    'Every orange slot uses an animated warrior gear layer');
  assert.notEqual(fitted.image,ordinaryFrame);
  const exported=await page.evaluate(async()=>{
    const hashes=[];
    for(let n=1;n<=35;n++){
      const id=`orange_${String(n).padStart(2,'0')}`,img=new Image();img.src=`assets/${id}.png`;await img.decode();
      const c=document.createElement('canvas');c.width=img.width;c.height=img.height;c.getContext('2d').drawImage(img,0,0);
      hashes.push(c.toDataURL());
    }
    return hashes;
  });
  assert.equal(new Set(exported).size,35,'Thirty-five distinct PixelFlow exports load in browser');
  assert.deepEqual(errors,[]);
  console.log('Gearwright merge and refinement browser checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{
  await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();
});
