// Focused real-client check: dungeon looks are visible around the wearer at field scale.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const stationary = process.env.MUTATE === 'stationary';
const output = path.join(root, 'test-results/dungeon-marks');
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  if (pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end('<script src="/items.js"></script><script src="/magesprite.js"></script><script src="/warriorsprite.js"></script><script src="/assassinsprite.js"></script>'); }
  const file = path.resolve(root, 'client', '.' + pathname);
  if (!file.startsWith(path.join(root, 'client') + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'application/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});

async function checkAuraFacing(page) {
  const { frames, danced, fallen, unequipped, preview } = await page.evaluate(async () => {
    const look = { class: 'assassin', gender: 'male', skin: 0, hair: 0 };
    const gloves = WORLD_ITEMS.find(i => i.id === 'assassin_gloves_shadow_l20_vault');
    const base = await AssassinSprite.load(look);
    const sprite = await AssassinSprite.load({ ...look, gloves: gloves.variant });
    await sprite.source.ensure('gloves_' + sprite.equipment.gloves);
    const directions = [[1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0]];
    const size = 240, center = size / 2;
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = size;
    const sheet = document.createElement('canvas'); sheet.width = size * directions.length; sheet.height = 2 * size;
    const g = canvas.getContext('2d', { willReadFrequently: true }), sheetG = sheet.getContext('2d');
    const frame = (wearer, dir, state = {}, addToSheet = false) => {
      const [fx, fy] = directions[dir];
      g.clearRect(0, 0, size, size);
      g.save(); g.translate(center, 202);
      wearer.draw(g, { fx, fy, ...state }, 0, 1.3);
      g.restore();
      if (addToSheet) sheetG.drawImage(canvas, dir * size, 0);
      g.clearRect(0, 0, size, size);
      // Read aura pixels without the dressed sprite covering them.
      g.drawImage = () => {};
      g.save(); g.translate(center, 202);
      wearer.draw(g, { fx, fy, ...state }, 0, 1.3);
      g.restore();
      delete g.drawImage;
      if (addToSheet) sheetG.drawImage(canvas, dir * size, size);
      const rgba = g.getImageData(0, 0, size, size).data;
      let left = size, right = 0, total = 0, weightedX = 0, hash = 2166136261;
      for (let i = 3; i < rgba.length; i += 4) {
        const alpha = rgba[i], x = ((i - 3) / 4) % size;
        hash = Math.imul(hash ^ alpha, 16777619);
        if (!alpha) continue;
        left = Math.min(left, x); right = Math.max(right, x);
        total += alpha; weightedX += alpha * (x + .5 - center);
      }
      return { width: right - left + 1, x: weightedX / total, total, hash };
    };
    const frames = directions.map((_, dir) => frame(sprite, dir, {}, true));
    return { frames, danced: frame(sprite, 0, { danceT: 0 }),
      fallen: frame(sprite, 0, { dead: true, deadT: 1 }), unequipped: frame(base, 0),
      preview: sheet.toDataURL('image/png').split(',')[1] };
  });
  fs.mkdirSync(output, { recursive: true });
  fs.writeFileSync(path.join(output, stationary ? 'gravewalker-stationary.png' : 'gravewalker-facing.png'), Buffer.from(preview, 'base64'));
  assert.ok(frames.every(f => f.total > 0), 'the Gravewalker aura is visible from all eight directions');
  assert.equal(new Set(frames.map(f => f.hash)).size, 8, 'the aura changes with all eight facings');
  assert.ok(frames[2].x > 10 && frames[6].x < -10, 'side views move the aura behind the wearer');
  for (const [diagonal, profile, face] of [[1, 2, 0], [3, 2, 4], [5, 6, 4], [7, 6, 0]]) {
    assert.ok(frames[profile].width < frames[diagonal].width && frames[diagonal].width < frames[face].width,
      'the aura narrows at diagonals and narrows further in profile');
  }
  assert.equal(danced.hash, frames[1].hash, 'a dance turn uses the same aura facing as the sprite');
  assert.equal(fallen.total, 0, 'the aura disappears on death');
  assert.equal(unequipped.total, 0, 'starter gear has no dungeon aura');
  console.log('Gravewalker aura checks passed for all eight directions, dance, death, and unequipping');
}

let browser;
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (stationary) {
    const source = fs.readFileSync(path.join(root, 'client/magesprite.js'), 'utf8');
    const mutated = source.replace('if (mark) dungeonAura(g, mark, t, dir);', 'if (mark) dungeonAura(g, mark, t, 0);');
    assert.notEqual(mutated, source, 'the mutation must fix the aura facing');
    await page.route('**/magesprite.js', route => route.fulfill({ contentType: 'application/javascript', body: mutated }));
  }
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await checkAuraFacing(page);
  if (stationary) return;
  const result = await page.evaluate(async () => {
    const sources = [null, 'undervault', 'cathedral_cloister', 'cathedral_reliquary', 'cathedral_nave', 'moonwell', 'eye_below', 'elder_hollow',
      'thousandfold', 'rain_crown', 'seed_vault', 'sunken_astrolabe', 'thunderheart_gate', 'blooming_labyrinth', 'solar_crucible', 'amber_archive', 'silent_solstice'];
    const levels = [40, 20, 40, 45, 50, 60, 65, 70, 75, 80, 80, 85, 95, 95, 95, 95, 95];
    const figures = [], values = [];
    for (let n = 0; n < sources.length; n++) {
      const source = sources[n], level = levels[n];
      const look = { class: 'warrior', gender: 'male', skin: 0, hair: 0 };
      for (const [kind, slot] of [['armor', 'warriorArmor'], ['weapon', 'warriorWeapon'], ['headgear', 'head'],
                                  ['shoulders', 'shoulders'], ['gloves', 'gloves'], ['pants', 'pants'],
                                  ['necklace', 'necklace'], ['accessory', 'accessory']]) {
        const item = WORLD_ITEMS.find(i => i.kind === kind && (i.class || null) === (['armor', 'weapon', 'headgear', 'shoulders', 'gloves'].includes(kind) ? 'warrior' : null)
          && i.requiredLevel === level && (i.source || null) === source && (source || i.rarity === 'common'));
        if (!item && source === 'undervault' && kind === 'necklace') {
          look[slot] = WORLD_ITEMS.find(i => i.kind === 'necklace' && i.requiredLevel === 20 && !i.source && i.rarity === 'common').variant;
        } else { if (!item) throw Error(`Missing ${source}/${kind}`); look[slot] = item.variant; }
      }
      const sprite = await WarriorSprite.load(look);
      await Promise.all(Object.entries(sprite.equipment).filter(([, art]) => art !== 'none').map(([slot, art]) => sprite.source.ensure(slot + '_' + art)));
      sprite.cache.clear();
      const c = document.createElement('canvas'); c.width = 240; c.height = 240;
      const g = c.getContext('2d'); g.translate(120, 202);
      sprite.draw(g, { fx: 1, fy: 1, atkT: 0, hurtT: 0, dead: false, moving: false }, 0, 1.5);
      const data = c.getContext('2d').getImageData(0, 0, 240, 240).data;
      let outer = 0, hash = 0;
      for (let y = 0; y < 240; y++) for (let x = 0; x < 240; x++) {
        const k = (y * 240 + x) * 4;
        if (data[k + 3] && (x < 60 || x > 180 || y < 20)) outer++;
        hash = (Math.imul(hash, 31) + data[k] * 3 + data[k + 1] * 5 + data[k + 2] * 7 + data[k + 3]) >>> 0;
      }
      figures.push(c.toDataURL('image/png'));
      values.push({ source, theme: MageSprite.dungeonMark(sprite.equipment)?.theme || null,
                    outer, hash, armorTint: sprite.tintLut.has('armor_' + sprite.equipment.armor) });
    }
    return { values, figures };
  });
  assert.equal(result.values[0].theme, null);
  assert.equal(new Set(result.values.slice(1).map(v => v.theme)).size, 16);
  assert.ok(result.values.slice(1).every(v => v.outer > result.values[0].outer + 100));
  assert.ok(result.values.slice(1).every(v => v.armorTint));
  assert.equal(new Set(result.values.map(v => v.hash)).size, 17);
  assert.deepEqual(errors, []);
  const out = path.join(output, 'real-client-warrior.png');
  // A browser canvas combines the seventeen real frames without resizing the pixels.
  const combined = await page.evaluate(figures => {
    const c = document.createElement('canvas'); c.width = 240 * figures.length; c.height = 240;
    const g = c.getContext('2d');
    return Promise.all(figures.map(src => new Promise(resolve => {
      const i = new Image(); i.onload = () => { g.drawImage(i, figures.indexOf(src) * 240, 0); resolve(); }; i.src = src;
    }))).then(() => c.toDataURL('image/png').split(',')[1]);
  }, result.figures);
  fs.writeFileSync(out, Buffer.from(combined, 'base64'));
  console.log('17 real-client dungeon look checks passed: ' + out);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
});
