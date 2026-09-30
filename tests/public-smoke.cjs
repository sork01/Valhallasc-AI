// Verify the deployed HTTPS client and real WSS multiplayer route.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const url = process.env.VALHALLA_PUBLIC_URL || 'https://gunning.se/Valhallasc/';
const root = path.resolve(__dirname, '..');
const result = { url, ids: [], checks: 0 };
let browser;
function check(value, message) { assert.ok(value, message); result.checks++; }
async function player(type, name) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await context.addInitScript(() => {
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ sound: false, lang: 'en', char: null, draft: null }));
  });
  const page = await context.newPage(); page.errors = []; page.sockets = [];
  page.on('pageerror', error => page.errors.push(error.message));
  page.on('websocket', socket => page.sockets.push(socket.url()));
  await page.goto(url);
  await page.locator('#start').click(); await page.locator('#cls-' + type).click();
  await page.locator('#name').fill(name); await page.locator('#go').click();
  await page.waitForFunction(() => Online.connected && !!(Field.warriorSprites || Field.mageSprites), null, { timeout: 60000 });
  result.ids.push(await page.evaluate(() => Online.id));
  return page;
}
(async () => {
  fs.mkdirSync(path.join(root, 'test-results'), { recursive: true });
  const response = await fetch(url); check(response.ok, 'Public client returns 200 over valid HTTPS');
  check((await response.text()).includes('online.js'), 'Public page is multiplayer client');
  const health = await (await fetch(new URL('health', url))).json(); check(health.status === 'ok', 'Public health reaches Rust');
  check((await fetch(url.replace(/\/$/, ''), { redirect: 'manual' })).status === 302, 'Missing slash redirects');
  const alias = await fetch(url.replace('gunning.se', 'www.gunning.se'), { redirect: 'manual' });
  check(alias.status === 302 && alias.headers.get('location') === url, 'www alias redirects to canonical origin');
  for (const file of ['server/src/main.rs', 'data/valhalla.sqlite', 'deploy/apache.conf', 'AGENTS.md', '.git/config']) {
    check((await fetch(new URL(file, url))).status >= 400, 'Workspace files are private: ' + file);
  }
  browser = await chromium.launch({ headless: true });
  const warrior = await player('warrior', 'HTTPS Warrior');
  const mage = await player('mage', 'HTTPS Mage');
  await warrior.waitForFunction(id => Field.remotePlayers.some(p => p.id === id && p.sprite), result.ids[1], { timeout: 60000 });
  check(warrior.sockets.includes('wss://gunning.se/Valhallasc/ws'), 'Browser uses secure public game WebSocket');
  check(await warrior.locator('#connection-overlay').isHidden(), 'Connection completes without overlay');
  const message = 'Hello from the public HTTPS client!';
  await warrior.locator('#chat-input').fill(message); await warrior.locator('#chat-input').press('Enter');
  await mage.waitForFunction(text => document.getElementById('chat-log').textContent.includes(text), message); result.checks++;
  const start = await warrior.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await warrior.keyboard.down('d'); await warrior.waitForTimeout(400); await warrior.keyboard.up('d');
  await warrior.waitForTimeout(400);
  const moved = await warrior.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  check(Math.hypot(moved.x - start.x, moved.y - start.y) > .5, 'Public client movement reaches Rust');
  await mage.waitForFunction(({ id, x, y }) => {
    const remote = Field.remotePlayers.find(p => p.id === id);
    return remote && Math.hypot(remote.x - x, remote.y - y) < .3;
  }, { id: result.ids[0], ...moved }); result.checks++;
  await warrior.reload(); await warrior.locator('#start').click();
  await warrior.waitForFunction(id => Online.connected && Online.id === id, result.ids[0], { timeout: 20000 }); result.checks++;
  check(warrior.errors.length === 0 && mage.errors.length === 0, 'No client runtime errors: ' + warrior.errors.concat(mage.errors).join('; '));
  await warrior.screenshot({ path: path.join(root, 'test-results/public-client.png') });
  console.log(`${result.checks} public HTTPS/WSS checks passed at ${url}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  // IDs only; keys never go into logs/artifacts. Remove these specific guest
  // records after the server has saved the browser disconnects.
  fs.writeFileSync(path.join(root, 'test-results/public-smoke-results.json'), JSON.stringify(result, null, 2));
});
