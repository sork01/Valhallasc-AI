const assert = require('node:assert/strict');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const world = new TestWorld();
let browser, checks = 0;
const check = (ok, text) => { assert.ok(ok, text); checks++; console.log(text); };
(async () => {
  world.startLevel = 99; world.godMode = true; world.levelSpread = 0;
  await world.start();
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-hunter').click(); await page.locator('#name').fill('DoorTester');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99);
  const send = packet => page.evaluate(packet => Online.send(packet), packet);
  const teleport = async (zone, x, y) => {
    await page.evaluate(() => City.close());
    await send({ type: 'debug', command: { op: 'teleport', zone, x, y } });
    await page.waitForFunction(({ zone, x, y }) => Field.zone === zone && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1, { zone, x, y });
  };
  const speak = async (zone, npc) => {
    const at = await page.evaluate(({ zone, npc }) => [WORLD_MAP, ...WORLD_MAP.zones][zone].npcs.find(n => n.id === npc), { zone, npc });
    await teleport(zone, at.x + 1, at.y);
    await page.waitForTimeout(550); // Normal NPC transaction spacing.
    await send({ type: 'interact', npc });
    await page.locator('#npc-dialogue').waitFor({ state: 'visible' });
  };
  const gates = [
    [6, 'barrow_guide', 'entry_norn', 'Three Names for the Dead'],
    [17, 'asterion_bellkeeper', 'entry_moon', 'A Bell for Your Reflection'],
    [25, 'lapis_seer', 'entry_astro', 'The Sky Beneath the Sand'],
    [28, 'yr_wi_lead', 'entry_solstice', 'Smuggle a Little Sunrise'],
  ];
  for (const [zone, npc, id, title] of gates) {
    await speak(zone, npc);
    await page.locator(`#npc-quests button[data-quest="${id}"]`).click();
    check(await page.locator('#npc-quests h4').textContent() === title, `${title}: offered at the exterior giver`);
    check((await page.locator('#npc-quests').textContent()).includes('permanently for you'), `${title}: explains the permanent unlock`);
    await page.locator('#npc-quests button[data-action="accept"]').click();
    await page.waitForFunction(id => Field.hero.quests.some(q => q.id === id && !q.claimed), id);
    check(true, `${title}: accepted through the quest window`);
  }
  // The new bell props and progress rings share the existing chime renderer.
  await teleport(17, 93.1, 68);
  await page.waitForFunction(() => Field.hero.quests.find(q => q.id === 'entry_moon').counts[0] === 1);
  check(await page.evaluate(() => Quests.chime('admit_waking').state === 'ringing'), 'Reflection bell publishes its live countdown to the renderer');
  await page.screenshot({ path: path.join(world.runDir, 'reflection-bell.png') });
  for (const [x, y] of [[101.1, 88], [117.1, 88]]) await teleport(17, x, y);
  await page.waitForFunction(() => Field.hero.quests.find(q => q.id === 'entry_moon').counts[0] === 3);
  await speak(17, 'asterion_bellkeeper');
  await page.locator('#npc-quests button[data-quest="entry_moon"]').click();
  await page.locator('#npc-quests button[data-action="claim"]').click();
  await page.waitForFunction(() => Field.hero.quests.find(q => q.id === 'entry_moon').completions === 1);
  check(true, 'The bell quest turns in through Complete Quest');
  for (const [x, y] of [[97.1, 58], [97.1, 65], [89.1, 71]]) await teleport(6, x, y);
  await speak(6, 'barrow_scribe');
  check((await page.locator('#npc-text').textContent()).includes('Alva'), 'Egil actually tells the forgotten names');
  await page.waitForFunction(() => Field.hero.quests.find(q => q.id === 'entry_norn').counts.every(n => n === 1));
  await speak(6, 'barrow_guide');
  await page.locator('#npc-quests button[data-quest="entry_norn"]').click();
  check((await page.locator('#npc-quests .quest-state').textContent()) === 'Ready to turn in', 'Funeral stones and the scribe complete all four objectives');
  await page.locator('#npc-quests button[data-action="claim"]').click();
  await page.waitForFunction(() => Field.hero.quests.find(q => q.id === 'entry_norn').completions === 1);
  check(true, 'The funeral quest turns in through Complete Quest');
  check(errors.length === 0, `No browser errors: ${errors.join(', ')}`);
  console.log(`${checks} admission browser checks passed: ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); await world.stop();
});
