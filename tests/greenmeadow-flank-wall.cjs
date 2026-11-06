// Greenmeadow's wall east of the Skaldholm vault is one regular run (owner, 2026-11-06: "the wall to the right of the arch looks weird in places").
// Each rampart draws floor(width / 1.2) merlons and restarts its ashlar joints, so filler pieces of 2.0 / 4.5 / 9.0 / 2.3 tiles gave uneven merlons and steps.
// Pure data check (no server, no browser). MAP=<file> checks another map (mutation: `git show HEAD~:world/map.txt` must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const world = JSON.parse(fs.readFileSync(process.env.MAP || path.join(__dirname, '../world/map.txt'), 'utf8'));
const arch = world.exitArches.find(a => a.portal === 'path_0_4');
assert.ok(arch, 'the Skaldholm vault is missing');
const towerRight = arch.x + arch.halfWidth + 1.7 + 1.7;
const walls = world.objects.filter(o => o.kind === 'rampart' && o.layout === 'shape_v1');
const wallY = walls[0].y;
const run = walls.filter(o => o.y === wallY && o.x > towerRight).sort((a, b) => a.x - b.x);
assert.ok(run.length >= 6, `the flank run has only ${run.length} pieces`);
const w0 = run[0].width;
for (const o of run) assert.ok(Math.abs(o.width - w0) < 0.02, `uneven piece at x ${o.x}: width ${o.width} (the run's is ${w0})`);
for (let i = 1; i < run.length; i++) {
  const lap = run[i - 1].x + run[i - 1].width / 2 - (run[i].x - run[i].width / 2);       // overlap between neighbours
  assert.ok(lap > 0 && lap < 0.4, `gap or stacking between x ${run[i - 1].x} and ${run[i].x}: overlap ${lap.toFixed(2)}`);
}
const pitches = run.slice(1).map((o, i) => o.x - run[i].x);
assert.ok(Math.max(...pitches) - Math.min(...pitches) < 0.2, `uneven pitch ${pitches.map(p => p.toFixed(2))}`);
console.log(`greenmeadow-flank-wall: ${run.length} pieces of ${w0.toFixed(3)} from x ${(run[0].x - w0 / 2).toFixed(2)} to ${(run.at(-1).x + w0 / 2).toFixed(2)}, pitch ${Math.min(...pitches).toFixed(2)}-${Math.max(...pitches).toFixed(2)}: ok`);
