// The field's own target pick, skill dispatch and frame counter, run against stubbed monsters and clocks.
// MUTATE=select|move|cap|damage|fps must fail.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
let field = fs.readFileSync(path.join(root, 'client', 'field.js'), 'utf8');
const mutations = {
  select: ['if (dealsDamage(def.effect)) acquireTarget(); ', ''],
  move: ['|| pointer?.down || keyboardDirection().some(Boolean)', ''],
  cap: ['const ACQUIRE_RANGE = 12,', 'const ACQUIRE_RANGE = Infinity,'],
  damage: ["effect === 'dash' ? mult > 0 :", "effect === 'dash' ? true :"],
  fps: ['fpsFrames * 1000 / (now - fpsSince)', 'fpsFrames'],
};
if (process.env.MUTATE) {
  const [before, after] = mutations[process.env.MUTATE];
  assert.ok(field.includes(before), 'mutation target exists');
  field = field.replace(before, after);
}
function slice(start, end) {
  const from = field.indexOf(start), to = field.indexOf(end, from);
  assert.ok(from >= 0 && to > from, start);
  return field.slice(from, to);
}
const skills = JSON.parse(fs.readFileSync(path.join(root, 'world', 'skills.txt'), 'utf8'));
const box = { hidden: true, lastElementChild: { textContent: '–' } };
const sandbox = vm.createContext({ skills, box, document: { getElementById: id => id === 'fps-counter' ? box : null } });
sandbox.window = sandbox;
vm.runInContext(`
  const SKILL_BY_ID = Object.fromEntries(skills.map(s => [s.id, s]));
  const hero = {}, remotePlayers = new Map(), pointer = { down: false }, log = [];
  let slimes = [], marker = null, held = [0, 0], wall = () => false, running = true, paused = false;
  const keyboardDirection = () => held, segmentFree = (a, b) => !wall(b);
  const swing = () => log.push('swing'), castSkill = def => log.push('skill:' + def.id), shadowstep = () => log.push('dash');
  const isAssassin = () => hero.look.class === 'assassin';
  const Online = { connected: true };
  ${slice('  // The living, awake monster closest', '  function shadowstep()')}
  ${slice('  // Settings > Video > Show FPS', '  function loop(now)')}
  window.Field = {
    canAct: true,
    clearInput() { log.push('clear'); },
    targetEnemy(id) { hero.target = slimes.find(s => s.id === id); log.push('target:' + id); return true; },
    ${slice('    useSkill(id) {', '    get canAct()')}
  };
  window.test = {
    hero, remotePlayers, pointer, count: countFrame,
    reset(cls, foes) {
      Object.assign(hero, { x: 0, y: 0, nx: 0, ny: 0, hp: 100, dead: false, level: 99, resource: 999, atkCd: 0, dashCd: 0, dashT: 0, skillCd: {}, target: null, pvpTargetId: null, sparkTravel: null, look: { class: cls } });
      slimes = foes; held = [0, 0]; pointer.down = false; wall = () => false; remotePlayers.clear(); log.length = 0;
    },
    hold(direction) { held = direction; }, wall(test) { wall = test; },
    use(id) { log.length = 0; const used = Field.useSkill(id); return { used, log: [...log] }; },
  };
`, sandbox);
const raw = sandbox.test;
// Results cross the vm boundary as plain data.
const T = Object.assign(Object.create(raw), { use: id => JSON.parse(JSON.stringify(raw.use(id))) });
const foe = (id, x, extra = {}) => ({ id, x, y: 0, nx: x, ny: 0, hp: 10, dead: false, state: 'idle', ...extra });
const crowd = () => [foe(1, 1, { dead: true }), foe(2, 2, { state: 'waiting' }), foe(3, 2.5, { hp: 0 }), foe(4, 9), foe(5, 5)];
const picked = ['clear', 'target:5'];

