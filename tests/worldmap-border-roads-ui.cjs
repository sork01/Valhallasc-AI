// Focused Chromium check for WORLDMAP-REMOVE-BORDER-ROADS (Beta 1.51.2):
// verifies no .wm-roads / .wm-connection-path / .wm-route-road inter-zone connectors
// render on the world map, the footer legend drops "Gold: walking paths" (EN & SV),
// while zone tiles, Route text, Spark stations, and zone-detail view keep working.
// Run via: bash scripts/test-touch-bounded.sh tests/worldmap-border-roads-ui.cjs
// MUTATE=1 injects a synthetic .wm-roads overlay and must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname, '..');

function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Use scripts/test-touch-bounded.sh (1536M cap).');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  while (dir.startsWith('/sys/fs/cgroup')) {
    try {
      const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim();
      if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) return;
    } catch (_) {}
    if (dir === '/sys/fs/cgroup') break;
    dir = path.dirname(dir);
  }
  throw Error('Refusing uncapped browser run; use scripts/test-touch-bounded.sh.');
}

async function openHero(context, world, { lang = 'en', name = 'RoadCheck' } = {}) {
  const page = await context.newPage();
  await page.addInitScript(l => {
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) {
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({
        lang: l, sound: false, uiSet: true, panelSizeSet: true, panelSize: {}, char: null, draft: null,
      }));
    }
  }, lang);
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => {
    const tip = document.getElementById('tutorial-tip');
    if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click();
  });
  return page;
}

