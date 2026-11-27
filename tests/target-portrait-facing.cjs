'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const file = process.argv[2] || path.join(__dirname, '../client/field.js');
const source = fs.readFileSync(file, 'utf8');
const sandbox = {
  window: {},
  document: { addEventListener() {} },
  addEventListener() {},
  WORLD_MAP: {}, WORLD_SKILLS: [], CATHEDRAL_ENEMIES: [],
  MageSprite: { direction: (fx, fy) => fx === fy ? fx < 0 ? 4 : 0 : 2 },
};
vm.runInNewContext(source.replace('  window.Field = Field;', `
  window.Field = Field;
  window.setPortraitActor = actor => remotePlayers.set(actor.id, actor);
`), sandbox, { filename: file });

const { Field, setPortraitActor } = sandbox.window;
const frontFrame = {}, calls = [];
const context = { clearRect() {}, drawImage: (...args) => calls.push(args) };
const canvas = { getContext: () => context };

for (const actor of [
  { id: 'player', fx: -1, fy: -1 },
  { id: 'adventurer', fx: 1, fy: -1, ambient: true, assisted: true },
]) {
  const crop = [54, 19, 50, 50];
  const sprite = {
    meta: { portrait: crop },
    frame(clip, direction, index) {
      assert.deepEqual([clip, direction, index], ['idle', 0, 0], `${actor.id} portrait faces the camera`);
      return frontFrame;
    },
  };
  setPortraitActor({ ...actor, sprite });
  assert(Field.drawTargetPortrait({ id: actor.id, player: true }, canvas));
  assert.deepEqual(calls.pop(), [frontFrame, ...crop, 0, 0, 96, 96]);
}

console.log('Player and assisted adventurer target portraits use the front-facing idle frame.');
