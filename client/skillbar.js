'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const SLOTS = 12, KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='];
  const icons = {
    attack: '<path d="m9 27 17-17 5-2-2 5-17 17M7 21l10 10M6 31l5-5"/>',
    arrow: '<path d="M6 30 29 7M29 7h-8m8 0v8M6 30l-1-6m1 6 6 1M9 27l-2-5m6 8-1-6"/>',
    powershot: '<path d="M4 18h26m0 0-6-5m6 5-6 5M4 18l-2-5m2 5-2 5M9 18l-2-4m2 4-2 4"/><circle cx="30" cy="18" r="4"/>',
    multishot: '<path d="M5 28 28 8M5 18h24M5 8l23 20M28 8h-6m6 0v6M29 18l-6-4m6 4-6 4M28 28h-6m6 0v-6"/>',
    rollaway: '<path d="M26 10a10 10 0 1 0 2 13M26 4v7h-7M6 33h6M8 28h5"/>',
    piercing: '<path d="M3 18h30m0 0-7-6m7 6-7 6M12 10v16M20 12v12"/>',
    mark: '<circle cx="18" cy="18" r="10"/><path d="M18 3v9M18 24v9M3 18h9M24 18h9"/><circle cx="18" cy="18" r="2"/>',
    explosive: '<path d="m18 4 3 8 8-3-4 7 7 3-8 3 3 8-8-4-5 6-1-8-8-1 6-5-4-8 8 2z"/>',
    rapidfire: '<path d="M4 12h20m0 0-5-4m5 4-5 4M4 20h26m0 0-5-4m5 4-5 4M4 28h16m0 0-4-3m4 3-4 3"/>',
    rain: '<path d="M8 4l-3 12m10-12-3 12m10-12-3 12m10-12-3 12M6 20l-2 5m2-5 2 4m5-7-2 5m2-5 2 4M20 20l-2 5m2-5 2 4m5-7-2 5m2-5 2 4M6 32h24"/>',
    eagle: '<path d="M3 20c6-2 10-8 15-9 5 1 9 7 15 9-6 0-10 2-15 8-5-6-9-8-15-8zM18 16v6"/>',
    cast: '<path d="m17 30 6-17M20 5l2 4 5 1-4 3v5l-4-3-4 1 2-5-2-4zM8 10v5m-2-2h4M29 24v5m-2-2h4"/>',
    shadowstep: '<path d="m23 6-6 10h9L15 31l3-12H9zM4 9h7M2 16h5M4 24h6"/>',
    cleave: '<path d="M5 27c9 1 20-6 26-19M9 31c9 1 20-6 26-19M12 9l4 5M7 14l5 3"/>',
    battlecry: '<path d="M6 14l16-6v20L6 22zM22 12c4 1 7 3 8 6s-4 5-8 6M8 24l2 7h4l-2-6"/>',
    shield: '<path d="M18 4l12 4v9c0 8-6 13-12 15C12 30 6 25 6 17V8zM18 10v16M11 15h14"/>',
    whirl: '<path d="M26 12a10 10 0 0 0-17 3M10 24a10 10 0 0 0 17-3M8 9v6h6M28 27v-6h-6"/>',
    charge: '<path d="M6 18h20M19 10l9 8-9 8M3 11h8M3 25h8"/>',
    slam: '<path d="M10 5h16v10H10zM18 15v6M4 31l8-6 4 4 4-4 4 4 8-4M8 22l-4 2M28 22l4 2"/>',
    heal: '<path d="M18 31C8 24 4 18 4 12a7 7 0 0 1 14-2 7 7 0 0 1 14 2c0 6-4 12-14 19zM18 12v10M13 17h10"/>',
    berserk: '<path d="M18 4c2 7 9 9 9 17a9 9 0 0 1-18 0c0-4 2-6 4-8 0 3 1 4 3 4-1-5-1-9 2-13z"/>',
    shatter: '<path d="M18 4v10l-5 4 6 3-4 5 3 6M5 20l8-2M31 20l-8-2M8 9l6 6M28 9l-6 6"/>',
    titan: '<path d="M6 28V12l6 7 6-12 6 12 6-7v16zM6 32h24"/>',
    twin: '<path d="M4 11h20M4 25h20M20 6l8 5-8 5M20 20l8 5-8 5"/>',
    ward: '<circle cx="18" cy="18" r="13"/><path d="M18 8l7 12H11z"/>',
    fireball: '<circle cx="22" cy="20" r="8"/><path d="M16 14L4 6M14 22L4 24M20 12L18 3"/>',
    barrage: '<path d="M5 18h23M5 18L26 7M5 18l21 11M5 18L22 3.5M5 18l17 14.5"/>',
    blink: '<circle cx="8" cy="18" r="4" stroke-dasharray="2 3"/><circle cx="28" cy="18" r="4"/><path d="M14 18h8M19 14l4 4-4 4"/>',
    lightning: '<path d="m21 3-12 17h9l-3 13L30 14h-9z"/>',
    meteor: '<circle cx="24" cy="12" r="6"/><path d="M19 17L4 32M16 14L4 24M22 20L12 32"/>',
    drain: '<path d="M18 4c6 8 10 12 10 18a10 10 0 0 1-20 0c0-6 4-10 10-18zM14 22a4 4 0 0 0 4 4"/>',
    storm: '<path d="M8 12h16a4 4 0 1 0-4-4M6 19h22a4 4 0 1 1-4 4M10 26h10"/>',
    starfall: '<path d="M22 4l2 5 5 1-4 4 1 5-4-3-4 3 1-5-4-4 5-1zM4 30l12-10M10 32l10-8"/>',
    knives: '<path d="M5 31l14-14 4 4-14 14zM17 17l10-10 3 3-10 10M21 4l11 11"/>',
    evade: '<path d="M18 5c-6 0-9 5-9 11v14l3-3 3 3 3-3 3 3 3-3V16c0-6-3-11-9-11zM14 15h2M20 15h2"/>',
    lunge: '<path d="M5 29L27 7M27 7l-2 8M27 7l-8 2M4 18h6M4 24h6"/>',
    flurry: '<path d="M6 8l10 14M13 6l10 14M20 4l10 14M8 29h20"/>',
    veil: '<path d="M18 4c-5 3-9 8-9 14 0 7 4 12 9 14 5-2 9-7 9-14 0-6-4-11-9-14zM18 12v14"/>',
    cyclone: '<path d="M18 8a10 10 0 0 1 10 10M28 18a10 10 0 0 1-10 10M18 28a10 10 0 0 1-10-10M8 18a10 10 0 0 1 10-10M18 15v6M15 18h6"/>',
    assassinate: '<circle cx="18" cy="18" r="9"/><path d="M18 3v8M18 25v8M3 18h8M25 18h8M18 15v6"/>',
    focus: '<path d="M3 18c5-8 11-11 15-11s10 3 15 11c-5 8-11 11-15 11S8 26 3 18z"/><circle cx="18" cy="18" r="4"/>',
    ring: '<circle cx="18" cy="18" r="6"/><path d="M18 3v6M18 27v6M3 18h6M27 18h6M8 8l4 4M24 24l4 4M28 8l-4 4M12 24l-4 4"/>',
    cuts: '<path d="M5 5l26 26M13 4l19 19M4 13l19 19M28 5L5 28"/>',
    food: '<path d="M5 17h26c0 8-5 13-13 13S5 25 5 17zM11 13c-2-3 2-4 0-8M18 13c-2-3 2-4 0-8M25 13c-2-3 2-4 0-8"/>',
    potion: '<path d="M14 4h8M15 4v8L7 27c-1 3 1 5 4 5h14c3 0 5-2 4-5L21 12V4M10 22h16"/>',
    mend: '<circle cx="18" cy="18" r="13"/><path d="M18 9v18M9 18h18"/>',
    smite: '<circle cx="18" cy="27" r="5"/><path d="M18 3v14M12 9l6 8 6-8M7 27H3M33 27h-4"/>',
    wardlight: '<path d="M18 4l11 4v9c0 8-5 13-11 15C12 30 7 25 7 17V8z"/><path d="M18 11v12M12 17h12"/>',
    prayer: '<path d="M18 31V16M18 16c-4-2-7-6-7-11 4 1 7 4 7 11zM18 16c4-2 7-6 7-11-4 1-7 4-7 11zM9 24c3 0 6 1 9 3M27 24c-3 0-6 1-9 3"/>',
    holynova: '<circle cx="18" cy="18" r="11"/><path d="M18 8v20M8 18h20M11 11l14 14M25 11L11 25"/>',
    blessing: '<path d="M18 4l4 9 10 1-7 7 2 10-9-5-9 5 2-10-7-7 10-1z"/>',
    guardian: '<path d="M18 30V10M18 10c-3-5-9-6-14-3 2 8 8 11 14 9M18 10c3-5 9-6 14-3-2 8-8 11-14 9"/>',
    searing: '<circle cx="18" cy="18" r="6"/><path d="M18 2v6M18 28v6M2 18h6M28 18h6M7 7l4 4M25 25l4 4M29 7l-4 4M11 25l-4 4"/>',
    hymn: '<path d="M14 27V8l14-3v19M14 27a4 4 0 1 1-4-4 4 4 0 0 1 4 4zM28 24a4 4 0 1 1-4-4 4 4 0 0 1 4 4z"/>',
    wrath: '<path d="M10 3l4 14M18 3v18M26 3l-4 14M6 28h24M10 24h16"/>',
  };
  const icon = kind => `<svg viewBox="0 0 36 36" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">${icons[kind]}</svg>`;
  let slots = [], skills = [], character = null, className = '', selected = 0, previousFocus = null, layoutLevel = 1, seenLevel = 0;
  const open = () => !$('skills-panel').hidden;
  function node(tag, text, cls) {
    const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n;
  }
  // Every skill the class can ever learn, in unlock order; `level` says when it becomes usable.
  function available() {
    const cls = Field.hero.look?.class || 'warrior';
    return [{ id: 'attack', name: cls === 'mage' ? 'Arcane Bolt' : cls === 'assassin' ? 'Twin Slash' : cls === 'priest' ? 'Mace Strike' : cls === 'hunter' ? 'Arrow Shot' : 'Sword Strike', level: 1,
      icon: cls === 'mage' ? 'cast' : cls === 'hunter' ? 'arrow' : 'attack', cooldown: cls === 'mage' ? .7 : cls === 'assassin' ? .46 : cls === 'priest' ? .62 : cls === 'hunter' ? .58 : .55,
      description: cls === 'mage' ? 'Cast a bolt at your target or in your aim direction.' : cls === 'hunter' ? 'Loose an arrow at your target or in your aim direction.' : 'Strike enemies within reach in your aim direction.' },
    ...(cls === 'assassin' ? [{ id: 'shadowstep', name: 'Shadowstep', icon: 'shadowstep', cooldown: 1.2, level: 1,
      cost: 20, description: 'Dash in your movement direction, or forward while standing still.' }] : []),
    ...WORLD_SKILLS.filter(s => s.class === cls).sort((a, b) => a.level - b.level)];
  }
  const resourceName = () => { const k = Field.hero.resourceType || 'rage'; return k[0].toUpperCase() + k.slice(1); };
  const costText = skill => skill.cost ? `${skill.cost} ${resourceName()}` : 'Free';
  const level = () => Field.hero.level || 1;
  const unlocked = skill => !!skill && skill.level <= level();
  const find = id => { const skill = skills.find(s => s.id === id); return unlocked(skill) ? skill : undefined; };
  const defaults = () => { const ready = skills.filter(unlocked).slice(0, SLOTS).map(s => s.id); return Array.from({ length: SLOTS }, (_, i) => ready[i] || null); };
  const remaining = skill => skill?.id === 'attack' ? Field.hero.atkCd || 0 : skill?.id === 'shadowstep' ? Field.hero.dashCd || 0 : Field.hero.skillCd?.[skill?.id] || 0;
  function save() { Online.saveSkillSlots(slots, layoutLevel); render(); }
  // A skill earned since the layout was last saved goes into the first empty slot, so a new ability is ready at once.
  function learn() {
    seenLevel = level();
    const fresh = skills.filter(s => s.level > layoutLevel && s.level <= seenLevel && !slots.includes(s.id));
    layoutLevel = seenLevel;
    for (const skill of fresh) { const free = slots.indexOf(null); if (free >= 0) slots[free] = skill.id; }
    save();
  }
  function sync() {
    if (!Online.connected || !Online.currentToken) return;
    const cls = Field.hero.look?.class;
    if (character === Online.currentToken && className === cls) { if (seenLevel !== level()) learn(); return; }
    character = Online.currentToken; className = cls; selected = 0; skills = available();
    const saved = Online.skillSlots;
    layoutLevel = Online.skillLevel ?? 1;
    slots = Array.isArray(saved) ? Array.from({ length: SLOTS }, (_, i) => find(saved[i])?.id || null) : defaults();
    if (!Array.isArray(saved)) layoutLevel = level();
    learn();
  }
  function drop(event, index) {
    event.preventDefault();
    if (!Online.connected || Field.hero.dead) return;
    let data; try { data = JSON.parse(event.dataTransfer.getData('application/x-valhallasc-skill')); } catch (_) { return; }
    if (Number.isInteger(data.slot) && data.slot >= 0 && data.slot < SLOTS) {
      [slots[index], slots[data.slot]] = [slots[data.slot], slots[index]];
    } else if (find(data.skill)) slots[index] = data.skill;
    else return;
    selected = index; save();
  }
  function slotButton(index, editor) {
    const skill = find(slots[index]), b = node('button', '', 'skill-slot'); b.type = 'button'; b.dataset.slot = index + 1;
    b.dataset.skill = skill?.id || ''; b.setAttribute('aria-keyshortcuts', KEYS[index]);
    b.setAttribute('aria-label', `Slot ${KEYS[index]}: ${skill?.name || 'Empty'}${editor ? ', select to assign' : ''}`);
    b.title = `${KEYS[index]} · ${skill?.name || 'Empty slot — assign in Skills (K)'}${skill ? '\n' + costText(skill) + ' · ' + skill.description : ''}`;
    b.append(node('kbd', KEYS[index]), node('span', skill?.name || 'Empty', 'skill-name'));
    const glyph = node('span', '', 'skill-icon'); glyph.innerHTML = skill ? icon(skill.icon) : '<span aria-hidden="true">+</span>'; b.append(glyph);
    b.append(node('span', '', 'skill-cooldown'));
    if (editor) { b.setAttribute('aria-pressed', String(selected === index)); }
    b.addEventListener('click', () => {
      if (editor) { selected = index; renderEditor(); $('skill-editor-slots').querySelector(`[data-slot="${index + 1}"]`).focus(); }
      else if (skill) Field.useSkill(skill.id);
      else { selected = index; show(); }
    });
    b.draggable = !!skill;
    b.addEventListener('dragstart', event => { event.dataTransfer.setData('application/x-valhallasc-skill', JSON.stringify({ slot: index })); event.dataTransfer.effectAllowed = 'move'; });
    b.addEventListener('dragover', event => { if (event.dataTransfer.types.includes('application/x-valhallasc-skill')) event.preventDefault(); });
    b.addEventListener('drop', event => drop(event, index));
    return b;
  }
  function renderEditor() {
    $('skill-editor-slots').replaceChildren(...slots.map((_, i) => slotButton(i, true)));
    $('skill-selection').textContent = `Slot ${selected + 1} · ${find(slots[selected])?.name || 'Empty'} — choose an ability above`;
    $('skill-clear').disabled = !slots[selected];
  }
  function render() {
    $('skillbar-slots').replaceChildren(...slots.map((_, i) => slotButton(i, false)));
    $('skill-library').replaceChildren(...skills.map(skill => {
      const ready = unlocked(skill), b = node(ready ? 'button' : 'div', '', 'skill-card' + (ready ? '' : ' locked')); b.dataset.skill = skill.id;
      const glyph = node('span', '', 'skill-icon'); glyph.innerHTML = icon(skill.icon);
      b.append(glyph, node('b', skill.name), node('small', ready ? `${skill.description} ${costText(skill)} · ${skill.cooldown}s cooldown.` : `Unlocks at level ${skill.level}. ${costText(skill)} · ${skill.description}`));
      if (!ready) { b.setAttribute('aria-disabled', 'true'); b.append(node('em', `Lv ${skill.level}`, 'skill-level')); return b; }
      b.type = 'button'; b.draggable = true;
      if (skill.level > 1) b.append(node('em', `Lv ${skill.level}`, 'skill-level'));
      b.addEventListener('click', () => { slots[selected] = skill.id; save(); $('skill-library').querySelector(`[data-skill="${skill.id}"]`).focus(); });
      b.addEventListener('dragstart', event => { event.dataTransfer.setData('application/x-valhallasc-skill', JSON.stringify({ skill: skill.id })); event.dataTransfer.effectAllowed = 'copy'; });
      return b;
    }));
    renderEditor();
  }
  function show() {
    if ($('scene-game').hidden || !Online.connected || Field.hero.dead) return;
    sync(); previousFocus = document.activeElement;
    Quests.close(false); City.close(false); Inventory.hideTooltip(); $('equipment').hidden = true; $('pause').hidden = true;
    Field.setPaused(true); $('skills-panel').hidden = false; renderEditor();
    $('skill-editor-slots').querySelector(`[data-slot="${selected + 1}"]`).focus({ preventScroll: true });
  }
  function close(resume = true) {
    if (!open()) return;
    $('skills-panel').hidden = true;
    if (resume) { Field.setPaused(false); if (previousFocus?.isConnected && !previousFocus.closest('[hidden]')) previousFocus.focus({ preventScroll: true }); else $('skills-open').focus({ preventScroll: true }); }
  }
  $('skills-open').addEventListener('click', show);
  $('skills-close').addEventListener('click', () => close());
  $('skill-clear').addEventListener('click', () => { slots[selected] = null; save(); });
  $('skill-reset').addEventListener('click', () => { slots = defaults(); save(); });
  $('skills-panel').addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const buttons = [...$('skills-panel').querySelectorAll('button:not(:disabled)')], first = buttons[0], last = buttons.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  addEventListener('keydown', event => {
    if ($('scene-game').hidden || event.repeat || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName || '') || event.ctrlKey || event.altKey || event.metaKey) return;
    const key = event.key.toLowerCase();
    if (open()) {
      if (key === 'escape' || key === 'k') { event.preventDefault(); close(); }
      else if (key === 'e' || key === 'i' || key === 'b') close(false); // The equipment handler opens its panel.
      else if (KEYS.includes(key)) { event.preventDefault(); selected = KEYS.indexOf(key); renderEditor(); }
      return;
    }
    if (key === 'k') { event.preventDefault(); show(); }
    else if (KEYS.includes(key) && Field.canAct) { event.preventDefault(); const skill = find(slots[KEYS.indexOf(key)]); if (skill) Field.useSkill(skill.id); }
  });
  window.Skillbar = { show, close, icon, get open() { return open(); }, update() {
    sync();
    for (const b of $('skillbar-slots').children) {
      const skill = find(b.dataset.skill), cooldown = skill ? remaining(skill) : 0;
      // Snapshot values are the authority; never start a local gameplay cooldown.
      const empty = !!skill?.cost && (Field.hero.resource || 0) < skill.cost;
      b.disabled = !Field.canAct || cooldown > 0 || empty;
      b.classList.toggle('resource-empty', empty);
      b.classList.toggle('on-cooldown', cooldown > 0);
      b.style.setProperty('--cooldown', skill ? Math.min(1, cooldown / skill.cooldown) : 0);
      b.querySelector('.skill-cooldown').textContent = cooldown > 0 ? cooldown.toFixed(1) : '';
    }
    $('skills-open').disabled = !Online.connected || Field.hero.dead;
    window.Quickuse?.update();
  } };
})();
