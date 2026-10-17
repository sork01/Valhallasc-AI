// REBIRTH-UI: the Rebirth panel, the confirmation, the reset, the Reborn title and aura on a second browser, the mount coat
// tints, the level-up hints and the badges in the party frame, on a private server with real browsers.
const assert = require('node:assert/strict');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const SAVE = JSON.stringify({ lang: 'en', sound: false, char: null, draft: null });
async function enter(browser, world, name, errors, record = false) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  await page.addInitScript(save => {
    if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', save);
    // What the canvas is asked to draw: texts with their colour, the aura atlas and every filled colour.
    window.__drawn = { texts: [], aura: 0, fills: new Set() };
    const proto = CanvasRenderingContext2D.prototype, fillText = proto.fillText, drawImage = proto.drawImage, fill = proto.fill;
    proto.fillText = function (text, ...rest) { window.__drawn.texts.push([String(text), String(this.fillStyle)]); return fillText.call(this, text, ...rest); };
    proto.drawImage = function (image, ...rest) { if (image?.src?.includes('rebirth.png') && Number.isFinite(rest[1])) window.__drawn.aura++; return drawImage.call(this, image, ...rest); };
    proto.fill = function (...args) { window.__drawn.fills.add(String(this.fillStyle)); return fill.apply(this, args); };
  }, SAVE);
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill(name); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.id);
  return page;
}
const debug = (page, command) => page.evaluate(command => Online.send({ type: 'debug', ref: 1, command }), command);
const level = (page, n) => debug(page, { op: 'set_level', level: n }).then(() => page.waitForFunction(n => Field.hero.level === n, n, { timeout: 10000 }));
async function openPanel(page) {
  await page.locator('#equipment-open').click();
  await page.waitForSelector('#character-rebirth .rebirth-perk');
}
async function closePanel(page) { await page.keyboard.press('Escape'); await page.waitForFunction(() => document.getElementById('equipment').hidden); }

