// Bounded private playback of the newly installed title, Moonwell, night, dungeon and raid scores.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { requireMemoryLimit } = require('./lib/touch.cjs'); requireMemoryLimit();
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const seconds = require('./lib/soundtrack.cjs');
const world = new TestWorld();
let browser, checks = 0;
const results = [], errors = [];
const check = (value, label) => { assert.ok(value, label); checks++; console.log(label); };
(async () => {
  try {
    await world.start(); browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
    const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
    page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => {
      window.__musicReleaseS = 1;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: .6, masterVol: .8, sfxVol: 0, weatherAudio: 0 }));
    });
    await page.goto(world.url); await page.locator('#start').click();
    await page.waitForFunction(() => valhalla.music?.loaded, null, { timeout: 30000 });
    check(Math.abs(await page.evaluate(() => valhalla.music.duration) - seconds('title')) < .05, 'Remade title recording decodes');
    await page.locator('#login-guest').click(); await page.locator('#name').fill('ScoreListener'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    const time = async hour => {
      await debug({ op: 'set_time', hour, freeze: true });
      await page.waitForFunction(h => Math.abs(DayNight.hour - h) < .01, hour);
    };
    const at = async (zone, key, slot) => {
      const spawn = await page.evaluate(z => WORLD_MAP.zones[z - 1].spawn, zone);
      await debug({ op: 'teleport', zone, x: spawn.x, y: spawn.y });
      await page.waitForFunction(({ zone, key }) => Field.zone === zone && valhalla[key]?.running && valhalla[key]?.loaded, { zone, key }, { timeout: 30000 });
      const duration = await page.evaluate(key => valhalla[key].duration, key);
      check(Math.abs(duration - seconds(slot)) < .05, `${slot}: correct replacement recording plays in zone ${zone}`);
      results.push({ zone, slot, duration });
    };
    await time(12); await at(18, 'moonwellMusic', 'moonwell');
    check(await page.evaluate(() => !valhalla.mmusic.running && !valhalla.nightMusic.running && DayNight.nightMix === 0), 'Moonwell uses its own score and keeps indoor lighting');
    await page.waitForFunction(() => Math.abs(valhalla.moonwellMusic.output.gain.value - .36) < .01);
    check(true, 'Moonwell honors saved music volume');
    await page.evaluate(() => Prefs.set({ sound: false }));
    await page.waitForFunction(() => valhalla.moonwellMusic.output.gain.value < .001);
    check(true, 'Mute silences the new Moonwell player');
    await page.evaluate(() => Prefs.set({ sound: true, musicVol: .5, masterVol: .7 }));
    await page.waitForFunction(() => Math.abs(valhalla.moonwellMusic.output.gain.value - .25) < .01);
    check(await page.evaluate(() => Prefs.master === .7 && JSON.parse(localStorage.getItem('valhallasc.save.v1')).masterVol === .7), 'Volume and saved master preference apply independently');
    await at(19, 'stormglassMusic', 'stormglass');
    await time(19);
    await page.waitForFunction(() => valhalla.stormglassNightMusic?.loaded && valhalla.stormglassNightMusic.running && !valhalla.stormglassMusic.running, null, { timeout: 30000 });
    check(Math.abs(await page.evaluate(() => valhalla.stormglassNightMusic.duration) - seconds('stormglass_night')) < .05, 'Remade night score takes over through the shared sequential fade');
    await time(8);
    await page.waitForFunction(() => valhalla.stormglassMusic.running && !valhalla.stormglassNightMusic.running);
    check(true, 'Dawn restores the remade daytime score');
    await at(42, 'skybridgeMusic', 'skybridge');
    await at(46, 'raidMusic', 'chained_forge');
    check(await page.evaluate(() => !valhalla.eldmarrMusic.running), 'Ordinary raid music leaves the final encounter score idle');
    check(errors.length === 0, `No browser errors: ${errors.join('; ')}`);
    fs.writeFileSync(path.join(world.runDir, 'soundtrack-playback.json'), JSON.stringify({ checks, results, errors }, null, 2) + '\n');
    console.log(`PASS soundtrack-filedrop-ui: ${checks} checks; ${world.runDir}`);
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
