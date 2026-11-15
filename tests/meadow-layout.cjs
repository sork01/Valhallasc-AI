// Greenmeadow (zone 0) as the zone-shapes pilot authored it: the painted outline at scale 1 is the walkable land, every
// authored spawn, place and scenery block sits on that land, and the land is one connected field with both halves in use.
// (The old 96x96 "wide" layout with its fixed scenery counts was replaced by meadow_design_v1; counts are floors now.)
// MAP=<file> checks another map instead (mutation: a map whose spawn is walled off from the rest of the land must FAIL).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(process.env.MAP || path.join(root, 'world/map.txt'), 'utf8'));
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
if (!process.env.MAP) {
  const client = JSON.parse(fs.readFileSync(path.join(root, 'client/world.js'), 'utf8').replace(/^'use strict';\s*window\.WORLD_MAP = /, '').replace(/;\s*$/, ''));
  check(JSON.stringify(client) === JSON.stringify(map), 'the client and server use the same map');
}
const F = map.shapeFloor;
const land = (x, y) => F[Math.floor(y)]?.[Math.floor(x)] === '#';
check(map.shape?.k === 1 && map.shape.rule === 'nofloor', 'Greenmeadow keeps its painted outline at scale 1 with no filler floor');
let landCells = 0, east = 0;
for (let y = 0; y < F.length; y++) for (let x = 0; x < F[y].length; x++) if (F[y][x] === '#') { landCells++; if (x >= map.size / 2) east++; }
check(Math.min(east, landCells - east) >= landCells / 3, 'both halves of the map carry land (no empty eastern or western half)');
check(land(map.spawn.x, map.spawn.y), 'the start point is on land');
check(land(map.city.plaza.x, map.city.plaza.y), 'Alderhaven plaza is on land');
const gate = map.portals.find(p => p.id === 'emberfall_gate');
check(gate?.to === 1 && gate.seam, 'the Emberfall Crags crossing is still a seam');
check(map.objects.filter(o => o.layout === 'meadow_design_v1').length >= 4000, 'the authored scenery is present (floor 4000)');
check(map.slimes.filter(s => s.layout === 'meadow_design_v1').length >= 200, 'the authored enemies are present (floor 200)');
check(map.slimes.filter(s => s.kind === 'big').length === 2, 'both King Slime spawn slots remain');
check(map.slimes.some(s => s.kind === 'big' && s.x > map.size / 2), 'the King can appear in the east');
check(map.paths.length >= 20, 'trails connect the field (floor 20)');

// Flood fill over the land: everything the player can be sent to must be in the start point's connected field.
const reached = new Set();
const key = (x, y) => y * 100000 + x;
const queue = [[Math.floor(map.spawn.x), Math.floor(map.spawn.y)]];
reached.add(key(...queue[0]));
for (let i = 0; i < queue.length; i++) {
  const [x, y] = queue[i];
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const nx = x + dx, ny = y + dy;
    if (!land(nx, ny) || reached.has(key(nx, ny))) continue;
    reached.add(key(nx, ny)); queue.push([nx, ny]);
  }
}
const connected = (x, y) => reached.has(key(Math.floor(x), Math.floor(y)));
check(connected(map.city.plaza.x, map.city.plaza.y), 'Alderhaven is reachable from the start');
check(connected(map.dock.start.x, map.dock.start.y), 'the landing dock is reachable from the start');
// The Crags crossing: the land cell nearest its gate must be part of the same field.
let nearest = null;
for (let r = 0; r <= 8 && !nearest; r++) for (let dy = -r; dy <= r && !nearest; dy++) for (let dx = -r; dx <= r; dx++) {
  if (Math.max(Math.abs(dx), Math.abs(dy)) === r && land(gate.x + dx, gate.y + dy)) { nearest = { x: gate.x + dx, y: gate.y + dy }; break; }
}
check(nearest && connected(nearest.x, nearest.y), 'the land at the Emberfall Crags gate is reachable');
for (const s of map.slimes.filter(s => s.layout === 'meadow_design_v1')) {
  check(connected(s.x, s.y), `${s.kind} spawn at ${s.x},${s.y} is on the connected land`);
}
// Every 32-tile block that is mostly land is dressed with scenery (no bare fields).
const blocks = new Map();
for (const o of map.objects) { const k = Math.floor(o.y / 32) * 100 + Math.floor(o.x / 32); blocks.set(k, (blocks.get(k) || 0) + 1); }
for (let by = 0; by * 32 < F.length; by++) for (let bx = 0; bx * 32 < (F[0] || []).length; bx++) {
  let cells = 0, on = 0;
  for (let y = by * 32; y < Math.min(F.length, by * 32 + 32); y++) for (let x = bx * 32; x < Math.min(F[y].length, bx * 32 + 32); x++) { cells++; if (F[y][x] === '#') on++; }
  if (on / cells < .5) continue;
  check((blocks.get(by * 100 + bx) || 0) > 0, `scenery reaches the land block ${bx},${by}`);
}
console.log(`${checks} Greenmeadow layout checks passed`);
