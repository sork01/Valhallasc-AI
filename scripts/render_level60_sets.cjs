// Render the real, fully equipped level-60 class sprites for a shareable preview.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results/moonspore-level60-sets');
const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
const rarities = ['gray', 'green', 'blue', 'purple'];
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt')));
const equipment = Object.fromEntries(classes.map(cls => [cls, Object.fromEntries(rarities.map(rarity => {
  const chosen = items.filter(i => i.class === cls && i.requiredLevel === 60 && i.id.endsWith('_l60_' + rarity));
  assert.deepEqual(chosen.map(i => i.kind).sort(), ['armor', 'gloves', 'headgear', 'shoulders', 'weapon']);
  const shared = items.filter(i => !i.class && i.requiredLevel === 60 && i.id.endsWith('_l60_' + rarity) && ['pants', 'necklace', 'accessory'].includes(i.kind));
  assert.deepEqual(shared.map(i => i.kind).sort(), ['accessory', 'necklace', 'pants']);
  return [rarity, Object.fromEntries([...chosen, ...shared].map(i => [i.kind === 'headgear' ? 'head' : i.kind, i.variant]))];
}))]));

const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  if (pathname === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end('<!doctype html><script src="items.js"></script><script src="magesprite.js"></script><script src="assassinsprite.js"></script><script src="warriorsprite.js"></script><script src="priestsprite.js"></script><script src="huntersprite.js"></script>');
  }
  const file = path.resolve(root, 'client', '.' + pathname);
  if (!file.startsWith(path.join(root, 'client') + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});

(async () => {
  let browser;
  try {
    fs.mkdirSync(out, { recursive: true });
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:' + server.address().port);
    const rows = [];
    for (const cls of classes) {
      const images = await page.evaluate(async ({ cls, tiers }) => {
        const Base = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
        const bare = { class: cls, gender: 'male', skin: 0, hairColor: 1,
          [cls + 'Armor']: 'none', [cls + 'Weapon']: 'none', head: 'none', shoulders: 'none', gloves: 'none',
          pants: 'none', necklace: 'none', accessory: 'none' };
        const sprite = await Base.load(bare);
        const png = [];
        for (const [rarity, pieces] of Object.entries(tiers)) {
          const look = { ...bare, [cls + 'Armor']: pieces.armor, [cls + 'Weapon']: pieces.weapon,
            head: pieces.head, shoulders: pieces.shoulders, gloves: pieces.gloves,
            pants: pieces.pants, necklace: pieces.necklace, accessory: pieces.accessory };
          sprite.set(look);
          for (const [slot, art] of Object.entries(sprite.equipment)) if (art !== 'none') {
            await sprite.source.ensure(slot + '_' + art);
            if (!sprite.source.parts[slot + '_' + art]) throw Error(`${cls}/${rarity}: missing ${slot}_${art}`);
          }
          for (const slot of ['armor', 'weapon', 'head', 'shoulders', 'gloves', 'pants', 'necklace', 'accessory']) {
            if (sprite.worn[slot] !== pieces[slot]) throw Error(`${cls}/${rarity}: ${slot} was not equipped`);
          }
          sprite.cache.clear();
          png.push([rarity, sprite.frame('idle', 0, 0).toDataURL('image/png')]);
        }
        return png;
      }, { cls, tiers: equipment[cls] });
      for (const [rarity, data] of images) fs.writeFileSync(path.join(out, `${cls}-${rarity}.png`), Buffer.from(data.split(',')[1], 'base64'));
      rows.push(cls);
      console.log(`Rendered ${cls}: ${images.length} complete sets`);
    }
    assert.deepEqual(rows, classes);
    assert.deepEqual(errors, []);
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
