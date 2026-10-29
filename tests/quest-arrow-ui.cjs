// Focused private-world checks: tracker controls and optional directional guidance.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld(); world.godMode = true;
const touch = process.env.QUEST_ARROW_TOUCH === '1';
let browser, checks = 0;
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: touch ? { width: 844, height: 390 } : { width: 1280, height: 800 }, hasTouch: touch, isMobile: touch, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => { errors.push(e.message); console.error('Browser:', e.message); });
  // A fulfilled document has no remote IP; Chrome asks permission for its loopback WebSocket.
  if (process.env.QUEST_ARROW_CANDIDATE) await page.context().grantPermissions(['local-network-access'], { origin: world.url });
  if (process.env.QUEST_ARROW_CANDIDATE) for (const file of ['index.html', 'quests.js', 'field.js', 'game.js', 'settings.js', 'online.css']) {
    const body = fs.readFileSync(path.join(process.env.QUEST_ARROW_CANDIDATE, file), 'utf8');
    await page.route(file === 'index.html' ? world.url : '**/' + file, r => r.fulfill({ body,
      contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html' }));
  }
  if (process.env.MUTATE) await page.route('**/field.js', async r => {
    const body = process.env.QUEST_ARROW_CANDIDATE ? fs.readFileSync(path.join(process.env.QUEST_ARROW_CANDIDATE, 'field.js'), 'utf8') : await (await r.fetch()).text();
    await r.fulfill({ body: body.replace('    drawQuestArrow(g);', '    /* disabled guidance mutation */'), contentType: 'text/javascript' });
  });
  await page.addInitScript(touch => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: touch ? 'sv' : 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} }));
  }, touch);
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('QuestArrow'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 15000 }).catch(async e => {
    console.error(await page.evaluate(() => ({ connected: Online.connected, hp: Field.hero?.hp, gameHidden: document.getElementById('scene-game').hidden, connection: document.getElementById('connection-text').textContent })));
    await page.screenshot({ path: path.join(world.runDir, 'failure.png') }); throw e;
  });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  const wait = (fn, arg) => page.waitForFunction(fn, arg, { timeout: 15000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  const quest = (id, action) => debug({ op: 'quest', id, action });
  const trackButton = id => page.locator(`.tracker-quest[data-quest="${id}"] .tracker-track`);
  check(await page.evaluate(() => Prefs.questArrow === false), 'Arrow starts off for existing preferences without the new setting');
  await quest('welcome', 'accept'); await wait(() => document.querySelector('.tracker-quest[data-quest="welcome"] .tracker-track'));
  if (touch) {
    check(await trackButton('welcome').textContent() === 'Spåra uppdrag', 'Direct tracking control is translated to Swedish');
    const size = await trackButton('welcome').boundingBox();
    check(size.width >= 43.9 && size.height >= 43.9, 'Tracking button remains a physical 44 px touch target');
  }
  await trackButton('welcome').click();
  check(await page.evaluate(() => Quests.tracked === 'welcome' && document.getElementById('quest-journal').hidden), 'Tracker starts tracking without opening the journal');
  check(await trackButton('welcome').getAttribute('aria-pressed') === 'true', 'Selected tracking control exposes its pressed state');
  check(await page.evaluate(() => {
    const { x, y } = Field.hero, target = Quests.navigationTarget(Field.zone, x, y);
    const goals = Quests.mapMarkers(Field.zone).filter(m => m.state === 'tracked');
    return goals.length === 3 && goals.includes(target) && goals.every(m => Math.hypot(m.x-x, m.y-y) >= Math.hypot(target.x-x, target.y-y));
  }), 'Navigation chooses the closest unfinished local objective');
  await trackButton('welcome').click();
  check(await page.evaluate(() => Quests.tracked === null && Quests.navigationTarget(0, 0, 0) === null), 'Tracking button can turn guidance off');
  await trackButton('welcome').click();
  // Observe the actual main canvas, including pixels and orientation, in a synchronous frame.
  const arrow = () => page.evaluate(() => {
    const g = document.getElementById('fieldcv').getContext('2d'), original = g.fill;
    const records = [];
    g.fill = function (...args) {
      if (this.fillStyle === '#a6ffcf') { const m = this.getTransform(); records.push({ angle: Math.atan2(m.b, m.a), x: m.e, y: m.f }); }
      return original.apply(this, args);
    };
    try {
      Field._debug.drawFrame(5);
      const data = g.getImageData(0, 0, g.canvas.width, g.canvas.height).data;
      let pixels = 0;
      for (let i = 0; i < data.length; i += 4) if (data[i] === 166 && data[i+1] === 255 && data[i+2] === 207) pixels++;
      const p = Field.hero, t = Quests.navigationTarget(Field.zone, p.x, p.y);
      const [x,y] = Field._debug.w2s(p.x,p.y), [tx,ty] = t ? Field._debug.w2s(t.x,t.y) : [x,y];
      return { records, pixels, scale: g.getTransform().a, expected: Math.atan2(ty-y,tx-x) };
    } finally { g.fill = original; }
  });
  check((await arrow()).records.length === 0, 'Tracking alone does not draw an arrow while the setting is off');
  await page.evaluate(() => { Field.setPaused(true); Settings.show(); });
  if (touch) check(await page.locator('#set-quest-arrow').evaluate(n => n.parentElement.textContent.trim() === 'Pil' && n.parentElement.title === 'Peka mot det spårade uppdragets mål.'), 'Arrow setting and help have Swedish text');
  check(!(await page.locator('#set-quest-arrow').isChecked()), 'Settings shows Arrow unchecked by default');
  await page.locator('#set-quest-arrow').check();
  check(await page.evaluate(() => Prefs.questArrow && JSON.parse(localStorage.getItem('valhallasc.save.v1')).questArrow === true), 'Arrow setting persists the checked choice');
  await page.evaluate(() => { Settings.close(false); Field.setPaused(false); });
  const drawn = await arrow();
  check(drawn.records.length === 1 && drawn.pixels > Math.max(5, 50*drawn.scale**2), 'Enabled setting paints a visible arrow on the game canvas: ' + JSON.stringify(drawn));
  check(Math.abs(drawn.records[0].angle - drawn.expected) < .001, 'Arrow faces the objective in the isometric screen projection');
  await page.screenshot({ path: path.join(world.runDir, 'quest-arrow.png') });
  // The narrow touch check covers the new controls/rendering/localization; zone transitions run on desktop.
  if (touch) {
    await page.reload(); await page.waitForFunction(() => window.Prefs);
    check(await page.evaluate(() => Prefs.questArrow === true), 'Arrow preference survives reloading');
    check(errors.length === 0, 'No browser errors: ' + errors.join('; '));
    console.log(`quest-arrow-ui (Swedish touch): ${checks} checks passed; ${world.runDir}`); return;
  }
  await quest('slime_patrol', 'accept'); await wait(() => document.querySelector('.tracker-quest[data-quest="slime_patrol"] .tracker-track'));
  await trackButton('slime_patrol').click();
  check(await page.evaluate(() => Quests.tracked === 'slime_patrol') && await trackButton('welcome').getAttribute('aria-pressed') === 'false', 'Tracking a second quest replaces the first selection');
  await debug({ op: 'teleport', zone: 2, x: 20, y: 20 }); await wait(() => Field.zone === 2);
  check(await page.evaluate(() => {
    const target = Quests.navigationTarget(Field.zone, Field.hero.x, Field.hero.y), zones = [WORLD_MAP, ...WORLD_MAP.zones];
    // Independent reverse BFS gives the minimum number of exits back to Greenmeadow.
    const distance = new Map([[0,0]]), queue = [0];
    for (const to of queue) for (let from=0; from<zones.length; from++) if (!distance.has(from) && zones[from].portals?.some(p => p.to === to)) { distance.set(from,distance.get(to)+1); queue.push(from); }
    return target?.viaPortal && target.destinationZone === 0 && zones[2].portals.some(p => p.x === target.x && p.y === target.y && distance.get(p.to) === distance.get(2)-1);
  }), 'A remote quest points to an actual exit on a shortest zone route');
  await trackButton('welcome').click();
  await quest('welcome', 'complete');
  await wait(() => Field.hero.quests.find(q => q.id === 'welcome')?.counts.every(n => n >= 1));
  check(await page.evaluate(() => {
    const guide = WORLD_MAP.npcs.find(n => n.id === 'guide'), target = Quests.navigationTarget(0, 0, 0);
    return target?.x === guide.x && target.y === guide.y;
  }), 'Completing a tracked quest switches guidance to its turn-in NPC');
  await quest('welcome', 'claim'); await wait(() => Quests.tracked === null);
  check((await arrow()).records.length === 0, 'Claiming a quest clears its arrow');
  await page.reload(); await page.waitForFunction(() => window.Prefs);
  check(await page.evaluate(() => Prefs.questArrow === true), 'Arrow preference survives reloading');
  check(errors.length === 0, 'No browser errors: ' + errors.join('; '));
  console.log(`quest-arrow-ui: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { if (browser) await browser.close(); await world.stop(); });
