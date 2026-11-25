const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { TestWorld } = require('../scripts/testing/driver.cjs');

const map = JSON.parse(fs.readFileSync(path.join(__dirname, '../world/map.txt'), 'utf8'));
const world = new TestWorld();
const bot = 'BagJournal';
const linen = 'linen_satchel', trail = 'trail_pack_l20', adventurer = 'adventurer_satchel';
const player = () => world.player(bot);
const count = id => player()?.inventory.find(row => row.item === id)?.quantity || 0;
const active = () => player()?.quests.filter(quest => !quest.claimed).length;
const learned = {
  enchanting: ['double_tap'],
  blacksmithing: ['smith_gear_meadowguard_gloves'],
  alchemy: ['alchemy_trailwind_potion'],
};

async function seedCharacter() {
  await world.start();
  const { id } = await world.connect({ bot });
  await world.stop();
  execFileSync('python3', ['-c', `
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    state = json.loads(db.execute("SELECT state FROM characters WHERE id = ?", (sys.argv[2],)).fetchone()[0])
    state["landing"] = False
    state["quests"] = [{"id": f"test_active_{i}", "counts": [], "claimed": False, "completions": 0} for i in range(19)]
    state["quests"].append({"id": "test_claimed", "counts": [], "claimed": True, "completions": 1})
    for profession, recipes in json.loads(sys.argv[3]).items():
        state[profession] = {"proficiency": {"skill": 1}, "recipes": recipes}
    db.execute("UPDATE characters SET state = ? WHERE id = ?", (json.dumps(state), sys.argv[2]))
`, world.db, id, JSON.stringify(learned)]);
  await world.launch();
  await world.connect({ bot });
  return id;
}

async function waitForError(action, text) {
  const old = new Set(world.events);
  await world.action(bot, action);
  await world.waitFor(() => world.events.some(event => !old.has(event) && event.bot === bot &&
    event.type === 'error' && event.text === text), 5000, text);
}

async function accept(id) {
  const { npc } = map.quests.find(quest => quest.id === id);
  const { x, y } = map.npcs.find(person => person.id === npc);
  await world.debug(bot, { op: 'teleport', zone: 0, x, y });
  return { type: 'interact', npc, offer: `quest:accept:${id}` };
}

(async () => {
  try {
    const id = await seedCharacter();
    const viewer = 'RecipeViewer';
    await world.connect({ bot: viewer });
    const visible = () => world.views.get(viewer)?.players.find(p => p.id === id);
    await world.waitFor(visible, 5000, 'another player can see the character');
    assert.deepEqual(player().learnedRecipes, learned);
    assert.equal(visible().learnedRecipes, undefined);
    await world.disconnect(viewer);

    await world.action(bot, await accept('slime_patrol'));
    await world.waitFor(() => active() === 20, 5000, 'the twentieth quest is accepted');
    await world.advance(650);
    await waitForError(await accept('welcome'), 'Your questlog is full');
    assert.equal(active(), 20);
    assert(!player().quests.some(quest => quest.id === 'welcome'));
    await world.action(bot, { type: 'quest_abandon', id: 'slime_patrol' });
    await world.waitFor(() => active() === 19, 5000, 'abandoning frees one slot');
    await world.advance(650);
    await world.action(bot, await accept('welcome'));
    await world.waitFor(() => active() === 20 && player().quests.some(q => q.id === 'welcome'), 5000, 'freed slot accepts another quest');

    await world.debug(bot, { op: 'drop_item', item: trail });
    await world.waitFor(() => count(trail) === 1, 5000, 'higher-level bag goes into inventory');
    assert.deepEqual(player().bags, []);
    await waitForError({ type: 'use_item', item: trail }, 'Your level is too low for this bag.');
    await world.debug(bot, { op: 'set_level', level: 20 });
    await world.action(bot, { type: 'use_item', item: trail });
    await world.waitFor(() => player().bags[0] === trail && !count(trail), 5000, 'fitting uses one loose bag');
    for (let i = 0; i < 3; i++) await world.debug(bot, { op: 'give_item', item: linen });
    assert.equal(player().bags.length, 4);
    await world.debug(bot, { op: 'drop_item', item: adventurer });
    await world.waitFor(() => count(adventurer) === 1, 5000, 'loot still enters inventory with all slots fitted');
    assert.equal(player().bagCapacity, 44);
    await world.action(bot, { type: 'use_item', item: adventurer, bag_slot: 2 });
    await world.waitFor(() => player().bags[2] === adventurer && count(linen) === 1, 5000, 'the chosen bag is replaced and returned');
    assert.deepEqual(player().bags, [trail, linen, adventurer, linen]);
    assert.equal(player().bagCapacity, 46);
    assert.equal(count(adventurer), 0);
    await world.restart();
    assert.deepEqual(player().bags, [trail, linen, adventurer, linen]);
    assert.equal(count(linen), 1);
    assert.equal(active(), 20);
    console.log('Private protocol checks passed for loose bag swaps, recipe privacy and the 20-quest limit.');
  } finally {
    await world.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
