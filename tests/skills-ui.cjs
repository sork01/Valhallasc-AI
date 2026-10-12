// Learned skills and the level-up spectacle in a real browser. A level-20 mage (VALHALLA_START_LEVEL is a test-server
// switch) casts through the real bar; the level-up fixture is display-only: it feeds the client the event the server sends.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-skills-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const MAGE = ['attack', 'twinbolt', 'arcaneward', 'fireball', 'barrage', 'blink', 'chainlightning', 'meteor', 'lifedrain', 'arcanestorm', 'starfall'];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_START_LEVEL: '20' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false, char: null, draft: null })); });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('Archmage'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.mageSprites && Field.hero.level === 20 && document.querySelectorAll('#skillbar-slots button').length === 12, null, { timeout: 60000 });
  await page.evaluate(() => {
    window.sent = []; const original = Online.send; Online.send = message => { if (message.type === 'skill') sent.push(message); return original(message); };
  });

  // --- the bar holds every learned skill, in unlock order ---
  const slots = await page.locator('#skillbar-slots button').evaluateAll(b => b.map(x => x.dataset.skill));
  check(JSON.stringify(slots) === JSON.stringify([...MAGE, '']), 'A level-20 character starts with all eleven abilities in unlock order and slot 12 empty');
  check(await page.locator('#character-attributes [data-stat="intellect"] b').textContent().then(t => t.includes('9 passive')), 'The character sheet includes earned passive Intellect from the server');
  check(await page.locator('#skillbar-slots kbd').allTextContents().then(k => k.join('') === '1234567890-='), 'The twelve slots are keyed 1-9, 0, minus and equals');
  await page.keyboard.press('k');
  check(await page.locator('#skill-library [data-skill]').count() === 11 && await page.locator('#skill-library [data-skill].locked').count() === 0, 'All active skills are unlocked at level 20');
  check(await page.locator('#skill-library [data-passive]').count() === 9 && await page.locator('#skill-library [data-passive].locked').count() === 7, 'The library shows two earned and seven future mage passives');
  check(await page.locator('#skill-library [data-passive="mage_milestone_20"] small').textContent().then(t => t.includes('Intellect')), 'The level-20 passive explains its automatic stat effect');
  check(await page.locator('#skill-library [data-skill="starfall"] .skill-level').textContent() === 'Lv 20', 'Each card names the level that unlocks it');
  check(await page.locator('#skill-library [data-skill="twinbolt"] small').textContent().then(t => t.includes('Next rank 2 at level 22')), 'The library previews the next rank');
  const panel = await page.locator('.skills-panel').boundingBox(), library = await page.locator('#skill-library').boundingBox();
  check(library.x >= panel.x && library.x + library.width <= panel.x + panel.width + 1, 'The library fits inside the skills panel');
  await page.screenshot({ path: path.join(world.artifacts, 'skills-panel-level20.png') });
  await page.keyboard.press('k');

  // --- casting through the real bar: the server answers with cooldowns and buffs ---
  await page.keyboard.press('2');
  await page.waitForFunction(() => Field.hero.skillCd?.twinbolt > 0);
  check(await page.evaluate(() => sent.at(-1).id === 'twinbolt' && Number.isFinite(sent.at(-1).fx)), 'Slot 2 sends the learned skill with an aim direction');
  check(await page.locator('#skillbar-slots [data-slot="2"]').isDisabled() && await page.locator('#skillbar-slots [data-slot="2"] .skill-cooldown').textContent().then(Boolean), 'The slot shows the server cooldown');
  const before = await page.evaluate(() => sent.length);
  await page.keyboard.press('2'); await page.waitForTimeout(150);
  check(await page.evaluate(n => sent.length === n, before), 'A skill on cooldown sends nothing');
  await page.keyboard.press('3');
  await page.waitForFunction(() => Field._debug.effects.some(e => e.kind === 'skAura'));
  await page.waitForFunction(() => Field.hero.buffs?.some(b => b.id === 'arcaneward'));
  check(await page.locator('#buff-bar [data-buff="arcaneward"]').isVisible() && Number(await page.locator('#buff-bar [data-buff="arcaneward"] i').textContent()) >= 7, 'Arcane Ward shows in the effects bar with its seconds left');
  check(await page.evaluate(() => Field._debug.effects.some(e => e.kind === 'skAura')), 'Casting a buff starts an aura effect');
  await page.keyboard.press('8');
  await page.waitForFunction(() => Field._debug.effects.some(e => e.kind === 'skMeteor'));
  check(await page.evaluate(() => { const m = Field._debug.effects.find(e => e.kind === 'skMeteor'); return m.r === 2.6 && Number.isFinite(m.x); }), 'Meteor draws a falling star at its authoritative impact point');
  await page.keyboard.press('10'.slice(0, 1)); // key 1 is the basic attack: it stays usable beside learned skills
  await page.keyboard.press('0');
  await page.waitForFunction(() => Field._debug.effects.some(e => e.kind === 'skNova' && e.r === 5), null, { timeout: 5000 });
  check(await page.evaluate(() => sent.some(m => m.id === 'arcanestorm')), 'Slot 0 casts Arcane Storm and draws its five-unit nova');
  await page.keyboard.press('-');
  await page.waitForFunction(() => Field.hero.skillCd?.starfall > 0);
  check(await page.evaluate(() => sent.some(m => m.id === 'starfall')), 'Slot 11 (minus) casts Starfall');
  await page.waitForTimeout(450);
  await page.screenshot({ path: path.join(world.artifacts, 'skills-cast-nova.png') });
  const n = await page.evaluate(() => sent.length);
  await page.keyboard.press('='); await page.waitForTimeout(150);
  check(await page.evaluate(k => sent.length === k, n), 'The empty twelfth slot casts nothing');
  const bar = await page.locator('#skillbar').boundingBox();
  check(bar.x >= 0 && bar.x + bar.width <= 1440, 'The twelve-slot bar fits the viewport');
  await page.setViewportSize({ width: 800, height: 450 });
  const small = await page.locator('#skillbar').boundingBox();
  check(small.x >= 0 && small.x + small.width <= 800, 'The twelve-slot bar fits a small landscape phone');
  await page.setViewportSize({ width: 1440, height: 900 });

  // --- other players' level-ups: effects only, no banner ---
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: 'someone-else', x: Field.hero.x + 3, y: Field.hero.y, value: 1, level: 5, unlocked: [] }));
  check(await page.evaluate(() => ['luPillar', 'luRays'].every(k => Field._debug.effects.some(e => e.kind === k)) && Field._debug.effects.filter(e => e.kind === 'ring').length >= 4), "Another player's level-up shows the pillar, rays and four rings");
  check(await page.locator('#levelup-banner').isHidden(), 'Their level-up shows no banner on this screen');

  // --- our own level-up: banner, flash, new-skill panel ---
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 21, unlocked: ['starfall'] }));
  await page.waitForTimeout(400);
  check(await page.locator('#levelup-banner').isVisible(), 'Your own level-up opens the banner');
  check(await page.locator('.lu-title').textContent() === 'LEVEL UP!' && await page.locator('#lu-level').textContent() === 'Level 21', 'The banner states the new level');
  check(await page.locator('#lu-skills .lu-skill b').allTextContents().then(t => t.join() === 'New skill: Starfall'), 'The banner announces the unlocked skill');
  const look = await page.evaluate(() => {
    const css = sel => getComputedStyle(document.querySelector(sel));
    return { banner: css('#levelup-banner').pointerEvents, title: +css('.lu-title').opacity, skill: +css('.lu-skill').opacity, size: parseFloat(css('.lu-title').fontSize), hud: document.getElementById('hud-lv').classList.contains('lv-pop') };
  });
  check(look.banner === 'none' && look.title >= .95 && look.skill >= .95 && look.size > 50 && look.hud, `The banner is large and fully visible, never blocks the game, and the HUD level pops (${JSON.stringify(look)})`);
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 22, unlocked: ['twinbolt'] }));
  check(await page.locator('#lu-skills .lu-skill b').textContent() === 'Rank 2: Twin Bolt', 'The banner announces a rank without treating it as a new skill');
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 40, unlocked: ['twinbolt', 'twinbolt'] }));
  check(await page.locator('#lu-skills .lu-skill b').allTextContents().then(t => t.join('|') === 'New skill: Twin Bolt|Rank 2: Twin Bolt'), 'A multi-level jump distinguishes a new skill from its rank');
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 42, unlocked: ['twinbolt'] }));
  check(await page.locator('#lu-skills .lu-skill b').textContent() === 'Rank 3: Twin Bolt', 'The next rotation announces rank 3');
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 62, unlocked: ['twinbolt'] }));
  check(await page.locator('#lu-skills .lu-skill b').textContent() === 'Rank 4: Twin Bolt', 'The level-62 rotation announces rank 4');
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 82, unlocked: ['twinbolt'] }));
  check(await page.locator('#lu-skills .lu-skill b').textContent() === 'Rank 5: Twin Bolt', 'The level-82 rotation announces rank 5');
  await page.evaluate(() => Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 90, unlocked: ['mage_milestone_90'] }));
  check(await page.locator('#lu-skills .lu-skill b').textContent() === 'New passive: Infinite Thesis', 'The banner announces a new automatic passive');
  await page.screenshot({ path: path.join(world.artifacts, 'levelup-reduced-motion.png') });
  await page.waitForFunction(() => document.getElementById('levelup-banner').hidden, null, { timeout: 8000 });
  check(await page.locator('#levelup-flash').evaluate(n => !n.classList.contains('show')), 'The banner and flash leave by themselves');

  // --- full motion: the real animation ---
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  // Sample the flash on every frame: its peak, not one instant, shows whether the screen really lights up.
  const peak = await page.evaluate(() => new Promise(resolve => {
    Field._debug.event({ type: 'event', kind: 'levelup', actor: Online.id, x: Field.hero.x, y: Field.hero.y, value: 1, level: 22, unlocked: [] });
    const flash = document.getElementById('levelup-flash'), start = performance.now(); let max = 0;
    const tick = () => { max = Math.max(max, +getComputedStyle(flash).opacity); performance.now() - start < 900 ? requestAnimationFrame(tick) : resolve(max); };
    tick();
  }));
  check(peak > .75, `The screen flashes gold as the level-up lands (peak opacity ${peak.toFixed(2)})`);
  await page.screenshot({ path: path.join(world.artifacts, 'levelup-flash.png') });
  await page.waitForTimeout(600);
  const full = await page.evaluate(() => ({ title: +getComputedStyle(document.querySelector('.lu-title')).opacity, rays: getComputedStyle(document.querySelector('.lu-rays')).animationName, shown: !document.getElementById('levelup-banner').hidden }));
  check(full.shown && full.title === 1 && full.rays.includes('lu-rays'), 'The full-motion banner settles with spinning rays behind it');
  check(await page.locator('#lu-hint').textContent() === 'Fully healed · spend stat points in Character (E)', 'A level without a new skill points to stat points instead');
  await page.screenshot({ path: path.join(world.artifacts, 'levelup-full.png') });
  // Five high-level reworks have distinct display paths while their IDs remain valid on the bar.
  const looks = await page.evaluate(() => {
    const result = {};
    for (const [skill, value] of [['earthshatter', 4.8], ['starfall', 6.5], ['thousandcuts', 3.7], ['guardianlight', 0.65], ['arrowstorm', 4.2]]) {
      Field._debug.event({ type: 'event', kind: 'skill', actor: Online.id, skill, x: Field.hero.x, y: Field.hero.y, fx: 1, fy: 0, value, points: [] });
      result[skill] = Field._debug.effects.slice(-15).map(e => ({ kind: e.kind, style: e.style, stars: e.stars?.length }));
    }
    return result;
  });
  check(looks.earthshatter.some(e => e.kind === 'skCone') && looks.earthshatter.some(e => e.style === 'cracks'), 'Earthshatter sweeps a directional fissure');
  check(looks.starfall.some(e => e.kind === 'skMeteor') && looks.starfall.some(e => e.stars === 28), 'Starfall paints a distant celestial impact');
  check(looks.thousandcuts.filter(e => e.kind === 'skCut').length >= 10, 'Thousand Cuts fans out ten blade trails');
  check(looks.guardianlight.some(e => e.kind === 'skBeam'), 'Guardian Light shows a sanctuary beam');
  check(looks.arrowstorm.some(e => e.style === 'arrows'), 'Arrow Storm draws outward arrows');
  await page.evaluate(() => Online.send({ type: 'debug', ref: 912, command: { op: 'set_level', level: 99 } }));
  await page.waitForFunction(() => Field.hero.level === 99);
  await page.evaluate(() => Online.saveSkillSlots(['attack', 'starfall', 'twinbolt', null, null, null, null, null, null, null, null, null], 99));
  await page.evaluate(() => Online.stop());
  for (let n = 0; n < 100; n++) { if ((await (await fetch(world.url + 'health')).json()).online === 0) break; await new Promise(resolve => setTimeout(resolve, 100)); }
  await page.reload(); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && document.querySelectorAll('#skillbar-slots button').length === 12, null, { timeout: 60000 });
  check(await page.locator('#skillbar-slots button').evaluateAll(b => b.slice(0, 3).map(x => x.dataset.skill).join(',') === 'attack,starfall,twinbolt'), 'An existing high-level character keeps its saved skillbar order');
  check(await page.evaluate(() => Field.hero.passiveAttributes.intellect > 0), 'Earned passives are derived from the resumed level');
  await page.keyboard.press('k');
  check(await page.locator('#skill-library [data-skill="starfall"] small').textContent().then(t => t.includes('Capstone')), 'The resumed level-99 mage has its capstone rank');
  await page.keyboard.press('k');
  check(errors.length === 0, `No page errors: ${errors.join('; ')}`);
  console.log(`${checks} learned-skill and level-up UI checks passed; screenshots: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
