// Focused real-client check: dungeon looks are visible around the wearer at field scale.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  if (pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end('<script src="/items.js"></script><script src="/magesprite.js"></script><script src="/warriorsprite.js"></script>'); }
  const file = path.resolve(root, 'client', '.' + pathname);
  if (!file.startsWith(path.join(root, 'client') + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'application/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
let browser;
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  const result = await page.evaluate(async () => {
    const sources = [null, 'undervault', 'cathedral_cloister', 'cathedral_reliquary', 'cathedral_nave', 'moonwell'];
    const levels = [40, 20, 40, 45, 50, 60];
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
      sprite.draw(g, { fx: 0, fy: 1, atkT: 0, hurtT: 0, dead: false, moving: false }, 0, 1.5);
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
  assert.equal(new Set(result.values.slice(1).map(v => v.theme)).size, 5);
  assert.ok(result.values.slice(1).every(v => v.outer > result.values[0].outer + 100));
  assert.ok(result.values.slice(1).every(v => v.armorTint));
  assert.equal(new Set(result.values.map(v => v.hash)).size, 6);
  assert.deepEqual(errors, []);
  const out = path.join(root, 'test-results/dungeon-marks/real-client-warrior.png');
  fs.mkdirSync(path.dirname(out), { recursive: true });
  // A browser canvas combines the six real frames without resizing the pixels.
  const combined = await page.evaluate(figures => {
    const c = document.createElement('canvas'); c.width = 240 * figures.length; c.height = 240;
    const g = c.getContext('2d');
    return Promise.all(figures.map(src => new Promise(resolve => {
      const i = new Image(); i.onload = () => { g.drawImage(i, figures.indexOf(src) * 240, 0); resolve(); }; i.src = src;
    }))).then(() => c.toDataURL('image/png').split(',')[1]);
  }, result.figures);
  fs.writeFileSync(out, Buffer.from(combined, 'base64'));
  console.log('6 real-client dungeon look checks passed: ' + out);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
});
