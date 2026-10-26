// Real authoritative damage from two humans and eight hires, without grinding a fight.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { chromium } = require('./lib/playwright.cjs');
const world = new TestWorld(); let browser, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const results = [];
(async () => {
  world.godMode = true; world.startLevel = 99; world.levelSpread = 0; await world.start();
  const sizes = process.env.MUTATE ? [{ width: 1440, height: 900 }] : [{ width: 1440, height: 900 }, { width: 844, height: 390 }];
  for (const viewport of sizes) {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport, hasTouch: viewport.width < 1000, reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    if (process.env.MUTATE) await page.route('**/dpsmeter.js', async route => {
      const response = await route.fetch(), body = await response.text();
      assert.ok(body.includes('data.rows.map(row => {'));
      await route.fulfill({ response, body: body.replace('data.rows.map(row => {', 'data.rows.filter(row => !row.hired).map(row => {') });
    });
    await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator('#name').fill('DPS Observer'); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero, null, { timeout: 60000 });
    await page.evaluate(() => { const update = DpsMeter.update; DpsMeter.update = value => { window.__meter = value; return update(value); }; });
    const owner = await page.evaluate(() => Online.id), bot = 'DpsFriend' + viewport.width;
    await world.connect({ bot, class: 'mage' });
    await page.evaluate(name => Online.send({ type: 'social', command: { op: 'party_invite', name } }), bot);
    await world.waitFor(() => world.bots.get(bot).social?.incoming.some(i => i.id === owner), 10000, 'Party invite');
    await world.social(bot, { op: 'party_accept', id: owner });
    const entry = await page.evaluate(() => GM.request({ op: 'gm_dungeon_enter', zone: 46, at: 'door', level: true, gear: null, mercs: true }));
    check(entry.ok && entry.result.mercs === 8, 'two humans plus eight real hires');
    await world.debug(bot, { op: 'teleport', zone: 46, x: 35, y: 303 });
    await page.waitForFunction(() => window.__meter?.rows.length === 10);
    await page.evaluate(() => dispatchEvent(new Event('prefs-change')));
    check(await page.locator('#dps-rows tr').count() === 10, 'all players and mercenaries appear, including zero DPS');
    check(await page.locator('#dps-rows tr[data-hired="true"]').count() === 8, 'hires have separate meter rows');
    check((await page.locator('#dps-status').textContent()).includes('Waiting for combat'), 'idle meter has clear status');
    const spawn = async (x, y, kind) => {
      const reply = await page.evaluate(({ x, y, kind }) => GM.request({ op: 'spawn_enemy', kind, level: 99, x, y }), { x, y, kind });
      check(reply.ok, 'private encounter fixture is created'); return reply.result.id;
    };
    const enemies = [await spawn(40, 303, 'cf_brute'), await spawn(42, 303, 'cf_sentry'), await spawn(40, 300, 'cf_crawler')];
    check(new Set(enemies).size === 3, 'three distinct live enemies exercise a pack pull');
    await page.evaluate(id => Online.send({ type: 'target', id }), enemies[0]);
    await world.action(bot, { type: 'target', id: enemies[0] });
    await page.waitForFunction(({ owner, friend }) => window.__meter?.active && window.__meter.rows.find(r => r.id === owner)?.damage > 0 && window.__meter.rows.find(r => r.id === friend)?.damage > 0 && window.__meter.rows.some(r => r.hired && r.damage > 0), { owner, friend: world.bots.get(bot).id }, { timeout: 20000 });
    const proof = await page.evaluate(() => {
      dispatchEvent(new Event('prefs-change'));
      return window.__meter.rows.map(row => {
        const tr = [...document.querySelectorAll('#dps-rows tr')].find(tr => tr.dataset.id === row.id);
        return { row, shown: tr ? [...tr.cells].map(td => td.textContent) : null };
      });
    });
    check(proof.every(({ row, shown }) => shown && shown[0] === row.name && shown[1] === Math.round(row.dps).toLocaleString() && shown[2] === Math.round(row.damage).toLocaleString()), 'every displayed value matches the authoritative packet');
    check((await page.locator('#dps-status').textContent()).includes('Current fight'), 'live encounter status');
    const rect = await page.locator('#dps-meter').boundingBox();
    check(rect && rect.x >= 0 && rect.y >= 0 && rect.x + rect.width <= viewport.width + 1 && rect.y + rect.height <= viewport.height + 1, 'meter fits the viewport');
    await page.screenshot({ path: path.join(world.runDir, 'dps-meter-' + viewport.width + '.png') });
    // Actual death still permits surviving hires to deal damage while the owner respawns.
    const before = await page.evaluate(() => window.__meter.rows.filter(r => r.hired).reduce((n, r) => n + r.damage, 0));
    const died = await page.evaluate(() => GM.request({ op: 'die' })); check(died.ok, 'private death goes through normal death handling');
    await page.waitForFunction(() => Field.hero.dead);
    await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 10000 });
    check(await page.evaluate(before => window.__meter.rows.filter(r => r.hired).reduce((n, r) => n + r.damage, 0) > before, before), 'surviving mercenaries keep dealing damage after owner death');
    for (const id of enemies) await page.evaluate(id => GM.request({ op: 'kill_enemy', id }), id);
    await page.waitForFunction(() => window.__meter && !window.__meter.active);
    await page.evaluate(() => dispatchEvent(new Event('prefs-change')));
    check((await page.locator('#dps-status').textContent()).includes('Last fight'), 'completed fight remains visible');
    const frozen = await page.evaluate(() => JSON.stringify(window.__meter));
    await page.waitForTimeout(700);
    check(await page.evaluate(frozen => JSON.stringify(window.__meter) === frozen, frozen), 'completed totals and DPS freeze');
    await page.locator('#dps-close').click(); check(await page.locator('#dps-meter').isHidden(), 'hide button works');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero);
    check(await page.evaluate(() => Prefs.dpsMeter === false), 'hidden preference survives a reload');
    check(await page.locator('#dps-meter').isHidden(), 'meter stays hidden on reconnect');
    await page.keyboard.press('Escape'); await page.locator('#dps-toggle').click();
    check(await page.evaluate(() => Prefs.dpsMeter === true), 'World Menu can restore the meter');
    await page.keyboard.press('Escape'); check(await page.locator('#dps-meter').isVisible(), 'restored meter is visible');
    check(await page.evaluate(() => Locale.translate('DPS meter') === 'DPS meter'), 'English label stays English');
    if (viewport.width < 1000) { const close = await page.locator('#dps-close').boundingBox(); check(close.width >= 43.5 && close.height >= 43.5, 'touch hide target remains reachable at the saved UI scale'); }
    await Promise.all([page.waitForNavigation(), page.evaluate(() => Prefs.set({ lang: 'sv' }))]);
    await page.waitForFunction(() => window.Locale?.language === 'sv');
    check((await page.locator('#dps-meter header b').textContent()) === 'DPS-mätare', 'Swedish meter heading is displayed');
    check(errors.length === 0, JSON.stringify(errors));
    results.push({ viewport, proof });
    await browser.close(); browser = null; await world.disconnect(bot);
  }
  fs.writeFileSync(path.join(world.runDir, 'dps-meter-ui.json'), JSON.stringify({ checks, results }, null, 2));
  console.log(JSON.stringify({ passed: true, checks, artifacts: world.runDir }));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
