// Production controls and preview in a small DOM fixture; no browser or live service.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = path.resolve(__dirname, '..');
if (process.argv.includes('--mutations')) {
  for (const [mode, reason] of Object.entries({ empty: 'empty slot stays bare', fee: 'free revert contributes no fee', class: 'foreign class excluded', hide: 'only three hide options', marker: 'marker preserves real icon', payload: 'one atomic multi-slot request', trade: 'trade excludes actual worn armor and offers loose cosmetic item', trade_refresh: 'trade refresh follows real upgrades behind the same cosmetic look' })) {
    const r = require('node:child_process').spawnSync(process.execPath, [__filename], { env: { ...process.env, MUTATE: mode }, encoding: 'utf8' });
    assert(r.status === 1 && r.stderr.includes('AssertionError') && r.stderr.includes(reason), `${mode}: ${r.stdout}${r.stderr}`);
    console.log(`Caught ${mode}: ${reason}`);
  }
  process.exit(0);
}
let count = 0;
const check = (v, message) => { assert(v, message); count++; };
const plain = x => JSON.parse(JSON.stringify(x));
class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.listeners = {}; this.attributes = {}; this.style = { setProperty() {} }; this.hidden = false; this.value = ''; this._text = ''; this.isConnected = true; this.classList = { add() {}, remove() {}, toggle() {} }; }
  append(...nodes) { for (const n of nodes) { n.parentElement = this; this.children.push(n); } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  set textContent(t) { this._text = t; } get textContent() { return this._text + this.children.map(n => n.textContent).join(''); }
  setAttribute(k, v) { this.attributes[k] = v; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(k, fn) { (this.listeners[k] ||= []).push(fn); }
  fire(k) { for (const fn of this.listeners[k] || []) fn({ target: this }); }
  matches(selector) {
    if (selector.startsWith('#')) return this.id === selector.slice(1);
    if (selector.startsWith('.')) return this.className?.split(' ').includes(selector.slice(1));
    const m = selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);
    if (m) { const k = m[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase()); return m[2] ? this.dataset[k] === m[2] : this.dataset[k] !== undefined; }
    return this.tagName === selector;
  }
  querySelectorAll(s) { return this.children.flatMap(n => [...(n.matches(s) ? [n] : []), ...n.querySelectorAll(s)]); }
  querySelector(s) { return this.querySelectorAll(s)[0] || null; }
  closest(s) { return this.matches(s) ? this : this.parentElement?.closest(s); }
  contains(n) { return n === this || this.children.some(c => c.contains(n)); }
  getBoundingClientRect() { return { left: 20, right: 80, top: 100, bottom: 160, width: 60, height: 60 }; }
  get options() { return this.children.filter(n => n.tagName === 'option'); }
  get childElementCount() { return this.children.length; }
  click() { this.fire('click'); }
  getContext() { return { clearRect() {}, save() {}, restore() {}, translate() {} }; }
}
const catalog = JSON.parse(fs.readFileSync(path.join(root, 'world/items.txt')));
const definitions = new Map(catalog.map(i => [i.id, i]));
const sent = [], previews = [];
const ctx = { WORLD_ITEMS: catalog, document: { createElement: tag => new Element(tag) },
  Inventory: { definition: id => definitions.get(id) }, Locale: { translate: s => s },
  Online: { send: p => { sent.push(plain(p)); return true; } }, Money: { html: n => `<money>${n}</money>` },
  Field: { loadSprite: look => { previews.push(plain(look)); return Promise.resolve({ draw() {} }); } },
  requestAnimationFrame: () => 1, cancelAnimationFrame() {} };
