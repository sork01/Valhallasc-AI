// Real inventory + tutorial modules: deterministic complexity checks and tutorial behavior, no browser.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const { performance } = require('node:perf_hooks');
const root = path.resolve(__dirname, '..'), read = name => fs.readFileSync(path.join(root, name), 'utf8');
if (process.argv.includes('--mutations')) {
  const cases = {
    definition: 'warm definition lookups never rescan catalog entries',
    quantity: 'quantity lookups never rescan inventory stacks',
    append: 'catalog extension invalidates the index',
    replacement: 'same-length catalog replacement invalidates the index',
    stale: 'same-array quantity changes rebuild on authoritative update',
    order: 'owned IDs are distinct/positive and preserve catalog priority rather than bag order',
    catalog: '20 incomplete-tutorial renders visit no unowned catalog entries',
  };
  for (const [mode, message] of Object.entries(cases)) {
    const result = require('node:child_process').spawnSync(process.execPath, [__filename], { env: { ...process.env, MUTATE: mode }, encoding: 'utf8' });
    assert(result.status === 1 && result.stderr.includes('AssertionError') && result.stderr.includes(message), `${mode}: ${result.stdout}${result.stderr}`);
    console.log(`Caught ${mode}: ${message}`);
  }
  process.exit(0);
}
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
const plain = value => JSON.parse(JSON.stringify(value));
function fixture(catalog) {
  const nodes = new Map(), frames = [], sent = [], events = {};
  class Element {
    constructor() { this.hidden = true; this.children = []; this.dataset = {}; this.style = { setProperty() {} }; this.classList = { add() {}, remove() {}, contains: () => false }; this.clientWidth = 960; this.clientHeight = 600; this.attrs = {}; }
    set id(id) { this._id = id; nodes.set(id, this); } get id() { return this._id; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener() {} setAttribute(k, v) { this.attrs[k] = v; } getAttribute(k) { return this.attrs[k]; }
    querySelector() { return null; } querySelectorAll() { return []; } contains() { return false; }
    getBoundingClientRect() { const stage = this.id === 'stage'; return { left: stage ? 0 : 100, top: stage ? 0 : 100, width: stage ? 960 : 200, height: stage ? 600 : 60, right: stage ? 960 : 300, bottom: stage ? 600 : 160 }; }
  }
  for (const id of ['stage', 'scene-game', 'inventory-open', 'inventory-list', 'equipment', 'character-tab-stats', 'character-attributes', 'skills-open', 'skill-library', 'quickuse', 'skillbar', 'wm-open', 'minimap', 'ghost-msg', 'npc-dialogue', 'npc-offers', 'npc-inventory', 'quest-tracker', 'mail-open']) {
    const n = new Element(); n.id = id;
    n.hidden = ['equipment', 'npc-dialogue'].includes(id);
  }
  nodes.get('character-tab-stats').setAttribute('aria-selected', 'true');
  const hero = { id: 'hero', level: 1, look: { class: 'warrior', warriorArmor: 'none', warriorWeapon: 'none' }, hp: 100, x: 10, y: 10, tutorialDone: [], tutorialDisabled: false, statPoints: 0, quests: [], kills: 0 };
  const ctx = { WORLD_ITEMS: catalog, WORLD_SKILLS: [], Field: { hero, slimes: [], drops: [] }, innerWidth: 960, innerHeight: 600,
    Online: { connected: true, currentToken: 'hero', send: p => sent.push(p), saveBagLayout() {} },
    document: { getElementById: id => nodes.get(id) || null, createElement: () => new Element(), querySelector: () => null, querySelectorAll: () => [] },
    requestAnimationFrame: fn => { frames.push(fn); return frames.length; }, addEventListener: (type, fn) => { (events[type] ||= []).push(fn); }, dispatchEvent: () => {}, Event: class { constructor(type) { this.type = type; } },
    getComputedStyle: () => ({ display: 'block', visibility: 'visible', opacity: '1' }), matchMedia: () => ({ matches: false }),
  };
  ctx.window = ctx; vm.createContext(ctx);
  const source = name => process.argv.includes('--baseline')
    ? require('node:child_process').execFileSync('git', ['show', '437d61b5:' + name], { cwd: root, encoding: 'utf8' }) : read(name);
  let inventory = source('client/inventory.js'), tutorial = source('client/tutorial.js');
  if (process.env.MUTATE === 'definition') inventory = inventory.replace('const definition = id => { indexDefinitions(); return defIndex.get(id); };', 'const definition = id => WORLD_ITEMS.find(i => i.id === id);');
  if (process.env.MUTATE === 'quantity') inventory = inventory.replace('const quantity = id => quantities.get(id) || 0;', 'const quantity = id => stacks.find(s => s.item === id)?.quantity || 0;');
  if (process.env.MUTATE === 'append') inventory = inventory.replace('source === defSource && source.length === defLength', 'source === defSource');
  if (process.env.MUTATE === 'replacement') inventory = inventory.replace('source === defSource && source.length === defLength', 'source.length === defLength');
  if (process.env.MUTATE === 'stale') inventory = inventory.replace('      quantities = new Map();', '      // fault: keep stale counts');
  if (process.env.MUTATE === 'order') inventory = inventory.replace('.sort((a, b) => (defOrder.get(a) ?? Infinity) - (defOrder.get(b) ?? Infinity))', '');
  if (process.env.MUTATE === 'catalog') tutorial = tutorial.replaceAll('inv.ownedItemIds()', 'window.WORLD_ITEMS.map(item => item.id)');
  vm.runInContext(inventory, ctx); vm.runInContext(tutorial, ctx);
  return { ctx, nodes, hero, sent, frames, inventory: ctx.Inventory, tutorial: ctx.Tutorial,
    update(stacks, look = hero.look, slots = {}) { ctx.Inventory.update(stacks, look, slots); },
    snapshot(patch = {}) { Object.assign(hero, patch); ctx.Tutorial.onSnapshot(hero); frames.length = 0; ctx.Tutorial.render(); return plain(ctx.Tutorial.state()); },
  };
}
if (process.argv.includes('--baseline')) {
  const catalog = JSON.parse(read('world/items.txt')), f = fixture(catalog);
  const materials = catalog.filter(i => i.kind === 'material').slice(0, 20).map(i => ({ item: i.id, quantity: 1 }));
  f.update(materials); f.snapshot({ tutorialDone: ['first_quest', 'levelup_stats', 'new_skill', 'merchant'] });
  const start = performance.now(); for (let i = 0; i < 20; i++) f.tutorial.render();
  const renderMs = (performance.now() - start) / 20;
  const lookupStart = performance.now(); for (const item of catalog) f.inventory.bagQuantity(item.id);
  const report = { source: '437d61b5', catalogItems: catalog.length, ownedStacks: materials.length, renderCalls: 20, averageRenderMs: renderMs, fullCatalogBagLookupMs: performance.now() - lookupStart, tutorial: plain(f.tutorial.state()) };
  fs.mkdirSync(path.join(root, 'test-results/tutorial-inventory-performance'), { recursive: true });
  fs.writeFileSync(path.join(root, 'test-results/tutorial-inventory-performance/baseline.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report)); process.exit(0);
}
const items = [
  { id: 'gear-first', kind: 'armor', class: 'warrior', variant: 'first', requiredLevel: 1 },
  { id: 'gear-second', kind: 'weapon', class: 'warrior', variant: 'second', requiredLevel: 1 },
  { id: 'starter', kind: 'armor', class: 'warrior', variant: 'starter', starter: true },
  { id: 'wrong-class', kind: 'armor', class: 'mage' },
  { id: 'too-high', kind: 'accessory', requiredLevel: 10 },
  { id: 'food', kind: 'food' }, { id: 'potion', kind: 'potion' },
  { id: 'fish', kind: 'fish' }, { id: 'material', kind: 'material' },
  { id: 'zero', kind: 'armor' }, { id: 'negative', kind: 'food' },
];
{
  const f = fixture(items.map(i => ({ ...i }))), inv = f.inventory;
  check(inv.definition('gear-first').variant === 'first' && inv.definition('missing') === undefined, 'definitions keep found/missing semantics');
  const sameLength = items.map(i => ({ ...i })); sameLength[0].name = 'Replacement'; f.ctx.WORLD_ITEMS = sameLength;
  check(inv.definition('gear-first').name === 'Replacement', 'same-length catalog replacement invalidates the index');
  sameLength.push({ id: 'appended', kind: 'food' });
  check(inv.definition('appended')?.kind === 'food', 'catalog extension invalidates the index');
  sameLength.pop(); check(inv.definition('appended') === undefined, 'catalog shrink removes old definitions');
  sameLength[0].requiredLevel = 7;
  check(inv.definition('gear-first').requiredLevel === 7, 'in-place property updates remain visible through indexed object references');
  f.ctx.WORLD_ITEMS = [{ id: 'duplicate', kind: 'food', name: 'First' }, { id: 'duplicate', kind: 'food', name: 'Second' }];
  check(inv.definition('duplicate').name === 'First', 'duplicate IDs retain old first-match behavior');
}
{
  const f = fixture(items), inv = f.inventory;
  const stacks = [{ item: 'gear-second', quantity: 2 }, { item: 'gear-first', quantity: 2 }, { item: 'food', quantity: 4 }, { item: 'zero', quantity: 0 }, { item: 'negative', quantity: -1 }, { item: 'unknown', quantity: 3 }];
  f.update(stacks, { class: 'warrior', warriorArmor: 'first', warriorWeapon: 'second' });
  check(inv.quantity('food') === 4 && inv.quantity('missing') === 0, 'quantity preserves found/missing semantics');
  check(inv.bagQuantity('gear-first') === 1 && inv.bagQuantity('gear-second') === 1, 'worn armor and weapon are excluded from bag counts');
  check(inv.bagQuantity('zero') === 0 && inv.bagQuantity('negative') === 0, 'bag quantity stays clamped to zero');
  check(plain(inv.ownedItemIds()).join(',') === 'gear-first,gear-second,food,unknown', 'owned IDs are distinct/positive and preserve catalog priority rather than bag order');
  stacks[2].quantity = 1; f.update(stacks);
  check(inv.quantity('food') === 1, 'same-array quantity changes rebuild on authoritative update');
  inv.updateBags([{ item: 'potion', quantity: 6 }]);
  check(inv.quantity('food') === 0 && inv.quantity('potion') === 6, 'bank and trade bag replies replace quantity indexes before snapshots');
  f.ctx.Online.currentToken = 'other'; f.update([]);
  check(inv.quantity('potion') === 0 && inv.ownedItemIds().length === 0, 'character switch/empty inventory clears stale counts');
  f.update([{ item: 'food', quantity: 2 }, { item: 'food', quantity: 3 }]);
  check(inv.quantity('food') === 2 && inv.ownedItemIds().length === 1, 'duplicate stacks preserve first-match semantics without duplicate owned IDs');
}
{
  const f = fixture(items), inv = f.inventory;
  // Only inventory primitives are exposed to the tutorial; the same filters and priority still apply.
  f.update([{ item: 'gear-second', quantity: 1 }, { item: 'gear-first', quantity: 1 }]);
  let state = f.snapshot({ tutorialDone: ['first_quest'] });
  check(state.active.id === 'equip_gear' && state.active.sub === 'equip_gear_bag', 'compatible owned gear still triggers equipment guidance');
  f.nodes.get('equipment').hidden = false; f.tutorial.render();
  check(f.tutorial.state().active.body.includes('Click this item'), 'opening equipment advances the same gear instruction');
  // Auto completion observes the selected catalog-first item, not a reordered bag's first stack.
  f.update([{ item: 'gear-second', quantity: 1 }]); f.tutorial.render();
  check(f.tutorial.state().done.includes('equip_gear'), 'catalog-first item priority is retained for auto-completion');
  f.nodes.get('equipment').hidden = true;
  f.update([{ item: 'starter', quantity: 1 }, { item: 'wrong-class', quantity: 1 }, { item: 'too-high', quantity: 1 }, { item: 'fish', quantity: 2 }, { item: 'material', quantity: 1 }, { item: 'zero', quantity: 0 }]);
  state = f.snapshot({ id: 'filtered', tutorialDone: ['first_quest'] });
  check(state.active === null, 'starter, wrong class, too-high, zero, materials and fish do not invent equipment/consumable tips');
  f.update([{ item: 'potion', quantity: 2 }, { item: 'food', quantity: 1 }]);
  state = f.snapshot({ id: 'consumable', tutorialDone: ['first_quest'] });
  check(state.active.id === 'consumables' && state.active.targetId === 'quickuse', 'owned food/potion still triggers quick-use guidance');
  state = f.snapshot({ id: 'stats', tutorialDone: ['first_quest'], statPoints: 1 });
  check(state.active.id === 'levelup_stats', 'stat points retain precedence over consumables');
  f.ctx.WORLD_SKILLS = [{ id: 'active', level: 2, class: 'warrior' }];
  state = f.snapshot({ id: 'skill', tutorialDone: ['first_quest', 'levelup_stats'], statPoints: 0, level: 2 });
  check(state.active.id === 'new_skill', 'unlocked skill guidance keeps its priority');
  state = f.snapshot({ id: 'more', tutorialDone: ['first_quest', 'levelup_stats', 'equip_gear', 'new_skill', 'consumables', 'merchant'], ghost: true });
  check(state.active.id === 'first_death', 'MORE spirit guidance remains available');
  f.tutorial.disable(); check(f.tutorial.state().disabled && f.tutorial.state().active === null, 'disable still hides and preserves tutorial state');
}
// Count actual array-entry reads instead of relying on machine-dependent timing.
const metered = array => {
  let reads = 0;
  return { array: new Proxy(array, { get(target, key, receiver) { if (/^\d+$/.test(String(key))) reads++; return Reflect.get(target, key, receiver); } }), reads: () => reads, reset: () => { reads = 0; } };
};
{
  const catalog = metered(Array.from({ length: 1600 }, (_, i) => ({ id: 'item-' + i, kind: 'food' })));
  const f = fixture(catalog.array); f.inventory.definition('item-1599'); catalog.reset();
  for (let i = 0; i < 1600; i++) f.inventory.definition('item-' + i);
  check(catalog.reads() === 0, 'warm definition lookups never rescan catalog entries');
  const stacks = metered(Array.from({ length: 80 }, (_, i) => ({ item: 'item-' + i, quantity: 1 })));
  f.update(stacks.array); stacks.reset();
  for (let i = 0; i < 1600; i++) f.inventory.quantity('item-' + (i % 80));
  check(stacks.reads() === 0, 'quantity lookups never rescan inventory stacks');
  f.update([{ item: 'item-1599', quantity: 1 }]);
  f.snapshot({ tutorialDone: ['first_quest', 'levelup_stats', 'new_skill', 'merchant'] }); catalog.reset();
  for (let i = 0; i < 20; i++) f.tutorial.render();
  check(catalog.reads() === 0, '20 incomplete-tutorial renders visit no unowned catalog entries');
}
// Bounded host benchmark on the real shipped catalog. Timings are evidence, not a brittle pass/fail threshold.
{
  const catalog = JSON.parse(read('world/items.txt')), f = fixture(catalog);
  const materials = catalog.filter(i => i.kind === 'material').slice(0, 20).map(i => ({ item: i.id, quantity: 1 }));
  f.update(materials); f.snapshot({ tutorialDone: ['first_quest', 'levelup_stats', 'new_skill', 'merchant'] });
  check(f.tutorial.state().active === null && !f.tutorial.state().disabled, 'benchmark reproduces incomplete tutorial with no active step');
  const start = performance.now(); for (let i = 0; i < 20; i++) f.tutorial.render(); const renderMs = (performance.now() - start) / 20;
  const lookupStart = performance.now(); for (const item of catalog) f.inventory.bagQuantity(item.id); const lookupMs = performance.now() - lookupStart;
  const report = { catalogItems: catalog.length, ownedStacks: materials.length, renderCalls: 20, averageRenderMs: renderMs, fullCatalogBagLookupMs: lookupMs, tutorial: plain(f.tutorial.state()) };
  fs.mkdirSync(path.join(root, 'test-results/tutorial-inventory-performance'), { recursive: true });
  fs.writeFileSync(path.join(root, 'test-results/tutorial-inventory-performance/benchmark.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(`Host VM benchmark: ${catalog.length} items, ${materials.length} owned; render ${renderMs.toFixed(3)} ms/call, full bag lookup ${lookupMs.toFixed(3)} ms.`);
}
console.log(`Tutorial/inventory: ${checks} behavior, cache invalidation and deterministic complexity checks passed.`);
