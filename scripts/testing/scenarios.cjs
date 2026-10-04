const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('./driver.cjs');
const { route } = require('./route.cjs');
const kit = require('./tools.cjs');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

const crags = map.zones[0];
const rime = map.zones[1];
const fen = map.zones[2];
const city = map.zones[3];
const wyrd = map.zones[5];
const sky = map.zones[6];
const deep = map.zones[7];
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
const DEFAULT_LEVELS = { green: 2, blue: 3, pink: 3, yellow: 4, beetle: 5, big: 6, wisp: 5, spider: 7, wraith: 8, golem: 10, cinderlord: 10, crab: 10, wolf: 12, yeti: 13, wyrm: 15, toad: 15, croc: 17, knight: 18, hydra: 20, gloomroot: 20, thrall: 19, archer: 19, acolyte: 20, gatewarden: 20, choir: 20, colossus: 21, hollowking: 21, boar: 21, crow: 23, troll: 25, weaver: 27, ram: 29, oakhorn: 25, hrungnir: 30, galehound: 30, prismgolem: 31, skyray: 32, einherjar: 33, thunderroc: 35, draugr: 35, angler: 36, moray: 37, siren: 38, shellback: 39, kraken: 40, hvitserk: 37, ghostmaw: 39 };
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

// A walking townsperson's place at world time `time`: the same arithmetic as the server's Npc::position_at.
function npcAt(n, time) {
  const r = n.route;
  if (!r || r.length < 2 || !(n.speed > 0)) return { x: n.x, y: n.y };
  const m = r.length, leg = i => Math.hypot(r[i][0] - r[(i + 1) % m][0], r[i][1] - r[(i + 1) % m][1]);
  let cycle = 0;
  for (let i = 0; i < m; i++) cycle += n.pause + leg(i) / n.speed;
  let t = (((time + n.phase) % cycle) + cycle) % cycle;
  for (let i = 0; i < m; i++) {
    if (t < n.pause) return { x: r[i][0], y: r[i][1] };
    t -= n.pause;
    const walk = leg(i) / n.speed;
    if (t < walk) { const a = r[i], b = r[(i + 1) % m], f = t / walk; return { x: a[0] + (b[0] - a[0]) * f, y: a[1] + (b[1] - a[1]) * f }; }
    t -= walk;
  }
  return { x: r[0][0], y: r[0][1] };
}

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
      await w.debug('Skillful', { op: 'set_resource', amount: 100 });
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
      const defaults = DEFAULT_LEVELS;
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
      check(away.length === 27 && away.every(s => s.zone === 1) && new Set(away.map(s => s.kind)).size === 5
        && ['wisp', 'spider', 'wraith', 'golem', 'cinderlord'].every(k => away.some(s => s.kind === k)), 'A Crags client receives exactly the 27 Crags monsters, five kinds, and nothing from the meadow');
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
      await w.debug('Gm', { op: 'set_resource', amount: 100 });
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
      check(kit.describe('quests').quests.filter(q => q.zone === 1).length === 14, 'MCP describes all fourteen Crags quests with their zone');
      for (const q of crags.quests.filter(q => !q.autoLevel)) {
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
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('health_potion')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('health_potion')), 'The camp sells health potions');
      await kit.teleport(w, bot, { npc: 'crags_supplier' });
      await kit.talkTo(w, bot, 'crags_supplier', 'buy_traveler_stew');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')), 'The quartermaster sells food');
      const history = JSON.stringify(w.player(bot).quests);
      await w.restart();
      check(w.player(bot).zone === 1 && JSON.stringify(w.player(bot).quests) === history, 'Every completion and restarted bounty survives a private server restart');
    },
  },
  rimeveil: {
    description: 'Walk through the Rimeveil Gate at the top of the Crags into the level 10-15 glacier, walk the whole ice spiral to the summit through all four ring gaps, fight a leveled Rime Crab, use both gates, and keep the zone across reconnect and restart.',
    async run(w, check) {
      const bot = 'Glacier';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 12 });
      const up = crags.portals.find(p => p.id === 'rimeveil_gate');
      check(up && up.to === 2 && crags.portals[0].id === 'meadow_gate', 'The Crags have a north gate to zone 2 after their meadow gate');
      // Staging only: stand a few steps below the gate; the crossing itself is a real walk between its two posts.
      await kit.teleport(w, bot, { zone: 1, x: up.x, y: up.y + 8 });
      await walkTo(w, bot, { x: up.x, y: up.y + 4 }, crags);
      check(w.player(bot).zone === 1, 'Still in the Crags in front of the gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 2, 15000, 'Step through the Rimeveil Gate');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: up.tx, y: up.ty };
      check(w.player(bot).zone === 2 && distance(w.player(bot), arrival) < 1, 'The server moves the walker to Rimeward Camp');
      const glacier = w.snapshot.slimes;
      check(glacier.length === 27 && glacier.every(s => s.zone === 2) && new Set(glacier.map(s => s.kind)).size === 4
        && ['crab', 'wolf', 'yeti', 'wyrm'].every(k => glacier.some(s => s.kind === k)), 'A glacier client receives exactly the 27 glacier monsters, four kinds, and nothing from the other zones');
      check(glacier.every(s => Math.abs(s.level - DEFAULT_LEVELS[s.kind]) <= 2 && s.level >= 8) && new Set(glacier.map(s => s.level - DEFAULT_LEVELS[s.kind])).size >= 3, 'Glacier levels sit within two of each default (10-15) and really vary');
      const hp = { crab: 900, wolf: 1000, yeti: 1900, wyrm: 2200 };
      check(glacier.every(s => s.maxHp === Math.round(hp[s.kind] * (1 + .12 * (s.level - DEFAULT_LEVELS[s.kind])))), 'Health follows each rolled level');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Rimeveil Glacier') && e.text.includes('10–15')), 'The player is told the recommended levels');
      // A second character in the Crags shares nothing with the glacier.
      await w.connect({ bot: 'Cragger', class: 'mage' });
      await kit.teleport(w, 'Cragger', { zone: 1, x: 48, y: 80 });
      check(w.player('Cragger').zone === 1 && w.player(bot).zone === 2, 'Players in the Crags and on the glacier are tracked separately');
      check(w.views.get(bot).slimes.every(s => s.zone === 2) && w.views.get('Cragger').slimes.every(s => s.zone === 1) && w.views.get(bot).players.length === 1,
        'Each client is sent only its own zone');
      check(JSON.stringify(w.snapshot.zonesSeen) === '[1,2]', 'The merged test view covers the two zones while a bot stands in each');
      await w.disconnect('Cragger');
      // The ice spiral: its route runs through all four ring gaps, and the walk to the summit really works.
      // The bowl's centre holds the gate to Gloamfen (64,50), so the walk ends just short of it.
      const center = { x: 64, y: 46 }, gaps = [{ x: 64, y: 100 }, { x: 64, y: 15 }, { x: 64, y: 78 }, { x: 64, y: 37 }];
      const path = route(rime, w.player(bot), center), from = { x: w.player(bot).x, y: w.player(bot).y };
      // The route is a few long straight legs, so measure how close each gap lies to a leg rather than to a waypoint.
      const legDistance = (g, a, b) => { const dx = b.x - a.x, dy = b.y - a.y, t = Math.max(0, Math.min(1, ((g.x - a.x) * dx + (g.y - a.y) * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(g.x - a.x - dx * t, g.y - a.y - dy * t); };
      check(gaps.every(g => path.some((p, i) => legDistance(g, i ? path[i - 1] : from, p) < 4.3)), 'The only route to the summit passes through the gaps of all four rings');
      let length = distance(w.player(bot), path[0]);
      path.forEach((p, i) => { if (i) length += distance(path[i - 1], p); });
      check(length > 3.5 * distance(w.player(bot), center), `The way in is a spiral: ${Math.round(length)} units of walking for ${Math.round(distance(w.player(bot), center))} units of distance`);
      for (const point of path) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .5, 30000, `Walk the spiral to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 2 && distance(w.player(bot), center) < 1.5, 'The bot reaches the summit bowl on foot');
      // Way back to the Crags: teleport to camp (staging), then a real walk through the Crags Gate and through the new gate again.
      const back = rime.portals[0];
      await kit.teleport(w, bot, { zone: 2, x: arrival.x, y: arrival.y });
      await w.action(bot, { type: 'move', x: back.x, y: back.y + 1.2 });
      await w.waitFor(() => w.player(bot).zone === 1, 15000, 'Step through the Crags Gate');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 1 && distance(w.player(bot), { x: back.tx, y: back.ty }) < 1, 'The Crags Gate arrives beside the Rimeveil Gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 2, 15000, 'Step through the Rimeveil Gate again');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 2 && distance(w.player(bot), arrival) < 1, 'The gate works again right after arriving, in both directions');
      // Fight a Rime Crab through normal target actions; test worlds are invulnerable.
      const crab = w.snapshot.slimes.filter(s => s.kind === 'crab' && !s.dead).sort((a, b) => distance(a, arrival) - distance(b, arrival))[0];
      await kit.teleport(w, bot, { enemy: crab.id });
      const before = { ...w.player(bot) };
      await w.action(bot, { type: 'target', id: crab.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === crab.id).dead, 90000, 'Defeat the crab');
      await w.action(bot, { type: 'stop' });
      const xp = enemyXp(crab.level), gold = Math.round(60 * (1 + .1 * (crab.level - 10)));
      check(w.player(bot).kills === before.kills + 1 && totalXp(w.player(bot)) === totalXp(before) + xp, `The kill pays the level-${crab.level} XP (${xp})`);
      const corpse = w.snapshot.slimes.find(s => s.id === crab.id);
      await w.action(bot, { type: 'move', x: corpse.x, y: corpse.y });
      await w.waitFor(() => w.player(bot).gold >= before.gold + gold && w.player(bot).inventory.some(i => i.item === 'rime_shell'), 15000, 'Collect glacier loot');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).gold === before.gold + gold, `Level-scaled gold (${gold}) and a Rime Shell drop are collected`);
      const where = { ...w.player(bot) };
      await w.disconnect(bot);
      await w.connect({ bot });
      check(w.player(bot).zone === 2 && distance(w.player(bot), where) < 1.2, 'Resume puts the character back on the glacier');
      await w.restart();
      check(w.player(bot).zone === 2 && w.player(bot).gold === where.gold, 'The glacier position and loot survive a Rust restart');
    },
  },
  rime_quests: {
    description: 'Rimeward Camp: all thirteen quests through real NPC offers, zone-local kill credit, prerequisites, rewards, repeatable contracts, healing, supplies and persisted progress.',
    async run(w, check) {
      const bot = 'Vanguard';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 15, gold: 1000, items: Array.from({ length: 4 }, () => ({ item: 'linen_satchel' })), finishQuests: ['slime_patrol', 'crags_welcome'] });
      await kit.teleport(w, bot, { npc: 'crags_supplier' });
      await kit.talkTo(w, bot, 'crags_supplier', 'quest:accept:crags_bounty');
      await w.waitFor(() => !!quest(w, bot, 'crags_bounty'), 5000, 'The Crags patrol appears');
      check(!!quest(w, bot, 'crags_bounty'), 'The Crags patrol is accepted before the glacier quests start');
      await kit.teleport(w, bot, { npc: 'rime_tracker' });
      await kit.talkTo(w, bot, 'rime_tracker', 'quest:accept:rime_crabs');
      check(!quest(w, bot, 'rime_crabs'), 'The glacier hunt requires the camp introduction');
      await kit.talkTo(w, bot, 'rime_tracker', 'quest:accept:rime_welcome');
      check(!quest(w, bot, 'rime_welcome'), 'The wrong NPC cannot offer another giver\'s quest');
      check(kit.describe('quests').quests.filter(q => q.zone === 2).length === 14 && rime.quests.length >= 10, 'MCP describes all fourteen glacier quests with their zone');
      for (const q of rime.quests.filter(q => !q.autoLevel)) {
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
              const enemy = w.snapshot.slimes.find(s => s.zone === 2 && (o.target === 'any' || s.kind === o.target));
              if (enemy.dead) await w.debug(bot, { op: 'respawn_enemy', id: enemy.id });
              await w.debug(bot, { op: 'kill_enemy', id: enemy.id });
            }
          }
        }
        await w.waitFor(() => quest(w, bot, q.id).counts.every((n, i) => n === q.objectives[i].count));
        check(quest(w, bot, 'crags_bounty').counts[0] === 0, `${q.title}: glacier actions leave the Crags patrol unchanged`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        await w.waitFor(() => quest(w, bot, q.id).claimed);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + q.rewardXp, `${q.title}: exact XP and gold reward`);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && quest(w, bot, q.id).completions === 1, `${q.title}: duplicate turn-in pays nothing`);
      }
      for (const q of rime.quests.filter(q => q.repeatable)) {
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${q.id}`);
        await w.waitFor(() => !quest(w, bot, q.id).claimed);
        check(!quest(w, bot, q.id).claimed && quest(w, bot, q.id).completions === 1 && quest(w, bot, q.id).counts.every(n => n === 0), `${q.title}: repeat acceptance resets objectives and retains history`);
      }
      await kit.teleport(w, bot, { npc: 'rime_healer' });
      await w.debug(bot, { op: 'set_hp', hp: 1 });
      await kit.talkTo(w, bot, 'rime_healer', 'blessing');
      await w.waitFor(() => w.player(bot).hp === w.player(bot).maxHp);
      check(w.player(bot).hp === w.player(bot).maxHp, 'The camp healer restores all HP');
      await kit.talkTo(w, bot, 'rime_healer', 'buy_health_potion');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('health_potion')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('health_potion')), 'The camp sells health potions');
      await kit.teleport(w, bot, { npc: 'rime_trader' });
      await kit.talkTo(w, bot, 'rime_trader', 'buy_traveler_stew');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')), 'The trader sells food');
      // Glacier loot sells at the trader (materials from the four new kinds).
      await w.debug(bot, { op: 'give_item', item: 'wyrm_scale', quantity: 2 });
      const gold = w.player(bot).gold;
      await kit.talkTo(w, bot, 'rime_trader', 'sell:materials');
      await w.waitFor(() => w.player(bot).gold > gold);
      check(w.player(bot).gold >= gold + 280, 'The trader buys Wyrm Scales at their catalog price');
      const history = JSON.stringify(w.player(bot).quests);
      await w.restart();
      check(w.player(bot).zone === 2 && JSON.stringify(w.player(bot).quests) === history, 'Every completion and restarted bounty survives a private server restart');
    },
  },
  gloamfen: {
    description: 'Walk through the summit gate at the heart of Rimeveil into the level 15-20 fen, walk the whole C round the lake (three ridge gaps and the causeway) to the hydra island, fight a leveled Fen Toad, use both gates, and keep the zone across reconnect and restart.',
    async run(w, check) {
      const bot = 'Fenwalker';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 17 });
      const up = rime.portals.find(p => p.id === 'fen_gate');
      check(up && up.to === 3 && rime.portals[0].id === 'crags_gate', 'The Rimeveil summit has a gate to zone 3 after its Crags gate');
      // Staging only: stand a few steps below the gate; the crossing itself is a real walk between its two posts.
      await kit.teleport(w, bot, { zone: 2, x: up.x, y: up.y + 8 });
      await walkTo(w, bot, { x: up.x, y: up.y + 4 }, rime);
      check(w.player(bot).zone === 2, 'Still on the glacier in front of the gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 3, 15000, 'Step through the Summit gate into Gloamfen');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: up.tx, y: up.ty };
      check(w.player(bot).zone === 3 && distance(w.player(bot), arrival) < 1, 'The server moves the walker into Lanternmere');
      const bogs = w.snapshot.slimes;
      check(bogs.length === 32 && bogs.every(s => s.zone === 3) && new Set(bogs.map(s => s.kind)).size === 5
        && ['toad', 'croc', 'knight', 'hydra', 'gloomroot'].every(k => bogs.some(s => s.kind === k)), 'A fen client receives exactly the 32 fen monsters, five kinds, and nothing from the other zones');
      check(bogs.every(s => Math.abs(s.level - DEFAULT_LEVELS[s.kind]) <= 2 && s.level >= 13) && new Set(bogs.map(s => s.level - DEFAULT_LEVELS[s.kind])).size >= 3, 'Fen levels sit within two of each default (15-20) and really vary');
      const hp = { toad: 2000, croc: 2800, knight: 3400, hydra: 5200, gloomroot: 90000 };
      check(bogs.every(s => s.maxHp === Math.round(hp[s.kind] * (1 + .12 * (s.level - DEFAULT_LEVELS[s.kind])))), 'Health follows each rolled level');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Gloamfen') && e.text.includes('15–20')), 'The player is told the recommended levels');
      // A second character on the glacier shares nothing with the fen.
      await w.connect({ bot: 'Icewalker', class: 'mage' });
      await kit.teleport(w, 'Icewalker', { zone: 2, x: 64, y: 110 });
      check(w.player('Icewalker').zone === 2 && w.player(bot).zone === 3, 'Players on the glacier and in the fen are tracked separately');
      check(w.views.get(bot).slimes.every(s => s.zone === 3) && w.views.get('Icewalker').slimes.every(s => s.zone === 2) && w.views.get(bot).players.length === 1,
        'Each client is sent only its own zone');
      check(JSON.stringify(w.snapshot.zonesSeen) === '[2,3]', 'The merged test view covers the two zones while a bot stands in each');
      await w.disconnect('Icewalker');
      // The C round the lake: the shortest route to the island passes the three ridge gaps and then the causeway mouth.
      const island = { x: 66, y: 76 }, gaps = [{ x: 18, y: 37 }, { x: 40, y: 93 }, { x: 92, y: 113 }, { x: 88.5, y: 76 }];
      const from = { x: w.player(bot).x, y: w.player(bot).y }, path = route(fen, from, island);
      const legDistance = (g, a, b) => { const dx = b.x - a.x, dy = b.y - a.y, t = Math.max(0, Math.min(1, ((g.x - a.x) * dx + (g.y - a.y) * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(g.x - a.x - dx * t, g.y - a.y - dy * t); };
      check(gaps.every(g => path.some((p, i) => legDistance(g, i ? path[i - 1] : from, p) < 4.3)), 'The only route to the island passes all three ridge gaps and the causeway mouth');
      const order = gaps.map(g => path.reduce((best, p, i) => legDistance(g, i ? path[i - 1] : from, p) < legDistance(g, best.a, best.b) ? { a: i ? path[i - 1] : from, b: p, i } : best, { a: from, b: path[0], i: 0 }).i);
      check(order.every((v, i) => !i || v >= order[i - 1]), 'They come in order: west gap, south gap, east gap, causeway');
      let length = distance(from, path[0]);
      path.forEach((p, i) => { if (i) length += distance(path[i - 1], p); });
      check(length > 2.2 * distance(from, island), `The way in goes round the lake: ${Math.round(length)} units of walking for ${Math.round(distance(from, island))} units of distance`);
      for (const point of path) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .5, 40000, `Walk the fen to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 3 && distance(w.player(bot), island) < 1.5, 'The bot reaches the hydra island on foot');
      // Way back: teleport to town (staging), then a real walk through the Summit gate and through the new gate again.
      const back = fen.portals[0];
      await kit.teleport(w, bot, { zone: 3, x: arrival.x, y: arrival.y });
      await w.action(bot, { type: 'move', x: back.x, y: back.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 2, 15000, 'Step through the Summit gate');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 2 && distance(w.player(bot), { x: back.tx, y: back.ty }) < 1, 'The Summit gate arrives beside the Gloamfen gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 3, 15000, 'Step through the fen gate again');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 3 && distance(w.player(bot), arrival) < 1, 'The gate works again right after arriving, in both directions');
      // Fight a Fen Toad through normal target actions; test worlds are invulnerable.
      // Stand west of a west-bank toad, on its own side of the thicket ridge and the lake (the default spot would be east of it).
      const toad = w.snapshot.slimes.filter(s => s.kind === 'toad' && !s.dead && s.x < 40 && s.y > 45 && s.y < 85).sort((a, b) => distance(a, arrival) - distance(b, arrival))[0];
      await kit.teleport(w, bot, { zone: 3, x: toad.x - 3, y: toad.y });
      const before = { ...w.player(bot) };
      await w.action(bot, { type: 'target', id: toad.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === toad.id).dead, 120000, 'Defeat the toad');
      await w.action(bot, { type: 'stop' });
      const xp = enemyXp(toad.level), gold = Math.round(165 * (1 + .1 * (toad.level - 15)));
      check(w.player(bot).kills === before.kills + 1 && totalXp(w.player(bot)) === totalXp(before) + xp, `The kill pays the level-${toad.level} XP (${xp})`);
      const corpse = w.snapshot.slimes.find(s => s.id === toad.id);
      await w.action(bot, { type: 'move', x: corpse.x, y: corpse.y });
      await w.waitFor(() => w.player(bot).gold >= before.gold + gold && w.player(bot).inventory.some(i => i.item === 'toad_gland'), 15000, 'Collect fen loot');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).gold === before.gold + gold, `Level-scaled gold (${gold}) and a Fen Toad Gland drop are collected`);
      const where = { ...w.player(bot) };
      await w.disconnect(bot);
      await w.connect({ bot });
      check(w.player(bot).zone === 3 && distance(w.player(bot), where) < 1.2, 'Resume puts the character back in the fen');
      await w.restart();
      check(w.player(bot).zone === 3 && w.player(bot).gold === where.gold, 'The fen position and loot survive a Rust restart');
    },
  },
  skaldholm: {
    description: 'Walk through the Skaldholm Gate in the Rimeveil summit into the walled city, cross the Great Gate to the plaza on foot, find no enemies, meet a walking townsperson where the server says they are, stop at the wall, use both gates, and keep the city across reconnect and restart.',
    async run(w, check) {
      const bot = 'Citywalker';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 14 });
      const up = rime.portals.find(p => p.id === 'city_gate');
      check(up && up.to === 4 && rime.portals[0].id === 'crags_gate' && rime.portals[1].id === 'fen_gate', 'The Rimeveil summit has a Skaldholm gate to zone 4 after the Crags and fen gates');
      check(map.zones.length === 6 && city.name === 'Skaldholm' && city.theme === 'city' && city.size === 160 && city.slimes.length === 0, 'Zone 4 is the 160-tile city and has no enemy spawns');
      await kit.teleport(w, bot, { zone: 2, x: up.x, y: up.y + 8 });
      await walkTo(w, bot, { x: up.x, y: up.y + 4 }, rime);
      check(w.player(bot).zone === 2, 'Still on the glacier in front of the gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 4, 15000, 'Step through the Skaldholm gate');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: up.tx, y: up.ty };
      check(w.player(bot).zone === 4 && distance(w.player(bot), arrival) < 1, 'The server moves the walker to the forecourt outside the Great Gate');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.views.get(bot).slimes.length === 0 && w.player(bot).zone === 4, 'The city client is sent no enemies at all');
      // The Great Gate is the only door: a real walk through it to the plaza, much longer than the straight line.
      const plaza = { x: 80, y: 68 }, from = { x: w.player(bot).x, y: w.player(bot).y };
      const path = route(city, from, plaza);
      for (const point of path) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .5, 40000, `Walk to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 4 && distance(w.player(bot), plaza) < 1.5 && w.player(bot).y < 100, 'The bot walks in through the Great Gate and up the avenue to the plaza');
      // The wall: walking at it from inside stops short of it.
      await kit.teleport(w, bot, { zone: 4, x: 30, y: 17 });
      await w.action(bot, { type: 'move', x: 30, y: 2 });
      await w.advance(3000);
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).y > 12.5 && w.player(bot).y < 16, `The north wall stops the walker at y ${w.player(bot).y.toFixed(1)}`);
      // A walking townsperson is where the world clock puts them: talk works there now and fails at the same spot later.
      const kid = city.npcs.find(n => n.id === 'city_watch_trade'), time = () => w.views.get(bot).time;
      const at = npcAt(kid, time() + 1);
      await kit.teleport(w, bot, { zone: 4, x: at.x, y: at.y + .8 });
      await w.advance(700);
      const here = npcAt(kid, time() + .3);
      check(distance(w.player(bot), here) < 2.8, 'Staged beside the walking watchman where the clock puts him');
      const earlier = new Set(w.events);
      await w.action(bot, { type: 'interact', npc: kid.id });
      const hello = await w.waitFor(() => w.events.find(e => !earlier.has(e) && e.bot === bot && (e.type === 'dialogue' || e.type === 'error')), 5000, 'Talk to the watchman');
      check(hello.type === 'dialogue' && hello.npc.id === kid.id, 'The server accepts talking to a walker at his current place');
      let far = null;
      for (let dt = 8; dt < 60; dt += 2) { const p = npcAt(kid, time() + dt); if (distance(p, here) > 12) { far = dt; break; } }
      check(far !== null, 'The watchman walks far from where he stood');
      await w.advance(far * 1000);
      await w.advance(600);
      const earlier2 = new Set(w.events);
      await w.action(bot, { type: 'interact', npc: kid.id });
      const gone = await w.waitFor(() => w.events.find(e => !earlier2.has(e) && e.bot === bot && (e.type === 'dialogue' || e.type === 'error')), 5000, 'Talk to the empty spot');
      check(gone.type === 'error' && /closer/i.test(gone.text), 'Standing where the watchman was, a while later, the server says to walk closer');
      // Both gates, twice, from the forecourt.
      const back = city.portals[0];
      check(back.id === 'glacier_gate' && back.to === 2 && back.tx === up.x, 'The Glacier Gate leads back beside the Skaldholm Gate');
      await kit.teleport(w, bot, { zone: 4, x: arrival.x, y: arrival.y });
      await w.action(bot, { type: 'move', x: back.x, y: back.y + 1.2 });
      await w.waitFor(() => w.player(bot).zone === 2, 15000, 'Step through the Glacier Gate');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 2 && distance(w.player(bot), { x: back.tx, y: back.ty }) < 1, 'The Glacier Gate arrives beside the Skaldholm Gate');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 4, 15000, 'Step through the city gate again');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 4 && distance(w.player(bot), arrival) < 1, 'The gate works again right after arriving, in both directions');
      // The city survives a reconnect and a Rust restart.
      await kit.teleport(w, bot, { zone: 4, x: 80, y: 120 });
      const where = { ...w.player(bot) };
      await w.disconnect(bot);
      await w.connect({ bot });
      check(w.player(bot).zone === 4 && distance(w.player(bot), where) < 1.2, 'Resume puts the character back in Skaldholm');
      await w.restart();
      check(w.player(bot).zone === 4 && distance(w.player(bot), where) < 1.5, 'The city position survives a Rust restart');
    },
  },
  skaldholm_quests: {
    description: 'Skaldholm: all eleven quests through real NPC offers, including errands that name people in the four earlier maps and hand-ins of materials from them: prerequisites, bag counting, item removal, exact rewards, the repeatable order and persisted progress.',
    async run(w, check) {
      const bot = 'Errandboy';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 20, gold: 0, items: Array.from({ length: 4 }, () => ({ item: 'linen_satchel' })) });
      const q = id => quest(w, bot, id), bag = item => (w.player(bot).inventory.find(i => i.item === item) || {}).quantity || 0;
      check(kit.describe('quests').quests.filter(x => x.zone === 4).length === 12, 'MCP describes all twelve city quests with their zone');
      await kit.teleport(w, bot, { npc: 'city_herald' });
      await kit.talkTo(w, bot, 'city_herald', 'quest:accept:city_seals');
      check(!q('city_seals'), 'The errands need the introduction first');
      await kit.teleport(w, bot, { npc: 'city_alchemist' });
      await kit.talkTo(w, bot, 'city_alchemist', 'quest:accept:city_gel');
      check(!q('city_gel'), 'Another giver cannot hand out a quest, and a locked one is refused');
      // Materials already in the bag count the moment a hand-in quest is accepted, and selling them takes progress back.
      await w.debug(bot, { op: 'give_item', item: 'slime_gel', quantity: 3 });
      for (const x of city.quests.filter(x => !x.autoLevel)) {
        await kit.teleport(w, bot, { npc: x.npc });
        if (x.requires && !(q(x.requires)?.claimed)) throw Error(`Order: ${x.id} needs ${x.requires}`);
        await kit.talkTo(w, bot, x.npc, `quest:accept:${x.id}`);
        await w.waitFor(() => !!q(x.id));
        const bring = x.objectives.filter(o => o.kind === 'bring');
        check(q(x.id).counts.every((n, k) => x.objectives[k].kind === 'bring' ? n <= x.objectives[k].count : n === 0), `${x.title}: accepted with fresh talk objectives`);
        const early = await kit.talkTo(w, bot, x.npc, `quest:claim:${x.id}`);
        check(/Complete the objectives/.test(early.notice), `${x.title}: premature reward refused`);
        for (const o of x.objectives) {
          if (o.kind === 'talk') {
            const zone = [map, ...map.zones].findIndex(a => (a.npcs || []).some(n => n.id === o.target));
            await kit.teleport(w, bot, { npc: o.target });
            await w.waitFor(() => w.player(bot).zone === zone);
            await kit.talkTo(w, bot, o.target);
          } else {
            const need = o.count - Math.min(bag(o.target), o.count);
            if (need > 0) await w.debug(bot, { op: 'give_item', item: o.target, quantity: need });
          }
        }
        await w.waitFor(() => q(x.id).counts.every((n, k) => n === x.objectives[k].count), 10000, `${x.title}: objectives fill`);
        check(bring.every(o => bag(o.target) >= o.count), `${x.title}: the bag holds every hand-in item`);
        await kit.teleport(w, bot, { npc: x.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)), bag: Object.fromEntries(bring.map(o => [o.target, bag(o.target)])) };
        await kit.talkTo(w, bot, x.npc, `quest:claim:${x.id}`);
        await w.waitFor(() => q(x.id).claimed);
        check(w.player(bot).gold === before.gold + x.rewardGold && totalXp(w.player(bot)) === before.xp + x.rewardXp, `${x.title}: exact XP and gold reward`);
        check(bring.every(o => bag(o.target) === before.bag[o.target] - o.count), `${x.title}: exactly the handed-in items leave the bag`);
        await kit.talkTo(w, bot, x.npc, `quest:claim:${x.id}`);
        check(w.player(bot).gold === before.gold + x.rewardGold && q(x.id).completions === 1, `${x.title}: duplicate turn-in pays nothing`);
      }
      // The repeatable standing order pays again after another hand-in.
      const standing = city.quests.find(x => x.repeatable);
      await kit.teleport(w, bot, { npc: standing.npc });
      await kit.talkTo(w, bot, standing.npc, `quest:accept:${standing.id}`);
      await w.waitFor(() => !q(standing.id).claimed);
      check(q(standing.id).completions === 1 && q(standing.id).counts.every(n => n === 0 || n > 0), `${standing.title}: repeat acceptance keeps its history`);
      for (const o of standing.objectives) await w.debug(bot, { op: 'give_item', item: o.target, quantity: o.count });
      await w.waitFor(() => q(standing.id).counts.every((n, k) => n === standing.objectives[k].count));
      const gold = w.player(bot).gold;
      await kit.talkTo(w, bot, standing.npc, `quest:claim:${standing.id}`);
      await w.waitFor(() => q(standing.id).completions === 2);
      check(w.player(bot).gold === gold + standing.rewardGold, `${standing.title}: the second hand-in pays again`);
      // Selling takes hand-in progress back.
      await kit.talkTo(w, bot, standing.npc, `quest:accept:${standing.id}`);
      await w.debug(bot, { op: 'give_item', item: 'magma_fang', quantity: 3 });
      await w.waitFor(() => q(standing.id).counts[0] === 3);
      await kit.teleport(w, bot, { npc: 'city_guildmaster' });
      await kit.talkTo(w, bot, 'city_guildmaster', 'sell:materials');
      await w.waitFor(() => q(standing.id).counts[0] === 0);
      check(q(standing.id).counts.every(n => n === 0), 'Selling the materials takes the hand-in progress back');
      await kit.teleport(w, bot, { npc: 'city_healer' });
      await w.debug(bot, { op: 'set_hp', hp: 1 });
      await kit.talkTo(w, bot, 'city_healer', 'blessing');
      await w.waitFor(() => w.player(bot).hp === w.player(bot).maxHp);
      check(w.player(bot).hp === w.player(bot).maxHp, 'The cathedral healer restores all HP');
      const history = JSON.stringify(w.player(bot).quests);
      await w.restart();
      check(w.player(bot).zone === 4 && JSON.stringify(w.player(bot).quests) === history, 'Every completion survives a private server restart');
    },
  },
  fen_quests: {
    description: 'Lanternmere: all sixteen quests through real NPC offers, zone-local kill credit, prerequisites, rewards, repeatable contracts, healing, supplies and persisted progress.',
    async run(w, check) {
      const bot = 'Reeveguest';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 20, gold: 1000, items: Array.from({ length: 4 }, () => ({ item: 'linen_satchel' })), finishQuests: ['slime_patrol', 'crags_welcome', 'rime_welcome'] });
      await kit.teleport(w, bot, { npc: 'crags_supplier' });
      await kit.talkTo(w, bot, 'crags_supplier', 'quest:accept:crags_bounty');
      await kit.teleport(w, bot, { npc: 'rime_trader' });
      await kit.talkTo(w, bot, 'rime_trader', 'quest:accept:rime_bounty');
      await w.waitFor(() => quest(w, bot, 'crags_bounty') && quest(w, bot, 'rime_bounty'), 5000, 'Both older patrols appear');
      check(!!quest(w, bot, 'crags_bounty') && !!quest(w, bot, 'rime_bounty'), 'The Crags and glacier patrols are accepted before the fen quests start');
      await kit.teleport(w, bot, { npc: 'fen_ranger' });
      await kit.talkTo(w, bot, 'fen_ranger', 'quest:accept:fen_toads');
      check(!quest(w, bot, 'fen_toads'), 'The fen hunt requires the town introduction');
      await kit.talkTo(w, bot, 'fen_ranger', 'quest:accept:fen_welcome');
      check(!quest(w, bot, 'fen_welcome'), 'The wrong NPC cannot offer another giver\'s quest');
      check(kit.describe('quests').quests.filter(q => q.zone === 3).length === 18 && fen.quests.length >= 10, 'MCP describes all eighteen fen quests with their zone');
      for (const q of fen.quests.filter(q => !q.autoLevel)) {
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
              const enemy = w.snapshot.slimes.find(s => s.zone === 3 && (o.target === 'any' || s.kind === o.target));
              if (enemy.dead) await w.debug(bot, { op: 'respawn_enemy', id: enemy.id });
              await w.debug(bot, { op: 'kill_enemy', id: enemy.id });
            }
          }
        }
        await w.waitFor(() => quest(w, bot, q.id).counts.every((n, i) => n === q.objectives[i].count));
        check(quest(w, bot, 'crags_bounty').counts[0] === 0 && quest(w, bot, 'rime_bounty').counts[0] === 0, `${q.title}: fen actions leave the older patrols unchanged`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        await w.waitFor(() => quest(w, bot, q.id).claimed);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + q.rewardXp, `${q.title}: exact XP and gold reward`);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && quest(w, bot, q.id).completions === 1, `${q.title}: duplicate turn-in pays nothing`);
      }
      for (const q of fen.quests.filter(q => q.repeatable)) {
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${q.id}`);
        await w.waitFor(() => !quest(w, bot, q.id).claimed);
        check(!quest(w, bot, q.id).claimed && quest(w, bot, q.id).completions === 1 && quest(w, bot, q.id).counts.every(n => n === 0), `${q.title}: repeat acceptance resets objectives and retains history`);
      }
      await kit.teleport(w, bot, { npc: 'fen_healer' });
      await w.debug(bot, { op: 'set_hp', hp: 1 });
      await kit.talkTo(w, bot, 'fen_healer', 'blessing');
      await w.waitFor(() => w.player(bot).hp === w.player(bot).maxHp);
      check(w.player(bot).hp === w.player(bot).maxHp, 'The town healer restores all HP');
      await kit.talkTo(w, bot, 'fen_healer', 'buy_health_potion');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('health_potion')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('health_potion')), 'The town sells health potions');
      await kit.teleport(w, bot, { npc: 'fen_trader' });
      await kit.talkTo(w, bot, 'fen_trader', 'buy_traveler_stew');
      await w.waitFor(() => w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')));
      check(w.player(bot).inventory.some(i => i.item.startsWith('traveler_stew')), 'The trader sells food');
      // Fen loot sells at the trader (materials from the four new kinds).
      await w.debug(bot, { op: 'give_item', item: 'hydra_fang', quantity: 2 });
      const gold = w.player(bot).gold;
      await kit.talkTo(w, bot, 'fen_trader', 'sell:materials');
      await w.waitFor(() => w.player(bot).gold > gold);
      check(w.player(bot).gold >= gold + 460, 'The trader buys Hydra Fangs at their catalog price');
      const history = JSON.stringify(w.player(bot).quests);
      await w.restart();
      check(w.player(bot).zone === 3 && JSON.stringify(w.player(bot).quests) === history, 'Every completion and restarted bounty survives a private server restart');
    },
  },
  gender: {
    description: 'Every class in a male and a female body: the choice is stored by the server, shown to the other players in their snapshots, kept through a restart and resume, and an unknown value is refused.',
    startLevel: 1,
    async run(w, check) {
      const classes = ['warrior', 'mage', 'assassin', 'priest', 'hunter'];
      for (const cls of classes) {
        await w.connect({ bot: 'F' + cls, class: cls, gender: 'female' });
        await w.connect({ bot: 'M' + cls, class: cls });
      }
      await w.waitFor(() => classes.every(cls => w.player('F' + cls) && w.player('M' + cls)), 20000, 'All ten characters join');
      check(classes.every(cls => w.player('F' + cls).look.gender === 'female' && w.player('F' + cls).look.class === cls), 'Each class can be created as a woman, and the server says so');
      check(classes.every(cls => w.player('M' + cls).look.gender === 'male'), 'Leaving the choice alone gives a man');
      const seen = w.snapshot.players;
      check(classes.every(cls => seen.find(p => p.look.name === 'F' + cls)?.look.gender === 'female' && seen.find(p => p.look.name === 'M' + cls)?.look.gender === 'male'), 'Every player\u2019s snapshot carries the others\u2019 body type');
      check(classes.every(cls => w.player('F' + cls).look[cls + 'Armor'] === w.player('M' + cls).look[cls + 'Armor'] && w.player('F' + cls).maxHp === w.player('M' + cls).maxHp), 'Starter gear and health do not depend on the body');
      await w.restart();
      await w.waitFor(() => classes.every(cls => w.player('F' + cls)?.look.gender === 'female' && w.player('M' + cls)?.look.gender === 'male'), 20000, 'Characters resume');
      check(classes.every(cls => w.player('F' + cls).look.class === cls && w.player('M' + cls).look.class === cls), 'Both bodies survive a server restart and resume');
      // A look with an unknown body type is refused outright, not stored as male.
      const refused = await new Promise(resolve => {
        const ws = new (require('ws'))(w.url.replace(/^http/, 'ws') + 'ws', { origin: new URL(w.url).origin });
        let outcome = 'silent';
        ws.on('open', () => ws.send(JSON.stringify({ type: 'join', version: 1, token: null, look: { name: 'Odd', class: 'mage', gender: 'other' } })));
        ws.on('message', data => { const packet = JSON.parse(data.toString()); if (packet.type === 'welcome') outcome = 'welcome'; });
        ws.on('close', () => resolve(outcome));
        setTimeout(() => { ws.close(); resolve(outcome); }, 3000);
      });
      check(refused !== 'welcome', 'A join with an unknown body type is not welcomed');
    },
  },
  priest: {
    description: 'The Priest, a healer that also fights alone: Mend and Prayer heal party members and nobody else, a heal with nobody hurt fizzles for free, Blessing and Holy Nova reach the party in range, and Smite damages a real enemy.',
    startLevel: 20,
    async run(w, check) {
      await w.connect({ bot: 'Pia', class: 'priest' });
      await w.connect({ bot: 'Tank', class: 'warrior' });
      await w.connect({ bot: 'Sam', class: 'mage' });
      const pia = () => w.player('Pia'), hp = bot => w.player(bot).hp;
      check(pia().look.class === 'priest' && pia().level === 20 && pia().maxHp === 100 + 19 * 20, 'The priest joins as a level-20 priest with 100 base health');
      check(pia().look.priestArmor === 'pilgrim' && pia().look.priestWeapon === 'mace', 'It starts in Pilgrim robes with an Oak mace');
      const learned = skillCatalog.filter(k => k.class === 'priest').map(k => k.level);
      check(learned.length === 10 && learned.join() === '2,4,6,8,10,12,14,16,18,20', 'A priest learns one skill at every even level up to 20');
      await w.social('Pia', { op: 'party_invite', bot: 'Tank' });
      await w.social('Tank', { op: 'party_accept', bot: 'Pia' });
      check(w.socialState('Pia').party?.size === 2, 'The priest and the warrior form a party');
      const errors = () => w.events.filter(e => e.bot === 'Pia' && e.type === 'error').map(e => e.text);
      // Nobody is hurt: the heal is refused and costs no cooldown.
      await cast(w, 'Pia', 'mend');
      await w.waitFor(() => errors().includes('Nobody nearby needs healing.'), 5000, 'Nobody to heal');
      check(!pia().skillCd.mend, 'A heal with nobody hurt spends no cooldown');
      // The party member is hurt, and so is a stranger: only the party member is healed.
      await w.debug('Tank', { op: 'set_hp', hp: 60 });
      await w.debug('Sam', { op: 'set_hp', hp: 30 });
      await w.advance(300);
      await cast(w, 'Pia', 'mend');
      const told = await w.waitFor(() => w.events.find(e => e.bot === 'Tank' && e.kind === 'healed'), 5000, 'Healed event');
      check(told.actor === w.player('Tank').id && told.value > 60 && told.from === pia().id, 'The healed player is told how much, and by whom');
      await w.waitFor(() => hp('Tank') > 100, 5000, 'Mend lands in the snapshot');
      check(hp('Tank') > 100, 'Mend heals the wounded party member (' + Math.round(hp('Tank')) + ')');
      check(Math.abs(hp('Sam') - 30) < 2, 'A stranger in the party\'s range is never healed');
      check(pia().skillCd.mend > 3 && pia().skillCd.mend <= 3.5, 'Mend starts its listed cooldown');
      // A prayer heals every wounded party member, the priest included.
      await w.debug('Tank', { op: 'set_hp', hp: 40 });
      await w.debug('Pia', { op: 'set_hp', hp: 40 });
      await w.advance(300);
      await cast(w, 'Pia', 'prayer');
      await w.waitFor(() => hp('Tank') > 100 && hp('Pia') > 100, 5000, 'Prayer of Healing');
      check(hp('Tank') > 100 && hp('Pia') > 100, 'Prayer of Healing heals the whole party');
      // A blessing and a nova reach the party, never the stranger.
      await cast(w, 'Pia', 'blessing');
      await w.waitFor(() => w.player('Tank').buffs.some(b => b.id === 'blessing'), 5000, 'Blessing');
      check(pia().buffs.some(b => b.id === 'blessing') && !w.player('Sam').buffs.some(b => b.id === 'blessing'), 'Blessing of Might buffs the priest and the party, not a stranger');
      await w.debug('Tank', { op: 'set_hp', hp: 50 });
      await w.advance(300);
      await cast(w, 'Pia', 'holynova');
      await w.waitFor(() => hp('Tank') > 100, 5000, 'Holy Nova heal');
      check(hp('Tank') > 100, 'Holy Nova heals the party while it burns enemies');
      // Alone on the field the priest fights: Smite and the mace.
      // This check requires a landed hit, so train the normal accuracy cap instead of relying on a random roll.
      for (let i = 0; i < 20; i++) await w.action('Pia', { type: 'allocate_stat', stat: 'accuracy' });
      await w.waitFor(() => pia().hitChance === 1);
      const front = await approach(w, 'Pia', 'green', 4);
      const before = { ...front() };
      await cast(w, 'Pia', 'smite', front());
      await w.waitFor(() => lost(before, front()), 8000, 'Smite');
      check(lost(before, front()), 'Smite damages the nearest enemy');
      await w.action('Pia', { type: 'target', id: before.id });
      await w.waitFor(() => !front() || front().dead, 40000, 'The priest defeats it with the mace');
      check(front().dead, 'The mace and holy light together defeat an enemy without any help');
    },
  },
  hunter: {
    description: 'The Hunter, a ranged class with layered gear: it starts in Scout gear with its head, shoulder and glove pieces unworn in the bag, wearing the pieces changes the look and taking them off clears it, another class\'s piece is refused, and arrows (Power Shot and the plain shot) damage a real enemy from beyond melee range.',
    startLevel: 20,
    async run(w, check) {
      await w.connect({ bot: 'Hana', class: 'hunter' });
      const hana = () => w.player('Hana');
      check(hana().look.class === 'hunter' && hana().level === 20 && hana().maxHp === 95 + 19 * 20, 'The hunter joins as a level-20 hunter with 95 base health');
      check(hana().look.hunterArmor === 'scout' && hana().look.hunterWeapon === 'shortbow', 'It starts in the Scout\u2019s Jerkin with a Hunter\u2019s Shortbow');
      check(hana().look.head === 'none' && hana().look.shoulders === 'none' && hana().look.gloves === 'none', 'The head, shoulder and glove layers start off');
      const pieces = ['hunter_headgear_scout', 'hunter_shoulders_scout', 'hunter_gloves_scout'];
      check(pieces.every(id => hana().inventory.some(s => s.item === id)), 'The three starter pieces are in the bag, unworn');
      const learned = skillCatalog.filter(k => k.class === 'hunter').map(k => k.level);
      check(learned.length === 10 && learned.join() === '2,4,6,8,10,12,14,16,18,20', 'A hunter learns one skill at every even level up to 20');
      await w.action('Hana', { type: 'equip', slots: { headgear: pieces[0], shoulders: pieces[1], gloves: pieces[2] } });
      await w.waitFor(() => hana().look.head === 'scout' && hana().look.shoulders === 'scout' && hana().look.gloves === 'scout', 5000, 'Pieces worn');
      check(true, 'Wearing the three pieces switches on the head, shoulder and glove layers');
      await w.debug('Hana', { op: 'give_item', item: 'mage_headgear_runic', quantity: 1 });
      const errors = () => w.events.filter(e => e.bot === 'Hana' && e.type === 'error').length;
      const before = errors();
      await w.action('Hana', { type: 'equip', slots: { headgear: 'mage_headgear_runic' } });
      await w.waitFor(() => errors() > before, 5000, 'Another class\u2019s piece is refused');
      check(hana().look.head === 'scout', 'Another class\u2019s piece is refused and the layer stays');
      await w.action('Hana', { type: 'equip', slots: { headgear: 'none', gloves: 'none' } });
      await w.waitFor(() => hana().look.head === 'none' && hana().look.gloves === 'none', 5000, 'Pieces removed');
      check(hana().look.shoulders === 'scout', 'Taking pieces off clears only their layers');
      await w.restart();
      check(hana().look.shoulders === 'scout' && hana().look.head === 'none', 'The worn layers survive a server restart');
      // Arrows: the plain shot and Power Shot reach an enemy from beyond any melee reach.
      const front = await approach(w, 'Hana', 'green', 6.5);
      const start = { ...front() };
      check(distance(hana(), start) > 3, 'The hunter stands well outside sword range');
      // An arrow can miss a slime that wanders off its line, so the shot is retried (re-aimed) once its cooldown ends.
      let struck = false;
      for (let attempt = 0; attempt < 4 && !struck; attempt++) {
        await w.waitFor(() => !hana().skillCd.powershot, 6000, 'Power Shot ready');
        await cast(w, 'Hana', 'powershot', front());
        struck = await w.waitFor(() => lost(start, front()), 3000, 'Power Shot').then(() => true, () => false);
      }
      check(struck && lost(start, front()), 'Power Shot damages an enemy from a distance');
      await w.action('Hana', { type: 'target', id: start.id });
      await w.waitFor(() => !front() || front().dead, 40000, 'The hunter defeats it with arrows');
      check(front().dead, 'Arrows alone defeat an enemy');
    },
  },
  cinderlord: {
    description: 'Two level-10 warriors fight the Cinderlord with real damage, skills and potions, both earn quest credit and guaranteed green gear, then equip it and retain the reward after restart.',
    startLevel: 10, godMode: false, levelSpread: 0,
    async run(w, check) {
      const bots = ['Ember', 'Cinder'], qid = 'crags_cinderlord', reward = 'necklace_moonstone_l10_green';
      for (const bot of bots) {
        await w.connect({ bot, class: 'warrior' });
        await kit.setupCharacter(w, bot, { items: [{ item: 'health_potion' }], teleportTo: { npc: 'crags_captain' } });
        for (let i = 0; i < 27; i++) await w.action(bot, { type: 'allocate_stat', stat: i < 20 ? 'strength' : 'accuracy' });
        await w.waitFor(() => w.player(bot).statPoints === 0, 5000, 'All training spent');
        await kit.talkTo(w, bot, 'crags_captain', `quest:accept:${qid}`);
        await w.waitFor(() => !!quest(w, bot, qid));
        check(quest(w, bot, qid).counts[0] === 0, `${bot} accepts the elite quest with no kill credit`);
      }
      const elite = w.snapshot.slimes.find(s => s.kind === 'cinderlord');
      check(elite.elite && elite.level === 10 && elite.maxHp === 2400 && elite.zone === 1, 'Exactly the new level-10 elite is present with authoritative 2400 HP');
      for (const [i, bot] of bots.entries()) await kit.teleport(w, bot, { zone: 1, x: elite.x + (i ? 2 : -2), y: elite.y });
      for (const bot of bots) await w.action(bot, { type: 'target', id: elite.id });
      const current = () => w.snapshot.slimes.find(s => s.id === elite.id), began = Date.now();
      while (!current().dead && Date.now() - began < 60000) {
        for (const bot of bots) {
          const p = w.player(bot);
          if (p.dead) throw Error(`${bot} died during the two-player fight`);
          for (const id of ['battlecry', 'shieldwall', 'cleave', 'whirlwind']) {
            if (!p.skillCd[id]) await w.action(bot, { type: 'skill', id, ...aimAt(w, bot, current()) });
          }
          if (p.hp <= p.maxHp - 100 && !p.potionCd && p.inventory.some(s => s.item === 'health_potion')) await w.action(bot, { type: 'use_item', item: 'health_potion' });
        }
        await w.advance(200);
      }
      check(current().dead, 'Two warriors defeat the elite through ordinary combat with god mode disabled');
      for (const bot of bots) {
        await w.action(bot, { type: 'stop' });
        await w.waitFor(() => quest(w, bot, qid).counts[0] === 1);
        check(w.player(bot).hp > 0 && w.player(bot).hp < w.player(bot).maxHp, `${bot} survives and took real damage`);
        check(w.events.some(e => e.type === 'event' && e.kind === 'hit' && e.actor === w.player(bot).id), `${bot} personally damaged the Cinderlord`);
        check(quest(w, bot, qid).counts[0] === 1, `${bot} earns shared elite quest credit`);
      }
      check(bots.reduce((n, bot) => n + w.player(bot).kills, 0) === 1, 'The ordinary kill reward still has only one owner');
      for (const bot of bots) {
        await kit.teleport(w, bot, { npc: 'crags_captain' });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        await kit.talkTo(w, bot, 'crags_captain', `quest:claim:${qid}`);
        await w.waitFor(() => quest(w, bot, qid).claimed && w.player(bot).inventory.some(s => s.item === reward));
        check(w.player(bot).gold === before.gold + 200 && totalXp(w.player(bot)) === before.xp + levelXp[9] / 10, `${bot} gets exact quest XP and gold`);
        check(w.player(bot).inventory.find(s => s.item === reward).quantity === 1 && kit.items.find(i => i.id === reward).rarity === 'uncommon', `${bot} gets one guaranteed green necklace`);
        await kit.talkTo(w, bot, 'crags_captain', `quest:claim:${qid}`);
        check(w.player(bot).gold === before.gold + 200 && w.player(bot).inventory.find(s => s.item === reward).quantity === 1, `${bot} cannot claim twice`);
        await w.action(bot, { type: 'equip', slots: { necklace: reward } });
        await w.waitFor(() => w.player(bot).equipment.necklace === reward);
        check(true, `${bot} can equip the level-10 reward`);
      }
      await w.restart();
      check(bots.every(bot => quest(w, bot, qid).claimed && w.player(bot).equipment.necklace === reward && w.player(bot).inventory.find(s => s.item === reward).quantity === 1), 'Both quest completions and worn rewards survive a private server restart');
    },
  },
  gloomroot: {
    description: 'Five level-20 warriors take the Gloamfen elite quest, every one of them damages the Gloomroot Colossus, all five earn shared kill credit and a guaranteed blue ring, then equip it and keep it after a restart. The combat balance is a Rust test.',
    startLevel: 20, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bots = ['Root1', 'Root2', 'Root3', 'Root4', 'Root5'], qid = 'fen_gloomroot', reward = 'accessory_amber_l20_blue';
      for (const bot of bots) {
        await w.connect({ bot, class: 'warrior' });
        await kit.setupCharacter(w, bot, { items: [{ item: 'health_potion' }] });
        await w.debug(bot, { op: 'quest', id: 'fen_hydra', action: 'finish' });
        await kit.teleport(w, bot, { zone: 3, x: 64, y: 12 });
        await kit.teleport(w, bot, { npc: 'fen_reeve' });
        await kit.talkTo(w, bot, 'fen_reeve', `quest:accept:${qid}`);
        await w.waitFor(() => !!quest(w, bot, qid));
        check(quest(w, bot, qid).counts[0] === 0, `${bot} accepts the five-player quest with no kill credit`);
      }
      const q = kit.describe('quests').quests.find(q => q.id === qid);
      check(q.group === true && q.recommendedPlayers === 5 && q.level === 20 && q.rewardItem === reward, 'The quest is a shared five-player level-20 quest with a guaranteed item');
      check(kit.items.find(i => i.id === reward).rarity === 'rare' && !kit.items.find(i => i.id === reward).class, 'The reward is a blue piece every class can wear');
      const elite = w.snapshot.slimes.find(s => s.kind === 'gloomroot');
      check(elite.elite && elite.level === 20 && elite.maxHp === 90000 && elite.zone === 3, 'Exactly the level-20 elite is present in Gloamfen with authoritative 90000 HP');
      const place = [[-3, -3], [3, -3], [-3, 3], [3, 3], [0, 5]];
      for (const [i, bot] of bots.entries()) await kit.teleport(w, bot, { zone: 3, x: elite.x + place[i][0], y: elite.y + place[i][1] });
      for (const bot of bots) await w.action(bot, { type: 'target', id: elite.id });
      const current = () => w.snapshot.slimes.find(s => s.id === elite.id);
      for (const bot of bots) {
        for (let tries = 0; tries < 20 && !w.events.some(e => e.type === 'event' && e.kind === 'hit' && e.actor === w.player(bot).id); tries++) {
          await w.action(bot, { type: 'skill', id: 'cleave', ...aimAt(w, bot, current()) });
          await w.advance(300);
        }
        check(w.events.some(e => e.type === 'event' && e.kind === 'hit' && e.actor === w.player(bot).id), `${bot} personally damages the Colossus`);
      }
      check(current().hp < current().maxHp && !current().dead, 'Five opening strikes do not come close to killing it');
      await w.debug(bots[0], { op: 'kill_enemy', id: elite.id });
      await w.waitFor(() => current().dead);
      for (const bot of bots) {
        await w.waitFor(() => quest(w, bot, qid).counts[0] === 1);
        check(quest(w, bot, qid).counts[0] === 1, `${bot} earns shared elite quest credit`);
      }
      check(bots.reduce((n, bot) => n + w.player(bot).kills, 0) === 1, 'The ordinary kill reward still has only one owner');
      for (const bot of bots) {
        await kit.teleport(w, bot, { npc: 'fen_reeve' });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        await kit.talkTo(w, bot, 'fen_reeve', `quest:claim:${qid}`);
        await w.waitFor(() => quest(w, bot, qid).claimed && w.player(bot).inventory.some(s => s.item === reward));
        check(w.player(bot).gold === before.gold + 1500 && totalXp(w.player(bot)) === before.xp + levelXp[19] / 10, `${bot} gets exact quest XP and gold`);
        check(w.player(bot).inventory.find(s => s.item === reward).quantity === 1, `${bot} gets one guaranteed blue ring`);
        await kit.talkTo(w, bot, 'fen_reeve', `quest:claim:${qid}`);
        check(w.player(bot).gold === before.gold + 1500 && w.player(bot).inventory.find(s => s.item === reward).quantity === 1, `${bot} cannot claim twice`);
        await w.action(bot, { type: 'equip', slots: { accessory1: reward } });
        await w.waitFor(() => w.player(bot).equipment.accessory1 === reward);
        check(true, `${bot} can equip the level-20 reward`);
      }
      await w.restart();
      check(bots.every(bot => quest(w, bot, qid).claimed && w.player(bot).equipment.accessory1 === reward), 'All five completions and worn rings survive a private server restart');
    },
  },
  mercenaries: {
    description: 'The two elite-quest givers rent mercenaries for 250 gold each: only with an unfinished quest taken, up to the players it wants, joining the party and the world, their kills paying the hirer, and the contract ending when its objective is complete.',
    startLevel: 20, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bot = 'Hirer', mercs = () => w.snapshot.players.filter(p => /^Merc /.test(p.look.name));
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { gold: 3000 });
      await w.debug(bot, { op: 'set_gold', gold: 3000 });
      // Two-player quest in the Crags: one mercenary of any class.
      await kit.teleport(w, bot, { npc: 'crags_captain' });
      let reply = await kit.talkTo(w, bot, 'crags_captain', 'merc_mage');
      check(/Take this elite quest first/.test(reply.notice) && !mercs().length, 'No mercenary without the quest');
      check(reply.offers.includes('merc_priest') && reply.offers.includes('merc_dismiss'), 'The captain offers every class and a dismissal');
      await kit.talkTo(w, bot, 'crags_captain', 'quest:accept:crags_cinderlord');
      await w.waitFor(() => !!quest(w, bot, 'crags_cinderlord'));
      reply = await kit.talkTo(w, bot, 'crags_captain', 'merc_priest');
      await w.waitFor(() => mercs().length === 1);
      check(/Merc Priest joins your party/.test(reply.notice) && w.player(bot).gold === 2750, 'A Priest is hired for 250 gold');
      check(mercs()[0].look.class === 'priest' && mercs()[0].level === 20, 'The mercenary is a level-20 Priest in the world');
      reply = await kit.talkTo(w, bot, 'crags_captain', 'merc_warrior');
      check(/wants 2 fighters/.test(reply.notice) && mercs().length === 1 && w.player(bot).gold === 2750, 'A two-player quest hires only one');
      await kit.talkTo(w, bot, 'crags_captain', 'merc_dismiss');
      await w.waitFor(() => mercs().length === 0);
      check(true, 'Sending them away removes the mercenary');
      // Five-player quest in Gloamfen: pick four.
      await w.debug(bot, { op: 'quest', id: 'fen_hydra', action: 'finish' });
      await kit.teleport(w, bot, { zone: 3, x: 64, y: 12 });
      await kit.teleport(w, bot, { npc: 'fen_reeve' });
      await kit.talkTo(w, bot, 'fen_reeve', 'quest:accept:fen_gloomroot');
      await w.waitFor(() => !!quest(w, bot, 'fen_gloomroot'));
      const purse = w.player(bot).gold;
      for (const c of ['priest', 'mage', 'hunter', 'warrior']) await kit.talkTo(w, bot, 'fen_reeve', 'merc_' + c);
      await w.waitFor(() => mercs().length === 4);
      check(mercs().map(m => m.look.class).sort().join() === 'hunter,mage,priest,warrior' && w.player(bot).gold === purse - 1000, 'Four chosen classes are hired for 1000 gold');
      reply = await kit.talkTo(w, bot, 'fen_reeve', 'merc_priest');
      check(/already has 5/.test(reply.notice) && mercs().length === 4, 'A fifth seat is refused: the party is full');
      // They follow into the arena and the kill is the hirer's.
      const elite = w.snapshot.slimes.find(s => s.kind === 'gloomroot');
      await kit.teleport(w, bot, { zone: 3, x: elite.x - 4, y: elite.y });
      await w.waitFor(() => mercs().every(m => Math.hypot(m.x - w.player(bot).x, m.y - w.player(bot).y) < 8), 15000, 'The mercenaries follow the hirer');
      check(true, 'The mercenaries keep to the hirer across the fen');
      await w.action(bot, { type: 'target', id: elite.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === elite.id).hp < elite.maxHp, 20000, 'The party hurts the Colossus');
      check(w.events.some(e => e.type === 'event' && e.kind === 'hit' && mercs().some(m => m.id === e.actor)), 'A mercenary personally damages the Colossus');
      await w.debug(bot, { op: 'kill_enemy', id: elite.id });
      await w.waitFor(() => quest(w, bot, 'fen_gloomroot').counts[0] === 1);
      check(w.player(bot).kills === 1, 'The hirer is credited with the kill');
      await w.waitFor(() => mercs().length === 0);
      check(!quest(w, bot, 'fen_gloomroot').claimed, 'The completed objective dismisses every hired mercenary before turn-in');
      await kit.teleport(w, bot, { npc: 'fen_reeve' });
      const completedPurse = w.player(bot).gold;
      reply = await kit.talkTo(w, bot, 'fen_reeve', 'merc_priest');
      check(/already complete/.test(reply.notice) && !mercs().length && w.player(bot).gold === completedPurse, 'Completed objectives cannot hire replacements or charge gold');
      await kit.talkTo(w, bot, 'fen_reeve', 'quest:claim:fen_gloomroot');
      await w.waitFor(() => quest(w, bot, 'fen_gloomroot').claimed);
      await w.waitFor(() => mercs().length === 0);
      check(w.player(bot).inventory.some(s => s.item === 'accessory_amber_l20_blue'), 'The completed quest still pays its ring');
      check(w.snapshot.online === 1, 'Mercenaries never count as players online');
    },
  },
  progression_quests: {
    description: 'Progression quests: one arrives by itself every five levels, is never offered at a giver, completes on arrival in the next zone, pays at that zone\'s captain and survives a restart.',
    async run(w, check) {
      const bot = 'Pathfinder', ids = ['crags_onward', 'rime_onward', 'fen_onward', 'city_onward'];
      await w.connect({ bot, class: 'warrior' });
      check(!w.player(bot).quests.length, 'A new character has no progression quest');
      await kit.setupCharacter(w, bot, { level: 4 });
      await w.advance(300);
      check(!quest(w, bot, 'crags_onward'), 'Level 4 is too early');
      await kit.setupCharacter(w, bot, { level: 5 });
      await w.waitFor(() => !!quest(w, bot, 'crags_onward'), 5000, 'The level-5 quest arrives');
      check(JSON.stringify(quest(w, bot, 'crags_onward').counts) === '[0]' && !quest(w, bot, 'rime_onward'), 'Level 5 brings only the Crags quest, with the trip still to make');
      check(w.events.some(e => e.type === 'system' && e.bot === bot && e.text.includes('Onward to the Crags')), 'The player is told a quest has found them');
      // Handing it in before the trip is refused, and nobody can hand it out.
      await kit.teleport(w, bot, { npc: 'crags_captain' });
      await w.waitFor(() => quest(w, bot, 'crags_onward').counts[0] === 1, 5000, 'Standing in the Crags completes it');
      await kit.teleport(w, bot, { npc: 'gatekeeper' });
      check(w.player(bot).zone === 0, 'The bot is back in the meadow');
      await w.waitFor(() => quest(w, bot, 'crags_onward').counts[0] === 1, 5000, 'Progress is kept after leaving');
      await kit.teleport(w, bot, { npc: 'crags_captain' });
      const before = totalXp(w.player(bot)), gold = w.player(bot).gold;
      const reply = await kit.talkTo(w, bot, 'crags_captain', 'quest:claim:crags_onward');
      await w.waitFor(() => quest(w, bot, 'crags_onward').claimed, 5000, 'The captain pays');
      check(reply.notice.includes('Quest complete') && w.player(bot).gold === gold + 100 && totalXp(w.player(bot)) === before + levelXp[4] / 10, 'The captain pays 100 gold and a tenth of level 5\'s XP');
      const refused = await kit.talkTo(w, bot, 'crags_captain', 'quest:accept:rime_onward');
      check(!quest(w, bot, 'rime_onward') && refused.notice !== undefined, 'A progression quest of another level cannot be taken at a giver');
      const id = w.player(bot).id;
      await w.restart();
      check(w.player(bot).id === id && quest(w, bot, 'crags_onward').claimed && quest(w, bot, 'crags_onward').completions === 1, 'The finished quest survives restarting the Rust process');
      await kit.talkTo(w, bot, 'crags_captain', 'quest:claim:crags_onward');
      check(w.player(bot).gold === gold + 100, 'It cannot be paid twice');
      // Levels 10, 15 and 20 each bring the next one, aimed at the next zone.
      for (const [level, quests] of [[10, 2], [15, 3], [20, 4]]) {
        await kit.setupCharacter(w, bot, { level });
        await w.waitFor(() => quest(w, bot, ids[quests - 1]), 5000, `The level-${level} quest arrives`);
        check(w.player(bot).quests.filter(q => ids.includes(q.id)).length === quests, `Level ${level} has brought ${quests} progression quests in all`);
      }
      check(JSON.stringify(quest(w, bot, 'city_onward').counts) === '[0]' && JSON.stringify(quest(w, bot, 'fen_onward').counts) === '[0]', 'The later quests still wait for the trip');
    },
  },
  resources: {
    description: 'All five class resources through real protocol: spending, exhaustion, combat recovery, food/potions, rage from a real fight, and mana persistence.',
    startLevel: 20,
    levelSpread: 0,
    async run(w, check) {
      for (const [bot, cls] of [['Rage','warrior'],['Mana','mage'],['Faith','priest'],['Energy','assassin'],['Arrows','hunter']]) {
        await w.connect({ bot, class: cls });
        const p = w.player(bot);
        check(p.resourceType === (cls === 'warrior' ? 'rage' : ['assassin','hunter'].includes(cls) ? 'energy' : 'mana'), `${cls} has its authoritative resource`);
        check(p.resource === (cls === 'warrior' ? 0 : p.maxResource), `${cls} starts with the correct resource amount`);
      }
      const mage = () => w.player('Mana');
      await cast(w, 'Mana', 'twinbolt');
      await w.waitFor(() => mage().skillCd.twinbolt > 0);
      // A mage in combat trickles 1.5% of the pool a second, so the spend is exact only to within a moment of that.
      const trickle = () => mage().maxResource * 0.03;
      check(Math.abs(mage().resource - (mage().maxResource - skillCatalog.find(s => s.id === 'twinbolt').cost)) <= trickle(), 'A valid mage cast spends its catalog mana cost (plus at most the in-combat trickle)');
      await w.debug('Mana', { op: 'set_resource', amount: 0 });
      await cast(w, 'Mana', 'starfall');
      await w.waitFor(() => w.events.some(e => e.bot === 'Mana' && e.type === 'error' && /Not enough mana/.test(e.text)));
      check(!mage().skillCd.starfall && mage().resource <= trickle(), 'An exhausted cast produces no cooldown or resource spend');
      await w.action('Mana', { type: 'attack', fx: 1, fy: 0 });
      await w.waitFor(() => mage().atkCd > 0);
      check(mage().resource <= trickle(), 'Basic attacks remain free when mana is empty');
      await w.advance(1000);
      check(mage().resource > 0 && mage().resource <= trickle() * 1.5, 'Mana only trickles while fighting (1.5% of the pool a second)');
      await w.action('Mana', { type: 'stop' });
      await w.waitFor(() => !mage().inCombat && mage().resource > mage().maxResource * 0.04, 9000, 'Out-of-combat mana recovery');
      check(!mage().inCombat, 'Mana recovers after the combat grace period');
      for (const bot of ['Energy','Arrows']) {
        await w.debug(bot, { op: 'set_resource', amount: 0 });
        await w.action(bot, { type: 'attack', fx: 1, fy: 0 });
        await w.advance(700);
        check(w.player(bot).resource > 5 && w.player(bot).inCombat, `${bot} recovers energy even in combat`);
      }
      // The apothecary sells the best tier the buyer's level allows: a level-20 mage gets the 110-gold, 300-mana Superior potion.
      const potion = kit.items.find(i => i.id === 'mana_potion_l20');
      await kit.setupCharacter(w, 'Mana', { gold: 200, teleportTo: { npc: 'apothecary' } });
      await kit.talkTo(w, 'Mana', 'apothecary', 'buy_mana_potion');
      await w.waitFor(() => mage().gold === 200 - potion.price && mage().inventory.some(i => i.item === potion.id), 3000, 'Mana potion purchase snapshot');
      check(mage().gold === 90 && mage().inventory.some(i => i.item === 'mana_potion_l20'), 'An ordinary merchant purchase supplies the level-20 mana potion for 110 gold');
      await w.debug('Mana', { op: 'give_item', item: 'health_potion', quantity: 1 });
      await w.debug('Mana', { op: 'set_resource', amount: 0 });
      await w.action('Mana', { type: 'attack', fx: 1, fy: 0 });
      await w.action('Mana', { type: 'use_item', item: potion.id });
      await w.waitFor(() => mage().potionCd > 0);
      const restored = Math.min(potion.mana, mage().maxResource);
      check(mage().resource >= restored - 3 && mage().resource <= mage().maxResource && mage().hp === mage().maxHp && w.events.some(e => e.bot === 'Mana' && e.kind === 'consume' && Math.abs(e.mana - restored) <= 3), 'A mana potion restores its mana (up to the pool) even at full health');
      await w.debug('Mana', { op: 'set_hp', hp: 1 });
      await w.action('Mana', { type: 'use_item', item: 'health_potion' });
      await w.advance(200);
      check(mage().inventory.some(i => i.item === 'health_potion'), 'Mana and health potions share the same cooldown');
      await w.debug('Faith', { op: 'give_item', item: 'traveler_stew', quantity: 1 });
      await w.debug('Faith', { op: 'set_resource', amount: 0 });
      await w.action('Faith', { type: 'attack', fx: 1, fy: 0 });
      await w.action('Faith', { type: 'use_item', item: 'traveler_stew' });
      await w.waitFor(() => w.player('Faith').buffs.some(b => b.kind === 'regen'));
      await w.advance(1000);
      check(w.player('Faith').resource >= 10 && w.player('Faith').hp === w.player('Faith').maxHp, 'Food restores priest mana at full health during combat');
      // Stage a target, then use ordinary attacks to build rage; no debug damage or resource grant.
      const enemy = await kit.spawnEnemy(w, 'Rage', { kind: 'beetle', level: 5, distance: 2 });
      const id = enemy.enemy?.id ?? enemy.id;
      await w.action('Rage', { type: 'target', id });
      await w.waitFor(() => w.player('Rage').resource >= 15, 10000, 'Rage from real hits');
      check(w.player('Rage').inCombat, 'The warrior builds rage through real damage');
      await cast(w, 'Rage', 'battlecry');
      await w.waitFor(() => w.player('Rage').buffs.some(b => b.id === 'battlecry'), 5000, 'Rage skill');
      check(w.player('Rage').skillCd.battlecry > 0, 'Built rage pays for a warrior skill');
      await w.action('Rage', { type: 'stop' });
      await kit.teleport(w, 'Rage', { npc: 'healer' });
      await w.debug('Mana', { op: 'set_resource', amount: 37 });
      await w.restart();
      check(mage().resource >= 37 && mage().resource < 60, 'Mana survives private server restart without refilling');
      check(mage().potionCd > 30, 'The shared potion cooldown also survives restart');
      check(w.player('Rage').resource === 0 && w.player('Energy').resource === 100, 'Rage resets to zero and energy starts full on resume');
    },
  },
  undervault: {
    description: 'The dungeon under Skaldholm: the stairs beside the Meeting Stone refuse level 19 and take level 20 in; the Stone hires a full party that follows in; every group gets a private copy (an unrelated hero sees none of it); archers shoot real missiles; each boss drops random cross-class Undervault gear shared through party rolls; the exit portal opens only when the last boss falls and returns to Skaldholm; the dungeon resets when empty; a hero who logs out inside wakes at the stairs.',
    startLevel: 20, godMode: true, levelSpread: 0,
    async run(w, check) {
      const vault = map.zones[4], stairs = city.portals.find(p => p.id === 'undervault_stairs'), exit = vault.portals.find(p => p.after_clear), ret = { x: vault.portals[0].tx, y: vault.portals[0].ty };
      const bot = 'Delver', rival = 'Rival', mercs = () => w.views.get(bot).players.filter(p => /^Merc /.test(p.look.name)), view = b => w.views.get(b);
      await w.connect({ bot, class: 'warrior' });
      check(vault.name === 'The Undervault' && vault.copies === 4 && vault.min_level === 20 && vault.final_boss === 'hollowking' && vault.players === 5, 'Zone 5 is a level-20 five-player dungeon with four private copies');
      check(stairs && stairs.to === 5 && city.portals[0].id === 'glacier_gate' && vault.portals[0].to === 4 && exit.to === 4, 'The stairs beside the Meeting Stone lead down; the dungeon has stairs up and a closed exit');
      const kinds = vault.slimes.reduce((c, s) => ({ ...c, [s.kind]: (c[s.kind] || 0) + 1 }), {});
      check(JSON.stringify(kinds) === JSON.stringify({ thrall: 25, archer: 12, acolyte: 9, gatewarden: 1, choir: 1, colossus: 1, hollowking: 1 }), 'Fifty enemies: 25 thralls, 12 archers, 9 acolytes and the four bosses');
      // Level 19 is turned away at the door.
      await kit.setupCharacter(w, bot, { level: 19, gold: 3000 });
      await kit.teleport(w, bot, { zone: 4, x: ret.x, y: ret.y });
      let earlier = new Set(w.events);
      await w.action(bot, { type: 'move', x: stairs.x, y: stairs.y });
      const refusal = await w.waitFor(() => w.events.find(e => !earlier.has(e) && e.bot === bot && e.type === 'error' && /level 20/.test(e.text)), 20000, 'The door refuses level 19');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).zone === 4 && /level 19/.test(refusal.text), 'A level-19 hero is told to come back at level 20 and stays in Skaldholm');
      await kit.teleport(w, bot, { zone: 4, x: 100, y: 128 });       // off the stairs: at level 20 the door would take them in at once
      await kit.setupCharacter(w, bot, { level: 20 });
      await w.debug(bot, { op: 'set_gold', gold: 3000 });
      for (let i = 0; i < 3; i++) await w.debug(bot, { op: 'give_item', item: 'linen_satchel', quantity: 1 });   // room for five pieces
      // The Meeting Stone hires a full party for 250 gold each, with no quest.
      let reply = await kit.talkTo(w, bot, 'city_meetingstone', 'merc_priest');
      await w.waitFor(() => w.player(bot).gold === 2750, 5000, 'The 250 gold is paid');
      check(/Merc Priest joins your party/.test(reply.notice) && w.player(bot).gold === 2750, 'The Stone hires a Priest for 250 gold with no quest');
      for (const c of ['warrior', 'mage', 'hunter']) await kit.talkTo(w, bot, 'city_meetingstone', 'merc_' + c);
      await w.waitFor(() => mercs().length === 4, 10000, 'Four mercenaries');
      reply = await kit.talkTo(w, bot, 'city_meetingstone', 'merc_assassin');
      check(/already has 5/.test(reply.notice) && mercs().length === 4, 'A party of five is full');
      // Walk down the stairs with real moves; the mercenaries follow into the same copy.
      await kit.teleport(w, bot, { zone: 4, x: ret.x, y: ret.y });
      await w.action(bot, { type: 'move', x: stairs.x, y: stairs.y });
      await w.waitFor(() => w.player(bot).zone === 5, 20000, 'Down the stairs');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), vault.spawn) < 1.5, 'The stairs set the hero down at the dungeon\'s start');
      await w.waitFor(() => mercs().length === 4 && mercs().every(m => m.zone === 5 && distance(m, w.player(bot)) < 12), 15000, 'The party arrives together');
      check(view(bot).slimes.length === 50 && view(bot).slimes.every(s => s.zone === 5) && view(bot).instance.cleared === false, 'The client is sent the fifty enemies of its own copy, labelled zone 5, not yet cleared');
      check(w.snapshot.online === 1, 'Mercenaries never count as players online');
      // A stranger gets a copy of their own and sees nothing of ours.
      await w.connect({ bot: rival, class: 'mage' });
      await kit.setupCharacter(w, rival, { level: 20 });
      await kit.teleport(w, rival, { zone: 5, x: vault.spawn.x, y: vault.spawn.y });
      await w.waitFor(() => view(rival).players.some(p => p.id === w.bots.get(rival).id && p.zone === 5), 10000, 'The stranger is in the dungeon');
      check(view(rival).players.length === 1 && !view(rival).players.some(p => p.id === w.bots.get(bot).id), 'A second group gets another copy: they never see each other (the merged snapshot keeps one view per zone, so each bot is read through its own)');
      const thrall = view(bot).slimes.find(s => s.kind === 'thrall');
      await w.debug(bot, { op: 'kill_enemy', id: thrall.id });
      await w.waitFor(() => view(bot).slimes.find(s => s.id === thrall.id).dead, 5000, 'Our thrall dies');
      const mirror = view(rival).slimes.find(s => s.kind === 'thrall');
      check(mirror && mirror.id !== thrall.id && !mirror.dead && mirror.hp === mirror.maxHp, 'Its twin in the other copy (another enemy id) is untouched');
      await w.disconnect(rival);
      // A real archer shoots real missiles at the hero.
      const archer = view(bot).slimes.filter(s => s.kind === 'archer' && !s.dead)[0];
      await kit.teleport(w, bot, { zone: 5, x: archer.x - 7, y: archer.y });
      await w.waitFor(() => (view(bot).ebolts || []).some(b => b.kind === 'archer'), 20000, 'An arrow is in the air');
      check((view(bot).ebolts || []).every(b => b.zone === 5 && typeof b.speed === 'number'), 'Missiles are in the snapshot with their speed, labelled zone 5');
      // Replace the hired party with two real heroes so we can answer the shared boss rolls.
      await kit.teleport(w, bot, { zone: 4, x: 100, y: 128 });
      await kit.talkTo(w, bot, 'city_meetingstone', 'merc_dismiss');
      await w.connect({ bot: rival, class: 'mage' });
      await kit.setupCharacter(w, rival, { level: 20 });
      await w.social(bot, { op: 'party_invite', bot: rival });
      await w.social(rival, { op: 'party_accept', bot });
      await kit.teleport(w, bot, { zone: 5, x: vault.spawn.x, y: vault.spawn.y });
      await kit.teleport(w, rival, { zone: 5, x: vault.spawn.x + 2, y: vault.spawn.y });
      await kit.teleport(w, bot, { zone: 5, x: exit.x, y: exit.y });
      await w.advance(2000);
      check(w.player(bot).zone === 5, 'Standing on the closed exit does nothing');
      const bag = b => w.player(b).inventory.filter(s => /_l20_vault$/.test(s.item)).reduce((n, s) => n + s.quantity, 0);
      for (const kind of ['gatewarden', 'choir', 'colossus', 'hollowking']) {
        const boss = view(bot).slimes.find(s => s.kind === kind), count = kind === 'hollowking' ? 2 : 1;
        await kit.teleport(w, bot, { zone: 5, x: boss.x - 3, y: boss.y });
        await kit.teleport(w, rival, { zone: 5, x: boss.x - 4, y: boss.y });
        const before = bag(bot) + bag(rival), earlier = new Set(w.events);
        await w.debug(bot, { op: 'kill_enemy', id: boss.id });
        const starts = b => w.events.filter(e => !earlier.has(e) && e.bot === b && e.type === 'roll' && e.op === 'start' && /_l20_vault$/.test(e.item));
        await w.waitFor(() => starts(bot).length === count && starts(rival).length === count, 5000, `${kind} starts shared boss rolls`);
        check(starts(bot).length === count && starts(rival).every(e => starts(bot).some(r => r.id === e.id && r.item === e.item)), `${kind} drops ${count} shared piece(s), both party members roll on the same items`);
        const winner = kind === 'hollowking' ? bot : rival, passer = winner === bot ? rival : bot;
        for (const roll of starts(winner)) {
          const piece = kit.items.find(i => i.id === roll.item);
          check(piece.rarity === 'rare' && piece.source === 'undervault' && piece.requiredLevel === 20, 'Boss gear is blue, level 20 and from the Undervault');
          check(roll.need === (!piece.class || piece.class === (winner === bot ? 'warrior' : 'mage')), 'Need is available only when the random boss piece fits the member');
          await w.action(passer, { type: 'roll', id: roll.id, choice: 'pass' });
          await w.action(winner, { type: 'roll', id: roll.id, choice: roll.need ? 'need' : 'greed' });
        }
        await kit.teleport(w, winner, { zone: 5, x: boss.x, y: boss.y });
        await w.waitFor(() => bag(bot) + bag(rival) === before + count, 15000, `${kind}'s winner collects the shared loot`);
        check(bag(bot) + bag(rival) === before + count, `${kind} awards each piece once, with no personal copies`);
        if (kind !== 'hollowking') check(view(bot).instance.cleared === false, `${kind} does not open the exit`);
      }
      await w.waitFor(() => view(bot).instance.cleared === true, 5000, 'The dungeon is cleared');
      await kit.teleport(w, bot, { zone: 5, x: exit.x, y: exit.y });
      await w.waitFor(() => w.player(bot).zone === 4, 15000, 'The portal carries the hero out');
      check(distance(w.player(bot), { x: exit.tx, y: exit.ty }) < 1.5, 'The opened portal leads out beside the stairs in Skaldholm');
      await w.disconnect(rival);
      // Empty, the dungeon is whole again; one who logs out inside wakes at the stairs.
      await w.action(bot, { type: 'move', x: stairs.x, y: stairs.y });
      await w.waitFor(() => w.player(bot).zone === 5, 20000, 'Down again');
      await w.action(bot, { type: 'stop' });
      check(view(bot).slimes.length === 50 && view(bot).slimes.every(s => !s.dead) && view(bot).instance.cleared === false, 'Back in: every enemy alive again and the exit shut');
      await w.disconnect(bot);
      await w.connect({ bot });
      check(w.player(bot).zone === 4 && distance(w.player(bot), { x: ret.x, y: ret.y }) < 3, 'A hero who logged out inside wakes at the stairs in Skaldholm');
      await w.restart();
      check(w.player(bot).zone === 4, 'The city position survives a Rust restart');
    },
  },

  spark_travel: {
    description: 'Spark Travel discovery, missing intermediate stops, fares, real flights through every stop, immunity and resume after restart.',
    godMode: false,
    levelSpread: 0,
    async run(w, check) {
      const bot = 'Spark', A = 'travel_alderhaven', B = 'travel_cinderwatch', C = 'travel_rimeward';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { gold: 100 });
      const visit = async id => { await kit.teleport(w, bot, { npc: id }); return kit.talkTo(w, bot, id); };
      const choose = async (from, to) => {
        const before = new Set(w.events);
        await w.advance(550);
        await w.action(bot, { type: 'interact', npc: from, offer: `spark:${to}` });
        return w.waitFor(() => w.events.find(e => !before.has(e) && e.bot === bot && (e.type === 'dialogue' || e.type === 'notice')), 5000, 'Spark reply');
      };
      let reply = await visit(A);
      check(reply.travel.length === 6, 'Every other settlement appears as a destination');
      check(reply.travel.find(d => d.id === C).cost === 40, 'Two legs cost 40 gold');
      await visit(C); await kit.teleport(w, bot, { npc: A });
      reply = await choose(A, C);
      check(reply.notice.includes('Cinderwatch'), 'A missing intermediate master blocks the third stop');
      check(w.player(bot).gold === 100 && !w.player(bot).sparkTravel, 'Blocked travel spends no gold and does not launch');
      await visit(B); await visit(A);
      await w.waitFor(() => w.player(bot).travelStops.length === 3);
      check(new Set(w.player(bot).travelStops).size === 3, 'Talking twice never duplicates discovery');
      await w.debug(bot, { op: 'set_gold', gold: 39 });
      reply = await choose(A, C);
      check(reply.notice.includes('enough'), 'A hero with 39 gold cannot buy a 40-gold flight');
      check(w.player(bot).gold === 39, 'Insufficient gold is preserved');
      await w.debug(bot, { op: 'set_gold', gold: 100 });
      const oldEvents = new Set(w.events);
      reply = await choose(A, C);
      await w.waitFor(() => !!w.player(bot).sparkTravel);
      check(reply.ok === true && w.player(bot).gold === 60, 'The full fare is charged once at departure');
      check(w.player(bot).sparkTravel.stops.join(',') === [A,B,C].join(','), 'The authoritative itinerary includes the second stop');
      const before = { ...w.player(bot) }, time = w.views.get(bot).time;
      await w.advance(500);
      const after = w.player(bot), elapsed = w.views.get(bot).time - time;
      check(Math.abs(distance(before, after) - 5.2 * 3 * elapsed) < .02, 'Real snapshots move at three times Warrior walking speed');
      await w.action(bot, { type: 'stop' });
      await w.action(bot, { type: 'move', x: 1, y: 1 });
      await w.action(bot, { type: 'attack', fx: 1, fy: 0 });
      await w.advance(300);
      check(!!w.player(bot).sparkTravel && w.player(bot).atkT === 0, 'Ground inputs cannot interrupt or attack during a flight');
      await w.restart();
      check(w.player(bot).gold === 60 && !!w.player(bot).sparkTravel, 'A private server restart resumes the paid flight');
      check(w.player(bot).travelStops.length === 3, 'Discovered masters survive restart');
      await w.waitFor(() => !w.player(bot).sparkTravel && w.player(bot).zone === 2, 30000, 'Arrive at the third stop');
      const stops = w.events.filter(e => !oldEvents.has(e) && e.bot === bot && e.kind === 'sparkStop').map(e => e.stop);
      check(stops.join(',') === [B,C].join(','), 'The spark passes the second master before stopping at the third');
      const master = rime.npcs.find(n => n.id === C);
      check(distance(w.player(bot), master) < .05, 'Arrival is beside the chosen travel master');
      check(w.player(bot).gold === 60 && w.player(bot).hp === w.player(bot).maxHp && w.player(bot).kills === 0, 'Flying past enemies causes no damage, rewards or extra fares');
      reply = await kit.talkTo(w, bot, C);
      check(reply.travel.find(d => d.id === B).cost === 20 && reply.travel.find(d => d.id === A).cost === 40, 'Return fares count the same legs');
      await choose(C, B);
      await w.waitFor(() => !w.player(bot).sparkTravel && w.player(bot).zone === 1, 20000, 'Return to Cinderwatch');
      check(w.player(bot).gold === 40, 'One-leg return charges exactly 20 gold');
      await w.disconnect(bot); await w.connect({ bot });
      check(w.player(bot).gold === 40 && w.player(bot).zone === 1 && w.player(bot).travelStops.length === 3, 'Arrival and discoveries survive logout');
    },
  },


  instance_pursuit: {
    description: 'Instance enemies keep chasing beyond range and home leash through dungeon corridors; Meeting Stone mercenaries depart on clear after final boss rolls are created.',
    startLevel: 20, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bot = 'Runner', anchor = 'Anchor', vault = map.zones[4];
      const view = () => w.views.get(bot), mercs = () => view().players.filter(p => /^Merc /.test(p.look.name));
      await w.connect({ bot, class: 'warrior' });
      await w.connect({ bot: anchor, class: 'mage' });
      await w.social(bot, { op: 'party_invite', bot: anchor });
      await w.social(anchor, { op: 'party_accept', bot });
      await kit.teleport(w, bot, { zone: 5, ...vault.spawn });
      await kit.teleport(w, anchor, { zone: 5, x: vault.spawn.x + 1, y: vault.spawn.y });
      await kit.teleport(w, anchor, { zone: 5, x: 57, y: 104 });
      const staged = await kit.spawnEnemy(w, bot, { kind: 'thrall', distance: 4 });
      const id = staged.enemy.id, enemy = () => view().slimes.find(s => s.id === id);
      await w.waitFor(() => ['chase','windup','lunge'].includes(enemy().state), 5000, 'The staged enemy aggroes normally');
      const from = { x: enemy().x, y: enemy().y };
      // The anchor keeps this private copy selected while the runner goes to the first room.
      await kit.teleport(w, bot, { zone: 5, x: 57, y: 104 });
      check(distance(from, w.player(bot)) > 30, 'The target is beyond the old awareness and chase range');
      await w.advance(1000);
      check(enemy().state !== 'return', 'The enemy pursues instead of dropping aggro');
      await w.waitFor(() => distance(enemy(), from) > 15, 30000, 'The enemy passes its old home leash');
      check(enemy().state !== 'return', 'Passing the home leash does not reset an instance enemy');
      await w.waitFor(() => distance(enemy(), w.player(bot)) < 4, 30000, 'The enemy follows through the entry corridors into the room');
      check(!enemy().dead && distance(enemy(), from) > 25, 'The living enemy reaches the distant hero through the dungeon');
      await w.debug(bot, { op: 'kill_enemy', id });
      // Hire a fighter for this run; completed unrelated objectives do not end Stone contracts.
      await kit.setupCharacter(w, bot, { gold: 1000, finishQuests: ['crags_cinderlord'], teleportTo: { npc: 'city_meetingstone' } });
      await kit.talkTo(w, bot, 'city_meetingstone', 'merc_priest');
      await kit.teleport(w, bot, { zone: 5, ...vault.spawn });
      await w.waitFor(() => mercs().length === 1, 5000, 'The hired mercenary follows into the copy');
      check(mercs().length === 1, 'An unrelated completed objective leaves the instance contract active');
      const boss = view().slimes.find(s => s.kind === 'gatewarden');
      await w.debug(bot, { op: 'kill_enemy', id: boss.id });
      check(!view().instance.cleared && mercs().length === 1, 'An earlier boss does not dismiss instance mercenaries');
      const king = (await kit.spawnEnemy(w, bot, { kind: 'hollowking', distance: 4 })).enemy;
      const earlier = new Set(w.events);
      await w.debug(bot, { op: 'kill_enemy', id: king.id });
      await w.waitFor(() => view().instance.cleared && !mercs().length, 5000, 'Clearance dismisses the hired fighter');
      check(view().instance.cleared && !mercs().length, 'The final boss clears the instance and its mercenary departs');
      const starts = w.events.filter(e => !earlier.has(e) && e.bot === bot && e.type === 'roll' && e.op === 'start' && /_l20_vault$/.test(e.item));
      check(starts.length === 2, 'Both final boss loot rolls are created before departure');
      check(w.player(bot).kills === 3, 'The runner retains all three kill credits');
    },
  },


  wyrdwood: {
    description: 'Walk out of Skaldholm through the new East Gate into the level 20-30 Wyrdwood, check its 67 monster slots (five kinds, two elites, five sleeping ambushers) and their levels, walk the real route to the Troll Bridge and across it into Skuldwatch, fight a level-1 Rotfang Boar for exact XP, gold and loot, keep the zone across a restart and walk back through the gate.',
    async run(w, check) {
      const bot = 'Woodwalker';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 24 });
      const east = city.portals.find(p => p.id === 'wyrd_gate'), back = wyrd.portals.find(p => p.id === 'skaldholm_gate');
      check(east && east.to === 6 && back && back.to === 4 && wyrd.name === 'Wyrdwood' && wyrd.levels.join() === '20,30' && wyrd.size === 192, 'Skaldholm has an East Gate to zone 6, the 192-tile Wyrdwood of levels 20-30, which has the gate back');
      check(wyrd.camps.length === 1 && wyrd.city.name === 'Hollowmoot' && wyrd.camps[0].name === 'Skuldwatch', 'The zone has two hubs, Hollowmoot and Skuldwatch');
      // Staging only: stand inside the city by the east wall. The walk through the gap in the wall and the gate are real.
      await kit.teleport(w, bot, { zone: 4, x: east.x - 14, y: east.y });
      await walkTo(w, bot, { x: east.x - 3, y: east.y }, city);
      check(w.player(bot).zone === 4, 'Still in Skaldholm in front of the gate');
      await w.action(bot, { type: 'move', x: east.x + 1.2, y: east.y });
      await w.waitFor(() => w.player(bot).zone === 6, 20000, 'Step through the East Gate');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: east.tx, y: east.ty };
      check(distance(w.player(bot), arrival) < 1.2, 'The server moves the walker to the west edge of Hollowmoot');
      const woods = w.snapshot.slimes;
      const kinds = {}; for (const s of woods) kinds[s.kind] = (kinds[s.kind] || 0) + 1;
      check(woods.every(s => s.zone === 6) && JSON.stringify(Object.entries(kinds).sort()) === JSON.stringify([['boar', 14], ['crow', 15], ['hrungnir', 1], ['oakhorn', 1], ['ram', 10], ['troll', 14], ['weaver', 12]]),
        'A Wyrdwood client receives exactly its 67 monster slots: 14 boars, 15 crows, 14 trolls, 12 weavers, 10 rams and the two elites');
      const asleep = woods.filter(s => s.dead && s.state === 'waiting');
      check(asleep.length === 5 && asleep.filter(s => s.kind === 'crow').length === 3 && asleep.filter(s => s.kind === 'troll').length === 2, 'Five ambushers sleep (three crows, two trolls) until an escort passes');
      const hp = { boar: 5600, crow: 4300, troll: 9500, weaver: 7600, ram: 11500, oakhorn: 60000, hrungnir: 150000 };
      const living = woods.filter(s => !s.dead);
      check(living.length === 62 && living.every(s => Math.abs(s.level - DEFAULT_LEVELS[s.kind]) <= 2) && new Set(living.map(s => s.level - DEFAULT_LEVELS[s.kind])).size >= 3, 'The 62 live monsters roll within two of each default level (21, 23, 25, 27, 29, 25, 30) and really vary');
      check(living.every(s => s.maxHp === Math.round(hp[s.kind] * (1 + .12 * (s.level - DEFAULT_LEVELS[s.kind])))), 'Health follows each rolled level');
      check(living.filter(s => s.elite).map(s => s.kind).sort().join() === 'hrungnir,oakhorn', 'Exactly Oakhorn and Hrungnir are elites');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Wyrdwood') && e.text.includes('20–30')), 'The player is told the recommended levels');
      // Another character in Skaldholm shares nothing with the forest.
      await w.connect({ bot: 'Citizen', class: 'mage' });
      await kit.teleport(w, 'Citizen', { zone: 4, x: 80, y: 120 });
      check(w.views.get('Citizen').slimes.length === 0 && w.views.get(bot).slimes.every(s => s.zone === 6) && w.views.get(bot).players.length === 1, 'Each client is sent only its own zone');
      await w.disconnect('Citizen');
      // The way to Skuldwatch: through the south forest to the bridge. The river is crossed in one place only.
      const bridge = { x: 96, y: 108 }, hubSouth = { x: 96, y: 92 };
      const start = { x: w.player(bot).x, y: w.player(bot).y }, to = route(wyrd, start, { x: 96, y: 118 }), over = route(wyrd, { x: 96, y: 118 }, hubSouth);
      const crossings = [...to, ...over].map((p, i, all) => [i ? all[i - 1] : start, p]).filter(([a, b]) => (a.y - 108) * (b.y - 108) <= 0 && a.y !== b.y).map(([a, b]) => a.x + (b.x - a.x) * (108 - a.y) / (b.y - a.y));
      check(crossings.length >= 1 && crossings.every(x => Math.abs(x - 96) < 3.5), `The only crossing of the river is the bridge (${crossings.map(x => x.toFixed(1)).join(', ')})`);
      for (const point of [...to, ...over]) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .6, 60000, `Walk the Wyrdwood to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), hubSouth) < 1.5 && w.player(bot).y < bridge.y, 'The bot crosses the Troll Bridge on foot and reaches Skuldwatch');
      // A level-1 Rotfang Boar is a short real fight, and pays its own level (staging: the spot is in the forest, away from the packs).
      await kit.teleport(w, bot, { zone: 6, x: 70, y: 150 });
      const before = { ...w.player(bot) };
      const boar = (await kit.spawnEnemy(w, bot, { kind: 'boar', level: 1, distance: 2.5 })).enemy;
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === boar.id)?.level === 1, 5000, 'See the spawned boar');
      check(w.snapshot.slimes.find(s => s.id === boar.id).maxHp === Math.round(5600 * .2), 'A level-1 boar has the floor of 20% of its health (1120)');
      await w.action(bot, { type: 'target', id: boar.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === boar.id).dead, 120000, 'Defeat the boar');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).kills === before.kills + 1 && totalXp(w.player(bot)) === totalXp(before) + enemyXp(1), `The kill pays the level-1 XP (${enemyXp(1)})`);
      await w.waitFor(() => w.player(bot).gold >= before.gold + 54, 15000, 'Pick up the gold');
      check(w.player(bot).gold === before.gold + 54, 'The kill drops 20% of the boar gold (54)');
      await w.waitFor(() => w.player(bot).inventory.some(s => s.item === 'rotfang_tusk'), 15000, 'Pick up the tusk');
      check(true, 'The boar drops its Rotfang Tusk');
      // A restart keeps the character in the Wyrdwood.
      await w.restart();
      check(w.player(bot).zone === 6, 'The character resumes in the Wyrdwood after a server restart');
      // The way back is a real walk through the Wyrdwood gate.
      await kit.teleport(w, bot, { zone: 6, x: 12, y: 150 });
      await w.action(bot, { type: 'move', x: back.x - 1.5, y: back.y });
      await w.waitFor(() => w.player(bot).zone === 4, 15000, 'Step through the gate back');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), { x: back.tx, y: back.ty }) < 1.2, 'The gate sets you down outside Skaldholm\'s East Gate');
      await w.action(bot, { type: 'move', x: east.x + 1.2, y: east.y });
      await w.waitFor(() => w.player(bot).zone === 6, 15000, 'Step through the East Gate again');
      check(distance(w.player(bot), arrival) < 1.5, 'The gate works again right after arriving');
    },
  },

  wyrd_quests: {
    description: 'Every ordinary quest of Hollowmoot and Skuldwatch played in dependency order through the real accept and claim paths (talk, kill, bring, visit, cross-hub message, repeatable bounties) with exact XP and gold, the two group quests hire their fighters, then the escort: Eydis is found, walked past two real ambushes and across the Troll Bridge into Skuldwatch for the reward; a second hero fails it by dying and starts again.',
    startLevel: 20, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bot = 'Questwalker';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 26, gold: 4000 });
      const defs = wyrd.quests, npcs = wyrd.npcs;
      check(npcs.length === 17 && defs.length >= 24 && defs.every(q => q.id.startsWith('wyrd_')), `The two hubs hold ${npcs.length} people and ${defs.length} quests`);
      const find = id => defs.find(q => q.id === id);
      const placeOf = id => wyrd.places.find(p => p.id === id);
      const state = id => quest(w, bot, id);
      const give = (item, quantity) => w.debug(bot, { op: 'give_item', item, quantity });
      // Earlier quests used the packs up: bring back the dead ones near a point (never the sleeping ambushers or the elites) until `n` live ones are within `radius`.
      async function refill(at, radius, n) {
        const live = () => w.snapshot.slimes.filter(s => !s.dead && !s.elite && distance(s, at) < radius).length;
        if (live() >= n) return;
        for (const d of w.snapshot.slimes.filter(s => s.dead && s.state !== 'waiting' && !s.elite && distance(s, at) < radius)) await w.debug(bot, { op: 'respawn_enemy', id: d.id });
        await w.waitFor(() => live() >= n, 10000, 'The woods refill');
      }
      async function playQuest(id) {
        const q = find(id);
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${id}`);
        await w.waitFor(() => state(id) && !state(id).claimed, 5000, `Accept ${id}`);
        for (const [i, o] of q.objectives.entries()) {
          if (o.kind === 'talk') { await kit.teleport(w, bot, { npc: o.target }); await kit.talkTo(w, bot, o.target); }
          else if (o.kind === 'bring') await give(o.target, o.count);
          else if (o.kind === 'visit') { const p = placeOf(o.target); await kit.teleport(w, bot, { zone: 6, x: p.x, y: p.y + (o.target.includes('beacon') ? 2.4 : 0) }); }
          else if (o.kind === 'kill') {
            const kinds = o.target === 'any' ? [undefined] : [o.target];
            const fields = o.target === 'any' ? { radius: 60, max: o.count } : { kind: o.target, max: o.count };
            if (o.target === 'any') { await kit.teleport(w, bot, { npc: q.npc }); await refill(w.player(bot), 60, o.count + 2); }
            if (o.target !== 'any') {                                  // earlier quests used the pack up: bring the dead ones back (never the sleeping ambushers)
              const alive = () => w.snapshot.slimes.filter(s => !s.dead && s.kind === o.target).length;
              if (alive() < o.count) {
                for (const d of w.snapshot.slimes.filter(s => s.dead && s.kind === o.target && s.state !== 'waiting').slice(0, o.count - alive())) await w.debug(bot, { op: 'respawn_enemy', id: d.id });
                await w.waitFor(() => alive() >= o.count, 10000, `Respawn ${o.target}`);
              }
            }
            const here = w.snapshot.slimes.filter(s => !s.dead && (o.target === 'any' || s.kind === o.target)).sort((a, b) => distance(a, w.player(bot)) - distance(b, w.player(bot)))[0];
            if (here) await kit.teleport(w, bot, { zone: 6, x: here.x + 3, y: here.y });
            const done = await kit.killEnemies(w, bot, fields); void kinds;
            assert.ok(done.count >= o.count || o.target === 'any', `Killed enough ${o.target}`);
          } else throw Error(`${id}: unexpected objective ${o.kind}`);
          await w.waitFor(() => (state(id).counts[i] || 0) >= Math.min(o.count, o.kind === 'kill' ? 99 : o.count), 8000, `${id} objective ${i}`);
        }
        await w.waitFor(() => state(id).counts.every((c, i) => c >= q.objectives[i].count), 8000, `${id} is ready`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        const held = item => w.player(bot).inventory.filter(s => s.item === item).reduce((n, s) => n + s.quantity, 0);
        const bringing = q.objectives.filter(o => o.kind === 'bring').map(o => [o.target, o.count, held(o.target)]);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${id}`);
        await w.waitFor(() => state(id).claimed, 5000, `Claim ${id}`);
        for (const [item, count, had] of bringing) check(held(item) === had - count, `${id}: the hand-in took exactly ${count} ${item}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + levelXp[q.level - 1] / 10, `${id}: the claim pays ${q.rewardGold} gold and a tenth of level ${q.level}'s XP`);
        return q;
      }
      // Dependency order: every ordinary quest, none of the group quests, the escort or the progression quest (it arrives by itself).
      const skip = new Set(['wyrd_oakhorn', 'wyrd_hrungnir', 'wyrd_escort', 'wyrd_onward']);
      const order = [], seen = new Set();
      const visit = q => { if (seen.has(q.id) || skip.has(q.id)) return; seen.add(q.id); if (q.requires && !skip.has(q.requires)) visit(find(q.requires)); order.push(q); };
      defs.forEach(visit);
      const tally = {};
      for (const q of order) { await playQuest(q.id); for (const o of q.objectives) tally[o.kind] = (tally[o.kind] || 0) + 1; }
      check(order.length >= 20 && ['talk', 'kill', 'bring', 'visit'].every(k => tally[k] >= 3), `${order.length} quests played end to end: ${JSON.stringify(tally)}`);
      const onward = state('wyrd_onward');
      check(onward && onward.counts[0] === 1 && !onward.claimed, 'The level-22 progression quest arrived by itself and already counts: the hero stands in the Wyrdwood');
      await kit.teleport(w, bot, { npc: 'wyrd_warden' });
      await kit.talkTo(w, bot, 'wyrd_warden', 'quest:claim:wyrd_onward');
      await w.waitFor(() => state('wyrd_onward').claimed, 5000, 'Claim the progression quest');
      // A repeatable bounty can be taken and paid again.
      const rep = defs.find(q => q.id === 'wyrd_patrol');
      for (let round = 0; round < 2; round++) {
        const before = { gold: w.player(bot).gold, completions: state('wyrd_patrol').completions };
        await kit.teleport(w, bot, { npc: rep.npc });
        await kit.talkTo(w, bot, rep.npc, 'quest:accept:wyrd_patrol');
        await w.waitFor(() => !state('wyrd_patrol').claimed, 5000, 'Take the patrol again');
        await kit.teleport(w, bot, { zone: 6, x: 60, y: 150 });
        await refill({ x: 60, y: 150 }, 80, 12);
        await kit.killEnemies(w, bot, { radius: 80, max: 12 });
        await w.waitFor(() => state('wyrd_patrol').counts[0] === 12, 8000, 'Patrol count');
        await kit.teleport(w, bot, { npc: rep.npc });
        await kit.talkTo(w, bot, rep.npc, 'quest:claim:wyrd_patrol');
        await w.waitFor(() => state('wyrd_patrol').completions === before.completions + 1, 5000, 'Patrol paid');
        check(w.player(bot).gold === before.gold + rep.rewardGold, `The repeatable patrol pays ${rep.rewardGold} gold again (round ${round + 1})`);
      }
      // The group quests: the giver hires exactly the missing fighters, up to the quest's party size.
      const mercs = () => w.snapshot.players.filter(p => /^Merc /.test(p.look.name)).length;
      await kit.teleport(w, bot, { npc: 'wyrd_warden' });
      await kit.talkTo(w, bot, 'wyrd_warden', 'quest:accept:wyrd_oakhorn');
      await w.waitFor(() => state('wyrd_oakhorn'), 5000, 'Accept the Oakhorn quest');
      for (const c of ['warrior', 'priest', 'mage']) await kit.talkTo(w, bot, 'wyrd_warden', `merc_${c}`);
      await w.waitFor(() => mercs() === 2, 8000, 'Two fighters join');
      check(mercs() === 2 && find('wyrd_oakhorn').recommendedPlayers === 3 && find('wyrd_oakhorn').rewardItem === 'pants_wayfarer_l20_blue', 'The Oakhorn quest wants three heroes, hires two fighters and refuses the third; its reward is a blue item');
      await kit.talkTo(w, bot, 'wyrd_warden', 'merc_dismiss');
      await w.waitFor(() => mercs() === 0, 8000, 'Send them away');
      await kit.teleport(w, bot, { npc: 'wyrd_captain' });
      await kit.talkTo(w, bot, 'wyrd_captain', 'quest:accept:wyrd_hrungnir');
      await w.waitFor(() => state('wyrd_hrungnir'), 5000, 'Accept the Hrungnir quest');
      for (const c of ['warrior', 'priest', 'mage', 'hunter', 'assassin']) await kit.talkTo(w, bot, 'wyrd_captain', `merc_${c}`);
      await w.waitFor(() => mercs() === 4, 8000, 'Four fighters join');
      check(mercs() === 4 && find('wyrd_hrungnir').recommendedPlayers === 5 && find('wyrd_hrungnir').rewardItem === 'necklace_moonstone_l20_purple', 'The Hrungnir quest wants five heroes, hires four fighters and refuses the fifth; its reward is an epic item');
      await kit.talkTo(w, bot, 'wyrd_captain', 'merc_dismiss');
      // The escort. Everything the server does is real; only the hero's own steps are staged (it stays beside her).
      const eydis = npcs.find(n => n.id === 'wyrd_eydis'), q = find('wyrd_escort');
      const asleep = new Set(w.snapshot.slimes.filter(s => s.dead && s.state === 'waiting').map(s => s.id));
      check(asleep.size === 5, 'Five ambushers sleep before the journey');
      await kit.teleport(w, bot, { npc: 'wyrd_loremaster' });
      await kit.talkTo(w, bot, 'wyrd_loremaster', 'quest:accept:wyrd_escort');
      await w.waitFor(() => state('wyrd_escort'), 5000, 'Accept the escort quest');
      const escortOf = () => w.snapshot.players.find(p => p.escort && p.escort.npc === 'wyrd_eydis');
      await kit.teleport(w, bot, { zone: 6, x: eydis.x, y: eydis.y + 1.2 });
      check(!escortOf(), 'Eydis only stands at the ruined mill until she is spoken to');
      await kit.talkTo(w, bot, 'wyrd_eydis');
      await w.waitFor(escortOf, 5000, 'Eydis joins');
      check(escortOf().look.name === 'Eydis Mapwright' && escortOf().look.class === 'mage' && escortOf().maxHp > 400 && escortOf().escort.owner === w.player(bot).id && w.snapshot.players.filter(p => p.escort).length === 1, 'Eydis Mapwright joins as a tough walking mage owned by the hero');
      const wokeIds = new Set(), began = Date.now();
      let walked = 0, last = { x: eydis.x, y: eydis.y };
      while (escortOf() && state('wyrd_escort').counts[0] < 1 && Date.now() - began < 360000) {
        const e = escortOf();
        await kit.teleport(w, bot, { zone: 6, x: e.x + 1, y: e.y + 1 });
        const foes = w.snapshot.slimes.filter(s => !s.dead && distance(s, e) < 15);
        for (const f of foes) if (asleep.has(f.id)) wokeIds.add(f.id);
        if (foes.length) await kit.killEnemies(w, bot, { ids: foes.map(s => s.id) });
        walked += distance(last, e); last = { x: e.x, y: e.y };
        await w.advance(600);
      }
      check(state('wyrd_escort').counts[0] === 1, 'Eydis reached Skuldwatch alive: the escort objective is done');
      check(wokeIds.size === 5 && [...wokeIds].every(id => asleep.has(id)), 'Both ambushes woke on the way (three crows and two trolls attacked her)');
      const routeLength = eydis.escort.route.reduce((n, p, i, r) => n + Math.hypot(p[0] - (i ? r[i - 1][0] : eydis.x), p[1] - (i ? r[i - 1][1] : eydis.y)), 0);
      check(walked > routeLength * .8 && last.y < 105, `She walked ${Math.round(walked)} tiles of her ${Math.round(routeLength)}-tile route and ended north of the river, over the Troll Bridge`);
      await w.waitFor(() => !escortOf(), 15000, 'Eydis walks off');
      check(w.snapshot.slimes.filter(s => asleep.has(s.id)).every(s => s.dead && s.state === 'waiting'), 'Every ambusher is asleep again');
      await kit.teleport(w, bot, { npc: 'wyrd_loremaster' });
      const gold = w.player(bot).gold;
      await kit.talkTo(w, bot, 'wyrd_loremaster', 'quest:claim:wyrd_escort');
      await w.waitFor(() => state('wyrd_escort').claimed, 5000, 'Claim the escort quest');
      check(w.player(bot).gold === gold + q.rewardGold, `Vigdis pays ${q.rewardGold} gold once`);
      // A second hero fails it: if the hero falls the quest fails, the escort is gone and the quest can be started again at the mill.
      const loser = 'Failer';
      await w.connect({ bot: loser, class: 'mage' });
      await kit.setupCharacter(w, loser, { level: 26, finishQuests: ['wyrd_watch_welcome'] });
      await kit.teleport(w, loser, { npc: 'wyrd_loremaster' });
      await kit.talkTo(w, loser, 'wyrd_loremaster', 'quest:accept:wyrd_escort');
      await w.waitFor(() => quest(w, loser, 'wyrd_escort'), 5000, 'The second hero accepts');
      await kit.teleport(w, loser, { zone: 6, x: eydis.x, y: eydis.y + 1.2 });
      await kit.talkTo(w, loser, 'wyrd_eydis');
      await w.waitFor(() => w.snapshot.players.find(p => p.escort?.owner === w.player(loser).id), 5000, 'The second Eydis joins');
      await w.advance(2000);
      await w.debug(loser, { op: 'die' });
      await w.waitFor(() => !w.snapshot.players.find(p => p.escort?.owner === w.player(loser).id), 8000, 'Eydis is gone when her hero falls');
      check(w.events.some(e => e.bot === loser && (e.type === 'notice' || e.type === 'system') && /Quest failed: Safe Passage/.test(e.text || '')), 'The hero is told the quest failed');
      const failed = quest(w, loser, 'wyrd_escort');
      check(failed.counts[0] === 0 && !failed.claimed, 'The objective is open again');
      await w.waitFor(() => !w.player(loser).dead, 15000, 'The fallen hero wakes');
      await kit.teleport(w, loser, { zone: 6, x: eydis.x, y: eydis.y + 1.2 });
      await kit.talkTo(w, loser, 'wyrd_eydis');
      await w.waitFor(() => w.snapshot.players.find(p => p.escort?.owner === w.player(loser).id), 5000, 'A second try');
      check(true, 'Speaking to Eydis again starts the escort over');
      // Persistence.
      await w.restart();
      check(['wyrd_welcome', 'wyrd_boars', 'wyrd_seal', 'wyrd_trolls', 'wyrd_escort', 'wyrd_beacons', 'wyrd_onward'].every(id => state(id)?.claimed) && state('wyrd_patrol').completions === 3, 'Every claim and the repeatable count survive a private server restart');
    },
  },

  bifrost: {
    description: 'Walk through the Wyrdwood\'s Stormrift up into the level 30-35 Bifrost Reach, check its 56 monster slots (five kinds, eleven sleeping ward ambushers) and their levels, walk the real route over the bridges, prove the void cannot be walked into, fight a level-1 Galehound for its own XP, gold and Gale Fang, keep the zone over a server restart and use both gates.',
    godMode: true,
    async run(w, check) {
      const bot = 'Skywalker';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 32 });
      const up = wyrd.portals.find(p => p.id === 'sky_gate'), down = sky.portals.find(p => p.id === 'stormrift_down');
      check(up && up.to === 7 && down && down.to === 6 && sky.name === 'Bifrost Reach' && sky.levels.join() === '30,35' && sky.size === 160 && sky.theme === 'sky', 'The Wyrdwood has a Stormrift to zone 7, the 160-tile Bifrost Reach of levels 30-35, which has the gate back down');
      check(sky.city.name === "Heimdall's Perch" && !sky.camps && sky.npcs.length === 8 && sky.quests.length === 22, 'The zone has one hub, Heimdall\'s Perch, eight people (seven and a travel master) and 22 quests');
      const rows = sky.sky, onFloor = p => rows[Math.floor(p.y)]?.[Math.floor(p.x)] !== undefined && rows[Math.floor(p.y)][Math.floor(p.x)] !== ' ';
      check(rows.length === 160 && rows.every(r => r.length === 160) && sky.objects.filter(o => o.kind === 'void').length > 300, 'The zone lists its floor and a ring of void obstacles');
      // Staging only: stand in the summit court below the rift. The walk into the gate is real.
      await kit.teleport(w, bot, { zone: 6, x: up.x + 6, y: up.y + 6 });
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 7, 20000, 'Walk up the Stormrift');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: up.tx, y: up.ty };
      check(distance(w.player(bot), arrival) < 1.2, 'The server sets the climber down on the Perch');
      const here = w.snapshot.slimes, kinds = {};
      for (const s of here) kinds[s.kind] = (kinds[s.kind] || 0) + 1;
      check(here.every(s => s.zone === 7) && JSON.stringify(Object.entries(kinds).sort()) === JSON.stringify([['einherjar', 12], ['galehound', 10], ['prismgolem', 10], ['skyray', 11], ['thunderroc', 13]]),
        'A Bifrost client receives exactly its 56 monster slots: 10 galehounds, 10 prism golems, 11 skyrays, 12 einherjar and 13 thunderrocs');
      const asleep = here.filter(s => s.dead && s.state === 'waiting');
      check(asleep.length === 11 && asleep.filter(s => s.kind === 'galehound').length === 2 && asleep.filter(s => s.kind === 'thunderroc').length === 4, 'Eleven ward ambushers sleep until a hero holds their ward');
      const hp = { galehound: 12500, prismgolem: 17500, skyray: 13500, einherjar: 18500, thunderroc: 22000 };
      const living = here.filter(s => !s.dead);
      check(living.length === 45 && living.every(s => Math.abs(s.level - DEFAULT_LEVELS[s.kind]) <= 2) && new Set(living.map(s => s.level - DEFAULT_LEVELS[s.kind])).size >= 3, 'The 45 live monsters roll within two of each default level (30, 31, 32, 33, 35)');
      check(living.every(s => s.maxHp === Math.round(hp[s.kind] * (1 + .12 * (s.level - DEFAULT_LEVELS[s.kind])))), 'Health follows each rolled level');
      check(living.every(s => !s.elite), 'There are no elites in this zone');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Bifrost Reach') && e.text.includes('30–35')), 'The player is told the recommended levels');
      // Another character in Skaldholm shares nothing with the sky.
      await w.connect({ bot: 'Citizen', class: 'mage' });
      await kit.teleport(w, 'Citizen', { zone: 4, x: 80, y: 120 });
      check(w.views.get('Citizen').slimes.length === 0 && w.views.get(bot).slimes.every(s => s.zone === 7) && w.views.get(bot).players.length === 1, 'Each client is sent only its own zone');
      await w.disconnect('Citizen');
      // The first bridge, on foot: the Perch to Windward Meadow.
      const windward = { x: 30, y: 112 }, start = { x: w.player(bot).x, y: w.player(bot).y };
      const path = route(sky, start, windward);
      check(path.length >= 3 && path.every(onFloor), `The route to Windward Meadow is ${path.length} legs, all on the floor`);
      for (const point of path) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .6, 60000, `Walk to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), windward) < 1.5, 'The hero crosses the western bridge on foot');
      // The void cannot be walked into: from the middle of the bridge, step off the side.
      await kit.teleport(w, bot, { zone: 7, x: 43.5, y: 134.5 });
      await w.action(bot, { type: 'move', x: 43.5, y: 118 });
      await w.advance(2500);
      await w.action(bot, { type: 'stop' });
      check(onFloor(w.player(bot)) && w.player(bot).y > 131, `Walking off the side of the bridge stops at its edge (y ${w.player(bot).y.toFixed(1)})`);
      await w.action(bot, { type: 'move', x: 43.5, y: 150 });
      await w.advance(2500);
      await w.action(bot, { type: 'stop' });
      check(onFloor(w.player(bot)) && w.player(bot).y < 137, 'and so does the other side');
      // A level-1 Galehound is a short real fight, and pays its own level (staging: Windward Meadow, away from the pack).
      await kit.teleport(w, bot, { zone: 7, x: 38, y: 100 });
      const before = { ...w.player(bot) };
      const hound = (await kit.spawnEnemy(w, bot, { kind: 'galehound', level: 1, distance: 2.5 })).enemy;
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === hound.id)?.level === 1, 5000, 'See the spawned galehound');
      check(w.snapshot.slimes.find(s => s.id === hound.id).maxHp === Math.round(12500 * .2), 'A level-1 galehound has the floor of 20% of its health (2500)');
      await w.action(bot, { type: 'target', id: hound.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === hound.id).dead, 240000, 'Defeat the galehound');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).kills === before.kills + 1 && totalXp(w.player(bot)) === totalXp(before) + enemyXp(1), `The kill pays the level-1 XP (${enemyXp(1)})`);
      await w.waitFor(() => w.player(bot).gold >= before.gold + 86, 15000, 'Pick up the gold');
      check(w.player(bot).gold === before.gold + 86, 'The kill drops 20% of the galehound gold (86)');
      await w.waitFor(() => w.player(bot).inventory.some(s => s.item === 'gale_fang'), 15000, 'Pick up the fang');
      check(true, 'The galehound drops its Gale Fang');
      // A restart keeps the character in the sky.
      await w.restart();
      check(w.player(bot).zone === 7, 'The character resumes in Bifrost Reach after a server restart');
      // The way back is a real walk to the Stormrift on the Perch, then up again from the court.
      await kit.teleport(w, bot, { zone: 7, x: down.x, y: down.y - 4.5 });
      await w.action(bot, { type: 'move', x: down.x, y: down.y + .8 });
      await w.waitFor(() => w.player(bot).zone === 6, 15000, 'Step through the gate back down');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), { x: down.tx, y: down.ty }) < 1.2, 'The Perch gate sets you down in the summit court beside the Stormrift');
      await w.action(bot, { type: 'move', x: up.x, y: up.y - 1.2 });
      await w.waitFor(() => w.player(bot).zone === 7, 15000, 'Walk up the Stormrift again');
      check(distance(w.player(bot), arrival) < 1.5, 'The Stormrift works again right after arriving');
    },
  },

  sky_quests: {
    description: 'Every ordinary quest of Heimdall\'s Perch played in dependency order through the real accept and claim paths (talk, kill, bring, visit and the new hold objective) with exact XP and gold: the first ward and the vigil are really held, their waves wake, hunt and dissolve; repeatable bounties pay twice; the group quest hires its two fighters; the progression quest arrives by itself.',
    startLevel: 30, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bot = 'Wardholder';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 33, gold: 4000 });
      const defs = sky.quests, npcs = sky.npcs;
      check(npcs.length === 8 && defs.length === 22 && defs.every(q => q.id.startsWith('sky_')), `The Perch holds ${npcs.length} people and ${defs.length} quests`);
      const find = id => defs.find(q => q.id === id);
      const placeOf = id => sky.places.find(p => p.id === id);
      const state = id => quest(w, bot, id);
      const give = (item, quantity) => w.debug(bot, { op: 'give_item', item, quantity });
      const rows = sky.sky;
      const floor = (x, y) => (rows[Math.floor(y)] || '')[Math.floor(x)] > ' ';
      // Three metres from an enemy, on the side that is floor (the island's edge is void).
      const beside = e => [[3, 0], [-3, 0], [0, 3], [0, -3], [2, 2], [-2, -2]].map(([dx, dy]) => ({ x: e.x + dx, y: e.y + dy })).find(p => floor(p.x, p.y) && floor(p.x + Math.sign(p.x - e.x), p.y + Math.sign(p.y - e.y)));
      async function refill(at, radius, n) {
        const live = () => w.snapshot.slimes.filter(s => !s.dead && distance(s, at) < radius).length;
        if (live() >= n) return;
        for (const d of w.snapshot.slimes.filter(s => s.dead && s.state !== 'waiting' && distance(s, at) < radius)) await w.debug(bot, { op: 'respawn_enemy', id: d.id }).catch(e => { if (!/already alive/.test(e.message)) throw e; });
        await w.waitFor(() => live() >= n, 10000, 'The Reach refills');
      }
      // Kills "any" enemy until a quest's counter is full: the Reach's packs are islands apart, so go from one to the next.
      async function killAny(id, index, n) {
        for (let round = 0; round < 12 && (state(id).counts[index] || 0) < n; round++) {
          const live = w.snapshot.slimes.filter(s => !s.dead && !sleeping.has(s.id));
          const next = live.sort((a, b) => distance(a, w.player(bot)) - distance(b, w.player(bot)))[0];
          assert.ok(next, 'A living enemy is available');
          await kit.teleport(w, bot, { zone: 7, ...(beside(next) || next) });
          await kit.killEnemies(w, bot, { radius: 14, max: Math.min(4, n - state(id).counts[index]) });
        }
      }
      const woke = new Set();
      await kit.teleport(w, bot, { zone: 7, x: 80, y: 144 });            // staging: the sky is entered through the Stormrift (see `bifrost`)
      await w.waitFor(() => w.player(bot).zone === 7 && w.snapshot.slimes.some(s => s.zone === 7), 8000, 'Arrive on the Perch');
      const sleepers = () => new Set(w.snapshot.slimes.filter(s => s.dead && s.state === 'waiting').map(s => s.id));
      const sleeping = sleepers();
      check(sleeping.size === 11, 'Eleven ambushers sleep before any ward is held');
      async function playQuest(id) {
        const q = find(id);
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${id}`);
        await w.waitFor(() => state(id) && !state(id).claimed, 5000, `Accept ${id}`);
        for (const [i, o] of q.objectives.entries()) {
          if (o.kind === 'talk') { await kit.teleport(w, bot, { npc: o.target }); await kit.talkTo(w, bot, o.target); }
          else if (o.kind === 'bring') await give(o.target, o.count);
          else if (o.kind === 'visit') { const p = placeOf(o.target); await kit.teleport(w, bot, { zone: 7, x: p.x, y: p.y + 2.4 }); }
          else if (o.kind === 'hold') {
            const p = placeOf(o.target), before = state(id).counts[i];
            await kit.teleport(w, bot, { zone: 7, x: p.x, y: p.y + 2 });
            check(before === 0, `${id}: the ward starts at zero`);
            // Hold the circle. The count must rise by about one a second, and the waves must wake, hunt and, at the end, dissolve.
            const t0 = Date.now(), c0 = state(id).counts[i];
            await w.advance(5200);
            const c1 = state(id).counts[i];
            check(c1 >= 4 && c1 <= 6, `${id}: five seconds in the circle count about five (${c1 - c0})`);
            // stepping out pauses the count
            await kit.teleport(w, bot, { zone: 7, x: p.x + p.r + .9, y: p.y });
            await w.advance(800);
            const c2 = state(id).counts[i];
            await w.advance(2500);
            check(c2 - c1 <= 1 && state(id).counts[i] === c2, `${id}: outside the circle the count pauses at ${c2}`);
            await kit.teleport(w, bot, { zone: 7, x: p.x, y: p.y + 2 });
            const last = Math.max(...p.waves.map(x => x.at));
            while (state(id).counts[i] < o.count && Date.now() - t0 < (o.count + 60) * 1000) {
              for (const s of w.snapshot.slimes) if (!s.dead && sleeping.has(s.id)) woke.add(s.id);
              await w.advance(1000);
            }
            await w.waitFor(() => state(id).counts[i] >= o.count, 20000, `${id} ward held`);
            check(Date.now() - t0 >= (o.count - 12) * 1000, `${id}: a ward of ${o.count} s takes about that long (${Math.round((Date.now() - t0) / 1000)} s)`);
            check(woke.size >= 1 && last < o.count, `${id}: its waves woke (${woke.size} enemies so far) before the end`);
            await w.advance(500);
            check(w.snapshot.slimes.filter(s => sleeping.has(s.id)).every(s => s.dead && s.state === 'waiting'), `${id}: when the ward holds every wave dissolves`);
          }
          else if (o.kind === 'kill') {
            if (o.target === 'any') { await kit.teleport(w, bot, { npc: q.npc }); await refill({ x: 80, y: 90 }, 90, o.count + 2); await killAny(id, i, o.count); }
            else {
              const alive = () => w.snapshot.slimes.filter(s => !s.dead && s.kind === o.target && !sleeping.has(s.id)).length;
              if (alive() < o.count) {
                for (const d of w.snapshot.slimes.filter(s => s.dead && s.kind === o.target && s.state !== 'waiting').slice(0, o.count - alive())) await w.debug(bot, { op: 'respawn_enemy', id: d.id }).catch(e => { if (!/already alive/.test(e.message)) throw e; });
                await w.waitFor(() => alive() >= o.count, 10000, `Respawn ${o.target}`);
              }
            }
            if (o.target === 'any') { await w.waitFor(() => (state(id).counts[i] || 0) >= o.count, 8000, `${id} patrol`); continue; }
            const targets = w.snapshot.slimes.filter(s => !s.dead && !sleeping.has(s.id) && s.kind === o.target);
            const first = targets.sort((a, b) => distance(a, w.player(bot)) - distance(b, w.player(bot)))[0];
            if (first) { const spot = beside(first) || { x: first.x, y: first.y }; await kit.teleport(w, bot, { zone: 7, ...spot }); }
            const done = await kit.killEnemies(w, bot, { kind: o.target, max: o.count });
            assert.ok(done.count >= o.count, `Killed enough ${o.target}`);
          } else throw Error(`${id}: unexpected objective ${o.kind}`);
          await w.waitFor(() => (state(id).counts[i] || 0) >= Math.min(o.count, o.kind === 'kill' ? 99 : o.count), 8000, `${id} objective ${i}`);
        }
        await w.waitFor(() => state(id).counts.every((c, i) => c >= q.objectives[i].count), 8000, `${id} is ready`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        const held = item => w.player(bot).inventory.filter(s => s.item === item).reduce((n, s) => n + s.quantity, 0);
        const bringing = q.objectives.filter(o => o.kind === 'bring').map(o => [o.target, o.count, held(o.target)]);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${id}`);
        await w.waitFor(() => state(id).claimed, 5000, `Claim ${id}`);
        for (const [item, count, had] of bringing) check(held(item) === had - count, `${id}: the hand-in took exactly ${count} ${item}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + levelXp[q.level - 1] / 10, `${id}: the claim pays ${q.rewardGold} gold and a tenth of level ${q.level}'s XP`);
        return q;
      }
      // Dependency order: every ordinary quest, none of the group quest or the progression quest (it arrives by itself).
      const skip = new Set(['sky_ward_last', 'sky_onward']);
      const order = [], seen = new Set();
      const visit = q => { if (seen.has(q.id) || skip.has(q.id)) return; seen.add(q.id); if (q.requires && !skip.has(q.requires)) visit(find(q.requires)); order.push(q); };
      defs.forEach(visit);
      const tally = {};
      for (const q of order) { await playQuest(q.id); for (const o of q.objectives) tally[o.kind] = (tally[o.kind] || 0) + 1; }
      check(order.length >= 19 && ['talk', 'kill', 'bring', 'visit'].every(k => tally[k] >= 3) && tally.hold === 2, `${order.length} quests played end to end: ${JSON.stringify(tally)}`);
      const onward = state('sky_onward');
      check(onward && onward.counts[0] === 1 && !onward.claimed, 'The level-30 progression quest arrived by itself and already counts: the hero stands in Bifrost Reach');
      await kit.teleport(w, bot, { npc: 'sky_warden' });
      await kit.talkTo(w, bot, 'sky_warden', 'quest:claim:sky_onward');
      await w.waitFor(() => state('sky_onward').claimed, 5000, 'Claim the progression quest');
      // The repeatable patrol can be taken and paid again.
      const rep = find('sky_patrol');
      for (let round = 0; round < 2; round++) {
        const before = { gold: w.player(bot).gold, completions: state('sky_patrol').completions };
        await kit.teleport(w, bot, { npc: rep.npc });
        await kit.talkTo(w, bot, rep.npc, 'quest:accept:sky_patrol');
        await w.waitFor(() => !state('sky_patrol').claimed, 5000, 'Take the patrol again');
        await refill({ x: 80, y: 90 }, 90, 16);
        await killAny('sky_patrol', 0, 14);
        await w.waitFor(() => state('sky_patrol').counts[0] === 14, 8000, 'Patrol count');
        await kit.teleport(w, bot, { npc: rep.npc });
        await w.advance(1500);                                     // let the last drops settle before the gold is read
        before.gold = w.player(bot).gold;
        await kit.talkTo(w, bot, rep.npc, 'quest:claim:sky_patrol');
        await w.waitFor(() => state('sky_patrol').completions === before.completions + 1, 5000, 'Patrol paid');
        check(w.player(bot).gold === before.gold + rep.rewardGold, `The repeatable patrol pays ${rep.rewardGold} gold again (round ${round + 1})`);
      }
      // The group quest: the giver hires exactly the missing fighters, up to the quest's party size.
      const mercs = () => w.snapshot.players.filter(p => /^Merc /.test(p.look.name)).length;
      await kit.teleport(w, bot, { npc: 'sky_warden' });
      await kit.talkTo(w, bot, 'sky_warden', 'quest:accept:sky_ward_last');
      await w.waitFor(() => state('sky_ward_last'), 5000, 'Accept the Last Ward');
      for (const c of ['warrior', 'priest', 'mage']) await kit.talkTo(w, bot, 'sky_warden', `merc_${c}`);
      await w.waitFor(() => mercs() === 2, 8000, 'Two fighters join');
      const last = find('sky_ward_last');
      check(mercs() === 2 && last.recommendedPlayers === 3 && last.rewardItem === 'pants_wayfarer_l20_purple' && last.objectives[0].kind === 'hold' && last.objectives[0].count === 120, 'The Last Ward wants three heroes for 120 s, hires two fighters and refuses the third; its reward is an epic item');
      await kit.talkTo(w, bot, 'sky_warden', 'merc_dismiss');
      await w.waitFor(() => mercs() === 0, 8000, 'Send them away');
      // Falling at a ward loses the count: the hero dies inside the Last Ward's circle and the objective starts over.
      const ward = placeOf('sky_ward_last');
      await kit.teleport(w, bot, { zone: 7, x: ward.x, y: ward.y + 2 });
      await w.advance(4300);
      check(state('sky_ward_last').counts[0] >= 3, `Three seconds of the Last Ward are counted (${state('sky_ward_last').counts[0]})`);
      await w.debug(bot, { op: 'set_god_mode', enabled: false });
      await w.debug(bot, { op: 'die' });
      await w.waitFor(() => state('sky_ward_last').counts[0] === 0, 6000, 'The ward collapses');
      check(w.events.some(e => e.bot === bot && /collapses/.test(e.text || '')), 'The hero is told the ward collapsed');
      // Persistence.
      await w.restart();
      check(['sky_welcome', 'sky_hounds', 'sky_ward_wind', 'sky_ward_vigil', 'sky_onward'].every(id => state(id)?.claimed) && state('sky_patrol').completions === 3, 'Every claimed quest and the repeatable\'s count survive a restart');
    },
  },
  deep: {
    description: 'Fall through the Roc\'s Eyrie\'s Maelstrom into the level 35-40 Ran\'s Deep, check its 53 monster slots (six kinds and three elites: the Kraken, Hvitserk and the Ghostmaw) and their levels, walk the real route to the Pearl Gate, prove the coral walls cannot be walked through, fight a level-1 Drowned Draugr for its own XP, gold and Drowned Coin, keep the zone over a server restart and use both Maelstrom gates.',
    godMode: true,
    async run(w, check) {
      const bot = 'Diver';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 37 });
      const down = sky.portals.find(p => p.id === 'maelstrom_down'), up = deep.portals.find(p => p.id === 'maelstrom_up');
      const NAME = "Rán's Deep";
      check(down && down.to === 8 && up && up.to === 7 && deep.name === NAME && deep.levels.join() === '35,40' && deep.size === 176 && deep.theme === 'deep', 'The Roc\'s Eyrie has a Maelstrom to zone 8, the 176-tile Ran\'s Deep of levels 35-40, which has the Maelstrom back up');
      check(deep.city.name === 'Keelhaven' && !deep.camps && deep.npcs.length === 8 && deep.quests.length === 24, 'The zone has one hub, Keelhaven, eight people (seven and a travel master) and 24 quests');
      check(deep.objects.filter(o => o.kind === 'reefwall').length > 300 && deep.places.filter(p => p.chain).length === 12, 'The Net is built of hundreds of coral wall pieces, and twelve tidebells stand in three chains');
      // Staging only: stand on the Eyrie beside the spout. The step into the Maelstrom is real.
      await kit.teleport(w, bot, { zone: 7, x: down.x, y: down.y + 5 });
      await w.action(bot, { type: 'move', x: down.x, y: down.y + .3 });
      await w.waitFor(() => w.player(bot).zone === 8, 20000, 'Step into the Maelstrom');
      await w.action(bot, { type: 'stop' });
      const arrival = { x: down.tx, y: down.ty };
      check(distance(w.player(bot), arrival) < 1.2, 'The server sets the diver down in Keelhaven');
      const here = w.snapshot.slimes, kinds = {};
      for (const s of here) kinds[s.kind] = (kinds[s.kind] || 0) + 1;
      check(here.every(s => s.zone === 8) && JSON.stringify(Object.entries(kinds).sort()) === JSON.stringify([['angler', 10], ['draugr', 11], ['ghostmaw', 1], ['hvitserk', 1], ['kraken', 1], ['moray', 10], ['shellback', 9], ['siren', 10]]),
        'A Ran\'s Deep client receives exactly its 53 monster slots: 11 draugr, 10 anglers, 10 morays, 10 sirens, 9 shellbacks and the three elites');
      const hp = { draugr: 24000, angler: 20500, moray: 27000, siren: 23500, shellback: 40000, kraken: 280000, hvitserk: 150000, ghostmaw: 190000 };
      check(here.every(s => !s.dead) && here.every(s => Math.abs(s.level - DEFAULT_LEVELS[s.kind]) <= 2), 'Every monster is awake and rolls within two of its default level');
      check(here.every(s => s.maxHp === Math.round(hp[s.kind] * (1 + .12 * (s.level - DEFAULT_LEVELS[s.kind])))), 'Health follows each rolled level');
      check(here.filter(s => s.elite).map(s => s.kind).sort().join() === 'ghostmaw,hvitserk,kraken', 'Exactly the Kraken, Hvitserk and the Ghostmaw are elites');
      check(w.events.some(e => e.bot === bot && e.type === 'event' && e.kind === 'portal'), 'The gate announces a portal event');
      check(w.events.some(e => e.type === 'system' && e.text.includes('Deep') && e.text.includes('35–40')), 'The player is told the recommended levels');
      // Another character in Skaldholm shares nothing with the sea floor.
      await w.connect({ bot: 'Citizen', class: 'mage' });
      await kit.teleport(w, 'Citizen', { zone: 4, x: 80, y: 120 });
      check(w.views.get('Citizen').slimes.length === 0 && w.views.get(bot).slimes.every(s => s.zone === 8) && w.views.get(bot).players.length === 1, 'Each client is sent only its own zone');
      await w.disconnect('Citizen');
      // The way to the Pearl Gate, on foot, through the real collision geometry.
      const gate = { x: 80, y: 124.5 }, start = { x: w.player(bot).x, y: w.player(bot).y };
      const path = route(deep, start, gate);
      check(path.length >= 2, `The route to the Pearl Gate is ${path.length} legs`);
      for (const point of path) {
        await w.action(bot, { type: 'move', ...point });
        await w.waitFor(() => distance(w.player(bot), point) < .6, 60000, `Walk to ${Math.round(point.x)},${Math.round(point.y)}`);
      }
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), gate) < 1.5, 'The diver walks from Keelhaven to the Net\'s door');
      // The coral cannot be walked through: the south wall of the maze beside the door, and the outer wall.
      await kit.teleport(w, bot, { zone: 8, x: 60, y: 126 });
      await w.action(bot, { type: 'move', x: 60, y: 108 });
      await w.advance(2500);
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).y > 121.4, `Walking north into the maze's south wall stops in front of it (y ${w.player(bot).y.toFixed(1)})`);
      await kit.teleport(w, bot, { zone: 8, x: 16, y: 100 });
      await w.action(bot, { type: 'move', x: 1, y: 100 });
      await w.advance(2500);
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).x > 9.4, `and so does the outer wall (x ${w.player(bot).x.toFixed(1)})`);
      // Through the door, into the first corridor: the way in is open.
      await kit.teleport(w, bot, { zone: 8, x: 80, y: 126 });
      await w.action(bot, { type: 'move', x: 80, y: 108 });
      await w.waitFor(() => w.player(bot).y < 110, 15000, 'Walk through the door');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).y < 110, 'The Net\'s door lets a hero in');
      // A level-1 Draugr is a short real fight, and pays its own level (staging: the west Shallows, away from the packs).
      await kit.teleport(w, bot, { zone: 8, x: 40, y: 134 });
      const before = { ...w.player(bot) };
      const dead = (await kit.spawnEnemy(w, bot, { kind: 'draugr', level: 1, distance: 2.5 })).enemy;
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === dead.id)?.level === 1, 5000, 'See the spawned draugr');
      check(w.snapshot.slimes.find(s => s.id === dead.id).maxHp === Math.round(24000 * .2), 'A level-1 draugr has the floor of 20% of its health (4800)');
      await w.action(bot, { type: 'target', id: dead.id });
      await w.waitFor(() => w.snapshot.slimes.find(s => s.id === dead.id).dead, 240000, 'Defeat the draugr');
      await w.action(bot, { type: 'stop' });
      check(w.player(bot).kills === before.kills + 1 && totalXp(w.player(bot)) === totalXp(before) + enemyXp(1), `The kill pays the level-1 XP (${enemyXp(1)})`);
      await w.waitFor(() => w.player(bot).gold >= before.gold + 128, 15000, 'Pick up the gold');
      check(w.player(bot).gold === before.gold + 128, 'The kill drops 20% of the draugr gold (128)');
      await w.waitFor(() => w.player(bot).inventory.some(s => s.item === 'drowned_coin'), 15000, 'Pick up the coin');
      check(true, 'The draugr drops its Drowned Coin');
      // A restart keeps the character on the sea floor.
      await w.restart();
      check(w.player(bot).zone === 8, 'The character resumes in Ran\'s Deep after a server restart');
      // The way back up is a real walk into Keelhaven's Maelstrom, and down again from the Eyrie.
      await kit.teleport(w, bot, { zone: 8, x: up.x, y: up.y - 4.5 });
      await w.action(bot, { type: 'move', x: up.x, y: up.y + .5 });
      await w.waitFor(() => w.player(bot).zone === 7, 15000, 'Step through the Maelstrom back up');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), { x: up.tx, y: up.ty }) < 1.2, 'Keelhaven\'s Maelstrom sets you down on the Roc\'s Eyrie beside the spout');
      await w.action(bot, { type: 'move', x: down.x, y: down.y });
      await w.waitFor(() => w.player(bot).zone === 8, 15000, 'Dive again');
      check(distance(w.player(bot), arrival) < 1.5, 'The Maelstrom works again right after arriving');
    },
  },

  deep_quests: {
    description: 'Every ordinary quest of Keelhaven played in dependency order through the real accept and claim paths (talk, kill, bring, visit and the new chime objective) with exact XP and gold: each bell chain is really rung in real time (a chain rung too slowly fails and its count falls as the bells go silent); repeatable bounties pay twice; both group quests hire their fighters; the Ghostmaw has no quest; the progression quest arrives by itself.',
    startLevel: 35, godMode: true, levelSpread: 0,
    async run(w, check) {
      const bot = 'Bellringer';
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { level: 40, gold: 9000 });
      const defs = deep.quests, npcs = deep.npcs;
      check(npcs.length === 8 && defs.length === 24 && defs.every(q => q.id.startsWith('deep_')), `Keelhaven holds ${npcs.length} people and ${defs.length} quests`);
      const find = id => defs.find(q => q.id === id);
      const placeOf = id => deep.places.find(p => p.id === id);
      const state = id => quest(w, bot, id);
      const give = (item, quantity) => w.debug(bot, { op: 'give_item', item, quantity });
      const bellsOf = chain => deep.places.filter(p => p.chain === chain);
      const spot = p => p.id === 'deep_garden' ? { x: p.x, y: p.y } : { x: p.x, y: p.y + 2 };
      const elites = () => w.snapshot.slimes.filter(s => s.elite);
      const nearElite = p => elites().some(e => distance(e, p) < 24);
      const sleeping = new Set();
      async function refill(kind, n) {
        const alive = () => w.snapshot.slimes.filter(s => !s.dead && s.kind === kind).length;
        if (alive() >= n) return;
        for (const d of w.snapshot.slimes.filter(s => s.dead && s.kind === kind).slice(0, n - alive())) await w.debug(bot, { op: 'respawn_enemy', id: d.id }).catch(e => { if (!/already alive/.test(e.message)) throw e; });
        await w.waitFor(() => alive() >= n, 10000, `Respawn ${kind}`);
      }
      // Kills "any" enemy until a quest counter is full, going from pack to pack and keeping away from the elites.
      async function killAny(id, index, n) {
        for (let round = 0; round < 20 && (state(id).counts[index] || 0) < n; round++) {
          const live = w.snapshot.slimes.filter(s => !s.dead && !s.elite && !nearElite(s));
          const next = live.sort((a, b) => distance(a, w.player(bot)) - distance(b, w.player(bot)))[0];
          assert.ok(next, 'A living enemy is available');
          await kit.teleport(w, bot, { zone: 8, x: next.x + 3, y: next.y });
          await kit.killEnemies(w, bot, { radius: 8, max: Math.min(3, n - state(id).counts[index]) });
        }
      }
      await kit.teleport(w, bot, { zone: 8, x: 80, y: 162 });            // staging: the deep is entered through the Maelstrom (see `deep`)
      await w.waitFor(() => w.player(bot).zone === 8 && w.snapshot.slimes.some(s => s.zone === 8), 8000, 'Arrive in Keelhaven');
      // The chime: ring every bell of a chain in order, `gap` ms apart; the count must follow the bells that are still sounding.
      async function ringChain(id, i, chain, gap) {
        const bells = bellsOf(chain), burn = bells[0].burn;
        await kit.teleport(w, bot, { zone: 8, x: 80, y: 162 });
        check(state(id).counts[i] === 0, `${id}: no bell rings before the hero reaches one`);
        for (const [k, b] of bells.entries()) {
          await kit.teleport(w, bot, { zone: 8, ...spot(b) });
          await w.waitFor(() => state(id).counts[i] >= Math.min(k + 1, bells.length), 4000, `${b.id} rings`);
          check(state(id).counts[i] === k + 1 || k === bells.length - 1, `${id}: bell ${k + 1} of ${bells.length} sounds at once (${state(id).counts[i]} ringing)`);
          if (k < bells.length - 1) { await kit.teleport(w, bot, { zone: 8, x: 80, y: 162 }); await w.advance(gap); }
        }
        await w.waitFor(() => state(id).counts[i] >= bells.length, 5000, `${id} chain rung`);
        check(state(id).counts[i] === bells.length, `${id}: all ${bells.length} bells rang at once within the ${burn} s window`);
      }
      const pause = async ms => { while (ms > 0) { const d = Math.min(ms, 25000); await w.advance(d); ms -= d; } };
      async function failChain(id, i, chain) {
        const bells = bellsOf(chain), burn = bells[0].burn;
        await kit.teleport(w, bot, { zone: 8, ...spot(bells[0]) });
        await w.waitFor(() => state(id).counts[i] === 1, 4000, 'The first bell rings');
        await kit.teleport(w, bot, { zone: 8, x: 80, y: 162 });
        await pause((burn + 2) * 1000);
        check(state(id).counts[i] === 0, `${id}: a bell goes silent after its ${burn} s and takes its share of the count with it`);
        check(w.events.some(e => e.bot === bot && /falls silent/.test(e.text || '')), `${id}: the hero is told the last bell fell silent`);
        await kit.teleport(w, bot, { zone: 8, ...spot(bells[1]) });
        await w.waitFor(() => state(id).counts[i] === 1, 4000, 'Another bell rings alone');
        await kit.teleport(w, bot, { zone: 8, x: 80, y: 162 });
        await w.advance(500);
        check(state(id).counts[i] === 1 && state(id).counts[i] < bells.length, `${id}: a slow hero has rung one bell, not the chain`);
        await pause((burn + 1) * 1000);
      }
      async function playQuest(id) {
        const q = find(id);
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${id}`);
        await w.waitFor(() => state(id) && !state(id).claimed, 5000, `Accept ${id}`);
        for (const [i, o] of q.objectives.entries()) {
          if (o.kind === 'talk') { await kit.teleport(w, bot, { npc: o.target }); await kit.talkTo(w, bot, o.target); }
          else if (o.kind === 'bring') await give(o.target, o.count);
          else if (o.kind === 'visit') { const p = placeOf(o.target); await kit.teleport(w, bot, { zone: 8, ...spot(p) }); }
          else if (o.kind === 'chime') {
            const gap = { deep_harbour: 9000, deep_net: 9000, deep_rans: 8500 }[o.target];
            if (o.target === 'deep_harbour') await failChain(id, i, o.target);
            await ringChain(id, i, o.target, gap);
          }
          else if (o.kind === 'kill') {
            if (o.target === 'any') { await kit.teleport(w, bot, { npc: q.npc }); await killAny(id, i, o.count); await w.waitFor(() => (state(id).counts[i] || 0) >= o.count, 8000, `${id} patrol`); continue; }
            await refill(o.target, o.count);
            const targets = w.snapshot.slimes.filter(s => !s.dead && s.kind === o.target && !nearElite(s));
            const first = targets.sort((a, b) => distance(a, w.player(bot)) - distance(b, w.player(bot)))[0];
            assert.ok(first, `A living ${o.target} away from the elites`);
            await kit.teleport(w, bot, { zone: 8, x: first.x + 3, y: first.y });
            const done = await kit.killEnemies(w, bot, { kind: o.target, max: o.count });
            assert.ok(done.count >= o.count, `Killed enough ${o.target}`);
          } else throw Error(`${id}: unexpected objective ${o.kind}`);
          await w.waitFor(() => (state(id).counts[i] || 0) >= Math.min(o.count, o.kind === 'kill' ? 99 : o.count), 8000, `${id} objective ${i}`);
        }
        await w.waitFor(() => state(id).counts.every((c, i) => c >= q.objectives[i].count), 8000, `${id} is ready`);
        await kit.teleport(w, bot, { npc: q.npc });
        const before = { gold: w.player(bot).gold, xp: totalXp(w.player(bot)) };
        const held = item => w.player(bot).inventory.filter(s => s.item === item).reduce((n, s) => n + s.quantity, 0);
        const bringing = q.objectives.filter(o => o.kind === 'bring').map(o => [o.target, o.count, held(o.target)]);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${id}`);
        await w.waitFor(() => state(id).claimed, 5000, `Claim ${id}`);
        for (const [item, count, had] of bringing) check(held(item) === had - count, `${id}: the hand-in took exactly ${count} ${item}`);
        check(w.player(bot).gold === before.gold + q.rewardGold && totalXp(w.player(bot)) === before.xp + levelXp[q.level - 1] / 10, `${id}: the claim pays ${q.rewardGold} gold and a tenth of level ${q.level}'s XP`);
        return q;
      }
      // Dependency order: every ordinary quest, none of the elite quests, the capstone or the progression quest.
      const skip = new Set(['deep_kraken', 'deep_captain', 'deep_vanguard', 'deep_onward']);
      const order = [], seen = new Set();
      const visit = q => { if (seen.has(q.id) || skip.has(q.id)) return; seen.add(q.id); if (q.requires && !skip.has(q.requires)) visit(find(q.requires)); order.push(q); };
      defs.forEach(visit);
      const tally = {};
      for (const q of order) { await playQuest(q.id); for (const o of q.objectives) tally[o.kind] = (tally[o.kind] || 0) + 1; }
      check(order.length >= 19 && ['talk', 'kill', 'bring', 'visit'].every(k => tally[k] >= 3) && tally.chime === 3, `${order.length} quests played end to end: ${JSON.stringify(tally)}`);
      const onward = state('deep_onward');
      check(onward && onward.counts[0] === 1 && !onward.claimed, 'The level-35 progression quest arrived by itself and already counts: the hero stands in Ran\'s Deep');
      await kit.teleport(w, bot, { npc: 'deep_warden' });
      await kit.talkTo(w, bot, 'deep_warden', 'quest:claim:deep_onward');
      await w.waitFor(() => state('deep_onward').claimed, 5000, 'Claim the progression quest');
      // The repeatable patrol can be taken and paid again.
      const rep = find('deep_patrol');
      for (let round = 0; round < 2; round++) {
        const before = { completions: state('deep_patrol').completions };
        await kit.teleport(w, bot, { npc: rep.npc });
        await kit.talkTo(w, bot, rep.npc, 'quest:accept:deep_patrol');
        await w.waitFor(() => !state('deep_patrol').claimed, 5000, 'Take the patrol again');
        for (const kind of ['draugr', 'angler', 'moray', 'siren', 'shellback']) await refill(kind, 4);
        await killAny('deep_patrol', 0, 14);
        await w.waitFor(() => state('deep_patrol').counts[0] === 14, 8000, 'Patrol count');
        await kit.teleport(w, bot, { npc: rep.npc });
        await w.advance(1500);
        before.gold = w.player(bot).gold;
        await kit.talkTo(w, bot, rep.npc, 'quest:claim:deep_patrol');
        await w.waitFor(() => state('deep_patrol').completions === before.completions + 1, 5000, 'Patrol paid');
        check(w.player(bot).gold === before.gold + rep.rewardGold, `The repeatable patrol pays ${rep.rewardGold} gold again (round ${round + 1})`);
      }
      // The two group quests: the giver hires exactly the missing fighters, up to the quest's party size.
      const mercs = () => w.snapshot.players.filter(p => /^Merc /.test(p.look.name)).length;
      for (const [id, size, kind, reward] of [['deep_captain', 3, 'hvitserk', 'accessory_amber_l20_blue'], ['deep_kraken', 5, 'kraken', 'necklace_moonstone_l20_purple']]) {
        const g = find(id);
        await kit.teleport(w, bot, { npc: g.npc });
        await kit.talkTo(w, bot, g.npc, `quest:accept:${id}`);
        await w.waitFor(() => state(id), 5000, `Accept ${id}`);
        for (const c of ['warrior', 'priest', 'mage', 'hunter', 'assassin', 'warrior']) await kit.talkTo(w, bot, g.npc, `merc_${c}`);
        await w.waitFor(() => mercs() === size - 1, 8000, 'The missing fighters join');
        check(mercs() === size - 1 && g.group && g.recommendedPlayers === size && g.rewardItem === reward && g.objectives[0].kind === 'kill' && g.objectives[0].target === kind, `${id} wants ${size} heroes, hires ${size - 1} fighters and refuses more; its reward is ${reward}`);
        await kit.talkTo(w, bot, g.npc, 'merc_dismiss');
        await w.waitFor(() => mercs() === 0, 8000, 'Send them away');
      }
      check(!defs.some(q => q.objectives.some(o => o.target === 'ghostmaw')) && w.snapshot.slimes.some(s => s.kind === 'ghostmaw' && s.elite), 'The Ghostmaw is an elite no quest asks for');
      // Persistence.
      await w.restart();
      check(['deep_welcome', 'deep_draugr', 'deep_harbour', 'deep_net', 'deep_rans', 'deep_onward'].every(id => state(id)?.claimed) && state('deep_patrol').completions === 3, 'Every claimed quest and the repeatable\'s count survive a restart');
    },
  },

  nacrehold: {
    description: 'Nacrehold: real paired Tideway entries, safe houses and authoritative collision, local view isolation, merfolk dialogue, services, Meeting Stone hire/dismiss, Spark discovery and flight, persisted city and quests after Rust restart.',
    startLevel: 40,
    async run(w, check) {
      const bot = 'Pearlwalker', watcher = 'Surface';
      await w.connect({ bot, class: 'warrior' });
      await w.connect({ bot: watcher, class: 'mage' });
      await kit.setupCharacter(w, bot, { gold: 2000 });
      const town = map.zones[8], gate = deep.portals.find(p => p.id === 'nacre_gate'), back = town.portals[0];
      check(town.objects.filter(o => o.kind === 'nacrehouse').length === 120 && town.npcs.length === 30 && town.slimes.length === 0, '120 homes, 30 people, no enemies');
      check(town.futureInstance.status === 'sealed' && town.futureInstance.players === 5 && town.portals.length === 1, 'The future Drowned Cathedral is sealed, beside its Meeting Stone');
      await kit.teleport(w, bot, { npc: 'travel_keelhaven' });
      await kit.talkTo(w, bot, 'travel_keelhaven');
      await kit.teleport(w, bot, { zone: 8, x: gate.x, y: gate.y - 4 });
      await w.action(bot, { type: 'move', x: gate.x, y: gate.y });
      await w.waitFor(() => w.player(bot).zone === 9, 15000, 'Walk into the Tideway');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), { x: gate.tx, y: gate.ty }) < 1.5, 'The Tideway arrives at the south city boulevard');
      const view = b => w.views.get(b);
      check(view(bot).slimes.length === 0 && view(bot).players.every(p => p.zone === 9) && view(watcher).players.every(p => p.zone === 0), 'City and meadow sockets receive separate zone views');
      const reply = await kit.talkTo(w, bot, 'nacre_envoy', 'quest:accept:nacre_welcome');
      await w.waitFor(() => !!quest(w, bot, 'nacre_welcome'));
      check(reply.dialogue.includes('hundred and twenty') && !!quest(w, bot, 'nacre_welcome'), 'The mermaid envoy introduces the city and accepts its quest');
      await kit.walkTo(w, bot, { zone: 9, x: 96, y: 151 });
      check(distance(w.player(bot), { x: 96, y: 151 }) < .6, 'A real walk follows the clear residential avenue');
      const house = town.objects.find(o => o.kind === 'nacrehouse' && o.y === 151);
      await kit.teleport(w, bot, { zone: 9, x: house.x, y: house.y + 4 });
      await w.action(bot, { type: 'move', x: house.x, y: house.y });
      await w.advance(1800); await w.action(bot, { type: 'stop' });
      check(w.player(bot).y > house.y + house.depth / 2, 'The server blocks movement into a shell home');
      await kit.teleport(w, bot, { npc: 'nacre_healer' });
      await w.debug(bot, { op: 'set_hp', hp: 1 });
      await kit.talkTo(w, bot, 'nacre_healer', 'blessing');
      await w.waitFor(() => w.player(bot).hp === w.player(bot).maxHp);
      check(w.player(bot).hp === w.player(bot).maxHp, 'The tide healer restores health through the real offer');
      await kit.teleport(w, bot, { npc: 'nacre_trader' });
      const gold = w.player(bot).gold;
      await kit.talkTo(w, bot, 'nacre_trader', 'satchel');
      await w.waitFor(() => w.player(bot).gold === gold - 500);
      check(w.player(bot).gold === gold - 500 && w.player(bot).bagCapacity === 22, 'The market sells the authoritative six-slot satchel for 500 gold');
      await kit.teleport(w, bot, { npc: 'nacre_stone' });
      const g = w.player(bot).gold;
      await kit.talkTo(w, bot, 'nacre_stone', 'merc_priest');
      await w.waitFor(() => view(bot).players.some(p => /^Merc /.test(p.look.name)) && w.player(bot).gold === g - 250);
      check(w.player(bot).gold === g - 250 && view(bot).players.some(p => /^Merc /.test(p.look.name) && p.look.class === 'priest'), 'The Meeting Stone hires a priest for 250 gold');
      await kit.talkTo(w, bot, 'nacre_stone', 'merc_dismiss');
      await w.waitFor(() => !view(bot).players.some(p => /^Merc /.test(p.look.name)));
      check(!view(bot).players.some(p => /^Merc /.test(p.look.name)), 'The stone dismisses hired companions');
      await kit.teleport(w, bot, { npc: 'travel_nacrehold' });
      await kit.talkTo(w, bot, 'travel_nacrehold');
      await w.waitFor(() => w.player(bot).travelStops.includes('travel_nacrehold'));
      check(w.player(bot).travelStops.includes('travel_nacrehold'), 'Speaking to the mermaid travel master discovers Nacrehold');
      await w.restart();
      check(w.player(bot).zone === 9 && w.player(bot).travelStops.includes('travel_nacrehold') && quest(w, bot, 'nacre_welcome'), 'City position, discovery and accepted quest survive Rust restart');
      const fare = w.player(bot).gold;
      await w.advance(550);
      await w.action(bot, { type: 'interact', npc: 'travel_nacrehold', offer: 'spark:travel_keelhaven' });
      await w.waitFor(() => !w.player(bot).sparkTravel && w.player(bot).zone === 8, 30000, 'Fly to Keelhaven');
      check(w.player(bot).gold === fare - 20 && distance(w.player(bot), deep.npcs.find(n => n.id === 'travel_keelhaven')) < 2, 'The linked Spark flight costs 20 gold and reaches Keelhaven');
      await kit.teleport(w, bot, { zone: 8, x: gate.x, y: gate.y - 4 });
      await w.action(bot, { type: 'move', x: gate.x, y: gate.y });
      await w.waitFor(() => w.player(bot).zone === 9, 15000);
      await w.action(bot, { type: 'stop' });
      await w.advance(1200);
      await w.action(bot, { type: 'move', x: back.x, y: back.y });
      await w.waitFor(() => w.player(bot).zone === 8, 15000, 'Walk back to the sea floor');
      await w.action(bot, { type: 'stop' });
      check(distance(w.player(bot), { x: back.tx, y: back.ty }) < 1.5, 'The return Tideway arrives outside its gate disc');
    },
  },
  nacre_quests: {
    description: 'Play all nine Nacrehold quests through authoritative NPC offers: real talks and visits, hand-in item consumption, exact XP/gold, locked and duplicate rewards, repeatable supply order and persisted ledger.',
    startLevel: 40,
    async run(w, check) {
      const bot = 'Shellcourier', town = map.zones[8];
      await w.connect({ bot, class: 'warrior' });
      await kit.setupCharacter(w, bot, { gold: 0 });
      await kit.teleport(w, bot, { npc: 'nacre_warden' });
      await kit.talkTo(w, bot, 'nacre_warden', 'quest:accept:nacre_cathedral');
      check(!quest(w, bot, 'nacre_cathedral'), 'The Cathedral preparation requires the city history first');
      for (const q of town.quests) {
        await kit.teleport(w, bot, { npc: q.npc });
        await kit.talkTo(w, bot, q.npc, `quest:accept:${q.id}`);
        await w.waitFor(() => !!quest(w, bot, q.id));
        const refused = await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(/Complete the objectives/.test(refused.notice), `${q.title}: unfinished claim refused`);
        for (const o of q.objectives) {
          if (o.kind === 'talk') {
            await kit.teleport(w, bot, { npc: o.target });
            await kit.talkTo(w, bot, o.target);
          } else if (o.kind === 'visit') {
            const p = town.places.find(p => p.id === o.target);
            await kit.teleport(w, bot, { zone: 9, x: p.x, y: p.y });
            await w.advance(150);
          } else await w.debug(bot, { op: 'give_item', item: o.target, quantity: o.count });
        }
        await w.waitFor(() => quest(w, bot, q.id).counts.every((n, i) => n === q.objectives[i].count));
        await kit.teleport(w, bot, { npc: q.npc });
        const before = w.player(bot).gold, xp = totalXp(w.player(bot));
        const bag = id => w.player(bot).inventory.find(i => i.item === id)?.quantity || 0;
        const handed = q.objectives.filter(o => o.kind === 'bring').map(o => [o, bag(o.target)]);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        await w.waitFor(() => quest(w, bot, q.id).claimed);
        check(w.player(bot).gold === before + q.rewardGold && totalXp(w.player(bot)) === xp + q.rewardXp, `${q.title}: exact level-table XP and gold`);
        check(handed.every(([o, n]) => bag(o.target) === n - o.count), `${q.title}: hand-in consumes exactly the requested items`);
        await kit.talkTo(w, bot, q.npc, `quest:claim:${q.id}`);
        check(w.player(bot).gold === before + q.rewardGold, `${q.title}: duplicate claim pays nothing`);
      }
      const repeat = town.quests.find(q => q.repeatable);
      await kit.talkTo(w, bot, repeat.npc, `quest:accept:${repeat.id}`);
      await w.debug(bot, { op: 'give_item', item: 'drowned_coin', quantity: 4 });
      await kit.talkTo(w, bot, repeat.npc, `quest:claim:${repeat.id}`);
      await w.waitFor(() => quest(w, bot, repeat.id).completions === 2);
      check(quest(w, bot, repeat.id).completions === 2, 'The standing order repeats with a second real hand-in');
      await w.restart();
      check(town.quests.every(q => quest(w, bot, q.id).claimed), 'All nine claimed quests survive Rust restart');
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
    if (scenarios[name].godMode !== undefined) world.godMode = scenarios[name].godMode;
    if (scenarios[name].levelSpread !== undefined) world.levelSpread = scenarios[name].levelSpread;
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
