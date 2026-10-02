const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('./driver.cjs');
const { route } = require('./route.cjs');
const kit = require('./tools.cjs');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

const crags = map.zones[0];
// `area` is the map of the zone the bot stands in: the meadow by default, or `crags`.
async function walkTo(world, bot, goal, area = map) {
  for (const point of route(area, world.player(bot), goal)) {
    await world.action(bot, { type: 'move', ...point });
    await world.waitFor(() => distance(world.player(bot), point) < .4, 20000, `Walk ${bot}`);
  }
  await world.action(bot, { type: 'stop' });
}

async function talk(w, bot, npcId, offer) {
  const npc = map.npcs.find(n => n.id === npcId);
  if (distance(w.player(bot), npc) > 2.5) await walkTo(w, bot, npc);
  await w.advance(550);
  const earlier = new Set(w.events);
  await w.action(bot, { type: 'interact', npc: npcId, ...(offer ? { offer } : {}) });
  return w.waitFor(() => w.events.find(e => !earlier.has(e) && e.bot === bot && e.type === 'dialogue' && e.npc.id === npcId), 5000, `Talk to ${npcId}`);
}
// Each kind's default level; every enemy rolls within two of it, and health/damage rise 12% per level above it.
const DEFAULT_LEVELS = { green: 2, blue: 3, pink: 3, yellow: 4, beetle: 5, big: 6, wisp: 5, spider: 7, wraith: 8, golem: 10 };
// Kill XP depends on each enemy's rolled level and a quest reward may cross a level, so compare lifetime XP.
// XP to the next level comes from world/levels.txt, the same file the server reads; an enemy pays 45 + 5 per level.
const levelXp = JSON.parse(fs.readFileSync(path.join(root, 'world/levels.txt'), 'utf8'));
const enemyXp = level => 45 + 5 * level;
const totalXp = p => p.xp + levelXp.slice(0, p.level - 1).reduce((a, b) => a + b, 0);
const skillCatalog = JSON.parse(fs.readFileSync(path.join(root, 'world/skills.txt'), 'utf8'));
const quest = (w, bot, id) => w.player(bot).quests.find(q => q.id === id);
async function defeat(w, bot, kind) {
  if (w.player(bot).hp < w.player(bot).maxHp * .85) await talk(w, bot, 'healer', 'blessing');
  // Starter gear needs isolated fights; prefer targets away from extra attackers.
  const risk = enemy => distance(w.player(bot), enemy) + 12 * (enemy.level - DEFAULT_LEVELS[enemy.kind]) + w.snapshot.slimes
    .filter(s => !s.dead && s.id !== enemy.id && s.zone === enemy.zone && distance(s, enemy) < 9)
    .reduce((sum, s) => sum + (s.kind === 'beetle' ? 200 : 50), 0);
  const enemy = w.snapshot.slimes.filter(s => !s.dead && s.kind === kind)
    .sort((a, b) => risk(a) - risk(b))[0];
  assert.ok(enemy, `A living ${kind} is available`);
  const kills = w.player(bot).kills;
  for (const point of route(map, w.player(bot), enemy)) {
    const current = () => w.snapshot.slimes.find(s => s.id === enemy.id);
    if (distance(w.player(bot), current()) < 5.3) break;
    await w.action(bot, { type: 'move', ...point });
    await w.waitFor(() => distance(w.player(bot), point) < .5 || distance(w.player(bot), current()) < 5.3, 20000, `Approach ${kind}`);
  }
  await w.action(bot, { type: 'target', id: enemy.id });
  await w.waitFor(() => w.snapshot.slimes.find(s => s.id === enemy.id).dead, 30000, `Defeat ${kind}`);
  await w.action(bot, { type: 'stop' });
  assert.equal(w.player(bot).kills, kills + 1);
  assert.ok(w.player(bot).hp > 0, 'The bot survives real combat');
}

// Walk to within `range` of a living enemy of one kind and return it (the bot attacks nothing on the way).
async function approach(w, bot, kind, range) {
  const risk = enemy => distance(w.player(bot), enemy) + 12 * (enemy.level - DEFAULT_LEVELS[enemy.kind]);
  const enemy = w.snapshot.slimes.filter(s => !s.dead && s.kind === kind && !s.zone).sort((a, b) => risk(a) - risk(b))[0];
  assert.ok(enemy, `A living ${kind} is available`);
  const current = () => w.snapshot.slimes.find(s => s.id === enemy.id);
  for (const point of route(map, w.player(bot), enemy)) {
    if (distance(w.player(bot), current()) < range) break;
    await w.action(bot, { type: 'move', ...point });
    await w.waitFor(() => distance(w.player(bot), point) < .5 || distance(w.player(bot), current()) < range, 20000, `Approach ${kind}`);
  }
  await w.action(bot, { type: 'stop' });
  return current;
}
const aimAt = (w, bot, enemy) => { const p = w.player(bot), d = Math.hypot(enemy.x - p.x, enemy.y - p.y) || 1; return { fx: (enemy.x - p.x) / d, fy: (enemy.y - p.y) / d }; };
// A skill is cast through the same message the browser sends; the server alone decides what it does.
async function cast(w, bot, id, enemy) {
  const aim = enemy ? aimAt(w, bot, enemy) : { fx: 1, fy: 0 };
  await w.action(bot, { type: 'skill', id, ...aim });
}
const lost = (before, after) => !after || after.dead || after.hp < before.hp;

