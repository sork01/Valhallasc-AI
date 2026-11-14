// Browser check for EARLY-LEVEL-TUTORIAL (desktop + touch + persistence + MUTATE=1 control).
// Run via: bash scripts/test-touch-bounded.sh tests/tutorial-ui.cjs
// MUTATE=1 serves a stub tutorial.js and must fail.
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

async function resumeAfterReload(page) {
  await page.reload();
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  if (await page.locator('#go').isVisible()) await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
}

async function setupPage(context, world, { lang = 'en', touch = false } = {}) {
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
  if (process.env.MUTATE === '1') {
    await page.route('**/tutorial.js', route => route.fulfill({
      contentType: 'application/javascript',
      body: 'window.Tutorial={onSnapshot(){},onEvent(){},refresh(){},reset(){},complete(){},disable(){},state:()=>({active:null,done:[],disabled:false})};',
    }));
  }
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click();
  await page.locator('#name').fill(touch ? 'TutTouch' : 'TutDesk');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  return page;
}

async function run() {
  requireMemoryLimit();
  const world = new TestWorld();
  let browser, checks = 0;
  const check = (cond, msg) => { assert.ok(cond, msg); checks++; };
  try {
    await world.start();
    browser = await chromium.launch({ headless: true, ignoreDefaultArgs: ['--hide-scrollbars'] });

    // --- 1. Desktop full milestone & persistence check ---
    {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
      const page = await setupPage(ctx, world, { touch: false });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      const debug = cmd => page.evaluate(c => Online.send({ type: 'debug', command: c }), cmd);

      // Walk/teleport off the pier if hero starts on dock so first_quest activates.
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 50, y: 50 } }));
      await page.waitForSelector('#tutorial-layer[data-step="first_quest"]:not([hidden])', { timeout: 10000 });
      const tipBox1 = await page.locator('#tutorial-tip').boundingBox();
      check(tipBox1 && tipBox1.width > 100 && tipBox1.height > 40, 'first_quest tooltip visible on desktop');

      // Non-blocking: click game canvas while tutorial tip is up (pointer-events: none on layer)
      const layerPointer = await page.locator('#tutorial-layer').evaluate(el => getComputedStyle(el).pointerEvents);
      check(layerPointer === 'none', 'tutorial layer is non-blocking');

      // Complete first_quest via Got it
      await page.locator('#tutorial-gotit').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('first_quest'));

      // Level up -> triggers levelup_stats
      await debug({ op: 'set_level', level: 2 });
      await page.waitForSelector('#tutorial-layer[data-step="levelup_stats"][data-substep="levelup_stats_bag"]:not([hidden])', { timeout: 10000 });

      // Interruption check: death & ghost form hide tutorial cleanly, then resurrect restores it
      await debug({ op: 'die' });
      await page.waitForFunction(() => Field.hero?.dead === true, null, { timeout: 10000 });
      await page.waitForFunction(() => document.getElementById('tutorial-layer')?.hidden === true, null, { timeout: 10000 });
      await page.waitForFunction(() => Field.hero?.ghost === true && !!Field.hero?.corpse, null, { timeout: 15000 });
      const corpse = await page.evaluate(() => Field.hero.corpse);
      await debug({ op: 'teleport', zone: corpse.zone, x: corpse.x, y: corpse.y });
      await page.waitForFunction(() => !document.getElementById('ghost-resurrect')?.disabled, null, { timeout: 10000 });
      await page.locator('#ghost-resurrect').click();
      await page.waitForFunction(() => !Field.hero?.dead && !Field.hero?.ghost, null, { timeout: 10000 });
      await debug({ op: 'set_hp', hp: 999 });
      await page.waitForSelector('#tutorial-layer[data-step="levelup_stats"]:not([hidden])', { timeout: 10000 });

      // Open bags -> switches to stats tab -> highlights ★ and Recommended
      await page.locator('#inventory-open').click();
      await page.waitForSelector('#tutorial-layer[data-step="levelup_stats"][data-substep="levelup_stats_attrs"]:not([hidden])', { timeout: 10000 });
      const attrFocus = await page.locator('#character-attributes .tutorial-focus-inline').count();
      check(attrFocus >= 2, '★ specialty row/button and Recommended button highlighted');
      const attrText = await page.locator('#tutorial-body').textContent();
      check(attrText.includes('★') && /Recommended/i.test(attrText), 'levelup tooltip mentions ★ and Recommended');

      // Click Recommended -> Confirm recommended -> levelup_stats auto-completes when statPoints reach 0
      await page.locator('#character-attributes .attribute-recommend').click();
      await page.locator('#recommended-confirm').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('levelup_stats'), null, { timeout: 10000 });

      // Close bags so equip_gear demonstrates bag prompt -> slot highlight
      await page.locator('#equipment-close').click();

      // Receive compatible non-starter gear -> equip_gear
      await debug({ op: 'give_item', item: 'warrior_weapon_sword_l1_blue', quantity: 1 });
      await page.waitForSelector('#tutorial-layer[data-step="equip_gear"][data-substep="equip_gear_bag"]:not([hidden])', { timeout: 10000 });
      await page.locator('#inventory-open').click();
      await page.waitForSelector('#tutorial-layer[data-step="equip_gear"][data-substep="equip_gear_slot"]:not([hidden])', { timeout: 10000 });
      await page.locator('#inventory-list [data-item="warrior_weapon_sword_l1_blue"] button').click();
      await page.locator('#bag-details [data-action="equip"]').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('equip_gear'), null, { timeout: 10000 });
      await page.locator('#equipment-close').click();

      // Unlock new active skill (level 4 Cleave) -> new_skill
      await debug({ op: 'set_level', level: 4 });
      await page.waitForSelector('#tutorial-layer[data-step="new_skill"][data-substep="new_skill_open"]:not([hidden])', { timeout: 10000 });
      await page.locator('#skills-open').click();
      await page.waitForSelector('#tutorial-layer[data-step="new_skill"][data-substep="new_skill_panel"]:not([hidden])', { timeout: 10000 });
      await page.locator('#skills-close').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('new_skill'), null, { timeout: 10000 });

      // Spend/dismiss remaining levelup_stats step if statPoints reappeared? Already done once!
      // Receive first consumable -> consumables
      await debug({ op: 'give_item', item: 'traveler_stew', quantity: 2 });
      await page.waitForSelector('#tutorial-layer[data-step="consumables"]:not([hidden])', { timeout: 10000 });
      await page.locator('#tutorial-gotit').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('consumables'), null, { timeout: 10000 });

      // Open Merchant -> merchant step & outsideClose guard
      const merchant = await page.evaluate(() => City.npcsOf(0).find(n => n.buys || n.stock?.length));
      check(!!merchant, 'Greenmeadow merchant NPC exists');
      await debug({ op: 'teleport', zone: 0, x: merchant.x, y: merchant.y });
      await page.waitForFunction(([mx, my]) => Math.hypot(Field.hero.x - mx, Field.hero.y - my) < 3, [merchant.x, merchant.y]);
      await page.evaluate(id => Online.send({ type: 'interact', npc: id }), merchant.id);
      await page.waitForSelector('#tutorial-layer[data-step="merchant"]:not([hidden])', { timeout: 10000 });
      await page.locator('#tutorial-gotit').click();
      await page.waitForFunction(() => Tutorial.state().done.includes('merchant'), null, { timeout: 10000 });
      check(await page.locator('#npc-dialogue').isVisible(), 'clicking tutorial Got it does not dismiss open merchant dialog');
      await page.locator('#npc-x').click();

      // Verify persistence across page reload (all 6 milestones saved on server)
      await resumeAfterReload(page);
      const reloadedDone = await page.evaluate(() => Tutorial.state().done);
      const first = ['first_quest', 'levelup_stats', 'equip_gear', 'new_skill', 'consumables', 'merchant'];
      check(first.every(id => reloadedDone.includes(id)), `all 6 first milestones persisted across reload (${reloadedDone.join(',')})`);

      // Reset / Replay tutorial from Settings
      await page.keyboard.press('Escape');
      await page.locator('#p-settings').click();
      await page.locator('#set-reset-tutorial').click();
      await page.waitForSelector('#tutorial-layer[data-step="first_quest"]:not([hidden])', { timeout: 10000 });
      check(await page.evaluate(() => Tutorial.state().done.length === 0), 'Reset / Replay tutorial clears completed steps');

      // Disable tutorial & confirm persistence across reload
      await page.locator('#tutorial-disable').click();
      await page.waitForFunction(() => document.getElementById('tutorial-layer')?.hidden === true && Tutorial.state().disabled === true);
      await resumeAfterReload(page);
      check(await page.evaluate(() => Tutorial.state().disabled === true), 'tutorial_disabled persists across reload');
      check(errors.length === 0, `desktop page errors: ${errors.join('; ')}`);
      await ctx.close();
    }

    // --- 2. Touch (844x390) + Swedish localization check ---
    {
      const ctx = await browser.newContext({
        viewport: { width: 844, height: 390 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 1,
        reducedMotion: 'reduce',
      });
      const page = await setupPage(ctx, world, { lang: 'sv', touch: true });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      const debug = cmd => page.evaluate(c => Online.send({ type: 'debug', command: c }), cmd);

      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 50, y: 50 } }));
      await page.waitForSelector('#tutorial-layer[data-step="first_quest"]:not([hidden])', { timeout: 10000 });
      const titleText = await page.locator('#tutorial-title').textContent();
      check(titleText && titleText !== 'Welcome to Greenmeadow', `Swedish localization translates tutorial title (got ${titleText})`);

      // Tip clears touch-stick and stays within viewport
      const boxes = await page.evaluate(() => ({
        tip: document.getElementById('tutorial-tip').getBoundingClientRect().toJSON(),
        stick: document.getElementById('touch-stick')?.getBoundingClientRect().toJSON() || null,
        vw: innerWidth,
        vh: innerHeight,
      }));
      check(boxes.tip.left >= 0 && boxes.tip.top >= 0 && boxes.tip.right <= boxes.vw && boxes.tip.bottom <= boxes.vh, 'touch tip fits viewport');
      if (boxes.stick && boxes.stick.width > 0) {
        const overlap = boxes.tip.left < boxes.stick.right && boxes.tip.right > boxes.stick.left && boxes.tip.top < boxes.stick.bottom && boxes.tip.bottom > boxes.stick.top;
        check(!overlap, 'touch tip does not overlap #touch-stick');
      }

      await page.locator('#tutorial-gotit').click();
      await debug({ op: 'set_level', level: 4 });
      await page.waitForSelector('#tutorial-layer[data-step="levelup_stats"]:not([hidden])', { timeout: 10000 });
      const glowBagsMatch = await page.evaluate(() => {
        const g = document.getElementById('tutorial-glow').getBoundingClientRect();
        const b = document.querySelector('#touch-actions [data-action="bags"]').getBoundingClientRect();
        return g.left < b.right && g.right > b.left && g.top < b.bottom && g.bottom > b.top;
      });
      check(glowBagsMatch, 'touch glow covers #touch-actions [data-action="bags"]');
      await page.locator('#tutorial-gotit').click();

      // new_skill targets touch Other skills tray toggle
      await page.waitForSelector('#tutorial-layer[data-step="new_skill"]:not([hidden])', { timeout: 10000 });
      await page.locator('#tutorial-gotit').click();

      // consumables targets touch-quickuse
      await debug({ op: 'give_item', item: 'health_potion', quantity: 1 });
      await page.waitForSelector('#tutorial-layer[data-step="consumables"]:not([hidden])', { timeout: 10000 });
      const consTarget = await page.evaluate(() => Tutorial.state().active.targetId);
      check(consTarget === 'touch-quickuse', `touch consumables targets #touch-quickuse (got ${consTarget})`);

      check(errors.length === 0, `touch page errors: ${errors.join('; ')}`);
      await ctx.close();
    }

    console.log(`PASS: tutorial-ui (${checks} checks)`);
  } finally {
    await browser?.close();
    await world.stop();
  }
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
