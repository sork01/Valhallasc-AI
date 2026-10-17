// Real Priest casts, two real party members, and real sprites in a private browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-priest-skill-effects', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
const skills = [
  ['mend', 'skPriestMend', .26],
  ['smite', 'skPriestSmite', .25],
  ['prayer', 'skPriestPrayer', .24],
  ['holynova', 'skPriestNova', .28],
  ['guardianlight', 'skPriestSanctuary', .32],
  ['searinglight', 'skPriestSearing', .38],
  ['divinehymn', 'skPriestHymn', .44],
  ['heavenswrath', 'skPriestNova', .34],
  ['wardoflight', 'skPriestBuff', .24],
  ['blessing', 'skPriestBuff', .25],
];
const allies = ['PriestAllyA', 'PriestAllyB'];

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  for (const bot of allies) await call('connect_bot', { bot, class: 'warrior' });
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-priest').click(); await page.locator('#name').fill('PriestEffects');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && !!Field.priestSprites, null, { timeout: 60000 });
  const catalog = await page.evaluate(() => WORLD_SKILLS.filter(s => s.class === 'priest').map(s => ({ id: s.id, icon: s.icon })));
  assert.deepEqual(catalog.map(s => s.id).sort(), skills.map(s => s[0]).sort());
  assert.equal(new Set(catalog.map(s => s.icon)).size, 10);
  const caster = await page.evaluate(() => ({ id: Online.id, x: Field.hero.x, y: Field.hero.y }));
  for (const bot of allies) {
    await page.evaluate(name => Online.send({ type: 'social', command: { op: 'party_invite', name } }), bot);
    await page.waitForFunction(() => Social.state.outgoing.some(i => i.kind === 'party'));
    const accepted = await call('social', { bot, command: { op: 'party_accept', id: caster.id } });
    assert.ok(accepted.notices.some(n => n.ok), `${bot} joined the party: ${JSON.stringify(accepted.notices)}`);
  }
  await page.waitForFunction(() => Social.state.party?.members.length === 3);
  const positions = [{ x: caster.x + 3, y: caster.y + 1 }, { x: caster.x + 2, y: caster.y - 3 }];
  for (let i = 0; i < allies.length; i++) {
    const moved = await call('teleport', { bot: allies[i], to: positions[i] });
    assert.ok(Math.hypot(moved.player.x - caster.x, moved.player.y - caster.y) < 7.5, `${allies[i]} is in Priest skill range`);
  }

  async function wound(includeCaster = true, onlyFirst = false) {
    for (const bot of (onlyFirst ? allies.slice(0, 1) : allies)) await call('set_health', { bot, hp: 1 });
    if (includeCaster) {
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_hp', hp: Field.hero.maxHp * .28 } }));
      await page.waitForFunction(() => Field.hero.hp < Field.hero.maxHp * .4);
    }
  }
  async function stageEnemy() {
    const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 8).map(s => s.id));
    for (const enemy of nearby) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), enemy);
    await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 8));
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'spawn_enemy', kind: 'green', x: Field.hero.x + 3.2, y: Field.hero.y, level: 99 } }));
    await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 6));
  }

  const selected = skills.filter(([id]) => !process.env.PRIEST_SKILL_ONLY || id === process.env.PRIEST_SKILL_ONLY);
  for (const [id, kind, age] of selected) {
    if (id === 'blessing') await page.waitForFunction(() => !Field.hero.buffs?.some(b => b.id === 'wardoflight'), null, { timeout: 15000 });
    await page.waitForFunction(() => Field._debug.effects.every(e => !e.kind.startsWith('sk')));
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 1000 } }));
    await page.waitForFunction(() => Field.hero.resource >= 60);
    if (id === 'mend') await wound(false, true);
    if (['prayer', 'holynova', 'divinehymn', 'heavenswrath'].includes(id)) await wound();
    if (['guardianlight', 'searinglight'].includes(id)) await wound(true, true);
    if (['smite', 'holynova', 'searinglight', 'heavenswrath'].includes(id)) await stageEnemy();
    const frame = await page.evaluate(({ id, kind, age }) => new Promise((resolve, reject) => {
      const initial = new Set(Field._debug.effects), deadline = performance.now() + 8000;
      const target = Field.slimes.find(s => s.kind === 'green' && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 6);
      const fx = target && ['smite', 'searinglight', 'holynova', 'heavenswrath'].includes(id) ? target.x - Field.hero.x : 1;
      const fy = target && ['smite', 'searinglight', 'holynova', 'heavenswrath'].includes(id) ? target.y - Field.hero.y : 0;
      function sample() {
        const effect = Field._debug.effects.find(e => !initial.has(e) && e.kind === kind && e.t >= age &&
          (!['wardoflight', 'blessing'].includes(id) || e.style === id) &&
          (!['holynova', 'heavenswrath'].includes(id) || e.style === (id === 'holynova' ? 'holy' : 'wrath')));
        if (effect) {
          resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'), kind: effect.kind, age: effect.t,
            targets: effect.targets?.length || 0, radius: effect.r || 0, healRadius: effect.healR || 0,
            heal: effect.heal || 0, buff: Field.hero.buffs?.some(b => b.id === id && b.left > 0) || false,
            crown: Field._debug.effects.some(e => !initial.has(e) && e.kind === 'skPriestCrown') }); return;
        }
        if (performance.now() > deadline) { reject(new Error(`${id} effect ${kind} did not reach its capture window`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id, fx, fy });
    }), { id, kind, age });
    if (id === 'mend') assert.equal(frame.targets, 1, 'Mend links its one wounded recipient');
    if (['prayer', 'divinehymn'].includes(id)) assert.ok(frame.targets >= 3, `${id} links three wounded party members`);
    if (['wardoflight', 'blessing'].includes(id)) { assert.equal(frame.targets, 2, `${id} reaches both other party members`); assert.ok(frame.buff); }
    if (id === 'holynova') { assert.equal(frame.radius, 3.4); assert.equal(frame.healRadius, 6); assert.ok(frame.targets >= 3); }
    if (id === 'heavenswrath') { assert.equal(frame.radius, 5); assert.equal(frame.healRadius, 8); assert.ok(frame.targets >= 3); assert.ok(frame.crown); }
    if (id === 'divinehymn') assert.equal(frame.radius, 12);
    if (id === 'searinglight') assert.ok(frame.heal > 0, 'Searing Light reports real healing return');
    const output = path.join(world.artifacts, `priest-${id}.png`);
    fs.writeFileSync(output, Buffer.from(frame.image.split(',')[1], 'base64'));
    assert.ok(fs.statSync(output).size > 100_000, `${id} captured a real game frame`);
    console.log(`${id}: ${frame.kind}, ${frame.age.toFixed(2)} s, ${output}`);
  }
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${selected.length} Priest skill effects passed in a real-sprite private party browser: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
