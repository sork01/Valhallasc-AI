const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('./driver.cjs');
const { route } = require('./route.cjs');
const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

async function walkTo(world, bot, goal) {
  for (const point of route(map, world.player(bot), goal)) {
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
const quest = (w, bot, id) => w.player(bot).quests.find(q => q.id === id);
async function tour(w, bot) {
  await talk(w, bot, 'guide', 'quest:accept:welcome');
  for (const npc of ['healer', 'smith', 'innkeeper']) await talk(w, bot, npc);
  await talk(w, bot, 'guide', 'quest:claim:welcome');
  await w.waitFor(() => quest(w, bot, 'welcome')?.claimed);
}
async function defeat(w, bot, kind) {
  if (w.player(bot).hp < 35) await talk(w, bot, 'healer', 'blessing');
  const enemy = w.snapshot.slimes.filter(s => !s.dead && s.kind === kind)
    .sort((a, b) => distance(w.player(bot), a) - distance(w.player(bot), b))[0];
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
      await w.action('Mage', { type: 'equip', armor: 'runic', weapon: 'crystal' });
      await w.waitFor(() => w.player('Mage').look.mageWeapon === 'crystal');
      const before = { ...w.player('Mage') };
      const enemy = w.snapshot.slimes.find(s => s.kind === 'beetle' && s.hx === 18 && s.hy === 42);
      assert.ok(enemy && !enemy.dead, 'The meadow Ironhide is alive');
      check(enemy.maxHp === 240, 'Ironhide has authoritative health');
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
      check(after.kills === before.kills + 1 && after.xp === before.xp + 32 && after.hp > 0,
        'Real combat awards one kill and 32 XP while the mage survives');
      const defeated = w.snapshot.slimes.find(s => s.id === enemy.id);
      await w.action('Mage', { type: 'move', x: defeated.x, y: defeated.y });
      await w.waitFor(() => w.player('Mage').gold >= before.gold + 10, 15000, 'Collect Ironhide gold');
      check(w.events.some(e => e.kind === 'pickup' && e.actor === before.id && e.value === 10), 'Killer receives the 10-gold pickup');
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
      await w.waitFor(() => w.player('Warrior').look.warriorWeapon === 'royal' && w.player('Warrior').look.warriorArmor === 'azure');
      check(w.player('Warrior').gold === gold, 'Armorer fits server-owned equipment for free');
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
      await w.action(bot, { type: 'equip', armor: 'runic', weapon: 'crystal' });
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
      check(w.player(bot).gold === before.gold + 24 && w.player(bot).level === 2 && w.player(bot).xp === 32,
        'Patrol turn-in awards 24 gold, levels the mage, and carries remaining XP');
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
      check(w.player(bot).gold === bountyBefore.gold + 25 && w.player(bot).xp === bountyBefore.xp + 60,
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
