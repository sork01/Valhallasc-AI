// Ordinary player activity is visible through the verified GM UI only, without server test flags.
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
(async () => {
  const dir = fs.mkdtempSync(path.join(root, 'test-results/activity-'));
  await startServer(await startFakeSso(), path.join(dir, 'test.sqlite'));
  browser = await chromium.launch({ headless: true });
  try {
    const other = await newPlayer(OTHER);
    await signIn(other); await other.locator('#chars-new').click();
    await other.locator('#cls-warrior').click(); await other.locator('#name').fill('Regular Visitor'); await other.locator('#go').click(); await connected(other);
    check(await other.locator('#activity-open').isHidden(), 'ordinary players have no Activity button');
    check(!await other.evaluate(() => GMActivity.open()), 'ordinary players cannot open the window');
    const denied = await other.evaluate(() => GM.request({op:'gm_activity',query:'',category:'',warnings:false}));
    check(denied.ok === false && !denied.result, 'forged request returns no activity data');
    await other.evaluate(() => Online.send({type:'unsupported_operation', secret:'NEVER_PERSIST_THIS_PAYLOAD'}));
    await other.context().close();
    const sork = await newPlayer(SORK); await signIn(sork); await sork.locator('#chars-gm').click(); await connected(sork);
    check(await sork.locator('#activity-open').isVisible(), 'GM has Activity button');
    await sork.locator('#activity-open').click();
    await sork.waitForFunction(() => document.querySelectorAll('#activity-rows tr').length > 0);
    check(await sork.locator('#activity-panel').isVisible(), 'GM window opens');
    check((await sork.locator('#activity-rows').innerText()).includes('Regular Visitor'), 'normal player is logged');
    await sork.locator('#activity-query').fill('Regular Visitor'); await sork.locator('#activity-filter').evaluate(form => form.requestSubmit());
    await sork.waitForFunction(() => [...document.querySelectorAll('#activity-rows tr')].every(tr => tr.cells[1].textContent === 'Regular Visitor'));
    check(await sork.locator('#activity-rows tr[data-category="login"]').count() === 1, 'normal login captured');
    check(await sork.locator('#activity-rows tr[data-category="logout"]').count() === 1, 'normal logout captured');
    check((await sork.locator('#activity-rows').innerText()).includes('Unauthorized GM command attempt'), 'unauthorized request logged');
    check((await sork.locator('#activity-rows').innerText()).includes('Malformed or unsupported command rejected'), 'bad protocol logged');
    check(!(await sork.locator('#activity-rows').innerText()).includes('NEVER_PERSIST'), 'raw payload never appears');
    await sork.locator('#activity-warnings').check();
    await sork.waitForFunction(() => [...document.querySelectorAll('#activity-rows tr')].every(tr => tr.dataset.warning === 'true'));
    check(await sork.locator('#activity-rows tr').count() === 2, 'warning filter only shows suspicious/refused events');
    await sork.locator('#activity-warnings').uncheck(); await sork.locator('#activity-category').selectOption('login');
    await sork.waitForFunction(() => document.querySelectorAll('#activity-rows tr').length === 1 && document.querySelector('#activity-rows tr').dataset.category === 'login');
    check(true, 'category filter works');
    await sork.locator('#activity-query').fill('NobodyMatchesThis'); await sork.locator('#activity-filter').evaluate(form => form.requestSubmit());
    await sork.waitForFunction(() => document.querySelector('#activity-status').textContent === 'No activity yet.');
    check(await sork.locator('#activity-rows tr').count() === 0, 'empty search is clear');
    await sork.locator('#activity-query').fill(''); await sork.locator('#activity-category').selectOption('');
    await sork.waitForFunction(() => document.querySelectorAll('#activity-rows tr').length >= 5);
    await sork.screenshot({path:path.join(dir,'activity-desktop.png')});
    await sork.keyboard.press('Escape'); check(await sork.locator('#activity-panel').isHidden(), 'Escape closes activity');
    await sork.setViewportSize({width:844,height:390}); await sork.locator('#activity-open').click();
    const box=await sork.locator('.activity-window').boundingBox();
    check(box.x >= 0 && box.y >= 0 && box.x+box.width <= 845 && box.y+box.height <= 391, 'window fits short viewport');
    await sork.screenshot({path:path.join(dir,'activity-short.png')});
    check(sork.errors.length===0, 'no browser errors: '+JSON.stringify(sork.errors));
    await sork.evaluate(() => GM.onSelf(null));
    check(await sork.locator('#activity-panel').isHidden() && await sork.locator('#activity-rows tr').count() === 0, 'losing the GM character clears the visible log');
    await sork.context().close();
    console.log(JSON.stringify({passed:true,checks,artifacts:dir}));
  } finally { await browser?.close(); server?.kill(); fake?.close(); }
})().catch(error => { console.error(error); console.error(logs.slice(-2000)); server?.kill(); fake?.close(); process.exit(1); });
