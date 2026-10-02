'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const areas = [WORLD_MAP, ...(WORLD_MAP.zones || [])];
  const definitions = areas.flatMap((area, zone) => (area.quests || []).map(q => ({ ...q, zone })));
  let heroLevel = 1, progress = [], signature = '', tracked = null, previousFocus = null, collapsed = false;
  const state = quest => progress.find(p => p.id === quest.id);
  const giver = quest => areas[quest.zone].npcs.find(n => n.id === quest.npc);
  function status(quest) {
    const p = state(quest);
    if (p && !p.claimed) return quest.objectives.every((o, i) => (p.counts[i] || 0) >= o.count) ? 'ready' : 'active';
    if (p?.claimed && !quest.repeatable) return 'completed';
    if (quest.requires && !(state({ id: quest.requires })?.completions > 0)) return 'locked';
    return 'available';
  }
  const words = { ready: 'Ready to turn in', active: 'In progress', completed: 'Completed', locked: 'Locked', available: 'Available' };
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
    return quest.objectives.map((o, i) => `${o.label}: ${p?.claimed ? o.count : p?.counts[i] || 0}/${o.count}`);
  }
  function card(quest, atNpc) {
    const s = status(quest), npc = giver(quest);
    const node = element('article', '', 'quest-card'); node.dataset.quest = quest.id; node.dataset.repeatable = String(quest.repeatable);
    node.append(element('h4', quest.title), element('span', words[s] + (quest.repeatable ? ' · Repeatable' : ''), 'quest-state'));
    if (!atNpc) node.append(element('small', `${areas[quest.zone].name} · ${areas[quest.zone].city?.name || 'Quest giver'}`, 'quest-location quest-history'));
    const gap = quest.level - (heroLevel);
    const rec = element('p', `Recommended level ${quest.level}`, 'quest-level'); rec.dataset.level = String(quest.level);
    if (gap >= 5) rec.style.color = '#ff6b6b'; else if (gap >= 3) rec.style.color = '#ffa65a'; else if (gap <= -5) rec.style.color = '#9fb0a0';
    node.append(rec);
    node.append(element('p', quest.description), element('p', objectives(quest).join(' · '), 'quest-objectives'));
    node.append(element('p', `Reward: ${quest.rewardXp} XP · ${quest.rewardGold} gold`, 'quest-reward'));
    if (s === 'locked') {
      node.append(element('p', `Complete “${definitions.find(q => q.id === quest.requires)?.title}” first.`));
    } else if (atNpc && ['available', 'ready'].includes(s)) {
      const action = s === 'ready' ? 'claim' : 'accept';
      const b = button(s === 'ready' ? 'Collect reward' : state(quest)?.completions ? 'Take bounty again' : 'Accept quest', () => {
        if (Online.send({ type: 'interact', npc: quest.npc, offer: `quest:${action}:${quest.id}` })) b.disabled = true;
      });
      b.dataset.action = action; node.append(b);
    } else if (!atNpc && s !== 'completed') {
      if (Field.zone !== quest.zone) node.append(element('p', quest.zone === 0
        ? `${npc.name} is back in Greenmeadow. Return through the gate first.`
        : `${npc.name} is in ${areas[quest.zone].name}. Travel through the gate to ${areas[quest.zone].city?.name || 'meet them'}.`, 'quest-history'));
      else node.append(button(`${s === 'ready' ? 'Return to' : s === 'available' ? 'Get quest from' : 'Visit'} ${npc.name}`, () => {
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
      if (status(quest) === 'ready') row.append(element('small', `✓ Return to ${giver(quest).name} for your reward`, 'tracker-objective complete'));
      else quest.objectives.forEach((o, i) => {
        const count = Math.min(state(quest)?.counts[i] || 0, o.count), done = count >= o.count;
        row.append(element('small', `${done ? '✓' : '•'} ${o.label}: ${count}/${o.count}`, `tracker-objective${done ? ' complete' : ''}`));
      });
      list.append(row);
    }
    if (!active.length) {
      const next = definitions.find(q => q.zone === (window.Field?.zone || 0) && status(q) === 'available') || definitions.find(q => status(q) === 'available');
      if (next) list.append(element('span', next.title, 'tracker-title'), element('small', `Speak to ${giver(next).name} in ${areas[next.zone].city?.name || areas[next.zone].name}`, 'tracker-objective'));
      else list.append(element('small', 'All stories complete. Visit a quartermaster for another bounty.', 'tracker-objective'));
    }
    tracker.append(list);
    if (open()) $('quest-list').replaceChildren(...[...definitions].sort((a, b) => Number(b.zone === (window.Field?.zone || 0)) - Number(a.zone === (window.Field?.zone || 0))).map(q => card(q, false)));
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
      node.append(element('h5', 'Objectives'), element('p', objectives(quest).join('\n'), 'quest-objectives'));
      node.append(element('h5', 'Rewards'), element('p', `${quest.rewardXp} experience · ${quest.rewardGold} gold`, 'quest-reward'));
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
      if (definitions.some(q => status(q) === 'active' && q.objectives.some((o, i) => o.kind === 'talk' && o.target === id && !(state(q)?.counts[i] >= o.count)))) return { symbol: '◆', color: '#ffdf88' };
      return { symbol: '', color: '#ffdf88' };
    },
  };
  render();
})();
