// Run through scripts/test-touch-bounded.sh on an approved browser host.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('./lib/playwright.cjs');
const {frameJson} = require('./lib/frames.cjs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(require.resolve('../world/map.txt')));
const smith = map.npcs.find(n => n.id === 'smith');
const alchemist = map.npcs.find(n => n.id === 'alchemy_alderhaven');
const world = new TestWorld();
let browser;

(async () => {
  await world.start();
  browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  const page = await browser.newPage({
    viewport:{width:844,height:390},
    hasTouch:true, isMobile:true, deviceScaleFactor:1, reducedMotion:'reduce',
  });
  const errors = [];
  let view;
  const gathered = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', socket => socket.on('framereceived', ({payload}) => {
    const packet = frameJson(payload);
    if (packet?.type === 'snapshot' || packet?.type === 'welcome') view = packet.snapshot || packet;
    if (packet?.state === 'done' && ['mining', 'picking'].includes(packet.type)) gathered.push(packet);
  }));
  await page.addInitScript(() => {
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang:'sv',sound:false}));
  });
  if (process.env.MUTATE === 'direct_gather') {
    const source = fs.readFileSync(require.resolve('../client/field.js'), 'utf8');
    await page.route('**/field.js', route => route.fulfill({ contentType:'text/javascript; charset=utf-8',
      body:source.replace('if (withinGatherReach(origin, target)) {', 'if (true) {') }));
  }
  await page.goto(world.url);
  for (const id of ['start','login-guest','cls-warrior']) await page.locator('#'+id).click();
  await page.locator('#name').fill('TouchGatherer');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, {timeout:60000});
  await page.locator('#connection-overlay').waitFor({state:'hidden'});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => window.Tutorial?.disable?.());
  const playerId = await page.evaluate(() => Online.id);
  const send = packet => page.evaluate(packet => Online.send(packet), packet);
  let ref = 0;
  const warp = async (point, tolerance = .15) => {
    await send({type:'debug',ref:++ref,command:{op:'teleport',zone:0,x:point.x,y:point.y}});
    await page.waitForFunction(({point,tolerance}) => Math.hypot(Field.hero.x-point.x,Field.hero.y-point.y) < tolerance,{point,tolerance});
  };
  const train = async (profession, npc) => {
    await warp(npc);
    await send({type:profession,request:{op:'train',npc:npc.id}});
  };
  assert.equal(await page.locator('#mini-gather').count(), 0, 'the minimap button was removed');
  await train('blacksmithing', smith);
  await world.waitFor(() => view.players.find(player => player.id === playerId)?.gathering?.ore,
    10000, 'mining training appears in the owner snapshot');
  await train('alchemy', alchemist);
  await world.waitFor(() => view.players.find(player => player.id === playerId)?.gathering?.flowers,
    10000, 'Alchemy training appears in the owner snapshot');

  const follow = async (point, color) => {
    const x = [12,-12].map(dx => point.x+dx).find(x => map.shapeFloor[Math.floor(point.y)]?.[Math.floor(x)]?.trim());
    assert(Number.isFinite(x),'resource has adjacent terrain for a marker check');
    await warp({x,y:point.y}, 4);
    await page.waitForFunction(({point,color}) => {
      const canvas = document.getElementById('minimap'), size = canvas.width;
      const scale = size / Field.miniTiles;
      const x = Math.round(size / 2 + (point.x - Field.hero.x) * scale);
      const y = Math.round(size / 2 + (point.y - Field.hero.y) * scale);
      const pixels = canvas.getContext('2d').getImageData(x-5,y-5,11,11).data;
      for (let i=0;i<pixels.length;i+=4) {
        if (color.every((channel,offset) => pixels[i+offset] === channel)) return true;
      }
      return false;
    }, {point,color}, {timeout:8000});
  };
  await follow(view.miningVeins[0],[255,209,122]);
  const inTown = p => p.x > map.city.x0 && p.x < map.city.x1 && p.y > map.city.y0 && p.y < map.city.y1;
  const garden = view.flowerPatches.find(inTown);
  const fieldPatch = view.flowerPatches.find(p => !inTown(p));
  assert(garden,'the active Alderhaven garden patch is in the snapshot');
  assert(fieldPatch, 'an outdoor patch is available away from overlapping town quest marks');
  await follow(fieldPatch,[255,166,219]);

  const walkAndGather = async (spot, type) => {
    const approach = await page.evaluate(spot => {
      const offsets = [[4,0],[-4,0],[0,4],[0,-4]];
      return offsets.map(([dx,dy]) => ({x:spot.x+dx,y:spot.y+dy}))
        .find(from => Field._debug.routeTo(spot,true,from,2).length);
    }, spot);
    assert(approach, 'there is a walkable starting point beyond gathering reach');
    await warp(approach, 1);
    assert(await page.evaluate(spot => Math.hypot(Field.hero.x-spot.x,Field.hero.y-spot.y) > 2.6, spot));
    await page.evaluate(({spot,type}) => {
      const canvas = document.getElementById('fieldcv').getBoundingClientRect();
      const [x,y] = Field.screenOf(spot.x,spot.y);
      Field.tapAt(canvas.left+x*canvas.width,canvas.top+y*canvas.height-(type==='picking' ? 8 : 12));
    }, {spot,type});
    await world.waitFor(() => gathered.some(packet => packet.type === type), 12000,
      'tapping a distant node walks into range and gathers').catch(async error => {
      const state = await page.evaluate(() => ({ point: [Field.hero.x, Field.hero.y],
        route: Field._debug.cityRoute, system: document.getElementById('system-log').textContent.slice(-500) }));
      throw new Error(type + ' did not finish. ' + JSON.stringify(state), { cause: error });
    });
  };
  await walkAndGather(garden, 'picking');
  await world.waitFor(() => !view.players.find(p => p.id === playerId).inCombat, 15000,
    'the miner is out of combat before starting the approach');
  const clearance = spot => Math.min(...map.slimes.map(enemy => Math.hypot(enemy.x-spot.x,enemy.y-spot.y)));
  const ore = [...view.miningVeins].sort((a,b) => clearance(b) - clearance(a))[0];
  await walkAndGather(ore, 'mining');
  const system = page.locator('#system-log');
  assert.match(await system.locator('p[data-category="alchemy"]').last().textContent(), /Du plockar .*Ängsguld/);
  assert.match(await system.locator('p[data-category="mining"]').last().textContent(), /Du bryter .*Tennmalm/);
  assert.match((await system.locator('p[data-category="progress"]').allTextContents()).join('\n'), /färdighet i Smide har höjts/);
  await page.screenshot({path:world.runDir+'/gathering-flower-phone.png'});
  await page.evaluate(() => Settings.show());
  const oreSetting = page.locator('#set-track-ore'), flowerSetting = page.locator('#set-track-flowers');
  assert(await oreSetting.isChecked() && await flowerSetting.isChecked());
  await oreSetting.uncheck();
  assert.equal(await page.evaluate(() => Prefs.trackOre), false);
  assert.equal(await page.evaluate(() => Prefs.trackFlowers), true);
  await flowerSetting.uncheck();
  assert.equal(await page.evaluate(() => Prefs.trackFlowers), false);
  assert.deepEqual(errors, []);
  console.log('Gathering minimap touch passed real training, Settings and active ore/flower pixels.', world.runDir);
})().catch(error => {
  console.error(error); process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
  await world.stop();
});
