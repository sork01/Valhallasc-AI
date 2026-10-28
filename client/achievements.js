'use strict';
(() => {
  const $ = id => document.getElementById(id), root = $('achievements-panel');
  const tr = text => window.Locale?.translate(text) || text;
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  let hero = null, data = null, signature = '', focus = null, category = '';
  const toast = $('achievement-toast'), pending = [], celebrated = new Set();
  let celebrationTimer = 0, batchTimer = 0;
  function celebrate() {
    clearTimeout(batchTimer);
    if (!pending.length || !toast.hidden) return;
    if (document.hidden || !$('levelup-banner').hidden) { batchTimer = setTimeout(celebrate, 250); return; }
    const batch = pending.splice(0), points = batch.reduce((sum, a) => sum + a.points, 0);
    $('achievement-toast-heading').textContent = tr(batch.length === 1 ? 'Achievement unlocked' : 'Achievements unlocked');
    $('achievement-toast-name').textContent = batch.slice(0, 2).map(a => tr(a.name)).join(' · ');
    $('achievement-toast-extra').textContent = batch.length > 2 ? `+${batch.length - 2} ${tr('more achievements')}` : '';
    $('achievement-toast-points').textContent = `+${points} ${tr('points')}`;
    toast.hidden = false; toast.classList.remove('celebrate'); void toast.offsetWidth; toast.classList.add('celebrate');
    window.AchievementAudio?.play();
    celebrationTimer = setTimeout(() => { toast.hidden = true; toast.classList.remove('celebrate'); celebrate(); }, 4800);
  }
  function onNotice(packet) {
    // This exact English notice is emitted only for a newly earned server achievement.
    // Consume the original packet before chat localization; ordinary chat never enters here.
    if (!window.Online?.connected || packet.ok !== true) return;
    const match = /^Achievement earned: (.+) \(\+(\d+) points\)\.$/.exec(packet.text || '');
    if (!match || celebrated.has(match[1])) return;
    celebrated.add(match[1]); pending.push({ name: match[1], points: Number(match[2]) });
    clearTimeout(batchTimer); batchTimer = setTimeout(celebrate, 200);
  }
  function render() {
    if (!data || root.hidden) return;
    const key = JSON.stringify([data, category, $('achievements-filter').value, window.Locale?.language]);
    if (key === signature) return; signature = key;
    $('achievement-total').textContent = `${data.points} / ${data.maximum}`;
    const titles = $('achievement-title-select'), selected = data.selected;
    titles.replaceChildren(new Option(tr('No title'), ''));
    for (const a of data.entries) if (a.complete && a.title) titles.add(new Option(tr(a.title), a.id));
    titles.value = selected;
    const categories = ['', ...new Set(data.entries.map(a => a.category))], navigation = $('achievement-categories');
    for (const [index, value] of categories.entries()) {
      let button = navigation.children[index];
      if (!button) {
        button = node('button', null, 'achievement-category'); button.type = 'button';
        button.append(node('span'), node('small')); navigation.append(button);
      }
      button.dataset.category = value; button.setAttribute('aria-pressed', String(category === value));
      const entries = data.entries.filter(a => !value || a.category === value);
      const label = tr(value || 'All achievements'), count = `${entries.filter(a => a.complete).length} / ${entries.length}`;
      if (button.firstChild.textContent !== label) button.firstChild.textContent = label;
      if (button.lastChild.textContent !== count) button.lastChild.textContent = count;
      button.setAttribute('aria-label', `${label} · ${count} ${tr('Completed')}`);
    }
    while (navigation.children.length > categories.length) navigation.lastChild.remove();
    const filter = $('achievements-filter').value, host = $('achievement-list');
    const scroll = host.scrollTop; host.replaceChildren();
    for (const value of categories.slice(1).filter(value => !category || category === value)) {
      const entries = data.entries.filter(a => a.category === value && (!filter || (filter === 'complete' ? a.complete : !a.complete)));
      if (!entries.length) continue;
      const group = node('section', null, 'achievement-group'), heading = node('h4', tr(value), 'achievement-group-heading');
      heading.id = 'achievement-group-' + categories.indexOf(value); group.setAttribute('aria-labelledby', heading.id);
      group.append(heading);
      for (const a of entries) {
        const row = node('article', null, 'achievement-card'); row.dataset.achievement = a.id; row.dataset.complete = a.complete;
        for (const corner of ['tl', 'tr', 'br', 'bl']) {
          const ornament = node('span', null, 'achievement-corner'); ornament.dataset.corner = corner;
          ornament.setAttribute('aria-hidden', 'true'); row.append(ornament);
        }
        const header = node('header'), name = node('h4', tr(a.name)), points = node('b', `${a.points} ${tr('points')}`);
        header.append(name, points); row.append(header, node('p', tr(a.description)));
        const progress = node('progress'); progress.max = a.target; progress.value = a.progress; progress.setAttribute('aria-label', tr(a.name));
        row.append(progress, node('small', `${a.progress} / ${a.target} · ${tr(a.complete ? 'Completed' : 'In progress')}`));
        if (a.title) row.append(node('small', `${tr('Title reward')}: ${tr(a.title)}`));
        if (a.mount) row.append(node('small', `${tr('Mount reward')}: ${tr(window.Mounts?.name(a.mount) || a.mount)}`));
        group.append(row);
      }
      host.append(group);
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
  $('achievements-filter').addEventListener('change', () => { $('achievement-list').scrollTop = 0; render(); });
  $('achievement-categories').addEventListener('click', event => {
    const button = event.target.closest('button'); if (!button) return;
    category = button.dataset.category; $('achievement-list').scrollTop = 0; render();
  });
  $('achievement-title-select').addEventListener('change', event => Online.send({ type: 'select_title', achievement: event.target.value }));
  root.addEventListener('click', event => { if (event.target === root) close(); });
  document.addEventListener('keydown', event => {
    if (root.hidden) return;
    if (window.Keys ? Keys.is(event, 'menu') : event.code === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(); return; }
    if (event.key === 'Tab') {
      const controls = [$('achievements-close'), $('achievement-title-select'), $('achievements-filter'), ...$('achievement-categories').children, $('achievement-list')];
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    event.stopPropagation();
  }, true);
  setInterval(refresh, 1500);
  window.Achievements = {
    open, close, onNotice,
    reset() {
      clearTimeout(celebrationTimer); clearTimeout(batchTimer); pending.length = 0; celebrated.clear();
      toast.hidden = true; toast.classList.remove('celebrate');
      hero = null; data = null; signature = ''; category = ''; $('achievement-categories').replaceChildren(); $('achievement-list').replaceChildren(); $('achievement-total').textContent = '…'; root.hidden = true;
    },
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
