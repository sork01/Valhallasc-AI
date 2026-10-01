// Settings (music/effects volume) and the Edit UI mode in a real browser. Nothing here touches gameplay state:
// the checks drive the real menu, real sliders and real pointer drags, and read back stage geometry and storage.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-settings-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const KEY = 'valhallasc.save.v1';
const stored = page => page.evaluate(k => JSON.parse(localStorage.getItem(k) || '{}'), KEY);
const rect = (page, selector) => page.locator(selector).evaluate(n => { const r = n.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; });
const stageRect = page => rect(page, '#stage');
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  // Record what is wired straight into the speakers: music's compressor and exactly one effects bus.
  await page.addInitScript(() => {
    window.__dest = new Set(); const connect = AudioNode.prototype.connect;
    AudioNode.prototype.connect = function (to, ...rest) { if (to instanceof AudioDestinationNode) window.__dest.add(this); return connect.call(this, to, ...rest); };
    if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, char: null, draft: null })); }
  });
  await page.goto(world.url); await page.locator('#start').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Tuner'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  await page.evaluate(() => {
    window.sent = []; const original = Online.send; Online.send = message => { sent.push(message.type === 'input' && !message.dx && !message.dy ? 'ping' : message.type); return original(message); };
    window.levels = []; for (const m of [valhalla.music, valhalla.fmusic]) { const set = m.setLevel; m.setLevel = (v, s) => { levels.push(v); return set.call(m, v, s); }; }
  });

  // --- the menu entry ---
  check(await page.locator('#p-settings').isHidden(), 'Settings is not on screen before the menu opens');
  await page.keyboard.press('Escape');
  check(await page.locator('#p-settings').isVisible(), 'The World Menu has a Settings button');
  await page.locator('#p-settings').click();
  check(await page.locator('#settings-panel').isVisible() && await page.locator('#pause').isHidden(), 'Settings replaces the World Menu');
  check(await page.locator('#set-music').inputValue() === '100' && await page.locator('#set-sfx').inputValue() === '100', 'Both sliders start at 100%, the loudness the game always had');
  check(await page.evaluate(() => document.activeElement.id) === 'set-music', 'Focus lands on the first slider');

  // --- volumes ---
  await page.locator('#set-music').fill('50');
  check(await page.locator('#set-music-out').textContent() === '50%', 'The music slider shows its percentage');
  check(await page.evaluate(() => Math.abs(levels.at(-1) - .25) < 1e-9), 'Music level follows a squared taper (50% slider = 0.25 gain)');
  check((await stored(page)).musicVol === .5, 'The music level is saved on this device');
  await page.locator('#set-sfx').fill('50');
  await page.evaluate(() => Prefs.preview());
  const bus = await page.evaluate(() => [...__dest].map(n => ({ type: n.constructor.name, gain: n.gain?.value })));
  const gains = bus.filter(n => n.type === 'GainNode');
  check(gains.length === 1 && Math.abs(gains[0].gain - .25) < 1e-6, `Every effect goes through one bus at 0.25 (${JSON.stringify(bus)})`);
  check((await stored(page)).sfxVol === .5, 'The effects level is saved');
  await page.locator('#set-sfx').fill('0'); await page.evaluate(() => Prefs.preview());
  check(await page.evaluate(() => [...__dest].find(n => n instanceof GainNode).gain.value) === 0, 'Effects at 0% are silent');
  await page.locator('#set-sfx').fill('100');
  await page.locator('#set-sound').uncheck();
  check(await page.evaluate(() => levels.at(-1) === 0), 'Turning sound off silences the music whatever the slider says');
  await page.locator('#set-sound').check();
  check(await page.evaluate(() => Math.abs(levels.at(-1) - .25) < 1e-9), 'Sound back on restores the music slider level');
  await page.evaluate(() => document.activeElement.blur()); await page.keyboard.press('m'); // M ignores text fields, so leave the checkbox first
  check((await stored(page)).sound === false && await page.locator('#set-sound').isChecked() === false, 'The M key and the panel stay in sync');
  await page.keyboard.press('m');
  check((await stored(page)).sound === true && await page.locator('#set-sound').isChecked(), 'M toggles it back');

  // --- escape walks back one level at a time ---
  await page.keyboard.press('Escape');
  check(await page.locator('#settings-panel').isHidden() && await page.locator('#pause').isVisible(), 'Esc in Settings returns to the World Menu');
  await page.keyboard.press('Escape');
  check(await page.locator('#pause').isHidden(), 'Esc again closes the menu');
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  await page.locator('#set-back').click();
  check(await page.locator('#pause').isVisible() && await page.locator('#settings-panel').isHidden(), 'Back to menu works with the mouse');
  await page.locator('#p-resume').click();

  // --- Edit UI ---
  const ids = ['frame', 'buffs', 'party', 'map', 'travel', 'quests', 'character', 'bags', 'social', 'skillbar', 'chat', 'hint'];
  const before = {}; for (const id of ids) before[id] = await rect(page, `[data-ui="${id}"]`);
  check(ids.length === 12, 'Twelve movable pieces');
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  await page.locator('#set-edit-ui').click();
  check(await page.locator('#layout-bar').isVisible() && await page.locator('#settings-panel').isHidden(), 'Edit UI hides the panel and shows its toolbar');
  const handles = await page.locator('.layout-handle').evaluateAll(list => list.map(n => ({ id: n.dataset.id, w: n.getBoundingClientRect().width, h: n.getBoundingClientRect().height, hidden: n.hidden })));
  check(handles.length === 12 && handles.every(h => !h.hidden && h.w > 10 && h.h > 10), `Every piece, even the empty party frame and tracker, gets a visible handle: ${JSON.stringify(handles.filter(h => h.hidden || h.w <= 10))}`);
  for (const id of ids) { const h = await rect(page, `.layout-handle[data-id="${id}"]`), e = await rect(page, `[data-ui="${id}"]`); check(Math.abs(h.l - e.l) < 1.5 && Math.abs(h.t - e.t) < 1.5, `The ${id} handle sits on its piece`); }
  await page.screenshot({ path: path.join(world.artifacts, 'edit-ui.png') });
  await page.evaluate(() => { sent.length = 0; });
  // dragging the skillbar by its handle
  const bar0 = await rect(page, '#skillbar'), stage = await stageRect(page);
  const grab = { x: bar0.l + bar0.w / 2, y: bar0.t + bar0.h / 2 };
  await page.mouse.move(grab.x, grab.y); await page.mouse.down(); await page.mouse.move(grab.x - 150, grab.y - 120, { steps: 8 }); await page.mouse.up();
  const bar1 = await rect(page, '#skillbar');
  check(Math.abs((bar1.l - bar0.l) + 150) < 1.5 && Math.abs((bar1.t - bar0.t) + 120) < 1.5, `The skillbar follows the pointer (${bar1.l - bar0.l}, ${bar1.t - bar0.t})`);
  const saved = (await stored(page)).ui;
  check(saved.skillbar && Math.abs(saved.skillbar.x * stage.w / 100 + 150) < 1.5, `The new spot is stored in stage units: ${JSON.stringify(saved)}`);
  check(!(await page.evaluate(() => sent)).some(t => t !== 'ping' && t !== 'stop'), 'Dragging sends nothing to the game: ' + JSON.stringify(await page.evaluate(() => sent)));
  // never off the stage
  await page.mouse.move(bar1.l + bar1.w / 2, bar1.t + bar1.h / 2); await page.mouse.down(); await page.mouse.move(-500, -500, { steps: 6 }); await page.mouse.up();
  const bar2 = await rect(page, '#skillbar');
  check(Math.abs(bar2.l - stage.l) < 1.5 && Math.abs(bar2.t - stage.t) < 1.5, 'A drag past the corner stops at the stage edge');
  await page.mouse.move(bar2.l + 20, bar2.t + 20); await page.mouse.down(); await page.mouse.move(5000, 5000, { steps: 6 }); await page.mouse.up();
  const bar3 = await rect(page, '#skillbar');
  check(Math.abs(bar3.r - stage.r) < 1.5 && Math.abs(bar3.b - stage.b) < 1.5, 'And at the opposite corner');
  // the game cannot hear the keyboard or the canvas
  await page.keyboard.press('1'); await page.keyboard.press('q'); await page.keyboard.press('e'); await page.keyboard.press('k');
  await page.mouse.click(stage.l + stage.w * .5, stage.t + stage.h * .5);
  check(await page.locator('#quest-journal, #skills-panel, #equipment').evaluateAll(l => l.every(n => n.hidden)), 'Hotkeys open nothing while editing');
  check(!(await page.evaluate(() => sent)).some(t => !['ping', 'stop'].includes(t)), `No skill, move or attack leaves the client while editing: ${JSON.stringify(await page.evaluate(() => sent))}`);
  // keyboard
  await page.locator('.layout-handle[data-id="chat"]').focus();
  const chat0 = await rect(page, '#chat');
  await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Shift+ArrowRight');
  const chat1 = await rect(page, '#chat');
  check(Math.abs((chat1.l - chat0.l) - stage.w * 1.25 / 100) < 1 && Math.abs((chat1.t - chat0.t) - stage.w * .25 / 100) < 1, 'Arrow keys nudge the focused handle; Shift moves four times as far');
  // move a button and an empty frame too
  const tracker0 = await rect(page, '#quest-tracker');
  await page.mouse.move(tracker0.l + 10, tracker0.t + 10); await page.mouse.down(); await page.mouse.move(tracker0.l - 90, tracker0.t + 60, { steps: 5 }); await page.mouse.up();
  const tracker1 = await rect(page, '#quest-tracker');
  check(Math.abs((tracker1.l - tracker0.l) + 100) < 1.5 && Math.abs((tracker1.t - tracker0.t) - 50) < 1.5, 'The quest tracker moves');
  const chatBefore = await stored(page);
  // finish with Esc: returns to Settings, not the World Menu, and the world stays paused
  await page.keyboard.press('Escape');
  check(await page.locator('#layout-bar').isHidden() && await page.locator('#settings-panel').isVisible() && await page.locator('#pause').isHidden(), 'Esc finishes editing and returns to Settings');
  check(await page.locator('.layout-layer').count() === 0, 'The edit layer is removed');
  check(await page.locator('[data-ui="hint"]').evaluate(n => getComputedStyle(n).pointerEvents === 'none'), 'Elements are back to normal after editing');
  await page.screenshot({ path: path.join(world.artifacts, 'settings-after-edit.png') });
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  const moved = {}; for (const id of ['skillbar', 'chat', 'quests']) moved[id] = await rect(page, `[data-ui="${id}"]`);
  await page.screenshot({ path: path.join(world.artifacts, 'ui-moved.png') });

  // --- it survives a reload, per device ---
  await page.reload(); await page.locator('#start').click();
  await page.waitForFunction(() => Online.connected && Field.hero.level > 0, null, { timeout: 60000 }).catch(() => {});
  if (await page.locator('#scene-create').isVisible()) await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  for (const id of ['skillbar', 'chat', 'quests']) { const r = await rect(page, `[data-ui="${id}"]`); check(Math.abs(r.l - moved[id].l) < 1.5 && Math.abs(r.t - moved[id].t) < 1.5, `${id} is where it was left after a reload`); }
  check((await stored(page)).musicVol === .5, 'Volumes survive the reload too');

  // --- a smaller window keeps everything reachable ---
  await page.setViewportSize({ width: 700, height: 394 });
  await page.waitForTimeout(200);
  const small = await stageRect(page);
  for (const id of ids) { const r = await rect(page, `[data-ui="${id}"]`); if (r.w) check(r.l >= small.l - 1.5 && r.r <= small.r + 1.5 && r.t >= small.t - 1.5 && r.b <= small.b + 1.5, `${id} is inside the stage in a small window`); }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(200);

  // --- reset ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#set-edit-ui').click();
  await page.locator('#layout-reset').click();
  for (const id of ['skillbar', 'chat', 'quests']) { const r = await rect(page, `[data-ui="${id}"]`); check(Math.abs(r.l - before[id].l) < 1.5 && Math.abs(r.t - before[id].t) < 1.5, `Reset puts ${id} back on its default spot`); }
  check(Object.keys((await stored(page)).ui || {}).length === 0, 'Reset clears the stored layout');
  await page.locator('#layout-done').click();
  check(await page.locator('#settings-panel').isVisible(), 'Done returns to Settings');
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  check(await page.locator('#pause').isHidden(), 'Resume leaves the game running');
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} settings and Edit UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
