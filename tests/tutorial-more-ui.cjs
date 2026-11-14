// Browser check for TUTORIAL-MORE-STEPS: the twelve later tutorial steps appear when their thing happens, each once, anchored to the control that
// matters, and "Got it" finishes them on the server. Run via: bash scripts/test-touch-bounded.sh tests/tutorial-more-ui.cjs
// MUTATE=1 serves the previous tutorial.js (only the first six steps) and must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
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

const FIRST_SIX = ['first_quest', 'levelup_stats', 'equip_gear', 'new_skill', 'consumables', 'merchant'];
const LATER = ['target_attack', 'loot', 'quest_turnin', 'first_death', 'map', 'spark_travel', 'elite', 'rested', 'repair', 'bags_full', 'mail_bank', 'party_mercs'];

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
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message));
    if (process.env.MUTATE === '1') {
      const old = execFileSync('git', ['show', '0106bebd:client/tutorial.js'], { cwd: root, encoding: 'utf8' });
      await page.route('**/tutorial.js*', route => route.fulfill({ contentType: 'text/javascript', body: old }));
    }
    await page.addInitScript(() => {
      window.AudioContext = undefined; window.webkitAudioContext = undefined;
      localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, uiSet: true, ui: {}, panelSizeSet: true, panelSize: {}, char: null, draft: null }));
    });
    await page.goto(world.url);
    await page.locator('#start').click();
    await page.locator('#login-guest').click();
    await page.locator('#name').fill('Tutor');
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero?.hp > 0, null, { timeout: 60000 });
    if (await page.locator('#low-gfx-dismiss').isVisible()) await page.locator('#low-gfx-dismiss').click();
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    await debug({ op: 'teleport', zone: 0, x: 250, y: 167 });
    await page.waitForFunction(() => Math.hypot(Field.hero.x - 250, Field.hero.y - 167) < 3);

    // Every snapshot passes through an override, so a test can say "the hero has a rested reserve" without waiting for a day offline.
    await page.evaluate(({ six }) => {
      window.__override = {};
      const original = Tutorial.onSnapshot;
      Tutorial.onSnapshot = own => { window.__own = own; return original(own ? { ...own, ...window.__override } : own); };
      window.__six = six;
    }, { six: FIRST_SIX });
    const start = async (id, override) => {
      // Everything except the step under test counts as done, so only that step can show.
      const others = [...FIRST_SIX, ...LATER.filter(x => x !== id)];
      await page.evaluate(([o, others]) => { window.__override = { tutorialDone: others, tutorialDisabled: false, ...o }; Tutorial.onSnapshot(window.__own); }, [override, others]);
    };
    const active = () => page.evaluate(() => Tutorial.state().active?.id || null);
    const expectStep = async (id, override, targetId, why) => {
      await start(id, override);
      await page.waitForFunction(id => Tutorial.state().active?.id === id, id, { timeout: 8000 }).catch(() => {});
      const state = await page.evaluate(() => Tutorial.state());
      if (!state.active) console.log('DEBUG', JSON.stringify(await page.evaluate(() => ({ st: Tutorial.state(), cut: !!Cutscene.active, sceneHidden: document.getElementById('scene-game')?.hidden, dead: Field.hero.dead, ghost: Field.hero.ghost, own: window.__own && { rested: window.__own.rested, td: window.__own.tutorialDisabled, hp: window.__own.hp }, modals: ['pause','settings-panel','whats-new','worldmap','equipment','npc-dialogue','quest-journal'].filter(id => { const e = document.getElementById(id); return e && !e.hidden && e.getBoundingClientRect().width > 4; }) }))));
      check(state.active?.id === id, `${why}: step ${id} is shown (got ${JSON.stringify(state.active)})`);
      if (targetId) check(state.active.targetId === targetId, `${id} points at #${targetId} (got ${state.active.targetId})`);
      check(await page.locator('#tutorial-tip').isVisible(), `${id}: the tip is on screen`);
      return state;
    };

    await start('none', {});
    check((await active()) === null, 'with all steps done nothing is shown');

    // Services and social, driven by state the snapshot or the page already carries.
    await expectStep('rested', { rested: { percent: 40 } }, 'xp-meter', 'a rested reserve');
    await expectStep('bags_full', { bagUsed: 16, bagCapacity: 16 }, 'inventory-open', 'full bags');
    await page.evaluate(() => { document.getElementById('inventory-open').dataset.gear = 'broken'; });
    await expectStep('repair', {}, 'inventory-open', 'a broken worn piece');
    await page.evaluate(() => { document.getElementById('inventory-open').dataset.gear = 'ok'; });
    await expectStep('first_death', { ghost: true }, null, 'a ghost');
    const dead = await page.evaluate(() => Tutorial.state().active.body);
    check(/Resurrect/.test(dead) && /Spirit Guide/.test(dead), 'the ghost step explains Resurrect and the Spirit Guide');
    await page.evaluate(() => Object.defineProperty(Quests, 'anyReady', { get: () => true, configurable: true }));
    await expectStep('quest_turnin', {}, null, 'a quest ready to hand in');
    await page.evaluate(() => Object.defineProperty(Quests, 'anyReady', { get: () => false, configurable: true }));
    await page.evaluate(() => { Social.state.incoming = [{ kind: 'party', id: 'someone', name: 'Someone' }]; });
    await expectStep('party_mercs', {}, 'social-open', 'a party invitation');
    await page.evaluate(() => { Social.state.incoming = []; });
    await expectStep('map', { quests: [{ id: 'x', counts: [0], claimed: false }], level: 3 }, 'wm-open', 'a quest in the journal');

    // World things near the hero: a real enemy, an elite, drops on the ground, a mailbox and a travel master.
    await debug({ op: 'spawn_enemy', kind: 'green', x: 252, y: 169 });
    await page.waitForFunction(() => Field.slimes.some(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 9));
    const fight = await expectStep('target_attack', {}, null, 'an enemy in reach');
    check(/target|Tap an enemy|Click an enemy/.test(fight.active.body), 'the fight step says how to target an enemy');
    // "Got it" finishes the step on the server for good.
    await page.locator('#tutorial-gotit').click();
    await page.waitForFunction(() => Tutorial.state().done.includes('target_attack'));
    check(await page.evaluate(() => Tutorial.state().done.includes('target_attack')), 'Got it marks the step done');
    await page.waitForTimeout(400);
    check((await active()) !== 'target_attack', 'a finished step does not come back');
    await debug({ op: 'kill_enemy', id: await page.evaluate(() => Field.slimes.find(s => !s.dead)?.id) });

    for (const [kind, id] of [['mail', 'mail_bank'], ['travel', 'spark_travel']]) {
      const npc = await page.evaluate(k => {
        const map = WORLD_MAP;
        const hit = n => k === 'mail' ? n.art === 'mailbox' || (n.offers || []).some(o => ['mail', 'bank'].includes(o.id)) : String(n.id).startsWith('travel_') || (n.offers || []).some(o => o.id === 'travel');
        return (map.npcs || []).find(hit) || null;
      }, kind);
      check(!!npc, `Greenmeadow has a ${kind} NPC`);
      await debug({ op: 'teleport', zone: 0, x: npc.x, y: npc.y + 1.2 });
      await page.waitForFunction(n => Math.hypot(Field.hero.x - n.x, Field.hero.y - n.y) < 3, npc);
      await expectStep(id, {}, 'wm-open', `standing by the ${kind} NPC`);
    }

    // Once per character: every id is accepted by the server and none is shown twice.
    await page.evaluate(all => { for (const id of all) Tutorial.complete(id); }, LATER);
    await page.waitForFunction(all => all.every(id => Tutorial.state().done.includes(id)), LATER);
    check(true, 'the server accepted all twelve ids (they are in the milestone list)');

    assert.equal(errors.length, 0, `Page errors: ${errors.join('; ')}`);
    await ctx.close();
    console.log(`PASS tutorial-more-ui (${checks} checks)`);
  } finally {
    await browser.close().catch(() => {});
    await world.stop().catch(() => {});
  }
})().catch(err => { console.error(err); process.exit(1); });
