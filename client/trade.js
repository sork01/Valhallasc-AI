'use strict';
// The server owns trade invitations, offers and the final exchange. This panel sends only item ids and quantities.
(() => {
  const $ = id => document.getElementById(id);
  const send = command => Online.send({ type: 'trade', command });
  const catalog = new Map((window.WORLD_ITEMS || []).map(i => [i.id, i]));
  let state = null, character = null, characterKey = '', draft = { items: [], gold: 0 };
  const make = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  const label = id => catalog.get(id)?.name || id;
  const available = id => {
    const stack = character?.inventory?.find(s => s.item === id), i = catalog.get(id);
    if (!stack || !i || i.starter || i.rarity === 'gm') return 0;
    let worn = Object.values(character.equipment || {}).filter(x => x === id).length;
    if (i.class === character.look.class && (i.kind === 'armor' || i.kind === 'weapon')) {
      const slot = `${i.class}_${i.kind}`;
      if (character.look[slot] === i.variant) worn++;
    }
    return Math.max(0, stack.quantity - worn);
  };
  function renderItems(id, offer, own) {
    const list = $(id); list.replaceChildren();
    for (const stack of offer?.items || []) {
      const row = make('li', `${label(stack.item)} ×${stack.quantity}`);
      if (own) {
        const remove = make('button', 'Remove'); remove.type = 'button'; remove.className = 'window-tool';
        remove.addEventListener('click', () => {
          draft.items = draft.items.filter(s => s.item !== stack.item);
          send({ op: 'offer', items: draft.items, gold: draft.gold });
        });
        row.append(remove);
      }
      list.append(row);
    }
    if (!list.childElementCount) list.append(make('li', 'No items'));
    list.append(make('li', `${offer?.gold || 0} gold`));
  }
  function render() {
    $('trade-request').hidden = state?.state !== 'request';
    $('trade-panel').hidden = !state || state.state === 'request';
    if (!state) return;
    const name = state.partner?.name || 'another player';
    if (state.state === 'request') { $('trade-request-text').textContent = `${name} wants to trade with you.`; return; }
    const active = state.state === 'open';
    $('trade-title').textContent = `Trade with ${name}`;
    $('trade-status').textContent = active ? 'Review both offers before you confirm.' : `Waiting for ${name} to accept…`;
    $('trade-offers').hidden = !active;
    $('trade-confirm').hidden = !active;
    if (!active) return;
    renderItems('trade-mine', state.mine, true);
    renderItems('trade-theirs', state.theirs, false);
    $('trade-partner-heading').textContent = `${name}'s offer`;
    if (document.activeElement !== $('trade-gold')) $('trade-gold').value = draft.gold;
    $('trade-my-ready').textContent = state.mine.ready ? 'You confirmed this offer.' : 'You have not confirmed.';
    $('trade-their-ready').textContent = state.theirs.ready ? `${name} confirmed.` : `${name} has not confirmed.`;
    $('trade-confirm').disabled = state.mine.ready;
    const selected = $('trade-item').value;
    $('trade-item').replaceChildren();
    for (const stack of character?.inventory || []) {
      const count = available(stack.item);
      if (!count) continue;
      const option = make('option', `${label(stack.item)} (${count})`); option.value = stack.item; $('trade-item').append(option);
    }
    if ([...$('trade-item').options].some(o => o.value === selected)) $('trade-item').value = selected;
    $('trade-set-item').disabled = !$('trade-item').options.length;
  }
  function close() {
    const wasOpen = !$('trade-panel').hidden;
    state = null; draft = { items: [], gold: 0 }; render();
    if (wasOpen) Field.setPaused(false);
  }
  function request(id) {
    if (!id || !Online.connected) return;
    window.Social?.close();
    send({ op: 'request', id });
  }
  function closeOtherPanels() {
    window.Social?.close(false);
    window.Quests?.close(false);
    window.WorldMap?.close(false);
    window.Skillbar?.close(false);
    window.Settings?.close(false);
    window.City?.close(false);
    if (!$('equipment').hidden) $('equipment-close').click();
    if (!$('pause').hidden) $('p-resume').click();
  }
  function onPacket(packet) {
    if (packet.state === 'closed' || packet.state === 'complete') { close(); return; }
    if (!state || state.partner?.id !== packet.partner?.id || state.state !== 'open' && packet.state === 'open')
      draft = { items: [...(packet.mine?.items || [])], gold: packet.mine?.gold || 0 };
    state = packet;
    if (packet.state === 'pending' || packet.state === 'open') {
      closeOtherPanels(); Field.setPaused(true);
      $('trade-panel').hidden = false;
    }
    render();
  }
  $('trade-accept').addEventListener('click', () => { window.Social?.close(); send({ op: 'accept', id: state.partner.id }); });
  $('trade-decline').addEventListener('click', () => send({ op: 'decline', id: state.partner.id }));
  $('trade-cancel').addEventListener('click', () => send({ op: 'cancel' }));
  $('trade-confirm').addEventListener('click', () => send({ op: 'confirm' }));
  $('trade-set-item').addEventListener('click', () => {
    const id = $('trade-item').value, quantity = Number($('trade-quantity').value);
    if (!id || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > available(id)) {
      $('trade-status').textContent = 'Choose an item quantity you can trade.'; return;
    }
    const items = draft.items.filter(s => s.item !== id);
    items.push({ item: id, quantity });
    draft.items = items;
    send({ op: 'offer', items, gold: draft.gold });
  });
  $('trade-set-gold').addEventListener('click', () => {
    const gold = Number($('trade-gold').value);
    if (!Number.isSafeInteger(gold) || gold < 0 || gold > (character?.gold || 0)) {
      $('trade-status').textContent = 'Choose a gold amount you have.'; return;
    }
    draft.gold = gold;
    send({ op: 'offer', items: draft.items, gold });
  });
  $('trade-panel').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); send({ op: 'cancel' }); }
  });
  window.Trade = { request, onPacket, onSnapshot(c) {
    character = c;
    const key = JSON.stringify([c?.inventory, c?.equipment, c?.gold, c?.look]);
    if (key !== characterKey) { characterKey = key; if (state?.state === 'open') render(); }
  }, reset() { close(); character = null; characterKey = ''; }, get state() { return state; } };
})();
