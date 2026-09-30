// world/map.txt is the source of truth for collision geometry and spawn points.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/world.js'), "'use strict';\nwindow.WORLD_MAP = " + JSON.stringify(map) + ';\n');
console.log(`Synced ${map.objects.length} obstacles and ${map.slimes.length} spawns. Rebuild Rust after changing the map.`);
