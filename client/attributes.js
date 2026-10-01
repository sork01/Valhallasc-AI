'use strict';
(() => {
  let character = null, signature = '', pending = false;
  const names = ['strength', 'agility', 'intellect', 'stamina', 'dexterity', 'accuracy'];
  const primary = { warrior: 'strength', assassin: 'agility', mage: 'intellect' };
  const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  const percent = n => `${Number(((n || 0) * 100).toFixed(1))}%`;
  function render() {
    const host = document.getElementById('character-attributes'); if (!host || !character) return;
    const c = character, best = primary[c.look.class], points = c.statPoints || 0;
    const descriptions = {
      strength: `+${best === 'strength' ? 2 : 0.5} attack, +0.2 defense`,
      agility: `+${best === 'agility' ? 2 : 0.5} attack, +0.5% crit (60% cap)`,
      intellect: `+${best === 'intellect' ? 2 : 0.5} attack, 1% faster recovery (30% cap)`,
      stamina: '+8 maximum health',
      dexterity: '+0.5% dodge (35% cap)',
      accuracy: '+0.5% hit (100% cap)',
    };
    const header = node('div', '', 'attribute-heading');
    header.append(node('b', 'Attributes · Per point'), node('span', `${points} point${points === 1 ? '' : 's'} available`, 'attribute-points'));
    const grid = node('div', '', 'attribute-grid');
    for (const stat of names) {
      const name = stat[0].toUpperCase() + stat.slice(1), row = node('div', '', 'attribute-row'); row.dataset.stat = stat;
      const label = node('div', '', 'attribute-label');
      label.append(node('b', `${name} ${c.attributes?.[stat] || 0}${stat === best ? ' ★' : ''}`), node('small', descriptions[stat]));
      const capped = (stat === 'accuracy' && c.attributes?.accuracy >= 20) || (stat === 'dexterity' && c.attributes?.dexterity >= 70);
      const add = node('button', capped ? '✓' : '+', 'attribute-add'); add.type = 'button'; add.setAttribute('aria-label', capped ? `${name} at maximum` : `Increase ${name}`); add.title = descriptions[stat];
      add.disabled = capped || pending || points === 0 || c.dead || !Online.connected;
      add.addEventListener('click', () => { if (Online.send({ type: 'allocate_stat', stat })) { pending = true; render(); } });
      row.append(label, add); grid.append(row);
    }
    host.replaceChildren(header, grid,
      node('p', `Hit ${percent(c.hitChance)} · Dodge ${percent(c.dodgeChance)} · Crit ${percent(c.critChance)} · Attack every ${Number((c.attackCooldown || 0).toFixed(2))}s`, 'attribute-derived'),
      node('small', '3 points per level · ★ Class specialty · Training is permanent', 'attribute-help'));
  }
  window.Attributes = {
    render,
    update(c) {
      const key = JSON.stringify([c.id, c.level, c.attributes, c.statPoints, c.dead, c.look.class, c.hitChance, c.dodgeChance, c.critChance, c.attackCooldown]);
      character = c; if (signature === key && !pending) return; signature = key; pending = false; render();
      dispatchEvent(new Event('character-stats-change'));
    },
  };
})();
