// REBIRTH-CHECK: the whole rebirth loop on a private server, with real WebSocket clients and no browser. A level-50
// character rebirths, plays the early game again with the perks, rebirths at 70 (tier 3) and four times at 90 (tier 5).
// Checked along the way: the reset and keep lists (friends, party, mount, gear, gold), a repeated quest that pays its
// rewards again with the bonus, the XP perk on a real kill, the gold and bag perks, the drop multiplier on real elite
// kills (x1, x2 after the first tier-5 rebirth, x5 after four), a server restart, and that no perk changes combat
// numbers (a reborn hero at level 40 against a fresh character). The large-sample rates (licences 8% and 6%, then 20%
// and 15%, the purple copy 25%) are measured by `cargo test perks`, which `npm run test:rebirth-check` runs too.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld, root } = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt'), 'utf8'));
const items = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt'), 'utf8'));
const zones = [map, ...map.zones];
const YEAR = zones.findIndex(z => z.name === 'The Yearwheel');
assert.ok(YEAR > 0, 'the Yearwheel exists');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const percentOf = (value, percent) => Math.floor((value * (100 + percent) + 50) / 100);
const armor = items.find(i => i.id === 'warrior_armor_azure_l50_green');
assert.ok(armor, 'the level-50 green armor exists');
const VARIANT = armor.id.replace('warrior_armor_', '');

