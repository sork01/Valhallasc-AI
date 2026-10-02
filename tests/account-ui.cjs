// Sign-in in a real browser: guest (unchanged), game account (username + password) and gunning.se SSO. The site SSO is
// a fake HTTP endpoint run by this test and named by VALHALLA_SSO_URL; the world is a private server and database.
// Account characters must live on the server: a second browser with empty storage logs in and gets the same character.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { chromium, STUB } = require('./lib/playwright.cjs');
const root = path.resolve(__dirname, '..');
const timeout = (promise, ms, label) => Promise.race([promise, new Promise((_, reject) => { const timer = setTimeout(() => reject(Error(label)), ms); timer.unref(); })]);
let server, fake, browser, url, logs = '', checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const GOOD_COOKIE = 'goodsession1234567890';
async function startFakeSso() {
  fake = http.createServer((req, res) => {
    const ok = (req.headers.cookie || '').includes('sso_session=' + GOOD_COOKIE);
    res.writeHead(ok ? 200 : 401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(ok ? { authenticated: true, username: 'Sso_Tester', email: '' } : { authenticated: false }));
  });
  await new Promise(resolve => fake.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${fake.address().port}/sso/kriswe-session.php`;
}
async function startServer(ssoUrl, db) {
  const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
  const env = { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: db, RUST_LOG: 'valhalla_server=info', VALHALLA_LEVEL_SPREAD: '0', VALHALLA_GOD_MODE: '1', VALHALLA_SSO_URL: ssoUrl };
  delete env.VALHALLA_ORIGIN; delete env.VALHALLA_SSO_RESOLVE;
  server = spawn(binary, [], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
  server.stderr.on('data', data => { logs += data; });
  await timeout(new Promise((resolve, reject) => {
    server.stdout.on('data', data => { logs += data.toString().replace(/\x1b\[[0-9;]*m/g, ''); const match = logs.match(/address=(127\.0\.0\.1:\d+)/); if (match) { url = 'http://' + match[1] + '/'; resolve(); } });
    server.once('error', reject); server.once('exit', code => reject(Error(`Server exited ${code}: ${logs}`)));
  }), 15000, 'Server did not start');
}
async function newPlayer(cookies = []) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await context.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  if (cookies.length) await context.addCookies(cookies);
  const page = await context.newPage(); page.errors = []; page.context_ = context;
  page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(url);
  return page;
}
const toLogin = async page => { await page.locator('#start').click(); await page.locator('#login-title').waitFor({ state: 'visible', timeout: 10000 }); };
const connected = page => page.waitForFunction(() => Online.connected && !!Field.hero, null, { timeout: 60000 });
async function createCharacter(page, cls, name) {
  await page.locator('#cls-' + cls).click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await connected(page);
}
const stored = (page, prefix) => page.evaluate(p => Object.entries(localStorage).filter(([k]) => k.startsWith(p)).map(([, v]) => JSON.parse(v)), prefix);

(async () => {
  const dir = fs.mkdtempSync(path.join(root, 'test-results/account-'));
  const ssoUrl = await startFakeSso();
  await startServer(ssoUrl, path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  const pages = [];
  try {
    // The scenarios use separate accounts, pages and cookies, so they run at the same time; only the steps inside one
    // scenario depend on each other.
    const accountKey = 'valhallasc.account.v1:' + url.replace(/^http/, 'ws') + 'ws';
    const flows = {
      guest: async () => {
      // --- the screen offers all three ways in ---
      const guest = await newPlayer(); pages.push(guest);
      await toLogin(guest);
      for (const id of ['#login-guest', '#login-sso', '#login-submit', '#login-register']) check(await guest.locator(id).isVisible(), id + ' is on the sign-in screen');
      check(await guest.locator('#login-account').isHidden(), 'nobody is signed in yet');

      // --- guest: the original flow, key kept in this browser, nothing account-shaped stored ---
      await guest.locator('#login-guest').click();
      await createCharacter(guest, 'mage', 'GuestOne');
      check(await guest.evaluate(() => Online.mode) === 'guest', 'guest mode');
      const guestChars = (await stored(guest, 'valhallasc.characters.v1:'))[0];
      check(guestChars?.characters?.length === 1 && /^[0-9a-f]{64}$/.test(guestChars.characters[0].token), 'the guest key is in this browser');
      check(!(await stored(guest, 'valhallasc.account.v1:'))[0]?.session, 'no account session for a guest');
      const guestId = await guest.evaluate(() => Online.id);
      await guest.reload(); await toLogin(guest); await guest.locator('#login-guest').click(); await connected(guest);
      check(await guest.evaluate(() => Online.id) === guestId, 'a guest resumes the same server character after a reload');

      },
      account: async () => {
      // --- game account: register, character stored on the server ---
      const one = await newPlayer(); pages.push(one);
      await toLogin(one);
      await one.locator('#login-user').fill('Acct_One'); await one.locator('#login-pass').fill('short');
      await one.locator('#login-register').click();
      await one.waitForFunction(() => /8 to 128/.test(document.getElementById('login-msg').textContent), null, { timeout: 5000 });
      check(true, 'a weak password is refused with the reason');
      await one.locator('#login-pass').fill('hunter22x'); await one.locator('#login-register').click();
      await one.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
      check((await one.locator('#chars-who').textContent()).includes('Acct_One') && (await one.locator('#chars-who').textContent()).includes('0 of 5'), 'the account has no characters yet');
      check(await one.locator('#chars-new').isEnabled(), 'New character is available');
      await one.locator('#chars-new').click();
      await createCharacter(one, 'warrior', 'AcctWarrior');
      check(await one.evaluate(() => Online.mode) === 'account', 'account mode');
      const acctId = await one.evaluate(() => Online.id);
      check(!(await stored(one, 'valhallasc.characters.v1:'))[0]?.characters?.length, 'an account character leaves no guest key behind');
      const acctStore = (await stored(one, 'valhallasc.account.v1:'))[0];
      check(/^[0-9a-f]{64}$/.test(acctStore.session) && acctStore.current === acctId, 'the browser keeps the session and the current character id');
      // a layout is saved per account character
      await one.evaluate(() => Online.saveSkillSlots(['a', 'b'], 3));
      check(JSON.stringify((await stored(one, 'valhallasc.account.v1:'))[0].slots[acctId].skillSlots) === '["a","b"]', 'skill layout is stored under the account character');

      // reload: still signed in, character listed, same character resumes
      await one.reload(); await toLogin(one);
      check(await one.locator('#login-account').isVisible() && (await one.locator('#login-name').textContent()) === 'Acct_One', 'a reload remembers the login');
      check(await one.locator('#login-form').isHidden(), 'the password form hides while signed in');
      await one.locator('#login-continue').click();
      await one.locator('.char-play').first().waitFor({ state: 'visible', timeout: 10000 });
      check((await one.locator('.char-play').first().textContent()).includes('AcctWarrior'), 'the character is listed');
      await one.locator('.char-play').first().click(); await connected(one);
      check(await one.evaluate(() => Online.id) === acctId, 'continuing resumes the same character');

      // the guest's own character is untouched by account play
      await one.context_.close();
      // --- a different browser with empty storage gets the same character from the server ---
      const two = await newPlayer(); pages.push(two);
      await toLogin(two);
      await two.locator('#login-user').fill('acct_one'); await two.locator('#login-pass').fill('wrongpass1'); await two.locator('#login-submit').click();
      await two.waitForFunction(() => /Wrong username or password/.test(document.getElementById('login-msg').textContent));
      check(true, 'a wrong password is refused');
      check(await two.locator('#chars-title').isHidden(), 'and stays on the sign-in screen');
      await two.locator('#login-pass').fill('hunter22x'); await two.locator('#login-submit').click();
      await two.locator('.char-play').first().waitFor({ state: 'visible', timeout: 10000 });
      check((await two.locator('.char-play').first().textContent()).includes('AcctWarrior'), 'another browser sees the account character (usernames ignore case)');
      await two.locator('.char-play').first().click(); await connected(two);
      check(await two.evaluate(() => Online.id) === acctId, 'the second browser plays the same server character');
      // taken name
      const three = await newPlayer(); pages.push(three);
      await toLogin(three);
      await three.locator('#login-user').fill('ACCT_ONE'); await three.locator('#login-pass').fill('another99'); await three.locator('#login-register').click();
      await three.waitForFunction(() => /taken/.test(document.getElementById('login-msg').textContent));
      check(true, 'a taken username is refused');
      // guest and account are separate: this browser's guest button still makes a guest
      await three.locator('#login-guest').click(); check(await three.locator('#cls-warrior').isVisible(), 'guest play from the same screen still starts character creation');
      // character in the world cannot be deleted; after leaving it can
      await two.keyboard.press('Escape'); await two.locator('#p-title').click();
      await toLogin(two);
      // the server needs a moment to notice the socket closed: while it still lists the character the delete is refused, so retry
      await two.locator('#login-continue').click(); await two.locator('.char-del').first().waitFor({ state: 'visible' });
      let deleted = false;
      for (let attempt = 0; attempt < 12 && !deleted; attempt++) {
        await two.evaluate(() => { document.getElementById('chars-msg').textContent = ''; });
        await two.locator('.char-del').first().click();
        if (attempt === 0) check((await two.locator('.char-del').first().textContent()) === 'Really?', 'deleting asks twice');
        await two.locator('.char-del').first().click();
        await two.waitForFunction(() => /was deleted|world right now/.test(document.getElementById('chars-msg').textContent), null, { timeout: 10000 });
        deleted = /was deleted/.test(await two.locator('#chars-msg').textContent());
        if (!deleted) await new Promise(r => setTimeout(r, 300));
      }
      check(deleted, 'a character is deleted once it has left the world');
      check(await two.locator('.char-play').count() === 0, 'the deleted character is gone from the list');
      check((await two.locator('#chars-who').textContent()).includes('0 of 5'), 'and from the count');
      // log out
      await two.locator('#chars-back').click(); await two.locator('#login-logout').click();
      await two.waitForFunction(() => !document.getElementById('login-form').hidden);
      check(!(await stored(two, 'valhallasc.account.v1:'))[0].session, 'logging out forgets the session');

      },
      stale: async () => {
      // --- an expired or forged session is rejected, not trusted ---
      const stale = await newPlayer(); pages.push(stale);
      await stale.evaluate(k => localStorage.setItem(k, JSON.stringify({ session: 'f'.repeat(64), name: 'Ghost', kind: 'game', current: null, slots: {} })), accountKey);
      await stale.reload(); await toLogin(stale);
      await stale.waitForFunction(() => !document.getElementById('login-form').hidden, null, { timeout: 10000 });
      check(/expired/.test(await stale.locator('#login-msg').textContent()), 'a session the server does not know is dropped with a message');

      },
      sso: async () => {
      // --- SSO: the site cookie identifies the user ---
      const sso = await newPlayer([{ name: 'sso_session', value: GOOD_COOKIE, url }]); pages.push(sso);
      await toLogin(sso); await sso.locator('#login-sso').click();
      await sso.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
      check((await sso.locator('#chars-who').textContent()).includes('Sso_Tester (gunning.se)'), 'SSO signs in as the site user');
      await sso.locator('#chars-new').click(); await createCharacter(sso, 'assassin', 'SsoRogue');
      const ssoId = await sso.evaluate(() => Online.id);
      check((await stored(sso, 'valhallasc.account.v1:'))[0].kind === 'sso', 'an SSO account is marked as one');
      await sso.context_.close();
      // the same SSO user from another browser
      const sso2 = await newPlayer([{ name: 'sso_session', value: GOOD_COOKIE, url }]); pages.push(sso2);
      await toLogin(sso2); await sso2.locator('#login-sso').click();
      await sso2.locator('.char-play').first().waitFor({ state: 'visible', timeout: 10000 });
      check((await sso2.locator('.char-play').first().textContent()).includes('SsoRogue'), 'SSO characters follow the site account');
      await sso2.locator('.char-play').first().click(); await connected(sso2);
      check(await sso2.evaluate(() => Online.id) === ssoId, 'and resume');
      // a game account named like the SSO user is a different account
      const clash = await newPlayer(); pages.push(clash);
      await toLogin(clash); await clash.locator('#login-user').fill('Sso_Tester'); await clash.locator('#login-pass').fill('hunter22x'); await clash.locator('#login-register').click();
      await clash.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
      check((await clash.locator('.char-play').count()) === 0, 'a game account called Sso_Tester does not see the SSO account\'s characters');

      },
      away: async () => {
      // --- SSO without a site login: sent to the site login, and finished on return ---
      const away = await newPlayer(); pages.push(away);
      await toLogin(away); await away.locator('#login-sso').click();
      await away.waitForURL(u => u.pathname.startsWith('/sso/'), { timeout: 10000 });
      check(await away.evaluate(() => sessionStorage.getItem('valhallasc.sso.pending')) === '1', 'the pending sign-in is remembered across the redirect');
      await away.context_.addCookies([{ name: 'sso_session', value: GOOD_COOKIE, url }]);
      await away.goto(url); await away.locator('#start').click();
      await away.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
      check((await away.locator('#chars-who').textContent()).includes('Sso_Tester'), 'coming back from the site login finishes the SSO sign-in');
      // a forged cookie is refused by the (fake) site
      const forged = await newPlayer([{ name: 'sso_session', value: 'forgedsession123456', url }]); pages.push(forged);
      const refused = await forged.evaluate(async () => (await fetch('api/sso', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).status);
      check(refused === 401, 'a cookie the site does not know signs nobody in');
      // a page on another origin cannot sign in or register through this server
      for (const route of ['login', 'register', 'sso']) {
        const res = await fetch(url + 'api/' + route, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: 'https://evil.example' }, body: JSON.stringify({ username: 'Evil_One', password: 'hunter22x' }) });
        check(res.status === 403, `a request from another origin to /api/${route} is refused`);
      }
      // bodies must be JSON
      const plain = await fetch(url + 'api/login', { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: '{"username":"a","password":"b"}' });
      check(plain.status === 415, 'a non-JSON body is refused');

      },
    };
    await Promise.all(Object.entries(flows).map(([name, flow]) => flow().catch(error => { error.message = `[${name}] ${error.message}`; throw error; })));
    for (const p of pages) check(p.errors.length === 0, 'no page errors: ' + p.errors.join('; '));
    console.log(`account UI: ${checks} checks passed`);
  } finally {
    await browser.close().catch(() => {});
    if (server && server.exitCode === null) { const exited = new Promise(r => server.once('exit', r)); server.kill('SIGTERM'); await timeout(exited, 7000, 'shutdown').catch(() => server.kill('SIGKILL')); }
    fake?.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
})().catch(error => { console.error(error); console.error(logs.slice(-2000)); process.exit(1); });
