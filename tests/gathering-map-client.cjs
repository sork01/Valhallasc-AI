// Exercise the real tracker with controlled snapshots and a recording canvas.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const prefs = {};
const context = vm.createContext({ window: { Prefs: prefs } });
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
const oreMarker = () => plot().some(call => call.join() === 'moveTo,88,55');
const flowerMarker = () => plot().some(call => call.slice(0,4).join() === 'arc,35,80,5');
sync(packets, {});
assert.deepEqual(plot(), [], 'an untrained character sees no markers');
sync(packets, oreOnly);
assert(oreMarker(), 'learning mining automatically shows ore');
assert(!flowerMarker());
sync(packets, both);
assert(oreMarker() && flowerMarker(), 'learning Alchemy adds flowers without hiding ore');
prefs.trackOre = false;
assert(!oreMarker() && flowerMarker(), 'the ore setting is independent');
prefs.trackFlowers = false;
assert.deepEqual(plot(), [], 'both settings can be disabled');
prefs.trackOre = true;
prefs.trackFlowers = true;
sync(packets, {gathering:{flowers:true}});
assert(!oreMarker() && flowerMarker(), 'training is per character');

sync({miningVeins:[{id:13,x:500,y:72},{id:14,x:72,y:-40}]}, oreOnly);
assert(plot().some(call => call.join() === 'translate,72,7'), 'the edge arrow points toward the closest off-map vein');
sync({miningVeins:[{id:15,x:38,y:48},{id:14,x:72,y:-40}]}, oreOnly);
const relocated = plot();
assert(relocated.some(call => call.join() === 'moveTo,38,43'), 'a replacement marker follows the next snapshot');
assert(!relocated.some(call => call[0] === 'rotate'), 'an in-view resource needs no edge arrow');
sync({flowerPatches:packets.flowerPatches}, oreOnly);
assert.deepEqual(plot(), [], 'an empty zone clears old vein positions');
reset();
assert.deepEqual(plot(), [], 'reset clears the training and latest positions');
console.log('Gathering minimap passed automatic tracking, independent Settings, marker geometry, edge direction and snapshot replacement.');
