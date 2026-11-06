// The city's east wall (atlas x 456.2) runs from the Crags' end tower (y 727) to the south-east corner tower (y 757.7) without a hole (owner, 2026-11-06:
// "in the south east corner of the wall in meadow going north, the first piece of wall is missing"): the generator stopped one piece short and left 3.8 tiles
// between the last rampart and the corner tower. Pure data check. MAP=<file> checks another map (mutation: the map of the commit before must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const world = JSON.parse(fs.readFileSync(process.env.MAP || path.join(__dirname, '../world/map.txt'), 'utf8'));
const city = world.zones.find(z => z.name === 'Skaldholm');
const TC = [352, 584];
const spans = city.objects.filter(o => o.layout === 'skaldholm_east_wall' && (o.kind === 'rampart' || o.kind === 'tower'))
  .map(o => [o.y + TC[1] - o.depth / 2, o.y + TC[1] + o.depth / 2, o.kind]).sort((a, b) => a[0] - b[0]);
assert.equal(spans.filter(s => s[2] === 'tower').length, 1, 'one corner tower');
const tower = spans.find(s => s[2] === 'tower');
assert.ok(Math.abs(tower[1] - tower[0] - 3.4) < 0.01 && Math.abs((tower[0] + tower[1]) / 2 - 757.7) < 0.05, 'the corner tower stands at y 757.7');
let reach = 727 + 1.7;                                   // the Crags' end tower's south face: the wall starts here
for (const [a, b, kind] of spans) {
  assert.ok(a <= reach + 0.15, `hole in the east wall: nothing covers y ${reach.toFixed(2)} to ${a.toFixed(2)} (before the ${kind})`);
  reach = Math.max(reach, b);
}
assert.ok(reach >= 757.7 + 1.7 - 0.01, 'the wall reaches the corner tower');
console.log(`east-wall-gapless: ${spans.length} pieces cover y 728.7 to ${reach.toFixed(2)} without a hole: ok`);
