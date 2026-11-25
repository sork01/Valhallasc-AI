const { execFileSync } = require('node:child_process');

// Set up a trained angler in the driver's disposable SQLite database.
async function seedFishingSkill(world, bot, skill) {
  const { id } = world.bots.get(bot);
  await world.disconnect(bot);
  execFileSync('python3', ['-c', `
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    raw, = db.execute("SELECT state FROM characters WHERE id = ?", (sys.argv[2],)).fetchone()
    state = json.loads(raw)
    state["fishing"]["skill"] = int(sys.argv[3])
    db.execute("UPDATE characters SET state = ? WHERE id = ?", (json.dumps(state), sys.argv[2]))
  `, world.db, id, String(skill)]);
  await world.connect({ bot });
  await world.waitFor(() => world.player(bot)?.professions?.fishing?.skill === skill);
}

module.exports = { seedFishingSkill };
