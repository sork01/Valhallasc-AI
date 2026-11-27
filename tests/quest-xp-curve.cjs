// Exercise the real quest journal and conversation renderer with a small DOM fixture.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = name => fs.readFileSync(path.join(__dirname, '..', 'client', name), 'utf8');

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.attributes = {};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener() {}
  focus() {}
  scrollIntoView() {}
  getClientRects() { return []; }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  querySelectorAll(selector) {
    const attribute = selector.match(/^\[([\w-]+)="([^"]+)"\]$/);
    const matches = node => attribute
      ? node.attributes[attribute[1]] === attribute[2]
      : selector.startsWith('.') && (node.className || '').split(' ').includes(selector.slice(1));
    return this.children.flatMap(node => [
      ...(matches(node) ? [node] : []),
      ...node.querySelectorAll(selector),
    ]);
  }
}

const quest = {
  id: 'patrol', title: 'Patrol', level: 20, npc: 'captain', rewardXp: 100, rewardGold: 10,
  objectives: [{ kind: 'kill', target: 'green', label: 'Green Slime', count: 1 }],
};
const elements = new Map();
const get = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
for (const id of ['quest-journal', 'pause', 'equipment']) get(id).hidden = true;
const shell = new Element();
shell.className = 'quest-panel';
get('quest-journal').append(shell);
const npc = get('npc-quests');
const context = vm.createContext({
  document: { getElementById: get, createElement: () => new Element() },
  WORLD_MAP: { name: 'Meadow', quests: [quest], npcs: [{ id: 'captain', name: 'Captain', x: 0, y: 0 }] },
  Field: { zone: 0, hero: {}, setPaused() {} },
  Online: { connected: true },
  City: { refresh() { if (npc.children.length) openNpc(); } },
  Locale: { translate: text => text },
  Money: { html: gold => String(gold) },
});
context.window = context;
vm.runInContext(read('quest-guidance.js'), context);

let questsScript = read('quests.js');
const mutations = {
  journal: ['history ? quest.rewardXp : rewardExperience(quest)', 'quest.rewardXp'],
  npc: ["element('h5', 'Rewards'), rewardLine(quest)", "element('h5', 'Rewards'), rewardLine(quest, quest.rewardXp)"],
  refresh: ["if ($('npc-dialogue')?.dataset.service === 'quest') window.City?.refresh?.();", ''],
};
if (process.env.MUTATE) {
  const [original, replacement] = mutations[process.env.MUTATE];
  assert.ok(questsScript.includes(original), 'mutation target is present');
  questsScript = questsScript.replace(original, replacement);
}
vm.runInContext(questsScript, context);

const { Quests, Field } = context;
function openNpc() {
  get('npc-dialogue').dataset.service = 'quest';
  Quests.detail(quest, npc, () => {});
}
function reward(node) { return node.querySelector('.quest-reward').innerHTML; }
function check(xp) {
  const display = `<span>${xp} experience</span> · 10`;
  assert.equal(reward(get('quest-page')), display, 'journal XP');
  assert.equal(reward(npc), display, 'conversation XP');
}

Quests.setLevel(18);
Quests.update([{ id: quest.id, counts: [1], claimed: false }]);
Quests.show();
openNpc();
check(100); // Older server with no curve advertised.

Quests.setXpCurve({ minGap: -7, rates: [30, 40, 50, 60, 70, 80, 90, 100, 103, 106, 109, 112, 115] });
for (const [level, xp] of [[14, 115], [19, 103], [20, 100], [21, 90], [25, 50], [27, 30], [30, 30]]) {
  Quests.setLevel(level);
  check(xp);
}
Field.hero.maxLevel = true;
Quests.setLevel(99);
check(0);

Field.hero.maxLevel = false;
Quests.setLevel(30);
for (const [base, xp] of [[25, 8], [1, 1], [0, 0]]) {
  Quests.detail({ ...quest, rewardXp: base }, npc, () => {});
  assert.equal(reward(npc), `<span>${xp} experience</span> · 10`, `rounding from ${base} XP`);
}
console.log('Quest XP previews pass for the journal and NPC conversation.');
