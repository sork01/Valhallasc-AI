// Every class resumes basic attacks after each skill, without another click/key.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-autoattack', version: '1.0.0' });
let browser, started = false;
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...process.env, VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  let checks = 0;
  const classes = (process.env.AUTOATTACK_CLASSES || 'warrior,mage,assassin,priest,hunter').split(',');
  for (const cls of classes) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const snapshots = [], events = [], errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('websocket', socket => socket.on('framereceived', ({ payload }) => {
      const packet = JSON.parse(payload.toString());
      if (packet.type === 'snapshot') snapshots.push(packet);
      if (packet.type === 'event') events.push({ ...packet, time: snapshots.at(-1)?.time || 0 });
    }));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill(`Auto${cls}`);
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
    const actor = await page.evaluate(() => Online.id);
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    // Open meadow ground, away from the town and its sanctuary. A raid pack has enough health for this short check.
    await debug({ op: 'teleport', zone: 0, x: 80, y: 25 });
    await page.waitForFunction(() => Math.hypot(Field.hero.x - 80, Field.hero.y - 25) < .2);
    const nearby = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - 80, s.y - 25) < 15).map(s => s.id));
    for (const id of nearby) await debug({ op: 'kill_enemy', id });
    const skills = await page.evaluate(cls => [
      ...WORLD_SKILLS.filter(s => s.class === cls).map(s => s.id), ...(cls === 'assassin' ? ['shadowstep'] : []),
    ], cls);
    assert.equal(skills.length, cls === 'assassin' ? 11 : 10, `${cls}: every active skill is covered`);
    for (const skill of skills.filter(id => !process.env.AUTOATTACK_SKILL_ONLY || id === process.env.AUTOATTACK_SKILL_ONLY)) {
      await page.evaluate(() => { Field.hero.target = null; Online.send({ type: 'stop' }); });
      await debug({ op: 'teleport', zone: 0, x: 80, y: 25 });
      await page.waitForFunction(() => Math.hypot(Field.hero.x - 80, Field.hero.y - 25) < .2);
      await debug({ op: 'reset_cooldowns' }); await debug({ op: 'set_resource', amount: 1000 });
      await debug({ op: 'set_hp', hp: await page.evaluate(() => Field.hero.maxHp * .4) });
      await debug({ op: 'spawn_enemy', kind: 'cf_brute', level: 99, x: 84, y: 25 });
      await page.waitForFunction(id => Field.hero.resource >= 60 && !Field.hero.skillCd[id] && Field.hero.dashCd <= 0 && Field.hero.hp < Field.hero.maxHp && Field.slimes.some(s => s.kind === 'cf_brute' && !s.dead), skill);
      const target = await page.evaluate(() => {
        const s = Field.slimes.find(s => s.kind === 'cf_brute' && !s.dead);
        Field.hero.target = s; Online.send({ type: 'target', id: s.id }); return s.id;
      });
      await page.waitForFunction(() => Field.hero.atkCd > 0);
      await page.locator(`#skillbar-slots [data-skill="${skill}"]`).click();
      await page.waitForFunction(id => id === 'shadowstep' ? Field.hero.dashCd > 0 : Field.hero.skillCd[id] > 0, skill);
      const after = snapshots.at(-1).time + .5;
      await page.waitForFunction(id => !Field.hero.dead && Field.slimes.some(s => s.id === id && !s.dead), target);
      // Use server time: a slow private world cannot make this pass or fail based on wall-clock attack timing.
      const deadline = Date.now() + 20000;
      while (snapshots.at(-1).time < after + 2.5 && Date.now() < deadline) await page.waitForTimeout(100);
      assert.ok(snapshots.at(-1).time >= after + 2.5, `${skill}: private server advanced`);
      // At melee distance arrows can spawn and hit between snapshots. Combat events retain every attack.
      const shots = events.filter(e => e.time >= after && e.actor === actor && ['cast', 'swing'].includes(e.kind));
      const impacts = events.filter(e => e.time >= after && e.actor === actor && ['hit', 'miss'].includes(e.kind) && !e.skill);
      assert.ok(shots.length >= 2, `${skill}: autoattack should resume by itself; saw ${shots.length} basic attacks`);
      assert.ok(impacts.length >= 1, `${skill}: a basic attack actually reached the enemy`);
      assert.equal(await page.evaluate(() => Field.hero.target?.id), target, `${skill}: selection still visible`);
      console.log(`${cls}/${skill}: ${shots.length} basic attacks, ${impacts.length} impacts after cast`); checks++;
      await page.evaluate(() => { Field.hero.target = null; Online.send({ type: 'stop' }); });
      await debug({ op: 'kill_enemy', id: target });
      await page.waitForFunction(id => Field.slimes.find(s => s.id === id)?.dead, target);
    }
    assert.deepEqual(errors, []);
    await page.close();
  }
  console.log(`${checks} autoattack continuations across ${classes.length} classes passed in a private browser.`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
