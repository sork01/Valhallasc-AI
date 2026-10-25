'use strict';
// Touch requests the same actions as keys. Only Field's existing input scheduler sends movement.
(() => {
  const $ = id => document.getElementById(id), coarse = matchMedia('(pointer: coarse)');
  const stick = $('touch-stick'), disc = stick.querySelector('.stick-disc'), knob = disc.querySelector('i');
  const arc = $('touch-skills'), actions = $('touch-actions'), quick = $('touch-quickuse');
  let held = null;
  const DEFAULTS = {
    warrior: ['cleave', 'battlecry', 'shieldwall', 'charge'],
    mage: ['fireball', 'arcaneward', 'blink', 'chainlightning'],
    assassin: ['shadowstep', 'throwingknives', 'evasion', 'lunge'],
    priest: ['mend', 'smite', 'wardoflight', 'holynova'],
    hunter: ['powershot', 'multishot', 'rollaway', 'huntersmark'],
  };
  const tr = text => window.Locale?.translate(text) || text;
  const cls = () => Field.hero?.look?.class || 'warrior';
  const catalog = () => window.Skillbar?.catalog || [];
  function assignments() {
    const saved = window.Prefs.touchSkills[cls()], known = new Set(catalog().map(s => s.id));
    return Array.from({ length: 4 }, (_, i) => Array.isArray(saved) && (saved[i] === null || known.has(saved[i])) ? saved[i] : DEFAULTS[cls()][i]);
  }
  function assign(index, skill) {
    if (!Number.isInteger(index) || index < 0 || index > 3 || (skill !== null && !catalog().some(s => s.id === skill))) return false;
    const next = assignments(); next[index] = skill;
    const saved = {};
    // Copy only valid class/skill IDs; old preferences cannot introduce new actions.
    for (const name of Object.keys(DEFAULTS)) {
      const list = window.Prefs.touchSkills[name];
      if (Array.isArray(list)) saved[name] = Array.from({ length: 4 }, (_, i) => {
        const id = list[i];
        return id === null || WORLD_SKILLS.some(s => s.class === name && s.id === id) || (name === 'assassin' && id === 'shadowstep') || id === 'attack' ? id : DEFAULTS[name][i];
      });
    }
    saved[cls()] = next; window.Prefs.set({ touchSkills: saved }); update(); return true;
  }
  function button(label, action, parent) {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = tr(label); b.dataset.action = action;
    let lastTouch = -Infinity;
    b.addEventListener('pointerdown', e => {
      if (parent !== arc || e.pointerType !== 'touch' || b.disabled) return;
      e.preventDefault(); lastTouch = performance.now(); Keys.invoke(action);
    });
    b.addEventListener('click', e => { if (!e.detail || performance.now() - lastTouch > 700) Keys.invoke(action); }); parent.append(b); return b;
  }
  Keys.register('attack', () => coarse.matches && !Field.hero?.pvpTargetId ? Field.startNearestAutoattack() : Field.action('attack'));
  for (const name of ['dash', 'talk', 'interact', 'mount']) Keys.register(name, () => Field.action(name));
  for (let i = 0; i < 12; i++) Keys.register('skill' + (i + 1), () => {
    const id = $('skillbar-slots').children[i]?.dataset.skill; return id ? Field.useSkill(id) : false;
  });
  for (const [action, kind] of [['quickFood', 'food'], ['quickPotion', 'potion'], ['quickMana', 'mana']]) Keys.register(action, () => Quickuse.use(kind));
  Keys.register('skills', () => { Skillbar.show(); return true; });
  Keys.register('map', () => { WorldMap.show(); return true; });
  function closeChat() {
    if ($('chat').contains(document.activeElement)) document.activeElement.blur();
    $('stage').classList.remove('touch-chat-open');
  }
  Keys.register('chat', () => {
    if (coarse.matches && $('stage').classList.contains('touch-chat-open')) { closeChat(); return true; }
    return Online.focusChat();
  });
  Keys.register('quests', () => { Quests.show(); return true; });
  const attack = button('Attack', 'attack', arc); attack.className = 'touch-attack';
  const skillButtons = Array.from({ length: 4 }, (_, i) => {
    const action = 'touchSkill' + (i + 1), b = button('Empty', action, arc); b.className = 'touch-skill'; b.dataset.arc = i;
    Keys.register(action, () => { const id = assignments()[i]; return !!id && Skillbar.state(id).ready && Field.useSkill(id); });
    return b;
  });
  for (const [label, action] of [['Menu', 'menu'], ['Bags', 'bags'], ['Chat', 'chat'], ['Cross', 'interact'], ['Mount', 'mount'], ['World map', 'map'], ['Quests', 'quests']]) button(label, action, actions);
  const targetMenu = document.createElement('button'); targetMenu.type = 'button'; targetMenu.textContent = tr('Target menu');
  targetMenu.setAttribute('aria-controls', 'portrait-menu'); targetMenu.hidden = true;
  targetMenu.addEventListener('click', () => PortraitMenu.toggle()); actions.append(targetMenu);
  const chatButton = actions.querySelector('[data-action="chat"]'); chatButton.setAttribute('aria-controls', 'chat');
  const chatHeader = document.createElement('div'); chatHeader.className = 'touch-chat-header';
  const tabs = $('chat').querySelector('.chat-tabs'); tabs.before(chatHeader); chatHeader.append(tabs);
  const chatClose = document.createElement('button'); chatClose.type = 'button'; chatClose.className = 'touch-chat-close';
  chatClose.textContent = '×'; chatClose.setAttribute('aria-label', tr('Close chat')); chatClose.addEventListener('click', closeChat); chatHeader.append(chatClose);
  // Mobile keyboards can shrink/pan only the visual viewport, leaving the stage unchanged.
  function fitChat() {
    if (!coarse.matches || !$('stage').classList.contains('touch-chat-open')) return;
    const stage = $('stage'), r = stage.getBoundingClientRect(), v = window.visualViewport;
    const left = Math.max(r.left, v?.offsetLeft || 0), top = Math.max(r.top, v?.offsetTop || 0);
    const right = Math.min(r.right, (v?.offsetLeft || 0) + (v?.width || innerWidth));
    const bottom = Math.min(r.bottom, (v?.offsetTop || 0) + (v?.height || innerHeight));
    stage.style.setProperty('--chat-left', `${left - r.left + 8}px`);
    stage.style.setProperty('--chat-bottom', `${r.bottom - bottom + 8}px`);
    stage.style.setProperty('--chat-width', `${Math.max(0, Math.min(600, right - left - 16))}px`);
    stage.style.setProperty('--chat-height', `${Math.max(0, bottom - top - 16)}px`);
  }
  let chatFrame = 0;
  function queueChatFit() { if (!chatFrame) chatFrame = requestAnimationFrame(() => { chatFrame = 0; fitChat(); }); }
  window.visualViewport?.addEventListener('resize', queueChatFit);
  window.visualViewport?.addEventListener('scroll', queueChatFit);
  addEventListener('resize', queueChatFit); addEventListener('scroll', queueChatFit);
  $('chat').addEventListener('focusin', queueChatFit);
  const tray = document.createElement('button'); tray.type = 'button'; tray.textContent = tr('Other skills'); tray.setAttribute('aria-expanded', 'false');
  tray.addEventListener('click', () => {
    const open = $('stage').classList.toggle('touch-tray-open'); tray.setAttribute('aria-expanded', String(open));
  }); quick.append(tray);
  let quickTouch = -Infinity;
  quick.addEventListener('pointerdown', e => {
    const b = e.target.closest('.quick-slot');
    if (!b || e.pointerType !== 'touch' || b.disabled) return;
    e.preventDefault(); quickTouch = performance.now();
    Keys.invoke({ food: 'quickFood', potion: 'quickPotion', mana: 'quickMana' }[b.dataset.kind]);
  });
  quick.addEventListener('click', e => { if (e.detail && e.target.closest('.quick-slot') && performance.now() - quickTouch < 700) { e.preventDefault(); e.stopImmediatePropagation(); } }, true);
  const quickHome = $('quickuse').parentElement, quickNext = $('quickuse').nextSibling;
  function deviceChanged() {
    resetStick(); Field.setTouchDirection?.(0, 0);
    if (coarse.matches) quick.prepend($('quickuse'));
    else { quickHome.insertBefore($('quickuse'), quickNext); $('stage').classList.remove('touch-tray-open'); }
    window.Settings?.applyScale(); window.Settings?.refresh();
  }
  coarse.addEventListener('change', deviceChanged); deviceChanged();

  function resetStick() {
    const previous = held; held = null;
    if (previous && stick.hasPointerCapture?.(previous.id)) stick.releasePointerCapture(previous.id);
    stick.classList.remove('held'); knob.style.translate = '';
  }
  // A tap in the stick area remains an ordinary world tap. Crossing the dead zone starts movement.
  stick.addEventListener('pointerdown', e => {
    if (!coarse.matches || !Field.canAct || Settings.editing || held || e.pointerType === 'mouse') return;
    e.preventDefault(); held = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false };
    const r = stick.getBoundingClientRect(), k = r.width / stick.offsetWidth;
    disc.style.left = (e.clientX - r.left) / k + 'px'; disc.style.top = (e.clientY - r.top) / k + 'px';
    stick.setPointerCapture(e.pointerId); stick.classList.add('held');
  });
  stick.addEventListener('pointermove', e => {
    if (!held || e.pointerId !== held.id) return;
    const dx = e.clientX - held.x, dy = e.clientY - held.y, n = Math.hypot(dx, dy);
    const k = stick.getBoundingClientRect().width / stick.offsetWidth;
    if (n > 8) held.moved = true;
    const r = Math.min(40, n), divisor = n || 1;
    knob.style.translate = `${dx / divisor * r / k}px ${dy / divisor * r / k}px`;
    Field.setTouchDirection(n > 8 ? dx / divisor : 0, n > 8 ? dy / divisor : 0);
  });
  function end(e) {
    if (!held || e.pointerId !== held.id) return;
    const tap = e.type === 'pointerup' && !held.moved, x = held.x, y = held.y;
    resetStick(); Field.setTouchDirection(0, 0);
    if (tap && Field.canAct) Field.tapAt(x, y);
  }
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) stick.addEventListener(type, end);
  addEventListener('blur', resetStick);
  document.addEventListener('visibilitychange', () => { if (document.hidden) resetStick(); });

  const editor = document.createElement('fieldset'); editor.id = 'touch-skill-editor'; editor.hidden = true;
  const legend = document.createElement('legend'); legend.textContent = tr('Choose touch skills'); editor.append(legend);
  const choices = skillButtons.map((_, i) => {
    const label = document.createElement('label'); label.textContent = tr('Touch skill ' + (i + 1));
    const select = document.createElement('select'); select.dataset.arc = i; select.setAttribute('aria-label', tr('Touch skill ' + (i + 1)));
    select.addEventListener('change', () => assign(i, select.value || null)); label.append(select); editor.append(label); return select;
  }); $('layout-bar').append(editor);
  function edit(on) {
    resetStick(); Field.setTouchDirection(0, 0); editor.hidden = !on || !coarse.matches;
    if (!on) return;
    const slots = assignments();
    for (const [i, select] of choices.entries()) {
      select.replaceChildren(...[{ id: '', name: tr('Empty') }, ...catalog()].map(s => {
        const option = document.createElement('option'); option.value = s.id; option.textContent = s.name; return option;
      })); select.value = slots[i] || '';
    }
  }
  let lastState = '';
  function update() {
    if (!coarse.matches || !Field.hero) return;
    const ids = assignments(), states = ids.map(id => Skillbar.state(id));
    attack.disabled = !Field.canAct || !!Field.hero.sparkTravel;
    targetMenu.hidden = $('hud-target').hidden || !$('hud-target').classList.contains('has-menu');
    targetMenu.setAttribute('aria-expanded', String(PortraitMenu.isOpen));
    chatButton.setAttribute('aria-expanded', String($('stage').classList.contains('touch-chat-open')));
    const key = JSON.stringify(states.map(s => [s.skill?.id, s.ready, Math.ceil(s.cooldown)]));
    if (key === lastState) return; lastState = key;
    states.forEach((state, i) => {
      const b = skillButtons[i], skill = state.skill; b.dataset.skill = skill?.id || ''; b.disabled = !state.ready;
      b.replaceChildren();
      if (skill) { const glyph = document.createElement('span'); glyph.innerHTML = Skillbar.icon(skill.icon); b.append(glyph); }
      const name = document.createElement('span'); name.textContent = skill?.name || tr('Empty'); b.append(name);
      b.classList.toggle('cooling', state.cooldown > 0);
      b.setAttribute('aria-label', (skill?.name || tr('Empty')) + (state.cooldown > 0 ? ` · ${Math.ceil(state.cooldown)}s` : ''));
      if (state.cooldown > 0) { const cd = document.createElement('small'); cd.className = 'touch-cooldown'; cd.textContent = Math.ceil(state.cooldown); b.append(cd); }
      if (skill && skill.level > (Field.hero.level || 1)) { const lock = document.createElement('small'); lock.textContent = `Lv ${skill.level}`; b.append(lock); }
    });
  }
  addEventListener('keydown', e => {
    if (e.repeat || Keys.typing(e) || !Field.canAct) return;
    const action = Keys.which(e, ['touchSkill1', 'touchSkill2', 'touchSkill3', 'touchSkill4']);
    if (action) { e.preventDefault(); Keys.invoke(action); }
  });
  window.TouchControls = { assign, assignments, edit, update, resetStick };
})();
