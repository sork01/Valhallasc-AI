'use strict';
// Friends and parties. The server owns every list (server/src/world/social.rs); this file only shows them and sends
// requests. Names are other players' text, so everything is built with textContent, never innerHTML.
(() => {
  const $ = id => document.getElementById(id);
  const PARTY_MAX = 5;
  const empty = () => ({ friends: [], incoming: [], outgoing: [], party: null, friendsMax: 50 });
  let state = empty(), roster = [], tab = 'friends', previousFocus = null;
  // Invites carry seconds left; remember when each lapses on this machine's clock.
  const lapse = new Map();
  const CLASSES = { warrior: 'Warrior', mage: 'Mage', assassin: 'Assassin' };

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function button(text, key, action, className = 'window-tool') {
    const node = el('button', text, className); node.type = 'button'; node.dataset.key = key;
    node.addEventListener('click', action); return node;
  }
  const send = command => Online.send({ type: 'social', command });
  const myId = () => Online.id;
  const open = () => !$('social-panel').hidden;
  const inParty = id => !!state.party?.members.some(m => m.id === id);
  const isLeader = () => state.party?.leader === myId();
  const isFriend = id => state.friends.some(f => f.id === id);
  const label = p => `${p.name} · Lv ${p.level} ${CLASSES[p.class] || ''}`.trim();

  function notice(text, ok = true) {
    const line = $('social-notice'); line.textContent = text; line.dataset.ok = String(ok);
  }
  function member(m, withActions) {
    const row = el('li', '', 'social-row'); row.dataset.member = m.id; row.dataset.online = String(m.online);
    const who = el('span', '', 'social-who');
    const name = el('b', m.name + (state.party.leader === m.id ? ' ★' : ''));
    name.title = state.party.leader === m.id ? 'Party leader' : '';
    who.append(name, el('small', `Lv ${m.level} ${CLASSES[m.class] || ''} · ${m.online ? m.place : 'Offline'}`));
    const bar = el('span', '', 'member-bar'); bar.append(el('i', '', 'member-fill'), el('em', ''));
    row.append(who, bar);
    paintHealth(row, m);
    if (withActions && isLeader() && m.id !== myId()) {
      row.append(button('Make leader', `promote:${m.id}`, () => send({ op: 'party_promote', id: m.id })),
        button('Remove', `kick:${m.id}`, () => send({ op: 'party_kick', id: m.id })));
    }
    return row;
  }
  function paintHealth(row, m) {
    const fill = row.querySelector('.member-fill'), text = row.querySelector('.member-bar em');
    const share = m.online && m.maxHp > 0 ? Math.max(0, Math.min(1, m.hp / m.maxHp)) : 0;
    fill.style.width = `${share * 100}%`;
    text.textContent = !m.online ? '' : m.dead ? 'Defeated' : `${Math.ceil(m.hp)}/${Math.ceil(m.maxHp)}`;
    row.dataset.dead = String(!!m.dead);
  }
  function sectionTitle(text) { return el('h4', text, 'social-title'); }
  function inviteRows(list) {
    return list.map(i => {
      const row = el('li', '', 'social-row invite'); row.dataset.invite = `${i.kind}:${i.id}`;
      row.append(el('span', `${label(i)} wants to ${i.kind === 'friend' ? 'be your friend' : 'invite you to a party'}.`, 'social-who'),
        el('small', '', 'invite-left'),
        button('Accept', `accept:${i.kind}:${i.id}`, () => send({ op: `${i.kind}_accept`, id: i.id })),
        button('Decline', `decline:${i.kind}:${i.id}`, () => send({ op: `${i.kind}_decline`, id: i.id })));
      return row;
    });
  }
  function renderFriends(body) {
    const incoming = state.incoming.filter(i => i.kind === 'friend');
    if (incoming.length) { const requests = el('ul', '', 'social-list'); requests.append(...inviteRows(incoming)); body.append(sectionTitle('Requests'), requests); }
    const outgoing = state.outgoing.filter(i => i.kind === 'friend');
    if (outgoing.length) body.append(el('p', `Waiting for an answer from ${outgoing.map(i => i.name).join(', ')}.`, 'social-note'));
    body.append(sectionTitle(`Friends (${state.friends.length}/${state.friendsMax})`));
    const list = el('ul', '', 'social-list'); list.dataset.list = 'friends';
    for (const f of state.friends) {
      const row = el('li', '', 'social-row'); row.dataset.friend = f.id; row.dataset.online = String(f.online);
      const who = el('span', '', 'social-who');
      who.append(el('b', f.name), el('small', `Lv ${f.level} ${CLASSES[f.class] || ''} · ${f.online ? f.place : 'Offline'}`));
      row.append(who);
      if (f.online && !inParty(f.id)) row.append(button('Invite to party', `invite:${f.id}`, () => send({ op: 'party_invite', id: f.id })));
      row.append(button('Remove', `unfriend:${f.id}`, () => send({ op: 'friend_remove', id: f.id })));
      list.append(row);
    }
    if (!state.friends.length) list.append(el('li', 'No friends yet. Type a name above, or find someone in the Online tab.', 'social-empty'));
    body.append(list);
  }
  function renderParty(body) {
    const incoming = state.incoming.filter(i => i.kind === 'party');
    if (incoming.length) { const invitations = el('ul', '', 'social-list'); invitations.append(...inviteRows(incoming)); body.append(sectionTitle('Invitations'), invitations); }
    const party = state.party;
    if (!party) {
      body.append(el('p', 'You are not in a party. Invite a player by name, from the Friends tab, or from the Online tab. A party holds up to 5.', 'social-note'));
    } else {
      body.append(sectionTitle(`Party (${party.members.length}/${party.max})`));
      const list = el('ul', '', 'social-list'); list.dataset.list = 'party';
      list.append(...party.members.map(m => member(m, true)));
      body.append(list, button('Leave party', 'leave', () => send({ op: 'party_leave' }), 'window-tool danger'));
      if (!isLeader()) body.append(el('p', 'Only the leader can invite, promote or remove members.', 'social-note'));
    }
    const outgoing = state.outgoing.filter(i => i.kind === 'party');
    if (outgoing.length) body.append(el('p', `Invited: ${outgoing.map(i => i.name).join(', ')}.`, 'social-note'));
  }
  function renderOnline(body) {
    body.append(sectionTitle(`Online (${roster.length})`));
    const list = el('ul', '', 'social-list'); list.dataset.list = 'online';
    for (const p of roster) {
      const row = el('li', '', 'social-row'); row.dataset.player = p.id;
      const who = el('span', '', 'social-who');
      who.append(el('b', p.name + (p.self ? ' (you)' : '')), el('small', `Lv ${p.level} ${CLASSES[p.class] || ''} · ${p.place}`));
      row.append(who);
      if (!p.self) {
        if (p.friend) row.append(el('small', 'Friend', 'social-tag'));
        else if (state.outgoing.some(i => i.kind === 'friend' && i.id === p.id)) row.append(el('small', 'Requested', 'social-tag'));
        else row.append(button('Add friend', `add:${p.id}`, () => send({ op: 'friend_request', id: p.id })));
        const seated = inParty(p.id), taken = p.inParty && !seated;
        const full = (state.party?.members.length || 1) >= PARTY_MAX;
        if (seated) row.append(el('small', 'In your party', 'social-tag'));
        else if (taken) row.append(el('small', 'In a party', 'social-tag'));
        else if (state.party && !isLeader()) row.append(el('small', '', 'social-tag'));
        else {
          const invite = button('Invite', `invite:${p.id}`, () => send({ op: 'party_invite', id: p.id }));
          invite.disabled = full; if (full) invite.title = 'Your party is full';
          row.append(invite);
        }
      }
      list.append(row);
    }
    body.append(list, button('Refresh', 'refresh-online', () => send({ op: 'who' })));
  }
  function renderPanel() {
    if (!open()) return;
    const focused = document.activeElement?.dataset?.key;
    for (const t of document.querySelectorAll('#social-panel [role="tab"]')) {
      t.setAttribute('aria-selected', String(t.dataset.tab === tab)); t.tabIndex = t.dataset.tab === tab ? 0 : -1;
    }
    $('social-tab-friends').textContent = `Friends${state.incoming.some(i => i.kind === 'friend') ? ' •' : ''}`;
    $('social-tab-party').textContent = `Party${state.party ? ` ${state.party.members.length}/${PARTY_MAX}` : ''}${state.incoming.some(i => i.kind === 'party') ? ' •' : ''}`;
    $('social-add-friend').hidden = tab === 'party'; $('social-add-party').hidden = tab === 'friends';
    $('social-add').hidden = tab === 'online';
    const body = $('social-body'); body.replaceChildren(); body.dataset.tab = tab;
    ({ friends: renderFriends, party: renderParty, online: renderOnline })[tab](body);
    tickInvites();
    const again = focused && body.querySelector(`[data-key="${CSS.escape(focused)}"]`);
    if (again) again.focus({ preventScroll: true });
  }
  // The party frame at the top left: names and health, always visible while in a party.
  function renderFrame() {
    const frame = $('party-frame'), party = state.party;
    frame.hidden = !party; if (!party) { frame.replaceChildren(); return; }
    const head = button(`Party ${party.members.length}/${party.max} · P`, 'frame-open', () => show('party'), 'party-head');
    const list = el('ul', '', 'social-list');
    list.append(...party.members.map(m => member(m, false)));
    frame.replaceChildren(head, list);
  }
  // Floating prompts: an invite needs an answer even when no panel is open.
  function renderPrompts() {
    const box = $('social-invites');
    box.replaceChildren(...state.incoming.slice(0, 3).map(i => {
      const card = el('div', '', 'invite-card'); card.dataset.invite = `${i.kind}:${i.id}`;
      card.append(el('p', `${i.name} (Lv ${i.level}) ${i.kind === 'friend' ? 'sent you a friend request' : 'invited you to a party'}`),
        el('small', '', 'invite-left'),
        button('Accept', `prompt-accept:${i.kind}:${i.id}`, () => send({ op: `${i.kind}_accept`, id: i.id }), 'btn primary'),
        button('Decline', `prompt-decline:${i.kind}:${i.id}`, () => send({ op: `${i.kind}_decline`, id: i.id }), 'btn ghost'));
      return card;
    }));
    tickInvites();
  }
  function tickInvites() {
    const now = performance.now();
    for (const node of document.querySelectorAll('.invite-left')) {
      const key = node.closest('[data-invite]').dataset.invite, until = lapse.get(key);
      if (until) node.textContent = `${Math.max(0, Math.ceil((until - now) / 1000))}s`;
    }
  }
  function render() { renderFrame(); renderPrompts(); renderPanel(); }
  const shape = party => party && JSON.stringify([party.leader, party.members.map(m => [m.id, m.online, m.dead, m.level, m.place])]);
  // Party health arrives twice a second; update the bars in place and rebuild only when the members change.
  function updateParty(party) {
    const changed = shape(party) !== shape(state.party);
    state.party = party;
    if (changed) { render(); return; }
    for (const m of party?.members || []) for (const row of document.querySelectorAll(`[data-member="${CSS.escape(m.id)}"]`)) paintHealth(row, m);
  }
  function setState(next) {
    const now = performance.now();
    lapse.clear();
    for (const i of [...next.incoming, ...next.outgoing]) lapse.set(`${i.kind}:${i.id}`, now + i.left * 1000);
    state = { ...empty(), ...next };
    render();
    if (open() && tab === 'online') send({ op: 'who' });
  }
  function show(next = tab) {
    if (!$('scene-game') || $('scene-game').hidden || !Online.connected || Field.hero.dead) return;
    if (!open() && document.querySelector('#scene-game .pause:not([hidden])')) return;
    tab = next;
    if (!open()) { previousFocus = document.activeElement; Field.setPaused(true); $('social-panel').hidden = false; }
    send({ op: 'refresh' }); if (tab === 'online') send({ op: 'who' });
    renderPanel();
    if (!document.activeElement?.closest?.('#social-panel')) document.querySelector('#social-panel [role="tab"][aria-selected="true"]').focus({ preventScroll: true });
  }
  function close(resume = true) {
    if (!open()) return;
    $('social-panel').hidden = true;
    if (resume) { Field.setPaused(false); if (previousFocus?.isConnected) previousFocus.focus?.({ preventScroll: true }); }
  }
  function toggle(next) { if (open() && tab === next) close(); else show(next); }

  // Chat commands. Returns true when the text was one, so it is not sent as ordinary chat.
  function command(text) {
    const [word, ...rest] = text.trim().split(/\s+/), arg = rest.join(' ');
    const name = word.toLowerCase();
    if (name === '/p' || name === '/party') { if (arg) send({ op: 'party_chat', text: arg }); return true; }
    if (name === '/friend' || name === '/addfriend') { send({ op: 'friend_request', name: arg }); return true; }
    if (name === '/invite') { send({ op: 'party_invite', name: arg }); return true; }
    if (name === '/leave') { send({ op: 'party_leave' }); return true; }
    return false;
  }

  for (const t of document.querySelectorAll('#social-panel [role="tab"]')) t.addEventListener('click', () => { tab = t.dataset.tab; if (tab === 'online') send({ op: 'who' }); renderPanel(); });
  $('social-add').addEventListener('submit', event => {
    event.preventDefault();
    const input = $('social-name'), name = input.value.trim(); if (!name) return;
    if (send({ op: tab === 'party' ? 'party_invite' : 'friend_request', name })) input.value = '';
  });
  $('social-add-friend').addEventListener('click', () => { const name = $('social-name').value.trim(); if (name && send({ op: 'friend_request', name })) $('social-name').value = ''; });
  $('social-add-party').addEventListener('click', () => { const name = $('social-name').value.trim(); if (name && send({ op: 'party_invite', name })) $('social-name').value = ''; });
  $('social-close').addEventListener('click', () => close());
  $('social-open').addEventListener('click', () => toggle('friends'));
  $('social-name').addEventListener('keydown', event => { event.stopPropagation(); if (event.key === 'Escape') { event.preventDefault(); close(); } });
  $('social-panel').addEventListener('keydown', event => {
    if (event.key === 'Tab') {
      const nodes = [...$('social-panel').querySelectorAll('button:not(:disabled), input:not(:disabled)')].filter(n => n.getClientRects().length);
      const first = nodes[0], last = nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    } else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      if (!event.target.matches?.('[role="tab"]')) return;
      const tabs = ['friends', 'party', 'online'], next = tabs[(tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : 2)) % 3];
      event.preventDefault(); tab = next; if (tab === 'online') send({ op: 'who' }); renderPanel(); $(`social-tab-${next}`).focus();
    }
  });
  // This listener is registered before the game's own (online.js precedes game.js), so an open panel keeps every key.
  addEventListener('keydown', event => {
    if ($('scene-game').hidden || event.repeat || event.ctrlKey || event.altKey || event.metaKey) return;
    const key = event.key.toLowerCase(), typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName || '');
    if (open()) {
      if (typing && key !== 'escape') return;
      event.preventDefault(); event.stopImmediatePropagation();
      if (key === 'escape') close();
      else if (key === 'o') toggle('friends');
      else if (key === 'p') toggle('party');
      return;
    }
    if (typing || (key !== 'o' && key !== 'p')) return;
    event.preventDefault(); show(key === 'o' ? 'friends' : 'party');
  }, true);

  window.Social = {
    show, close, command, get open() { return open(); },
    get state() { return state; }, get roster() { return roster; },
    isPartyMember: id => inParty(id), isFriend,
    reset() { close(false); state = empty(); roster = []; lapse.clear(); render(); },
    // Packets from the server.
    onState: setState,
    onParty: updateParty,
    onWho(players) { roster = players; if (open() && tab === 'online') renderPanel(); },
    onNotice(packet) { notice(packet.text, packet.ok !== false); },
  };
  setInterval(() => { if (state.incoming.length || state.outgoing.length) tickInvites(); }, 1000);
  render();
})();
