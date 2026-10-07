// The first map must be a whole 96x96 field, not a compact cluster with an empty eastern half.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { route } = require('../scripts/testing/route.cjs');
const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt')));
const client = JSON.parse(fs.readFileSync(path.join(root, 'client/world.js'), 'utf8').replace(/^'use strict';\s*window\.WORLD_MAP = /, '').replace(/;\s*$/, ''));
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
check(JSON.stringify(client) === JSON.stringify(map), 'the client and server use the same map');
check(map.size === 96 && map.spawn.x === 36 && map.spawn.y === 60, 'size and original start are preserved');
check(map.city.x0 === 24 && map.city.x1 === 48 && map.city.y0 === 72 && map.city.y1 === 94, 'Alderhaven is untouched');
check(map.portals.find(p => p.id === 'emberfall_gate')?.x === 54, 'the Crags gate stays in place');
check(map.objects.filter(o => o.layout === 'greenmeadow_wide_v1').length === 175, 'the added scenery has a stable count');
check(map.slimes.filter(s => s.layout === 'greenmeadow_wide_v1').length === 11, 'the added enemies have a stable count');
check(map.slimes.filter(s => s.kind === 'big').length === 2, 'both King Slime spawn slots remain');
check(map.slimes.some(s => s.kind === 'big' && s.x === 84 && s.y === 41), 'the King can appear in the east');
check(map.objects.some(o => o.kind === 'water' && o.x > 70), 'the eastern pond is present');
check(map.objects.filter(o => o.layout === 'greenmeadow_wide_v1' && o.kind === 'rock' && Math.hypot(o.x - 82, o.y - 82) < 5.5).length === 7, 'seven stones mark the southeastern ring');
check(!map.objects.some(o => o.layout === 'greenmeadow_wide_v1' && ['tree', 'bush'].includes(o.kind) && Math.hypot(o.x - 82, o.y - 82) < 7.5), 'the stone circle has a clear grass floor');
check(map.paths.length === 7 && map.paths.some(p => p.some(([x, y]) => x >= 87 && y >= 80)), 'trails reach the southeast');
for (let by = 0; by < 6; by++) for (let bx = 0; bx < 6; bx++) {
  check(map.objects.some(o => o.x >= bx * 16 && o.x < (bx + 1) * 16 && o.y >= by * 16 && o.y < (by + 1) * 16), `scenery reaches map block ${bx},${by}`);
}
for (const target of [{ x: 8, y: 84 }, { x: 90, y: 88 }, { x: 89, y: 10 }, { x: 54, y: 13.5 }, { x: 79, y: 72 }]) {
  check(route(map, map.spawn, target).length > 0, `player can reach ${target.x},${target.y}`);
}
for (const spawn of map.slimes.filter(s => s.layout === 'greenmeadow_wide_v1')) {
  check(route(map, map.spawn, spawn).length > 0, `${spawn.kind} spawn at ${spawn.x},${spawn.y} is reachable`);
}
console.log(`${checks} Greenmeadow layout checks passed`);
