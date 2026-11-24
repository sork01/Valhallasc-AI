// Exercise the field's actual pointer/touch and selection handlers with the production PvP state.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = file => fs.readFileSync(path.join(__dirname, '..', 'client', file), 'utf8');
let field = read('field.js');
if (process.env.MUTATE === 'single') {
  assert.ok(field.includes("op: 'arena_target'"));
  field = field.replace("op: 'arena_target'", "op: 'attack'");
}
function slice(start, end) {
  const from = field.indexOf(start);
  const to = field.indexOf(end, from);
  assert.ok(from >= 0 && to > from, start);
  return field.slice(from, to);
}

const elements = new Map(), messages = [];
const sandbox = vm.createContext({
  document: { getElementById(id) {
    if (!elements.has(id)) elements.set(id, { addEventListener() {} });
    return elements.get(id);
  } },
  Online: { id: 'me', connected: true, send(message) { messages.push(structuredClone(message)); return true; } },
  City: { npcs: [] },
  setInterval: () => 1,
  clearInterval() {},
});
sandbox.window = sandbox;
vm.runInContext(`
  const hero = { hp: 100, target: null, pvpTargetId: null };
  const opponent = { id: 'rival', x: 100, y: 100, hp: 100 };
  const ally = { id: 'ally', x: 200, y: 100, hp: 100 };
  const remotePlayers = new Map([[opponent.id, opponent], [ally.id, ally]]);
  const VW = 500, VH = 300, MAP = 500, running = true, paused = false;
  const pointer = {}, signs = [], chests = [];
  const cv = { getBoundingClientRect: () => ({ left: 0, top: 0, width: VW, height: VH }) };
  const w2s = (x, y) => [x, y];
  const pickSlime = () => null, pickPortal = () => null;
  const rememberPointer = e => { pointer.x = e.clientX; pointer.y = e.clientY; };
  const clamp = (x, min, max) => Math.min(max, Math.max(min, x));
  const emitHud = () => {};
  let autoAttackTarget = null, cityRoute, pendingNpc, pendingChest, npcTarget, marker;
  ${slice('  function onPointerDown(e) {', '  // A boss sign is read')}
  window.Field = {
    hero, canAct: true, get remotePlayers() { return [...remotePlayers.values()]; },
    clearInput() { autoAttackTarget = null; pointer.down = false; },
    click: onPointerDown,
    ${slice('    tapAt(clientX, clientY)', '    startNearestAutoattack()')}
    ${slice('    stopMoving() {', '    setPaused(p)')}
    ${slice('    targetPlayer(id, attack = false)', '    // Shows `text`')}
  };
`, sandbox);
vm.runInContext(read('pvp.js'), sandbox);
const { Field, Pvp } = sandbox;
const select = (x = 100, y = 100) => Field.click({ clientX: x, clientY: y });
const takeMessages = () => messages.splice(0);
const attack = { type: 'pvp', command: { op: 'arena_target', id: 'rival' } };

const trial = { gauntlet: { fight: 1, of: 5, opponent: { id: 'rival', name: 'Arena Warrior' } } };
Pvp.onPacket(trial);
select();
assert.deepEqual(takeMessages(), [], 'older servers keep manual targeting');
Pvp.reset();

Pvp.onPacket({ ...trial, arenaAutoattack: true });
assert.equal(Field.hero.pvpTargetId, 'rival', 'the banner aims at the opponent');
assert.deepEqual(takeMessages(), [], 'the banner never starts an attack');
select();
assert.deepEqual(takeMessages(), [attack], 'one click starts a sustained Arena attack');
Field.stopMoving();
assert.deepEqual(takeMessages(), [{ type: 'input', dx: 0, dy: 0 }], 'opening a panel keeps the attack');
select(400);
assert.deepEqual(takeMessages(), [{ type: 'move', x: 400, y: 100 }], 'clicking open ground moves and cancels');
Field.stopMoving();
assert.deepEqual(takeMessages(), [{ type: 'stop' }]);

Pvp.onPacket({ gauntlet: null, arena: { size: 2, teams: [['me', 'ally'], ['rival']] } });
const panel = [];
Pvp.render({ append: (...rows) => panel.push(...rows) }, () => null, (_tag, text) => text);
assert.ok(panel.includes('Select an Arena opponent to attack automatically.'), 'the Arena shows the selection control');
Field.tapAt(100, 100);
assert.deepEqual(takeMessages(), [attack], 'tapping an opposing player works in a team match');
select(200);
assert.deepEqual(takeMessages(), [{ type: 'stop' }], 'changing selection to a teammate stops the old attack');
select(200);
assert.deepEqual(takeMessages(), [], 'no attack is sent for a teammate');
Pvp.onPacket({ arena: null, duel: { id: 'rival' }, flag: true });
select();
assert.deepEqual(takeMessages(), [], 'duel selection keeps its manual attack controls');

console.log('Arena client selection, touch, movement, team, and fallback checks passed.');
