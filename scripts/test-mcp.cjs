// stdout belongs exclusively to the MCP stdio transport.
const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { z } = require('zod');
const { TestWorld, actionSchema, botSchema } = require('./testing/driver.cjs');
const { scenarios, runScenario } = require('./testing/scenarios.cjs');
const kit = require('./testing/tools.cjs');

const server = new McpServer({ name: 'valhallasc-testing', version: '1.0.0' });
let world = null;
let queue = Promise.resolve();
let closing = false;
const current = () => {
  if (!world) throw Error('Call start_world first.');
  return world;
};
function tool(name, description, schema, handler, readOnly = false) {
  server.registerTool(name, { description, inputSchema: schema,
    annotations: { readOnlyHint: readOnly, destructiveHint: false, openWorldHint: false } }, args => {
    // Tools share one world; serialize mutations and inspections for predictable results.
    const job = queue.then(async () => {
      if (closing) throw Error('MCP server is shutting down.');
      const result = await handler(args);
      return { ...(result.passed === false ? { isError: true } : {}),
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }], structuredContent: result };
    }).catch(error => ({ isError: true, content: [{ type: 'text', text: error.message }] }));
    queue = job.then(() => {});
    return job;
  });
}
const empty = z.object({}).strict();
const startOptions = z.object({
  startLevel: z.number().int().min(1).max(40).optional().describe('new characters begin at this level (VALHALLA_START_LEVEL)'),
  godMode: z.boolean().optional().describe('players take no damage; default on'),
  levelSpread: z.number().int().min(0).max(5).optional().describe('enemy levels roll within this distance of their default; 0 pins them (default 2)'),
}).strict();
tool('start_world', 'Start an isolated Rust server on loopback with a fresh test database and test shortcuts enabled. Build the binary first. Never connects to production. Options: startLevel, godMode, levelSpread.', startOptions, async options => {
  if (world) throw Error('A world is already active. Call stop_world first.');
  world = new TestWorld();
  world.startLevel = options.startLevel;
  world.godMode = options.godMode;
  world.levelSpread = options.levelSpread;
  try { return await world.start(); } catch (error) { world = null; throw error; }
});
tool('stop_world', 'Disconnect bots and gracefully stop the private server. Test artifacts remain available.', empty, async () => {
  if (!world) return { running: false };
  const result = await world.stop();
  if (world.runDir) result.artifact = world.saveReport({ interactive: true });
  world = null;
  return result;
});
tool('connect_bot', 'Create a bot with a class and a body (male or female). Reusing a disconnected bot name resumes its character; its original class and body are retained. Keys stay internal.', botSchema,
  args => current().connect(args));
tool('disconnect_bot', 'Disconnect a bot and save its character for resume within this test world.', z.object({ bot: botSchema.shape.bot }).strict(),
  ({ bot }) => current().disconnect(bot));
tool('send_action', 'Send a normal player action. Move x/y is a movement destination; the Rust server calculates the path motion, combat, and rewards.',
  z.object({ bot: botSchema.shape.bot, action: actionSchema }).strict(), ({ bot, action }) => current().action(bot, action));
tool('inspect_world', 'Read the latest observed authoritative snapshot, bounded recent events, and enemy spacing checks. Bot selects one player. Snapshots refresh while bots are connected.',
  z.object({ bot: botSchema.shape.bot.optional(), events: z.number().int().min(0).max(500).default(20) }).strict(),
  args => current().inspect(args), true);
tool('wait_world', 'Wait up to 30 seconds of real simulation time and return the latest snapshot. Does not change the simulation clock.',
  z.object({ milliseconds: z.number().int().min(0).max(30000) }).strict(), ({ milliseconds }) => current().advance(milliseconds));
