// Key map (UI-KEYMAP) in a real browser. Rebind keys on the Keyboard screen (Settings), then play with them: the old key does nothing, the
// new key works, hints and tooltips read the new key, a taken key is swapped, typing in chat triggers nothing, and everything is still
// there after a reload. Client-only. MUTATE=1 serves a keymap.js whose labels ignore the player's choices, MUTATE=2 one whose handlers
// do (the Keyboard screen and labels still work): both runs must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-keymap', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [];
const visible = (page, selector) => page.locator(selector).isVisible();
const pos = page => page.evaluate(() => ({ x: Field.hero.nx ?? Field.hero.x, y: Field.hero.ny ?? Field.hero.y }));
const moved = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
async function hold(page, key, ms) {
  const before = await pos(page);
  await page.keyboard.down(key); await page.waitForTimeout(ms); await page.keyboard.up(key); await page.waitForTimeout(350);
  return moved(before, await pos(page));
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE) await page.route('**/keymap.js', async route => {
    const src = fs.readFileSync(path.join(root, 'client/keymap.js'), 'utf8');
    const body = process.env.MUTATE === '2' ? src.replace('return bindings(action).includes(codeOf(event));', 'return DEFAULTS[action].includes(codeOf(event));') : src.replace('const list = Array.isArray(own) ? own.filter', 'const list = false ? own.filter');
    assert.notEqual(body, src, 'the mutation applied');
    await route.fulfill({ body, contentType: 'text/javascript' });
  });
  await page.addInitScript(() => { if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); } });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Keyer'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });

  // --- the shipped keys read and work exactly as before ---
  const shipped = await page.evaluate(() => ({ bags: Keys.label('bags'), quests: Keys.label('quests'), first: document.querySelector('#skillbar-slots .skill-slot kbd').textContent, eleven: document.querySelectorAll('#skillbar-slots .skill-slot kbd')[10].textContent, food: document.querySelector('#quickuse kbd').textContent, skills: document.querySelector('#skills-open kbd').textContent, sound: document.querySelector('#set-sound-row kbd').textContent, bagsAria: document.getElementById('inventory-open').getAttribute('aria-label'), tracker: document.querySelector('.tracker-journal')?.textContent }));
  check(shipped.bags === 'B / I' && shipped.quests === 'Q' && shipped.first === '1' && shipped.eleven === '-' && shipped.food === 'Z' && shipped.skills === 'K' && shipped.sound === 'M / N', `Shipped labels are unchanged: ${JSON.stringify(shipped)}`);
  check(shipped.bagsAria === 'Open bags (B or I)', 'The static hints keep their shipped text until a key is changed');
  await page.keyboard.press('q');
  check(await visible(page, '#quest-journal'), 'Q opens the quest journal');
  await page.keyboard.press('Escape');
  check(!(await visible(page, '#quest-journal')), 'Esc closes it');

  // --- rebind on the Keyboard screen ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#set-keys').click();
  check(await visible(page, '#keys-panel') && !(await visible(page, '#settings-panel')), 'The Keyboard screen opens from Settings');
  // a short phone screen: the panel fits, the last row scrolls into view and takes a click
  await page.setViewportSize({ width: 844, height: 390 });
  await page.locator('.key-row').last().scrollIntoViewIfNeeded();
  const small = await page.evaluate(() => { const p = document.querySelector('.keys-panel').getBoundingClientRect(), l = document.querySelector('.key-row:last-child').getBoundingClientRect(), hit = document.elementFromPoint(p.left + p.width / 2, p.top + p.height / 2); return { top: p.top, bottom: p.bottom, lastIn: l.top >= p.top - 1 && l.bottom <= p.bottom + 1, hits: !!hit?.closest('.keys-panel') }; });
  check(small.top >= 0 && small.bottom <= 390 && small.lastIn && small.hits, `At 844x390 the Keyboard panel fits and its last row is reachable: ${JSON.stringify(small)}`);
  await page.locator('.key-row').last().locator('.key-cell').first().click();
  check(await page.locator('.key-row').last().locator('.key-cell').first().textContent() === 'Press a key…', 'The last row takes a click');
  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 1440, height: 900 });
  const rows = await page.locator('.key-row').count(), actions = await page.evaluate(() => Keys.ACTIONS.length);
  check(rows === actions && actions >= 30, `One row per action (${rows} of ${actions})`);
  const cell = (action, slot) => page.locator(`#key-${action}-${slot}`);
  const say = () => page.locator('#keys-message').textContent();
  check(await cell('quests', 0).textContent() === 'Q' && await cell('bags', 1).textContent() === 'I' && await cell('attack', 0).textContent() === 'Space', 'The boxes show the shipped keys');
  await cell('quests', 0).click();
  check(await cell('quests', 0).textContent() === 'Press a key…', 'A click starts the capture');
  await page.keyboard.press('g');
  check(await cell('quests', 0).textContent() === 'G' && /Quests is now G/.test(await say()), `Quests is now G (${await say()})`);
  await cell('bags', 0).click(); await page.keyboard.press('u');
  check(await cell('bags', 0).textContent() === 'U', 'Bags: first key is now U');
  await cell('moveLeft', 0).click(); await page.keyboard.press('r');
  check(await cell('moveLeft', 0).textContent() === 'R', 'Move left is now R');
  await cell('skills', 0).click(); await page.keyboard.press('y');
  await cell('skill1', 0).click(); await page.keyboard.press('v');
  check(await page.evaluate(() => Keys.label('skills') === 'Y' && Keys.label('skill1') === 'V'), 'Skills is Y and slot 1 is V');

  // a key another action uses moves to the new one, and the old holder gets the key this slot had
  await cell('party', 0).click(); await page.keyboard.press('u');
  check(/U moved from Bags to Party/.test(await say()), `A taken key is swapped (${await say()})`);
  const swapped = await page.evaluate(() => ({ bags: Keys.slots('bags'), party: Keys.slots('party') }));
  check(swapped.party[0] === 'KeyU' && swapped.bags[0] === 'KeyP' && swapped.bags[1] === 'KeyI', `Bags took Party's old key: ${JSON.stringify(swapped)}`);
  const dupes = await page.evaluate(() => { const seen = new Map(), twice = []; for (const a of Keys.ACTIONS) for (const c of Keys.slots(a[1])) if (c) { if (seen.has(c) && !(c === 'KeyM' && [seen.get(c), a[1]].every(x => x === 'map' || x === 'sound'))) twice.push(c); seen.set(c, a[1]); } return twice; });
  check(dupes.length === 0, `No key belongs to two actions (${dupes.join()})`);
  // Esc cancels and Backspace clears; neither can be bound by accident
  await cell('friends', 1).click(); await page.keyboard.press('Escape');
  check(await visible(page, '#keys-panel') && await cell('friends', 1).textContent() === '—', 'Esc cancels the capture and leaves the Keyboard screen open');
  await cell('friends', 1).click(); await page.keyboard.press('l');
  check(await page.locator('[data-action=friends] .key-reset').isEnabled(), 'A changed row can be reset');
  await page.locator('[data-action=friends] .key-reset').click();
  check(await page.locator('[data-action=friends] .key-reset').isDisabled() && await cell('friends', 0).textContent() === 'O' && await cell('friends', 1).textContent() === '—', 'Reset puts the row back to its shipped keys');
  await cell('quests', 1).click(); await page.keyboard.press('Tab');
  check(/cannot be used/.test(await say()), 'Tab is refused');
  await page.locator('#keys-back').click();
  check(await visible(page, '#settings-panel'), 'Back returns to Settings');
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();

  // --- play with them ---
  await page.keyboard.press('q');
  check(!(await visible(page, '#quest-journal')), 'The old quest key does nothing');
  await page.keyboard.press('g');
  check(await visible(page, '#quest-journal'), 'The new quest key opens the journal');
  await page.keyboard.press('g');
  check(!(await visible(page, '#quest-journal')), 'It closes with the same key');
  await page.locator('#chat-input').focus(); await page.keyboard.type('g');
  check(!(await visible(page, '#quest-journal')) && await page.locator('#chat-input').inputValue() === 'g', 'Typing in the chat box triggers nothing');
  await page.locator('#chat-input').fill(''); await page.locator('#chat-input').blur();
  await page.keyboard.press('u');
  check(await visible(page, '#social-panel'), 'The party key (U) opens the social panel');
  await page.keyboard.press('Escape');
  await page.keyboard.press('p');
  check(await visible(page, '#equipment'), 'Bags took the old party key (P)');
  await page.keyboard.press('Escape');
  await page.keyboard.press('y');
  check(await visible(page, '#skills-panel'), 'The skills key (Y) opens the skills panel');
  await page.keyboard.press('Escape');
  check(await hold(page, 'a', 700) < 0.3, 'The old move-left key does nothing');
  check(await hold(page, 'r', 700) > 0.8, 'The new move-left key walks');
  const hints = await page.evaluate(() => ({ tracker: document.querySelector('.tracker-journal').textContent, bags: document.getElementById('inventory-open').getAttribute('aria-label'), social: document.getElementById('social-open').getAttribute('aria-label'), skills: document.querySelector('#skills-open kbd').textContent, slot: document.querySelector('#skillbar-slots .skill-slot kbd').textContent, slotTitle: document.querySelector('#skillbar-slots .skill-slot').title.split(' · ')[0], welcome: document.getElementById('chat-log')?.textContent || '' }));
  check(/· G$/.test(hints.tracker), `The quest tracker reads G (${hints.tracker})`);
  check(hints.bags === 'Open bags (P / I)' && hints.social === 'Friends and party (O)' && hints.skills === 'Y' && hints.slot === 'V' && hints.slotTitle === 'V', `Hints follow the new keys: ${JSON.stringify(hints)}`);

  // --- it persists ---
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('valhallasc.save.v1')).keys);
  check(stored.quests[0] === 'KeyG' && stored.party[0] === 'KeyU' && stored.moveLeft[0] === 'KeyR' && !('friends' in stored), `Only the changed actions are stored: ${JSON.stringify(Object.keys(stored))}`);
  await page.reload();
  const after = await page.evaluate(() => ({ quests: Keys.label('quests'), party: Keys.label('party'), left: Keys.label('moveLeft'), attack: Keys.label('attack') }));
  check(after.quests === 'G' && after.party === 'U' && after.left === 'R / ←' && after.attack === 'Space / J', `The choices survive a reload: ${JSON.stringify(after)}`);
  await page.evaluate(() => Keys.resetAll());
  // swaps never hand a key to an action that may not have it, and a key two actions share leaves both
  await page.evaluate(() => Keys.bind('menu', 0, 'KeyQ'));
  check(await page.evaluate(() => Keys.slots('menu')[0] === 'KeyQ' && !Keys.slots('quests').includes('Escape') && Keys.actionsFor('Escape').length === 0), 'Menu took Q: Quests does not get Escape in the swap');
  await page.evaluate(() => Keys.resetAll());
  await page.evaluate(() => Keys.bind('chat', 0, 'KeyQ'));
  check(await page.evaluate(() => !Keys.slots('quests').includes('Enter')), 'Chat took Q: Quests does not get Enter in the swap');
  await page.evaluate(() => Keys.resetAll());
  check(await page.evaluate(() => JSON.stringify(Keys.actionsFor('KeyM')) === '["map","sound"]'), 'Map and sound share M as shipped');
  await page.evaluate(() => Keys.bind('quests', 0, 'KeyM'));
  check(await page.evaluate(() => JSON.stringify(Keys.actionsFor('KeyM')) === '["quests"]'), 'Quests took M: map and sound both gave it up');
  await page.evaluate(() => Keys.resetAll());
  // the shipped '-' and '=' still answer by character: Swedish '=' is Shift+0 and '-' is the Slash key
  const legacy = await page.evaluate(() => { const ids = Array.from({ length: 12 }, (_, i) => 'skill' + (i + 1)), ev = (code, key, shiftKey = false) => new KeyboardEvent('keydown', { code, key, shiftKey }); return [Keys.which(ev('Digit0', '=', true), ids), Keys.which(ev('Slash', '-'), ids), Keys.which(ev('Digit0', '0'), ids), Keys.which(ev('Minus', '-'), ids), Keys.which(ev('Equal', '='), ids)]; });
  check(JSON.stringify(legacy) === '["skill12","skill11","skill10","skill11","skill12"]', `Slots 11 and 12 keep answering to - and =: ${JSON.stringify(legacy)}`);
  check(await page.evaluate(() => Keys.label('quests') === 'Q' && Keys.label('party') === 'P' && JSON.stringify(Prefs.keys) === '{}'), 'Reset all returns every key to its shipped value');
  // --- Swedish: the rewritten hints are translated, key names included ---
  const sv = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  sv.on('pageerror', e => errors.push(e.message));
  await sv.addInitScript(() => { if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'sv', sound: false, char: null, draft: null })); } });
  await sv.goto(world.url);
  await sv.evaluate(() => { Keys.bind('friends', 0, 'Space'); Keys.bind('map', 0, 'KeyX'); Keys.bind('bags', 0, 'KeyU'); });
  await sv.waitForFunction(() => document.getElementById('wm-open').getAttribute('title') === 'Världskarta (X)', null, { timeout: 5000 });
  const swedish = await sv.evaluate(() => ({ map: document.getElementById('wm-open').getAttribute('title'), friends: document.getElementById('social-open').getAttribute('aria-label'), bags: document.getElementById('inventory-open').getAttribute('aria-label'), chat: document.getElementById('chat-input').placeholder }));
  check(swedish.friends === 'Vänner och grupp (Mellanslag)' && swedish.bags === 'Öppna väskor (U / I)', `The Swedish hints follow the keys: ${JSON.stringify(swedish)}`);
  await sv.close();
  check(errors.length === 0, `No page errors: ${errors.join(' | ')}`);
  console.log(`keymap-ui: ${checks} checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close().catch(() => {}); });
