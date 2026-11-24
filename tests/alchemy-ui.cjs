// Run with scripts/test-touch-bounded.sh on an approved browser host.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('./lib/playwright.cjs');
const {frameJson} = require('./lib/frames.cjs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(require.resolve('../world/map.txt')));
const trainer = map.npcs.find(n => n.id === 'alchemy_alderhaven');
const potion = 'alchemy_meadowgold_potion';
const touch = process.env.TOUCH === '1';
const w = new TestWorld();
let browser;

(async () => {
  await w.start();
  browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  const page = await browser.newPage({
    viewport:touch ? {width:844,height:390} : {width:1100,height:680},
    hasTouch:touch, isMobile:touch, deviceScaleFactor:1, reducedMotion:'reduce',
  });
  const errors = [], requests = [], replies = [];
  let view;
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', ws => {
    ws.on('framereceived', frame => {
      const p = frameJson(frame.payload);
      if (p?.type === 'snapshot' || p?.type === 'welcome') view = p.snapshot || p;
      if (p?.type === 'picking') replies.push(p);
    });
    ws.on('framesent', frame => {
      const p = frameJson(frame.payload);
      if (p?.type === 'pick_flower') requests.push(p.id);
    });
  });
  await page.addInitScript(lang => localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang,sound:false})), touch ? 'sv' : 'en');
  await page.goto(w.url);
  for (const id of ['start','login-guest','cls-warrior']) await page.locator('#'+id).click();
  await page.locator('#name').fill(touch ? 'Touchalchemist' : 'Desktopalchemist');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, {timeout:60000});
  await page.locator('#connection-overlay').waitFor({state:'hidden'});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => window.Tutorial?.disable?.());

  let ref = 1;
  const debug = command => page.evaluate(({command,ref}) => Online.send({type:'debug',command,ref}), {command,ref:ref++});
  async function warp(p) {
    await debug({op:'teleport',zone:0,x:p.x,y:p.y});
    await page.waitForFunction(p => Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.08,p);
  }
  const use = locator => touch ? locator.tap() : locator.click();
  async function interact() {
    await page.evaluate(id => Online.send({type:'interact',npc:id}),trainer.id);
    await use(page.locator('#npc-offers [data-view="alchemy"]'));
  }
  const brew = page.locator(`[data-alchemy-action="${potion}"]`);
  await warp(trainer);
  await interact();
  await use(page.getByRole('button',{name:touch ? 'Lär dig alkemi' : 'Learn Alchemy',exact:true}));
  await page.waitForFunction(() => document.querySelector('.smith-skill')?.textContent.includes('1 / 600'));
  await use(page.locator('[data-alchemy-action="flowers"]'));
  await page.locator('.alchemy-workshop select').selectOption('6');
  const plants = await page.locator('.alchemy-flowers').textContent();
  assert.match(plants,touch ? /Wyrdklöver.*120.*Månslöjeorkidé.*150/ : /Wyrd Clover.*120.*Moonveil Orchid.*150/);
  await use(page.locator('[data-alchemy-action="recipes"]'));
  await use(brew);
  await brew.waitFor();
  assert(await brew.isDisabled());
  await use(page.locator('#npc-x'));

  const c = map.city;
  const patch = view.flowerPatches.find(p => p.x > c.x0 && p.x < c.x1 && p.y > c.y0 && p.y < c.y1);
  await warp(patch);
  await page.evaluate(id => {
    const draw = Alchemy.drawPatch;
    Alchemy.drawPatch = (g,patch,x,y) => {
      if (patch.id === id) {
        const scale = g.getTransform().a;
        window.testFlower = {x,y,width:g.canvas.width/scale,height:g.canvas.height/scale};
      }
      draw(g,patch,x,y);
    };
  },patch.id);
  await page.waitForFunction(() => window.testFlower);
  await page.waitForTimeout(600);
  const target = await page.evaluate(() => {
    const {x,y,width,height} = window.testFlower;
    const bounds = document.getElementById('fieldcv').getBoundingClientRect();
    return {x:bounds.x+x*bounds.width/width,y:bounds.y+(y-22)*bounds.height/height};
  });
  if (touch) await page.touchscreen.tap(target.x,target.y);
  else await page.mouse.click(target.x,target.y);
  await w.waitFor(() => replies.at(-1)?.state === 'done' || replies.at(-1)?.state === 'error',9500,'flower response');
  assert(requests.includes(patch.id));
  assert.equal(replies.at(-1).state,'done',JSON.stringify(replies));

  await warp(trainer);
  await debug({op:'give_item',item:'alchemy_meadowgold',quantity:2});
  await debug({op:'give_item',item:'alchemy_empty_vial',quantity:1});
  await page.waitForFunction(() => Inventory.bagQuantity('alchemy_empty_vial') === 1);
  await interact();
  await use(brew);
  await page.waitForFunction(id => Inventory.bagQuantity(id) === 1,potion);
  assert(await brew.isDisabled());
  await use(page.locator('#npc-x'));
  await page.evaluate(id => Field.useItem(id),potion);
  const chip = page.locator(`[data-buff="${potion}"]`);
  await chip.waitFor();
  if (touch) await chip.tap(); else await chip.hover();
  await page.locator('#buff-tooltip').waitFor();
  assert.match(await page.locator('#buff-tooltip').textContent(),touch ? /4 % skada i 15 s/ : /\+4% damage for 15 s/);
  assert.deepEqual(errors,[]);
  console.log(`Alchemy ${touch ? 'Swedish touch' : 'desktop'} passed gathering, recipes, zone guide and buff tooltip.`);
})().catch(error => { console.error(error); process.exitCode = 1; })
  .finally(async () => { await browser?.close(); await w.stop(); });
