// Higher-level test helpers behind the MCP tools: catalog lookups, target resolution, real walking, NPC talk, skill casts,
// and bulk setup. Everything that changes game state goes through the server's real rules, either as an ordinary player
// action or as a `debug` shortcut (see driver.cjs), never by editing the database.
const fs = require('node:fs');
const path = require('node:path');
const { z } = require('zod');
const { root, debugSchema, socialSchema } = require('./driver.cjs');
const { route } = require('./route.cjs');

const read = file => JSON.parse(fs.readFileSync(path.join(root, 'world', file), 'utf8'));
const map = read('map.txt'), items = read('items.txt'), skills = read('skills.txt');
// Zone 0 is the top-level map (Greenmeadow + Alderhaven); the rest come from `zones`.
const zones = [map, ...(map.zones || [])];
const quests = zones.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
const DEFAULT_LEVELS = { green: 2, blue: 3, pink: 3, yellow: 4, beetle: 5, big: 6, wisp: 5, spider: 7, wraith: 8, golem: 10, crab: 10, wolf: 12, yeti: 13, wyrm: 15, toad: 15, croc: 17, knight: 18, hydra: 20 };
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const number = z.number().finite();
const botName = z.string().regex(/^[a-zA-Z][a-zA-Z0-9_-]{0,15}$/);

// Where a bot should stand. Positions are resolved here and the server still applies its own collision.
const targetSchema = z.union([
  z.object({ zone: z.number().int().min(0).optional(), x: number, y: number }).strict().describe('exact coordinates; zone defaults to the bot\'s zone'),
  z.object({ npc: z.string() }).strict().describe('beside an NPC, in talking range'),
  z.object({ portal: z.string() }).strict().describe('a few units before a portal gate, not inside it'),
  z.object({ enemy: z.number().int().min(0) }).strict().describe('a few units from a living enemy (by id)'),
  z.object({ spawn: z.number().int().min(0) }).strict().describe('a zone\'s spawn point'),
  z.object({ bot: botName }).strict().describe('beside another connected bot'),
]);

function areaOf(zone) {
  const area = zones[zone];
  if (!area) throw Error(`Unknown zone ${zone}; zones are 0-${zones.length - 1}.`);
  return area;
}
function livingEnemy(world, id) {
  const enemy = world.snapshot?.slimes.find(s => s.id === id);
  if (!enemy) throw Error(`No enemy ${id}.`);
  return enemy;
}
function resolve(world, bot, target) {
  const here = world.player(bot);
  if (!here) throw Error(`Bot ${bot} has no player yet.`);
  if ('npc' in target) {
    const found = zones.map((area, zone) => ({ zone, npc: (area.npcs || []).find(n => n.id === target.npc) })).find(f => f.npc);
    if (!found) throw Error(`Unknown NPC ${target.npc}.`);
    return { zone: found.zone, x: found.npc.x, y: found.npc.y + 1.2 };
  }
  if ('portal' in target) {
    for (const [zone, area] of zones.entries()) {
      const portal = (area.portals || []).find(p => p.id === target.portal);
      if (!portal) continue;
      // Step back from the gate toward the middle of the map, so the bot does not trigger it.
      const centre = { x: area.size / 2, y: area.size / 2 }, length = dist(portal, centre) || 1, back = portal.r + 1.5;
      return { zone, x: portal.x + (centre.x - portal.x) / length * back, y: portal.y + (centre.y - portal.y) / length * back };
    }
    throw Error(`Unknown portal ${target.portal}.`);
  }
  if ('enemy' in target) {
    const enemy = livingEnemy(world, target.enemy);
    return { zone: enemy.zone || 0, x: enemy.x + 3, y: enemy.y };
  }
  if ('spawn' in target) return { zone: target.spawn, ...areaOf(target.spawn).spawn };
  if ('bot' in target) {
    const other = world.player(target.bot);
    if (!other) throw Error(`Bot ${target.bot} is not in the world.`);
    return { zone: other.zone || 0, x: other.x + 1, y: other.y };
  }
  return { zone: target.zone ?? here.zone ?? 0, x: target.x, y: target.y };
}

async function teleport(world, bot, target) {
  const spot = resolve(world, bot, target);
  areaOf(spot.zone);
  return world.debug(bot, { op: 'teleport', ...spot });
}

// Puts an enemy next to a bot (distance units east of it) or at x/y in the bot's zone. Returns its id and where it landed.
async function spawnEnemy(world, bot, { kind, level, x, y, distance = 3 }) {
  const here = world.player(bot);
  if (!here) throw Error(`Bot ${bot} is not in the world.`);
  const at = x === undefined || y === undefined ? { x: here.x + distance, y: here.y } : { x, y };
  const reply = await world.debug(bot, { op: 'spawn_enemy', kind, ...at, ...(level ? { level } : {}) });
  return { bot, enemy: reply.result, player: reply.player };
}

