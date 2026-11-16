// Facing the camera, a lock of hair that lies flush on a sleeve or robe (a depth tie) must not show through the worn piece.
// Real atlases and the real compositor, female Mage in apprentice armour, shoulders and gloves. MUTATE=1 serves the compositor
// with the tie windows closed (HAIR_TIE = 0; MUTATE=back closes only the back-quarter window; MUTATE=allbehind hides all hair behind
// the shoulder piece from behind, the 2026-11-16 regression), which must fail. Run: bash scripts/test-touch-bounded.sh tests/hair-front-clothes-ui.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
require('./lib/touch.cjs').requireMemoryLimit();
const root = path.resolve(__dirname, '../client');
const WORN = ['body', 'armor_apprentice', 'shoulders_apprentice', 'gloves_apprentice'];
const server = http.createServer((req, res) => {
  const name = new URL(req.url, 'http://localhost').pathname;
  if (name === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end('<!doctype html>' + ['items', 'magesprite'].map(file => `<script src="${file}.js"></script>`).join(''));
  }
  const file = path.resolve(root, '.' + name);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  if (name === '/magesprite.js') {
    let text = fs.readFileSync(file, 'utf8');
    if (process.env.MUTATE === '1') { assert.ok(text.includes('HAIR_TIE = 400, BACK_HAIR_TIE = 150')); text = text.replace('HAIR_TIE = 400, BACK_HAIR_TIE = 150', 'HAIR_TIE = 0, BACK_HAIR_TIE = 0'); }
    if (process.env.MUTATE === 'back') { assert.ok(text.includes('BACK_HAIR_TIE = 150')); text = text.replace('BACK_HAIR_TIE = 150', 'BACK_HAIR_TIE = 0'); }
    if (process.env.MUTATE === 'allbehind') { assert.ok(text.includes('BACK_HAIR_TIE = 150')); text = text.replace('const hairKeeps = (dir, part) => BACK_DIRS.includes(dir) && part.startsWith', 'const hairKeeps = (dir, part) => false && part.startsWith').replace('const HAIR_TIE = 400', 'const HAIR_TIE = 400'); text = text.replace("if (!f.pixels[src + 3]) continue;\n          if (f.z[pixel] > nearest[dst]) {", "if (!f.pixels[src + 3]) continue;\n          if (hairAt && part.startsWith('shoulders_') && BACK_DIRS.includes(dir) && hairAt[dst]) { nearest[dst] = f.z[pixel]; hairAt[dst] = 0; out.data.set(f.pixels.subarray(src, src + 4), dst * 4); continue; }\n          if (f.z[pixel] > nearest[dst]) {"); }
    res.setHeader('Content-Type', 'text/javascript'); return res.end(text);
  }
  if (name.endsWith('mage_f_sprites.txt')) {
    const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
    meta.parts = Object.fromEntries(Object.entries(meta.parts).filter(([key]) => WORN.includes(key)));
    res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify(meta));
  }
  res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/plain');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  let browser;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 800, height: 600 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const r = await page.evaluate(async WORN => {
      if (window.__valhallaTestSprites) throw Error('Real sprites required');
      const C = MageSprite.variant({ gender: 'female' });
      const look = { class: 'mage', gender: 'female', mageArmor: 'apprentice', mageWeapon: 'none', shoulders: 'apprentice', gloves: 'apprentice', head: 'none', pants: 'none', necklace: 'none', accessory: 'none', cloak: 'none' };
      const sprite = await C.load(look);
      for (const part of ['shoulders_apprentice', 'gloves_apprentice']) await sprite.source.ensure(part);
      sprite.set(look);
      const hairColours = new Set(sprite.meta.ramps.hair.map(c => parseInt(c.slice(1), 16)));
      const parts = sprite.source.parts;
      const out = { tie: 0, shown: 0, clear: 0, clearShown: 0, otherDirs: 0, backTie: 0, backShown: 0, frames: 0 };
      for (const clip of ['idle', 'walk']) for (let dir = 0; dir < 8; dir++) for (let k = 0; k < sprite.meta.clips[clip].n; k++) {
        const key = `${clip}/${dir}/${k}`, canvas = sprite.frame(clip, dir, k), body = parts.body[key];
        out.frames++;
        for (let y = 0; y < body.h; y++) for (let x = 0; x < body.w; x++) {
          const bp = y * body.w + x, b = bp * 4;
          if (!body.pixels[b + 3] || !hairColours.has(body.pixels[b] * 65536 + body.pixels[b + 1] * 256 + body.pixels[b + 2])) continue;
          const dx = body.x + x, dy = body.y + y, at = (dy * 160 + dx) * 4;
          for (const name of WORN.slice(1)) {
            const f = parts[name][key]; if (!f.w) continue;
            const fx = dx - f.x, fy = dy - f.y;
            if (fx < 0 || fy < 0 || fx >= f.w || fy >= f.h) continue;
            const p = fy * f.w + fx; if (!f.pixels[p * 4 + 3]) continue;
            const gap = f.z[p] - body.z[bp];            // > 0: the hair is nearer
            // The pixel shows a worn piece (this one, or another that is nearer still) and not the hair.
            const same = WORN.slice(1).some(other => {
              const o = parts[other][key], ox = dx - o.x, oy = dy - o.y;
              if (!o.w || ox < 0 || oy < 0 || ox >= o.w || oy >= o.h) return false;
              const q = (oy * o.w + ox) * 4;
              return o.pixels[q + 3] && [0, 1, 2].every(c => canvas._px[at + c] === o.pixels[q + c]);
            });
            if ([3, 4, 5].includes(dir) && name === 'shoulders_apprentice') {     // from behind the hair hangs over the shoulder mantle
              // Only where the hair is still visible when the shoulder piece is laid down (the robe is drawn first and may cover it).
              const robe = parts.armor_apprentice[key], rx = dx - robe.x, ry = dy - robe.y;
              if (robe.w && rx >= 0 && ry >= 0 && rx < robe.w && ry < robe.h && robe.pixels[(ry * robe.w + rx) * 4 + 3] && robe.z[ry * robe.w + rx] <= body.z[bp]) continue;
              const sameAsShoulder = [0, 1, 2].every(c => canvas._px[at + c] === f.pixels[p * 4 + c]);
              if (gap > -150) { out.backTie++; if (sameAsShoulder) out.backShown++; }   // hair nearer, or the piece only just nearer: hair stays
              continue;
            }
            if (![0, 1, 7].includes(dir)) { if (gap > 0 && gap < 400 && !same) out.otherDirs++; continue; }
            if (gap > 0 && gap < 400) { out.tie++; if (!same) out.shown++; }
            else if (gap >= 400) { out.clear++; if (!same) out.clearShown++; }
          }
        }
      }
      return out;
    }, WORN);
    assert.deepEqual(errors, []);
    assert.ok(r.tie > 40, `the fixture must contain depth ties in the front views (${r.tie})`);
    assert.equal(r.shown, 0, `${r.shown} of ${r.tie} tied hair pixels still show through the worn pieces`);
    assert.ok(r.backTie > 100, `the fixture must contain hair over the shoulder piece in the back-quarter views (${r.backTie})`);
    assert.equal(r.backShown, 0, `${r.backShown} of ${r.backTie} hair pixels are hidden behind the shoulder piece from behind`);
    assert.ok(r.clearShown > 0, 'hair clearly in front of a worn piece still shows (the fix is not a blanket hide)');
    assert.ok(r.otherDirs > 0, 'side and back views keep their hair as before (the rule covers only the front views)');
    console.log(`hair-front-clothes-ui: ${r.frames} frames, ${r.backTie} hair pixels kept over the shoulders from behind and ${r.tie} tied hair pixels all behind the clothes, ${r.clearShown}/${r.clear} clearly-in-front hair pixels kept`);
  } finally { await browser?.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
