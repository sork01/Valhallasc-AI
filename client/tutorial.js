'use strict';
window.Tutorial = (() => {
  const $ = id => document.getElementById(id);
  const tr = s => window.Locale?.translate ? window.Locale.translate(s) : s;
  const MILESTONES = ['first_quest', 'levelup_stats', 'equip_gear', 'new_skill', 'consumables', 'merchant',
    'target_attack', 'loot', 'quest_turnin', 'first_death', 'map', 'spark_travel', 'elite', 'rested', 'repair', 'bags_full', 'mail_bank', 'party_mercs'];
  const COARSE = () => !!(window.matchMedia?.('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) <= 500);

  let hero = null;
  let lastHeroId = null;
  let done = new Set();
  let disabled = false;
  let pendingComplete = new Set();
  let pendingDisable = false;
  let active = null; // { id, sub, target, title, body, total, index, rect, stageRect }
  let seenSubsteps = new Set();
  let seenQuestsCount = null;
  let seenKills = null;
  let seenBagQty = new Map();
  let lastEquipItemId = null;
  let lastConsumableKind = null;
  let lastConsumableCounts = new Map();
  let skillDialogSeen = false;
  let merchantModeSeen = false;
  let merchantTransacted = false;
  let syncQueued = false;
  let observed = false;
  let layer = null, glowEl = null, tipEl = null, arrowEl = null, titleEl = null, progressEl = null, bodyEl = null, disableBtn = null, gotItBtn = null;
  let attrMarked = [];

  function observeUi() {
    if (observed || typeof MutationObserver === 'undefined') return;
    observed = true;
    const attrIds = ['stage', 'equipment', 'character-tab-stats', 'skills-panel', 'npc-dialogue',
      'pause', 'settings-panel', 'recommended-dialog', 'sell-warning', 'quest-journal', 'worldmap',
      'touch-actions', 'touch-quickuse'];
    const attrObs = new MutationObserver(scheduleRender);
    for (const id of attrIds) {
      const el = $(id);
      if (el) attrObs.observe(el, { attributes: true, attributeFilter: ['hidden', 'class', 'aria-selected', 'aria-expanded'] });
    }
    const ws = document.querySelector('.equipment-workspace');
    if (ws) attrObs.observe(ws, { attributes: true, attributeFilter: ['data-view'] });

    const childObs = new MutationObserver(scheduleRender);
    for (const id of ['quest-tracker', 'inventory-list', 'npc-inventory', 'npc-offers', 'character-attributes']) {
      const el = $(id);
      if (el) childObs.observe(el, { childList: true });
    }
  }

  function ensureDom() {
    if (layer) return;
    const stage = $('stage');
    if (!stage) return;
    layer = document.createElement('div');
    layer.id = 'tutorial-layer';
    layer.className = 'tutorial-layer';
    layer.hidden = true;

    glowEl = document.createElement('div');
    glowEl.id = 'tutorial-glow';
    glowEl.className = 'tutorial-glow';
    glowEl.setAttribute('aria-hidden', 'true');
    glowEl.hidden = true;

    tipEl = document.createElement('aside');
    tipEl.id = 'tutorial-tip';
    tipEl.className = 'tutorial-tip';
    tipEl.setAttribute('role', 'dialog');
    tipEl.setAttribute('aria-live', 'polite');
    tipEl.setAttribute('aria-label', tr('Tutorial tip'));
    tipEl.hidden = true;

    arrowEl = document.createElement('span');
    arrowEl.id = 'tutorial-arrow';
    arrowEl.className = 'tutorial-arrow';
    arrowEl.setAttribute('aria-hidden', 'true');

    const head = document.createElement('div');
    head.className = 'tutorial-head';
    titleEl = document.createElement('strong');
    titleEl.id = 'tutorial-title';
    progressEl = document.createElement('span');
    progressEl.id = 'tutorial-progress';
    progressEl.className = 'tutorial-progress';
    head.append(titleEl, progressEl);

    bodyEl = document.createElement('p');
    bodyEl.id = 'tutorial-body';
    bodyEl.className = 'tutorial-body';

    const actions = document.createElement('div');
    actions.className = 'tutorial-actions';
    disableBtn = document.createElement('button');
    disableBtn.id = 'tutorial-disable';
    disableBtn.type = 'button';
    disableBtn.className = 'tutorial-btn tutorial-btn-muted';
    disableBtn.textContent = tr('Disable tutorial');
    disableBtn.addEventListener('click', e => {
      e.stopPropagation();
      disable();
    });

    gotItBtn = document.createElement('button');
    gotItBtn.id = 'tutorial-gotit';
    gotItBtn.type = 'button';
    gotItBtn.className = 'tutorial-btn tutorial-btn-primary';
    gotItBtn.textContent = tr('Got it');
    gotItBtn.addEventListener('click', e => {
      e.stopPropagation();
      if (active) complete(active.id);
    });

    actions.append(disableBtn, gotItBtn);
    tipEl.append(arrowEl, head, bodyEl, actions);
    layer.append(glowEl, tipEl);
    stage.append(layer);
    observeUi();
  }

  function sendCommand(command) {
    if (window.Online?.connected) window.Online.send({ type: 'tutorial', command });
  }

  function clearAttrFocus() {
    while (attrMarked.length) attrMarked.pop().classList.remove('tutorial-focus-inline');
  }

  function applyAttrFocus() {
    clearAttrFocus();
    const box = $('character-attributes');
    if (!box) return;
    for (const row of box.querySelectorAll('.attribute-row')) {
      if (row.querySelector('b')?.textContent?.includes('★')) {
        row.classList.add('tutorial-focus-inline');
        attrMarked.push(row);
        const plus = row.querySelector('.attribute-add');
        if (plus) { plus.classList.add('tutorial-focus-inline'); attrMarked.push(plus); }
      }
    }
    const rec = box.querySelector('.attribute-recommend');
    if (rec) { rec.classList.add('tutorial-focus-inline'); attrMarked.push(rec); }
  }

  function isShown(el) {
    if (!el || el.hidden) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return false;
    const r = el.getBoundingClientRect();
    return r.width > 4 && r.height > 4;
  }

  function isAnyBlockingModalOpen(allowedId) {
    const blockers = ['pause', 'settings-panel', 'keys-panel', 'whats-new', 'worldmap',
      'social-panel', 'inspect-panel', 'trade-panel', 'trade-request', 'rebirth-dialog',
      'recommended-dialog', 'sell-warning', 'mail-panel', 'bank-panel', 'activity-panel',
      'quest-journal', 'equipment', 'skills-panel', 'npc-dialogue', 'connection-overlay',
      'gmtest-panel', 'sign-panel'];
    for (const id of blockers) {
      if (id === allowedId) continue;
      if (isShown($(id))) return true;
    }
    if (window.Settings?.editing) return true;
    return false;
  }

  function nearbyBossActive() {
    if (window.BossMech?.active) return true;
    const h = window.Field?.hero || hero;
    const slimes = window.Field?.slimes;
    if (!h || !Array.isArray(slimes)) return false;
    for (const s of slimes) {
      if (!s || s.dead || !s.d?.boss) continue;
      const dx = (s.x ?? 0) - (h.x ?? 0), dy = (s.y ?? 0) - (h.y ?? 0);
      if (['chase', 'windup', 'lunge'].includes(s.state) && dx * dx + dy * dy <= 256) return true;
    }
    return false;
  }

  function isInterrupted(allowedDialogId, allowGhost) {
    if ($('scene-game')?.hidden) return true;
    if (!window.Online?.connected) return true;
    if (window.Cutscene?.active) return true;
    const h = window.Field?.hero || hero;
    if (!h) return true;
    if (allowGhost ? (h.dead && !h.ghost) : (h.dead || h.ghost || (h.hp !== undefined && h.hp <= 0))) return true;
    if (nearbyBossActive()) return true;
    if (isAnyBlockingModalOpen(allowedDialogId)) return true;
    return false;
  }

  function compatibleWearableItems() {
    const list = window.WORLD_ITEMS || [];
    const inv = window.Inventory;
    const h = hero;
    if (!inv || !h) return [];
    const cls = h.look?.class;
    const lvl = h.level || 1;
    const out = [];
    for (const item of list) {
      if (!item || item.starter) continue;
      const isGear = item.kind === 'armor' || item.kind === 'weapon' || item.kind === 'accessory' || !!item.slot;
      if (!isGear) continue;
      if ((inv.bagQuantity?.(item.id) || 0) <= 0) continue;
      if (item.class && item.class !== cls) continue;
      if ((item.requiredLevel || item.level || 1) > lvl) continue;
      out.push(item);
    }
    return out;
  }

  function bagConsumables() {
    const list = window.WORLD_ITEMS || [];
    const inv = window.Inventory;
    if (!inv) return [];
    const out = [];
    for (const item of list) {
      if (!item || (item.kind !== 'food' && item.kind !== 'potion')) continue;
      const qty = inv.bagQuantity?.(item.id) || 0;
      if (qty > 0) out.push({ item, qty });
    }
    return out;
  }

  function findUnlockedActiveSkill() {
    const skills = window.WORLD_SKILLS || [];
    const h = hero;
    if (!h || !h.look) return null;
    const cls = h.look.class;
    const lvl = h.level || 1;
    return skills.find(s => !s.passive && (!s.class || s.class === cls) && (s.level || 1) > 1 && (s.level || 1) <= lvl) || null;
  }

  function findBagElementForItem(itemId) {
    return document.querySelector(`#inventory-list [data-item="${itemId}"]`) || $('inventory-list');
  }

  function isMerchantOpen() {
    const dlg = $('npc-dialogue');
    if (!isShown(dlg)) return false;
    if (dlg.classList.contains('merchant-mode')) return true;
    return !!dlg.querySelector('#npc-offers [data-view="sell"], #npc-offers [data-view="buy"]');
  }

  function currentDialogContext() {
    if (isMerchantOpen()) return 'merchant';
    if (isShown($('skills-panel'))) return 'skills-panel';
    if (isShown($('equipment'))) return 'equipment';
    return null;
  }

  function stepFirstQuest() {
    const touch = COARSE();
    const target = touch
      ? (isShown($('touch-actions')?.querySelector('[data-action="quests"]'))
        ? $('touch-actions').querySelector('[data-action="quests"]')
        : isShown($('touch-stick')) ? $('touch-stick') : $('touch-actions'))
      : (isShown($('quest-tracker')) ? $('quest-tracker') : null);
    return {
      id: 'first_quest',
      sub: 'first_quest',
      allowedDialog: null,
      target,
      title: 'Welcome to Greenmeadow',
      body: touch
        ? 'Move with the left thumbstick, tap Attack to fight nearby foes, and check Quests to follow your first adventure.'
        : 'Move with WASD or click ground to walk, click enemies to fight, and check your Quest Tracker for your first quest.',
    };
  }

  function stepLevelUpStats() {
    const touch = COARSE();
    const eqOpen = isShown($('equipment'));
    const ws = document.querySelector('.equipment-workspace');
    if (!eqOpen) {
      return {
        id: 'levelup_stats',
        sub: 'levelup_stats_bag',
        allowedDialog: 'equipment',
        target: touch && isShown($('touch-actions')?.querySelector('[data-action="bags"]'))
          ? $('touch-actions').querySelector('[data-action="bags"]')
          : $('inventory-open'),
        title: 'Stat points available!',
        body: touch
          ? 'You leveled up! Tap Bags to open your character and spend your new stat points.'
          : 'You leveled up! Click Bags (B) to open your character pane and spend your stat points.',
      };
    }
    if (ws && ws.dataset.view === 'bags' && isShown($('bag-character'))) {
      return {
        id: 'levelup_stats',
        sub: 'levelup_stats_charbtn',
        allowedDialog: 'equipment',
        target: $('bag-character'),
        title: 'Open Character Stats',
        body: 'Tap Character to view your attributes and train your new stat points.',
      };
    }
    const statsTab = $('character-tab-stats');
    if (statsTab && statsTab.getAttribute('aria-selected') !== 'true') {
      return {
        id: 'levelup_stats',
        sub: 'levelup_stats_tab',
        allowedDialog: 'equipment',
        target: statsTab,
        title: 'Character & Stats',
        body: 'Switch to the Character & stats tab to spend your unspent stat points.',
      };
    }
    return {
      id: 'levelup_stats',
      sub: 'levelup_stats_attrs',
      allowedDialog: 'equipment',
      target: $('character-attributes'),
      highlightAttrs: true,
      title: 'Spend your stat points',
      body: 'Click + on your ★ class specialty stat or use Recommended to distribute your points automatically.',
    };
  }

  function stepEquipGear(gearItems) {
    const touch = COARSE();
    const eqOpen = isShown($('equipment'));
    const item = gearItems[0];
    lastEquipItemId = item.id;
    if (!eqOpen) {
      return {
        id: 'equip_gear',
        sub: 'equip_gear_bag',
        allowedDialog: 'equipment',
        target: touch && isShown($('touch-actions')?.querySelector('[data-action="bags"]'))
          ? $('touch-actions').querySelector('[data-action="bags"]')
          : $('inventory-open'),
        title: 'New equipment found!',
        body: touch
          ? 'You picked up wearable gear. Tap Bags to inspect and equip it.'
          : 'You obtained compatible gear! Open Bags (B) to equip it.',
      };
    }
    const el = findBagElementForItem(item.id);
    return {
      id: 'equip_gear',
      sub: 'equip_gear_slot',
      allowedDialog: 'equipment',
      target: el,
      title: 'Equip your new gear',
      body: touch
        ? 'Tap this item in your bag and choose Equip (or drag it onto a character slot) to wear it.'
        : 'Click this item and drag it onto a matching character slot (or click Equip) to put it on.',
    };
  }

  function stepNewSkill(skill) {
    const touch = COARSE();
    const open = isShown($('skills-panel'));
    if (!open) {
      let target = $('skills-open');
      if (touch && !isShown(target)) {
        target = document.querySelector('#touch-quickuse button[aria-expanded]') || $('touch-quickuse');
      }
      return {
        id: 'new_skill',
        sub: 'new_skill_open',
        allowedDialog: 'skills-panel',
        target,
        title: 'New skill unlocked!',
        body: touch
          ? 'New active skill unlocked! Tap Other skills then Skills to view and arrange your abilities.'
          : 'New active skill unlocked! Open Skills (K) to inspect and arrange your skillbar.',
      };
    }
    skillDialogSeen = true;
    return {
      id: 'new_skill',
      sub: 'new_skill_panel',
      allowedDialog: 'skills-panel',
      target: isShown($('skill-editor-slots')) ? $('skill-editor-slots') : $('skill-library'),
      title: 'Arrange your skillbar',
      body: 'Click or drag unlocked abilities into your skillbar slots so they are ready during combat.',
    };
  }

  function stepConsumables() {
    const touch = COARSE();
    const target = touch && isShown($('touch-quickuse')) ? $('touch-quickuse') : $('quickuse');
    return {
      id: 'consumables',
      sub: 'consumables',
      allowedDialog: null,
      target,
      title: 'Quick-use food & potions',
      body: touch
        ? 'Tap the quick-use slots to eat food or drink potions. Consumables share a brief cooldown.'
        : 'Press Z (food), X (health potion), or C (mana potion), or click the quick-use slots, to recover. They share a short cooldown.',
    };
  }

  function stepMerchant() {
    const dlg = $('npc-dialogue');
    const inShop = dlg.classList.contains('merchant-mode');
    if (inShop) merchantModeSeen = true;
    const target = inShop
      ? (isShown($('sell-junk')) && $('sell-junk').offsetParent ? $('sell-junk') : $('npc-inventory'))
      : $('npc-offers');
    return {
      id: 'merchant',
      sub: inShop ? 'merchant_shop' : 'merchant_offer',
      allowedDialog: 'npc-dialogue',
      target,
      title: 'Merchant: Buy & Sell',
      body: inShop
        ? 'Buy food and potions here for recovery, click items from your bag to sell them, or use Sell Junk for quick gold.'
        : 'Choose Buy or Sell to stock up on food and potions or trade unneeded loot for gold.',
    };
  }

  // ---- The twelve later steps (TUTORIAL-MORE-STEPS). Each fires once per character, the first time it happens at any level; a hero past level 5
  // when the steps arrived has them marked done by the server. A step is a note anchored to one control, finished by "Got it" or by doing the thing.
  const fh = () => window.Field?.hero;
  const dist = (x, y) => { const h = fh(); return h && Number.isFinite(x) && Number.isFinite(y) ? Math.hypot(x - h.x, y - h.y) : Infinity; };
  const enemies = () => (window.Field?.slimes || []).filter(s => s && !s.dead && s.state !== 'waiting' && !s.d?.add);
  const npcNear = (test, r = 6) => (window.City?.npcs || []).find(n => n && test(n) && dist(n.x, n.y) <= r);
  const hasOffer = (n, ...ids) => (n.offers || []).some(o => ids.includes(o.id));
  const touchOr = (touchSelector, desktop) => COARSE() && isShown(document.querySelector(touchSelector)) ? document.querySelector(touchSelector) : desktop;
  const FULL = () => { const h = hero; return !!h && h.bagCapacity > 0 && h.bagUsed >= h.bagCapacity; };
  const MORE = {
    first_death: {
      when: () => !!(fh()?.ghost || hero?.ghost), allowGhost: true,
      target: () => isShown($('ghost-resurrect')) ? $('ghost-resurrect') : $('ghost-msg'),
      title: 'You are a spirit',
      body: 'Run back to your body and press Resurrect when you are within 15 tiles, at half health. Or talk to a Spirit Guide: that costs half the durability of your worn gear and ten minutes of Resurrection Sickness.',
      expiresOn: () => !!(fh()?.ghost || hero?.ghost),
    },
    target_attack: {
      when: () => enemies().some(s => dist(s.x, s.y) <= 9),
      target: () => touchOr('#touch-actions [data-action="attack"], #touch-skills .touch-attack', $('skillbar')),
      title: 'Fight!',
      body: 'Click an enemy to target it. Your hero attacks on its own while it is targeted; use the skillbar below (keys 1-9) for stronger moves.',
      touchBody: 'Tap an enemy to target it, then tap Attack. The skill buttons beside it are stronger moves.',
    },
    loot: {
      when: () => (window.Field?.drops || []).some(d => dist(d.x, d.y) <= 8),
      target: () => $('inventory-open'),
      title: 'Loot on the ground',
      body: 'Walk over a drop to pick it up (money goes straight to your purse). Colour shows rarity: grey, green, blue, purple. Everything you take lands in your Bags.',
      touchBody: 'Walk over a drop to pick it up. Colour shows rarity: grey, green, blue, purple. Everything lands in your Bags.',
    },
    quest_turnin: {
      when: () => !!window.Quests?.anyReady,
      target: () => isShown($('quest-tracker')) ? $('quest-tracker') : $('minimap'),
      title: 'A quest is ready',
      body: 'A yellow ? marks the person to hand it in to, on your minimap and in the world. Walk back to them, talk, and choose your reward.',
    },
    map: {
      when: () => (hero?.quests?.length || 0) > 0 && (hero?.level || 1) >= 2,
      target: () => $('wm-open'),
      title: 'Find your way',
      body: 'The minimap marks quest givers and goals. Press M for the world map, and track a quest to see where to go next.',
    },
    spark_travel: {
      when: () => !!npcNear(n => hasOffer(n, 'travel') || String(n.id).startsWith('travel_'), 7),
      target: () => $('wm-open'),
      title: 'Spark Travel',
      body: 'This is a Spark Travel master. Talk to one to discover its station, and the world map will let you fly between the stations you know.',
    },
    elite: {
      when: () => enemies().some(s => s.d?.elite && dist(s.x, s.y) <= 16),
      target: () => isShown($('hud-target')) ? $('hud-target') : $('skillbar'),
      title: 'An elite enemy',
      body: 'Elites are much tougher than normal enemies. Bring a group, or hire mercenaries at a Meeting Stone, before you take one on.',
    },
    rested: {
      when: () => !!hero?.rested && hero.rested.percent > 0,
      target: () => $('xp-meter'),
      title: 'Rested',
      body: 'You rested while away. The light-green part of your experience bar is bonus experience: monsters and quests give extra until it is used up.',
    },
    repair: {
      when: () => ['low', 'broken'].includes($('inventory-open')?.dataset.gear),
      target: () => $('inventory-open'),
      title: 'Your gear is worn',
      body: 'A worn piece is low or broken (the ! on your Bags button). Visit a smith to repair it; a broken piece gives no stats.',
    },
    bags_full: {
      when: FULL,
      target: () => $('inventory-open'),
      title: 'Your bags are full',
      body: 'Sell what you do not need to a merchant (Sell junk clears grey items at once), or buy a bigger bag. Full bags cannot take new loot.',
    },
    mail_bank: {
      when: () => !!npcNear(n => hasOffer(n, 'mail', 'bank') || n.art === 'mailbox', 5),
      target: () => $('mail-open'),
      title: 'Mail and bank',
      body: 'A mailbox sends letters and items to other players, and holds loot you won while your bags were full. A banker stores items and money safely for you.',
    },
    party_mercs: {
      when: () => !!window.Social?.hasPartyInvite || !!npcNear(n => (n.offers || []).some(o => o.merc), 6),
      target: () => window.Social?.hasPartyInvite ? $('social-open') : $('social-open'),
      title: 'Parties and mercenaries',
      body: 'Open Friends (O) to invite players to a party; parties share experience and loot. At a Meeting Stone you can hire mercenaries to fight beside you.',
    },
  };
  const MORE_ORDER = ['target_attack', 'loot', 'quest_turnin', 'elite', 'repair', 'bags_full', 'rested', 'mail_bank', 'spark_travel', 'party_mercs', 'map'];
  function moreStep(id) {
    const def = MORE[id];
    if (!def || done.has(id) || !def.when()) return null;
    const touch = COARSE();
    return { id, sub: id, allowedDialog: null, allowGhost: !!def.allowGhost, expiresOn: def.expiresOn, target: def.target(), title: def.title, body: touch && def.touchBody ? def.touchBody : def.body };
  }
  function nextMoreStep() {
    for (const id of MORE_ORDER) { const step = moreStep(id); if (step) return step; }
    return null;
  }

  function pickNextStep() {
    if (!hero || disabled) return null;
    const ghostStep = moreStep('first_death');
    if (ghostStep) return ghostStep;
    const dlg = currentDialogContext();
    const statPoints = hero.statPoints || 0;
    const gear = !done.has('equip_gear') ? compatibleWearableItems() : [];
    const skill = !done.has('new_skill') ? findUnlockedActiveSkill() : null;
    const consumables = !done.has('consumables') ? bagConsumables() : [];

    // 1. Contextual priority when a relevant window is already open
    if (dlg === 'merchant' && !done.has('merchant')) return stepMerchant();
    if (dlg === 'skills-panel' && skill) return stepNewSkill(skill);
    if (dlg === 'equipment') {
      if (!done.has('levelup_stats') && statPoints > 0) return stepLevelUpStats();
      if (gear.length) return stepEquipGear(gear);
    }

    // 2. General progression order
    if (!done.has('first_quest') && !hero.landing) return stepFirstQuest();
    if (!done.has('levelup_stats') && statPoints > 0) return stepLevelUpStats();
    if (!done.has('equip_gear') && gear.length) return stepEquipGear(gear);
    if (!done.has('new_skill') && skill) return stepNewSkill(skill);
    if (!done.has('consumables') && consumables.length) return stepConsumables(consumables);
    return nextMoreStep();
  }

  function updateAutoCompletions() {
    if (!hero || disabled) return;
    // first_quest: complete on accepting another quest (non-landing) or defeating a foe
    if (!done.has('first_quest') && seenSubsteps.has('first_quest')) {
      const qc = Array.isArray(hero.quests) ? hero.quests.length : 0;
      const kills = hero.kills || 0;
      if ((seenQuestsCount !== null && qc > seenQuestsCount) || (seenKills !== null && kills > seenKills)) {
        complete('first_quest');
        return;
      }
    }
    // levelup_stats: complete once user viewed stats attrs and spent all points
    if (!done.has('levelup_stats') && seenSubsteps.has('levelup_stats_attrs') && (hero.statPoints || 0) === 0) {
      complete('levelup_stats');
      return;
    }
    // equip_gear: complete if the highlighted item was equipped (bag quantity decreased and item in equipped or worn)
    if (!done.has('equip_gear') && seenSubsteps.has('equip_gear_slot') && lastEquipItemId) {
      const curBag = window.Inventory?.bagQuantity?.(lastEquipItemId) || 0;
      const prevBag = seenBagQty.get(lastEquipItemId) ?? curBag;
      if (curBag < prevBag) {
        complete('equip_gear');
        return;
      }
    }
    // new_skill: complete once user closes skills panel after viewing the editor substep
    if (!done.has('new_skill') && skillDialogSeen && !isShown($('skills-panel'))) {
      complete('new_skill');
      return;
    }
    // consumables: complete once consumable bag count decreases
    if (!done.has('consumables') && seenSubsteps.has('consumables')) {
      for (const [id, prev] of lastConsumableCounts) {
        const cur = window.Inventory?.bagQuantity?.(id) || 0;
        if (cur < prev) {
          complete('consumables');
          return;
        }
      }
    }
    // The later steps finish by themselves once the thing they pointed at is over (the foe is dead, the quest handed in, the gear repaired...).
    for (const id of Object.keys(MORE)) {
      if (!done.has(id) && seenSubsteps.has(id) && !MORE[id].when()) { complete(id); return; }
    }
    // merchant: complete after transacting or closing npc-dialogue after seeing shop view
    if (!done.has('merchant') && (merchantTransacted || (merchantModeSeen && !isShown($('npc-dialogue'))))) {
      complete('merchant');
      return;
    }
  }

  function stageRectFor(el, stage) {
    if (!el || !isShown(el)) return null;
    const sr = stage.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    const sx = sr.width ? stage.clientWidth / sr.width : 1;
    const sy = sr.height ? stage.clientHeight / sr.height : 1;
    return {
      left: (r.left - sr.left) * sx,
      top: (r.top - sr.top) * sy,
      width: r.width * sx,
      height: r.height * sy,
      right: (r.right - sr.left) * sx,
      bottom: (r.bottom - sr.top) * sy,
    };
  }

  function rectsOverlap(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function overlapArea(a, b) {
    const x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
    const y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
    return x * y;
  }

  function positionStep(step) {
    const stage = $('stage');
    if (!stage || !layer || !tipEl) return;
    const W = stage.clientWidth || innerWidth;
    const H = stage.clientHeight || innerHeight;
    const targetRect = step.target ? stageRectFor(step.target, stage) : null;

    if (targetRect) {
      const pad = 4;
      glowEl.style.left = `${Math.max(2, targetRect.left - pad)}px`;
      glowEl.style.top = `${Math.max(2, targetRect.top - pad)}px`;
      glowEl.style.width = `${Math.min(W - 4, targetRect.width + pad * 2)}px`;
      glowEl.style.height = `${Math.min(H - 4, targetRect.height + pad * 2)}px`;
      glowEl.hidden = false;
    } else {
      glowEl.hidden = true;
    }

    tipEl.hidden = false;
    const tipRect = tipEl.getBoundingClientRect();
    const sr = stage.getBoundingClientRect();
    const sx = sr.width ? stage.clientWidth / sr.width : 1;
    const sy = sr.height ? stage.clientHeight / sr.height : 1;
    const tipW = (tipRect.width || 290) * sx;
    const tipH = (tipRect.height || 130) * sy;
    const margin = 12;
    const gap = 14;

    const avoid = [];
    if (targetRect) avoid.push(targetRect);
    const stickRect = COARSE() ? stageRectFor($('touch-stick'), stage) : null;
    if (stickRect && step.target !== $('touch-stick')) avoid.push(stickRect);
    const lowGfxRect = stageRectFor($('low-gfx-suggestion'), stage);
    if (lowGfxRect) avoid.push(lowGfxRect);
    const dlgEl = step.allowedDialog ? $(step.allowedDialog) : null;
    if (dlgEl && isShown(dlgEl)) {
      if (dlgEl.classList.contains('merchant-mode')) {
        const invRect = stageRectFor($('inventory-list'), stage);
        if (invRect) avoid.push(invRect);
      }
      for (const btn of dlgEl.querySelectorAll('button')) {
        if (step.target && (btn === step.target || step.target.contains(btn))) continue;
        const br = stageRectFor(btn, stage);
        if (br) avoid.push(br);
      }
    }

    let best = null;
    if (targetRect) {
      const cx = (targetRect.left + targetRect.right) / 2;
      const cy = (targetRect.top + targetRect.bottom) / 2;
      const candidates = [
        { side: 'bottom', x: cx - tipW / 2, y: targetRect.bottom + gap },
        { side: 'top', x: cx - tipW / 2, y: targetRect.top - tipH - gap },
        { side: 'right', x: targetRect.right + gap, y: cy - tipH / 2 },
        { side: 'left', x: targetRect.left - tipW - gap, y: cy - tipH / 2 },
      ];
      if (dlgEl) {
        const panel = dlgEl.querySelector('.panel, .gossip-window, .skills-window, .equipment-workspace');
        const pr = panel ? stageRectFor(panel, stage) : null;
        if (pr) {
          candidates.push(
            { side: 'left', x: pr.right + gap, y: Math.min(H - tipH - margin, Math.max(margin, cy - tipH / 2)) },
            { side: 'right', x: pr.left - tipW - gap, y: Math.min(H - tipH - margin, Math.max(margin, cy - tipH / 2)) }
          );
        }
      }
      for (const c of candidates) {
        const clampedX = Math.max(margin, Math.min(W - tipW - margin, c.x));
        const clampedY = Math.max(margin, Math.min(H - tipH - margin, c.y));
        const box = { left: clampedX, top: clampedY, right: clampedX + tipW, bottom: clampedY + tipH };
        let penalty = Math.abs(clampedX - c.x) + Math.abs(clampedY - c.y);
        for (const a of avoid) penalty += overlapArea(box, a) * 20;
        if (!best || penalty < best.penalty) best = { ...c, x: clampedX, y: clampedY, penalty };
      }
    } else {
      // Fallback floating placement in upper-left/center, clear of touch-stick and low-gfx banner
      let x = Math.max(margin, Math.min(W - tipW - margin, (W - tipW) / 2));
      let y = Math.max(margin, Math.min(H - tipH - margin, COARSE() ? margin + 10 : Math.round(H * 0.14)));
      if (lowGfxRect && y < lowGfxRect.bottom + gap) y = Math.min(H - tipH - margin, lowGfxRect.bottom + gap);
      const box = { left: x, top: y, right: x + tipW, bottom: y + tipH };
      if (stickRect && rectsOverlap(box, stickRect)) y = margin + 8;
      best = { side: 'none', x, y };
    }

    tipEl.style.left = `${Math.round(best.x)}px`;
    tipEl.style.top = `${Math.round(best.y)}px`;
    arrowEl.dataset.side = best.side;
    if (best.side === 'none' || !targetRect) {
      arrowEl.hidden = true;
    } else {
      arrowEl.hidden = false;
      const tx = Math.max(18, Math.min(tipW - 18, (targetRect.left + targetRect.right) / 2 - best.x));
      const ty = Math.max(18, Math.min(tipH - 18, (targetRect.top + targetRect.bottom) / 2 - best.y));
      arrowEl.style.left = (best.side === 'top' || best.side === 'bottom') ? `${Math.round(tx)}px` : '';
      arrowEl.style.top = (best.side === 'left' || best.side === 'right') ? `${Math.round(ty)}px` : '';
    }
    active.rect = targetRect;
  }

  function render() {
    ensureDom();
    if (!layer) return;
    if (!hero || disabled) {
      hide();
      return;
    }

    updateAutoCompletions();
    if (disabled) { hide(); return; }

    const step = pickNextStep();
    if (!step || isInterrupted(step.allowedDialog, step.allowGhost)) {
      hide();
      return;
    }

    active = step;
    seenSubsteps.add(step.sub);
    if (step.sub === 'first_quest') {
      if (seenQuestsCount === null) seenQuestsCount = Array.isArray(hero.quests) ? hero.quests.length : 0;
      if (seenKills === null) seenKills = hero.kills || 0;
    }
    if (step.sub === 'equip_gear_slot' && lastEquipItemId) {
      seenBagQty.set(lastEquipItemId, window.Inventory?.bagQuantity?.(lastEquipItemId) || 0);
    }
    if (step.id === 'consumables') {
      for (const c of bagConsumables()) {
        if (!lastConsumableCounts.has(c.item.id)) lastConsumableCounts.set(c.item.id, c.qty);
      }
    }

    if (step.highlightAttrs) applyAttrFocus();
    else clearAttrFocus();

    const idx = MILESTONES.indexOf(step.id) + 1;
    if (step.expiresOn && !step.expiresOn()) { hide(); return; }
    titleEl.textContent = tr(step.title);
    progressEl.textContent = `${done.size}/${MILESTONES.length}`;
    bodyEl.textContent = tr(step.body);
    disableBtn.textContent = tr('Disable tutorial');
    gotItBtn.textContent = tr('Got it');
    layer.hidden = false;
    positionStep(step);
    layer.dataset.step = step.id;
    layer.dataset.substep = step.sub;
    layer.dataset.index = String(idx);
  }

  function hide() {
    active = null;
    clearAttrFocus();
    if (!layer) return;
    layer.hidden = true;
    if (glowEl) glowEl.hidden = true;
    if (tipEl) tipEl.hidden = true;
    delete layer.dataset.step;
    delete layer.dataset.substep;
  }

  function scheduleRender() {
    if (syncQueued) return;
    syncQueued = true;
    requestAnimationFrame(() => {
      syncQueued = false;
      render();
    });
  }

  function complete(id) {
    if (!MILESTONES.includes(id)) return;
    if (!done.has(id)) {
      done.add(id);
      pendingComplete.add(id);
      sendCommand({ op: 'complete', id });
    }
    render();
  }

  function disable() {
    if (!disabled) {
      disabled = true;
      pendingDisable = true;
      sendCommand({ op: 'disable' });
    }
    hide();
  }

  function reset() {
    done.clear();
    disabled = false;
    pendingComplete.clear();
    pendingDisable = false;
    seenSubsteps.clear();
    seenQuestsCount = hero && Array.isArray(hero.quests) ? hero.quests.length : null;
    seenKills = hero ? (hero.kills || 0) : null;
    seenBagQty.clear();
    lastEquipItemId = null;
    lastConsumableCounts.clear();
    skillDialogSeen = false;
    merchantModeSeen = false;
    merchantTransacted = false;
    sendCommand({ op: 'reset' });
    render();
  }

  function onSnapshot(own) {
    if (!own) {
      hero = null;
      lastHeroId = null;
      done.clear();
      disabled = false;
      pendingComplete.clear();
      pendingDisable = false;
      hide();
      return;
    }
    if (own.id !== lastHeroId) {
      lastHeroId = own.id;
      done = new Set(Array.isArray(own.tutorialDone) ? own.tutorialDone : []);
      disabled = !!own.tutorialDisabled;
      pendingComplete.clear();
      pendingDisable = false;
      seenSubsteps.clear();
      seenQuestsCount = null;
      seenKills = null;
      seenBagQty.clear();
      lastEquipItemId = null;
      lastConsumableCounts.clear();
      skillDialogSeen = false;
      merchantModeSeen = false;
      merchantTransacted = false;
    } else {
      if (Array.isArray(own.tutorialDone)) {
        const serverDone = new Set(own.tutorialDone);
        for (const id of [...pendingComplete]) {
          if (serverDone.has(id)) pendingComplete.delete(id);
        }
        done = new Set([...serverDone, ...pendingComplete]);
      }
      if (typeof own.tutorialDisabled === 'boolean') {
        if (pendingDisable && own.tutorialDisabled) pendingDisable = false;
        disabled = own.tutorialDisabled || pendingDisable;
      }
    }
    hero = own;
    scheduleRender();
  }

  function onEvent(event) {
    if (!event) return;
    if (event.type === 'slimeDie' && active?.id === 'first_quest') {
      complete('first_quest');
      return;
    }
    if (event.type === 'levelup') {
      scheduleRender();
    }
  }

  // Track skill assignments, equipment changes, shop transactions, resize & locale updates
  addEventListener('inventory-change', scheduleRender);
  addEventListener('character-stats-change', scheduleRender);
  addEventListener('resize', scheduleRender);
  addEventListener('click', e => {
    if (e.target.closest?.('#skill-library button, #skill-editor-slots button')) {
      skillDialogSeen = true;
      if (active?.id === 'new_skill' && active.sub === 'new_skill_panel') {
        scheduleRender();
      }
    }
    if (e.target.closest?.('#npc-inventory button') && active?.id === 'merchant') {
      if (e.target.closest?.('#sell-junk, .merchant-buy, .merchant-sell, .gossip-button')) {
        merchantTransacted = true;
        scheduleRender();
      }
    }
  }, true);

  return {
    MILESTONES,
    onSnapshot,
    onEvent,
    refresh: scheduleRender,
    render,
    complete,
    disable,
    reset,
    state: () => ({
      active: active ? { id: active.id, sub: active.sub, title: active.title, body: active.body, targetId: active.target?.id || null } : null,
      done: [...done],
      disabled,
    }),
  };
})();
