'use strict';
// Slot choices are cosmetic. Inventory receives equippedLook, while scene/preview sprites receive the visible look.
(() => {
  const SLOTS = [['chest', 'Chest'], ['hands', 'Hands'], ['headgear', 'Headgear'], ['shoulders', 'Shoulders'], ['gloves', 'Gloves'], ['pants', 'Pants'], ['cloak', 'Cloak']];
  const HIDE = ['headgear', 'shoulders', 'cloak'];
  const kind = s => s === 'chest' ? 'armor' : s === 'hands' ? 'weapon' : s;
  const field = (s, look) => s === 'chest' ? look.class + 'Armor' : s === 'hands' ? look.class + 'Weapon' : s === 'headgear' ? 'head' : s;
  const tr = s => window.Locale?.translate(s) || s;
  const item = id => window.Inventory?.definition(id) || (window.WORLD_ITEMS || []).find(i => i.id === id);
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = tr(text); if (cls) n.className = cls; return n; };
  const eligible = (i, slot, look, gm) => i && i.kind === kind(slot) && i.variant && (!i.class || i.class === look.class) && (i.rarity !== 'gm' || gm);
  function preview(look, equipment, choices) {
    const next = { ...look };
    for (const [slot] of SLOTS) {
      const key = field(slot, look), id = choices[slot];
      const worn = ['chest', 'hands'].includes(slot) ? look[key] && look[key] !== 'none' : equipment[slot] && equipment[slot] !== 'none';
      if (!worn || !id || id === 'real') continue;
      if (id === 'hide' && HIDE.includes(slot)) next[key] = 'none';
      else if (eligible(item(id), slot, look, true)) next[key] = item(id).variant;
    }
    return next;
  }
  function changes(saved, selected) {
    return Object.fromEntries(SLOTS.map(([s]) => [s, selected[s] || 'real']).filter(([s, id]) => id !== (saved[s] || 'real')));
  }
  const fee = (diff, price) => Object.values(diff).filter(id => id !== 'real').length * price;
  function description(id) {
    if (!id || id === 'real') return '';
    if (id === 'hide') return tr('Appearance: Hidden');
    const name = item(id)?.name;
    return name ? tr(`Transmogrified to: ${name}`) : '';
  }
  function mark(glyph, id) {
    const note = description(id);
    if (note) { glyph.dataset.transmog = id; glyph.dataset.appearance = note; }
    else { delete glyph.dataset.transmog; delete glyph.dataset.appearance; }
  }
  let key = '', packet = null, selected = {}, host = null, sprite = null, generation = 0, raf = 0, sending = false;
  function stop() { cancelAnimationFrame(raf); raf = 0; }
  function close() { key = ''; host = null; packet = null; sprite = null; generation++; sending = false; stop(); }
  function paint(time) {
    const cv = host?.querySelector('canvas'); if (!cv || !sprite) return;
    const g = cv.getContext('2d'); g.clearRect(0, 0, cv.width, cv.height); g.save();
    g.translate(cv.width / 2, cv.height - 25); sprite.draw(g, { fx: 1, fy: 1, walk: 0 }, time / 1000, 2.1); g.restore();
  }
  function updatePreview() {
    const mine = ++generation;
    stop(); sprite = null;
    const cv = host?.querySelector('canvas'); cv?.getContext('2d').clearRect(0, 0, cv.width, cv.height);
    const look = preview(packet.look, packet.equipment || {}, selected);
    window.Field?.loadSprite(look).then(s => {
      if (mine !== generation || !host) return;
      sprite = s; let last = 0;
      const frame = t => {
        if (!host?.isConnected || host.closest('[hidden]')) { stop(); return; }
        raf = requestAnimationFrame(frame);
        if (t - last >= 33) { last = t; paint(t); }
      };
      raf = requestAnimationFrame(frame);
    }).catch(() => {});
  }
  function render(npc, next, container) {
    const signature = JSON.stringify([npc.id, next.transmogs, next.look, next.equipment, next.wardrobe, next.transmogPrice]);
    if (signature !== key) { key = signature; selected = { ...(next.transmogs || {}) }; }
    packet = next; host = container; sending = false;
    const form = node('div', null, 'transmog-layout'), controls = node('div', null, 'transmog-controls');
    const figure = node('div', null, 'transmog-figure'), cv = node('canvas'); cv.width = 240; cv.height = 320;
    cv.setAttribute('aria-label', tr('Appearance preview')); figure.append(cv);
    controls.append(node('h4', 'Transmogrify'), node('p', 'Choose appearances for your equipment slots. Upgrades keep the chosen look. Empty slots show nothing.'));
    const price = node('p'); price.innerHTML = tr('Price per changed slot:') + ' ' + Money.html(next.transmogPrice || 0); controls.append(price);
    const search = node('input'); search.type = 'search'; search.placeholder = tr('Search unlocked appearances'); search.setAttribute('aria-label', search.placeholder); controls.append(search);
    const list = node('div', null, 'transmog-slots'); controls.append(list);
    const quote = node('p', null, 'transmog-total'), apply = node('button', 'Apply appearances', 'gossip-button'); apply.type = 'button'; apply.dataset.action = 'transmog-apply';
    function updateQuote() {
      const diff = changes(next.transmogs || {}, selected), cost = fee(diff, next.transmogPrice || 0);
      quote.innerHTML = tr('Total fee:') + ' ' + Money.html(cost) + ' · ' + tr('Your purse:') + ' ' + Money.html(next.gold || 0);
      apply.disabled = sending || !Object.keys(diff).length || cost > (next.gold || 0);
      quote.dataset.cost = String(cost);
    }
    const unlocked = (next.wardrobe || []).map(item).filter(Boolean);
    function renderChoices() {
      list.replaceChildren(); const query = search.value.trim().toLocaleLowerCase();
      for (const [slot, label] of SLOTS) {
        const row = node('label', null, 'transmog-slot'); row.append(node('span', label));
        const select = node('select'); select.dataset.slot = slot; select.setAttribute('aria-label', tr(label));
        function option(value, label) { const n = node('option', label); n.value = value; select.append(n); }
        option('real', 'Real appearance (free)'); if (HIDE.includes(slot)) option('hide', 'Hide');
        for (const i of unlocked.filter(i => eligible(i, slot, next.look, next.gm)).sort((a, b) => tr(a.name).localeCompare(tr(b.name)))) {
          if (i.id !== selected[slot] && query && !tr(i.name).toLocaleLowerCase().includes(query)) continue;
          option(i.id, i.name);
        }
        select.value = selected[slot] || 'real';
        select.addEventListener('change', () => { selected[slot] = select.value; updateQuote(); updatePreview(); });
        row.append(select); list.append(row);
      }
    }
    search.addEventListener('input', renderChoices);
    apply.addEventListener('click', () => {
      if (apply.disabled) return;
      if (Online.send({ type: 'transmogrify', npc: npc.id, changes: changes(next.transmogs || {}, selected) })) {
        sending = true; updateQuote();
      }
    });
    controls.append(quote, apply); form.append(figure, controls); container.replaceChildren(form);
    container.className = 'transmog-workshop'; renderChoices(); updateQuote(); updatePreview();
  }
  // A refusal must allow correcting/retrying the draft without discarding it.
  function error() {
    sending = false;
    const b = host?.querySelector('button');
    if (b && packet) {
      const diff = changes(packet.transmogs || {}, selected);
      b.disabled = !Object.keys(diff).length || fee(diff, packet.transmogPrice || 0) > (packet.gold || 0);
    }
  }
  window.Transmog = { render, close, error, preview, eligible, changes, fee, description, mark };
})();