let damaging = 0, harmless = 0;
for (const skill of skills) {
  T.reset(skill.class, crowd());
  const hurts = !['buff', 'heal', 'mend'].includes(skill.effect.effect) && !(skill.effect.effect === 'dash' && !skill.effect.mult);
  assert.deepEqual(T.use(skill.id).log, [...(hurts ? picked : []), 'skill:' + skill.id], skill.id);
  hurts ? damaging++ : harmless++;
}
assert.ok(damaging >= 30 && harmless >= 10, `both kinds of skill were swept (${damaging}, ${harmless})`);

T.reset('warrior', crowd());
assert.deepEqual(T.use('attack').log, picked, 'a basic attack picks a target and leaves the swing to autoattack');
assert.deepEqual(T.use('attack').log, ['swing'], 'with a target the basic attack swings as before');
T.reset('assassin', crowd());
assert.deepEqual(T.use('shadowstep').log, ['dash'], 'Shadowstep picks nothing');

T.reset('warrior', crowd()); raw.hero.target = foe(4, 9);
assert.deepEqual(T.use('cleave').log, ['skill:cleave'], 'a selected monster is kept');
T.reset('warrior', crowd()); raw.hero.target = foe(7, 1, { dead: true });
assert.deepEqual(T.use('cleave').log, [...picked, 'skill:cleave'], 'a dead selection counts as none');
T.reset('warrior', crowd()); raw.hero.pvpTargetId = 'rival'; T.remotePlayers.set('rival', {});
assert.deepEqual(T.use('cleave').log, ['skill:cleave'], 'a selected player is kept');
T.reset('warrior', crowd()); raw.hero.pvpTargetId = 'gone';
assert.deepEqual(T.use('cleave').log, [...picked, 'skill:cleave'], 'a player who left the zone is no selection');

T.reset('warrior', crowd()); T.hold([1, 0]);
assert.deepEqual(T.use('cleave').log, ['skill:cleave'], 'held movement keeps steering');
assert.deepEqual(T.use('attack').log, ['swing'], 'a basic attack while moving swings as before');
T.reset('warrior', crowd()); T.pointer.down = true;
assert.deepEqual(T.use('cleave').log, ['skill:cleave'], 'a held click-to-walk is left alone');
T.reset('warrior', crowd()); raw.hero.sparkTravel = {};
assert.deepEqual(T.use('cleave').log, ['skill:cleave']);

T.reset('warrior', [foe(6, 12.5)]);
assert.deepEqual(T.use('cleave').log, ['skill:cleave'], 'a monster beyond 12 tiles is ignored');
T.reset('warrior', [foe(6, 12)]);
assert.deepEqual(T.use('cleave').log, ['clear', 'target:6', 'skill:cleave']);
T.reset('warrior', crowd()); T.wall(at => at.x === 5);
assert.deepEqual(T.use('cleave').log, ['clear', 'target:4', 'skill:cleave'], 'a monster behind a wall is passed over');
T.reset('warrior', crowd()); raw.hero.skillCd = { cleave: 2 };
assert.deepEqual(T.use('cleave'), { used: false, log: [] }, 'a skill on cooldown selects nothing');

// Frame counter: off by default, then painted frames per second, twice a second.
sandbox.Prefs = { showFps: false };
T.count(1000); assert.equal(box.hidden, true);
sandbox.Prefs.showFps = true;
for (let t = 2000; t <= 2500; t += 20) T.count(t);
assert.equal(box.hidden, false); assert.equal(box.lastElementChild.textContent, '50');
for (let t = 2540; t <= 3100; t += 40) T.count(t);
assert.equal(box.lastElementChild.textContent, '25');
T.count(9000); T.count(9100);
assert.equal(box.lastElementChild.textContent, '25', 'a long gap starts a new measurement');
sandbox.Prefs.showFps = false; T.count(9200);
assert.equal(box.hidden, true); assert.equal(box.lastElementChild.textContent, '–');
console.log(`skill autotarget and frame counter: ${damaging} damaging and ${harmless} other skills passed`);
