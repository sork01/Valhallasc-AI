'use strict';
// The sign-in and character-picker scenes. Three ways in: a game account (username + password), the gunning.se site
// SSO, or a guest (the original flow). Accounts keep their characters on the server; this file only drives the screens.
// Every string that came from the network or another player goes through textContent.
(() => {
  const $ = id => document.getElementById(id);
  const SSO_PENDING = 'valhallasc.sso.pending';
  let handlers = null, busy = false;

  function say(id, text, ok) { const node = $(id); node.textContent = text || ''; node.dataset.state = ok ? 'ok' : 'error'; }
  function setBusy(on) {
    busy = on;
    for (const id of ['login-submit', 'login-register', 'login-sso', 'login-guest', 'login-continue', 'login-logout']) $(id).disabled = on;
  }
  function renderLogin() {
    const account = Online.account;
    $('login-account').hidden = !account; $('login-form').hidden = !!account; $('login-sso').hidden = !!account;
    if (account) {
      $('login-name').textContent = account.name;
      $('login-kind').textContent = account.kind === 'sso' ? '(gunning.se)' : '';
    }
  }
  async function finish(data) {
    setBusy(false);
    if (!data?.ok) { renderLogin(); say('login-msg', data?.error || 'Could not sign in.'); return false; }
    $('login-pass').value = ''; say('login-msg', '');
    handlers.account(); handlers.show('chars');
    return true;
  }
  async function credentials(action) {
    if (busy) return;
    const username = $('login-user').value.trim(), password = $('login-pass').value;
    if (!username || !password) { say('login-msg', 'Enter a username and a password.'); return; }
    setBusy(true); say('login-msg', action === 'register' ? 'Creating your account…' : 'Signing in…', true);
    await finish(await Online[action](username, password));
  }
  async function sso() {
    if (busy) return;
    setBusy(true); say('login-msg', 'Checking your gunning.se login…', true);
    const data = await Online.sso();
    if (!data.ok && /not signed in/i.test(data.error || '')) {
      // Off to the site login; it sends the browser back here, and the next visit to this screen finishes the sign-in.
      try { sessionStorage.setItem(SSO_PENDING, '1'); } catch (_) {}
      say('login-msg', 'Opening the gunning.se login…', true);
      location.href = '/sso/?redirect=' + encodeURIComponent(location.pathname);
      return;
    }
    await finish(data);
  }

  function enter() {
    say('login-msg', ''); renderLogin(); setBusy(false);
    if (Online.account) {
      // The stored session may have lapsed; this also refreshes the character list.
      Online.resume().then(data => { if (data && !data.ok) { renderLogin(); if (!Online.account) say('login-msg', 'Your login expired. Please sign in again.'); } else renderLogin(); });
    }
    let returning = false;
    try { returning = sessionStorage.getItem(SSO_PENDING) === '1'; sessionStorage.removeItem(SSO_PENDING); } catch (_) {}
    if (returning && !Online.account) sso();
    else (Online.account ? $('login-continue') : $('login-user')).focus({ preventScroll: true });
  }

  function renderChars() {
    const account = Online.account, list = $('chars-list');
    if (!account) { handlers.show('login'); return; }
    const entries = Online.characters, ordinary = entries.filter(c => !c.gm).length, hasGm = entries.some(c => c.gm);
    $('chars-who').textContent = `${account.name}${account.kind === 'sso' ? ' (gunning.se)' : ''} · ${ordinary} of ${account.max} characters${hasGm ? ' + [GM]' : ''}`;
    list.replaceChildren(...entries.map(c => {
      const row = document.createElement('div'); row.className = c.gm ? 'char-row gm' : 'char-row';
      const play = document.createElement('button'); play.type = 'button'; play.className = 'btn ghost char-play';
      play.textContent = `${c.look.name} · Lv ${c.level} ${c.look.class}`;
      play.addEventListener('click', () => { const look = Online.select(c.key); if (look) handlers.play(look); });
      const del = document.createElement('button'); del.type = 'button'; del.className = 'btn ghost char-del';
      del.textContent = 'Delete'; del.setAttribute('aria-label', 'Delete ' + c.look.name);
      let armed = 0;
      del.addEventListener('click', async () => {
        if (!armed) { armed = setTimeout(() => { armed = 0; del.textContent = 'Delete'; }, 4000); del.textContent = 'Really?'; return; }
        clearTimeout(armed); del.disabled = true;
        const data = await Online.deleteCharacter(c.key);
        if (!data.ok) say('chars-msg', data.error || 'Could not delete that character.');
        else say('chars-msg', `${c.look.name} was deleted.`, true);
        renderChars();
      });
      row.append(play, del); return row;
    }));
    if (!entries.length) list.textContent = 'No characters yet. Create your first one.';
    $('chars-new').disabled = ordinary >= account.max;
    // The administrator character is a sixth, separate slot that only the game master's login is offered.
    $('chars-gm').hidden = !(account.gm && !hasGm);
  }
  function enterChars() {
    say('chars-msg', ''); renderChars();
    // Fresh from the server: another window may have added or deleted characters.
    Online.resume().then(data => { if (data?.ok) renderChars(); else if (!Online.account) { handlers.show('login'); } });
    ($('chars-list').querySelector('.char-play') || $('chars-new')).focus({ preventScroll: true });
  }

  window.Account = {
    init(h) {
      handlers = h;
      $('login-form').addEventListener('submit', event => { event.preventDefault(); credentials('login'); });
      $('login-register').addEventListener('click', () => credentials('register'));
      $('login-sso').addEventListener('click', sso);
      $('login-guest').addEventListener('click', () => { if (!busy) handlers.guest(); });
      $('login-continue').addEventListener('click', () => { if (!busy) { handlers.account(); handlers.show('chars'); } });
      $('login-logout').addEventListener('click', async () => { if (busy) return; setBusy(true); await Online.logout(); setBusy(false); renderLogin(); say('login-msg', 'Logged out.', true); });
      $('login-back').addEventListener('click', () => handlers.show('splash'));
      $('chars-new').addEventListener('click', () => { if (!$('chars-new').disabled) handlers.create(); });
      $('chars-gm').addEventListener('click', () => { if (!$('chars-gm').hidden) handlers.createGm(); });
      $('chars-back').addEventListener('click', () => handlers.show('login'));
    },
    enter, enterChars, renderChars,
  };
})();
