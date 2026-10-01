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
    await w.waitFor(() => w.events.some(e => e.type === 'error' && e.text.includes('must own')));
    assert.equal(w.player('Tester').look.mageWeapon, 'ash');
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
    assert.equal(w.player('Tester').look.mageWeapon, 'ash');
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
    assert.deepEqual((await call('list_scenarios')).scenarios.map(s => s.name), ['skills', 'movement', 'ironhide', 'city', 'quests', 'quest_combat', 'inventory', 'stats', 'crags', 'bags', 'shortcuts', 'social']);
    const first = await call('start_world');
    url = first.url;
    assert.match(url, /^http:\/\/127\.0\.0\.1:\d+\/$/);
    assert.notEqual(first.database, '/tmp/mcp-must-not-use.sqlite');
    await call('connect_bot', { bot: 'McpMage', class: 'mage' });
    const rejected = await client.callTool({ name: 'send_action', arguments: { bot: 'McpMage', action: { type: 'move', x: 5, y: 5, hp: 999 } } });
    assert.equal(rejected.isError, true);
    await call('send_action', { bot: 'McpMage', action: { type: 'equip', armor: 'runic', weapon: 'crystal' } });
    await call('send_action', { bot: 'McpMage', action: { type: 'equip', slots: { hands: 'none' } } });
    await call('wait_world', { milliseconds: 100 });
    const slotsResult = await call('inspect_world', { bot: 'McpMage', events: 0 });
    assert.equal(slotsResult.snapshot.look.mageWeapon, 'none');
    await call('send_action', { bot: 'McpMage', action: { type: 'equip', slots: { hands: 'mage_weapon_ash' } } });
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

