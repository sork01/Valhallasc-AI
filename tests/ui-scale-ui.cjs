// UI size and window resizing in a real browser: the Settings slider scales every HUD piece about the corner it is anchored to,
// and each window has a corner grip that resizes just that window. Client-only; nothing here touches gameplay state.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-ui-scale', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const KEY = 'valhallasc.save.v1';
const stored = page => page.evaluate(k => JSON.parse(localStorage.getItem(k) || '{}'), KEY);
const rect = (page, selector) => page.locator(selector).evaluate(n => { const r = n.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2 }; });
const near = (a, b, tol = 1.5) => Math.abs(a - b) <= tol;
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment() } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, char: null, draft: null })); }
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Sizer'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });

  // --- the global slider ---
  const anchored = { skillbar: 'cx b', bags: 'r b', quests: 'l', frame: 'l t', map: 'r t' };
  const base = {}; for (const id of Object.keys(anchored)) base[id] = await rect(page, `[data-ui="${id}"]`);
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  check(await page.locator('#set-uiscale').inputValue() === '80', 'UI size starts at 80%');
  check((await stored(page)).uiScaleSet !== true, 'The default is not stored as a choice');
  await page.locator('#set-uiscale').fill('100'); await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  for (const id of Object.keys(anchored)) base[id] = await rect(page, `[data-ui="${id}"]`); // the checks below measure from 100%
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  await page.locator('#set-uiscale').fill('150');
  check(await page.locator('#set-uiscale-out').textContent() === '150%', 'The slider shows its percentage');
  check((await stored(page)).uiScale === 1.5, 'The size is saved on this device');
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  for (const [id, anchor] of Object.entries(anchored)) {
    const r = await rect(page, `[data-ui="${id}"]`), b = base[id];
    if (!b.w) continue;
    check(near(r.w, b.w * 1.5, 2) && near(r.h, b.h * 1.5, 2), `${id} is 1.5 times as big (${b.w.toFixed(1)}x${b.h.toFixed(1)} -> ${r.w.toFixed(1)}x${r.h.toFixed(1)})`);
    for (const edge of anchor.split(' ')) check(near(r[edge], b[edge]), `${id} keeps its ${edge} where it was (${b[edge].toFixed(1)} -> ${r[edge].toFixed(1)})`);
  }
  const stage = await rect(page, '#stage');
  for (const id of Object.keys(anchored)) { const r = await rect(page, `[data-ui="${id}"]`); if (r.w) check(r.l >= stage.l - 1.5 && r.r <= stage.r + 1.5 && r.t >= stage.t - 1.5 && r.b <= stage.b + 1.5, `${id} stays inside the stage at 150%`); }
  await page.screenshot({ path: path.join(world.artifacts, 'ui-size-150.png') });

  // --- Edit UI still lines up at another size ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#set-edit-ui').click();
  for (const id of ['skillbar', 'chat', 'bags']) { const h = await rect(page, `.layout-handle[data-id="${id}"]`), e = await rect(page, `[data-ui="${id}"]`); check(near(h.l, e.l) && near(h.t, e.t) && near(h.w, e.w) && near(h.h, e.h), `The ${id} handle covers the scaled piece`); }
  check(await page.locator('.win-grip:visible').count() === 0, 'No resize grips while editing the layout');
  await page.locator('#layout-done').click(); await page.locator('#set-back').click(); await page.locator('#p-resume').click();

  // --- window resizing ---
  await page.keyboard.press('k');
  check(await page.locator('#skills-panel').isVisible(), 'K opens the skills window');
  const grip = page.locator('.win-grip[aria-label^="Resize Skills"]');
  check(await grip.isVisible(), 'The skills window has a resize grip');
  const win0 = await rect(page, '#skills-panel .skills-panel'), g0 = await rect(page, '.win-grip[aria-label^="Resize Skills"]');
  check(near(g0.r, win0.r - 3, 2) && near(g0.b, win0.b - 3, 2), 'The grip sits in the window corner');
  // 150% already: shrink first by dragging the grip towards the centre
  await page.mouse.move(g0.cx, g0.cy); await page.mouse.down(); await page.mouse.move(win0.cx + (g0.cx - win0.cx) * .5, win0.cy + (g0.cy - win0.cy) * .5, { steps: 8 }); await page.mouse.up();
  const win1 = await rect(page, '#skills-panel .skills-panel');
  check(near(win1.w, win0.w * .5, 3) && near(win1.cx, win0.cx) && near(win1.cy, win0.cy), `Dragging the grip inwards halves the window about its centre (${win0.w.toFixed(0)} -> ${win1.w.toFixed(0)})`);
  const g1 = await rect(page, '.win-grip[aria-label^="Resize Skills"]');
  check(near(g1.r, win1.r - 3, 2) && near(g1.b, win1.b - 3, 2), 'The grip follows the window corner');
  const saved = (await stored(page)).winScale;
  check(saved['skills-panel'] > .3 && saved['skills-panel'] < .6, `The window factor is saved: ${JSON.stringify(saved)}`);
  check(!(await stored(page)).winScale.equipment, 'Other windows are untouched');
  // too big: capped to the stage
  await page.mouse.move(g1.cx, g1.cy); await page.mouse.down(); await page.mouse.move(stage.r + 400, stage.b + 400, { steps: 8 }); await page.mouse.up();
  const win2 = await rect(page, '#skills-panel .skills-panel');
  check(win2.w <= stage.w + 1 && win2.h <= stage.h + 1 && win2.l >= stage.l - 1.5 && win2.t >= stage.t - 1.5, `A window never grows past the stage (${win2.w.toFixed(0)}x${win2.h.toFixed(0)} in ${stage.w.toFixed(0)}x${stage.h.toFixed(0)})`);
  // too small: floor
  const g2 = await rect(page, '.win-grip[aria-label^="Resize Skills"]');
  await page.mouse.move(g2.cx, g2.cy); await page.mouse.down(); await page.mouse.move(win2.cx, win2.cy, { steps: 8 }); await page.mouse.up();
  const win3 = await rect(page, '#skills-panel .skills-panel');
  check(win3.w > 150, `And never shrinks to nothing (${win3.w.toFixed(0)}px)`);
  // keyboard and reset
  await page.locator('.win-grip[aria-label^="Resize Skills"]').focus();
  const k0 = (await rect(page, '#skills-panel .skills-panel')).w;
  await page.keyboard.press('ArrowRight');
  check((await rect(page, '#skills-panel .skills-panel')).w > k0, 'An arrow key grows the focused window');
  await page.locator('.win-grip[aria-label^="Resize Skills"]').dblclick();
  const win4 = await rect(page, '#skills-panel .skills-panel');
  check(near(win4.w, win0.w, 2), `Double-clicking the grip restores the normal size (${win4.w.toFixed(1)} vs ${win0.w.toFixed(1)})`);
  check((await stored(page)).winScale['skills-panel'] === undefined, 'The stored factor is dropped');
  // resize and survive a reload
  const g4 = await rect(page, '.win-grip[aria-label^="Resize Skills"]');
  await page.mouse.move(g4.cx, g4.cy); await page.mouse.down(); await page.mouse.move(win4.cx + (g4.cx - win4.cx) * .7, win4.cy + (g4.cy - win4.cy) * .7, { steps: 8 }); await page.mouse.up();
  const sized = await rect(page, '#skills-panel .skills-panel');
  await page.keyboard.press('Escape');
  check(await page.locator('.win-grip:visible').count() === 0, 'Grips go with their windows');
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Field.hero.level > 0, null, { timeout: 60000 }).catch(() => {});
  if (await page.locator('#scene-create').isVisible()) await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites, null, { timeout: 60000 });
  await page.keyboard.press('k');
  const again = await rect(page, '#skills-panel .skills-panel');
  check(near(again.w, sized.w, 2), `The window size survives a reload (${sized.w.toFixed(1)} -> ${again.w.toFixed(1)})`);
  check(near((await rect(page, '[data-ui="skillbar"]')).w, base.skillbar.w * 1.5, 2), 'So does the UI size');
  await page.screenshot({ path: path.join(world.artifacts, 'window-resized.png') });
  await page.keyboard.press('Escape');

  // --- the other windows get grips, and the bag/character pair scales as one ---
  await page.keyboard.press('b');
  check(await page.locator('#equipment').isVisible() && await page.locator('.win-grip[aria-label^="Resize Character and bags"]').isVisible(), 'The character and bag windows share one grip');
  const eq = await rect(page, '#equipment .equipment-workspace');
  check(eq.w <= stage.w + 1 && eq.h <= stage.h + 1, 'At 150% the bag windows still fit the stage');
  await page.keyboard.press('Escape');

  // --- reset window sizes from Settings ---
  await page.keyboard.press('Escape'); await page.locator('#p-settings').click();
  await page.locator('#set-win-reset').click();
  check(Object.keys((await stored(page)).winScale || {}).length === 0, 'Reset window sizes clears every stored factor');
  await page.locator('#set-uiscale').fill('100');
  check((await rect(page, '[data-ui="skillbar"]')).w - base.skillbar.w < 1.5, 'Back at 100% the skillbar is its old size');
  check(await page.locator('[data-ui="skillbar"]').evaluate(n => n.style.scale === ''), 'And the inline scale is gone');
  await page.locator('#set-back').click(); await page.locator('#p-resume').click();
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} UI size and window resize checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
