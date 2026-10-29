// Real compositor, isolated HTTP origin, only the changed female body/outfit layers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require('playwright');
require('./lib/touch.cjs').requireMemoryLimit();
const root = path.resolve(__dirname, '../client');
const out = process.env.TORSO_ART_DIR ? path.resolve(process.env.TORSO_ART_DIR) : path.resolve(__dirname, '../test-results/female-torso');
const candidates = path.join(out, 'assets'), before = path.join(out, 'before');
const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end('<!doctype html><canvas width="1400" height="310"></canvas>' + ['items', 'magesprite', 'warriorsprite', 'assassinsprite', 'priestsprite', 'huntersprite'].map(s => `<script src="/${s}.js"></script>`).join(''));
  }
  const name = path.basename(url.pathname);
  let file = url.pathname.startsWith('/before/') ? path.join(before, name) : url.pathname.startsWith('/after/') ? path.join(candidates, name) : path.join(root, name);
  if (!fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  if (name.endsWith('_sprites.txt')) {
    const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([p]) => p === 'body' || p.startsWith('armor_')));
    const folder = url.pathname.startsWith('/before/') ? 'before' : 'after';
    for (const files of Object.values(meta.parts)) for (const key of ['png', 'depth']) files[key] = '../'+folder+'/'+files[key];
    res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(meta));
  }
  res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : name.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  let browser, checks = 0;
  try {
    await new Promise(r => server.listen(0, '127.0.0.1', r));
    browser = await chromium.launch({ headless: true });
    for (const cls of classes) {
      const page = await browser.newPage({ viewport: { width: 1400, height: 400 } });
      const errors = []; page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://127.0.0.1:${server.address().port}/`);
      const result = await page.evaluate(async cls => {
        const Base = { warrior: WarriorSprite, mage: MageSprite, assassin: AssassinSprite, priest: PriestSprite, hunter: HunterSprite }[cls];
        const stem = (cls === 'warrior' ? 'warrior_layered' : cls) + '_f';
        const Previous = class extends Base.Female {}, Current = class extends Base.Female {};
        Previous.METADATA = `/before/${stem}_sprites.txt`; Current.METADATA = `/after/${stem}_sprites.txt`;
        const look = { class: cls, gender: 'female', [cls+'Armor']: 'none', [cls+'Weapon']: 'none', hair: 0, skin: 0, head: 'none', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
        const old = await Previous.load(look), current = await Current.load(look);
        const tiers = Object.keys(current.meta.equipment.armor).filter(t => t !== 'none');
        for (const s of [old, current]) for (const tier of tiers) await s.source.ensure('armor_'+tier);
        const canvas = document.querySelector('canvas'), g = canvas.getContext('2d');
        const pixels = frame => frame.getContext('2d').getImageData(0,0,160,160).data;
        let frames = 0, changed = 0;
        const sample = {};
        for (const tier of ['none', ...tiers]) {
          old.set({ ...look, [cls+'Armor']: tier }); current.set({ ...look, [cls+'Armor']: tier });
          for (const [clip, spec] of Object.entries(current.meta.clips)) for (let dir=0;dir<8;dir++) for (let k=0;k<spec.n;k++) {
            const a = pixels(old.frame(clip,dir,k)), b = pixels(current.frame(clip,dir,k));
            let opaque = 0, delta = 0;
            for (let i=0;i<b.length;i+=4) { if (b[i+3]) opaque++; if ([0,1,2,3].some(j => a[i+j] !== b[i+j])) delta++; }
            if (opaque < 100) throw Error(`${cls}/${tier}/${clip}/${dir}/${k}: missing figure`);
            if (delta) changed++;
            frames++;
            if (clip === 'idle' && k === 0 && [0,6,7].includes(dir)) sample[`${tier}/${dir}`] = delta;
          }
        }
        // Show unchanged clothing choices and poses, at identical scale, before and after.
        g.fillStyle = '#20313d'; g.fillRect(0,0,1400,310); g.imageSmoothingEnabled = false;
        g.fillStyle = '#ffdf88'; g.font = 'bold 23px sans-serif'; g.fillText(cls[0].toUpperCase()+cls.slice(1),18,30);
        const starter = current.meta.defaultEquipment.armor;
        for (let column=0;column<4;column++) {
          const sprite = column%2 ? current : old, tier = column<2 ? 'none' : starter;
          sprite.set({ ...look, [cls+'Armor']: tier });
          const x = column*350;
          g.font = '18px sans-serif'; g.fillStyle = '#e4edf4';
          g.fillText(`${column%2 ? 'After' : 'Before'} — ${column<2 ? 'cloth' : 'armor'}`,x+20,60);
          for (const [i,dir] of [7,6].entries()) g.drawImage(sprite.frame('idle',dir,0),40,10,80,115,x+10+i*165,72,160,230);
        }
        return { frames, changed, sample, image: canvas.toDataURL('image/png') };
      }, cls);
      assert.ok(result.changed > result.frames/2, `${cls}: new geometry must reach the compositor across poses/outfits`); checks++;
      for (const [key, count] of Object.entries(result.sample)) { assert.ok(count > 0, `${cls}/${key}: chest change must remain visible`); checks++; }
      assert.equal(errors.length,0,errors.join('; ')); checks++;
      fs.writeFileSync(path.join(out, cls+'-comparison.png'), Buffer.from(result.image.split(',')[1], 'base64'));
      console.log(`${cls}: ${result.frames} actual composite frames, ${result.changed} changed`);
      await page.close();
    }
    console.log(`female-torso-art: ${checks} checks passed`);
  } finally { if (browser) await browser.close(); server.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
