const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { playGuest } = require('./lib/guest.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

requireMemoryLimit();
const world = new TestWorld();
let browser;

(async () => {
  await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 900, height: 620 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
  });
  await page.goto(world.url);
  await page.locator('#start').click();
  await playGuest(page);
  await page.locator('#cls-warrior').click();
  await page.locator('#name').fill('Auden');
  await page.locator('#go').click();
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0);
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();

  const dungeon = await page.evaluate(() => {
    const area = WORLD_MAP.zones[4];
    return { spawn: area.spawn, hasGuide: area.npcs.some(npc => npc.art === 'spirit_guide') };
  });
  assert.equal(dungeon.hasGuide, false, 'Undervault has no Spirit Guide');
  const sendDebug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await sendDebug({ op: 'teleport', zone: 5, x: dungeon.spawn.x + 5, y: dungeon.spawn.y });
  await page.waitForFunction(() => Field.zone === 5 && Field.inInstance);
  await sendDebug({ op: 'die' });
  await page.waitForFunction(() => Field.hero.dead && !document.getElementById('dead-msg').hidden);
  assert.equal(await page.locator('#dead-sub').textContent(), 'You wake up back at the start…');
  const first = await page.evaluate(() => ({ ghost: !!Field.hero.ghost, corpses: Field.corpses.length }));
  assert.deepEqual(first, { ghost: false, corpses: 0 }, 'Dungeon death has no ghost or visible corpse');
  await page.waitForFunction(spawn => {
    const hero = Field.hero;
    return !hero.dead && !hero.ghost && hero.hp === hero.maxHp && Math.hypot(hero.x - spawn.x, hero.y - spawn.y) < 3;
  }, dungeon.spawn);
  assert.ok(await page.locator('#ghost-msg').isHidden(), 'The Spirit Form banner stays hidden');
  assert.deepEqual(errors, []);
  console.log('instance-respawn-ui: dungeon death shows the entrance message and revives alive at the spawn');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(async () => {
  await browser?.close().catch(() => {});
  await world.stop().catch(() => {});
});
