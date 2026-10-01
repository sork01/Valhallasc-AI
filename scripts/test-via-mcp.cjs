// Run scenarios through the actual MCP handshake and run_scenario tool.
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');

async function main() {
  const options = process.argv.slice(2);
  const registered = options.includes('--registered');
  const positional = options.filter(o => o !== '--registered');
  const [command = 'run', name = 'all', ...extra] = positional;
  if (extra.length || !['list', 'run'].includes(command)) throw Error('Usage: node scripts/test-via-mcp.cjs [--registered] list | run <scenario|all>');
  let launch = { command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root };
  if (registered) {
    const configuration = JSON.parse(execFileSync('codex', ['mcp', 'get', 'valhallasc-testing', '--json'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }));
    if (!configuration.enabled || configuration.transport.type !== 'stdio') throw Error('valhallasc-testing must be enabled and use stdio.');
    const { command, args, cwd, env } = configuration.transport;
    launch = { command, args, cwd: cwd || root, ...(env ? { env: { ...process.env, ...env } } : {}) };
  }
  const transport = new StdioClientTransport({ ...launch, stderr: 'pipe' });
  let startupError = '';
  transport.stderr.on('data', data => { startupError = (startupError + data.toString()).slice(-4000); });
  const client = new Client({ name: 'valhallasc-scenario-runner', version: '1.0.0' });
  const close = () => client.close().catch(() => {});
  process.once('SIGINT', () => { process.exitCode = 130; close(); });
  process.once('SIGTERM', () => { process.exitCode = 130; close(); });
  try {
    await client.connect(transport);
    const call = (name, args = {}) => client.callTool({ name, arguments: args }, undefined, { timeout: 600000 });
    const listed = await call('list_scenarios');
    if (listed.isError) throw Error(listed.content[0].text);
    const scenarios = listed.structuredContent.scenarios;
    if (command === 'list') { console.log(JSON.stringify(scenarios, null, 2)); return; }
    const names = name === 'all' ? scenarios.map(s => s.name) : [name];
    for (const scenario of names) {
      if (process.exitCode === 130) break;
      console.error(`MCP run_scenario: ${scenario}`);
      const result = await call('run_scenario', { name: scenario });
      console.log(JSON.stringify(result.structuredContent || result.content, null, 2));
      if (result.isError) process.exitCode = 1;
    }
  } catch (error) {
    if (startupError) console.error(startupError.trim());
    throw error;
  } finally { await close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
