'use strict';
// The Mounts list in the Character window: every mount with its route, level and price or drop rate, the unlock hint
// for the ones not owned, and a Select button on the owned ones. The server owns ownership and the selection
// (docs/mounts.md); this only shows them and sends `select_mount`.
(() => {
  const MOUNTS = [
    { id: 'horse', name: 'Riding horse', level: 50, route: 'Buy from Stable-hand Greta in Skaldholm', cost: '500,000 gold' },
    { id: 'raptor', name: 'Raptor', level: 75, route: 'Quest chain The Banyan Run, from Mara Vines in the Tanglecrown', cost: 'no gold fee' },
    { id: 'lizard', name: 'Lizard', level: 80, route: 'Buy from the Dune-wrangler in the Lapis Erg hub', cost: '160,000 gold' },
    { id: 'sabertooth', name: 'Sabertooth', level: 95, route: 'Rare drop: Sabertooth Whistle from the Rimesaber in the Yearwheel', cost: '4% per kill' },
    { id: 'gryphon', name: 'Gryphon', level: 95, route: 'Dungeon reward: Gryphon Egg from the Thunderheart Gate\'s final boss, hatched by Oren Highwind in the Cairnspine', cost: '3% per kill and 250,000 gold to hatch' },
  ];
  const byId = Object.fromEntries(MOUNTS.map(m => [m.id, m]));
  let hero = null, signature = '';
  const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  function render() {
    const host = document.getElementById('character-mounts'); if (!host || !hero) return;
    const owned = hero.mounts || [], selected = hero.mount || '';
    const key = JSON.stringify([owned, selected, hero.level, !!hero.dead, !!hero.sparkTravel]);
    if (key === signature && host.childElementCount) return;
    signature = key;
    host.replaceChildren(node('h4', 'Mounts'));
    host.append(node('small', owned.length ? `${Keys.label('mount', false)} and the Mount button summon the selected mount. All mounts ride at 2× speed.` : `Own a mount to ride at 2× speed (${Keys.label('mount', false)}).`, 'mount-help'));
    for (const m of MOUNTS) {
      const has = owned.includes(m.id), card = node('article', '', 'mount-card');
      card.dataset.mount = m.id; card.dataset.owned = has; card.dataset.selected = has && m.id === selected;
      const text = node('div', '', 'mount-text');
      text.append(node('b', m.name), node('small', has ? (m.id === selected ? 'Owned · selected' : 'Owned') : `Level ${m.level} · ${m.route} · ${m.cost}`));
      card.append(text);
      if (has) {
        const pick = node('button', m.id === selected ? 'Selected' : 'Select', 'window-tool mount-select'); pick.type = 'button';
        pick.disabled = m.id === selected || !window.Online?.connected;
        pick.setAttribute('aria-label', `Select the ${m.name.toLowerCase()}`);
        pick.addEventListener('click', () => window.Online?.send({ type: 'select_mount', mount: m.id }));
        card.append(pick);
      } else if (hero.level < m.level) card.title = `Reach level ${m.level} first`;
      host.append(card);
    }
  }
  window.Mounts = {
    MOUNTS, name: id => byId[id]?.name || 'Mount',
    update(own) { hero = own; render(); },
    render,
  };
})();
