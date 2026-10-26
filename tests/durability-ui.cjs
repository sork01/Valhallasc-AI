// Focused private Chromium check for gear durability (docs/durability.md): a death wears the worn necklace, the slot bar and
// tooltip show it, the tenth death breaks it, and the Alderhaven smith repairs it for gold.
// MUTATE=1 serves the client file from HEAD that lacks the repair window, and the check must fail.
const assert=require('node:assert/strict');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require('./lib/playwright.cjs');
const {Client}=require('@modelcontextprotocol/sdk/client/index.js');
const {StdioClientTransport}=require('@modelcontextprotocol/sdk/client/stdio.js');
const root=path.resolve(__dirname,'..');
const client=new Client({name:'durability-ui',version:'1'});
let browser,started=false;
async function call(name,args={}){const result=await client.callTool({name,arguments:args});assert.ok(!result.isError,`${name}: ${JSON.stringify(result.content)}`);return result.structuredContent;}
(async()=>{
  require('./lib/touch.cjs').requireMemoryLimit();
  const transport=new StdioClientTransport({command:process.execPath,args:[path.join(root,'scripts/test-mcp.cjs')],cwd:root,env:{...process.env},stderr:'pipe'});
  transport.stderr?.on('data',chunk=>process.stderr.write(chunk));
  await client.connect(transport);
  const world=await call('start_world');started=true;
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  if(process.env.MUTATE){
    const old=execFileSync('git',['show','7e2a362:client/gearservices.js'],{cwd:root,maxBuffer:1<<24}).toString();
    await page.route('**/gearservices.js*',route=>route.fulfill({contentType:'text/javascript',body:old}));
  }
  await page.addInitScript(()=>localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false,char:null,draft:null})));
  await page.goto(world.url);
  await page.locator('#start').click();await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();await page.locator('#name').fill('DurabilityUI');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(()=>Online.connected&&!!Field.warriorSprites,null,{timeout:60000});
  const debug=command=>page.evaluate(command=>Online.send({type:'debug',ref:Math.floor(Math.random()*1e9),command}),command);
  await debug({op:'set_level',level:20});
  await page.waitForFunction(()=>Field.hero.level===20,null,{timeout:15000});
  await debug({op:'give_item',item:'necklace_upgrade',quantity:1});
  await page.waitForFunction(()=>Inventory.quantity('necklace_upgrade')>=1,null,{timeout:15000});
  await page.evaluate(()=>Field.equipSlot('necklace','necklace_upgrade'));
  await page.waitForFunction(()=>Field.hero.equipment?.necklace==='necklace_upgrade',null,{timeout:15000});
  await page.keyboard.press('e');
  const slot=page.locator('[data-slot="necklace"]');
  await slot.waitFor({state:'visible',timeout:15000});
  assert.equal(await slot.getAttribute('data-condition'),'new');
  assert.equal(await slot.locator('.item-break').count(),0,'healthy gear has no crack');
  const die=async()=>{
    await debug({op:'die'});
    await page.waitForFunction(()=>Field.hero.hp<=0||Field.hero.dead,null,{timeout:15000});
    await debug({op:'set_hp',hp:1e9});
    await page.waitForFunction(()=>Field.hero.hp>0&&!Field.hero.dead,null,{timeout:15000});
  };
  const level=await page.evaluate(()=>Field.hero.level);
  await die();
  assert.equal(await page.evaluate(()=>Field.hero.level),level,'a death takes no level');
  await page.waitForFunction(()=>document.querySelector('[data-slot="necklace"]')?.dataset.condition==='worn',null,{timeout:15000});
  assert.equal(await slot.evaluate(el=>el.style.getPropertyValue('--dur')),'90');
  await slot.locator('.gear-icon').hover();
  await page.waitForFunction(()=>/Durability 90%/.test(document.querySelector('.item-tooltip,#item-tooltip,[role="tooltip"]')?.textContent||''),null,{timeout:10000});
  assert.equal(await page.locator('#inventory-open').getAttribute('data-gear'),'ok');
  for(let n=0;n<6;n++)await die(); // 70% worn
  await page.waitForFunction(()=>document.querySelector('[data-slot="necklace"]')?.dataset.condition==='low',null,{timeout:15000});
  for(let n=0;n<3;n++)await die();
  await page.waitForFunction(()=>document.querySelector('[data-slot="necklace"]')?.dataset.condition==='broken',null,{timeout:15000});
  const crack=slot.locator('.item-break');
  assert.equal(await crack.count(),1,'broken worn gear has a crack across the icon');
  assert.equal(await crack.evaluate(el=>getComputedStyle(el).pointerEvents),'none','the crack does not block item controls');
  const red=Number(execFileSync('python3',['-c','import sys,io; from PIL import Image; im=Image.open(io.BytesIO(sys.stdin.buffer.read())).convert("RGB"); w,h=im.size; print(sum(1 for y in range(int(h*.2)+1,int(h*.8)) for x in range(int(w*.2)+1,int(w*.8)) if (lambda c:c[0]>200 and c[1]<85 and c[2]<85)(im.getpixel((x,y)))))'],{input:await slot.locator('.gear-icon').screenshot(),encoding:'utf8'}));
  assert.ok(red>10,'a large red crack is painted over the actual icon');
  assert.equal(await page.locator('#inventory-open').getAttribute('data-gear'),'broken','the bags button warns while a worn piece is broken');
  await slot.locator('.gear-icon').hover();
  await page.waitForFunction(()=>/Broken/.test(document.querySelector('.item-tooltip,#item-tooltip,[role="tooltip"]')?.textContent||''),null,{timeout:10000});
  assert.equal(await page.evaluate(()=>Field.hero.equipment.necklace),'necklace_upgrade','a broken piece stays worn');
  await page.evaluate(()=>Field.equipSlot('necklace','none'));
  await page.waitForFunction(()=>document.querySelector('#inventory-list [data-item="necklace_upgrade"] .item-break'));
  await page.evaluate(()=>Field.equipSlot('necklace','necklace_upgrade'));
  await page.waitForFunction(()=>document.querySelector('[data-slot="necklace"] .item-break'));
  await page.keyboard.press('e');
  // The smith: a quarter of 240 gold for a full repair.
  await debug({op:'set_gold',gold:1000});
  await page.waitForFunction(()=>Field.hero.gold===1000,null,{timeout:15000});
  await debug({op:'teleport',zone:0,x:31,y:88});
  await page.waitForTimeout(500);
  await page.evaluate(()=>Online.send({type:'interact',npc:'smith'}));
  await page.locator('#npc-dialogue').waitFor({state:'visible',timeout:15000});
  const offer=page.locator('[data-action="repair-one"]');
  await offer.waitFor();
  assert.equal(await offer.count(),1);
  assert.match(await page.locator('[data-action="repair-all"]').getAttribute('title'),/60 gold/);
  await offer.click();
  assert.equal(await page.locator('#npc-inventory .repair-row[data-state="broken"]').count(),1);
  await page.locator('#npc-inventory [data-action="repair_all"]').click();
  await page.getByText(/Repaired one piece for 60 gold/).waitFor({timeout:10000});
  await page.waitForFunction(()=>Field.hero.gold===940,null,{timeout:15000});
  await page.locator('#npc-close').click();
  await page.keyboard.press('e');
  await page.waitForFunction(()=>document.querySelector('[data-slot="necklace"]')?.dataset.condition==='new',null,{timeout:15000});
  assert.equal(await page.locator('#inventory-open').getAttribute('data-gear'),'ok','repairing clears the warning');
  assert.equal(await slot.locator('.item-break').count(),0,'repairing removes the red crack');
  if(process.env.DUNGEON_REPAIRS){
    await page.keyboard.press('e');await die();
    const smith=await page.evaluate(()=>WORLD_MAP.zones[4].npcs.find(n=>n.id==='dungeon_repair_5'));
    await debug({op:'teleport',zone:5,x:smith.x,y:smith.y});
    await page.waitForFunction(()=>Field.zone===5);
    await page.evaluate(()=>Field.visitNpc('dungeon_repair_5'));
    await page.locator('[data-offer="repair"]').waitFor();
    assert.match(await page.locator('[data-offer="repair"]').textContent(),/24 gold/,'dungeon quote is four times the 6-gold town price');
    await page.locator('[data-offer="repair"]').click();
    assert.match(await page.locator('#npc-inventory').textContent(),/four times the town price/);
    await page.locator('#npc-inventory [data-action="repair_all"]').click();
    await page.getByText(/Repaired one piece for 24 gold/).waitFor();
    await page.waitForFunction(()=>Field.hero.gold===916);
  }
  assert.deepEqual(errors,[]);
  console.log('durability-ui: ok');
})().then(async()=>{await browser?.close();if(started)await call('stop_world').catch(()=>{});await client.close();process.exit(0);},
  async error=>{console.error(error);await browser?.close().catch(()=>{});if(started)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});process.exit(1);});
