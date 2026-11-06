// The wing opens onto the Emberfall Crags (owner, 2026-11-06: "there is still a row of 7 tiles that is brown and then invisible wall, can't pass through to crags").
// Between the wing's north edge (y 99 in Greenmeadow's frame) and the Crags' south edge (y 92) lay 7 rows of void. The 0-1 border is one straight line (y 92) from
// the city's east wall to x 234: the gap is Greenmeadow's land now, the seam runs along the line in both zones, and a walker can step across anywhere on it.
// Pure data check (no server, no browser). MAP=<file> checks another map (mutation: `git show HEAD:world/map.txt` of the commit before must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const world = JSON.parse(fs.readFileSync(process.env.MAP || path.join(__dirname, '../world/map.txt'), 'utf8'));
const meadow = world, crags = world.zones[0];
assert.equal(crags.name, 'Emberfall Crags');
const [sx, sy] = meadow.portals.find(p => p.to === 1 && p.seam).seam.shift;      // meadow cell + shift = Crags cell
// collision exactly as the server's push_out sees a walker of radius r: a void rectangle blocks it
const blocked = (z, x, y, r = 0.5) => z.objects.some(o => o.kind === 'void' && Math.abs(x - o.x) < o.width / 2 + r && Math.abs(y - o.y) < o.depth / 2 + r);
const stepsBlocked = [];
for (const x of [182, 190, 200, 210, 220, 230]) {                                  // straight north through the old gap, from the wing to the Crags' land
  for (let y = 105; y >= 86; y -= 0.5) {
    if (y >= 90.5 && blocked(meadow, x, y)) stepsBlocked.push(`meadow (${x}, ${y})`);
    if (y <= 93.5 && blocked(crags, x + sx, y + sy)) stepsBlocked.push(`crags (${x + sx}, ${y + sy})`);   // a walker over the line is the Crags' to move: its side must be open too
  }
}
assert.deepEqual(stepsBlocked.slice(0, 5), [], `${stepsBlocked.length} void-blocked steps on the way north: ${stepsBlocked.slice(0, 3)}`);
// the seam covers the whole line in both zones (the server moves a walker within 3 tiles of it)
const covers = (z, to, x0, y) => z.portals.filter(p => p.to === to && p.seam).some(p => p.seam.points.some(q => Math.abs(q[0] - x0) < 3 && Math.abs(q[1] - y) < 3));
assert.ok(covers(meadow, 1, 182, 92), 'Greenmeadow\'s 0-1 seam does not reach the city wall');
assert.ok(covers(crags, 0, 182 + sx, 92 + sy), 'the Crags\' 0-1 seam does not reach the city wall');
// no seam neighbour's outside tile on our land, and no cell of the gap is an outside tile
let over = 0;
for (let y = 0; y < meadow.size; y++) for (let x = 0; x < meadow.size; x++) {
  const e = crags.shapeEdge[y + sy]?.[x + sx] || ' ';
  if (meadow.shapeFloor[y][x] === '#' && e === 'l') over++;
}
assert.equal(over, 0, `${over} Crags outer-land tiles lie on Greenmeadow's land`);
for (let y = 92; y < 99; y++) for (let x = 180; x < 233; x++) assert.equal(meadow.shapeFloor[y][x], '#', `(${x}, ${y}) in the old gap is not land`);
console.log('wing-gate: six lines walk from the wing to the Crags without a void, the seam runs from the wall to x 234 in both zones, the gap is land: ok');