// Walks like a player: ordinary move actions along a route through the real collision geometry.
async function walkTo(world, bot, target, timeoutMs = 60000) {
  const spot = resolve(world, bot, target);
  const start = world.player(bot);
  if ((start.zone || 0) !== spot.zone) throw Error(`${bot} is in zone ${start.zone || 0}; ${spot.zone} is reached by a portal or teleport.`);
  const area = areaOf(spot.zone), deadline = Date.now() + timeoutMs;
  for (const point of route(area, world.player(bot), spot)) {
    await world.action(bot, { type: 'move', ...point });
    const remaining = Math.max(1000, deadline - Date.now());
    await world.waitFor(() => (world.player(bot).zone || 0) !== spot.zone || dist(world.player(bot), point) < .4, remaining, `Walk ${bot}`);
    if ((world.player(bot).zone || 0) !== spot.zone) break;
  }
  await world.action(bot, { type: 'stop' });
  return { bot, goal: spot, player: world.summary(bot) };
}

// Walk into range if needed, then use an NPC offer (quest:accept:<id>, quest:claim:<id>, sell:materials, a service id...).
async function talkTo(world, bot, npcId, offer) {
  const npc = zones.flatMap(a => a.npcs || []).find(n => n.id === npcId);
  if (!npc) throw Error(`Unknown NPC ${npcId}.`);
  if (dist(world.player(bot), npc) > 2.5) await walkTo(world, bot, { npc: npcId });
  // The server throttles service requests to one per half second.
  await world.advance(550);
  const earlier = new Set(world.events);
  await world.action(bot, { type: 'interact', npc: npcId, ...(offer ? { offer } : {}) });
  const reply = await world.waitFor(() => world.events.find(e => !earlier.has(e) && e.bot === bot && (e.type === 'dialogue' || e.type === 'error') && (e.type === 'error' || e.npc?.id === npcId)), 5000, `Talk to ${npcId}`);
  if (reply.type === 'error') throw Error(reply.text);
  return { bot, npc: npcId, offer: offer || null, notice: reply.notice, dialogue: reply.npc.dialogue, offers: reply.npc.offers.map(o => o.id), gold: reply.gold, quests: reply.quests };
}

function aimAt(from, to) {
  const length = dist(from, to) || 1;
  return { fx: (to.x - from.x) / length, fy: (to.y - from.y) / length };
}
// Cast a learned skill through the same message the browser sends. `unlock` raises the level to the skill's level first.
async function castSkill(world, bot, { skill, target, unlock = true, resetCooldown = false, settleMs = 700 }) {
  const me = world.player(bot);
  const mine = skills.filter(s => s.class === me.look.class);
  const def = mine.find(s => s.id === skill);
  if (!def) throw Error(`${skill} is not a ${me.look.class} skill. Available: ${mine.map(s => `${s.id} (lv ${s.level})`).join(', ')}.`);
  const unlocked = me.level < def.level;
  if (unlocked && unlock) await world.debug(bot, { op: 'set_level', level: def.level });
  if (resetCooldown) await world.debug(bot, { op: 'reset_cooldowns' });
  const here = world.player(bot);
  const living = () => world.snapshot.slimes.filter(s => !s.dead && (s.zone || 0) === (here.zone || 0));
  let aim = { fx: here.fx ?? 1, fy: here.fy ?? 0 };
  let aimedAt = null;
  if (target === 'nearest') {
    aimedAt = living().sort((a, b) => dist(here, a) - dist(here, b))[0];
    if (aimedAt) aim = aimAt(here, aimedAt);
  } else if (target && 'enemy' in target) {
    aimedAt = livingEnemy(world, target.enemy);
    aim = aimAt(here, aimedAt);
  } else if (target && 'x' in target) aim = aimAt(here, target);
  else if (target && 'dx' in target) aim = { fx: target.dx, fy: target.dy };
  // A single-target skill needs a target to latch on, so mirror the browser: target the enemy first.
  if (aimedAt) await world.action(bot, { type: 'target', id: aimedAt.id });
  const hpBefore = new Map(living().map(s => [s.id, s.hp]));
  const earlier = new Set(world.events);
  await world.action(bot, { type: 'skill', id: skill, ...aim });
  await world.advance(settleMs);
  const mineAfter = world.summary(bot);
  const fresh = world.events.filter(e => !earlier.has(e) && e.bot === bot && (e.type === 'error' || e.actor === mineAfter.id));
  const damaged = world.snapshot.slimes.filter(s => hpBefore.has(s.id) && (s.hp < hpBefore.get(s.id) || s.dead))
    .map(s => ({ id: s.id, kind: s.kind, level: s.level, hpBefore: Math.round(hpBefore.get(s.id)), hp: Math.round(s.hp), dead: s.dead }));
  const cast = fresh.some(e => e.type === 'event' && e.kind === 'skill' && e.skill === skill);
  return { bot, skill, name: def.name, requiredLevel: def.level, raisedLevel: unlocked && unlock, cast,
    refused: fresh.filter(e => e.type === 'error').map(e => e.text), cooldownLeft: mineAfter.skillCd?.[skill] ?? 0,
    buffs: mineAfter.buffs, hp: mineAfter.hp, maxHp: mineAfter.maxHp, enemiesHurt: damaged,
    events: fresh.filter(e => e.type === 'event').map(({ bot: _, type, ...e }) => e) };
}

