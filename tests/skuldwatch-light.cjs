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
const sk = wyrdwood.camps.find(c => c.name === 'Skuldwatch');
assert.deepEqual({x:beacon.x, y:beacon.y}, sk.plaza);
const cutRadii = [], glowWidths = [], specks = [], gradients = [], glowCentres = [];
const drawing = {
  createRadialGradient(...args) { gradients.push(args); return { addColorStop() {} }; },
  clearRect() {}, beginPath() {}, fill() {}, save() {}, restore() {}, moveTo() {}, quadraticCurveTo() {}, closePath() {},
  fillRect(x, y, width, height) { if (width <= 2 && height <= 2) specks.push([x, y]); },
  arc(x, y, radius) { cutRadii.push(radius); },
  drawImage(sprite, x, y, width, height) {
    if (this.globalCompositeOperation === 'lighter') {
      glowWidths.push(width ?? sprite.width);
      glowCentres.push([x+width/2, y+height/2]);
    }
  },
};
const City = { art: {} };
const sandbox = vm.createContext({
  City, window: { City },
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
vm.runInContext(fs.readFileSync(path.join(client, 'wyrdart.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(client, 'daynight.js'), 'utf8'), sandbox);

const ground = [500, 450];
City.art.beacon.animate(drawing, beacon, ...ground, 1);
const flame = gradients[0].slice(0, 2);
specks.length = 0;

const lights = sandbox.window.testLights();
assert.deepEqual(Array.from(lights, light => light.kind), ['beacon', 'lamp'],
  'the fort beacon lights the plaza and unlit quest beacons stay dark');

const { DayNight } = sandbox.window;
DayNight.setZone(wyrdwood);
DayNight.sync({ hour: 0, hoursPerSecond: 0 });
DayNight.tick(1.2);
DayNight.draw(drawing, 1200, 900, lights, () => ground);
assert.equal(specks.length, 0, 'Wyrdwood night lighting draws no fixed dots over the field');
assert.deepEqual(cutRadii, [160, 60], 'the great beacon cuts a wider pool in the half-scale night veil');
assert.deepEqual(glowWidths, [480, 128], 'the beacon casts a wider glow than a lamp');
assert.deepEqual(glowCentres[0], flame, 'the night glow starts at the flame');
const plazaLight = gradients.find(gradient => gradient[5] === 160).slice(0, 2);
assert.deepEqual(plazaLight.map(v => v*2), flame, 'the plaza light is centered on the flame');

DayNight.setZone(zones.find(zone => zone.name === 'Skaldholm'));
DayNight.draw(drawing, 1200, 900, [], () => [500, 450]);
assert.equal(specks.length, 0, 'Skaldholm night lighting draws no fixed dots over the city');

DayNight.setZone(wyrdwood);
DayNight.sync({ hour: 12, hoursPerSecond: 0 });
DayNight.draw(drawing, 1200, 900, lights, () => [500, 450]);
assert.equal(glowWidths.length, 2, 'the added night glow fades out by midday');
console.log('Skuldwatch beacon lighting and the night-sky overlay passed.');
