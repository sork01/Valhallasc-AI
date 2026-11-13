// Browser check for BUFF-DEBUFF-TOOLTIPS: hover tooltips on buffs & debuffs + gold/red borders.
// Run via: bash scripts/test-touch-bounded.sh tests/buff-tooltip-ui.cjs
// MUTATE=1 disables pointer-events / polarity borders and must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const root = path.resolve(__dirname, '..');

function requireMemoryLimit() {
  const entry = fs.readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(s => s.startsWith('0::'));
  if (!entry) throw Error('Use scripts/test-touch-bounded.sh (1536M cap).');
  let dir = path.join('/sys/fs/cgroup', entry.slice(3));
  while (dir.startsWith('/sys/fs/cgroup')) {
    try {
      const limit = fs.readFileSync(path.join(dir, 'memory.max'), 'utf8').trim();
      if (/^\d+$/.test(limit) && BigInt(limit) <= 1536n * 1024n ** 2n) return;
    } catch (_) {}
    if (dir === '/sys/fs/cgroup') break;
    dir = path.dirname(dir);
  }
  throw Error('Refusing uncapped browser run; use scripts/test-touch-bounded.sh.');
}

async function openHero(context, world, { lang = 'en', name = 'BuffHero' } = {}) {
  const page = await context.newPage();
  await page.addInitScript(l => {
    window.AudioContext = undefined;
    window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) {
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({
        lang: l, sound: false, uiSet: true, ui: { obsolete: { x: 9, y: 9 } },
        panelSizeSet: true, panelSize: {}, char: null, draft: null,
      }));
    }
  }, lang);
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  // Dismiss tutorial overlays if any appear so pointer tests target the buff bar cleanly.
  await page.evaluate(() => {
    const tip = document.getElementById('tutorial-tip');
    if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click();
  });
  return page;
}

