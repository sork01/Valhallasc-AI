'use strict';
// Rebirth in the client (docs/rebirth.md): the panel in the Character window, the confirmation dialog, the Reborn title
// and colour, the ground aura, the mount coat tints and the level-up hints. The server owns the rules, the perks and the
// confirmation nonce; this file only shows them and sends `rebirth_preview`, `rebirth` and `select_mount_tint`.
(() => {
  const $ = id => document.getElementById(id);
  const MIN_LEVEL = 50, STEP = 10, MAX_TIER = 5;
  const NUMERAL = ['', 'I', 'II', 'III', 'IV', 'V'];
  // Index = tier. Bronze, silver, gold, cyan and rose-white, the same hues as the aura atlas (scripts/make_rebirth_sprites.py).
  const NAME_COLORS = ['#fff4ca', '#e8a46c', '#e3ebf5', '#ffd84a', '#62e8f4', '#ffc4d9'];
  const RGB = ['255,255,255', '232,164,108', '227,235,245', '255,216,74', '98,232,244', '255,196,217'];
  // Mount coats come from tiers 2 to 5.
  const TINTS = { 2: '#aab7c6', 3: '#e0b13a', 4: '#43c9d6', 5: '#f0a9c4' };
  const PERKS = {
    xp: { label: 'Experience', show: v => `+${v}%` },
    gold: { label: 'Gold', show: v => `+${v}%` },
    bagCells: { label: 'Bag cells', show: v => `+${v}` },
    fare: { label: 'Spark Travel fares', show: v => `−${v}%` },
    resetPrice: { label: 'Stat reset price', show: v => `−${v}%` },
    drops: { label: 'Drop rate', show: v => `×${v}` },
  };
  const tierFor = level => level >= MIN_LEVEL ? Math.min(MAX_TIER, Math.floor((level - MIN_LEVEL) / STEP) + 1) : 0;
  const levelOf = tier => 40 + STEP * tier;
  const title = tier => tier > 0 ? `Reborn ${NUMERAL[tier]}` : '';
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined && text !== null) n.textContent = text; if (cls) n.className = cls; return n; };

  let hero = null, signature = '', pending = false, reason = '', offer = null, deadline = 0, ticker = 0, hinted = -1, lastLevel = 0;

  // ---- the perk arithmetic, the same as server/src/perks.rs (every perk is derived from the rebirth counts) ----
  function perkAfter(perk, tiers, tier) {
    const n = tiers.slice(perk.unlock - 1).reduce((a, b) => a + b, 0) + (tier >= perk.unlock ? 1 : 0);
    return perk.id === 'drops' ? Math.min(perk.cap, 1 + perk.step * n) : Math.min(perk.cap, perk.step * n);
  }
  function blocker(h) {
    if (h.level < MIN_LEVEL) return `You need level ${MIN_LEVEL} to be reborn.`;
    if (h.dead) return 'You cannot be reborn while defeated.';
    if (h.mounted) return 'Dismount before you are reborn.';
    if (h.sparkTravel) return 'You cannot be reborn during Spark Travel.';
    if (h.inCombat) return 'Leave combat before you are reborn.';
    return '';
  }

  // ---- the Character window panel ----
  function perkRow(perk, now, after, highest) {
    const def = PERKS[perk.id] || { label: perk.id, show: String }, locked = perk.unlock > Math.max(highest, 1) && perk.value === (perk.id === 'drops' ? 1 : 0);
    const row = node('div', '', 'rebirth-perk'); row.dataset.perk = perk.id; row.dataset.locked = String(locked);
    const bar = node('i'); const full = perk.id === 'drops' ? perk.cap - 1 : perk.cap, have = perk.id === 'drops' ? perk.value - 1 : perk.value;
    bar.style.width = `${Math.round(100 * Math.min(1, have / full))}%`;
    const meter = node('span', '', 'rebirth-meter'); meter.append(bar);
    row.append(node('b', def.label), node('span', def.show(perk.value), 'rebirth-value'), meter,
      node('small', locked ? `From level ${levelOf(perk.unlock)} (tier ${NUMERAL[perk.unlock]})` : perk.value >= perk.cap ? 'At its cap' : `Next rebirth: ${def.show(after)}`));
    row.title = `Cap ${def.show(perk.cap)}`;
    return row;
  }
  function render() {
    const host = $('character-rebirth'); if (!host || !hero) return;
    const perks = hero.rebirthPerks || [], tiers = hero.rebirthTiers || [0, 0, 0, 0, 0];
    const highest = hero.reborn?.tier || 0, count = hero.reborn?.count || 0, now = tierFor(hero.level), why = blocker(hero);
    const key = JSON.stringify([perks, tiers, hero.level, why, hero.mountTint, hero.mounts?.length, pending, reason]);
    if (key === signature && host.childElementCount) return;
    signature = key;
    host.replaceChildren(node('h4', 'Rebirth'));
    host.append(node('small', !count ? 'Never reborn' : count === 1 ? `${title(highest)} · ${count} rebirth` : `${title(highest)} · ${count} rebirths`, 'rebirth-status'));
    const list = node('div', '', 'rebirth-perks');
    for (const perk of perks) list.append(perkRow(perk, perk.value, perkAfter(perk, tiers, now || 1), highest));
    host.append(list);
    // What a rebirth now would be, and the next step up.
    const next = node('p', '', 'rebirth-next');
    if (!now) next.textContent = `The first rebirth is at level ${MIN_LEVEL}.`;
    else if (now < MAX_TIER) next.textContent = `A rebirth now is tier ${NUMERAL[now]}. At level ${levelOf(now + 1)} it becomes tier ${NUMERAL[now + 1]}, with more perks.`;
    else next.textContent = 'A rebirth now is tier V, the best there is.';
    host.append(next);
    const button = node('button', pending ? 'Checking…' : 'Rebirth…', 'window-tool rebirth-open'); button.type = 'button'; button.id = 'rebirth-open';
    button.disabled = !!why || pending || !window.Online?.connected;
    button.addEventListener('click', ask);
    host.append(button, node('small', why || reason, 'rebirth-reason'));
    host.lastChild.dataset.ok = String(!(why || reason));
    if (highest >= 2) {
      const coats = node('div', '', 'rebirth-coats'); coats.append(node('b', 'Mount coat'));
      for (const tier of [0, 2, 3, 4, 5]) {
        if (tier > highest) break;
        const pick = node('button', tier ? '' : 'Plain', 'rebirth-coat'); pick.type = 'button'; pick.dataset.tint = String(tier);
        pick.setAttribute('aria-pressed', String((hero.mountTint || 0) === tier));
        pick.setAttribute('aria-label', tier ? `${title(tier)} coat` : 'Plain coat');
        if (tier) pick.style.background = TINTS[tier];
        pick.addEventListener('click', () => window.Online?.send({ type: 'select_mount_tint', tier }));
        coats.append(pick);
      }
      host.append(coats);
    }
  }
  function ask() {
    if (pending || blocker(hero)) return;
    pending = true; reason = ''; render();
    window.Online?.send({ type: 'rebirth_preview' });
    setTimeout(() => { if (pending) { pending = false; reason = 'No answer from the server. Try again.'; render(); } }, 6000);
  }

  // ---- the confirmation dialog ----
  const dialog = () => $('rebirth-dialog');
  // A row is a label (translated as its own text) and, when given, a value that is only numbers.
  function lines(list, rows) {
    list.replaceChildren(...rows.map(([label, value]) => { const li = node('li'); li.append(node('span', label)); if (value) li.append(' ', node('span', value, 'rebirth-change')); return li; }));
  }
  function onPreview(p) {
    pending = false;
    if (!p.ok) { reason = p.reason || 'A rebirth is not possible now.'; render(); return; }
    reason = ''; offer = p; deadline = performance.now() + (p.lifetime || 60) * 1000;
    $('rebirth-title').textContent = `Rebirth at level ${p.level}: tier ${NUMERAL[p.tier]}`;
    const changed = (p.perks || []).map((now, i) => [now, p.perksAfter?.[i]]).filter(([a, b]) => b && a.value !== b.value);
    lines($('rebirth-adds'), changed.length
      ? changed.map(([a, b]) => { const show = PERKS[a.id]?.show || String; return [PERKS[a.id]?.label || a.id, `${show(a.value)} → ${show(b.value)}`]; })
      : [['Nothing new: every perk this tier gives is already at its cap.']]);
    $('rebirth-gear').textContent = !p.gearOff ? '' : p.gearOff === 1 ? `${p.gearOff} worn piece goes into your bags.` : `${p.gearOff} worn pieces go into your bags.`;
    $('rebirth-gear').hidden = !p.gearOff;
    $('rebirth-type').value = ''; $('rebirth-confirm').disabled = true; $('rebirth-error').textContent = '';
    dialog().hidden = false; tick(); clearInterval(ticker); ticker = setInterval(tick, 250);
    $('rebirth-type').focus();
  }
  function tick() {
    const left = Math.max(0, Math.ceil((deadline - performance.now()) / 1000));
    $('rebirth-timer').textContent = left ? `${left}s` : 'Expired';
    const typed = $('rebirth-type').value.trim().toUpperCase() === 'REBIRTH';
    $('rebirth-confirm').disabled = !offer || !typed || left === 0;
    if (!left && offer) $('rebirth-error').textContent = 'The confirmation ran out. Close this and ask again.';
  }
  function close() {
    clearInterval(ticker); offer = null;
    if (dialog()) dialog().hidden = true;
    pending = false; render();
    $('rebirth-open')?.focus({ preventScroll: true });
  }
  function confirm() {
    if (!offer || $('rebirth-confirm').disabled) return;
    window.Online?.send({ type: 'rebirth', nonce: offer.nonce });
    const sent = offer; offer = null; clearInterval(ticker); dialog().hidden = true; pending = true; reason = ''; render();
    // If nothing happens, the reason arrives as an error packet; otherwise the level drop closes the loop.
    setTimeout(() => { if (pending && hero?.level === sent.level) { pending = false; render(); } }, 5000);
  }
  function wire() {
    if (!dialog() || dialog().dataset.wired) return; dialog().dataset.wired = '1';
    $('rebirth-cancel').addEventListener('click', close);
    $('rebirth-confirm').addEventListener('click', confirm);
    $('rebirth-type').addEventListener('input', tick);
    $('rebirth-type').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); confirm(); } });
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || dialog().hidden) return;
      e.preventDefault(); e.stopImmediatePropagation(); close();
    }, true);
  }

  // ---- the level-up hints ----
  // A hint is shown once for each tier a level reaches; a character who logs in already past a step is not told again.
  function hint(level) {
    const tier = tierFor(level);
    if (hinted < 0) hinted = tier;
    if (tier <= hinted) return '';
    hinted = tier;
    const text = tier === 1 ? `Rebirth is now possible: open Character (E)` : `A better rebirth is now available: tier ${NUMERAL[tier]} at level ${levelOf(tier)}.`;
    window.SystemLog?.add(text, 'notice');
    return text;
  }

  // ---- the marks other players see ----
  let atlas = null;
  fetch('assets/rebirth.txt').then(r => r.ok ? r.json() : Promise.reject()).then(meta => {
    const img = new Image(); img.onload = () => { atlas = { meta, img }; }; img.src = 'assets/rebirth.png';
  }).catch(() => {});
  // The aura lies on the ground under the feet: `g` is already translated to them. One atlas cell per tier and frame.
  function drawAura(g, tier, scale = 1) {
    if (!atlas || !(tier >= 1 && tier <= MAX_TIER)) return;
    const { frame: [w, h], anchor: [ax, ay], frames, fps } = atlas.meta, now = performance.now() / 1000;
    const f = Math.floor(now * fps) % frames;
    g.save(); g.globalAlpha = .82 + .12 * Math.sin(now * 2.4 + tier);
    g.drawImage(atlas.img, f * w, (tier - 1) * h, w, h, -ax * scale, -ay * scale + 2, w * scale, h * scale);
    g.restore();
  }

  window.Rebirth = {
    NUMERAL, NAME_COLORS, TINTS, tierFor, levelOf, title, drawAura,
    color: tier => NAME_COLORS[tier] || NAME_COLORS[0],
    rgb: tier => RGB[tier] || RGB[1],
    tintColor: tint => TINTS[tint] || '',
    // The small Reborn label for the party frame and the friend list.
    badge(tier) { if (!tier) return null; const n = node('small', title(tier), 'reborn-badge'); n.dataset.tier = String(tier); n.style.color = NAME_COLORS[tier]; return n; },
    hint,
    update(own) {
      hero = own; wire();
      if (hinted < 0 || own.level < lastLevel) hinted = tierFor(own.level);
      lastLevel = own.level;
      const tag = $('hud-reborn');
      if (tag) { const tier = own.reborn?.tier || 0; tag.textContent = title(tier); tag.hidden = !tier; tag.style.color = NAME_COLORS[tier]; tag.dataset.tier = String(tier); }
      if (offer && own.level !== offer.level) close();
      if (pending && own.level < (offer?.level ?? MIN_LEVEL)) pending = false;
      render();
    },
    render,
    onPreview,
    onError(text) {
      if (!pending && !offer) return;
      if (offer) { $('rebirth-error').textContent = text; return; }
      pending = false; reason = text; render();
    },
    // The celebration banner for the player's own rebirth.
    celebrate(ev) {
      const box = $('rebirth-banner'); if (!box) return;
      const tier = Math.round(ev.value) || 1;
      $('rebirth-banner-tier').textContent = title(tier); box.style.setProperty('--rebirth-rgb', RGB[tier]);
      box.hidden = false; box.classList.remove('show'); void box.offsetWidth; box.classList.add('show');
      clearTimeout(box._t); box._t = setTimeout(() => { box.hidden = true; box.classList.remove('show'); }, matchMedia('(prefers-reduced-motion: reduce)').matches ? 3200 : 5200);
      pending = false; offer = null; if (dialog()) dialog().hidden = true; clearInterval(ticker);
    },
  };
})();
