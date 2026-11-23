const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const world = JSON.parse(read('world/map.txt'));
const window = {};
vm.runInNewContext(read('client/world.js'), { window });
const client = window.WORLD_MAP;
const serverAreas = [world, ...world.zones];
const clientAreas = [client, ...client.zones];

if (process.env.MUTATE === 'radius') delete client.places.find(p => p.id === 'fold_watch_m').holdRadius;
let sites = 0;
for (const [zone, area] of serverAreas.entries()) {
  const targets = new Set((area.quests || []).flatMap(q => q.objectives
    .filter(o => o.kind === 'hold').map(o => o.target)));
  const places = area.places || [];
  const holds = places.filter(p => targets.has(p.id));
  assert.equal(holds.length, targets.size, `zone ${zone}: every hold objective has a place`);
  for (const place of places) {
    const radius = targets.has(place.id) ? +(place.r + 2.5).toFixed(2) : undefined;
    assert.equal(place.holdRadius, radius, `${place.id}: authoritative hold radius`);
    assert.equal(clientAreas[zone].places?.find(p => p.id === place.id)?.holdRadius, radius,
      `${place.id}: client hold radius matches`);
  }
  for (const [i, a] of holds.entries()) for (const b of holds.slice(i + 1)) {
    assert.ok(Math.hypot(a.x - b.x, a.y - b.y) > a.holdRadius + b.holdRadius,
      `${a.id} and ${b.id}: separate hold timers need distinct circles`);
  }
  sites += holds.length;
}

const source = read('client/emptyseat.js');
const emptySeat = process.env.MUTATE === 'stones' ? source.replace('p.holdRadius ?? p.r', 'p.r') : source;
vm.runInNewContext(emptySeat, { window, WORLD_MAP: client, document: { getElementById: () => null } });
const project = (x, y) => [x, y];
for (const [zone, area] of clientAreas.entries()) {
  window.EmptySeat.sync(null, zone);
  const items = window.EmptySeat.ringItems(project, () => true);
  for (const place of (area.places || []).filter(p => p.ring)) {
    const stones = items.filter(s => s.ring.id === place.id);
    assert.equal(stones.length, place.ring.stones, `${place.id}: all ring stones are drawn`);
    for (const { stone } of stones) {
      const distance = Math.hypot(stone.x - place.x, stone.y - place.y);
      assert.ok(Math.abs(distance - (place.holdRadius ?? place.r)) <= .13,
        `${place.id}: ring stones follow the objective boundary`);
    }
  }
}
console.log(`hold-areas: ${sites} server/client boundaries and Empty Seat stone layouts passed`);
