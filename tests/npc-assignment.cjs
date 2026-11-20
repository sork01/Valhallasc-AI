const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root, p)));
const world = read('world/map.txt'), old = read('client/assets/npc.txt'), fresh = read('client/assets/npcp.txt');
const plan = read('docs/npc-named-plan.txt');
const baseline = JSON.parse(execFileSync('git', ['show', 'c0b93e8e:client/assets/npc.txt'], { cwd: root }));
const people = [world, ...world.zones].flatMap(z => z.npcs || []).filter(n => !['stone','scenery','mailbox','spirit_guide'].includes(n.art) && !/meeting stone/i.test(n.name));
const fishers=people.filter(n=>n.id.startsWith('fisher_'));
// Four new Transmog Masters reuse the local smiths' existing player-style sprites.
assert.equal(people.length-fishers.length, 592);
assert.equal(people.filter(n=>n.id.endsWith('_transmog')).length,4);
assert.equal(fishers.length,13);
for(const n of fishers)assert.equal(old.npcs[n.id].art,'fisher_rod');
assert.deepEqual(Object.keys(old.npcs).sort(), people.map(n => n.id).sort(), 'Every actual person, and no scenery, is assigned');
for (const [key, value] of Object.entries(baseline)) if (key !== 'npcs') assert.deepEqual(old[key], value, key);
for (const [id, who] of Object.entries(baseline.npcs)) assert.deepEqual(old.npcs[id], who, `Original identity ${id}`);
assert.equal(Object.keys(fresh.sprites).length, 319);
for (const n of people) {
  const who = old.npcs[n.id];
  assert(who && fresh.sprites[who.art] && fresh.designs[who.art], `${n.id}: player-style source`);
  assert(fs.existsSync(path.join(root, `client/assets/npcp_${who.art}.png`)));
}
for (const p of plan.people) {
  const who = old.npcs[p.id], spec = fresh.designs[who.art];
  if (p.classification === 'named') assert.equal(who.art, p.designKey);
  else assert(who.art.startsWith('reuse_') && spec.general && spec.amounts, p.id);
  if (p.requiredSpecies) assert.equal(spec.species, p.requiredSpecies, p.id);
  if (p.identity.species === 'merfolk') assert.equal(spec.species, 'merfolk', p.id);
}
for (const [alias, source] of Object.entries({ reuse_treefolk_merchant:'named_hw_sorter', reuse_treefolk_courier:'named_hw_courier', reuse_treefolk_sentinel:'named_hw_captain', reuse_treefolk_steward:'named_hw_storyteller' })) {
  assert.equal(fresh.sprites[alias], fresh.sprites[source]);
  assert.deepEqual(fs.readFileSync(path.join(root,`client/assets/npcp_${alias}.png`)), fs.readFileSync(path.join(root,`client/assets/npcp_${source}.png`)));
}
console.log(`NPC assignments: ${people.length}/${people.length} people covered, including ${fishers.length} Fishers; original identities preserved`);
