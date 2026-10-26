// The GM test menu (client/gmtest.js) in a real browser. Based on gm-ui.cjs: the server runs WITHOUT test shortcuts, so only
// [GM]Sork may use it.
// (gm-ui.cjs header follows) The game master's administrator character in a real browser. The site SSO is a fake endpoint run by this test: one
// cookie signs in as Sork, another as an ordinary user. The server runs WITHOUT the test shortcuts, so everything the
// game master does goes through the one rule that lets [GM]Sork use them. Covers: the extra character slot, the golden
// look, the chat commands (/tp /god /give /level /goto ...), their replies in the chat log, and that nobody else
// gets any of it (no slot button, slash text is plain chat, a hand-made debug message is refused).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const timer = setTimeout(() => reject(Error(label)), ms); timer.unref(); })]);
let server, fake, browser, url, logs = '', checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const SORK = 'sorksession1234567890', OTHER = 'othersession1234567890';
async function startFakeSso() {
  fake = http.createServer((req, res) => {
    const cookie = req.headers.cookie || '', user = cookie.includes('sso_session=' + SORK) ? 'Sork' : cookie.includes('sso_session=' + OTHER) ? 'Other_User' : null;
    res.writeHead(user ? 200 : 401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(user ? { authenticated: true, username: user, email: '' } : { authenticated: false }));
  });
  await new Promise(resolve => fake.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${fake.address().port}/sso/kriswe-session.php`;
}
async function startServer(ssoUrl, db) {
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  const env = { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_SSO_URL: ssoUrl };
  for (const name of ['VALHALLA_ORIGIN', 'VALHALLA_SSO_RESOLVE', 'VALHALLA_GOD_MODE', 'VALHALLA_TEST_COMMANDS']) delete env[name];
  server = spawn(binary, [], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); const match = logs.match(/address=(127\.0\.0\.1:\d+)/); if (match) { url = 'http://' + match[1] + '/'; resolve(); } });
    server.once('error', reject); server.once('exit', code => reject(Error(`Server exited ${code}: ${logs}`)));
  }), 15000, 'Server did not start');
}
async function newPlayer(cookie) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await context.addInitScript(() => { window.__valhallaTestSprites = true; if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await context.addCookies([{ name: 'sso_session', value: cookie, url }]);
  if (process.env.MUTATE === 'raid-hires') await context.route('**/gmtest.js', async route => {
    const response = await route.fetch(), body = await response.text();
    assert.ok(body.includes('dungeon?.mercs ?? 4'), 'hire-label mutation must match');
    await route.fulfill({ response, body: body.replace('dungeon?.mercs ?? 4', '4') });
  });
  const page = await context.newPage(); page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(url);
  return page;
}
const signIn = async page => {
  await page.locator('#start').click(); await page.locator('#login-title').waitFor({ state: 'visible', timeout: 10000 });
  await page.locator('#login-sso').click(); await page.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
};
const connected = page => page.waitForFunction(() => Online.connected && !!Field.hero, null, { timeout: 60000 });
const chatLog = page => page.locator('#chat-log').innerText();
async function type(page, text) {
  await page.locator('#chat-input').fill(text); await page.locator('#chat-input').press('Enter');
}

(async () => {
  const dir = fs.mkdtempSync(path.join(root, 'test-results/gmtest-'));
  const ssoUrl = await startFakeSso();
  await startServer(ssoUrl, path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  const pages = [];
  try {
    const sork = await newPlayer(SORK); pages.push(sork);
    await signIn(sork);
    await sork.locator('#chars-gm').click();
    await connected(sork);
    check(await sork.locator('#gmtest-open').isVisible(), 'the GM sees the Test button');
    await sork.locator('#gmtest-open').click();
    await sork.waitForFunction(() => document.querySelectorAll('#gmtest-dungeon option').length > 10, null, { timeout: 10000 });
    check(await sork.locator('#gmtest-panel').isVisible(), 'the menu opens');
    const names = await sork.locator('#gmtest-dungeon option').allTextContents();
    check(names.some(n => n.startsWith('The Undervault')) && names.some(n => n.includes('Chained Forge')), 'dungeons and the raid are listed');
    check((await sork.locator('#gmtest-glevel option').count()) > 0 && (await sork.locator('#gmtest-gfight option').count()) === 5, 'gauntlet levels and five fights are listed');
    // Enter the Undervault at its final boss with level, blue gear and four hired fighters.
    await sork.locator('#gmtest-dungeon').selectOption({ label: names.find(n => n.startsWith('The Undervault')) });
    check((await sork.locator('#gmtest-at option').allTextContents()).includes('Final boss'), 'places include the final boss');
    await sork.locator('#gmtest-at').selectOption('boss');
    await sork.locator('#gmtest-gear').selectOption('blue');
    await sork.locator('#gmtest-level').check(); await sork.locator('#gmtest-mercs').check();
    await sork.locator('#gmtest-panel button', { hasText: 'Enter' }).click();
    await sork.waitForFunction(() => Field.zone === 5 && Field.hero.level === 20 && Field.remotePlayers.filter(p => p.hired).length === 4, null, { timeout: 15000 });
    const state = await sork.evaluate(() => ({ level: Field.hero.level }));
    check(state.level === 20, 'the hero is at the dungeon level (' + state.level + ')');
    // A multiplier applies to this copy and the status reads back.
    await sork.locator('#gmtest-t-pack_damage').evaluate(el => { el.value = '0.5'; el.dispatchEvent(new Event('change')); });
    await sork.waitForFunction(() => /Pack damage x0.50/.test(document.querySelector('.gmtest-status')?.textContent || ''), null, { timeout: 8000 });
    check(await sork.locator('#gmtest-t-pack_damage').inputValue() === '0.5', 'the pack damage slider holds the server value');
    check(await sork.locator('#gmtest-t-opponent_damage').isDisabled(), 'gauntlet multipliers are off outside a run');
    await sork.locator('#gmtest-panel button', { hasText: 'Enrage clock' }).click();
    await sork.waitForFunction(() => /hollowking/.test(document.querySelector('.gmtest-status')?.textContent || ''), null, { timeout: 8000 });
    check(true, 'the enrage clock lists the boss');
    // Escape closes the window.
    await sork.keyboard.press('Escape');
    check(await sork.locator('#gmtest-panel').isHidden(), 'Escape closes the menu');
    // /dungeon reset and /tune reset work as console commands.
    await type(sork, '/tune reset');
    await sork.waitForFunction(() => /\/tune: dungeon/.test(document.getElementById('chat-log').textContent), null, { timeout: 8000 });
    check(true, '/tune answers in the chat log');
    check(sork.errors.length === 0, 'no page errors for the GM: ' + sork.errors.join('; '));

    // The raid option provisions the GM plus nine actual fighters and survives its info refresh.
    await sork.locator('#gmtest-open').click();
    await sork.locator('#gmtest-dungeon').selectOption({ label: names.find(n => n.includes('Chained Forge')) });
    check(/9 hired fighters/.test(await sork.locator('label', { has: sork.locator('#gmtest-mercs') }).innerText()), 'the raid offers nine hires');
    await sork.locator('#gmtest-at').selectOption('door');
    // Keep the previous gear: a second full set tests bag capacity, not raid hiring.
    await sork.locator('#gmtest-gear').selectOption('');
    await sork.evaluate(() => {
      const request = GM.request.bind(GM);
      GM.request = async command => { const reply = await request(command); if (command.op === 'gm_dungeon_enter') window.__raidEntry = reply; return reply; };
    });
    await sork.locator('#gmtest-panel button', { hasText: 'Enter' }).click();
    await sork.waitForFunction(() => !!window.__raidEntry);
    const raidEntry = await sork.evaluate(() => window.__raidEntry);
    check(raidEntry.ok && raidEntry.result.mercs === 9, 'raid entry hires nine: ' + JSON.stringify(raidEntry));
    await sork.waitForFunction(() => Field.zone === 46 && Field.remotePlayers.filter(p => p.hired).length === 9, null, { timeout: 15000 });
    check(await sork.evaluate(() => Field.hero.level === 99 && Field.remotePlayers.filter(p => p.hired).every(p => p.level === 99)), 'nine level-99 mercenaries arrive in the raid');
    await sork.waitForFunction(() => document.querySelector('.gmtest-status')?.textContent === 'Ready. Every action is logged on the server.');
    check((await sork.locator('#gmtest-dungeon option:checked').innerText()).includes('Chained Forge'), 'refresh keeps the raid selected');
    check(/9 hired fighters/.test(await sork.locator('label', { has: sork.locator('#gmtest-mercs') }).innerText()), 'refresh retains the raid hire count');
    await sork.locator('#gmtest-dungeon').selectOption({ label: names.find(n => n.startsWith('The Undervault')) });
    check(/4 hired fighters/.test(await sork.locator('label', { has: sork.locator('#gmtest-mercs') }).innerText()), 'ordinary dungeons still offer four hires');
    await sork.keyboard.press('Escape');

    await sork.context().close();
    // An ordinary player has no button and a hand-made op is refused.
    const other = await newPlayer(OTHER); pages.push(other);
    await signIn(other);
    await other.locator('#chars-new').click(); await other.locator('#cls-warrior').click(); await other.locator('#name').fill('Plainhero'); await other.locator('#go').click();
    await connected(other);
    check(await other.locator('#gmtest-open').isHidden(), 'an ordinary player has no Test button');
    const reply = await other.evaluate(() => GM.request({ op: 'gm_dungeon_enter', zone: 5, at: 'door', level: true, gear: null, mercs: false }));
    check(reply.ok === false, 'a hand-made menu op is refused for an ordinary player');
    check(await other.evaluate(() => Field.hero.level) === 1, 'and the level did not move');
    console.log(`gmtest-ui: ${checks} checks passed`);
  } finally {
    for (const page of pages) await page.context().close().catch(() => {});
    await browser.close().catch(() => {});
    server?.kill(); fake?.close();
  }
})().catch(error => { console.error(error); console.error(logs.slice(-2500)); process.exit(1); });
