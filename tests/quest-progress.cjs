// Lifecycle regression using the shipped update method and tracker comparator.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let source = fs.readFileSync('client/quests.js', 'utf8');
if (process.env.MUTATE === 'recent') source = source.replace('(recentProgress.get(b.id) || 0) - (recentProgress.get(a.id) || 0)', '0');
if (process.env.MUTATE === 'notice') source = source.replace("window.Announce?.show(`${label} ${count}/${o.count}${unit(o)} (Quest)`, 'quest-progress');", '');
const definitions = [
  { id: 'low', zone: 0, level: 1, title: 'Low', objectives: [{ kind: 'kill', label: 'Slimes', count: 5 }] },
  { id: 'gel', zone: 0, level: 8, title: 'Gel', objectives: [{ kind: 'bring', target: 'quest_gel', label: 'Bring slime gel', count: 3 }] },
  { id: 'span', zone: 7, level: 30, title: 'Span', objectives: [{ kind: 'kill', label: 'Keeper', count: 1 }] },
  { id: 'sky', zone: 7, level: 31, title: 'Sky', objectives: [{ kind: 'kill', label: 'Wolves', count: 5 }] },
  { id: 'deep', zone: 8, level: 35, title: 'Deep', objectives: [{ kind: 'kill', label: 'Draugr', count: 5 }] },
];
const rows = definitions.map(q => ({ id: q.id, counts: [0], claimed: false, completions: 0 }));
const notices = [], orders = [];
const context = {
  definitions, byId: new Map(definitions.map(q => [q.id, q])),
  trackerZones: new Map(definitions.map(q => [q.id, q.id === 'span' ? 42 : q.zone])),
  questItems: new Map([['quest_gel', { name: 'Gel (Quest Title)', questMaterial: 'slime_gel' }], ['slime_gel', { name: 'Slime Gel' }]]),
  recentProgress: new Map(), progressOrder: 0, initialized: false, progress: [], abandoned: [],
  Field: { zone: 0 }, signature: '', tracked: null, abandonConfirm: null, groupKey: '',
  clearGuidance() {}, status(q) { return context.progress.some(p => p.id === q.id && !p.claimed) ? 'active' : 'completed'; },
  window: { Announce: { show: (...args) => notices.push(args) } }, unit: () => '',
  orders,
};
context.window.Field = context.Field;
vm.createContext(context);
const sort = source.slice(source.indexOf('    const active = definitions.filter', source.indexOf('  function render()')), source.indexOf("    const tracker = $('quest-tracker');"));
vm.runInContext(`function render() { ${sort}; orders.push(active.map(q => q.id)); }`, context);
const update = source.slice(source.indexOf('    update(next, dismissed = abandoned) {'), source.indexOf('    // What an NPC', source.indexOf('    update(next, dismissed = abandoned) {')));
vm.runInContext(`var api = { ${update} };`, context);
const send = data => context.api.update(structuredClone(data));
const count = (id, n) => { rows.find(p => p.id === id).counts[0] = n; send(rows); };
const lastOrder = () => Array.from(orders.at(-1));
send(rows);
assert.equal(notices.length, 0, 'login is quiet');
count('gel', 1);
assert.equal(lastOrder()[0], 'gel', 'updated higher-level quest moves above lower-level quests');
assert.deepEqual(notices.at(-1), ['Slime Gel 1/3 (Quest)', 'quest-progress'], 'collection notice uses the material name, without the quest-item suffix');
const size = notices.length; send(rows);
assert.equal(notices.length, size, 'unchanged snapshots do not repeat progress');
context.Field.zone = 7; send(rows);
assert.deepEqual(lastOrder().slice(0, 2), ['sky', 'span'], 'current province, its dungeon, then other regions');
count('deep', 1);
assert.deepEqual(lastOrder().slice(0, 2), ['sky', 'span'], 'remote progress keeps current-zone groups first');
context.Field.zone = 0; send(rows); count('low', 1);
assert.equal(lastOrder()[0], 'low', 'most recent progress takes priority within the zone');
count('gel', 3);
assert.equal(lastOrder()[0], 'gel', 'finishing an objective still promotes its quest');
assert.ok(notices.some(n => n[0] === 'Slime Gel 3/3 (Quest)'), 'final count is shown');
const full = notices.length; count('gel', 5);
assert.equal(notices.length, full, 'excess materials do not repeat completed objectives');
count('gel', 2);
assert.equal(notices.length, full, 'losing materials does not announce a gain');
rows.find(p => p.id === 'gel').claimed = true; send(rows);
assert.ok(!lastOrder().includes('gel'), 'claimed quests leave the tracker');
rows.find(p => p.id === 'gel').claimed = false; rows.find(p => p.id === 'gel').counts = [0]; send(rows);
assert.equal(notices.length, full, 'repeatable acceptance is quiet');
count('gel', 1);
assert.equal(notices.at(-1)[0], 'Slime Gel 1/3 (Quest)', 'a new repeatable run can show progress again');
const newRun = notices.length;
rows.find(p => p.id === 'gel').completions++; rows.find(p => p.id === 'gel').counts = [0]; send(rows);
assert.equal(notices.length, newRun, 'a repeatable run reset is quiet even if the claimed snapshot was skipped');
assert.ok(!context.recentProgress.has('gel'), 'a fresh run does not inherit old recency');
const beforeAccept = notices.length;
context.api.update([...structuredClone(rows), { id: 'unknown', counts: [1] }]);
assert.equal(notices.length, beforeAccept, 'unknown definitions are harmless');
console.log('PASS quest-progress: zone groups, recency, collection names, completion, duplicates and repeatable lifecycle');

// Classify actual external-giver quests from authored objective sources.
if (process.env.MUTATE === 'dungeon') source = source.replace('areas[destination]?.copies ? destination : q.zone', 'q.zone');
const world = JSON.parse(fs.readFileSync('world/map.txt', 'utf8'));
const areas = [world, ...world.zones];
const catalog = areas.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
const grouping = { window: {}, areas, definitions: catalog };
vm.createContext(grouping);
for (const file of ['quest-guidance.js', 'quest-sources.js']) vm.runInContext(fs.readFileSync(`client/${file}`, 'utf8'), grouping);
grouping.QuestGuidance = grouping.window.QuestGuidance;
vm.runInContext(source.slice(source.indexOf('  const guidance ='), source.indexOf("  let groupKey =")) + '\nthis.result = trackerZones;', grouping);
for (const id of ['span_entry', 'span_toll', 'span_spectrum']) assert.equal(grouping.result.get(id), 42, `${id} belongs to The Shattered Span despite its Bifrost giver`);
assert.equal(grouping.result.get('sky_hounds'), 7, 'ordinary Bifrost hunt stays in Bifrost');
assert.equal(grouping.result.get('deep_draugr'), 8, "ordinary Rán's Deep hunt stays in its province");

const locale = { window: { WORLD_ITEMS: [{ name: 'Slime Gel' }] }, localStorage: { getItem: () => '{"lang":"sv"}' }, navigator: { language: 'sv' },
  document: { documentElement: {}, body: { nodeType: 0 } }, Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 },
  MutationObserver: class { observe() {} },
};
vm.createContext(locale);
for (const file of ['sv-data.js', 'locale.js']) vm.runInContext(fs.readFileSync(`client/${file}`, 'utf8'), locale);
assert.equal(locale.window.Locale.translate(`${locale.window.WORLD_ITEMS[0].name} 1/3 (Quest)`), 'Slemgelé 1/3 (Uppdrag)', 'progress uses the localized catalog material and Swedish Quest suffix');
console.log('PASS quest-progress: authored dungeon categories and Swedish text');
