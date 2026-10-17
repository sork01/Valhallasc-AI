// UI-DAMAGE-NUMBERS in a real client: a hit on a small slime and on a tall boss in a private world. The number the canvas
// really draws must start at each target's own head (the boss's higher than the slime's), pop in, climb monotonically, hold, and fade out.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-damage-numbers-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (c, m) => { assert.ok(c, m); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe',
    env: { ...getDefaultEnvironment(), VALHALLA_BINARY: process.env.VALHALLA_BINARY || path.join(root, 'target/release/valhalla-server') } }));
  const world = await call('start_world', { startLevel: 99, godMode: true, levelSpread: 0 }); started = true;
  browser = await chromium.launch({ headless: true });
  const reduced = process.env.REDUCED === '1';
  const page = await browser.newPage({ viewport: process.env.PHONE ? { width: 844, height: 390 } : { width: 1920, height: 1080 }, reducedMotion: reduced ? 'reduce' : 'no-preference' });
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false }));
    window.__nums = [];                                          // every number the canvas draws: text, position, size, opacity
    const proto = CanvasRenderingContext2D.prototype, fill = proto.fillText;
    proto.fillText = function (text, x, y) {
      if (/^[+-]?\d[\d,.]*[kM]?$/.test(String(text)) && /Lilita/.test(this.font)) window.__nums.push({ text, x, y, size: parseFloat(this.font), alpha: this.globalAlpha, at: performance.now() });
      return fill.apply(this, arguments);
    };
  });
  await page.goto(world.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-warrior').click(); await page.locator('#name').fill('Numbers');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && Field.hero.level === 99, null, { timeout: 60000 });
  const debug = command => page.evaluate(c => Online.send({ type: 'debug', command: c }), command);
  const near = await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 14).map(s => s.id));
  for (const id of near) await debug({ op: 'kill_enemy', id });
  await page.waitForFunction(() => Field.slimes.every(s => s.dead || Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) >= 14));
  fs.mkdirSync(path.join(world.artifacts, 'damage-numbers'), { recursive: true });

  const heads = {};
  for (const kind of ['green', 'snowgiant']) {
    await debug({ op: 'reset_cooldowns' });
    await debug({ op: 'spawn_enemy', kind, x: 0, y: 0, level: 99 });     // moved next to the hero below, once it exists
    await page.waitForFunction(k => Field.slimes.some(s => s.kind === k && s.level === 99 && !s.dead), kind);
    const feetAt = await page.evaluate(k => { const s = Field.slimes.find(x => x.kind === k && x.level === 99 && !x.dead); return { x: s.x, y: s.y }; }, kind);
    await debug({ op: 'teleport', zone: await page.evaluate(() => Field.zone), x: feetAt.x - 1.3, y: feetAt.y });
    await page.waitForFunction(p => Math.hypot(Field.hero.x - p.x, Field.hero.y - p.y) < 2, { x: feetAt.x - 1.3, y: feetAt.y });
    await page.evaluate(() => { window.__nums.length = 0; });
    const got = await page.evaluate(k => new Promise(resolve => {
      const slime = Field.slimes.find(x => x.kind === k && x.level === 99 && !x.dead), feet = [], start = performance.now();
      let sentAt = -1e9;
      (function frame() {
        const [fx, fy] = Field._debug.w2s(slime.x, slime.y, 0);
        if (!window.__nums.length && performance.now() - sentAt > 700) { sentAt = performance.now(); Online.send({ type: 'attack', fx: slime.x - Field.hero.x, fy: slime.y - Field.hero.y }); }
        const first = window.__nums[0];
        if (first) feet.push({ at: performance.now(), fx, fy });
        if (window.__nums.length && performance.now() - window.__nums[0].at > 1700 || performance.now() - start > 8000) resolve({ nums: window.__nums.slice(), feet });
        else requestAnimationFrame(frame);
      })();
    }), kind);
    check(got.nums.length > 10, `${kind}: a number was drawn (${got.nums.length} draws)`);
    // The first number: its consecutive draws (same text), until a different one appears.
    const text = got.nums[0].text, run = []; for (const n of got.nums) { if (n.text !== text) break; run.push(n); }
    const feet = got.feet.reduce((a, b) => Math.abs(b.at - run[0].at) < Math.abs(a.at - run[0].at) ? b : a);
    heads[kind] = feet.fy - run[0].y;
    check(heads[kind] > 30, `${kind}: the number starts ${heads[kind].toFixed(0)} px above the feet`);
    if (reduced) {
      check(run.every(n => Math.abs(n.y - run[0].y) < 4), `${kind}: fades in place under reduced motion ${run.map(n => Math.round(n.y)).join(',')}`);
      check(run.every(n => n.size === run[0].size), `${kind}: no pop under reduced motion`);
    } else {
      const sizes = run.map(n => n.size), settled = sizes[sizes.length - 1];
      check(Math.max(...sizes) >= settled * 1.15 && sizes[0] < Math.max(...sizes), `${kind}: pops in past full size and settles (${sizes.slice(0, 8).join(',')} ... ${settled})`);
      for (let i = 1; i < run.length; i++) check(run[i].y <= run[i - 1].y + .6 || run[i - 1].y < 40 || Math.abs(run[i].at - run[i - 1].at) > 200, `${kind}: climbs monotonically at draw ${i}`);
      check(run[0].y < 40 || run[run.length - 1].y < run[0].y - 25, `${kind}: climbed ${(run[0].y - run[run.length - 1].y).toFixed(0)} px`);
    }
    check(run.some(n => n.alpha === 1) && run[run.length - 1].alpha < .5, `${kind}: holds at full opacity, then fades (${run[run.length - 1].alpha.toFixed(2)} at the end)`);
    fs.writeFileSync(path.join(world.artifacts, 'damage-numbers', `${kind}${reduced ? '-reduced' : ''}.json`), JSON.stringify(run.slice(0, 60)));
    // Screenshot a moment after the hit, for the eye.
    await debug({ op: 'reset_cooldowns' });
    await page.evaluate(k => { const s = Field.slimes.find(x => x.kind === k && !x.dead); if (s) Online.send({ type: 'attack', fx: s.x - Field.hero.x, fy: s.y - Field.hero.y }); }, kind);
    await page.waitForTimeout(320);
    await page.screenshot({ path: path.join(world.artifacts, 'damage-numbers', `${kind}${reduced ? '-reduced' : ''}${process.env.PHONE ? '-phone' : ''}.png`) });
    for (const id of await page.evaluate(() => Field.slimes.filter(s => !s.dead && Math.hypot(s.x - Field.hero.x, s.y - Field.hero.y) < 14).map(s => s.id))) await debug({ op: 'kill_enemy', id });
  }
  // A busy moment for the eye: a run of ten hits, a crit, a heal, a miss and a hurt number over the hero and a slime beside it.
  await debug({ op: 'spawn_enemy', kind: 'green', x: 0, y: 0, level: 99 });
  await page.waitForFunction(() => Field.slimes.some(s => s.kind === 'green' && !s.dead));
  const spot = await page.evaluate(() => { const s = Field.slimes.find(x => x.kind === 'green' && !x.dead); return { x: s.x, y: s.y }; });
  await debug({ op: 'teleport', zone: await page.evaluate(() => Field.zone), x: spot.x - 2.5, y: spot.y });
  await page.waitForFunction(p => Math.hypot(Field.hero.x - (p.x - 2.5), Field.hero.y - p.y) < 1, spot);
  await page.evaluate(spot => {
    const head = 120, add = (kind, text, color, delay = 0, x = spot.x, y = spot.y, h = head) => DamageNumbers.spawn(Field._debug.floaters, { x, y, kind, text, color, head: h, delay });
    for (let i = 0; i < 10; i++) add('hit', DamageNumbers.format(3000 + i * 411), '#fff4e0', i * .1);
    add('crit', DamageNumbers.format(18420), '#ffe066', .5); add('miss', 'Miss', '#c9c9bd', .35);
    add('heal', '+' + DamageNumbers.format(1250), '#7dff9a', .2, Field.hero.x, Field.hero.y, 118); add('hurt', '-' + DamageNumbers.format(642), '#ff8b9b', .3, Field.hero.x, Field.hero.y, 118);
  }, spot);
  for (const [name, ms] of [['busy-early', 380], ['busy-late', 420]]) {
    await page.waitForTimeout(ms);
    await page.screenshot({ path: path.join(world.artifacts, 'damage-numbers', `${name}${reduced ? '-reduced' : ''}${process.env.PHONE ? '-phone' : ''}.png`) });
  }
  // Render cost: the mean frame time with the full cap of numbers alive against the same scene without any (headless is
  // software-rendered, so only the ratio means something).
  await page.waitForTimeout(2000);
  const frames = () => page.evaluate(() => new Promise(resolve => { const ts = []; (function f(t) { ts.push(t); if (ts.length > 120) resolve((ts[ts.length - 1] - ts[0]) / (ts.length - 1)); else requestAnimationFrame(f); })(performance.now()); }));
  const idle = await frames();
  await page.evaluate(spot => { for (let i = 0; i < 60; i++) DamageNumbers.spawn(Field._debug.floaters, { x: spot.x + (i % 6) * 1.5, y: spot.y + (i % 4), kind: i % 7 ? 'hit' : 'crit', text: DamageNumbers.format(1000 + i * 91), color: '#fff4e0', head: 100, delay: i * .01 }); }, spot);
  const busy = await frames();
  console.log(`frame ${idle.toFixed(2)} ms idle, ${busy.toFixed(2)} ms with a full cap of numbers`);
  check(busy < idle * 1.35 + 2, `numbers cost frames: ${idle.toFixed(2)} -> ${busy.toFixed(2)} ms`);
  check(heads.snowgiant > heads.green + 40, `the tall boss's number starts higher (${heads.snowgiant.toFixed(0)} px) than the slime's (${heads.green.toFixed(0)} px)`);
  assert.equal(errors.length, 0, `No browser errors: ${errors.join('; ')}`);
  console.log(`${checks} drawn-number checks passed${reduced ? ' (reduced motion)' : ''}: ${path.join(world.artifacts, 'damage-numbers')}`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close();
});
