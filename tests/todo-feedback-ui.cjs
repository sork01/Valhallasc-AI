// The eight November 12 requests: one bounded private browser, no combat or grinding.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
requireMemoryLimit();
const world = new TestWorld(); world.godMode = true;
let browser, checks = 0;
const errors = [];
const check = (ok, label) => { assert.ok(ok, label); console.log(`${++checks}: ${label}`); };
const wait = (page, fn, value) => page.waitForFunction(fn, value, { timeout: 15000 });
async function debug(page, command) {
  await page.evaluate(command => Online.send({ type: 'debug', command }), command);
  await page.waitForTimeout(180);
}
async function player(lang) {
  const page = await browser.newPage({ viewport: { width: 1100, height: 720 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(({ lang, version }) => {
    window.AudioContext = undefined; window.webkitAudioContext = undefined;
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang, sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {} }));
    localStorage.setItem('valhallasc.whats-new.v1', version);
  }, { lang, version: fs.readFileSync('client/index.html', 'utf8').match(/class="version">([^<]+)/)[1] });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill(`Todo${lang}`); await page.locator('#go').click({ timeout: 60000 });
  await wait(page, () => Online.connected && Field.hero?.hp > 0);
  if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
  await page.evaluate(() => {
    window.todoNotices = []; const original = Announce.show;
    Announce.show = (text, kind) => { todoNotices.push({ text, kind }); original(text, kind); };
  });
  return page;
}
async function quest(page, id, action) {
  await debug(page, { op: 'quest', id, action });
  await wait(page, ({ id, action }) => {
    const p = Field.hero.quests?.find(p => p.id === id);
    if (!p) return false;
    if (action === 'claim') return p.claimed;
    if (action === 'accept') return !p.claimed;
    const q = [WORLD_MAP, ...WORLD_MAP.zones].flatMap(a => a.quests || []).find(q => q.id === id);
    return q.objectives.every((o, i) => p.counts[i] >= o.count);
  }, { id, action });
}
async function screenshot(page, name) { await page.screenshot({ path: path.join(world.runDir, name) }); }
(async () => {
  await world.start(); browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await player('en');
  if (process.env.PART === 'errors') {
    await page.evaluate(() => {
      Announce.show('Quest completed: A Home in Alderhaven', 'quest');
      Announce.show('Quest completed: Keep the Paths Clear', 'quest');
      Field.error('A wall blocks your skill.');
    });
    await wait(page, () => document.getElementById('hero-errors').style.left);
    check(await page.evaluate(() => +getComputedStyle(document.getElementById('hero-errors')).zIndex > +getComputedStyle(document.getElementById('announce')).zIndex), 'Action errors stay above simultaneous completion banners');
    check((await page.locator('#hero-errors').textContent()).includes('A wall blocks your skill.'), 'The short error remains readable above the hero');
    for (const edge of [0, 1600]) check(await page.evaluate(edge => {
      Field.error('A wall blocks your skill. Move closer to your target and try again.');
      const canvas = document.getElementById('fieldcv'), rect = canvas.getBoundingClientRect();
      WorldFeedback.draw({ canvas, hero: Field.hero, project: () => [edge, 400], width: 1600, height: rect.height / rect.width * 1600, drops: [], blocked: true });
      const b = document.getElementById('hero-errors').getBoundingClientRect();
      return b.left >= rect.left && b.right <= rect.right;
    }, edge), `Long action errors fit at the ${edge === 0 ? 'left' : 'right'} edge`);
    await page.evaluate(() => { WorldFeedback.reset(); Field.error('A wall blocks your skill.'); });
    await page.waitForTimeout(120);
    await screenshot(page, 'todo-error-priority.png');
    await page.close(); console.log(`todo-feedback-ui errors: ${checks} checks passed; ${world.runDir}`); return;
  }
  await wait(page, () => Field.hero.travelStops?.includes('travel_saltby'));
  check(true, 'Arriving at the Saltby dock discovers its hub without talking');
  const entry = await page.evaluate(() => {
    const c = WORLD_MAP.city, n = WORLD_MAP.npcs.find(n => n.id === 'travel_alderhaven');
    for (let y = c.y0 + 1; y < c.y1 - 1; y += 2) for (let x = c.x0 + 1; x < c.x1 - 1; x += 2) {
      if (Math.hypot(x-n.x, y-n.y) > 5 && WORLD_MAP.objects.every(o => o.width ? Math.abs(x-o.x) > o.width/2+.7 || Math.abs(y-o.y) > o.depth/2+.7 : Math.hypot(x-o.x,y-o.y) > o.r+.7)) return { x, y };
    }
  });
  await debug(page, { op: 'teleport', zone: 0, ...entry });
  await wait(page, () => Field.hero.travelStops?.includes('travel_alderhaven'));
  check(await page.evaluate(() => !City.open && todoNotices.filter(n => n.text === 'Discovered Alderhaven for Spark Travel.').length === 1), 'City entry unlocks Alderhaven once, without opening a dialogue');
  await quest(page, 'welcome', 'accept'); await quest(page, 'fold_strays', 'accept');
  await quest(page, 'welcome', 'complete');
  await wait(page, () => todoNotices.some(n => n.text === 'Quest completed: A Home in Alderhaven'));
  check(await page.locator('#announce').textContent().then(t => t.includes('Quest completed: A Home in Alderhaven')), 'Objective completion paints a toast naming the quest');
  await page.waitForTimeout(350);
  check(await page.evaluate(() => todoNotices.filter(n => n.text === 'Quest completed: A Home in Alderhaven').length === 1), 'Repeated snapshots do not repeat the completion toast');
  await page.evaluate(() => { Quests.track('welcome'); Quests.show(); });
  check(await page.evaluate(() => {
    const ids = [...document.querySelectorAll('#quest-list > .quest-entry')].map(n => n.dataset.quest);
    return ids.indexOf('fold_strays') >= 0 && ids.indexOf('fold_strays') < ids.indexOf('welcome');
  }), 'An unfinished quest stays above a tracked quest ready to turn in');
  await screenshot(page, 'todo-quest-journal.png');
  await page.evaluate(() => Quests.close()); await quest(page, 'welcome', 'claim');
  await quest(page, 'slime_patrol', 'accept'); await quest(page, 'slime_patrol', 'complete'); await quest(page, 'slime_patrol', 'claim');
  await quest(page, 'meadow_bounty', 'accept'); await quest(page, 'meadow_bounty', 'complete'); await quest(page, 'meadow_bounty', 'claim');
  await page.evaluate(() => Quests.show());
  check(await page.evaluate(() => {
    const done = document.querySelector('#quest-list > .quest-completed');
    return done === document.querySelector('#quest-list').lastElementChild && !!done.querySelector('[data-quest="meadow_bounty"][data-status="completed"]');
  }), 'Claimed quests, including repeatable quest history, appear in the final section');
  await page.evaluate(() => Quests.close());
  const marker = await page.evaluate(() => {
    const q = WORLD_MAP.quests.find(q => q.id === 'meadow_bounty');
    return Quests.mapMarkers(0).find(m => m.npc === q.npc);
  });
  check(marker?.repeatable && marker.color === '#64b5ff', 'Available repeatable quest marker is blue');
  const mini = await page.evaluate(id => {
    const original = Quests.mapMarkers, cv = document.getElementById('minimap'), g = cv.getContext('2d');
    try {
      Quests.mapMarkers = zone => original(zone).filter(m => m.npc !== id); Field._debug.drawFrame(4); const a = g.getImageData(0, 0, cv.width, cv.height).data;
      Quests.mapMarkers = original; Field._debug.drawFrame(4); const b = g.getImageData(0, 0, cv.width, cv.height).data;
      let blue = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== b[i] || a[i+1] !== b[i+1] || a[i+2] !== b[i+2]) {
        if (Math.abs(b[i]-100)<20 && Math.abs(b[i+1]-181)<20 && Math.abs(b[i+2]-255)<20) blue++;
      }
      return blue;
    } finally { Quests.mapMarkers = original; }
  }, marker.npc);
  check(mini > 2, 'The actual minimap paints the repeatable marker in blue');
  check(await page.evaluate(() => {
    const q = WORLD_MAP.zones.flatMap(a => a.quests || []).find(q => q.id === 'city_gel');
    Quests.update([{ id: q.id, counts: q.objectives.map(() => 0), claimed: false, completions: 0 }]); Quests.track(q.id);
    const points = q.objectives.flatMap(o => QUEST_SOURCES[o.target] || []).filter(p => p.zone === 0), a = points[0], b = points.at(-1);
    const first = Quests.navigationTarget(0, a.x, a.y), second = Quests.navigationTarget(0, b.x, b.y);
    return first.x === a.x && first.y === a.y && second.x === b.x && second.y === b.y;
  }), 'Navigation reselects real gathering targets as the hero moves, without stale cached coordinates');
  await page.evaluate(() => Online.send({ type: 'use_item', item: 'not_a_real_item' }));
  await page.locator('#hero-errors p').first().waitFor({ state: 'visible' });
  check(await page.evaluate(() => {
    const b = document.getElementById('hero-errors').getBoundingClientRect(), cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect(), [x, y] = Field._debug.w2s(Field.hero.x, Field.hero.y);
    return b.bottom < r.y + y / 1600 * r.width && b.left >= r.left && b.right <= r.right;
  }), 'A real refused action appears in a box above the character');
  await page.evaluate(() => { WorldFeedback.reset(); Field.error('A wall blocks your skill.'); Field.error('A wall blocks your skill.'); });
  check(await page.locator('#hero-errors p').count() === 1, 'Repeated action errors stay readable in one line');
  await screenshot(page, 'todo-hero-error.png');
  await page.waitForTimeout(2600);
  check(await page.locator('#hero-errors').isHidden(), 'Brief error messages expire automatically');
  await page.evaluate(() => {
    Online.send({ type: 'debug', command: { op: 'drop_item', item: 'slime_gel', quantity: 3 } });
    Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: Field.hero.x + 4, y: Field.hero.y } });
  });
  await wait(page, () => Field._debug.drops.some(d => d.item === 'slime_gel'));
  const drop = await page.evaluate(() => Field._debug.drops.find(d => d.item === 'slime_gel'));
  assert.ok(drop, 'The real drop exists');
  await page.waitForTimeout(650);
  const cursor = await page.evaluate(id => {
    const d = Field._debug.drops.find(d => d.id === id), [x,y] = Field._debug.w2s(d.x,d.y), r = document.getElementById('fieldcv').getBoundingClientRect();
    return { x: r.x + (x + 12) / 1600 * r.width, y: r.y + (y - d.z) / 1600 * r.width };
  }, drop.id);
  await page.mouse.move(cursor.x, cursor.y);
  await page.locator('#item-tooltip').waitFor({ state: 'visible' });
  check((await page.locator('#item-tooltip').textContent()).includes('Slime Gel') && (await page.locator('#item-tooltip').textContent()).includes('3 on the ground'), 'Hovering a real ground pile reveals its item and quantity');
  await screenshot(page, 'todo-loot-hover.png');
  await debug(page, { op: 'teleport', zone: 0, x: drop.x, y: drop.y });
  await wait(page, id => !Field._debug.drops.some(d => d.id === id), drop.id);
  check(await page.locator('#item-tooltip').isHidden(), 'Picking up a hovered pile dismisses its tooltip');
  for (const kind of ['oak_tree', 'birch_tree', 'apple_tree', 'willow_tree']) {
    const target = await page.evaluate(kind => {
      const objects = WORLD_MAP.objects;
      for (const o of objects.filter(o => o.kind === kind)) for (const d of [1.5, 2, 2.5, 3]) {
        const x = o.x-d, y = o.y-d;
        if (objects.every(p => p.width ? Math.abs(x-p.x)>p.width/2+.5 || Math.abs(y-p.y)>p.depth/2+.5 : Math.hypot(x-p.x,y-p.y)>p.r+.5)) return { x, y, tree: o };
      }
    }, kind);
    assert.ok(target, `${kind}: clear point behind a real tree`);
    await debug(page, { op: 'teleport', zone: 0, x: target.x, y: target.y });
    await wait(page, target => Math.hypot(Field.hero.x-target.x, Field.hero.y-target.y) < 1, target);
    await wait(page, target => {
      const [x, y] = Field._debug.w2s(target.tree.x, target.tree.y), r = document.getElementById('fieldcv').getBoundingClientRect();
      return x > 350 && x < 1250 && y > 350 && y < r.height / r.width * 1600 - 60;
    }, target);
    const result = await page.evaluate(tree => {
      const cv = document.getElementById('fieldcv'), g = cv.getContext('2d'), original = City.drawObject;
      let faded = false, solid = false;
      City.drawObject = (ctx, o, x, y, alpha) => { if (o.kind === tree.kind && o.x === tree.x && o.y === tree.y) { faded ||= alpha < 1; if (solid) alpha = 1; } return original(ctx, o, x, y, alpha); };
      try {
        Field._debug.drawFrame(4); const a = g.getImageData(0,0,cv.width,cv.height).data;
        solid = true; Field._debug.drawFrame(4); const b = g.getImageData(0,0,cv.width,cv.height).data;
        let changed = 0; for (let i=0;i<a.length;i+=4) if (Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2])>12) changed++;
        return { faded, changed };
      } finally { City.drawObject = original; }
    }, target.tree);
    check(result.faded && result.changed > 250, `${kind} visibly fades in the real renderer when the hero stands behind it (${JSON.stringify(result)})`);
  }
  await page.close();
  const swedish = await player('sv');
  check(await swedish.evaluate(() => {
    const q = WORLD_MAP.zones.flatMap(a => a.quests || []).find(q => q.id === 'crags_onward');
    Quests.update([{ id: q.id, counts: [0], claimed: false, completions: 0 }]); Quests.track(q.id);
    const target = Quests.navigationTarget(0, Field.hero.x, Field.hero.y);
    return !!target?.viaPortal && target.destinationZone === 1 && Quests.mapMarkers(1).some(m => m.quest === q.id);
  }), 'Swedish reach guidance resolves the correct zone using its untranslated identity');
  await swedish.evaluate(() => { WorldFeedback.reset(); Field.error('A wall blocks your skill.'); });
  check((await swedish.locator('#hero-errors').textContent()).includes('vägg'), 'The hero error box translates the action refusal into Swedish');
  check(errors.length === 0, 'No browser errors: ' + errors.join('; '));
  await swedish.close();
  console.log(`todo-feedback-ui: ${checks} focused checks passed; ${world.runDir}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { await browser?.close(); await world.stop(); });
