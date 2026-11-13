// Spark Travel in a real browser: the destination is chosen on the world map. Debug commands stage only gold and visits.
// Run with the bounded runner. MUTATE=fare (the card loses its fare) and MUTATE=touch (a finger flies at once) must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-spark-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; if (process.env.VERBOSE) console.error('ok', checks, message); };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } }));
  const world = await call('start_world', { godMode: false, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/worldmap.js*', route => {
    let source = fs.readFileSync(path.join(root, 'client/worldmap.js'), 'utf8');
    const swap = (from, to) => { assert.ok(source.includes(from), `mutation target: ${from}`); source = source.replace(from, to); };
    if (process.env.MUTATE === 'fare') swap("el('span', `${d.cost} gold`, 'wm-spark-cost')", "el('span', '', 'wm-spark-cost')");
    if (process.env.MUTATE === 'touch') swap("const finger = event.pointerType === 'touch' || event.pointerType === 'pen';", 'const finger = false;');
    route.fulfill({ contentType: 'text/javascript', body: source });
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('SparkUI');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0 && Spark.atlas.naturalWidth > 0);
  // The fastest flight from Alderhaven to the Rimeward Camp crosses Skaldholm.
  const A = 'travel_alderhaven', B = 'travel_skaldholm', C = 'travel_rimeward', S = 'travel_saltby';
  const visit = async id => {
    await page.evaluate(id => {
      WorldMap.close(); City.close();
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
  const openMap = async () => {
    await page.locator('[data-view="sparkmap"]').click();
    await page.locator('#wm-spark').waitFor({ state: 'visible' });
  };
  const station = id => page.locator(`.wm-spark[data-station="${id}"]`);
  const card = page.locator('#wm-spark-card');
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_gold', gold: 100 } }));
  await page.waitForFunction(() => Field.hero.gold === 100);

  await visit(A);
  check(await page.locator('#npc-role').textContent() === 'Spark Travel', 'The travel master names the service');
  check(await page.locator('[data-view="sparkmap"]').count() === 1 && await page.locator('[data-travel]').count() === 0, 'The conversation offers the map, not a list of destinations');
  check(await page.evaluate(() => City.npcs.find(n => n.travelStop).key), 'The master always has a visible nameplate');
  await openMap();
  check(await page.locator('#npc-dialogue').isHidden() && await page.evaluate(() => WorldMap.open && WorldMap.travel && WorldMap.view === 'world'), 'Choosing Spark Travel opens the world map in place of the conversation');
  check((await page.locator('#wm-title').innerText()).includes('Spark Travel') && await page.locator('#wm-foot-travel').isVisible() && await page.locator('#wm-foot').isHidden(), 'The map says it is choosing a Spark Travel destination');
  check(await station(A).getAttribute('data-state') === 'here', 'The station the hero stands at is marked');
  check(await page.evaluate(id => {
    const b = document.querySelector(`.wm-spark[data-station="${id}"]`).getBoundingClientRect(), t = document.querySelector('.wm-tile[data-zone="0"]').getBoundingClientRect();
    const x = b.left + b.width / 2, y = b.top + b.height / 2;
    return x > t.left && x < t.right && y > t.top && y < t.bottom;
  }, A), 'Alderhaven is drawn inside Greenmeadow');
  const hiddenOk = await page.evaluate(() => {
    const areas = [WORLD_MAP, ...WORLD_MAP.zones], all = areas.flatMap((a, zone) => a.npcs.filter(n => n.travelStop).map(n => ({ zone, n })));
    const shown = new Set([...document.querySelectorAll('.wm-spark')].map(b => b.dataset.station));
    const wrong = all.filter(s => shown.has(s.n.id) !== (s.n.id === 'travel_alderhaven' || Field.fog.seen(s.zone, s.n.x, s.n.y)));
    return { shown: shown.size, all: all.length, wrong: wrong.map(s => s.n.id) };
  });
  check(hiddenOk.wrong.length === 0 && hiddenOk.shown < hiddenOk.all, `Undiscovered stations show only on charted ground (${JSON.stringify(hiddenOk)})`);
  await page.evaluate(() => document.querySelector('.wm-tile[data-zone="0"]').click());
  check(await page.evaluate(() => WorldMap.view === 'world' && WorldMap.travel), 'A zone cannot be opened while choosing a destination');
  await page.keyboard.press('Escape');
  check(await page.locator('#worldmap').isHidden() && await page.evaluate(() => !WorldMap.travel && !document.getElementById('wm-spark')), 'Escape closes the map and leaves travel mode');

  await visit(C); await visit(A); await openMap();
  check(await station(C).getAttribute('data-state') === 'blocked' && await station(C).getAttribute('aria-disabled') === 'true', 'A discovered station behind an unknown stop cannot be chosen yet');
  await station(C).hover();
  check((await card.innerText()).includes('Rimeward Camp') && (await card.innerText()).includes('Skaldholm'), 'Its card names the station and the stop that is missing');
  await station(C).click({ force: true });
  check(await page.evaluate(() => WorldMap.open && !Field.hero.sparkTravel && Field.hero.gold === 100), 'Clicking it neither flies nor charges');

  await visit(B); await visit(S); await visit(A); await openMap();
  check(await station(B).getAttribute('data-state') === 'open' && await station(C).getAttribute('data-state') === 'open', 'Discovering the stop between opens both stations');
  await station(C).hover();
  const text = await card.innerText();
  check(text.includes('Rimeward Camp'), 'Hovering a station shows its name');
  check(text.includes('40 gold'), `Hovering a two-leg station shows 40 gold (${text.replace(/\n/g, ' | ')})`);
  check(text.includes('Alderhaven → Skaldholm → Rimeward Camp'), 'The card lists every stop in order');
  check(await page.evaluate(() => document.getElementById('wm-spark-line').getAttribute('points').trim().split(/\s+/).length === 3), 'The route is drawn through its three stations');
  check(await page.evaluate(() => {
    const c = document.getElementById('wm-spark-card').getBoundingClientRect(), b = document.getElementById('wm-body').getBoundingClientRect();
    return c.width > 40 && c.left >= b.left && c.right <= b.right && c.top >= b.top && c.bottom <= b.bottom;
  }), 'The card stays inside the map');
  await station(B).hover();
  check((await card.innerText()).includes('Skaldholm') && (await card.innerText()).includes('20 gold'), 'Hovering a one-leg station shows 20 gold');
  await page.screenshot({ path: path.join(world.artifacts, 'spark-travel-map.png') });

  // A finger first sees the name and the fare; the flight starts from the Fly button.
  // The flights stay inside Greenmeadow: a browser that also loads the zones on the way outgrows the bounded runner.
  const tap = id => station(id).evaluate(b => b.dispatchEvent(new PointerEvent('click', { pointerType: 'touch', bubbles: true })));
  const fly = page.locator('#wm-spark-card .wm-spark-fly');
  await tap(C);
  check(await page.evaluate(() => WorldMap.open && !Field.hero.sparkTravel && Field.hero.gold === 100), 'A tap does not fly at once');
  check(await fly.isVisible() && (await card.innerText()).includes('40 gold'), 'The tapped station keeps its card with the fare and a Fly button');
  check((await fly.boundingBox()).height >= 34, 'The Fly button is a comfortable target');
  await tap(S);
  check((await card.innerText()).includes('Saltby') && (await card.innerText()).includes('20 gold') && await fly.isVisible(), 'Tapping another station moves the card to it');
  await page.evaluate(() => {
    window.sparkDraws = 0; const draw = Spark.draw;
    Spark.draw = (g, actor, t, beacon) => { if (!beacon && actor.sparkTravel) window.sparkDraws++; return draw(g, actor, t, beacon); };
    window.groundSends = [];
    const send = Online.send;
    Online.send = m => { if (m.type === 'attack' || m.type === 'move' || m.type === 'dash') window.groundSends.push(m); return send(m); };
  });
  await fly.click();
  await page.waitForFunction(() => !!Field.hero.sparkTravel && window.sparkDraws > 2);
  check(await page.locator('#worldmap').isHidden() && await page.locator('#npc-dialogue').isHidden(), 'Departure closes the map and leaves no conversation open');
  check(await page.evaluate(() => Field.hero.gold === 80 && Field.hero.sparkTravel.destination === 'Saltby'), 'The server charges exactly 20 gold and selects the destination');
  check(await page.locator('#city-travel').isDisabled() && (await page.locator('#city-travel').innerText()).includes('Spark Travel'), 'The HUD labels the active flight');
  await page.keyboard.press('w'); await page.keyboard.press('Space'); await page.keyboard.press('Shift');
  await page.locator('#fieldcv').click({ position: { x: 700, y: 400 } });
  check(await page.evaluate(() => window.groundSends.length === 0), 'Flight ignores walking, attack, dash and canvas input');
  await page.screenshot({ path: path.join(world.artifacts, 'spark-travel-flight.png') });
  await page.waitForFunction(() => Field.zone === 0 && !Field.hero.sparkTravel, null, { timeout: 120000 });
  check(await page.evaluate(() => {
    const n = City.npcs.find(n => n.id === 'travel_saltby'); return Math.hypot(Field.hero.x - n.x, Field.hero.y - n.y) < .2 && Field.hero.gold === 80;
  }), 'The flight ends at the Saltby master with no second charge');

  // With a mouse, one click on an open station flies.
  await page.keyboard.press('f'); await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  await openMap();
  check(await station(S).getAttribute('data-state') === 'here' && await station(A).getAttribute('data-state') === 'open', 'The map follows the hero to the new station');
  await station(A).click();
  await page.waitForFunction(() => Field.hero.sparkTravel?.destination === 'Alderhaven');
  check(await page.locator('#worldmap').isHidden() && await page.evaluate(() => Field.hero.gold === 60), 'A mouse click on a station starts the flight for 20 gold');
  check(await page.evaluate(() => Field.hero.hp === Field.hero.maxHp && !Field.hero.inCombat), 'Flight remains safe with god mode disabled');
  check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.artifacts }));
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {});
});
