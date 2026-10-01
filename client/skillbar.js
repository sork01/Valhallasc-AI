'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const icons = {
    attack: '<path d="m9 27 17-17 5-2-2 5-17 17M7 21l10 10M6 31l5-5"/>',
    cast: '<path d="m17 30 6-17M20 5l2 4 5 1-4 3v5l-4-3-4 1 2-5-2-4zM8 10v5m-2-2h4M29 24v5m-2-2h4"/>',
    shadowstep: '<path d="m23 6-6 10h9L15 31l3-12H9zM4 9h7M2 16h5M4 24h6"/>',
  };
  const icon = kind => `<svg viewBox="0 0 36 36" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">${icons[kind]}</svg>`;
  let slots = [], skills = [], character = null, className = '', selected = 0, previousFocus = null;
  const open = () => !$('skills-panel').hidden;
  function node(tag, text, cls) {
    const n = document.createElement(tag); if (text) n.textContent = text; if (cls) n.className = cls; return n;
  }
  function available() {
    const cls = Field.hero.look?.class || 'warrior';
    return [{ id: 'attack', name: cls === 'mage' ? 'Arcane Bolt' : cls === 'assassin' ? 'Twin Slash' : 'Sword Strike',
      icon: cls === 'mage' ? 'cast' : 'attack', cooldown: cls === 'mage' ? .7 : cls === 'assassin' ? .46 : .55,
      description: cls === 'mage' ? 'Cast a bolt at your target or in your aim direction.' : 'Strike enemies within reach in your aim direction.' },
    ...(cls === 'assassin' ? [{ id: 'shadowstep', name: 'Shadowstep', icon: 'shadowstep', cooldown: 1.2,
      description: 'Dash in your movement direction, or forward while standing still.' }] : [])];
  }
  const defaults = () => Array.from({ length: 9 }, (_, i) => skills[i]?.id || null);
  const find = id => skills.find(s => s.id === id);
  const remaining = skill => skill?.id === 'shadowstep' ? Field.hero.dashCd || 0 : Field.hero.atkCd || 0;
  function save() { Online.saveSkillSlots(slots); render(); }
  function sync() {
    if (!Online.connected || !Online.currentToken) return;
    const cls = Field.hero.look?.class;
    if (character === Online.currentToken && className === cls) return;
    character = Online.currentToken; className = cls; selected = 0; skills = available();
    slots = Array.isArray(Online.skillSlots) ? Array.from({ length: 9 }, (_, i) => find(Online.skillSlots[i])?.id || null) : defaults();
    render();
  }
  function drop(event, index) {
    event.preventDefault();
    if (!Online.connected || Field.hero.dead) return;
    let data; try { data = JSON.parse(event.dataTransfer.getData('application/x-valhallasc-skill')); } catch (_) { return; }
    if (Number.isInteger(data.slot) && data.slot >= 0 && data.slot < 9) {
      [slots[index], slots[data.slot]] = [slots[data.slot], slots[index]];
    } else if (find(data.skill)) slots[index] = data.skill;
    else return;
    selected = index; save();
  }
  function slotButton(index, editor) {
    const skill = find(slots[index]), b = node('button', '', 'skill-slot'); b.type = 'button'; b.dataset.slot = index + 1;
    b.dataset.skill = skill?.id || ''; b.setAttribute('aria-keyshortcuts', String(index + 1));
    b.setAttribute('aria-label', `Slot ${index + 1}: ${skill?.name || 'Empty'}${editor ? ', select to assign' : ''}`);
    b.title = `${index + 1} · ${skill?.name || 'Empty slot — assign in Skills (K)'}${skill ? '\n' + skill.description : ''}`;
    b.append(node('kbd', String(index + 1)), node('span', skill?.name || 'Empty', 'skill-name'));
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
      const b = node('button', '', 'skill-card'); b.type = 'button'; b.dataset.skill = skill.id; b.draggable = true;
      const glyph = node('span', '', 'skill-icon'); glyph.innerHTML = icon(skill.icon);
      b.append(glyph, node('b', skill.name), node('small', `${skill.description} ${skill.cooldown}s cooldown.`));
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
      else if (/^[1-9]$/.test(key)) { event.preventDefault(); selected = Number(key) - 1; renderEditor(); }
      return;
    }
    if (key === 'k') { event.preventDefault(); show(); }
    else if (/^[1-9]$/.test(key) && Field.canAct) { event.preventDefault(); const skill = find(slots[Number(key) - 1]); if (skill) Field.useSkill(skill.id); }
  });
  window.Skillbar = { show, close, get open() { return open(); }, update() {
    sync();
    for (const b of $('skillbar-slots').children) {
      const skill = find(b.dataset.skill), cooldown = skill ? remaining(skill) : 0;
      // Snapshot values are the authority; never start a local gameplay cooldown.
      b.disabled = !Field.canAct || cooldown > 0;
      b.classList.toggle('on-cooldown', cooldown > 0);
      b.style.setProperty('--cooldown', skill ? Math.min(1, cooldown / skill.cooldown) : 0);
      b.querySelector('.skill-cooldown').textContent = cooldown > 0 ? cooldown.toFixed(1) : '';
    }
    $('skills-open').disabled = !Online.connected || Field.hero.dead;
  } };
})();
