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
  const track = page.locator('#mini-gather');
  assert(await track.isHidden(), 'no Track button before learning a gathering skill');

  await train('blacksmithing', smith);
  await track.waitFor();
  assert.equal(await track.textContent(), 'Spåra');
  const bounds = await track.boundingBox();
  assert(bounds.width >= 44 && bounds.height >= 44,`Track is a full-sized touch target (${bounds.width} × ${bounds.height})`);
  assert(await track.evaluate(button => {
    const r = button.getBoundingClientRect();
    return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2) === button;
  }),'the tracker is uncovered on a landscape phone');
  await track.tap();
  assert.equal(await track.textContent(), 'Malm');
  await track.tap();
  assert.equal(await track.getAttribute('aria-pressed'), 'false','an ore-only character skips the flower mode');

  await train('alchemy', alchemist);
  await world.waitFor(() => view.players.find(player => player.id === playerId)?.gathering?.flowers,
    10000,'Alchemy training appears in the owner snapshot');
  await track.tap();
  assert.equal(await track.textContent(), 'Malm');

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
  await track.tap();
  assert.equal(await track.textContent(), 'Blommor');
  const garden = view.flowerPatches.find(p => p.x > map.city.x0 && p.x < map.city.x1 && p.y > map.city.y0 && p.y < map.city.y1);
  assert(garden,'the active Alderhaven garden patch is in the snapshot');
  await follow(garden,[255,166,219]);
  await page.screenshot({path:world.runDir+'/gathering-flower-phone.png'});
  await track.tap();
  assert.equal(await track.textContent(), 'Spåra');
  assert.equal(await track.getAttribute('aria-pressed'), 'false');
  assert.deepEqual(errors, []);
  console.log('Gathering minimap touch passed real training, Swedish modes and active ore/flower pixels.', world.runDir);
})().catch(error => {
  console.error(error); process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
  await world.stop();
});
