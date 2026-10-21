// Browser check of the raid group UI (RAID-PARTY): a leader in a real client turns a full party of five into a raid of
// ten, fills it, sees the compact ten-row frame inside the stage (desktop and 390x844), is refused an eleventh, and turns it
// back once five are left. The rules themselves (caps, loot, the raid door, contracts) are Rust tests in social.rs/rolls.rs.
// MUTATE=1 serves the committed social.js (no raid support): the run must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-raid-party-check', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...process.env } }); // the child would otherwise drop VALHALLA_BINARY
  await client.connect(transport);
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  const names = Array.from({ length: 10 }, (_, i) => `Raid${i + 1}`);
  for (const bot of names) await call('connect_bot', { bot, class: 'warrior' });
  browser = await chromium.launch({ headless: true });
  const errors = [];
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', error => errors.push(error.message));
  if (process.env.MUTATE) {
    const old = execFileSync('git', ['show', 'HEAD:client/social.js'], { cwd: root, encoding: 'utf8' });
    await page.route('**/social.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Lead');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero && Field.hero.hp > 0, null, { timeout: 60000 });
  const leaderId = await page.evaluate(() => Online.id);

  // Invite by name from the panel, then let the bot accept.
  await page.keyboard.press('p');
  async function invite(name) {
    await page.locator('#social-name').fill(name);
    await page.locator('#social-add-party').click();
    await page.waitForFunction(n => Social.state.outgoing.some(i => i.name === n), name, { timeout: 10000 });
    await call('social', { bot: name, command: { op: 'party_accept', id: leaderId } });
    await page.waitForFunction(n => Social.state.party?.members.some(m => m.name === n), name, { timeout: 10000 });
  }
  const frameOf = () => page.locator('#party-frame');
  const head = () => page.locator('#party-frame .party-head').textContent();
  for (const bot of names.slice(0, 4)) await invite(bot);
  check((await head()).includes('Party 5/5'), 'Five members fill a party');
  check(await page.locator('#social-body [data-key="raid"]').textContent() === 'Make a raid of 10', 'The leader is offered a raid');

  // A sixth is refused while it is a party.
  await page.locator('#social-name').fill(names[4]);
  await page.locator('#social-add-party').click();
  await page.waitForFunction(() => document.getElementById('social-notice').textContent.includes('Your party is full (5/5)'), null, { timeout: 10000 });
  check(true, 'A sixth invite is refused: party is full (5/5)');

  // Make the raid: the header and the button change, and the seats open.
  await page.locator('#social-body [data-key="raid"]').click();
  await page.waitForFunction(() => document.querySelector('#party-frame .party-head')?.textContent.includes('Raid 5/10'), null, { timeout: 10000 });
  check(await page.locator('#social-body [data-key="raid"]').textContent() === 'Back to a party of 5', 'The raid button turns into the way back');
  check(await page.locator('#social-tab-party').textContent().then(t => t.includes('Raid 5/10')), 'The tab names the raid');
  for (const bot of names.slice(4, 9)) await invite(bot);
  check((await head()).includes('Raid 10/10'), 'Ten members fill the raid');
  check(await page.locator('#social-body [data-key="raid"]').isDisabled(), 'Back to a party is disabled while more than five are in');

  // An eleventh is refused.
  await page.locator('#social-name').fill(names[9]);
  await page.locator('#social-add-party').click();
  await page.waitForFunction(() => document.getElementById('social-notice').textContent.includes('Your raid is full (10/10)'), null, { timeout: 10000 });
  check(true, 'An eleventh invite is refused: raid is full (10/10)');
  await page.keyboard.press('Escape');

  // The frame: ten one-line rows in one column, every one inside the stage, at desktop and phone size.
  async function frameFits(label) {
    const m = await page.evaluate(() => {
      const stage = document.getElementById('stage').getBoundingClientRect();
      const rows = [...document.querySelectorAll('#party-frame .social-row')].map(r => r.getBoundingClientRect());
      return {
        stage: { l: stage.left, t: stage.top, r: stage.right, b: stage.bottom },
        compact: document.getElementById('party-frame').dataset.compact,
        lefts: [...new Set(rows.map(r => Math.round(r.left)))].length,
        count: rows.length,
        inside: rows.every(r => r.width > 0 && r.height > 0 && r.left >= stage.left - 1 && r.right <= stage.right + 1 && r.top >= stage.top - 1 && r.bottom <= stage.bottom + 1),
      };
    });
    check(m.count === 10 && m.compact === '1', `${label}: ten compact rows`);
    check(m.lefts === 1, `${label}: the rows sit in one column (${m.lefts} distinct lefts)`);
    check(m.inside, `${label}: every row is inside the stage`);
  }
  await frameFits('Desktop');
  await page.screenshot({ path: path.join(world.artifacts, 'raid-frame-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  await frameFits('Phone');
  await page.screenshot({ path: path.join(world.artifacts, 'raid-frame-phone.png') });
  await page.setViewportSize({ width: 1440, height: 900 });

  // Back: five leave, then the leader turns the raid into a party again.
  for (const bot of names.slice(4, 9)) await call('social', { bot, command: { op: 'party_leave' } });
  await page.waitForFunction(() => Social.state.party?.members.length === 5, null, { timeout: 10000 });
  await page.keyboard.press('p');
  check(await page.locator('#social-body [data-key="raid"]').isEnabled(), 'With five left the way back is open');
  await page.locator('#social-body [data-key="raid"]').click();
  await page.waitForFunction(() => document.querySelector('#party-frame .party-head')?.textContent.includes('Party 5/5'), null, { timeout: 10000 });
  check(await frameOf().getAttribute('data-compact') === '0', 'Back to a party: full-size rows again');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} raid party UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
