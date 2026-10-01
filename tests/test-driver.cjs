const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const { TestWorld, root, actionSchema, delay } = require('../scripts/testing/driver.cjs');

test('private driver: isolated storage, normal actions, resume, credentials, and shutdown', { timeout: 30000 }, async () => {
  const w = new TestWorld();
  try {
    const info = await w.start();
    assert.match(info.url, /^http:\/\/127\.0\.0\.1:\d+\/$/);
    assert.ok(info.database.startsWith(path.join(root, 'test-results/driver-')));
    assert.notEqual(info.database, path.join(root, 'data/valhalla.sqlite'));
    await w.connect({ bot: 'Tester', class: 'mage' });
    const id = w.player('Tester').id;
    const token = w.bots.get('Tester').token;
    assert.ok(token && id);
    assert.throws(() => actionSchema.parse({ type: 'move', x: 1, y: 1, hp: 999 }));
    await assert.rejects(w.action('Tester', { type: 'set_hp', hp: 999 }));
    assert.throws(() => actionSchema.parse({ type: 'join', token }));
    assert.throws(() => actionSchema.parse({ type: 'move', x: Infinity, y: 1 }));
    await w.action('Tester', { type: 'equip', armor: 'runic', weapon: 'crystal' });
    await w.waitFor(() => w.player('Tester').look.mageWeapon === 'crystal');
    await w.action('Tester', { type: 'ping', nonce: 42 });
    await w.waitFor(() => w.events.some(e => e.type === 'pong' && e.nonce === 42));
    await Promise.all(Array.from({ length: 90 }, (_, i) => w.action('Tester', { type: 'ping', nonce: 100 + i })));
    await w.waitFor(() => w.events.some(e => e.type === 'pong' && e.nonce === 189));
    assert.ok(!w.events.some(e => e.fatal), 'Concurrent actions stay below the server rate limit');
    assert.equal(w.spacingFailure, null);
    const inspection = JSON.stringify(w.inspect());
    assert.ok(!inspection.includes(token));
    const artifact = w.saveReport({ test: true });
    assert.ok(!fs.readFileSync(artifact, 'utf8').includes(token));
    await w.disconnect('Tester');
    assert.equal((await (await fetch(info.url + 'health')).json()).online, 0);
    await w.connect({ bot: 'Tester' });
    assert.equal(w.player('Tester').id, id);
    assert.equal(w.player('Tester').look.class, 'mage');
    assert.equal(w.player('Tester').look.mageWeapon, 'crystal');
    await assert.rejects(w.connect({ bot: 'Tester' }), /already connected/);
  } finally { await w.stop(); }
  await assert.rejects(fetch(w.url + 'health', { signal: AbortSignal.timeout(1000) }));
  await w.stop(); // Cleanup is idempotent.
});

test('MCP: real SDK handshake, tools, invalid actions, world lifecycle, and parent disconnect', { timeout: 30000 }, async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root,
    env: { VALHALLA_BIND: '0.0.0.0:8080', VALHALLA_DB: '/tmp/mcp-must-not-use.sqlite', VALHALLA_ORIGIN: 'https://production.invalid' }, stderr: 'pipe' });
  const client = new Client({ name: 'valhallasc-test', version: '1.0.0' });
  let url;
  const call = async (name, args = {}) => {
    const result = await client.callTool({ name, arguments: args });
    assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
    return result.structuredContent;
  };
  try {
    await client.connect(transport);
    const listed = await client.listTools();
    for (const name of ['start_world', 'stop_world', 'connect_bot', 'disconnect_bot', 'send_action', 'inspect_world', 'wait_world', 'list_scenarios', 'run_scenario']) {
      assert.ok(listed.tools.some(t => t.name === name), `Advertises ${name}`);
    }
    assert.deepEqual((await call('list_scenarios')).scenarios.map(s => s.name), ['movement', 'ironhide', 'city', 'quests', 'quest_combat']);
    const first = await call('start_world');
    url = first.url;
    assert.match(url, /^http:\/\/127\.0\.0\.1:\d+\/$/);
    assert.notEqual(first.database, '/tmp/mcp-must-not-use.sqlite');
    await call('connect_bot', { bot: 'McpMage', class: 'mage' });
    const rejected = await client.callTool({ name: 'send_action', arguments: { bot: 'McpMage', action: { type: 'move', x: 5, y: 5, hp: 999 } } });
    assert.equal(rejected.isError, true);
    await call('send_action', { bot: 'McpMage', action: { type: 'equip', armor: 'runic', weapon: 'crystal' } });
    const parallel = await Promise.all([call('inspect_world', { bot: 'McpMage', events: 0 }), call('wait_world', { milliseconds: 100 })]);
    assert.equal(parallel[0].snapshot.look.class, 'mage');
    assert.ok(parallel[1].snapshot.tick >= 0);
    const stopped = await call('stop_world');
    assert.equal(stopped.running, false);
    assert.ok(fs.existsSync(stopped.artifact));
    await assert.rejects(fetch(url + 'health', { signal: AbortSignal.timeout(1000) }));
    const scenario = await call('run_scenario', { name: 'movement' });
    assert.equal(scenario.passed, true);
    assert.ok(fs.existsSync(scenario.artifact));
    const second = await call('start_world');
    url = second.url;
    assert.notEqual(second.database, first.database);
    await call('connect_bot', { bot: 'McpWarrior' });
  } finally { await client.close(); }
  // Closing the parent's stdio must also stop the Rust child, not leave a world behind.
  if (url) {
    let alive = true;
    for (let i = 0; i < 40 && alive; i++) {
      try { await fetch(url + 'health', { signal: AbortSignal.timeout(200) }); await delay(50); } catch { alive = false; }
    }
    assert.equal(alive, false, 'MCP parent disconnect stops the private Rust server');
  }
});
