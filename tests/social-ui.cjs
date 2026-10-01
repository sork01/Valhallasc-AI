// Browser-only checks for the friends and party UI: panel, prompts, party frame, chat command, key handling and
// escaping. The rules (limits, leadership, persistence) are exercised through the social MCP scenario and Rust tests.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-ui-check', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' });
  await client.connect(transport);
  const world = await call('start_world', { levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const errors = [];
  async function player(name, cls = 'warrior') {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.on('pageerror', error => errors.push(`${name}: ${error.message}`));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
    await page.goto(world.url); await page.locator('#start').click();
    await page.locator('#cls-' + cls).click(); await page.locator('#name').fill(name);
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero && Field.hero.hp > 0, null, { timeout: 60000 });
    return page;
  }
  const alice = await player('Alice'), bobby = await player('Bobby', 'mage'), eve = await player('<u>Eve</u>', 'assassin');
  const rows = (page, list) => page.locator(`#social-body [data-list="${list}"] .social-row`);

  // The panel: O opens it, focus moves in, Escape closes it, and the game is paused while it is open.
  check(await alice.locator('#social-open').isVisible() && await alice.locator('#party-frame').isHidden(), 'The Social button shows and the party frame is hidden outside a party');
  await alice.keyboard.press('o');
  check(await alice.locator('#social-panel').isVisible(), 'O opens the social panel');
  check(await alice.locator('#social-tab-friends').evaluate(n => n === document.activeElement), 'The panel takes keyboard focus');
  check(await alice.evaluate(() => !Field.canAct), 'The world is paused while the panel is open');
  await alice.keyboard.press('q');
  check(await alice.locator('#quest-journal').isHidden(), 'Other panels cannot open on top of the social panel');
  await alice.keyboard.press('Escape');
  check(await alice.locator('#social-panel').isHidden() && await alice.locator('#pause').isHidden(), 'Escape closes only the social panel');
  check(await alice.evaluate(() => Field.canAct), 'The world resumes after closing');
  await alice.keyboard.press('q'); await alice.keyboard.press('o');
  check(await alice.locator('#quest-journal').isVisible() && await alice.locator('#social-panel').isHidden(), 'O does nothing while another panel is open');
  await alice.keyboard.press('Escape');

  // Friends: the request by name reaches the other browser as a prompt with Accept and Decline.
  await alice.keyboard.press('o');
  await alice.locator('#social-name').fill('nobody');
  await alice.locator('#social-add-friend').click();
  await alice.waitForFunction(() => document.getElementById('social-notice').textContent.includes('No player named nobody'));
  check(await alice.locator('#social-notice').getAttribute('data-ok') === 'false', 'A refusal shows in the panel as a refusal');
  await alice.locator('#social-name').fill('bobby');
  await alice.locator('#social-name').press('Enter');
  await bobby.locator('#social-invites .invite-card').waitFor({ state: 'visible', timeout: 10000 });
  check(await bobby.locator('#social-invites .invite-card').textContent().then(t => t.includes('Alice') && t.includes('friend request')), 'The prompt names the sender and the request');
  await alice.waitForFunction(() => document.getElementById('social-body').textContent.includes('Waiting for an answer from Bobby'), null, { timeout: 10000 });
  check(true, 'The sender sees the request is pending');
  check(/^\d+s$/.test(await bobby.locator('#social-invites .invite-left').textContent()), 'The prompt counts down the seconds left');
  await bobby.locator('#social-invites button', { hasText: 'Accept' }).click();
  await alice.waitForFunction(() => document.querySelector('#social-body [data-list="friends"] [data-friend]'));
  check(await rows(alice, 'friends').count() === 1 && await rows(alice, 'friends').first().textContent().then(t => t.includes('Bobby') && t.includes('Greenmeadow')), 'The new friend appears with their location');
  await bobby.locator('#social-invites .invite-card').waitFor({ state: 'detached', timeout: 10000 });
  check(await bobby.locator('#social-invites .invite-card').count() === 0, 'The answered prompt disappears');
  await bobby.keyboard.press('o');
  check(await rows(bobby, 'friends').first().textContent().then(t => t.includes('Alice')), 'The friendship is mutual');
  await bobby.keyboard.press('Escape');
  await alice.screenshot({ path: path.join(world.artifacts, 'social-friends.png') });

  // Party: invite from the Friends tab, accept from the prompt.
  await alice.locator('#social-body [data-friend] button', { hasText: 'Invite to party' }).click();
  await bobby.locator('#social-invites .invite-card').waitFor({ state: 'visible', timeout: 10000 });
  check(await bobby.locator('#social-invites .invite-card').textContent().then(t => t.includes('invited you to a party')), 'A party invite arrives as a prompt');
  await bobby.keyboard.press('p');
  check(await bobby.locator('#social-panel').isVisible() && await bobby.locator('#social-tab-party').getAttribute('aria-selected') === 'true', 'P opens the party tab');
  await bobby.locator('#social-body .invite button', { hasText: 'Accept' }).click();
  await bobby.waitForFunction(() => !document.getElementById('party-frame').hidden);
  await alice.waitForFunction(() => !document.getElementById('party-frame').hidden);
  await bobby.keyboard.press('Escape');
  check(await alice.locator('#party-frame .social-row').count() === 2, 'The party frame lists both members');
  check(await alice.locator('#party-frame .party-head').textContent().then(t => t.includes('Party 2/5')), 'The frame header counts the seats');
  check(await alice.locator('#party-frame [data-member] b').first().textContent().then(t => t.includes('★')), 'The leader is marked');
  check(await alice.locator('#party-frame .member-fill').first().evaluate(n => parseFloat(n.style.width)) > 99, 'A healthy member shows a full health bar');
  await alice.keyboard.press('Escape'); // closes the panel that is still open on the friends tab
  await alice.keyboard.press('p');
  check(await alice.locator('#social-body [data-list="party"] .social-row').count() === 2, 'The party tab lists the members');
  check(await alice.locator('#social-body button', { hasText: 'Make leader' }).count() === 1 && await alice.locator('#social-body button', { hasText: 'Remove' }).count() === 1, 'The leader gets promote and remove for the other member');
  await bobby.keyboard.press('p');
  check(await bobby.locator('#social-body button', { hasText: 'Make leader' }).count() === 0 && await bobby.locator('#social-body').textContent().then(t => t.includes('Only the leader can invite')), 'A member gets no leader controls');
  await bobby.keyboard.press('Escape');
  await alice.screenshot({ path: path.join(world.artifacts, 'social-party.png') });
  await alice.keyboard.press('Escape');

  // Party health arrives twice a second; it repaints the bars in place instead of rebuilding the rows.
  const row = bobby.locator('#party-frame [data-member]').first();
  await row.evaluate(n => { n.dataset.probe = 'same-node'; });
  await bobby.waitForTimeout(1300);
  const before = await bobby.locator('#party-frame [data-member] .member-bar em').first().textContent();
  check(/^\d+\/\d+$/.test(before), 'Health text shows current and maximum');
  check(await row.getAttribute('data-probe') === 'same-node', 'Health updates keep the same party rows');

  // Chat: /p reaches the party in its own colour; a stranger does not hear it.
  await alice.locator('#chat-input').fill('/p hello team');
  await alice.keyboard.press('Enter');
  await bobby.waitForFunction(() => [...document.querySelectorAll('#chat-log .chat-party')].some(p => p.textContent.includes('hello team')));
  check(await bobby.locator('#chat-log .chat-party').last().textContent().then(t => t === '[Party] Alice: hello team'), 'Party chat is labelled with the channel and sender');
  await eve.waitForTimeout(300);
  check(await eve.locator('#chat-log').textContent().then(t => !t.includes('hello team')), 'Party chat is not shown to someone outside the party');
  await alice.locator('#chat-input').fill('/p ');
  await alice.keyboard.press('Enter');
  check(await alice.locator('#chat-input').inputValue() === '', 'An empty party message is swallowed by the command, not sent as chat');
  await alice.waitForTimeout(1100); // the server allows one chat line per second, party or world
  await alice.locator('#chat-input').fill('/nonsense hi');
  await alice.keyboard.press('Enter');
  await eve.waitForFunction(() => document.getElementById('chat-log').textContent.includes('/nonsense hi'));
  check(await eve.locator('#chat-log p', { hasText: '/nonsense hi' }).count() === 1, 'An unknown slash command is ordinary chat');

  // Online tab: names are shown as text, never as markup; relationships are labelled.
  await alice.keyboard.press('o');
  await alice.locator('#social-tab-online').click();
  await alice.waitForFunction(() => document.querySelectorAll('#social-body [data-list="online"] .social-row').length === 3);
  check(await alice.locator('#social-body [data-list="online"]').textContent().then(t => t.includes('<u>Eve</u>')), 'A name with markup in it is displayed literally');
  check(await alice.locator('#social-body u').count() === 0, 'No element is created from a player\'s name');
  check(await alice.locator('#social-body [data-player]', { hasText: 'Bobby' }).textContent().then(t => t.includes('Friend') && t.includes('In your party')), 'The online list labels friends and party members');
  check(await alice.locator('#social-body [data-player]', { hasText: 'Eve' }).locator('button').allTextContents().then(t => t.join() === 'Add friend,Invite'), 'A stranger offers Add friend and Invite');
  await alice.locator('#social-body [data-player]', { hasText: 'Eve' }).locator('button', { hasText: 'Invite' }).click();
  await eve.locator('#social-invites .invite-card').waitFor({ state: 'visible', timeout: 10000 });
  check(await eve.locator('#social-invites .invite-card p').textContent().then(t => t.startsWith('Alice')), 'The invited stranger sees the prompt');
  await eve.locator('#social-invites button', { hasText: 'Decline' }).click();
  await eve.locator('#social-invites .invite-card').waitFor({ state: 'detached', timeout: 10000 });
  check(await eve.locator('#social-invites .invite-card').count() === 0, 'Declining removes the prompt');
  await alice.waitForFunction(() => document.getElementById('social-notice').textContent.includes('declined your party invite'), null, { timeout: 10000 });
  check(await alice.locator('#social-notice').getAttribute('data-ok') === 'false', 'The inviter is told the invite was declined');
  check(await alice.evaluate(() => Social.state.party.members.length === 2), 'A declined invite does not change the party');
  await alice.keyboard.press('Escape');

  // Leaving: the other member sees the party end; offline friends stay listed as offline.
  await bobby.keyboard.press('p');
  await bobby.locator('#social-body button', { hasText: 'Leave party' }).click();
  await bobby.waitForFunction(() => document.getElementById('party-frame').hidden);
  await alice.waitForFunction(() => document.getElementById('party-frame').hidden);
  check(true, 'Leaving a two-person party ends it for both');
  await bobby.keyboard.press('Escape');
  await bobby.close();
  await alice.keyboard.press('o');
  await alice.waitForFunction(() => document.querySelector('#social-body [data-friend][data-online="false"]'), null, { timeout: 10000 });
  check(await rows(alice, 'friends').first().textContent().then(t => t.includes('Bobby') && t.includes('Offline')), 'A friend who left is listed as offline');
  await alice.screenshot({ path: path.join(world.artifacts, 'social-offline.png') });
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} focused social UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
