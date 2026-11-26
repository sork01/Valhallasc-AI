const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('client/field.js', 'utf8');
let handler = source.slice(source.indexOf("    if (event.kind === 'itemPickup') {"), source.indexOf("    if (event.kind === 'shotBlocked')"));
if (process.env.MUTATE) handler = handler.replace("[rarity] || '#64b5ff'", "['rare'] || '#64b5ff'");
const colors = { common: '#c4c4c4', uncommon: '#4ad66d', rare: '#64b5ff', epic: '#b45cff', legendary: '#ff9a2e', hierloom: '#ffd24a', gm: '#ffd24a' };
const css = fs.readFileSync('client/online.css', 'utf8');
for (const [rarity, color] of Object.entries(colors)) {
  if (!['hierloom'].includes(rarity)) assert.ok(css.includes(`.inventory-item[data-rarity="${rarity}"] b { color: ${color}; }`));
  for (const rolled of [false, true]) {
    let result;
    vm.runInNewContext(handler, {
      event: { kind: 'itemPickup', actor: 1, item: 'gear', rarity: rolled ? rarity : undefined, quantity: 1, name: 'Test Sword', x: 10, y: 20 },
      WORLD_ITEMS: [{ id: 'gear', kind: 'weapon', rarity: rolled ? 'common' : rarity }],
      Online: { id: 1 }, say() {}, burst() {}, bagColor: () => '#bag',
      floater: (...args) => { result = args; }
    });
    assert.equal(result[3], color, `${rarity}: ${rolled ? 'rolled' : 'catalog'} rarity`);
    assert.equal(result[2], '+1 Test Sword');
  }
}
console.log('Equipment pickup colors match all seven rarities, including rolled rarity overrides');
