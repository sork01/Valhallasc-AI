'use strict';
/* Settings panel (music and effects volume) and the "Edit UI" mode, where the HUD pieces can be dragged.
   Layout is stored per device as {id: {x, y}} offsets in stage-width percent (cqw) from each element's
   default spot, applied with the CSS `translate` property so it composes with the elements' own transforms.
   Preferences are read and written only through window.Prefs (game.js owns localStorage). */
(() => {
  const $ = id => document.getElementById(id);
  const ITEMS = [
    ['frame', 'Character frame', '.hud-tl'], ['buffs', 'Active effects', '#buff-bar'], ['party', 'Party', '#party-frame'],
    ['map', 'Minimap', '.hud-tr'], ['travel', 'Travel button', '#city-travel'], ['quests', 'Quest tracker', '#quest-tracker'],
    ['character', 'Character button', '#equipment-open'], ['bags', 'Bags button', '#inventory-open'], ['social', 'Social button', '#social-open'],
    ['skillbar', 'Skillbar', '#skillbar'], ['quickuse', 'Food and potion slots', '#quickuse'], ['chat', 'Chat', '#chat'], ['hint', 'Controls hint', '.hud-hint'],
  ];
  const stage = $('stage'), panel = $('settings-panel'), bar = $('layout-bar');
  const els = new Map(ITEMS.map(([id, name, selector]) => [id, document.querySelector(selector)]));
  for (const [id, name] of ITEMS) { const el = els.get(id); if (el) { el.dataset.ui = id; el.dataset.uiName = name; } }
  const layout = {};
  let editing = false, selected = null, layer = null, drag = null;
  const handles = new Map();

  const round = v => Math.round(v * 100) / 100;
  const clamp = (v, lo, hi) => hi < lo ? 0 : Math.max(lo, Math.min(hi, v));
  const offset = id => layout[id] || { x: 0, y: 0 };
  function loadLayout() {
    for (const id of Object.keys(layout)) delete layout[id];
    const saved = window.Prefs.layout;
    for (const [id] of ITEMS) {
      const v = saved[id];
      if (v && Number.isFinite(+v.x) && Number.isFinite(+v.y)) layout[id] = { x: clamp(+v.x, -100, 100), y: clamp(+v.y, -100, 100) };
    }
  }
  const paint = id => { const el = els.get(id), o = layout[id]; if (el) el.style.translate = o && (o.x || o.y) ? `${o.x}cqw ${o.y}cqw` : ''; };

  // How far an element may move and stay inside the stage, in cqw. null while it is not on screen.
  function range(id) {
    const el = els.get(id); if (!el) return null;
    const r = el.getBoundingClientRect(), s = stage.getBoundingClientRect();
    if (!r.width && !r.height) return null;
    const u = s.width / 100, o = offset(id), left = r.left - o.x * u, top = r.top - o.y * u;
    return { u, minX: (s.left - left) / u, maxX: (s.right - left - r.width) / u, minY: (s.top - top) / u, maxY: (s.bottom - top - r.height) / u };
  }
  function place(id, x, y, r = range(id)) {
    if (r) { x = clamp(x, r.minX, r.maxX); y = clamp(y, r.minY, r.maxY); }
    layout[id] = { x: round(x), y: round(y) }; paint(id); syncHandle(id);
  }
  function store() {
    const ui = {}; for (const [id, o] of Object.entries(layout)) if (o.x || o.y) ui[id] = { ...o };
    window.Prefs.set({ ui });
  }
  // Re-apply the saved layout and pull anything that no longer fits (a smaller window) back inside the stage.
  function refresh() {
    loadLayout();
    for (const [id] of ITEMS) { paint(id); if (layout[id]) { const r = range(id); if (r) place(id, layout[id].x, layout[id].y, r); } }
    if (editing) syncHandles();
  }

  // ---------- the volume panel ----------
  const music = $('set-music'), sfx = $('set-sfx'), sound = $('set-sound');
  function syncPanel() {
    music.value = Math.round(window.Prefs.music * 100); sfx.value = Math.round(window.Prefs.sfx * 100); sound.checked = window.Prefs.sound;
    $('set-music-out').textContent = music.value + '%'; $('set-sfx-out').textContent = sfx.value + '%';
  }
  music.addEventListener('input', () => window.Prefs.set({ musicVol: music.value / 100 }));
  sfx.addEventListener('input', () => window.Prefs.set({ sfxVol: sfx.value / 100 }));
  sfx.addEventListener('change', () => window.Prefs.preview());     // a sample when the slider is released
  sound.addEventListener('change', () => window.Prefs.set({ sound: sound.checked }));
  addEventListener('prefs-change', () => { if (!panel.hidden) syncPanel(); });

  function show() {
    $('pause').hidden = true; panel.hidden = false; syncPanel(); music.focus({ preventScroll: true });
  }
  // toMenu: go back to the World Menu; false: just shut everything (the caller is closing the menus itself).
  function close(toMenu = true) {
    if (editing) stopEdit(false);
    if (panel.hidden) return;
    panel.hidden = true;
    if (toMenu) { $('pause').hidden = false; $('p-settings').focus({ preventScroll: true }); }
  }

  // ---------- Edit UI ----------
  function syncHandle(id) {
    const h = handles.get(id), el = els.get(id); if (!h || !el) return;
    const r = el.getBoundingClientRect(), s = stage.getBoundingClientRect();
    h.hidden = !r.width && !r.height;
    h.style.left = r.left - s.left + 'px'; h.style.top = r.top - s.top + 'px'; h.style.width = r.width + 'px'; h.style.height = r.height + 'px';
  }
  const syncHandles = () => { for (const id of handles.keys()) syncHandle(id); };
  function select(id) {
    selected = id;
    for (const [key, h] of handles) h.classList.toggle('selected', key === id);
  }
  function makeHandle(id, name) {
    const h = document.createElement('div');
    h.className = 'layout-handle'; h.tabIndex = 0; h.setAttribute('role', 'button'); h.setAttribute('aria-label', `Move ${name}`);
    h.dataset.id = id; const label = document.createElement('span'); label.textContent = name; h.append(label);
    h.addEventListener('focus', () => select(id));
    h.addEventListener('pointerdown', e => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      e.preventDefault(); select(id); h.focus({ preventScroll: true });
      const o = offset(id); drag = { id, pointer: e.pointerId, x: e.clientX, y: e.clientY, ox: o.x, oy: o.y, r: range(id) };
      h.setPointerCapture(e.pointerId); h.classList.add('dragging');
    });
    h.addEventListener('pointermove', e => {
      if (!drag || drag.pointer !== e.pointerId || !drag.r) return;
      place(id, drag.ox + (e.clientX - drag.x) / drag.r.u, drag.oy + (e.clientY - drag.y) / drag.r.u, drag.r);
    });
    const end = e => { if (!drag || drag.pointer !== e.pointerId) return; drag = null; h.classList.remove('dragging'); store(); };
    h.addEventListener('pointerup', end); h.addEventListener('pointercancel', end);
    return h;
  }
  function startEdit() {
    if (editing) return;
    editing = true; panel.hidden = true; $('pause').hidden = true;
    stage.classList.add('ui-editing'); bar.hidden = false;
    layer = document.createElement('div'); layer.className = 'layout-layer'; stage.append(layer);
    for (const [id, name] of ITEMS) if (els.get(id)) { const h = makeHandle(id, name); handles.set(id, h); layer.append(h); }
    syncHandles(); select(null);
    $('layout-done').focus({ preventScroll: true });
  }
  function stopEdit(toPanel = true) {
    if (!editing) return;
    editing = false; drag = null; store();
    stage.classList.remove('ui-editing'); bar.hidden = true; layer.remove(); layer = null; handles.clear(); selected = null;
    if (toPanel) { panel.hidden = false; syncPanel(); $('set-edit-ui').focus({ preventScroll: true }); }
  }
  function reset() {
    for (const id of Object.keys(layout)) { delete layout[id]; paint(id); }
    for (const [id] of ITEMS) paint(id);
    syncHandles(); store();
  }
  function nudge(id, dx, dy) { const o = offset(id); place(id, o.x + dx, o.y + dy); store(); }

  // While editing the game must not see any key; Esc finishes and arrows move the focused handle.
  addEventListener('keydown', e => {
    if (!editing && panel.hidden) return;
    if (e.key === 'Escape') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (editing) stopEdit(); else close();
      return;
    }
    if (!editing) return;
    const handle = e.target.closest?.('.layout-handle');
    if (handle && e.key.startsWith('Arrow')) {
      e.preventDefault(); e.stopImmediatePropagation();
      const step = e.shiftKey ? 1 : .25;
      nudge(handle.dataset.id, e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0, e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0);
    } else if (!bar.contains(e.target) && e.key !== 'Tab') e.stopImmediatePropagation();
  }, true);
  addEventListener('resize', () => { if (editing) syncHandles(); refresh(); });

  $('p-settings').addEventListener('click', show);
  $('set-back').addEventListener('click', () => close());
  $('set-edit-ui').addEventListener('click', startEdit);
  $('layout-done').addEventListener('click', () => stopEdit());
  $('layout-reset').addEventListener('click', reset);

  window.Settings = { show, close, refresh, startEdit, stopEdit, reset, get active() { return !panel.hidden || editing; }, get editing() { return editing; }, get layout() { return layout; } };
  refresh();
})();