// ---- Test shortcuts. Each runs a server-side `debug` command (only a test server accepts them) or real player actions. ----
const bot = botSchema.shape.bot;
const forBot = shape => z.object({ bot, ...shape }).strict();
const summarize = result => ({ ...result.result, player: result.player });
tool('restart_world', 'Restart only the private Rust server and database, resuming connected bots. Use it to check persistence.', empty, () => current().restart());
tool('describe_world', 'Static facts so you never read world files: zones, NPCs and their offers, portals, quests, items, skills, enemy kinds with default levels. what = overview | zones | npcs | quests | items | skills | enemies.',
  z.object({ what: z.enum(['overview', 'zones', 'npcs', 'quests', 'items', 'skills', 'enemies']).default('overview') }).strict(), ({ what }) => kit.describe(what), true);
tool('set_level', 'Set a bot\'s level (1-100), refill health and announce the level-up with the skills it unlocks. Level 20 unlocks every class skill. Lowering also resets trained stats.',
  forBot({ level: z.number().int().min(1).max(100) }), async ({ bot, level }) => summarize(await current().debug(bot, { op: 'set_level', level })));
tool('give_xp', 'Grant XP through the normal rules, so levels, stat points and level-up events follow.',
  forBot({ amount: z.number().int().min(0) }), async ({ bot, amount }) => summarize(await current().debug(bot, { op: 'give_xp', amount })));
tool('set_gold', 'Set a bot\'s gold.', forBot({ gold: z.number().int().min(0) }), async ({ bot, gold }) => summarize(await current().debug(bot, { op: 'set_gold', gold })));
tool('set_health', 'Set hp (clamped to max; revives a defeated bot) or defeat the bot with defeat:true to test death and respawn.',
  forBot({ hp: z.number().positive().optional(), defeat: z.boolean().optional() }), async ({ bot, hp, defeat }) => {
    if ((hp === undefined) === !defeat) throw Error('Give exactly one of hp or defeat:true.');
    return summarize(await current().debug(bot, defeat ? { op: 'die' } : { op: 'set_hp', hp }));
  });
tool('give_item', 'Put an item (see describe_world items) in a bot\'s bags. Respects bag capacity unless force:true; bags (linen_satchel, ...) are fitted, up to four.',
  forBot({ item: z.string(), quantity: z.number().int().min(1).max(9999).default(1), force: z.boolean().default(false) }), async ({ bot, ...rest }) => summarize(await current().debug(bot, { op: 'give_item', ...rest })));
tool('take_item', 'Remove spare copies of an item (worn copies stay; a fitted bag can be removed if everything still fits).',
  forBot({ item: z.string(), quantity: z.number().int().min(1).max(9999).default(1) }), async ({ bot, ...rest }) => summarize(await current().debug(bot, { op: 'take_item', ...rest })));
tool('drop_item', 'Drop an item on the ground at the bot\'s feet, owned by that bot, to test pickup and the 60-second expiry.',
  forBot({ item: z.string(), quantity: z.number().int().min(1).max(9999).default(1) }), async ({ bot, ...rest }) => summarize(await current().debug(bot, { op: 'drop_item', ...rest })));
tool('teleport', 'Move a bot instantly, across zones if needed. to: {x,y,zone?} | {npc} | {portal} | {enemy} | {spawn: zone} | {bot}. The server still pushes the bot out of obstacles.',
  forBot({ to: kit.targetSchema }), async ({ bot, to }) => summarize(await kit.teleport(current(), bot, to)));
tool('walk_to', 'Walk like a player (real move actions along a collision-aware route) to {x,y} | {npc} | {portal} | {enemy} | {bot}, within the bot\'s current zone. Takes real time.',
  forBot({ to: kit.targetSchema, timeoutMs: z.number().int().min(1000).max(120000).default(60000) }), ({ bot, to, timeoutMs }) => kit.walkTo(current(), bot, to, timeoutMs));
tool('talk_to', 'Interact with an NPC, walking into range first. offer: a service id (heal, satchel...), quest:accept:<id>, quest:claim:<id>, sell:materials or sell:<item>:<n>. Returns the server\'s notice, offers, gold and quests.',
  forBot({ npc: z.string(), offer: z.string().max(32).optional() }), ({ bot, npc, offer }) => kit.talkTo(current(), bot, npc, offer));
