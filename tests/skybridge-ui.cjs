// One new dungeon only: real client travel, readable art, sign, music and controls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'skybridge-private-ui', version: '1' });
let browser, started = false;
const call = async (name, args = {}) => {
  const r = await client.callTool({ name, arguments: args });
  assert.ok(!r.isError, JSON.stringify(r.content));
  return r.structuredContent;
};

(async () => {
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')],
    cwd: root,
    stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server') }
  }));
  const world = await call('start_world', { godMode: true, levelSpread: 0 });
  started = true;
  browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [], bad = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => {
    if (r.status() >= 400 && /skybridge|span_|cathedral\.txt/.test(r.url())) bad.push([r.url(), r.status()]);
  });

  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, musicVol: .45, sfxVol: 0 })));
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill('Span Explorer');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && window.SkybridgeArt && Field.hero, { timeout: 60000 });

  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  const teleport = async (zone, x, y) => {
    await debug({ op: 'teleport', zone, x, y });
    await page.waitForFunction(([z, x, y]) => Field.zone === z && Math.hypot(Field.hero.x - x, Field.hero.y - y) < 1.5, [zone, x, y], { timeout: 15000 });
  };
  const shot = async name => {
    await page.waitForTimeout(650);
    await page.locator('#fieldcv').screenshot({ path: path.join(world.artifacts, `skybridge-${name}-${STUB ? 'stub' : 'real'}.png`) });
  };

  await debug({ op: 'set_level', level: 30 });
  await debug({ op: 'explore_all' });

  // Bifrost Reach gate
  await teleport(7, 58, 133);
  await shot('entrance');
  await page.evaluate(() => Online.send({ type: 'move', x: 58, y: 128 }));
  await page.waitForFunction(() => Field.zone === 42, null, { timeout: 15000 });
  await page.evaluate(() => Online.send({ type: 'stop' }));

  // Background music
  await page.waitForFunction(() => valhalla.skybridgeMusic?.running && valhalla.skybridgeMusic.loaded, null, { timeout: 30000 });
  assert.ok(await page.evaluate(() => Math.abs(valhalla.skybridgeMusic.duration - 24 * 3 * 60 / 96) < .05), 'The new 3/4 music decodes at the correct loop length (45s)');
  assert.ok(await page.evaluate(() => DayNight.nightMix < .01), 'Dungeon keeps indoor light and its own score');
  assert.ok(await page.evaluate(() => WORLD_MAP.zones[41].name === 'The Shattered Span' && WORLD_MAP.zones[6].portals.some(p => p.to === 42)), 'Correct Bifrost Reach entrance and stable zone ID');

  if (!STUB) {
    assert.equal(await page.evaluate(async () => {
      const meta = await (await fetch('assets/cathedral.txt')).json();
      let n = 0;
      for (const kind of meta.kinds.filter(k => k.startsWith('span_'))) {
        const i = new Image();
        i.src = `assets/cathedral_${kind}.png`;
        await i.decode();
        if (i.width === 768 && i.height === 480 && meta.sprites[kind] && meta.tops[kind]) n++;
      }
      return n;
    }), 6, 'All six editable enemy atlases decode');
  }

  for (const [name, x, y] of [['threshold', 56, 99], ['west-gallery', 23, 53], ['east-gallery', 89, 53], ['archon-arch', 56, 18]]) {
    await teleport(42, x, y);
    await shot(name);
  }

  // Boss sign
  await teleport(42, 47.5, 42.5);
  await page.evaluate(() => Online.send({ type: 'sign_read', sign: 'span_archon' }));
  await page.locator('#sign-panel').waitFor({ state: 'visible' });
  assert.match(await page.locator('#sign-panel').innerText(), /behind Vaelor|wide red cone/i);
  await page.screenshot({ path: path.join(world.artifacts, `skybridge-sign-${STUB ? 'stub' : 'real'}.png`) });
  await page.keyboard.press('Escape');

  // Music volume preference
  await page.evaluate(() => Prefs.set({ musicVol: .3, sound: true }));
  await page.waitForTimeout(700);
  assert.ok(await page.evaluate(() => Math.abs(valhalla.skybridgeMusic.output.gain.value - .09) < .005), 'Saved music volume reaches this score');

  console.log('skybridge-ui passed cleanly');
})().catch(err => {
  console.error('skybridge-ui failed:', err);
  process.exitCode = 1;
}).finally(async () => {
  if (browser) await browser.close();
  if (started) await call('stop_world');
  await client.close();
});
