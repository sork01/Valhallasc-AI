const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const { seedFishingSkill } = require('../scripts/testing/fishing-fixture.cjs');

const zone = 6, bot = 'Wyrdwood';
const { zones } = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'), 'utf8'));
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const w = new TestWorld();
w.startLevel = 27;
w.levelSpread = 0;

async function castAt(zone) {
  const map = zones[zone - 1];
  const clearance = spot => Math.min(...map.slimes.map(enemy => distance(spot.shore, enemy)));
  const { shore } = [...map.fishingSpots].sort((a, b) => clearance(b) - clearance(a))[0];
  await w.debug(bot, { op: 'teleport', zone, ...shore });
  const start = w.events.length;
  w.bots.get(bot).socket.send(JSON.stringify({ type: 'fish', auto_aim: true }));
  return w.waitFor(() => w.events.slice(start).find(e =>
    e.bot === bot && (e.kind === 'fish_cast' || e.type === 'error')), 5000, 'cast reply');
}

async function fishWithPlatinum() {
  await w.debug(bot, { op: 'give_item', item: 'rod_emberline_rod', quantity: 1 });
  await seedFishingSkill(w, bot, 96);
  const blocked = await castAt(zone);
  assert.equal(blocked.text, 'You need Fishing skill 120 to fish here. Fish in Gloamfen to reach skill 120.');
  assert(!w.player(bot)?.fishing);

  await seedFishingSkill(w, bot, 120);
  for (const target of [zone, 3]) {
    const reply = await castAt(target);
    assert.equal(reply.kind, 'fish_cast', reply.text || `Platinum casts in zone ${target}`);
    await w.waitFor(() => w.player(bot)?.fishing, 5000, 'line is visible in the snapshot');
    await w.action(bot, { type: 'fish' });
    await w.waitFor(() => !w.player(bot)?.fishing, 5000, 'line pulled in');
    if (target === zone) await w.advance(1100);
  }
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
