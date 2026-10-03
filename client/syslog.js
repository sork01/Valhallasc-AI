/* The chat window's System tab: every combat and game event for the player's own character - damage dealt and taken (and by what),
   misses and dodges, kills and XP, loot, healing, level-ups. Lines come from the server's events; every string goes through textContent.
   API: SystemLog.add(text, cls), SystemLog.event(packet, selfId), SystemLog.show('chat' | 'system'). */
(() => {
  const $ = name => document.getElementById(name);
  const MAX = 200;
  const tabs = { chat: ['tab-chat', 'chat-log'], system: ['tab-system', 'system-log'] };
  let current = 'chat';
  function show(name) {
    if (!tabs[name]) return;
    current = name;
    for (const [key, [tab, log]] of Object.entries(tabs)) {
      const on = key === name;
      $(tab).setAttribute('aria-selected', String(on)); $(tab).classList.toggle('on', on);
      if (on) $(tab).classList.remove('unread');
      $(log).hidden = !on;
    }
    const log = $(tabs[name][1]); log.scrollTop = log.scrollHeight;
  }
  function add(text, cls) {
    const log = $('system-log'), line = document.createElement('p');
    if (cls) line.className = cls;
    line.textContent = text; log.append(line);
    while (log.children.length > MAX) log.firstElementChild.remove();
    log.scrollTop = log.scrollHeight;
    if (current !== 'system') $('tab-system').classList.add('unread');
  }
  const enemyName = kind => (window.Field?.enemyName?.(kind)) || kind || 'something';
  const skillName = id => (window.WORLD_SKILLS || []).find(s => s.id === id)?.name || id;
  const itemName = id => (window.WORLD_ITEMS || []).find(i => i.id === id)?.name || id;
  const who = (kind, level) => `${enemyName(kind)}${level ? ` (Lv ${level})` : ''}`;
  const playerName = id => (window.Field?.remotePlayers || []).find(p => p.id === id)?.look?.name || 'A party member';
  // The lines for one event. Only events about the player's own character are shown.
  function lines(e, me) {
    if (e.actor !== me) return [];
    switch (e.kind) {
      case 'hit': return [[`You hit ${who(e.enemy, e.level)} for ${e.value}${e.crit ? ' (critical)' : ''} with ${e.skill ? skillName(e.skill) : 'a basic attack'}.`, e.crit ? 'sys-crit' : 'sys-dealt']];
      case 'miss': return [['Your attack missed.', 'sys-dealt']];
      case 'slimeDie': return [[`${who(e.enemy, e.level)} was defeated. +${e.xp} XP.`, 'sys-xp']];
      case 'partyXp': return [[`${who(e.enemy, e.level)} was defeated by your party. +${e.xp} XP.`, 'sys-xp']];
      case 'hurt': return [[`${e.enemy ? who(e.enemy, e.level) : 'Something'} hits you for ${e.value}.`, 'sys-taken']];
      case 'dodge': return [[`You dodge an attack${e.enemy ? ` from ${who(e.enemy, e.level)}` : ''}.`, 'sys-taken']];
      case 'death': return [[`You were slain${e.enemy ? ` by ${who(e.enemy, e.level)}` : ''}.`, 'sys-taken']];
      case 'respawn': return [['You return to life.', 'sys-heal']];
      case 'skill': return [[`You cast ${skillName(e.skill)}.`, 'sys-skill'], ...(e.heal > 0 ? [[`${skillName(e.skill)} heals you for ${e.heal}.`, 'sys-heal']] : [])];
      case 'healed': return e.value > 0 ? [[e.from === me ? `You heal yourself for ${e.value}.` : `${playerName(e.from)} heals you for ${e.value}.`, 'sys-heal']] : [];
      case 'consume': return [[`You use ${itemName(e.item)}${e.value > 0 ? `: +${e.value} health` : ''}${e.mana > 0 ? `${e.value > 0 ? ',' : ':'} +${e.mana} mana` : ''}.`, 'sys-heal']];
      case 'itemPickup': return [[`You pick up ${e.quantity > 1 ? e.quantity + ' × ' : ''}${e.name || itemName(e.item)}.`, 'sys-loot']];
      case 'pickup': return [[`You pick up ${e.value} gold.`, 'sys-loot']];
      case 'levelup': return [[`You reached level ${e.level}!${e.unlocked?.length ? ` New skills: ${e.unlocked.map(skillName).join(', ')}.` : ''}`, 'sys-xp']];
      case 'portal': return [['You pass through a portal.', 'sys-skill']];
      default: return [];
    }
  }
  window.SystemLog = {
    add, show, lines,
    event(packet, me) { for (const [text, cls] of lines(packet, me)) add(text, cls); },
  };
  document.addEventListener('DOMContentLoaded', () => {
    // A mouse click hands the keyboard back to the game, so Enter still opens the chat box afterwards.
    for (const [name, [tab]] of Object.entries(tabs)) $(tab).addEventListener('click', event => { show(name); if (event.detail > 0) event.currentTarget.blur(); });
    $('chat-input').addEventListener('focus', () => show('chat'));
  });
})();
