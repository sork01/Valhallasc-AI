// Which body layer the compositor draws (no browser): a woman's long hair is baked into `body`, so under a worn head piece
// MageSprite draws `body_hat` (the body without it). Loads the real client/magesprite.js in a vm with a tiny fake source.
// MUTATE=1 makes the selector ignore the head piece (must fail).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

let code = fs.readFileSync(path.resolve(__dirname, '../client/magesprite.js'), 'utf8');
if (process.env.MUTATE === '1') {
  const before = code;
  code = code.replace("parts['head_' + equipment.head] ? 'body_hat' : 'body'", "parts['head_' + equipment.head] ? 'body' : 'body'");
  assert.notEqual(code, before, 'mutation did not apply');
}
const fake = () => ({ width: 0, height: 0, getContext: () => ({ createImageData: (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) }), putImageData() {} }) });
const window = { matchMedia: () => ({ matches: false }), WORLD_ITEMS: [], addEventListener() {}, dispatchEvent() {} };
class InactiveMessageChannel { port1 = {}; port2 = {}; }
const sandbox = { window, navigator: { vendor: '' }, document: { createElement: fake }, MessageChannel: InactiveMessageChannel, performance, console, setTimeout, Promise };
vm.runInNewContext(code, sandbox);
const { MageSprite } = window;
assert.equal(typeof MageSprite.bodyPart, 'function');

// Pure selection.
const parts = (...names) => Object.fromEntries(names.map(n => [n, {}]));
const withHat = parts('body', 'body_hat', 'head_ironhide');
assert.equal(MageSprite.bodyPart(withHat, { head: 'ironhide' }), 'body_hat', 'a worn head piece swaps in the hairless body');
assert.equal(MageSprite.bodyPart(withHat, { head: 'none' }), 'body', 'no head piece keeps the long hair');
assert.equal(MageSprite.bodyPart(withHat, {}), 'body');
assert.equal(MageSprite.bodyPart(parts('body', 'body_hat'), { head: 'ironhide' }), 'body', 'head piece not loaded yet: no bald flash');
assert.equal(MageSprite.bodyPart(parts('body', 'head_ironhide'), { head: 'ironhide' }), 'body', 'a man (no body_hat) is unchanged');

// Through frame(): a 1x1 frame per part with a distinct colour shows which body was composited.
const cell = (r, g, b, z) => ({ x: 1, y: 1, w: 1, h: 1, pixels: new Uint8ClampedArray([r, g, b, 255]), z: new Uint16Array([z]) });
const frames = (r, g, b, z) => new Proxy({}, { get: () => cell(r, g, b, z) });
const meta = { frame: [4, 4], anchor: [2, 3], clips: { idle: { row0: 0, n: 1, fps: 1 } }, ramps: { hair: ['#4a2a68', '#7a52a0', '#ac78c4', '#dcb4ec'], brow: ['#4a2a68', '#7a52a0', '#ac78c4', '#dcb4ec'], skin: ['#92595c', '#ce9182', '#f0bfac', '#ffe0ce'] }, defaultEquipment: {}, equipment: {}, parts: {} };
function composite(head, withHatPart) {
  const source = { meta, parts: { body: frames(10, 0, 0, 1000), head_ironhide: frames(0, 0, 200, 500) }, ensure: () => Promise.resolve() };
  if (withHatPart) { source.parts.body_hat = frames(0, 90, 0, 1000); meta.parts.body_hat = {}; } else delete meta.parts.body_hat;
  const sprite = new MageSprite(source, { head: head ? 'ironhide' : 'none' });
  sprite.equipment = { ...sprite.equipment, head: head ? 'ironhide' : 'none' };
  sprite.cache.clear();
  const px = sprite.frame('idle', 0, 0)._px;
  return [...px.slice((1 * 4 + 1) * 4, (1 * 4 + 1) * 4 + 4)];
}
assert.deepEqual(composite(false, true), [10, 0, 0, 255], 'bareheaded: the ordinary body');
assert.deepEqual(composite(true, false), [0, 0, 200, 255], 'a man: head piece over his body');
// The head piece is nearer than either body, so look at a pixel the head piece does not cover: use a body-only probe.
{
  const source = { meta, parts: { body: frames(10, 0, 0, 1000), body_hat: frames(0, 90, 0, 1000), head_ironhide: { 'idle/0/0': { x: 2, y: 2, w: 1, h: 1, pixels: new Uint8ClampedArray([0, 0, 200, 255]), z: new Uint16Array([500]) } } }, ensure: () => Promise.resolve() };
  meta.parts.body_hat = {};
  const at = (sprite, x, y) => [...sprite.frame('idle', 0, 0)._px.slice((y * 4 + x) * 4, (y * 4 + x) * 4 + 4)];
  const hatted = new MageSprite(source, {}); hatted.equipment = { ...hatted.equipment, head: 'ironhide' }; hatted.cache.clear();
  assert.deepEqual(at(hatted, 1, 1), [0, 90, 0, 255], 'headgear on: the body drawn is the hairless one');
  const bare = new MageSprite(source, {}); bare.equipment = { ...bare.equipment, head: 'none' }; bare.cache.clear();
  assert.deepEqual(at(bare, 1, 1), [10, 0, 0, 255], 'headgear off: the long-haired one');
}
console.log('hat-hair-unit: ok');