const scenarios = {
  skills: {
    description: 'Learned skills at level 20: real casts per class, server cooldowns, buffs, projectiles, dashes and rejected requests.',
    startLevel: 20,
    async run(w, check) {
      await w.connect({ bot: 'Skillful', class: 'warrior' });
      await w.connect({ bot: 'Sage', class: 'mage' });
      await w.connect({ bot: 'Shade', class: 'assassin' });
      check(['Skillful', 'Sage', 'Shade'].every(b => w.player(b).level === 20), 'Test characters start at the configured level');
      const errors = bot => w.events.filter(e => e.bot === bot && e.type === 'error').map(e => e.text);
      await cast(w, 'Skillful', 'twinbolt');
      await w.waitFor(() => errors('Skillful').length > 0, 5000, 'Class error');
      check(errors('Skillful').at(-1) === 'That skill is not available to your class.', 'A warrior cannot cast a mage skill');
      await cast(w, 'Skillful', 'nonsense');
      await w.advance(300);
      check(Object.keys(w.player('Skillful').skillCd).length === 0, 'Rejected requests spend no cooldown');
      // Warrior: area damage, cooldown, buffs.
      const front = await approach(w, 'Skillful', 'green', 1.5);
      const before = { ...front() };
      await cast(w, 'Skillful', 'whirlwind', front());
      await w.waitFor(() => w.player('Skillful').skillCd.whirlwind > 0, 5000, 'Whirlwind cooldown');
      check(lost(before, front()), 'Whirlwind damages an enemy beside the warrior');
      const cd = w.player('Skillful').skillCd.whirlwind;
      check(cd > 4 && cd <= 6, 'The server starts the skill at its listed cooldown (' + cd.toFixed(2) + 's)');
      await w.advance(600);
      await cast(w, 'Skillful', 'whirlwind', front());
      await w.advance(300);
      check(w.player('Skillful').skillCd.whirlwind < cd - .5, 'A cast on cooldown is ignored instead of restarting it');
      await cast(w, 'Skillful', 'battlecry');
      await cast(w, 'Skillful', 'shieldwall');
      await w.waitFor(() => w.player('Skillful').buffs.length === 2, 5000, 'Buffs');
      const buffs = Object.fromEntries(w.player('Skillful').buffs.map(b => [b.id, b]));
      check(buffs.battlecry.kind === 'damage' && buffs.shieldwall.kind === 'shield' && buffs.battlecry.left > 8 && buffs.battlecry.time === 10, 'Buffs appear in the snapshot with their remaining time');
      // Mage: a projectile that explodes, lightning, and blink.
      const target = await approach(w, 'Sage', 'green', 4);
      const mageBefore = { ...target() };
      await cast(w, 'Sage', 'fireball', target());
      const flying = await w.waitFor(() => w.snapshot.bolts.find(b => b.size === 20 && b.color === '#ff8a3a'), 5000, 'Fireball bolt');
      check(flying.owner !== undefined, 'Fireball is a large orange projectile in the snapshot');
      await w.waitFor(() => lost(mageBefore, target()), 8000, 'Fireball impact');
      check(lost(mageBefore, target()), 'The fireball reaches and damages its target');
      const start = { x: w.player('Sage').x, y: w.player('Sage').y };
      await cast(w, 'Sage', 'blink');
      await w.waitFor(() => w.player('Sage').dashT > 0 || Math.hypot(w.player('Sage').x - start.x, w.player('Sage').y - start.y) > 2, 3000, 'Blink');
      await w.advance(500);
      check(Math.hypot(w.player('Sage').x - start.x, w.player('Sage').y - start.y) > 2.5, 'Blink moves the mage in one jump');
      // Assassin: a ring of knives, a damaging dash.
      await cast(w, 'Shade', 'knifering');
      await w.waitFor(() => w.snapshot.bolts.filter(b => b.color === '#f3d8ff').length >= 12, 5000, 'Knife ring');
      check(w.snapshot.bolts.filter(b => b.color === '#f3d8ff').length === 12, 'Knife Ring throws twelve knives');
      await cast(w, 'Shade', 'evasion');
      await w.waitFor(() => w.player('Shade').buffs.some(b => b.id === 'evasion'), 5000, 'Evasion');
      const from = { x: w.player('Shade').x, y: w.player('Shade').y };
      await cast(w, 'Shade', 'lunge');
      await w.advance(500);
      check(Math.hypot(w.player('Shade').x - from.x, w.player('Shade').y - from.y) > 2, 'Lunge carries the assassin forward');
      const events = w.events.filter(e => e.bot === 'Skillful' && e.kind === 'skill').map(e => e.skill);
      check(events.includes('whirlwind') && events.includes('battlecry'), 'Every cast is announced to the zone with its skill id');
    },
  },
  movement: {
    description: 'Three classes share spawn, walk through another player, and preserve enemy spacing.',
    async run(w, check) {
      for (const [bot, playerClass] of [['Warrior', 'warrior'], ['Mage', 'mage'], ['Assassin', 'assassin']]) {
        await w.connect({ bot, class: playerClass });
      }
      await w.waitFor(() => w.snapshot.players.length === 3);
      check(w.snapshot.players.length === 3, 'Three classes are online');
      check(w.player('Warrior').xpNeed === 100, 'Authoritative level threshold');
      const kings = w.snapshot.slimes.filter(s => s.kind === 'big');
      check(kings.length === 2 && kings.every(s => s.dead && s.state === 'waiting'), 'King slots start dormant');
      const original = { ...w.player('Warrior') };
      // Find a clear short segment so map collision cannot be confused with player collision.
      let point;
      for (const [dx, dy] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) {
        const goal = { x: original.x + dx, y: original.y + dy };
        const points = route(map, original, goal);
        if (points.length <= 2) { point = goal; break; }
      }
      assert.ok(point, 'A nearby movement destination is available');
      await walkTo(w, 'Assassin', point);
      await walkTo(w, 'Warrior', point);
      check(distance(w.player('Warrior'), w.player('Assassin')) < .5, 'Players can share a destination');
      check(distance(w.player('Warrior'), original) > 1, 'Movement is calculated by the server');
      await w.action('Warrior', { type: 'move', x: original.x, y: original.y });
      await w.waitFor(() => distance(w.player('Warrior'), original) < .4);
      check(distance(w.player('Warrior'), original) < .4, 'Player walks back through occupied spawn');
      const id = w.player('Warrior').id;
      await w.disconnect('Warrior');
      await w.connect({ bot: 'Warrior' });
      check(w.player('Warrior').id === id, 'Disconnect and resume keep the same character');
    },
  },
  ironhide: {
    description: 'A mage walks to an Ironhide, defeats it through normal target actions, and collects its loot.',
    async run(w, check) {
      await w.connect({ bot: 'Mage', class: 'mage' });
      const beetle = () => w.snapshot.slimes.find(s => s.kind === 'beetle' && s.hx === 18 && s.hy === 42);
      const before = { ...w.player('Mage') };
      const enemy = beetle();
      assert.ok(enemy && !enemy.dead, 'The meadow Ironhide is alive');
      // Every enemy rolls a level within two of its kind's default (Ironhide: 5); health, XP and gold follow it.
      const level = enemy.level, scale = per => 1 + per * (level - 5);
      check(level >= 3 && level <= 7, 'Ironhide level is within two of its default');
      check(enemy.maxHp === Math.round(240 * scale(.12)), 'Ironhide has authoritative, level-scaled health');
      for (const point of route(map, before, enemy)) {
        if (distance(point, enemy) < 7) break;
        await w.action('Mage', { type: 'move', ...point });
        await w.waitFor(() => {
          const current = w.snapshot.slimes.find(s => s.id === enemy.id);
          return distance(w.player('Mage'), point) < .5 || distance(w.player('Mage'), current) < 6;
        }, 20000, 'Approach Ironhide');
        if (distance(w.player('Mage'), w.snapshot.slimes.find(s => s.id === enemy.id)) < 6) break;
      }
      await w.action('Mage', { type: 'target', id: enemy.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === enemy.id).dead, 30000, 'Defeat Ironhide');
      const after = w.player('Mage');
      const xp = enemyXp(enemy.level), gold = Math.round(10 * scale(.1));
      check(after.kills === before.kills + 1 && after.xp === before.xp + xp && after.hp > 0,
        `Real combat awards one kill and the level-${level} XP (${xp}) while the mage survives`);
      const defeated = w.snapshot.slimes.find(s => s.id === enemy.id);
      await w.action('Mage', { type: 'move', x: defeated.x, y: defeated.y });
      await w.waitFor(() => w.player('Mage').gold >= before.gold + gold, 15000, 'Collect Ironhide gold');
      check(w.events.some(e => e.kind === 'pickup' && e.actor === before.id && e.value === gold), `Killer receives the level-scaled ${gold}-gold pickup`);
      await w.action('Mage', { type: 'stop' });
      const progress = { ...w.player('Mage') };
      await w.disconnect('Mage');
      await w.connect({ bot: 'Mage', class: 'mage' });
      check(w.player('Mage').id === progress.id && w.player('Mage').kills === progress.kills && w.player('Mage').gold === progress.gold,
        'Earned combat progress survives disconnect and resume');
    },
  },
  city: {
    description: 'A warrior walks into Alderhaven and receives authoritative healer and armorer service results.',
    async run(w, check) {
      await w.connect({ bot: 'Warrior' });
      await w.action('Warrior', { type: 'interact', npc: 'healer', offer: 'blessing' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')));
      check(w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')), 'Remote services are refused');
      await walkTo(w, 'Warrior', { x: 32, y: 80 });
      const gold = w.player('Warrior').gold;
      await w.action('Warrior', { type: 'interact', npc: 'healer', offer: 'blessing' });
      await w.waitFor(() => w.events.some(e => e.type === 'dialogue' && e.npc.id === 'healer'));
      check(w.player('Warrior').gold === gold, 'Sanctuary service is free');
      await walkTo(w, 'Warrior', { x: 33, y: 88 });
      await w.action('Warrior', { type: 'equip', armor: 'none', weapon: 'none' });
      await w.waitFor(() => w.player('Warrior').look.warriorWeapon === 'none');
      await w.action('Warrior', { type: 'interact', npc: 'smith', offer: 'fitting' });
      await w.waitFor(() => w.player('Warrior').look.warriorWeapon === 'sword' && w.player('Warrior').look.warriorArmor === 'crimson');
      check(w.player('Warrior').gold === gold, 'Armorer replaces starter gear for free');
    },
  },
  quests: {
    description: 'Town quest acceptance, real conversations, duplicate protection, XP/gold rewards, disconnect, and actual server restart.',
    async run(w, check) {
      const bot = 'QuestWarrior';
      await w.connect({ bot });
      await w.action(bot, { type: 'interact', npc: 'guide', offer: 'quest:accept:welcome' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')));
      check(!w.player(bot).quests.length, 'Quest acceptance from a distance is refused');
      await talk(w, bot, 'healer');
      await talk(w, bot, 'guide', 'quest:accept:welcome');
      await w.waitFor(() => !!quest(w, bot, 'welcome'));
      check(quest(w, bot, 'welcome').counts.every(n => n === 0), 'Earlier conversations do not count before acceptance');
      const incomplete = await talk(w, bot, 'guide', 'quest:claim:welcome');
      check(incomplete.notice.includes('Complete the objectives') && incomplete.gold === 0, 'Incomplete reward claims are refused');
      await talk(w, bot, 'healer');
      await talk(w, bot, 'healer');
      await talk(w, bot, 'guide', 'quest:accept:welcome');
      await w.waitFor(() => quest(w, bot, 'welcome').counts[0] === 1);
      check(JSON.stringify(quest(w, bot, 'welcome').counts) === '[1,0,0]', 'Repeated conversations are capped and reaccepting preserves progress');
      const id = w.player(bot).id;
      await w.disconnect(bot); await w.connect({ bot });
      check(w.player(bot).id === id && JSON.stringify(quest(w, bot, 'welcome').counts) === '[1,0,0]', 'Accepted quest and partial progress survive disconnect');
      await talk(w, bot, 'smith');
      await talk(w, bot, 'innkeeper', 'quest:claim:welcome');
      await w.waitFor(() => quest(w, bot, 'welcome').counts.every(n => n === 1));
      check(!quest(w, bot, 'welcome').claimed && w.player(bot).gold === 0, 'All three objectives are counted but the wrong NPC cannot pay the reward');
      const reward = await talk(w, bot, 'guide', 'quest:claim:welcome');
      await w.waitFor(() => quest(w, bot, 'welcome').claimed);
      check(reward.gold === 12 && w.player(bot).xp === 10, 'Turn-in awards exactly 12 gold and 10 XP');
      await talk(w, bot, 'guide', 'quest:claim:welcome');
      await talk(w, bot, 'guide', 'quest:accept:welcome');
      check(w.player(bot).gold === 12 && quest(w, bot, 'welcome').completions === 1, 'One-time rewards cannot be replayed or reaccepted');
      const database = w.db;
      await w.restart();
      check(w.db === database && w.player(bot).id === id && quest(w, bot, 'welcome').claimed && w.player(bot).gold === 12 && w.player(bot).xp === 10,
        'Quest completion and rewards survive restarting the actual Rust process');
      await talk(w, bot, 'guide', 'quest:claim:welcome');
      check(w.player(bot).gold === 12 && w.player(bot).xp === 10, 'Replaying a claim after restart grants nothing');
    },
  },
  quest_combat: {
    description: 'One real slime fight, then shortcut kills through the real kill path: prerequisite unlocks, level-up, killer-only quest credit, repeatable bounty, and save/resume.',
    async run(w, check) {
      const bot = 'QuestMage';
      await w.connect({ bot, class: 'mage' });
      // The welcome tour is covered by the quests scenario; here it is only the prerequisite of the patrol.
      await kit.setupCharacter(w, bot, { finishQuests: ['welcome'] });
      await w.connect({ bot: 'Observer' });
      // Level 1 here; the kills below pay enough XP to pass level 2, so the locked-skill refusal is checked first.
      await cast(w, bot, 'twinbolt');
      await w.waitFor(() => w.events.some(e => e.bot === bot && e.type === 'error' && e.text === 'Twin Bolt unlocks at level 2.'), 5000, 'Locked skill');
      check(Object.keys(w.player(bot).skillCd).length === 0, 'A skill above the mage level is refused with its unlock level and costs nothing');
      const locked = await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      check(locked.notice.includes('earlier quest') && !quest(w, bot, 'ironhide_hunt'), 'Ironhide hunt is locked until the slime patrol is turned in');
      await talk(w, bot, 'gatekeeper', 'quest:accept:slime_patrol');
      // One enemy is fought for real (movement, targeting, damage); the other five go through the same kill path.
      await defeat(w, bot, 'green');
      await w.waitFor(() => quest(w, bot, 'slime_patrol').counts[0] === 1);
      check((await kit.killEnemies(w, bot, { kind: 'green', max: 5 })).count === 5, 'Five more greens are defeated through the kill path');
      await w.waitFor(() => quest(w, bot, 'slime_patrol').counts[0] === 6);
      check(quest(w, bot, 'slime_patrol').counts[0] === 6, 'One real kill and five shortcut kills advance the accepted slime patrol');
      check(w.player('Observer').kills === 0 && !w.player('Observer').quests.length, 'Another player receives no killer quest credit');
      await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      check(!quest(w, bot, 'ironhide_hunt'), 'Completing objectives alone does not unlock the next quest');
      // Kill XP depends on the rolled enemy levels, so the mage is level 2 or 3 here. The patrol pays 20 XP: top the
      // bar up so that turning it in crosses exactly one level and leaves 10 XP over.
      await w.debug(bot, { op: 'give_xp', amount: w.player(bot).xpNeed - 20 - w.player(bot).xp + 10 });
      const before = { ...w.player(bot) }, next = before.level + 1;
      check(before.level >= 2 && before.xp === before.xpNeed - 10, 'The top-up stops just short of the next level');
      await talk(w, bot, 'gatekeeper', 'quest:claim:slime_patrol');
      await w.waitFor(() => quest(w, bot, 'slime_patrol').claimed);
      check(w.player(bot).gold === before.gold + 24 && w.player(bot).level === next && w.player(bot).xp === 10 && totalXp(w.player(bot)) === totalXp(before) + 20,
        'Patrol turn-in awards 24 gold and 20 XP, levels the mage, and carries the remainder');
      const unlocks = skillCatalog.filter(k => k.class === 'mage' && k.level === next).map(k => k.id);
      const levelUp = w.events.find(e => e.bot === bot && e.kind === 'levelup' && e.actor === w.player(bot).id && e.level === next);
      check(levelUp && JSON.stringify(levelUp.unlocked) === JSON.stringify(unlocks), 'The level-up event carries the new level and names the skill it unlocks');
      await cast(w, bot, 'twinbolt');
      await w.waitFor(() => w.player(bot).skillCd.twinbolt > 0, 5000, 'Twin Bolt cooldown');
      check(w.snapshot.bolts.length >= 2 || w.events.some(e => e.bot === bot && e.kind === 'skill' && e.skill === 'twinbolt'), 'Twin Bolt casts for real once unlocked');
      await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      await talk(w, bot, 'merchant', 'quest:accept:meadow_bounty');
      await w.waitFor(() => !!quest(w, bot, 'meadow_bounty'));
      check(quest(w, bot, 'meadow_bounty').counts[0] === 0, 'Bounty excludes kills made before acceptance');
      check((await kit.killEnemies(w, bot, { kind: 'beetle', max: 2 })).count === 2, 'Two Ironhides are defeated through the kill path');
      await w.waitFor(() => quest(w, bot, 'ironhide_hunt').counts[0] === 2 && quest(w, bot, 'meadow_bounty').counts[0] === 2);
      check(quest(w, bot, 'ironhide_hunt').counts[0] === 2 && quest(w, bot, 'slime_patrol').counts[0] === 6,
        'Ironhide kills advance both matching active quests while completed patrol stays unchanged');
      // Six more for the bounty: only two greens are left alive (respawn takes 22 s), so take the other small slimes too.
      let rest = 6;
      for (const kind of ['green', 'blue', 'pink', 'yellow']) if (rest) rest -= (await kit.killEnemies(w, bot, { kind, max: rest })).count;
      assert.equal(rest, 0, 'Enough slimes are alive for the bounty');
      await w.waitFor(() => quest(w, bot, 'meadow_bounty').counts[0] === 8);
      await talk(w, bot, 'smith', 'quest:claim:ironhide_hunt');
      await talk(w, bot, 'gatekeeper', 'quest:accept:king_challenge');
      await w.waitFor(() => !!quest(w, bot, 'king_challenge'));
      check(quest(w, bot, 'king_challenge').counts[0] === 0, 'Ironhide turn-in unlocks the King Slime quest without crediting other kills');
      const bountyBefore = { ...w.player(bot) };
      await talk(w, bot, 'merchant', 'quest:claim:meadow_bounty');
      await w.waitFor(() => quest(w, bot, 'meadow_bounty').claimed);
      check(w.player(bot).gold === bountyBefore.gold + 25 && totalXp(w.player(bot)) === totalXp(bountyBefore) + 40,
        'Eight mixed kills pay the promised bounty reward');
      await talk(w, bot, 'merchant', 'quest:claim:meadow_bounty');
      check(w.player(bot).gold === bountyBefore.gold + 25, 'Repeated bounty claims cannot duplicate rewards');
      await talk(w, bot, 'merchant', 'quest:accept:meadow_bounty');
      await w.waitFor(() => !quest(w, bot, 'meadow_bounty').claimed);
      check(quest(w, bot, 'meadow_bounty').counts[0] === 0 && quest(w, bot, 'meadow_bounty').completions === 1,
        'Taking the bounty again resets objectives and preserves completion history');
      const premature = await talk(w, bot, 'merchant', 'quest:claim:meadow_bounty');
      check(premature.notice.includes('Complete the objectives'), 'A new bounty must be completed before claiming again');
      await w.restart();
      check(quest(w, bot, 'meadow_bounty').counts[0] === 0 && !quest(w, bot, 'meadow_bounty').claimed && quest(w, bot, 'meadow_bounty').completions === 1,
        'Reset bounty and history survive a real server restart');
    },
  },
  inventory: {
    description: 'Real mob loot, owned equipment, remote sale refusal, vendor sales, replay protection, and inventory persistence.',
    async run(w, check) {
      const bot = 'LootMage';
      await w.connect({ bot, class: 'mage' });
      const count = id => w.player(bot).inventory.find(s => s.item === id)?.quantity || 0;
      check(count('mage_armor_apprentice') === 1 && count('mage_weapon_ash') === 1, 'Starter items are server-issued');
      await w.action(bot, { type: 'equip', armor: 'runic', weapon: 'crystal' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('must own')));
      check(w.player(bot).look.mageWeapon === 'ash', 'Unowned upgrades cannot be equipped');
      await defeat(w, bot, 'green');
      const corpse = w.snapshot.slimes.filter(s => s.dead && s.kind === 'green').sort((a, b) => distance(w.player(bot), a) - distance(w.player(bot), b))[0];
      const gold = w.player(bot).gold;
      await walkTo(w, bot, corpse);
      await w.waitFor(() => count('slime_gel') === 1);
      // The snapshot with the new stack and the pickup event are separate messages, so wait for the event too.
      const pickedUp = () => w.events.some(e => e.kind === 'itemPickup' && e.actor === w.player(bot).id && e.item === 'slime_gel');
      await w.waitFor(pickedUp, 5000, 'Pickup event');
      check(pickedUp(), 'Real combat creates a collectible material drop');
      await w.waitFor(() => w.player(bot).gold > gold);
      check(w.player(bot).gold > gold, 'Gold drops remain alongside material drops');
      await w.action(bot, { type: 'interact', npc: 'merchant', offer: 'sell:slime_gel:1' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')));
      check(count('slime_gel') === 1, 'Remote sales cannot consume inventory');
      const inventory = JSON.stringify(w.player(bot).inventory);
      await w.restart();
      check(JSON.stringify(w.player(bot).inventory) === inventory, 'Loot survives restarting the private Rust server');
      const before = w.player(bot).gold;
      const sale = await talk(w, bot, 'merchant', 'sell:slime_gel:1');
      await w.waitFor(() => count('slime_gel') === 0);
      check(sale.gold === before + 3, 'Vendor consumes one material and pays its catalog value');
      const replay = await talk(w, bot, 'merchant', 'sell:slime_gel:1');
      check(replay.gold === sale.gold && replay.notice.includes('items you own'), 'Replaying a sale cannot duplicate gold');
      await w.action(bot, { type: 'equip', weapon: 'none' });
      await w.waitFor(() => w.player(bot).look.mageWeapon === 'none');
      await talk(w, bot, 'smith', 'fitting');
      await w.waitFor(() => w.player(bot).look.mageWeapon === 'ash');
      const worthless = await talk(w, bot, 'smith', 'sell:mage_weapon_ash:1');
      check(worthless.notice.includes('Starter gear cannot be sold') && worthless.gold === sale.gold, 'Free starter replacement cannot generate sale income');
      await w.restart();
      check(count('slime_gel') === 0 && w.player(bot).gold === sale.gold, 'Sale and item removal survive restart');
    },
  },
  stats: {
    description: 'Reach level 2 with the set_level shortcut (real XP-to-level is covered by quest_combat), train stats, reject overspending, and resume saved allocations.',
    async run(w, check) {
      const bot = 'StatMage'; await w.connect({ bot, class: 'mage' });
      check(w.player(bot).statPoints === 0 && w.player(bot).hitChance === .9, 'New characters have no free training points and 90% hit chance');
      await w.action(bot, { type: 'allocate_stat', stat: 'intellect' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Level up')));
      check(w.player(bot).attributes.intellect === 0, 'The server rejects spending points before leveling');
      await kit.setupCharacter(w, bot, { level: 2 });
      await w.waitFor(() => w.player(bot).level === 2 && w.player(bot).statPoints === 3);
      check(w.player(bot).statPoints === 3, 'Level 2 grants three training points');
      const before = { ...w.player(bot) };
      for (const stat of ['intellect', 'dexterity', 'accuracy']) {
        await w.action(bot, { type: 'allocate_stat', stat });
        await w.waitFor(() => w.player(bot).attributes[stat] === 1);
      }
      const trained = w.player(bot);
      check(trained.attack === before.attack + 2 && trained.attackCooldown < before.attackCooldown, 'Mage intellect improves damage and recovery');
      check(trained.dodgeChance === .005 && trained.hitChance === .905, 'Dexterity and Accuracy change authoritative dodge and hit chances');
      check(trained.statPoints === 0, 'All three training points are consumed');
      await w.action(bot, { type: 'allocate_stat', stat: 'stamina' });
      await w.advance(150);
      check(w.player(bot).attributes.stamina === 0, 'Further training cannot overspend points');
      await w.restart();
      check(w.player(bot).statPoints === 0 && w.player(bot).attributes.intellect === 1 && w.player(bot).attributes.dexterity === 1 && w.player(bot).attributes.accuracy === 1, 'Allocations and remaining points survive a real restart');
    },
  },
  crags: {
    description: 'Walk through the Emberfall Gate into the level 5-10 Crags, use both gates, fight a leveled Cinder Wisp, and keep the zone across reconnect and restart.',
    async run(w, check) {
      const bot = 'Crawler';
      await w.connect({ bot, class: 'warrior' });
      const defaults = { green: 2, blue: 3, pink: 3, yellow: 4, beetle: 5, big: 6, wisp: 5, spider: 7, wraith: 8, golem: 10 };
      const home = w.snapshot.slimes;
      check(w.player(bot).zone === 0, 'New characters start in Greenmeadow');
      check(home.length === 21 && home.every(s => s.zone === 0), 'A meadow client receives exactly the 21 meadow enemies and nothing from the Crags');
      check(home.every(s => Math.abs(s.level - defaults[s.kind]) <= 2 && s.level >= 1), 'Every meadow enemy level is within two of its kind default');
      // The gate is a real walk: the meadow route ends between its two posts.
      const gate = map.portals[0];
      await walkTo(w, bot, { x: gate.x, y: gate.y + 4 });
      await w.action(bot, { type: 'move', x: gate.x, y: gate.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 1, 15000, 'Step through the Emberfall Gate');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: gate.tx, y: gate.ty };
      check(w.player(bot).zone === 1 && distance(w.player(bot), arrival) < 1, 'The server moves the walker to the Crags arrival camp');
      const away = w.snapshot.slimes;
      check(away.length === 26 && away.every(s => s.zone === 1) && new Set(away.map(s => s.kind)).size === 4
        && ['wisp', 'spider', 'wraith', 'golem'].every(k => away.some(s => s.kind === k)), 'A Crags client receives exactly the 26 Crags monsters, four kinds, and nothing from the meadow');
      check(away.every(s => Math.abs(s.level - defaults[s.kind]) <= 2 && s.level >= 3) && new Set(away.map(s => s.level - defaults[s.kind])).size >= 3,
        'Crags levels sit within two of each default and really vary');
      check(away.filter(s => s.kind === 'wisp').every(s => s.maxHp === Math.round(280 * (1 + .12 * (s.level - 5)))), 'Health follows each rolled level');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Emberfall Crags') && e.text.includes('5-10'.replace('-', '–'))), 'The player is told the recommended levels');
      // A second character in the meadow shares coordinates but not the world.
      await w.connect({ bot: 'Meadow', class: 'mage' });
      check(w.player('Meadow').zone === 0 && w.player(bot).zone === 1, 'Players in different zones are tracked separately');
      check(w.views.get(bot).players.length === 1 && w.views.get('Meadow').players.length === 1 && w.views.get(bot).slimes.every(s => s.zone === 1) && w.views.get('Meadow').slimes.every(s => s.zone === 0),
        'Each client is sent only its own zone: no foreign players or enemies');
      check(JSON.stringify(w.snapshot.zonesSeen) === '[0,1]', 'The merged test view covers both zones while a bot stands in each');
      await w.disconnect('Meadow');
      // The way back is checked here, at the camp, before any fighting: after a restart the walk home from the wisps' band would
      // cross wisp territory, and a level-1 warrior can die on it. Then the gate is taken again.
      const back = crags.portals[0];
      await walkTo(w, bot, { x: back.x, y: back.y - 3 }, crags);
      await w.action(bot, { type: 'move', x: back.x, y: back.y + 1.2 });
      await w.waitFor(() => w.player(bot).zone === 0, 15000, 'Step through the Meadow Gate');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 0 && distance(w.player(bot), { x: back.tx, y: back.ty }) < 1, 'The Meadow Gate arrives beside the Emberfall Gate');
      await w.action(bot, { type: 'move', x: gate.x, y: gate.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 1, 15000, 'Step through the Emberfall Gate again');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 1 && distance(w.player(bot), arrival) < 1, 'The gate works again right after arriving, in both directions');
      // Fight the weakest wisp through normal target actions.
      // Test worlds are invulnerable, so any wisp will do: take the one guarding the first ford, the nearest on the way north.
      const ford = { x: crags.paths[0][3][0], y: crags.paths[0][3][1] };
      const wisp = w.snapshot.slimes.filter(s => s.kind === 'wisp' && !s.dead).sort((a, b) => distance({ x: a.hx, y: a.hy }, ford) - distance({ x: b.hx, y: b.hy }, ford))[0];
      check(wisp.level >= 3 && wisp.level <= 7 && wisp.zone === 1, `Fighting the level ${wisp.level} Cinder Wisp that guards the first ford`);
      const before = { ...w.player(bot) };
      for (const point of route(crags, w.player(bot), wisp)) {
        const current = () => w.snapshot.slimes.find(s => s.id === wisp.id);
        if (distance(w.player(bot), current()) < 5.3) break;
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .5 || distance(w.player(bot), current()) < 5.3, 25000, 'Approach the wisp');
      }
      await w.action(bot, { type: 'target', id: wisp.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === wisp.id).dead || w.player(bot).hp <= 0, 40000, 'Defeat the wisp');
      await w.action(bot, { type: 'stop' });
      const after = w.player(bot);
      check(after.hp > 0, 'The warrior survives real combat in the Crags');
      const xp = enemyXp(wisp.level), gold = Math.round(18 * (1 + .1 * (wisp.level - 5)));
      check(after.kills === before.kills + 1 && after.xp === before.xp + xp, `The kill pays the level-${wisp.level} XP (${xp})`);
      const corpse = w.snapshot.slimes.find(s => s.id === wisp.id);
      await w.action(bot, { type: 'move', x: corpse.x, y: corpse.y });
      await w.waitFor(() => w.player(bot).gold >= before.gold + gold && w.player(bot).inventory.some(i => i.item === 'ember_core'), 15000, 'Collect Crags loot');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).gold === before.gold + gold, `Level-scaled gold (${gold}) and an Ember Core drop are collected`);
      // The zone is part of the saved character.
      const where = { ...w.player(bot) };
      await w.disconnect(bot);
      await w.connect({ bot });
      check(w.player(bot).zone === 1 && distance(w.player(bot), where) < 1.2, 'Resume puts the character back in the Crags');
      await w.restart();
      check(w.player(bot).zone === 1 && w.player(bot).gold === where.gold, 'The Crags position and loot survive a Rust restart');
    },
  },
  bags: {
    description: 'Buy an expansion bag from Linden with granted gold (500 exactly, 499 refused), then fill every cell with given items to verify authoritative capacity, overflow refusal and persistence.',
    async run(w, check) {
      const bot = 'BagMage'; await w.connect({ bot, class: 'mage' });
      check(w.player(bot).bagCapacity === 16 && w.player(bot).bags.length === 0, 'New character starts with a sixteen-slot backpack');
      await w.action(bot, { type: 'interact', npc: 'merchant', offer: 'satchel' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')));
      check(w.player(bot).bags.length === 0, 'Expansion bags cannot be bought remotely');
      const refused = await talk(w, bot, 'merchant', 'satchel');
      check(refused.notice.includes('gold') && w.player(bot).bags.length === 0, 'Insufficient funds do not grant a bag');
      // The 500 gold used to be farmed through quests and combat (about eight minutes); the shortcut grants it, and the purchase is still the real NPC offer.
      await kit.setupCharacter(w, bot, { gold: 499 });
      const short = await talk(w, bot, 'merchant', 'satchel');
      check(short.notice.includes('gold') && w.player(bot).bags.length === 0 && w.player(bot).gold === 499, 'One gold short still does not grant a bag');
      await kit.setupCharacter(w, bot, { gold: 500 });
      const before = w.player(bot).gold;
      const purchase = await talk(w, bot, 'merchant', 'satchel');
      await w.waitFor(() => w.player(bot).bags.length === 1);
      check(purchase.notice.includes('22 bag slots') && w.player(bot).gold === before - 500, 'Earned gold purchases six additional slots for 500 gold');
      check(w.player(bot).bagCapacity === 22 && w.player(bot).bags[0] === 'linen_satchel', 'Snapshot carries the fitted bag and authoritative capacity');
      // Fill all 22 cells with distinct items; the 23rd kind has nowhere to go.
      const kinds = kit.items.filter(i => i.kind !== 'bag');
      while (w.player(bot).bagUsed < 22) {
        const have = new Set(w.player(bot).inventory.map(s => s.item));
        const fresh = kinds.find(i => !have.has(i.id));
        assert.ok(fresh, 'the catalog has enough kinds to fill the bags');
        await w.debug(bot, { op: 'give_item', item: fresh.id, quantity: 1 });
        await w.waitFor(() => w.player(bot).inventory.some(s => s.item === fresh.id), 3000, 'Given item');
      }
      check(w.player(bot).bagUsed === 22 && w.player(bot).bagUsed === w.player(bot).bagCapacity, 'Given items fill all 22 cells');
      const have = new Set(w.player(bot).inventory.map(s => s.item)), overflow = kinds.find(i => !have.has(i.id));
      await assert.rejects(() => w.debug(bot, { op: 'give_item', item: overflow.id, quantity: 1 }), /Bags are full/);
      check(true, 'A new kind of item is refused when every cell holds a stack');
      const stacked = w.player(bot).inventory.find(s => kinds.some(i => i.id === s.item && i.kind === 'material'));
      await w.debug(bot, { op: 'give_item', item: stacked.item, quantity: 5 });
      await w.waitFor(() => w.player(bot).inventory.find(s => s.item === stacked.item).quantity === stacked.quantity + 5, 3000, 'Stack grows');
      check(w.player(bot).bagUsed === 22, 'More of a carried item still stacks into its cell');
      await w.restart();
      check(w.player(bot).bagCapacity === 22 && w.player(bot).bags[0] === 'linen_satchel' && w.player(bot).gold === before - 500, 'Bag ownership and payment survive restarting Rust');
    },
  },

  shortcuts: {
    description: 'Test-server shortcuts through the real server: level 20, gold, items, finished quests, teleport, skill casts, bulk kills, pickup, trade, a portal walk, death and respawn, and persistence across a restart.',
    async run(w, check) {
      await w.connect({ bot: 'Gm', class: 'warrior' });
      check(w.player('Gm').level === 1 && w.player('Gm').gold === 0, 'A new character starts at level 1 with no gold');
      const finished = ['slime_patrol', 'ironhide_hunt', 'king_challenge'];
      const rewardGold = kit.quests.filter(q => finished.includes(q.id)).reduce((sum, q) => sum + q.rewardGold, 0);
      const setup = await kit.setupCharacter(w, 'Gm', { level: 20, gold: 1000, items: [{ item: 'slime_gel', quantity: 12 }], finishQuests: ['king_challenge'], teleportTo: { spawn: 1 } });
      const me = () => w.player('Gm');
      check(me().level === 20 && me().hp === me().maxHp && setup.player.statPoints === 57, 'set_level reaches level 20 at full health with 57 stat points');
      const up = await kit.waitForEvent(w, { kind: 'levelup', bot: 'Gm' }, new Set());
      check(up.level === 20 && up.unlocked.length === 10, 'The level-up event names the ten skills it unlocks');
      check(me().gold === 1000 + rewardGold && finished.every(id => quest(w, 'Gm', id)?.claimed), 'Finishing a quest walks its prerequisites and pays every reward once');
      check(me().quests.find(q => q.id === 'king_challenge').completions === 1, 'A finished one-time quest records one completion');
      check(me().zone === 1 && me().inventory.find(i => i.item === 'slime_gel').quantity === 12, 'The character stands in the Crags and holds the given items');
      await kit.castSkill(w, 'Gm', { skill: 'battlecry' }).then(r => check(r.cast && r.buffs.some(b => b.id === 'battlecry') && r.cooldownLeft > 20, 'cast_skill casts a skill and reports its buff and cooldown'));
      const again = await kit.castSkill(w, 'Gm', { skill: 'battlecry', settleMs: 300 });
      check(!again.cast && again.cooldownLeft > 19, 'A repeated cast is ignored while the skill is on cooldown');
      const reset = await kit.castSkill(w, 'Gm', { skill: 'battlecry', resetCooldown: true, settleMs: 300 });
      check(reset.cast, 'resetCooldown allows an immediate second cast');
      await w.connect({ bot: 'Rookie', class: 'mage' });
      const locked = await kit.castSkill(w, 'Rookie', { skill: 'meteor', unlock: false, settleMs: 300 });
      check(!locked.cast && locked.refused.some(t => /unlocks at level 14/.test(t)), 'The server refuses a skill above the level when unlock is off');
      const unlocked = await kit.castSkill(w, 'Rookie', { skill: 'meteor', settleMs: 300 });
      check(unlocked.cast && unlocked.raisedLevel && w.player('Rookie').level === 14, 'unlock raises the level to the skill requirement and casts it');
      const xpBefore = totalXp(me()), kills = me().kills;
      const slain = await kit.killEnemies(w, 'Gm', { kind: 'wisp', max: 3 });
      check(slain.count === 3 && me().kills === kills + 3 && totalXp(me()) > xpBefore, 'kill_enemies defeats enemies through the real kill path with XP');
      check(slain.dropsOnGround >= 3 && w.snapshot.drops.some(d => d.owner === me().id && d.item === 'ember_core'), 'The kills drop loot owned by the killer');
      const dead = slain.killed[0].id;
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === dead).dead, 2000, 'Wisp stays dead');
      await w.debug('Gm', { op: 'respawn_enemy', id: dead });
      await w.waitFor(() => !w.snapshot.slimes.find(s => s.id === dead).dead, 3000, 'Wisp respawns');
      check(true, 'respawn_enemy brings a dead enemy back immediately');
      // spawn_enemy puts an enemy where the test needs it, in the bot's zone, at a chosen level.
      const spawned = await kit.spawnEnemy(w, 'Gm', { kind: 'golem', level: 12, distance: 4 });
      const golem = () => w.snapshot.slimes.find(s => s.id === spawned.enemy.id);
      check(golem() && !golem().dead && golem().kind === 'golem' && golem().level === 12 && golem().zone === me().zone, 'spawn_enemy places a living golem at level 12 in the bot\'s zone');
      check(Math.hypot(golem().x - me().x, golem().y - me().y) >= 1 && Math.hypot(golem().x - me().x, golem().y - me().y) < 8, 'spawn_enemy puts it a few steps from the bot, never on top of it');
      await assert.rejects(() => kit.spawnEnemy(w, 'Gm', { kind: 'big' }), /Invalid|kind/i, 'kings are not spawnable');
      check(true, 'spawn_enemy refuses kings and unknown kinds');
      const spawnKills = me().kills;
      await kit.killEnemies(w, 'Gm', { ids: [spawned.enemy.id] });
      check(me().kills === spawnKills + 1 && golem().dead, 'A spawned enemy dies through the real kill path');
      await w.debug('Gm', { op: 'drop_item', item: 'royal_jelly', quantity: 2 });
      await w.waitFor(() => me().inventory.some(i => i.item === 'royal_jelly' && i.quantity === 2), 6000, 'Pickup');
      check(true, 'drop_item places loot at the feet that the owner picks up');
      await assert.rejects(() => w.debug('Gm', { op: 'take_item', item: 'warrior_weapon_sword', quantity: 1 }), /spare|worn/, 'a worn copy stays');
      check(true, 'take_item refuses a worn copy');
      await assert.rejects(() => w.debug('Gm', { op: 'give_item', item: 'no_such_item', quantity: 1 }), /Unknown item/);
      check(true, 'An unknown item is rejected');
      await kit.teleport(w, 'Gm', { npc: 'merchant' });
      check(me().zone === 0 && Math.hypot(me().x - kit.zones[0].npcs.find(n => n.id === 'merchant').x, me().y - kit.zones[0].npcs.find(n => n.id === 'merchant').y) < 2.5, 'teleport to an NPC lands in talking range, across zones');
      const goldBefore = me().gold;
      const sale = await kit.talkTo(w, 'Gm', 'merchant', 'sell:materials');
      await w.waitFor(() => me().gold > goldBefore, 5000, 'Sale');
      check(/sold/.test(sale.notice) && !me().inventory.some(i => i.item === 'slime_gel'), 'talk_to sells materials to the merchant');
      await kit.teleport(w, 'Gm', { portal: 'emberfall_gate' });
      const gate = kit.zones[0].portals.find(p => p.id === 'emberfall_gate');
      check(me().zone === 0 && Math.hypot(me().x - gate.x, me().y - gate.y) > gate.r, 'teleport to a portal stops short of the gate');
      await w.action('Gm', { type: 'move', x: gate.x, y: gate.y });
      await w.waitFor(() => me().zone === 1, 10000, 'Portal');
      check(true, 'Walking into the gate crosses into the Crags');
      await w.debug('Gm', { op: 'set_level', level: 20 });
      const need20 = me().xpNeed;
      check(me().level === 20 && me().xp === 0, 'The character is level 20 with an empty bar before dying');
      await w.debug('Gm', { op: 'die' });
      await w.waitFor(() => me().dead, 3000, 'Defeat');
      await w.waitFor(() => me().level === 19, 3000, 'Penalty');
      check(me().xp === me().xpNeed - Math.floor(need20 / 3), 'Dying costs a third of level 20\'s XP and, with an empty bar, takes the character down to level 19');
      await kit.waitForEvent(w, { kind: 'respawn', bot: 'Gm', timeout: 8000 });
      await w.waitFor(() => !me().dead && me().hp === me().maxHp, 3000, 'Respawn heals');
      check(true, 'A defeated character respawns at full health');
      const snapshot = w.summary('Gm'), history = me().quests.map(q => [q.id, q.completions]);
      await w.restart();
      await w.waitFor(() => w.player('Gm') && w.player('Gm').level === 19, 10000, 'Resume');
      check(me().level === 19 && me().xp === snapshot.xp && me().gold === snapshot.gold && me().zone === snapshot.zone, 'Level, gold and zone survive restarting Rust');
      check(JSON.stringify(me().quests.map(q => [q.id, q.completions])) === JSON.stringify(history), 'Finished quests survive restarting Rust');
    },
  },

  social: {
    description: 'Friends and parties through real connections: requests by name and by bot, mutual friends that survive a restart, a five-member party that refuses a sixth, leader-only invites, party chat, party health, promote/kick/leave, and a dropped member keeping their seat.',
    async run(w, check) {
      const names = ['Ann', 'Bob', 'Cy', 'Dee', 'Eve', 'Fay'];
      for (const bot of names) await w.connect({ bot, class: 'mage' });
      const refused = (r, pattern) => r.notices.some(n => !n.ok && pattern.test(n.text));
      const state = bot => w.socialState(bot);

      // Friends: asking by name reaches the other player, who accepts; both lists change and both are saved.
      const asked = await w.social('Ann', { op: 'friend_request', name: 'bob' });
      check(asked.notices.some(n => n.ok && /Friend request sent to Bob/.test(n.text)) && state('Ann').outgoing[0]?.to === 'Bob', 'A friend request by name reaches the named player');
      check(state('Bob').incoming.some(i => i.kind === 'friend' && i.from === 'Ann'), 'The other player sees the request with its sender');
      check(refused(await w.social('Ann', { op: 'friend_request', bot: 'Bob' }), /already sent/), 'A second request to the same player is refused');
      check(refused(await w.social('Ann', { op: 'friend_request', name: 'Ann' }), /yourself/), 'Nobody can befriend themselves');
      check(refused(await w.social('Ann', { op: 'friend_request', name: 'Nobody' }), /No player named Nobody/), 'An unknown name is refused');
      await w.social('Bob', { op: 'friend_accept', bot: 'Ann' });
      check(state('Ann').friends.map(f => f.name).join() === 'Bob' && state('Bob').friends.map(f => f.name).join() === 'Ann', 'Accepting makes both players each other\'s friend');
      check(state('Ann').incoming.length === 0 && state('Bob').incoming.length === 0, 'The answered request is gone');
      check(refused(await w.social('Ann', { op: 'friend_request', name: 'Bob' }), /already your friend/), 'A friend cannot be requested again');
      await w.social('Cy', { op: 'friend_request', bot: 'Ann' });
      await w.social('Ann', { op: 'friend_decline', bot: 'Cy' });
      check(state('Ann').friends.length === 1 && state('Cy').outgoing.length === 0, 'Declining a request clears it without a friendship');
      // Requests both ways at once are an acceptance.
      await w.social('Dee', { op: 'friend_request', bot: 'Eve' });
      await w.social('Eve', { op: 'friend_request', bot: 'Dee' });
      check(state('Dee').friends[0]?.name === 'Eve' && state('Eve').friends[0]?.name === 'Dee', 'Asking someone who already asked you makes you friends');
      // Online state follows connections, and a dropped friend stays listed.
      await w.disconnect('Bob');
      await w.waitFor(() => state('Ann').friends[0]?.online === false, 5000, 'Friend offline');
      check(state('Ann').friends[0].name === 'Bob', 'An offline friend stays on the list');
      await w.connect({ bot: 'Bob' });
      await w.waitFor(() => state('Ann').friends[0]?.online === true && state('Bob').friends[0]?.name === 'Ann', 5000, 'Friend online');
      check(w.events.some(e => e.bot === 'Ann' && e.type === 'notice' && e.text === 'Bob came online.'), 'A friend is told when another friend comes online');

      // Parties: the leader fills five seats and a sixth is refused.
      for (const bot of ['Bob', 'Cy', 'Dee', 'Eve']) await w.social('Ann', { op: 'party_invite', bot });
      check(refused(await w.social('Ann', { op: 'party_invite', bot: 'Fay' }), /already fill the party/), 'Open invitations never promise more than five seats');
      for (const bot of ['Bob', 'Cy', 'Dee', 'Eve']) await w.social(bot, { op: 'party_accept', bot: 'Ann' });
      const party = state('Cy').party;
      check(party.size === 5 && party.leader === 'Ann' && party.max === 5 && ['Ann', 'Bob', 'Cy', 'Dee', 'Eve'].every(n => party.members.some(m => m.name === n)), 'Five players form one party led by the inviter');
      check(refused(await w.social('Ann', { op: 'party_invite', bot: 'Fay' }), /party is full/), 'A sixth player is refused');
      check(refused(await w.social('Bob', { op: 'party_invite', bot: 'Fay' }), /Only the party leader/), 'Only the leader invites');
      check(refused(await w.social('Fay', { op: 'party_accept', bot: 'Ann' }), /no longer pending/), 'A player nobody invited cannot join');
      // Chat reaches the party only.
      const said = await w.social('Bob', { op: 'party_chat', text: 'rally at the gate' });
      await w.waitFor(() => w.events.some(e => e.bot === 'Eve' && e.type === 'chat' && e.channel === 'party' && e.text === 'rally at the gate'), 5000, 'Party chat');
      check(!w.events.some(e => e.bot === 'Fay' && e.type === 'chat'), 'Party chat is not heard outside the party');
      check(said.chat.some(c => c.channel === 'party' && c.name === 'Bob'), 'The speaker also sees their party chat');
      // Health reaches the party within a moment.
      await w.debug('Cy', { op: 'set_hp', hp: 11 });
      await w.waitFor(() => w.bots.get('Ann').social.party.members.find(m => m.name === 'Cy')?.hp < 40, 5000, 'Party health');
      check(w.bots.get('Eve').social.party.members.find(m => m.name === 'Cy').maxHp === 80, 'A member\'s health shows on every member\'s party list');
      // Leader changes.
      await w.social('Ann', { op: 'party_promote', bot: 'Bob' });
      check(state('Dee').party.leader === 'Bob', 'Promoting hands the party to another member');
      check(refused(await w.social('Ann', { op: 'party_kick', bot: 'Cy' }), /Only the party leader/), 'A former leader cannot remove members');
      await w.social('Bob', { op: 'party_kick', bot: 'Cy' });
      check(state('Cy').party === null && state('Bob').party.size === 4, 'The leader removes a member');
      await w.social('Bob', { op: 'party_invite', bot: 'Fay' });
      await w.social('Fay', { op: 'party_accept', bot: 'Bob' });
      check(state('Fay').party.size === 5, 'A seat freed by a removal can be filled');
      await w.social('Bob', { op: 'party_leave' });
      check(state('Ann').party.leader === 'Ann' && state('Ann').party.size === 4, 'When the leader leaves the longest-standing member leads');
      // A dropped connection keeps its seat for a minute.
      await w.disconnect('Dee');
      await w.waitFor(() => state('Ann').party.members.find(m => m.name === 'Dee')?.online === false, 5000, 'Member offline');
      check(state('Ann').party.size === 4, 'A disconnected member keeps their party seat');
      await w.connect({ bot: 'Dee' });
      await w.waitFor(() => state('Dee').party?.size === 4 && state('Ann').party.members.find(m => m.name === 'Dee').online, 5000, 'Member back');
      check(state('Dee').party.leader === 'Ann', 'Reconnecting inside the minute returns to the same party');

      // Friends are saved; parties are not.
      await w.restart();
      for (const bot of names) await w.social(bot, { op: 'refresh' });
      check(state('Ann').friends[0]?.name === 'Bob' && state('Dee').friends[0]?.name === 'Eve', 'Friends survive restarting Rust');
      check(names.every(bot => state(bot).party === null), 'Parties are transient and end with a restart');
      const roster = await w.social('Ann', { op: 'who' });
      check(roster.online.length === 6 && roster.online.find(p => p.name === 'Bob').friend && roster.online.find(p => p.name === 'Ann').self, 'who lists every online player with their relationship to you');
      await w.social('Ann', { op: 'friend_remove', bot: 'Bob' });
      check(state('Ann').friends.length === 0 && state('Bob').friends.length === 0, 'Removing a friend removes both sides');
    },
  },

  consumables: {
    description: 'Food and potions through the real server: buying from the baker and the apothecary, a 100 HP meal over eight seconds that never stacks, an instant potion with one 60 second cooldown, refusals that keep the item, and the pack surviving a restart.',
    async run(w, check) {
      await w.connect({ bot: 'Diner', class: 'warrior' });
      const me = () => w.player('Diner');
      const owned = id => me().inventory.find(s => s.item === id)?.quantity || 0;
      const regen = () => me().buffs.find(b => b.kind === 'regen');
      // Send use_item and report what the server said back (null when it simply took effect).
      async function use(item) {
        const earlier = new Set(w.events);
        await w.action('Diner', { type: 'use_item', item });
        await w.advance(500);
        return w.events.find(e => !earlier.has(e) && e.bot === 'Diner' && e.type === 'error')?.text || null;
      }
      // The shop trips are not what this checks, so the character is placed beside each counter.
      await kit.setupCharacter(w, 'Diner', { gold: 100, teleportTo: { npc: 'baker' } });
      const bun = await kit.talkTo(w, 'Diner', 'baker', 'buy_traveler_stew');
      await w.waitFor(() => owned('traveler_stew') === 1, 3000, 'First stew');
      check(/Bought Traveler/.test(bun.notice) && bun.gold === 88 && me().gold === 88, 'The baker sells Traveler\'s Stew for 12 gold');
      await kit.talkTo(w, 'Diner', 'baker', 'buy_traveler_stew');
      await w.waitFor(() => owned('traveler_stew') === 2, 3000, 'Second stew');
      await w.advance(550);
      await w.action('Diner', { type: 'interact', npc: 'baker', offer: 'buy_health_potion' });
      await w.advance(600);
      check(owned('health_potion') === 0 && me().gold === 76, 'The baker does not sell potions and charges nothing for the request');
      await kit.teleport(w, 'Diner', { npc: 'apothecary' });
      await kit.talkTo(w, 'Diner', 'apothecary', 'buy_health_potion');
      await kit.talkTo(w, 'Diner', 'apothecary', 'buy_health_potion');
      await w.waitFor(() => owned('health_potion') === 2, 3000, 'Two potions');
      check(me().gold === 16, 'The apothecary sells Health Potions for 30 gold each');
      const poor = await kit.talkTo(w, 'Diner', 'apothecary', 'buy_health_potion');
      check(/need 30 gold/.test(poor.notice) && owned('health_potion') === 2 && me().gold === 16, 'Without 30 gold nothing is sold');

      // Nothing is wasted: full health, and things that are not food or potions.
      check(/full health/.test(await use('health_potion')) && owned('health_potion') === 2, 'A potion is refused at full health and kept');
      check(/cannot be used/.test(await use('slime_gel')) && /cannot be used/.test(await use('no_such_item')), 'Only food and potions can be used');

      // The potion heals at once and starts the one cooldown.
      await w.debug('Diner', { op: 'set_hp', hp: 1 });
      await w.waitFor(() => me().hp <= 3, 3000, 'Hurt');
      check(await use('health_potion') === null, 'A potion is accepted when hurt');
      await w.waitFor(() => owned('health_potion') === 1, 3000, 'Potion spent');
      check(me().hp >= 100 && me().hp <= 106, `The potion heals about 100 at once (${me().hp})`);
      check(me().potionCd > 55 && me().potionCd <= 60, `A 60 second cooldown starts (${me().potionCd})`);
      await w.debug('Diner', { op: 'set_hp', hp: 1 });
      await w.waitFor(() => me().hp <= 3, 3000, 'Hurt again');
      check(/recovering/.test(await use('health_potion')) && owned('health_potion') === 1 && me().hp < 30, 'A second potion waits for the cooldown and is kept');
      await w.debug('Diner', { op: 'reset_cooldowns' });
      check(await use('health_potion') === null && me().hp >= 100, 'Once the cooldown is cleared the next potion works');

      // The meal heals over eight seconds and does not stack; a potion may overlap it.
      await w.debug('Diner', { op: 'set_hp', hp: 1 });
      await w.waitFor(() => me().hp <= 3, 3000, 'Hurt for a meal');
      const ate = Date.now();
      check(await use('traveler_stew') === null, 'A meal is accepted when hurt');
      check(owned('traveler_stew') === 1 && regen()?.id === 'traveler_stew' && regen().time === 8, 'The stew is spent and a regen effect lasting eight seconds appears');
      check(me().hp < 40, `Nothing arrives at once (${me().hp})`);
      check(/still eating/.test(await use('traveler_stew')) && owned('traveler_stew') === 1 && me().buffs.filter(b => b.kind === 'regen').length === 1, 'A second meal is refused, kept, and does not stack');
      await w.waitFor(() => !regen(), 12000, 'Meal ends');
      const took = (Date.now() - ate) / 1000;
      check(took > 7 && took < 10.5, `The meal lasts about eight seconds (${took.toFixed(1)})`);
      check(me().hp >= 98, `All 100 HP arrived, with natural regeneration on top at most (${me().hp})`);
      await w.debug('Diner', { op: 'set_hp', hp: 1e9 });
      await w.waitFor(() => me().hp === me().maxHp, 3000, 'Full health');
      check(/full health/.test(await use('traveler_stew')) && owned('traveler_stew') === 1 && !regen(), 'Once the meal is over, a new one is judged on health and kept at full health');

      // Persistence: the pack and purse survive a restart.
      const stew = owned('traveler_stew'), gold = me().gold;
      await w.restart();
      await w.waitFor(() => w.player('Diner') && w.player('Diner').inventory.some(s => s.item === 'traveler_stew'), 10000, 'Resume');
      check(owned('traveler_stew') === stew && owned('health_potion') === 0 && me().gold === gold, 'Food, spent potions and gold persist across a restart');
      check(me().potionCd > 20 && me().potionCd <= 60 && me().buffs.length === 0, `The potion cooldown survives a restart but a meal does not (${me().potionCd})`);
    },
  },

  crags_quests: {
    description: 'Cinderwatch Camp: all twelve quests through real NPC offers, zone-local kill credit, prerequisites, rewards, repeatable contracts, healing, supplies and persisted progress.',
    async run(w, check) {
      const bot = 'Expedition';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 10, gold: 1000, items: Array.from({ length: 4 }, () => ({ item: 'linen_satchel' })), finishQuests: ['slime_patrol'] });
      await kit.teleport(w, bot, { npc: 'merchant' });
      await kit.talkTo(w, bot, 'merchant', 'quest:accept:meadow_bounty');
      await kit.teleport(w, bot, { npc: 'crags_scout' });
      await kit.talkTo(w, bot, 'crags_scout', 'quest:accept:crags_wisps');
      check(!quest(w, bot, 'crags_wisps'), 'The Crags hunt requires the camp introduction');
      await kit.talkTo(w, bot, 'crags_scout', 'quest:accept:crags_welcome');
      check(!quest(w, bot, 'crags_welcome'), 'The wrong NPC cannot offer another giver\'s quest');
      check(kit.describe('quests').quests.filter(q => q.zone === 1).length === 12, 'MCP describes all twelve Crags quests with their zone');
      for (const q of crags.quests) {
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${q.id}`);
        await w.waitFor(() => !!quest(w, bot, q.id));
        check(quest(w, bot, q.id)?.counts.every(n => n === 0), `${q.title}: accepted with fresh objectives`);
        const early = await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(/Complete the objectives/.test(early.notice), `${q.title}: premature reward refused`);
        for (const o of q.objectives) {
          if (o.kind === 'talk') {
            await kit.teleport(w, bot, { npc: o.target });
            await kit.talkTo(w, bot, o.target);
          } else {
            for (let i = 0; i < o.count; i++) {
              const enemy = w.snapshot.slimes.find(s => s.zone === 1 && (o.target === 'any' || s.kind === o.target));
              if (enemy.dead) await w.debug(bot, { op: 'respawn_enemy', id: enemy.id });
              await w.debug(bot, { op: 'kill_enemy', id: enemy.id });
            }
          }
        }
        await w.waitFor(() => quest(w, bot, q.id).counts.every((n, i) => n === q.objectives[i].count));
        check(quest(w, bot, 'meadow_bounty').counts[0] === 0, `${q.title}: Crags actions leave the meadow bounty unchanged`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        await w.waitFor(() => quest(w, bot, q.id).claimed);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + q.rewardXp, `${q.title}: exact XP and gold reward`);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && quest(w, bot, q.id).completions === 1, `${q.title}: duplicate turn-in pays nothing`);
      }
      for (const q of crags.quests.filter(q => q.repeatable)) {
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${q.id}`);
        await w.waitFor(() => !quest(w, bot, q.id).claimed);
        check(!quest(w, bot, q.id).claimed && quest(w, bot, q.id).completions === 1 && quest(w, bot, q.id).counts.every(n => n === 0), `${q.title}: repeat acceptance resets objectives and retains history`);
      }
      await kit.teleport(w, bot, { npc: 'crags_healer' });
      await w.debug(bot, { op: 'set_hp', hp: 1 });
      await kit.talkTo(w, bot, 'crags_healer', 'blessing');
      await w.waitFor(() => w.player(bot).hp === w.player(bot).maxHp);
      check(w.player(bot).hp === w.player(bot).maxHp, 'The camp healer restores all HP');
      await kit.talkTo(w, bot, 'crags_healer', 'buy_health_potion');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item === 'health_potion'));
      check(w.player(bot).inventory.some(i => i.item === 'health_potion'), 'The camp sells health potions');
      await kit.teleport(w, bot, { npc: 'crags_supplier' });
      await kit.talkTo(w, bot, 'crags_supplier', 'buy_traveler_stew');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item === 'traveler_stew'));
      check(w.player(bot).inventory.some(i => i.item === 'traveler_stew'), 'The quartermaster sells food');
      const history = JSON.stringify(w.player(bot).quests);
      await w.restart();
      check(w.player(bot).zone === 1 && JSON.stringify(w.player(bot).quests) === history, 'Every completion and restarted bounty survives a private server restart');
    },
  },
};

async function runScenario(name, world = new TestWorld()) {
  if (!Object.hasOwn(scenarios, name)) throw Error(`Unknown scenario: ${name}`);
  const checks = [];
  const started = Date.now();
  const check = (condition, message) => { assert.ok(condition, message); checks.push(message); };
  let result;
  try {
    if (scenarios[name].startLevel) world.startLevel = scenarios[name].startLevel;
    await world.start();
    await scenarios[name].run(world, check);
    check(!world.spacingFailure, 'Every observed snapshot preserves enemy spacing');
    result = { scenario: name, passed: true, checks };
  } catch (error) {
    result = { scenario: name, passed: false, checks, error: error.message };
  } finally {
    await world.stop();
  }
  result.durationMs = Date.now() - started;
  if (world.runDir) result.artifact = world.saveReport(result);
  return result;
}

module.exports = { scenarios, runScenario, walkTo };
