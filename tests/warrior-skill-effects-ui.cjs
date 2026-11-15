// Every warrior effect is captured from a real server cast in a private real-sprite browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, STUB } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-warrior-skill-effects', version: '1.0.0' });
let browser, started = false;
// Every effect is captured from the real artwork (the stub has no frames to draw).
if (STUB) throw new Error('warrior-skill-effects-ui captures real artwork: run with REAL_SPRITES=1');
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
  // A new hero stands on the Saltby pier, beside a wall: move to open ground so the level-99 spawn lands next to it.
  await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 250, y: 235 } }));
  await page.waitForFunction(() => Field.zone === 0 && Math.hypot(Field.hero.nx - 250, Field.hero.ny - 235) < 8, null, { timeout: 30000 });
  await page.waitForTimeout(1500); // let the camera settle on the hero before any spawn is placed beside it
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
      // Debug replies only reach window.GM.onReply: capture them so a refused spawn says why.
    await page.evaluate(() => { window.debugReplies = []; window.GM = Object.assign(window.GM || {}, { onReply: p => debugReplies.push(p) }); });
    // One resend if the first request gets no answer; the reply is checked below.
      let spawned = false;
      for (let attempt = 0; attempt < 2 && !spawned; attempt++) {
        await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'spawn_enemy', kind: 'green',
          x: Field.hero.x + 2, y: Field.hero.y, level: 99 } }));
        spawned = await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 4), null, { timeout: 8000 }).then(() => true, () => false);
      }
      if (!spawned) throw new Error(`titanswrath: the level-99 green spawn did not appear (server replies: ${JSON.stringify(await page.evaluate(() => debugReplies))}; hero ${JSON.stringify(await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y, zone: Field.zone })))}; level99 ${JSON.stringify(await page.evaluate(() => Field.slimes.filter(s => s.level === 99 || s.id === 0).map(s => ({ id: s.id, kind: s.kind, x: s.x, y: s.y, nx: s.nx, ny: s.ny, level: s.level, dead: s.dead }))))}; slimes ${await page.evaluate(() => Field.slimes.length)})`);
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
