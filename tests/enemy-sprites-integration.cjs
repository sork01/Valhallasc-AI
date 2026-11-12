// Integration of the independently reviewed enemy banks, without encounter/balance tests.
process.env.REAL_SPRITES = '1';
require('./lib/touch.cjs').requireMemoryLimit();
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const groups = ['frostwake', 'cairn', 'yearwheel', 'eye', 'elder', 'pavilion', 'raincrown', 'seedvault', 'astrolabe', 'thunderheart', 'blooming', 'crucible', 'amber', 'solstice', 'nornroot', 'span', 'longship', 'foundry', 'emberwake', 'forge', 'shared'];
const registries = groups.map(group => JSON.parse(fs.readFileSync(path.join(root, `scripts/${group}_slime_sources.txt`))));
const sources = Object.assign({}, ...registries);
const assets = path.join(root, 'client/assets');
const banks = ['frostwake', 'cairn', 'yearwheel', 'cathedral', 'halloween', 'christmas', 'easter', 'solstice', 'valentines', 'newyear'];
let entries = [];
for (const bank of banks) {
  const meta = JSON.parse(fs.readFileSync(path.join(assets, bank + '.txt')));
  for (const kind of meta.kinds.filter(kind => sources[kind])) {
    assert.equal(meta.sprites[kind], sources[kind], `Accepted editor source: ${kind}`);
    const atlas = meta.atlases?.[kind] || `${bank}_${kind}.png`;
    entries.push({ kind, source: sources[kind], atlas, frame: meta.kindFrames[kind],
      sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(assets, atlas))).digest('hex') });
  }
}
assert.equal(entries.length, Object.keys(sources).length, 'Every accepted kind belongs to one production bank');
if (process.env.ENEMY_ART_KINDS) {
  const selected = process.env.ENEMY_ART_KINDS.split(',');
  assert(selected.every(kind => sources[kind]), 'Valid focused selection');
  entries = entries.filter(entry => selected.includes(entry.kind));
}
let browser;
const world = new TestWorld();
const errors = [];
const receipt = [];
(async () => {
  try {
    await world.start();
    browser = await chromium.launch({ headless: true, args: ['--disable-gpu'] });
    // Expose the existing private loader only in the test response. Its body is unchanged.
    const source = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8');
    const hook = 'enemyCullMargin, enemyShadowK, enemySource },';
    assert.equal(source.split(hook).length, 2);
    const field = source.replace(hook, 'enemyCullMargin, enemyShadowK, enemySource, loadSceneEnemyArt, slimeDefinitions: SLIME },');
    for (let start = 0; start < entries.length; start += 12) {
      const batch = entries.slice(start, start + 12);
      const page = await browser.newPage({ viewport: { width: 960, height: 600 } });
      page.on('pageerror', e => errors.push(e.message));
      await page.route('**/field.js*', r => r.fulfill({ body: field, contentType: 'application/javascript' }));
      await page.addInitScript(() => { window.AudioContext = window.webkitAudioContext = undefined; });
      await page.goto(world.url);
      await page.waitForFunction(() => !!window.Field?._debug.loadSceneEnemyArt);
      await page.evaluate(kinds => Field._debug.loadSceneEnemyArt(kinds.map(kind => ({ kind, state: 'idle' }))), batch.map(e => e.kind));
      await page.waitForFunction(kinds => kinds.every(kind => Field._debug.enemySource({ kind })?.img[kind]?.complete), batch.map(e => e.kind), { timeout: 60000 });
      const results = await page.evaluate(async expected => {
        const result = [];
        for (const entry of expected) {
          const { kind } = entry;
          const src = Field._debug.enemySource({ kind });
          const image = src.img[kind];
          const f = Field.frameOf(src, kind);
          const bytes = await (await fetch(image.src)).arrayBuffer();
          const sha256 = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
          const render = document.createElement('canvas'); render.width = f.w; render.height = f.h;
          const g = render.getContext('2d', { willReadFrequently: true });
          const reference = document.createElement('canvas'); reference.width = f.w; reference.height = f.h;
          const rg = reference.getContext('2d', { willReadFrequently: true });
          const sheet = kind === 'ember_firelord' ? RaidKey.tint(image, WORLD_MAP.crosses?.[0]?.color || '#ed9152') : image;
          let rendered = 0;
          const hashes = { attack: new Set(), die: new Set() };
          for (const clip of ['attack', 'die']) for (let n = 0; n < 8; n++) {
            const actor = { kind, d: { scale: 1 / 2.1 }, dir: 1, seed: 0, dead: false,
              hurtT: 0, recT: 0, hop: 0, hopV: 0, landT: 0, blink: 0, state: 'idle', st: 0 };
            if (clip === 'die') { actor.dead = true; actor.dieT = (n + .05) / src.meta.clips.die.fps; }
            else if (n < 3) { actor.state = 'windup'; actor.windupTime = .45; actor.st = .45 * (1 - (n + .05) / 3); }
            else if (n < 6) { actor.state = 'lunge'; actor.st = .3 * (1 - (n - 3 + .05) / 3); }
            else actor.recT = .22 * (1 - (n - 6 + .05) / 2);
            g.clearRect(0, 0, f.w, f.h); g.save(); g.translate(f.ax, f.ay); Field._debug.drawSlimeSprite(g, actor, 0); g.restore();
            rg.clearRect(0, 0, f.w, f.h); rg.drawImage(sheet, n * f.w, src.meta.clips[clip].row * f.h, f.w, f.h, 0, 0, f.w, f.h);
            const actual = g.getImageData(0, 0, f.w, f.h).data;
            const wanted = rg.getImageData(0, 0, f.w, f.h).data;
            if (!actual.some((v, i) => i % 4 === 3 && v) || !actual.every((v, i) => v === wanted[i])) throw Error(`${kind} ${clip} ${n}: compositor differs`);
            const digest = await crypto.subtle.digest('SHA-256', actual);
            hashes[clip].add(Array.from(new Uint8Array(digest)).join(','));
            rendered++;
          }
          const portrait = document.createElement('canvas'); portrait.width = portrait.height = 96;
          const ready = Field.drawTargetPortrait({ kind }, portrait);
          const visible = portrait.getContext('2d').getImageData(0, 0, 96, 96).data.some((v, i) => i % 4 === 3 && v);
          result.push({ kind, sha256, source: src.meta.sprites[kind], frame: [f.w, f.h, f.ax, f.ay],
            top: Field._debug.slimeDefinitions[kind].top, expectedTop: src.meta.tops[kind],
            attacks: hashes.attack.size, deaths: hashes.die.size, rendered, ready, visible });
        }
        return result;
      }, batch);
      for (let i = 0; i < results.length; i++) {
        const r = results[i], e = batch[i];
        assert.equal(r.sha256, e.sha256, `${r.kind}: exact accepted atlas loaded`);
        assert.equal(r.source, e.source, `${r.kind}: accepted editor source loaded`);
        assert.deepEqual(r.frame, [...e.frame.frame, ...e.frame.anchor], `${r.kind}: individual frame/anchor retained`);
        assert.equal(r.top, r.expectedTop, `${r.kind}: production health-bar top`);
        assert.equal(r.attacks, 8); assert.equal(r.deaths, 8); assert.equal(r.rendered, 16);
        assert(r.ready && r.visible, `${r.kind}: production portrait`);
      }
      receipt.push(...results);
      console.log(`${receipt.length}/${entries.length} accepted kinds: exact atlas, source, frame, portrait, health bar and 16 compositor cells`);
      await page.close();
    }
    assert.deepEqual(errors, []);
    const out = path.join(root, 'test-results/enemy-sprites'); fs.mkdirSync(out, { recursive: true });
    const suffix = process.env.ENEMY_ART_KINDS ? '-' + crypto.createHash('sha256').update(process.env.ENEMY_ART_KINDS).digest('hex').slice(0, 10) : '';
    fs.writeFileSync(path.join(out, `integration-browser${suffix}.json`), JSON.stringify(receipt, null, 2) + '\n');
    console.log(`PASS: ${receipt.length} kinds, ${receipt.length * 16} production attack/death renders; no browser errors`);
  } finally { await browser?.close(); await world.stop(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
