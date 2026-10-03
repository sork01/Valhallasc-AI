// The chat window's System tab and the speech bubbles, in a real browser against a private server. Debug commands only stage the
// fight (spawn a slime next to the hero); every damage line comes from the server's own combat events.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-syslog-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
async function join(world, name) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.warriorSprites, null, { timeout: 60000 });
  return page;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world', { godMode: false }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await join(world, 'Fighter'), other = await join(world, 'Bystander');
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const system = () => page.locator('#system-log').innerText();

  // --- tabs ---
  check(await page.locator('#tab-chat').getAttribute('aria-selected') === 'true' && await page.locator('#system-log').isHidden(), 'The chat window opens on the Chat tab');
  check(await page.locator('#chat-log').isVisible(), 'The Chat log is visible at first');
  await page.locator('#tab-system').click();
  check(await page.locator('#system-log').isVisible() && await page.locator('#chat-log').isHidden(), 'The System tab swaps the log');
  check(await page.locator('#tab-system').getAttribute('aria-selected') === 'true' && await page.locator('#tab-chat').getAttribute('aria-selected') === 'false', 'The selected tab is marked');
  check((await system()).includes('Welcome to Greenmeadow'), 'Game notices are on the System tab');
  await page.locator('#tab-chat').click();

  // --- unread dot ---
  await page.evaluate(() => SystemLog.add('probe line', 'sys-note'));
  check(await page.locator('#tab-system').evaluate(n => n.classList.contains('unread')), 'A line on the hidden System tab marks it unread');
  await page.locator('#tab-system').click();
  check(await page.locator('#tab-system').evaluate(n => !n.classList.contains('unread')), 'Opening the tab clears the mark');

  // --- a real fight: damage dealt, damage taken, the kill ---
  const here = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await debug({ op: 'spawn_enemy', kind: 'green', x: here.x + 1.4, y: here.y, level: 1 });
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 3));
  await page.waitForFunction(() => /Green Slime \(Lv 1\) hits you for \d+\./.test(document.getElementById('system-log').textContent), null, { timeout: 20000 });
  check(true, 'Damage taken names the enemy, its level and the amount');
  check(await page.locator('#system-log .sys-taken').count() > 0, 'Damage taken has its own colour class');
  await page.evaluate(() => { const s = Field.slimes.find(s => s.kind === 'green' && !s.dead); window.__slimeId = s.id; });
  for (let i = 0; i < 40; i++) {
    if (/was defeated/.test(await system())) break;
    await page.evaluate(() => { const s = Field.slimes.find(s => s.id === window.__slimeId); if (s && !s.dead) { Online.send({ type: 'target', id: s.id }); Online.send({ type: 'attack', fx: s.x - Field.hero.x, fy: s.y - Field.hero.y }); } });
    await page.waitForTimeout(450);
  }
  const text = await system();
  check(/You hit Green Slime \(Lv 1\) for \d+ with a basic attack\./.test(text), 'Damage dealt names the target, the amount and the attack');
  check(/Green Slime \(Lv 1\) was defeated\. \+\d+ XP\./.test(text), 'A kill reports the enemy and the XP');
  check(await page.locator('#system-log .sys-dealt, #system-log .sys-crit').count() > 0, 'Damage dealt has its own colour class');

  // --- a skill names itself in the damage line ---
  await debug({ op: 'set_level', level: 5 });
  await page.waitForFunction(() => Field.hero.level === 5);
  await debug({ op: 'reset_cooldowns' }); await debug({ op: 'set_resource', amount: 1e9 });
  const at = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
  await debug({ op: 'spawn_enemy', kind: 'blue', x: at.x + 1.2, y: at.y, level: 1 });
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'blue' && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 3));
  const skill = await page.evaluate(() => WORLD_SKILLS.find(s => s.id === 'cleave'));
  await page.evaluate(id => { const s = Field.slimes.find(s => s.kind === 'blue' && !s.dead); Online.send({ type: 'skill', id, fx: s.x - Field.hero.x, fy: s.y - Field.hero.y }); }, skill.id);
  await page.waitForFunction(name => new RegExp(`You hit Blue Slime \\(Lv 1\\) for \\d+ .*with ${name}\\.`).test(document.getElementById('system-log').textContent), skill.name, { timeout: 8000 });
  check(true, `A skill hit says which skill landed (${skill.name})`);
  await page.waitForFunction(name => document.getElementById('system-log').textContent.includes(`You cast ${name}.`), skill.name, { timeout: 5000 });
  check(true, 'Casting a skill is logged');

  // --- chat stays on the Chat tab, and focusing the input returns to it ---
  await page.keyboard.press('Enter');
  check(await page.locator('#chat-log').isVisible(), 'Pressing Enter to chat switches back to the Chat tab');
  await page.locator('#chat-input').fill('hello <b>world</b> from the fighter');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.getElementById('chat-log').textContent.includes('hello <b>world</b>'));
  check(!(await system()).includes('from the fighter'), 'Player chat is not repeated on the System tab');

  // --- speech bubble: shown over the speaker for the speaker, and for a bystander in view ---
  check(await page.evaluate(() => Field.bubbleText(Online.id)) === 'hello <b>world</b> from the fighter', 'The speaker has a bubble with the literal text');
  await other.evaluate(() => Field.hero.goal = null);
  const seen = await other.waitForFunction(() => Field.remotePlayers.length === 1 && Field.bubbleText(Field.remotePlayers[0].id), null, { timeout: 8000 }).then(h => h.jsonValue());
  check(seen === 'hello <b>world</b> from the fighter', 'A bystander sees the bubble over the speaker');
  const pixels = async p => p.evaluate(() => Field.bubbleDrawn());
  check(await pixels(page) > 0, 'The bubble is drawn on the canvas for the speaker');
  check(await pixels(other) > 0, 'The bubble is drawn on the canvas for the bystander');
  if (process.env.SHOT) { await page.locator('#tab-system').click(); await page.screenshot({ path: process.env.SHOT }); }
  await page.waitForFunction(() => !Field.bubbleText(Online.id), null, { timeout: 15000 });
  check(true, 'The bubble goes away after a few seconds');
  // a long message wraps into at most four lines and stays inside the screen
  await page.evaluate(() => Field.bubble(Online.id, 'word '.repeat(120)));
  await page.waitForTimeout(300);
  const box = await page.evaluate(() => Field.bubbleBox(Online.id));
  check(box && box.lines <= 4 && box.l >= 0 && box.r <= 1600, `A long message is cut to four lines inside the screen (${JSON.stringify(box)})`);

  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} syslog UI checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); });
