const { scenarios, runScenario } = require('./testing/scenarios.cjs');
const { TestWorld } = require('./testing/driver.cjs');
let active;
let interrupted = false;
async function shutdown() {
  interrupted = true;
  await active?.stop();
  process.exitCode = 130;
}
process.once('SIGINT', shutdown);
process.once('SIGTERM', shutdown);
(async () => {
  const [command = 'list', name = 'all', ...extra] = process.argv.slice(2);
  if (extra.length || !['list', 'run'].includes(command)) throw Error('Usage: node scripts/test-driver.cjs list | run <movement|ironhide|city|all>');
  if (command === 'list') {
    console.log(JSON.stringify(Object.entries(scenarios).map(([name, s]) => ({ name, description: s.description })), null, 2));
    return;
  }
  const names = name === 'all' ? Object.keys(scenarios) : [name];
  for (const scenario of names) {
    if (interrupted) break;
    active = new TestWorld();
    console.error(`Running ${scenario} in a private test world…`);
    const result = await runScenario(scenario, active);
    console.log(JSON.stringify(result, null, 2));
    if (!result.passed) process.exitCode = 1;
    active = null;
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
