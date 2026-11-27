'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
let source = fs.readFileSync(path.join(__dirname, '../client/field.js'), 'utf8');
if (process.env.MUTATE === 'padding') source = source.replace(
  'g.drawImage(c, 0, 0, G.w * chunkScale, G.h * chunkScale, dx, dy, G.w, G.h);',
  'g.drawImage(c, dx, dy, G.w, G.h);');
const sandbox = {
  window: {}, document: { addEventListener() {} }, addEventListener() {},
  WORLD_MAP: {}, WORLD_SKILLS: [], CATHEDRAL_ENEMIES: [], Online: { id: 'test' },
  matchMedia: () => ({ matches: false }),
};
vm.runInNewContext(source.replace('  window.Field = Field;', `
  window.Field = Field;
  window.groundBlitTest = (g, c, dx, dy, scale, geometry) => {
    chunkScale = scale; drawGroundChunk(g, c, dx, dy, geometry);
  };
`), sandbox);
let checks = 0;
for (const scale of [.375, .6, .8, 1, 1.2, 1.333, 1.5]) {
  for (const [dx, dy] of [[0, 0], [-33.25, 12.5], [1900, -750]]) {
    const G = { w: 812, h: 556 }, c = { width: Math.ceil(G.w * scale), height: Math.ceil(G.h * scale) };
    let call;
    sandbox.window.groundBlitTest({ drawImage: (...args) => { call = args; } }, c, dx, dy, scale, G);
    const [image, sx, sy, sw, sh, tx, ty, tw, th] = call;
    assert.equal(image, c);
    assert.equal(call.length, 9, 'ground blits select the painted source rectangle');
    assert.deepEqual([sx, sy, tx, ty, tw, th], [0, 0, dx, dy, G.w, G.h], 'world placement and extent stay unchanged');
    assert.ok(sw <= c.width && sh <= c.height && c.width - sw < 1 && c.height - sh < 1, 'only rounding padding is excluded');
    // At a matched raster/backing scale, every source pixel maps to exactly
    // one output pixel. At the 1.5 raster cap or a small resize it keeps the
    // intended scale, rather than independently squeezing the two axes.
    for (const backing of [scale, scale + .025, 2.4]) {
      assert.ok(Math.abs(tw * backing / sw - backing / scale) < 1e-12);
      assert.ok(Math.abs(th * backing / sh - backing / scale) < 1e-12);
    }
    checks++;
  }
}
console.log(`Ground blits: ${checks} fractional-scale, placement and backing-scale cases passed.`);
