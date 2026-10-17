// Real server casts and real sprites: one capture for every active Mage skill.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-mage-skill-effects', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

const skills = [
  ['twinbolt', 'skMageVolley', '', .18],
  ['fireball', 'skMageFireImpact', '', .08],
  ['barrage', 'skMageVolley', '', .18],
  ['blink', 'skMageBlink', '', .20],
  ['chainlightning', 'skMageLightning', '', .20],
  ['meteor', 'skMageMeteor', '', .48],
  ['lifedrain', 'skMageDrain', '', .20],
  ['arcanestorm', 'skNova', 'mageStorm', .22],
  ['starfall', 'skNova', 'mageStarfield', .55],
  ['arcaneward', 'skMageWard', '', .24],
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
  await page.locator('#cls-mage').click(); await page.locator('#name').fill('MageEffects');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99 && !!Field.mageSprites, null, { timeout: 60000 });
  const catalog = await page.evaluate(() => WORLD_SKILLS.filter(s => s.class === 'mage').map(s => ({ id: s.id, icon: s.icon, description: s.description })));
  assert.deepEqual(catalog.map(s => s.id).sort(), skills.map(s => s[0]).sort(), 'All ten Mage skills have catalog entries');
  assert.equal(new Set(catalog.map(s => s.icon)).size, 10, 'The Mage icons are distinct');
  assert.ok(catalog.every(s => s.description.length > 30), 'Every Mage skill describes its purpose');

  for (const [id, kind, style, age] of skills.filter(([id]) => !process.env.MAGE_SKILL_ONLY || id === process.env.MAGE_SKILL_ONLY)) {
    await page.waitForFunction(() => Field._debug.effects.every(e => !e.kind.startsWith('sk')) && Field._debug.bolts.length === 0);
    await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_resource', amount: 1000 } }));
    await page.waitForFunction(() => Field.hero.resource >= 60);
    if (id === 'lifedrain') {
      const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 6).map(s => s.id));
      for (const enemy of nearby) await page.evaluate(id => Online.send({ type: 'debug', command: { op: 'kill_enemy', id } }), enemy);
      await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 6));
    }
    if (['fireball', 'chainlightning', 'lifedrain'].includes(id)) {
      const kinds = id === 'chainlightning' ? ['green', 'blue', 'pink'] : ['green'];
      for (let i = 0; i < kinds.length; i++) {
        await page.evaluate(({ enemy, i, id }) => Online.send({ type: 'debug', command: { op: 'spawn_enemy', kind: enemy,
          x: Field.hero.x + (id === 'lifedrain' ? 4 : 2.5) + i * .8, y: Field.hero.y + (i % 2 ? 1.3 : 0), level: 99 } }), { enemy: kinds[i], i, id });
      }
      await page.waitForFunction(kinds => kinds.some(kind => Field.slimes.some(s => s.kind === kind && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 5)), kinds);
    }
    if (id === 'lifedrain') {
      await page.evaluate(() => Online.send({ type: 'debug', command: { op: 'set_hp', hp: Field.hero.maxHp * .4 } }));
      await page.waitForFunction(() => Field.hero.hp < Field.hero.maxHp * .5);
    }
    const frame = await page.evaluate(({ id, kind, style, age }) => new Promise((resolve, reject) => {
      const initial = new Set(Field._debug.effects), deadline = performance.now() + 8000;
      let alternateImage = null;
      const target = Field.slimes.find(s => s.kind === 'green' && s.level === 99 && !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 5);
      const fx = target && ['fireball', 'chainlightning', 'lifedrain'].includes(id) ? target.x - Field.hero.x : 1;
      const fy = target && ['fireball', 'chainlightning', 'lifedrain'].includes(id) ? target.y - Field.hero.y : 0;
      function sample() {
        if (!alternateImage && id === 'fireball' && Field._debug.bolts.some(b => b.skill === 'fireball'))
          alternateImage = document.querySelector('#fieldcv').toDataURL('image/png');
        if (!alternateImage && id === 'meteor' && Field._debug.effects.some(e => !initial.has(e) && e.kind === 'skMageMeteor' && e.t >= .16 && e.t < .30))
          alternateImage = document.querySelector('#fieldcv').toDataURL('image/png');
        const effect = Field._debug.effects.find(e => !initial.has(e) && e.kind === kind && (!style || e.style === style) && e.t >= age);
        const traveling = Field._debug.bolts.filter(b => b.skill === id).length;
        if (effect && (id !== 'twinbolt' && id !== 'barrage' || traveling === (id === 'twinbolt' ? 2 : 5))) {
          resolve({ image: document.querySelector('#fieldcv').toDataURL('image/png'), alternateImage, kind: effect.kind,
            style: effect.style || '', reach: effect.r || null, points: effect.path?.length || 0,
            heal: effect.heal || 0, bolts: traveling,
            moved: Math.hypot(Field.hero.x - effect.x, Field.hero.y - effect.y), age: effect.t });
          return;
        }
        if (performance.now() > deadline) { reject(new Error(`${id} effect ${kind}/${style} did not reach its capture window`)); return; }
        requestAnimationFrame(sample);
      }
      requestAnimationFrame(sample);
      Online.send({ type: 'skill', id, fx, fy });
    }), { id, kind, style, age });
    if (id === 'twinbolt') assert.equal(frame.bolts, 2, 'Twin Bolt has two distinct traveling bolts');
    if (id === 'barrage') assert.equal(frame.bolts, 5, 'Arcane Barrage has five traveling bolts');
    if (id === 'fireball') assert.equal(frame.reach, 2, 'The actual bolt impact shows its two-unit blast radius');
    if (id === 'blink') assert.ok(frame.moved > 1, 'Blink traces the observed movement');
    if (id === 'chainlightning') assert.ok(frame.points >= 2, 'Lightning links actual struck targets');
    if (id === 'meteor') assert.equal(frame.reach, 2.6, 'Meteor shows the catalog impact radius');
    if (id === 'lifedrain') assert.ok(frame.heal > 0, 'Life Drain shows the actual heal return');
    if (id === 'arcanestorm') assert.equal(frame.reach, 5, 'Arcane Storm shows its five-unit reach');
    if (id === 'starfall') assert.equal(frame.reach, 6.5, 'Starfall shows its broad hit field');
    if (id === 'arcaneward') await page.waitForFunction(() => Field.hero.buffs?.some(b => b.id === 'arcaneward' && b.left > 0));
    const output = path.join(world.artifacts, `mage-${id}.png`);
    fs.writeFileSync(output, Buffer.from(frame.image.split(',')[1], 'base64'));
    assert.ok(fs.statSync(output).size > 100_000, `${id} captured a real game frame`);
    if (id === 'fireball' || id === 'meteor') {
      assert.ok(frame.alternateImage, `${id} has a travel or warning frame`);
      const phase = id === 'fireball' ? 'travel' : 'warning';
      const alternate = path.join(world.artifacts, `mage-${id}-${phase}.png`);
      fs.writeFileSync(alternate, Buffer.from(frame.alternateImage.split(',')[1], 'base64'));
      assert.ok(fs.statSync(alternate).size > 100_000, `${id} ${phase} captured a real game frame`);
    }
    console.log(`${id}: ${frame.kind}${frame.style ? '/' + frame.style : ''}, ${frame.age.toFixed(2)} s, ${output}`);
  }
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`10 Mage skill effects passed in a real-sprite private browser: ${world.artifacts}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
