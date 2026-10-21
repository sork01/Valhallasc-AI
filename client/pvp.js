'use strict';
// PvP controls display server state. Consent, matchmaking and combat are checked by Rust.
(() => {
  let state = { flag: false, requests: [], duel: null, queue: null, arena: null, gauntlet: null };
  let available = false;
  // The arena gauntlet banner counts down from the seconds the server sent with the packet.
  let gauntletStamp = 0, gauntletTimer = 0, gauntletTarget = null;
  const gauntletBanner = () => document.getElementById('gauntlet-banner');
  const capital = word => word ? word[0].toUpperCase() + word.slice(1) : '';
  function paintGauntlet() {
    const g = state.gauntlet, banner = gauntletBanner();
    if (!g) { banner.hidden = true; clearInterval(gauntletTimer); gauntletTimer = 0; return; }
    const left = Math.max(0, Math.ceil((g.countdown ?? g.ends ?? 0) - (Date.now() - gauntletStamp) / 1000));
    document.getElementById('gauntlet-title').textContent = `Arena gauntlet · Fight ${g.fight} of ${g.of}`;
    document.getElementById('gauntlet-line').textContent = g.opponent ? `${g.opponent.name} · ${left}s left` : `Next: ${capital(g.next)} · starts in ${left}s`;
    banner.hidden = false;
    // Aim at the opponent as soon as the snapshot lists it, so Space or J swings at it.
    if (gauntletTarget && window.Field?.remotePlayers?.some(p => p.id === gauntletTarget)) { window.Field.targetPlayer(gauntletTarget); gauntletTarget = null; }
  }
  function showGauntlet(previous) {
    const g = state.gauntlet;
    gauntletStamp = Date.now();
    // The giver's dialogue is still open when the run starts: the hero is in the Arena now.
    if (g && !previous) window.City?.close?.();
    if (g?.opponent && g.opponent.id !== previous?.opponent?.id) gauntletTarget = g.opponent.id;
    paintGauntlet();
    if (g && !gauntletTimer) gauntletTimer = setInterval(paintGauntlet, 250);
  }
  document.getElementById('gauntlet-leave')?.addEventListener('click', () => send({ op: 'arena_leave' }));
  const send = command => Online.send({ type: 'pvp', command });
  function render(body, button, el) {
    body.append(el('h4', 'World PvP', 'social-title'));
    body.append(el('p', state.flag ? 'Your PvP flag is on. Other flagged players can fight you outside sanctuaries.' : 'Your PvP flag is off.', 'social-note'));
    body.append(button(state.flag ? 'Turn PvP off' : 'Turn PvP on', 'pvp-flag', () => send({ op: 'flag', enabled: !state.flag })));
    if (state.requests.length) {
      body.append(el('h4', 'Duel challenges', 'social-title'));
      for (const request of state.requests) {
        const row = el('div', '', 'social-row');
        row.append(el('span', `${request.name} challenged you (${request.left}s left).`, 'social-who'),
          button('Accept', `duel-accept:${request.id}`, () => send({ op: 'duel_accept', id: request.id })),
          button('Decline', `duel-decline:${request.id}`, () => send({ op: 'duel_decline', id: request.id })));
        body.append(row);
      }
    }
    if (state.duel) body.append(el('p', `Dueling ${state.duel.name} inside a ${state.duel.range}-tile ring. First to one HP loses. ${state.duel.returnIn == null ? '' : `Return in ${state.duel.returnIn}s or forfeit.`}`, 'social-note'),
      button('End duel', 'duel-cancel', () => send({ op: 'duel_cancel' }), 'window-tool danger'));
    body.append(el('h4', 'Arena', 'social-title'));
    if (state.arena) body.append(el('p', `${state.arena.size}v${state.arena.size} match in progress. Defeat the whole opposing team.`, 'social-note'),
      button('Forfeit match', 'arena-leave', () => send({ op: 'arena_leave' }), 'window-tool danger'));
    else if (state.queue) body.append(el('p', `Queued for ${state.queue}v${state.queue}.`, 'social-note'),
      button('Leave queue', 'arena-leave', () => send({ op: 'arena_leave' })));
    else {
      body.append(el('p', 'For 2v2 or 3v3, form a party of exactly that size. The leader queues the team.', 'social-note'));
      for (const size of [1, 2, 3]) body.append(button(`Queue ${size}v${size}`, `arena-${size}`, () => send({ op: 'arena_queue', size })));
    }
    body.append(el('p', `Select an opponent in the world or the Online list, then press ${Keys.label('attack')} to attack.`, 'social-note'));
  }
  window.Pvp = {
    send, render,
    duel(id) { if (!available) return; send({ op: 'duel_request', id }); window.Social?.show('pvp'); },
    target(id) { window.Social?.close(); window.Field?.targetPlayer(id); },
    canAttack(id, otherFlag) { return !!(state.arena || state.gauntlet?.opponent?.id === id || state.duel?.id === id || (state.flag && otherFlag)); },
    onPacket(packet) {
      available = true; document.getElementById('social-tab-pvp').hidden = false;
      const previous = state.gauntlet;
      state = { ...state, ...packet };
      showGauntlet(previous);
      const warning = document.getElementById('pvp-duel-warning');
      warning.hidden = state.duel?.returnIn == null && state.duel?.opponentReturnIn == null;
      if (!warning.hidden) warning.textContent = state.duel.returnIn == null ? `${state.duel.name} has ${state.duel.opponentReturnIn}s to return to the duel area.` : `Return to the duel area in ${state.duel.returnIn}s or forfeit!`;
      window.Social?.refreshPvp();
    },
    reset() { state = { flag: false, requests: [], duel: null, queue: null, arena: null, gauntlet: null }; paintGauntlet(); available = false; document.getElementById('social-tab-pvp').hidden = true; document.getElementById('pvp-duel-warning').hidden = true; },
    get available() { return available; },
    get state() { return state; },
  };
})();
