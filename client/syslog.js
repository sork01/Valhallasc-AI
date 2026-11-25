/* The chat window shows typed game messages and independently filtered views of the current session. */
(() => {
  const $ = name => document.getElementById(name);
  const tr = text => window.Locale?.translate(text) || text;
  const STORAGE = 'valhallasc.chat-tabs.v1';
  const MAX = 500;
  const categories = {
    combat: 'Combat', abilities: 'Abilities and healing', progress: 'Experience and skill gains',
    items: 'Items and currency', fishing: 'Fishing', mining: 'Mining', alchemy: 'Alchemy',
    enchanting: 'Enchanting', crafting: 'Blacksmithing', quests: 'Quests',
    travel: 'Travel', notices: 'Game notices', chat: 'World chat', party: 'Party chat',
  };
  const playerChat = category => category === 'chat' || category === 'party';
  const selections = value => Array.isArray(value) ? value.filter(key => Object.hasOwn(categories, key)) : null;
  let custom = [], systemFilter = null;
  try {
    const prefs = JSON.parse(localStorage.getItem(STORAGE)) || {};
    systemFilter = selections(prefs.system);
    if (Array.isArray(prefs.tabs)) custom = prefs.tabs.filter(tab => typeof tab.name === 'string')
      .map(tab => ({ name: tab.name.trim().slice(0, 24), filters: selections(tab.filters) }))
      .filter(tab => tab.name);
  } catch (_) {}
  function persist() {
    try { localStorage.setItem(STORAGE, JSON.stringify({ system: systemFilter, tabs: custom })); } catch (_) {}
  }

  const history = [];
  let current = 'chat', editing = null, editorButton = null;
  const panel = key => $(key === 'chat' ? 'chat-log' : key === 'system' ? 'system-log' : 'custom-chat-log');
  const tabs = () => [...($('chat-tab-list')?.children || [])];
  const filterFor = key => key === 'system' ? systemFilter : custom[key]?.filters;
  function matches(key, entry) {
    if (key === 'chat') return false;
    if (key === 'system' && playerChat(entry.category)) return false;
    return filterFor(key)?.includes(entry.category) ?? true;
  }
  function renderLine(entry) {
    const line = document.createElement('p');
    line.className = entry.cls || '';
    line.dataset.category = entry.category;
    if (entry.name) {
      const speaker = document.createElement('b');
      speaker.textContent = entry.name + ': ';
      if (entry.name.startsWith('[GM]')) speaker.className = 'gm';
      line.append(speaker, entry.text);
    } else if (entry.mark) fill(line, entry.text, entry.mark);
    else line.textContent = entry.text;
    return line;
  }
  function render(key) {
    const log = panel(key);
    log.replaceChildren(...history.filter(entry => matches(key, entry)).map(renderLine));
    log.scrollTop = log.scrollHeight;
  }
  function hideEditor() {
    editing = null;
    $('chat-filters').hidden = true;
    $('chat-filter-open').setAttribute('aria-expanded', 'false');
    $('chat-tab-add').setAttribute('aria-expanded', 'false');
  }
  function show(key) {
    key = String(key);
    if (key !== 'chat' && key !== 'system' && !custom[key]) return;
    hideEditor();
    current = key;
    for (const tab of tabs()) {
      const selected = tab.dataset.tab === String(key);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      tab.classList.toggle('on', selected);
      if (selected) {
        tab.classList.remove('unread');
        tab.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
      }
    }
    $('chat-filter-open').hidden = key === 'chat';
    for (const name of ['chat-log', 'system-log', 'custom-chat-log']) $(name).hidden = panel(key).id !== name;
    if (key !== 'chat') render(key);
    else panel(key).scrollTop = panel(key).scrollHeight;
  }
  function rebuildTabs() {
    for (const tab of tabs()) if (tab.classList.contains('custom-chat-tab')) tab.remove();
    for (const [index, tab] of custom.entries()) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'custom-chat-tab';
      button.dataset.tab = String(index);
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', 'custom-chat-log');
      button.setAttribute('translate', 'no');
      button.textContent = tab.name;
      $('chat-tab-list').append(button);
    }
  }
  function openEditor(key, button) {
    if (editing === key) { show(current); return; }
    hideEditor();
    editing = key;
    editorButton = button;
    panel(current).hidden = true;
    $('chat-filters').hidden = false;
    button.setAttribute('aria-expanded', 'true');
    $('chat-tab-label').hidden = key === 'system';
    $('chat-tab-name').required = key !== 'system';
    $('chat-tab-name').value = custom[key]?.name || '';
    $('chat-tab-delete').hidden = !custom[key];
    const options = $('chat-filter-options');
    options.replaceChildren();
    for (const [category, title] of Object.entries(categories)) {
      if (key === 'system' && playerChat(category)) continue;
      const label = document.createElement('label'), checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.name = 'category';
      checkbox.value = category;
      checkbox.checked = filterFor(key)?.includes(category) ?? !playerChat(category);
      label.append(checkbox, tr(title));
      options.append(label);
    }
    if (key !== 'system') $('chat-tab-name').focus({ preventScroll:true });
    else options.querySelector('input')?.focus({ preventScroll:true });
  }
  function saveEditor(event) {
    event.preventDefault();
    const key = editing;
    if (key === null) return;
    const filters = [...$('chat-filter-options').querySelectorAll('input')].filter(box => box.checked).map(box => box.value);
    if (key === 'system') {
      systemFilter = filters.length === Object.keys(categories).filter(key => !playerChat(key)).length ? null : filters;
      persist(); show(key); editorButton?.focus({ preventScroll:true });
      return;
    }
    const input = $('chat-tab-name'), name = input.value.trim();
    if (!name) { input.focus(); return; }
    const index = key === 'new' ? custom.length : Number(key);
    custom[index] = { name, filters };
    persist(); rebuildTabs(); show(String(index));
    tabs().find(tab => tab.dataset.tab === String(index))?.focus({ preventScroll:true });
  }
  function record(entry) {
    history.push(entry);
    const removed = history.length > MAX ? history.shift() : null;
    for (const tab of tabs()) {
      const key = tab.dataset.tab;
      if (key === 'chat') continue;
      if (key === 'system' || key === current) {
        const log = panel(key);
        const following = log.scrollHeight - log.clientHeight - log.scrollTop < 16;
        if (removed && matches(key, removed)) log.firstElementChild?.remove();
        if (matches(key, entry)) log.append(renderLine(entry));
        if (following) log.scrollTop = log.scrollHeight;
      }
      if (key !== current && matches(key, entry)) tab.classList.add('unread');
    }
  }
  // An item name in its rarity colour: `mark` = { name, rarity }. The sentence is translated first (Locale would otherwise see three
  // text nodes and miss the "{0}" template), the translated name is located in it, and the line then opts out of Locale. Built with
  // DOM nodes only: item names are data. Any miss falls back to the plain line.
  function fill(line, text, mark) {
    const shown = window.Locale?.translate ? window.Locale.translate(text) : text;
    const name = [mark.name, window.Locale?.translate?.(mark.name)].find(n => n && shown.lastIndexOf(n) >= 0);
    if (!name || !/^[a-z]+$/.test(mark.rarity || '')) { line.textContent = text; return; }
    const at = shown.lastIndexOf(name), span = document.createElement('span');
    span.className = 'sys-rarity'; span.dataset.rarity = mark.rarity; span.textContent = name;
    line.setAttribute('translate', 'no');
    line.append(shown.slice(0, at), span, shown.slice(at + name.length));
  }
  function add(text, cls, mark, category = 'notices') {
    if (typeof text === 'string' && text.trim()) record({ text, cls, mark, category });
  }
  function chat(text, name, channel) {
    record({ text, name, cls: channel ? 'chat-' + channel : '', category: channel === 'party' ? 'party' : 'chat' });
  }
  const enemyName = kind => (window.Field?.enemyName?.(kind)) || kind || 'something';
  const skillName = id => (id?.startsWith('enchant_proc_') && window.Enchanting?.name(id.slice('enchant_proc_'.length)))
    || (window.WORLD_SKILLS || []).find(s => s.id === id)?.name || id;
  const itemName = id => (window.WORLD_ITEMS || []).find(i => i.id === id)?.name || id;
  const rarityOf = id => { const i = (window.WORLD_ITEMS || []).find(x => x.id === id); return i ? { name: i.name, rarity: i.rarity } : null; };
  const who = (kind, level) => `${enemyName(kind)}${level ? ` (Lv ${level})` : ''}`;
  const playerName = id => (window.Field?.remotePlayers || []).find(p => p.id === id)?.look?.name || 'A party member';
  // The lines for one event. Only events about the player's own character are shown.
  function lines(e, me) {
    if (e.kind === 'cleared') return [['The dungeon is cleared.', 'sys-xp']];
    if (e.actor !== me) return [];
    switch (e.kind) {
      case 'hit': return [[`You hit ${who(e.enemy, e.level)} for ${e.value}${e.crit ? ' (critical)' : ''} with ${e.skill ? skillName(e.skill) : 'a basic attack'}.`, e.crit ? 'sys-crit' : 'sys-dealt']];
      case 'miss': return [['Your attack missed.', 'sys-dealt']];
      case 'slimeDie': return [[`${who(e.enemy, e.level)} was defeated. +${e.xp} XP.`, 'sys-xp']];
      case 'partyXp': return [[`${who(e.enemy, e.level)} was defeated by your party. +${e.xp} XP.`, 'sys-xp']];
      case 'hurt': return [[`${e.cause || (e.enemy ? who(e.enemy, e.level) : 'Something')} hits you for ${e.value}.`, 'sys-taken']];
      case 'dodge': return [[`You dodge an attack${e.enemy ? ` from ${who(e.enemy, e.level)}` : ''}.`, 'sys-taken']];
      case 'death': if (e.cause) return [[`You were killed by ${e.cause}.`, 'sys-taken']]; return [[`You were slain${e.enemy ? ` by ${who(e.enemy, e.level)}` : ''}.`, 'sys-taken']];
      case 'respawn': return [['You return to life.', 'sys-heal']];
      case 'skill': return [[`You cast ${skillName(e.skill)}.`, 'sys-skill'], ...(e.heal > 0 ? [[`${skillName(e.skill)} heals you for ${e.heal}.`, 'sys-heal']] : [])];
      case 'healed': return e.value > 0 ? [[e.from === me ? `You heal yourself for ${e.value}.` : `${playerName(e.from)} heals you for ${e.value}.`, 'sys-heal']] : [];
      case 'consume': return [[`You use ${itemName(e.item)}${e.value > 0 ? `: +${e.value} health` : ''}${e.mana > 0 ? `${e.value > 0 ? ',' : ':'} +${e.mana} ${e.resourceType || 'mana'}` : ''}.`, 'sys-heal', rarityOf(e.item)]];
      case 'itemPickup': {
        const def = (window.WORLD_ITEMS || []).find(i => i.id === e.item), name = e.name || itemName(e.item);
        return [[`You pick up ${e.quantity > 1 ? e.quantity + ' × ' : ''}${name}.`, 'sys-loot sys-item', { name, rarity: e.rarity || def?.rarity }]];
      }
      case 'fish_catch': {
        const name = itemName(e.item), amount = e.quantity || 1;
        const text = e.kg == null ? `You reel in ${name} ×${amount}.` : `You catch ${name} (ca ${e.kg} kg) ×${amount}.`;
        return [[text, 'sys-loot sys-item', { name, rarity: e.rarity || rarityOf(e.item)?.rarity }]];
      }
      case 'fish_miss': return [[e.text || 'It got away.', 'sys-taken']];
      case 'shotBlocked': return [['Your shot hits a wall.', 'sys-dealt']];
      case 'pickup': return [[`You pick up ${Money.text(e.value)}.`, 'sys-loot']];
      case 'levelup': return [[`You reached level ${e.level}!${e.unlocked?.length ? ` New skills: ${e.unlocked.map(skillName).join(', ')}.` : ''}`, 'sys-xp']];
      case 'portal': return [['You pass through a portal.', 'sys-skill']];
      case 'chestOpen': return [['You open a chest.', 'sys-loot']];
      case 'immune': return [['The target is immune.', 'sys-dealt']];
      default: return [];
    }
  }
  const eventCategories = {
    hit: 'combat', miss: 'combat', hurt: 'combat', dodge: 'combat', death: 'combat', immune: 'combat',
    shotBlocked: 'combat', respawn: 'abilities', ghost: 'abilities', skill: 'abilities', healed: 'abilities',
    consume: 'items', itemPickup: 'items', pickup: 'items', chestOpen: 'items',
    slimeDie: 'progress', partyXp: 'progress', levelup: 'progress', cleared: 'progress',
    fish_catch: 'fishing', fish_miss: 'fishing', portal: 'travel',
  };
  const professions = {
    fishing: 'Fishing', blacksmithing: 'Blacksmithing', alchemy: 'Alchemy', enchanting: 'Enchanting',
  };
  const services = {
    dialogue: 'notices', blacksmithing: 'crafting', enchanting: 'enchanting', alchemy: 'alchemy',
    picking: 'alchemy', mining: 'mining', bank: 'items', mail: 'items', shop: 'items', trade: 'items', pvp: 'combat',
  };
  let owner, inventory, skills, unreadMail;
  const reported = new Map();
  const inventoryCounts = entries => new Map(entries.map(({item, quantity}) => [item, quantity]));
  function noteReceipt(item, quantity) {
    reported.set(item, (reported.get(item) ?? 0) + quantity);
  }
  function trackInventory(packet) {
    if (!Array.isArray(packet.inventory)) return;
    const next = inventoryCounts(packet.inventory);
    if (inventory) {
      for (const [item, total] of next) {
        const quantity = total - (inventory.get(item) ?? 0) - (reported.get(item) ?? 0);
        if (quantity <= 0) continue;
        const name = itemName(item);
        const copy = packet.gearInstances?.filter(gear => gear.item === item).at(-1);
        const mark = copy ? { name, rarity: copy.rarity } : rarityOf(item);
        add(`You receive ${quantity} × ${name}.`, 'sys-loot sys-item', mark, 'items');
      }
    }
    inventory = next;
    reported.clear();
  }
  function skillGain(key, skill) {
    if (!skills || !Number.isFinite(skill)) return;
    const previous = skills[key];
    skills[key] = skill;
    if (previous != null && skill > previous) {
      add(`${professions[key]} skill increased to ${skill}.`, 'sys-xp', null, 'progress');
    }
  }
  function mailCount(count) {
    if (!Number.isFinite(count)) return;
    if (unreadMail != null && count > unreadMail) add('You have new mail.', 'sys-note');
    unreadMail = count;
  }
  function snapshot(own) {
    mailCount(own.mailUnread || 0);
    trackInventory(own);
    for (const key of Object.keys(professions)) skillGain(key, own.professions?.[key]?.skill);
  }
  function welcome(own) {
    if (owner && owner !== own.id) {
      history.length = 0;
      for (const name of ['chat-log', 'system-log', 'custom-chat-log']) $(name).replaceChildren();
      tabs().forEach(tab => tab.classList.remove('unread'));
      show('chat');
    }
    owner = own.id;
    inventory = null;
    skills = {};
    unreadMail = null;
    reported.clear();
    snapshot(own);
  }
  function categoryFor(text, kind) {
    if (kind === 'quest' || /^(?:Quest |You abandon|A new quest|Your questlog)/i.test(text)) return 'quests';
    if (kind === 'treasure' || /^(?:Roll for |Everyone passed on )/.test(text)) return 'items';
    if (/^Spark Travel/.test(text)) return 'travel';
    return 'notices';
  }
  function notice(text, kind, failed, name) {
    if (name && text) {
      record({ text, name, cls: 'chat-npc', category: 'notices' });
      return;
    }
    add(text, failed ? 'sys-taken' : 'sys-note', null, categoryFor(text, kind));
  }
  function packet(p) {
    if (p.type === 'mail_unread') mailCount(p.count);
    if (p.type === 'roll' && p.op === 'start') {
      add(`Loot roll started for ${itemName(p.item)}.`, 'sys-loot sys-item', rarityOf(p.item), 'items');
    }
    const category = services[p.type];
    if (!category) return;
    const message = p.notice || p.text;
    const failed = p.ok === false || p.state === 'error';
    if (message && (p.type !== 'dialogue' || history.at(-1)?.text !== message)) {
      add(message, failed ? 'sys-taken' : 'sys-note', null,
        p.type === 'dialogue' ? categoryFor(message, p.kind) : category);
    }
    if (p.state === 'done' && (p.type === 'picking' || p.type === 'mining')) {
      const name = itemName(p.item);
      const text = p.type === 'mining' ? `You mine ${p.quantity} × ${name}.` : `You pick ${p.quantity} × ${name}.`;
      add(text, 'sys-loot sys-item', rarityOf(p.item), category);
      noteReceipt(p.item, p.quantity);
    }
    const key = p.type === 'mining' ? 'blacksmithing' : p.type === 'picking' ? 'alchemy' : p.type;
    if (Object.hasOwn(professions, key)) skillGain(key, p.skill);
    trackInventory(p);
  }
  window.SystemLog = {
    add, show, lines, chat, notice, packet, snapshot, welcome,
    event(packet, me) {
      const category = eventCategories[packet.kind];
      for (const [text, cls, mark] of lines(packet, me)) add(text, cls, mark, category);
      if (packet.actor !== me) return;
      if (packet.kind === 'itemPickup' || packet.kind === 'fish_catch') noteReceipt(packet.item, packet.quantity || 1);
      if (packet.kind === 'fish_catch') skillGain('fishing', packet.skillUp);
    },
  };
  document.addEventListener('DOMContentLoaded', () => {
    const list = $('chat-tab-list');
    $('tab-chat').dataset.tab = 'chat';
    $('tab-system').dataset.tab = 'system';
    rebuildTabs();
    show('chat');
    list.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;
      show(button.dataset.tab);
      if (event.detail > 0) button.blur();
    });
    list.addEventListener('keydown', event => {
      const buttons = tabs(), at = buttons.indexOf(event.target);
      const offset = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      const index = offset ? (at + offset + buttons.length) % buttons.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : null;
      if (index === null) return;
      event.preventDefault();
      show(buttons[index].dataset.tab);
      buttons[index].focus();
    });
    $('chat-input').addEventListener('focus', () => show('chat'));
    $('chat-filter-open').addEventListener('click', event => openEditor(current, event.currentTarget));
    $('chat-tab-add').addEventListener('click', event => openEditor('new', event.currentTarget));
    $('chat-filters').addEventListener('submit', saveEditor);
    const cancel = () => { show(current); editorButton?.focus({ preventScroll:true }); };
    $('chat-filter-cancel').addEventListener('click', cancel);
    $('chat-filters').addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      event.stopPropagation();
      cancel();
    });
    $('chat-tab-delete').addEventListener('click', () => {
      if (!custom[editing]) return;
      custom.splice(Number(editing), 1);
      persist(); rebuildTabs(); show('system'); $('chat-filter-open').focus();
    });
  });
})();
