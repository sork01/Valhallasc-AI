// Render the new, unassigned designs using in-memory assignments in a private client.
process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const plan = JSON.parse(fs.readFileSync(path.join(root, 'docs/npc-named-plan.txt')));
const people = plan.people.filter(n => n.classification === 'named');
const world = new TestWorld();
let browser;
(async () => {
  try {
    await world.start();
    browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
    const page = await browser.newPage({ viewport: { width: 960, height: 600 }, reducedMotion: 'reduce' });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.addInitScript(() => { window.AudioContext = window.webkitAudioContext = undefined; });
    if (process.env.MUTATE_STYLE) {
      await page.route('**/assets/npcp.txt', route => {
        const meta = JSON.parse(fs.readFileSync(path.join(root, 'client/assets/npcp.txt')));
        for (const key of Object.keys(meta.sprites)) if (key.startsWith('named_')) delete meta.sprites[key];
        return route.fulfill({ body: JSON.stringify(meta), contentType: 'application/json' });
      });
    }
    await page.goto(world.url);
    await page.evaluate(() => NpcArt.ready);
    await page.evaluate(people => {
      for (const p of people) NpcArt.manifest.npcs[p.id] = { art: p.designKey, identity: p.identity, color: p.color };
    }, people);
    assert.equal(await page.evaluate(p => NpcArt.styleOf({ id: p.id }), people[0]), 'player', 'Named candidate selects player-style art');
    const report = [];
    for (let start = 0; start < people.length; start += 12) {
      const batch = people.slice(start, start + 12);
      await page.waitForFunction(batch => NpcArt.readyFor(batch), batch, { timeout: 30000 });
      const results = await page.evaluate(batch => batch.map(p => {
        const n = { id: p.id, name: p.name, look: p.identity, fx: 1, fy: 0, moving: false };
        const canvas = document.createElement('canvas'); canvas.width = 192; canvas.height = 224;
        const g = canvas.getContext('2d', { willReadFrequently: true });
        const phase = Array.from(n.id).reduce((sum, ch) => sum + ch.charCodeAt(0), 0);
        const frames = [];
        for (const [clip, count, fps] of [['idle', 6, 6], ['walk', 8, 10], ['talk', 6, 6]]) {
          n.moving = clip === 'walk';
          for (let frame = 0; frame < count; frame++) {
            const t = (frame + .05 - phase) / fps;
            const pose = NpcArt.frame(n, t, clip === 'talk');
            g.clearRect(0, 0, canvas.width, canvas.height);
            g.save(); g.translate(96, 180); const drawn = NpcArt.draw(g, n, t, clip === 'talk'); g.restore();
            const data = g.getImageData(0, 0, canvas.width, canvas.height).data;
            let opaque = 0, edge = false;
            for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) if (data[(y * canvas.width + x) * 4 + 3]) {
              opaque++; if (x === 0 || y === 0 || x === canvas.width - 1 || y === canvas.height - 1) edge = true;
            }
            frames.push({ clip, frame, selected: pose?.step, drawn, opaque, edge, head: NpcArt.head(n, t, clip === 'talk') });
          }
        }
        n.moving = false;
        return { id: p.id, art: p.designKey, style: NpcArt.styleOf(n), top: NpcArt.top(n), frames };
      }), batch);
      for (const r of results) {
        assert.equal(r.style, 'player', `${r.id}: new design is used`);
        assert(r.top > 30 && r.top < 190, `${r.id}: nameplate height`);
        assert.equal(r.frames.length, 20);
        for (const f of r.frames) {
          assert.equal(f.selected, f.frame, `${r.id}: actual ${f.clip} frame selected`);
          assert(f.drawn && f.opaque > 500 && !f.edge, `${r.id} ${f.clip} ${f.frame}: visible, uncropped production sprite`);
          assert(f.head && Number.isFinite(f.head.x) && Number.isFinite(f.head.y) && f.head.width >= 10, `${r.id}: head socket`);
        }
      }
      report.push(...results);
      console.log(`${report.length}/${people.length} new named NPCs: all idle/walk/talk frames, head sockets and bounds`);
    }
    assert.deepEqual(errors, []);
    const out = path.join(root, 'test-results/npc-named'); fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(path.join(out, 'browser-proof.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(`PASS: ${report.length} named designs, ${report.length * 20} production poses; no browser errors`);
  } finally { await browser?.close(); await world.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
