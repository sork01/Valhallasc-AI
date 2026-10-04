'use strict';
// Party loot rolls. The server (server/src/world/rolls.rs) decides who may roll and who wins; this file shows one
// card per open roll with Need / Greed / Pass and a countdown. Item names come from the catalog, never from markup.
(() => {
  const $ = id => document.getElementById(id);
  const COLOURS = { uncommon: '#4ad66d', rare: '#4aa3ff', epic: '#b45cff', legendary: '#ff9a2e' };
  const cards = new Map();
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  const num = n => Number(n.toFixed(1));
  function summary(i) {
    const stats = [i.attack ? `+${num(i.attack)} attack` : '', i.defense ? `${num(i.defense)} defense` : ''].filter(Boolean).join(' · ');
    return `${i.class || 'All classes'} · ${i.kind} · level ${i.requiredLevel || 1}${stats ? ` · ${stats}` : ''}`;
  }
  function remove(id) {
    const card = cards.get(id); if (!card) return;
    clearInterval(card.timer); card.node.remove(); cards.delete(id);
  }
  function start(packet) {
    if (cards.has(packet.id)) return;
    const holder = $('loot-rolls'); if (!holder) return;
    const item = window.WORLD_ITEMS?.find(i => i.id === packet.item) || { name: packet.item, rarity: 'uncommon', kind: 'gear' };
    const node = el('div', '', 'roll-card'); node.dataset.roll = packet.id; node.dataset.rarity = item.rarity;
    node.setAttribute('role', 'group'); node.setAttribute('aria-label', `Loot roll: ${item.name}`);
    const name = el('b', item.name, 'roll-name'); name.style.color = COLOURS[item.rarity] || '#fff';
    const time = el('span', '', 'roll-time');
    const head = el('div', '', 'roll-head'); head.append(name, time);
    const buttons = el('div', '', 'roll-buttons');
    const make = (label, choice, title) => {
      const b = el('button', label, `roll-${choice}`); b.type = 'button'; b.dataset.choice = choice; b.title = title;
      b.addEventListener('click', () => {
        for (const other of buttons.children) other.disabled = true;
        Online.send({ type: 'roll', id: packet.id, choice });
      });
      return b;
    };
    const need = make('Need', 'need', packet.need ? 'Your class can wear this piece' : 'Your class cannot use this piece');
    need.disabled = !packet.need;
    buttons.append(need, make('Greed', 'greed', 'Roll for the gold value'), make('Pass', 'pass', 'Give it up'));
    node.append(head, el('small', summary(item), 'roll-stats'), buttons);
    const ends = Date.now() + packet.seconds * 1000;
    const tick = () => { time.textContent = `${Math.max(0, Math.ceil((ends - Date.now()) / 1000))}s`; };
    tick();
    cards.set(packet.id, { node, timer: setInterval(tick, 500), need: !!packet.need, buttons });
    holder.append(node);
  }
  window.Rolls = {
    onPacket(packet) {
      if (packet.op === 'start') start(packet);
      else if (packet.op === 'voted' || packet.op === 'end') remove(packet.id);
    },
    // A refused vote (the server sent an error) leaves the card open and its buttons usable again.
    reopen() { for (const c of cards.values()) for (const b of c.buttons.children) b.disabled = b.dataset.choice === 'need' && !c.need; },
    reset() { for (const id of [...cards.keys()]) remove(id); },
  };
})();
