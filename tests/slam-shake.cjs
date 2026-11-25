'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const sourcePath = process.argv[2] || path.join(__dirname, '../client/field.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const sandbox = {
  window: {},
  document: { addEventListener() {} },
  addEventListener() {},
  WORLD_MAP: {},
  WORLD_SKILLS: [],
  CATHEDRAL_ENEMIES: [],
  Online: { id: 'player' },
  matchMedia: () => ({ matches: false }),
};

// Use the live event handler with a fresh camera and particle state for each impact.
vm.runInNewContext(source.replace('  window.Field = Field;', `
  window.Field = Field;
  window.slamTest = function (x, y, radius) {
    hero = { x: 100, y: 200 };
    effects = [];
    parts = [];
    shakeT = shakeMag = 0;
    Field._debug.event({ kind: 'slam', actor: '', x, y, value: radius });
    return { duration: shakeT, magnitude: shakeMag, ringRadius: effects[0]?.r, particles: parts.length };
  };
`), sandbox, { filename: sourcePath });

const { slamTest } = sandbox.window;
const near = slamTest(102, 201, 3.6);
assert.equal(near.duration, .45, 'a nearby slam shakes for the usual duration');
assert.equal(near.magnitude, 9);

const edge = slamTest(130, 240, 4.5);
assert.equal(edge.duration, .45, 'a slam exactly 50 tiles away still shakes the camera');
assert.equal(edge.magnitude, 14);

const far = slamTest(130, 240.1, 3.6);
assert.equal(far.duration, 0, 'a slam beyond the 50-tile radius does not shake the camera');
assert.equal(far.ringRadius, 3.6);
assert.ok(far.particles > 0);

sandbox.matchMedia = () => ({ matches: true });
assert.equal(slamTest(102, 201, 3.6).duration, 0, 'reduced motion still suppresses nearby shake');

console.log('Slam shake respects the 50-tile radius and reduced motion.');
