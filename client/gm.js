'use strict';
// Game master console. The administrator character ([GM]Sork, built by the server for the gunning.se login Sork) types
// chat commands here; each one becomes a `debug` message, which the server runs only for that character and logs. Nothing
// in this file is a security check: another player who sends the same messages is refused. Replies arrive as `debug`
// packets and are printed in the chat log. Every string that came from the network goes through textContent.
(() => {
  let self = null, ref = 0;
  const pending = new Map();
  const say = text => window.Online.log(text, null, 'gm');
  const zoneNames = () => [WORLD_MAP.name || 'Greenmeadow', ...(WORLD_MAP.zones || []).map(z => z.name)];
  const spawnOf = zone => (zone === 0 ? WORLD_MAP.spawn : WORLD_MAP.zones?.[zone - 1]?.spawn);
  const number = text => { const n = Number(text); return text !== undefined && text !== '' && Number.isFinite(n) ? n : null; };
  const whole = text => { const n = number(text); return n !== null && Number.isInteger(n) ? n : null; };

  // A zone by number, or by (part of) its name: "crags", "2", "alderhaven" (the city is in zone 0).
  function findZone(text) {
    const names = zoneNames(), n = whole(text);
    if (n !== null) return n >= 0 && n < names.length ? n : null;
    const q = String(text || '').toLowerCase();
    if (!q) return null;
    if ('alderhaven'.startsWith(q) || 'city'.startsWith(q)) return 0;
    const hits = names.map((name, i) => [name.toLowerCase(), i]).filter(([name]) => name.includes(q));
    return hits.length === 1 ? hits[0][1] : null;
  }
  // An item by id, exact name or a unique part of either.
  function findItem(text) {
    const q = String(text || '').toLowerCase().replace(/\s+/g, ' ').trim(), items = window.WORLD_ITEMS || [];
    if (!q) return { error: 'Name an item.' };
    const exact = items.find(i => i.id === q || i.name.toLowerCase() === q);
    if (exact) return { item: exact };
    const hits = items.filter(i => i.id.includes(q.replace(/ /g, '_')) || i.name.toLowerCase().includes(q));
    if (hits.length === 1) return { item: hits[0] };
    if (!hits.length) return { error: `No item matches "${q}".` };
    return { error: `${hits.length} items match "${q}": ${hits.slice(0, 6).map(i => i.id).join(', ')}${hits.length > 6 ? ', …' : ''}` };
  }

  // name -> [usage, help, build(args) -> a debug command, or a string with the problem]
  const COMMANDS = {
    god: ['[on|off]', 'Take no damage (only you; others are unaffected).', a => ({ op: 'set_god_mode', enabled: a[0] ? !/^(off|0|false|no)$/i.test(a[0]) : !(self?.god) })],
    tp: ['<zone> [x y] | <x y>', 'Teleport: a zone number or name (to its start point, or to x y), or just x y in this zone.', a => {
      if (a.length === 2 && number(a[0]) !== null && number(a[1]) !== null) return { op: 'teleport', zone: self?.zone ?? 0, x: number(a[0]), y: number(a[1]) };
      const zone = findZone(a[0]);
      if (zone === null) return `Unknown zone. Zones: ${zoneNames().map((n, i) => `${i} ${n}`).join(', ')}.`;
      const start = spawnOf(zone), x = a.length >= 3 ? number(a[1]) : start?.x, y = a.length >= 3 ? number(a[2]) : start?.y;
      return x === null || y === null || x === undefined || y === undefined ? 'Use /tp <zone> [x y].' : { op: 'teleport', zone, x, y };
    }],
    goto: ['<player>', 'Teleport to an online player.', a => a.length ? { op: 'goto', name: a.join(' ') } : 'Name a player.'],
    give: ['<item> [quantity]', 'Add an item to your bags (ignores bag capacity). Id, name or a unique part of either.', a => {
      const last = a.length > 1 ? whole(a.at(-1)) : null, quantity = last ?? 1, found = findItem((last === null ? a : a.slice(0, -1)).join(' '));
      return found.error || { op: 'give_item', item: found.item.id, quantity, force: true };
    }],
    take: ['<item> [quantity]', 'Remove spare copies of an item from your bags.', a => {
      const last = a.length > 1 ? whole(a.at(-1)) : null, quantity = last ?? 1, found = findItem((last === null ? a : a.slice(0, -1)).join(' '));
      return found.error || { op: 'take_item', item: found.item.id, quantity };
    }],
    level: ['<1-100>', 'Set your level (XP resets; skills unlock as usual).', a => whole(a[0]) === null ? 'Use /level <1-100>.' : { op: 'set_level', level: whole(a[0]) }],
    xp: ['<amount>', 'Grant XP (levels up as usual).', a => whole(a[0]) === null || whole(a[0]) < 0 ? 'Use /xp <amount>.' : { op: 'give_xp', amount: whole(a[0]) }],
    gold: ['<amount>', 'Set your gold.', a => whole(a[0]) === null || whole(a[0]) < 0 ? 'Use /gold <amount>.' : { op: 'set_gold', gold: whole(a[0]) }],
    hp: ['[amount]', 'Set your health (default: full). Also revives.', a => ({ op: 'set_hp', hp: a[0] === undefined ? 1e9 : (number(a[0]) ?? 1e9) })],
    mana: ['[amount]', 'Set your mana, energy or rage (default: full).', a => ({ op: 'set_resource', amount: a[0] === undefined ? 1e9 : (number(a[0]) ?? 1e9) })],
    cd: ['', 'Clear every cooldown.', () => ({ op: 'reset_cooldowns' })],
    resetstats: ['', 'Take back every trained stat point.', () => ({ op: 'reset_stats' })],
    explore: ['', 'Uncover the fog on every map.', () => ({ op: 'explore_all' })],
    spawn: ['<kind> [level]', 'Put an enemy next to you (green, blue, pink, yellow, beetle, wisp, spider, wraith, golem, cinderlord, crab, wolf, yeti, wyrm, toad, croc, knight, hydra).', a => {
      if (!a[0]) return 'Name an enemy kind.';
      const level = a[1] === undefined ? undefined : whole(a[1]);
      return level === null ? 'Use /spawn <kind> [level].' : { op: 'spawn_enemy', kind: a[0].toLowerCase(), x: (self?.x ?? 0) + 2, y: (self?.y ?? 0) + 2, ...(level === undefined ? {} : { level }) };
    }],
    kill: ['<id>', 'Defeat the enemy with this id in your zone (the loot is yours).', a => whole(a[0]) === null ? 'Use /kill <enemy id>.' : { op: 'kill_enemy', id: whole(a[0]) }],
    respawn: ['<id>', 'Bring a defeated enemy back at its own spawn point.', a => whole(a[0]) === null ? 'Use /respawn <enemy id>.' : { op: 'respawn_enemy', id: whole(a[0]) }],
    quest: ['<id> <accept|complete|claim|finish|reset>', 'Move a quest along (finish = accept, fill and claim, with its prerequisites).', a =>
      a.length === 2 && /^(accept|complete|claim|finish|reset)$/.test(a[1]) ? { op: 'quest', id: a[0], action: a[1] } : 'Use /quest <id> <accept|complete|claim|finish|reset>.'],
    king: ['', 'Summon the King Slime now.', () => ({ op: 'summon_king' })],
    die: ['', 'Be defeated (with the normal death penalty).', () => ({ op: 'die' })],
  };

  function help() {
    say('Game master commands (/gmcommands shows this list):');
    for (const [name, [usage, text]] of Object.entries(COMMANDS)) say(`/${name}${usage ? ' ' + usage : ''} — ${text}`);
  }
  function brief(op, result) {
    switch (op) {
      case 'teleport': case 'goto': return `now in ${zoneNames()[result.zone] || 'zone ' + result.zone} at ${Math.round(result.x)}, ${Math.round(result.y)}`;
      case 'set_god_mode': return result.godMode ? 'god mode ON (only you)' : 'god mode off';
      case 'set_level': return `level ${result.level}`;
      case 'give_xp': return `level ${result.level}, ${result.xp} xp`;
      case 'give_item': case 'take_item': return `${result.item}: you now have ${result.owned}`;
      case 'set_gold': return `${result.gold} gold`;
      case 'set_hp': return `${Math.round(result.hp)} / ${Math.round(result.maxHp)} health`;
      case 'set_resource': return `${Math.round(result.resource)} / ${Math.round(result.maxResource)}`;
      case 'spawn_enemy': return `enemy ${result.id} (${result.kind}, level ${result.level}) at ${Math.round(result.x)}, ${Math.round(result.y)}`;
      case 'kill_enemy': return `enemy ${result.id} (${result.kind}) defeated`;
      default: return 'done';
    }
  }

  window.GM = {
    // The own snapshot, kept for the commands that need your zone and position (and whether god mode is on).
    onSelf(character) { self = character?.gm ? character : null; },
    // True when the text was a game master command (so it is not sent as chat). Anyone else's slash text goes on to the
    // party and friend commands, and a command typed by a non-GM is simply not recognised here.
    command(text) {
      if (!window.Online?.gm) return false;
      const [word, ...args] = text.trim().split(/\s+/), name = word.slice(1).toLowerCase();
      if (name === 'gm' || name === 'gmhelp' || name === 'gmcommands') { help(); return true; }
      const entry = Object.hasOwn(COMMANDS, name) ? COMMANDS[name] : null;
      if (!entry) return false;
      const built = entry[2](args);
      if (typeof built === 'string') { say(`/${name}: ${built}`); return true; }
      const id = ++ref;
      if (!window.Online.send({ type: 'debug', ref: id, command: built })) { say('Not connected.'); return true; }
      pending.set(id, { name, op: built.op });
      return true;
    },
    onReply(packet) {
      const asked = pending.get(packet.ref);
      pending.delete(packet.ref);
      if (!asked) return;
      say(packet.ok ? `/${asked.name}: ${brief(asked.op, packet.result || {})}` : `/${asked.name}: ${packet.error || 'refused'}`);
    },
  };
})();
