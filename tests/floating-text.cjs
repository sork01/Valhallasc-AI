const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const field = fs.readFileSync('client/field.js', 'utf8');
let code = field.slice(field.indexOf('  function floater('), field.indexOf('  let currentHitKind = null;'));
if (process.env.MUTATE) code = code.replace("window.Prefs?.floatingText?.[category] === false", 'false');
const emitted = [];
const sandbox = { window: { Prefs: { floatingText: {} } }, numberAnchorVisible: () => true,
  DamageNumbers: { spawn: (_all, spec) => emitted.push(spec) }, floaters: [], headAt: () => 80, currentHitKind: null };
vm.createContext(sandbox); vm.runInContext(code, sandbox);
const kinds = { hit: 'damage', crit: 'damage', hurt: 'incoming', heal: 'healing', miss: 'misses', pickup: 'loot', xp: 'xp', level: 'levels', banner: 'notices' };
for (const [kind, category] of Object.entries(kinds)) {
  emitted.length = 0; sandbox.window.Prefs.floatingText = { [category]: false };
  sandbox.floater(10, 20, 'Test', '#fff', false, kind);
  assert.equal(emitted.length, 0, `disabled ${category} hides ${kind}`);
  sandbox.window.Prefs.floatingText = {};
  sandbox.floater(10, 20, 'Test', '#fff', false, kind);
  assert.equal(emitted.length, 1, `default ${category} shows ${kind}`);
}
for (const category of ['professions', 'combat', 'skills']) {
  emitted.length = 0; sandbox.window.Prefs.floatingText = { [category]: false };
  sandbox.floater(10, 20, 'Test', '#fff', false, 'banner', 118, category);
  assert.equal(emitted.length, 0, `explicit ${category} is filtered`);
  sandbox.floater(10, 20, 'Test', '#fff', false, 'pickup');
  assert.equal(emitted.length, 1, 'other categories remain visible');
}
const syslog = fs.readFileSync('client/syslog.js', 'utf8');
const gains = [], notices = [];
const skills = { fishing: 30 };
const gainSandbox = { skills, professions: { fishing: 'Fishing' }, Number,
  add: (...args) => notices.push(args), window: { Field: { floatHero: (...args) => gains.push(args) } } };
vm.createContext(gainSandbox);
vm.runInContext(syslog.slice(syslog.indexOf('  function skillGain('), syslog.indexOf('  function mailCount(')), gainSandbox);
gainSandbox.skillGain('fishing', 31); gainSandbox.skillGain('fishing', 31);
assert.equal(gains.length, 1, 'a skill increase floats exactly once');
assert.equal(gains[0][2], 'professions'); assert.equal(notices.length, 1, 'log is independent of filtering');
gainSandbox.skills = null; gainSandbox.skillGain('fishing', 40); assert.equal(gains.length, 1, 'no gain on initial baseline');
const combatCode = field.slice(field.indexOf('    if (!initial && !moved && previousCombat'), field.indexOf('    hero.raidSupport ='));
for (const [initial, moved, previousCombat, next, expected] of [[true,false, false,true,0],[false,true,false,true,0],[false,false,undefined,true,0],[false,false,false,true,1],[false,false,true,false,1],[false,false,true,true,0]]) {
  const events = [];
  vm.runInNewContext(combatCode, { initial, moved, previousCombat, own: { inCombat: next }, hero: { x: 10, y: 20 }, floater: (...a) => events.push(a) });
  assert.equal(events.length, expected, 'combat notices require an actual change in the current zone');
  if (expected) { assert.equal(events[0][2], next ? '+Combat' : '-Combat'); assert.equal(events[0][7], 'combat'); }
}
console.log('Floating text: eleven categories, independent filtering, profession deduplication and combat transitions passed');
