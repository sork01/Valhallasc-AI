// The Crags' wall ends in a tower on the 0-1 border (atlas 456.2, 727) and the city's east wall starts from it (owner, 2026-11-06: "where meadow meets crags
// on the Skaldholm wall, from the meadow side the wall is missing a tower, from the Crags side the tower is there"). Greenmeadow never draws a neighbour's piece
// over its own land, so the tower must be Greenmeadow's own piece as well, identical to the Crags' (collision and art). Pure data check.
// MAP=<file> checks another map (mutation: the map of the commit before must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const world = JSON.parse(fs.readFileSync(process.env.MAP || path.join(__dirname, '../world/map.txt'), 'utf8'));
const crags = world.zones[0];
assert.equal(crags.name, 'Emberfall Crags');
const atlas = (z, o) => [+(o.x + z.shape.T[0]).toFixed(1), +(o.y + z.shape.T[1]).toFixed(1)];
const towersAt = (z, x, y) => z.objects.filter(o => o.kind === 'tower' && Math.hypot(atlas(z, o)[0] - x, atlas(z, o)[1] - y) < 0.2);
const tc = towersAt(crags, 456.2, 727);
assert.equal(tc.length, 1, "the Crags' wall ends in one tower at (456.2, 727)");
const tg = towersAt(world, 456.2, 727);
assert.equal(tg.length, 1, `Greenmeadow has ${tg.length} towers at the Crags' end tower (456.2, 727), want exactly one`);
for (const k of ['width', 'depth', 'color', 'r', 'v']) assert.equal(tg[0][k], tc[0][k], `the two towers differ in ${k}`);
// every wall piece of the city's east wall below it is still there (the tower is its start)
const city = world.zones[3];
assert.ok(city.objects.filter(o => o.kind === 'rampart' && o.layout === 'skaldholm_east_wall').length >= 4, "the city's east wall run");
console.log('seam-tower: Greenmeadow stands the same end tower as the Crags at (456.2, 727): ok');
