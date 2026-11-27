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
  const gathered = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('websocket', socket => {
    socket.on('framesent', ({payload}) => {
      const packet = frameJson(payload);
      if (['move', 'mine', 'pick_flower'].includes(packet?.type)) requests.push(packet);
    });
    socket.on('framereceived', ({payload}) => {
      const packet = frameJson(payload);
      if (packet?.type === 'snapshot' || packet?.type === 'welcome') view = packet.snapshot || packet;
      if (packet?.state === 'done' && ['mining', 'picking'].includes(packet.type)) gathered.push(packet);
    });
  });
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

  const walkAndGather = async (spots, type) => {
    const target = await page.evaluate(spots => {
      for (const spot of spots) {
        for (const radius of [3.75, 5.5, 7]) {
          for (let i=0; i<16; i++) {
            const angle = i * Math.PI / 8;
            const approach = {x:spot.x + radius*Math.cos(angle), y:spot.y + radius*Math.sin(angle)};
            if (Field._debug.routeTo(spot,true,approach,2,() => true).length) return {spot,approach};
          }
        }
      }
      return null;
    }, spots);
    assert(target, 'there is a walkable starting point beyond gathering reach');
    const {spot,approach} = target;
    await warp(approach, 1);
    assert(await page.evaluate(spot => Math.hypot(Field.hero.x-spot.x,Field.hero.y-spot.y) > 2.6, spot));
    requests.length = 0;
    const hit = await page.evaluate(({spot,type}) => {
      const canvas = document.getElementById('fieldcv').getBoundingClientRect();
      const [x,y] = Field.screenOf(spot.x,spot.y), [sx,sy] = Field._debug.w2s(spot.x,spot.y);
      const project = Field._debug.w2s;
      const offset = [-9,-19,-3,0].find(dy => {
        const flower = Alchemy.hit(sx,sy+dy,project);
        if (type === 'picking') return flower?.id === spot.id;
        return !flower && Blacksmithing.pick(sx,sy+dy,project)?.id === spot.id;
      });
      if (offset == null) return false;
      Field.tapAt(canvas.left+x*canvas.width,canvas.top+(y+offset*y/sy)*canvas.height);
      return true;
    }, {spot,type});
    assert(hit, 'the gathering sprite can be hit at the chosen camera position');
    const action = type === 'picking' ? 'pick_flower' : 'mine';
    await world.waitFor(() => requests.some(packet => packet.type === action && packet.id === spot.id), 25000,
      'the client starts gathering from the selected node after walking into range').catch(async error => {
      const state = await page.evaluate(() => ({ point: [Field.hero.x, Field.hero.y],
        route: Field._debug.cityRoute, system: document.getElementById('system-log').textContent.slice(-500) }));
      throw new Error(type + ' did not start. ' + JSON.stringify({ ...state, spot, requests }), { cause: error });
    });
    assert.equal(requests[0].type, 'move', 'gathering first walks toward the distant target');
    assert(await page.evaluate(spot => Math.hypot(Field.hero.nx-spot.x,Field.hero.ny-spot.y) <= 2.6, spot),
      'the gathering request is sent from within reach');
    if (type === 'picking') {
      await world.waitFor(() => gathered.some(packet => packet.type === type), 8000, 'the flower is gathered');
    }
  };
  await walkAndGather([garden], 'picking');
  await world.waitFor(() => !view.players.find(p => p.id === playerId).inCombat, 15000,
    'the miner is out of combat before starting the approach');
  const clearance = spot => Math.min(...map.slimes.map(enemy => Math.hypot(enemy.x-spot.x,enemy.y-spot.y)));
  const ore = [...view.miningVeins].sort((a,b) => clearance(b) - clearance(a));
  await walkAndGather(ore, 'mining');
  const system = page.locator('#system-log');
  assert.match(await system.locator('p[data-category="alchemy"]').last().textContent(), /Du plockar .*Ängsguld/);
  const pick = gathered.find(packet => packet.type === 'picking');
  if (pick.skillUp) {
    await system.getByText('Din färdighet i Alkemi har höjts till ' + pick.skill + '.').waitFor({state:'attached'});
  }
  assert.doesNotMatch(await system.textContent(), /Du får \d+ × Ängsguld\./, 'the picked flower gets one receipt');
  await page.screenshot({path:world.runDir+'/gathering-flower-phone.png'});
  await page.evaluate(() => Settings.show());
  await page.locator('#set-tab-interface').tap();
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
