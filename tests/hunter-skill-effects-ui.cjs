// Ten real Hunter casts on a private server, captured with the real sprite atlases.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-hunter-skill-effects', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const skills = [
  ['powershot', 'skHunterImpact', .08], ['multishot', 'skHunterDraw', .12],
  ['rollaway', 'skHunterRoll', .28], ['piercingarrow', 'skHunterImpact', .04],
  ['huntersmark', 'skHunterBuff', .24], ['explosivearrow', 'skHunterBlast', .18],
  ['rapidfire', 'skHunterBuff', .24], ['rainofarrows', 'skHunterRain', .42],
  ['eaglesight', 'skHunterBuff', .24], ['arrowstorm', 'skHunterStorm', .23],
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
  await page.locator('#cls-hunter').click(); await page.locator('#name').fill('HunterEffects');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && !!Field.hunterSprites, null, { timeout: 60000 });
  const catalog = await page.evaluate(() => WORLD_SKILLS.filter(s => s.class === 'hunter').map(s => ({ id: s.id, icon: s.icon })));
  assert.deepEqual(catalog.map(s => s.id).sort(), skills.map(s => s[0]).sort());
  assert.equal(new Set(catalog.map(s => s.icon)).size, 10);
  const origin = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));

  async function clearNearby() {
    const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 10).map(s => s.id));
    for (const enemy of nearby) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), enemy);
    await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 10));
  }
  async function stageEnemies(count) {
    await clearNearby();
    for (let i = 0; i < count; i++) {
      await page.evaluate(i => Online.send({ type: 'debug', command: {
        op: 'spawn_enemy', kind: i ? 'blue' : 'green', x: Field.hero.x + 2.5 + i * 2, y: Field.hero.y, level: 99 } }), i);
      await page.waitForFunction(i => Field.slimes.filter(s => ['green', 'blue'].includes(s.kind) && s.level === 99 && !s.dead &&
        Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 9).length >= i + 1, i);
    }
  }

  const selected = skills.filter(([id]) => !process.env.HUNTER_SKILL_ONLY || id === process.env.HUNTER_SKILL_ONLY);
  for (const [id, kind, age] of selected) {
    await page.waitForFunction(() => Field._debug.effects.every(e => !e.kind.startsWith('sk')) && Field._debug.bolts.length === 0);
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 1000 } }));
    await page.waitForFunction(() => Field.hero.resource >= 60);
    if (['powershot', 'piercingarrow', 'explosivearrow'].includes(id)) await stageEnemies(id === 'piercingarrow' ? 2 : 1);
    else await clearNearby();
    const frame = await page.evaluate(({ id, kind, age }) => new Promise((resolve, reject) => {
      const initial = new Set(Field._debug.effects), deadline = performance.now() + 8000;
      const target = Field.slimes.find(s => s.kind === 'green' && s.level === 99 && !s.dead &&
        Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 7);
      const fx = target && ['powershot', 'piercingarrow', 'explosivearrow'].includes(id) ? target.x - Field.hero.x : 1;
      const fy = target && ['powershot', 'piercingarrow', 'explosivearrow'].includes(id) ? target.y - Field.hero.y : 0;
      function sample() {
        const matches = Field._debug.effects.filter(e => !initial.has(e) && e.kind === kind &&
          (!['huntersmark', 'rapidfire', 'eaglesight'].includes(id) || e.style === id));
        const effect = matches.find(e => e.t >= age);
        const bolts = Field._debug.bolts.filter(b => b.skill === id);
        if (effect && (id !== 'multishot' || bolts.length === 3)) {
          resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'), age: effect.t,
            radius: effect.r || 0, count: effect.count || 0, bolts: bolts.length,
            impactCount: matches.length, capstone: !!effect.capstone,
            moved: Math.hypot(Field.hero.x - effect.x, Field.hero.y - effect.y),
            buff: Field.hero.buffs?.some(b => b.id === id && b.left > 0) || false }); return;
        }
        if (performance.now() > deadline) { reject(new Error(`${id} ${kind} never reached its capture window`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id, fx, fy });
    }), { id, kind, age });
    if (id === 'multishot') { assert.equal(frame.count, 3); assert.equal(frame.bolts, 3); }
    if (id === 'rollaway') assert.ok(frame.moved > .4, 'Roll Away follows real movement');
    if (id === 'piercingarrow') await page.waitForFunction(() => {
      const impacts = Field._debug.effects.filter(e => e.kind === 'skHunterImpact' && e.style === 'piercingarrow');
      return impacts.length >= 2 && impacts[0].bolt === impacts[1].bolt;
    }, null, { timeout: 3000 });
    if (id === 'explosivearrow') assert.equal(frame.radius, 2.2);
    if (id === 'rainofarrows') assert.equal(frame.radius, 2.8);
    if (id === 'arrowstorm') { assert.equal(frame.radius, 4.2); assert.ok(frame.capstone); }
    if (['huntersmark', 'rapidfire', 'eaglesight'].includes(id)) assert.ok(frame.buff, `${id} persists`);
    const output = path.join(world.artifacts, `hunter-${id}.png`);
    fs.writeFileSync(output, Buffer.from(frame.image.split(',')[1], 'base64'));
    assert.ok(fs.statSync(output).size > 100_000, `${id} captured a real game frame`);
    console.log(`${id}: ${frame.age.toFixed(2)} s, ${frame.bolts} bolts, ${output}`);
    if (id === 'rollaway') {
      await page.evaluate(at => Online.send({ type: 'debug', command: { op: 'teleport', zone: Field.zone, x: at.x, y: at.y } }), origin);
      await page.waitForFunction(at => Math.hypot(Field.hero.x - at.x, Field.hero.y - at.y) < .2, origin);
    }
  }
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${selected.length} Hunter effects passed in a private real-sprite browser: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
