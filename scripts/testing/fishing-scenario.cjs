// One real hook, one early miss and one lava cast; no loot grind or combat shortcuts.
const fs = require('node:fs');
const path = require('node:path');
module.exports = (_kit, map) => ({
  description: 'Fishing through real packets: pier cast, early miss, private deadline, public bobber, catch, lava rod isolation and SQLite restart.',
  startLevel: 99, levelSpread: 0, godMode: true,
  async run(w, check) {
    const bot = 'FishCheck', witness = 'FishWitness';
    const fish = JSON.parse(fs.readFileSync(path.join(__dirname, '../../world/fish.txt')));
    const items = JSON.parse(fs.readFileSync(path.join(__dirname, '../../world/items.txt')));
    await w.connect({ bot, class: 'warrior' });
    await w.connect({ bot: witness, class: 'priest' });
    await w.debug(bot, { op: 'give_item', item: 'rod_twig_rod', quantity: 1 });
    await w.debug(bot, { op: 'teleport', zone: 0, ...map.dock.start });
    await w.action(bot, { type: 'input', dx: 1, dy: 0 });
    await w.waitFor(() => w.player(bot).x > map.dock.start.x + .01);
    await w.action(bot, { type: 'stop' });
    const own = () => w.player(bot), events = (from, kind) => w.events.slice(from).filter(e => e.bot === bot && e.kind === kind);
    let from = w.events.length;
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => own().fishing);
    check(own().fishing.lava === false, 'Pier cast selects ordinary water');
    await w.action(bot, { type: 'fish' });
    const miss = await w.waitFor(() => events(from, 'fish_miss')[0]);
    await w.waitFor(() => !own().fishing);
    check(miss.text === 'Too early.', 'Early hook ends the line with the authoritative miss');
    await w.advance(1100);
    from = w.events.length;
    const before = { x: own().x, y: own().y, hp: own().hp };
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => own().fishing);
    const publicLine = await w.waitFor(() => w.views.get(witness)?.players.find(p => p.id === own().id)?.fishing);
    check(Number.isFinite(publicLine.x) && Number.isFinite(publicLine.y), 'Nearby player sees the public bobber');
    check(events(from, 'fish_cast').length === 1, 'One cast press produces one private cast event');
    const snap = w.views.get(bot);
    check(Number.isFinite(snap.fishingTime) && Math.abs(snap.fishingTime - Date.now() / 1000) < 2, 'Snapshot carries the shared Unix clock');
    check(snap.fishingSpots.length > 0 && snap.fishingSpots.length < map.fishingSpots.length && snap.fishingSpots.every(p => map.fishingSpots.some(candidate => Math.hypot(candidate.x - p.x, candidate.y - p.y) < .001)), 'Snapshot contains active rich spots from the candidate pool');
    await w.waitFor(() => own().fishing?.state === 'bite', 15000, 'Fishing bite');
    check(own().fishDeadline > w.views.get(bot).fishingTime, 'Owner receives a future bite deadline');
    const otherView = w.views.get(witness).players.find(p => p.id === own().id);
    check(otherView.fishDeadline === undefined && otherView.fishingLog === undefined, 'Other players receive neither deadline nor collection log');
    await w.action(bot, { type: 'fish' });
    const caught = await w.waitFor(() => events(from, 'fish_catch')[0]);
    await w.waitFor(() => own().inventory.some(s => s.item === caught.item && s.quantity >= caught.quantity));
    check(items.some(i => i.id === caught.item) && caught.quantity > 0, 'Hook awards a real catalogue item into the bags');
    check(!w.events.slice(from).some(e => e.bot === witness && e.kind === 'fish_catch'), 'Catch result is private to the angler');
    check(Math.hypot(own().x - before.x, own().y - before.y) < .01 && own().hp === before.hp, 'Pier catch preserves position and health');
    const species = fish.find(f => f.item === caught.item);
    check(species ? own().fishingLog.species[caught.item].count === 1 && own().fishingLog.species[caught.item].bestKg === caught.kg : (own().fishingLog?.total || 0) === 0, 'Real species record or non-fish exclusion matches the award');

    const area = map.zones[0];
    const point = [...area.fishingSpots].sort((a, b) => {
      const clearance = p => Math.min(...area.slimes.filter(s => !s.sleeping).map(s => Math.hypot(p.shore.x - s.x, p.shore.y - s.y)));
      return clearance(b) - clearance(a);
    })[0];
    await w.debug(bot, { op: 'teleport', zone: 1, ...point.shore });
    await w.action(bot, { type: 'input', dx: point.facing.x, dy: point.facing.y });
    await w.waitFor(() => Math.hypot(own().x - point.shore.x, own().y - point.shore.y) > .01);
    await w.action(bot, { type: 'stop' });
    await w.advance(1100);
    from = w.events.length;
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => w.events.slice(from).some(e => e.bot === bot && e.type === 'error'));
    check(w.events.slice(from).some(e => e.bot === bot && e.text === 'Carry a suitable fishing rod.') && !own().fishing, 'Water rod is rejected at a lava shore');
    await w.debug(bot, { op: 'give_item', item: 'rod_emberline_rod', quantity: 1 });
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => own().fishing);
    check(own().fishing.lava === true, 'Matching lava rod starts a real lava line');
    const inventory = JSON.stringify(own().inventory), log = JSON.stringify(own().fishingLog), id = own().id;
    await w.restart();
    check(own().id === id && JSON.stringify(own().inventory) === inventory && JSON.stringify(own().fishingLog) === log, 'Inventory and fishing records survive SQLite restart');
    check(!own().fishing, 'An active fishing line is cleared by restart');
  },
});