test('MCP shortcuts: every tool advertised, strict inputs, and server-side effects through the real transport', { timeout: 60000 }, async () => {
  const client = new Client({ name: 'valhallasc-shortcuts', version: '1.0.0' });
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe' }));
  const raw = async (name, args = {}) => client.callTool({ name, arguments: args });
  const call = async (name, args = {}) => {
    const result = await raw(name, args);
    assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`);
    return result.structuredContent;
  };
  try {
    const names = (await client.listTools()).tools.map(t => t.name);
    for (const name of ['restart_world', 'describe_world', 'set_level', 'give_xp', 'set_gold', 'set_health', 'give_item', 'take_item', 'drop_item', 'teleport', 'walk_to', 'talk_to', 'quest',
      'cast_skill', 'reset_character', 'kill_enemies', 'respawn_enemy', 'set_god_mode', 'setup_character', 'wait_for_event', 'debug_command', 'social']) assert.ok(names.includes(name), `Advertises ${name}`);
    const catalog = await call('describe_world', { what: 'quests' });
    assert.ok(catalog.quests.length >= 5 && catalog.quests.every(q => q.id && q.objectives.length));
    assert.ok((await call('describe_world', { what: 'skills' })).skills.length >= 30);
    await call('start_world', { startLevel: 3, levelSpread: 0, godMode: false });
    await call('connect_bot', { bot: 'Gm', class: 'assassin' });
    assert.equal((await call('inspect_world', { bot: 'Gm', events: 0 })).snapshot.level, 3, 'start_world honours startLevel');
    // Inputs are strict: unknown fields, impossible levels and bad targets never reach the server.
    for (const [name, args] of [['set_level', { bot: 'Gm', level: 0 }], ['set_level', { bot: 'Gm', level: 5, hp: 1 }], ['teleport', { bot: 'Gm', to: { zone: 1, x: 'a', y: 2 } }],
      ['debug_command', { bot: 'Gm', command: { op: 'nuke' } }], ['give_item', { bot: 'Gm', item: 'x', quantity: 0 }],
      ['social', { bot: 'Gm', command: { op: 'party_disband' } }], ['social', { bot: 'Gm', command: { op: 'party_leave', extra: 1 } }], ['social', { bot: 'Gm', command: { op: 'party_chat', text: '' } }]]) assert.equal((await raw(name, args)).isError, true, `${name} rejects ${JSON.stringify(args)}`);
    assert.equal((await raw('give_item', { bot: 'Gm', item: 'no_such_item' })).isError, true, 'Unknown items are server errors');
    assert.equal((await raw('teleport', { bot: 'Gm', to: { npc: 'nobody' } })).isError, true);
    const leveled = await call('set_level', { bot: 'Gm', level: 20 });
    assert.equal(leveled.player.level, 20);
    assert.equal(leveled.unlocked.length, 9, 'Levels 4-20 unlock nine skills; the level-2 skill was already known at level 3');
    const hurt = await call('set_health', { bot: 'Gm', hp: 5 });
    assert.ok(hurt.player.hp >= 5 && hurt.player.hp < 10, 'hp is set (natural regeneration adds a few tenths before the snapshot)');
    assert.equal((await call('set_health', { bot: 'Gm', hp: 1e9 })).player.hp, leveled.player.maxHp);
    await call('give_xp', { bot: 'Gm', amount: 100000 });
    assert.ok((await call('inspect_world', { bot: 'Gm', events: 0 })).snapshot.level > 20);
    await call('set_gold', { bot: 'Gm', gold: 123 });
    await call('give_item', { bot: 'Gm', item: 'linen_satchel' });
    const stacked = await call('give_item', { bot: 'Gm', item: 'ember_core', quantity: 4 });
    assert.equal(stacked.owned, 4);
    assert.equal(stacked.bagCapacity, 22);
    assert.equal((await call('take_item', { bot: 'Gm', item: 'ember_core', quantity: 4 })).owned, 0);
    const finished = await call('quest', { bot: 'Gm', id: 'king_challenge', action: 'finish' });
    assert.deepEqual(finished.claimed, ['slime_patrol', 'ironhide_hunt', 'king_challenge']);
    assert.equal((await call('quest', { bot: 'Gm', id: 'meadow_bounty', action: 'complete' })).quest.counts[0], 8);
    const moved = await call('teleport', { bot: 'Gm', to: { spawn: 1 } });
    assert.equal(moved.player.zone, 1);
    assert.equal(moved.player.x, 48);
    const cast = await call('cast_skill', { bot: 'Gm', skill: 'evasion' });
    assert.equal(cast.cast, true);
    assert.ok(cast.buffs.some(b => b.id === 'evasion'));
    assert.equal((await call('cast_skill', { bot: 'Gm', skill: 'twinbolt' }).catch(e => ({ error: e.message }))).error?.includes('not a assassin skill'), true);
    assert.equal((await call('reset_character', { bot: 'Gm' })).player.skillCd.evasion, undefined);
    const slain = await call('kill_enemies', { bot: 'Gm', kind: 'wisp', max: 2 });
    assert.equal(slain.count, 2);
    assert.ok(slain.xpGained > 0 || slain.levelsGained > 0);
    // God mode is off in this world, so the bot can be defeated for real and then respawns.
    await call('set_health', { bot: 'Gm', defeat: true });
    assert.equal((await call('inspect_world', { bot: 'Gm', events: 0 })).snapshot.dead, true);
    const respawn = await call('wait_for_event', { type: 'event', kind: 'respawn', bot: 'Gm', timeout: 8000 });
    assert.equal(respawn.received, true);
    assert.equal((await call('set_god_mode', { bot: 'Gm', enabled: true })).godMode, true);
    const setup = await call('setup_character', { bot: 'Gm', level: 7, gold: 50, items: [{ item: 'slime_gel', quantity: 3 }], teleportTo: { npc: 'healer' } });
    assert.equal(setup.player.level, 7);
    assert.equal(setup.player.zone, 0);
    assert.ok(setup.steps.includes('teleport'));
    const talked = await call('talk_to', { bot: 'Gm', npc: 'healer' });
    assert.ok(talked.offers.length > 0);
    await call('restart_world');
    assert.equal((await call('inspect_world', { bot: 'Gm', events: 0 })).snapshot.level, 7);
    await call('stop_world');
  } finally { await client.close(); }
});
