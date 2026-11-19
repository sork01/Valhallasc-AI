// Real route placement and player-style frame/draw selection, without a browser.
// Snapshot clock corrections must never become a one-frame change of heading.
// MUTATE=displacement restores the old update; MUTATE=stopped restores its
// displacement-based moving flag. Both must fail. No art, routes or speeds change.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const world = JSON.parse(read('world/map.txt'));
let city = read('client/city.js');
if (process.env.MUTATE) {
  const changes = {
    displacement: [
      'const p=routePoint(n,time);\n      n.moving=!!(p.fx||p.fy);if(n.moving){n.fx=p.fx;n.fy=p.fy;}',
      'const p=routePoint(n,time),dx=p.x-n.x,dy=p.y-n.y;\n      n.moving=Math.hypot(dx,dy)>1e-4;if(n.moving){n.fx=dx;n.fy=dy;}'
    ],
    stopped: ['n.moving=!!(p.fx||p.fy)', 'n.moving=Math.hypot(p.x-n.x,p.y-n.y)>1e-4']
  };
  const mutation = changes[process.env.MUTATE];
  assert(mutation, 'Known mutation');
  assert(city.includes(mutation[0]), 'Mutation applies to the actual implementation');
  city = city.replace(mutation[0], mutation[1]);
}
const context = {
  WORLD_MAP: world, Field: { zone: 9 }, setInterval() {},
  document: { getElementById: () => ({ querySelectorAll: () => [], addEventListener() {} }) },
  fetch: async url => ({ ok: true, json: async () => JSON.parse(read(`client/${url}`)) }),
  Image: class { complete = true; naturalWidth = 768; },
  matchMedia: () => ({ matches: true })
};
context.window = context;
vm.createContext(context);
vm.runInContext(city, context, { filename: 'city.js' });
vm.runInContext(read('client/npc-art.js'), context, { filename: 'npc-art.js' });
let checks = 0;
function check(value, message) { assert.ok(value, message); checks++; }
function render(n, t) {
  const calls = [];
  const g = Object.fromEntries(['save', 'restore', 'translate', 'rotate', 'scale', 'drawImage'].map(name =>
    [name, (...args) => calls.push([name, ...args])]));
  check(context.NpcArt.draw(g, n, t), `${n.id}: production draw succeeds`);
  return calls;
}
(async () => {
  const { City, NpcArt } = context;
  await NpcArt.ready;
  const folk = City.npcs.filter(n => n.route && NpcArt.manifest.npcs[n.id]?.identity.species === 'merfolk');
  check(folk.length === 18, 'All 18 current Nacrehold swimming routes are exercised');
  for (const n of folk) {
    check(NpcArt.styleOf(n) === 'player', `${n.id}: current player-style art`);
    const authored = world.zones[8].npcs.find(p => p.id === n.id);
    const original = JSON.stringify(authored);
    let start = 100 * n.route.reduce((sum, a, i) => {
      const b = n.route[(i + 1) % n.route.length];
      return sum + n.pause + Math.hypot(b[0] - a[0], b[1] - a[1]) / n.speed;
    }, 0);
    for (let leg = 0; leg < n.route.length; leg++) {
      const a = n.route[leg], b = n.route[(leg + 1) % n.route.length];
      const duration = Math.hypot(b[0] - a[0], b[1] - a[1]) / n.speed;
      const middle = start + n.pause + duration / 2 - n.phase;
      const mirrored = b[0] - a[0] - (b[1] - a[1]) < 0;
      // First placement, forward frames, a snapshot rewinding 12 ms, recovery,
      // repeated clock values, then both sides of an animation-frame boundary.
      const phase = [...n.id].reduce((sum, char) => sum + char.charCodeAt(0), 0);
      const edge = (Math.ceil(middle * 10 + phase) - phase) / 10;
      for (const t of [middle, middle + 1 / 60, middle + .005, middle + .005 + 1 / 60,
        middle + .005 + 1 / 60, edge - 1e-6, edge, edge + 1e-6]) {
        City.update(t);
        const pose = NpcArt.frame(n, t);
        check(pose.clip === 'walk', `${n.id} leg ${leg}: holds the swim clip through clock corrections/repeated times`);
        check(pose.mirrored === mirrored, `${n.id} leg ${leg}: route heading survives clock correction at ${t}`);
        const elapsed = t + n.phase - start - n.pause;
        check(Math.abs(n.x - (a[0] + (b[0] - a[0]) * elapsed / duration)) < 1e-10 &&
          Math.abs(n.y - (a[1] + (b[1] - a[1]) * elapsed / duration)) < 1e-10,
        `${n.id}: authored position/speed/phase unchanged`);
        // Verify the production draw consumes that direction for both mirror and
        // lean, rather than just checking a field which the drawing could ignore.
        const calls = render(n, t);
        check(calls.some(([name, angle]) => name === 'rotate' && angle === (mirrored ? -.5 : .5)), `${n.id}: swim lean agrees with heading`);
        check(calls.some(([name, x]) => name === 'scale' && x === -1) === mirrored, `${n.id}: drawn mirror agrees with heading`);
        const draw = calls.find(([name]) => name === 'drawImage');
        const m = NpcArt.fresh;
        const step = Math.floor(t * m.clips.walk.fps + phase) % m.clips.walk.n;
        check(draw[2] === step * m.frame[0] && draw[3] === m.frame[1], `${n.id}: current walk frame selected across animation boundary`);
      }
      // Walk up to an actual waypoint, then pause there without a spurious
      // one-frame walk caused by catching up to its coordinates.
      const arrival = start + n.pause + duration - n.phase;
      City.update(arrival - .001);
      City.update(arrival + .001);
      check(!n.moving && NpcArt.frame(n, arrival + .001).clip === 'idle', `${n.id}: waypoint pause begins immediately`);
      check(n.x === b[0] && n.y === b[1], `${n.id}: pause stays at authored waypoint`);
      City.update(arrival + .5);
      check(!n.moving, `${n.id}: authored pause is preserved`);
      start += n.pause + duration;
    }
    check(JSON.stringify(authored) === original, `${n.id}: authored route data untouched`);
  }
  console.log(`merfolk-facing: ${checks} checks passed (18 routes, 72 legs; clock rewind, repeated timestamps, animation boundaries, pauses and draw transforms)`);
})().catch(error => { console.error(error); process.exitCode = 1; });
