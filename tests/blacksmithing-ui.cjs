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
const miningAudio = process.env.MINING_AUDIO === '1';
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
    const call = touch ? "startGathering(vein, smithing, 'veins');" : "startGathering(vein, window.Blacksmithing, 'veins');";
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
  await page.addInitScript(({lang, miningAudio}) => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({lang,sound:miningAudio,musicVol:0}));
    if (!miningAudio) return;
    window.strikePlayback = [];
    const samples = new WeakSet(), buffers = new WeakSet();
    const fetchAsset = window.fetch;
    window.fetch = async (input, options) => {
      const response = await fetchAsset(input, options);
      if (!String(input).endsWith('/sfx_smith_strike.mp3')) return response;
      const bytes = response.arrayBuffer.bind(response);
      response.arrayBuffer = async () => {
        const sample = await bytes();
        samples.add(sample);
        return sample;
      };
      return response;
    };
    const decode = AudioContext.prototype.decodeAudioData;
    AudioContext.prototype.decodeAudioData = function (sample, ...callbacks) {
      const result = decode.call(this, sample, ...callbacks);
      if (!samples.has(sample)) return result;
      return result.then(buffer => {
        buffers.add(buffer);
        window.strikeDecodedAt = performance.now();
        return buffer;
      });
    };
    const start = AudioBufferSourceNode.prototype.start;
    AudioBufferSourceNode.prototype.start = function (...args) {
      if (buffers.has(this.buffer)) window.strikePlayback.push({at:performance.now(), state:this.context.state});
      return start.apply(this, args);
    };
  }, {lang:touch ? 'sv' : 'en', miningAudio});
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
  assert.match(await skill.textContent(), touch ? /Smidesfärdighet 1 \/ 600/ : /Blacksmithing skill 1 \/ 600/);
  const staple = page.locator(`[data-recipe="${gear}"]`);
  const craft = staple.locator(`[data-smith-action="${gear}"]`);
  await craft.click();
  await craft.filter({hasText:touch ? 'Smid föremål' : 'Forge item'}).waitFor();
  assert(await craft.isDisabled(),'ingredients are required');
  await page.locator('#npc-x').click();

  const safe = v => Math.min(...map.slimes.map(s => Math.hypot(s.x-v.x,s.y-v.y)));
  const vein = [...view.miningVeins].sort((a,b) => safe(b)-safe(a))[0];
  await warp(vein);
  // Wandering enemies can put the character in combat even with test invulnerability.
  const playerId = await page.evaluate(() => Online.id);
  const nearbyEnemies = view.slimes.filter(s => !s.dead && Math.hypot(s.x-vein.x,s.y-vein.y) < 16);
  const clearAt = view.tick;
  for (const enemy of nearbyEnemies) await debug({op:'kill_enemy',id:enemy.id});
  await w.waitFor(() => view.tick > clearAt && view.players.find(p => p.id === playerId)?.inCombat === false
    && nearbyEnemies.every(enemy => !view.slimes.some(s => s.id === enemy.id && !s.dead)),
    15000,'the test vein is clear of combat');
  await page.evaluate(id => {
    const draw = Blacksmithing.drawVein;
    Blacksmithing.drawVein = (g,vein,x,y) => {
      if (vein.id === id) {
        const scale = g.getTransform().a;
        window.smithVeinTest = {x,y,width:g.canvas.width/scale,height:g.canvas.height/scale};
      }
      draw(g,vein,x,y);
    };
  },vein.id);
  await page.waitForFunction(() => Boolean(window.smithVeinTest));
  if (miningAudio) await page.evaluate(() => {
    const mining = Blacksmithing.mining;
    window.mineTimes = {};
    Blacksmithing.mining = packet => {
      window.mineTimes[packet.state] = performance.now();
      mining(packet);
    };
  });
  await page.waitForTimeout(600); // let camera movement settle before taking the hitbox coordinates
  const target = await page.evaluate(() => {
    const {x,y,width,height} = window.smithVeinTest;
    const r = document.getElementById('fieldcv').getBoundingClientRect();
    return {x:r.x+x*r.width/width,y:r.y+(y-47)*r.height/height};
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
  if (miningAudio) {
    const {strikePlayback, mineTimes, strikeDecodedAt} = await page.evaluate(() => ({strikePlayback, mineTimes, strikeDecodedAt}));
    assert.ok(strikeDecodedAt < mineTimes.started, 'the first pull has its sound decoded before mining starts');
    assert.equal(strikePlayback.length, 3, 'the mining sample plays three times during the pull');
    for (const [i, {at, state}] of strikePlayback.entries()) {
      const offset = at - mineTimes.started;
      assert.equal(state, 'running', 'the sample plays through the live audio mixer');
      assert.ok(Math.abs(offset - (300 + i * 600)) < 220 && at < mineTimes.done,
        `strike ${i + 1} plays near contact before the reward (${Math.round(offset)} ms)`);
    }
    assert.deepEqual(errors,[]);
    console.log('Mining audio: all three pickaxe clangs played through Web Audio during a real mining pull.');
    return;
  }
  await page.screenshot({path:path.join(w.runDir,touch ? 'blacksmithing-touch-mining.png' : 'blacksmithing-desktop-mining.png')});

  await warp(smith);
  await debug({op:'give_item',item:'smith_bar_tin',quantity:3});
  await debug({op:'give_item',item:'smith_leather_strips',quantity:2});
  await page.waitForFunction(() => Inventory.bagQuantity('smith_leather_strips') === 2);
  await interact();
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
