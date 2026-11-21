// Run the shipped profession controls against a minimal DOM, independently of browsers and the public game.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const mutations = {
  rarity: ['&& gearRarities.indexOf(gear.rarity) >= gearRarities.indexOf(tier.rarity)', '&& true', 'rare gear cannot receive an epic enchant'],
  expertLevel: ['&& (item.requiredLevel || 1) >= (tier.minGearLevel || 1)', '&& true', 'expert recipes exclude gear below the required level'],
  replacing: ['expected:target.gear.enchant ?? null', 'expected:null', 'apply names the old enchant'],
  salvage: ['copies().filter(row => !row.worn)', 'copies()', 'worn pieces cannot be salvaged'],
  cost: ['canCraft &&= have >= amount', 'canCraft = true', 'missing materials disable crafting'],
  training: ["skill < cap ? tr('Can raise Enchanting", "skill <= cap ? tr('Can raise Enchanting", 'gear at its training cap explains why skill cannot rise'],
  trainer: ['An Enchanting Master can teach you. In Alderhaven, find one near the apothecary.', 'Learn in your bags.', 'untrained characters are sent to a trainer'],
  skill: ['skill, maxSkill) : tr(', 'skill, 100) : tr(', 'the pane shows the authoritative skill cap'],
  tooltip: ['rarity(tier.rarity), recipe.cooldown', 'rarity(tier.rarity), 0', 'copy tooltip shows the effect and cooldown'],
};
if (process.argv.includes('--mutations')) {
  for (const [mode, [, , error]] of Object.entries(mutations)) {
    const result = spawnSync(process.execPath, [__filename], { env: { ...process.env, MUTATE: mode }, encoding:'utf8' });
    assert(result.status === 1 && result.stderr.includes('AssertionError') && result.stderr.includes(error), result.stderr || result.stdout);
    console.log('Caught ' + mode + ' mutation');
  }
  process.exit(0);
}

