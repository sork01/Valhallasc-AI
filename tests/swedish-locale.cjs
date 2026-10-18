// L-SWEDISH-REDO: Locale.translate on the strings the client really builds, run against client/sv-data.js and
// client/locale.js in a bare sandbox (no browser): templates and their {0:t} pieces, composed lines ("Rank 3:", "· 6s cooldown."),
// and the rule that a bare word caught by a template, such as a player's name, is left alone.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const body = { nodeType: 1, querySelectorAll: () => [], hasAttribute: () => false };
const sandbox = {
  localStorage: { getItem: () => JSON.stringify({ lang: 'sv' }) }, navigator: { language: 'sv' },
  document: { documentElement: {}, body, createTreeWalker: () => ({ nextNode: () => null }) },
  Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 }, NodeFilter: { SHOW_TEXT: 4 }, MutationObserver: class { observe() {} },
  window: {},
};
sandbox.window = sandbox;
vm.createContext(sandbox);
for (const file of ['sv-data.js', 'locale.js']) vm.runInContext(fs.readFileSync(path.join(root, 'client', file), 'utf8'), sandbox, { filename: file });
const t = sandbox.Locale.translate;
let checks = 0;
const is = (english, swedish) => { assert.equal(t(english), swedish, english); checks++; };

// exact text and the old machine mistakes
is('Invite to party', 'Bjud in till grupp');
is('Ash Staff', 'Askstav');
is('Tempered Apprentice\'s Gloves', 'Härdade lärlingshandskar');
is('Defeat the Floodgate Keeper', 'Besegra Slussvaktaren');
// templates; a player's name is never translated, a {0:t} piece is
is('You and Fog are now friends.', 'Du och Fog är nu vänner.');
is('A new quest has found you: Onward to the Crags. Follow it in your journal (Q).', 'Ett nytt uppdrag har hittat dig: Vidare till Crags. Följ det i din journal (Q).');
is('Wind entered Greenmeadow.', 'Wind gick in i Greenmeadow.');
is('Sells for 5 gold each', 'Säljs för 5 guld styck');
is('You hit Green Slime for 12 (critical) with Hugg.', 'Du träffar Green Slime för 12 (kritiskt) med Hugg.');
is('Level 50 Warrior', 'Nivå 50 Krigare');
is('Slot 2: Cleave, select to assign', 'Plats 2: Klyvande hugg, välj för att tilldela');
// composed lines: numbers and ids inside longer text
is('Rage 12 / 100', 'Raseri 12 / 100');
is('Strength 12 (0 trained + 12 passive) ★', 'Styrka 12 (0 tränade + 12 passiva) ★');
is('+0.5 attack, +0.5% crit (60% cap)', '+0.5 attack, +0.5 % kritisk (60 % tak)');
is('Rank 3: 40 % stronger. Next rank 4 at level 62: 60 % stronger. 10 Rage · 3s cooldown.', 'Grad 3: 40 % stronger. Nästa grad 4 på nivå 62: 60 % stronger. 10 raseri · 3 s nedkylning.');
is('Crimson Plumed Helm ×1 · warrior · headgear · Starter gear · cannot be sold', 'Crimson Plumed Helm ×1 · krigare · huvudbonad · Startutrustning · kan inte säljas');
is('1 point available', '1 poäng tillgänglig');
is('Friends (3/50)', 'Vänner (3/50)');
// nothing changes twice
for (const s of ['Rage 12 / 100', 'Bjud in till grupp', 'Du och Fog är nu vänner.']) { assert.equal(t(t(s)), t(s), s); checks++; }
console.log(`${checks} Locale.translate checks passed`);
