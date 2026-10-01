const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('./driver.cjs');
const { route } = require('./route.cjs');
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
const totalXp = p => p.xp + Array.from({ length: p.level - 1 }, (_, i) => Math.round(160 * (i + 1) ** 1.35)).reduce((a, b) => a + b, 0);
const quest = (w, bot, id) => w.player(bot).quests.find(q => q.id === id);
async function tour(w, bot) {
  await talk(w, bot, 'guide', 'quest:accept:welcome');
  for (const npc of ['healer', 'smith', 'innkeeper']) await talk(w, bot, npc);
  await talk(w, bot, 'guide', 'quest:claim:welcome');
  await w.waitFor(() => quest(w, bot, 'welcome')?.claimed);
}
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

const scenarios = {
  movement: {
    description: 'Three classes share spawn, walk through another player, and preserve enemy spacing.',
    async run(w, check) {
      for (const [bot, playerClass] of [['Warrior', 'warrior'], ['Mage', 'mage'], ['Assassin', 'assassin']]) {
        await w.connect({ bot, class: playerClass });
      }
      await w.waitFor(() => w.snapshot.players.length === 3);
      check(w.snapshot.players.length === 3, 'Three classes are online');
      check(w.player('Warrior').xpNeed === 160, 'Authoritative level threshold');
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
      const xp = Math.round(32 * scale(.15)), gold = Math.round(10 * scale(.1));
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
      check(reward.gold === 12 && w.player(bot).xp === 40, 'Turn-in awards exactly 12 gold and 40 XP');
      await talk(w, bot, 'guide', 'quest:claim:welcome');
      await talk(w, bot, 'guide', 'quest:accept:welcome');
      check(w.player(bot).gold === 12 && quest(w, bot, 'welcome').completions === 1, 'One-time rewards cannot be replayed or reaccepted');
      const database = w.db;
      await w.restart();
      check(w.db === database && w.player(bot).id === id && quest(w, bot, 'welcome').claimed && w.player(bot).gold === 12 && w.player(bot).xp === 40,
        'Quest completion and rewards survive restarting the actual Rust process');
      await talk(w, bot, 'guide', 'quest:claim:welcome');
      check(w.player(bot).gold === 12 && w.player(bot).xp === 40, 'Replaying a claim after restart grants nothing');
    },
  },
  quest_combat: {
    description: 'Real slime/Ironhide kills, prerequisite unlocks, level-up, killer-only quest credit, repeatable bounty, and save/resume.',
    async run(w, check) {
      const bot = 'QuestMage';
      await w.connect({ bot, class: 'mage' });
      await tour(w, bot);
      await w.connect({ bot: 'Observer' });
      const locked = await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      check(locked.notice.includes('earlier quest') && !quest(w, bot, 'ironhide_hunt'), 'Ironhide hunt is locked until the slime patrol is turned in');
      await talk(w, bot, 'gatekeeper', 'quest:accept:slime_patrol');
      for (let i = 1; i <= 6; i++) {
        await defeat(w, bot, 'green');
        await w.waitFor(() => quest(w, bot, 'slime_patrol').counts[0] === i);
      }
      check(quest(w, bot, 'slime_patrol').counts[0] === 6, 'Six real kills advance the accepted slime patrol');
      check(w.player('Observer').kills === 0 && !w.player('Observer').quests.length, 'Another player receives no killer quest credit');
      await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      check(!quest(w, bot, 'ironhide_hunt'), 'Completing objectives alone does not unlock the next quest');
      const before = { ...w.player(bot) };
      await talk(w, bot, 'gatekeeper', 'quest:claim:slime_patrol');
      await w.waitFor(() => quest(w, bot, 'slime_patrol').claimed);
      check(w.player(bot).gold === before.gold + 24 && w.player(bot).level === 2 && totalXp(w.player(bot)) === totalXp(before) + 80,
        'Patrol turn-in awards 24 gold and 80 XP, levels the mage, and carries the remainder');
      await talk(w, bot, 'smith', 'quest:accept:ironhide_hunt');
      await talk(w, bot, 'merchant', 'quest:accept:meadow_bounty');
      await w.waitFor(() => !!quest(w, bot, 'meadow_bounty'));
      check(quest(w, bot, 'meadow_bounty').counts[0] === 0, 'Bounty excludes kills made before acceptance');
      await talk(w, bot, 'healer', 'blessing');
      for (let i = 1; i <= 2; i++) {
        await defeat(w, bot, 'beetle');
        await w.waitFor(() => quest(w, bot, 'ironhide_hunt').counts[0] === i && quest(w, bot, 'meadow_bounty').counts[0] === i);
      }
      check(quest(w, bot, 'ironhide_hunt').counts[0] === 2 && quest(w, bot, 'slime_patrol').counts[0] === 6,
        'Ironhide kills advance both matching active quests while completed patrol stays unchanged');
      for (let i = 3; i <= 8; i++) {
        await defeat(w, bot, 'green');
        await w.waitFor(() => quest(w, bot, 'meadow_bounty').counts[0] === i);
      }
      await talk(w, bot, 'smith', 'quest:claim:ironhide_hunt');
      await talk(w, bot, 'gatekeeper', 'quest:accept:king_challenge');
      await w.waitFor(() => !!quest(w, bot, 'king_challenge'));
      check(quest(w, bot, 'king_challenge').counts[0] === 0, 'Ironhide turn-in unlocks the King Slime quest without crediting other kills');
      const bountyBefore = { ...w.player(bot) };
      await talk(w, bot, 'merchant', 'quest:claim:meadow_bounty');
      await w.waitFor(() => quest(w, bot, 'meadow_bounty').claimed);
      check(w.player(bot).gold === bountyBefore.gold + 25 && totalXp(w.player(bot)) === totalXp(bountyBefore) + 60,
        'Eight real mixed kills pay the promised bounty reward');
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
      check(w.events.some(e => e.kind === 'itemPickup' && e.actor === w.player(bot).id && e.item === 'slime_gel'), 'Real combat creates a collectible material drop');
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
    description: 'Earn a level through real quests and combat, train stats, reject overspending, and resume saved allocations.',
    async run(w, check) {
      const bot = 'StatMage'; await w.connect({ bot, class: 'mage' });
      check(w.player(bot).statPoints === 0 && w.player(bot).hitChance === .9, 'New characters have no free training points and 90% hit chance');
      await w.action(bot, { type: 'allocate_stat', stat: 'intellect' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Level up')));
      check(w.player(bot).attributes.intellect === 0, 'The server rejects spending points before leveling');
      await tour(w, bot);
      await talk(w, bot, 'gatekeeper', 'quest:accept:slime_patrol');
      for (let i = 0; i < 6; i++) await defeat(w, bot, 'green');
      await talk(w, bot, 'gatekeeper', 'quest:claim:slime_patrol');
      await w.waitFor(() => w.player(bot).level === 2 && w.player(bot).statPoints === 3);
      check(w.player(bot).statPoints === 3, 'A real combat and quest level earns three points');
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
      const xp = Math.round(80 * (1 + .15 * (wisp.level - 5))), gold = Math.round(18 * (1 + .1 * (wisp.level - 5)));
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
    description: 'Earn expansion-bag gold through real quests and combat, buy a bag from Linden, and verify authoritative capacity and persistence.',
    async run(w, check) {
      const bot = 'BagMage'; await w.connect({ bot, class: 'mage' });
      check(w.player(bot).bagCapacity === 16 && w.player(bot).bags.length === 0, 'New character starts with a sixteen-slot backpack');
      await w.action(bot, { type: 'interact', npc: 'merchant', offer: 'satchel' });
      await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('Walk closer')));
      check(w.player(bot).bags.length === 0, 'Expansion bags cannot be bought remotely');
      const refused = await talk(w, bot, 'merchant', 'satchel');
      check(refused.notice.includes('gold') && w.player(bot).bags.length === 0, 'Insufficient funds do not grant a bag');
      await tour(w, bot);
      const count = id => w.player(bot).inventory.find(s => s.item === id)?.quantity || 0;
      await talk(w, bot, 'gatekeeper', 'quest:accept:slime_patrol');
      for (let i = 0; w.player(bot).gold + count('slime_gel') * 3 < 500 && i < 75; i++) {
        while (w.player(bot).statPoints > 0) {
          const trained = w.player(bot).attributes.intellect;
          await w.action(bot, { type: 'allocate_stat', stat: 'intellect' });
          await w.waitFor(() => w.player(bot).attributes.intellect > trained);
        }
        await defeat(w, bot, 'green');
        const corpse = w.snapshot.slimes.filter(s => s.dead && s.kind === 'green').sort((a, b) => distance(w.player(bot), a) - distance(w.player(bot), b))[0];
        await walkTo(w, bot, corpse);
        await w.advance(600);
        if (quest(w, bot, 'slime_patrol').counts[0] === 6 && !quest(w, bot, 'slime_patrol').claimed) {
          await talk(w, bot, 'gatekeeper', 'quest:claim:slime_patrol');
          await w.waitFor(() => quest(w, bot, 'slime_patrol').claimed);
          await talk(w, bot, 'merchant', 'quest:accept:meadow_bounty');
          await w.waitFor(() => !!quest(w, bot, 'meadow_bounty'));
        }
        if (quest(w, bot, 'meadow_bounty')?.counts[0] === 8) {
          await talk(w, bot, 'merchant', 'quest:claim:meadow_bounty');
          await talk(w, bot, 'merchant', 'sell:materials');
          if (w.player(bot).gold < 500) await talk(w, bot, 'merchant', 'quest:accept:meadow_bounty');
        }
      }
      await talk(w, bot, 'merchant', 'sell:materials');
      await w.waitFor(() => w.player(bot).gold >= 500);
      const before = w.player(bot).gold;
      const purchase = await talk(w, bot, 'merchant', 'satchel');
      await w.waitFor(() => w.player(bot).bags.length === 1);
      check(purchase.notice.includes('22 bag slots') && w.player(bot).gold === before - 500, 'Earned gold purchases six additional slots for 500 gold');
      check(w.player(bot).bagCapacity === 22 && w.player(bot).bags[0] === 'linen_satchel', 'Snapshot carries the fitted bag and authoritative capacity');
      await w.restart();
      check(w.player(bot).bagCapacity === 22 && w.player(bot).bags[0] === 'linen_satchel' && w.player(bot).gold === before - 500, 'Bag ownership and payment survive restarting Rust');
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
