// The game master's administrator character in a real browser. The site SSO is a fake endpoint run by this test: one
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
  const dir = fs.mkdtempSync(path.join(root, 'test-results/gm-'));
  const ssoUrl = await startFakeSso();
  await startServer(ssoUrl, path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  const pages = [];
  try {
    // ---- the game master ----
    const sork = await newPlayer(SORK); pages.push(sork);
    await signIn(sork);
    check((await sork.locator('#chars-who').textContent()).includes('Sork (gunning.se)') && (await sork.locator('#chars-who').textContent()).includes('0 of 5'), 'Sork is signed in with no characters');
    check(await sork.locator('#chars-gm').isVisible(), 'the game master is offered the [GM] slot');
    check(await sork.locator('#chars-new').isEnabled(), 'the five ordinary slots are untouched');
    await sork.locator('#chars-gm').click();
    await connected(sork);
    check(await sork.evaluate(() => Online.gm === true), 'the server says this is the administrator character');
    const look = await sork.evaluate(() => Field.hero.look);
    check(look.name === '[GM]Sork' && look.class === 'warrior' && look.gender === 'male', 'the character is [GM]Sork, a male Warrior');
    check(look.warriorArmor === 'gm' && look.warriorWeapon === 'gm' && look.head === 'gm', 'it wears the golden robe, sword and shield and the golden top hat');
    const sprite = await sork.evaluate(() => { const S = WarriorSprite; const s = new S({ meta: { frame: [8, 8], anchor: [4, 8], clips: {}, parts: {}, ramps: { hair: ['#111111', '#222222', '#333333', '#444444'], brow: ['#111111', '#222222', '#333333', '#444444'], skin: ['#111111', '#222222', '#333333', '#444444'] } }, parts: {} }, { warriorArmor: 'gm', warriorWeapon: 'gm', head: 'gm' }); return { armor: s.equipment.armor, weapon: s.equipment.weapon, head: s.equipment.head }; });
    check(sprite.armor === 'gm' && sprite.weapon === 'gm' && sprite.head === 'gm', 'the warrior sprite accepts all three golden pieces');

    // help, then a command a typo cannot send
    await type(sork, '/gm');
    await sork.waitForFunction(() => /Game master commands/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check((await chatLog(sork)).includes('/tp'), '/gm lists the commands');
    const listed = async word => { await sork.evaluate(() => { document.getElementById('chat-log').textContent = ''; }); await type(sork, word); await sork.waitForFunction(() => /Game master commands/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 }); return chatLog(sork); };
    check((await listed('/gmcommands')).includes('/tp'), '/gmcommands lists the commands too');
    // Enter opens the chat box even when a button kept the focus after a mouse click
    await sork.evaluate(() => document.getElementById('chat-input').blur());
    await sork.locator('#chat-form button').focus();
    await sork.keyboard.press('Enter');
    check(await sork.evaluate(() => document.activeElement?.id === 'chat-input'), 'Enter puts the cursor in the chat box even after a button was focused');
    await sork.keyboard.press('Escape');
    await type(sork, '/give');
    await sork.waitForFunction(() => /Name an item/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check(true, 'a malformed command is explained, not sent');

    // level, gold, items, teleport, god mode: each changes the real character and answers in the log
    await type(sork, '/level 20');
    await sork.waitForFunction(() => /level 20/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/gold 12345');
    await sork.waitForFunction(() => /12345 gold/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/give health potion 3');
    await sork.waitForFunction(() => /health_potion: you now have 3/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/give royal sword');
    await sork.waitForFunction(() => /warrior_weapon_royal: you now have 1/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/tp crags');
    await sork.waitForFunction(() => /now in Emberfall Crags/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await sork.waitForFunction(() => Field.zone === 1 || document.getElementById('network-status').textContent.includes('Emberfall'), null, { timeout: 8000 });
    check(true, 'give, level, gold and teleport all answered, and the zone changed');
    await type(sork, '/tp 40 40');
    await sork.waitForFunction(() => (document.getElementById('chat-log').textContent.match(/now in Emberfall Crags at/g) || []).length >= 2, null, { timeout: 5000 });
    await type(sork, '/tp city');
    await sork.waitForFunction(() => /now in Greenmeadow/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/god');
    await sork.waitForFunction(() => /god mode ON \(only you\)/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/god off');
    await sork.waitForFunction(() => /god mode off/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/spawn green 3');
    await sork.waitForFunction(() => /\(green, level 3\)/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/give nonsense_item_zz');
    await sork.waitForFunction(() => /No item matches/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    await type(sork, '/goto nobodyhere');
    await sork.waitForFunction(() => /No player named nobodyhere is online/.test(document.getElementById('chat-log').textContent), null, { timeout: 5000 });
    check(true, 'god mode, spawn, a bad item name and an unknown player all answer');
    check(sork.errors.length === 0, 'no page errors for the game master: ' + sork.errors.join('; '));
    check(/game master command/.test(logs), 'the server logged the game master commands');

    // back to the list: the GM row is there, the slot button is gone, ordinary slots still free
    await sork.evaluate(() => document.getElementById('p-menu')?.click());
    await sork.keyboard.press('Escape');
    await sork.reload(); await sork.locator('#start').click(); await sork.locator('#login-continue').click();
    await sork.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
    check(await sork.locator('.char-row.gm').count() === 1 && (await sork.locator('.char-row.gm').textContent()).includes('[GM]Sork'), 'the [GM] character is listed, in gold');
    check(await sork.locator('#chars-gm').isHidden(), 'only one administrator character is offered');
    check((await sork.locator('#chars-who').textContent()).includes('0 of 5') && (await sork.locator('#chars-who').textContent()).includes('[GM]'), 'it does not use one of the five ordinary slots');
    check(await sork.locator('#chars-new').isEnabled(), 'New character is still available');
    await sork.locator('.char-row.gm .char-play').click(); await connected(sork);
    check(await sork.evaluate(() => Online.gm === true && Field.hero.look.warriorArmor === 'gm'), 'the character comes back as the administrator, still golden');

    // ---- everyone else ----
    const other = await newPlayer(OTHER); pages.push(other);
    await signIn(other);
    check(await other.locator('#chars-gm').isHidden(), 'another login is not offered the [GM] slot');
    await other.locator('#chars-new').click(); await other.locator('#cls-warrior').click(); await other.locator('#name').fill('[GM]Fake'); await other.locator('#go').click();
    await other.waitForFunction(() => /reserved/i.test(document.getElementById('connection-text')?.textContent || '') || Online.connected, null, { timeout: 15000 });
    check(!(await other.evaluate(() => Online.connected)), 'a [GM] name is refused for an ordinary player');
    await other.reload(); await other.locator('#start').click(); await other.locator('#login-continue').click(); await other.locator('#chars-title').waitFor({ state: 'visible', timeout: 10000 });
    check((await other.locator('#chars-who').textContent()).includes('0 of 5'), 'the refused [GM] name created nothing');
    await other.locator('#chars-new').click(); await other.locator('#cls-warrior').click(); await other.locator('#name').fill('Plainhero'); await other.locator('#go').click();
    await connected(other);
    check(await other.evaluate(() => Online.gm === false), 'an ordinary character is not a game master');
    await type(other, '/level 20');
    await other.waitForTimeout(600);
    check(!(await chatLog(other)).includes('Game master') && /\/level 20/.test(await chatLog(other)), 'slash text from an ordinary player is plain chat');
    const reply = await other.evaluate(() => new Promise(resolve => {
      const timer = setTimeout(() => resolve(null), 3000);
      GM.onReply = packet => { clearTimeout(timer); resolve(packet); };
      Online.send({ type: 'debug', ref: 99, command: { op: 'set_level', level: 50 } });
    }));
    check(reply === null || reply.ok === false, 'a hand-made debug message is refused for an ordinary player');
    const level = await other.evaluate(() => Field.hero.level);
    check(level === 1, 'and the level did not move');
    check(other.errors.length === 0, 'no page errors for the other player: ' + other.errors.join('; '));
    console.log(`gm-ui: ${checks} checks passed`);
  } finally {
    for (const page of pages) await page.context().close().catch(() => {});
    await browser.close().catch(() => {});
    server?.kill(); fake?.close();
  }
})().catch(error => { console.error(error); console.error(logs.slice(-2500)); process.exit(1); });
