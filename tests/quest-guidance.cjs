const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: {} };
for (const file of ['quest-guidance.js', 'quest-sources.js']) vm.runInNewContext(fs.readFileSync(`client/${file}`, 'utf8'), context);
const world = JSON.parse(fs.readFileSync('world/map.txt', 'utf8'));
const areas = [world, ...world.zones];
const guidance = context.window.QuestGuidance.create(areas, context.window.QUEST_SOURCES);
const fish = new Map(JSON.parse(fs.readFileSync('world/fish.txt', 'utf8')).map(f => [f.item, f]));
let objectives = 0, candidates = 0, anglers = 0;
for (const [zone, area] of areas.entries()) for (const definition of area.quests || []) {
  const q = { ...definition, zone };
  for (const o of q.objectives) {
    const points = guidance.pool(q, o);
    assert.ok(points.length, `${q.id}: unresolved ${o.kind} ${o.target}`);
    for (const p of points) {
      assert.ok(areas[p.zone] && Number.isFinite(p.x) && Number.isFinite(p.y), `${q.id}: invalid target`);
      if (p.enemy) assert.ok(areas[p.zone].slimes.some(s => s.kind === p.enemy && !s.ambush && s.x === p.x && s.y === p.y), `${q.id}: stale spawn`);
      if (p.npc) assert.ok(areas[p.zone].npcs.some(n => n.id === p.npc && n.x === p.x && n.y === p.y), `${q.id}: stale NPC`);
      if (p.place) assert.ok(areas[p.zone].places.some(n => n.id === p.place && n.x === p.x && n.y === p.y), `${q.id}: stale place`);
      if (p.fishing) {
        // The shore the angler stands on, in water this species lives in (the server's catch rule, read from the catalogue).
        const spot = areas[p.zone].fishingSpots.find(s => s.id === p.fishing), species = fish.get(o.target);
        assert.ok(spot && spot.shore.x === p.x && spot.shore.y === p.y, `${q.id}: stale casting spot`);
        assert.ok(species && spot.habitat === species.habitat && [null, p.zone].includes(species.zone), `${q.id}: ${o.target} does not live at ${p.fishing}`);
        anglers++;
      }
      candidates++;
    }
    objectives++;
  }
}
for (const [zone, area] of areas.entries()) {
  const reachable = new Set([zone]), queue = [zone];
  for (let i = 0; i < queue.length; i++) for (const p of areas[queue[i]].portals || []) {
    if (areas[p.to] && !areas[p.to].sealedTemplate && !p.after_clear && !reachable.has(p.to)) { reachable.add(p.to); queue.push(p.to); }
  }
  for (const q of area.quests || []) for (const o of q.objectives) {
    assert.ok(guidance.pool({ ...q, zone }, o).some(p => reachable.has(p.zone)), `${q.id}: no usable route to ${o.target}`);
  }
}
const q = (id) => areas.flatMap((a, zone) => (a.quests || []).filter(q => q.id === id).map(q => ({ ...q, zone })))[0];
// Fisher errands stay at the Fisher's own water; a fish the quest's zone lacks leads to every shore that has it.
assert.ok(anglers > 1000, `only ${anglers} casting spots were offered`);
let local = 0;
for (const [zone, area] of areas.entries()) for (const quest of area.quests || []) if (quest.id.startsWith('fisher_')) for (const o of quest.objectives) if (fish.has(o.target)) {
  const points = guidance.pool({ ...quest, zone }, o);
  assert.ok(points.every(p => p.fishing && p.zone === zone), `${quest.id}: guidance leaves the Fisher's waters`); local++;
}
assert.ok(local >= 80, `only ${local} Fisher objectives`);
const seahorse = q('deep_seahorse');
for (const o of seahorse.objectives) assert.deepEqual([...new Set(guidance.pool(seahorse, o).map(p => p.zone))].sort((a, b) => a - b), [0, 19], 'the seahorse fish are caught on the two sea coasts');
const hunt = q('slime_patrol'), target = hunt.objectives.find(o => o.kind === 'kill');
const pool = guidance.pool(hunt, target), a = pool[0], b = pool.at(-1);
assert.equal(guidance.nearest(pool, a.zone, a.x, a.y).x, a.x);
assert.equal(guidance.nearest(pool, b.zone, b.x, b.y).y, b.y);
assert.ok(pool.every(p => p.zone === hunt.zone), 'ordinary hunts stay in their province');
const scene = q('es_14'), first = guidance.groups(scene, scene.objectives.map(() => 0));
assert.ok(first.every(g => g.objective === 0 || !['memory', 'echo'].includes(scene.objectives[g.objective].kind)), 'later story scenes stay gated');
const escort = q('apple_mill'), objective = escort.objectives.find(o => o.kind === 'escort');
const started = guidance.groups(escort, escort.objectives.map(() => 0), { escorts: [{ npc: objective.target }] });
const destination = started.find(g => escort.objectives[g.objective].kind === 'escort').candidates[0];
const npc = areas[escort.zone].npcs.find(n => n.id === objective.target);
assert.deepEqual([destination.x, destination.y], npc.escort.route.at(-1), 'started escort guides to safety');
const talk = q('welcome'), talkObjective = talk.objectives.find(o => o.kind === 'talk');
const moving = guidance.nearest(guidance.pool(talk, talkObjective), talk.zone, 0, 0, { npc: () => ({ x: 123, y: 456 }) });
assert.equal(moving.x, 123, 'guidance follows the live walker');
for (const id of ['crags_onward', 'rime_onward', 'stormglass_onward']) {
  const reach = q(id), o = reach.objectives.find(o => o.kind === 'reach');
  assert.ok(guidance.pool(reach, o).every(p => areas[p.zone].name === o.target), 'reach targets use untranslated world names');
}
console.log(`quest-guidance: ${objectives} objectives audited against ${candidates} real candidates; nearest targets, live NPCs, ordered scenes and escort destinations pass`);
