'use strict';
// Merchant basket. Ownership, prices, payment and buy-back are server decisions.
(() => {
  const $ = id => document.getElementById(id);
  const make = (tag, text = '', cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  const button = (text, action) => { const b = make('button', text, 'btn ghost'); b.type = 'button'; b.addEventListener('click', action); return b; };
  const key = row => `${row.item}:${row.copy || 0}`;
  const price = row => Math.min(4294967295, Math.floor((row.base * row.quantity * (100 + (data?.goldPercent || 0)) + 50) / 100));
  const rarity = row => row.rarity || row.gear?.[0]?.rarity || Inventory.definition(row.item)?.rarity;
  let npc = null, container = null, data = null, basket = new Map(), filter = 'all', tab = 'sell', pending = false, timer = 0, snapshotKey = '', warning = null, zone = null;
  function settle() { clearTimeout(timer); pending = false; }
  function send(message) {
    if (pending || !npc || !Online.send({ ...message, npc: npc.id })) return false;
    pending = true;
    timer = setTimeout(() => { settle(); if (container) { data = null; draw(); request(); } }, 4000);
    return true;
  }
  function request() { send({ type: 'shop_open' }); }
  function closeWarning() { if (warning) { warning.close(); warning.remove(); warning = null; } }
  function close() {
    closeWarning(); settle(); npc = null; container = null; data = null; basket.clear(); snapshotKey = '';
  }
  function reconcile() {
    const available = new Map((data?.available || []).map(row => [key(row), row]));
    for (const [id, row] of basket) {
      const next = available.get(id);
      if (!next) basket.delete(id);
      else basket.set(id, { ...next, quantity: Math.min(row.quantity, next.quantity) });
    }
  }
  function itemRow(row, action, actionLabel, sold = false) {
    const i = Inventory.definition(row.item), n = make('article', '', 'sell-item');
    n.dataset.item = row.item; n.dataset.copy = String(row.copy || row.gear?.[0]?.id || ''); n.dataset.rarity = rarity(row);
    const icon = make('span', '', 'sell-icon'); icon.innerHTML = Inventory.icon(i);
    const details = make('div'), name = make('b', `${i?.name || row.item} ×${row.quantity}`, 'sell-name');
    details.append(name);
    const copy = sold ? row.gear?.[0] : row.gear;
    if (copy) details.append(make('small', `Copy #${copy.id} · ${Inventory.rarityName(copy)} · rank ${copy.rank} · ${Inventory.durabilityOf(copy)}% durability`));
    details.append(make('small', `${sold ? row.paid : price(row)} gold`));
    Inventory.attachTooltip(icon, () => i);
    const b = button(actionLabel, action); b.disabled = pending; n.append(icon, details, b); return n;
  }
  function submit() {
    closeWarning();
    const items = [...basket.values()].map(({ item, copy, quantity }) => ({ item, ...(copy ? { copy } : {}), quantity }));
    if (send({ type: 'sell_batch', items })) draw();
  }
  function confirm() {
    if (pending || !basket.size) return;
    const precious = [...basket.values()].filter(row => ['epic', 'legendary'].includes(row.rarity));
    if (!precious.length) { submit(); return; }
    closeWarning();
    warning = make('dialog', '', 'sell-warning panel'); warning.id = 'sell-warning';
    warning.setAttribute('aria-labelledby', 'sell-warning-title');
    const title = make('h3', 'Sell valuable items?'); title.id = 'sell-warning-title'; warning.append(title);
    warning.append(make('p', 'These purple or orange items are in your basket:'));
    const list = make('ul');
    for (const row of precious) {
      const n = make('li', Inventory.definition(row.item)?.name || row.item); n.dataset.rarity = row.rarity; list.append(n);
    }
    const yes = button('Yes, sell', submit), cancel = button('Cancel', () => { closeWarning(); $('sell-confirm')?.focus(); });
    yes.id = 'sell-yes'; cancel.id = 'sell-cancel';
    warning.append(list, make('p', `You receive: ${[...basket.values()].reduce((sum, row) => sum + price(row), 0)} gold`), cancel, yes);
    warning.addEventListener('cancel', event => { event.preventDefault(); closeWarning(); $('sell-confirm')?.focus(); });
    warning.addEventListener('keydown', event => event.stopPropagation());
    $('stage').append(warning); warning.showModal();
    window.Settings?.registerWindow('sell-warning', null, 'Sell valuable items?', false);
    (precious.some(row => row.rarity === 'legendary') ? cancel : yes).focus();
  }
  function draw() {
    if (!container || !npc) return;
    if (warning) closeWarning();
    container.replaceChildren(); container.className = 'sell-workspace'; container.setAttribute('aria-busy', String(pending));
    const tabs = make('div', '', 'sell-tabs');
    for (const [id, label] of [['sell', 'Sell'], ['back', 'Buy-back']]) {
      const b = button(label, () => { tab = id; draw(); }); b.dataset.tab = id; b.setAttribute('aria-pressed', String(tab === id)); tabs.append(b);
    }
    container.append(tabs, make('p', data?.notice || '', 'sell-notice'));
    if (!data) { container.append(make('p', 'Loading merchant…')); return; }
    if (tab === 'back') {
      container.append(make('p', 'Last 12 items at this merchant. Buy-back is cleared when you leave the game.'));
      const list = make('div', '', 'sell-list'); list.id = 'sell-buyback';
      for (const row of [...data.buyBack].reverse()) list.append(itemRow(row, () => { if (send({ type: 'buy_back', id: row.id })) draw(); }, 'Buy back', true));
      if (!list.childElementCount) list.append(make('p', 'No items to buy back.'));
      container.append(list); return;
    }
    const filters = make('div', '', 'sell-filters');
    for (const [id, label] of [['all', 'All'], ['common', 'Common'], ['uncommon', 'Uncommon'], ['rare', 'Rare'], ['epic', 'Epic'], ['legendary', 'Legendary']]) {
      const b = button(label, () => { filter = id; draw(); }); b.dataset.filter = id; b.setAttribute('aria-pressed', String(filter === id)); filters.append(b);
    }
    const junk = button('Sell all junk', () => {
      for (const row of data.available) {
        const i = Inventory.definition(row.item);
        if (['common', 'uncommon'].includes(row.rarity) && (row.gear || i?.kind === 'material')) basket.set(key(row), { ...row });
      }
      draw();
    }); junk.id = 'sell-junk'; junk.disabled = pending;
    container.append(filters, junk, make('p', 'Equipped copies are kept.'));
    const columns = make('div', '', 'sell-columns'), pick = make('section'), give = make('section');
    pick.append(make('h4', 'Your bags')); give.append(make('h4', 'You give'));
    const choices = make('div', '', 'sell-list'); choices.id = 'sell-pick';
    for (const row of data.available) {
      if (filter !== 'all' && row.rarity !== filter) continue;
      const remaining = row.quantity - (basket.get(key(row))?.quantity || 0); if (!remaining) continue;
      const shown = { ...row, quantity: remaining };
      const n = itemRow(shown, () => {
        const quantity = row.copy ? 1 : Number(n.querySelector('input').value);
        if (!Number.isSafeInteger(quantity) || quantity < 1 || quantity > remaining) return;
        basket.set(key(row), { ...row, quantity: quantity + (basket.get(key(row))?.quantity || 0) }); draw();
      }, 'Add');
      if (!row.copy) {
        const input = make('input'); input.type = 'number'; input.min = '1'; input.max = String(remaining); input.value = '1';
        input.setAttribute('aria-label', 'Quantity'); input.disabled = pending; n.insertBefore(input, n.lastChild);
      }
      choices.append(n);
    }
    if (!choices.childElementCount) choices.append(make('p', 'No items to show.'));
    const offered = make('div', '', 'sell-list'); offered.id = 'sell-basket';
    for (const [id, row] of basket) offered.append(itemRow(row, () => { basket.delete(id); draw(); }, 'Remove'));
    if (!basket.size) offered.append(make('p', 'Add items to review your sale.'));
    pick.append(choices); give.append(offered); columns.append(pick, give); container.append(columns);
    const total = make('strong', `You receive: ${[...basket.values()].reduce((sum, row) => sum + price(row), 0)} gold`, 'sell-total');
    total.id = 'sell-total'; total.setAttribute('aria-live', 'polite');
    const confirmButton = button('Confirm sale', confirm); confirmButton.id = 'sell-confirm'; confirmButton.disabled = pending || !basket.size || basket.size > 256;
    container.append(total, confirmButton);
  }
  window.Shop = {
    render(merchant, target) {
      const opening = npc?.id !== merchant.id || container !== target;
      if (opening) { close(); npc = merchant; zone = Field.zone || 0; container = target; filter = 'all'; tab = 'sell'; draw(); request(); }
      else draw();
    }, close,
    onPacket(packet) {
      if (!npc || packet.npc !== npc.id) return;
      settle(); closeWarning();
      if (packet.closed) { close(); City.close(); return; }
      data = packet;
      if (packet.ok && packet.changed) basket.clear();
      reconcile();
      Inventory.updateBags(packet.inventory, packet.equipment, packet.bags, packet.gearInstances);
      window.City?.shopGold(packet.gold); draw();
    },
    onSnapshot(c) {
      if (!npc) return;
      const merchant = City.npcs.find(n => n.id === npc.id);
      if (!c || c.dead || c.sparkTravel || (c.zone || 0) !== zone || !merchant || Math.hypot(c.x - merchant.x, c.y - merchant.y) > 3.2) { close(); City.close(); return; }
      const nextKey = JSON.stringify([c.inventory, c.gearInstances, c.equipment, c.gold, c.rebirthTiers]);
      if (nextKey !== snapshotKey && !pending && !warning) { snapshotKey = nextKey; request(); }
    },
  };
})();
