// Greenmeadow's landing dock (pilot, owner 2026-11-07): a new hero starts on the pier beside the moored ship, the pier and ship are
// drawn, the landing quest is not in the journal while the hero stands on the pier, and it arrives (one announcement) the moment
// they walk off the pier onto the beach. Pictures in test-results/meadow-dock/.
//   bash scripts/test-touch-bounded.sh tests/meadow-dock-ui.cjs
//   MUTATE=1 ...   serves meadowdock.js with a draw that does nothing: must fail
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/meadow-dock');
fs.mkdirSync(out, { recursive: true });
const port = 19900 + (process.pid % 90);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'meadow-dock-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
// pixels of the sail's red stripe (#b8382f) in a screenshot, within the given box
async function sailRed(page, box) {
  const png = await page.screenshot({ clip: box });
  return page.evaluate(async b64 => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0;
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 184) < 14 && Math.abs(d[i + 1] - 56) < 14 && Math.abs(d[i + 2] - 47) < 14) n++;
    return n;
  }, png.toString('base64'));
}
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/meadowdock.js', route => route.fulfill({ contentType: 'text/javascript', body: 'window.MeadowDock = { draw() {} };' }));
  const version = fs.readFileSync(path.join(root, 'client/index.html'), 'utf8').match(/Beta [0-9.]+/)[0];
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, version);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Sailor'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  await page.waitForTimeout(1500);

  const dock = await page.evaluate(() => WORLD_MAP.dock);
  const hero = await page.evaluate(() => ({ zone: Field.zone, x: Field.hero.nx, y: Field.hero.ny }));
  check(hero.zone === 0 && Math.hypot(hero.x - dock.start.x, hero.y - dock.start.y) < 1, `a new hero starts on the dock (${hero.x.toFixed(1)}, ${hero.y.toFixed(1)})`);
  await page.screenshot({ path: path.join(out, 'start.png') });
  const red = await sailRed(page, { x: 240, y: 0, width: 800, height: 520 });
  check(red > 400, `the ship's striped sail is drawn beside the hero (${red} red pixels)`);
  check(await page.evaluate(() => !Quests.active('meadow_landing')), 'no landing quest while on the pier');
  check(await page.evaluate(() => ![...document.querySelectorAll('[data-quest="meadow_landing"]')].length), 'the journal does not list it yet');

  // Walk north (world -y = Up+Right) off the pier onto the beach.
  await page.keyboard.down('ArrowUp'); await page.keyboard.down('ArrowRight');
  await page.waitForFunction(y0 => Field.hero.ny < y0 - 2, dock.y0, { timeout: 15000 }).catch(async e => { console.log('hero at', await page.evaluate(() => [Field.hero.nx, Field.hero.ny, document.activeElement?.id])); throw e; });
  await page.keyboard.up('ArrowUp'); await page.keyboard.up('ArrowRight');
  await page.waitForFunction(() => Quests.active('meadow_landing'), null, { timeout: 5000 });
  check(true, 'stepping off the dock gives the landing quest');
  const said = await page.evaluate(() => [...document.querySelectorAll('#announce .announce-line')].map(l => l.textContent));
  check(said.length === 1 && said[0].includes('Ashore at Saltby'), `one announcement names it (${JSON.stringify(said)})`);
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(out, 'ashore.png') });
  check(errors.length === 0, `no page errors (${errors.join('; ')})`);
  console.log(`${checks} checks passed`);
})().catch(e => { console.error(e.message); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
