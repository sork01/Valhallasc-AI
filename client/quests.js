'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const areas = [WORLD_MAP, ...(WORLD_MAP.zones || [])];
  const definitions = areas.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
  let heroLevel = 1, progress = [], signature = '', tracked = null, previousFocus = null, collapsed = false, completedOpen = false;
  const state = quest => progress.find(p => p.id === quest.id);
  const giver = quest => areas[quest.zone].npcs.find(n => n.id === quest.npc);
  // The hub a quest's giver belongs to: a zone may have several (the Wyrdwood's Hollowmoot and Skuldwatch).
  const hubName = quest => {
    const a = areas[quest.zone], hubs = [a.city, ...(a.camps || [])].filter(Boolean), g = giver(quest);
    if (!hubs.length) return undefined;
    if (!g || hubs.length === 1) return hubs[0].name;
    return hubs.reduce((best, c) => Math.hypot(g.x - c.plaza.x, g.y - c.plaza.y) < Math.hypot(g.x - best.plaza.x, g.y - best.plaza.y) ? c : best).name;
  };
  function status(quest) {
    const p = state(quest);
    if (p && !p.claimed) return quest.objectives.every((o, i) => (p.counts[i] || 0) >= o.count) ? 'ready' : 'active';
    if (p?.claimed && !quest.repeatable) return 'completed';
    if (quest.autoLevel) return 'upcoming'; // a progression quest is accepted by the server, never offered
    if (quest.requires && !(state({ id: quest.requires })?.completions > 0)) return 'locked';
    return 'available';
  }
  const words = { ready: 'Ready to turn in', active: 'In progress', completed: 'Completed', locked: 'Locked', upcoming: 'Comes at a later level', available: 'Available' };
  function element(tag, text, className) {
    const node = document.createElement(tag); node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function button(text, action) {
    const node = element('button', text, 'btn ghost'); node.type = 'button';
    node.addEventListener('click', action); return node;
  }
  function objectives(quest) {
    const p = state(quest);
    return quest.objectives.map((o, i) => `${o.label}: ${p?.claimed ? o.count : p?.counts[i] || 0}/${o.count}${unit(o)}`);
  }
  // A `hold` objective counts seconds of channelling in a ward.
  const unit = o => o.kind === 'hold' ? ' s' : '';
  function gearReward(quest, container) {
    const i = (window.WORLD_ITEMS || []).find(i => i.id === quest.rewardItem);
    if (!i) return;
    const reward = element('p', `${i.name} · ${{ uncommon: 'Uncommon (green)', rare: 'Rare (blue)', epic: 'Epic (purple)' }[i.rarity] || i.rarity} · Level ${i.requiredLevel || 1} · ${i.class || 'All classes'} · +${i.attack || 0} attack · +${i.defense || 0} defense`, 'quest-reward item-name');
    reward.dataset.rarity = i.rarity; reward.dataset.item = i.id;
    container.append(reward);
  }
  // Party mates (not you) who have also taken this quest, with how far each one is.
  function mates(quest) {
    return (window.Social?.questMates?.(quest.id) || []).map(m => {
      const done = quest.objectives.every((o, i) => (m.counts[i] || 0) >= o.count);
      const text = quest.objectives.map((o, i) => `${Math.min(m.counts[i] || 0, o.count)}/${o.count}${unit(o)}`).join(' · ');
      return { name: m.name, done, text };
    });
  }
  const here = quest => areas[quest.zone].name;
  function card(quest, atNpc) {
    const s = status(quest), npc = giver(quest);
    const node = element('article', '', 'quest-card'); node.dataset.quest = quest.id; node.dataset.repeatable = String(quest.repeatable);
    node.append(element('h4', quest.title), element('span', words[s] + (quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
    if (!atNpc) node.append(element('small', `${areas[quest.zone].name} · ${hubName(quest) || 'Quest giver'}`, 'quest-location quest-history'));
    const gap = quest.level - (heroLevel);
    const rec = element('p', `Recommended level ${quest.level}${quest.recommendedPlayers ? ` · Group: ${quest.recommendedPlayers} players` : ''}`, 'quest-level'); rec.dataset.level = String(quest.level);
    if (gap >= 5) rec.style.color = '#ff6b6b'; else if (gap >= 3) rec.style.color = '#ffa65a'; else if (gap <= -5) rec.style.color = '#9fb0a0';
    node.append(rec);
    node.append(element('p', quest.description), element('p', objectives(quest).join(' · '), 'quest-objectives'));
    const party = mates(quest);
    if (party.length) {
      const line = element('p', `Party on this quest: ${party.map(m => `${m.name} (${m.done ? 'ready' : m.text})`).join(', ')}`, 'quest-party');
      line.dataset.partyQuest = String(party.length); node.append(line);
    }
    node.append(element('p', `Reward: ${quest.rewardXp} XP · ${quest.rewardGold} gold`, 'quest-reward'));
    gearReward(quest, node);
    if (s === 'upcoming') {
      node.append(element('p', `This quest finds you by itself at level ${quest.autoLevel}.`, 'quest-history'));
    } else if (s === 'locked') {
      node.append(element('p', `Complete “${definitions.find(q => q.id === quest.requires)?.title}” first.`));
    } else if (atNpc && ['available', 'ready'].includes(s)) {
      const action = s === 'ready' ? 'claim' : 'accept';
      const b = button(s === 'ready' ? 'Collect reward' : state(quest)?.completions ? 'Take bounty again' : 'Accept quest', () => {
        if (Online.send({ type: 'interact', npc: quest.npc, offer: `quest:${action}:${quest.id}` })) b.disabled = true;
      });
      b.dataset.action = action; node.append(b);
    } else if (!atNpc && !['completed', 'upcoming'].includes(s)) {
      if (Field.zone !== quest.zone) node.append(element('p', quest.zone === 0
        ? `${npc.name} is back in Greenmeadow. Return through the gate first.`
        : `${npc.name} is in ${areas[quest.zone].name}. Travel through the gate to ${hubName(quest) || 'meet them'}.`, 'quest-history'));
      else node.append(button(`${s === 'ready' ? (quest.autoLevel ? 'Report to' : 'Return to') : s === 'available' ? 'Get quest from' : 'Visit'} ${npc.name}`, () => {
        close(); Field.visitNpc(quest.npc);
      }));
    }
    if (!atNpc && ['active', 'ready'].includes(s)) node.append(button(tracked === quest.id ? 'Tracking' : 'Track quest', () => {
      tracked = quest.id; render(); $('quest-close').focus();
    }));
    if (state(quest)?.completions) node.append(element('p', `Completed ${state(quest).completions} time${state(quest).completions === 1 ? '' : 's'}.`, 'quest-history'));
    return node;
  }
  function render() {
    const active = definitions.filter(q => ['ready', 'active'].includes(status(q)));
    active.sort((a, b) => Number(b.id === tracked) - Number(a.id === tracked) || Number(status(b) === 'ready') - Number(status(a) === 'ready'));
    const tracker = $('quest-tracker');
    const header = element('div', '', 'tracker-heading');
    const journal = button(`Quests (${active.length}) · Q`, show); journal.className = 'tracker-journal';
    const toggle = button(collapsed ? '+' : '−', () => { collapsed = !collapsed; render(); $('quest-tracker').querySelector('.tracker-toggle').focus(); }); toggle.className = 'tracker-toggle';
    toggle.setAttribute('aria-label', collapsed ? 'Expand quest tracker' : 'Collapse quest tracker'); toggle.setAttribute('aria-expanded', String(!collapsed));
    header.append(journal, toggle); tracker.replaceChildren(header);
    const list = element('div', '', 'tracker-list'); list.hidden = collapsed;
    for (const quest of active) {
      const row = element('div', '', 'tracker-quest'); row.dataset.quest = quest.id;
      const title = button(quest.title, () => { tracked = quest.id; show(); }); title.className = 'tracker-title';
      row.append(title);
      if (status(quest) === 'ready') row.append(element('small', `✓ ${quest.autoLevel ? 'Report to' : 'Return to'} ${giver(quest).name} for your reward`, 'tracker-objective complete'));
      else quest.objectives.forEach((o, i) => {
        const count = Math.min(state(quest)?.counts[i] || 0, o.count), done = count >= o.count;
        row.append(element('small', `${done ? '✓' : '•'} ${o.label}: ${count}/${o.count}${unit(o)}`, `tracker-objective${done ? ' complete' : ''}`));
      });
      const party = mates(quest);
      if (party.length) { const line = element('small', `Party: ${party.map(m => m.name).join(', ')}`, 'tracker-objective tracker-party'); line.dataset.partyQuest = String(party.length); row.append(line); }
      list.append(row);
    }
    if (!active.length) {
      const next = definitions.find(q => q.zone === (window.Field?.zone || 0) && status(q) === 'available') || definitions.find(q => status(q) === 'available');
      if (next) list.append(element('span', next.title, 'tracker-title'), element('small', `Speak to ${giver(next).name} in ${hubName(next) || areas[next.zone].name}`, 'tracker-objective'));
      else list.append(element('small', 'All stories complete. Visit a quartermaster for another bounty.', 'tracker-objective'));
    }
    tracker.append(list);
    if (open()) renderJournal(active);
  }
  // The journal holds your own quests only: the ones in progress or ready to hand in (those of this zone first), and a
  // folded list of the finished ones. Quests you have not taken are found at the people marked with !.
  function renderJournal(active) {
    const zone = window.Field?.zone || 0;
    const mine = [...active].sort((a, b) => Number(b.id === tracked) - Number(a.id === tracked) || Number(status(b) === 'ready') - Number(status(a) === 'ready') || Number(b.zone === zone) - Number(a.zone === zone));
    const nodes = mine.map(q => card(q, false));
    if (!mine.length) {
      nodes.push(element('p', 'You have no quests in progress. Speak to anyone with a ! over their head to take one.', 'quest-empty'));
      const next = definitions.find(q => q.zone === zone && status(q) === 'available') || definitions.find(q => status(q) === 'available');
      if (next) nodes.push(element('p', `Next: “${next.title}”. Speak to ${giver(next).name} in ${hubName(next) || areas[next.zone].name}.`, 'quest-empty quest-next'));
    }
    const done = definitions.filter(q => status(q) === 'completed');
    if (done.length) {
      const folded = document.createElement('details'); folded.className = 'quest-completed'; folded.open = completedOpen;
      folded.addEventListener('toggle', () => { completedOpen = folded.open; });
      folded.append(element('summary', `Completed (${done.length})`));
      for (const q of done) { const row = element('p', `${q.title} · ${here(q)}`, 'quest-done'); row.dataset.quest = q.id; folded.append(row); }
      nodes.push(folded);
    }
    $('quest-list').replaceChildren(...nodes);
  }
  function open() { return !$('quest-journal').hidden; }
  function show() {
    if (window.Skillbar?.open || !Online.connected || Field.hero.dead || City.open || !$('pause').hidden || !$('equipment').hidden) return;
    previousFocus = document.activeElement;
    Field.setPaused(true); $('quest-journal').hidden = false; render(); $('quest-close').focus();
  }
  function close(resume = true) {
    if (!open()) return;
    $('quest-journal').hidden = true;
    if (resume) { Field.setPaused(false); previousFocus?.focus?.({ preventScroll: true }); }
  }
  $('quest-tracker').addEventListener('click', event => { if (!event.target.closest('button')) show(); });
  $('quest-close').addEventListener('click', () => close());
  $('quest-journal').addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const buttons = [...$('quest-journal').querySelectorAll('button:not(:disabled)')];
    const first = buttons[0], last = buttons.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  window.Quests = {
    show, close, get open() { return open(); },
    setLevel(level) { heroLevel = level; },
    refresh() { render(); },
    // Titles of the quests you and this party member both have in progress.
    sharedWith(member) {
      return (member.quests || []).map(q => definitions.find(d => d.id === q.id)).filter(q => q && ['ready', 'active'].includes(status(q))).map(q => q.title);
    },
    // Whether any of your quests has a `visit` objective for this place that is done (a beacon you have lit).
    visited(placeId) { return definitions.some(q => q.objectives.some((o, i) => o.kind === 'visit' && o.target === placeId && (state(q)?.claimed || (state(q)?.counts[i] || 0) >= o.count))); },
    // Your progress at a ward (a place a `hold` objective names): 'active' while a quest of yours still needs it, 'done' once it holds, else 'none'.
    hold(placeId) {
      let out = { state: 'none', have: 0, need: 0 };
      for (const q of definitions) q.objectives.forEach((o, i) => {
        if (o.kind !== 'hold' || o.target !== placeId) return;
        const p = state(q); if (!p) return;
        const have = p.claimed ? o.count : Math.min(p.counts[i] || 0, o.count);
        if (have < o.count) out = { state: 'active', have, need: o.count };
        else if (out.state !== 'active') out = { state: 'done', have, need: o.count };
      });
      return out;
    },
    reset() { progress = []; signature = ''; tracked = null; close(false); render(); },
    update(next) { const key = `${Field.zone}:` + JSON.stringify(next); if (key === signature) return; progress = next; signature = key; render(); },
    // What an NPC's conversation lists, in World of Warcraft order: turn-ins, new quests, then quests still in progress.
    // Locked and finished quests are hidden, as they are there.
    offered(id) {
      const rank = { ready: 0, available: 1, active: 2 };
      return definitions.filter(q => q.npc === id && status(q) in rank)
        .sort((a, b) => rank[status(a)] - rank[status(b)] || Number(a.repeatable) - Number(b.repeatable));
    },
    npc(id, container, pick) {
      container.replaceChildren(...this.offered(id).map(q => {
        const s = status(q), gap = q.level - heroLevel;
        const row = element('button', '', 'gossip-row'); row.type = 'button'; row.dataset.quest = q.id; row.dataset.status = s;
        if (q.repeatable) row.dataset.repeatable = 'true';
        const tag = element('span', `Lv ${q.level}`, 'gossip-tag'); tag.dataset.level = String(q.level);
        if (gap >= 5) tag.style.color = '#a31515'; else if (gap >= 3) tag.style.color = '#b8560f'; else if (gap <= -5) tag.style.color = '#6f6a58';
        const icon = element('span', s === 'available' ? '!' : '?', 'gossip-icon'); icon.setAttribute('aria-hidden', 'true');
        row.append(icon, element('span', q.title, 'gossip-label'), tag);
        row.setAttribute('aria-label', `${q.title}, ${words[s]}`);
        row.addEventListener('click', () => pick(q));
        return row;
      }));
    },
    // The quest page of a conversation: story, objectives, reward, then the accept / complete button.
    detail(quest, container, back) {
      const s = status(quest);
      const node = element('article', '', 'quest-card quest-detail'); node.dataset.quest = quest.id; node.dataset.status = s;
      node.append(element('h4', quest.title), element('span', words[s] + (quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
      node.append(element('p', quest.description));
      if (quest.recommendedPlayers) node.append(element('p', `Recommended level ${quest.level} · Group: ${quest.recommendedPlayers} players`, 'quest-level'));
      node.append(element('h5', 'Objectives'), element('p', objectives(quest).join('\n'), 'quest-objectives'));
      node.append(element('h5', 'Rewards'), element('p', `${quest.rewardXp} experience · ${quest.rewardGold} gold`, 'quest-reward'));
      gearReward(quest, node);
      const actions = element('div', '', 'quest-actions');
      if (['available', 'ready'].includes(s)) {
        const action = s === 'ready' ? 'claim' : 'accept';
        const b = element('button', s === 'ready' ? 'Complete Quest' : state(quest)?.completions ? 'Take bounty again' : 'Accept', 'gossip-button primary'); b.type = 'button';
        b.dataset.action = action;
        b.addEventListener('click', () => { if (Online.send({ type: 'interact', npc: quest.npc, offer: `quest:${action}:${quest.id}` })) b.disabled = true; });
        actions.append(b);
      }
      const decline = element('button', s === 'available' ? 'Decline' : 'Back', 'gossip-button'); decline.type = 'button'; decline.dataset.action = 'decline';
      decline.addEventListener('click', back); actions.append(decline);
      node.append(actions);
      container.replaceChildren(node);
    },
    marker(id) { return this.markerInfo(id).symbol; },
    markerInfo(id) {
      for (const s of ['ready', 'available']) {
        const quest = definitions.find(q => q.npc === id && status(q) === s && !q.repeatable)
          || definitions.find(q => q.npc === id && status(q) === s);
        if (quest) return { symbol: s === 'ready' ? '?' : '!', color: quest.repeatable ? '#64b5ff' : '#ffdf88', repeatable: quest.repeatable };
      }
      if (definitions.some(q => status(q) === 'active' && q.objectives.some((o, i) => (o.kind === 'talk' || o.kind === 'escort') && o.target === id && !(state(q)?.counts[i] >= o.count)))) return { symbol: '◆', color: '#ffdf88' };
      return { symbol: '', color: '#ffdf88' };
    },
  };
  render();
})();
