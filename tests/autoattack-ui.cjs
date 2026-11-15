const { frameJson } = require('./lib/frames.cjs');
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
    const snapshots = [], events = [], errors = [], serverErrors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('websocket', socket => socket.on('framereceived', ({ payload }) => {
      const packet = frameJson(payload);
      if (packet.type === 'snapshot') snapshots.push(packet);
      if (packet.type === 'event') events.push({ ...packet, time: snapshots.at(-1)?.time || 0 });
      if (packet.type === 'error') serverErrors.push(packet.text);
    }));
    await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
    await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
    await page.locator(`#cls-${cls}`).click(); await page.locator('#name').fill(`Auto${cls}`);
    await page.locator('#go').click({ timeout: 60000 });
    await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
    const actor = await page.evaluate(() => Online.id);
    const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
    // Open meadow ground, away from the town and its sanctuary. A raid pack has enough health for this short check.
    await debug({ op: 'teleport', zone: 0, x: 250, y: 235 });
    // A teleport lands on the nearest free ground, which need not be the requested point (80, 25 is a tree in the shaped
    // Greenmeadow and the hero arrives about 3.7 tiles east). Settle there, then test from where the hero actually stands.
    await page.waitForFunction(() => Field.zone === 0 && Math.hypot(Field.hero.x - 250, Field.hero.y - 235) < 8, null, { timeout: 30000 });
    await page.waitForTimeout(500);
    const home = await page.evaluate(() => ({ x: Field.hero.x, y: Field.hero.y }));
    console.log(`home ${home.x.toFixed(2)}, ${home.y.toFixed(2)}`);
    const nearby = await page.evaluate(h => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - h.x, s.y - h.y) < 15).map(s => s.id), home);
    for (const id of nearby) await debug({ op: 'kill_enemy', id });
    const skills = await page.evaluate(cls => [
      ...WORLD_SKILLS.filter(s => s.class === cls).map(s => s.id), ...(cls === 'assassin' ? ['shadowstep'] : []),
    ], cls);
    assert.equal(skills.length, cls === 'assassin' ? 11 : 10, `${cls}: every active skill is covered`);
    for (const skill of skills.filter(id => !process.env.AUTOATTACK_SKILL_ONLY || id === process.env.AUTOATTACK_SKILL_ONLY)) {
      await page.evaluate(() => { Field.hero.target = null; Online.send({ type: 'stop' }); });
      await debug({ op: 'teleport', zone: 0, x: home.x, y: home.y });
      await page.waitForFunction(h => Math.hypot(Field.hero.x - h.x, Field.hero.y - h.y) < .2, home);
      await debug({ op: 'reset_cooldowns' }); await debug({ op: 'set_resource', amount: 1000 });
      await debug({ op: 'set_hp', hp: await page.evaluate(() => Field.hero.maxHp * .4) });
      // The brute must stand where the skill's line is clear: a cone blocked by a wall or tree is refused with no cooldown
      // ("A wall blocks your skill."). Try the eight points around home in turn and keep the first the server accepts.
      const offsets = [[4, 0], [-4, 0], [0, 4], [0, -4], [3, 3], [-3, -3], [3, -3], [-3, 3]];
      let target = null;
      for (const [dx, dy] of offsets) {
        serverErrors.length = 0;
        await debug({ op: 'spawn_enemy', kind: 'cf_brute', level: 99, x: home.x + dx, y: home.y + dy });
        await page.waitForFunction(id => Field.hero.resource >= 60 && !Field.hero.skillCd[id] && Field.hero.dashCd <= 0 && Field.hero.hp < Field.hero.maxHp && Field.slimes.some(s => s.kind === 'cf_brute' && !s.dead), skill);
        const attempt = await page.evaluate(() => {
          const s = Field.slimes.find(s => s.kind === 'cf_brute' && !s.dead);
          Field.hero.target = s; Online.send({ type: 'target', id: s.id }); return s.id;
        });
        await page.waitForFunction(() => Field.hero.atkCd > 0);
        await page.locator(`#skillbar-slots [data-skill="${skill}"]`).click();
        const accepted = await page.waitForFunction(id => id === 'shadowstep' ? Field.hero.dashCd > 0 : Field.hero.skillCd[id] > 0, skill, { timeout: 2500 }).then(() => true, () => false);
        if (accepted) { target = attempt; break; }
        await page.evaluate(() => { Field.hero.target = null; Online.send({ type: 'stop' }); });
        await debug({ op: 'kill_enemy', id: attempt });
        await page.waitForFunction(id => Field.slimes.find(s => s.id === id)?.dead, attempt);
      }
      assert.ok(target !== null, `${cls}/${skill}: no cooldown started at any of ${offsets.length} spots; server said: ${JSON.stringify(serverErrors)}`);
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
