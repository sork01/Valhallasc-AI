'use strict';
// Quick slots: Z food, X health potion, C mana potion (mana classes). They only send
// "use this item"; the server owns ownership, the one-meal rule, the 60 s potion cooldown and the healing.
(() => {
  const $ = id => document.getElementById(id);
  const KINDS = [{ kind: 'food', key: 'z', name: 'Food', empty: 'No food · buy Traveler\'s Stew from Pip in Alderhaven' }, { kind: 'potion', key: 'x', name: 'Potion', empty: 'No potion · buy Health Potions from Mira Moonleaf in Alderhaven' }, { kind: 'mana', key: 'c', name: 'Mana', empty: 'No mana potion · buy from a potion merchant' }];
  const best = kind => WORLD_ITEMS.filter(i => (kind === 'mana' ? i.kind === 'potion' && i.mana > 0 : i.kind === kind && (kind !== 'potion' || i.heal > 0)) && Inventory.quantity(i.id) > 0 && (i.requiredLevel || 1) <= (Field.hero.level || 1)).sort((a, b) => kind === 'mana' ? b.mana - a.mana : (b.heal || 0) - (a.heal || 0))[0];
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n; };
  const slots = new Map();
  function use(kind) {
    const i = best(kind);
    if (!i) { Field.floatHero(kind === 'food' ? 'No food' : 'No potion', '#ffb0a0'); return false; }
    return Field.useItem(i.id);
  }
  function build() {
    for (const k of KINDS) {
      const b = node('button', '', 'skill-slot quick-slot'); b.type = 'button'; b.dataset.kind = k.kind; b.dataset.item = ''; b.setAttribute('aria-keyshortcuts', k.key.toUpperCase());
      const glyph = node('span', '', 'skill-icon'); glyph.innerHTML = Skillbar.icon(k.kind === 'mana' ? 'potion' : k.kind);
      b.append(node('kbd', k.key.toUpperCase()), glyph, node('span', k.name, 'skill-name'), node('span', '', 'quick-count'), node('span', '', 'skill-cooldown'));
      b.addEventListener('click', () => use(k.kind));
      slots.set(k.kind, b); $('quickuse').append(b);
    }
  }
  // Seconds left before the slot works again, and how long that wait was in all.
  function wait(kind, item) {
    if (kind === 'food') { const meal = (Field.hero.buffs || []).find(b => b.kind === 'regen'); return meal ? [meal.left, meal.time] : [0, 1]; }
    return [Field.hero.potionCd || 0, item?.cooldown || 60];
  }
  function update() {
    if (!slots.size) build();
    for (const k of KINDS) {
      const b = slots.get(k.kind); b.hidden = k.kind === 'mana' && Field.hero.resourceType !== 'mana';
      const i = best(k.kind), [left, total] = wait(k.kind, i);
      b.dataset.item = i?.id || '';
      b.disabled = !Field.canAct || (!!i && left > 0);
      b.classList.toggle('on-cooldown', !!i && left > 0);
      b.style.setProperty('--cooldown', i ? Math.min(1, left / total) : 0);
      b.querySelector('.skill-cooldown').textContent = i && left > 0 ? Math.ceil(left) : '';
      b.querySelector('.quick-count').textContent = i ? Inventory.quantity(i.id) : '';
      b.querySelector('.skill-name').textContent = i ? i.name : k.name;
      b.setAttribute('aria-label', i ? `${k.name} slot ${k.key.toUpperCase()}: ${i.name} ×${Inventory.quantity(i.id)}` : `${k.name} slot ${k.key.toUpperCase()}: empty`);
      b.title = i ? `${k.key.toUpperCase()} · ${i.name} ×${Inventory.quantity(i.id)}\n${Inventory.effect(i)}` : k.empty;
    }
  }
  addEventListener('keydown', event => {
    if ($('scene-game').hidden || event.repeat || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName || '') || event.ctrlKey || event.altKey || event.metaKey) return;
    const slot = KINDS.find(k => k.key === event.key.toLowerCase());
    if (!slot || !Field.canAct || (slot.kind === 'mana' && Field.hero.resourceType !== 'mana')) return;
    event.preventDefault(); use(slot.kind);
  });
  window.Quickuse = { update, use };
})();
