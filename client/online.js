'use strict';
// The same client works in Windows and Linux browsers. The Rust server hosts it.
(() => {
  const endpoint = new URL('ws', location.href);
  endpoint.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const storageKey = 'valhallasc.characters.v1:' + endpoint.href;
  let saved = { current: null, characters: [] };
  try { const raw = JSON.parse(localStorage.getItem(storageKey) || 'null'); if (raw && Array.isArray(raw.characters)) saved = raw; } catch (_) {}
  const persist = () => { try { localStorage.setItem(storageKey, JSON.stringify(saved)); } catch (_) { status('Character key could not be saved. Keep this window open.', false); } };
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
    if (name) { const label = document.createElement('b'); label.textContent = name + ': '; line.append(label); }
    line.append(document.createTextNode(text)); $('chat-log').append(line);
    while ($('chat-log').children.length > 80) $('chat-log').firstElementChild.remove();
    $('chat-log').scrollTop = $('chat-log').scrollHeight;
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
      ws.send(JSON.stringify({ type: 'join', version: 1, token: saved.current, look: saved.current ? null : look }));
    };
    ws.onmessage = event => {
      if (!active || currentGeneration !== generation) return;
      let packet; try { packet = JSON.parse(event.data); } catch (_) { return; }
      switch (packet.type) {
        case 'welcome': {
          clearTimeout(joinTimeout); connected = true; failures = 0; id = packet.id;
          const character = packet.snapshot.players.find(p => p.id === id);
          if (packet.token) {
            saved.current = packet.token;
            saved.characters.push({ token: packet.token, look: character.look }); persist();
          }
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
          const slot = saved.characters.find(c => c.token === saved.current);
          if (character && slot && JSON.stringify(slot.look) !== JSON.stringify(character.look)) { slot.look = character.look; persist(); }
          callbacks.onSnapshot?.(packet); break;
        }
        case 'event': callbacks.onEvent?.(packet); break;
        case 'dialogue': window.City?.dialogue(packet); break;
        case 'chat': log(packet.text, packet.channel === 'party' ? `[Party] ${packet.name}` : packet.name, packet.channel); break;
        case 'system': log(packet.text); break;
        case 'notice': log(packet.text, null, packet.ok === false ? 'refused' : 'notice'); window.Social?.onNotice(packet); break;
        case 'social': window.Social?.onState(packet); break;
        case 'party': window.Social?.onParty(packet.party); break;
        case 'who': window.Social?.onWho(packet.players); break;
        case 'error':
          log(packet.text);
          if (packet.fatal) { fatal = true; connected = false; overlay(packet.text, true); status('Unable to enter world', false); ws.close(); }
          break;
      }
    };
    ws.onerror = () => {};
    ws.onclose = () => {
      clearTimeout(joinTimeout);
      if (!active || currentGeneration !== generation) return;
      clearInterval(heartbeat);
      connected = false; window.Inventory?.hideTooltip(); window.Skillbar?.close(false); window.Quests?.close(false); window.Social?.reset(); window.City?.close(); $('equipment').hidden = true; $('chat-input').disabled = true; callbacks.onDisconnect?.();
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
      active = false; generation++; connected = false; id = null; window.Social?.reset();
      clearTimeout(retryTimer); clearInterval(heartbeat);
      socket?.close(); socket = null;
      $('chat').hidden = true; $('connection-overlay').hidden = true;
      $('network-status').textContent = 'Valhalla · Shared world';
    },
    newCharacter() { saved.current = null; persist(); },
    select(token) {
      const slot = saved.characters.find(c => c.token === token); if (!slot) return null;
      saved.current = token; persist(); return { ...slot.look };
    },
    get currentToken() { return saved.current; },
    get bagLayout() { return saved.characters.find(c => c.token === saved.current)?.bagLayout || null; },
    saveBagLayout(layout) {
      const slot = saved.characters.find(c => c.token === saved.current); if (!slot) return;
      slot.bagLayout = [...layout]; persist();
    },
    get skillSlots() { return saved.characters.find(c => c.token === saved.current)?.skillSlots || null; },
    // The level the layout was last saved at: skills unlocked above it are placed into free slots.
    get skillLevel() { return saved.characters.find(c => c.token === saved.current)?.skillLevel; },
    saveSkillSlots(slots, level) {
      const slot = saved.characters.find(c => c.token === saved.current); if (!slot) return;
      slot.skillSlots = [...slots]; if (level) slot.skillLevel = level; persist();
    },
    get characters() { return saved.characters.map(c => ({ ...c, look: { ...c.look } })); },
    get connected() { return connected; },
    get id() { return id; }, send,
  };
  $('chat-form').addEventListener('submit', event => {
    event.preventDefault(); const input = $('chat-input'), text = input.value.trim();
    if (text.startsWith('/') && window.Social?.command(text)) input.value = '';
    else if (text && send({ type: 'chat', text })) input.value = '';
    input.blur();
  });
  $('chat-input').addEventListener('focus', () => { window.Field?.clearInput(); send({ type: 'stop' }); });
  $('chat-input').addEventListener('keydown', event => {
    event.stopPropagation(); if (event.key === 'Escape') { event.preventDefault(); event.currentTarget.blur(); }
  });
  addEventListener('keydown', event => {
    if (event.key === 'Enter' && active && connected && !/^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(event.target.tagName)) {
      event.preventDefault(); $('chat-input').focus();
    }
  });
  addEventListener('blur', () => { window.Field?.clearInput(); send({ type: 'stop' }); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { window.Field?.clearInput(); send({ type: 'stop' }); } });
  $('connection-retry').addEventListener('click', () => { generation++; socket?.close(); connect(); });
  $('connection-title').addEventListener('click', () => $('p-title').click());
  $('connection-new').addEventListener('click', () => $('p-new').click());
})();
