// world/map.txt is the source of truth for collision geometry and spawn points.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/world.js'), "'use strict';\nwindow.WORLD_MAP = " + JSON.stringify(map) + ';\n');
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/items.js'), "'use strict';\nwindow.WORLD_ITEMS = " + JSON.stringify(items) + ';\n');
const skills = JSON.parse(fs.readFileSync(path.join(root, 'world/skills.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/skills.js'), "'use strict';\nwindow.WORLD_SKILLS = " + JSON.stringify(skills) + ';\n');
const passives = JSON.parse(fs.readFileSync(path.join(root, 'world/passives.txt'), 'utf8'));
fs.writeFileSync(path.join(root, 'client/passives.js'), "'use strict';\nwindow.WORLD_PASSIVES = " + JSON.stringify(passives) + ';\n');
const zones = map.zones || [];
console.log(`Synced ${map.objects.length} obstacles and ${map.slimes.length} spawns` + zones.map(z => `, plus zone "${z.name}": ${z.objects.length} obstacles and ${z.slimes.length} spawns`).join('') + '. Rebuild Rust after changing the map.');

const cathedral = [
  ...JSON.parse(fs.readFileSync(path.join(root, "world/cathedral.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/eye_below.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/elder_hollow.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/thousandfold.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/rain_crown.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/seed_vault.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/sunken_astrolabe.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/blooming_labyrinth.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/solar_crucible.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/amber_archive.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/silent_solstice.txt"), "utf8")),
  ...JSON.parse(fs.readFileSync(path.join(root, "world/thunderheart_gate.txt"), "utf8"))
];
fs.writeFileSync(path.join(root, "client/cathedral.js"), "'use strict';\nwindow.CATHEDRAL_ENEMIES = " + JSON.stringify(cathedral) + ";\n");
