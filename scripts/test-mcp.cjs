// stdout belongs exclusively to the MCP stdio transport.
const { McpServer } = require('@modelcontextprotocol/sdk/server/mcp.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { z } = require('zod');
const { TestWorld, actionSchema, botSchema } = require('./testing/driver.cjs');
const { scenarios, runScenario } = require('./testing/scenarios.cjs');

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
tool('start_world', 'Start an isolated Rust server on loopback with a fresh test database. Build the binary first. Never connects to production.', empty, async () => {
  if (world) throw Error('A world is already active. Call stop_world first.');
  world = new TestWorld();
  try { return await world.start(); } catch (error) { world = null; throw error; }
});
tool('stop_world', 'Disconnect bots and gracefully stop the private server. Test artifacts remain available.', empty, async () => {
  if (!world) return { running: false };
  const result = await world.stop();
  if (world.runDir) result.artifact = world.saveReport({ interactive: true });
  world = null;
  return result;
});
tool('connect_bot', 'Create a bot with a class. Reusing a disconnected bot name resumes its character; its original class is retained. Keys stay internal.', botSchema,
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
