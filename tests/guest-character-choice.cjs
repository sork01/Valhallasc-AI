// Real login handlers, guest storage and join packets, without Chromium or a public guest.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = path.resolve(__dirname, '..'), read = p => fs.readFileSync(path.join(root, p), 'utf8');
const warning = 'Guest progress is tied to this browser. Clearing browser data or losing this browser can make your character and progress inaccessible. Use an account to keep access across devices. Continue as guest?';
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
class Element {
  constructor() { this.hidden = true; this.disabled = false; this.children = []; this.events = {}; this.dataset = {}; this.style = { setProperty() {} }; this.classList = { toggle() {}, remove() {}, add() {} }; this._text = ''; }
  set textContent(text) { this._text = text; this.children = []; }
  get textContent() { return this._text + this.children.map(n => n.textContent).join(''); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, fn) { (this.events[type] ||= []).push(fn); }
  setAttribute(name, value) { this[name] = value; }
  querySelector(selector) { return this.children.find(n => n.className?.split(' ').includes(selector.slice(1))) || this.children.map(n => n.querySelector(selector)).find(Boolean) || null; }
  querySelectorAll() { return []; }
  focus() { this.focused = true; }
  click() { if (!this.disabled) for (const fn of this.events.click || []) fn({ preventDefault() {} }); }
}
const guestSlots = [
  { token: 'guest-one', look: { name: 'First', class: 'warrior', gender: 'male' }, skillSlots: ['a', 'b'] },
  { token: 'guest-two', look: { name: 'Second', class: 'priest', gender: 'female' }, bagLayout: [0, 1] },
];
function fixture({ characters = [], current = null, cached = null, mode = 'guest', lang = 'en', account = null } = {}) {
  const nodes = new Map(), get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const store = new Map(), endpoint = 'ws://127.0.0.1/Valhalla/ws';
  const guestKey = 'valhallasc.characters.v1:' + endpoint, accountKey = 'valhallasc.account.v1:' + endpoint;
  store.set(guestKey, JSON.stringify({ current, characters }));
  if (account) store.set(accountKey, JSON.stringify(account));
  const save = { char: cached, draft: null, mode, lang }, confirmations = [], scenes = [], sockets = [];
  const ctx = {
    URL, location: { href: 'http://127.0.0.1/Valhalla/' }, navigator: { language: lang }, save,
    localStorage: { getItem: k => store.get(k) || null, setItem: (k, v) => store.set(k, String(v)) },
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    document: { getElementById: get, createElement: () => new Element(), addEventListener() {}, documentElement: {}, body: new Element(), createTreeWalker: () => ({ nextNode: () => null }) },
    Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 }, NodeFilter: { SHOW_TEXT: 4 }, MutationObserver: class { observe() {} },
    addEventListener() {}, setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    requestAnimationFrame: () => 1, cancelAnimationFrame() {},
    confirm: message => { confirmations.push(message); return ctx.acceptWarning; }, acceptWarning: true,
    persist: () => store.set('valhallasc.save.v1', JSON.stringify(save)),
    cfg: { name: 'NewHero', class: 'warrior', gender: 'male' },
    load: look => { ctx.cfg = { ...look }; }, equipmentKeys: c => [c.class + 'Armor', c.class + 'Weapon'], clang() {}, horn() {}, blip() {},
    fetch: async () => ({ status: 200, json: async () => ({ ok: true, account: { name: 'Account', kind: 'game' }, max: 5, characters: [] }) }),
  };
  ctx.window = ctx; ctx.$ = get;
  ctx.WebSocket = class {
    static OPEN = 1;
    constructor() { this.readyState = 0; this.packets = []; sockets.push(this); }
    send(text) { this.packets.push(JSON.parse(text)); }
    close() { this.readyState = 3; }
  };
  ctx.show = scene => { scenes.push(scene); if (scene === 'chars') ctx.Account.enterChars(); if (scene === 'game') ctx.Online.start({ look: { ...save.char } }); };
  vm.createContext(ctx);
  vm.runInContext(read('client/online.js'), ctx);
  let resumes = 0;
  const resume = ctx.Online.resume.bind(ctx.Online);
  ctx.Online.resume = async () => { resumes++; return resume(); };
  vm.runInContext(read('client/sv-data.js'), ctx); vm.runInContext(read('client/locale.js'), ctx);
  let accountSource = read('client/account.js'), game = read('client/game.js');
  if (process.env.MUTATE === 'warning') accountSource = accountSource.replace('!busy && window.confirm(', '!busy && (true || window.confirm(').replace('))) handlers.guest();', ')))) handlers.guest();');
  if (process.env.MUTATE === 'picker') accountSource = accountSource.replace("Online.mode === 'guest', account", "false, account");
  if (process.env.MUTATE === 'refresh') accountSource = accountSource.replace("if (Online.mode === 'account') Online.resume().then(data => { if (data?.ok)", 'Online.resume().then(data => { if (data?.ok)');
  if (process.env.MUTATE === 'auto') game = game.replace("show(Online.characters.length ? 'chars' : 'create')", "show(save.char ? 'game' : 'create')");
  vm.runInContext(accountSource, ctx);
  const start = game.indexOf('  function setMode(mode)'), end = game.indexOf('  // ---------- effects:', start);
  assert(start > 0 && end > start);
  vm.runInContext(game.slice(start, end), ctx);
  const goStart = game.indexOf("  $('go').addEventListener('click'");
  vm.runInContext(game.slice(goStart, game.indexOf('  // ---------- the field:', goStart)), ctx);
  return { ctx, get, store, confirmations, scenes, sockets, guestKey, accountKey, resumes: () => resumes, open() { const s = sockets.at(-1); s.readyState = 1; s.onopen(); return s.packets[0]; } };
}
(async () => {
  for (const cached of [null, { name: 'Obsolete', class: 'warrior' }]) {
    const f = fixture({ cached });
    f.get('login-guest').click();
    check(f.confirmations[0] === warning, 'guest risk is explained before any transition');
    check(f.scenes.at(-1) === 'create' && f.sockets.length === 0, 'no guest key means job/appearance selection even with cached look');
    f.ctx.cfg = { name: 'NewMage', class: 'mage', gender: 'female' }; f.get('name').value = 'NewMage'; f.get('go').click();
    const join = f.open();
    check(join.token === null && join.look.class === 'mage' && join.look.gender === 'female', 'new guest joins with the chosen job and body');
  }
  for (const lang of ['en', 'sv']) {
    const f = fixture({ characters: guestSlots, current: 'guest-two', cached: guestSlots[1].look, lang });
    f.get('login-guest').click(); await Promise.resolve();
    check(f.scenes.at(-1) === 'chars' && f.sockets.length === 0, 'saved guests get a choice before any connection');
    check(f.resumes() === 0, 'guest picker never refreshes an account session');
    const rows = f.get('chars-list').children;
    check(rows.length === 2 && rows.every(r => r.children.length === 1), 'both saved guests appear without deleting their keys');
    check(rows[0].textContent === 'First · warrior' && rows[1].textContent === 'Second · priest', 'picker shows character name and job without invented levels');
    check(!f.get('chars-new').disabled && f.get('chars-gm').hidden, 'guest can create another character without account or GM controls');
    check(f.confirmations[0] === f.ctx.Locale.translate(warning), 'warning uses the selected language');
    check(f.ctx.Locale.translate('Guest characters saved in this browser') === (lang === 'sv' ? 'Gästkaraktärer sparade i den här webbläsaren' : 'Guest characters saved in this browser'), 'guest heading has Swedish');
    rows[0].children[0].click(); const join = f.open();
    check(join.token === 'guest-one' && join.look === null, 'explicit selection resumes the chosen server character rather than the last one');
    check(JSON.parse(f.store.get(f.guestKey)).characters.length === 2, 'selecting does not replace another guest');
  }
  {
    const f = fixture({ characters: guestSlots, current: 'guest-two', cached: guestSlots[1].look });
    const before = f.store.get(f.guestKey); f.ctx.acceptWarning = false; f.get('login-guest').click();
    check(f.confirmations.length === 1 && f.scenes.length === 0 && f.sockets.length === 0, 'cancel leaves the player at sign-in');
    check(f.store.get(f.guestKey) === before, 'cancel preserves current guest, all keys and layouts');
  }
  {
    const f = fixture({ characters: guestSlots, current: 'guest-two', cached: guestSlots[1].look });
    f.get('login-guest').click(); f.get('chars-new').click();
    check(f.scenes.at(-1) === 'create' && !f.sockets.length, 'New character opens job and appearance choices before connecting');
    f.ctx.cfg = { name: 'NewHunter', class: 'hunter', gender: 'female' }; f.get('name').value = 'NewHunter'; f.get('go').click();
    const join = f.open();
    check(join.token === null && join.look.name === 'NewHunter' && join.look.class === 'hunter', 'new job creates a new guest rather than modifying the old one');
    check(f.store.get(f.guestKey).includes('guest-one') && f.store.get(f.guestKey).includes('guest-two'), 'creating preserves previous guest access');
  }
  {
    const account = { session: 'account-session', name: 'Account', kind: 'game', current: 'account-one', slots: { 'account-one': { skillSlots: ['account-skill'] } } };
    const f = fixture({ characters: guestSlots, current: 'guest-two', cached: { name: 'AccountHero', class: 'hunter' }, mode: 'account', account });
    f.ctx.Online.useAccount(); f.ctx.save.guestChar = guestSlots[1].look;
    f.ctx.acceptWarning = false; f.get('login-guest').click();
    check(f.ctx.Online.mode === 'account' && f.ctx.save.char.name === 'AccountHero', 'cancel does not switch account mode or character');
    f.ctx.acceptWarning = true; f.get('login-guest').click(); await Promise.resolve();
    check(f.scenes.at(-1) === 'chars' && f.ctx.Online.mode === 'guest', 'switching from account shows guest choices');
    check(f.resumes() === 0 && JSON.parse(f.store.get(f.accountKey)).session === 'account-session', 'guest choices neither refresh nor clear the saved account');
    check(f.ctx.save.char.name === 'Second', 'account appearance cannot be reused as the guest identity');
  }
  {
    const f = fixture();
    const entries = Array.from({ length: 5 }, (_, i) => ({ id: 'account-' + i, look: { name: 'Account' + i, class: 'mage' }, level: i + 1 }));
    f.ctx.Online.adopt({ ok: true, session: 'account-session', account: { name: 'Account', kind: 'game' }, characters: entries, max: 5 });
    f.ctx.Online.useAccount(); f.ctx.Account.renderChars();
    check(f.get('chars-new').disabled && f.get('chars-list').children.every(r => r.children.length === 2), 'account cap and deletion controls remain available only for accounts');
    check(f.get('chars-list').children[0].textContent.includes('Lv 1 mage'), 'accounts retain authoritative levels');
  }
  // Reconnect helper must select the saved current character, not blindly the first.
  const { playGuest } = require('./lib/guest.cjs');
  for (const [visible, selected, expected] of [[false, -1, null], [true, 1, 1], [true, -1, 0]]) {
    let choice = null, guestClicks = 0, listener = null, accepted = 0;
    await playGuest({ on: (event, fn) => { listener = fn; }, off: () => { listener = null; }, evaluate: async () => selected,
      locator: selector => ({ click: async () => { guestClicks++; await listener({ message: () => warning, accept: async () => { accepted++; } }); },
        isVisible: async () => visible, nth: index => ({ click: async () => { choice = index; } }) }) });
    check(choice === expected && guestClicks === 1 && accepted === 1 && listener === null, 'reconnect fixture acknowledges the warning, cleans up its handler and explicitly chooses the current guest or leaves creation alone');
  }
  // Shared unrelated browser fixtures acknowledge only this warning, in either language.
  const shared = read('tests/lib/playwright.cjs');
  const initSource = shared.slice(shared.indexOf('const init = '), shared.indexOf('function wrap('));
  for (const enabled of [true, false]) {
    let nativeCalls = 0;
    const ctx = { window: { confirm: () => { nativeCalls++; return false; } } };
    vm.createContext(ctx); vm.runInContext(initSource + '; globalThis.runInit = init;', ctx);
    ctx.runInit({ stub: false, version: null, guestWarnings: enabled ? [warning] : [] });
    check(ctx.window.confirm(warning) === enabled, 'test fixtures explicitly accept the guest risk while dedicated dialog tests opt out');
    check(ctx.window.confirm('Unrelated confirmation') === false, 'other confirmation dialogs are never auto accepted');
    check(nativeCalls === (enabled ? 1 : 2), 'native dialog handling is preserved outside the guest warning');
  }
  console.log(`Guest choice: ${checks} warning, cancel, saved-key, job/body, picker, account and reconnect checks passed.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
