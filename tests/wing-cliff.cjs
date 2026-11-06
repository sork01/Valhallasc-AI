// The wing's north edge is a cliff you can see, and no seam neighbour paints over its land (owner, 2026-11-06: "going alongside the right Skaldholm wall in meadow
// there is this black ground and then you get stopped by an invisible wall"). The client draws a seam neighbour's outside tiles AFTER our own ground, so a Crags `l`
// cell on the wing's land showed as dark rock; and with no letter on the void north of the wing the land ended in flat dark with no cliff.
// Pure data check (no server, no browser). MAP=<file> checks another map (mutation: `git show HEAD~:world/map.txt` must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const world = JSON.parse(fs.readFileSync(process.env.MAP || path.join(__dirname, '../world/map.txt'), 'utf8'));
const meadow = world, crags = world.zones[0];
assert.equal(crags.name, 'Emberfall Crags');
const [gx, gy] = meadow.shape.T, [cx, cy] = crags.shape.T;
const gLand = (x, y) => meadow.shapeFloor[y]?.[x] === '#', cLand = (x, y) => crags.shapeFloor[y + gy - cy]?.[x + gx - cx] === '#';
const cEdge = (x, y) => crags.shapeEdge[y + gy - cy]?.[x + gx - cx] || ' ';
let over = 0, ourOver = 0;
for (let y = 0; y < meadow.size; y++) for (let x = 0; x < meadow.size; x++) {
  if (gLand(x, y) && cEdge(x, y) === 'l') over++;                                           // a Crags outer-land tile on our land
  if (cLand(x, y) && meadow.shapeEdge[y][x] === 'l' && !gLand(x, y)) ourOver++;             // our outer-land tile on Crags land
}
assert.equal(over, 0, `${over} Crags outer-land tiles lie on Greenmeadow's land (drawn as dark rock over the wing)`);
assert.equal(ourOver, 0, `${ourOver} Greenmeadow outer-land tiles lie on Crags land`);
// the wing: land east of the city's east wall (x 178.2) whose north neighbour is void must have an edge letter there (the client draws the cliff block from it)
let rim = 0;
for (let x = 180; x < 224; x++) for (let y = 90; y < 110; y++) {
  if (gLand(x, y) && !gLand(x, y - 1)) { rim++; assert.notEqual(meadow.shapeEdge[y - 1][x], ' ', `the wing's north rim at (${x}, ${y}) has no edge letter: the land would end in flat dark with no cliff`); }
}
assert.ok(rim >= 40, `only ${rim} rim cells found: the wing's north edge moved, update this test`);
console.log(`wing-cliff: no Crags tile over our land, no tile of ours over theirs, ${rim} rim cells all carry a cliff letter: ok`);
