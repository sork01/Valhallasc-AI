// Browser check for MENU-TO-SETTINGS-DPS, MINIMAP-MAIL-ICON and MENU-REMOVE-EQUIP-ACHIEVEMENTS.
// Run via: bash scripts/test-touch-bounded.sh tests/menu-cleanup-ui.cjs
// MUTATE=1 puts a removed menu button back, moves the mail icon onto the globe and shows it with no mail: the run must fail.
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

async function openHero(context, world, { lang = 'en', name = 'MenuHero' } = {}) {
  const page = await context.newPage();
  await page.addInitScript(l => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    if (!localStorage.getItem('valhallasc.save.v1')) {
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: l, sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    }
  }, lang);
  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill(name);
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => { const tip = document.getElementById('tutorial-tip'); if (tip && !tip.hidden) document.getElementById('tutorial-disable')?.click(); });
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
  const box = async (page, sel) => page.locator(sel).boundingBox();

  try {
    for (const view of [
      { name: 'desktop', viewport: { width: 1440, height: 900 } },
      { name: 'phone', viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true },
    ]) {
      const ctx = await browser.newContext({ viewport: view.viewport, isMobile: view.isMobile, hasTouch: view.hasTouch, reducedMotion: 'reduce' });
      const page = await openHero(ctx, world, { name: `Menu${view.name}` });
      page.on('pageerror', e => errors.push(e.message));
      const tag = s => `${view.name}: ${s}`;

      if (process.env.MUTATE === '1') {
        await page.evaluate(() => { const b = document.createElement('button'); b.id = 'p-achievements'; document.querySelector('#pause .pause-panel').append(b); });
        await page.addStyleTag({ content: '.mail-open { top: .8cqw !important; }' });
        await page.addStyleTag({ content: '.mail-open[hidden] { display: grid !important; }' });   // the old always-visible icon
      }

      // 0. MAIL-ICON-ONLY-WITH-MAIL: a hero with no letters sees no envelope at all (not just a transparent one). The snapshot re-applies the
      //    mail count on every tick, so each sequence below runs inside one synchronous evaluate.
      check(await page.evaluate(() => { const b = document.getElementById('mail-open'); return b.hidden && getComputedStyle(b).display === 'none' && b.getBoundingClientRect().width === 0; }), tag('no letters: the mail icon is not displayed'));
      const seq = await page.evaluate(() => {
        const b = document.getElementById('mail-open'), shown = () => getComputedStyle(b).display !== 'none' && b.getBoundingClientRect().width > 4, out = {};
        Mail.onUnread(0, 0); out.zero = shown();
        Mail.onUnread(0, 1); out.read = shown(); out.readTitle = b.title; out.tab = b.tabIndex;
        Mail.onUnread(0, 0); out.emptied = shown();
        Mail.onUnread(1, 1); out.arrived = shown();
        Mail.reset(); out.reset = shown();
        return out;
      });
      check(seq.zero === false, tag('0 in total keeps it hidden'));
      check(seq.read === true && seq.readTitle === 'Mail: 1 in total, 0 unread', tag(`one letter, already read, shows it (${seq.readTitle})`));
      check(seq.emptied === false, tag('the last letter deleted or collected hides it again'));
      check(seq.arrived === true, tag('a new letter makes it appear on its own'));
      check(seq.reset === false, tag('switching character (reset) hides it'));
      // From here on pretend the mailbox holds one letter, whatever the snapshots say (they say none).
      await page.evaluate(() => { window.__realOnUnread = Mail.onUnread; Mail.onUnread = (c, t) => window.__realOnUnread(c, Math.max(t ?? 0, 1)); Mail.onUnread(0, 1); });

      // 1. The World Menu no longer lists the moved or removed controls.
      const menu = await page.evaluate(() => ['p-equipment', 'p-achievements', 'mail-open', 'mail-unread', 'mail-menu-notice', 'dps-toggle'].map(id => !!document.querySelector(`#pause .pause-panel #${id}`)));
      check(menu.every(found => !found), tag(`World Menu has none of the removed controls (${menu})`));
      check(await page.evaluate(() => !document.getElementById('p-equipment') && !document.getElementById('mail-menu-notice')), tag('the old nodes are gone from the page'));

      // 2. The DPS meter switch lives in Settings, works and persists in Prefs.
      check(await page.evaluate(() => !!document.querySelector('#settings-panel .settings-panel #dps-toggle[type="checkbox"]')), tag('Settings holds the DPS meter checkbox'));
      await page.keyboard.press('Escape');
      await page.locator('#p-settings').click();
      check(await page.locator('#dps-toggle').isChecked(), tag('DPS meter starts on'));
      await page.locator('#dps-toggle').uncheck();
      check(await page.evaluate(() => Prefs.dpsMeter === false), tag('unchecking turns the meter off'));
      await page.locator('#dps-toggle').check();
      check(await page.evaluate(() => Prefs.dpsMeter !== false), tag('checking turns the meter back on'));
      await page.evaluate(() => Prefs.set({ dpsMeter: false }));
      check(!(await page.locator('#dps-toggle').isChecked()), tag('the checkbox follows a Prefs change'));
      await page.evaluate(() => Prefs.set({ dpsMeter: true }));
      await page.locator('#set-back').click();
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => document.getElementById('pause').hidden);

      // 3. The mail icon: round, under the globe, same edge, no overlap, touch sized.
      const wm = await box(page, '#wm-open'), mail = await box(page, '#mail-open');
      check(mail && wm, tag('both minimap buttons are on screen'));
      check(mail.y >= wm.y + wm.height - 0.5, tag(`mail icon sits below the world map button (${mail.y} vs ${wm.y + wm.height})`));
      check(Math.abs(mail.x - wm.x) < 2, tag(`mail icon shares the left edge (${mail.x} vs ${wm.x})`));
      check(Math.abs(mail.width - mail.height) < 1 && Math.abs(mail.width - wm.width) < 1, tag('mail icon is a circle the size of the globe'));
      check(await page.evaluate(() => getComputedStyle(document.getElementById('mail-open')).borderRadius === '50%'), tag('the icon has a round border'));
      check(await page.evaluate(() => !!document.querySelector('#mail-open svg rect')), tag('the icon draws an envelope'));
      const wrap = await box(page, '.minimap-wrap');
      check(mail.y + mail.height <= wrap.y + wrap.height + 1, tag('the icon stays beside the minimap'));
      for (const other of ['#mini-zoom-in', '#mini-zoom-out']) {
        if (await page.locator(other).isVisible()) {
          const o = await box(page, other);
          const overlap = !(mail.x + mail.width <= o.x || o.x + o.width <= mail.x || mail.y + mail.height <= o.y || o.y + o.height <= mail.y);
          check(!overlap, tag(`the icon does not overlap ${other}`));
        }
      }
      if (view.hasTouch) check(Math.abs(mail.width - wm.width) < 1 && mail.width >= 20, tag(`touch size matches the world-map button's 44 css px at the UI scale (${mail.width}x${mail.height} vs ${wm.width})`));

      // 4. Hover text tells how many letters there are.
      const text = await page.evaluate(() => {
        const read = () => ({ title: document.getElementById('mail-open').title, label: document.getElementById('mail-open').getAttribute('aria-label'), dot: document.getElementById('mail-unread').hidden ? '' : document.getElementById('mail-unread').textContent, unread: document.getElementById('mail-open').dataset.unread });
        const out = {};
        const real = window.__realOnUnread;
        real(0, 0); out.none = read();
        real(3, 5); out.some = read(); out.dotShown = getComputedStyle(document.getElementById('mail-unread')).display !== 'none' && document.getElementById('mail-unread').getBoundingClientRect().width > 4;
        real(120, 130); out.many = read();
        return out;
      });
      check(text.none.title === 'Mail: no unread letters' && text.none.dot === '' && text.none.unread === 'false', tag(`no mail: ${JSON.stringify(text.none)}`));
      check(text.some.title === 'Mail: 5 in total, 3 unread' && text.some.label === text.some.title && text.some.dot === '3' && text.some.unread === 'true', tag(`some mail: ${JSON.stringify(text.some)}`));
      check(text.many.dot === '99+', tag('the unread dot caps at 99+'));
      check(text.dotShown, tag('the unread dot is visible'));

      // 5. Away from a mailbox the click explains itself instead of doing nothing.
      await page.evaluate(() => Announce.clearErrors());
      if (view.hasTouch) await page.locator('#mail-open').tap(); else await page.locator('#mail-open').click();
      await page.waitForFunction(() => document.getElementById('error-messages').textContent.includes('Walk closer to a mailbox'));
      check(await page.locator('#mail-panel').isHidden(), tag('no mailbox in reach, so no mail window'));
      check(await page.evaluate(() => document.getElementById('pause').hidden), tag('the World Menu stays closed'));

      // 6. Equipment and achievements are reached through the Character pane.
      await page.keyboard.press('e');
      await page.locator('#equipment').waitFor({ state: 'visible' });
      await page.locator('#character-tab-achievements').click();
      check(await page.locator('#character-achievements').isVisible(), tag('the Achievements tab opens from the Character pane'));
      check(await page.evaluate(() => { Achievements.open(); return document.getElementById('character-tab-achievements').getAttribute('aria-selected') === 'true'; }), tag('Achievements.open() still selects the tab'));
      await page.locator('#equipment-close').click();
      await ctx.close();
    }

    // 7. Swedish hover text.
    const svCtx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const sv = await openHero(svCtx, world, { lang: 'sv', name: 'MenuSv' });
    await sv.waitForFunction(() => Locale.language === 'sv');
    const svTitle = await sv.evaluate(() => { Mail.onUnread(3, 5); return document.getElementById('mail-open').title; });
    check(svTitle === 'Post: 5 totalt, 3 olästa', `Swedish mail text (${svTitle})`);
    await sv.evaluate(() => Mail.onUnread(0, 0));
    check((await sv.locator('#mail-open').getAttribute('title')) === 'Post: inga olästa brev', 'Swedish empty text');
    check(await sv.evaluate(() => getComputedStyle(document.getElementById('mail-open')).display === 'none'), 'Swedish: hidden with no letters');
    await svCtx.close();

    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    console.log(`PASS menu-cleanup-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