tool('quest', 'Quest shortcuts. accept/claim follow the real rules (prerequisite, objectives) without needing the NPC; complete fills every objective; finish does prerequisites + accept + complete + claim and pays rewards; reset forgets the quest. Ids: see describe_world quests.',
  forBot({ id: z.string(), action: z.enum(['accept', 'complete', 'claim', 'finish', 'reset']) }), async ({ bot, id, action }) => summarize(await current().debug(bot, { op: 'quest', id, action })));
tool('cast_skill', 'Cast a class skill as the browser does and report whether it went off, cooldown, buffs and which enemies lost hp. target: "nearest" | {enemy: id} | {x,y} | {dx,dy} (default: current facing). unlock (default true) raises the level to the skill\'s requirement first; resetCooldown clears cooldowns first.',
  forBot({ skill: z.string().regex(/^[a-z]{3,20}$/), target: z.union([z.literal('nearest'), z.object({ enemy: z.number().int().min(0) }).strict(), z.object({ x: z.number().finite(), y: z.number().finite() }).strict(), z.object({ dx: z.number().finite(), dy: z.number().finite() }).strict()]).optional(),
    unlock: z.boolean().default(true), resetCooldown: z.boolean().default(false), settleMs: z.number().int().min(100).max(5000).default(700) }),
  ({ bot, ...options }) => kit.castSkill(current(), bot, options));
tool('reset_character', 'Clear skill/attack cooldowns and/or refund trained stat points.',
  forBot({ cooldowns: z.boolean().default(true), stats: z.boolean().default(false) }), async ({ bot, cooldowns, stats }) => {
    if (cooldowns) await current().debug(bot, { op: 'reset_cooldowns' });
    const last = stats ? await current().debug(bot, { op: 'reset_stats' }) : null;
    return { bot, cooldownsCleared: cooldowns, statsReset: stats, player: last?.player ?? current().summary(bot) };
  });
tool('kill_enemies', 'Defeat living enemies in the bot\'s zone through the real kill path (XP, quest credit, gold and loot go to this bot). Filter by ids, kind (green, blue, pink, yellow, beetle, big, wisp, spider, wraith, golem) or radius; nearest first, at most max.',
  forBot({ ids: z.array(z.number().int().min(0)).max(100).optional(), kind: z.string().optional(), radius: z.number().positive().optional(), max: z.number().int().min(1).max(100).default(50) }),
  ({ bot, ...options }) => kit.killEnemies(current(), bot, options));
tool('spawn_enemy', 'Put an enemy exactly where a test needs it: kind (green, blue, pink, yellow, beetle, wisp, spider, wraith, golem), optional level (default: the kind\'s own, no spread), and either x/y or, by default, `distance` (3) east of the bot. Uses a free slot of that kind (a dead one first), on the nearest free ground in the bot\'s zone; it fights, drops and respawns like any other. Returns its id.',
  forBot({ kind: z.enum(['green', 'blue', 'pink', 'yellow', 'beetle', 'wisp', 'spider', 'wraith', 'golem']), level: z.number().int().min(1).max(100).optional(),
    x: z.number().finite().optional(), y: z.number().finite().optional(), distance: z.number().min(1.5).max(20).default(3) }),
  ({ bot, ...options }) => kit.spawnEnemy(current(), bot, options));
tool('respawn_enemy', 'Bring a dead enemy back next tick (id), or call the King Slime now (king:true) instead of waiting 5-10 minutes.',
  z.object({ bot, id: z.number().int().min(0).optional(), king: z.boolean().optional() }).strict(), async ({ bot, id, king }) => {
    if ((id === undefined) === !king) throw Error('Give exactly one of id or king:true.');
    return summarize(await current().debug(bot, king ? { op: 'summon_king' } : { op: 'respawn_enemy', id }));
  });
