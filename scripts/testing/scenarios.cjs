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
