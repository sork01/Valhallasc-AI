'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const dragType = 'application/x-valhallasc-item';
  const slots = [['headgear', 'Headgear'], ['shoulders', 'Shoulders'], ['chest', 'Chest'], ['pants', 'Pants'], ['gloves', 'Gloves'], ['hands', 'Hands'], ['necklace', 'Necklace'], ['accessory1', 'Accessory 1'], ['accessory2', 'Accessory 2']];
  let stacks = [], look = null, gearSlots = {}, bags = [], signature = '', layout = [], character = null, activeBag = 0, selected = null, search = '', pendingPlacement = null;
  const bagPages = () => { let start = 0; return [{ name: 'Backpack', size: 16 }, ...bags.map(id => ({ name: definition(id)?.name || 'Bag', size: definition(id)?.bagSlots || 0 }))].map(bag => { const page = { ...bag, start }; start += bag.size; return page; }); };
  const capacity = () => bagPages().reduce((sum, b) => sum + b.size, 0);
  const definition = id => WORLD_ITEMS.find(i => i.id === id);
  const slotKind = slot => ({ chest: 'armor', hands: 'weapon', accessory1: 'accessory', accessory2: 'accessory' })[slot] || slot;
  const quantity = id => stacks.find(s => s.item === id)?.quantity || 0;
  const equippedCount = i => !i ? 0 : Object.values(gearSlots).filter(id => id === i.id).length + Number(i.class === look?.class && ['armor', 'weapon'].includes(i.kind) && look[i.class + (i.kind === 'armor' ? 'Armor' : 'Weapon')] === i.variant);
  const bagQuantity = id => Math.max(0, quantity(id) - equippedCount(definition(id)));
  const spare = s => definition(s.item)?.starter ? 0 : bagQuantity(s.item);
  const consumable = i => i && ['food', 'potion'].includes(i.kind);
  const compatible = i => i && !['material', 'bag', 'food', 'potion'].includes(i.kind) && (!i.class || i.class === look?.class);
  const effect = i => i.kind === 'food' ? `Restores ${i.heal} HP over ${i.duration} s · one meal at a time` : `Restores ${i.heal} HP at once · ${i.cooldown} s cooldown shared by all potions`;
  const useItem = i => consumable(i) && canEquip() && bagQuantity(i.id) > 0 && Field.useItem(i.id);
  const activate = i => consumable(i) ? useItem(i) : equip(i);
  const stats = i => [i.attack ? `+${i.attack} attack` : '', i.defense ? `${i.defense} defense` : ''].filter(Boolean).join(' · ');
  const itemAtSlot = slot => ['chest', 'hands'].includes(slot) ? WORLD_ITEMS.find(i => i.kind === slotKind(slot) && i.class === look?.class && look[i.class + (slot === 'chest' ? 'Armor' : 'Weapon')] === i.variant) : definition(gearSlots[slot]);
  const canEquip = () => Online.connected && !Field.hero?.dead;
  function node(tag, text = '', cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
  function button(text, action, cls = 'btn ghost') { const b = node('button', text, cls); b.type = 'button'; b.addEventListener('click', action); return b; }
  const art = {
    headgear: '<path d="M12 33v-9a20 20 0 0 1 40 0v9l-8 11H20z" fill="currentColor"/><path d="M18 29h28v8H18z" fill="#15171e"/><path d="M30 8h4v37h-4z" fill="#f4df99"/>',
    shoulders: '<path d="m8 21 17-9 7 9 7-9 17 9-3 23-17-6-4-8-4 8-17 6z" fill="currentColor"/><path d="m13 25 10-5 4 8m24-3-10-5-4 8" fill="none" stroke="#f3deb3" stroke-width="3"/>',
    armor: '<path d="m18 10 10 6h8l10-6 11 14-11 7-2 24H20l-2-24-11-7z" fill="currentColor"/><path d="M32 19v29M23 26h18M23 37h18" stroke="#f3deb3" stroke-width="3"/>',
    pants: '<path d="M17 10h30l-2 44H33l-1-26-1 26H19z" fill="currentColor"/><path d="M17 16h30M25 25l-2 21m16-21 2 21" stroke="#e7d1a6" stroke-width="3"/>',
    gloves: '<path d="m14 44-5-15 6-4 5 9V12h6v17h3V8h6v21h3V12h6v20l3-8 6 2-5 18-6 9H20z" fill="currentColor"/><path d="M21 44h22" stroke="#ebd2a1" stroke-width="4"/>',
    weapon: '<path d="m13 49 32-38 10-3-2 11-34 34z" fill="#dce5ef"/><path d="m17 34 14 13M11 53l10-12" stroke="currentColor" stroke-width="6" stroke-linecap="round"/><path d="m30 29 14-16" stroke="#fcf6ce" stroke-width="2"/>',
    bow: '<path d="M18 8Q54 32 18 56" fill="none" stroke="currentColor" stroke-width="6"/><path d="M18 8v48M8 32h40" stroke="#ecf3ff" stroke-width="2.5"/><path d="m48 32-8-5v10z" fill="#dce5ef"/>',
    mace: '<path d="m18 56 18-28" stroke="#b78a4e" stroke-width="6"/><circle cx="42" cy="19" r="11" fill="currentColor"/><path d="M42 4v30M27 19h30" stroke="#ecf3ff" stroke-width="3"/>',
    staff: '<path d="m20 56 16-36" stroke="#b78a4e" stroke-width="6"/><path d="m34 6 12 12-9 14-12-12z" fill="currentColor"/><path d="m34 10 2 14 7-6" fill="#ecf3ff"/>',
    daggers: '<path d="m9 49 16-31 11-6-3 12-18 31m14-6 16-31 11-6-3 12-18 31" fill="#dce5ef"/><path d="m10 38 14 6m10-6 14 6M9 53l8-13m12 13 8-13" stroke="currentColor" stroke-width="4"/>',
    necklace: '<path d="M13 12c0 31 38 31 38 0" fill="none" stroke="#d8b96a" stroke-width="5"/><path d="m32 30 10 10-10 14-10-14z" fill="currentColor"/><path d="m32 33 2 13 5-6" fill="#e6f6ff"/>',
    accessory: '<ellipse cx="32" cy="37" rx="16" ry="15" fill="none" stroke="#cda45b" stroke-width="7"/><path d="m32 9 12 12-12 12-12-12z" fill="currentColor"/><path d="m32 12 2 12 7-3" fill="#fff6c8"/>',
    material: '<path d="M13 39c-9-12 0-28 11-27 8-11 29-4 25 9 13 6 12 26-1 30-11 12-34 4-35-12z" fill="currentColor"/><ellipse cx="25" cy="24" rx="5" ry="7" fill="#ffffff8a"/><path d="m22 44 15 3" stroke="#ffffff44" stroke-width="4" stroke-linecap="round"/>',
    food: '<path d="M8 34h48c0 14-10 22-24 22S8 48 8 34zM18 26c-4-5 4-8 0-15M32 26c-4-5 4-8 0-15M46 26c-4-5 4-8 0-15" fill="none" stroke="currentColor" stroke-width="4"/><path d="M8 34h48" stroke="#f3deb3" stroke-width="3"/>',
    potion: '<path d="M25 6h14v14l14 28c2 5-1 10-7 10H18c-6 0-9-5-7-10l14-28z" fill="currentColor"/><path d="M25 6h14M16 40h32" stroke="#f3deb3" stroke-width="3"/><ellipse cx="26" cy="46" rx="4" ry="3" fill="#ffffff66"/>',
    shell: '<path d="M12 39c0-36 40-36 40 0l-9 14H21z" fill="currentColor"/><path d="M32 12v40M16 30l16 8 16-8M19 44l13-6 13 6" fill="none" stroke="#f1d59c" stroke-width="3"/>',
    bag: '<path d="M18 20c0-17 28-17 28 0M12 21h40l3 31H9z" fill="none" stroke="currentColor" stroke-width="5"/><path d="M10 32h44M25 26v12h14V26" fill="none" stroke="currentColor" stroke-width="3"/>',
  };
  const RARITY_NAMES = { common: 'Common', uncommon: 'Uncommon', rare: 'Rare', epic: 'Epic', legendary: 'Legendary' };
  const rarityName = i => RARITY_NAMES[i?.rarity] || 'Common';
  function icon(i, emptyKind) {
    const kind = i?.kind || emptyKind;
    const cell = i && window.ITEM_ICONS?.at[i.id];   // equipment has its own pixel icon (assets/items.png); everything else keeps the glyph
    if (cell) {
      const { cols, rows } = ITEM_ICONS;
      return `<span class="item-art" role="img" aria-hidden="true" data-icon="${i.id}" style="background-size:${cols * 100}% ${rows * 100}%;background-position:${cell[0] / (cols - 1) * 100}% ${cell[1] / (rows - 1) * 100}%"></span>`;
    }
    const glyph = kind === 'weapon' && i?.class === 'mage' ? 'staff' : kind === 'weapon' && i?.class === 'assassin' ? 'daggers' : kind === 'weapon' && i?.class === 'priest' ? 'mace' : kind === 'weapon' && i?.class === 'hunter' ? 'bow' : i?.id === 'ironhide_shell' ? 'shell' : kind;
    const palette = { slime_gel: '#88c675', blue_gel: '#6ca6ec', pink_gel: '#dd88b1', golden_gel: '#edc561', royal_jelly: '#bd84e2', traveler_stew: '#c98a4b', health_potion: '#e0476b' };
    const color = palette[i?.id] || (i?.variant === 'crimson' ? '#c16b67' : { uncommon: '#6fcf86', rare: '#86acd5', epic: '#b98be6', legendary: '#f0a85a' }[i?.rarity] || '#ab8e68');
    return `<svg viewBox="0 0 64 64" aria-hidden="true" style="color:${color}" stroke="#15151a" stroke-width="2" stroke-linejoin="round">${art[glyph] || art.accessory}</svg>`;
  }
  function summary(i, count = quantity(i.id)) {
    return `${i.name} ×${count} · ${i.rarity === 'common' ? '' : rarityName(i) + ' · '}${i.kind === 'material' ? 'Material' : consumable(i) ? `${i.kind === 'food' ? 'Food' : 'Potion'} · ${effect(i)}` : `${i.class || 'All classes'} · ${i.kind} · ${stats(i)}`} · ${i.starter ? 'Starter gear · cannot be sold' : `sells for ${i.sell} gold each`}${equippedCount(i) ? ` · Equipped ×${equippedCount(i)}` : ''}`;
  }
  function tooltip() {
    let t = $('item-tooltip'); if (!t) { t = node('div', '', 'item-tooltip'); t.id = 'item-tooltip'; t.role = 'tooltip'; t.hidden = true; document.body.append(t); } return t;
  }
  function hideTooltip() { if ($('item-tooltip')) $('item-tooltip').hidden = true; }
  function showTooltip(anchor, i, slot) {
    if (!i) return;
    const t = tooltip(); t.replaceChildren(node('b', i.name, 'item-name'), node('small', `${rarityName(i)} · ${i.class || (i.kind === 'material' ? 'Material' : consumable(i) ? 'Consumable' : 'All classes')}`)); t.dataset.rarity = i.rarity;
    if (consumable(i)) t.append(node('p', effect(i)));
    else if (i.kind !== 'material') t.append(node('p', `${slot ? slots.find(s => s[0] === slot)?.[1] : i.kind === 'armor' ? 'Chest' : i.kind === 'weapon' ? 'Hands' : i.kind} · ${stats(i)}`));
    if (i.class && i.class !== look?.class) t.append(node('p', `Requires ${i.class}`, 'item-restriction'));
    if (compatible(i) && !slot) {
      const target = slots.find(([s]) => slotKind(s) === i.kind)?.[0], current = target && itemAtSlot(target);
      if (current && current.id !== i.id) {
        const attack = (i.attack || 0) - (current.attack || 0), defense = (i.defense || 0) - (current.defense || 0);
        t.append(node('p', `Compared with ${current.name}: ${attack >= 0 ? '+' : ''}${attack} attack · ${defense >= 0 ? '+' : ''}${defense} defense`, 'item-comparison'));
      }
    }
    t.append(node('p', `${bagQuantity(i.id)} in bags · ${equippedCount(i)} equipped`), node('small', i.starter ? 'Starter gear · cannot be sold' : `Sells for ${i.sell} gold each`));
    t.append(node('small', consumable(i) ? 'Right-click or double-click to use · Z / X on the quick slots' : slot ? 'Right-click to unequip · Drag into a bag' : compatible(i) ? 'Right-click to equip · Drag onto a gear slot' : i.kind === 'material' ? 'Sell to Linden or Bram in Alderhaven' : 'Keep or sell to a merchant'));
    t.hidden = false;
    const r = anchor.getBoundingClientRect(), tr = t.getBoundingClientRect();
    t.style.left = Math.max(8, Math.min(innerWidth - tr.width - 8, r.right + 10)) + 'px';
    t.style.top = Math.max(8, Math.min(innerHeight - tr.height - 8, r.top)) + 'px';
    anchor.setAttribute('aria-describedby', t.id);
  }
  function attachTooltip(anchor, getItem, slot) {
    anchor.addEventListener('pointerenter', () => showTooltip(anchor, getItem(), slot));
    anchor.addEventListener('focus', () => showTooltip(anchor, getItem(), slot));
    anchor.addEventListener('pointerleave', hideTooltip); anchor.addEventListener('blur', hideTooltip);
  }
  function equip(i, slot) {
    if (!compatible(i) || !canEquip() || bagQuantity(i.id) < 1) return false;
    const targets = slots.filter(([s]) => slotKind(s) === i.kind).map(([s]) => s);
    slot ||= targets.find(s => !itemAtSlot(s)) || targets.find(s => itemAtSlot(s)?.id !== i.id) || targets[0];
    if (!slot || slotKind(slot) !== i.kind) return false;
    return Field.equipSlot(slot, i.id);
  }
  function unequip(slot) { return canEquip() && !!itemAtSlot(slot) && Field.equipSlot(slot, 'none'); }
  function readDrag(event) { try { return JSON.parse(event.dataTransfer.getData(dragType)); } catch (_) { return null; } }
  function dragSource(element, data) {
    element.draggable = true;
    element.addEventListener('dragstart', event => { hideTooltip(); event.dataTransfer.setData(dragType, JSON.stringify(data())); event.dataTransfer.effectAllowed = 'move'; });
  }
  function dropTarget(element, action) {
    element.addEventListener('dragover', event => { if (event.dataTransfer.types.includes(dragType)) { event.preventDefault(); element.classList.add('drop-ready'); } });
    element.addEventListener('dragleave', () => element.classList.remove('drop-ready'));
    element.addEventListener('drop', event => { event.preventDefault(); element.classList.remove('drop-ready'); const data = readDrag(event); if (data && canEquip()) action(data); });
  }
  function reconcile() {
    const nextCharacter = Online.currentToken || look?.class;
    if (nextCharacter !== character) {
      character = nextCharacter; activeBag = 0; selected = null; search = ''; if ($('bag-search')) $('bag-search').value = '';
      layout = Array.isArray(Online.bagLayout) ? Online.bagLayout.slice(0, 1024) : [];
    }
    layout = layout.slice(0, capacity()); while (layout.length < capacity()) layout.push(null);
    const before = JSON.stringify(layout), seen = new Set();
    layout = layout.map(id => { if (typeof id !== 'string' || !definition(id) || !bagQuantity(id) || seen.has(id)) return null; seen.add(id); return id; });
    for (const s of stacks) if (bagQuantity(s.item) && !seen.has(s.item)) {
      let index = layout.indexOf(null); if (index >= 0) { layout[index] = s.item; seen.add(s.item); }
    }
    if (pendingPlacement && Date.now() < pendingPlacement.until && bagQuantity(pendingPlacement.item)) {
      const oldIndex = layout.indexOf(pendingPlacement.item), index = pendingPlacement.index;
      if (index >= layout.length) pendingPlacement.index = layout.length - 1;
      [layout[oldIndex], layout[pendingPlacement.index]] = [layout[pendingPlacement.index], layout[oldIndex]]; pendingPlacement = null;
    }
    if (pendingPlacement && Date.now() >= pendingPlacement.until) pendingPlacement = null;
    if (JSON.stringify(layout) !== before) Online.saveBagLayout?.(layout);
    activeBag = Math.min(activeBag, bagPages().length - 1);
  }
  function moveToBag(data, index) {
    if (search || index < 0 || index >= capacity()) return;
    if (data.from === 'equipment') {
      if (itemAtSlot(data.slot)?.id !== data.item) return;
      pendingPlacement = { item: data.item, index, until: Date.now() + 3000 }; unequip(data.slot); return;
    }
    if (data.from !== 'bag' || !bagQuantity(data.item)) return;
    const from = layout.indexOf(data.item); if (from < 0) return;
    [layout[from], layout[index]] = [layout[index], layout[from]];
    Online.saveBagLayout?.(layout); render($('inventory-list'));
  }
  function renderDetails() {
    const container = $('bag-details'); if (!container) return;
    const i = selected && definition(selected);
    container.replaceChildren();
    if (!i || !bagQuantity(i.id)) { container.append(node('p', 'Select an item to inspect it.', 'bag-empty-note')); return; }
    const heading = node('b', i.name, 'item-name'); heading.dataset.rarity = i.rarity;
    container.append(heading, node('small', summary(i, bagQuantity(i.id))));
    if (compatible(i)) {
      const targets = slots.filter(([s]) => slotKind(s) === i.kind && itemAtSlot(s)?.id !== i.id);
      for (const [slot, label] of targets) {
        const b = button(i.kind === 'accessory' ? `Equip · ${label}` : 'Equip', () => equip(i, slot), 'item-action'); b.dataset.action = 'equip'; b.disabled = !canEquip(); container.append(b);
      }
    } else if (consumable(i)) {
      const b = button('Use', () => useItem(i), 'item-action'); b.dataset.action = 'use'; b.disabled = !canEquip(); container.append(b);
      container.append(node('p', effect(i), 'bag-empty-note'));
    } else if (i.class && i.class !== look?.class) container.append(node('p', `Requires ${i.class}`, 'item-restriction'));
    else container.append(node('p', 'Sell materials to Linden or Bram in Alderhaven.', 'bag-empty-note'));
  }
  function render(container) {
    if (!container) return;
    reconcile(); hideTooltip();
    const focusItem = container.contains(document.activeElement) ? document.activeElement?.closest('[data-item]')?.dataset.item : null;
    container.replaceChildren();
    const pages = bagPages(), page = pages[activeBag];
    let positions = Array.from({ length: page.size }, (_, n) => page.start + n);
    if (search) positions = layout.map((id, index) => ({ id, index })).filter(({ id }) => id && summary(definition(id)).toLowerCase().includes(search)).map(({ index }) => index);
    for (const index of positions) {
      const i = definition(layout[index]), count = i ? bagQuantity(i.id) : 0;
      const cell = node('div', '', 'bag-cell'); cell.dataset.position = index;
      dropTarget(cell, data => moveToBag(data, index));
      if (i && count) {
        cell.classList.add('inventory-item'); cell.dataset.item = i.id; cell.dataset.rarity = i.rarity;
        const b = button('', () => { selected = i.id; renderDetails(); for (const n of container.querySelectorAll('.item-tile')) n.setAttribute('aria-pressed', String(n.closest('[data-item]').dataset.item === selected)); }, 'item-tile');
        b.setAttribute('aria-label', summary(i, count)); b.setAttribute('aria-pressed', String(selected === i.id));
        b.innerHTML = icon(i); b.append(node('span', String(count), 'item-stack'));
        b.append(node('b', i.name, 'sr-only'), node('small', summary(i, count), 'sr-only'));
        b.addEventListener('contextmenu', event => { event.preventDefault(); selected = i.id; activate(i); renderDetails(); });
        b.addEventListener('dblclick', () => activate(i)); attachTooltip(b, () => definition(i.id));
        dragSource(b, () => ({ from: 'bag', item: i.id })); cell.append(b);
      } else {
        cell.classList.add('bag-cell-empty'); cell.setAttribute('aria-label', `Empty bag slot ${index - page.start + 1}`);
      }
      container.append(cell);
    }
    if (search && !positions.length) container.append(node('p', 'No matching items.', 'bag-empty-note'));
    if ($('bag-tabs')) {
      $('bag-tabs').replaceChildren(...Array.from({ length: 5 }, (_, index) => {
        const bag = pages[index], used = bag ? layout.slice(bag.start, bag.start + bag.size).filter(Boolean).length : 0;
        const b = button('', () => { if (!bag) { $('bag-details').replaceChildren(node('b', 'Empty bag slot', 'item-name'), node('p', 'Buy a six-slot Linen Satchel for 500 gold from Linden in Alderhaven.', 'bag-empty-note')); return; } activeBag = index; search = ''; $('bag-search').value = ''; render(container); }, 'bag-tab');
        b.innerHTML = icon(null, 'bag'); b.append(node('span', bag ? `${used}/${bag.size}` : '+')); b.dataset.bag = index; b.dataset.locked = String(!bag);
        b.setAttribute('aria-label', bag ? `${bag.name}, ${used} of ${bag.size} slots` : `Empty expansion bag slot ${index}`); b.setAttribute('aria-pressed', String(index === activeBag));
        if (bag) dropTarget(b, data => { const empty = layout.slice(bag.start, bag.start + bag.size).indexOf(null); if (empty >= 0) { search = ''; $('bag-search').value = ''; activeBag = index; moveToBag(data, bag.start + empty); } });
        return b;
      }));
    }
    if ($('bag-title')) $('bag-title').textContent = search ? 'Search All Bags' : page.name;
    if ($('bag-capacity')) $('bag-capacity').textContent = `${layout.filter(Boolean).length}/${capacity()} slots · ${layout.filter(id => !id).length} free`;
    if ($('bag-gold')) $('bag-gold').textContent = `${Field.hero?.gold || 0} gold`;
    if ($('bag-capacity')) $('bag-capacity').classList.toggle('bags-full', !layout.includes(null));
    if ($('inventory-open')) $('inventory-open').title = `Bags · ${layout.filter(Boolean).length} stacks · B / I`;
    renderDetails();
    if (focusItem) container.querySelector(`[data-item="${focusItem}"] button`)?.focus({ preventScroll: true });
  }
  function shopRow(s) {
    const i = definition(s.item), n = node('article', '', 'inventory-item shop-item'); n.dataset.item = i.id; n.dataset.rarity = i.rarity;
    const glyph = node('span', '', 'shop-item-icon'); glyph.innerHTML = icon(i); n.append(glyph, node('b', `${i.name} ×${s.quantity}`), node('small', summary(i))); attachTooltip(n, () => i); return n;
  }
  function renderShop(npc, container) {
    container.replaceChildren(); if (!npc.buys) return;
    container.append(node('h4', 'Sell from your bags'), node('p', 'Equipped copies are kept. Starter gear cannot be sold.'));
    const sell = (offer, b) => { if (Online.send({ type: 'interact', npc: npc.id, offer })) b.disabled = true; };
    const materials = stacks.filter(s => definition(s.item)?.kind === 'material');
    if (materials.length) {
      const value = materials.reduce((sum, s) => sum + s.quantity * definition(s.item).sell, 0);
      const b = button(`Sell all materials · ${value} gold`, () => sell('sell:materials', b)); b.dataset.sell = 'materials'; container.append(b);
    }
    for (const s of stacks) {
      const count = spare(s); if (count <= 0) continue;
      const i = definition(s.item), n = shopRow(s);
      const b = button(`Sell 1 · ${i.sell} gold`, () => sell(`sell:${i.id}:1`, b)); b.dataset.sell = 'one'; n.append(b);
      if (count > 1) { const b = button(`Sell ${count} · ${count * i.sell} gold`, () => sell(`sell:${i.id}:${count}`, b)); b.dataset.sell = 'stack'; n.append(b); }
      container.append(n);
    }
    if (!stacks.some(s => spare(s) > 0)) container.append(node('p', 'No spare items to sell. Bring back loot from the meadow.'));
  }
  function renderEquipped(container) {
    if (!look) return;
    if (container.dataset.class !== look.class) { container.replaceChildren(); container.dataset.class = look.class; }
    for (const [slot, label] of slots) {
      const kind = slotKind(slot), legacy = slot === 'chest' || slot === 'hands', i = itemAtSlot(slot);
      let card = container.querySelector(`[data-slot="${slot}"]`);
      if (!card) {
        card = node('article', '', 'equipped-slot'); card.dataset.slot = slot;
        const select = node('select'); select.id = legacy ? 'field-' + look.class + (slot === 'chest' ? 'Armor' : 'Weapon') : 'field-' + slot; select.setAttribute('aria-label', label);
        select.addEventListener('change', () => { if (legacy) Field.equip({ [look.class + (slot === 'chest' ? 'Armor' : 'Weapon')]: select.value }); else Field.equipSlot(slot, select.value); select.value = card.dataset.value; });
        const title = node('label', label.toUpperCase(), 'sr-only'); title.htmlFor = select.id;
        const glyph = button('', () => { if (itemAtSlot(slot)) { selected = itemAtSlot(slot).id; renderDetails(); } select.focus(); try { select.showPicker?.(); } catch (_) {} }, 'gear-icon');
        attachTooltip(glyph, () => itemAtSlot(slot), slot);
        glyph.addEventListener('contextmenu', event => { event.preventDefault(); unequip(slot); });
        attachTooltip(select, () => itemAtSlot(slot), slot);
        select.addEventListener('contextmenu', event => { event.preventDefault(); unequip(slot); });
        dragSource(glyph, () => ({ from: 'equipment', slot, item: itemAtSlot(slot)?.id }));
        dropTarget(card, data => {
          const item = definition(data.item); if (!compatible(item) || item.kind !== kind) return;
          if (data.from === 'equipment' && data.slot !== slot && itemAtSlot(data.slot)?.id === data.item && slotKind(data.slot) === kind) {
            const other = itemAtSlot(slot); Online.send({ type: 'equip', slots: { [data.slot]: other?.id || 'none', [slot]: item.id } });
          } else if (data.from === 'bag') equip(item, slot);
        });
        card.append(title, glyph, node('b', '', 'sr-only'), node('span', label, 'gear-label'), select); container.append(card);
      }
      card.dataset.rarity = i?.rarity || 'common'; card.dataset.empty = String(!i);
      card.querySelector('b').textContent = i?.name || 'Empty slot';
      const glyph = card.querySelector('.gear-icon'); glyph.innerHTML = icon(i, kind); glyph.draggable = !!i; glyph.setAttribute('aria-label', `${label}: ${i?.name || 'Empty'}. Right-click to unequip.`);
      const select = card.querySelector('select'), owned = WORLD_ITEMS.filter(item => item.kind === kind && compatible(item) && quantity(item.id) > 0);
      const options = [['none', 'None'], ...owned.map(item => [legacy ? item.variant : item.id, item.name])], key = JSON.stringify(options);
      if (select.dataset.options !== key) { select.replaceChildren(...options.map(([value, name]) => { const o = node('option', name); o.value = value; return o; })); select.dataset.options = key; }
      select.value = i ? (legacy ? i.variant : i.id) : 'none'; card.dataset.value = select.value; select.disabled = !canEquip(); glyph.disabled = !canEquip();
    }
  }
  $('bag-search')?.addEventListener('input', event => { search = event.target.value.trim().toLowerCase(); render($('inventory-list')); });
  $('bag-sort')?.addEventListener('click', () => { reconcile(); const ids = layout.filter(Boolean).sort((a, b) => definition(a).kind.localeCompare(definition(b).kind) || definition(a).name.localeCompare(definition(b).name)); layout = ids; while (layout.length < capacity()) layout.push(null); activeBag = 0; Online.saveBagLayout?.(layout); render($('inventory-list')); });
  window.Inventory = { quantity, bagQuantity, effect, render, renderShop, renderEquipped, hideTooltip,
    update(next, nextLook, nextSlots = {}, nextBags = []) {
      const key = JSON.stringify([next, nextLook, nextSlots, nextBags]); if (key === signature) return;
      stacks = next; look = nextLook; gearSlots = nextSlots; bags = nextBags; signature = key;
      reconcile(); hideTooltip(); dispatchEvent(new Event('inventory-change')); window.City?.refreshInventory();
    },
  };
})();