tool('set_god_mode', 'Turn invulnerability on or off for the whole world, to test damage and death after start.',
  z.object({ bot, enabled: z.boolean() }).strict(), async ({ bot, enabled }) => summarize(await current().debug(bot, { op: 'set_god_mode', enabled })));
tool('setup_character', 'Reach a state in one call: level, gold, items [{item,quantity,force}], quests to finish, then a teleport target. Unspecified parts stay unchanged.',
  forBot({ level: z.number().int().min(1).max(100).optional(), gold: z.number().int().min(0).optional(),
    items: z.array(z.object({ item: z.string(), quantity: z.number().int().min(1).max(9999).optional(), force: z.boolean().optional() }).strict()).max(40).optional(),
    finishQuests: z.array(z.string()).max(10).optional(), teleportTo: kit.targetSchema.optional(), heal: z.boolean().default(true) }),
  ({ bot, ...options }) => kit.setupCharacter(current(), bot, options));
tool('wait_for_event', 'Wait up to timeout ms for a NEW event: type (event, chat, system, notice, social, who, dialogue, error, debug), optional kind (levelup, skill, hit, slimeDie, death, respawn, pickup, portal...) and bot.',
  z.object({ type: z.string().default('event'), kind: z.string().optional(), bot: bot.optional(), timeout: z.number().int().min(100).max(30000).default(10000) }).strict(),
  options => kit.waitForEvent(current(), options));
tool('debug_command', 'Escape hatch: send one raw test-server shortcut ({op: set_level|give_xp|set_gold|set_hp|die|reset_stats|reset_cooldowns|set_god_mode|teleport|give_item|take_item|drop_item|quest|kill_enemy|respawn_enemy|spawn_enemy|summon_king, ...fields}).',
  forBot({ command: kit.debugSchema }), async ({ bot, command }) => summarize(await current().debug(bot, command)));
tool('social', 'Friends and parties as a player does them. command: {op: friend_request|friend_accept|friend_decline|friend_remove|party_invite|party_accept|party_decline|party_kick|party_promote, bot|id|name} | {op: party_leave} | {op: party_chat, text} | {op: refresh} | {op: who}. Name another connected bot with `bot` (resolved to its character id); friend_request and party_invite also take a player `name`. Returns what the bot was told: notices (ok:false is a refusal), its friends/requests/party now, party chat, and for who the online roster. A party holds 5; requests lapse after 60 s.',
  forBot({ command: kit.socialSchema }), ({ bot, command }) => current().social(bot, command));
tool('list_scenarios', 'List reusable real-protocol scenarios.', empty,
  () => ({ scenarios: Object.entries(scenarios).map(([name, s]) => ({ name, description: s.description })) }), true);
tool('run_scenario', 'Run a named scenario in a fresh private world, stop it, and return checks and a report path. Stop any interactive world first. City travel may take about a minute.',
  z.object({ name: z.enum(Object.keys(scenarios)) }).strict(), async ({ name }) => {
    if (world) throw Error('Stop the interactive world before running a scenario.');
    world = new TestWorld();
    try {
      const result = await runScenario(name, world);
      return { ...result, ...(result.passed ? {} : { failure: result.error }) };
    } finally { world = null; }
  });

async function shutdown() {
  if (closing) return;
  closing = true;
  await world?.stop();
  await server.close();
}
process.once('SIGINT', () => shutdown().catch(error => { console.error(error.message); process.exitCode = 1; }));
process.once('SIGTERM', () => shutdown().catch(error => { console.error(error.message); process.exitCode = 1; }));
// StdioServerTransport does not notify close on stdin EOF; clean up on parent disconnect.
process.stdin.once('end', () => shutdown().catch(error => { console.error(error.message); process.exitCode = 1; }));
server.server.onclose = () => { if (!closing) shutdown().catch(error => { console.error(error.message); process.exitCode = 1; }); };
server.connect(new StdioServerTransport()).catch(error => { console.error(error.message); process.exitCode = 1; });
