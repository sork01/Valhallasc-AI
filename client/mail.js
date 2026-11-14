'use strict';
// UI for persisted mail escrow. Only authoritative replies change inventory or letters.
(() => {
  const $ = id => document.getElementById(id);
  const tr = value => window.Locale?.translate(value) || value;
  const el = (tag, text, raw = false) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (raw) n.setAttribute('translate', 'no'); return n; };
  const button = (text, fn) => { const b = el('button', tr(text)); b.type = 'button'; b.className = 'btn ghost'; b.onclick = fn; return b; };
  const icon = new Image(); icon.src = 'assets/mailbox.png';
  let npc = null, zone = 0, data = null, selected = null, attached = [], receipt = null;
  let pending = null, timer = 0, watch = 0, priorFocus = null, unread = 0, total = null, draftOwner = null;
  const visible = () => !$('mail-panel').hidden;
  const say = (message, ok = false) => { $('mail-notice').textContent = tr(message); $('mail-notice').dataset.state = ok ? 'ok' : 'error'; };
  const near = () => {
    const h = window.Field?.hero;
    return Online.connected && h && !h.dead && !h.mounted && !h.sparkTravel && Field.zone === zone && npc && Math.hypot(h.x - npc.x, h.y - npc.y) <= 2.8;
  };
  function settle() {
    clearTimeout(timer); pending = null;
    $('mail-panel').removeAttribute('aria-busy');
    for (const b of $('mail-panel').querySelectorAll('button[data-mail-busy]')) { b.disabled = false; delete b.dataset.mailBusy; }
  }
  function send(request) {
    if (pending || !npc) return false;
    pending = request.op;
    if (!Online.send({ type: 'mail', npc: npc.id, request })) { settle(); say('You are disconnected. Reconnect before using mail.'); return false; }
    $('mail-panel').setAttribute('aria-busy', 'true');
    for (const b of $('mail-panel').querySelectorAll('button:not(:disabled)')) {
      if (b.id === 'mail-close') continue;
      b.disabled = true; b.dataset.mailBusy = '';
    }
    timer = setTimeout(() => { settle(); say('No reply yet. Retry keeps the same send receipt.'); }, 5000);
    return true;
  }
  function tab(compose) {
    $('mail-inbox-view').hidden = compose;
    $('mail-compose-view').hidden = !compose;
    $('mail-confirm').hidden = true;
    $('mail-inbox-tab').setAttribute('aria-pressed', String(!compose));
    $('mail-compose-tab').setAttribute('aria-pressed', String(compose));
    if (compose) { receipt ||= crypto.randomUUID(); renderChoices(); $('mail-recipient').focus(); }
  }
  function attachmentsLine(contents, target) {
    const rows = [];
    if (contents.gold) { const p = el('p'); Money.set(p, contents.gold); rows.push(p); }
    for (const a of contents.items || []) {
      const i = WORLD_ITEMS.find(i => i.id === a.item), g = contents.gear?.find(g => g.id === a.copy);
      const p = el('p', `${tr(i?.name || a.item)} ×${a.quantity}`);
      if (g) p.append(el('small', Inventory.copyLine(g)));
      rows.push(p);
    }
    target.replaceChildren(...rows);
  }
  const systemMail = { sender: 'Dungeon loot', subject: 'Dungeon loot award', body: 'Your bags were full. Your won item is enclosed.' };
  const letterText = (letter, key) => letter.systemAward ? tr(systemMail[key]) : letter[key];
  function renderReader() {
    const letter = data?.letters.find(l => l.id === selected);
    $('mail-reader').hidden = !letter;
    if (!letter) return;
    $('mail-subject-view').textContent = letterText(letter, 'subject');
    $('mail-sender').textContent = letterText(letter, 'sender');
    $('mail-body-view').textContent = letterText(letter, 'body');
    $('mail-returned').hidden = !letter.returned || letter.systemAward;
    attachmentsLine(letter.contents, $('mail-contents'));
    const has = letter.contents.gold > 0 || letter.contents.items.length > 0;
    $('mail-collect').disabled = !has;
    $('mail-return').disabled = !has || letter.returned;
    $('mail-delete').disabled = has;
  }
  function renderLetters() {
    const rows = (data?.letters || []).map(l => {
      const b = button('', () => { selected = l.id; send({ op: 'read', id: l.id }); });
      b.dataset.letter = l.id;
      b.dataset.unread = String(!l.read);
      b.setAttribute('aria-pressed', String(l.id === selected));
      b.append(el('strong', letterText(l, 'subject'), true), el('span', letterText(l, 'sender'), true));
      if (!l.read) b.append(el('small', tr('Unread')));
      if (l.returned && !l.systemAward) b.append(el('small', tr('Returned letter')));
      return b;
    });
    $('mail-letters').replaceChildren(...(rows.length ? rows : [el('p', tr('Your inbox is empty.'))]));
    renderReader();
  }
  function renderChoices() {
    const select = $('mail-item'), old = select.value;
    select.replaceChildren(...(data?.choices || []).map((a, index) => {
      const i = WORLD_ITEMS.find(i => i.id === a.item);
      const option = el('option', `${tr(i?.name || a.item)}${a.copy != null ? ` #${a.copy} · ${Inventory.copyLine(a.gear)}` : ` ×${a.quantity}`}${a.reason ? ` · ${tr(a.reason)}` : ''}`);
      option.value = index; option.dataset.item = a.item; option.disabled = !!a.reason || !a.quantity; option.title = tr(a.reason || ''); return option;
    }));
    if (select.options[old] && !select.options[old].disabled) select.value = old;
    $('mail-attached').replaceChildren(...attached.map((a, index) => {
      const row = el('div'), i = WORLD_ITEMS.find(i => i.id === a.item);
      row.append(el('span', `${tr(i?.name || a.item)} ×${a.quantity}${a.copy != null ? ` #${a.copy}` : ''}`), button('Remove attachment', () => { attached.splice(index, 1); $('mail-confirm').hidden = true; renderChoices(); }));
      return row;
    }));
    $('mail-add').disabled = attached.length >= 6 || ![...select.options].some(o => !o.disabled);
  }
  function onPacket(packet) {
    if (!npc || packet.npc !== npc.id) return;
    const op = pending; settle();
    if (!packet.ok) {
      say(packet.notice);
      if (!visible()) { $('npc-notice').textContent = tr(packet.notice); window.Announce?.show(tr(packet.notice), 'error'); }
      return;
    }
    if (!visible()) {
      if (op !== 'open' || !near()) return;
      priorFocus = document.activeElement;
      window.City?.close(false); window.Settings?.close(false); window.Quests?.close(false); window.Social?.close(false); window.Bank?.close(false); window.Skillbar?.close(false); window.WorldMap?.close(false); $('equipment').hidden = true;
      $('pause').hidden = true; Field.setPaused(true); $('mail-panel').hidden = false; window.Settings?.applyScale();
      tab(false); $('mail-inbox-tab').focus();
      clearInterval(watch); watch = setInterval(() => { if (!near()) close(); }, 250);
    }
    data = packet;
    Inventory.updateBags(packet.inventory, packet.equipment, packet.bags, packet.gearInstances);
    if (packet.found) { $('mail-recipient').value = packet.found; $('mail-recipient-result').textContent = packet.found; }
    if (packet.sent != null) {
      attached = []; receipt = null; $('mail-compose-form').reset(); $('mail-recipient-result').textContent = ''; tab(false);
    }
    say(packet.notice, true); renderLetters(); renderChoices();
  }
  function open(box) {
    if (visible() || pending || !Online.connected) return false;
    const h = Field.hero;
    box ||= City.npcs.filter(n => n.offers?.some(o => o.id === 'mail')).sort((a,b) => Math.hypot(h.x-a.x,h.y-a.y)-Math.hypot(h.x-b.x,h.y-b.y))[0];
    if (!box || Math.hypot(h.x-box.x,h.y-box.y)>2.8) { window.Announce?.show(tr('Walk closer to a mailbox.'), 'error'); return false; }
    if (draftOwner !== Online.id) { attached = []; receipt = null; confirmed = null; $('mail-compose-form').reset(); $('mail-recipient-result').textContent = ''; draftOwner = Online.id; }
    npc = box; zone = Field.zone;
    return send({ op: 'open' });
  }
  function close(resume = true) {
    const wasVisible = visible(); settle(); clearInterval(watch); $('mail-panel').hidden = true; npc = null; data = null; selected = null;
    if (wasVisible && resume) { Field.setPaused(false); priorFocus?.focus?.({ preventScroll: true }); }
  }
  function label() {
    if (total != null && total > 0) return tr(`Mail: ${total} in total, ${unread} unread`);
    return unread ? tr(`Mail: ${unread} unread`) : tr('Mail: no unread letters');
  }
  function onUnread(count, all) {
    const changed = unread !== count; unread = count; total = Number.isFinite(all) ? all : (count > 0 ? Math.max(total ?? 0, count) : total);
    const dot = $('mail-unread'), btn = $('mail-open'), text = label();
    dot.textContent = count > 99 ? '99+' : String(count); dot.hidden = !count;
    btn.dataset.unread = String(count > 0); btn.title = text; btn.setAttribute('aria-label', text);
    if (changed && visible() && !pending && !$('mail-inbox-view').hidden) send({ op: 'open' });
  }
  Money.preview($('mail-gold'));
  $('mail-open').onclick = () => open();
  $('mail-close').onclick = () => close();
  $('mail-inbox-tab').onclick = () => { tab(false); send({ op: 'open' }); };
  $('mail-compose-tab').onclick = () => tab(true);
  $('mail-lookup').onclick = () => send({ op: 'lookup', name: $('mail-recipient').value });
  $('mail-recipient').oninput = () => { $('mail-recipient-result').textContent = ''; $('mail-confirm').hidden = true; };
  $('mail-add').onclick = () => {
    const a = data?.choices[Number($('mail-item').value)], quantity = Number($('mail-quantity').value);
    if (!a || a.reason || !Number.isSafeInteger(quantity) || quantity<1 || quantity>a.quantity || (a.copy != null && quantity !== 1)) { say('Choose a valid attachment and quantity.'); return; }
    if (attached.some(b => b.item === a.item && b.copy === a.copy)) { say('That attachment is already selected.'); return; }
    attached.push({ item: a.item, quantity, ...(a.copy != null ? {copy:a.copy} : {}) });
    $('mail-confirm').hidden = true; renderChoices();
  };
  let confirmed = null;
  $('mail-compose-form').addEventListener('input', () => { $('mail-confirm').hidden = true; });
  $('mail-compose-form').onsubmit = event => {
    event.preventDefault();
    if (pending) return;
    const gold = Number($('mail-gold').value);
    if (!Number.isSafeInteger(gold) || gold<0 || gold>data.gold) { say('You do not have that much copper.'); return; }
    confirmed = { op:'send',request:receipt ||= crypto.randomUUID(),recipient:$('mail-recipient').value.trim(),subject:$('mail-subject').value.trim(),body:$('mail-body').value,gold,attachments:attached.map(a => ({...a})) };
    $('mail-confirm-recipient').textContent = confirmed.recipient;
    $('mail-confirm-subject').textContent = confirmed.subject;
    attachmentsLine({ gold, items:attached, gear:data.choices.filter(a=>a.gear).map(a=>a.gear) }, $('mail-confirm-attachments'));
    $('mail-confirm').hidden = false; $('mail-send-confirm').focus();
  };
  $('mail-send-confirm').onclick = () => { if (confirmed) send(confirmed); };
  $('mail-confirm-cancel').onclick = () => { $('mail-confirm').hidden = true; };
  for (const action of ['collect','return','delete']) $('mail-'+action).onclick = () => { if (selected != null) send({ op:action,id:selected }); };
  $('mail-panel').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
    if (event.key === 'Tab') {
      const nodes = [...$('mail-panel').querySelectorAll('button:not(:disabled),input,textarea,select')].filter(n=>n.offsetParent);
      const first=nodes[0],last=nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    event.stopPropagation();
  });
  window.Mail = { open, onPacket, onUnread, close, reset() { close(false); onUnread(0); },
    draw(g) { if (icon.complete && icon.naturalWidth) { g.imageSmoothingEnabled=false; g.drawImage(icon,-48,-104,96,112); } },
    get visible() { return visible(); } };
})();