(async () => {
  requireMemoryLimit();
  const mutate = process.env.MUTATE === '1';
  let world, browser;
  const errors = [];
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };

  try {
    world = new TestWorld(root, { artifactsDir: path.join(root, 'test-results', 'worldmap-border-roads') });
    await world.start();
    browser = await chromium.launch({ headless: true });

    // 1. Desktop (1440x900, English)
    const deskCtx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await openHero(deskCtx, world, { lang: 'en', name: 'WMDesk' });
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error' && !/401|Failed to load resource/.test(m.text())) errors.push(m.text()); });

    await page.keyboard.press('m');
    await page.waitForFunction(() => WorldMap.open && WorldMap.view === 'world');
    if (mutate) {
      await page.evaluate(() => {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'wm-roads');
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'wm-connection-path');
        svg.appendChild(g);
        document.getElementById('wm-world').appendChild(svg);
      });
    }

    const desk = await page.evaluate(() => ({
      version: document.querySelector('.version')?.textContent?.trim(),
      roads: document.querySelectorAll('#worldmap .wm-roads').length,
      connPaths: document.querySelectorAll('#worldmap .wm-connection-path').length,
      roadStrokes: document.querySelectorAll('#worldmap .wm-road, #worldmap .wm-road-under').length,
      routeRoads: document.querySelectorAll('#worldmap .wm-route-road').length,
      tiles: document.querySelectorAll('#worldmap .wm-tile').length,
      sparks: document.querySelectorAll('#worldmap .wm-spark-dot, #worldmap .wm-travel-badge').length,
      keyText: document.querySelector('#worldmap .wm-connection-key')?.textContent?.trim() || '',
      routeText: document.getElementById('wm-route')?.textContent?.trim() || '',
    }));
    check(desk.version === 'Beta 1.51.2', `Version label updated (${desk.version})`);
    check(desk.roads === 0 && desk.connPaths === 0 && desk.roadStrokes === 0 && desk.routeRoads === 0,
      `No inter-zone border road SVG elements render (roads=${desk.roads}, paths=${desk.connPaths}, strokes=${desk.roadStrokes}, route=${desk.routeRoads})`);
    check(desk.tiles >= 20, `World tiles intact (${desk.tiles})`);
    check(!/gold|walking paths/i.test(desk.keyText) && /Purple:\s*entrance maps/i.test(desk.keyText),
      `Legend omits Gold walking paths and keeps entrance maps: "${desk.keyText}"`);

    // Visit Emberfall Crags (zone 1) so two zones are charted and Route text between them can be checked
    await page.keyboard.press('Escape');
    await page.evaluate(() => {
      const sp = Field._debug.zones[1].spawn;
      Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: sp.x, y: sp.y } });
    });
    await page.waitForFunction(() => Field.zone === 1, null, { timeout: 10000 });
    await page.keyboard.press('m');
    await page.waitForFunction(() => WorldMap.open && WorldMap.view === 'world');
    const cragsTile = await page.evaluate(() => document.querySelectorAll('#worldmap .wm-roads, #worldmap .wm-connection-path, #worldmap .wm-route-road').length);
    check(cragsTile === 0, 'World view renders 0 inter-zone border road SVGs after visiting multiple zones');

    // Clicking visited Greenmeadow opens zone-detail with Route text and returns cleanly with 0 road lines
    await page.locator('.wm-name[data-zone="0"]').click();
    await page.waitForFunction(() => WorldMap.view === 'zone');
    const meadow = await page.evaluate(() => ({
      route: document.querySelector('#wm-side .wm-route-text')?.textContent?.trim() || '',
      hasCanvas: (() => { const c = document.querySelector('#wm-body canvas'); return !!c && c.width > 0 && c.height > 0; })(),
      backVisible: !document.getElementById('wm-back').hidden,
    }));
    check(meadow.route.includes('Route:') && meadow.route.includes('Emberfall Crags') && meadow.route.includes('Greenmeadow') && meadow.hasCanvas && meadow.backVisible,
      `Greenmeadow detail view shows Route text (${meadow.route}) and canvas`);
    await page.locator('#wm-back').click();
    await page.waitForFunction(() => WorldMap.view === 'world');
    const afterBack = await page.evaluate(() => document.querySelectorAll('#worldmap .wm-roads, #worldmap .wm-connection-path, #worldmap .wm-route-road').length);
    check(afterBack === 0, 'Returning to world view renders 0 inter-zone border road SVGs');

    // Zone-detail for current zone (Emberfall Crags) also works
    await page.locator('.wm-name[data-zone="1"]').click();
    await page.waitForFunction(() => WorldMap.view === 'zone');
    const crags = await page.evaluate(() => ({
      route: document.querySelector('#wm-side .wm-route-text')?.textContent?.trim() || '',
      hasCanvas: (() => { const c = document.querySelector('#wm-body canvas'); return !!c && c.width > 0 && c.height > 0; })(),
    }));
    check(crags.route === 'You are here' && crags.hasCanvas, `Emberfall Crags detail view shows "${crags.route}" and canvas`);
    await page.locator('#wm-back').click();
    await page.waitForFunction(() => WorldMap.view === 'world');
    await deskCtx.close();

    // 2. Touch phone (844x390, Swedish)
    const mobCtx = await browser.newContext({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const mobPage = await openHero(mobCtx, world, { lang: 'sv', name: 'WMTouch' });
    mobPage.on('pageerror', e => errors.push(e.message));
    await mobPage.evaluate(() => WorldMap.show());
    await mobPage.waitForFunction(() => WorldMap.open && WorldMap.view === 'world');
    const mob = await mobPage.evaluate(() => {
      const panel = document.querySelector('.wm-panel').getBoundingClientRect();
      const key = document.querySelector('.wm-connection-key');
      const kr = key.getBoundingClientRect();
      return {
        roads: document.querySelectorAll('#worldmap .wm-roads, #worldmap .wm-connection-path, #worldmap .wm-route-road').length,
        keyText: key.textContent.trim(),
        keyInsidePanel: kr.bottom <= panel.bottom + 1 && kr.right <= panel.right + 1,
      };
    });
    check(mob.roads === 0, 'Mobile world map also renders zero border road SVGs');
    check(!/guld|gångvägar/i.test(mob.keyText) && /Lila:\s*kartor över ingångar/i.test(mob.keyText),
      `Swedish legend updated: "${mob.keyText}"`);
    check(mob.keyInsidePanel, 'Connection key fits inside world map panel on 844x390');
    await mobCtx.close();

    check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
    console.log(`worldmap-border-roads-ui: ${checks} focused checks passed`);
  } finally {
    await browser?.close();
    await world?.stop();
  }
})().catch(err => {
  console.error(err);
  process.exitCode = 1;
});