(async () => {
  const world = new TestWorld();
  let browser;
  try {
    await world.start();
    browser = await chromium.launch({ headless: true });
    const errors = [];
    const page = await enter(browser, world, 'Phoenix', errors);

    // 1. A new character: the panel lists six perks, nothing earned, and the button is disabled with its reason.
    await openPanel(page);
    assert.equal(await page.locator('#character-rebirth .rebirth-perk').count(), 6, 'six perks are listed');
    assert.deepEqual(await page.locator('.rebirth-perk').evaluateAll(rows => rows.map(r => r.dataset.perk)), ['xp', 'gold', 'bagCells', 'fare', 'resetPrice', 'drops']);
    assert.match(await page.locator('.rebirth-status').textContent(), /Never reborn/);
    assert.equal(await page.locator('#rebirth-open').isDisabled(), true);
    assert.match(await page.locator('.rebirth-reason').textContent(), /You need level 50 to be reborn/);
    assert.match(await page.locator('.rebirth-next').textContent(), /first rebirth is at level 50/);
    assert.equal(await page.locator('.rebirth-perk[data-perk="drops"] .rebirth-value').textContent(), '×1');
    assert.equal(await page.locator('#rebirth-title').isVisible(), false, 'no dialog yet');
    assert.equal(await page.locator('#hud-reborn').isVisible(), false, 'no Reborn tag for a new character');
    await closePanel(page);

    // 2. Reaching level 50 puts the hint on the level-up banner and into the system log.
    await level(page, 50);
    await page.waitForFunction(() => /Rebirth is now possible/.test(document.getElementById('lu-hint').textContent), null, { timeout: 5000 });
    assert.match(await page.evaluate(() => document.getElementById('lu-hint').textContent), /open Character \(E\)/);
    await openPanel(page);
    assert.equal(await page.locator('#rebirth-open').isEnabled(), true, 'level 50 may rebirth');
    assert.match(await page.locator('.rebirth-next').textContent(), /A rebirth now is tier I\. At level 60 it becomes tier II/);
    assert.match(await page.locator('.rebirth-perk[data-perk="xp"] small').textContent(), /Next rebirth: \+10%/);
    assert.equal(await page.locator('.rebirth-perk[data-perk="gold"]').getAttribute('data-locked'), 'true', 'gold needs tier 2');
    await closePanel(page);

    // 3. In combat the button is disabled with the reason; leaving combat enables it again.
    await debug(page, { op: 'teleport', zone: 0, x: 48, y: 20 });
    await page.waitForFunction(() => Field.zone === 0 && Math.hypot(Field.hero.x - 48, Field.hero.y - 20) < 2, null, { timeout: 10000 });
    const prey = await page.waitForFunction(() => Field.slimes.find(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 40)?.id, null, { timeout: 15000 }).then(h => h.jsonValue());
    await debug(page, { op: 'kill_enemy', id: prey });
    await page.waitForFunction(() => Field.hero.inCombat, null, { timeout: 5000 });
    await openPanel(page);
    assert.equal(await page.locator('#rebirth-open').isDisabled(), true, 'combat blocks the button');
    assert.match(await page.locator('.rebirth-reason').textContent(), /Leave combat before you are reborn/);
    await page.waitForFunction(() => !Field.hero.inCombat, null, { timeout: 12000 });
    await page.waitForFunction(() => !document.getElementById('rebirth-open').disabled, null, { timeout: 5000 });
    assert.equal(await page.locator('.rebirth-reason').textContent(), '');

    // 4. The preview and the confirmation: nothing happens until REBIRTH is typed, Cancel changes nothing, Escape closes.
    await page.locator('#rebirth-open').click();
    await page.locator('#rebirth-dialog').waitFor({ state: 'visible' });
    assert.match(await page.locator('#rebirth-title').textContent(), /Rebirth at level 50: tier I/);
    assert.match(await page.locator('#rebirth-adds').textContent(), /Experience\s*\+0% → \+10%/);
    assert.match(await page.locator('#rebirth-dialog').textContent(), /What resets[\s\S]*Quest progress[\s\S]*What stays[\s\S]*the bank/);
    assert.equal(await page.locator('#rebirth-confirm').isDisabled(), true, 'the button waits for the typed word');
    await page.locator('#rebirth-type').fill('REBIR');
    assert.equal(await page.locator('#rebirth-confirm').isDisabled(), true, 'a partial word is not enough');
    await page.keyboard.press('Escape');
    await page.locator('#rebirth-dialog').waitFor({ state: 'hidden' });
    assert.equal(await page.evaluate(() => Field.hero.level), 50, 'closing the dialog rebirths nothing');
    assert.equal(await page.locator('#equipment').isVisible(), true, 'Escape closed only the dialog');
    await page.locator('#rebirth-open').click();
    await page.locator('#rebirth-dialog').waitFor({ state: 'visible' });
    await page.locator('#rebirth-cancel').click();
    await page.locator('#rebirth-dialog').waitFor({ state: 'hidden' });
    assert.equal(await page.evaluate(() => Field.hero.level), 50);

    // 5. Confirm: the hero is level 1 in Greenmeadow with the perks, the title, the banner and the aura.
    await page.evaluate(() => Online.send({ type: 'debug', ref: 2, command: { op: 'set_gold', gold: 777 } }));
    await page.locator('#rebirth-open').click();
    await page.locator('#rebirth-dialog').waitFor({ state: 'visible' });
    await page.locator('#rebirth-type').fill('rebirth');
    await page.locator('#rebirth-confirm').click();
    await page.waitForFunction(() => Field.hero.level === 1 && Field.hero.reborn?.count === 1, null, { timeout: 10000 });
    const state = await page.evaluate(() => ({ tiers: Field.hero.rebirthTiers, reborn: Field.hero.reborn, zone: Field.zone, gold: Field.hero.gold, xp: Field.hero.rebirthPerks.find(p => p.id === 'xp').value }));
    assert.deepEqual(state.tiers, [1, 0, 0, 0, 0]);
    assert.deepEqual(state.reborn, { count: 1, tier: 1 });
    assert.equal(state.zone, 0);
    assert.equal(state.gold, 777, 'gold is kept');
    assert.equal(state.xp, 10, 'the XP perk is +10%');
    await page.locator('#rebirth-banner').waitFor({ state: 'visible', timeout: 5000 });
    assert.match(await page.locator('#rebirth-banner-tier').textContent(), /Reborn I/);
    assert.equal(await page.locator('#rebirth-dialog').isVisible(), false);
    assert.equal((await page.locator('#hud-reborn').textContent()).trim(), 'Reborn I', 'the HUD shows the title');
    assert.equal(await page.locator('.rebirth-status').textContent(), 'Reborn I · 1 rebirth');
    assert.equal(await page.locator('.rebirth-perk[data-perk="xp"] .rebirth-value').textContent(), '+10%');
    assert.equal(await page.locator('#rebirth-open').isDisabled(), true, 'level 1 may not rebirth');
    await page.waitForFunction(() => window.__drawn.aura > 0, null, { timeout: 5000 });
    // A reply to a stale nonce is refused and changes nothing.
    await page.evaluate(() => Online.send({ type: 'rebirth', nonce: 'stale' }));
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => Field.hero.level), 1);
    await closePanel(page);

    // 6. Another browser sees the title, the tier colour and the aura on the reborn player.
    const watcher = await enter(browser, world, 'Watcher', errors);
    const spot = await watcher.evaluate(() => ({ zone: Field.zone, x: Field.hero.x, y: Field.hero.y }));
    await debug(page, { op: 'teleport', zone: spot.zone, x: spot.x + 3, y: spot.y });
    await watcher.waitForFunction(() => [...Field.remotePlayers.values()].some(p => p.reborn?.tier === 1), null, { timeout: 15000 });
    await watcher.waitForFunction(() => window.__drawn.texts.some(([t]) => t === 'Reborn I') && window.__drawn.aura > 0, null, { timeout: 8000 });
    const seen = await watcher.evaluate(() => ({ title: window.__drawn.texts.filter(([t]) => t === 'Reborn I').pop(), name: window.__drawn.texts.filter(([t]) => t === 'Phoenix').pop() }));
    assert.equal(seen.title[1].toLowerCase(), '#e8a46c', 'the title is bronze for tier 1');
    assert.equal(seen.name[1].toLowerCase(), '#e8a46c', 'the name takes the tier colour');

    // 7. The five auras are different, drawn from the atlas, and every one lights up the ground.
    const auras = await watcher.evaluate(async () => {
      const out = [];
      for (let tier = 1; tier <= 5; tier++) {
        const c = document.createElement('canvas'); c.width = 160; c.height = 80;
        const g = c.getContext('2d'); g.fillStyle = '#5f8f4a'; g.fillRect(0, 0, 160, 80); g.translate(80, 40);
        Rebirth.drawAura(g, tier, 1);
        const d = g.getImageData(0, 0, 160, 80).data;
        let changed = 0; for (let i = 0; i < d.length; i += 4) if (d[i] !== 0x5f || d[i + 1] !== 0x8f || d[i + 2] !== 0x4a) changed++;
        out.push({ tier, changed, hash: Array.from(d).reduce((h, v, i) => (h * 31 + v + i) >>> 0, 7) });
      }
      return out;
    });
    for (const a of auras) assert.ok(a.changed > 150, `aura ${a.tier} paints ${a.changed} pixels`);
    assert.equal(new Set(auras.map(a => a.hash)).size, 5, 'five different looks');

    // 8. A second rebirth at level 60 earns the gold perk and a mount coat, chosen in the panel and seen by the watcher.
    await level(page, 60);
    await page.waitForFunction(() => /Rebirth is now possible|A better rebirth/.test(document.getElementById('lu-hint').textContent), null, { timeout: 5000 }).catch(() => {});
    await openPanel(page);
    await page.locator('#rebirth-open').click();
    await page.locator('#rebirth-dialog').waitFor({ state: 'visible' });
    const adds = await page.locator('#rebirth-adds').textContent();
    assert.match(adds, /Experience\s*\+10% → \+20%/);
    assert.match(adds, /Gold\s*\+0% → \+10%/);
    assert.doesNotMatch(adds, /Drop rate/, 'tier 2 never raises the drops');
    await page.locator('#rebirth-type').fill('REBIRTH');
    await page.locator('#rebirth-confirm').click();
    await page.waitForFunction(() => Field.hero.level === 1 && Field.hero.reborn?.count === 2 && Field.hero.reborn.tier === 2, null, { timeout: 10000 });
    assert.deepEqual(await page.evaluate(() => Field.hero.rebirthTiers), [1, 1, 0, 0, 0]);
    await page.waitForSelector('.rebirth-coat');
    assert.equal(await page.locator('.rebirth-coat').count(), 2, 'Plain and the tier-2 coat');
    assert.equal(await page.locator('.rebirth-coat[data-tint="0"]').getAttribute('aria-pressed'), 'true');
    await debug(page, { op: 'give_mount', mount: 'horse' });
    await page.waitForFunction(() => Field.hero.mountOwned, null, { timeout: 10000 });
    await page.locator('.rebirth-coat[data-tint="2"]').click();
    await page.waitForFunction(() => Field.hero.mountTint === 2, null, { timeout: 10000 });
    assert.equal(await page.locator('.rebirth-coat[data-tint="2"]').getAttribute('aria-pressed'), 'true');
    // The server refuses a coat that was not earned.
    await page.evaluate(() => Online.send({ type: 'select_mount_tint', tier: 5 }));
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => Field.hero.mountTint), 2, 'an unearned coat is refused');
    await closePanel(page);
    await debug(page, { op: 'teleport', zone: spot.zone, x: spot.x + 3, y: spot.y });
    await page.waitForFunction(() => !Field.hero.mounted, null, { timeout: 5000 });
    await page.evaluate(() => { document.activeElement?.blur?.(); });
    await page.keyboard.press('h');
    await page.waitForFunction(() => Field.hero.mounted, null, { timeout: 10000 });
    await watcher.waitForFunction(() => [...Field.remotePlayers.values()].some(p => p.mounted && p.mountTint === 2), null, { timeout: 10000 });
    await watcher.waitForFunction(() => window.__drawn.fills.has('#aab7c6'), null, { timeout: 8000 });

    // 9. A later step up shows the better-rebirth hint once, and the party frame and friend list wear the badge.
    await level(page, 70);
    await page.waitForFunction(() => /A better rebirth is now available: tier III at level 70/.test(document.getElementById('lu-hint').textContent), null, { timeout: 5000 });
    await page.evaluate(() => Social.onState({
      friends: [], incoming: [], outgoing: [], friendsMax: 50,
      party: { leader: 'x', max: 5, xp: { level: 1 }, members: [{ id: 'x', name: 'Ann', class: 'mage', level: 50, online: true, place: 'Here', dead: false, hp: 1, maxHp: 1, reborn: 3, quests: [] }] },
    }));
    assert.equal((await page.locator('#party-frame .reborn-badge').textContent()).trim(), 'Reborn III');
    assert.equal(await page.evaluate(() => getComputedStyle(document.querySelector('#party-frame .reborn-badge')).color), 'rgb(255, 216, 74)', 'tier 3 is gold');

    assert.deepEqual(errors, [], 'rebirth UI has no page errors');
    console.log('Rebirth panel, preview, combat refusal, typed confirmation, reset, title, aura, mount coat, hints and badges checks passed');
  } finally {
    await browser?.close(); await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
