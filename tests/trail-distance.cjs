// Ground trails (client/field.js `trailDistances`): the tiles painted as trail are the ones the plain test of every tile
// against every trail stretch would paint. Greenmeadow is compared tile by tile, every other zone on every eleventh tile
// (the plain test is slow; ALL=1 compares every tile, about 90 s). MUTATE=reach|box must fail.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = path.resolve(__dirname, '..'), source = fs.readFileSync(path.join(root, 'client/field.js'), 'utf8');
const between = (from, to) => { const a = source.indexOf(from), b = source.indexOf(to, a); assert.ok(a >= 0 && b > a, `field.js no longer has: ${from}`); return source.slice(a, b); };
const world = { window: {} }; vm.runInNewContext(fs.readFileSync(path.join(root, 'client/world.js'), 'utf8'), world);
const map = world.window.WORLD_MAP, zones = [map, ...map.zones];
// The functions under test, taken from the client as it is.
let code = between('  const hash2 = ', '  const clamp = ') + between('  const clamp = ', '  const lerp = ') + between('  const segDist = ', '  // The distance from each tile')
  + between('  const TRAIL_REACH = ', '  const w2sRaw = ');
if (process.env.MUTATE === 'reach') code = code.replace('TRAIL_REACH = 1.75', 'TRAIL_REACH = 1.4');
if (process.env.MUTATE === 'box') code = code.replace('Math.ceil(v + TRAIL_REACH - .5)', 'Math.floor(v)');
const { vnoise, segDist, trailDistances, TRAIL_REACH } = vm.runInNewContext(`${code}; ({ vnoise, segDist, trailDistances, TRAIL_REACH })`);
// The ragged edge used by buildMap must stay within the reach the distances are collected for.
const edge = /map\.dirt\[i\] = d < TRAIL_REACH && d < ([\d.]+) \+ vnoise\(cx \* \.5, cy \* \.5, 3\) \* ([\d.]+) \? 1 : 0;/.exec(source);
assert.ok(edge, 'buildMap paints trails from the collected distances');
const [, base, spread] = edge.map(Number);
assert.ok(base + spread <= 1.75 + 1e-9, 'a trail edge cannot reach further than the distances collected');
let tiles = 0, trail = 0, checked = 0;
for (const [index, zone] of zones.entries()) {
  const size = zone.size, paths = zone.paths || [];
  if (!paths.length) continue;
  const near = trailDistances(paths, size);
  const step = index === 0 || process.env.ALL === '1' ? 1 : 11;
  for (let n = 0; n < size * size; n += step) {
    const x = n % size, y = (n / size) | 0;
    const cx = x + .5, cy = y + .5, limit = base + vnoise(cx * .5, cy * .5, 3) * spread;
    let d = 99; for (const p of paths) for (let k = 0; k < p.length - 1; k++) d = Math.min(d, segDist(cx, cy, p[k][0], p[k][1], p[k + 1][0], p[k + 1][1]));
    const i = y * size + x, want = d < limit, got = near[i] < TRAIL_REACH && near[i] < limit;
    if (want !== got) assert.fail(`zone ${index} tile ${x},${y}: trail ${want} by every stretch, ${got} from the collected distances`);
    // Within the reach the distance itself is exact (the meadow's plaza circle is combined with it).
    if (d < TRAIL_REACH && near[i] !== d) assert.fail(`zone ${index} tile ${x},${y}: distance ${near[i]}, want ${d}`);
    tiles++; if (want) trail++;
  }
  checked++;
}
assert.ok(checked >= 20 && trail > 3000, `only ${checked} zones and ${trail} trail tiles were compared`);
console.log(`trail distances match on ${tiles} tiles of ${checked} zones (${trail} trail tiles)`);
