'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const areas = [WORLD_MAP, ...(WORLD_MAP.zones || [])];
  const definitions = areas.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
  let heroLevel = 1, progress = [], bells = [], signature = '', tracked = null, previousFocus = null, collapsed = false;
  let abandoned = [], initialized = false;
  const guidance = QuestGuidance.create(areas, window.QUEST_SOURCES || {});
  let groupKey = '', groupList = [];
  const closedGroups = new Set();
  let abandonConfirm = null, journalSelection = null;
  const phoneQuest = window.matchMedia?.('(pointer: coarse) and (max-width: 900px), (pointer: coarse) and (max-height: 500px)');
  const paneScroll = { list: 0, detail: 0 };
  function questPane(pane, focus = false) {
    const shell = $('quest-journal').querySelector('.quest-panel');
    const panes = { list: $('quest-list'), detail: $('quest-page') };
    for (const [key, node] of Object.entries(panes)) if (node.getClientRects().length) paneScroll[key] = node.scrollTop;
    shell.dataset.questPane = pane;
    for (const b of shell.querySelectorAll('[data-quest-pane]')) b.setAttribute('aria-pressed', String(b.dataset.questPane === pane));
    panes[pane].scrollTop = paneScroll[pane];
    window.Inventory?.hideTooltip();
    if (focus && phoneQuest?.matches) panes[pane].focus({ preventScroll: true });
  }
  const state = quest => progress.find(p => p.id === quest.id);
  const allGivers=q=>q.givers?areas.flatMap((a,zone)=>a.npcs.filter(n=>q.givers.includes(n.id)).map(n=>({...n,zone}))):[{...areas[q.zone].npcs.find(n=>n.id===q.npc),zone:q.zone}];
  const giver = quest => allGivers(quest).find(n=>n.zone===(window.Field?.zone||0))||allGivers(quest)[0];
  // The hub a quest's giver belongs to: a zone may have several (the Wyrdwood's Hollowmoot and Skuldwatch).
  const hubName = quest => {
    const a = areas[giver(quest)?.zone??quest.zone], hubs = [a.city, ...(a.camps || [])].filter(Boolean), g = giver(quest);
    if (!hubs.length) return undefined;
    if (!g || hubs.length === 1) return hubs[0].name;
    return hubs.reduce((best, c) => Math.hypot(g.x - c.plaza.x, g.y - c.plaza.y) < Math.hypot(g.x - best.plaza.x, g.y - best.plaza.y) ? c : best).name;
  };
  const arenaLevel = q => q.objectives.find(o => o.kind === 'gauntlet')?.target;
  const arenaGivers = areas.flatMap((area, zone) => (area.npcs || [])
    .filter(n => n.offers?.some(o => o.id === 'gauntlet')).map(n => ({ ...n, zone })));
  const arenaQuests = definitions.filter(arenaLevel), arenaGiverIds = new Set(arenaGivers.map(n => n.id));
  const handInAt = (q, id) => q.npc === id || q.givers?.includes(id) || (arenaLevel(q) && arenaGivers.some(n => n.id === id));
  const turnIns = q => arenaLevel(q) ? arenaGivers : allGivers(q);
  const handIn = q => {
    const local = turnIns(q).filter(n => n.zone === (window.Field?.zone || 0));
    const hero = window.Field?.hero;
    if (local.length) return local.reduce((a, b) => hero && Math.hypot(b.x-hero.x,b.y-hero.y) < Math.hypot(a.x-hero.x,a.y-hero.y) ? b : a);
    const target = tracked === q.id && hero && navigationTarget(window.Field?.zone || 0, hero.x, hero.y);
    return turnIns(q).find(n => n.zone === target?.destinationZone) || turnIns(q)[0];
  };
  function status(quest) {
    const p = state(quest), festival=window.Seasonal?.questState(quest);
    if (festival==='inactive') return p?.claimed?'completed':'unavailable';
    if (festival==='completed') return 'completed';
    if (p && !p.claimed) return quest.objectives.every((o, i) => (p.counts[i] || 0) >= o.count) ? 'ready' : 'active';
    if (p?.claimed && !quest.repeatable) return 'completed';
    if (arenaLevel(quest) && arenaQuests.some(q => q.id !== quest.id && arenaLevel(q) === arenaLevel(quest) && state(q))) return 'unavailable';
    if (quest.landing && !p && !abandoned.includes(quest.id)) return 'unavailable'; // Greenmeadow's landing quest finds only heroes who step off the dock
    if (quest.autoLevel && !abandoned.includes(quest.id)) return 'upcoming'; // a progression quest is accepted by the server, never offered
    if (quest.requires && !(state({ id: quest.requires })?.completions > 0)) return 'locked';
    if (quest.minLevel && heroLevel < quest.minLevel) return 'locked';
    return 'available';
  }
  const words = { ready: 'Ready to turn in', active: 'In progress', completed: 'Completed', locked: 'Locked', upcoming: 'Comes at a later level', available: 'Available' };
  // Both maps share the journal's eligibility rules. Cache presentation by zone, never in the ground/fog canvas.
  const mapCache = new Map(), navigationCache = new Map();
  const byId = new Map(definitions.map(q => [q.id, q]));
  const clearGuidance = () => { mapCache.clear(); navigationCache.clear(); };
  function track(id) {
    const quest = byId.get(id);
    if (id != null && (!quest || !['active', 'ready'].includes(status(quest)))) return false;
    tracked = id; clearGuidance(); render(); return true;
  }
  const questsByNpc = new Map();
  for (const q of definitions) {
    for(const id of q.givers||[q.npc]){if(!questsByNpc.has(id))questsByNpc.set(id,[]);questsByNpc.get(id).push(q);}
  }
  const guidanceContext = () => ({
    escorts: (window.Field?.remotePlayers || []).filter(p => p.escort?.owner === Online.id).map(p => p.escort),
    npc: (zone, id) => window.City?.npcsOf?.(zone)?.find(n => n.id === id),
  });
  function objectiveGroups(q) {
    const context = guidanceContext(), counts = state(q)?.counts || [];
    const key = JSON.stringify([q.id, counts, context.escorts.map(e => e.npc)]);
    if (key !== groupKey) {
      groupKey = key; groupList = guidance.groups(q, counts, context); navigationCache.clear();
    }
    return groupList;
  }
  function reference(zone) {
    const current = window.Field?.zone || 0, hero = window.Field?.hero;
    if (hero && current === zone) return hero;
    const from = areas[current]?.shape?.T, to = areas[zone]?.shape?.T;
    if (hero && from && to) return { x: hero.x + from[0] - to[0], y: hero.y + from[1] - to[1] };
    return areas[zone]?.spawn || { x: 0, y: 0 };
  }
  function mapMarkers(zone) {
    const area = areas[zone]; if (!area) return [];
    if (!mapCache.has(zone)) {
      const out = [];
      for (const n of area.npcs || []) {
        let offered = (questsByNpc.get(n.id) || []).map(q => ({ q, s: status(q) }));
        if (arenaGiverIds.has(n.id)) offered = offered.concat(arenaQuests.filter(q => status(q) === 'ready').map(q => ({ q, s: 'ready' })));
        const s = offered.some(p => p.s === 'ready') ? 'ready' : offered.some(p => p.s === 'available') ? 'available' : null;
        if (!s) continue;
        const repeatable = offered.filter(p => p.s === s).every(p => p.q.repeatable);
        out.push({ x: n.x, y: n.y, npc: n.id, state: s, symbol: s === 'ready' ? '?' : '!', repeatable,
          color: repeatable ? '#64b5ff' : '#ffdf88', label: `${n.name} · ${words[s]}` });
      }
      mapCache.set(zone, out);
    }
    const context = guidanceContext(), ref = reference(zone);
    const out = mapCache.get(zone).map(m => ({ ...m, ...(context.npc(zone, m.npc) ? { x: context.npc(zone, m.npc).x, y: context.npc(zone, m.npc).y } : {}) }));
    const q = byId.get(tracked), s = q && status(q);
    const add = (p, label) => {
      if (!p || out.some(m => m.state === 'tracked' && m.x === p.x && m.y === p.y)) return;
      out.push({ x: p.x, y: p.y, quest: q.id, state: 'tracked', symbol: '◆', color: '#a6ffcf', label: `Tracked quest · ${q.title} · ${label}` });
    };
    if (s === 'ready') for (const n of turnIns(q)) { if (n.zone === zone) add(context.npc(zone, n.id) || n, words.ready); }
    else if (s === 'active') for (const group of objectiveGroups(q)) {
      add(guidance.nearest(group.candidates, zone, ref.x, ref.y, context), group.label);
    }
    return out;
  }
  // Cache zone routes, while selecting the nearest real destination from the hero's current position.
  function navigationTarget(zone, x, y) {
    const q = byId.get(tracked), s = q && status(q);
    if (!q || !areas[zone] || !['active', 'ready'].includes(s)) return null;
    const candidates = s === 'ready' ? turnIns(q).map(n => ({ ...n, npc: n.id })) : objectiveGroups(q).flatMap(g => g.candidates);
    const local = guidance.nearest(candidates, zone, x, y, guidanceContext());
    if (local) return { ...local, quest: q.id };
    const cacheKey = `${zone}:${!!(window.Field?.instanceCleared)}`;
    if (!navigationCache.has(cacheKey)) {
      const goals = new Set(candidates.map(p => p.zone)), targets = [];
      const usable = (from, p) => areas[p.to] && !areas[p.to].sealedTemplate && (!p.after_clear || (from === zone && window.Field?.instanceCleared));
      let best = Infinity;
      for (const exit of areas[zone].portals || []) {
        if (!usable(zone, exit)) continue;
        const queue = [[exit.to, 1]], seen = new Set([zone]);
        for (let i = 0; i < queue.length; i++) {
          const [here, depth] = queue[i];
          if (seen.has(here) || depth > best) continue;
          seen.add(here);
          if (goals.has(here)) {
            if (depth < best) { best = depth; targets.length = 0; }
            targets.push({ x: exit.x, y: exit.y, quest: tracked, viaPortal: true, destinationZone: here }); break;
          }
          for (const p of areas[here].portals || []) if (usable(here, p) && !seen.has(p.to)) queue.push([p.to, depth + 1]);
        }
      }
      navigationCache.set(cacheKey, targets);
    }
    return navigationCache.get(cacheKey).reduce((best, p) => !best || Math.hypot(p.x-x, p.y-y) < Math.hypot(best.x-x, best.y-y) ? p : best, null);
  }
  function element(tag, text, className) {
    const node = document.createElement(tag); node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  // The Empty Seat campaign (chapters and their "seek" handoffs) is the main questline.
  const isMainQuest = quest => /^es_(go_)?\d+$/.test(quest.id);
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
  // `named` (a conversation's quest page) sets each reward icon on a plate with the item's name beside it.
  function rewards(quest, container, claimable, npcId = quest.npc, named = false) {
    const icons = element('div', '', 'quest-reward-icons' + (named ? ' quest-reward-named' : ''));
    const put = n => { if (!n) return; if (!named) { icons.append(n); return; } const cell = element('div', '', 'quest-reward-cell'); cell.dataset.rarity = n.dataset.rarity; cell.append(n, element('span', Inventory.definition(n.dataset.item).name, 'quest-reward-name')); icons.append(cell); };
    if (quest.rewardItem) put(rewardIcon(quest.rewardItem));
    const choices = classChoices(quest);
    if (choices.length) container.append(element('p', 'Choose one class reward:', 'quest-reward'));
    for (const id of choices) {
      const n = rewardIcon(id, claimable ? b => {
        if (Online.send({ type: 'interact', npc: npcId, offer: `quest:claim:${quest.id}:${id}` })) b.disabled = true;
      } : null);
      put(n);
    }
    if (icons.childElementCount) container.append(icons);
    return choices;
  }
  function questAction(quest, action, b, npcId = quest.npc) {
    if (action === 'accept') return City.acceptQuest(quest, b);
    if (Online.send({ type: 'interact', npc: npcId, offer: `quest:${action}:${quest.id}` })) b.disabled = true;
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
  function render() {
    const active = definitions.filter(q => ['ready', 'active'].includes(status(q)));
    active.sort((a, b) => Number(status(a) === 'ready') - Number(status(b) === 'ready') || Number(b.id === tracked) - Number(a.id === tracked));
    const tracker = $('quest-tracker');
    const header = element('div', '', 'tracker-heading');
    const journal = button(`Quests (${active.length}) · ${window.Keys ? Keys.label('quests', false) : 'Q'}`, show); journal.className = 'tracker-journal';
    const toggle = button(collapsed ? '+' : '−', () => { collapsed = !collapsed; render(); $('quest-tracker').querySelector('.tracker-toggle').focus(); }); toggle.className = 'tracker-toggle';
    toggle.setAttribute('aria-label', collapsed ? 'Expand quest tracker' : 'Collapse quest tracker'); toggle.setAttribute('aria-expanded', String(!collapsed));
    header.append(journal, toggle); tracker.replaceChildren(header);
    const list = element('div', '', 'tracker-list'); list.hidden = collapsed;
    for (const quest of active) {
      const row = element('div', '', 'tracker-quest'); row.dataset.quest = quest.id;
      row.dataset.status = status(quest);
      row.dataset.tracked = String(tracked === quest.id); row.setAttribute('role', 'group'); row.setAttribute('aria-label', quest.title);
      if (isMainQuest(quest)) row.append(element('small', 'Main Questline', 'tracker-main'));
      const heading = element('div', '', 'tracker-quest-heading');
      const title = button(quest.title, () => { track(quest.id); show(); }); title.className = 'tracker-title';
      const tracking = button(tracked === quest.id ? 'Tracking' : 'Track quest', () => {
        track(tracked === quest.id ? null : quest.id);
        $('quest-tracker').querySelector(`[data-quest="${quest.id}"] .tracker-track`)?.focus({ preventScroll: true });
      });
      tracking.className = 'tracker-track'; tracking.dataset.action = 'track'; tracking.setAttribute('aria-pressed', String(tracked === quest.id));
      heading.append(title, tracking); row.append(heading);
      if (status(quest) === 'ready') {
        const npc = handIn(quest);
        row.append(element('small', '✓ Complete · Ready to turn in', 'tracker-objective complete'));
        const destination = button(`Hand in: ${npc.name} · ${areas[npc.zone].name}`, () => {
          track(quest.id);
          if (npc.zone === Field.zone) Field.visitNpc(npc.id);
          else window.WorldMap?.show();
        });
        destination.className = 'tracker-destination'; row.append(destination);
      }
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
  // One selected quest is read on the parchment; the dark list keeps regions,
  // ready turn-ins, abandoned automatic quests and completed history separate.
  function renderJournal(active) {
    const zone = window.Field?.zone || 0;
    const mine = [...active].sort((a, b) => Number(status(a) === 'ready') - Number(status(b) === 'ready') || Number(b.id === tracked) - Number(a.id === tracked) || Number(b.zone === zone) - Number(a.zone === zone));
    const recoverable = definitions.filter(q => q.autoLevel && heroLevel >= q.autoLevel && abandoned.includes(q.id)
      && status(q) === 'available' && (!q.handoffTo || !state({id: q.handoffTo})));
    const done = definitions.filter(q => !q.handoffTo && (status(q) === 'completed' || state(q)?.claimed && state(q)?.completions > 0));
    const entries = [...mine.map(q => ({ q, history: false })), ...recoverable.map(q => ({ q, history: false })), ...done.map(q => ({ q, history: true }))];
    const key = entry => (entry.history ? 'history:' : '') + entry.q.id;
    const chosen = entries.find(e => key(e) === journalSelection) || entries.find(e => e.q.id === tracked && !e.history) || entries[0];
    journalSelection = chosen ? key(chosen) : null;
    const list = $('quest-list'), page = $('quest-page'), controls = $('quest-controls');
    const scroll = list.getClientRects().length ? list.scrollTop : paneScroll.list, reading = page.dataset.selection === journalSelection, pageScroll = reading ? (page.getClientRects().length ? page.scrollTop : paneScroll.detail) : 0;
    paneScroll.list = scroll; paneScroll.detail = pageScroll;
    const memoriesOpen = reading && page.querySelector('.quest-memories')?.open;
    const previousStatus = list.querySelector('[aria-pressed="true"]')?.dataset.status;
    const focus = document.activeElement, focusKey = focus?.closest('.journal-quest')?.dataset.selection, focusAction = focus?.closest('#quest-controls button')?.dataset.action;
    const row = (q, history = false) => {
      const s = history ? 'completed' : status(q), selection = (history ? 'history:' : '') + q.id;
      const b = button('', () => { journalSelection = selection; abandonConfirm = null; renderJournal(active); questPane('detail', true); });
      b.className = 'journal-quest'; b.dataset.quest = q.id; b.dataset.status = s; b.dataset.selection = selection; b.dataset.repeatable = String(!!q.repeatable);
      b.setAttribute('aria-pressed', String(selection === journalSelection));
      b.setAttribute('aria-controls', 'quest-page');
      b.setAttribute('aria-label', `${q.title}, ${words[s]}${tracked === q.id && !history ? ', Tracking' : ''}`);
      b.append(element('span', `[${q.level}] ${q.title}`, 'journal-quest-name'));
      const mark = element('span', tracked === q.id && !history ? '◆' : s === 'ready' ? '?' : history ? '✓' : q.repeatable ? '↻' : '!', 'journal-quest-mark');
      mark.setAttribute('aria-hidden', 'true'); b.append(mark);
      return b;
    };
    const group = (name, id, quests, history = false, className = '') => {
      const g = document.createElement('details'); g.className = 'journal-group ' + className; g.dataset.group = id;
      g.open = !closedGroups.has(id);
      g.append(element('summary', name));
      for (const q of quests) g.append(row(q, history));
      g.addEventListener('toggle', () => { if (g.isConnected) { if (g.open) closedGroups.delete(id); else closedGroups.add(id); } });
      return g;
    };
    const nodes = [];
    const unfinished = mine.filter(q => status(q) === 'active');
    for (const z of [...new Set(unfinished.map(q => q.zone))]) nodes.push(group(areas[z].name, `zone:${z}`, unfinished.filter(q => q.zone === z)));
    const ready = mine.filter(q => status(q) === 'ready');
    if (ready.length) nodes.push(group(`Ready to turn in (${ready.length})`, 'ready', ready, false, 'quest-ready'));
    if (!mine.length) {
      nodes.push(element('p', 'You have no quests in progress. Speak to anyone with a ! over their head to take one.', 'quest-empty'));
      const next = definitions.find(q => q.zone === zone && status(q) === 'available') || definitions.find(q => status(q) === 'available');
      if (next) nodes.push(element('p', `Next: “${next.title}”. Speak to ${giver(next).name} in ${hubName(next) || areas[next.zone].name}.`, 'quest-empty quest-next'));
    }
    if (recoverable.length) nodes.push(group(`Abandoned automatic quests (${recoverable.length})`, 'abandoned', recoverable, false, 'quest-abandoned'));
    if (done.length) nodes.push(group(`Completed (${done.length})`, 'completed', done, true, 'quest-completed'));
    list.replaceChildren(...nodes); list.scrollTop = scroll;
    if (chosen && (!reading || previousStatus !== (chosen.history ? 'completed' : status(chosen.q)))) {
      [...list.querySelectorAll('.journal-quest')].find(n => n.dataset.selection === journalSelection)?.scrollIntoView({ block: 'nearest' });
    }
    $('quest-count').textContent = `Quests: ${mine.length}`;
    page.replaceChildren(); controls.replaceChildren(); page.dataset.selection = journalSelection || '';
    if (chosen) journalPage(chosen.q, chosen.history, page, controls);
    else {
      page.append(element('h4', 'Your next adventure'), element('p', 'Select a quest from the list to read its story, objectives and rewards.'));
      page.append(element('p', 'Find new quests at townspeople and camp crews marked with a !.', 'journal-hint'));
    }
    if (memoriesOpen && page.querySelector('.quest-memories')) page.querySelector('.quest-memories').open = true;
    page.scrollTop = pageScroll;
    if (focusKey) [...list.querySelectorAll('.journal-quest')].find(n => n.dataset.selection === focusKey)?.focus({ preventScroll: true });
    else if (focusAction) controls.querySelector(`[data-action="${focusAction}"]`)?.focus({ preventScroll: true });
  }
  function journalPage(quest, history, page, controls) {
    const s = history ? 'completed' : status(quest), npc = handIn(quest) || giver(quest);
    const node = element('article', '', 'journal-detail'); node.dataset.quest = quest.id; node.dataset.status = s;
    node.append(element('h4', quest.title));
    if (isMainQuest(quest)) node.append(element('small', 'Main Questline', 'quest-main'));
    node.append(element('p', words[s] + (quest.season ? (quest.seasonCadence==='daily'?' · Daily festival quest':' · Annual festival quest') : quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
    if (quest.story) node.append(element('small', `${quest.story.title} · ${quest.story.chapter}/28`, 'quest-location'));
    node.append(element('p', `Recommended level ${quest.level}${quest.recommendedPlayers ? ` · Group: ${quest.recommendedPlayers} players` : ''}`, 'quest-level'));
    node.append(element('h5', 'Description'), element('p', quest.description));
    storyRecap(quest, node);
    if (quest.story?.next) node.append(element('p', quest.story.next, 'quest-next'));
    node.append(element('h5', 'Objectives'));
    const objectiveList = element('ul', '', 'journal-objectives');
    quest.objectives.forEach((o, i) => {
      const count = history ? o.count : Math.min(state(quest)?.counts[i] || 0, o.count), complete = count >= o.count;
      objectiveList.append(element('li', `${complete ? '✓' : '•'} ${o.label}: ${count}/${o.count}${unit(o)}`, complete ? 'complete' : ''));
    });
    node.append(objectiveList);
    if (npc?.name) node.append(element('p', s === 'ready' ? `Hand in: ${npc.name} · ${areas[npc.zone ?? quest.zone].name}` : `Quest giver: ${npc.name} · ${areas[npc.zone ?? quest.zone].name}`, 'quest-location'));
    if (arenaLevel(quest)) node.append(element('p', `Accepted from ${giver(quest).name}. Enter and hand in at any arena giver.`, 'quest-location'));
    const party = mates(quest);
    if (!history && party.length) { const line = element('p', `Party on this quest: ${party.map(m => `${m.name} (${m.done ? 'ready' : m.text})`).join(', ')}`, 'quest-party'); line.dataset.partyQuest = String(party.length); node.append(line); }
    if (!quest.handoffTo) {
      node.append(element('h5', 'Rewards'), element('p', 'You will receive:', 'quest-reward-label'));
      rewards(quest, node, false);
      { const p = element('p', '', 'quest-reward'); p.innerHTML = `<span>${Locale.translate(`${quest.rewardXp} experience`)}</span> · ${Money.html(quest.rewardGold)}`; node.append(p); }
    }
    if (state(quest)?.completions) node.append(element('p', `Completed ${state(quest).completions} time${state(quest).completions === 1 ? '' : 's'}.`, 'quest-history'));
    const action = (label, name, handler, disabled = false) => {
      const b = button(label, handler); b.className = 'gossip-button'; b.dataset.action = name; b.disabled = disabled; controls.append(b); return b;
    };
    const current = !history && ['active', 'ready'].includes(s), asking = abandonConfirm === quest.id;
    if (asking) {
      const warning = element('div', '', 'journal-abandon-confirm'); warning.setAttribute('role', 'alert');
      warning.append(element('p', 'Abandon this quest? Current progress will be lost. You can take it again from its questgiver.', 'quest-abandon-warning'));
      const cancel = button('Cancel', () => { abandonConfirm = null; render(); controls.querySelector('[data-action="abandon"]')?.focus(); }); cancel.className = 'gossip-button'; warning.append(cancel); node.append(warning);
    }
    const abandon = action(asking ? 'Confirm abandon' : 'Abandon quest', 'abandon', () => {
      if (!asking) { abandonConfirm = quest.id; render(); $('quest-controls').querySelector('[data-action="abandon"]').focus(); }
      else if (Online.send({ type: 'quest_abandon', id: quest.id })) abandon.disabled = true;
    }, !current || quest.id.startsWith('es_'));
    action(tracked === quest.id && current ? 'Tracking' : 'Track quest', 'track', () => track(tracked === quest.id ? null : quest.id), !current);
    action('Show Map', 'map', () => { track(quest.id); close(); window.WorldMap?.show(); }, !current);
    if (!history && quest.autoLevel && abandoned.includes(quest.id) && s === 'available') {
      const restore = action('Restore quest', 'restore', () => { if (Online.send({ type: 'quest_restore', id: quest.id })) restore.disabled = true; });
    }
    if (current && npc?.zone === Field.zone) {
      const visit = button(`${s === 'ready' ? 'Return to' : 'Visit'} ${npc.name}`, () => { close(); Field.visitNpc(npc.id); });
      visit.className = 'gossip-button journal-visit'; node.append(visit);
    }
    page.append(node);
  }
  function open() { return !$('quest-journal').hidden; }
  function show() {
    if (window.Skillbar?.open || !Online.connected || Field.hero.dead || City.open || !$('pause').hidden || !$('equipment').hidden) return;
    previousFocus = document.activeElement; journalSelection = null; closedGroups.clear(); closedGroups.add('completed'); closedGroups.add('abandoned'); abandonConfirm = null;
    paneScroll.list = 0; paneScroll.detail = 0; questPane('list');
    Field.setPaused(true); $('quest-journal').hidden = false; render(); $('quest-close').focus();
  }
  function close(resume = true) {
    if (!open()) return;
    $('quest-journal').hidden = true;
    if (resume) { Field.setPaused(false); previousFocus?.focus?.({ preventScroll: true }); }
  }
  for (const b of $('quest-journal').querySelectorAll('.quest-mobile-tabs button')) b.addEventListener('click', () => questPane(b.dataset.questPane));
  $('quest-tracker').addEventListener('click', event => { if (!event.target.closest('button')) show(); });
  $('quest-close').addEventListener('click', () => close());
  $('quest-x')?.addEventListener('click', () => close());
  $('quest-list').addEventListener('keydown', event => {
    if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.code) || !event.target.matches('.journal-quest')) return;
    const rows = [...$('quest-list').querySelectorAll('.journal-quest')].filter(n => n.getClientRects().length);
    const index = rows.indexOf(event.target), next = event.code === 'Home' ? 0 : event.code === 'End' ? rows.length - 1 : Math.max(0, Math.min(rows.length - 1, index + (event.code === 'ArrowDown' ? 1 : -1)));
    event.preventDefault(); rows[next]?.focus(); rows[next]?.click();
  });
  $('quest-journal').addEventListener('keydown', event => {
    if (event.code !== 'Tab') return;
    const buttons = [...$('quest-journal').querySelectorAll('button:not(:disabled), summary, [tabindex="0"]')].filter(b => b.getClientRects().length);
    const first = buttons[0], last = buttons.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  window.Quests = {
    show, close, get open() { return open(); },
    setLevel(level) { if (heroLevel !== level) { heroLevel = level; clearGuidance(); render(); } },
    mapMarkers, navigationTarget, track, get tracked() { return tracked; },
    get anyReady() { return definitions.some(q => status(q) === 'ready'); },
    refresh() { render(); },
    seasonChanged() { clearGuidance(); render(); },
    // The merchant protects every material until its active quest is handed in or abandoned.
    needsMaterial(id) { return definitions.some(q => state(q) && !state(q).claimed && q.objectives.some(o => o.kind === 'bring' && o.target === id)); },
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
    reset() { initialized = false; groupKey = ''; groupList = []; progress = []; abandoned = []; journalSelection = null; closedGroups.clear(); abandonConfirm = null; signature = ''; tracked = null; bells = []; clearGuidance(); close(false); render(); },
    update(next, dismissed = abandoned) {
      const key = `${Field.zone}:` + JSON.stringify([next, dismissed]); if (key === signature) return;
      if (initialized) for (const p of next) {
        const q = byId.get(p.id), before = progress.find(old => old.id === p.id);
        if (!q || q.handoffTo || p.claimed || !q.objectives.every((o, i) => (p.counts[i] || 0) >= o.count)) continue;
        const wasReady = before && !before.claimed && q.objectives.every((o, i) => (before.counts[i] || 0) >= o.count);
        if (!wasReady) { window.Announce?.show(`Quest completed: ${q.title}`, 'quest'); window.QuestAudio?.play(); }
      }
      initialized = true; progress = next; abandoned = dismissed || []; signature = key;
      if (tracked && !progress.some(p => p.id === tracked && !p.claimed)) tracked = null;
      if (abandonConfirm && !progress.some(p => p.id === abandonConfirm && !p.claimed)) abandonConfirm = null;
      groupKey = ''; clearGuidance(); render();
    },
    // What an NPC's conversation lists, in World of Warcraft order: turn-ins, new quests, then quests still in progress.
    // Locked and finished quests are hidden, as they are there.
    active(id){const q=definitions.find(q=>q.id===id);return !!q&&status(q)==='active';},
    offered(id) {
      const rank = { ready: 0, available: 1, active: 2 };
      return definitions.filter(q => (q.npc===id||q.givers?.includes(id)||(status(q)==='ready'&&handInAt(q,id))) && status(q) in rank)
        .sort((a, b) => rank[status(a)] - rank[status(b)] || Number(a.repeatable) - Number(b.repeatable));
    },
    npc(id, container, pick, selected = null) {
      const classic = container.classList.contains('npc-quest-nav');
      container.replaceChildren(...this.offered(id).map(q => {
        const s = status(q), gap = q.level - heroLevel;
        const row = element('button', '', 'gossip-row'); row.type = 'button'; row.dataset.quest = q.id; row.dataset.status = s;
        if (q.repeatable) row.dataset.repeatable = 'true';
        if (classic) {
          // A row on the conversation's parchment: the quest mark, the title, the level.
          row.className = 'gossip-row journal-quest'; row.setAttribute('aria-controls', 'npc-quests');
          const mark = element('span', s === 'available' ? '!' : '?', 'gossip-icon journal-quest-mark'); mark.setAttribute('aria-hidden', 'true');
          const tag = element('span', `Lv ${q.level}`, 'gossip-tag'); tag.dataset.level = String(q.level);
          if (gap >= 5) tag.style.color = '#a31515'; else if (gap >= 3) tag.style.color = '#b8560f'; else if (gap <= -5) tag.style.color = '#6f6a58';
          row.append(mark, element('span', q.title, 'gossip-label journal-quest-name'), tag);
          row.setAttribute('aria-label', `${q.title}, ${words[s]}`); row.addEventListener('click', () => pick(q)); return row;
        }
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
    detail(quest, container, back, npcId = quest.npc, actionContainer = null) {
      const s = status(quest);
      const node = element('article', '', 'quest-card quest-detail'); node.dataset.quest = quest.id; node.dataset.status = s;
      node.append(element('h4', quest.title), element('span', words[s] + (quest.season ? (quest.seasonCadence==='daily'?' · Daily festival quest':' · Annual festival quest') : quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
      if (quest.story) node.prepend(element('small', quest.story.title + ' · ' + quest.story.chapter + '/28', 'quest-location'));
      node.append(element('p', quest.description));
      storyRecap(quest, node);
      if (quest.story?.next) node.append(element('p', quest.story.next, 'quest-next'));
      if (quest.recommendedPlayers) node.append(element('p', `Recommended level ${quest.level} · Group: ${quest.recommendedPlayers} players`, 'quest-level'));
      node.append(element('h5', actionContainer ? 'Quest Objectives' : 'Objectives'), element('p', s === 'ready' ? 'Complete · Ready to turn in' : objectives(quest).join('\n'), 'quest-objectives'));
      if (arenaLevel(quest)) node.append(element('p', `Accepted from ${giver(quest).name}. Enter and hand in at any arena giver.`, 'quest-location'));
      if (!quest.handoffTo) { const p = element('p', '', 'quest-reward'); p.innerHTML = `<span>${Locale.translate(`${quest.rewardXp} experience`)}</span> · ${Money.html(quest.rewardGold)}`; node.append(element('h5', 'Rewards'), p); }
      const choices = rewards(quest, node, s === 'ready', npcId, !!actionContainer);
      const actions = element('div', '', 'quest-actions');
      if (['available', 'ready'].includes(s) && !(s === 'ready' && choices.length)) {
        const action = s === 'ready' ? 'claim' : 'accept';
        const b = element('button', s === 'ready' ? 'Complete Quest' : state(quest)?.completions ? (quest.season ? (quest.seasonCadence==='daily'?'Take today’s quest':'Take this year’s quest') : 'Take bounty again') : 'Accept', 'gossip-button primary'); b.type = 'button';
        b.dataset.action = action;
        b.addEventListener('click', () => { questAction(quest, action, b, npcId); });
        actions.append(b);
      }
      const decline = element('button', s === 'available' ? 'Decline' : 'Back', 'gossip-button'); decline.type = 'button'; decline.dataset.action = 'decline';
      decline.addEventListener('click', back); actions.append(decline);
      if (actionContainer) actionContainer.replaceChildren(...actions.children);
      else node.append(actions);
      container.replaceChildren(node);
    },
    marker(id) { return this.markerInfo(id).symbol; },
    markerInfo(id) {
      for (const s of ['ready', 'available']) {
        const quest = definitions.find(q => (q.npc===id||q.givers?.includes(id)||(s==='ready'&&handInAt(q,id))) && status(q) === s && !q.repeatable)
          || definitions.find(q => (q.npc===id||q.givers?.includes(id)||(s==='ready'&&handInAt(q,id))) && status(q) === s);
        if (quest) return { symbol: s === 'ready' ? '?' : '!', color: quest.repeatable ? '#64b5ff' : '#ffdf88', repeatable: quest.repeatable };
      }
      if (definitions.some(q => status(q) === 'active' && q.objectives.some((o, i) => (o.kind === 'talk' || o.kind === 'escort' || o.kind === 'handoff') && o.target === id && !(state(q)?.counts[i] >= o.count)))) return { symbol: '◆', color: '#ffdf88' };
      return { symbol: '', color: '#ffdf88' };
    },
  };
  render();
})();
