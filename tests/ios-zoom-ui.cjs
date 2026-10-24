// iOS Safari zoom guards: every text field is at least 16 px on a coarse pointer (Safari zooms the page on focus below that),
// the pinch gesture events are cancelled, and the viewport allows no scaling. MUTATE=1 serves HEAD's online.css and game.js, which must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-ios-zoom', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), ...process.env } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const page = await context.newPage();
  if (process.env.MUTATE) for (const f of ['online.css', 'game.js']) {
    const old = execFileSync('git', ['show', `HEAD:client/${f}`], { cwd: root, maxBuffer: 1 << 26 });
    await page.route(`**/${f}`, route => route.fulfill({ body: old, contentType: f.endsWith('.css') ? 'text/css' : 'text/javascript' }));
  }
  await page.goto(world.url);
  await page.waitForFunction(() => document.querySelector('#chat-input'));
  check(await page.evaluate(() => matchMedia('(pointer: coarse)').matches), 'the context has a coarse pointer');
  check(/maximum-scale=1\b/.test(await page.locator('meta[name=viewport]').getAttribute('content')), 'the viewport allows no scaling');
  const small = await page.evaluate(() => [...document.querySelectorAll('input, select, textarea')]
    .filter(n => !['range', 'checkbox', 'radio', 'button', 'submit', 'hidden'].includes(n.type))
    .map(n => ({ id: n.id || n.className || n.tagName, px: parseFloat(getComputedStyle(n).fontSize) })).filter(f => f.px < 16));
  check(small.length === 0, `fields under 16 px: ${JSON.stringify(small)}`);
  const total = await page.evaluate(() => document.querySelectorAll('input, select, textarea').length);
  check(total >= 10, `the page has its fields (${total})`);
  for (const ev of ['gesturestart', 'gesturechange', 'gestureend'])
    check(await page.evaluate(e => { const x = new Event(e, { cancelable: true, bubbles: true }); document.body.dispatchEvent(x); return x.defaultPrevented; }, ev), `${ev} is cancelled`);
  check(await page.evaluate(() => getComputedStyle(document.documentElement).touchAction === 'manipulation'), 'the root element allows only pan and pinch-free taps');
  console.log(`ios-zoom-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
