'use strict';
(() => {
  const $ = id => document.getElementById(id), root = $('achievements-panel');
  const tr = text => window.Locale?.translate(text) || text;
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  let hero = null, data = null, signature = '', focus = null;
  function render() {
    if (!data || root.hidden) return;
    const key = JSON.stringify([data, $('achievements-filter').value, window.Locale?.language]);
    if (key === signature) return; signature = key;
    $('achievement-total').textContent = `${data.points} / ${data.maximum}`;
    const titles = $('achievement-title-select'), selected = data.selected;
    titles.replaceChildren(new Option(tr('No title'), ''));
    for (const a of data.entries) if (a.complete && a.title) titles.add(new Option(tr(a.title), a.id));
    titles.value = selected;
    const filter = $('achievements-filter').value, host = $('achievement-list');
    const scroll = host.scrollTop; host.replaceChildren();
    for (const a of data.entries.filter(a => !filter || (filter === 'complete' ? a.complete : !a.complete))) {
      const row = node('article', null, 'achievement-card'); row.dataset.achievement = a.id; row.dataset.complete = a.complete;
      const header = node('header'), name = node('h4', tr(a.name)), points = node('b', `${a.points} ${tr('points')}`);
      header.append(name, points); row.append(header, node('p', tr(a.description)));
      const progress = node('progress'); progress.max = a.target; progress.value = a.progress; progress.setAttribute('aria-label', tr(a.name));
      row.append(progress, node('small', `${a.progress} / ${a.target} · ${tr(a.complete ? 'Completed' : 'In progress')}`));
      if (a.title) row.append(node('small', `${tr('Title reward')}: ${tr(a.title)}`));
      if (a.mount) row.append(node('small', `${tr('Mount reward')}: ${tr(window.Mounts?.name(a.mount) || a.mount)}`));
      host.append(row);
    }
    if (!host.childElementCount) host.append(node('p', tr('No achievements in this view.')));
    host.scrollTop = scroll;
  }
  function refresh() { if (!root.hidden && window.Online?.connected) Online.send({ type: 'achievements' }); }
  function close() { root.hidden = true; window.Field?.setPaused(false); if (focus?.isConnected && !focus.closest('[hidden]')) focus.focus({ preventScroll: true }); else $('inventory-open').focus({ preventScroll: true }); }
  function open() {
    if (!window.Online?.connected) return;
    focus = document.activeElement; $('pause').hidden = true;
    root.hidden = false; signature = ''; window.Field?.setPaused(true); window.Settings?.applyScale();
    render(); refresh(); $('achievements-close').focus({ preventScroll: true });
  }
  $('p-achievements').addEventListener('click', open);
  $('character-achievements-open').addEventListener('click', () => { $('equipment').hidden = true; open(); });
  $('achievements-close').addEventListener('click', close);
  $('achievements-filter').addEventListener('change', render);
  $('achievement-title-select').addEventListener('change', event => Online.send({ type: 'select_title', achievement: event.target.value }));
  root.addEventListener('click', event => { if (event.target === root) close(); });
  document.addEventListener('keydown', event => {
    if (root.hidden) return;
    if (window.Keys ? Keys.is(event, 'menu') : event.code === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(); return; }
    if (event.key === 'Tab') {
      const controls = [$('achievements-close'), $('achievement-title-select'), $('achievements-filter'), $('achievement-list')];
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    event.stopPropagation();
  }, true);
  setInterval(refresh, 1500);
  window.Achievements = {
    open, close,
    reset() { hero = null; data = null; signature = ''; $('achievement-list').replaceChildren(); $('achievement-total').textContent = '…'; root.hidden = true; },
    receive(packet) { if (packet.character !== window.Online?.id) return; data = packet; render(); },
    update(own) {
      if (hero && hero.id !== own.id) this.reset(); hero = own;
      const suffix = tr(own.achievementTitle || '');
      const label = $('hud-name'), name = own.look.name + (suffix ? ' ' + suffix : '');
      if (label.textContent !== name) label.textContent = name; label.setAttribute('translate', 'no');
    },
    displayName(actor) { return (actor.look?.name || '') + (actor.achievementTitle ? ' ' + tr(actor.achievementTitle) : ''); },
  };
})();
