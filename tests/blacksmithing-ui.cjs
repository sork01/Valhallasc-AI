// Run under scripts/test-touch-bounded.sh against a private world and database.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('./lib/playwright.cjs');
const {frameJson} = require('./lib/frames.cjs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname,'..');
const map = JSON.parse(fs.readFileSync(path.join(root,'world/map.txt')));
const smith = map.npcs.find(n => n.id === 'smith');
const w = new TestWorld();
w.startLevel = 4;
w.levelSpread = 0;
const touch = process.env.TOUCH === '1';
const gear = 'smith_gear_tin_banded_gloves';
let browser;

(async () => {
  await w.start();
  browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  const page = await browser.newPage({
    viewport:touch ? {width:844,height:390} : {width:1100,height:680},
    hasTouch:touch, isMobile:touch, deviceScaleFactor:1, reducedMotion:'reduce',
  });
  if (process.env.MUTATE === 'no-vein-click') {
    const text = fs.readFileSync(path.join(root,'client/field.js'),'utf8');
    const call = touch ? 'startGathering(vein, smithing.start);' : 'startGathering(vein, window.Blacksmithing.start);';
    assert(text.includes(call));
    await page.route('**/field.js', route => route.fulfill({
      contentType:'application/javascript',
      body:text.replace(call,'void vein;'),
    }));
  }
  const errors = [];
  let view;
  const miningPackets = [];
  const miningRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', ws => {
    ws.on('framereceived', frame => {
      const packet = frameJson(frame.payload);
      if (packet?.type === 'snapshot' || packet?.type === 'welcome') view = packet.snapshot || packet;
      if (packet?.type === 'mining') miningPackets.push(packet);
    });
    ws.on('framesent', frame => {
      const packet = frameJson(frame.payload);
      if (packet?.type === 'mine') miningRequests.push(packet.id);
    });
  });
  await page.addInitScript(lang => localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang,sound:false})), touch ? 'sv' : 'en');
  await page.goto(w.url);
  for (const id of ['start','login-guest','cls-warrior']) await page.locator('#'+id).click();
  await page.locator('#name').fill(touch ? 'Touchminer' : 'Desktopminer');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, {timeout:60000});
  await page.locator('#connection-overlay').waitFor({state:'hidden'});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => window.Tutorial?.disable?.());

  let ref = 1;
  const debug = command => page.evaluate(({command,ref}) => Online.send({type:'debug',command,ref}), {command,ref:ref++});
  const warp = async point => {
    await debug({op:'teleport',zone:0,x:point.x,y:point.y});
    await page.waitForFunction(p => Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y) < .08, point);
  };
  const interact = async () => {
    await page.evaluate(id => Online.send({type:'interact',npc:id}), smith.id);
    await page.locator('#npc-offers [data-view="smith"]').click();
  };
  await warp(smith);
  await interact();
  await page.locator('#npc-inventory button').click();
  await page.waitForFunction(() => Inventory.bagQuantity('smith_pick_1') === 1);
  const skill = page.locator('.smith-skill');
  assert.match(await skill.textContent(), touch ? /Smidesfärdighet 1 \/ 300/ : /Blacksmithing skill 1 \/ 300/);
  const staple = page.locator(`[data-recipe="${gear}"]`);
  await staple.locator('button').click();
  await staple.locator('button').filter({hasText:touch ? 'Smid föremål' : 'Forge item'}).waitFor();
  assert(await staple.locator('button').isDisabled(),'ingredients are required');
  await page.locator('#npc-x').click();

  const safe = v => Math.min(...map.slimes.map(s => Math.hypot(s.x-v.x,s.y-v.y)));
  const vein = [...view.miningVeins].sort((a,b) => safe(b)-safe(a))[0];
  await warp(vein);
  await page.evaluate(vein => {
    const draw = Blacksmithing.draw;
    Blacksmithing.draw = (g,project,width,height,reduced) => {
      const [x,y] = project(vein.x,vein.y);
      if (x > 80 && x < width-80 && y > 90 && y < height-60) window.smithVeinTest = {x,y,width,height};
      draw(g,project,width,height,reduced);
    };
  },vein);
  await page.waitForFunction(() => Boolean(window.smithVeinTest));
  await page.waitForTimeout(600); // let camera movement settle before taking the hitbox coordinates
  const target = await page.evaluate(() => {
    const {x,y,width,height} = window.smithVeinTest;
    const r = document.getElementById('fieldcv').getBoundingClientRect();
    return {x:r.x+x*r.width/width,y:r.y+(y-22)*r.height/height};
  });
  assert(await page.evaluate(({x,y}) => document.elementFromPoint(x,y)?.id === 'fieldcv', target),
    'the ore is visible on the interactive world canvas');
  if (touch) {
    const mine = page.locator('#touch-skills .touch-mine');
    assert.equal(await mine.textContent(),'Bryt malm');
    const box = await mine.boundingBox();
    assert(box.width >= 44 && box.height >= 44,'mining is a full-sized touch target');
    assert(await mine.evaluate(button => {
      const r=button.getBoundingClientRect();
      return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2) === button;
    }),'the Mine ore button receives touch events');
    await mine.tap();
  } else await page.mouse.click(target.x,target.y);
  try {
    await w.waitFor(() => miningPackets.at(-1)?.state === 'done' || miningPackets.at(-1)?.state === 'error', 9500, 'mining reply');
    assert.equal(miningPackets.at(-1).state,'done',miningPackets.at(-1).text || 'pull completed');
    assert(miningPackets.some(packet => packet.state === 'started'));
    assert.deepEqual(miningRequests,[vein.id]);
    await page.waitForFunction(() => Inventory.bagQuantity('smith_ore_tin') > 0, null, {timeout:8000});
  } catch (error) {
    error.message += ` (sent ${JSON.stringify(miningRequests)}, received ${JSON.stringify(miningPackets)})`;
    throw error;
  }
  assert.match(await page.locator('#mining-status').textContent(),touch ? /Bröt [12] × Tennmalm/ : /Mined [12] × Tin Ore/);
  await page.screenshot({path:path.join(w.runDir,touch ? 'blacksmithing-touch-mining.png' : 'blacksmithing-desktop-mining.png')});

  await warp(smith);
  await debug({op:'give_item',item:'smith_bar_tin',quantity:3});
  await debug({op:'give_item',item:'smith_leather_strips',quantity:2});
  await page.waitForFunction(() => Inventory.bagQuantity('smith_leather_strips') === 2);
  await interact();
  const craft = staple.locator('button');
  await craft.scrollIntoViewIfNeeded();
  assert(await craft.isEnabled());
  const workshopBounds = await page.locator('#npc-dialogue > .gossip-window').boundingBox();
  assert(workshopBounds.width >= 400, 'workshop leaves room to read requirements and costs');
  assert(await craft.evaluate(el => {
    const rect = el.getBoundingClientRect();
    return document.elementFromPoint(rect.x+rect.width/2,rect.y+rect.height/2) === el;
  }), 'the visible shop button is usable');
  await page.screenshot({path:path.join(w.runDir,touch ? 'blacksmithing-touch-workshop.png' : 'blacksmithing-desktop-workshop.png')});
  if (touch) await craft.tap();
  else await craft.click();
  await page.waitForFunction(id => Inventory.bagQuantity(id) === 1,gear);
  assert(await craft.isDisabled(),'materials update after the craft');
  await page.locator('#npc-back').click();
  await page.locator('[data-view="smith"]').click();
  assert(await craft.isDisabled(),'reopening preserves updated materials and blueprints');
  assert.deepEqual(errors,[]);
  console.log(`Blacksmithing ${touch ? 'touch and Swedish' : 'desktop'} passed workshop and real mine/forge controls. ${w.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; })
  .finally(async () => { await browser?.close(); await w.stop(); });
