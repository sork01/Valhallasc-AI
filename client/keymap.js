'use strict';
// One key map for the whole client (UI-KEYMAP). Every action has up to two keys; the player's choices are kept in
// Prefs.keys as overrides only ({action: [code, code]}), merged over DEFAULTS here, so a new action gets its shipped key
// without touching old saves. Keys are stored as `event.code` (the physical key), so a binding survives Shift, an IME and
// other layouts; labels come from the layout map when the browser has one. Prefs lives in game.js, which loads last, so
// it is only read when a key is pressed, never at load.
(() => {
  // Group, action, label and shipped keys. Order is the order of the Settings screen.
  const ACTIONS = [
    ['Movement', 'moveUp', 'Move up', ['KeyW', 'ArrowUp']],
    ['Movement', 'moveDown', 'Move down', ['KeyS', 'ArrowDown']],
    ['Movement', 'moveLeft', 'Move left', ['KeyA', 'ArrowLeft']],
    ['Movement', 'moveRight', 'Move right', ['KeyD', 'ArrowRight']],
    ['Movement', 'mount', 'Mount or dismount', ['KeyH']],
    ['Movement', 'talk', 'Talk or read', ['KeyF']],
    ['Movement', 'interact', 'Interact with a cross', ['KeyG']],
    ['Combat', 'attack', 'Attack', ['Space', 'KeyJ']],
    ['Combat', 'dash', 'Shadow Step (Assassin)', ['Shift']],
    ...Array.from({ length: 12 }, (_, i) => ['Skillbar', 'skill' + (i + 1), `Skill slot ${i + 1}`, [['Digit1', 'Digit2', 'Digit3', 'Digit4', 'Digit5', 'Digit6', 'Digit7', 'Digit8', 'Digit9', 'Digit0', 'Minus', 'Equal'][i]]]),
    ['Quick slots', 'quickFood', 'Food', ['KeyZ']],
    ['Quick slots', 'quickPotion', 'Health potion', ['KeyX']],
    ['Quick slots', 'quickMana', 'Resource potion', ['KeyC']],
    ['Windows', 'character', 'Character', ['KeyE']],
    ['Windows', 'bags', 'Bags', ['KeyB', 'KeyI']],
    ['Windows', 'skills', 'Skills', ['KeyK']],
    ['Windows', 'quests', 'Quests', ['KeyQ']],
    ['Windows', 'friends', 'Friends', ['KeyO']],
    ['Windows', 'party', 'Party', ['KeyP']],
    ['Windows', 'map', 'World map', ['KeyM']],
    ['Windows', 'menu', 'Menu', ['Escape']],
    ['Other', 'chat', 'Chat', ['Enter']],
    ['Other', 'sound', 'Sound on or off', ['KeyN', 'KeyM']],
  ];
  const DEFAULTS = Object.fromEntries(ACTIONS.map(([, id, , keys]) => [id, keys]));
  const SLOTS = 2;
  // The two skillbar keys that were typed as characters before the map existed ('-' and '=' are not on the same key in every
  // layout): an unchanged default keeps answering to the character too.
  const LEGACY = { skill11: '-', skill12: '=' };
  // Never bindable: they would break the browser, focus handling or the capture itself. Enter is only for chat.
  const FORBIDDEN = /^(Tab|Meta.*|OS.*|Control.*|Alt.*|CapsLock|NumLock|ScrollLock|ContextMenu|PrintScreen|Pause|F5|F11|F12|Backspace|Delete|Escape|Unidentified)$/;
  const FROM_KEY = { ' ': 'Space', '-': 'Minus', '=': 'Equal', arrowup: 'ArrowUp', arrowdown: 'ArrowDown', arrowleft: 'ArrowLeft', arrowright: 'ArrowRight', escape: 'Escape', enter: 'Enter', shift: 'Shift' };
  const NAMES = { Space: 'Space', Shift: 'Shift', Enter: '↵ Enter', Escape: 'Esc', Minus: '-', Equal: '=', Backquote: '`', BracketLeft: '[', BracketRight: ']', Semicolon: ';', Quote: "'", Backslash: '\\', Comma: ',', Period: '.', Slash: '/', ArrowUp: '↑', ArrowDown: '↓', ArrowLeft: '←', ArrowRight: '→', Insert: 'Insert', Home: 'Home', End: 'End', PageUp: 'Page up', PageDown: 'Page down', IntlBackslash: '<' };
  let layout = null, capturing = false;

  // The code of a key event. Left and right Shift are one key. A synthetic event with no code falls back to its character.
  function codeOf(event) {
    const code = event.code || (event.key.length === 1 && /[a-z]/i.test(event.key) ? `Key${event.key.toUpperCase()}` : /^\d$/.test(event.key) ? `Digit${event.key}` : FROM_KEY[event.key.toLowerCase()] || event.key);
    return /^Shift(Left|Right)$/.test(code) ? 'Shift' : code;
  }
  const overrides = () => { try { const o = window.Prefs?.keys; return o && typeof o === 'object' ? o : {}; } catch (_) { return {}; } };
  function bindings(action) {
    const own = overrides()[action];
    const list = Array.isArray(own) ? own.filter(c => typeof c === 'string' && c) : DEFAULTS[action] || [];
    return list.slice(0, SLOTS);
  }
  // Both slots, with null for an empty one: the Settings screen shows two cells per action.
  const slots = action => { const own = overrides()[action]; return Array.isArray(own) ? [own[0] || null, own[1] || null] : [DEFAULTS[action][0] || null, DEFAULTS[action][1] || null]; };
  const isDefault = action => !Array.isArray(overrides()[action]);

  // Typing in a field never triggers an action.
  function typing(event) {
    const el = event.target;
    return !!el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable);
  }
  // Whether this key event is the action: no Ctrl/Alt/Meta, not while the capture of a new key is running.
  // A character typed on the old keys is the old action's, whatever its physical key (Swedish: '=' is Shift+0 and '-' is Slash).
  const legacyClaim = event => Object.keys(LEGACY).find(id => LEGACY[id] === event.key && isDefault(id)) || null;
  function is(event, action) {
    if (capturing || event.ctrlKey || event.altKey || event.metaKey) return false;
    const claim = legacyClaim(event);
    if (claim) return claim === action;
    return bindings(action).includes(codeOf(event));
  }
  // Every action this key is bound to (a held movement key looks up its direction here).
  function actionsFor(code) { return ACTIONS.filter(([, id]) => bindings(id).includes(code)).map(([, id]) => id); }
  // The action in `list` this event is, or null.
  const which = (event, list) => list.find(action => is(event, action)) || null;

  function name(code) {
    if (!code) return '';
    if (NAMES[code] && !/^(Minus|Equal|Backquote|BracketLeft|BracketRight|Semicolon|Quote|Backslash|Comma|Period|Slash|IntlBackslash)$/.test(code)) return NAMES[code];
    const printed = layout?.get(code);
    if (printed && printed.length === 1) return printed.toUpperCase();
    if (NAMES[code]) return NAMES[code];
    if (/^Key[A-Z]$/.test(code)) return code.slice(3);
    if (/^Digit\d$/.test(code)) return code.slice(5);
    if (/^Numpad/.test(code)) return `Num ${code.slice(6).replace(/Add/, '+').replace(/Subtract/, '-').replace(/Multiply/, '*').replace(/Divide/, '/').replace(/Decimal/, '.')}`;
    return code;
  }
  // "B / I": every key of the action, or its first one when `all` is false. An unbound action reads "unbound".
  function label(action, all = true) {
    const keys = bindings(action).map(name);
    return keys.length ? (all ? keys.join(' / ') : keys[0]) : 'unbound';
  }

  // Every other action that holds `code` (it gives it up when `action` takes it).
  const holders = (code, action) => ACTIONS.map(a => a[1]).filter(id => id !== action && bindings(id).includes(code));
  // Whether `code` may be a key of `action`: the same rule bind() applies to a pressed key and to a key handed over in a swap.
  const allowed = (action, code) => !(FORBIDDEN.test(code) && !(code === 'Escape' && action === 'menu')) && !(code === 'Enter' && action !== 'chat');
  function save(map) { window.Prefs.set({ keys: map }); dispatchEvent(new Event('keymap-change')); }
  // Bind `code` into one slot of an action. A key another action holds is taken from it (swap); the result says which.
  function bind(action, slot, code) {
    if (!DEFAULTS[action] || !(slot >= 0 && slot < SLOTS)) return { ok: false };
    if (!allowed(action, code)) return { ok: false, why: 'This key cannot be used' };
    const next = { ...overrides() }, mine = slots(action), others = holders(code, action);
    const old = mine[slot];
    if (mine.includes(code)) mine[mine.indexOf(code)] = null;           // the same key twice in one action moves
    mine[slot] = code;
    next[action] = mine;
    // A key held by one other action swaps: that action gets what this slot held, if it may have it. A key held by several (M is
    // the map and a sound key) just leaves all of them. Nothing else ever ends up holding a key it could not have chosen.
    for (const other of others) {
      const give = others.length === 1 && old && !mine.includes(old) && allowed(other, old) ? old : null;
      next[other] = slots(other).map(c => c === code ? give : c);
    }
    save(next);
    return { ok: true, swapped: others[0] || null };
  }
  function clear(action, slot) { const next = { ...overrides() }, mine = slots(action); mine[slot] = null; next[action] = mine; save(next); }
  function reset(action) { const next = { ...overrides() }; delete next[action]; save(Object.keys(next).length ? next : null); }
  function resetAll() { save(null); }

  // The first capture: the next key press that is not Escape (cancel) goes to the callback as a code; Backspace or Delete clears.
  function capture(done) {
    capturing = true;
    const stop = value => { removeEventListener('keydown', onKey, true); setTimeout(() => { capturing = false; }, 0); done(value); };
    function onKey(event) {
      event.preventDefault(); event.stopImmediatePropagation();
      if (event.repeat || /^(Shift|Control|Alt|Meta)(Left|Right)?$/.test(event.code) && event.code !== 'ShiftLeft' && event.code !== 'ShiftRight') return;
      if (event.code === 'Escape') return stop(undefined);
      if (event.code === 'Backspace' || event.code === 'Delete') return stop(null);
      stop(codeOf(event));
    }
    addEventListener('keydown', onKey, true);
    return () => { removeEventListener('keydown', onKey, true); capturing = false; };
  }

  // "1–9, 0, -, =" while the twelve skill slots are on their shipped keys, else the twelve labels in order.
  function skillRange() {
    const ids = ACTIONS.filter(a => a[0] === 'Skillbar').map(a => a[1]);
    return ids.every(isDefault) ? '1–9, 0, -, =' : ids.map(id => label(id, false)).join(' ');
  }

  // Printed names of the keys, for labels. Only Chromium has it; elsewhere the code's own name is used.
  if (navigator.keyboard?.getLayoutMap) navigator.keyboard.getLayoutMap().then(map => { layout = map; dispatchEvent(new Event('keymap-change')); }).catch(() => {});

  // Hints that live in index.html: the markup keeps the shipped keys, and this rewrites them with the player's own.
  const list = (action, joiner) => bindings(action).map(name).join(joiner) || 'unbound';
  const first = action => label(action, false);
  // A hint is only rewritten once its action has been changed (and again when it is changed back), so the shipped text, and
  // its Swedish, stay exactly as they are for a player who never opens the Keyboard screen.
  const touched = new Set();
  function applyHints() {
    const put = (key, actions, write) => {
      if (actions.every(isDefault) && !touched.has(key)) return;
      write(); if (actions.every(isDefault)) touched.delete(key); else touched.add(key);
    };
    const attr = (id, name, actions, text) => put(id + name, actions, () => { const el = document.getElementById(id); if (el && el.getAttribute(name) !== text) el.setAttribute(name, text); });
    const body = (selector, actions, text) => put(selector, actions, () => { const el = document.querySelector(selector); if (el && el.textContent !== text) el.textContent = text; });
    attr('inventory-open', 'aria-label', ['bags'], `Open bags (${list('bags', ' / ')})`);
    attr('social-open', 'aria-label', ['friends'], `Friends and party (${first('friends')})`);
    attr('wm-open', 'title', ['map'], `World map (${first('map')})`);
    attr('wm-open', 'aria-label', ['map'], `Open the world map (${first('map')})`);
    attr('mount-toggle', 'aria-label', ['mount'], `Mount or dismount (${first('mount')})`);
    attr('quickuse', 'aria-label', ['quickFood', 'quickPotion', 'quickMana'], `Quick use, ${first('quickFood')} food, ${first('quickPotion')} health potion, ${first('quickMana')} mana potion`);
    attr('chat-input', 'placeholder', ['chat'], `${first('chat')} to chat…`);
    body('#p-equipment', ['character'], `Equipment & Inventory (${first('character')})`);
    body('#skills-open kbd', ['skills'], first('skills'));
    body('#set-sound-row kbd', ['sound'], list('sound', ' / '));
    put('wm-foot', ['map'], () => {
      const note = [...(document.querySelector('.wm-foot')?.childNodes || [])].find(n => n.nodeType === 3);
      const text = `Press a zone to zoom in · Esc steps back · ${first('map')} closes`;
      if (note && note.nodeValue.trim() !== text) note.nodeValue = note.nodeValue.match(/^\s*/)[0] + text;
    });
    const slotIds = Object.keys(DEFAULTS).filter(id => /^skill\d+$/.test(id));
    put('skillbar', slotIds, () => { const bar = document.getElementById('skillbar'), a = slotIds.every(isDefault) ? 'Skillbar, keys 1 to 9, 0, minus and equals' : 'Skillbar'; if (bar && bar.getAttribute('aria-label') !== a) bar.setAttribute('aria-label', a); });
  }
  // Texts the server and the world data write (they cannot know the player's keys) name a key as ‹action›, as in "Press ‹mount› to
  // mount.". It is replaced where the text lands on the page, after Locale (loaded first, so its observer runs first) has
  // translated it. Text that arrived before a rebind keeps the key it was written with.
  const TOKEN = /‹(\w+)›/g;
  const fill = text => text.replace(TOKEN, (whole, id) => DEFAULTS[id] ? (window.Locale ? Locale.translate(first(id)) : first(id)) : whole);
  function fillNode(node) {
    if (node.nodeType === 3) { if (node.nodeValue.includes('‹')) node.nodeValue = fill(node.nodeValue); return; }
    if (node.nodeType !== 1) return;
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    for (let t = walker.nextNode(); t; t = walker.nextNode()) if (t.nodeValue.includes('‹')) t.nodeValue = fill(t.nodeValue);
    for (const el of [node, ...node.querySelectorAll('[title],[aria-label],[placeholder]')]) for (const a of ['title', 'aria-label', 'placeholder']) { const v = el.getAttribute?.(a); if (v?.includes('‹')) el.setAttribute(a, fill(v)); }
  }
  new MutationObserver(records => {
    for (const r of records) {
      if (r.type === 'characterData') fillNode(r.target);
      else if (r.type === 'attributes') fillNode(r.target);
      else r.addedNodes.forEach(fillNode);
    }
  }).observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['title', 'aria-label', 'placeholder'] });
  addEventListener('load', applyHints); addEventListener('keymap-change', applyHints);

  window.Keys = { skillRange, ACTIONS, SLOTS, is, which, codeOf, actionsFor, typing, label, name, slots, isDefault, bind, clear, reset, resetAll, capture, holders, get capturing() { return capturing; } };
})();
