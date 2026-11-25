const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const zone = 6, bot = 'Wyrdwood';
const map = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'), 'utf8')).zones[zone - 1];
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const w = new TestWorld();
w.startLevel = 27;
w.levelSpread = 0;

async function fishWithPlatinum() {
  const clearance = spot => Math.min(...map.slimes.map(enemy => distance(spot.shore, enemy)));
  const { shore } = [...map.fishingSpots].sort((a, b) => clearance(b) - clearance(a))[0];
  await w.debug(bot, { op: 'teleport', zone, ...shore });
  await w.debug(bot, { op: 'give_item', item: 'rod_emberline_rod', quantity: 1 });
  const start = w.events.length;
  w.bots.get(bot).socket.send(JSON.stringify({ type: 'fish', auto_aim: true }));
  const reply = await w.waitFor(() => w.events.slice(start).find(e =>
    e.bot === bot && (e.kind === 'fish_cast' || e.type === 'error')), 5000, 'Wyrdwood cast reply');
  assert.equal(reply.kind, 'fish_cast', reply.text || 'Platinum casts from the Wyrdwood shore');
  await w.waitFor(() => w.player(bot)?.fishing, 5000, 'line is visible in the snapshot');
  await w.action(bot, { type: 'fish' });
  await w.waitFor(() => !w.player(bot)?.fishing, 5000, 'line pulled in');
}

async function fightWyrdweaver() {
  // A clearing east of Skuldwatch keeps other enemies and obstacles out of the approach.
  await w.debug(bot, { op: 'teleport', zone, x: 202.8, y: 207 });
  const { result, player } = await w.debug(bot, { op: 'spawn_enemy', kind: 'weaver', x: 200, y: 207 });
  assert(distance(result, player) < 3.4, 'the hero starts in the old retreat range');
  const view = () => w.views.get(bot);
  const enemy = () => view()?.slimes.find(s => s.id === result.id);
  await w.waitFor(() => enemy()?.state === 'lunge', 8000, 'the nearby Wyrdweaver shoots a volley');
  await w.waitFor(() => enemy()?.state === 'chase', 8000, 'volley enters cooldown');
  const until = view().time + 0.7;
  await w.waitFor(() => view().time >= until, 8000, 'watch the Wyrdweaver recover');
  assert(distance(result, enemy()) < 0.15, 'the Wyrdweaver holds its ground during cooldown');
  await w.waitFor(() => enemy()?.state === 'lunge', 8000, 'the Wyrdweaver fires again at close range');
}

(async () => {
  await w.start();
  try {
    await w.connect({ bot, class: 'warrior' });
    if (!process.argv.includes('--weaver-only')) await fishWithPlatinum();
    if (!process.argv.includes('--fishing-only')) await fightWyrdweaver();
    console.log('Wyrdwood private checks passed');
  } finally {
    await w.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
