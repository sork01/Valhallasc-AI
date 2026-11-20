// Approved browser host only. Run through scripts/test-touch-bounded.sh with this branch's private binary.
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const { chromium } = require('./lib/playwright.cjs'), { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..'), data = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt')));
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt')));
const npc = data.zones[3].npcs.find(n => n.id === 'city_transmog');
const head = items.find(i => i.kind === 'headgear' && i.class === 'warrior' && i.requiredLevel === 1);
const appearance = items.find(i => i.kind === 'armor' && i.class === 'warrior' && i.requiredLevel === 95 && i.rarity === 'uncommon');
const w = new TestWorld(); w.levelSpread = 0; let browser, page; let checks = 0; const errors = [];
const check = (value, message) => { assert(value, message); checks++; };
async function resume(viewport, state) {
  await browser.close(); browser = null;
  await w.waitFor(async () => (await (await fetch(w.url + 'health')).json()).online === 0, 10000, 'old browser leaves');
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const context = await browser.newContext({ viewport, storageState: state, reducedMotion: 'reduce', hasTouch: viewport.width <= 600, isMobile: viewport.width <= 600 });
  page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
  await page.goto(w.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#scene-chars').waitFor({ state: 'visible' }); await page.locator('.char-play').first().click();
  await page.waitForFunction(() => Online.connected && Field.zone === 4 && Field.warriorSprites && !Field.hero.dead, null, { timeout: 60000 });
  await page.locator('#connection-overlay').waitFor({ state: 'hidden' });
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  // Wait for an authoritative reply after the scene and its artwork are ready, before opening a service.
  await page.evaluate(n => Online.send({ type: 'debug', command: { op: 'teleport', zone: 4, x: n.x + 1, y: n.y } }), npc);
  await page.waitForFunction(n => Field.zone === 4 && Math.hypot(Field.hero.x - n.x, Field.hero.y - n.y) < 2.5, npc);
  console.log(`Ready: ${viewport.width}×${viewport.height}, ${await page.evaluate(() => Locale.language)}`);
}
async function panelFits() {
  return page.locator('#npc-dialogue .gossip-window').evaluate(e => { const a = e.getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect(); return a.top >= s.top - 1 && a.left >= s.left - 1 && a.bottom <= s.bottom + 1 && a.right <= s.right + 1; });
}
(async () => {
  const boot = Date.now(); await w.start(); console.log(`Private server ready in ${Date.now() - boot} ms`);
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE === '1') {
    const source = fs.readFileSync(path.join(root, 'client/transmog.js'), 'utf8'), needle = ".filter(id => id !== 'real')";
    assert(source.includes(needle));
    await page.route('**/transmog.js', r => r.fulfill({ contentType: 'application/javascript', body: source.replace(needle, '.filter(() => false)') }));
  }
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(w.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('WardrobeUI'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.warriorSprites, null, { timeout: 60000 });
  await page.locator('#connection-overlay').waitFor({ state: 'hidden' });
  console.log('Ready: desktop character');
  await page.evaluate(() => window.Tutorial?.disable?.());
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  const debug = command => page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await debug({ op: 'set_gold', gold: 200_000 });
  await debug({ op: 'give_item', item: head.id, quantity: 1 }); await debug({ op: 'give_item', item: appearance.id, quantity: 1 });
  await page.waitForFunction(ids => ids.every(id => Inventory.quantity(id) >= 1), [head.id, appearance.id]);
  await page.evaluate(id => Online.send({ type: 'equip', slots: { headgear: id } }), head.id);
  await page.waitForFunction(id => Field.hero.equipment.headgear === id, head.id);
  await debug({ op: 'take_item', item: appearance.id, quantity: 1 });
  await page.waitForFunction(id => Inventory.quantity(id) === 0, appearance.id);
  await debug({ op: 'teleport', zone: 4, x: npc.x + 1, y: npc.y });
  await page.waitForFunction(n => Field.zone === 4 && Math.hypot(Field.hero.x - n.x, Field.hero.y - n.y) < 2.5, npc);
  await page.evaluate(() => {
    const load = Field.loadSprite;
    Field.loadSprite = look => load(look).then(sprite => { window.__transmogPreview = { look: { ...look }, sprite }; return sprite; });
  });
  await page.evaluate(() => Online.send({ type: 'interact', npc: 'city_transmog' }));
  await page.locator('[data-view="transmog"]').click();
  check(await panelFits(), 'entire desktop window including footer fits the stage');
  check(await page.locator('.transmog-slot select').count() === 7, 'all seven equipment slots are offered');
  await page.locator('.transmog-slot select[data-slot="chest"]').selectOption(appearance.id);
  await page.locator('.transmog-slot select[data-slot="headgear"]').selectOption('hide');
  check(await page.locator('.transmog-total').getAttribute('data-cost') === '1000', 'combined fee covers both changed slots');
  check(await page.locator('.transmog-slot option[value="hide"]').count() === 3, 'Hide is available on exactly three slots');
  const before = await page.evaluate(() => ({ stats: [Field.hero.attack, Field.hero.defense], actual: Field.hero.equippedLook.warriorArmor, gold: Field.hero.gold }));
  await page.waitForFunction(variant => { const p = window.__transmogPreview; return p?.look.warriorArmor === variant && p.look.head === 'none' && Object.entries(p.sprite.equipment).every(([slot, art]) => !art || art === 'none' || p.sprite.source.parts[slot + '_' + art]); }, appearance.variant);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.waitForFunction(() => { const c = document.querySelector('.transmog-figure canvas'); return c && c.getContext('2d').getImageData(0, 0, c.width, c.height).data.some((v, i) => i % 4 === 3 && v > 0); });
  check(true, 'live character preview draws the real class artwork');
  check(await page.locator('[data-action="transmog-apply"]').evaluate(e => { const a = e.getBoundingClientRect(), p = e.closest('.gossip-parchment').getBoundingClientRect(); return a.top >= p.top && a.bottom <= p.bottom; }), 'desktop shows all seven choices, fee and Apply without scrolling');
  await page.screenshot({ path: path.join(w.runDir, 'transmog-desktop.png') });
  await page.locator('[data-action="transmog-apply"]').click();
  await page.waitForFunction(id => Field.hero.transmogs.chest === id && Field.hero.look.head === 'none', appearance.id);
  await page.waitForFunction(variant => { const s = Field.warriorSprites; return s?.worn?.armor === variant && Object.entries(s.equipment).every(([slot, art]) => !art || art === 'none' || s.source.parts[slot + '_' + art]); }, appearance.variant);
  check(await page.evaluate(b => Field.hero.gold === b.gold - 1000 && Field.hero.attack === b.stats[0] && Field.hero.defense === b.stats[1] && Field.hero.equippedLook.warriorArmor === b.actual, before), 'apply changes visuals and money while preserving real equipment and stats');
  check(await page.evaluate(id => Inventory.quantity(id) === 0, appearance.id), 'appearance remains usable after the original item is gone');
  await page.locator('#npc-x').click(); await page.evaluate(() => document.getElementById('inventory-open').click());
  const chest = page.locator('#equipped-slots [data-slot="chest"] .gear-icon');
  check(await chest.getAttribute('data-transmog') === appearance.id, 'paper doll uses a real-item icon with transmog marker');
  await chest.hover(); check((await page.locator('#item-tooltip').innerText()).includes(`Transmogrified to: ${appearance.name}`), 'paper-doll tooltip names the cosmetic item');
  console.log('Passed: desktop preview, Apply and actual-item tooltip');
  await resume({ width: 600, height: 390 }, await page.context().storageState());
  await page.evaluate(() => Online.send({ type: 'interact', npc: 'city_transmog' }));
  await page.locator('[data-view="transmog"]').click();
  await page.locator('[data-action="transmog-apply"]').scrollIntoViewIfNeeded();
  check(await panelFits(), 'entire phone window including footer fits the stage');
  check(await page.locator('.gossip-parchment').evaluate(e => e.scrollWidth <= e.clientWidth + 1), 'controls fit a small landscape phone');
  check(await page.locator('.transmog-figure canvas').evaluate(e => { const a = e.getBoundingClientRect(), p = e.closest('.gossip-parchment').getBoundingClientRect(); return a.top >= p.top - 1 && a.bottom <= p.bottom + 1; }), 'phone keeps the live preview visible beside the lower slots');
  await page.screenshot({ path: path.join(w.runDir, 'transmog-phone.png') });
  await page.locator('.transmog-slot select[data-slot="chest"]').selectOption('real');
  await page.locator('.transmog-slot select[data-slot="headgear"]').selectOption('real');
  check(await page.locator('.transmog-total').getAttribute('data-cost') === '0', 'all reverts are free');
  await page.locator('[data-action="transmog-apply"]').click();
  await page.waitForFunction(() => !Field.hero.transmogs.chest && !Field.hero.transmogs.headgear);
  check(await page.evaluate(gold => Field.hero.gold === gold - 1000, before.gold), 'revert does not charge again');
  console.log('Passed: phone controls and free revert');
  await page.evaluate(() => { const key = 'valhallasc.save.v1', save = JSON.parse(localStorage.getItem(key)); save.lang = 'sv'; localStorage.setItem(key, JSON.stringify(save)); });
  await resume({ width: 600, height: 390 }, await page.context().storageState());
  await page.evaluate(() => Online.send({ type: 'interact', npc: 'city_transmog' }));
  await page.locator('[data-view="transmog"]').click();
  check(await page.evaluate(() => Locale.language === 'sv'), 'reconnecting restores the Swedish locale');
  check(await page.locator('.transmog-controls button').innerText() === 'Tillämpa utseenden', 'Apply uses the handwritten Swedish text');
  check(await page.locator('.transmog-slot select[data-slot="headgear"] option[value="hide"]').innerText() === 'Dölj', 'Hide is localized');
  check(await page.locator('.transmog-slot span').evaluateAll(nodes => nodes.every(n => n.scrollWidth <= n.clientWidth + 1)), 'Swedish slot labels remain fully readable beside their selectors');
  check(await page.evaluate(id => Transmog.description(id).startsWith('Transmogrifierad till: '), appearance.id), 'appearance tooltips use the Swedish template');
  await page.locator('.transmog-slot select[data-slot="chest"]').selectOption(appearance.id);
  await page.locator('[data-action="transmog-apply"]').scrollIntoViewIfNeeded();
  check(await panelFits(), 'entire Swedish window including footer fits the stage');
  check(await page.locator('.gossip-parchment').evaluate(e => e.scrollWidth <= e.clientWidth + 1), 'Swedish appearance controls fit the phone');
  await page.screenshot({ path: path.join(w.runDir, 'transmog-phone-swedish.png') });
  check(errors.length === 0, `no browser errors: ${errors.join('; ')}`);
  console.log(`Transmogrify: ${checks} private desktop/phone browser checks passed; screenshots in ${w.runDir}`);
})().catch(async e => {
  console.error(e);
  if (page && !page.isClosed()) {
    try {
      console.error('UI state:', await page.evaluate(() => ({ connected: Online.connected, locale: Locale.language, zone: Field.zone, x: Field.hero?.x, y: Field.hero?.y, dead: Field.hero?.dead, dialogue: City.open, errors: document.querySelector('#chat-log')?.innerText?.slice(-1500) })));
      await page.screenshot({ path: path.join(w.runDir, 'transmog-failure.png'), timeout: 5000 });
    } catch (_) {}
  }
  process.exitCode = 1;
}).finally(async () => { await browser?.close(); await w.stop(); });
