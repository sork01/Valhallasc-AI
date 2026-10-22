'use strict';
// The bank window (docs/bank.md). The server owns the bank and every move: this sends item ids, quantities and copy
// ids, and draws whatever the last `bank` answer said. It never edits its own copy of the bank.
(() => {
  const $ = id => document.getElementById(id);
  const GEAR = new Set(['armor', 'weapon', 'headgear', 'shoulders', 'pants', 'gloves', 'necklace', 'accessory', 'cloak']);
  const dragType = 'application/x-valhallasc-bank';
  const RANGE = 2.8 + .4;      // the server's reach plus a margin, so a rounding difference never closes the window
  const MOST_GOLD = 4294967295;
  let npc = null, data = null, pending = null, previousFocus = null, selected = null, sorted = false, busy = 0, watch = 0, pendingTimer = 0;
  const make = (tag, text = '', cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  const button = (text, action, cls = 'btn ghost') => { const b = make('button', text, cls); b.type = 'button'; b.addEventListener('click', action); return b; };
  const item = id => Inventory.definition(id);
  const gear = i => GEAR.has(i?.kind);
  const number = n => Number(n).toLocaleString();
  const isOpen = () => !$('bank-panel').hidden;
  function say(text, ok = true) {
    const n = $('bank-notice'); n.textContent = text || ''; n.dataset.state = ok ? 'ok' : 'error';
  }
  const bankStacks = () => (data?.bank.items || []).filter(s => s.quantity > 0 && item(s.item));
  const bankCopies = id => (data?.bank.gear || []).filter(g => g.item === id);
  // The two sides of the window share one description, so a move reads the same in both directions.
  const sides = {
    bank: { stacks: bankStacks, copies: bankCopies, capacity: () => data?.bank.capacity || 0, where: 'in the bank', hint: 'Click to take · Shift-click takes all' },
    bags: { stacks: () => Inventory.looseStacks(), copies: id => Inventory.looseCopies(id), capacity: () => data?.bagCapacity || 0, where: 'in your bags', hint: 'Click to store · Shift-click stores all' },
  };
  const other = side => side === 'bank' ? 'bags' : 'bank';
  const order = stacks => !sorted ? stacks : [...stacks].sort((a, b) => {
    const x = item(a.item), y = item(b.item);
    return x.kind.localeCompare(y.kind) || (x.requiredLevel || 1) - (y.requiredLevel || 1) || x.name.localeCompare(y.name);
  });

  function send(message) {
    if (busy || !npc || !Online.send({ ...message, npc: npc.id })) return false;
    busy = setTimeout(() => { busy = 0; $('bank-panel').removeAttribute('aria-busy'); }, 3000);
    $('bank-panel').setAttribute('aria-busy', 'true');
    return true;
  }
  const settle = () => { clearTimeout(busy); busy = 0; $('bank-panel').removeAttribute('aria-busy'); };

  // Moves `amount` units (or one named gear copy) of `id` from one side to the other, after the same checks the
  // server makes, so an obvious refusal costs no round trip. The server still decides.
  function move(from, id, amount, copy) {
    const toBank = from === 'bags', i = item(id);
    if (!i || !data) return false;
    if (!Number.isSafeInteger(amount) || amount < 1) { say(toBank ? 'Choose a quantity to store.' : 'Choose a quantity to take.', false); return false; }
    if (toBank && i.rarity === 'gm') { say('Game master gear cannot be banked.', false); return false; }
    if (toBank && !bankStacks().some(s => s.item === id) && data.bank.used >= data.bank.capacity) { say('The bank is full.', false); return false; }
    if (!toBank && !Inventory.looseStacks().some(s => s.item === id) && Inventory.looseStacks().length >= data.bagCapacity) { say('Your bags are full. Make room first.', false); return false; }
    const message = toBank ? { type: 'bank_deposit', item: id, quantity: amount } : { type: 'bank_withdraw', item: id, quantity: amount };
    if (copy != null) message.copy = copy;
    return send(message);
  }
  // A click moves the quantity in the box; a shift-click moves the whole stack. A gear ID with several loose copies
  // opens its copy list instead, because the copies differ (rarity, rank, rolled stats) and the player picks one.
  function activate(side, stack, event) {
    Inventory.hideTooltip();
    const i = item(stack.item), copies = sides[side].copies(stack.item);
    if (event.shiftKey) { selected = null; move(side, stack.item, stack.quantity); return; }
    if (gear(i) && copies.length > 1) {
      selected = selected?.side === side && selected.item === stack.item ? null : { side, item: stack.item };
      render(); return;
    }
    selected = null;
    const asked = Number($('bank-quantity').value);
    move(side, stack.item, gear(i) ? 1 : Math.min(asked, stack.quantity));
  }
  function cell(side, stack) {
    const i = item(stack.item), copies = sides[side].copies(stack.item);
    const wrap = make('div', '', 'bag-cell inventory-item bank-cell');
    wrap.dataset.item = i.id; wrap.dataset.side = side; wrap.dataset.rarity = Inventory.bestRarity(i, copies);
    const b = make('button', '', 'item-tile'); b.type = 'button';
    b.innerHTML = Inventory.icon(i);
    b.append(make('span', String(stack.quantity), 'item-stack'), make('b', i.name, 'sr-only'));
    b.setAttribute('aria-label', side === 'bank' ? `${i.name} ×${stack.quantity} in the bank` : `${i.name} ×${stack.quantity} in your bags`);
    b.setAttribute('aria-pressed', String(selected?.side === side && selected.item === i.id));
    if (side === 'bags' && i.rarity === 'gm') b.setAttribute('aria-disabled', 'true');
    b.addEventListener('click', event => activate(side, stack, event));
    Inventory.attachTooltip(b, () => i, null, () => ({ copies: sides[side].copies(i.id), count: stack.quantity, in: sides[side].where, hint: sides[side].hint }));
    b.draggable = true;
    b.addEventListener('dragstart', event => { Inventory.hideTooltip(); event.dataTransfer.setData(dragType, JSON.stringify({ side, item: i.id })); event.dataTransfer.effectAllowed = 'move'; });
    wrap.append(b); return wrap;
  }
  // Dropping a stack on the other side's grid moves the quantity in the box, as a click does.
  function dropTarget(grid, side) {
    grid.addEventListener('dragover', event => { if (event.dataTransfer.types.includes(dragType)) { event.preventDefault(); grid.classList.add('drop-ready'); } });
    grid.addEventListener('dragleave', () => grid.classList.remove('drop-ready'));
    grid.addEventListener('drop', event => {
      event.preventDefault(); grid.classList.remove('drop-ready');
      let drag = null; try { drag = JSON.parse(event.dataTransfer.getData(dragType)); } catch (_) {}
      if (!drag || drag.side === side) return;
      const stack = sides[drag.side].stacks().find(s => s.item === drag.item); if (!stack) return;
      activate(drag.side, stack, { shiftKey: false });
    });
  }
  function grid(side, container) {
    const stacks = order(sides[side].stacks()), size = Math.max(sides[side].capacity(), stacks.length);
    const cells = stacks.map(stack => cell(side, stack));
    for (let n = stacks.length; n < size; n++) { const empty = make('div', '', 'bag-cell bag-cell-empty'); empty.setAttribute('aria-label', `Empty ${side === 'bank' ? 'bank' : 'bag'} slot ${n + 1}`); cells.push(empty); }
    container.replaceChildren(...cells);
  }
  function details() {
    const box = $('bank-details'), pick = selected && sides[selected.side].stacks().some(s => s.item === selected.item) ? selected : null;
    if (!pick) { selected = null; box.replaceChildren(make('p', 'Click an item to move it. Shift-click moves the whole stack.', 'bag-empty-note')); return; }
    const i = item(pick.item), copies = sides[pick.side].copies(pick.item), toBank = pick.side === 'bags';
    const heading = make('b', i.name, 'item-name'); heading.dataset.rarity = Inventory.bestRarity(i, copies);
    const rows = copies.map(g => {
      const row = make('div', '', 'bank-copy'); row.dataset.copy = g.id; row.dataset.rarity = g.rarity;
      row.append(make('span', `Copy #${g.id} · ${Inventory.copyLine(g)}`), button(toBank ? 'Store' : 'Take', () => { selected = null; move(pick.side, pick.item, 1, g.id); }, 'btn ghost item-action'));
      return row;
    });
    box.replaceChildren(heading, make('small', toBank ? 'Choose which copy to store.' : 'Choose which copy to take.'), ...rows);
  }
  function gold() {
    const bank = data.bank;
    $('bank-gold').textContent = `${number(bank.gold)} gold`;
    $('bank-purse').textContent = `Your purse: ${number(data.gold)} gold`;
    const expand = $('bank-expand'), price = bank.nextPrice;
    $('bank-expand-text').textContent = price == null
      ? `The bank is at its largest: ${number(bank.capacity)} cells.`
      : `Expansion ${bank.expansions + 1} of ${bank.expansionsMax}: +${bank.expansionCells} cells for ${number(price)} gold. It is never refunded.`;
    expand.hidden = price == null;
    expand.textContent = price == null ? '' : `Expand the bank · ${number(price)} gold`;
    expand.disabled = price != null && data.gold < price;
    $('bank-expand-short').textContent = price != null && data.gold < price ? `You need ${number(price - data.gold)} more gold.` : '';
  }
  function render() {
    if (!data || !isOpen()) return;
    Inventory.hideTooltip();
    const focus = $('bank-panel').contains(document.activeElement) ? document.activeElement.closest('[data-item]')?.dataset : null;
    $('bank-title').textContent = npc.name;
    $('bank-capacity').textContent = `${data.bank.used}/${data.bank.capacity} slots · ${Math.max(0, data.bank.capacity - data.bank.used)} free`;
    const bagUsed = Inventory.looseStacks().length;
    $('bank-bag-capacity').textContent = `${bagUsed}/${data.bagCapacity} slots · ${Math.max(0, data.bagCapacity - bagUsed)} free`;
    $('bank-capacity').classList.toggle('bags-full', data.bank.used >= data.bank.capacity);
    $('bank-bag-capacity').classList.toggle('bags-full', bagUsed >= data.bagCapacity);
    grid('bank', $('bank-grid')); grid('bags', $('bank-bag-grid'));
    gold(); details();
    if (focus) $('bank-panel').querySelector(`.bank-cell[data-side="${focus.side}"][data-item="${focus.item}"] button`)?.focus({ preventScroll: true });
  }

  // The window belongs to one banker. It closes when the hero is defeated, walks away, changes zone or disconnects.
  function stillNear() {
    const hero = window.Field?.hero, banker = window.City?.npcs.find(n => n.id === npc?.id);
    if (!hero || hero.dead || !Online.connected) return false;
    return !!banker && Math.hypot(hero.x - banker.x, hero.y - banker.y) <= RANGE;
  }
  function open(banker) {
    if (!Online.connected || isOpen() || !banker) return false;
    pending = banker; clearTimeout(pendingTimer); pendingTimer = setTimeout(() => { pending = null; }, 4000);
    return Online.send({ type: 'bank_open', npc: banker.id });
  }
  function show() {
    previousFocus = document.activeElement;
    window.City?.close(false);
    window.Quests?.close(false); window.Skillbar?.close(false); window.Social?.close(false);
    Field.setPaused(true);
    $('bank-panel').hidden = false;
    clearInterval(watch); watch = setInterval(() => { if (!stillNear()) close(); }, 250);
  }
  function close(resume = true) {
    if (!isOpen()) return;
    clearInterval(watch); settle(); Inventory.hideTooltip();
    $('bank-panel').hidden = true; npc = null; data = null; selected = null;
    if (resume) { Field.setPaused(false); previousFocus?.focus?.({ preventScroll: true }); }
  }
  function onPacket(packet) {
    if (!isOpen()) {
      if (!pending || pending.id !== packet.npc) return;
      npc = pending; pending = null; clearTimeout(pendingTimer);
      data = packet; show();
    }
    settle(); data = packet;
    Inventory.updateBags(packet.inventory || [], packet.equipment || {}, packet.bags || [], packet.gearInstances || []);
    if (packet.notice) say(packet.notice, packet.ok); else say('');
    render();
    if (!document.activeElement || !$('bank-panel').contains(document.activeElement)) $('bank-x').focus({ preventScroll: true });
  }
  // A refusal before the bank is reached (combat, mounted, too far) is a plain error packet: say it in the window, or
  // in the banker's dialogue when the window never opened, and let the player try again.
  function onError(text) {
    const asked = !!pending; pending = null; settle();
    if (isOpen()) say(text, false);
    else if (asked) { $('npc-notice').textContent = text; $('npc-offers').querySelector('[data-offer="bank"]')?.removeAttribute('disabled'); }
  }
  function reset() { pending = null; close(false); }

  dropTarget($('bank-grid'), 'bank'); dropTarget($('bank-bag-grid'), 'bags');
  $('bank-x').addEventListener('click', () => close());
  $('bank-close').addEventListener('click', () => close());
  $('bank-sort').addEventListener('click', () => { sorted = !sorted; $('bank-sort').setAttribute('aria-pressed', String(sorted)); render(); });
  function goldMove(deposit) {
    const amount = Number($('bank-gold-amount').value);
    if (!Number.isSafeInteger(amount) || amount < 1 || amount > MOST_GOLD) { say('Choose an amount of gold.', false); return; }
    if (deposit && amount > data.gold) { say('You do not carry that much gold.', false); return; }
    if (!deposit && amount > data.bank.gold) { say('The bank does not hold that much gold.', false); return; }
    send({ type: 'bank_gold', deposit, amount });
  }
  $('bank-gold-deposit').addEventListener('click', () => goldMove(true));
  $('bank-gold-withdraw').addEventListener('click', () => goldMove(false));
  $('bank-gold-amount').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); goldMove(!event.shiftKey); } });
  $('bank-expand').addEventListener('click', () => { if (data?.bank.nextPrice != null && data.gold >= data.bank.nextPrice) send({ type: 'bank_expand' }); });
  // Escape closes the window. No key typed in it reaches the game's shortcuts (Enter would open the chat and take the
  // focus before a cell's own click), and Tab stays inside.
  $('bank-panel').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); return; }
    if (event.key === 'Tab') {
      const buttons = [...$('bank-panel').querySelectorAll('button:not(:disabled), input:not(:disabled)')].filter(b => b.offsetParent);
      const first = buttons[0], last = buttons.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    event.stopPropagation();
  });
  // A key pressed while the focus has slipped outside the window (a click on the backdrop) is kept from the game too.
  addEventListener('keydown', event => {
    if (!isOpen() || $('bank-panel').contains(event.target) || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName || '')) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    event.stopPropagation();
  }, true);

  window.Bank = { open, onPacket, onError, reset, close, get visible() { return isOpen(); } };
})();
