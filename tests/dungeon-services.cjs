const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const read = filename => fs.readFileSync(path.join(root, filename), 'utf8');
const data = JSON.parse(read('world/map.txt'));
const zones = [data, ...data.zones];
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

assert.deepEqual(JSON.parse(read('client/world.js').split('window.WORLD_MAP = ')[1].trim().slice(0, -1)), data);
if (process.env.MUTATE === 'outdoor_hire') {
  const stone = zones[4].npcs.find(npc => npc.id === 'city_meetingstone');
  stone.offers.push({ id:'merc_priest', merc:'priest', open:true });
}
let dungeons = 0, outsideStones = 0;
for (const [zone, map] of zones.entries()) {
  const inside = map.copies > 0 && map.players > 0;
  const stones = map.npcs.filter(npc => npc.name.includes('Meeting Stone'));
  const hire = map.npcs.filter(npc => npc.offers?.some(offer => offer.merc && (offer.open || offer.raid)));
  if (!inside) {
    outsideStones += stones.length;
    assert.equal(hire.length, 0, map.name + ' has no dungeon hire offer');
  } else {
    dungeons++;
    assert.deepEqual(hire.map(npc => npc.id), ['dungeon_repair_' + zone]);
    assert(hire[0].offers.some(o => o.id === 'repair'));
    assert.equal(hire[0].offers.filter(o => o.merc && o.merc !== 'dismiss').length, 5);
    assert(hire[0].offers.filter(o => o.merc && o.merc !== 'dismiss').every(o => map.raid ? o.raid : o.open));
    assert.deepEqual(stones.map(npc => npc.id), ['dungeon_stone_' + zone]);
    assert(distance(map.spawn, stones[0]) <= 6);
    assert(map.objects.some(o => o.kind === 'meetingstone' && distance(stones[0], o) === 0));
  }
  for (const stone of stones) assert.deepEqual(stone.offers.map(o => o.id), ['summon_party']);
}
assert.equal(dungeons, 21);
assert.equal(outsideStones, 13);
const barrow = zones[41], wyrd = zones[6], door = wyrd.portals.find(portal => portal.id === 'wyrd_nornroot');
assert.equal(door.needs_quest, 'entry_norn');
assert(distance(door, { x: 154, y: 183.5 }) > 12);
assert(barrow.portals.every(p => p.to !== 6 || distance(door, { x: p.tx, y: p.ty }) > p.r + 2.8));
console.log('Data verified for 21 instance smiths and 34 summon stones');
if (process.argv.includes('--data-only')) return;

const { TestWorld } = require('../scripts/testing/driver.cjs');
const kit = require('../scripts/testing/tools.cjs');
const world = new TestWorld();
const wait = (fn, description) => world.waitFor(fn, 15000, description);
const smith = 'dungeon_repair_41', stone = 'dungeon_stone_41';
const leader = 'Lead', ally = 'Ally', outsider = 'Outsider';
const zone = bot => world.player(bot)?.zone;
const hire = () => world.views.get(leader)?.players.find(p => p.hired);
const summon = () => world.action(leader, { type:'interact', npc:stone, offer:'summon_party' });
const invitation = since => world.events.slice(since).some(e => e.bot === ally && e.type === 'social' &&
  e.incoming?.some(i => i.kind === 'summon' && i.destination === barrow.name));

(async () => {
  await world.start();
  try {
    for (const bot of [leader, ally, outsider]) await world.connect({ bot, class:'warrior' });
    await world.debug(leader, { op:'set_level', level:25 });
    await world.debug(leader, { op:'set_gold', gold:10000 });
    await world.debug(ally, { op:'set_level', level:24 });
    await world.social(leader, { op:'party_invite', bot:ally });
    await world.social(ally, { op:'party_accept', bot:leader });
    await kit.teleport(world, leader, { npc:smith });
    const opened = await kit.talkTo(world, leader, smith, 'merc_priest');
    assert.match(opened.notice, /joins your party/);
    assert(world.events.some(e => e.bot === leader && e.type === 'dialogue' &&
      e.npc?.id === smith && e.repairMultiplier === 4 && Array.isArray(e.repairQuote)));
    await wait(hire, 'a dungeon hire');
    await kit.teleport(world, leader, { npc:stone });
    await world.advance(650);
    let since = world.events.length;
    await summon();
    await wait(() => invitation(since), 'summon invitation reaches the party');
    assert.equal(zone(ally), 0, 'sending an invitation leaves the recipient in place');
    assert(!world.events.slice(since).some(e => e.bot === outsider && e.incoming?.some(i => i.kind === 'summon')));
    await world.social(ally, { op:'summon_accept', id:world.player(leader).id });
    await wait(() => world.events.slice(since).some(e => e.bot === ally && /level 25/.test(e.text || '')), 'under-level summon is refused');
    assert.equal(zone(ally), 0);
    await world.debug(ally, { op:'set_level', level:25 });
    await world.advance(600);
    since = world.events.length;
    await summon();
    await wait(() => invitation(since), 'new invitation after leveling');
    assert(!world.player(ally).quests.some(q => q.id === 'entry_norn'));
    await world.social(ally, { op:'summon_accept', id:world.player(leader).id });
    await wait(() => zone(ally) === 41 && world.views.get(ally)?.players.some(p => p.id === world.player(leader).id), 'arrive in the summoner’s private copy');
    assert(distance(world.player(ally), zones[41].npcs.find(npc => npc.id === stone)) < 3);

    await kit.teleport(world, leader, { npc:'barrow_guide' });
    await wait(() => zone(leader) === 6 && !hire(), 'the hire stays in its instance and its contract ends on exit');
    if (process.argv.includes('--all-dungeons')) {
      await world.debug(leader, { op:'set_gold', gold:10000000 });
      for (const [id, map] of zones.entries()) {
        if (!(map.copies > 0 && map.players > 0)) continue;
        await world.debug(leader, { op:'set_level', level:map.min_level });
        const npc = 'dungeon_repair_' + id;
        await kit.teleport(world, leader, { npc });
        const reply = await kit.talkTo(world, leader, npc, 'merc_priest');
        assert.match(reply.notice, /joins your party/, map.name);
        await wait(() => hire()?.zone === id, map.name + ' hire is in the instance');
        await kit.talkTo(world, leader, npc, 'merc_dismiss');
        await wait(() => !hire(), map.name + ' hire can be dismissed at its smith');
      }
      console.log('Verified hiring and dismissal at every dungeon and raid Repair Smith');
    }
    console.log('Private summon, level, repair and hire-boundary checks passed');
  } finally {
    await world.stop();
  }
})().catch(err => { console.error(err); process.exitCode = 1; });
