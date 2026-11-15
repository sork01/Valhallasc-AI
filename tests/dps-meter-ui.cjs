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
      // MUTATE=freeze: the elapsed clock keeps running after the fight ends, so the frozen check must fail.
      const [from, to] = process.env.MUTATE === 'freeze'
        ? ['data = value && Array.isArray(value.rows) ? value : null;', 'data = value && Array.isArray(value.rows) ? Object.assign(value, { elapsed: value.elapsed + (performance.now() % 1000) / 1000 }) : null;']
        : ['data.rows.map(row => {', 'data.rows.filter(row => !row.hired).map(row => {'];
      assert.ok(body.includes(from), 'mutation anchor found');
      await route.fulfill({ response, body: body.replace(from, to) });
    });
    await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })); });
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    // Each viewport logs in again in the same world, and a guest name is unique (characters.name_key), so the name carries the viewport.
    await page.locator('#name').fill('DpsOwner' + viewport.width); await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero, null, { timeout: 60000 }).catch(async error => {
      const overlay = await page.evaluate(() => document.querySelector('#connection-overlay')?.innerText?.slice(0, 300) || '').catch(() => '');
      throw new Error('The private world did not accept the guest login; overlay: ' + JSON.stringify(overlay) + ' ' + error.message);
    });
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
    // A death leaves the owner a ghost until released/resurrected (corpse run), so the hires must keep dealing damage meanwhile.
    await page.waitForFunction(before => window.__meter.rows.filter(r => r.hired).reduce((n, r) => n + r.damage, 0) > before, before, { timeout: 20000 });
    check(await page.evaluate(() => Field.hero.dead), 'owner stays fallen while the hires keep fighting');
    check(await page.evaluate(before => window.__meter.rows.filter(r => r.hired).reduce((n, r) => n + r.damage, 0) > before, before), 'surviving mercenaries keep dealing damage after owner death');
    // A debug kill is credited to the owner, and the server refuses it while the owner is a ghost (hit_slime returns at
    // hp <= 0), so the owner is revived by set_hp before the raid is cleared.
    await page.evaluate(() => GM.request({ op: 'set_hp', hp: 1e6 }));
    await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 10000 });
    for (const id of enemies) await page.evaluate(id => GM.request({ op: 'kill_enemy', id }), id);
    // The hires keep fighting the raid's other living packs, and the pull stays open while any of them is engaged
    // (packs.rs). Clear the rest of this raid's living enemies so the fight can end.
    // The final boss is left out: a debug strike on Eldmarr starts his boss fight (state chase, phase cap at 66% health), and a
    // boss fight holds the meter open (damage_meter.rs pull_active), so he can never be cleared this way. The probe showed him
    // idle at full health before the loop and in chase afterwards, with the meter still active.
    const living = () => (world.snapshot?.slimes || []).filter(s => !s.dead && s.zone === 46 && !enemies.includes(s.id) && s.kind !== 'cf_eldmarr').map(s => s.id);
    for (let round = 0; round < 12 && living().length; round++) {
      for (const id of living()) await page.evaluate(id => GM.request({ op: 'kill_enemy', id }), id);
      await page.waitForTimeout(400);
    }
    await page.waitForFunction(() => window.__meter && !window.__meter.active, null, { timeout: 30000 }).catch(async error => {
      throw new Error('The fight did not end; living raid enemies: ' + JSON.stringify((world.snapshot?.slimes || []).filter(s => !s.dead && s.zone === 46).map(s => [s.id, s.kind, s.state, s.target])).slice(0, 800) + ' ' + error.message);
    });
    await page.evaluate(() => dispatchEvent(new Event('prefs-change')));
    check((await page.locator('#dps-status').textContent()).includes('Last fight'), 'completed fight remains visible');
    // The completed record freezes: its elapsed time, active flag, and the damage and DPS of every row that dealt damage.
    // A hire doomed by its hirer's death leaves the party later (mercs.rs), so a row with no damage may drop out of the list.
    const totals = meter => JSON.stringify({ active: meter.active, elapsed: meter.elapsed, rows: meter.rows.filter(row => row.damage > 0).sort((a, b) => a.id.localeCompare(b.id)).map(row => [row.id, row.damage, row.dps]) });
    const frozen = await page.evaluate(() => JSON.parse(JSON.stringify(window.__meter)));
    const samples = [];
    for (let i = 0; i < 8; i++) { await page.waitForTimeout(100); samples.push(await page.evaluate(() => JSON.parse(JSON.stringify(window.__meter)))); }
    check(frozen.active === false && samples.every(sample => totals(sample) === totals(frozen)), 'completed totals and DPS freeze');
    await page.locator('#dps-close').click(); check(await page.locator('#dps-meter').isHidden(), 'hide button works');
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero);
    check(await page.evaluate(() => Prefs.dpsMeter === false), 'hidden preference survives a reload');
    check(await page.locator('#dps-meter').isHidden(), 'meter stays hidden on reconnect');
    await page.keyboard.press('Escape'); await page.locator('#p-settings').click(); await page.locator('#dps-toggle').check();
    check(await page.evaluate(() => Prefs.dpsMeter === true), 'Settings can restore the meter');
    await page.locator('#set-back').click(); await page.keyboard.press('Escape'); check(await page.locator('#dps-meter').isVisible(), 'restored meter is visible');
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
