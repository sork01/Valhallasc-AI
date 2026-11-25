'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const client = process.argv[2] || path.join(__dirname, '../client');
const { zones } = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'), 'utf8'));
const wyrdwood = zones.find(zone => zone.name === 'Wyrdwood');
const beacon = wyrdwood.objects.find(object => object.kind === 'beacon' && object.great);
const lamp = wyrdwood.objects.find(object => object.kind === 'lamp');
const cutRadii = [], glowWidths = [];
const drawing = {
  createRadialGradient: () => ({ addColorStop() {} }),
  clearRect() {}, fillRect() {}, beginPath() {}, fill() {}, save() {}, restore() {},
  arc(x, y, radius) { cutRadii.push(radius); },
  drawImage(sprite, x, y, width) {
    if (this.globalCompositeOperation === 'lighter') glowWidths.push(width ?? sprite.width);
  },
};
const sandbox = vm.createContext({
  window: {},
  document: { addEventListener() {}, createElement: () => ({ getContext: () => drawing }) },
  addEventListener() {},
  performance: { now: () => 0 },
  WORLD_MAP: { zones: [{ theme: 'wyrd', size: 1, paths: [], objects: [beacon, lamp, { ...beacon, great: false }] }] },
  WORLD_SKILLS: [], CATHEDRAL_ENEMIES: [],
  SeasonDungeonArt: { isTheme: () => false }, CathedralArt: { isTheme: () => false },
});

const source = fs.readFileSync(path.join(client, 'field.js'), 'utf8');
vm.runInContext(source.replace('  window.Field = Field;', `
  window.Field = Field;
  window.testLights = () => {
    zdef = ZONES[1];
    buildMap();
    return nightLights;
  };
`), sandbox);
vm.runInContext(fs.readFileSync(path.join(client, 'daynight.js'), 'utf8'), sandbox);

const lights = sandbox.window.testLights();
assert.deepEqual(Array.from(lights, light => light.kind), ['beacon', 'lamp'],
  'the fort beacon lights the plaza and unlit quest beacons stay dark');

const { DayNight } = sandbox.window;
DayNight.setZone(wyrdwood);
DayNight.sync({ hour: 0, hoursPerSecond: 0 });
DayNight.tick(1.2);
DayNight.draw(drawing, 1200, 900, lights, () => [500, 450]);
assert.deepEqual(cutRadii, [160, 60], 'the great beacon cuts a wider pool in the half-scale night veil');
assert.deepEqual(glowWidths, [480, 128], 'the beacon casts a wider glow than a lamp');

DayNight.sync({ hour: 12, hoursPerSecond: 0 });
DayNight.draw(drawing, 1200, 900, lights, () => [500, 450]);
assert.equal(glowWidths.length, 2, 'the added night glow fades out by midday');
console.log('Skuldwatch’s beacon lights a wider area at night.');
