// Actual atlases and compositor. Each page loads only one rig's body and starter
// armor/headgear so the whole check stays within the shared-host memory limit.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
require('./lib/touch.cjs').requireMemoryLimit();
const root = path.resolve(__dirname, '../client');
const output = path.resolve(__dirname, '../test-results/turning-hair');
const candidates = path.join(output, 'assets');
const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
const prefix = cls => cls === 'warrior' ? 'warrior_layered' : cls;
const server = http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  if (name === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end('<!doctype html><canvas id="sheet" width="1280" height="500"></canvas>' + ['items', 'magesprite', 'warriorsprite', 'assassinsprite', 'priestsprite', 'huntersprite'].map(file => `<script src="${file}.js"></script>`).join(''));
  }
  let file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep)) { res.writeHead(404); return res.end(); }
  if (process.env.HAIR_CANDIDATES === '1' && fs.existsSync(path.join(candidates, path.basename(file)))) file = path.join(candidates, path.basename(file));
  if (!fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  if (name.endsWith('_sprites.txt')) {
    const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
    const armor = meta.defaultEquipment.armor;
    const head = Object.keys(meta.equipment.head).find(name => name !== 'none');
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([key]) => ['body', 'armor_' + armor, 'head_' + head].includes(key)));
    res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(meta));
  }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
function variation(data, frames) {
  const colours = new Set(data.hair.map(c => parseInt(c.slice(1), 16)));
  const masks = frames.map(frame => frame.map(([r, g, b, a]) => a && colours.has(r * 65536 + g * 256 + b) ? 1 : 0));
  return masks.slice(1).reduce((sum, frame) => sum + frame.filter((v, i) => v !== masks[0][i]).length, 0) / 7;
}
(async () => {
  let browser, total = 0;
  const reports = [];
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    browser = await chromium.launch({ headless: true });
    for (const cls of classes) for (const gender of ['male', 'female']) {
      const rig = prefix(cls) + (gender === 'female' ? '_f' : '');
      const metrics = JSON.parse(fs.readFileSync(path.join(candidates, rig + '_hair-check.txt')));
      const oldVariation = variation(metrics, metrics.before), newVariation = variation(metrics, metrics.current);
      assert.ok(newVariation > 25, `${rig}: crown silhouette must change with facing (${newVariation})`);
      assert.ok(metrics.depthLevels.current.every(n => n >= 12), `${rig}: crown has curved surfaces in every facing`);
      assert.ok(metrics.depthLevels.current.some((n, i) => n > metrics.depthLevels.before[i] + 10), `${rig}: crown must replace the old flat-depth painting`);
      const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
      const errors = []; page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      const result = await page.evaluate(async ({ cls, gender }) => {
        if (window.__valhallaTestSprites) throw Error('Real sprites required');
        const Base = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
        const C = Base.variant({ gender });
        const look = { class: cls, gender, [cls + 'Armor']: 'none', [cls + 'Weapon']: 'none', head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
        const sprite = await C.load(look), head = Object.keys(sprite.meta.equipment.head).find(name => name !== 'none');
        await sprite.source.ensure('head_' + head);
        const canvas = document.querySelector('#sheet'), g = canvas.getContext('2d');
        g.fillStyle = '#283c46'; g.fillRect(0, 0, canvas.width, canvas.height); g.fillStyle = '#ffffff'; g.font = '15px sans-serif';
        let count = 0, minimumHead = Infinity;
        for (const [clip, spec] of Object.entries(sprite.meta.clips)) for (let dir = 0; dir < 8; dir++) for (let k = 0; k < spec.n; k++) {
          sprite.set(look); const bare = sprite.frame(clip, dir, k);
          const f = sprite.source.parts.body[`${clip}/${dir}/${k}`];
          if (f.x <= 0 || f.y <= 0 || f.x + f.w >= 160 || f.y + f.h >= 160) throw Error(`Clipped body ${cls}/${gender}/${clip}/${dir}/${k}`);
          sprite.set({ ...look, head }); const equipped = sprite.frame(clip, dir, k);
          let delta = 0;
          for (let p = 0; p < bare._px.length; p += 4) if (bare._px[p] !== equipped._px[p] || bare._px[p + 1] !== equipped._px[p + 1] || bare._px[p + 2] !== equipped._px[p + 2] || bare._px[p + 3] !== equipped._px[p + 3]) delta++;
          if (!delta) throw Error(`Hair hides headgear ${cls}/${gender}/${clip}/${dir}/${k}`);
          minimumHead = Math.min(minimumHead, delta); count += 2;
          if (clip === 'idle' && k === 0) {
            g.drawImage(bare, 45, 0, 70, 110, dir * 160 + 10, 25, 140, 220);
            g.drawImage(equipped, 45, 0, 70, 110, dir * 160 + 10, 270, 140, 220);
            g.fillText(`${cls} ${gender} ${sprite.meta.dirs[dir]}`, dir * 160 + 5, 18);
            g.fillText('Starter headgear', dir * 160 + 5, 263);
          }
        }
        return { count, minimumHead, png: canvas.toDataURL() };
      }, { cls, gender });
      assert.equal(result.count, 544); assert.deepEqual(errors, []);
      fs.writeFileSync(path.join(output, `${rig}-client.png`), Buffer.from(result.png.split(',')[1], 'base64'));
      reports.push({ rig, oldVariation, newVariation, minimumHead: result.minimumHead }); total += result.count;
      console.log(`${rig}: 544 real frames; crown variation ${oldVariation.toFixed(1)} -> ${newVariation.toFixed(1)}`);
      await page.close();
    }
    fs.writeFileSync(path.join(output, 'verification.txt'), JSON.stringify({ total, reports }, null, 2) + '\n');
    console.log(`character-hair-art: ${total} real frames passed across all ten rigs`);
  } finally { await browser?.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
