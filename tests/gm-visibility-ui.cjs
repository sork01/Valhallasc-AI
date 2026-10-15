// GM invisibility in two real browsers (GM-INVIS-CLIENT, GM-INVIS-CHECK). [GM]Sork and an ordinary player share Greenmeadow;
// the ordinary player's raw WebSocket frames are inspected, so hidden means absent from the traffic, not just from the screen.
// (Original header of the scaffolding below:) The game master's administrator character in a real browser. The site SSO is a fake endpoint run by this test: one
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
  // Prefer the release build: the debug server falls behind real time in a busy zone.
  const release = path.join(root, 'target/release/valhalla-server');
  const binary = process.env.VALHALLA_BINARY || (fs.existsSync(release) ? release : path.join(root, 'target/debug/valhalla-server'));
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


const framesOf = page => {
  const seen = { raw: [], players: [], online: null, chat: [] };
  page.on('websocket', ws => ws.on('framereceived', f => {
    const text = String(f.payload);
    seen.raw.push(text);
    try {
      const data = JSON.parse(text);
      const view = data.snapshot || data;
      if (Array.isArray(view.players)) { seen.players = view.players.map(p => p.look?.name); seen.online = view.online; }
      if (data.type === 'chat') seen.chat.push(data);
    } catch { /* not JSON */ }
  }));
  return seen;
};
const mentions = seen => seen.raw.filter(t => t.includes('[GM]Sork')).length;
const badge = page => page.evaluate(() => { const b = document.getElementById('gm-visibility'); return { text: b.textContent, hidden: b.dataset.hidden, shown: !b.hidden }; });
const waitFor = async (fn, ms = 6000) => { const end = Date.now() + ms; while (Date.now() < end) { if (await fn()) return true; await new Promise(r => setTimeout(r, 100)); } return false; };

(async () => {
  const dir = fs.mkdtempSync(path.join(root, 'test-results/gm-vis-'));
  const ssoUrl = await startFakeSso();
  await startServer(ssoUrl, path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  const pages = [];
  try {
    // the ordinary player first, so every frame the GM could leak is recorded from the start
    const other = await newPlayer(OTHER); pages.push(other);
    const seen = framesOf(other);
    await signIn(other);
    await other.locator('#chars-new').click(); await other.locator('#cls-warrior').click(); await other.locator('#name').fill('Plainhero'); await other.locator('#go').click();
    await connected(other);

    const sork = await newPlayer(SORK); pages.push(sork);
    await signIn(sork);
    await sork.locator('#chars-gm').click(); await connected(sork);
    await other.waitForTimeout(1200);

    // ---- hidden by default ----
    const first = await badge(sork);
    check(first.shown && first.text === 'Hidden' && first.hidden === 'true', 'the GM sees a Hidden badge on login: ' + JSON.stringify(first));
    check(await sork.evaluate(() => Field.hero.hidden === true), 'the GM client knows its own character is hidden');
    check(mentions(seen) === 0, 'the ordinary player received nothing that names the GM (' + mentions(seen) + ' frames)');
    check(!seen.players.includes('[GM]Sork') && seen.players.includes('Plainhero'), 'the ordinary player sees only themself: ' + JSON.stringify(seen.players));
    check(seen.online === 1, 'the count the ordinary player sees excludes the GM (' + seen.online + ')');
    check(!(await other.evaluate(() => (document.body.innerText || '').includes('[GM]Sork'))), 'the GM is nowhere on the ordinary player\'s screen');

    // ---- chat while hidden: name and text, no position or id ----
    await type(sork, 'hello from nowhere');
    check(await waitFor(() => seen.chat.some(c => c.text === 'hello from nowhere')), 'a hidden GM can still chat');
    const line = seen.chat.find(c => c.text === 'hello from nowhere');
    check(line.name === '[GM]Sork' && (line.id === null || line.id === undefined) && !('x' in line), 'the chat line has a name and text but no character id or position: ' + JSON.stringify(line));

    // ---- /show, /hide ----
    await type(sork, '/vis');
    await sork.waitForFunction(() => /You are hidden\./.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check(true, '/vis reports the state');
    await type(sork, '/show');
    await sork.waitForFunction(() => /You are visible\./.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check((await badge(sork)).text === 'Visible', 'the badge says Visible after /show');
    check(await waitFor(() => seen.players.includes('[GM]Sork')), 'after /show the ordinary player receives the GM in the zone view: ' + JSON.stringify(seen.players));
    check(await waitFor(() => seen.online === 2), 'and the count includes the GM (' + seen.online + ')');
    await type(sork, '/hide');
    await sork.waitForFunction(() => /You are hidden\./.test(document.getElementById('chat-log').textContent.split('You are visible.').pop()), null, { timeout: 5000 });
    check(await waitFor(() => !seen.players.includes('[GM]Sork') && seen.online === 1), '/hide removes the GM from the ordinary player\'s view again: ' + JSON.stringify(seen.players));
    check((await badge(sork)).text === 'Hidden', 'and the badge says Hidden');
    await type(sork, '/vis toggle');
    check(await waitFor(() => seen.players.includes('[GM]Sork')), '/vis toggle flips it back to visible');
    await type(sork, '/vis off');
    check(await waitFor(() => !seen.players.includes('[GM]Sork')), '/vis off hides');

    // ---- an ordinary player cannot do any of it ----
    await type(other, '/show');
    await other.waitForTimeout(500);
    check(!(await chatLog(other)).includes('You are visible'), 'slash text from an ordinary player is plain chat');
    const refused = await other.evaluate(() => new Promise(resolve => {
      const timer = setTimeout(() => resolve(null), 3000);
      GM.onReply = packet => { clearTimeout(timer); resolve(packet); };
      Online.send({ type: 'debug', ref: 77, command: { op: 'visibility', mode: 'off' } });
    }));
    check(refused === null || refused.ok === false, 'a hand-made visibility message is refused for an ordinary player');
    check((await badge(sork)).text === 'Hidden' && !seen.players.includes('[GM]Sork'), 'and nothing changed for the GM');

    // ---- a zone change hides the GM again ----
    await type(sork, '/show');
    check(await waitFor(() => seen.players.includes('[GM]Sork')), 'visible again before leaving');
    await type(sork, '/tp crags');
    await sork.waitForFunction(() => /now in Emberfall Crags/.test(document.getElementById('chat-log').textContent), null, { timeout: 8000 });
    check(await waitFor(async () => (await badge(sork)).text === 'Hidden', 8000), 'the zone change reset the GM to Hidden');
    await type(sork, '/tp city');
    await sork.waitForFunction(() => /now in Greenmeadow/.test(document.getElementById('chat-log').textContent.split('Emberfall Crags').pop()), null, { timeout: 8000 });
    await other.waitForTimeout(800);
    check(!seen.players.includes('[GM]Sork'), 'back in the city the GM is still hidden to the ordinary player');

    check(sork.errors.length === 0 && other.errors.length === 0, 'no page errors: ' + sork.errors.concat(other.errors).join('; '));
    console.log(`gm-visibility-ui: ${checks} checks passed`);
  } finally {
    for (const page of pages) await page.context().close().catch(() => {});
    await browser.close().catch(() => {});
    server?.kill(); fake?.close();
  }
})().catch(error => { console.error(error); console.error(logs.slice(-2500)); process.exit(1); });
