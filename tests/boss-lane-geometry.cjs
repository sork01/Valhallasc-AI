// Match the real warning polygon to the lane boundary cases in bossmech.rs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = { window: {}, performance: { now: () => 0 } };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../client/bossmech.js'), 'utf8'), context);
const polygons = context.window.BossMech._polygons;
const inside = (poly, point) => {
  const crosses = poly.map((a, i) => {
    const b = poly[(i + 1) % poly.length];
    return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0]);
  });
  return crosses.every(n => n >= 0) || crosses.every(n => n <= 0);
};
let checks = 0;
for (const [dx, dy] of [[1, 0], [0, 1], [.6, .8], [-.6, -.8]]) for (const half of [2, 3]) {
  const point = (along, across) => [10 + dx * along - dy * across, 20 + dy * along + dx * across];
  const [x2, y2] = point(10, 0);
  const [poly] = polygons({ t: 'lane', x1: 10, y1: 20, x2, y2, half });
  for (const [along, across, expected] of [[5, half - .01, true], [5, half + .01, false], [.01, 0, true], [9.99, 0, true], [-1, 0, false], [11, 0, false], [-.5, half * .5, false]]) {
    assert.equal(inside(poly, point(along, across)), expected, `lane ${dx},${dy} half ${half}, point ${along},${across}`);
    checks++;
  }
}
console.log(`boss-lane-geometry: ${checks} actual warning-polygon checks passed`);
