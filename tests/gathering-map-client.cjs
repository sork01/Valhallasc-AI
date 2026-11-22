// Exercise the real tracker with controlled snapshots and a recording canvas.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const button = {
  hidden: true, dataset: {}, attributes: {},
  setAttribute(name, value) { this.attributes[name] = value; },
  addEventListener(type, fn) { this[type] = fn; },
};
const context = vm.createContext({ window: {}, document: {getElementById: () => button} });
let source = fs.readFileSync(require.resolve('../client/gathering-map.js'), 'utf8');
const mutations = {
  untrained: ['learned = own.gathering;', 'learned = {ore:true,flowers:true};'],
  stale: ['veins = packet.miningVeins || [];', 'veins = packet.miningVeins || veins;'],
  edge: ['if (!hasVisible && nearest) {', 'if (false) {'],
};
if (process.env.MUTATE) {
  const [before, after] = mutations[process.env.MUTATE];
  assert(source.includes(before));
  source = source.replace(before, after);
}
vm.runInContext(source, context);
const {sync, reset, draw} = context.window.GatheringMap;
const packets = {miningVeins:[{id:11,x:88,y:60}], flowerPatches:[{id:12,x:35,y:80}]};
const oreOnly = {gathering:{ore:true,flowers:false}}, both = {gathering:{ore:true,flowers:true}};

function plot() {
  const calls = [];
  const g = new Proxy({}, {get(target, key) {
    return target[key] ?? ((...args) => calls.push([key,...args]));
  }});
  draw(g, 1, 0, 0, 144);
  return calls;
}
const mode = () => button.dataset.mode;
sync(packets, {});
assert.equal(button.hidden, true, 'an untrained character cannot track resources');
button.click();
assert.deepEqual(plot(), []);

sync(packets, oreOnly);
assert.equal(button.hidden, false);
assert.equal(mode(), 'off');
button.click();
assert.equal(mode(), 'ore');
assert.equal(button.attributes['aria-pressed'], 'true');
assert(plot().some(call => call.join() === 'moveTo,88,55'), 'the active vein uses its snapshot coordinates');
button.click();
assert.equal(mode(), 'off', 'an ore-only character skips the flower mode');

sync(packets, both);
button.click();
button.click();
assert.equal(mode(), 'flowers');
assert(plot().some(call => call.slice(0,4).join() === 'arc,35,80,5'), 'flower mode draws a differently shaped mark');
button.click();
assert.equal(mode(), 'off');
assert.deepEqual(plot(), []);

sync(packets, {gathering:{flowers:true}});
button.click();
assert.equal(mode(), 'flowers', 'a flower-only character skips the ore mode');
sync(packets, oreOnly);
assert.equal(mode(), 'off', 'a missing profession clears that mode');
button.click();

sync({miningVeins:[{id:13,x:500,y:72},{id:14,x:72,y:-40}]}, oreOnly);
assert(plot().some(call => call.join() === 'translate,72,7'), 'the edge arrow points toward the closest off-map vein');
sync({miningVeins:[{id:15,x:38,y:48},{id:14,x:72,y:-40}]}, oreOnly);
const relocated = plot();
assert(relocated.some(call => call.join() === 'moveTo,38,43'), 'a replacement marker follows the next snapshot');
assert(!relocated.some(call => call[0] === 'rotate'), 'an in-view resource needs no edge arrow');
sync({flowerPatches:packets.flowerPatches}, oreOnly);
assert.equal(mode(), 'ore', 'the selected mode survives a zone change');
assert.deepEqual(plot(), [], 'an empty zone clears old vein positions');
reset();
assert.equal(mode(), 'off');
assert.equal(button.hidden, true);
console.log('Gathering minimap passed skill gating, mode cycling, marker geometry, edge direction and snapshot replacement.');
