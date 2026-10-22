'use strict';
// The inspect window: another character's look, worn gear and stat sheet. Everything shown is what the server's
// `inspect` answer carries (server/src/world/inspect.rs); the window asks again every few seconds while it is open.
(() => {
  const $ = id => document.getElementById(id);
  const panel = $('inspect-panel');
  if (!panel) return;
  const REFRESH = 3000;
  const SLOTS = [['headgear', 'Headgear'], ['shoulders', 'Shoulders'], ['chest', 'Chest'], ['pants', 'Pants'], ['gloves', 'Gloves'], ['hands', 'Hands'], ['necklace', 'Necklace'], ['accessory1', 'Accessory 1'], ['accessory2', 'Accessory 2']];
  const KIND = { chest: 'armor', hands: 'weapon', accessory1: 'accessory', accessory2: 'accessory' };
  const RARITY = { common: 'Common', uncommon: 'Uncommon', rare: 'Rare', epic: 'Epic', legendary: 'Legendary', gm: 'Game Master' };
  const ATTRIBUTES = ['strength', 'agility', 'intellect', 'stamina', 'dexterity', 'accuracy'];
  const tr = text => window.Locale ? Locale.translate(text) : text;
  const catalog = id => (window.WORLD_ITEMS || []).find(i => i.id === id);
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  let target = null, timer = 0, opener = null, generation = 0, lookKey = '', sprite = null, answer = null, shown = '';

  function send() { if (target && Online.connected) Online.send({ type: 'inspect', id: target.id }); }
  function tip() {
    let t = $('inspect-tip');
    if (!t) { t = node('div', null, 'item-tooltip'); t.id = 'inspect-tip'; t.setAttribute('role', 'tooltip'); t.hidden = true; document.body.append(t); }
    return t;
  }
  const hideTip = () => { if ($('inspect-tip')) $('inspect-tip').hidden = true; };
  function stats(piece) {
    const b = piece.bonus || {}, num = n => Number(n.toFixed(1));
    return [piece.attack ? `+${num(piece.attack)} attack` : '', piece.defense ? `${num(piece.defense)} defense` : '',
      ...ATTRIBUTES.filter(k => b[k]).map(k => `+${b[k]} ${k}`)].filter(Boolean).join(' · ');
  }
  function showTip(anchor, piece) {
    const t = tip(), rarity = piece.rarity || 'common';
    t.replaceChildren(node('b', piece.name, 'item-name'), node('small', `${tr(RARITY[rarity] || 'Common')} · ${piece.class ? piece.class : tr('All classes')}`));
    t.dataset.rarity = rarity;
    t.append(node('p', stats(piece) || tr('No bonuses')));
    t.append(node('small', `${tr('Requires level')} ${piece.level}${piece.rank ? ` · ${tr('Rank')} ${piece.rank}` : ''}${piece.usable ? '' : ` · ${tr('Cannot be used yet')}`}`));
    t.hidden = false;
    const a = anchor.getBoundingClientRect(), w = t.getBoundingClientRect();
    t.style.left = `${Math.max(4, Math.min(innerWidth - w.width - 4, a.left + a.width / 2 - w.width / 2))}px`;
    t.style.top = `${a.top - w.height - 6 < 4 ? a.bottom + 6 : a.top - w.height - 6}px`;
  }

  function drawFigure(look) {
    const key = JSON.stringify(look), canvas = $('inspect-cv'), mine = ++generation;
    if (key === lookKey && sprite) return;
    lookKey = key;
    const paint = () => {
      canvas.width = 320; canvas.height = 420;
      const g = canvas.getContext('2d'); g.clearRect(0, 0, 320, 420);
      if (sprite) { g.translate(160, 365); sprite.draw(g, { fx: 1, fy: 1, walk: 0 }, 0, 2.8); }
    };
    sprite = null; paint();
    window.Field?.loadSprite(look).then(s => { if (mine === generation) { sprite = s; paint(); } }).catch(() => {});
  }

  function renderSlots(slots) {
    const holder = $('inspect-slots'); holder.replaceChildren();
    for (const [slot, label] of SLOTS) {
      const piece = slots.find(s => s.slot === slot), card = node('article', null, 'equipped-slot');
      card.dataset.slot = slot; card.dataset.rarity = piece?.rarity || 'common'; card.dataset.empty = String(!piece);
      const glyph = node('button', null, 'gear-icon'); glyph.type = 'button';
      glyph.innerHTML = window.Inventory ? Inventory.icon(piece ? catalog(piece.item) : null, KIND[slot] || slot) : '';
      glyph.setAttribute('aria-label', `${tr(label)}: ${piece ? `${piece.name}, ${tr(RARITY[piece.rarity] || 'Common')}, ${stats(piece)}` : tr('Empty')}`);
      if (piece) {
        glyph.addEventListener('pointerenter', () => showTip(glyph, piece)); glyph.addEventListener('focus', () => showTip(glyph, piece));
        glyph.addEventListener('pointerleave', hideTip); glyph.addEventListener('blur', hideTip);
      }
      card.append(glyph, node('small', tr(label), 'inspect-slot-label'), node('span', piece ? piece.name : tr('Empty'), 'inspect-slot-item'));
      holder.append(card);
    }
  }
  function renderStats(a) {
    const s = a.stats, pct = v => `${Math.round(v * 1000) / 10}%`, num = v => Number(v.toFixed(1));
    const rows = [
      ['Health', Math.round(s.hp)], [s.resourceType[0].toUpperCase() + s.resourceType.slice(1), Math.round(s.resource)],
      ['Attack', num(s.attack)], ['Defense', num(s.defense)],
      ['Hit chance', pct(s.hitChance)], ['Dodge chance', pct(s.dodgeChance)], ['Critical chance', pct(s.critChance)], ['Cooldown reduction', pct(s.cooldownReduction)],
    ];
    const list = $('inspect-stats'); list.replaceChildren();
    for (const [name, value] of rows) list.append(node('dt', tr(name)), node('dd', String(value)));
    const attrs = $('inspect-attributes'); attrs.replaceChildren();
    for (const k of ATTRIBUTES) {
      const total = (s.attributes[k] || 0) + (s.gearAttributes[k] || 0) + (s.passiveAttributes[k] || 0);
      attrs.append(node('dt', tr(k[0].toUpperCase() + k.slice(1))), node('dd', String(total)));
    }
    const sets = $('inspect-sets'); sets.replaceChildren();
    const counts = Object.entries(a.setCounts || {}).filter(([, n]) => n > 0);
    sets.hidden = !counts.length;
    if (counts.length) { sets.append(node('h4', tr('Set bonuses'))); for (const [name, n] of counts) sets.append(node('p', `${name.replace(/_/g, ' ')} · ${n}`)); }
  }
  function render() {
    const a = answer;
    $('inspect-note').hidden = !!(a && a.ok);
    $('inspect-body').hidden = !(a && a.ok);
    if (!a) { $('inspect-note').textContent = tr('Looking…'); return; }
    if (!a.ok) { $('inspect-note').textContent = tr('No longer nearby'); return; }
    $('inspect-title').textContent = a.name;
    const cls = a.look.class[0].toUpperCase() + a.look.class.slice(1);
    $('inspect-subtitle').textContent = `${tr('Level')} ${a.level} ${cls}${a.reborn?.count ? ` · ${tr('Reborn')} ×${a.reborn.count}` : ''}${a.hired ? ` · ${tr('Hired fighter')}` : ''}`;
    // The refresh brings the same answer most of the time: keep the nodes, so a hovered or focused slot stays put.
    const key = JSON.stringify(a);
    if (key === shown) return;
    shown = key;
    drawFigure(a.look); renderSlots(a.slots); renderStats(a);
  }

  function open(id, name) {
    if (!id || !Online.connected) return;
    opener = document.activeElement; target = { id, name }; answer = null; shown = '';
    $('inspect-title').textContent = name || tr('Inspect'); $('inspect-subtitle').textContent = '';
    render(); panel.hidden = false; send();
    clearInterval(timer); timer = setInterval(send, REFRESH);
    $('inspect-close').focus({ preventScroll: true });
  }
  function close() {
    if (panel.hidden) return;
    panel.hidden = true; clearInterval(timer); timer = 0; target = null; answer = null; shown = ''; hideTip();
    if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
    opener = null;
  }
  $('inspect-close').addEventListener('click', close);
  panel.addEventListener('pointerdown', event => { if (event.target === panel) close(); });
  panel.addEventListener('keydown', event => {
    event.stopPropagation();            // no walking or attacking behind the window
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    else if (event.key === 'Tab') {
      const focusable = [...panel.querySelectorAll('button')].filter(b => !b.closest('[hidden]'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  window.Inspect = {
    open, close,
    onPacket(packet) {
      if (!target || packet.id !== target.id) return;
      answer = packet; render();
    },
    reset() { close(); },
    get isOpen() { return !panel.hidden; },
  };
})();
