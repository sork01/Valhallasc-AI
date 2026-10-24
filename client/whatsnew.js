'use strict';
// English-only release notes. Load before the game handlers so this dialog owns its keys.
(() => {
  const $ = id => document.getElementById(id);
  const root = $('whats-new'), panel = root.querySelector('.news-panel');
  const ownGrip = target => target?.closest?.('.win-grip[data-window="whats-new"]');
  const current = document.querySelector('.version').textContent.trim();
  const STORAGE = 'valhallasc.whats-new.v1';
  let seen = null, returning = false;
  try {
    seen = localStorage.getItem(STORAGE);
    returning = !!localStorage.getItem('valhallasc.save.v1');
  } catch (_) { /* A blocked store still allows reading the notes. */ }
  let notes = null, loading = null, previousFocus = null;
  const node = (tag, text) => { const el = document.createElement(tag); el.textContent = text; return el; };
  function remember() {
    seen = current;
    try { localStorage.setItem(STORAGE, current); } catch (_) {}
  }
  function welcome() {
    const body = document.createDocumentFragment();
    body.append(node('h3', 'Welcome to Valhalla Rumble!'), node('p', 'Explore a shared world, help people with their quests, and grow stronger with friends or hired fighters.'));
    const list = document.createElement('ul');
    const key = action => { const label = Keys.label(action, false); return node('kbd', label === 'unbound' ? 'no key set' : label); };
    const line = (...parts) => { const li = document.createElement('li'); li.append(...parts); list.append(li); };
    line('Move with ', key('moveUp'), ', ', key('moveLeft'), ', ', key('moveDown'), ' and ', key('moveRight'), ', or click the ground to walk there.');
    line('Click an enemy to keep attacking it, or press ', key('attack'), ' to attack. Use your learned skills from the bar at the bottom.');
    line('Begin in Greenmeadow. Follow the path to Alderhaven and talk to Linden for your first quests. Press ', key('talk'), ' near someone to talk, and ', key('quests'), ' to read your quests.');
    line('Open Settings, then Keyboard, whenever you want to change your keys.');
    body.append(list);
    return body;
  }
  function release(entry, target) {
    for (const [field, heading] of [['new', 'New'], ['changed', 'Changed'], ['removed', 'Removed']]) {
      if (!entry[field].length) continue;
      target.append(node('h3', heading));
      const list = document.createElement('ul');
      for (const text of entry[field]) list.append(node('li', text));
      target.append(list);
    }
  }
  async function loadNotes() {
    if (notes) return notes;
    if (!loading) loading = fetch('release-notes.txt', { cache: 'no-store' }).then(async response => {
      if (!response.ok) throw new Error('Release notes unavailable');
      const entries = await response.json();
      if (!Array.isArray(entries) || !entries.some(entry => entry.version === current) || entries.some(entry =>
        typeof entry.version !== 'string' || ['new', 'changed', 'removed'].some(field => !Array.isArray(entry[field]) || entry[field].some(text => typeof text !== 'string')))) throw new Error('Invalid release notes');
      notes = entries; return entries;
    }).finally(() => { loading = null; });
    return loading;
  }
  function open(firstVisit = false) {
    if (root.hidden) previousFocus = document.activeElement;
    $('news-title').textContent = current;
    $('news-label').textContent = firstVisit ? 'Welcome' : "What's new";
    const body = $('news-body'); body.replaceChildren();
    if (firstVisit) body.append(welcome());
    else {
      release(notes.find(entry => entry.version === current), body);
      const history = document.createElement('details'); history.className = 'news-history';
      history.append(node('summary', 'Older updates'));
      for (const entry of notes.filter(entry => entry.version !== current)) {
        const older = document.createElement('details');
        older.append(node('summary', entry.version));
        release(entry, older); history.append(older);
      }
      body.append(history);
    }
    body.scrollTop = 0; root.hidden = false;
    $('stage').classList.add('reading-news');
    // A held movement key must not carry on walking behind the window.
    window.Field?.clearInput();
    if (window.Online?.connected) Online.send({ type: 'stop' });
    window.Settings?.applyScale();
    $('news-close').focus({ preventScroll: true });
    remember();
  }
  function close() {
    if (root.hidden) return;
    root.hidden = true;
    $('stage').classList.remove('reading-news');
    if (previousFocus?.isConnected && !previousFocus.closest('[hidden]')) previousFocus.focus({ preventScroll: true });
  }
  async function showLatest() {
    try { await loadNotes(); open(); }
    catch (_) { /* Leave the game usable; the Settings row retries the next time. */ }
  }
  $('news-close').addEventListener('click', close);
  $('set-whats-new').addEventListener('click', showLatest);
  addEventListener('keymap-change', () => {
    if (!root.hidden && $('news-label').textContent === 'Welcome') $('news-body').replaceChildren(welcome());
  });
  addEventListener('keydown', event => {
    if (root.hidden) return;
    if (ownGrip(event.target) && (event.key.startsWith('Arrow') || event.key === '0')) return;
    event.stopImmediatePropagation();
    if (event.key === 'Escape' || event.key === 'Enter') {
      event.preventDefault(); if (!event.repeat) close();
    } else if (event.key === 'Tab') {
      const grip = document.querySelector('.win-grip[data-window="whats-new"]');
      const focusable = [...panel.querySelectorAll('button, summary, [tabindex="0"]'), grip].filter(el => el && !el.closest('[hidden]') && el.getClientRects().length);
      const index = focusable.indexOf(document.activeElement);
      event.preventDefault();
      focusable[(index + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length].focus();
    } else if (!event.key.startsWith('Arrow') && !['Home', 'End', 'PageUp', 'PageDown', ' '].includes(event.key)) event.preventDefault();
  }, true);
  addEventListener('keyup', event => { if (!root.hidden) event.stopImmediatePropagation(); }, true);
  // Keep programmatic focus and clicks on background controls inside the modal too.
  addEventListener('focusin', event => { if (!root.hidden && !root.contains(event.target) && !ownGrip(event.target)) $('news-close').focus({ preventScroll: true }); });
  addEventListener('pointerdown', event => {
    if (!root.hidden && !root.contains(event.target) && !ownGrip(event.target)) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  addEventListener('DOMContentLoaded', async () => {
    if (seen === current) return;
    if (!seen && !returning) { open(true); return; }
    await showLatest();
  }, { once: true });
  window.WhatsNew = { show: showLatest, close, get open() { return !root.hidden; } };
})();
