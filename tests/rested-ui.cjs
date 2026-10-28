const { execFileSync } = require('node:child_process');
const { run, replace, debug, safeSpot } = require('./lib/touch.cjs');

// Only the private fixture database is edited, after the connection has closed.
function offline(db, id, seconds) {
  execFileSync('python3', ['-c', `
import json, sqlite3, sys, time
with sqlite3.connect(sys.argv[1]) as db:
    row = db.execute('SELECT state FROM characters WHERE id=?', (sys.argv[2],)).fetchone()
    assert row
    c = json.loads(row[0])
    c['rested'] = {'reserve': 0, 'lastSeen': int(time.time()) - int(sys.argv[3])}
    db.execute('UPDATE characters SET state=? WHERE id=?', (json.dumps(c), sys.argv[2]))
`, db, id, String(seconds)]);
}

run([{
  name: 'rested',
  mutate: page => replace(page, 'field.js', 'rested: hero.rested,', ''),
  async test({ player, check, world, width, height, out }) {
    const lang = width > 900 ? 'sv' : 'en';
    const page = await player('RestedHero', { lang });
    await safeSpot(page);
    const label = page.locator('#rested-status');
    await label.waitFor({ state: 'visible' });
    const target = await label.boundingBox();
    check(target.width >= 43.9 && target.height >= 43.9, 'touch target stays at least 44 pixels after UI scaling');
    check(/0% \/ 200%/.test(await label.textContent()), 'new character starts with no reserve');
    check(await label.getAttribute('aria-expanded') === 'false', 'details start folded');
    await label.tap();
    const details = page.locator('#rested-details');
    await details.waitFor({ state: 'visible' });
    const text = await details.innerText();
    check(text.includes('200%') && text.includes('5%') && text.includes('40'), 'explanation includes bonus, accrual and cap');
    check(lang === 'sv' ? text.includes('Utvilad') && text.includes('uppdrag') : text.includes('monsters and quests'), 'explanation is localized');
    const box = await details.boundingBox();
    check(box.x >= 0 && box.x + box.width <= width && box.y + box.height <= height, 'details fit the viewport');
    await page.keyboard.press('Escape');
    check(await details.isHidden(), 'Escape closes the explanation');
    await label.tap();
    await page.touchscreen.tap(width / 2, height / 2);
    check(await details.isHidden(), 'outside tap closes the explanation');
    const id = await page.evaluate(() => Online.id);
    await page.evaluate(() => Online.stop());
    await page.waitForFunction(async () => (await (await fetch('health')).json()).online === 0);
    offline(world.db, id, 144000);
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.rested?.percent === 200);
    await page.waitForFunction(() => /200% \/ 200%/.test(document.querySelector('#rested-status')?.textContent || ''));
    check(await page.locator('#rested').evaluate(el => el.classList.contains('rested-active')), 'offline reserve is full and purple');
    // One actual quest payout, prepared directly by the test-only quest helper.
    const before = await page.evaluate(() => ({ xp: Field.hero.xp, percent: Field.hero.rested.percent }));
    await debug(page, { op: 'quest', id: 'crags_onward', action: 'finish' });
    await page.waitForFunction(before => Field.hero.rested.percent < before, before.percent);
    const after = await page.evaluate(() => ({ xp: Field.hero.xp, percent: Field.hero.rested.percent }));
    check(after.xp > before.xp, 'quest XP is actually awarded');
    check(after.percent > 0 && after.percent < 200, 'quest bonus spends some reserve');
    await label.tap();
    await page.screenshot({ path: `${out}/rested-${width}x${height}.png` });
    await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.waitForFunction(() => Online.connected && Field.hero?.rested?.percent > 0 && Field.hero.rested.percent < 200);
    const resumed = await page.evaluate(() => Field.hero.rested.percent);
    check(Math.abs(resumed - after.percent) < .1, 'spent reserve persists across reconnect without refill');
    check((await label.textContent()).startsWith(lang === 'sv' ? 'Utvilad:' : 'Rested:'), 'reserve label stays localized after reconnect');
  },
}]).catch(e => { console.error(e); process.exitCode = 1; });