class Element {
  constructor(tag) {
    this.tagName = tag; this.value = ''; this.hidden = false; this.children = [];
    this.dataset = {}; this.events = {}; this.attributes = {};
    this.classList = { add() {}, remove() {} };
  }
  set textContent(text) { this.text = text; }
  get textContent() { return (this.text || '') + this.children.map(child => child.textContent).join(' '); }
  append(...children) { for (const child of children) { child.parentElement = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(event, listener) { this.events[event] = listener; }
  querySelectorAll(tag) { return this.children.flatMap(child => [ ...(child.tagName === tag ? [child] : []), ...child.querySelectorAll(tag)]); }
  querySelector(selector) { return this.querySelectorAll(selector.split(' ').at(-1))[0]; }
  get options() { return this.children; }
  click() { if (!this.disabled) this.events.click?.(); }
  choose(value) { assert(this.options.some(option => option.value === value), value); this.value = value; this.events.change(); }
  focus() {}
}
const read = file => fs.readFileSync(path.join(root, file), 'utf8');
const readJson = file => JSON.parse(read(file));
const plain = value => JSON.parse(JSON.stringify(value));
const defs = readJson('world/items.txt');
const items = new Map(defs.map(row => [row.id, row]));
const panel = new Element('section');
const toggle = new Element('button');
panel.hidden = true;
new Element('div').append(panel, toggle);
const calls = [];
const names = {rare:'Rare',epic:'Epic',legendary:'Legendary',uncommon:'Uncommon'};
const context = {
  document: {createElement: tag => new Element(tag), getElementById: id => id === 'enchanting-panel' ? panel : toggle},
  Inventory: {definition: id => items.get(id), rarityName: item => names[item.rarity], hideTooltip() {}},
  Online: {send: request => { calls.push(plain(request)); return true; }},
  addEventListener() {},
  setTimeout() { return 1; }, clearTimeout() {},
};
context.window = context;
let source = read('client/enchanting.js');
if (process.env.MUTATE) {
  const [old, replacement] = mutations[process.env.MUTATE];
  assert(source.includes(old)); source = source.replace(old, replacement);
}
vm.runInNewContext(read('client/enchanting-data.js') + '\n' + source, context);
const EN = context.Enchanting;
const gear = (kind, rarity, id, enchant) => ({id, item:defs.find(i => i.rarity === rarity && i.kind === kind && !i.starter).id, rarity, enchant});
const epic = gear('weapon','epic',101,'double_tap');
const rare = gear('weapon','rare',102);
const worn = gear('weapon','epic',103);
const invalid = gear('necklace','epic',104);
const copies = [{gear:epic,worn:false,skillCap:30},{gear:rare,worn:false,skillCap:30},{gear:worn,worn:true},{gear:invalid,worn:false}];
const inventory = [{item:'enchant_scroll_shieldbreaker',quantity:1},{item:'enchant_recipe_double_tap',quantity:1}];
const answer = (patch = {}) => EN.onPacket({ok:true, text:'', skill:0, maxSkill:600, craftSkillCaps:[30,90,210,330,450,570,600], recipes:[], inventory, copies, ...patch});
const button = label => panel.querySelectorAll('button').find(node => node.textContent === label);
const select = label => panel.querySelectorAll('select').find(node => node.dataset.enchantingField === label);
const emit = request => assert.deepEqual(calls.at(-1), {type:'enchanting',request});

EN.open(inventory[0].item);
emit({op:'open'});
answer();
assert.equal(toggle.attributes['aria-expanded'],'true');
assert.match(panel.textContent, /Enchanting Master.*Alderhaven.*apothecary/, 'untrained characters are sent to a trainer');
assert(!button('Learn Enchanting'), 'training has no bag button');
assert.match(panel.textContent, /Weapon · Epic or higher · 10 s cooldown/, 'copy tooltip shows the effect and cooldown');
assert.match(panel.textContent, /Cost · One crafted scroll/);
assert(!select('Equipment copy').options.some(o => o.value === '102'), 'rare gear cannot receive an epic enchant');
assert(!select('Equipment copy').options.some(o => o.value === '104'), 'the wrong slot is excluded');
select('Equipment copy').choose('101');
assert.match(panel.textContent, /Replaces Double Tap on this copy/);
button('Apply enchantment').click();
assert.deepEqual(calls.at(-1).request, {op:'apply', enchant:'shieldbreaker', copy:101, expected:'double_tap'}, 'apply names the old enchant and the exact copy');
answer({text:'Enchantment applied.'});
assert.match(panel.textContent, /Enchantment applied\./);
answer({skill:1,trainingGearLevel:1});
assert.match(panel.textContent, /Enchanting skill 1 \/ 600/, 'the pane shows the authoritative skill cap');
button('Study').click();
select('Enchantment').choose('double_tap');
button('Study recipe').click();
emit({op:'study',enchant:'double_tap'});
answer({skill:1,recipes:['double_tap']});

button('Craft').click();
select('Enchantment').choose('double_tap');
assert.match(panel.textContent,/Enchanting Dust · 0 of 4 in bags/);
assert.equal(button('Craft one scroll').disabled,true,'missing materials disable crafting');
answer({skill:1,recipes:['double_tap'],inventory:[{item:'enchant_dust',quantity:4},{item:'enchant_essence',quantity:2}]});
button('Craft one scroll').click();
emit({op:'craft',enchant:'double_tap'});
answer({skill:2,skillUp:true,text:'Enchant scroll crafted.',recipes:['double_tap']});
assert.match(panel.textContent, /Enchanting skill increased to 2/);

button('Disenchant').click();
assert(!select('Equipment copy').options.some(o => o.value === '103'),'worn pieces cannot be salvaged');
select('Equipment copy').choose('101');
assert.match(panel.textContent,/Destroys this copy. You receive 2 × Enchanting Shard\./);
answer({skill:30,trainingGearLevel:6,recipes:['double_tap']});
assert.match(panel.textContent,/This action is below your current Enchanting training band/, 'gear at its training cap explains why skill cannot rise');
answer({skill:300,trainingGearLevel:51,recipes:['double_tap']});
assert.match(panel.textContent,/Use level 51 or higher gear for your next skill point/);
const requests = calls.length;
button('Disenchant this copy').click();
assert.equal(calls.length, requests,'a destructive action requires explicit confirmation');
button('Confirm disenchant').click();
emit({op:'disenchant',copy:101,expected:'double_tap'});
answer();
const tooltip = new Element('div');
assert(EN.tooltip(tooltip, items.get(epic.item), epic));
assert(/strike again/.test(tooltip.textContent) && /3 s cooldown/.test(tooltip.textContent),'copy tooltip shows the effect and cooldown');
assert(!EN.tooltip(new Element('div'), items.get(epic.item), { ...epic, enchant:null }));
EN.close();
const expert = {...rare, id:105, item:'warrior_weapon_sword_l55_blue'};
EN.open('enchant_scroll_prism_echo');
answer({skill:300, trainingGearLevel:51, inventory:[{item:'enchant_scroll_prism_echo',quantity:1}],
  copies:[...copies, {gear:expert,worn:false,skillCap:330}]});
assert.match(panel.textContent, /Requires equipment level 51 or higher/);
assert(!select('Equipment copy').options.some(o => o.value === '101'), 'expert recipes exclude gear below the required level');
assert(select('Equipment copy').options.some(o => o.value === '105'), 'expert recipe accepts level-55 rare gear');
answer({skill:570, trainingGearLevel:96});
assert.match(panel.textContent,/Craft Evergreen Sigil to reach skill 600/);
EN.close();
assert(panel.hidden);
console.log('Enchanting controls, selection, costs, requests, and copy tooltips pass');