ctx.window = ctx;
let source = fs.readFileSync(path.join(root, 'client/transmog.js'), 'utf8');
const mutations = {
  empty: ['if (!worn || !id', 'if (!id'], fee: [".filter(id => id !== 'real')", '.filter(() => true)'],
  class: ['(!i.class || i.class === look.class)', 'true'], hide: ["['headgear', 'shoulders', 'cloak']", "['chest', 'hands', 'headgear', 'shoulders', 'gloves', 'pants', 'cloak']"],
  marker: ['glyph.dataset.transmog = id;', "glyph.innerHTML = 'changed icon'; glyph.dataset.transmog = id;"],
  payload: ["changes: changes(next.transmogs || {}, selected)", 'changes: {}'],
};
if (mutations[process.env.MUTATE]) { const [a, b] = mutations[process.env.MUTATE]; assert(source.includes(a)); source = source.replace(a, b); }
vm.runInNewContext(source, ctx);
const t = ctx.Transmog;
const slots = ['chest', 'hands', 'headgear', 'shoulders', 'gloves', 'pants', 'cloak'];
const kind = s => ({ chest: 'armor', hands: 'weapon' })[s] || s;
const field = (s, cls) => s === 'chest' ? cls + 'Armor' : s === 'hands' ? cls + 'Weapon' : s === 'headgear' ? 'head' : s;
const pick = (s, cls, level = 50) => catalog.find(i => i.kind === kind(s) && (!i.class || i.class === cls) && i.variant && i.requiredLevel >= level && i.rarity === 'uncommon');
for (const cls of ['warrior', 'mage', 'priest', 'hunter', 'assassin']) {
  const look = { class: cls }, equipment = {}, selected = {};
  for (const s of slots) { look[field(s, cls)] = 'none'; selected[s] = pick(s, cls).id; }
  const bare = t.preview(look, equipment, selected);
  for (const s of slots) check(bare[field(s, cls)] === 'none', `empty slot stays bare: ${cls} ${s}`);
  for (const s of slots) { equipment[s] = 'worn'; look[field(s, cls)] = 'worn'; }
  const dressed = t.preview(look, equipment, selected);
  for (const s of slots) check(dressed[field(s, cls)] === pick(s, cls).variant, `all seven previews follow selected art: ${cls} ${s}`);
  check(look[cls + 'Armor'] === 'worn', 'preview never mutates real equipment look');
}
check(!t.eligible(pick('chest', 'mage'), 'chest', { class: 'warrior' }, false), 'foreign class excluded');
const gm = catalog.find(i => i.kind === 'armor' && i.rarity === 'gm');
check(!t.eligible(gm, 'chest', { class: 'warrior' }, false) && t.eligible(gm, 'chest', { class: 'warrior' }, true), 'GM filter follows authoritative flag');
const crown = pick('headgear', 'warrior'), chest = pick('chest', 'warrior'), cloak = pick('cloak', 'warrior');
check(t.fee({ chest: 'real', headgear: 'hide', cloak: cloak.id }, 500) === 1000, 'free revert contributes no fee');
check(Object.keys(t.changes({ chest: chest.id }, { chest: chest.id })).length === 0, 'unchanged selections are free noops');
check(plain(t.changes({ chest: chest.id }, {})).chest === 'real', 'revert uses explicit real sentinel');
const glyph = new Element('button'); glyph.innerHTML = '<svg>real item</svg>'; t.mark(glyph, chest.id);
check(glyph.innerHTML === '<svg>real item</svg>' && glyph.dataset.transmog === chest.id, 'marker preserves real icon');
check(t.description('hide') === 'Appearance: Hidden' && t.description(chest.id) === `Transmogrified to: ${chest.name}`, 'tooltips describe chosen appearance');
t.mark(glyph, null); check(!glyph.dataset.transmog && !glyph.dataset.appearance, 'free revert removes marker');
const npc = { id: 'city_transmog' }, packet = { wardrobe: [chest.id, crown.id, cloak.id, gm.id, pick('chest', 'mage').id],
  transmogs: {}, look: { class: 'warrior', warriorArmor: 'crimson', warriorWeapon: 'sword', head: 'none', cloak: 'none' },
  equipment: {}, transmogPrice: 500, gold: 1000, gm: false };
