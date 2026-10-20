// Real private protocol coverage for the level-30 Bifrost Reach dungeon. No progression grind.
module.exports = (kit, map) => ({
  description: 'The Shattered Span: level gate, both exits, party isolation, three quests, boss loot and saved rewards.',
  startLevel: 30, levelSpread: 0, godMode: true,
  async run(w, check) {
    const hero = 'SpanRunner', ally = 'SpanAlly', other = 'SpanOther', low = 'SpanLow';
    const span = map.zones[41], parent = map.zones[6];
    const q = (bot, id) => w.player(bot).quests.find(q => q.id === id);
    const enter = async bot => {
      await kit.teleport(w, bot, { zone: 7, x: 58, y: 133 });
      await w.action(bot, { type: 'move', x: 58, y: 128 });
      await w.waitFor(() => w.player(bot).zone === 42, 12000, `${bot} enters The Shattered Span`);
      await w.action(bot, { type: 'stop' });
    };

    for (const bot of [hero, ally, other, low]) await w.connect({ bot, class: 'warrior' });

    // Level gate: 29 is refused
    await w.debug(low, { op: 'set_level', level: 29 });
    await kit.teleport(w, low, { zone: 7, x: 58, y: 133 });
    const before = new Set(w.events);
    await w.action(low, { type: 'move', x: 58, y: 128 });
    await w.waitFor(() => w.events.some(e => !before.has(e) && e.bot === low && e.type === 'error' && /level 30/.test(e.text)), 12000, 'Level 29 is refused');
    await w.action(low, { type: 'stop' });
    check(w.player(low).zone === 7, 'Level-29 heroes stay in Bifrost Reach');

    // Party formation
    await w.social(hero, { op: 'party_invite', bot: ally });
    await w.social(ally, { op: 'party_accept', bot: hero });

    // Accept quests
    for (const bot of [hero, ally]) {
      for (const [npc, id] of [['span_guide', 'span_entry'], ['span_guide', 'span_toll'], ['span_chronicler', 'span_spectrum']]) {
        await kit.teleport(w, bot, { npc });
        await kit.talkTo(w, bot, npc, `quest:accept:${id}`);
        await w.waitFor(() => !!q(bot, id), 5000, `Accept ${id}`);
      }
    }

    await enter(hero); await enter(ally); await enter(other);

    // Speak to the watcher inside
    await kit.teleport(w, hero, { npc: 'span_witness' });
    await kit.talkTo(w, hero, 'span_witness');
    await w.waitFor(() => q(hero, 'span_entry')?.counts[0] === 1, 5000, 'Speak to the Last Watcher');

    await kit.teleport(w, hero, { zone: 42, x: 56, y: 99 });
    const ids = bot => new Set(w.views.get(bot).slimes.map(s => s.id));
    check([...ids(hero)].every(id => ids(ally).has(id)) && [...ids(hero)].every(id => !ids(other).has(id)),
      'Party members share enemies and another party has separate enemies');
    check(w.views.get(hero).slimes.filter(s => !s.dead).length === 15, 'Twelve ordinary foes and three guardians occupy the dungeon');

    // Entrance return
    await w.action(hero, { type: 'move', x: 49, y: 99 });
    await w.waitFor(() => w.player(hero).zone === 7, 15000, 'Entrance return to Bifrost Reach');
    await kit.teleport(w, hero, { npc: 'span_guide' });
    await kit.talkTo(w, hero, 'span_guide', 'quest:claim:span_entry');
    await w.waitFor(() => q(hero, 'span_entry')?.claimed, 5000, 'Claim entry quest');
    await enter(hero);

    // Ordinary materials
    for (const kind of ['span_lynx', 'span_sentinel', 'span_caster']) {
      const enemy = w.views.get(hero).slimes.find(s => s.kind === kind && !s.dead);
      await w.debug(hero, { op: 'kill_enemy', id: enemy.id });
      await w.waitFor(() => w.views.get(hero).drops.some(d => d.item === `${kind}_relic`), 5000, `${kind} material`);
      check(true, `${kind} awards its own material`);
    }

    // Boss kills: Torstein, Sunniva, and Vaelor (span_archon)
    for (const [i, kind] of ['span_warden', 'span_weaver', 'span_archon'].entries()) {
      const enemy = w.views.get(hero).slimes.find(s => s.kind === kind && !s.dead);
      await w.debug(hero, { op: 'kill_enemy', id: enemy.id });
      await w.waitFor(() => w.views.get(hero).slimes.find(s => s.id === enemy.id)?.dead, 5000, `${kind} defeated`);
      check(w.views.get(hero).instance.cleared === (i === 2), 'Clear waits for all three guardians');
      const drops = w.views.get(hero).drops.filter(d => d.item && d.item.endsWith('_l30_span'));
      const rolls = w.events.filter(e => e.type === 'roll' && e.op === 'start' && e.bot === hero);
      check(drops.length + rolls.filter(r => r.item?.endsWith('_l30_span')).length > 0, 'Boss kills produce exclusive Bridgeward level-30 gear');
    }

    await w.waitFor(() => q(hero, 'span_toll')?.counts[0] === 1 && q(ally, 'span_toll')?.counts[0] === 1 &&
      q(hero, 'span_spectrum')?.counts[0] === 1 && q(ally, 'span_spectrum')?.counts[0] === 1, 5000, 'Party copy quest credit');
    check(!w.views.get(other).instance.cleared && w.views.get(other).slimes.filter(s => !s.dead).length === 15, 'Other party retains its live enemies and uncleared exit');

    // Exit through cleared arch
    await kit.teleport(w, hero, { zone: 42, x: 56, y: 14 });
    await w.action(hero, { type: 'move', x: 56, y: 10 });
    await w.waitFor(() => w.player(hero).zone === 7, 12000, 'Clear exit returns to Bifrost Reach');

    // Claim boss quests
    for (const [npc, id] of [['span_guide', 'span_toll'], ['span_chronicler', 'span_spectrum']]) {
      await kit.teleport(w, hero, { npc }); await kit.talkTo(w, hero, npc, `quest:claim:${id}`);
      await w.waitFor(() => q(hero, id)?.claimed, 5000, `Claim ${id}`);
    }

    const rewards = ['pants_wayfarer_l30_span', 'accessory_amber_l30_span'];
    check(rewards.every(item => w.player(hero).inventory.some(i => i.item === item)), 'Both boss quests award level-30 Bridgeward gear');

    // Restart check
    await w.restart();
    check(w.player(hero).zone === 7 && rewards.every(item => w.player(hero).inventory.some(i => i.item === item)) &&
      ['span_entry', 'span_toll', 'span_spectrum'].every(id => q(hero, id)?.claimed), 'Return, quest claims and rewards survive restart');
    check(span.name === 'The Shattered Span' && parent.portals.some(p => p.to === 42), 'The dungeon entrance is in Bifrost Reach');
  }
});
