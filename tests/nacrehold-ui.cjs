// Private Chromium checks of Nacrehold's controls and original canvas art.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'nacrehold-ui', version: '1.0.0' });
let browser, world, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
async function call(name, args = {}) {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, JSON.stringify(r.content));
  return r.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  world = await call('start_world', { startLevel: 40 });
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('NacreUI'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
  const stage = async (x, y, zone = 9) => {
    await page.evaluate(() => { City.close(); Quests.close(); });
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([x, y, zone]) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1, [x, y, zone], { timeout: 12000 });
    let last = null;
    for (let i = 0; i < 50; i++) {
      const now = await page.evaluate(() => Field._debug.w2s(Field.hero.x, Field.hero.y));
      if (last && Math.hypot(now[0] - last[0], now[1] - last[1]) < .4) break;
      last = now; await page.waitForTimeout(80);
    }
    await page.waitForTimeout(250);
  };
  const shot = name => page.screenshot({ path: path.join(world.artifacts, name + '.png') });
  const z = await page.evaluate(() => WORLD_MAP.zones[8]);
  check(z.name === 'Nacrehold' && z.theme === 'nacre' && z.size === 192 && !z.levels, 'A 192-tile underwater city without combat levels');
  check(z.objects.filter(o => o.kind === 'nacrehouse').length === 120 && z.npcs.length === 30 && z.quests.length === 9, '120 houses, 30 people and nine quests');
  check(z.slimes.length === 0 && z.npcs.filter(n => n.route).length === 18, 'A safe city with eighteen swimming residents');
  check(z.npcs.filter(n => n.art !== 'stone').every(n => n.look.species === 'merfolk') && z.npcs.some(n => n.look.female) && z.npcs.some(n => n.look.female === false), 'Both mermaids and mermen, including the travel master');
  check(z.futureInstance.name === 'The Drowned Cathedral' && z.futureInstance.status === 'sealed' && z.futureInstance.players === 5, 'The next five-player instance is named and visibly sealed');
  check(await page.evaluate(() => WORLD_MAP.zones[7].portals.some(p => p.id === 'nacre_gate' && p.to === 9)), 'Ran’s Deep includes the incoming Tideway');
  await stage(96, 164);
  check(await page.locator('#area-title b').textContent() === 'Nacrehold', 'The arrival banner names the city');
  check(await page.locator('#city-travel').isHidden(), 'The city is sanctuary, with no redundant town travel button');
  check(await page.evaluate(() => Field.slimes.length === 0 && City.inside(Field.hero.x, Field.hero.y)), 'The live city snapshot contains no enemies');
  await shot('nacrehold-arrival');
  // Every building must fit its raster, including the Cathedral's high spires.
  const rasters = await page.evaluate(() => {
    const z = WORLD_MAP.zones[8];
    const kinds = [...new Set(z.objects.filter(o => o.kind.startsWith('nacre')).map(o => o.kind))];
    return kinds.map(kind => {
      const o = z.objects.find(o => o.kind === kind), def = City.art[kind];
      if (!def) return { kind, missing: true };
      const [w, h, x, y] = def.box, c = document.createElement('canvas'); c.width = w; c.height = h;
      const g = c.getContext('2d'); g.translate(x, y); def.draw(g, o);
      const d = g.getImageData(0, 0, w, h).data;
      let count = 0, edge = 0;
      for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (d[(j * w + i) * 4 + 3]) { count++; if (i < 2 || j < 2 || i > w - 3 || j > h - 3) edge++; }
      return { kind, count, edge };
    });
  });
  for (const r of rasters) check(!r.missing && r.count > 1000 && r.edge === 0, `${r.kind}: artwork fits the canvas (${r.count} pixels, ${r.edge} edge pixels)`);
  const tails = await page.evaluate(() => {
    return WORLD_MAP.zones[8].npcs.filter(n => n.art !== 'stone').slice(0, 2).map(n => {
      const c = document.createElement('canvas'); c.width = 160; c.height = 180;
      const g = c.getContext('2d'); g.translate(70, 145); NacreArt.merfolk(g, n, 1);
      const d = g.getImageData(85, 117, 36, 35).data;
      return Array.from(d).filter((v, i) => i % 4 === 3 && v > 0).length;
    });
  });
  check(tails.every(n => n > 60), 'The mermaid and merman have visible tails in their own rasters');
  // A real click moves along the clear residential avenue.
  await stage(96, 155);
  const xy = await page.evaluate(() => Field._debug.w2s(96, 151));
  const box = await page.locator('#fieldcv').boundingBox();
  await page.mouse.click(box.x + xy[0] / 1600 * box.width, box.y + xy[1] / 900 * box.height);
  await page.waitForFunction(() => Math.hypot(Field.hero.x - 96, Field.hero.y - 151) < .6, null, { timeout: 12000 });
  check(await page.evaluate(() => Field.hero.zone === 9), 'Real canvas movement works in the city');
  await stage(96, 106); await shot('nacrehold-pearl-plaza');
  const frame = await page.evaluate(() => { const c = document.getElementById('fieldcv'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let r = 0, g = 0, b = 0, n = 0; for (let i = 0; i < d.length; i += 40) { r += d[i]; g += d[i + 1]; b += d[i + 2]; n++; } return { r: r / n, g: g / n, b: b / n }; });
  check(frame.g > frame.r + 12 && frame.b > frame.r + 15, 'The city has underwater blue-green lighting');
  await page.evaluate(() => document.querySelector('.tracker-toggle')?.click());
  await stage(90, 25); await shot('nacrehold-cathedral-and-stone');
  check(await page.evaluate(() => City.art.meetingstone && City.art.nacrecathedral), 'The Cathedral and Meeting Stone are both rendered');
  await stage(96, 32);
  await page.evaluate(() => Field.visitNpc('nacre_warden'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  check((await page.locator('#npc-text').textContent()).includes('next level-40 five-player instance'), 'The warden explains the future Cathedral expedition');
  check((await page.locator('#npc-text').textContent()).includes('future expedition'), 'The sealed entrance cannot pretend the instance is playable');
  await stage(90.7, 33.7);
  await debug({ op: 'set_gold', gold: 1000 });
  await page.evaluate(() => Field.visitNpc('nacre_stone'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  check(await page.locator('[data-offer="merc_priest"]').isEnabled(), 'The Meeting Stone offers the existing priest hire');
  check(await page.locator('[data-offer^="merc_"]').count() === 6, 'All five classes and dismissal are offered');
  await stage(100, 164);
  await page.evaluate(() => Field.visitNpc('travel_nacrehold'));
  await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  check((await page.locator('#npc-name').textContent()) === 'Travel Master Auralis', 'The mermaid travel master opens her dialogue');
  check(await page.locator('[data-travel="travel_keelhaven"]').count() === 1, 'Spark Travel lists Keelhaven');
  await stage(92, 166);
  await page.evaluate(() => Field.visitNpc('nacre_envoy'));
  await page.locator('[data-quest="nacre_welcome"]').click();
  await page.locator('[data-action="accept"]').click();
  await page.waitForFunction(() => Field.hero.quests.some(q => q.id === 'nacre_welcome'));
  check((await page.locator('#quest-tracker').textContent()).includes('A City Beneath the Waves'), 'Accepting the envoy’s quest updates the tracker');
  await page.evaluate(() => City.close()); await page.keyboard.press('q');
  check((await page.locator('#quest-journal').textContent()).includes('A City Beneath the Waves'), 'The journal lists the accepted city quest');
  await page.evaluate(() => Quests.close());
  await debug({ op: 'explore_all' });
  await page.waitForFunction(() => Field.explored?.length === 10 && Field.explored.every(x => x === 511));
  await page.keyboard.press('m');
  check((await page.locator('#worldmap').textContent()).includes('Nacrehold'), 'The world map includes the underwater city');
  await shot('nacrehold-world-map');
  check(await page.locator('.wm-tile[data-zone="9"]').isEnabled(), 'The discovered city tile opens on the world sheet');
  await page.locator('.wm-tile[data-zone="9"]').click();
  await page.waitForFunction(() => document.getElementById('wm-body').dataset.view === 'zone');
  check(await page.locator('.wm-gate[data-portal="nacre_deep_gate"]').count() === 1, 'The detailed city map shows the return Tideway');
  check(await page.evaluate(() => document.querySelector('.wm-tile[data-zone="9"]').getAttribute('aria-label').includes('safe city')), 'The city map advertises sanctuary rather than combat levels');
  check(errors.length === 0, `No browser errors: ${errors.join(' | ')}`);
  console.log(`nacrehold-ui: ${checks} checks passed; ${world.artifacts}`);
})().then(async () => { await browser?.close(); if (world) await call('stop_world'); await client.close(); }, async e => {
  console.error(e); await browser?.close().catch(() => {}); if (world) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); process.exitCode = 1;
});
