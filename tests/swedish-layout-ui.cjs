// L-SWEDISH-REDO: look at every main window in Swedish and in English, at game scale and on an 844x390 touch phone, and
// fail when a button, label, tab or text line overflows its box in Swedish where English fits (Swedish compounds are long).
// SHOT_DIR=<dir> also saves one screenshot per window and size.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const fs = require('node:fs');
const SHOT_DIR = process.env.SHOT_DIR;
// English left on screen: a word that the English catalog uses and no Swedish text or kept name does (a composed line the
// catalog and the phrase table do not reach). Words of four letters or more, case folded.
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'scripts', name), 'utf8'));
const words = text => text.toLowerCase().match(/[a-zåäöéáíóúü]{4,}/g) || [];
const english = new Set(), swedish = new Set();
for (const table of [read('sv-translations.txt'), read('sv-template-translations.txt'), read('sv-phrase-translations.txt')])
  for (const [en, sv] of Object.entries(table)) { words(en).forEach(w => english.add(w)); words(sv).forEach(w => swedish.add(w)); }
for (const name of read('sv-keep.txt')) words(name).forEach(w => swedish.add(w));
const englishOnly = new Set([...english].filter(w => !swedish.has(w)));
const visibleText = () => {
  const out = [], walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n.nodeValue.trim(), el = n.parentElement, r = el?.getBoundingClientRect();
    if (t.length > 2 && r?.width && r.height && !el.closest('script,style') && getComputedStyle(el).visibility !== 'hidden') out.push(t);
  }
  for (const el of document.querySelectorAll('[title],[placeholder],[aria-label]'))
    if (el.getBoundingClientRect().width) for (const a of ['title', 'placeholder', 'aria-label']) if (el.getAttribute(a)) out.push(el.getAttribute(a));
  return out;
};
const seed = lang => `if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: '${lang}', sound: false, char: null, draft: null }));`;
const SIZES = { desk: { viewport: { width: 1440, height: 900 } }, phone: { viewport: { width: 844, height: 390 }, isMobile: true, hasTouch: true } };
const WINDOWS = [['menu', 'Escape'], ['settings', 'Escape'], ['character', 'e'], ['bags', 'b'], ['skills', 'k'], ['social', 'o'], ['map', 'm'], ['quests', 'q'], ['npc', null]];

// Elements whose own text is wider than their box, as "text|width|box". The same page in English is the baseline.
const overflows = () => [...document.querySelectorAll('button, label, a, span, p, div, li, h1, h2, h3, td, th, small, b')].filter(el => {
  const r = el.getBoundingClientRect(); if (!r.width || !r.height || getComputedStyle(el).visibility === 'hidden') return false;
  const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.nodeValue.trim()).map(n => n.nodeValue.trim()).join(' ');
  const style = getComputedStyle(el); if (!own || /scroll|auto/.test(style.overflowX)) return false;
  return el.scrollWidth > el.clientWidth + 1 && style.display !== 'inline';
}).map(el => `${el.id || el.className || el.tagName}:${[...el.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue.trim()).join(' ').slice(0, 40)}`);

async function run(world, lang, sizeName) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ ...SIZES[sizeName], reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(seed(lang));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Utsikt' + lang); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.id);
  const debug = (ref, command) => page.evaluate(([ref, command]) => Online.send({ type: 'debug', ref, command }), [ref, command]);
  await debug(1, { op: 'set_gold', gold: 5000 }); await debug(2, { op: 'give_item', item: 'slime_gel', quantity: 5 });
  await page.waitForTimeout(400);
  const found = {}, left = {};
  const settle = async () => { for (let i = 0; i < 4; i++) { if (await page.locator('#pause').isVisible()) { await page.keyboard.press('Escape'); await page.waitForTimeout(150); } else break; } };
  const npc = await page.evaluate(() => WORLD_MAP.npcs.find(n => n.id === 'mira_moonleaf')?.id || WORLD_MAP.npcs[0].id);
  for (const [name, key] of WINDOWS) {
    await settle();
    if (name === 'npc') { await debug(5, { op: 'teleport', zone: 0, x: 36, y: 83 }); await page.waitForTimeout(500); await page.evaluate(id => Online.send({ type: 'interact', npc: id }), npc); }
    else { await page.keyboard.press(key); if (name === 'settings') { await page.locator('#p-settings').click(); } }
    await page.waitForTimeout(450);
    found[name] = await page.evaluate(overflows);
    if (lang === 'sv') left[name] = [...new Set(await page.evaluate(visibleText))].filter(t => words(t).some(w => englishOnly.has(w)));
    if (SHOT_DIR) await page.screenshot({ path: path.join(SHOT_DIR, `${lang}-${sizeName}-${name}.png`) });
    await page.keyboard.press('Escape'); await page.waitForTimeout(150);
  }
  assert.ok(!errors.length, `page errors: ${errors.join('; ')}`);
  await browser.close();
  return { found, left };
}

(async () => {
  const world = new TestWorld(); let checks = 0;
  try {
    await world.start();
    for (const sizeName of Object.keys(SIZES)) {
      const en = (await run(world, 'en', sizeName)).found, { found: sv, left } = await run(world, 'sv', sizeName);
      for (const [name] of WINDOWS) {
        const extra = sv[name].filter(x => !en[name].some(y => y.split(':')[0] === x.split(':')[0]));
        assert.deepEqual(extra, [], `${sizeName} ${name}: overflows in Swedish only: ${extra.join(' | ')}`); checks++;
        assert.deepEqual(left[name], [], `${sizeName} ${name}: English left on screen: ${left[name].join(' | ')}`); checks++;
      }
    }
    console.log(`${checks} Swedish window layout checks passed`);
  } finally { await world.stop?.(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