// Defeat enemies through the real kill path (XP, quest credit, gold and loot all go to this bot).
async function killEnemies(world, bot, { ids, kind, radius, max = 50 }) {
  const here = world.player(bot);
  const before = world.summary(bot);
  let chosen = world.snapshot.slimes.filter(s => !s.dead && (s.zone || 0) === (here.zone || 0));
  if (ids) chosen = chosen.filter(s => ids.includes(s.id));
  if (kind) chosen = chosen.filter(s => s.kind === kind);
  if (radius !== undefined) chosen = chosen.filter(s => dist(here, s) <= radius);
  chosen = chosen.sort((a, b) => dist(here, a) - dist(here, b)).slice(0, max);
  const killed = [];
  for (const enemy of chosen) {
    try { await world.debug(bot, { op: 'kill_enemy', id: enemy.id }); killed.push({ id: enemy.id, kind: enemy.kind, level: enemy.level }); } catch (error) { if (!/No living enemy/.test(error.message)) throw error; }
  }
  const after = world.summary(bot);
  return { bot, killed, count: killed.length, xpGained: after.xp - before.xp, levelsGained: after.level - before.level,
    goldNow: after.gold, dropsOnGround: world.snapshot.drops.filter(d => d.owner === after.id).length, player: after };
}

// One call to reach a state: level, gold, items, finished quests, then a place to stand.
async function setupCharacter(world, bot, { level, gold, items: give = [], finishQuests = [], teleportTo, heal = true }) {
  const steps = [];
  const run = async command => steps.push((await world.debug(bot, command)).op);
  if (level !== undefined) await run({ op: 'set_level', level });
  if (gold !== undefined) await run({ op: 'set_gold', gold });
  for (const g of give) await run({ op: 'give_item', item: g.item, quantity: g.quantity ?? 1, force: g.force ?? false });
  for (const id of finishQuests) await run({ op: 'quest', id, action: 'finish' });
  if (teleportTo) {
    const spot = resolve(world, bot, teleportTo);
    await run({ op: 'teleport', ...spot });
  }
  if (heal && level === undefined) await run({ op: 'set_hp', hp: world.player(bot).maxHp });
  return { bot, steps, player: world.summary(bot) };
}

async function waitForEvent(world, { type = 'event', kind, bot, timeout = 10000 }, earlier = new Set(world.events)) {
  const found = await world.waitFor(() => world.events.find(e => !earlier.has(e) && e.type === type && (!kind || e.kind === kind) && (!bot || e.bot === bot)), timeout, `Event ${type}${kind ? ':' + kind : ''}`);
  const { type: t, bot: b, ...rest } = found;
  return { received: true, bot: b, type: t, ...rest };
}

// Static catalog and map facts, so a caller never has to read the world files.
function describe(what = 'overview') {
  const area = (a, zone) => ({ zone, name: a.name || 'Greenmeadow', size: a.size, spawn: a.spawn, levels: a.levels || null,
    npcs: (a.npcs || []).map(n => n.id), portals: (a.portals || []).map(p => ({ id: p.id, at: { x: p.x, y: p.y }, r: p.r, to: p.to, arrival: { x: p.tx, y: p.ty } })),
    enemies: Object.fromEntries(Object.entries(a.slimes.reduce((c, s) => ({ ...c, [s.kind]: (c[s.kind] || 0) + 1 }), {})).map(([k, n]) => [k, { spawns: n, defaultLevel: DEFAULT_LEVELS[k] }])) });
  switch (what) {
    case 'zones': return { zones: zones.map(area) };
    case 'npcs': return { npcs: zones.flatMap((a, zone) => (a.npcs || []).map(n => ({ zone, id: n.id, name: n.name, role: n.role, x: n.x, y: n.y, buys: !!n.buys, offers: n.offers.map(o => ({ id: o.id, label: o.label, cost: o.cost })) }))) };
    case 'quests': return { quests: quests.map(q => ({ zone: q.zone, id: q.id, title: q.title, npc: q.npc, requires: q.requires || null, repeatable: !!q.repeatable, level: q.level, rewardXp: q.reward_xp ?? q.rewardXp, rewardGold: q.reward_gold ?? q.rewardGold, objectives: q.objectives })) };
    case 'items': return { items };
    case 'skills': return { skills: skills.map(({ id, name, class: c, level, cooldown, effect }) => ({ id, name, class: c, level, cooldown, effect: effect.effect })) };
    case 'enemies': return { defaultLevels: DEFAULT_LEVELS, zones: zones.map(area).map(({ zone, name, enemies }) => ({ zone, name, enemies })) };
    default: return { zones: zones.map(area), quests: quests.map(q => q.id), itemCount: items.length, skillCount: skills.length,
      hint: 'Ask for npcs, quests, items, skills, enemies or zones in full.' };
  }
}

module.exports = { zones, items, skills, quests, targetSchema, botName, debugSchema, socialSchema, resolve, teleport, spawnEnemy, walkTo, talkTo, castSkill, killEnemies, setupCharacter, waitForEvent, describe };
