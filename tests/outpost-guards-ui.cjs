// End-to-end Chromium + Rust server test for OUTPOST-GUARDS:
// 1. Open-world towns/outposts spawn guards visible in Field.guards with loaded sprites,
//    while leaving Field.remotePlayers empty.
// 2. Luring a nearby monster to an outpost perimeter causes the guards to engage and kill it
//    without granting the bystander hero free XP/gold/kills, and the guards return to post.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debugBin = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debugBin]
  .filter(f => fs.existsSync(f))
  .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const shotDir = process.env.SHOT_DIR || fs.mkdtempSync(path.join(root, 'test-results', 'outpost-guards-'));
fs.mkdirSync(shotDir, { recursive: true });

const client = new Client({ name: 'valhallasc-outpost-guards-ui', version: '1.0.0' });
let browser, ctx, started = false, checks = 0;
const check = (ok, msg) => { assert.ok(ok, msg); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({
    command: process.execPath,
    args: [path.join(root, 'scripts/test-mcp.cjs')],
    cwd: root,
    stderr: 'pipe',
    env: {
      ...getDefaultEnvironment(),
      VALHALLA_LEVEL_SPREAD: '0',
      ...(process.env.NODE_PATH ? { NODE_PATH: process.env.NODE_PATH } : {}),
      ...(binary ? { VALHALLA_BINARY: binary } : {}),
    },
  }));
  const world = await call('start_world');
  started = true;
  browser = await chromium.launch({ headless: true });
  ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));

  await page.goto(world.url);
  await page.locator('#start').click();
  await page.locator('#login-guest').click();
  await page.locator('#name').fill('Watchman');
  await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(
    () => Online.connected && !!Field.hero.x && Field.guards.length >= 2 && Field.guards.every(g => !!g.sprite),
    null,
    { timeout: 60000 },
  );

  const sendDebug = (command) => page.evaluate(c => {
    Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command: c });
  }, command);

  await sendDebug({ op: 'set_level', level: 1, god: true });
  await page.waitForTimeout(300);

  const init = await page.evaluate(() => ({
    remoteCount: Field.remotePlayers.length,
    guardCount: Field.guards.length,
    firstGuard: Field.guards[0] && {
      name: Field.guards[0].look?.name,
      class: Field.guards[0].look?.class,
      guard: !!Field.guards[0].guard,
      x: Field.guards[0].x,
      y: Field.guards[0].y,
      hasSprite: !!Field.guards[0].sprite,
    },
  }));
  check(init.remoteCount === 0, `Field.remotePlayers stays empty (got ${init.remoteCount})`);
  check(init.guardCount >= 2, `Outpost/town guards spawned (got ${init.guardCount})`);
  check(init.firstGuard?.guard && init.firstGuard.hasSprite, 'Guard carries guard flag and loaded sprite');
  check(/Guard/.test(init.firstGuard?.name || ''), `Guard has expected name (${init.firstGuard?.name})`);

  // Pick the enemy closest to any camp/city hub (outside it) so we can cleanly walk it to the perimeter.
  const targetInfo = await page.evaluate(() => {
    const z = Field.zone === 0 ? WORLD_MAP : WORLD_MAP.zones[Field.zone - 1];
    const hubs = [z.city, ...(z.camps || [])].filter(Boolean);
    let best = null;
    for (const hub of hubs) {
      const hubGuards = Field.guards
        .map(g => ({ g, d: Math.hypot(g.x - (hub.x0 + hub.x1) / 2, g.y - (hub.y0 + hub.y1) / 2) }))
        .filter(e => e.d <= Math.hypot(hub.x1 - hub.x0, hub.y1 - hub.y0))
        .map(e => e.g);
      const guard = hubGuards[0];
      if (!guard) continue;
      for (const s of Field.slimes) {
        if (s.dead || s.kind === 'big' || s.d?.elite) continue;
        const dx = s.x < hub.x0 ? hub.x0 - s.x : s.x > hub.x1 ? s.x - hub.x1 : 0;
        const dy = s.y < hub.y0 ? hub.y0 - s.y : s.y > hub.y1 ? s.y - hub.y1 : 0;
        const edgeDist = Math.hypot(dx, dy);
        const guardDist = Math.hypot(s.x - guard.x, s.y - guard.y);
        if (edgeDist >= 3 && (!best || guardDist < best.guardDist)) {
          // Point 1 tile outside the hub nearest the guard post so both enemy & guard can meet freely.
          const outDir = Math.hypot(guard.x - (hub.x0 + hub.x1) / 2, guard.y - (hub.y0 + hub.y1) / 2) || 1;
          const meetX = guard.x + ((guard.x - (hub.x0 + hub.x1) / 2) / outDir) * 1.2;
          const meetY = guard.y + ((guard.y - (hub.y0 + hub.y1) / 2) / outDir) * 1.2;
          best = {
            id: s.id,
            kind: s.kind,
            sx: s.x,
            sy: s.y,
            edgeDist,
            guardDist,
            gx: guard.x,
            gy: guard.y,
            meetX,
            meetY,
          };
        }
      }
    }
    return best;
  });
  check(!!targetInfo, 'Found reachable enemy near an outpost');

  // Stand beside the enemy so it aggros on Watchman, then lure it straight to `meetX/meetY` near the guard post.
  await sendDebug({ op: 'teleport', zone: 0, x: targetInfo.sx + 0.8, y: targetInfo.sy });
  await page.waitForFunction(
    id => Field.slimes.find(s => s.id === id)?.state === 'chase',
    targetInfo.id,
    { timeout: 10000 },
  );
  check(true, `Lured ${targetInfo.kind} (id ${targetInfo.id}, dist=${targetInfo.guardDist.toFixed(1)}) into chase`);

  // Lead the enemy step-by-step toward the guard perimeter, waiting for it to stay close
  // so it never breaks off past HOME_LEASH_RANGE + CLOSE_CHASE_RANGE.
  const steps = Math.max(6, Math.ceil(targetInfo.guardDist / 2.2));
  for (let i = 1; i <= steps; i++) {
    const f = i / steps;
    const x = targetInfo.sx + (targetInfo.meetX - targetInfo.sx) * f;
    const y = targetInfo.sy + (targetInfo.meetY - targetInfo.sy) * f;
    await page.evaluate(({ x, y }) => Online.send({ type: 'move', x, y }), { x, y });
    try {
      await page.waitForFunction(
        ({ id, x, y }) => {
          const s = Field.slimes.find(m => m.id === id);
          return s && (s.dead || Math.hypot(s.x - x, s.y - y) < 2.8);
        },
        { id: targetInfo.id, x, y },
        { timeout: 10000 },
      );
    } catch (err) {
      const diag = await page.evaluate(({ id, x, y, i }) => {
        const s = Field.slimes.find(m => m.id === id);
        return {
          i,
          goal: { x, y },
          hero: { x: Field.hero.x, y: Field.hero.y },
          slime: s && { x: s.x, y: s.y, hp: s.hp, maxHp: s.maxHp, state: s.state, dead: s.dead },
          guards: Field.guards.map(g => ({ x: g.x, y: g.y, hp: g.hp, atkT: g.atkT })),
        };
      }, { id: targetInfo.id, x, y, i });
      throw new Error(`Step ${i} timed out: ${JSON.stringify(diag)}`);
    }
  }
  // Walk to the final lure spot right next to the guard, wait until the chased slime reaches the guard perimeter,
  // then step behind the guard inside the outpost so the guard finishes the kill.
  await page.evaluate(({ x, y }) => Online.send({ type: 'move', x, y }), { x: targetInfo.meetX, y: targetInfo.meetY });
  await page.waitForFunction(
    ({ id, gx, gy }) => {
      const s = Field.slimes.find(m => m.id === id);
      return s && (s.dead || Math.hypot(s.x - gx, s.y - gy) < 4.5);
    },
    { id: targetInfo.id, gx: targetInfo.gx, gy: targetInfo.gy },
    { timeout: 10000 },
  );
  await page.evaluate(({ x, y }) => Online.send({ type: 'move', x, y }), { x: targetInfo.gx, y: targetInfo.gy });

  // Wait until guards defeat the lured enemy; dump diagnostic state if it stalls.
  try {
    await page.waitForFunction(
      id => !!Field.slimes.find(s => s.id === id)?.dead,
      targetInfo.id,
      { timeout: 25000 },
    );
  } catch (err) {
    const diag = await page.evaluate(id => {
      const s = Field.slimes.find(m => m.id === id);
      return {
        hero: { x: Field.hero.x, y: Field.hero.y },
        slime: s && { x: s.x, y: s.y, hp: s.hp, state: s.state, dead: s.dead },
        guards: Field.guards.map(g => ({ x: g.x, y: g.y, hp: g.hp, atkT: g.atkT })),
      };
    }, targetInfo.id);
    throw new Error(`${err.message} | targetInfo=${JSON.stringify(targetInfo)} | diag=${JSON.stringify(diag)}`);
  }
  check(true, `Guards defeated lured ${targetInfo.kind}`);
  await page.screenshot({ path: path.join(shotDir, 'guards-killed-lured-foe.png') });

  // Allow guards a few seconds to walk back to their post and confirm hero received zero rewards.
  await page.waitForTimeout(2500);
  const after = await page.evaluate(({ gx, gy }) => ({
    xp: Field.hero.xp,
    gold: Field.hero.gold,
    kills: Field.hero.kills,
    remoteCount: Field.remotePlayers.length,
    nearestGuardDist: Math.min(...Field.guards.map(g => Math.hypot(g.x - gx, g.y - gy))),
  }), { gx: targetInfo.gx, gy: targetInfo.gy });

  check(after.xp === 0 && after.gold === 0 && after.kills === 0,
    `Guard kill granted zero player XP/gold/kills (got xp=${after.xp} gold=${after.gold} kills=${after.kills})`);
  check(after.remoteCount === 0, 'Field.remotePlayers remained empty after guard combat');
  check(after.nearestGuardDist < 1.5, `Guard returned near post (dist=${after.nearestGuardDist.toFixed(2)})`);
  check(errors.length === 0, `No browser errors (${errors.join('; ')})`);
  console.log(`PASS outpost-guards-ui: ${checks} checks ok (screenshots in ${shotDir})`);
})().catch(async (err) => {
  console.error(err);
  process.exitCode = 1;
}).finally(async () => {
  await ctx?.close().catch(() => {});
  await browser?.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
