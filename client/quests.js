'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const areas = [WORLD_MAP, ...(WORLD_MAP.zones || [])];
  const definitions = areas.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
  let heroLevel = 1, progress = [], bells = [], signature = '', tracked = null, previousFocus = null, collapsed = false, completedOpen = false;
  let abandoned = [];
  const expanded = new Set();
  let abandonConfirm = null, abandonedOpen = false;
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
    if (quest.autoLevel && !abandoned.includes(quest.id)) return 'upcoming'; // a progression quest is accepted by the server, never offered
    if (quest.requires && !(state({ id: quest.requires })?.completions > 0)) return 'locked';
    if (quest.minLevel && heroLevel < quest.minLevel) return 'locked';
    return 'available';
  }
  const words = { ready: 'Ready to turn in', active: 'In progress', completed: 'Completed', locked: 'Locked', upcoming: 'Comes at a later level', available: 'Available' };
  // Both maps share the journal's eligibility rules. Cache presentation by zone, never in the ground/fog canvas.
  const mapCache = new Map();
  const questsByNpc = new Map();
  for (const q of definitions) {
    if (!questsByNpc.has(q.npc)) questsByNpc.set(q.npc, []);
    questsByNpc.get(q.npc).push(q);
  }
  const matchesEnemy = (target, kind) => target === kind || target === 'any'
    || (target === 'slime' && ['green', 'blue', 'pink', 'yellow'].includes(kind));
  function mapMarkers(zone) {
    if (mapCache.has(zone)) return mapCache.get(zone);
    const area = areas[zone], out = [];
    if (!area) return out;
    for (const n of area.npcs || []) {
      const states = (questsByNpc.get(n.id) || []).map(status);
      const s = states.includes('ready') ? 'ready' : states.includes('available') ? 'available' : null;
      if (s) out.push({ x: n.x, y: n.y, npc: n.id, state: s, symbol: s === 'ready' ? '?' : '!',
        color: s === 'ready' ? '#64b5ff' : '#ffdf88', label: `${n.name} · ${words[s]}` });
    }
    const q = definitions.find(q => q.id === tracked), s = q && status(q);
    if (s === 'active' || s === 'ready') {
      const add = (p, label) => {
        if (!p || out.some(m => m.state === 'tracked' && m.x === p.x && m.y === p.y)) return;
        out.push({ x: p.x, y: p.y, quest: q.id, state: 'tracked', symbol: '◆', color: '#a6ffcf',
          label: `Tracked quest · ${q.title} · ${label}` });
      };
      if (s === 'ready') add((area.npcs || []).find(n => n.id === q.npc), words.ready);
      else q.objectives.forEach((o, i) => {
        if ((state(q)?.counts[i] || 0) >= o.count) return;
        if (o.kind === 'kill') {
          // A hub can send you into a neighbouring dungeon. Ordinary "any"/"slime" hunts stay in their own zone.
          const home = areas[q.zone], local = (home.slimes || []).some(e => matchesEnemy(o.target, e.kind));
          if (zone !== q.zone && (local || !home.portals?.some(p => p.to === zone))) return;
          const spawns = (area.slimes || []).filter(e => matchesEnemy(o.target, e.kind) && !e.ambush);
          if (!spawns.length) return;
          // Anchor a hunt to a real spawn near its centre, rather than to empty space between packs.
          const x = spawns.reduce((n, e) => n + e.x, 0) / spawns.length, y = spawns.reduce((n, e) => n + e.y, 0) / spawns.length;
          add(spawns.reduce((best, e) => Math.hypot(e.x - x, e.y - y) < Math.hypot(best.x - x, best.y - y) ? e : best), o.label);
        } else if (['visit', 'hold', 'chime', 'memory', 'echo'].includes(o.kind)) {
          for (const p of area.places || []) if (o.kind === 'chime' ? p.chain === o.target : p.id === o.target) add(p, o.label);
        } else if (o.kind === 'talk' || o.kind === 'escort' || o.kind === 'handoff') add((area.npcs || []).find(n => n.id === o.target), o.label);
        else if (o.kind === 'reach') {
          const name = window.Locale?.translate(o.target) || o.target;
          if (area.name === name) add(area.spawn, o.label);
          for (const p of area.portals || []) if (areas[p.to]?.name === name) add(p, o.label);
        } else if (o.kind === 'bring' || o.kind === 'gauntlet') add((area.npcs || []).find(n => n.id === q.npc), o.label);
      });
    }
    mapCache.set(zone, out);
    return out;
  }
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
  // A `hold` objective counts seconds of channelling in a ward; a `chime` objective counts the bells of its chain that ring right now.
  const unit = o => o.kind === 'hold' ? ' s' : o.kind === 'chime' ? ' ringing' : '';
  function storyRecap(quest, node) {
    if (!quest.story) return;
    const p = state(quest); if (!p) return;
    const ready = p.claimed || quest.objectives.every((o, i) => (p.counts[i] || 0) >= o.count);
    const memories = (window.EMPTY_SEAT_SCENES || []).filter(s => s.quest === quest.id && !s.enemy);
    const texts = ready ? quest.story.recap : memories.filter(s => {
      const i = quest.objectives.findIndex(o => o.target === s.id);
      return i >= 0 && (p.counts[i] || 0) >= quest.objectives[i].count;
    }).map(s => s.description);
    if (!texts?.length) return;
    const folded = document.createElement('details'); folded.className = 'quest-memories';
    folded.append(element('summary', 'Recovered memories'));
    for (const text of texts) folded.append(element('p', text));
    node.append(folded);
  }
  function rewardIcon(id, claim) {
    const item = Inventory.definition(id); if (!item) return null;
    const b = element('button', '', 'item-tile quest-reward-icon'); b.type = 'button';
    b.dataset.item = id; b.dataset.rarity = item.rarity; b.setAttribute('aria-label', item.name);
    b.innerHTML = Inventory.icon(item);
    const where = () => ({ copies: [], count: 1, in: Locale.translate('Quest reward'), hint: Locale.translate(claim ? 'Tap again to claim this reward.' : 'Quest reward') });
    Inventory.attachTooltip(b, () => item, undefined, where);
    let touch = false, previewed = false;
    b.addEventListener('pointerdown', e => { touch = e.pointerType === 'touch'; });
    b.addEventListener('click', () => {
      if (touch && (!claim || !previewed)) { previewed = true; requestAnimationFrame(() => Inventory.showTooltip(b, item, undefined, where())); return; }
      if (claim) claim(b);
    });
    b.addEventListener('blur', () => { previewed = false; });
    if (claim) b.dataset.action = 'claim';
    return b;
  }
  function rewards(quest, container, claimable) {
    const icons = element('div', '', 'quest-reward-icons');
    if (quest.rewardItem) { const n = rewardIcon(quest.rewardItem); if (n) icons.append(n); }
    const choices = classChoices(quest);
    if (choices.length) container.append(element('p', 'Choose one class reward:', 'quest-reward'));
    for (const id of choices) {
      const n = rewardIcon(id, claimable ? b => {
        if (Online.send({ type: 'interact', npc: quest.npc, offer: `quest:claim:${quest.id}:${id}` })) b.disabled = true;
      } : null);
      if (n) icons.append(n);
    }
    if (icons.childElementCount) container.append(icons);
    return choices;
  }
  function questAction(quest, action, b) {
    if (action === 'accept') return City.acceptQuest(quest, b);
    if (Online.send({ type: 'interact', npc: quest.npc, offer: `quest:${action}:${quest.id}` })) b.disabled = true;
  }
  function classChoices(quest) {
    return (quest.rewardChoices || {})[Field.hero?.look?.class] || [];
  }
  // Party mates (not you) who have also taken this quest, with how far each one is.
  function mates(quest) {
    return (window.Social?.questMates?.(quest.id) || []).map(m => {
      const done = quest.objectives.every((o, i) => (m.counts[i] || 0) >= o.count);
      const text = quest.objectives.map((o, i) => `${Math.min(m.counts[i] || 0, o.count)}/${o.count}${unit(o)}`).join(' · ');
      return { name: m.name, done, text };
    });
  }
  function card(quest, atNpc) {
    const s = status(quest), npc = giver(quest);
    const node = element('article', '', 'quest-card'); node.dataset.quest = quest.id; node.dataset.repeatable = String(quest.repeatable);
    node.append(element('h4', quest.title), element('span', words[s] + (quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
    if (quest.story) node.prepend(element('small', quest.story.title + ' · ' + quest.story.chapter + '/28', 'quest-location'));
    if (!atNpc) node.append(element('small', `${areas[quest.zone].name} · ${hubName(quest) || 'Quest giver'}`, 'quest-location quest-history'));
    const gap = quest.level - (heroLevel);
    const rec = element('p', `Recommended level ${quest.level}${quest.recommendedPlayers ? ` · Group: ${quest.recommendedPlayers} players` : ''}`, 'quest-level'); rec.dataset.level = String(quest.level);
    if (gap >= 5) rec.style.color = '#ff6b6b'; else if (gap >= 3) rec.style.color = '#ffa65a'; else if (gap <= -5) rec.style.color = '#9fb0a0';
    node.append(rec);
    node.append(element('p', quest.description), element('p', objectives(quest).join(' · '), 'quest-objectives'));
    storyRecap(quest, node);
    if (quest.story?.next) node.append(element('p', quest.story.next, 'quest-next'));
    const party = mates(quest);
    if (party.length) {
      const line = element('p', `Party on this quest: ${party.map(m => `${m.name} (${m.done ? 'ready' : m.text})`).join(', ')}`, 'quest-party');
      line.dataset.partyQuest = String(party.length); node.append(line);
    }
    if (!quest.handoffTo) node.append(element('p', `Reward: ${quest.rewardXp} XP · ${quest.rewardGold} gold`, 'quest-reward'));
    const choices = rewards(quest, node, s === 'ready' && atNpc);
    if (s === 'upcoming') {
      node.append(element('p', `This quest finds you by itself at level ${quest.autoLevel}.`, 'quest-history'));
    } else if (s === 'locked') {
      const early = quest.requires && !(state({ id: quest.requires })?.completions > 0);
      node.append(element('p', early ? `Complete “${definitions.find(q => q.id === quest.requires)?.title}” first.` : `This quest is for heroes of level ${quest.minLevel} and above.`));
    } else if (atNpc && ['available', 'ready'].includes(s) && !(s === 'ready' && choices.length)) {
      const action = s === 'ready' ? 'claim' : 'accept';
      const b = button(s === 'ready' ? 'Collect reward' : state(quest)?.completions ? 'Take bounty again' : 'Accept quest', () => {
        questAction(quest, action, b);
      });
      b.dataset.action = action; node.append(b);
    } else if (!atNpc && quest.autoLevel && abandoned.includes(quest.id) && s === 'available') {
      const b = button('Restore quest', () => {
        if (Online.send({ type: 'quest_restore', id: quest.id })) b.disabled = true;
      });
      b.dataset.action = 'restore'; node.append(b);
    } else if (!atNpc && !['completed', 'upcoming'].includes(s)) {
      if (Field.zone !== quest.zone) node.append(element('p', quest.zone === 0
        ? `${npc.name} is back in Greenmeadow. Return through the gate first.`
        : `${npc.name} is in ${areas[quest.zone].name}. Travel through the gate to ${hubName(quest) || 'meet them'}.`, 'quest-history'));
      else node.append(button(`${s === 'ready' ? (quest.autoLevel ? 'Report to' : 'Return to') : s === 'available' ? 'Get quest from' : 'Visit'} ${npc.name}`, () => {
        close(); Field.visitNpc(quest.npc);
      }));
    }
    if (!atNpc && ['active', 'ready'].includes(s)) node.append(button(tracked === quest.id ? 'Tracking' : 'Track quest', () => {
      tracked = quest.id; mapCache.clear(); render(); $('quest-close').focus();
    }));
    if (!atNpc && ['active', 'ready'].includes(s)) {
      const asking = abandonConfirm === quest.id;
      if (asking) node.append(element('p', 'Abandon this quest? Current progress will be lost. You can take it again from its questgiver.', 'quest-abandon-warning'));
      const b = button(asking ? 'Confirm abandon' : 'Abandon quest', () => {
        expanded.add(quest.id);
        if (!asking) { abandonConfirm = quest.id; render(); $('quest-list').querySelector(`[data-quest="${quest.id}"] [data-action="abandon"]`).focus(); }
        else if (Online.send({ type: 'quest_abandon', id: quest.id })) { b.disabled = true; }
      });
      b.dataset.action = 'abandon'; node.append(b);
      if (asking) node.append(button('Cancel', () => { abandonConfirm = null; render(); }));
    }
    if (state(quest)?.completions) node.append(element('p', `Completed ${state(quest).completions} time${state(quest).completions === 1 ? '' : 's'}.`, 'quest-history'));
    return node;
  }
  function render() {
    const active = definitions.filter(q => ['ready', 'active'].includes(status(q)));
    active.sort((a, b) => Number(b.id === tracked) - Number(a.id === tracked) || Number(status(b) === 'ready') - Number(status(a) === 'ready'));
    const tracker = $('quest-tracker');
    const header = element('div', '', 'tracker-heading');
    const journal = button(`Quests (${active.length}) · ${window.Keys ? Keys.label('quests', false) : 'Q'}`, show); journal.className = 'tracker-journal';
    const toggle = button(collapsed ? '+' : '−', () => { collapsed = !collapsed; render(); $('quest-tracker').querySelector('.tracker-toggle').focus(); }); toggle.className = 'tracker-toggle';
    toggle.setAttribute('aria-label', collapsed ? 'Expand quest tracker' : 'Collapse quest tracker'); toggle.setAttribute('aria-expanded', String(!collapsed));
    header.append(journal, toggle); tracker.replaceChildren(header);
    const list = element('div', '', 'tracker-list'); list.hidden = collapsed;
    for (const quest of active) {
      const row = element('div', '', 'tracker-quest'); row.dataset.quest = quest.id;
      const title = button(quest.title, () => { tracked = quest.id; mapCache.clear(); show(); }); title.className = 'tracker-title';
      row.append(title);
      if (status(quest) === 'ready') row.append(element('small', `✓ ${quest.autoLevel ? 'Report to' : 'Return to'} ${giver(quest).name} for your reward`, 'tracker-objective complete'));
      else if(quest.id==='raid_key') { const n=quest.objectives.filter((o,i)=>(state(quest)?.counts[i]||0)>=o.count).length; row.append(element('small', `Pieces: ${n}/10`, 'tracker-objective')); }
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
    const nodes = mine.map(q => foldedCard(q));
    if (!mine.length) {
      nodes.push(element('p', 'You have no quests in progress. Speak to anyone with a ! over their head to take one.', 'quest-empty'));
      const next = definitions.find(q => q.zone === zone && status(q) === 'available') || definitions.find(q => status(q) === 'available');
      if (next) nodes.push(element('p', `Next: “${next.title}”. Speak to ${giver(next).name} in ${hubName(next) || areas[next.zone].name}.`, 'quest-empty quest-next'));
    }
    const recoverable = definitions.filter(q => q.autoLevel && heroLevel >= q.autoLevel && abandoned.includes(q.id)
      && status(q) === 'available' && (!q.handoffTo || !state({id: q.handoffTo})));
    if (recoverable.length) {
      const folded = document.createElement('details'); folded.className = 'quest-abandoned'; folded.open = abandonedOpen;
      folded.addEventListener('toggle', () => { if (folded.isConnected) abandonedOpen = folded.open; });
      folded.append(element('summary', `Abandoned automatic quests (${recoverable.length})`));
      for (const q of recoverable) folded.append(foldedCard(q));
      nodes.unshift(folded);
    }
    const done = definitions.filter(q => !q.handoffTo && status(q) === 'completed');
    if (done.length) {
      const folded = document.createElement('details'); folded.className = 'quest-completed'; folded.open = completedOpen;
      folded.addEventListener('toggle', () => { if (folded.isConnected) completedOpen = folded.open; });
      folded.append(element('summary', `Completed (${done.length})`));
      for (const q of done) folded.append(foldedCard(q));
      nodes.push(folded);
    }
    $('quest-list').replaceChildren(...nodes);
  }
  function foldedCard(quest) {
    const node = document.createElement('details'); node.className = 'quest-entry'; node.dataset.quest = quest.id;
    node.open = expanded.has(quest.id);
    const summary = element('summary', `! ${quest.title}`);
    node.append(summary);
    // Completed histories can be long: render rewards/details only for entries being read.
    const fill = () => {
      if (node.querySelector(':scope > article')) return;
      const body = card(quest, false); delete body.dataset.quest;
      body.querySelector('h4')?.remove(); node.append(body);
    };
    if (node.open) fill();
    node.addEventListener('toggle', () => {
      if (!node.isConnected) return;
      if (node.open) { expanded.add(quest.id); fill(); }
      else { expanded.delete(quest.id); node.querySelector(':scope > article')?.remove(); }
    });
    return node;
  }
  function open() { return !$('quest-journal').hidden; }
  function show() {
    if (window.Skillbar?.open || !Online.connected || Field.hero.dead || City.open || !$('pause').hidden || !$('equipment').hidden) return;
    previousFocus = document.activeElement; expanded.clear(); completedOpen = false; abandonedOpen = false; abandonConfirm = null;
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
    const buttons = [...$('quest-journal').querySelectorAll('button:not(:disabled), summary')].filter(b => b.getClientRects().length);
    const first = buttons[0], last = buttons.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  window.Quests = {
    show, close, get open() { return open(); },
    setLevel(level) { if (heroLevel !== level) { heroLevel = level; mapCache.clear(); render(); } },
    mapMarkers,
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
    // The bells you have ringing, from your own snapshot: [{ place, left }] (seconds left on each).
    setBells(list) { bells = Array.isArray(list) ? list : []; },
    // Your state at a tidebell (a place of a chain a `chime` objective names): 'waiting' while a quest of yours still needs it, 'ringing' while
    // it sounds (with the seconds `left` of its `burn`, and how many of the chain ring: `have` of `need`), 'done' once the chain has rung, else 'none'.
    chime(placeId) {
      const place = window.Field?.place?.(placeId);
      if (!place || !place.chain) return { state: 'none' };
      let out = null, done = false;
      for (const q of definitions) q.objectives.forEach((o, i) => {
        if (o.kind !== 'chime' || o.target !== place.chain) return;
        const p = state(q); if (!p) return;
        const have = p.claimed ? o.count : Math.min(p.counts[i] || 0, o.count);
        if (have < o.count) out = { have, need: o.count }; else done = true;
      });
      const ringing = bells.find(b => b.place === placeId);
      if (out) return { state: ringing ? 'ringing' : 'waiting', left: ringing ? ringing.left : 0, burn: place.burn, ...out };
      return done ? { state: 'done', burn: place.burn } : { state: 'none' };
    },
    reset() { progress = []; abandoned = []; expanded.clear(); abandonConfirm = null; abandonedOpen = false; signature = ''; tracked = null; bells = []; mapCache.clear(); close(false); render(); },
    update(next, dismissed = abandoned) { const key = `${Field.zone}:` + JSON.stringify([next, dismissed]); if (key === signature) return; progress = next; abandoned = dismissed || []; signature = key; if (tracked && !progress.some(p => p.id === tracked && !p.claimed)) tracked = null; if (abandonConfirm && !progress.some(p => p.id === abandonConfirm && !p.claimed)) abandonConfirm = null; mapCache.clear(); render(); },
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
      if (quest.story) node.prepend(element('small', quest.story.title + ' · ' + quest.story.chapter + '/28', 'quest-location'));
      node.append(element('p', quest.description));
      storyRecap(quest, node);
      if (quest.story?.next) node.append(element('p', quest.story.next, 'quest-next'));
      if (quest.recommendedPlayers) node.append(element('p', `Recommended level ${quest.level} · Group: ${quest.recommendedPlayers} players`, 'quest-level'));
      node.append(element('h5', 'Objectives'), element('p', objectives(quest).join('\n'), 'quest-objectives'));
      if (!quest.handoffTo) node.append(element('h5', 'Rewards'), element('p', `${quest.rewardXp} experience · ${quest.rewardGold} gold`, 'quest-reward'));
      const choices = rewards(quest, node, s === 'ready');
      const actions = element('div', '', 'quest-actions');
      if (['available', 'ready'].includes(s) && !(s === 'ready' && choices.length)) {
        const action = s === 'ready' ? 'claim' : 'accept';
        const b = element('button', s === 'ready' ? 'Complete Quest' : state(quest)?.completions ? 'Take bounty again' : 'Accept', 'gossip-button primary'); b.type = 'button';
        b.dataset.action = action;
        b.addEventListener('click', () => { questAction(quest, action, b); });
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
      if (definitions.some(q => status(q) === 'active' && q.objectives.some((o, i) => (o.kind === 'talk' || o.kind === 'escort' || o.kind === 'handoff') && o.target === id && !(state(q)?.counts[i] >= o.count)))) return { symbol: '◆', color: '#ffdf88' };
      return { symbol: '', color: '#ffdf88' };
    },
  };
  render();
})();
