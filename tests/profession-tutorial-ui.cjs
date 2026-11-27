// Run through scripts/test-touch-bounded.sh on an approved browser host.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('./lib/playwright.cjs');
const {frameJson} = require('./lib/frames.cjs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(require.resolve('../world/map.txt')));
const world = new TestWorld();
let browser;

(async () => {
  await world.start();
  browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  const page = await browser.newPage({
    viewport:{width:844,height:390}, hasTouch:true, isMobile:true, reducedMotion:'reduce',
  });
  if (process.env.MUTATE === 'profession-tip') {
    const source = fs.readFileSync(require.resolve('../client/tutorial.js'),'utf8');
    const line = 'if (profession) return professionStep(profession';
    assert(source.includes(line));
    await page.route('**/tutorial.js', route => route.fulfill({
      contentType:'application/javascript', body:source.replace(line,'if (false) return professionStep(profession'),
    }));
  }
  const errors = [];
  let view;
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', socket => socket.on('framereceived', ({payload}) => {
    const packet = frameJson(payload);
    if (packet?.type === 'snapshot' || packet?.type === 'welcome') view = packet.snapshot || packet;
  }));
  await page.addInitScript(() => {
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang:'sv',sound:false}));
  });
  await page.goto(world.url);
  for (const id of ['start','login-guest','cls-warrior']) await page.locator('#'+id).click();
  await page.locator('#name').fill('TutorMaker');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, {timeout:60000});
  await page.locator('#connection-overlay').waitFor({state:'hidden'});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  const id = await page.evaluate(() => Online.id);
  const own = () => view?.players.find(player => player.id === id);
  const send = packet => page.evaluate(message => Online.send(message),packet);
  let ref = 0;

  const lessons = [
    {key:'fishing', instructor:'fisher_meadow_1', view:'fisher', title:'Fiske', text:/Kvistspö.*Kroka!/},
    {key:'blacksmithing', instructor:'smith', view:'smith', title:'Smide', text:/Bram Emberforge.*Spåra.*Bryt malm/},
    {key:'enchanting', instructor:'alder_enchanting', title:'Förtrollning', text:/Mira Moonleaf.*Avförtrolla/},
    {key:'alchemy', instructor:'alchemy_alderhaven', view:'alchemy', title:'Alkemi', text:/Maera Petalbrook.*Blommor.*brygga/},
  ];
  for (const lesson of lessons) {
    const npc = map.npcs.find(n => n.id === lesson.instructor);
    assert(npc,lesson.instructor);
    await send({type:'debug',ref:++ref,command:{op:'teleport',zone:0,x:npc.x,y:npc.y}});
    await page.waitForFunction(p => Math.hypot(Field.hero.x-p.x,Field.hero.y-p.y)<.15,npc);
    await send({type:'interact',npc:npc.id});
    await page.locator('#npc-dialogue').waitFor();
    const step = 'profession_' + lesson.key;
    if (lesson.view) {
      await page.locator(`#tutorial-layer[data-step="${step}"]`).waitFor({timeout:6000});
      assert.equal(await page.locator('#tutorial-arrow').evaluate(node => getComputedStyle(node).pointerEvents), 'none');
      await page.locator(`#npc-offers [data-view="${lesson.view}"]`).tap({timeout:7000});
      await page.waitForFunction(() => Tutorial.state().active?.targetId === 'npc-inventory', null, {timeout:6000});
    }
    await page.locator(`#tutorial-layer[data-step="${step}"]`).waitFor({timeout:6000});
    assert.equal(await page.locator('#tutorial-title').textContent(),lesson.title);
    assert.match(await page.locator('#tutorial-body').textContent(),lesson.text);
    await page.locator('#tutorial-gotit').tap();
    await world.waitFor(() => own()?.tutorialDone.includes(step),8000,`saving ${step}`);
    await page.locator('#npc-x').tap();
  }

  await page.locator('#touch-actions [data-action="menu"]').tap();
  await page.locator('#p-settings').tap();
  await page.locator('#set-tab-general').tap();
  const summary = page.locator('#set-profession-guide summary');
  assert.equal(await summary.textContent(),'Yrkesguide');
  await summary.tap();
  const guide = page.locator('#profession-guide-list');
  await guide.locator('dt').first().waitFor();
  assert.deepEqual(await guide.locator('dt').allTextContents(),lessons.map(lesson => lesson.title));
  for (let i = 0; i < lessons.length; i++) assert.match(await guide.locator('dd').nth(i).textContent(),lessons[i].text);
  assert.equal(await guide.evaluate(node => node.scrollWidth <= node.clientWidth + 1),true,'guide has no horizontal overflow');
  await page.screenshot({path:path.join(world.runDir,'profession-guide-phone.png')});
  assert.deepEqual(errors,[]);
  console.log('Profession tutorial passed four real workshops, saved completion, and the Swedish landscape guide.',world.runDir);
})().catch(error => {
  console.error(error); process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
  await world.stop();
});
