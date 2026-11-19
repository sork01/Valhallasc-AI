// Corrupt actual driver inputs / received snapshots, then run the scenario through MCP.
// These mutations never edit game source, the executable or the database.
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const mutation = process.env.FISH_CHECK_MUTATION;
if (mutation) {
  const { TestWorld } = require('../scripts/testing/driver.cjs');
  const candidates = mutation === 'spots' ? JSON.parse(require('node:fs').readFileSync(path.join(root, 'world/map.txt'))).fishingSpots : null;
  if (mutation === 'input') {
    const action = TestWorld.prototype.action;
    TestWorld.prototype.action = function(bot, packet) {
      return packet.type === 'fish' ? Promise.resolve() : action.call(this, bot, packet);
    };
  } else {
    const merge = TestWorld.prototype.merge;
    TestWorld.prototype.merge = function() {
      for (const [bot, view] of this.views) {
        if (mutation === 'clock') view.fishingTime = 0;
        if (mutation === 'spots' && view.fishingSpots) {
          view.fishingSpots = candidates;
        }
        if (mutation === 'privacy' && bot === 'FishWitness') {
          for (const p of view.players) if (p.fishing) p.fishDeadline = 42;
        }
        if (mutation === 'persistence' && this.fishingRestarted && bot === 'FishCheck') {
          for (const p of view.players) p.inventory = p.inventory.filter(s => s.item !== 'rod_emberline_rod');
        }
      }
      return merge.call(this);
    };
    if (mutation === 'persistence') {
      const restart = TestWorld.prototype.restart;
      TestWorld.prototype.restart = async function() {
        this.fishingRestarted = true;
        return restart.call(this);
      };
    }
  }
} else if (require.main === module) {
  const assert = require('node:assert/strict');
  const { spawnSync } = require('node:child_process');
  const failures = {
    input: 'timed out',
    clock: 'Snapshot carries the shared Unix clock',
    spots: 'Snapshot contains active rich spots from the candidate pool',
    privacy: 'Other players receive neither deadline nor collection log',
    persistence: 'Inventory and fishing records survive SQLite restart',
  };
  for (const [name, expected] of Object.entries(failures)) {
    const run = spawnSync(process.execPath, ['scripts/test-via-mcp.cjs', 'run', 'fishing'], {
      cwd: root, encoding: 'utf8', timeout: 60000,
      env: { ...process.env, FISH_CHECK_MUTATION: name, NODE_OPTIONS: `--require=${__filename}` },
    });
    const output = run.stdout + run.stderr;
    assert(!run.error && run.status !== 0 && output.includes('"passed": false') && output.includes(expected), `${name}: expected scenario assertion, got ${output}`);
    console.log(`Caught fishing MCP mutation: ${name} (${expected})`);
  }
}
