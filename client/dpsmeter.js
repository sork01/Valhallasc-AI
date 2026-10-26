'use strict';
// The server owns damage totals, encounter time and resets. This panel only displays them.
(() => {
  const $ = id => document.getElementById(id);
  let data = null, painted = -Infinity;
  const text = value => window.Locale?.translate(value) || value;
  const number = value => Math.round(Number(value) || 0).toLocaleString();
  const node = (tag, value) => { const el = document.createElement(tag); if (value != null) el.textContent = value; return el; };
  function render(force = false) {
    const host = $('dps-meter'), enabled = window.Prefs?.dpsMeter !== false;
    host.hidden = !enabled || !data;
    $('dps-toggle').setAttribute('aria-pressed', String(enabled));
    if (host.hidden || (!force && performance.now() - painted < 450)) return;
    painted = performance.now();
    const elapsed = Math.floor(data.elapsed || 0), time = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`;
    const damage = data.rows.some(row => row.damage > 0);
    $('dps-status').textContent = damage ? `${text(data.active ? 'Current fight' : 'Last fight')} · ${time}` : text('Waiting for combat');
    const most = Math.max(1, ...data.rows.map(row => row.damage));
    $('dps-rows').replaceChildren(...data.rows.map(row => {
      const tr = node('tr'), who = node('td'), name = node('span', row.name);
      tr.dataset.id = row.id; tr.dataset.hired = String(!!row.hired);
      name.dataset.playerName = ''; name.title = row.name;
      const bar = node('i'); bar.style.width = `${Math.max(0, Math.min(100, row.damage / most * 100))}%`;
      who.append(bar, name); tr.append(who, node('td', number(row.dps)), node('td', number(row.damage)));
      return tr;
    }));
  }
  const toggle = () => { window.Prefs?.set({ dpsMeter: window.Prefs?.dpsMeter === false }); render(true); };
  $('dps-toggle').addEventListener('click', toggle);
  $('dps-close').addEventListener('click', () => { window.Prefs?.set({ dpsMeter: false }); render(true); });
  window.addEventListener('prefs-change', () => render(true));
  window.DpsMeter = {
    update(value) { data = value && Array.isArray(value.rows) ? value : null; render(); },
    reset() { data = null; render(true); },
  };
})();
