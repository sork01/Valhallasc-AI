'use strict';
// The same client works in Windows and Linux browsers. The Rust server hosts it.
(() => {
  const endpoint = new URL('ws', location.href);
  endpoint.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const storageKey = 'valhallasc.characters.v1:' + endpoint.href;
  let saved = { current: null, characters: [] };
  try { const raw = JSON.parse(localStorage.getItem(storageKey) || 'null'); if (raw && Array.isArray(raw.characters)) saved = raw; } catch (_) {}
  const persist = () => { try { localStorage.setItem(storageKey, JSON.stringify(saved)); } catch (_) { status('Character key could not be saved. Keep this window open.', false); } };
  // A logged-in account (game login or gunning.se SSO) keeps its characters on the server; only the session key and the
  // per-character UI layouts live here. Guests are the original flow above: a server-issued key per character.
  const accountKey = 'valhallasc.account.v1:' + endpoint.href;
  let acct = { session: null, name: null, kind: null, current: null, slots: {} };
  try { const raw = JSON.parse(localStorage.getItem(accountKey) || 'null'); if (raw && typeof raw === 'object') acct = { ...acct, ...raw, slots: raw.slots || {} }; } catch (_) {}
  const persistAccount = () => { try { localStorage.setItem(accountKey, JSON.stringify(acct)); } catch (_) {} };
  let mode = 'guest', accountList = [], accountMax = 5, accountGm = false, characterGm = false;
  // Where the current character's local layouts live: its guest slot, or its entry under the account.
  const layoutSlot = () => mode === 'account' ? (acct.current ? (acct.slots[acct.current] ||= {}) : null) : saved.characters.find(c => c.token === saved.current);
  const persistSlot = () => mode === 'account' ? persistAccount() : persist();
  let socket = null, generation = 0, active = false, callbacks = {}, look = null, retryTimer = 0, heartbeat = 0, failures = 0;
  let connected = false, id = null;
  const $ = name => document.getElementById(name);
  function status(text, ready) {
    $('network-status').textContent = text;
    $('network-status').dataset.state = ready ? 'online' : 'offline';
  }
  function log(text, name, channel) {
    const line = document.createElement('p');
    if (channel) line.className = 'chat-' + channel;
    if (name) { const label = document.createElement('b'); label.textContent = name + ': '; if (name.startsWith('[GM]')) label.className = 'gm'; line.append(label); }
    line.append(document.createTextNode(text)); $('chat-log').append(line);
    while ($('chat-log').children.length > 80) $('chat-log').firstElementChild.remove();
    $('chat-log').scrollTop = $('chat-log').scrollHeight;
    // Everything that is not a player's chat line is also kept on the System tab.
    if (!name) window.SystemLog?.add(text, channel === 'refused' ? 'sys-taken' : 'sys-note');
  }
  function overlay(text, fatal = false) {
    $('connection-overlay').hidden = false; $('connection-text').textContent = text;
    $('connection-retry').hidden = fatal;
  }
  function send(message) {
    if (!connected || socket?.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(message)); return true;
  }
  function connect() {
    clearTimeout(retryTimer); clearInterval(heartbeat);
    const currentGeneration = generation;
    connected = false;
    status('Connecting to Greenmeadow…', false); overlay('Connecting to the world…');
    const ws = new WebSocket(endpoint); socket = ws;
    let fatal = false;
    const joinTimeout = setTimeout(() => { if (!connected) ws.close(); }, 10000);
    ws.onopen = () => {
      if (!active || currentGeneration !== generation) { ws.close(); return; }
      ws.send(JSON.stringify(mode === 'account'
        ? { type: 'join', version: 1, session: acct.session, character: acct.current, look: acct.current ? null : look }
        : { type: 'join', version: 1, token: saved.current, look: saved.current ? null : look }));
    };
    ws.onmessage = event => {
      if (!active || currentGeneration !== generation) return;
      let packet; try { packet = JSON.parse(event.data); } catch (_) { return; }
      switch (packet.type) {
        case 'welcome': {
          clearTimeout(joinTimeout); connected = true; failures = 0; id = packet.id;
          const character = packet.snapshot.players.find(p => p.id === id);
          if (mode === 'account') { acct.current = packet.id; persistAccount(); }
          else if (packet.token) {
            saved.current = packet.token;
            saved.characters.push({ token: packet.token, look: character.look }); persist();
          }
          characterGm = character?.gm === true; window.GM?.onSelf(character);
          callbacks.onWelcome?.(packet);
          window.Social?.reset(); send({ type: 'social', command: { op: 'refresh' } });
          $('connection-overlay').hidden = true; $('chat-input').disabled = false;
          heartbeat = setInterval(() => send({ type: 'ping', nonce: Date.now() }), 5000);
          log('Welcome to Greenmeadow. E: character · B/I: bags · K: skills · 1–9, 0, -, =: skillbar · Q: quests · O: friends · P: party · F: talk · Enter: chat (/p for party).');
          break;
        }
        case 'snapshot': {
          if (!connected) break;
          const character = packet.players.find(p => p.id === id);
          const away = character?.zone > 0 ? WORLD_MAP.zones?.[character.zone - 1]?.name : null;
          status(`${away || (window.City?.inside(character?.x, character?.y) ? WORLD_MAP.city.name : 'Greenmeadow')} · ${packet.online} online`, true);
          const slot = mode === 'guest' ? saved.characters.find(c => c.token === saved.current) : null;
          if (character) window.GM?.onSelf(character);
          if (character && slot && JSON.stringify(slot.look) !== JSON.stringify(character.look)) { slot.look = character.look; persist(); }
          callbacks.onSnapshot?.(packet); break;
        }
        case 'event': window.SystemLog?.event(packet, id); callbacks.onEvent?.(packet); break;
        case 'dialogue': window.City?.dialogue(packet); break;
        case 'chat': window.Field?.bubble(packet.id, packet.text, packet.channel === 'party'); log(packet.text, packet.channel === 'party' ? `[Party] ${packet.name}` : packet.name, packet.channel); break;
        case 'system': log(packet.text); break;
        case 'notice': log(packet.text, null, packet.ok === false ? 'refused' : 'notice'); window.Social?.onNotice(packet); break;
        case 'debug': window.GM?.onReply(packet); break;
        case 'social': window.Social?.onState(packet); break;
        case 'roll': window.Rolls?.onPacket(packet); break;
        case 'party': window.Social?.onParty(packet.party); break;
        case 'who': window.Social?.onWho(packet.players); break;
        case 'error':
          log(packet.text); window.Rolls?.reopen();
          if (packet.code === 'auth') { acct.session = null; accountList = []; persistAccount(); }
          if (packet.fatal) { fatal = true; connected = false; overlay(packet.text, true); status('Unable to enter world', false); ws.close(); }
          break;
      }
    };
    ws.onerror = () => {};
    ws.onclose = () => {
      clearTimeout(joinTimeout);
      if (!active || currentGeneration !== generation) return;
      clearInterval(heartbeat);
      connected = false; characterGm = false; window.GM?.onSelf(null); window.Inventory?.hideTooltip(); window.Settings?.close(false); window.Skillbar?.close(false); window.Quests?.close(false); window.WorldMap?.close(false); window.Social?.reset(); window.Rolls?.reset(); window.City?.close(); $('equipment').hidden = true; $('chat-input').disabled = true; callbacks.onDisconnect?.();
      if (fatal) return;
      status('Disconnected · reconnecting…', false);
      overlay('Connection lost. Reconnecting to your character…');
      retryTimer = setTimeout(connect, Math.min(5000, 500 * 2 ** Math.min(failures++, 4)));
    };
  }
  window.Online = {
    start(options) {
      this.stop(); callbacks = options; look = options.look; active = true; failures = 0;
      $('chat').hidden = false; connect();
    },
    stop() {
      active = false; generation++; connected = false; id = null; window.Social?.reset(); window.Rolls?.reset();
      clearTimeout(retryTimer); clearInterval(heartbeat);
      socket?.close(); socket = null;
      $('chat').hidden = true; $('connection-overlay').hidden = true;
      $('network-status').textContent = 'Valhalla · Shared world';
    },
    newCharacter() { if (mode === 'account') { acct.current = null; persistAccount(); } else { saved.current = null; persist(); } },
    // Characters in the current mode as {key, look, level?}: a guest's key is its server key, an account's is the character id.
    select(key) {
      if (mode === 'account') {
        const entry = accountList.find(c => c.id === key); if (!entry) return null;
        acct.current = key; persistAccount(); return { ...entry.look };
      }
      const slot = saved.characters.find(c => c.token === key); if (!slot) return null;
      saved.current = key; persist(); return { ...slot.look };
    },
    get currentKey() { return mode === 'account' ? acct.current : saved.current; },
    // The same value under its original name: skillbar.js, inventory.js and the tests use it to notice a character change.
    get currentToken() { return mode === 'account' ? acct.current : saved.current; },
    get bagLayout() { return layoutSlot()?.bagLayout || null; },
    saveBagLayout(layout) { const slot = layoutSlot(); if (!slot) return; slot.bagLayout = [...layout]; persistSlot(); },
    get skillSlots() { return layoutSlot()?.skillSlots || null; },
    // The level the layout was last saved at: skills unlocked above it are placed into free slots.
    get skillLevel() { return layoutSlot()?.skillLevel; },
    saveSkillSlots(slots, level) {
      const slot = layoutSlot(); if (!slot) return;
      slot.skillSlots = [...slots]; if (level) slot.skillLevel = level; persistSlot();
    },
    get characters() {
      return mode === 'account' ? accountList.map(c => ({ key: c.id, look: { ...c.look }, level: c.level, gm: c.gm === true }))
        : saved.characters.map(c => ({ key: c.token, look: { ...c.look } }));
    },
    // ----- accounts -----
    get mode() { return mode; },
    useGuest() { mode = 'guest'; },
    useAccount() { mode = 'account'; },
    get account() { return acct.session ? { name: acct.name, kind: acct.kind, max: accountMax, gm: accountGm } : null; },
    // True while the character in the world is the administrator character; the server decides it, this only shows the console.
    get gm() { return characterGm; },
    log,
    async api(path, body) {
      try {
        const res = await fetch(new URL('api/' + path, location.href), {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', ...(acct.session && path !== 'login' && path !== 'register' ? { Authorization: 'Bearer ' + acct.session } : {}) },
          body: JSON.stringify(body ?? {}),
        });
        const data = await res.json().catch(() => null);
        return data || { ok: false, error: 'The server sent an unexpected answer.' };
      } catch (_) { return { ok: false, error: 'Could not reach the server.' }; }
    },
    // Adopts a successful login/session answer: the session key (when issued), the name and the character list.
    adopt(data) {
      if (!data?.ok) return data;
      if (data.session) { if (data.session !== acct.session) acct.current = null; acct.session = data.session; }
      acct.name = data.account.name; acct.kind = data.account.kind; accountMax = data.max || 5; accountGm = data.gm === true;
      accountList = data.characters || []; persistAccount(); return data;
    },
    async login(username, password) { return this.adopt(await this.api('login', { username, password })); },
    async register(username, password) { return this.adopt(await this.api('register', { username, password })); },
    async sso() { return this.adopt(await this.api('sso')); },
    // Checks the stored session and refreshes the character list. A rejected session is forgotten.
    async resume() {
      if (!acct.session) return null;
      const data = await this.api('session');
      if (data.ok) return this.adopt(data);
      if (data.error && !/reach|unexpected/.test(data.error)) { acct.session = null; accountList = []; persistAccount(); }
      return data;
    },
    async refreshCharacters() { return mode === 'account' ? this.resume() : null; },
    async deleteCharacter(id) {
      const data = this.adopt(await this.api('character/delete', { id }));
      if (data?.ok && acct.current === id) { acct.current = null; delete acct.slots[id]; persistAccount(); }
      return data;
    },
    async logout() {
      if (acct.session) await this.api('logout');
      acct = { ...acct, session: null, name: null, kind: null, current: null }; accountList = []; persistAccount();
    },
    get connected() { return connected; },
    get id() { return id; }, send,
  };
  $('chat-form').addEventListener('submit', event => {
    event.preventDefault(); const input = $('chat-input'), text = input.value.trim();
    if (text.startsWith('/') && (window.GM?.command(text) || window.Social?.command(text))) input.value = '';
    else if (text && send({ type: 'chat', text })) input.value = '';
    input.blur();
  });
  $('chat-input').addEventListener('focus', () => { window.Field?.clearInput(); send({ type: 'stop' }); });
  $('chat-input').addEventListener('keydown', event => {
    event.stopPropagation(); if (event.key === 'Escape') { event.preventDefault(); event.currentTarget.blur(); }
  });
  addEventListener('keydown', event => {
    // A button left focused by a mouse click must not swallow Enter (it would re-press the button instead of opening the chat box).
    if (event.key === 'Enter' && active && connected && !event.target.isContentEditable && !/^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) {
      event.preventDefault(); document.activeElement?.blur?.(); $('chat-input').focus();
    }
  });
  addEventListener('blur', () => { window.Field?.clearInput(); send({ type: 'stop' }); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { window.Field?.clearInput(); send({ type: 'stop' }); } });
  $('connection-retry').addEventListener('click', () => { generation++; socket?.close(); connect(); });
  $('connection-title').addEventListener('click', () => $('p-title').click());
  $('connection-new').addEventListener('click', () => $('p-new').click());
})();
