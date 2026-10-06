// Real client compositor check for one newly exported piece, including every relevant class and both bodies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const job = process.argv[2];
const state = JSON.parse(fs.readFileSync(path.join(root, 'docs/gear-redesign-state.txt')));
const task = state.tasks.find(t => t.id === job); assert.ok(task, 'Provide a checklist job ID');
const record = JSON.parse(fs.readFileSync(path.join(root, 'world/gear-art.txt')))[job]; assert.ok(record?.files, 'Export the piece first');
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt')));
const selected = items.filter(i => i.kind === task.kind && (i.class || null) === task.className && (task.group.startsWith('L') ? !i.source && i.requiredLevel === Number(task.group.slice(1)) : i.source === 'cathedral_' + task.group));
assert.ok(selected.length);
const slot = task.kind === 'headgear' ? 'head' : task.kind;
const originalVariant = selected[0].variant.split('_l')[0];
const metadataNames = { warrior: 'warrior_layered', assassin: 'assassin', mage: 'mage', priest: 'priest', hunter: 'hunter' };
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  if (pathname === '/') { res.setHeader('Content-Type', 'text/html'); return res.end('<!doctype html><script src="items.js"></script><script src="magesprite.js"></script><script src="assassinsprite.js"></script><script src="warriorsprite.js"></script><script src="priestsprite.js"></script><script src="huntersprite.js"></script>'); }
  const match = pathname.match(/^\/preview-(assassin|warrior|mage|priest|hunter)-(male|female)\.txt$/);
  if (match) {
    const [, cls, gender] = match;
    const meta = JSON.parse(fs.readFileSync(path.join(root, 'client/assets', metadataNames[cls] + (gender === 'female' ? '_f' : '') + '_sprites.txt')));
    const needed = ['body', slot + '_' + record.variant, slot + '_' + originalVariant];
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([key]) => needed.includes(key)));
    // Private fixture mutation: substituting the starter silhouette must fail the shape guard even after a tint.
    if (process.argv.includes('--mutation-original')) meta.parts[slot + '_' + record.variant] = meta.parts[slot + '_' + originalVariant];
    assert.ok(meta.parts[slot + '_' + record.variant], 'New part is in the actual class metadata');
    res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(meta));
  }
  const file = path.resolve(root, 'client', '.' + pathname);
  if (!file.startsWith(path.join(root, 'client') + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain'); fs.createReadStream(file).pipe(res);
});
(async () => {
  let browser, checks = 0;
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage(), errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:' + server.address().port);
    const evidence = [];
    for (const cls of Object.keys(record.classes)) {
      const result = await page.evaluate(async ({ cls, slot, variants, originalVariant }) => {
        const Base = { assassin: AssassinSprite, warrior: WarriorSprite, mage: MageSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
        const values = [];
        const c = document.createElement('canvas'); c.width = (variants.length + 1) * 160; c.height = 2 * 180;
        const g = c.getContext('2d'); g.fillStyle = '#263d48'; g.fillRect(0, 0, c.width, c.height);
        for (const [row, gender] of ['male', 'female'].entries()) {
          const C = gender === 'female' ? Base.Female : Base; C.METADATA = `preview-${cls}-${gender}.txt`;
          const bare = { class: cls, gender, skin: 0, hair: 0, [cls + 'Armor']: 'none', [cls + 'Weapon']: 'none', head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none' };
          const s = await C.load(bare);
          const put = async v => {
            const look = { ...bare, [slot === 'armor' ? cls + 'Armor' : slot === 'weapon' ? cls + 'Weapon' : slot]: v };
            s.set(look); await Promise.all(Object.entries(s.equipment).filter(([, art]) => art !== 'none').map(([part, art]) => s.source.ensure(part + '_' + art))); s.cache.clear();
            const image = s.frame('idle', 0, 0), data = image.getContext('2d').getImageData(0, 0, image.width, image.height).data;
            let hash = 0, silhouette = 0; const alpha = [];
            for (let k = 0; k < data.length; k += 4) { hash = (hash * 31 + data[k] * 3 + data[k + 1] * 5 + data[k + 2] * 7 + data[k + 3]) >>> 0; silhouette = (silhouette * 31 + data[k + 3]) >>> 0; alpha.push(data[k + 3]); }
            return { hash, silhouette, alpha, image };
          };
          const naked = await put('none'), old = await put(originalVariant);
          // Jewelry can change shape entirely inside the body's outline. Compare the equipment masks themselves,
          // while the rendered hashes above still prove that the new layer is visible on the actual figure.
          const layerMask = part => {
            const f = s.source.parts[part]?.['idle/0/0']; if (!f) throw Error('Missing decoded equipment layer: ' + part);
            const mask = new Uint8Array(s.meta.frame[0] * s.meta.frame[1]);
            for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) mask[(f.y + y) * s.meta.frame[0] + f.x + x] = f.pixels[(y * f.w + x) * 4 + 3];
            return mask;
          };
          const oldLayer = layerMask(slot + '_' + originalVariant);
          g.drawImage(old.image, 0, row * 180 + 18); g.fillStyle = '#fff'; g.font = '10px sans-serif'; g.fillText('Original ' + gender, 3, row * 180 + 12);
          const coloured = [];
          for (const [n, variant] of variants.entries()) {
            const frame = await put(variant); coloured.push({ hash: frame.hash, silhouette: frame.silhouette });
            g.drawImage(frame.image, (n + 1) * 160, row * 180 + 18); g.fillText(variant.split('_').slice(-1)[0] + ' ' + gender, (n + 1) * 160 + 3, row * 180 + 12);
          }
          const newFrame = await put(variants[0]);
          const delta = newFrame.alpha.filter((value, k) => value !== old.alpha[k]).length;
          const newLayer = layerMask(slot + '_' + s.equipment[slot]);
          const layerDelta = newLayer.filter((value, k) => value !== oldLayer[k]).length;
          const remove = await put('none');
          values.push({ gender, naked: naked.hash, old: old.hash, coloured, silhouetteDelta: delta, layerSilhouetteDelta: layerDelta, removed: remove.hash });
        }
        return { values, png: c.toDataURL('image/png') };
      }, { cls, slot, variants: selected.map(i => i.variant), originalVariant });
      for (const body of result.values) {
        assert.ok(body.coloured.every(c => c.hash !== body.naked && c.hash !== body.old), `${cls}/${body.gender}: new gear is drawn`); checks++;
        assert.ok(body.layerSilhouetteDelta > 0, `${cls}/${body.gender}: equipment has a new shape, not only a color change`); checks++;
        assert.equal(new Set(body.coloured.map(c => c.silhouette)).size, 1, 'All rarity tiers share the level base shape'); checks++;
        assert.equal(new Set(body.coloured.map(c => c.hash)).size, selected.length, 'Rarity tints are different'); checks++;
        assert.equal(body.removed, body.naked, 'Unequip removes the new layer'); checks++;
      }
      const preview = path.join(root, 'test-results/gear-redesign', job + '-' + cls + '-client.png'); fs.writeFileSync(preview, Buffer.from(result.png.split(',')[1], 'base64'));
      evidence.push({ cls, bodies: result.values, preview: path.relative(root, preview) });
    }
    const icons = JSON.parse(fs.readFileSync(path.join(root, 'client/assets/items.txt')));
    assert.ok(selected.every(i => icons.at[i.id]), 'Every tier has its new inventory icon'); checks++;
    assert.equal(new Set(selected.map(i => icons.at[i.id].join())).size, 1, 'Rarity tiers recolor the same base icon'); checks++;
    assert.equal(errors.length, 0, errors.join('; ')); checks++;
    fs.writeFileSync(path.join(root, 'test-results/gear-redesign', job + '-browser.json'), JSON.stringify({ job, checks, evidence }, null, 2) + '\n');
    console.log(`${job}: ${checks} real-client art checks passed`);
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(e => { console.error(e); process.exitCode = 1; });
