// world/map.txt is the source of truth for collision geometry and spawn points.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/world.js'), "'use strict';\nwindow.WORLD_MAP = " + JSON.stringify(map) + ';\n');
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/items.js'), "'use strict';\nwindow.WORLD_ITEMS = " + JSON.stringify(items) + ';\n');
const zones = map.zones || [];
console.log(`Synced ${map.objects.length} obstacles and ${map.slimes.length} spawns` + zones.map(z => `, plus zone "${z.name}": ${z.objects.length} obstacles and ${z.slimes.length} spawns`).join('') + '. Rebuild Rust after changing the map.');
