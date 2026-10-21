'use strict';
/* Settings panel (music and effects volume) and the "Edit UI" mode, where the HUD pieces can be dragged.
   Layout is stored per device as {id: {x, y}} offsets in stage-width percent (cqw) from each element's
   default spot, applied with the CSS `translate` property so it composes with the elements' own transforms.
   UI size: one global factor (Prefs.uiScale) scales every HUD piece and window with the CSS `scale` property, about the
   corner each piece is anchored to, so nothing drifts. Each window also has a corner grip that resizes just that window (the quest tracker and chat get width and height grips, Prefs.panelSize)
   (Prefs.winScale, a factor on top of the global one). `scale` never changes layout, so the stage maths stays as it was.
   Preferences are read and written only through window.Prefs (game.js owns localStorage). */
(() => {
  const $ = id => document.getElementById(id);
  // [id, name, selector, transform-origin]: the origin is the corner the piece is anchored to. A piece centred with
  // translateX(-50%) uses x=0: the shift is applied before the scale, which leaves its centre where it was.
  const ITEMS = [
    ['frame', 'Character frame', '.hud-tl', '0 0'], ['buffs', 'Active effects', '#buff-bar', '0 0'], ['party', 'Party', '#party-frame', '0 0'],
    ['map', 'Minimap', '.hud-tr', '100% 0'], ['travel', 'Travel button', '#city-travel', '100% 0'], ['quests', 'Quest tracker', '#quest-tracker', '0 0'],
    ['bags', 'Bags button', '#inventory-open', '100% 100%'], ['social', 'Social button', '#social-open', '100% 100%'],
    ['skillbar', 'Skillbar', '#skillbar', '0 100%'], ['quickuse', 'Food and potion slots', '#quickuse', '0 100%'], ['chat', 'Chat', '#chat', '0 100%'],
  ];
  // Scaled with the UI but not movable.
  const EXTRA = [['#loot-rolls', '0 0'], ['#social-invites', '0 0'], ['#pvp-duel-warning', '0 0'], ['#rare-pickup', '0 0'], ['#toast', '0 100%']];
  // [overlay id, window selector or null for the overlay itself, name, origin, resizable]
  const WINDOWS = [
    ['pause', '.pause-panel', 'World Menu', '50% 50%', false], ['settings-panel', '.settings-panel', 'Settings', '50% 50%', false],
    ['quest-journal', '.quest-panel', 'Quest journal', '50% 50%', true], ['npc-dialogue', '.gossip-window', 'Conversation', '50% 50%', true],
    ['worldmap', '.wm-panel', 'World map', '50% 50%', true], ['social-panel', '.social-panel', 'Social', '50% 50%', true],
    ['trade-panel', '.trade-panel', 'Trade', '50% 50%', true], ['rebirth-dialog', '.rebirth-dialog', 'Rebirth', '50% 50%', true],
    ['bank-panel', '.bank-panel', 'Bank', '50% 50%', true], ['skills-panel', '.skills-panel', 'Skills', '50% 50%', true],
    ['equipment', '.equipment-workspace', 'Character and bags', '50% 50%', true], ['sign-panel', null, 'Sign', '0 0', true],
  ];
  const stage = $('stage'), panel = $('settings-panel'), bar = $('layout-bar');
  const els = new Map(ITEMS.map(([id, name, selector]) => [id, document.querySelector(selector)]));
  for (const [id, name, , origin] of ITEMS) { const el = els.get(id); if (el) { el.dataset.ui = id; el.dataset.uiName = name; el.style.transformOrigin = origin; } }
  for (const [selector, origin] of EXTRA) { const el = document.querySelector(selector); if (el) el.style.transformOrigin = origin; }
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
    placePanelGrips();
  }

  // ---------- UI size and window sizes ----------
  const UI_MIN = .6, UI_MAX = 1.5, WIN_MIN = .5;
  const wins = WINDOWS.map(([overlay, selector, name, origin, resizable]) => {
    const root = $(overlay), el = selector ? root?.querySelector(selector) : root;
    if (el) el.style.transformOrigin = origin;
    return { id: overlay, name, el, resizable, grip: null };
  }).filter(w => w.el);
  const winScale = {};
  const uiScale = () => window.Prefs.uiScale;
  const fitScale = w => { const s = stage.getBoundingClientRect(), width = w.el.offsetWidth, height = w.el.offsetHeight; return width && height ? Math.max(WIN_MIN, Math.min(s.width / width, s.height / height) * .98) : Infinity; };
  const windowScale = w => Math.max(WIN_MIN, Math.min(uiScale() * (winScale[w.id] || 1), fitScale(w)));
  function loadWindowScales() {
    for (const id of Object.keys(winScale)) delete winScale[id];
    for (const w of wins) { const v = +window.Prefs.winScale[w.id]; if (Number.isFinite(v) && v > 0) winScale[w.id] = Math.max(.4, Math.min(3, v)); }
  }
  function placeGrip(w) {
    if (!w.grip) return;
    const r = w.el.getBoundingClientRect(), s = stage.getBoundingClientRect();
    w.grip.hidden = editing || !r.width || !r.height;
    if (w.grip.hidden) return;
    const g = w.grip.offsetWidth || 16;
    w.grip.style.left = Math.min(r.right, s.right) - s.left - g - 3 + 'px'; w.grip.style.top = Math.min(r.bottom, s.bottom) - s.top - g - 3 + 'px';
  }
  function applyWindow(w) {
    const k = windowScale(w);
    w.el.style.scale = Math.abs(k - 1) < .005 ? '' : String(Math.round(k * 1000) / 1000);
    placeGrip(w);
  }
  function applyScale() {
    const k = uiScale();
    stage.style.setProperty('--ui', String(k)); // CSS that lines one piece up with another reads the scale from here
    for (const [id] of ITEMS) { const el = els.get(id); if (el) el.style.scale = Math.abs(k - 1) < .005 ? '' : String(k); }
    for (const [selector] of EXTRA) { const el = document.querySelector(selector); if (el) el.style.scale = Math.abs(k - 1) < .005 ? '' : String(k); }
    for (const w of wins) applyWindow(w);
    placePanelGrips();
  }
  function storeWindows() {
    const out = {}; for (const [id, v] of Object.entries(winScale)) if (Math.abs(v - 1) > .005) out[id] = Math.round(v * 1000) / 1000;
    window.Prefs.set({ winScale: out });
  }
  // Set a window's size as a factor of the global scale; the factor is capped so the window still fits the stage.
  function sizeWindow(w, factor, save = true) {
    const cap = fitScale(w) / uiScale();
    const f = Math.max(WIN_MIN / uiScale(), Math.min(factor, cap, 3));
    if (Math.abs(f - 1) < .005) delete winScale[w.id]; else winScale[w.id] = f;
    applyWindow(w); if (save) storeWindows();
  }
  function clearWindow(w) { delete winScale[w.id]; applyWindow(w); storeWindows(); }
  function makeGrip(w) {
    const g = document.createElement('div');
    g.className = 'win-grip'; g.tabIndex = 0; g.setAttribute('role', 'button'); g.hidden = true;
    g.title = `Drag to resize · double-click for the normal size`;
    g.setAttribute('aria-label', `Resize ${w.name}: arrow keys change the size, 0 resets it`);
    let drag = null;
    g.addEventListener('pointerdown', e => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();
      const r = w.el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      drag = { pointer: e.pointerId, cx, cy, start: Math.hypot(e.clientX - cx, e.clientY - cy) || 1, size: windowScale(w) };
      g.setPointerCapture(e.pointerId); g.classList.add('dragging');
    });
    g.addEventListener('pointermove', e => {
      if (!drag || drag.pointer !== e.pointerId) return;
      // The window grows about its centre, so the grip follows the pointer when the distance from the centre scales with it.
      sizeWindow(w, drag.size * Math.hypot(e.clientX - drag.cx, e.clientY - drag.cy) / drag.start / uiScale(), false);
    });
    const end = e => { if (!drag || drag.pointer !== e.pointerId) return; drag = null; g.classList.remove('dragging'); storeWindows(); };
    g.addEventListener('pointerup', end); g.addEventListener('pointercancel', end);
    g.addEventListener('dblclick', () => clearWindow(w));
    g.addEventListener('keydown', e => {
      const step = { ArrowRight: .05, ArrowUp: .05, ArrowLeft: -.05, ArrowDown: -.05 }[e.key];
      if (step === undefined && e.key !== '0') return;
      e.preventDefault(); e.stopPropagation();
      if (e.key === '0') clearWindow(w); else sizeWindow(w, (winScale[w.id] || 1) + step * (e.shiftKey ? 3 : 1));
    });
    return g;
  }
  let gripLayer = null;
  function initWindows() {
    gripLayer = document.createElement('div'); gripLayer.className = 'win-grips'; stage.append(gripLayer);
    const watch = new ResizeObserver(entries => { for (const entry of entries) { const w = wins.find(x => x.el === entry.target); if (w) applyWindow(w); } });
    for (const w of wins) {
      if (w.resizable) { w.grip = makeGrip(w); gripLayer.append(w.grip); }
      watch.observe(w.el);
    }
    new ResizeObserver(() => applyScale()).observe(stage);
  }
  function resetWindows() { for (const w of wins) { delete winScale[w.id]; applyWindow(w); } storeWindows(); resetPanels(); }

  // ---------- width and height of the quest tracker and the chat ----------
  // These two are lists, so they get a real width and height (the list scrolls inside) instead of the window zoom. Sizes are
  // stored in cqw of the layout box (Prefs.panelSize {id: {w, h}}), applied as --pw / --ph, and h is the height of the list.
  // The grip lives in the grip layer, not inside the piece: quests.js rebuilds the tracker's children on every update.
  const PANELS = [
    { id: 'quests', name: 'Quest tracker', top: false, w: [12, 60], h: [4, 50], body: el => el.querySelector('.tracker-list') },
    { id: 'chat', name: 'Chat', top: true, w: [14, 60], h: [3.5, 45], body: el => [...el.querySelectorAll('.chat-log')].find(x => !x.hidden) },
  ].map(p => ({ ...p, el: els.get(p.id), grip: null, size: null })).filter(p => p.el);
  const cq = () => stage.offsetWidth / 100;
  const panelScale = p => p.el.getBoundingClientRect().width / (p.el.offsetWidth || 1) || 1;
  function paintPanel(p) {
    if (!p.size) { p.el.style.removeProperty('--pw'); p.el.style.removeProperty('--ph'); delete p.el.dataset.sized; return; }
    p.el.style.setProperty('--pw', p.size.w + 'cqw'); p.el.style.setProperty('--ph', p.size.h + 'cqw'); p.el.dataset.sized = '1';
  }
  function placePanelGrip(p) {
    if (!p.grip) return;
    const r = p.el.getBoundingClientRect(), s = stage.getBoundingClientRect(), body = p.body(p.el);
    p.grip.hidden = editing || !r.width || !r.height || !body || !body.offsetHeight;
    if (p.grip.hidden) return;
    const g = p.grip.offsetWidth || 18;
    p.grip.style.left = Math.min(r.right, s.right) - s.left - g - 3 + 'px';
    p.grip.style.top = (p.top ? Math.max(r.top, s.top) - s.top + 3 : Math.min(r.bottom, s.bottom) - s.top - g - 3) + 'px';
  }
  const placePanelGrips = () => { for (const p of PANELS) placePanelGrip(p); };
  // Set a size; a size that would push the piece out of the stage is refused (the previous one stays).
  function sizePanel(p, w, h, save = true) {
    const before = p.size, lim = (v, [lo, hi]) => round(Math.max(lo, Math.min(hi, v)));
    p.size = { w: lim(w, p.w), h: lim(h, p.h) }; paintPanel(p);
    const r = p.el.getBoundingClientRect(), s = stage.getBoundingClientRect();
    if (r.right > s.right + 1 || r.bottom > s.bottom + 1 || r.top < s.top - 1 || r.left < s.left - 1) { p.size = before; paintPanel(p); }
    placePanelGrip(p); if (save) storePanels();
  }
  const currentPanel = p => ({ w: p.el.offsetWidth / cq(), h: (p.body(p.el)?.offsetHeight || 0) / cq() });
  function storePanels() {
    const out = {}; for (const p of PANELS) if (p.size) out[p.id] = { ...p.size };
    window.Prefs.set({ panelSize: out });
  }
  function clearPanel(p) { p.size = null; paintPanel(p); placePanelGrip(p); storePanels(); }
  function loadPanels() {
    for (const p of PANELS) {
      const v = window.Prefs.panelSize[p.id];
      p.size = v && Number.isFinite(+v.w) && Number.isFinite(+v.h) ? { w: Math.max(p.w[0], Math.min(p.w[1], +v.w)), h: Math.max(p.h[0], Math.min(p.h[1], +v.h)) } : null;
      paintPanel(p);
    }
  }
  function makePanelGrip(p) {
    const g = document.createElement('div');
    g.className = 'panel-grip' + (p.top ? ' top' : ''); g.tabIndex = 0; g.setAttribute('role', 'button'); g.hidden = true; g.dataset.panel = p.id;
    g.title = 'Drag to change the width and height · double-click for the normal size';
    g.setAttribute('aria-label', `Resize ${p.name}: arrow keys change the width and height, 0 resets it`);
    let drag = null;
    g.addEventListener('pointerdown', e => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      e.preventDefault(); e.stopPropagation();
      drag = { pointer: e.pointerId, x: e.clientX, y: e.clientY, k: panelScale(p) * cq(), start: currentPanel(p) };
      g.setPointerCapture(e.pointerId); g.classList.add('dragging');
    });
    g.addEventListener('pointermove', e => {
      if (!drag || drag.pointer !== e.pointerId) return;
      sizePanel(p, drag.start.w + (e.clientX - drag.x) / drag.k, drag.start.h + (p.top ? drag.y - e.clientY : e.clientY - drag.y) / drag.k, false);
    });
    const end = e => { if (!drag || drag.pointer !== e.pointerId) return; drag = null; g.classList.remove('dragging'); storePanels(); };
    g.addEventListener('pointerup', end); g.addEventListener('pointercancel', end);
    g.addEventListener('dblclick', () => clearPanel(p));
    g.addEventListener('keydown', e => {
      const step = (e.shiftKey ? 3 : 1), grow = p.top ? 'ArrowUp' : 'ArrowDown', shrink = p.top ? 'ArrowDown' : 'ArrowUp';
      const d = { ArrowRight: [step, 0], ArrowLeft: [-step, 0], [grow]: [0, step], [shrink]: [0, -step] }[e.key];
      if (!d && e.key !== '0') return;
      e.preventDefault(); e.stopPropagation();
      if (e.key === '0') clearPanel(p); else { const c = p.size || currentPanel(p); sizePanel(p, c.w + d[0], c.h + d[1]); }
    });
    return g;
  }
  function initPanels() {
    const watch = new ResizeObserver(placePanelGrips);
    for (const p of PANELS) { p.grip = makePanelGrip(p); gripLayer.append(p.grip); watch.observe(p.el); }
    loadPanels(); placePanelGrips();
    // The tracker's list is rebuilt on every update and the chat swaps its log between tabs: look again when they change.
    for (const p of PANELS) new MutationObserver(placePanelGrips).observe(p.el, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] });
  }
  function resetPanels() { window.Prefs.set({ panelSize: null }); loadPanels(); placePanelGrips(); }

  // ---------- the volume panel ----------
  const music = $('set-music'), sfx = $('set-sfx'), sound = $('set-sound'), night = $('set-night'), weather = $('set-weather'), weatherAudio = $('set-weather-audio'), language = $('set-language'), size = $('set-uiscale');
  function syncPanel() {
    language.value = window.Prefs.lang;
    music.value = Math.round(window.Prefs.music * 100); sfx.value = Math.round(window.Prefs.sfx * 100); sound.checked = window.Prefs.sound;
    night.value = Math.round(window.Prefs.night * 100); $('set-night-out').textContent = night.value + '%';
    weather.value = Math.round(window.Prefs.weather * 100); $('set-weather-out').textContent = weather.value + '%';
    weatherAudio.value = Math.round(window.Prefs.weatherAudio * 100); $('set-weather-audio-out').textContent = weatherAudio.value + '%';
    size.value = Math.round(uiScale() * 100); $('set-uiscale-out').textContent = size.value + '%';
    $('set-music-out').textContent = music.value + '%'; $('set-sfx-out').textContent = sfx.value + '%';
  }
  music.addEventListener('input', () => window.Prefs.set({ musicVol: music.value / 100 }));
  language.addEventListener('change', () => window.Prefs.set({ lang: language.value }));
  sfx.addEventListener('input', () => window.Prefs.set({ sfxVol: sfx.value / 100 }));
  sfx.addEventListener('change', () => window.Prefs.preview());     // a sample when the slider is released
  sound.addEventListener('change', () => window.Prefs.set({ sound: sound.checked }));
  night.addEventListener('input', () => { $('set-night-out').textContent = night.value + '%'; window.Prefs.set({ night: night.value / 100 }); });
  weather.addEventListener('input', () => { $('set-weather-out').textContent = weather.value + '%'; window.Prefs.set({ weather: weather.value / 100 }); });
  weatherAudio.addEventListener('input', () => { $('set-weather-audio-out').textContent = weatherAudio.value + '%'; window.Prefs.set({ weatherAudio: weatherAudio.value / 100 }); });
  size.addEventListener('input', () => { $('set-uiscale-out').textContent = size.value + '%'; window.Prefs.set({ uiScale: size.value / 100 }); applyScale(); refresh(); });
  $('set-win-reset').addEventListener('click', resetWindows);
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
    stage.classList.add('ui-editing'); bar.hidden = false; for (const w of wins) placeGrip(w); placePanelGrips();
    layer = document.createElement('div'); layer.className = 'layout-layer'; stage.append(layer);
    for (const [id, name] of ITEMS) if (els.get(id)) { const h = makeHandle(id, name); handles.set(id, h); layer.append(h); }
    syncHandles(); select(null);
    $('layout-done').focus({ preventScroll: true });
  }
  function stopEdit(toPanel = true) {
    if (!editing) return;
    editing = false; drag = null; store();
    stage.classList.remove('ui-editing'); bar.hidden = true; for (const w of wins) placeGrip(w); placePanelGrips(); layer.remove(); layer = null; handles.clear(); selected = null;
    if (toPanel) { panel.hidden = false; syncPanel(); $('set-edit-ui').focus({ preventScroll: true }); }
  }
  function reset() {
    window.Prefs.set({ ui: null }); refresh();
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
  addEventListener('resize', () => { if (editing) syncHandles(); refresh(); applyScale(); });

  $('p-settings').addEventListener('click', show);
  $('set-back').addEventListener('click', () => close());
  $('set-edit-ui').addEventListener('click', startEdit);
  $('layout-done').addEventListener('click', () => stopEdit());
  $('layout-reset').addEventListener('click', reset);

  window.Settings = { show, close, refresh, startEdit, stopEdit, reset, applyScale, resetWindows, resetPanels, get panelSizes() { return Object.fromEntries(PANELS.map(p => [p.id, p.size])); }, sizeWindow: (id, factor) => { const w = wins.find(x => x.id === id); if (w) sizeWindow(w, factor); }, get windowScales() { return winScale; }, get active() { return !panel.hidden || editing; }, get editing() { return editing; }, get layout() { return layout; } };
  loadWindowScales(); initWindows(); initPanels(); applyScale(); refresh();
})();
