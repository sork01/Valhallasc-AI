// Greenmeadow's own buildings (client/meadowart.js, owner 2026-11-07): the ten hamlet cottages, the Three Meres mill and the roofless
// Hollowend chapel are isometric and stand on their collision footprint, each hamlet builds its own way and no two cottages look alike,
// and the real client draws every one of them with its new art. Pictures in test-results/meadow-houses/.
//   bash scripts/test-touch-bounded.sh tests/meadow-houses-ui.cjs
//   MUTATE=1 ...   serves meadowart.js with the old flat Sunward drawings under the new kinds: must fail
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/meadow-houses');
fs.mkdirSync(out, { recursive: true });
const port = 19500 + (process.pid % 400);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'meadow-houses-'));
let server, browser, checks = 0;
const check = (v, l) => { assert.ok(v, l); checks++; console.log('ok', l); };
const KINDS = ['meadow_cottage', 'meadow_mill', 'chapel_ruin'];
(async () => {
  server = spawn(process.env.VALHALLA_BINARY, [], { cwd: root, stdio: 'ignore',
    env: { ...process.env, VALHALLA_BIND: `127.0.0.1:${port}`, VALHALLA_DB: path.join(tmp, 'v.sqlite'), VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_TEST_COMMANDS: '1', VALHALLA_GOD_MODE: '1', VALHALLA_LEVEL_SPREAD: '0' } });
  for (let i = 0; i < 100; i++) { try { if ((await fetch(`http://127.0.0.1:${port}/health`)).ok) break; } catch (_) {} await new Promise(r => setTimeout(r, 200)); }
  browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' })).newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/meadowart.js', route => route.fulfill({ contentType: 'text/javascript',
    body: fs.readFileSync(path.join(root, 'client/meadowart.js'), 'utf8') + "\nCity.art.meadow_cottage.draw = (g, o) => City.art.vale_cottage.draw(g, o); City.art.meadow_mill.draw = (g, o) => City.art.watermill.draw(g, o);\n" }));
  const version = fs.readFileSync(path.join(root, 'client/index.html'), 'utf8').match(/Beta [0-9.]+/)[0];
  await page.addInitScript(v => { localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} })); localStorage.setItem('valhallasc.whats-new.v1', v); }, version);
  await page.goto(`http://127.0.0.1:${port}/`); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Thatcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });

  // In the game first (the sprite cache is keyed by kind, style and variant, so the field must be the first to draw each one): walk to each place.
  await page.evaluate(k => { window.__drawn = new Set(); for (const kind of k) { const def = City.art[kind], draw = def.draw; def.draw = (g, o, kit) => { window.__drawn.add(`${o.kind}|${o.style || ''}|${o.v}`); return draw(g, o, kit); }; } }, KINDS);
  const debug = c => page.evaluate(x => Online.send({ type: 'debug', command: x }), c);
  await debug({ op: 'set_time', hour: 12, freeze: true }); await debug({ op: 'set_weather', kind: 'clear' });
  for (const [id, x, y] of [['stonefold', 92, 226], ['saltby', 190, 274], ['applewick', 345, 234], ['mill', 343, 158], ['hollowend', 346, 309]]) {
    await debug({ op: 'teleport', zone: 0, x, y });
    await page.waitForFunction(([a, b]) => Field.zone === 0 && Math.hypot(Field.hero.nx - a, Field.hero.ny - b) < 2, [x, y], { timeout: 20000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(out, `${id}.png`) });
  }
  // The data: every Greenmeadow building that was flat now has its own kind, and the cottages carry their hamlet's style.
  const objs = await page.evaluate(k => WORLD_MAP.objects.filter(o => k.includes(o.kind) || ['vale_cottage', 'watermill'].includes(o.kind) || o.label === 'Hollowend Chapel'), KINDS);
  const styles = objs.filter(o => o.kind === 'meadow_cottage').map(o => o.style).sort().join(',');
  check(styles === 'fisher,fisher,fisher,stone,stone,stone,thatch,thatch,thatch,thatch', `ten cottages: three stone, three fisher, four thatch (${styles})`);
  check(!objs.some(o => ['vale_cottage', 'watermill'].includes(o.kind)), 'no flat Sunward cottage or mill is left in Greenmeadow');
  check(objs.some(o => o.kind === 'meadow_mill') && objs.find(o => o.label === 'Hollowend Chapel')?.kind === 'chapel_ruin', 'the mill and the Hollowend ruin have their own kinds');

  // Each sprite on its own: isometric (it reaches the footprint's corners on both sides and below the anchor), and no two cottages alike.
  const sprites = await page.evaluate(k => WORLD_MAP.objects.filter(o => k.includes(o.kind)).map(o => {
    const c = document.createElement('canvas'); c.width = 1000; c.height = 900; const g = c.getContext('2d');
    City.drawObject(g, o, 500, 600);
    const d = g.getImageData(0, 0, c.width, c.height).data; let x0 = 1e9, x1 = -1e9, y1 = -1e9, h = 2166136261, n = 0, r = 0, gg = 0, b = 0;
    for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) { const i = (y * c.width + x) * 4; if (d[i + 3] < 200) continue;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y1 = Math.max(y1, y); n++; r += d[i]; gg += d[i + 1]; b += d[i + 2]; h = Math.imul(h ^ (d[i] * 65536 + d[i + 1] * 256 + d[i + 2]), 16777619) >>> 0; }
    return { kind: o.kind, style: o.style || '', v: o.v, x: o.x, y: o.y, half: (o.width + o.depth) / 2, left: 500 - x0, right: x1 - 500, below: y1 - 600, hash: h, rgb: [r / n, gg / n, b / n].map(Math.round) };
  }), KINDS);
  check(sprites.length === 12, `twelve buildings drawn (${sprites.length})`);
  for (const s of sprites) {
    const reach = s.half * 44 * .9, foot = s.half * 22 * .8;
    check(s.left >= reach && s.right >= reach && s.below >= foot, `${s.kind} ${s.style} v${s.v} at (${s.x},${s.y}) is isometric on its footprint (left ${s.left}, right ${s.right}, below ${s.below}; need ${Math.round(reach)}/${Math.round(foot)})`);
  }
  const cottages = sprites.filter(s => s.kind === 'meadow_cottage');
  check(new Set(cottages.map(s => s.hash)).size === cottages.length, 'no two cottages draw the same picture');
  const mean = st => { const l = cottages.filter(s => s.style === st); return [0, 1, 2].map(i => l.reduce((a, s) => a + s.rgb[i], 0) / l.length); };
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
  const [stone, fisher, thatch] = ['stone', 'fisher', 'thatch'].map(mean);
  check(dist(stone, fisher) > 20 && dist(stone, thatch) > 20 && dist(fisher, thatch) > 20, `each hamlet has its own colours (stone ${stone.map(Math.round)}, fisher ${fisher.map(Math.round)}, thatch ${thatch.map(Math.round)})`);

  const drawn = await page.evaluate(() => [...window.__drawn]);
  for (const s of sprites) check(drawn.includes(`${s.kind}|${s.style}|${s.v}`), `the field drew ${s.kind} ${s.style} v${s.v} with its new art`);
  check(errors.length === 0, `no page errors (${errors.join('; ')})`);
  console.log(`${checks} checks passed`);
})().catch(e => { console.error(e.message); process.exitCode = 1; }).finally(async () => { await browser?.close(); server?.kill(); fs.rmSync(tmp, { recursive: true, force: true }); });