const container = new Element('div'); t.render(npc, packet, container);
check(container.querySelectorAll('select').length === 7, 'master exposes exactly seven slots');
check(container.querySelectorAll('option').filter(o => o.value === 'hide').length === 3, 'only three hide options');
check(container.querySelectorAll('option').every(o => o.value !== gm.id && o.value !== pick('chest', 'mage').id), 'unlocked list still filters class and GM');
check(container.querySelector('button').disabled, 'unchanged draft cannot be applied');
t.error(); check(container.querySelector('button').disabled, 'unrelated errors do not enable an unchanged draft');
function choose(slot, value) { const s = container.querySelector(`[data-slot="${slot}"]`); s.value = value; s.fire('change'); }
choose('chest', chest.id); choose('headgear', 'hide');
check(container.querySelector('.transmog-total').dataset.cost === '1000', 'combined fee covers two changed slots');
check(previews.at(-1).warriorArmor === chest.variant && previews.at(-1).head === 'none', 'live preview updates from controls');
container.querySelector('button').fire('click'); container.querySelector('button').fire('click');
check(sent.length === 1 && sent[0].changes.chest === chest.id && sent[0].changes.headgear === 'hide' && Object.keys(sent[0].changes).length === 2, 'one atomic multi-slot request');
check(container.querySelector('button').disabled, 'double apply is suppressed while awaiting reply');
t.error(); check(!container.querySelector('button').disabled, 'refusal lets owner retry');
t.render(npc, { ...packet, transmogs: { chest: chest.id, headgear: 'hide' }, gold: 0 }, container);
check(container.querySelector('button').disabled && container.querySelector('.transmog-total').dataset.cost === '0', 'accepted response reconciles draft and fee');
choose('chest', 'real'); choose('headgear', 'real');
check(!container.querySelector('button').disabled && container.querySelector('.transmog-total').dataset.cost === '0', 'free revert works with no money');
choose('cloak', cloak.id); check(container.querySelector('button').disabled, 'unaffordable batch cannot be sent');
t.close(); check(true, 'closing releases preview state');
// Exercise real item resolution, quantities, icons and tooltips in the production inventory module.
const body = new Element('body');
ctx.document.body = body; ctx.document.getElementById = id => body.querySelector('#' + id);
ctx.Online.connected = true; ctx.Online.currentToken = 'test'; ctx.Online.saveBagLayout = () => {};
ctx.Field.hero = { level: 99 }; ctx.Event = class {}; ctx.dispatchEvent = () => {};
ctx.Money.text = n => String(n); ctx.innerWidth = 960; ctx.innerHeight = 600;
vm.runInNewContext(fs.readFileSync(path.join(root, 'client/inventory.js'), 'utf8'), ctx);
const real = catalog.find(i => i.kind === 'armor' && i.class === 'warrior' && i.variant === 'crimson');
const realLook = { class: 'warrior', warriorArmor: 'crimson', warriorWeapon: 'none' };
const stacks = [{ item: real.id, quantity: 2 }, { item: chest.id, quantity: 1 }];
ctx.Inventory.update(stacks, realLook, {}, [], [], {}, { chest: chest.id });
check(ctx.Inventory.bagQuantity(real.id) === 1 && ctx.Inventory.bagQuantity(chest.id) === 1, 'real worn quantities ignore cosmetic item');
const doll = new Element('div'); body.append(doll); ctx.Inventory.renderEquipped(doll);
const card = doll.querySelector('[data-slot="chest"]'), icon = card.querySelector('.gear-icon');
check(card.dataset.value === real.variant && card.querySelector('b').textContent === real.name, 'paper doll selects and names actual item');
check(icon.dataset.transmog === chest.id && icon.innerHTML === ctx.Inventory.icon(real, 'armor'), 'paper doll keeps real icon and adds corner marker');
ctx.Inventory.showTooltip(icon, real, 'chest');
check(body.querySelector('#item-tooltip').textContent.includes(real.name) && body.querySelector('#item-tooltip').textContent.includes(`Transmogrified to: ${chest.name}`), 'actual item tooltip includes appearance line');
const bags = new Element('div'); body.append(bags); ctx.Inventory.render(bags);
const looseReal = bags.querySelector(`[data-item="${real.id}"]`);
check(looseReal.querySelector('.item-tile').dataset.transmog === chest.id, 'bag copy of worn item gets slot appearance marker');
ctx.Inventory.update(stacks, realLook, {}, [], [], {}, {}); ctx.Inventory.renderEquipped(doll);
check(!icon.dataset.transmog, 'revert clears paper-doll marker on next snapshot');
// Trading also resolves chest/weapon ownership from the actual gear, even while cosmetics render.
ctx.document.getElementById = id => { let n = body.querySelector('#' + id); if (!n) { n = new Element('div'); n.id = id; n.hidden = true; body.append(n); } return n; };
ctx.Money.set = (n, value) => { n.textContent = String(value); }; ctx.Money.preview = () => {};
ctx.Field.setPaused = () => {};
let trade = fs.readFileSync(path.join(root, 'client/trade.js'), 'utf8');
if (process.env.MUTATE === 'trade') trade = trade.replace('const look = character.equippedLook || character.look;', 'const look = character.look;');
if (process.env.MUTATE === 'trade_refresh') trade = trade.replace('c?.equippedLook || c?.look', 'c?.look');
vm.runInNewContext(trade, ctx);
const worn = pick('chest', 'warrior', 20);
const character = { look: { class: 'warrior', warriorArmor: chest.variant }, equippedLook: { class: 'warrior', warriorArmor: worn.variant },
  inventory: [{ item: worn.id, quantity: 1 }, { item: chest.id, quantity: 1 }], equipment: {}, gold: 0,
  gearInstances: [worn, chest].map((i, n) => ({ item: i.id, id: n + 1, tradeUntil: Date.now() / 1000 + 9999, tradeWith: ['partner'] })) };
ctx.Trade.onSnapshot(character); ctx.Trade.onPacket({ state: 'open', partner: { id: 'partner', name: 'Other' }, mine: { items: [], gold: 0 }, theirs: { items: [], gold: 0 } });
const options = ctx.document.getElementById('trade-item').options;
check(!options.some(o => o.value === worn.id) && options.some(o => o.value === chest.id && !o.disabled), 'trade excludes actual worn armor and offers loose cosmetic item');
ctx.Trade.onSnapshot({ ...character, equippedLook: character.look });
const upgradedOptions = ctx.document.getElementById('trade-item').options;
check(upgradedOptions.some(o => o.value === worn.id && !o.disabled) && !upgradedOptions.some(o => o.value === chest.id), 'trade refresh follows real upgrades behind the same cosmetic look');
console.log(`Transmogrify: ${count} production preview/control checks passed.`);
