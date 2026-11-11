// NPC-PLAYER-STYLE in a real browser: every person in a zone is drawn from the player-style atlases (`npcp_<design>.png`), through the page's own
// `City.drawNpc`. Checks per zone: each NPC with art reports style 'player', draws opaque pixels on an offscreen canvas, has a head socket (hats,
// antlers and portraits depend on it) and a nameplate height; for the general designs the person's own skin / hair / cloth colours are applied
// with the design's own brightness steps (no pixel of the design's base skin3 / hair3 / cloth3 ramp is left over, and changing the person's
// cloth colour changes the picture). `ZONES=0,9` picks zones (default 0,4,7,9,24), `SHOTS=<dir>` writes a screenshot per zone.
// Needs the bounded runner and a `--profile test` server binary. MUTATE=style|amounts serves an npc-art.js without that part and must fail.
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('./lib/playwright.cjs');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-npc-style', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; console.log(`${checks}: ${message}`); };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const errors = [], map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
(async () => {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0', ...(process.env.VALHALLA_BINARY ? { VALHALLA_BINARY: process.env.VALHALLA_BINARY } : {}) } }));
  const world = await call('start_world'); started = true;
  browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  const mutations = { style: ['const isNew = !!fresh && !!fresh.sprites[who.art]', 'const isNew = false'], amounts: ['const given = pose.m.designs[pose.art].amounts || {};', 'const given = {};'] };
  if (process.env.MUTATE) {
    const [from, to] = mutations[process.env.MUTATE] || mutations.style, src = fs.readFileSync(path.join(root, 'client/npc-art.js'), 'utf8');
    assert.ok(src.includes(from), 'the mutation applies');
    await page.route('**/npc-art.js*', route => route.fulfill({ contentType: 'text/javascript', body: src.replace(from, to) }));
  }
  await page.addInitScript(() => localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: false })));
  await page.goto(world.url);
  await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#name').fill('Looker'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && !!Field.hero.x, null, { timeout: 60000 });
  const zones = (process.env.ZONES || '0,4,7,9,24').split(',').map(Number);
  for (const zone of zones) {
    // Stand beside the zone's first person (from map.txt) so the town is loaded around the hero.
    const z = zone === 0 ? map : map.zones[zone - 1], first = z.npcs[0];
    await page.evaluate(([zone, x, y]) => Online.send({ type: 'debug', ref: 2, command: { op: 'teleport', zone, x, y } }), [zone, first.x + 1, first.y + 1]);
    await page.waitForFunction(zone => Field.zone === zone && City.npcs.length > 0 && NpcArt.readyFor(City.npcs), zone, { timeout: 40000 });
    await page.waitForTimeout(1200);
    const r = await page.evaluate(() => {
      const out = { people: 0, withArt: 0, notPlayer: [], blank: [], noHead: [], noTop: [], general: 0, leftover: [], unchanged: [] };
      const man = NpcArt.fresh, base = NpcArt.manifest, hex = c => parseInt(c.slice(1), 16);
      const render = n => {
        const c = document.createElement('canvas'); c.width = 200; c.height = 260; const g = c.getContext('2d', { willReadFrequently: true });
        City.drawNpc(g, { ...n, x: -999, y: -999, key: false, offers: [], buys: null, moving: false, fx: 1, fy: 0 }, 100, 220, 0.37, false, false);
        return g.getImageData(0, 0, 200, 260).data;
      };
      for (const n of City.npcs) {
        out.people++;
        const who = base.npcs[n.id]; if (!who) continue; out.withArt++;
        if (NpcArt.styleOf(n) !== 'player') { out.notPlayer.push(n.id); continue; }
        const d = render(n); let opaque = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 200) opaque++;
        if (opaque < 300) out.blank.push(n.id);
        if (!NpcArt.head(n, 0.37, false)) out.noHead.push(n.id);
        if (NpcArt.top(n) == null) out.noTop.push(n.id);
        const design = man.designs[who.art];
        if (design.general) {
          out.general++;
          // A person whose colours are not the design's own base: none of the base ramp's lightest steps may remain.
          const left = [];
          for (const [group, own] of [['skin', who.identity.skin], ['hair', who.identity.hair], ['cloth', who.color]]) {
            const last = design.materials[group + '3']; if (!last || !own || hex(own) === hex(last)) continue;
            let k = 0; for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 200 && ((d[i] << 16) | (d[i + 1] << 8) | d[i + 2]) === hex(last)) k++;
            if (k) left.push(group + k);
          }
          if (left.length) out.leftover.push(n.id + ':' + left.join(','));
          // And the picture follows the person's cloth colour.
          const keep = who.color; who.color = keep.toLowerCase() === '#ff2020' ? '#2020ff' : '#ff2020';
          const e = render(n); who.color = keep;
          let diff = 0; for (let i = 0; i < d.length; i += 4) if (d[i] !== e[i] || d[i + 1] !== e[i + 1] || d[i + 2] !== e[i + 2]) diff++;
          if (diff < 30) out.unchanged.push(n.id);
        }
      }
      return out;
    });
    console.log(`zone ${zone}: ${r.people} people, ${r.withArt} with art, ${r.general} general designs`);
    check(r.withArt >= 1, `Zone ${zone} has people with art (${r.withArt})`);
    check(r.notPlayer.length === 0, `Zone ${zone}: every person is drawn in the player style ${JSON.stringify(r.notPlayer.slice(0, 5))}`);
    check(r.blank.length === 0, `Zone ${zone}: every figure draws opaque pixels ${JSON.stringify(r.blank.slice(0, 5))}`);
    check(r.noHead.length === 0, `Zone ${zone}: every figure has a head socket for hats and portraits ${JSON.stringify(r.noHead.slice(0, 5))}`);
    check(r.noTop.length === 0, `Zone ${zone}: every figure has a nameplate height ${JSON.stringify(r.noTop.slice(0, 5))}`);
    check(r.leftover.length === 0, `Zone ${zone}: recoloured people keep none of the design's base ramp ${JSON.stringify(r.leftover.slice(0, 5))}`);
    check(r.unchanged.length === 0, `Zone ${zone}: the cloth colour changes the picture ${JSON.stringify(r.unchanged.slice(0, 5))}`);
    if (process.env.SHOTS) { fs.mkdirSync(process.env.SHOTS, { recursive: true }); await page.screenshot({ path: path.join(process.env.SHOTS, `zone-${zone}.png`) }); }
  }
  assert.deepEqual(errors, []);
  console.log(`npc-player-style-ui: ${checks} checks passed`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close(); if (started) await call('stop_world').catch(() => {}); await client.close();
});
