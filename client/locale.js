'use strict';
// UI-only localization. IDs, commands and server-owned state always stay in English.
(() => {
  const key = 'valhallasc.save.v1';
  let language = 'en';
  try { language = JSON.parse(localStorage.getItem(key) || '{}').lang || (/^sv\b/i.test(navigator.language) ? 'sv' : 'en'); } catch (_) {}
  if (!['en', 'ko', 'sv'].includes(language)) language = 'en';
  const dictionary = window.SV_TEXT || {};
  const escape = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const windowTemplates = (window.SV_TEMPLATES || []).map(([english, swedish]) => {
    const parts = english.split(/\{\d+\}/g);
    return [new RegExp('^' + parts.map(escape).join('([\\s\\S]*?)') + '$'), swedish];
  });
  const manual = {
    'English':'Engelska', 'Swedish':'Svenska', 'Korean':'Koreanska',
    'Language':'Språk', 'Rain':'Regn', 'Snow':'Snö', 'Fog':'Dimma',
    'Thunderstorm':'Åskväder', 'Wind':'Vind', 'Sandstorm':'Sandstorm',
    'Clear':'Klart', 'Indoors':'Inomhus', 'gold':'guld', 'slots':'platser',
    'Slime Gel':'Slemgelé', 'Blue Slime Gel':'Blå slemgelé', 'Pink Slime Gel':'Rosa slemgelé',
    'Night':'Natt', 'Dawn':'Gryning', 'Day':'Dag', 'Dusk':'Skymning',
    'light':'lätt', 'medium':'måttlig', 'heavy':'kraftig', 'none':'ingen',
  };
  const staticTemplates = [
    [/^Your purse: ([\d,.]+) gold$/, (_,n) => `Din börs: ${n} guld`],
    [/^([\d,.]+) gold$/, (_,n) => `${n} guld`],
    [/^([\d,.]+) online$/, (_,n) => `${n} uppkopplade`],
    [/^([\d,.]+)\/([\d,.]+) slots · ([\d,.]+) free$/, (_,used,total,free) => `${used}/${total} platser · ${free} lediga`],
    [/^Recommended level (\d+)$/, (_,level) => `Rekommenderad nivå ${level}`],
    [/^Level (\d+)$/, (_,level) => `Nivå ${level}`],
    [/^Lv (\d+)$/, (_,level) => `Nivå ${level}`],
    [/^([\d,.]+) of ([\d,.]+) characters$/, (_,count,max) => `${count} av ${max} karaktärer`],
    [/^World time · (Night|Dawn|Day|Dusk)( · indoor light)? · one day every 20 minutes$/, (_,phase,inside) => `Världstid · ${manual[phase]}${inside?' · inomhusljus':''} · ett dygn på 20 minuter`],
  ];
  const translate = value => {
    if (language !== 'sv' || typeof value !== 'string') return value;
    const exact = manual[value] || dictionary[value];
    if (exact) return exact;
    for (const [pattern, replacement] of staticTemplates) if (pattern.test(value)) return value.replace(pattern,replacement);
    for (const [pattern, target] of windowTemplates) {
      const match = value.match(pattern);
      if (match) return target.replace(/\{(\d+)\}/g, (_,index) => match[+index + 1] || '');
    }
    return value.replace(/\b(gold|slots|Indoors|Rain|Snow|Fog|Thunderstorm|Wind|Sandstorm|Clear|Night|Dawn|Day|Dusk)\b/g, word => manual[word] || word);
  };
  // Catalog strings come from the checked-in world data. Mutating display fields does not
  // affect IDs, server validation, item ownership or the network protocol.
  const displayKeys = new Set(['name', 'title', 'description', 'label', 'dialogue', 'role']);
  function data(value) {
    if (language !== 'sv' || !value || typeof value !== 'object') return;
    if (Array.isArray(value)) { value.forEach(data); return; }
    for (const [field, child] of Object.entries(value)) {
      if (displayKeys.has(field) && typeof child === 'string') value[field] = translate(child);
      else if (child && typeof child === 'object') data(child);
    }
  }
  [window.WORLD_MAP, window.WORLD_ITEMS, window.WORLD_SKILLS, window.WORLD_PASSIVES].forEach(data);

  function textNode(node) {
    if (language !== 'sv' || !node?.parentElement) return;
    if (node.parentElement.closest('script,style,#npc-name,#login-name,[data-player-name]')) return;
    const chatLine = node.parentElement.closest('#chat-log p');
    if (chatLine?.querySelector('b')) return; // other players' names and messages
    const source = node.nodeValue;
    const trim = source.trim();
    if (!trim || !/[A-Za-z]{3}/.test(trim)) return;
    const result = translate(trim);
    if (result !== trim) node.nodeValue = source.replace(trim, result);
  }
  function walk(root) {
    if (root.nodeType === Node.TEXT_NODE) { textNode(root); return; }
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) textNode(node);
    attributes(root);
    root.querySelectorAll('[title],[placeholder],[aria-label]').forEach(attributes);
  }
  function attributes(node) {
    for (const name of ['title','placeholder','aria-label']) {
      if (!node.hasAttribute(name)) continue;
      const before = node.getAttribute(name), after = translate(before);
      if (after !== before) node.setAttribute(name, after);
    }
  }
  if (language === 'sv') {
    document.documentElement.lang = 'sv';
    walk(document.body);
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'characterData') textNode(record.target);
        else if (record.type === 'attributes') attributes(record.target);
        else for (const node of record.addedNodes) walk(node);
      }
    }).observe(document.body, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','placeholder','aria-label']});
  }
  window.Locale = {get language(){return language;},translate,data};
})();
