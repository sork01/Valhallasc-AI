// ZONE-CONTEXT-UNLOAD in a real browser: the field keeps a zone context (map arrays, cloned objects, ground canvases) only for the hero's
// zone, its seam and vault neighbours and the last two zones visited. A tour of eight zones must never hold more than that, a seam
// neighbour must be entered without a rebuild, and a dropped zone must be built again on return and draw its ground.
// MUTATE=1 serves a field.js that never drops a context and must fail. Run with scripts/test-touch-bounded.sh (1.5 GiB cap).
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-zone-unload', version: '1.0.0' });
let browser, started = false, checks = 0, debugRef = 1;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [];
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  if (process.env.MUTATE && process.env.MUTATE !== 'music') {
    // MUTATE=ctx keeps every context, MUTATE=sprites never sweeps the scenery sprites, MUTATE=1 does both (the client before this work).
    const m = process.env.MUTATE === 'music' ? null : process.env.MUTATE, src = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8');
    let off = src;
    if (m !== 'sprites') off = off.replace('if (!held.has(k)) dropCtx(k, cc);', 'if (false) dropCtx(k, cc);');
    if (m !== 'ctx') off = off.replace('City.sweepSprites?.();', '');
    assert.notEqual(src, off, 'the mutation found its line');
    await page.route('**/field.js*', route => route.fulfill({ contentType: 'text/javascript', body: off }));
  }
  if (process.env.DIAG) await page.addInitScript(() => {      // where the pixels are: every canvas and image, by the line that made it
    const made = []; const where = () => (new Error().stack.split('\n')[3] || '').replace(/^.*\//, '').trim();
    const ce = document.createElement.bind(document);
    document.createElement = (t, ...r) => { const e = ce(t, ...r); if (String(t).toLowerCase() === 'canvas') made.push([new WeakRef(e), 'canvas ' + where()]); if (String(t).toLowerCase() === 'img') made.push([new WeakRef(e), 'img ' + where()]); return e; };
    const I = window.Image; window.Image = function (...a) { const e = new I(...a); made.push([new WeakRef(e), 'img ' + where()]); return e; }; window.Image.prototype = I.prototype;
    window.__pixels = () => { const by = {}; let total = 0; for (const [r, w] of made) { const e = r.deref(); if (!e) continue; const mb = (e.naturalWidth ?? e.width) * (e.naturalHeight ?? e.height) * 4 / 1048576; total += mb; by[w] = (by[w] || 0) + mb; } return { total: Math.round(total), top: Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 14).map(([k, v]) => `${Math.round(v)} MB ${k}`) }; };
  });
  // Decoded music: every buffer is held weakly, so after a GC only the ones a score still keeps are counted. A stopped score releases
  // its buffer after window.__musicReleaseS (60 s in the game, 1 s here); MUTATE=music never releases.
  await page.addInitScript(release => {
    window.__musicReleaseS = release; const live = [];
    for (const AC of [window.AudioContext, window.webkitAudioContext]) if (AC) { const d = AC.prototype.decodeAudioData; AC.prototype.decodeAudioData = function (...a) { return d.apply(this, a).then(b => { live.push(new WeakRef(b)); return b; }); }; }
    window.__audioLive = () => { let mb = 0, n = 0, all = live.length; for (const r of live) { const b = r.deref(); if (b) { mb += b.length * b.numberOfChannels * 4 / 1048576; n++; } } return { mb: Math.round(mb), n, all }; };
  }, process.env.MUTATE === 'music' ? 1e6 : 1);      // (setTimeout overflows past 2^31 ms)
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Rover'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const cdp = await page.context().newCDPSession(page);
  const heap = async () => { await cdp.send('HeapProfiler.collectGarbage'); return Math.round((await cdp.send('Runtime.getHeapUsage')).usedSize / 1048576); };
  const debug = command => page.evaluate(([command, ref]) => Online.send({ type: 'debug', ref, command }), [command, debugRef++]);
  const zones = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
  const defs = [zones, ...zones.zones];
  const near = z => [...new Set((defs[z].portals || []).filter(p => p.seam || p.vault).map(p => p.to))];
  const info = () => page.evaluate(() => Field.ctxInfo);
  const visited = [0], sprites = [], tunes = []; let peak = 0;
  const go = async z => {
    const { x, y } = defs[z].spawn;
    await debug({ op: 'teleport', zone: z, x, y });
    await page.waitForFunction(z => Field.zone === z, z, { timeout: 20000 });
    await page.waitForTimeout(700 + 350 * near(z).length);      // the neighbours are built one per timer tick
    visited.unshift(z);
  };
  const audit = async label => {
    const z = visited[0], i = await info(), nb = near(z), recent = [...new Set(visited.slice(1))].filter(k => k !== z).slice(0, 2);
    const allowed = new Set([z, ...nb, ...recent]);
    const sp = await page.evaluate(() => City.spriteInfo); peak = Math.max(peak, sp.mb); sprites.push(sp.mb);
    const hp = await heap(), au = await page.evaluate(() => window.__audioLive()); tunes.push(au);
    console.log(`  ${label}: zone ${z}, contexts [${i.zones}], builds ${i.builds}, drops ${i.drops}, heap ${hp} MB, scenery sprites ${sp.sprites} / ${sp.mb} MB, music held ${au.n} of ${au.all} decoded / ${au.mb} MB`);
    if (process.env.DIAG) { const cg = fs.readFileSync('/proc/self/cgroup', 'utf8').trim().split('::')[1]; const dir = '/sys/fs/cgroup' + cg, stat = Object.fromEntries(fs.readFileSync(dir + '/memory.stat', 'utf8').trim().split('\n').map(l => l.split(' '))), mb = v => Math.round(+v / 1048576);
      const procs = fs.readFileSync(dir + '/cgroup.procs', 'utf8').trim().split('\n').map(pid => { try { const st = fs.readFileSync(`/proc/${pid}/status`, 'utf8'), cmd = fs.readFileSync(`/proc/${pid}/cmdline`, 'utf8').split('\0'); return [+(/RssAnon:\s+(\d+)/.exec(st) || [0, 0])[1] >> 10, path.basename(cmd[0]) + ' ' + ((cmd.find(a => a.startsWith('--type=')) || cmd[1] || '').slice(0, 16))]; } catch { return [0, '']; } }).filter(p => p[0] > 20).sort((a, b) => b[0] - a[0]);
      console.log(`    cgroup ${mb(fs.readFileSync(dir + '/memory.current', 'utf8'))} MB, anon ${mb(stat.anon)}, file ${mb(stat.file)}, shmem ${mb(stat.shmem)}; ` + procs.map(p => `${p[0]} ${p[1]}`).join(', ') + `; pixels ${(await page.evaluate(() => window.__pixels())).total}; ${JSON.stringify(await cdp.send('Runtime.getHeapUsage'))}`); }
    check(i.zones.includes(z) && nb.every(k => i.zones.includes(k)), `${label}: the zone and its ${nb.length} seam/vault neighbours have a context`);
    check(i.zones.every(k => allowed.has(k)), `${label}: nothing else is held but the last two visited (held [${i.zones}], allowed [${[...allowed]}])`);
    check(JSON.stringify(i.recent) === JSON.stringify(recent), `${label}: the recent list is [${recent}] (is [${i.recent}])`);
    check(i.chunks[z] > 0, `${label}: the zone's ground is drawn (${i.chunks[z]} chunks)`);
    check(Object.entries(i.chunks).every(([k, n]) => +k === z || nb.includes(+k) || n === 0), `${label}: a merely recent zone holds no ground canvases`);
    return i;
  };

  await page.waitForTimeout(2500);
  await audit('Start');
  // --- a seam neighbour is entered without a rebuild: only ITS new neighbours are built ---
  let before = await info();
  check(before.zones.includes(1), 'The Crags already have a context beside Greenmeadow');
  await go(1);
  let after = await audit('Crags');
  const fresh = near(1).filter(k => !before.zones.includes(k)).length;
  check(after.builds - before.builds === fresh, `Crossing into the seam neighbour built only its ${fresh} new neighbours (${after.builds - before.builds} builds)`);
  // --- a tour of far zones: the set stays bounded ---
  for (const [z, name] of [[8, 'Deep'], [13, 'Astralhollow'], [25, 'Lapis'], [26, 'Frostwake'], [7, 'Bifrost'], [3, 'Gloamfen']].slice(0, +process.env.TOUR || 6)) { await go(z); await audit(name); }
  const end = await info();
  check(end.drops >= 6, `Contexts were dropped along the way (${end.drops})`);
  if (visited.length >= 8) check(!end.zones.includes(8) && !end.zones.includes(13), 'The Deep and Astralhollow are unloaded');
  // --- scenery sprites: what the last three stays drew, never the whole tour ---
  check(sprites[sprites.length - 1] < sprites[0] * 2.2 && peak < sprites[0] * 2.6, `The scenery sprite cache stays bounded over the tour (start ${sprites[0]} MB, peak ${peak} MB, end ${sprites[sprites.length - 1]} MB)`);
  // --- decoded music: the scores of zones left behind are released (a held loop is ~30 MB) ---
  const lastTune = tunes[tunes.length - 1];
  check(lastTune.all >= 5, `Music was decoded for the zones on the tour (${lastTune.all} decodes)`);
  check(lastTune.n <= 3, `Only the scores in use stay decoded (${lastTune.n} held, ${lastTune.mb} MB)`);
  // --- returning to a dropped zone builds it again and draws it ---
  await go(8);
  const back = await audit('Deep again');
  check(back.builds > end.builds, 'Returning rebuilt the dropped context');
  check(errors.length === 0, `No page errors (${errors.join(' | ')})`);
  console.log(`zone-unload-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close().catch(() => {});
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
