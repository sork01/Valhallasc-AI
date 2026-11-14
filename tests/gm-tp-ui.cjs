// GM-TP-PLAYER (a slim cut of gm-ui.cjs, which is too heavy for the 1.5 GiB cap): /tp <player> lands next to a named online player. MUTATE=1 serves the old gm.js.
// Original header: The game master's administrator character in a real browser. The site SSO is a fake endpoint run by this test: one
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
  const page = await context.newPage(); page.errors = [];
  if (process.env.MUTATE === '1') { const old = require('node:child_process').execFileSync('git', ['show', '0106bebd:client/gm.js'], { cwd: root, encoding: 'utf8' }); await page.route('**/gm.js*', route => route.fulfill({ contentType: 'text/javascript', body: old })); }
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
  const dir = fs.mkdtempSync(path.join(root, 'test-results/gm-tp-'));
  const ssoUrl = await startFakeSso();
  await startServer(ssoUrl, path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const pages = [];
  try {
    // One page only (two browsers do not fit the memory cap): the command is captured on its way to the server, which the Rust test
    // the gm-shortcuts Rust test in world.rs ("Goto finds a player by name") proves lands next to the player, in a dungeon copy too.
    const sork = await newPlayer(SORK); pages.push(sork);
    await signIn(sork);
    await sork.locator('#chars-gm').click();
    await connected(sork);
    await sork.evaluate(() => { window.__sent = []; const send = Online.send; Online.send = m => { if (m?.type === 'debug') window.__sent.push(m.command); return send.call(Online, m); }; });
    const sent = async text => { await sork.evaluate(() => { window.__sent.length = 0; }); await type(sork, text); await sork.waitForTimeout(250); return sork.evaluate(() => window.__sent.slice()); };
    check(JSON.stringify(await sent('/tp plainhero')) === JSON.stringify([{ op: 'goto', name: 'plainhero' }]), '/tp <player> asks the server to go to that player');
    check(JSON.stringify(await sent('/tp Old Tusker Fan')) === JSON.stringify([{ op: 'goto', name: 'Old Tusker Fan' }]), 'a name of several words is passed whole');
    const crags = await sent('/tp crags');
    check(crags.length === 1 && crags[0].op === 'teleport' && crags[0].zone === 1, 'a zone name still wins: /tp crags is a teleport to zone 1');
    check(JSON.stringify(await sent('/tp 40 40')).includes('"op":"teleport"'), '/tp x y is unchanged');
    check((await sent('/tp 2')).every(c => c.op === 'teleport' && c.zone === 2), 'a zone number is unchanged');
    check((await sent('/tp 9999')).length === 0, 'an unknown zone number sends nothing');
    await sork.waitForFunction(() => /No zone or online player named 9999/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check((await sork.locator('#chat-log').innerText()).includes('/tp'), 'the error mentions players, and /gmcommands lists the new usage');
    await type(sork, '/gmcommands');
    await sork.waitForFunction(() => /\/tp <zone> \[x y\] \| <x y> \| <player>/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    console.log(`gm-tp-ui: ${checks} checks passed`);
  } finally {
    for (const page of pages) await page.context().close().catch(() => {});
    await browser.close().catch(() => {});
    server?.kill(); fake?.close();
  }
})().catch(error => { console.error(error); console.error(logs.slice(-1500)); process.exit(1); });
