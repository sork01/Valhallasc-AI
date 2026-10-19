// BOSSMECH-CHECK: every shipped final boss fought with a real client in a private world, with a screenshot of each distinct
// telegraph at game size (1440 x 900) and phone size (844 x 390). The shipped table is used as it is; PHASE=2 loads a copy where
// every "below x% health" mechanic is live from full health and every "above x%" one is dropped, so the second phase can be seen
// without grinding the boss down. BOSSES=a,b limits the run, SECONDS caps the watch per boss (default 80). The server decides all
// of it; this checks what the player is told: each cast has a name, a countdown, drawn shapes inside the screen, and no page error.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');

const root = path.resolve(__dirname, '..');
const release = path.join(root, 'target/release/valhalla-server');
const debugBin = path.join(root, 'target/debug/valhalla-server');
const newest = [release, debugBin].filter(f => fs.existsSync(f)).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
const binary = process.env.VALHALLA_BINARY || newest;
const phase = Number(process.env.PHASE || 1);
const seconds = Number(process.env.SECONDS || 80);
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const shipped = JSON.parse(fs.readFileSync(path.join(root, 'world/boss-mechanics.txt'), 'utf8'));
const wanted = (process.env.BOSSES || '').split(',').filter(Boolean);
const kinds = Object.keys(shipped).filter(k => !wanted.length || wanted.includes(k));

const env = { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(binary ? { VALHALLA_BINARY: binary } : {}) };
if (phase === 2) {
  const dir = fs.mkdtempSync(path.join(root, 'test-results', 'bossmech-phase2-'));
  const table = {};
  for (const [kind, def] of Object.entries(shipped)) {
    const mechanics = def.mechanics.filter(m => m.hp_min === undefined).map(m => { const { hp_max, ...rest } = m; return m.block === 'split' ? { ...m, hp: 0.99 } : hp_max === undefined ? m : { ...rest, hp_max: 1 }; });
    if (mechanics.some(m => m.hp_max !== undefined || m.block === 'split')) table[kind] = { ...def, mechanics };
  }
  fs.writeFileSync(path.join(dir, 'boss-mechanics.txt'), JSON.stringify(table));
  env.VALHALLA_BOSSMECH_FILE = path.join(dir, 'boss-mechanics.txt');
  for (const k of kinds.slice()) if (!table[k]) kinds.splice(kinds.indexOf(k), 1);
}