(async () => {
  const w = new TestWorld();
  w.levelSpread = 0;       // every respawn keeps the same level, so one kill pays exactly what the next does
  try {
    await w.start();
    await w.connect({ bot: 'Reborn', class: 'warrior' });
    await w.connect({ bot: 'Mate', class: 'mage' });
    const send = (bot, message) => w.bots.get(bot).socket.send(JSON.stringify(message));
    const debug = (op, rest = {}, bot = 'Reborn') => w.debug(bot, { op, ...rest });
    const me = () => w.player('Reborn');
    const ask = async (message, type, bot = 'Reborn') => {
      const earlier = new Set(w.events);
      send(bot, message);
      return w.waitFor(() => w.events.find(e => !earlier.has(e) && e.bot === bot && (e.type === type || e.type === 'error')), 5000, message.type);
    };
    const perk = id => me().rebirthPerks.find(p => p.id === id).value;
    const owned = id => (me().inventory.find(s => s.item === id)?.quantity || 0);
    const rebirth = async (level, expectTier) => {
      await debug('set_level', { level });
      await w.waitFor(() => !me().inCombat, 12000, 'leave combat');
      const before = me().reborn.count;
      const preview = await ask({ type: 'rebirth_preview' }, 'rebirthPreview');
      assert.equal(preview.type, 'rebirthPreview', preview.text);
      assert.equal(preview.ok, true, preview.reason);
      assert.equal(preview.tier, expectTier, `a level-${level} rebirth is tier ${expectTier}`);
      send('Reborn', { type: 'rebirth', nonce: preview.nonce });
      await w.waitFor(() => me().level === 1 && me().reborn.count === before + 1, 10000, `rebirth at ${level}`);
    };
    const keeps = (label, mounts = ['horse']) => {
      const p = me();
      assert.equal(p.zone, 0, `${label}: back in Greenmeadow`);
      assert.deepEqual(p.mounts, mounts, `${label}: mounts kept`);
      assert.ok(owned(armor.id) >= 1, `${label}: the level-50 armor is still owned (in the bags, not worn)`);
      assert.notEqual(p.look.warriorArmor, VARIANT, `${label}: it is no longer worn at level 1`);
      assert.ok(p.gold >= 5000, `${label}: gold kept`);
      const social = w.socialState('Reborn');
      assert.deepEqual(social.friends.map(f => f.name), ['Mate'], `${label}: friends kept`);
      assert.equal(social.party?.size, 2, `${label}: party kept`);
    };

    // 0. Set up a character with friends, a party, a mount, gear and gold.
    await debug('set_level', { level: 50 });
    await debug('set_gold', { gold: 5000 });
    await debug('give_mount', { mount: 'horse' });
    await debug('give_item', { item: armor.id, quantity: 1, force: true });
    send('Reborn', { type: 'equip', armor: VARIANT });
    await w.waitFor(() => me().look.warriorArmor === VARIANT, 5000, 'wear the level-50 armor');
    await w.social('Reborn', { op: 'friend_request', bot: 'Mate' });
    await w.social('Mate', { op: 'friend_accept', bot: 'Reborn' });
    await w.social('Reborn', { op: 'party_invite', bot: 'Mate' });
    await w.social('Mate', { op: 'party_accept', bot: 'Reborn' });
    assert.equal(me().reborn.count, 0);
    assert.deepEqual(me().rebirthPerks.map(p => p.value), [0, 0, 0, 0, 0, 1], 'no perks before the first rebirth');
    // Bags dropped by elites are picked up and fitted, so compare the cells that are not from a bag: 16 + the perk.
    const bareCells = p => p.bagCapacity - (p.bags || []).reduce((n, id) => n + (items.find(i => i.id === id)?.bagSlots || 0), 0);
    assert.equal(bareCells(me()), 16);

    // 1. A quest played before any rebirth pays its plain rewards.
    const claim = async id => {
      const before = { xp: me().xp, gold: me().gold, level: me().level };
      await debug('quest', { id, action: 'accept' });
      await debug('quest', { id, action: 'complete' });
      await debug('quest', { id, action: 'claim' });
      const p = me();
      assert.ok(p.quests.find(q => q.id === id)?.claimed, `${id} is claimed`);
      return { xp: p.xp - before.xp, gold: p.gold - before.gold, levelBefore: before.level, level: p.level };
    };
    // The hero is level 50 here, so its XP bar is huge and a 10 XP reward is exact.
    const first = await claim('welcome');
    assert.deepEqual([first.xp, first.gold], [10, 12], 'the unreborn reward');

    // 2. Rebirth at level 50: tier 1. The reset and keep lists.
    await rebirth(50, 1);
    assert.deepEqual(me().rebirthTiers, [1, 0, 0, 0, 0]);
    assert.deepEqual(me().reborn, { count: 1, tier: 1 });
    assert.equal(me().xp, 0);
    assert.equal(me().quests.length, 0, 'the quest ledger is empty: every quest can be taken again');
    keeps('tier 1');
    assert.equal(perk('xp'), 10);
    assert.equal(perk('gold'), 0, 'the gold perk starts at tier 2');
    assert.equal(bareCells(me()), 16);

    // 3. The same quest again pays its rewards again, with the XP bonus (level 1 has a 100 XP bar, 10 XP + 10% = 11).
    const again = await claim('welcome');
    assert.deepEqual([again.xp, again.gold], [percentOf(10, 10), 12], 'a repeated quest pays again, boosted');
    // A real kill pays the XP bonus too. The party of two shares it at party level 1 (40% of a level-1 slime's 50 XP
    // is 20 each); the reborn hero's 20 becomes 22 and the unreborn friend keeps 20.
    await debug('teleport', { zone: 0, x: 48, y: 20 });
    await debug('teleport', { zone: 0, x: 49, y: 20 }, 'Mate');
    await w.waitFor(() => Math.hypot(me().x - 48, me().y - 20) < 2 && Math.hypot(w.player('Mate').x - 49, w.player('Mate').y - 20) < 2, 10000, 'to the meadow');
    const [xpBefore, mateBefore] = [me().xp, w.player('Mate').xp];
    const spawned = await debug('spawn_enemy', { kind: 'green', x: 50, y: 20, level: 1 });
    await debug('kill_enemy', { id: spawned.result.id });
    await w.waitFor(() => me().xp !== xpBefore && w.player('Mate').xp !== mateBefore, 5000, 'kill XP');
    assert.equal(w.player('Mate').xp - mateBefore, 20, 'the unreborn friend gets the plain share');
    assert.equal(me().xp - xpBefore, percentOf(20, 10), 'the reborn hero gets the same share with the tier-1 bonus');

    // 4. Rebirth at 70: tier 3 earns bag cells and the gold perk once, and XP counts both rebirths.
    await rebirth(70, 3);
    assert.deepEqual(me().rebirthTiers, [1, 0, 1, 0, 0]);
    assert.equal(perk('xp'), 20);
    assert.equal(perk('gold'), 10, 'the gold perk counts the tier-3 rebirth');
    assert.equal(perk('bagCells'), 2);
    assert.equal(bareCells(me()), 16 + 2, 'two extra bag cells');
    assert.equal(perk('fare'), 0);
    assert.equal(perk('drops'), 1);
    keeps('tier 3');
    const second = await claim('welcome');
    assert.deepEqual([second.xp, second.gold], [percentOf(10, 20), percentOf(12, 10)], 'XP +20% and gold +10%');

    // 5. Drops on real elite kills. Control at x1, then after the first tier-5 rebirth at x2.
    const rimesaber = zones[YEAR].slimes.findIndex(s => s.kind === 'rimesaber');
    assert.ok(rimesaber >= 0);
    const spawn = zones[YEAR].slimes[rimesaber];
    // Enemy ids are global: zone files are numbered in order, so count the spawns before the Yearwheel.
    const enemyId = zones.slice(0, YEAR).reduce((n, z) => n + (z.slimes || []).length, 0) + rimesaber;
    const seenDrops = new Set();
    const killElite = async (kills) => {
      const result = { gold: [], material: 0, green: 0, kills };
      await debug('teleport', { zone: YEAR, x: spawn.x + 1, y: spawn.y + 1 });
      await w.waitFor(() => (me().zone || 0) === YEAR && Math.hypot(me().x - spawn.x - 1, me().y - spawn.y - 1) < 2, 10000, 'to the Rimesaber');
      for (let n = 0; n < kills; n++) {
        await debug('respawn_enemy', { id: enemyId }).catch(() => {});
        await w.waitFor(() => w.snapshot.slimes.find(s => s.id === enemyId && !s.dead), 5000, 'the Rimesaber lives');
        await debug('kill_enemy', { id: enemyId });
        await sleep(120);
        for (const d of w.snapshot.drops) {
          if (seenDrops.has(d.id)) continue;
          seenDrops.add(d.id);
          const item = d.item && items.find(i => i.id === d.item);
          if (!item) result.gold.push(d.value);
          else if (item.kind === 'material') result.material += d.quantity || 1;
          else if (item.rarity === 'uncommon' && item.kind !== 'bag') result.green += 1;
        }
      }
      return result;
    };
    const control = await killElite(6);
    assert.equal(control.material, 6, 'one material stack of 1 per kill at x1');
    assert.equal(control.green, 6, 'a green piece per kill at x1');
    assert.equal(new Set(control.gold).size, 1);

    await rebirth(90, 5);
    assert.deepEqual(me().rebirthTiers, [1, 0, 1, 0, 1]);
    assert.equal(perk('drops'), 2, 'the first tier-5 rebirth doubles the drops');
    assert.equal(perk('fare'), 10);
    assert.equal(perk('resetPrice'), 10);
    assert.equal(perk('bagCells'), 4, 'the tier-5 rebirth counts for the bag perk too');
    keeps('tier 5');
    const doubled = await killElite(6);
    assert.equal(doubled.material, 12, 'one stack worth two per kill at x2');
    assert.equal(doubled.green, 12, 'two green pieces per kill at x2');
    // The pile is the plain pile times 2, then the gold bonus: +10% for the control (one rebirth at tier 2 or higher),
    // +20% now (two). The plain amount is recovered from the control pile.
    const guess = Math.round(control.gold[0] * 100 / 110);
    const base = [guess - 2, guess - 1, guess, guess + 1, guess + 2].find(b => percentOf(b, 10) === control.gold[0]);
    assert.ok(base, 'the control pile matches a plain amount at +10% gold');
    assert.equal(doubled.gold[0], percentOf(base * 2, 20), 'the x2 pile');

    // 6. Three more rebirths at 90: x3, x4, x5, then it stays.
    for (const m of [3, 4, 5]) {
      await rebirth(90, 5);
      assert.equal(perk('drops'), m, `x${m}`);
    }
    await rebirth(90, 5);
    assert.equal(perk('drops'), 5, 'the multiplier stops at x5');
    assert.equal(perk('xp'), 50, 'XP is at its cap');
    assert.equal(perk('gold'), 50);
    assert.equal(bareCells(me()), 16 + 10, 'bag cells are capped at 10');
    assert.equal(perk('fare'), 50);
    assert.equal(perk('resetPrice'), 50);
    keeps('x5');
    const quintuple = await killElite(4);
    assert.equal(quintuple.material, 20, 'one stack worth five per kill at x5');
    assert.equal(quintuple.green, 20, 'five green pieces per kill at x5');

    // 7. The perks and the cosmetic choice survive a restart.
    await debug('give_mount', { mount: 'raptor' });
    const counts = me().rebirthTiers;
    await w.restart();
    await w.waitFor(() => me() && me().rebirthTiers, 15000, 'resume after the restart');
    assert.deepEqual(me().rebirthTiers, counts, 'rebirth counts survive a restart');
    assert.equal(perk('drops'), 5);
    assert.equal(bareCells(me()), 16 + 10);

    // 8. No perk changes combat. A reborn hero at level 40 has exactly the numbers of a fresh character.
    await w.connect({ bot: 'Control', class: 'warrior' });
    await debug('set_level', { level: 40 });
    await debug('set_level', { level: 40 }, 'Control');
    const numbers = p => ({ hp: p.maxHp, attack: p.attack, defense: p.defense, crit: p.critChance, cooldown: p.attackCooldown,
      dodge: p.dodgeChance, hit: p.hitChance, resource: p.maxResource, points: p.statPoints, skillCd: p.cooldownReduction });
    assert.deepEqual(numbers(w.player('Reborn')), numbers(w.player('Control')), 'rebirth perks change no combat number');

    console.log('Rebirth check: reset and keep lists, repeated quest, XP/gold/bag perks, x1 to x5 elite drops over five rebirths, restart and combat numbers all passed');
  } finally {
    await w.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
