'use strict';
// The server owns trade invitations, offers and the final exchange.
(() => {
  const $ = id => document.getElementById(id);
  const send = command => Online.send({ type: 'trade', command });
  const offerDraft = () => send({ op: 'offer_copies', items: draft.items, copies: draft.copies.map(g => g.id), gold: draft.gold });
  const catalog = new Map((window.WORLD_ITEMS || []).map(i => [i.id, i]));
  let state = null, character = null, characterKey = '', draft = { items: [], copies: [], gold: 0 };
  const make = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  const label = id => catalog.get(id)?.name || id;
  const available = id => {
    const stack = character?.inventory?.find(s => s.item === id), i = catalog.get(id);
    if (!stack || !i || i.starter || i.rarity === 'gm') return 0;
    let worn = Object.values(character.equipment || {}).filter(x => x === id).length;
    const look = character.equippedLook || character.look;
    if (window.Inventory?.legacyPiece(i.kind, look)?.id === id) worn++;
    return Math.max(0, stack.quantity - worn);
  };
  // Class gear is bound to its owner; a rolled copy can be handed to a voter of its roll for two hours (the server decides).
  const bound = i => !!i.class && !['material', 'bag', 'food', 'potion', 'mount_licence'].includes(i.kind);
  const windowCopies = id => {
    const stack = character?.inventory?.find(s => s.item === id), partner = state?.partner?.id;
    const worn = (stack?.quantity || 0) - available(id), now = Date.now() / 1000;
    return (character?.gearInstances || []).filter(g => g.item === id).slice(worn)
      .filter(g => g.tradeUntil > now && (g.tradeWith || []).includes(partner));
  };
  // How many of `id` the picker may offer right now.
  const tradeable = id => { const i = catalog.get(id); return i && bound(i) ? windowCopies(id).length : available(id); };
  function exactCopies(id) {
    const item = catalog.get(id);
    if (bound(item)) return windowCopies(id);
    const worn = (character?.inventory?.find(s => s.item === id)?.quantity || 0) - available(id);
    return (character?.gearInstances || []).filter(g => g.item === id).slice(worn);
  }
  const timeLeft = seconds => {
    const minutes = Math.max(1, Math.ceil(seconds / 60)), h = Math.floor(minutes / 60);
    return h ? `${h} h ${minutes % 60} min` : `${minutes} min`;
  };
  function renderItems(id, offer, own) {
    const list = $(id); list.replaceChildren();
    for (const stack of offer?.items || []) {
      const row = make('li', `${label(stack.item)} ×${stack.quantity}`);
      for (const gear of (offer.gear || []).filter(g => g.item === stack.item && g.enchant)) {
        const detail = make('span', ' · ' + window.Enchanting?.name(gear.enchant));
        detail.tabIndex = 0;
        Inventory.attachTooltip(detail, () => catalog.get(gear.item), undefined, () => ({ copies: [gear], count: 1, in:'Trade', hint:'' }));
        row.append(detail);
      }
      if (own) {
        const remove = make('button', 'Remove'); remove.type = 'button'; remove.className = 'window-tool';
        remove.addEventListener('click', () => {
          draft.items = draft.items.filter(s => s.item !== stack.item);
          draft.copies = draft.copies.filter(g => g.item !== stack.item);
          offerDraft();
        });
        row.append(remove);
      }
      list.append(row);
    }
    if (!list.childElementCount) list.append(make('li', 'No items'));
    { const li = make('li'); Money.set(li, offer?.gold || 0); list.append(li); }
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
      const count = available(stack.item), i = catalog.get(stack.item);
      if (!count) continue;
      const open = tradeable(stack.item);
      if (i && bound(i) && !open) {
        const option = make('option', `${label(stack.item)} (bound)`); option.value = stack.item; option.disabled = true;
        option.title = 'Class gear is bound to its owner. It can only be sold.'; $('trade-item').append(option); continue;
      }
      const option = make('option', `${label(stack.item)} (${open})`); option.value = stack.item; $('trade-item').append(option);
      for (const gear of exactCopies(stack.item)) {
        const enchant = window.Enchanting?.name(gear.enchant);
        if (!enchant) continue;
        const copy = make('option', Locale.translate('{0} · Copy #{1} · {2}'.replace('{0}', label(gear.item)).replace('{1}', gear.id).replace('{2}', enchant)));
        copy.dataset.item = gear.item;
        copy.dataset.copy = String(gear.id);
        copy.value = [gear.item, gear.id].join('@');
        $('trade-item').append(copy);
      }
      if (i && bound(i)) {
        const until = Math.min(...windowCopies(stack.item).map(g => g.tradeUntil));
        option.title = `Tradeable for ${timeLeft(until - Date.now() / 1000)} with the party of the roll`;
      }
    }
    if ([...$('trade-item').options].some(o => o.value === selected && !o.disabled)) $('trade-item').value = selected;
    else $('trade-item').selectedIndex = [...$('trade-item').options].findIndex(o => !o.disabled);
    $('trade-set-item').disabled = ![...$('trade-item').options].some(o => !o.disabled);
  }
  function close() {
    const wasOpen = !$('trade-panel').hidden;
    state = null; draft = { items: [], copies: [], gold: 0 }; render();
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
      draft = { items: [...(packet.mine?.items || [])], copies: [], gold: packet.mine?.gold || 0 };
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
    const option = $('trade-item').selectedOptions[0];
    const id = option?.dataset.item || option?.value;
    const copy = option?.dataset.copy && exactCopies(id).find(g => String(g.id) === option.dataset.copy);
    const quantity = copy ? 1 : Number($('trade-quantity').value);
    if (!id || !Number.isSafeInteger(quantity) || quantity < 1 || quantity > tradeable(id)) {
      $('trade-status').textContent = 'Choose an item quantity you can trade.'; return;
    }
    const items = draft.items.filter(s => s.item !== id);
    if (copy) {
      if (!draft.copies.some(g => g.id === copy.id)) draft.copies.push(copy);
      items.push({ item: id, quantity: draft.copies.filter(g => g.item === id).length });
    } else {
      draft.copies = draft.copies.filter(g => g.item !== id);
      items.push({ item: id, quantity });
    }
    draft.items = items;
    offerDraft();
  });
  Money.preview($('trade-gold'));
  $('trade-set-gold').addEventListener('click', () => {
    const gold = Number($('trade-gold').value);
    if (!Number.isSafeInteger(gold) || gold < 0 || gold > (character?.gold || 0)) {
      $('trade-status').textContent = 'Choose an amount of copper you have.'; return;
    }
    draft.gold = gold;
    offerDraft();
  });
  $('trade-panel').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); send({ op: 'cancel' }); }
  });
  window.Trade = { request, onPacket, onSnapshot(c) {
    character = c;
    const key = JSON.stringify([c?.inventory, c?.equipment, c?.gold, c?.equippedLook || c?.look, c?.gearInstances]);
    if (key !== characterKey) { characterKey = key; if (state?.state === 'open') render(); }
  }, reset() { close(); character = null; characterKey = ''; }, get state() { return state; } };
})();