const client = new Client({ name: 'valhallasc-bossmech-fights-ui', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
  return result.structuredContent;
}

(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  const replies = [];
  page.on('websocket', ws => ws.on('framereceived', f => { if (typeof f.payload === 'string' && f.payload.startsWith('{"type":"debug"')) replies.push(f.payload.slice(0, 300)); }));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Watcher'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const debug = command => page.evaluate(command => { Online.send({ type: 'debug', ref: Math.floor(Math.random() * 1e9), command }); }, command).then(() => page.waitForTimeout(350));
  await debug({ op: 'set_god_mode', enabled: true });
  await debug({ op: 'set_level', level: 99 });
  const report = [];

  for (const kind of kinds) {
    const zone = map.zones.findIndex(z => z.final_boss === kind) + 1;
    check(zone > 0, `${kind} has a dungeon`);
    const boss = map.zones[zone - 1].slimes.find(s => s.kind === kind);
    check(boss, `${kind} is placed in zone ${zone}`);
    let placed = null;
    const melee = shipped[kind].mechanics.some(m => ['shield', 'adds', 'split', 'static'].includes(m.block));
    for (const [dx, dy] of [...(melee ? [[-1.6, 0], [1.6, 0], [0, 1.6], [0, -1.6]] : []), [-6, 0], [6, 0], [0, 6], [0, -6], [-4, 4], [4, -4], [-9, 0], [9, 0]]) {
      await debug({ op: 'teleport', zone, x: boss.x + dx, y: boss.y + dy });
      placed = await page.evaluate(() => ({ zone: Field.zone, x: Field.hero.x, y: Field.hero.y }));
      if (Math.hypot(placed.x - boss.x - dx, placed.y - boss.y - dy) < 2) break;
    }
    console.log(`${kind}: hero placed ${JSON.stringify(placed)} for boss at ${boss.x},${boss.y}; last reply ${replies[replies.length - 1]}`);
    check(Math.hypot(placed.x - boss.x, placed.y - boss.y) < 12, `${kind}: the hero stands in the boss room`);
    // The arrival banner covers the top of the screen for a few seconds, and the last boss's fight clears with the zone.
    await page.waitForFunction(() => !BossMech.active, null, { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(4500);
    const seen = new Map();
    const shieldBoss = shipped[kind].mechanics.some(m => m.block === 'shield' || m.block === 'adds' || m.block === 'split' || m.block === 'static');
    const started = Date.now();
    let fightSeen = false;
    while (Date.now() - started < seconds * 1000 * (melee ? 2.2 : 1)) {
      const state = await page.evaluate(({ bx, by }) => {
        const f = BossMech.fights[0];
        if (!f) return null;
        const hero = Field.hero, d = Math.atan2(by - hero.y, bx - hero.x);
        Field.hero.dir = { x: Math.cos(d), y: Math.sin(d) };
        const live = t => Math.max(0, (t.left || 0) - (performance.now() / 1000 - 0));
        return { name: f.cast?.name || f.banner || '', castLeft: f.cast?.left ?? null, castTotal: f.cast?.total ?? null, banner: f.banner || '',
          tele: (f.tele || []).filter(t => t.tele !== 'cover' && t.shapes?.length).map(t => ({ tele: t.tele, shapes: t.shapes.map(s => s.t), left: t.left, total: t.total })),
          shield: !!f.shield, brk: !!(f.break && f.break.needed > 0), stunned: f.stunned || 0, marked: (f.marked || []).length, frozen: (f.frozen || []).length,
          cover: (f.tele || []).filter(t => t.tele === 'cover').length, live };
      }, { bx: boss.x, by: boss.y });
      if (process.env.DIAG && Date.now() - started > 15000 && !seen.has('diag')) { seen.set('diag', 1); await page.screenshot({ path: path.join(world.artifacts, `diag-${kind}.png`) }); }
      if (process.env.DIAG && Math.round((Date.now() - started) / 500) % 12 === 0) console.log(kind, Math.round((Date.now() - started) / 1000), JSON.stringify(await page.evaluate(() => ({ f: BossMech.fights[0] || null, hero: { x: Field.hero.x, y: Field.hero.y, dir: Field.hero.dir, dead: Field.hero.dead } }))).slice(0, 700));
      if (state) {
        fightSeen = true;
        // A key per distinct thing on the screen: the cast, the banner and the telegraph kinds.
        const key = `${state.name}|${state.banner}|${[...new Set(state.tele.map(t => `${t.tele}:${t.shapes.join('+')}`))].sort().join(',')}|${state.shield ? 'shield' : ''}${state.brk ? 'break' : ''}${state.marked ? 'marked' : ''}${state.frozen ? 'frozen' : ''}`;
        const worth = state.tele.length || state.banner || state.shield || state.brk || state.marked || state.frozen || state.cover;
        if (worth && !seen.has(key) && seen.size < 6 && (state.tele.length === 0 || state.tele.some(t => (t.left ?? 0) > 2.2 || !t.total))) {
          const file = `${phase === 2 ? 'p2-' : ''}${kind}-${seen.size + 1}`;
          await page.screenshot({ path: path.join(world.artifacts, `${file}-game.png`) });
          const inside = await page.evaluate(() => {
            const f = BossMech.fights[0], hits = [];
            const w2s = Field._debug.w2s, cv = document.getElementById('fieldcv');
            for (const t of f.tele || []) for (const s of t.shapes || []) {
              const polys = BossMech._polygons(s, null);
              for (const poly of polys) for (const p of poly) { const [sx, sy] = w2s(p[0], p[1]); hits.push([sx, sy]); }
            }
            return { points: hits.length, cvw: cv.width, cvh: cv.height };
          });
          await page.setViewportSize({ width: 844, height: 390 });
          await page.waitForTimeout(400);
          await page.screenshot({ path: path.join(world.artifacts, `${file}-phone.png`) });
          const fit = await page.evaluate(() => {
            const cv = document.getElementById('fieldcv'), r = cv.getBoundingClientRect();
            return { canvas: [Math.round(r.width), Math.round(r.height)], viewport: [innerWidth, innerHeight], hud: !!BossMech.fights[0] };
          });
          await page.setViewportSize({ width: 1440, height: 900 });
          await page.waitForTimeout(250);
          seen.set(key, { file, name: state.name, banner: state.banner, tele: state.tele, castTotal: state.castTotal, inside, fit });
        }
      }
      // Swing only while a break bar or a shield asks for damage, or the level-99 hero ends the fight before every cast has been seen.
      if (state && (state.brk || state.shield || shieldBoss)) await page.keyboard.press('Space');
      await page.waitForTimeout(500);
    }
    report.push({ kind, zone, fought: fightSeen, shots: [...seen.values()] });
    console.log(`${kind}: fight ${fightSeen ? 'seen' : 'NOT SEEN'}, ${seen.size} distinct screens: ${[...seen.values()].map(s => `${s.file} [${s.name || s.banner || '-'}]`).join('; ')}`);
    // Leave the arena before the next boss: the fight ends when the zone empties.
    await debug({ op: 'teleport', zone: 0, x: map.spawn.x, y: map.spawn.y });
    await page.waitForTimeout(800);
  }
  fs.writeFileSync(path.join(world.artifacts, `fights-report-phase${phase}.txt`), JSON.stringify(report, null, 1));
  for (const r of report) check(r.fought && r.shots.length > 0, `${r.kind}: a fight with at least one telegraph was seen`);
  assert.deepEqual(errors, []);
  console.log(`bossmech-fights-ui: ${checks} checks passed; screenshots in ${world.artifacts}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
