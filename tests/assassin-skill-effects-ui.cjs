// Real server casts and real sprites: one capture for every active Assassin skill.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-assassin-skill-effects', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

const skills = [
  ['throwingknives', 'skAssassinCast', .16],
  ['evasion', 'skAssassinBuff', .22],
  ['lunge', 'skAssassinLunge', .22],
  ['flurry', 'skAssassinFlurry', .12],
  ['shadowveil', 'skAssassinBuff', .22],
  ['cycloneblades', 'skNova', .20],
  ['assassinate', 'skAssassinAssassinate', .34],
  ['deadlyfocus', 'skAssassinBuff', .22],
  ['knifering', 'skAssassinCast', .24],
  ['thousandcuts', 'skAssassinFan', .24],
];

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-assassin').click(); await page.locator('#name').fill('AssassinEffects');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && !!Field.assassinSprites, null, { timeout: 60000 });
  const catalog = await page.evaluate(() => WORLD_SKILLS.filter(s => s.class === 'assassin').map(s => ({ id: s.id, icon: s.icon })));
  assert.deepEqual(catalog.map(s => s.id).sort(), skills.map(s => s[0]).sort());
  assert.equal(new Set(catalog.map(s => s.icon)).size, 10);

  const selected = skills.filter(([id]) => !process.env.ASSASSIN_SKILL_ONLY || id === process.env.ASSASSIN_SKILL_ONLY);
  for (const [id, kind, age] of selected) {
    await page.waitForFunction(() => Field._debug.effects.every(e => !e.kind.startsWith('sk')) && Field._debug.bolts.length === 0);
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 1000 } }));
    await page.waitForFunction(() => Field.hero.resource >= 60);
    if (id === 'knifering') {
      const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 9).map(s => s.id));
      for (const enemy of nearby) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), enemy);
      await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 9));
    }
    if (['flurry', 'assassinate', 'lunge'].includes(id)) {
      const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 6).map(s => s.id));
      for (const enemy of nearby) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), enemy);
      await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 6));
      await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'spawn_enemy', kind: id === 'flurry' ? 'gloomroot' : 'green',
        x: Field.hero.x + (id === 'flurry' ? 1.4 : 2.4), y: Field.hero.y, level: 99 } }), id);
      await page.waitForFunction(id => Field.slimes.some(s => s.kind === (id === 'flurry' ? 'gloomroot' : 'green') && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 5), id);
    }
    const frame = await page.evaluate(({ id, kind, age }) => new Promise((resolve, reject) => {
      const initial = new Set(Field._debug.effects), deadline = performance.now() + 8000;
      const needBolts = id === 'throwingknives' ? 3 : id === 'knifering' ? 12 : 0;
      const target = Field.slimes.find(s => s.kind === (id === 'flurry' ? 'gloomroot' : 'green') && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 5);
      const fx = target && ['lunge', 'flurry', 'assassinate'].includes(id) ? target.x - Field.hero.x : 1;
      const fy = target && ['lunge', 'flurry', 'assassinate'].includes(id) ? target.y - Field.hero.y : 0;
      function sample() {
        const matching = Field._debug.effects.filter(e => !initial.has(e) && e.kind === kind &&
          (id !== 'cycloneblades' || e.style === 'assassinCyclone') &&
          (id !== 'flurry' || e.index >= 1));
        const effect = matching.find(e => e.t >= age);
        const bolts = Field._debug.bolts.filter(b => b.skill === id).length;
        if (effect && (!needBolts || bolts === needBolts)) {
          resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'), kind: effect.kind,
            age: effect.t, radius: effect.r || 0, arc: effect.arc || 0, count: effect.count || effect.total || 0,
            bolts, moved: Math.hypot(Field.hero.x - effect.x, Field.hero.y - effect.y),
            buff: Field.hero.buffs?.some(b => b.id === id && b.left > 0) || false }); return;
        }
        if (performance.now() > deadline) { reject(new Error(`${id} effect ${kind} did not reach its capture window`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id, fx, fy });
    }), { id, kind, age });
    if (id === 'throwingknives') assert.equal(frame.bolts, 3);
    if (id === 'knifering') assert.equal(frame.bolts, 12);
    if (id === 'lunge') assert.ok(frame.moved > .4, 'Lunge shows observed player movement');
    if (id === 'flurry') assert.equal(frame.count, 4, 'Flurry rendered four real target hits');
    if (id === 'cycloneblades') assert.equal(frame.radius, 2.6);
    if (id === 'thousandcuts') { assert.equal(frame.radius, 3.7); assert.ok(frame.arc > 3); }
    if (['evasion', 'shadowveil', 'deadlyfocus'].includes(id)) assert.ok(frame.buff, `${id} has an active persistent marker`);
    const output = path.join(world.artifacts, `assassin-${id}.png`);
    fs.writeFileSync(output, Buffer.from(frame.image.split(',')[1], 'base64'));
    assert.ok(fs.statSync(output).size > 100_000, `${id} captured a real game frame`);
    if (id === 'flurry') {
      const colossus = await page.evaluate(() => Field.slimes.find(s => s.kind === 'gloomroot' && s.level === 99 && !s.dead)?.id);
      if (colossus !== undefined) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), colossus);
    }
    console.log(`${id}: ${frame.kind}, ${frame.age.toFixed(2)} s, ${output}`);
  }
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${selected.length} Assassin skill effects passed in a real-sprite private browser: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
