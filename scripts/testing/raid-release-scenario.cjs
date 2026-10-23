// Release integration only: real entry, nine hires, one walked hall and live boss casts.
// Debug kills finish fixtures promptly; this scenario does not measure balance.
module.exports = (kit, map) => ({
  description: 'Open Chained Forge: level gate, muster contracts, ten living fighters, walked hall, boss casts, rewards and safe exit.',
  startLevel: 99, levelSpread: 0, godMode: true,
  async run(w, check) {
    const bot = 'RaidRelease', area = map.zones[45];
    check(!area.sealedTemplate, 'The released raid template is open');
    await w.connect({ bot, class: 'hunter' });
    await kit.teleport(w, bot, { zone: 45, x: 133, y: 27 });
    await w.action(bot, { type: 'move', x: 133, y: 24 });
    await w.waitFor(() => w.player(bot).zone === 46, 15000, 'Public muster entrance');
    await w.action(bot, { type: 'stop' });
    check(w.player(bot).y > 290, 'The public door reaches the separate muster chamber');
    await w.action(bot, { type: 'move', x: 30, y: 296 });
    await w.advance(1800); await w.action(bot, { type: 'stop' });
    check(w.player(bot).y > 294, 'A lone player cannot enter the descent');
    await w.debug(bot, { op: 'set_gold', gold: 2000000 });
    await kit.teleport(w, bot, { npc: 'cf_quartermaster' });
    for (const cls of ['warrior', 'warrior', 'mage', 'mage', 'assassin', 'assassin', 'priest', 'priest', 'hunter'])
      await kit.talkTo(w, bot, 'cf_quartermaster', 'merc_' + cls);
    await w.waitFor(() => w.views.get(bot).players.length === 10, 10000, 'Nine real contracts');
    check(w.player(bot).gold === 965000, 'Nine contracts charge the normal level-99 price');
    check(w.player(bot).raidSupport?.others === 9, 'The ten-fighter strength bonus is active');
    await w.action(bot, { type: 'move', x: 30, y: 296 });
    await w.waitFor(() => Math.hypot(w.player(bot).x - 62, w.player(bot).y - 290) < 3, 15000, 'Ten-fighter inner gate');
    await w.action(bot, { type: 'stop' });
    check(w.views.get(bot).players.length === 10, 'The full company crosses the inner gate');
    for (const [x, y] of area.forgeHalls[0].route.slice(1)) await kit.walkTo(w, bot, { x, y }, 30000);
    check(Math.hypot(w.player(bot).x - 84, w.player(bot).y - 272) < .6, 'The company walks actual collision into the first hall');
    const boss = w.views.get(bot).slimes.find(s => s.kind === 'cf_kettil');
    await w.action(bot, { type: 'target', id: boss.id });
    await w.action(bot, { type: 'attack', fx: 1, fy: 0 });
    await w.waitFor(() => (w.views.get(bot).bossMech || []).some(f => f.boss === boss.id && f.tele?.length), 40000, 'Actual first-boss cast');
    check(true, 'The actual first Warden emits authoritative cast geometry');
    await w.debug(bot, { op: 'kill_enemy', id: boss.id });
    await w.waitFor(() => w.views.get(bot).slimes.find(s => s.id === boss.id)?.dead, 5000, 'First Warden fixture kill');
    check(w.views.get(bot).slimes.filter(s => s.kind.startsWith('cf_') && !s.dead).length >= 49, 'Other encounters remain alive after one boss dies');
    const pieceIds = new Set(JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname, '../../world/items.txt'))).filter(i => i.source === 'chained_forge').map(i => i.id));
    await w.waitFor(() => w.player(bot).inventory.some(s => pieceIds.has(s.item)) || w.views.get(bot).drops.some(d => pieceIds.has(d.item)), 5000, 'Actual orange boss rewards');
    check(true, 'The real kill pays guaranteed Chainforged orange rewards');
    await kit.teleport(w, bot, { zone: 46, x: 30, y: 303 });
    await w.action(bot, { type: 'move', x: 22, y: 303 });
    await w.waitFor(() => w.player(bot).zone === 45, 15000, 'Safe raid return');
    await w.action(bot, { type: 'stop' });
    await w.waitFor(() => !w.views.get(bot).players.some(p => p.look.name.startsWith('Merc ')), 5000, 'Contracts end outside');
    check(Math.hypot(w.player(bot).x - 127, w.player(bot).y - 25) < 2, 'The exit lands safely outside the entrance disc');
  }
});
