'use strict';
(() => {
  let character = null, signature = '', pending = false, previewOpen = false;
  const names = ['strength', 'agility', 'intellect', 'stamina', 'dexterity', 'accuracy'];
  const primary = { warrior: 'strength', assassin: 'agility', mage: 'intellect', priest: 'intellect', hunter: 'agility' };
  const weights = {warrior:[40,5,0,30,10,15],mage:[0,5,45,25,10,15],assassin:[10,40,0,20,15,15],priest:[0,5,45,30,5,15],hunter:[5,40,0,25,15,15]};
  const reasons = {warrior:'Strength and stamina lead, with accuracy and defense as support.',mage:'Intellect leads for spell power and mana; stamina keeps you alive.',assassin:'Agility leads for attack and critical hits, with dodge and stamina.',priest:'Intellect and stamina support healing and survival.',hunter:'Agility leads bow damage; stamina and accuracy support safe shots.'};
  const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
  const percent = n => `${Number(((n || 0) * 100).toFixed(1))}%`;
  function recommended(c) {
    const spent = Object.fromEntries(names.map(name => [name, 0]));
    const w = weights[c.look.class] || weights.warrior;
    const values = names.map(name => (c.attributes?.[name] || 0) + (c.gearAttributes?.[name] || 0) + (c.passiveAttributes?.[name] || 0));
    const trained = names.map(name => c.attributes?.[name] || 0);
    for (let point = 0; point < (c.statPoints || 0); point++) {
      const total = values.reduce((sum, value) => sum + value, 0) + c.statPoints - point;
      let best = -1;
      for (let i = 0; i < names.length; i++) {
        if (!w[i] || (i === 4 && (trained[i] >= 70 || values[i] >= 70)) || (i === 5 && (trained[i] >= 20 || values[i] >= 20))) continue;
        const score = total * w[i] - values[i] * 100;
        if (best < 0 || score > total * w[best] - values[best] * 100 ||
          (score === total * w[best] - values[best] * 100 && w[i] > w[best])) best = i;
      }
      if (best < 0) break;
      spent[names[best]]++; values[best]++; trained[best]++;
    }
    return spent;
  }
  function render() {
    const host = document.getElementById('character-attributes'); if (!host || !character) return;
    const c = character, best = primary[c.look.class], points = c.statPoints || 0;
    const descriptions = {
      strength: `+${best === 'strength' ? 2 : 0.5} attack, +0.2 defense`,
      agility: `+${best === 'agility' ? 2 : 0.5} attack, +0.5% crit (60% cap)`,
      intellect: `+${best === 'intellect' ? 2 : 0.5} attack, 1% faster recovery (30% cap)${c.resourceType === 'mana' ? ", +5 maximum mana" : ""}`,
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
      const trained = c.attributes?.[stat] || 0, gear = c.gearAttributes?.[stat] || 0, passive = c.passiveAttributes?.[stat] || 0;
      const parts = [gear ? `${gear} gear` : '', passive ? `${passive} passive` : ''].filter(Boolean);
      label.append(node('b', `${name} ${trained + gear + passive}${parts.length ? ` (${trained} trained + ${parts.join(' + ')})` : ''}${stat === best ? ' ★' : ''}`), node('small', descriptions[stat]));
      const capped = (stat === 'accuracy' && c.attributes?.accuracy >= 20) || (stat === 'dexterity' && c.attributes?.dexterity >= 70);
      const add = node('button', capped ? '✓' : '+', 'attribute-add'); add.type = 'button'; add.setAttribute('aria-label', capped ? `${name} at maximum` : `Increase ${name}`); add.title = descriptions[stat];
      add.disabled = capped || pending || points === 0 || c.dead || !Online.connected;
      add.addEventListener('click', () => { if (Online.send({ type: 'allocate_stat', stat })) { pending = true; render(); } });
      row.append(label, add); grid.append(row);
    }
    const actions = node('div', '', 'attribute-recommended');
    const recommend = node('button', 'Recommended', 'attribute-recommend'); recommend.type = 'button';
    recommend.title = `${c.look.class[0].toUpperCase()}${c.look.class.slice(1)}: ${reasons[c.look.class]} Considers worn gear, passives and points already trained.`;
    recommend.disabled = !points || pending || c.dead || !Online.connected;
    recommend.addEventListener('click', () => { previewOpen = true; render(); });
    actions.append(recommend);
    if (!points) actions.append(node('small', 'No unspent stat points. Level up to earn more.', 'attribute-no-points'));
    if (previewOpen && points) {
      const spent = recommended(c);
      const summary = names.filter(name => spent[name]).map(name => `${name[0].toUpperCase()}${name.slice(1)} +${spent[name]}`).join(' · ');
      const panel = node('div', '', 'attribute-preview');
      panel.append(node('b', `Spend ${points} point${points === 1 ? '' : 's'}?`), node('p', summary || 'No eligible stats.'));
      const confirm = node('button', 'Confirm recommended', 'attribute-recommend-confirm'); confirm.type = 'button'; confirm.disabled = pending || !summary;
      confirm.addEventListener('click', () => { if (Online.send({type:'allocate_recommended'})) { pending = true; previewOpen = false; render(); } });
      const cancel = node('button', 'Cancel', 'attribute-recommend-cancel'); cancel.type = 'button';
      cancel.addEventListener('click', () => { previewOpen = false; render(); });
      panel.append(confirm, cancel); actions.append(panel);
    }
    host.replaceChildren(header, grid, actions,
      node('p', `Hit ${percent(c.hitChance)} · Dodge ${percent(c.dodgeChance)} · Crit ${percent(c.critChance)} · Attack every ${Number((c.attackCooldown || 0).toFixed(2))}s`, 'attribute-derived'),
      node('small', '3 points per level · ★ Class specialty · A city steward can reset trained points for gold', 'attribute-help'));
    if (c.raidSupport) host.append(node('p', `Raid strength: +${c.raidSupport.attackPercent}% attack · ${c.raidSupport.damageReductionPercent}% damage reduction (${c.raidSupport.others} allies)`, 'attribute-derived raid-strength'));
  }
  window.Attributes = {
    render,
    update(c) {
      const key = JSON.stringify([c.id, c.level, c.attributes, c.gearAttributes, c.passiveAttributes, c.statPoints, c.dead, c.look.class, c.hitChance, c.dodgeChance, c.critChance, c.attackCooldown, c.raidSupport]);
      character = c; if (signature === key) return; signature = key; pending = false; previewOpen = false; render();
      dispatchEvent(new Event('character-stats-change'));
    },
    error() { if (pending) { pending = false; render(); } },
  };
})();
