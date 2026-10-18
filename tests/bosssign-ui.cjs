// The boss sign on the screen (BOSSMECH-SIGN-ENGINE), in a real browser against a real private server. The world loads a
// one-boss table of its own (VALHALLA_BOSSMECH_FILE, honoured only with test commands) that gives the Undervault's king a
// harmless break bar, so the test does not depend on the shipped numbers; a dungeon whose boss has no mechanic shows no sign.
// This checks what the
// player sees: the sign is drawn where the server says, F or a click reads it (walking up first), the window shows the
// server's words and the picture strip, Esc, the cross, the Close button and walking away close it, a reload reads it again,
// it fits a phone-sized screen, no other zone has one, and the new texts exist in Swedish.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debug = path.join(root, 'target/debug/valhalla-server');
// The newer of the two builds: the release binary is the live service's and is only rebuilt at a deploy, so it is often the stale one.
const newest = [release, debug].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bosssign-'));
const table = path.join(dir, 'boss-mechanics.txt');
fs.writeFileSync(table, JSON.stringify({
  hollowking: { mechanics: [{ name: 'Test Dirge', block: 'break', cast: 8, every: 30, first: 1, bar: 0.05, stun: 6, vulnerable: 0.3 }] },
}));
const signs = JSON.parse(fs.readFileSync(path.join(root, 'world/boss-signs.txt'), 'utf8'));
const sign = signs.hollowking;
const UNDERVAULT = 5;
const client = new Client({ name: 'valhallasc-bosssign-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', VALHALLA_BOSSMECH_FILE: table, ...(binary ? { VALHALLA_BINARY: binary } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
  const enter = async () => {
    await page.goto(world.url);
    await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill('Reader'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  };
  await enter();
  const debugOp = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(400));
  const hero = () => page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  const panel = () => page.locator('#sign-panel');
  const visible = () => page.evaluate(() => !document.getElementById('sign-panel').hidden);
  // Teleports to the first of the offsets from the sign that is open ground (the server moves a hero off a wall), and says how far that is.
  const goNear = async (...offsets) => {
    for (const [dx, dy] of offsets) {
      await debugOp({ op: 'teleport', zone: UNDERVAULT, x: sign.x + dx, y: sign.y + dy });
      await page.waitForFunction(() => Field.signs.length === 1, null, { timeout: 15000 });
      const h = await hero();
      if (Math.hypot(h.x - (sign.x + dx), h.y - (sign.y + dy)) < 0.6) return Math.hypot(dx, dy);
    }
    throw new Error('no open ground near the sign');
  };
  await debugOp({ op: 'set_god_mode', enabled: true });

  // ---- 1. a dungeon whose boss has a mechanic shows its sign; no other zone does -------------------------------------------------
  check(await page.evaluate(() => Field.signs.length) === 0, 'the starting meadow has no sign');
  await goNear([0, 1.2], [1.2, 0], [-1.2, 0]);
  const listed = await page.evaluate(() => Field.signs.map(s => ({ id: s.id, x: s.x, y: s.y, title: s.title, keys: Object.keys(s).sort().join() })));
  check(listed.length === 1 && listed[0].id === 'hollowking' && listed[0].x === sign.x && listed[0].y === sign.y, `the server says where the sign stands (${JSON.stringify(listed)})`);
  check(!/what|todo|tip/.test(listed[0].keys), 'the snapshot carries no words');
  check(!(await visible()), 'the window is closed until the sign is read');
  const board = () => page.evaluate(() => {
    const s = Field.signs[0], [sx, sy] = Field._debug.w2s(s.x, s.y), cv = document.getElementById('fieldcv'), k = cv.width / 1600, g = cv.getContext('2d');
    const d = g.getImageData(Math.round((sx - 26) * k), Math.round((sy - 66) * k), Math.round(52 * k), Math.round(34 * k)).data;
    let gold = 0, wood = 0; for (let i = 0; i < d.length; i += 4) { if (d[i] > 200 && d[i + 1] > 160 && d[i] - d[i + 2] > 90) gold++; if (d[i] > 130 && d[i] < 190 && d[i + 1] > 80 && d[i + 1] < 130 && d[i + 2] < 80) wood++; }
    return { gold, wood };
  });
  await page.waitForTimeout(300);
  const drawn = await board();
  check(drawn.wood > 200 && drawn.gold > 15, `the board and its gold "!" are drawn (${JSON.stringify(drawn)})`);
  await page.screenshot({ path: path.join(world.artifacts, 'bosssign-board.png') });

  // ---- 2. F reads it: the window shows the server's words in the three parts, with the colour strip ------------------------------
  await page.keyboard.press('f');
  await page.waitForFunction(() => !document.getElementById('sign-panel').hidden, null, { timeout: 8000 });
  const text = id => page.locator(id).innerText();
  check(await text('#sign-title') === sign.title, 'the title is the boss');
  check(await text('#sign-what') === sign.what && await text('#sign-todo') === sign.todo && await text('#sign-tip') === sign.tip, 'the three parts are the sign\'s words');
  check((await page.locator('.sign-part h4').allInnerTexts()).join('|') === 'What it does|What to do|Good to know', 'the same three headings on every sign');
  const strip = await page.evaluate(() => [...document.querySelectorAll('#sign-pictures figure')].map(f => ({ color: f.dataset.color, caption: f.querySelector('figcaption').textContent, art: !!f.querySelector('svg') })));
  check(strip.map(s => s.color).join() === sign.colors.join() && strip.every(s => s.art && s.caption), `the picture strip shows ${sign.colors} (${JSON.stringify(strip)})`);
  const stroke = await page.evaluate(() => { const c = document.querySelector('#sign-pictures figure[data-color="red"] circle'); return c?.getAttribute('stroke'); });
  check(stroke === await page.evaluate(() => BossMech.colors.red), 'the red in the picture is the red of the fight');
  check(await page.evaluate(() => { const r = document.getElementById('sign-panel').getBoundingClientRect(); return r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight; }), 'the window fits the screen');
  check(!(await page.evaluate(() => Field.hero.dead)) && (await page.evaluate(() => Online.connected)), 'the game keeps running behind it');
  await page.screenshot({ path: path.join(world.artifacts, 'bosssign-window.png') });

  // ---- 3. the four ways to close it ---------------------------------------------------------------------------------------------
  await page.keyboard.press('Escape');
  check(!(await visible()), 'Esc closes it');
  await page.keyboard.press('f'); await page.waitForFunction(() => !document.getElementById('sign-panel').hidden);
  await page.locator('#sign-x').click();
  check(!(await visible()), 'the cross closes it');
  await page.keyboard.press('f'); await page.waitForFunction(() => !document.getElementById('sign-panel').hidden);
  await page.locator('#sign-close').click();
  check(!(await visible()), 'the Close button closes it');
  await page.keyboard.press('f'); await page.waitForFunction(() => !document.getElementById('sign-panel').hidden);
  await debugOp({ op: 'teleport', zone: UNDERVAULT, x: sign.x, y: sign.y + 7 });
  await page.waitForFunction(() => document.getElementById('sign-panel').hidden, null, { timeout: 4000 });
  check(true, 'walking away closes it');

  // ---- 4. a click walks up to the sign and reads it ----------------------------------------------------------------------------
  const far = await goNear([-6, 0], [6, 0], [0, 6], [0, -6]);
  check(far > 4, `the hero stands ${far.toFixed(1)} tiles from the sign`);
  await page.evaluate(() => {
    const s = Field.signs[0], [sx, sy] = Field._debug.w2s(s.x, s.y), cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect();
    window.__signClick = { x: r.left + sx / 1600 * r.width, y: r.top + (sy - 40) / (cv.height / (cv.width / 1600)) * r.height };
  });
  const at = await page.evaluate(() => window.__signClick);
  await page.mouse.click(at.x, at.y);
  await page.waitForFunction(() => !document.getElementById('sign-panel').hidden, null, { timeout: 20000 });
  const reached = await page.evaluate(() => { const s = Field.signs[0]; return Math.hypot(Field.hero.x - s.x, Field.hero.y - s.y); });
  check(reached <= 2.6, `a click on the board walked the hero to it (${reached.toFixed(2)} tiles) and read it`);
  await page.keyboard.press('Escape');

  // ---- 5. a reload reads it again; the text is the server's every time ---------------------------------------------------------
  await page.evaluate(() => Online.stop());
  for (let i = 0; i < 50 && (await (await fetch(world.url + 'health')).json()).online !== 0; i++) await new Promise(r => setTimeout(r, 200));   // the old connection is gone
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();   // the saved guest key signs the same hero in
  await page.waitForFunction(() => Online.connected && Field.hero.id, null, { timeout: 60000 });
  await goNear([0, 1.2], [1.2, 0], [-1.2, 0]);
  await page.keyboard.press('f');
  await page.waitForFunction(() => !document.getElementById('sign-panel').hidden, null, { timeout: 8000 });
  check(await text('#sign-what') === sign.what && await text('#sign-title') === sign.title, 'after a reload the sign reads the same');
  await page.keyboard.press('Escape');

  // ---- 6. a phone-sized screen --------------------------------------------------------------------------------------------------
  await page.setViewportSize({ width: 844, height: 390 });
  await page.keyboard.press('f');
  await page.waitForFunction(() => !document.getElementById('sign-panel').hidden, null, { timeout: 8000 });
  await page.waitForTimeout(200);
  const phone = await page.evaluate(() => {
    const p = document.getElementById('sign-panel'), r = p.getBoundingClientRect(), x = document.getElementById('sign-x').getBoundingClientRect();
    return { inside: r.left >= 0 && r.top >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1, reachable: p.scrollHeight <= p.clientHeight + 1 || getComputedStyle(p).overflowY !== 'hidden', cross: Math.min(x.width, x.height), font: parseFloat(getComputedStyle(document.getElementById('sign-what')).fontSize) };
  });
  check(phone.inside && phone.reachable, `the window fits 844 x 390 (${JSON.stringify(phone)})`);
  check(phone.font >= 15, `the type stays large (${phone.font}px)`);
  await page.screenshot({ path: path.join(world.artifacts, 'bosssign-phone.png') });
  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 1440, height: 900 });

  // ---- 7. no sign outside the dungeon ---------------------------------------------------------------------------------------------
  await debugOp({ op: 'teleport', zone: 0, x: 48, y: 60 });
  await page.waitForFunction(() => Field.signs.length === 0, null, { timeout: 10000 });
  check(true, 'back in the meadow there is no sign');

  // ---- 8. Swedish, written by hand ---------------------------------------------------------------------------------------------------
  const sv = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  await sv.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false })));
  await sv.goto(world.url);
  const words = await sv.evaluate(() => ['What it does', 'What to do', 'Good to know', 'Red hurts.', 'Blue is safe.', 'A dashed line is a path that is about to be used.', 'Green is the way through.', 'F · Read', 'Close the sign', 'Walk closer to read this sign.'].map(s => Locale.translate(s)));
  assert.deepEqual(words, ['Vad den gör', 'Vad du ska göra', 'Bra att veta', 'Rött gör ont.', 'Blått är säkert.', 'En streckad linje är en väg som snart ska användas.', 'Grönt är vägen igenom.', 'F · Läs', 'Stäng skylten', 'Gå närmare för att läsa skylten.']);
  checks += words.length;
  const own = await sv.evaluate(({ what, todo, tip, title }) => [what, todo, tip, title].map(s => Locale.translate(s)), sign);
  check(own.every((s, i) => s && s !== [sign.what, sign.todo, sign.tip, sign.title][i] || i === 3), 'the sign\'s own words have Swedish');

  assert.deepEqual(errors, []);
  console.log(`bosssign-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
  fs.rmSync(dir, { recursive: true, force: true });
});
