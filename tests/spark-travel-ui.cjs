// Real browser dialogue and Spark Travel; debug commands stage only gold and visits.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-spark-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const world = await call('start_world', { godMode: false, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('SparkUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0 && Spark.atlas.naturalWidth > 0);
  const A = 'travel_alderhaven', B = 'travel_cinderwatch', C = 'travel_rimeward';
  const visit = async id => {
    await page.evaluate(id => {
      City.close();
      const areas = [WORLD_MAP, ...WORLD_MAP.zones], zone = areas.findIndex(a => a.npcs.some(n => n.id === id)), n = areas[zone].npcs.find(n => n.id === id);
      Online.send({ type: 'debug', command: { op: 'teleport', zone, x: n.x, y: n.y + 1.2 } });
    }, id);
    await page.waitForFunction(id => {
      const n = City.npcs.find(n => n.id === id);
      return n && Math.hypot(Field.hero.x - n.x, Field.hero.y - n.y) < 2;
    }, id);
    await page.evaluate(id => Online.send({ type: 'interact', npc: id }), id);
    await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
    await page.waitForFunction(id => Field.hero.travelStops?.includes(id), id);
  };
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_gold', gold: 100 } }));
  await page.waitForFunction(() => Field.hero.gold === 100);
  await visit(A);
  check(await page.locator('#npc-role').textContent() === 'Spark Travel', 'The travel master names the service');
  check(await page.locator('[data-travel]').count() === 4, 'All four destinations are listed');
  check(await page.locator(`[data-travel="${C}"]`).isDisabled(), 'An undiscovered destination is disabled');
  check((await page.locator(`[data-travel="${C}"]`).innerText()).includes('40 gold'), 'Two-stop travel shows 40 gold');
  check((await page.locator(`[data-travel="${B}"]`).innerText()).includes('20 gold'), 'One-stop travel shows 20 gold');
  check(await page.evaluate(() => City.npcs.find(n => n.travelStop).key), 'The master always has a visible nameplate');
  await visit(C); await visit(A);
  check(await page.locator(`[data-travel="${C}"]`).isDisabled(), 'Discovering only the first and third stops still blocks travel');
  check((await page.locator(`[data-travel="${C}"] .spark-route`).innerText()).includes('Cinderwatch'), 'The menu identifies the missing intermediate master');
  await visit(B); await visit(A);
  check(await page.locator(`[data-travel="${C}"]`).isEnabled(), 'Discovering the intermediate stop unlocks the route');
  check(await page.locator(`[data-travel="${C}"] .spark-route`).innerText() === 'Alderhaven → Cinderwatch Camp → Rimeward Camp', 'The route lists every stop in order');
  check(await page.evaluate(() => Field.hero.travelStops.length === 3), 'Repeated conversations create one discovery each');
  await page.screenshot({ path: path.join(world.artifacts, 'spark-travel-menu.png') });
  await page.evaluate(() => {
    window.sparkDraws = 0; const draw = Spark.draw;
    Spark.draw = (g, actor, t, beacon) => { if (!beacon && actor.sparkTravel) window.sparkDraws++; return draw(g, actor, t, beacon); };
    window.groundSends = [];
    const send = Online.send;
    Online.send = m => { if (m.type === 'attack' || m.type === 'move' || m.type === 'dash') window.groundSends.push(m); return send(m); };
  });
  await page.locator(`[data-travel="${C}"]`).click();
  await page.waitForFunction(() => !!Field.hero.sparkTravel && window.sparkDraws > 2);
  check(await page.locator('#npc-dialogue').isHidden(), 'Departure closes the dialogue');
  check(await page.evaluate(() => Field.hero.gold === 60 && Field.hero.sparkTravel.destination === 'Rimeward Camp'), 'The server charges exactly 40 gold and selects the destination');
  check(await page.locator('#city-travel').isDisabled() && (await page.locator('#city-travel').innerText()).includes('Spark Travel'), 'The HUD labels the active flight');
  await page.keyboard.press('w'); await page.keyboard.press('Space'); await page.keyboard.press('Shift');
  await page.locator('#fieldcv').click({ position: { x: 700, y: 400 } });
  check(await page.evaluate(() => window.groundSends.length === 0), 'Flight ignores walking, attack, dash and canvas input');
  check(await page.evaluate(() => Spark.atlas.naturalWidth === 768 && Spark.atlas.naturalHeight === 64), 'The real twelve-frame PixelFlow atlas loads');
  const art = await page.evaluate(() => {
    const c = document.createElement('canvas'); c.width = 160; c.height = 160; const g = c.getContext('2d'), hashes = new Set();
    for (let k = 0; k < 12; k++) {
      g.clearRect(0,0,160,160); g.save(); g.translate(80,140); Spark.draw(g,{fx:1,fy:0},k/12); g.restore();
      let h=0; for(const x of g.getImageData(0,0,160,160).data) h=(Math.imul(h,31)+x)|0; hashes.add(h);
    }
    return hashes.size;
  });
  check(art === 12, 'Every spark frame produces distinct animated pixels');
  await page.screenshot({ path: path.join(world.artifacts, 'spark-travel-flight.png') });
  await page.waitForFunction(() => Field.zone === 1 && !!Field.hero.sparkTravel, null, { timeout: 15000 });
  check(await page.evaluate(() => Field.hero.sparkTravel.stops.includes('travel_cinderwatch')), 'The client sees the intermediate zone while the flight continues');
  await page.waitForFunction(() => Field.zone === 2 && !Field.hero.sparkTravel, null, { timeout: 20000 });
  check(await page.evaluate(() => {
    const n=City.npcs.find(n=>n.id==='travel_rimeward'); return Math.hypot(Field.hero.x-n.x,Field.hero.y-n.y)<.2 && Field.hero.gold===60;
  }), 'The flight ends at the third master with no second charge');
  await page.keyboard.press('f'); await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  check(await page.locator(`[data-travel="${B}"]`).isEnabled(), 'Normal NPC interaction returns after landing');
  check(await page.evaluate(() => Field.hero.hp === Field.hero.maxHp && !Field.hero.inCombat), 'Flight remains safe with god mode disabled');
  check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.artifacts }));
})().catch(e => { console.error(e.stack || e); process.exitCode=1; }).finally(async () => {
  if(browser)await browser.close();if(started)await call('stop_world').catch(()=>{});await client.close().catch(()=>{});
});
