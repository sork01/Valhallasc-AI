// Owner follow-up: default/persisted sound modes and authoritative mounted rear-hit daze.
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const world = new TestWorld(); world.startLevel = 99; world.godMode = false; world.levelSpread = 0;
let browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
(async () => {
  const info = await world.start();
  browser = await chromium.launch({ headless: true });
  for (const [stored, expected] of [
    [null, 'synthesized'], [{ sound: false }, 'synthesized'],
    [{ combatSounds: 'invalid' }, 'synthesized'],
    [{ combatSounds: 'recorded' }, 'recorded'], [{ combatSounds: 'synthesized' }, 'synthesized'],
  ]) {
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    await page.addInitScript(stored => {
      if (stored && !localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify(stored));
    }, stored);
    await page.goto(info.url);
    await page.waitForFunction(() => window.Prefs);
    check(await page.evaluate(() => Prefs.combatSounds) === expected, `mode ${JSON.stringify(stored)} gives ${expected}`);
    await page.evaluate(() => Prefs.set({ sound: false }));
    await page.reload(); await page.waitForFunction(() => window.Prefs);
    check(await page.evaluate(() => Prefs.combatSounds) === expected, 'mode survives saving and reload');
    await page.close();
  }
  await browser.close(); browser = null;
  await world.connect({ bot: 'MountedDaze', class: 'warrior' });
  await world.debug('MountedDaze', { op: 'teleport', zone: 0, x: 80, y: 80 });
  await world.action('MountedDaze', { type: 'input', dx: 1, dy: 0 });
  await world.waitFor(() => world.player('MountedDaze').fx > .99, 3000, 'east-facing fixture');
  await world.action('MountedDaze', { type: 'stop' });
  await world.debug('MountedDaze', { op: 'give_mount', mount: 'horse' });
  await world.action('MountedDaze', { type: 'mount', mounted: true });
  await world.waitFor(() => world.player('MountedDaze').mounted, 3000, 'mounted fixture');
  check(true, 'victim is mounted before the enemy attack');
  const { x, y } = world.player('MountedDaze');
  await world.debug('MountedDaze', { op: 'spawn_enemy', kind: 'green', x: x - 1.5, y, level: 1 });
  await world.waitFor(() => world.player('MountedDaze').daze > 0, 30000, 'real rear-hit daze');
  check(world.player('MountedDaze').mounted === false, 'real rear-hit daze dismounts the rider');
  await world.action('MountedDaze', { type: 'mount', mounted: true });
  await world.waitFor(() => world.events.some(e => e.type === 'error' && e.text.includes('out of combat')), 3000, 'remount refusal');
  check(world.player('MountedDaze').mounted === false, 'dazed rider cannot remount during combat');
  console.log(`daze-sound-defaults: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close(); await world.stop();
});
