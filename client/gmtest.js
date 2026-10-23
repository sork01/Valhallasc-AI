'use strict';
// The game master's test menu: enter any dungeon at its door, final boss or a pack (with the dungeon's level, a gear set and
// four hired fighters), reset the copy, read or skip the enrage clock, start an arena gauntlet at any level and fight, and
// change difficulty multipliers. Every button sends one `debug` command through gm.js (the server runs it only for the
// verified GM character and logs it); nothing here is a security check. The multipliers live on the server, per dungeon
// copy or gauntlet run, in memory only. Everything that came from the network goes through textContent.
(() => {
  const TUNING = [
    ['pack_damage', 'Pack damage', 'dungeon'], ['boss_health', 'Boss health', 'dungeon'], ['enrage_start', 'Enrage start', 'dungeon'],
    ['opponent_health', 'Opponent health', 'gauntlet'], ['opponent_damage', 'Opponent damage', 'gauntlet'],
  ];
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text != null) n.textContent = text; if (cls) n.className = cls; return n; };
  let panel = null, info = null, status = null;
  const refs = {};

  const say = (text, bad) => { if (status) { status.textContent = text; status.dataset.bad = String(!!bad); } };
  async function send(command, okText) {
    const packet = await window.GM.request(command);
    if (packet.ok) say(okText ? okText(packet.result || {}) : 'Done.');
    else say(/unknown variant|invalid/i.test(packet.error || '') ? 'This server has no test menu yet (it needs the new release).' : (packet.error || 'Refused.'), true);
    return packet;
  }
  const select = (id, options) => {
    const s = node('select'); s.id = id;
    for (const [value, label] of options) { const o = node('option', label); o.value = value; s.append(o); }
    return s;
  };
  const check = (id, label) => {
    const l = node('label', null, 'gmtest-check'), c = node('input'); c.type = 'checkbox'; c.id = id;
    l.append(c, document.createTextNode(' ' + label));
    return [l, c];
  };
  const button = (text, onClick) => { const b = node('button', text, 'btn ghost'); b.type = 'button'; b.addEventListener('click', onClick); return b; };
  const row = (...children) => { const r = node('div', null, 'gmtest-row'); r.append(...children); return r; };

  function packs() { const d = info?.dungeons.find(d => String(d.zone) === refs.dungeon.value); return d ? d.packs : 0; }
  function fillPlaces() {
    const options = [['door', 'Door'], ['boss', 'Final boss']];
    for (let i = 1; i <= packs(); i++) options.push([`pack:${i - 1}`, `Pack ${i}`]);
    refs.at.replaceChildren(...options.map(([v, l]) => { const o = node('option', l); o.value = v; return o; }));
  }
  function fillTuning(t) {
    for (const [key, , scope] of TUNING) {
      const value = t?.[scope]?.[key], r = refs['t_' + key];
      r.input.disabled = value == null;
      r.input.value = value ?? 1;
      r.out.textContent = value == null ? '—' : `x${Number(value).toFixed(2)}`;
    }
  }
  function fill(data) {
    info = data;
    refs.dungeon.replaceChildren(...data.dungeons.map(d => { const o = node('option', `${d.name} · L${d.level}${d.sealed ? ' (sealed)' : ''}`); o.value = d.zone; return o; }));
    refs.level.replaceChildren(...data.gauntletLevels.map(l => { const o = node('option', `Level ${l}`); o.value = l; return o; }));
    refs.fight.replaceChildren(...Array.from({ length: data.fights }, (_, i) => { const o = node('option', `Fight ${i + 1} · ${data.classes[i]}`); o.value = i + 1; return o; }));
    fillPlaces();
    fillTuning(data.tuning);
  }
  async function refresh() {
    const packet = await window.GM.request({ op: 'gm_test_info' });
    if (!packet.ok) return say(/unknown variant|invalid/i.test(packet.error || '') ? 'This server has no test menu yet (it needs the new release).' : (packet.error || 'Refused.'), true);
    fill(packet.result);
    say('Ready. Every action is logged on the server.');
  }

  function build() {
    panel = node('div', null, 'pause'); panel.id = 'gmtest-panel'; panel.hidden = true;
    const win = node('section', null, 'rpg-window gmtest-window');
    win.setAttribute('role', 'dialog'); win.setAttribute('aria-modal', 'true'); win.setAttribute('aria-labelledby', 'gmtest-title');
    const head = node('header', null, 'rpg-titlebar');
    const title = node('h3', 'GM test menu'); title.id = 'gmtest-title';
    const close = node('button', '×', 'window-close'); close.type = 'button'; close.id = 'gmtest-close'; close.setAttribute('aria-label', 'Close the GM test menu');
    close.addEventListener('click', hide);
    head.append(node('span', '⚙', 'window-emblem'), title, close);
    const body = node('div', null, 'gmtest-body');

    // Dungeons
    const [lvl, lvlBox] = check('gmtest-level', 'Set my level to the dungeon\'s'), [mercs, mercBox] = check('gmtest-mercs', 'Four hired fighters');
    refs.dungeon = select('gmtest-dungeon', []); refs.at = select('gmtest-at', []);
    refs.gear = select('gmtest-gear', [['', 'Keep my gear'], ['green', 'Green set'], ['blue', 'Blue set'], ['purple', 'Purple set']]);
    refs.dungeon.addEventListener('change', fillPlaces);
    const enter = button('Enter', () => {
      const [at, n] = refs.at.value.split(':');
      send({ op: 'gm_dungeon_enter', zone: Number(refs.dungeon.value), at, pack: Number(n || 0), level: lvlBox.checked, gear: refs.gear.value || null, mercs: mercBox.checked },
        r => `In a copy at ${Math.round(r.x)}, ${Math.round(r.y)}; level ${r.level}${r.mercs ? `, ${r.mercs} hired` : ''}.`).then(refresh);
    });
    const dungeon = node('section', null, 'gmtest-section');
    dungeon.append(node('h4', 'Dungeon'), row(refs.dungeon, refs.at), row(refs.gear, lvl, mercs), row(enter,
      button('Reset copy', () => send({ op: 'gm_dungeon_reset' }, () => 'Copy reset: enemies back, everyone healed.').then(refresh)),
      button('Enrage clock', () => send({ op: 'gm_enrage', action: 'status' }, r => r.bosses.length ? r.bosses.map(b => `${b.kind} ${Math.round(b.fight)}/${Math.round(b.start ?? 0)} s${b.engaged ? '' : ' (idle)'}`).join(' · ') : 'No boss in this copy.')),
      button('Skip to enrage', () => send({ op: 'gm_enrage', action: 'skip' }, r => `${r.note} ${r.bosses.length} boss(es) moved.`))));

    // Gauntlet
    refs.level = select('gmtest-glevel', []); refs.fight = select('gmtest-gfight', []);
    const gauntlet = node('section', null, 'gmtest-section');
    gauntlet.append(node('h4', 'Arena gauntlet'), row(refs.level, refs.fight, button('Start', () => send({ op: 'gm_gauntlet', level: Number(refs.level.value), fight: Number(refs.fight.value) }, r => `Gauntlet level ${r.level}, fight ${r.fight} (${r.class}). No quest is touched.`).then(refresh))));

    // Tuning
    const tuning = node('section', null, 'gmtest-section');
    tuning.append(node('h4', 'Difficulty (this copy or run, memory only)'));
    for (const [key, label] of TUNING) {
      const input = node('input'); input.type = 'range'; input.min = '0.1'; input.max = '3'; input.step = '0.05'; input.value = '1'; input.id = 'gmtest-t-' + key;
      const out = node('output', 'x1.00');
      input.addEventListener('input', () => { out.textContent = `x${Number(input.value).toFixed(2)}`; });
      input.addEventListener('change', () => send({ op: 'gm_tune', key, value: Number(input.value) }, () => `${label} x${Number(input.value).toFixed(2)}.`).then(r => r.ok && fillTuning(r.result)));
      refs['t_' + key] = { input, out };
      tuning.append(row(node('label', label), input, out));
    }
    tuning.append(row(button('Reset multipliers', () => send({ op: 'gm_tune', key: 'reset', value: 0 }, () => 'Multipliers reset.').then(r => r.ok && fillTuning(r.result)))));

    status = node('p', 'Loading…', 'gmtest-status'); status.setAttribute('role', 'status');
    body.append(dungeon, gauntlet, tuning, status);
    win.append(head, body); panel.append(win);
    (document.getElementById('stage') || document.body).append(panel);
    panel.addEventListener('click', e => { if (e.target === panel) hide(); });
    document.addEventListener('keydown', e => {
      if (panel.hidden) return;
      if (window.Keys ? Keys.is(e, 'menu') : e.code === 'Escape') { e.preventDefault(); e.stopPropagation(); hide(); }
    }, true);
  }
  function show() { if (!panel) build(); panel.hidden = false; say('Loading…'); refresh(); }
  function hide() { if (panel) panel.hidden = true; }

  window.GMTest = { open: show, close: hide, toggle() { if (panel && !panel.hidden) hide(); else show(); } };
  document.addEventListener('DOMContentLoaded', () => document.getElementById('gmtest-open')?.addEventListener('click', () => window.GMTest.toggle()));
  if (document.readyState !== 'loading') document.getElementById('gmtest-open')?.addEventListener('click', () => window.GMTest.toggle());
})();
