'use strict';
// Everyone's activity is recorded by the server. Only the verified GM may read it.
(() => {
  const $ = id => document.getElementById(id), text = value => window.Locale?.translate(value) || value;
  let rows = [], next = null, pending = false, live = true;
  const categories = { login: 'Login', logout: 'Logout', level: 'Level change', travel: 'Travel', death: 'Death', trade: 'Trade', gm: 'GM command', security: 'Warning' };
  const node = (tag, value) => { const el = document.createElement(tag); if (value != null) el.textContent = value; return el; };
  function render() {
    $('activity-rows').replaceChildren(...rows.map(entry => {
      const tr = node('tr'), name = node('td', entry.actor);
      tr.dataset.event = entry.id; tr.dataset.warning = String(!!entry.warning); tr.dataset.category = entry.category;
      name.dataset.playerName = '';
      tr.append(node('td', new Date(entry.at).toLocaleString()), name, node('td', text(categories[entry.category] || entry.category)), node('td', text(entry.details)));
      return tr;
    }));
    $('activity-status').textContent = rows.length ? text('Showing {0} events').replace('{0}', rows.length) : text('No activity yet.');
    $('activity-more').hidden = !next; $('activity-more').disabled = pending;
    $('activity-refresh').disabled = pending;
  }
  async function load(more = false) {
    if (pending || !window.Online?.gm) return;
    pending = true; $('activity-status').textContent = text('Loading…');
    const reply = await window.GM.request({ op: 'gm_activity', before: more ? next : null,
      query: $('activity-query').value, category: $('activity-category').value, warnings: $('activity-warnings').checked });
    pending = false;
    if (!window.Online?.gm) { reset(); return; }
    if (!reply.ok) { $('activity-status').textContent = text(reply.error || 'Activity log is unavailable.'); return; }
    rows = more ? [...rows, ...reply.result.rows] : reply.result.rows; next = reply.result.next;
    render();
  }
  function reset() { rows = []; next = null; $('activity-rows').replaceChildren(); $('activity-panel').hidden = true; }
  function close() { $('activity-panel').hidden = true; window.Field?.setPaused(false); }
  function open() {
    if (!window.Online?.gm) return false;
    $('activity-panel').hidden = false; window.Field?.setPaused(true); live = true; load(); return true;
  }
  $('activity-open').addEventListener('click', open); $('activity-close').addEventListener('click', close);
  $('activity-refresh').addEventListener('click', () => { live = true; load(); });
  $('activity-more').addEventListener('click', () => { live = false; load(true); });
  $('activity-filter').addEventListener('submit', event => { event.preventDefault(); live = true; load(); });
  for (const id of ['activity-category', 'activity-warnings']) $(id).addEventListener('change', () => { live = true; load(); });
  $('activity-panel').addEventListener('click', event => { if (event.target === $('activity-panel')) close(); });
  document.addEventListener('keydown', event => {
    if (!$('activity-panel').hidden && (window.Keys ? Keys.is(event, 'menu') : event.code === 'Escape')) { event.preventDefault(); event.stopPropagation(); close(); }
  }, true);
  setInterval(() => { if (!$('activity-panel').hidden && !document.hidden && live && $('activity-scroll').scrollTop < 20) load(); }, 5000);
  window.GMActivity = { open, close, reset };
})();
