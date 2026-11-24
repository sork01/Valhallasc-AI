// Two real shore catches against a disposable server/DB; no browser or loot grind.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {TestWorld} = require('../scripts/testing/driver.cjs');
const { seedFishingSkill } = require('../scripts/testing/fishing-fixture.cjs');
const root = path.resolve(__dirname, '..');
const world = JSON.parse(fs.readFileSync(path.join(root, 'world/map.txt')));
const species = JSON.parse(fs.readFileSync(path.join(root, 'world/fish.txt')));
const loot = JSON.parse(fs.readFileSync(path.join(root, 'world/fishing-loot.txt')));
const w = new TestWorld(), bot = 'LavaAngler';
w.startLevel = 99;
w.levelSpread = 0;

async function shore(zone) {
  const area = zone === 0 ? world : world.zones[zone - 1];
  // Pick the authored shore furthest from ordinary monsters, without moving content.
  const candidates = area.fishingSpots.map(p => ({...p, clearance: Math.min(
    ...area.slimes.filter(s => !s.sleeping).map(s => Math.hypot(p.shore.x-s.x, p.shore.y-s.y)))}));
  const point = candidates.sort((a, b) => b.clearance-a.clearance)[0];
  assert(point);
  await w.debug(bot, {op:'teleport', zone, ...point.shore});
  await w.waitFor(() => w.player(bot).zone === zone &&
    Math.hypot(w.player(bot).x-point.shore.x, w.player(bot).y-point.shore.y) < .05);
  await w.action(bot, {type:'input', dx:point.facing.x, dy:point.facing.y});
  await w.waitFor(() => Math.hypot(w.player(bot).x-point.shore.x, w.player(bot).y-point.shore.y) > .01);
  await w.action(bot, {type:'stop'});
  await w.advance(150);
  return point;
}

async function rejected(text) {
  const start = w.events.length;
  await w.action(bot, {type:'fish'});
  await w.waitFor(() => w.events.slice(start).some(e => e.type === 'error' && e.text === text));
  assert(!w.player(bot).fishing, text);
}

async function cadence() {
  const ticks = [], times = [], socket = w.bots.get(bot).socket;
  const sample = data => {
    const packet = JSON.parse(data);
    if (packet.type === 'snapshot') {ticks.push(packet.tick); times.push(performance.now());}
  };
  socket.on('message', sample);
  try {
    await w.waitFor(() => ticks.length >= 30, 3800, '30 lava snapshots');
    const elapsed = Math.round(times[29]-times[0]);
    assert(elapsed <= 3000, `30 snapshots took ${elapsed} ms`);
    assert(ticks.slice(1).every((t, i) => t-ticks[i] === 2), JSON.stringify(ticks));
    console.log(`30 lava snapshots in ${elapsed} ms, tick gaps of two`);
  } finally {socket.off('message', sample);}
}

(async () => {
  await w.start();
  await w.connect({bot, class:'warrior', gender:'male'});
  await seedFishingSkill(w, bot, 255);
  await w.debug(bot, {op:'give_item', item:'rod_twig_rod', quantity:1});
  await shore(1);
  await rejected('This water requires Platinum Rod (level 5).');
  await w.debug(bot, {op:'give_item', item:'rod_emberline_rod', quantity:1});
  for (const [zone, rod] of [[1, 'rod_emberline_rod'], [45, 'rod_magma_reel']]) {
    if (zone === 45) {
      await shore(zone);
      await rejected('This water requires Tempered Platinum Rod (level 45).');
      await w.debug(bot, {op:'give_item', item:rod, quantity:1});
    }
    const before = {...w.player(bot)}, start = w.events.length;
    await w.action(bot, {type:'fish'});
    await w.waitFor(() => w.player(bot).fishing);
    assert.equal(w.player(bot).fishing.lava, true);
    // Await the cadence result along with the catch so any early failure is handled.
    const probe = zone === 45 ? cadence() : Promise.resolve();
    const catchFish = async () => {
      await w.waitFor(() => w.player(bot).fishing?.state === 'bite', 15000, `zone ${zone} bite`);
      await w.action(bot, {type:'fish'});
      const caught = await w.waitFor(() => w.events.slice(start).find(e => e.kind === 'fish_catch'));
      const fish = species.find(s => s.item === caught.item);
      if (fish) {
        assert.equal(fish.habitat, 'Lava');
        assert(fish.zone == null || fish.zone === zone);
        assert(fish.min_tier <= (zone === 1 ? 2 : 6));
        assert(caught.kg >= fish.kg[0] && caught.kg <= fish.kg[1]);
      } else {
        assert(loot.some(s => s.item === caught.item && ['any', 'lava'].includes(s.habitat)));
      }
      await w.waitFor(() => w.player(bot).inventory.some(s => s.item === caught.item && s.quantity >= caught.quantity));
      const after = w.player(bot);
      assert(Math.hypot(after.x-before.x, after.y-before.y) < .01, 'catch moved the hero');
      assert.equal(after.hp, before.hp, 'shore cast changed health');
      console.log(`Zone ${zone}: ${rod} caught ${caught.item} from dry shore`);
    };
    await Promise.all([probe, catchFish()]);
    await w.advance(1100);
  }
  await w.debug(bot, {op:'take_item', item:'rod_twig_rod', quantity:1});
  await shore(0);
  await w.action(bot, {type:'fish'});
  await w.waitFor(() => w.player(bot).fishing);
  assert.equal(w.player(bot).fishing.lava, false, 'one upgraded rod also fishes water');
  await w.action(bot, {type:'fish'});
  const inventory = JSON.stringify(w.player(bot).inventory);
  const log = JSON.stringify(w.player(bot).fishingLog);
  await w.disconnect(bot);
  await w.connect({bot, class:'warrior', gender:'male'});
  assert.equal(JSON.stringify(w.player(bot).inventory), inventory);
  assert.equal(JSON.stringify(w.player(bot).fishingLog), log);
  assert(!w.player(bot).fishing);
  console.log('Lava/water rod isolation and catch persistence pass');
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(() => w.stop());
