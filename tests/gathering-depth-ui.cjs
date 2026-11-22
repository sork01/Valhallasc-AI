// Run through scripts/test-touch-bounded.sh against a private world.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('./lib/playwright.cjs');
const {TestWorld} = require('../scripts/testing/driver.cjs');

const {spawn: point} = JSON.parse(fs.readFileSync(require.resolve('../world/map.txt')));
const world = new TestWorld();
let browser;

(async () => {
  await world.start();
  browser = await chromium.launch({headless:true,args:['--disable-gpu']});
  const page = await browser.newPage({
    viewport:{width:844,height:390}, hasTouch:true, isMobile:true, deviceScaleFactor:1, reducedMotion:'reduce',
  });
  if (process.env.MUTATE === 'foreground') {
    let source = fs.readFileSync(require.resolve('../client/field.js'),'utf8');
    for (const node of ['vein','patch']) {
      const entry = `d: ${node}.x + ${node}.y, ${node}, sx, sy`;
      assert(source.includes(entry));
      source = source.replace(entry,`d: Infinity, ${node}, sx, sy`);
    }
    await page.route('**/field.js',route => route.fulfill({contentType:'application/javascript',body:source}));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1',JSON.stringify({lang:'en',sound:false})));
  const errors = [];
  page.on('pageerror',error => errors.push(error.message));
  await page.goto(world.url);
  for (const id of ['start','login-guest','cls-warrior']) await page.locator('#'+id).click();
  await page.locator('#name').fill('DepthGatherer');
  await page.locator('#go').click({timeout:60000});
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites,null,{timeout:60000});
  await page.locator('#connection-overlay').waitFor({state:'hidden'});
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();

  await page.evaluate(({x,y}) => {
    window.Tutorial?.disable?.();
    // Place the two resources alongside each other on open ground, at the same depth.
    const vein = {id:9991,tier:0,x:x-.25,y:y+.25};
    const patch = {id:9992,flower:0,x:x+.25,y:y-.25};
    const syncSmith = Blacksmithing.sync, syncAlchemy = Alchemy.sync;
    Blacksmithing.sync = (packet,own,cue) => syncSmith({...packet,miningVeins:[vein]},own,cue);
    Alchemy.sync = (packet,cue) => syncAlchemy({...packet,flowerPatches:[patch]},cue);

    const canvas = document.getElementById('fieldcv');
    const g = canvas.getContext('2d');
    const setTransform = g.setTransform.bind(g), drawImage = g.drawImage.bind(g);
    g.setTransform = (...args) => {
      window.gatheringFrame = [];
      setTransform(...args);
    };
    g.drawImage = (image,...args) => {
      if (image.src?.endsWith('/blacksmithing.png')) window.gatheringFrame?.push(['ore',args[6],args[7]]);
      if (image.src?.endsWith('/alchemy.png')) window.gatheringFrame?.push(['flowers',args[6],args[7]]);
      drawImage(image,...args);
    };
    const drawAura = Rebirth.drawAura;
    Rebirth.drawAura = (ctx,...args) => {
      // The private character is centered after the camera catches up.
      const {e,f} = ctx.getTransform();
      if (ctx === g && Math.abs(e-canvas.width/2) < 4 && Math.abs(f-canvas.height/2) < 4) {
        window.gatheringFrame?.push(['character']);
      }
      drawAura(ctx,...args);
    };
  },point);

  for (const [side,offset,ref] of [['behind',-.375,1],['in-front',.375,2]]) {
    const position = {x:point.x+offset,y:point.y+offset};
    await page.evaluate(({position,ref}) => Online.send({
      type:'debug',ref,command:{op:'teleport',zone:0,...position},
    }),{position,ref});
    await page.waitForFunction(({x,y}) => Math.hypot(Field.hero.x-x,Field.hero.y-y) < .08,position);
    const sample = await page.waitForFunction(() => {
      const frame = window.gatheringFrame;
      return frame?.length === 3 ? frame : false;
    });
    const frame = await sample.jsonValue();
    await page.screenshot({path:path.join(world.runDir,`gathering-${side}.png`),clip:{x:340,y:126,width:164,height:142}});
    const order = frame.map(([kind]) => kind);
    for (const node of ['ore','flowers']) {
      assert(order.includes(node) && order.includes('character'),'the resource and character were painted in the same frame');
      assert.equal(order.indexOf(node) < order.indexOf('character'),side === 'in-front',
        `the character ${side} paints in the correct order with ${node}. Draw order: ${order.join(', ')}`);
    }
    assert.deepEqual(frame.find(([kind]) => kind === 'ore').slice(1),[92,92]);
    assert.deepEqual(frame.find(([kind]) => kind === 'flowers').slice(1),[46,46]);
  }
  assert.deepEqual(errors,[]);
  console.log('Phone world canvas passed ore size and character depth on both sides of ore and flowers.',world.runDir);
})().catch(error => {
  console.error(error,world.runDir);
  process.exitCode = 1;
}).finally(async () => {
  await browser?.close();
  await world.stop();
});
