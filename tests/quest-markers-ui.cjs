// UI-QUEST-MARKERS only: private real client, authoritative quest transitions, paired minimap pixels.
process.env.REAL_SPRITES = '1';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'quest-markers', version: '1' });
let browser, started = false, checks = 0;
const check = (ok, message) => { assert.ok(ok, message); checks++; console.log(`${checks}: ${message}`); };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, JSON.stringify(r.content)); return r.structuredContent;
}
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } });
  transport.stderr?.on('data', data => process.stderr.write(data));
  await client.connect(transport);
  const world = await call('start_world', { godMode: true, startLevel: 1, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/quests.js', async route => {
    const r = await route.fetch(); await route.fulfill({ response: r, body: (await r.text()) + '\nQuests.mapMarkers = () => [];\n' });
  });
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Map Quests'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.warriorSprites?.source?.parts?.body, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  const wait = (fn, arg) => page.waitForFunction(fn, arg, { timeout: 15000 });
  const markers = () => page.evaluate(() => Quests.mapMarkers(Field.zone));
  const quest = (id, action) => debug({ op: 'quest', id, action });
  async function map(zone) {
    await page.evaluate(() => { Quests.close(); WorldMap.close(); WorldMap.show(); });
    await page.locator(`.wm-tile[data-zone="${zone}"]`).click();
    await wait(zone => WorldMap.view === 'zone' && WorldMap.zone === zone, zone);
  }
  async function track(id) {
    await page.evaluate(() => { WorldMap.close(); Quests.close(); Quests.show(); });
    await page.locator(`#quest-list .quest-entry[data-quest="${id}"] > summary`).click();
    await page.locator(`#quest-list .quest-entry[data-quest="${id}"] button`).filter({ hasText: /^Track quest$|^Tracking$/ }).click();
    await page.evaluate(() => Quests.close());
  }
  // Capture two real frames synchronously with the guidance layer on/off. No shared files or server state are changed.
  async function miniDelta(state, npc) {
    return page.evaluate(({ state, npc }) => {
      const original = Quests.mapMarkers, cv = document.getElementById('minimap'), g = cv.getContext('2d');
      const list = original(Field.zone), wanted = list.filter(m => m.state === state && (!npc || m.npc === npc));
      const render = on => { Quests.mapMarkers = zone => on ? original(zone) : []; Field._debug.drawFrame(5); return g.getImageData(0, 0, cv.width, cv.height).data; };
      try {
        const a = render(false), b = render(true), size = Field._debug.zones[Field.zone].size;
        return wanted.map(m => {
          let pixels = 0, colored = 0; const x = Math.round(m.x / size * cv.width), y = Math.round(m.y / size * cv.height);
          const rgb = m.color.slice(1).match(/../g).map(h => parseInt(h, 16));
          for (let py = Math.max(0, y - 9); py < Math.min(cv.height, y + 10); py++) for (let px = Math.max(0, x - 9); px < Math.min(cv.width, x + 10); px++) {
            const k = (py * cv.width + px) * 4;
            if ([0, 1, 2].some(j => a[k + j] !== b[k + j])) pixels++;
            if ([0, 1, 2].every(j => Math.abs(b[k + j] - rgb[j]) < 15)) colored++;
          }
          return { npc: m.npc, pixels, colored, fogged: !Field.fog.seen(Field.zone, m.x, m.y) };
        });
      } finally { Quests.mapMarkers = original; Field._debug.drawFrame(5); }
    }, { state, npc });
  }
  const initial = await markers();
  check(initial.some(m => m.npc === 'guide' && m.symbol === '!' && m.color === '#ffdf88'), 'Available giver gets a gold !');
  check(!initial.some(m => ['smith', 'merchant'].includes(m.npc)), 'Prerequisite-locked quests have no marker');
  check(!initial.some(m => m.state === 'tracked'), 'No target until the player tracks a quest');
  const gold = await miniDelta('available', 'guide');
  check(gold.length === 1 && gold[0].fogged && gold[0].pixels > 15 && gold[0].colored > 2, 'Gold ! is painted on the actual minimap above unexplored fog');
  await map(0);
  check(await page.locator('.wm-quest[data-npc="guide"]').textContent() === '!', 'Zone map shows the same available giver');
  check(await page.locator('.wm-quest[data-npc="guide"]').evaluate(n => getComputedStyle(n).color) === 'rgb(255, 223, 136)', 'Zone map gold matches the minimap');
  check(await page.locator('.wm-quest[data-npc="guide"]').evaluate(n => {
    const npc = WORLD_MAP.npcs.find(n => n.id === 'guide'); return Math.abs(parseFloat(n.style.left) - npc.x / WORLD_MAP.size * 100) < .001 && Math.abs(parseFloat(n.style.top) - npc.y / WORLD_MAP.size * 100) < .001;
  }), 'Giver marker uses the actual NPC coordinates');
  check(await page.locator('#wm-fog').evaluate(cv => cv.getContext('2d').getImageData(304, 640, 1, 1).data[3] > 100), 'Guidance does not clear the ground fog');
  check(await page.locator('.wm-quest-legend').textContent().then(t => t.includes('Available') && t.includes('Ready to turn in') && t.includes('Tracked quest')), 'Zone map explains all three symbols');
  await quest('welcome', 'accept');
  await wait(() => document.querySelector('.tracker-quest[data-quest="welcome"]'));
  await wait(() => !document.querySelector('.wm-quest[data-npc="guide"]'));
  check(!(await markers()).some(m => m.npc === 'guide'), 'Accepting removes the available marker while the map is open');
  await track('welcome'); await map(0);
  check(await page.locator('.wm-quest[data-state="tracked"]').count() === 3, 'Tracked welcome marks all three unfinished talk destinations');
  const targets = await miniDelta('tracked');
  check(targets.length === 3 && targets.every(m => m.pixels > 15 && m.colored > 2), 'Tracked destinations are real green diamonds on the minimap');
  await quest('welcome', 'complete');
  await wait(() => document.querySelector('.wm-quest[data-npc="guide"][data-state="ready"]'));
  check(await page.locator('.wm-quest[data-npc="guide"]').textContent() === '?' && await page.locator('.wm-quest[data-npc="guide"]').evaluate(n => getComputedStyle(n).color) === 'rgb(100, 181, 255)', 'Completion changes the giver to a blue ? without closing the map');
  check(await page.locator('.wm-quest[data-state="tracked"]').count() === 1 && await page.locator('.wm-quest[data-state="tracked"]').getAttribute('data-quest') === 'welcome', 'Completed tracked quest replaces objectives with its hand-in destination');
  const blue = await miniDelta('ready', 'guide');
  check(blue.length === 1 && blue[0].pixels > 15 && blue[0].colored > 2, 'Blue turn-in ? is drawn on the real minimap');
  await page.screenshot({ path: path.join(world.artifacts, 'quest-turn-in-map.png') });
  await quest('welcome', 'claim');
  await wait(() => !document.querySelector('.wm-quest[data-npc="guide"]') && !document.querySelector('.wm-quest[data-state="tracked"]'));
  check(!(await markers()).some(m => m.npc === 'guide' || m.state === 'tracked'), 'Claimed quest and its tracked target disappear');
  await debug({ op: 'set_level', level: 20 });
  await wait(() => document.querySelector('.wm-quest[data-npc="guide"][data-state="available"]'));
  check((await markers()).some(m => m.npc === 'guide'), 'Level changes unlock giver markers while progress and zone stay the same');
  check(await page.evaluate(() => {
    Quests.setLevel(1); const low = Quests.mapMarkers(0); Quests.setLevel(20); const high = Quests.mapMarkers(0);
    return !low.some(m => m.npc === 'guide') && high.some(m => m.npc === 'guide') && low !== high;
  }), 'A level-only change invalidates cached markers without any quest-progress update');
  await quest('slime_patrol', 'accept'); await wait(() => document.querySelector('.tracker-quest[data-quest="slime_patrol"]'));
  await track('slime_patrol'); await map(0);
  check(await page.evaluate(() => {
    const target = Quests.mapMarkers(0).find(m => m.state === 'tracked');
    return target && WORLD_MAP.slimes.some(s => ['green', 'blue', 'pink', 'yellow'].includes(s.kind) && s.x === target.x && s.y === target.y);
  }), 'Slime hunt target anchors to a real matching spawn, including the slime alias');
  check((await miniDelta('tracked')).every(m => m.pixels > 15 && m.colored > 2), 'Kill-area diamond is painted in the minimap');
  await quest('slime_patrol', 'complete'); await wait(() => document.querySelector('.wm-quest[data-npc="gatekeeper"][data-state="ready"]'));
  await quest('slime_patrol', 'claim'); await wait(() => document.querySelector('.wm-quest[data-npc="merchant"][data-state="available"]'));
  check((await markers()).some(m => m.npc === 'smith') && (await markers()).some(m => m.npc === 'merchant'), 'Claiming a prerequisite unlocks both next givers');
  await quest('meadow_bounty', 'accept'); await wait(() => document.querySelector('.tracker-quest[data-quest="meadow_bounty"]'));
  await quest('meadow_bounty', 'complete'); await wait(() => document.querySelector('.wm-quest[data-npc="merchant"][data-state="ready"]'));
  check((await markers()).find(m => m.npc === 'merchant')?.color === '#64b5ff', 'Repeatable turn-in uses the same blue ?');
  await quest('meadow_bounty', 'claim'); await wait(() => document.querySelector('.wm-quest[data-npc="merchant"][data-state="available"]'));
  check((await markers()).find(m => m.npc === 'merchant')?.color === '#ffdf88', 'Repeatable quest becomes a gold ! again after claiming');
  await quest('welcome', 'reset'); await wait(() => Quests.offered('guide').some(q => q.id === 'welcome'));
  await quest('welcome', 'accept'); await wait(() => document.querySelector('.tracker-quest[data-quest="welcome"]'));
  await quest('welcome', 'complete'); await wait(() => document.querySelector('.wm-quest[data-npc="guide"][data-state="ready"]'));
  check((await markers()).filter(m => m.npc === 'guide').length === 1 && (await markers()).find(m => m.npc === 'guide')?.state === 'ready', 'A turn-in takes priority over available Arena quests at the same giver');

  // Presentation fixtures on the full real client cover remote-zone and partial objectives without grinding quests.
  await debug({ op: 'explore_all' }); await wait(() => Field.explored?.[6] === 511);
  await page.evaluate(() => { window.questFixtureUpdate = Quests.update; Quests.update = () => {}; });
  const fixture = data => page.evaluate(data => questFixtureUpdate(data), data);
  const state = (id, counts, claimed = false) => ({ id, counts, claimed, completions: claimed ? 1 : 0 });
  await fixture([state('wyrd_moonpetal', [0, 0])]); await track('wyrd_moonpetal'); await map(6);
  check(await page.locator('.wm-quest[data-state="tracked"]').count() === 2, 'Viewing another zone shows both its tracked visit spot and kill area');
  check(await page.evaluate(() => Field.zone === 0 && Quests.mapMarkers(6).filter(m => m.state === 'tracked').some(m => {
    const place = WORLD_MAP.zones[5].places.find(p => p.id === 'wyrd_glade'); return m.x === place.x && m.y === place.y;
  })), 'Visit marker uses the target place in the viewed zone, independently of the hero zone');
  check(await page.locator('.wm-quest[data-npc="guide"]').count() === 0 && await page.locator('.wm-quest[data-npc="wyrd_warden"]').count() === 1, 'NPC markers never leak between zones');
  await fixture([state('wyrd_moonpetal', [1, 0])]); await wait(() => document.querySelectorAll('.wm-quest[data-state="tracked"]').length === 1);
  check(await page.locator('.wm-quest[data-state="tracked"]').count() === 1, 'A partial objective update removes only the completed destination');
  await fixture([state('wyrd_moonpetal', [1, 3])]); await wait(() => document.querySelector('.wm-quest[data-npc="wyrd_healer"][data-state="ready"]'));
  check(await page.evaluate(() => {
    const n = WORLD_MAP.zones[5].npcs.find(n => n.id === 'wyrd_healer'), target = Quests.mapMarkers(6).find(m => m.state === 'tracked'); return target.x === n.x && target.y === n.y;
  }), 'Remote ready quest tracks the actual hand-in NPC');
  await fixture([state('city_seals', [0, 0, 0, 0])]); await track('city_seals'); await map(1);
  check(await page.evaluate(() => {
    const marks = Quests.mapMarkers(1).filter(m => m.state === 'tracked'), n = WORLD_MAP.zones[0].npcs.find(n => n.id === 'crags_captain'); return marks.length === 1 && marks[0].x === n.x && marks[0].y === n.y;
  }), 'Cross-zone talk targets resolve only the NPC in the zone being viewed');
  await fixture([state('city_vault_bosses', [0, 0, 0, 0])]); await track('city_vault_bosses'); await map(5);
  check(await page.locator('.wm-quest[data-state="tracked"]').count() === 4, 'A hub quest tracks its four boss targets inside the adjacent dungeon');
  await fixture([state('slime_patrol', [6], true), state('ironhide_hunt', [0])]); await track('ironhide_hunt'); await map(0);
  await page.locator('.wm-quest[data-npc="guide"]').hover();
  check(await page.locator('.wm-quest[data-npc="guide"]').getAttribute('title').then(t => t.includes('Available')), 'Available marker has a useful tooltip');
  await page.locator('.wm-quest[data-state="tracked"]').hover();
  check(await page.locator('.wm-quest[data-state="tracked"]').getAttribute('title').then(t => t.startsWith('Tracked quest') && t.includes('Ironhide Beetles')), 'Tracked diamond can be hovered for the quest and objective');
  check(await page.evaluate(() => [WORLD_MAP, ...WORLD_MAP.zones].every((z, zone) => {
    const expected = [];
    for (const n of z.npcs || []) {
      const container = document.createElement('div'); Quests.npc(n.id, container, () => {});
      const rows = [...container.querySelectorAll('[data-status]')], state = rows.some(r => r.dataset.status === 'ready') ? 'ready' : rows.some(r => r.dataset.status === 'available') ? 'available' : null;
      if (state) expected.push(n.id + ':' + state);
    }
    return JSON.stringify(expected.sort()) === JSON.stringify(Quests.mapMarkers(zone).filter(m => m.npc).map(m => m.npc + ':' + m.state).sort());
  })), 'All zone markers match actual gossip eligibility, excluding active, completed, locked and upcoming quests');
  await page.screenshot({ path: path.join(world.artifacts, 'quest-markers-map.png') });
  await page.setViewportSize({ width: 844, height: 390 }); await page.waitForTimeout(300);
  check(await page.locator('.wm-quest[data-state="tracked"]').isVisible(), 'Tracked destination remains visible on a short screen');
  await page.screenshot({ path: path.join(world.artifacts, 'quest-markers-small.png') });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => { WorldMap.close(); Quests.reset(); });
  check(!(await markers()).some(m => m.state === 'tracked'), 'Reset clears the previous hero selection');

  const sv = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  sv.on('pageerror', e => errors.push(e.message));
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url); await sv.locator('#start').click(); await sv.locator('#login-guest').click(); await sv.locator('#name').fill('Kart Uppdrag'); await sv.locator('#go').click({ timeout: 60000 });
  await sv.waitForFunction(() => Online.connected && Field.warriorSprites?.source?.parts?.body, null, { timeout: 60000 });
  await sv.evaluate(() => { WorldMap.show(); }); await sv.locator('.wm-tile[data-zone="0"]').click();
  check(await sv.locator('.wm-quest-legend').textContent().then(t => t.includes('Uppdragsmarkörer') || t.includes('Spårat uppdrag')), 'Swedish legend is translated by hand');
  check(await sv.locator('.wm-quest[data-npc="guide"]').getAttribute('aria-label').then(t => t.includes('Tillgänglig')), 'Swedish giver tooltip is translated');
  await sv.evaluate(() => { WorldMap.close(); Online.send({ type: 'debug', command: { op: 'quest', id: 'welcome', action: 'accept' } }); });
  await sv.waitForFunction(() => document.querySelector('.tracker-quest[data-quest="welcome"]'));
  await sv.locator('.tracker-quest[data-quest="welcome"] .tracker-title').click();
  await sv.evaluate(() => { Quests.close(); WorldMap.show(); }); await sv.locator('.wm-tile[data-zone="0"]').click();
  await sv.waitForFunction(() => document.querySelector('.wm-quest[data-state="tracked"]'));
  check(await sv.locator('.wm-quest[data-state="tracked"]').first().getAttribute('aria-label').then(t => t.startsWith('Spårat uppdrag')), 'Swedish tracked-objective tooltip is translated');
  check(errors.length === 0, 'No browser runtime errors: ' + errors.join('; '));
  fs.writeFileSync(path.join(world.artifacts, 'quest-markers-result.json'), JSON.stringify({ passed: true, checks, errors }, null, 2));
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.artifacts }));
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
