// Private websocket check of the real pier, server clock and tick cadence while a line is out.
const assert = require('node:assert/strict');
const { TestWorld } = require('../scripts/testing/driver.cjs');
async function run() {
  const w = new TestWorld();
  const bot = 'PierAngler';
  try {
    await w.start();
    await w.connect({ bot, class: 'warrior', gender: 'male' });
    await w.debug(bot, { op: 'give_item', item: 'rod_twig_rod', quantity: 1 });
    await w.debug(bot, { op: 'teleport', zone: 0, x: 200.5, y: 293.5 });
    await w.action(bot, { type: 'input', dx: 1, dy: 0 });
    await w.waitFor(() => w.player(bot).x > 200.55);
    await w.action(bot, { type: 'stop' });
    const socket = w.bots.get(bot).socket;
    socket.send(JSON.stringify({type: 'shop_presence', open: true}));
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text === 'You cannot fish right now.'));
    socket.send(JSON.stringify({type: 'shop_presence', open: false}));
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => w.player(bot).fishing);
    const ticks = [];
    const arrivals = [];
    const sample = data => {
      const packet = JSON.parse(data);
      if (packet.type === 'snapshot') { ticks.push(packet.tick); arrivals.push(performance.now()); }
    };
    w.bots.get(bot).socket.on('message', sample);
    await w.waitFor(() => ticks.length >= 30, 3800, '30 snapshots');
    w.bots.get(bot).socket.off('message', sample);
    const elapsed = Math.round(arrivals[29] - arrivals[0]);
    assert(elapsed <= 3000, `30 snapshots took ${elapsed} ms`);
    assert(ticks.slice(1).every((tick, i) => tick - ticks[i] === 2), JSON.stringify(ticks));
    console.log(`30 snapshots in ${elapsed} ms, tick gaps of 2`);
    await w.waitFor(() => w.player(bot).fishing?.state === 'bite', 15000, 'bite');
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => w.player(bot).fishingLog?.total === 1);
    const [id] = Object.keys(w.player(bot).fishingLog.species);
    assert(w.player(bot).inventory.some(s => s.item === id && s.quantity === 1));
    await w.disconnect(bot);
    await w.connect({ bot, class: 'warrior', gender: 'male' });
    assert.equal(w.player(bot).fishingLog.species[id].count, 1);
    assert(!w.player(bot).fishing);
    console.log('Pier catch recorded and placed in bags:', id);
  } finally { await w.stop(); }
}
run().catch(error => {console.error(error); process.exitCode = 1;});
