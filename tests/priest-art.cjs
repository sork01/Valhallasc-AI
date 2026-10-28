// Real Priest PNGs and compositor, without loading the rest of the world.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
require('./lib/touch.cjs').requireMemoryLimit();
const root = path.resolve(__dirname, '..', 'client');
const hair = process.argv.includes('--hair');
const output = path.resolve(__dirname, '..', hair ? 'test-results/priest-hair' : 'test-results/priest-hood');
const server = http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  if (name === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end('<!doctype html><canvas id="sheet" width="1280" height="400"></canvas><script src="items.js"></script><script src="magesprite.js"></script><script src="priestsprite.js"></script>');
  }
  const file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  if (process.env.PRIEST_HAIR_PREVIEW === '1' && /priest_f_(body(_depth)?\.png|bounds\.txt)$/.test(name)) {
    res.setHeader('Content-Type', name.endsWith('.png') ? 'image/png' : 'text/plain');
    return fs.createReadStream(path.join(output, path.basename(name))).pipe(res);
  }
  if (/priest(_f)?_sprites\.txt$/.test(name)) {
    const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([key]) => ['body', 'armor_pilgrim', 'head_pilgrim'].includes(key)));
    res.setHeader('Content-Type', 'application/json');
    return res.end(JSON.stringify(meta));
  }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  let browser;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const result = await page.evaluate(async hair => {
      const canvas = document.querySelector('#sheet'), g = canvas.getContext('2d');
      g.fillStyle = '#283c46'; g.fillRect(0, 0, canvas.width, canvas.height);
      g.font = '16px sans-serif'; g.fillStyle = '#ffffff';
      const reports = [];
      for (const [row, C] of (hair ? [PriestSprite.Female] : [PriestSprite, PriestSprite.Female]).entries()) {
        const look = { class: 'priest', gender: hair || row ? 'female' : 'male', priestArmor: 'pilgrim', priestWeapon: 'none', head: 'pilgrim', shoulders: 'none', gloves: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
        const sprite = await C.load(look);
        await sprite.source.ensure('head_pilgrim');
        let frames = 0;
        for (const [clip, spec] of Object.entries(sprite.meta.clips)) for (let dir = 0; dir < 8; dir++) for (let k = 0; k < spec.n; k++) {
          sprite.set({ ...look, head: 'none' });
          const bare = sprite.frame(clip, dir, k)._px;
          sprite.set(look);
          const dressed = sprite.frame(clip, dir, k)._px;
          let changed = 0;
          for (let p = 0; p < bare.length; p += 4) if (bare[p] !== dressed[p] || bare[p + 1] !== dressed[p + 1] || bare[p + 2] !== dressed[p + 2] || bare[p + 3] !== dressed[p + 3]) changed++;
          if (!changed) throw Error(`Invisible hood: ${row}/${clip}/${dir}/${k}`);
          const f = sprite.source.parts[hair ? 'body' : 'head_pilgrim'][`${clip}/${dir}/${k}`];
          if (f.x <= 0 || f.y <= 0 || f.x + f.w >= 160 || f.y + f.h >= 160) throw Error('Hood touches frame boundary');
          frames++;
        }
        if (hair) {
          const colours = new Set(sprite.meta.ramps.hair.map(c => parseInt(c.slice(1), 16)));
          const mask = frame => {
            const f = sprite.source.parts.body[frame], pixels = new Uint8Array(160 * 160);
            for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
              const p = (y * f.w + x) * 4;
              if (f.pixels[p + 3] && colours.has(f.pixels[p] * 65536 + f.pixels[p + 1] * 256 + f.pixels[p + 2])) pixels[(f.y + y) * 160 + f.x + x] = 1;
            }
            return pixels;
          };
          const profile = [2, 6].map(dir => {
            const pixels = mask(`idle/${dir}/0`);
            return [75, 80].map(y => pixels.slice(y * 160, (y + 1) * 160).reduce((a, b) => a + b, 0));
          });
          const motion = new Set();
          for (let k = 0; k < sprite.meta.clips.walk.n; k++) {
            let hash = 0; for (const pixel of mask(`walk/2/${k}`)) hash = (hash * 31 + pixel) >>> 0;
            motion.add(hash);
          }
          for (let dir = 0; dir < 8; dir++) for (const [r, head] of ['none', 'pilgrim'].entries()) {
            sprite.set({ ...look, head });
            g.drawImage(sprite.frame('idle', dir, 0), 45, 10, 70, 110, dir * 160, r * 200 + 25, 112, 176);
            g.fillText(`${head === 'none' ? 'Hair' : 'Hood'} ${sprite.meta.dirs[dir]}`, dir * 160 + 20, r * 200 + 20);
          }
          reports.push({ frames, profile, motion: motion.size });
          continue;
        }
        const trim = [];
        for (let dir = 0; dir < 8; dir++) {
          const f = sprite.source.parts.head_pilgrim[`idle/${dir}/0`];
          let xsum = 0, count = 0;
          for (let y = 0; y < f.h; y++) for (let x = 0; x < f.w; x++) {
            const p = (y * f.w + x) * 4;
            if (f.pixels[p] === 232 && f.pixels[p + 1] === 184 && f.pixels[p + 2] === 64 && f.pixels[p + 3]) { xsum += f.x + x; count++; }
          }
          trim.push(count ? xsum / count - (f.x + f.w / 2) : null);
          g.drawImage(sprite.frame('idle', dir, 0), dir * 160, row * 200 + 25);
          g.fillText(`${row ? 'Female' : 'Male'} ${sprite.meta.dirs[dir]}`, dir * 160 + 35, row * 200 + 20);
        }
        reports.push({ frames, trim });
      }
      return { reports, png: canvas.toDataURL() };
    }, hair);
    for (const report of result.reports) {
      assert.equal(report.frames, 272, 'every pose and facing is rendered');
      if (hair) {
        assert.ok(report.profile.every(rows => rows.every(width => width >= 6)), 'long hair retains volume through both profiles');
        // The eight-frame sine cycle repeats its intermediate positions.
        assert.ok(report.motion >= 5, 'hair moves through all five distinct walking positions');
        continue;
      }
      assert.ok(report.trim[2] < -2, 'west-facing hood opening turns left');
      assert.ok(report.trim[6] > 2, 'east-facing hood opening turns right');
      assert.ok(Math.abs(report.trim[0]) < 2, 'front-facing hood stays centered');
      assert.ok([3, 4, 5].every(dir => report.trim[dir] === null), 'rear-facing hoods stay closed');
    }
    assert.deepEqual(errors, []);
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, 'client-facings.png'), Buffer.from(result.png.split(',')[1], 'base64'));
    console.log(hair ? 'priest-art: 272 female poses with and without a hood; profile volume and hair movement pass' : 'priest-art: 544 real composite frames; both bodies turn left/right and close at the back');
    console.log(JSON.stringify(result.reports));
  } finally {
    await browser?.close(); await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