(async () => {
  requireMemoryLimit();
  const world = new TestWorld(root, { env: { VALHALLA_LEVEL_SPREAD: '0' } });
  await world.start();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  let checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };

  try {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await openHero(ctx, world, { lang: 'en', name: 'BuffCheck' });
    page.on('pageerror', e => errors.push(e.message));

    if (process.env.MUTATE === '1') {
      await page.addStyleTag({ content: '.buff-chip { pointer-events: none !important; border-color: #ff9a3a !important; }' });
    }

    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);

    // 1. Grant level 8 + rage + food, step off dock onto open ground, use Battle Cry (damage buff) and Traveler's Stew (regen buff).
    await debug({ op: 'teleport', zone: 0, x: 250, y: 167 });
    await page.waitForFunction(() => Math.hypot(Field.hero.x - 250, Field.hero.y - 167) < 3);
    await debug({ op: 'set_level', level: 8 });
    await page.waitForFunction(() => Field.hero.level >= 8);
    await debug({ op: 'set_resource', amount: 50 });
    await debug({ op: 'set_hp', hp: 50 });
    await debug({ op: 'give_item', item: 'traveler_stew', quantity: 1 });
    await page.waitForFunction(() => Inventory.bagQuantity('traveler_stew') >= 1);

    await page.evaluate(() => {
      Online.send({ type: 'skill', id: 'battlecry', fx: 1, fy: 0 });
      Online.send({ type: 'use_item', item: 'traveler_stew' });
    });
    await page.locator('#buff-bar [data-buff="battlecry"]').waitFor({ state: 'visible', timeout: 10000 });
    await page.locator('#buff-bar [data-buff="traveler_stew"]').waitFor({ state: 'visible', timeout: 10000 });

    const buffChipStyles = await page.evaluate(() => {
      const bar = document.getElementById('buff-bar');
      const bc = document.querySelector('#buff-bar [data-buff="battlecry"]');
      const ts = document.querySelector('#buff-bar [data-buff="traveler_stew"]');
      return {
        barPointer: getComputedStyle(bar).pointerEvents,
        bcPolarity: bc.dataset.polarity,
        tsPolarity: ts.dataset.polarity,
        bcBorder: getComputedStyle(bc).borderTopColor,
        tsBorder: getComputedStyle(ts).borderTopColor,
        tsTitle: ts.getAttribute('title'),
      };
    });
    check(buffChipStyles.barPointer === 'none', `Buff bar container does not block world clicks (${buffChipStyles.barPointer})`);
    check(buffChipStyles.bcPolarity === 'buff' && buffChipStyles.tsPolarity === 'buff', 'Both skill and food buffs have buff polarity');
    check(buffChipStyles.bcBorder === 'rgb(240, 201, 84)' && buffChipStyles.tsBorder === 'rgb(240, 201, 84)',
      `Buff chips share gold border (got ${buffChipStyles.bcBorder}, ${buffChipStyles.tsBorder})`);
    check(buffChipStyles.tsTitle && buffChipStyles.tsTitle.includes('Traveler'), 'Title attribute remains intact when not hovered');

    // 2. Hover Battle Cry chip with real pointer move.
    const bcBox = await page.locator('#buff-bar [data-buff="battlecry"]').boundingBox();
    await page.mouse.move(bcBox.x + bcBox.width / 2, bcBox.y + bcBox.height / 2);
    await page.locator('#buff-tooltip').waitFor({ state: 'visible', timeout: 5000 });
    const bcTip = await page.evaluate(() => {
      const tip = document.getElementById('buff-tooltip');
      const bc = document.querySelector('#buff-bar [data-buff="battlecry"]');
      const r = tip.getBoundingClientRect();
      return {
        polarity: tip.dataset.polarity,
        border: getComputedStyle(tip).borderTopColor,
        text: tip.innerText,
        nativeTitleWhileHovered: bc.getAttribute('title'),
        inBounds: r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight,
      };
    });
    check(bcTip.polarity === 'buff' && bcTip.border === 'rgb(240, 201, 84)', `Buff tooltip has gold border (${bcTip.border})`);
    check(bcTip.text.includes('Battle Cry') && bcTip.text.includes('Buff') && bcTip.text.includes('35% more damage') && bcTip.text.includes('remaining'),
      `Buff tooltip shows name, type, effect, and remaining time: ${bcTip.text}`);
    check(bcTip.nativeTitleWhileHovered === null, 'Native title suppressed while hovered so OS tooltip cannot overlap');
    check(bcTip.inBounds, 'Buff tooltip stays within viewport bounds');

    // 3. Move pointer away -> tooltip hides and native title restores.
    await page.mouse.move(700, 450);
    await page.waitForFunction(() => document.getElementById('buff-tooltip')?.hidden === true, null, { timeout: 5000 });
    const titleRestored = await page.locator('#buff-bar [data-buff="battlecry"]').getAttribute('title');
    check(Boolean(titleRestored && titleRestored.includes('Battle Cry')), 'Tooltip hides on mouseout and native title restores');

    // 4. Trigger a real debuff (Resurrection Sickness via Spirit Guide resurrection).
    await debug({ op: 'die' });
    await page.waitForFunction(() => Field.hero.dead === true && Field.hero.ghost === true, null, { timeout: 10000 });
    const guide = await page.evaluate(() => {
      const g = City.npcs.find(n => n.art === 'spirit_guide');
      return g ? { id: g.id, x: g.x, y: g.y } : null;
    });
    check(Boolean(guide), 'Spirit Guide is present while in ghost form');
    await debug({ op: 'teleport', zone: 0, x: guide.x, y: guide.y - 1.5 });
    await page.waitForFunction(g => Math.hypot(Field.hero.x - g.x, Field.hero.y - g.y) < 3, guide);
    await page.evaluate(id => Online.send({ type: 'interact', npc: id, offer: '' }), guide.id);
    await page.locator('[data-offer="spirit_resurrect"]').waitFor({ state: 'visible', timeout: 5000 });
    await page.locator('[data-offer="spirit_resurrect"]').click();
    await page.locator('#buff-bar [data-buff="resurrection_sickness"]').waitFor({ state: 'visible', timeout: 10000 });

    const debuffStyles = await page.evaluate(() => {
      const chip = document.querySelector('#buff-bar [data-buff="resurrection_sickness"]');
      return {
        polarity: chip.dataset.polarity,
        border: getComputedStyle(chip).borderTopColor,
      };
    });
    check(debuffStyles.polarity === 'debuff' && debuffStyles.border === 'rgb(230, 73, 73)',
      `Debuff chip has debuff polarity and red border (got ${debuffStyles.border})`);

    const sickBox = await page.locator('#buff-bar [data-buff="resurrection_sickness"]').boundingBox();
    await page.mouse.move(sickBox.x + sickBox.width / 2, sickBox.y + sickBox.height / 2);
    await page.locator('#buff-tooltip').waitFor({ state: 'visible', timeout: 5000 });
    const sickTip = await page.evaluate(() => {
      const tip = document.getElementById('buff-tooltip');
      return {
        polarity: tip.dataset.polarity,
        border: getComputedStyle(tip).borderTopColor,
        text: tip.innerText,
      };
    });
    check(sickTip.polarity === 'debuff' && sickTip.border === 'rgb(230, 73, 73)', `Debuff tooltip has red border (${sickTip.border})`);
    check(sickTip.text.includes('Resurrection Sickness') && sickTip.text.includes('Debuff') && sickTip.text.includes('25%'),
      `Debuff tooltip describes effect: ${sickTip.text}`);

    await ctx.close();

    // 5. Verify Swedish translation on buff & debuff tooltips.
    const svCtx = await browser.newContext({ viewport: { width: 1280, height: 720 }, reducedMotion: 'reduce' });
    const svPage = await openHero(svCtx, world, { lang: 'sv', name: 'BuffSvensk' });
    svPage.on('pageerror', e => errors.push(e.message));
    const svDebug = command => svPage.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    await svDebug({ op: 'teleport', zone: 0, x: 250, y: 167 });
    await svPage.waitForFunction(() => Math.hypot(Field.hero.x - 250, Field.hero.y - 167) < 3);
    await svDebug({ op: 'set_level', level: 8 });
    await svPage.waitForFunction(() => Field.hero.level >= 8);
    await svDebug({ op: 'set_resource', amount: 50 });
    await svPage.evaluate(() => Online.send({ type: 'skill', id: 'battlecry', fx: 1, fy: 0 }));
    await svPage.locator('#buff-bar [data-buff="battlecry"]').waitFor({ state: 'visible', timeout: 10000 });
    const svBox = await svPage.locator('#buff-bar [data-buff="battlecry"]').boundingBox();
    await svPage.mouse.move(svBox.x + svBox.width / 2, svBox.y + svBox.height / 2);
    await svPage.locator('#buff-tooltip').waitFor({ state: 'visible', timeout: 5000 });
    const svText = await svPage.locator('#buff-tooltip').innerText();
    check(svText.includes('Förstärkning') && svText.includes('kvar'), `Swedish buff tooltip translated: ${svText}`);
    await svCtx.close();

    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS buff-tooltip-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => {
  console.error(err);
  process.exit(1);
});
