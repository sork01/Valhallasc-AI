const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { chromium } = require('./lib/playwright.cjs');
const { requireMemoryLimit } = require('./lib/touch.cjs');

requireMemoryLimit();
const root = path.resolve(__dirname, '..');
const zone = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'))).zones[44];
const huts = zone.objects.filter(object => object.kind === 'ew_hut');
const output = path.join(root, 'test-results/emberwake-hut');
const oldArt = () => execFileSync('git', ['show', 'acd1bdc7:client/emberwakeart.js'], { cwd: root, encoding: 'utf8' });
const current = fs.readFileSync(path.join(root, 'client/emberwakeart.js'), 'utf8');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    assert.ok(huts.length > 0, 'Emberwake has authored basalt huts');
    const page = await browser.newPage();
    await page.setContent('<div id="npc-dialogue"></div><button id="npc-x"></button><button id="npc-back"></button><canvas width="500" height="380"></canvas>');
    await page.addScriptTag({ path: path.join(root, 'client/city.js') });
    await page.addScriptTag({ content: process.env.MUTATE === 'flat' ? oldArt() : current });
    const seen = await page.evaluate(huts => {
      const art = City.art.ew_hut;
      const canvas = document.querySelector('canvas'), g = canvas.getContext('2d', { willReadFrequently: true });
      const [width, height, anchorX, anchorY] = art.box;
      const original = City.kit.wallPlane;
      const results = [];
      for (const hut of huts) {
        g.clearRect(0, 0, canvas.width, canvas.height);
        const planes = [];
        City.kit.wallPlane = (...args) => { planes.push(args[3]); return original(...args); };
        g.save(); g.translate(anchorX + 20, anchorY + 20); art.draw(g, hut); g.restore();
        City.kit.wallPlane = original;
        const pixels = g.getImageData(0, 0, canvas.width, canvas.height).data;
        let opaque = 0, clipped = 0;
        for (let i = 3; i < pixels.length; i += 4) {
          if (!pixels[i]) continue;
          opaque++;
          const x = ((i - 3) / 4) % canvas.width, y = Math.floor((i - 3) / 4 / canvas.width);
          if (x <= 20 || x >= width + 19 || y <= 20 || y >= height + 19) clipped++;
        }
        results.push({ planes, opaque, clipped });
      }
      g.clearRect(0, 0, canvas.width, canvas.height);
      City.drawObject(g, huts[0], anchorX + 20, anchorY + 20);
      return { objects: results, png: canvas.toDataURL().split(',')[1] };
    }, huts);
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(path.join(output, process.env.MUTATE === 'flat' ? 'previous.png' : 'release.png'), Buffer.from(seen.png, 'base64'));
    for (const hut of seen.objects) {
      assert.deepEqual(hut.planes, ['y', 'x'], 'Emberwake hut draws openings on both isometric faces');
      assert.ok(hut.opaque > 10000 && hut.clipped === 0, 'Emberwake hut fits inside the cached sprite');
    }
    console.log(`emberwake-hut-art: ${seen.objects.length} authored huts fit their isometric sprites`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
