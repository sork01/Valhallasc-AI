'use strict';
// The menu on the target badge of a player or an adventurer: Trade, Duel and Inspect. Right-click, a long press or the
// Menu key opens it. The server decides every answer; this file only explains in advance what it will refuse.
(() => {
  const $ = id => document.getElementById(id);
  const TRADE_RANGE = 4, DUEL_RANGE = 25, LONG_PRESS = 500;
  const badge = $('hud-target'), menu = $('portrait-menu');
  if (!badge || !menu) return;
  const items = [...menu.querySelectorAll('[role=menuitem]')];
  let current = null, context = {}, inspectOk = false, isOpen = false, pressTimer = 0, pressAt = null, swallowContext = false;

  const live = () => items.filter(i => !i.hidden);
  const remote = () => current && window.Field?.remotePlayers?.find(p => p.id === current.id);
  const spot = a => ({ x: a.nx ?? a.x, y: a.ny ?? a.y });
  const distance = (a, b) => { const p = spot(a), q = spot(b); return Math.hypot(p.x - q.x, p.y - q.y); };
  const translate = text => window.Locale ? Locale.translate(text) : text;

  // Why an action will not work right now, or null. These mirror the server's rules (world/trade.rs, world/pvp.rs).
  function tradeReason(r, hero) {
    if (r.hired) return 'Hired fighters do not trade.';
    if (hero.dead || r.dead) return 'Both of you must be alive.';
    if (hero.sparkTravel || r.sparkTravel) return 'Not while travelling by Spark.';
    if (window.Trade?.state || r.tradeBusy) return 'One of you is already trading.';
    if (distance(hero, r) > TRADE_RANGE) return 'Move within four steps to trade.';
    return null;
  }
  function duelReason(r, hero) {
    const pvp = window.Pvp?.state;
    if (!window.Pvp?.available) return 'Duels are not available here.';
    if (r.hired) return 'Hired fighters do not duel.';
    if (hero.dead || r.dead) return 'Both of you must be alive.';
    if (hero.sparkTravel || r.sparkTravel) return 'Not while travelling by Spark.';
    if (pvp?.duel || pvp?.arena || pvp?.queue || pvp?.gauntlet || r.pvpBusy) return 'One of you is already in a duel or match.';
    if (context.sanctuary) return 'No duels in a sanctuary.';
    if (distance(hero, r) > DUEL_RANGE) return 'Too far away for a duel.';
    return null;
  }
  function paint() {
    const r = remote(), hero = window.Field?.hero;
    const reasons = !r || !hero ? { trade: 'Out of sight.', duel: 'Out of sight.', inspect: 'Out of sight.' }
      : { trade: tradeReason(r, hero), duel: duelReason(r, hero), inspect: null };
    for (const item of items) {
      item.hidden = item.dataset.act === 'inspect' && !inspectOk;   // an older server has no inspect message
      const reason = reasons[item.dataset.act], off = !!reason;
      item.setAttribute('aria-disabled', String(off)); item.classList.toggle('off', off);
      item.title = off ? translate(reason) : '';
      item.querySelector('.pm-reason').textContent = off ? reason : '';
    }
  }

  function open() {
    if (!current || isOpen) return;
    isOpen = true; paint(); menu.hidden = false; badge.setAttribute('aria-expanded', 'true');
    menu.querySelector('.pm-name').textContent = current.name;
    // Keyboard and pointer both land on the first entry, so the arrow keys always work.
    live()[0].focus({ preventScroll: true });
  }
  function close(refocus) {
    if (!isOpen) return;
    isOpen = false; menu.hidden = true; badge.setAttribute('aria-expanded', 'false');
    if (refocus && !badge.hidden) badge.focus({ preventScroll: true });
  }
  function activate(item) {
    if (item.getAttribute('aria-disabled') === 'true' || !current) return;
    const { id, name } = current, act = item.dataset.act;
    close(false);
    if (act === 'trade') window.Trade?.request(id);
    else if (act === 'duel') window.Pvp?.duel(id);
    else if (act === 'inspect') window.Inspect?.open(id, name);
  }

  badge.addEventListener('contextmenu', event => {
    if (!current) return;
    event.preventDefault(); swallowContext = false;
    isOpen ? close(false) : open();
  });
  // A touch or pen long press is the same gesture; the contextmenu event some browsers add afterwards is swallowed.
  badge.addEventListener('pointerdown', event => {
    if (!current || event.pointerType === 'mouse') return;
    pressAt = { x: event.clientX, y: event.clientY };
    clearTimeout(pressTimer);
    pressTimer = setTimeout(() => { pressTimer = 0; swallowContext = true; open(); }, LONG_PRESS);
  });
  badge.addEventListener('pointermove', event => {
    if (pressTimer && pressAt && Math.hypot(event.clientX - pressAt.x, event.clientY - pressAt.y) > 10) { clearTimeout(pressTimer); pressTimer = 0; }
  });
  for (const type of ['pointerup', 'pointercancel', 'pointerleave']) badge.addEventListener(type, () => { clearTimeout(pressTimer); pressTimer = 0; });
  badge.addEventListener('contextmenu', event => { if (swallowContext) { event.preventDefault(); swallowContext = false; } }, true);
  badge.addEventListener('keydown', event => {
    if (!current) return;
    const key = event.key;
    if (key === 'ContextMenu' || (key === 'F10' && event.shiftKey) || key === 'Enter' || key === ' ') {
      event.preventDefault(); event.stopPropagation(); open();
    }
  });

  menu.addEventListener('keydown', event => {
    const list = live(), key = event.key, at = list.indexOf(document.activeElement);
    const move = to => { event.preventDefault(); list[(to + list.length) % list.length].focus({ preventScroll: true }); };
    if (key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); }
    else if (key === 'ArrowDown') { move(at + 1); event.stopPropagation(); }
    else if (key === 'ArrowUp') { move(at - 1); event.stopPropagation(); }
    else if (key === 'Home') { move(0); event.stopPropagation(); }
    else if (key === 'End') { move(list.length - 1); event.stopPropagation(); }
    else if (key === 'Tab') { move(at + (event.shiftKey ? -1 : 1)); event.stopPropagation(); }
    else if (key === 'Enter' || key === ' ') { event.preventDefault(); event.stopPropagation(); if (at >= 0) activate(list[at]); }
    else if (key.length === 1 || key.startsWith('Arrow')) event.stopPropagation();   // no attack or walk while a menu is up
  });
  for (const item of items) item.addEventListener('click', () => activate(item));
  // Escape closes the menu before it can open the world menu, wherever the focus is.
  addEventListener('keydown', event => {
    if (isOpen && event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(true); }
  }, true);
  addEventListener('pointerdown', event => { if (isOpen && !menu.contains(event.target) && !badge.contains(event.target) && !event.target.closest('[aria-controls="portrait-menu"]')) close(false); }, true);
  addEventListener('blur', () => close(false));

  window.PortraitMenu = {
    toggle() { isOpen ? close(false) : open(); },
    // The server announces at join whether it answers `inspect`; without it that entry stays hidden.
    supported(on) { inspectOk = !!on; },
    // Called with each HUD update: the target (or null) and what the HUD knows about the hero's surroundings.
    target(t, ctx) {
      const player = t && t.player ? t : null;
      const changed = (player?.id || null) !== (current?.id || null);
      current = player; context = ctx || {};
      badge.tabIndex = player ? 0 : -1;
      badge.classList.toggle('has-menu', !!player);
      if (player) { badge.setAttribute('aria-haspopup', 'menu'); badge.setAttribute('aria-expanded', String(isOpen)); badge.title = translate('Right-click for Trade, Duel and Inspect'); }
      else { badge.removeAttribute('aria-haspopup'); badge.removeAttribute('aria-expanded'); badge.removeAttribute('title'); }
      if (!player || changed) close(false);
      else if (isOpen) { menu.querySelector('.pm-name').textContent = player.name; paint(); }
    },
    get isOpen() { return isOpen; },
  };
})();
