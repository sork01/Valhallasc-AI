'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const definitions = WORLD_MAP.quests || [];
  let progress = [], signature = '', tracked = null, previousFocus = null;
  const state = quest => progress.find(p => p.id === quest.id);
  const giver = quest => WORLD_MAP.npcs.find(n => n.id === quest.npc);
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
      node.append(button(`${s === 'ready' ? 'Return to' : s === 'available' ? 'Get quest from' : 'Visit'} ${npc.name}`, () => {
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
    const selected = definitions.find(q => q.id === tracked && ['ready', 'active'].includes(status(q)))
      || definitions.find(q => status(q) === 'ready') || definitions.find(q => status(q) === 'active')
      || definitions.find(q => status(q) === 'available');
    const tracker = $('quest-tracker');
    tracker.replaceChildren(element('b', 'Quest Journal · Q'));
    if (selected) {
      tracker.append(element('span', selected.title));
      tracker.append(element('small', status(selected) === 'ready' ? `Return to ${giver(selected).name} for your reward`
        : status(selected) === 'available' ? `Speak to ${giver(selected).name} in Alderhaven` : objectives(selected).join(' · ')));
    } else tracker.append(element('small', 'All stories complete. Visit Linden for another bounty.'));
    if (open()) $('quest-list').replaceChildren(...definitions.map(q => card(q, false)));
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
  $('quest-tracker').addEventListener('click', show);
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
    reset() { progress = []; signature = ''; tracked = null; close(false); render(); },
    update(next) { const key = JSON.stringify(next); if (key === signature) return; progress = next; signature = key; render(); },
    npc(id, container) { container.replaceChildren(...definitions.filter(q => q.npc === id).map(q => card(q, true))); },
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
