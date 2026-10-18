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
  // Words the harvest cannot see because they are plain lowercase identifiers in the scripts (weather levels, class and
  // item kinds, as the item tooltips print them).
  const manual = {
    'light':'lätt', 'medium':'måttlig', 'heavy':'kraftig', 'none':'ingen',
    'gold':'guld', 'slots':'platser', 'Indoors':'Inomhus',
    warrior:'krigare', mage:'magiker', assassin:'lönnmördare', priest:'präst', hunter:'jägare',
    headgear:'huvudbonad', shoulders:'axlar', gloves:'handskar', armor:'rustning', weapon:'vapen', pants:'byxor',
    necklace:'halsband', accessory:'smycke',
  };
  const staticTemplates = [
    [/^Your purse: ([\d,.]+) gold$/, (_,n) => `Din börs: ${n} guld`],
    [/^([\d,.]+) gold$/, (_,n) => `${n} guld`],
    [/^([\d,.]+) online$/, (_,n) => `${n} online`],
    [/^([\d,.]+)\/([\d,.]+) slots · ([\d,.]+) free$/, (_,used,total,free) => `${used}/${total} platser · ${free} lediga`],
    [/^Recommended level (\d+)$/, (_,level) => `Rekommenderad nivå ${level}`],
    [/^Level (\d+)$/, (_,level) => `Nivå ${level}`],
    [/^Lv (\d+)$/, (_,level) => `Nivå ${level}`],
    [/^([\d,.]+) of ([\d,.]+) characters$/, (_,count,max) => `${count} av ${max} karaktärer`],
    [/^World time · (Night|Dawn|Day|Dusk)( · indoor light)? · one day every 20 minutes$/, (_,phase,inside) => `Världstid · ${dictionary[phase]}${inside?' · inomhusljus':''} · ett dygn på 20 minuter`],
  ];
  // Short phrases with numbers, replaced inside longer composed lines ("Rank 3:", "6s cooldown."). A placeholder is a number.
  const number = '(\\d+(?:[.,]\\d+)?)';
  const phrases = (window.SV_PHRASES || []).map(([english, swedish]) => {
    const parts = english.split(/\{\d+\}/g).map(escape);
    const first = /^\w/.test(english) ? '(?<![\\w])' : '', last = /\w$/.test(english) ? '(?![\\w])' : '';
    return [new RegExp(first + parts.join(number) + last, 'g'), swedish.replace(/\{(\d+)\}/g, (_, i) => '$' + (+i + 1))];
  });
  // A piece caught by a template ({0}) is translated only when the Swedish template asks for it ({0:t}), or when it is a
  // fragment (it starts with a space or a punctuation mark, as " each" or ", select to assign"); a bare word could be a
  // player's name.
  const fragmentKeys = Object.keys(dictionary).filter(key => key !== key.trim() || /^[,.·(]/.test(key)).sort((a, b) => b.length - a.length);
  const fragment = text => fragmentKeys.reduce((left, key) => left.includes(key) ? left.split(key).join(dictionary[key]) : left, text);
  const lookup = value => {
    const exact = dictionary[value] || manual[value];
    if (exact) return exact;
    for (const [pattern, replacement] of staticTemplates) if (pattern.test(value)) return value.replace(pattern,replacement);
    for (const [pattern, target] of windowTemplates) {
      const match = value.match(pattern);
      if (match) return target.replace(/\{(\d+)(:t)?\}/g, (_,index,wanted) => wanted ? translate(match[+index + 1] || '') : segment(fragment(match[+index + 1] || '')));
    }
    return null;
  };
  const rephrase = value => phrases.reduce((text, [pattern, swedish]) => text.replace(pattern, swedish), value);
  // A composed line (parts joined with " · ", sentences, line breaks) is translated part by part. A single part is never
  // looked up as a whole here, so a name that equals a dictionary word stays as it is.
  const SEPARATORS = /((?<=[.!?])\s+| · |\n)/;
  const segment = text => {
    const phrased = rephrase(text), parts = phrased.split(SEPARATORS);
    if (parts.length < 3) return phrased;
    return parts.map((part, index) => {
      const bare = part.trim(), own = index % 2 || !bare ? null : lookup(bare) || rephrase(bare);
      return own && own !== bare ? part.match(/^\s*/)[0] + own : part;
    }).join('');
  };
  const translate = value => {
    if (language !== 'sv' || typeof value !== 'string') return value;
    const whole = lookup(value);
    if (whole) return whole;
    const phrased = rephrase(value);
    if (phrased !== value) { const again = lookup(phrased); if (again) return again; }
    return segment(value);
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
    if (node.parentElement.closest('script,style,#login-name,[data-player-name]')) return;
    const chatLine = node.parentElement.closest('#chat-log p');
    if (chatLine?.querySelector('b')) return; // other players' names and messages
    const source = node.nodeValue;
    const trim = source.trim();
    if (!trim || !/[A-Za-z]{2}/.test(trim)) return;
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
