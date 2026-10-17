// Every warrior effect is captured from a real server cast in a private real-sprite browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-warrior-skill-effects', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

const skills = [
  ['cleave', 'skCleave', 1.9],
  ['whirlwind', 'warWhirl', 2.4],
  ['groundslam', 'warSlam', 3.4],
  ['earthshatter', 'skWarFissure', 4.8],
  ['titanswrath', 'warTitan', 6],
  ['charge', 'skWarCharge', null],
  ['battlecry', 'skWarCry', null],
  ['shieldwall', 'skWarShield', null],
  ['berserk', 'skWarBerserk', null],
  ['secondwind', 'skWarHeal', null],
];

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('WarriorEffects');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && !!Field.warriorSprites, null, { timeout: 60000 });
  const catalog = await page.evaluate(() => WORLD_SKILLS.filter(s => s.class === 'warrior').map(s => ({ id: s.id, icon: s.icon, description: s.description })));
  assert.deepEqual(catalog.map(s => s.id).sort(), skills.map(s => s[0]).sort(), 'All ten warrior skills have a catalog entry');
  assert.equal(new Set(catalog.map(s => s.icon)).size, 10, 'All warrior skills have distinct icons');
  assert.ok(catalog.every(s => s.description.length > 30), 'All warrior skills describe their purpose');

  for (const [id, visual, reach] of skills.filter(([id]) => !process.env.WARRIOR_SKILL_ONLY || id === process.env.WARRIOR_SKILL_ONLY)) {
    await page.waitForFunction(() => Field._debug.effects.every(e => !e.kind.startsWith('sk')));
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 100 } }));
    await page.waitForFunction(() => Field.hero.resource >= 40);
    if (id === 'secondwind' || id === 'titanswrath') {
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_hp', hp: Field.hero.maxHp * .4 } }));
      await page.waitForFunction(() => Field.hero.hp < Field.hero.maxHp * .5);
    }
    if (id === 'titanswrath') {
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'spawn_enemy', kind: 'green',
        x: Field.hero.x + 2, y: Field.hero.y, level: 99 } }));
      await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 4));
    }
    const frame = await page.evaluate(({ id, visual }) => new Promise((resolve, reject) => {
      const initial = new Set(Field._debug.effects), deadline = performance.now() + 6000;
      function sample() {
        const effect = Field._debug.effects.find(e => !initial.has(e) && (visual.startsWith('war') ? e.kind === 'skNova' && e.style === visual : e.kind === visual));
        if (effect && effect.t >= .19 && effect.t <= .38) {
          resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'),
            kind: effect.kind, style: effect.style || '', reach: effect.r || null,
            heal: Field._debug.effects.find(e => !initial.has(e) && e.kind === 'skWarTitanCore')?.heal || 0, age: effect.t });
          return;
        }
        if (performance.now() > deadline) { reject(new Error(`${id} server effect did not reach the capture window`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id, fx: 1, fy: 0 });
    }), { id, visual });
    if (reach !== null) assert.equal(frame.reach, reach, `${id} uses the catalog reach`);
    if (['battlecry', 'shieldwall', 'berserk'].includes(id))
      await page.waitForFunction(skill => Field.hero.buffs?.some(buff => buff.id === skill && buff.left > 0), id);
    if (id === 'secondwind')
      await page.waitForFunction(() => Field.hero.hp > Field.hero.maxHp * .7);
    if (id === 'titanswrath') {
      const state = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, hp: Field.hero.hp, maxHp: Field.hero.maxHp,
        nearby: Field.slimes.filter(s => s.kind === 'green' && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 7)
          .map(s => ({ x: s.x, y: s.y, hp: s.hp, level: s.level })) }));
      assert.ok(frame.heal > 0, `Titan's Wrath shows the actual healing return: ${JSON.stringify({ heal: frame.heal, state })}`);
    }
    const output = path.join(world.artifacts, `warrior-${id}.png`);
    fs.writeFileSync(output, Buffer.from(frame.image.split(',')[1], 'base64'));
    assert.ok(fs.statSync(output).size > 100_000, `${id} captured a real game frame`);
    console.log(`${id}: ${frame.kind}${frame.style ? '/' + frame.style : ''}, ${frame.age.toFixed(2)} s, ${output}`);
  }
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`10 warrior skill effects passed in a real-sprite private browser: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
