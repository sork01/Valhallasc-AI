// Virtual network/clock: exercise stale sockets and queued snapshots without live accounts.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(process.env.ONLINE_CANDIDATE || path.join(__dirname, '../client/online.js'), 'utf8');
const busy = { type: 'error', fatal: true, text: 'This character is already online in another window.' };
let checks = 0;
const check = (ok, label) => { assert.ok(ok, label); checks++; };
function harness(account = false) {
  let now = 0, nextId = 0; const timers = new Map(), frames = new Map(), elements = new Map(), storage = new Map(), sockets = [], received = [];
  const endpoint = 'ws://example.test/Valhallasc/ws';
  storage.set('valhallasc.characters.v1:' + endpoint, JSON.stringify({ current: 'fixture-guest', characters: [{ token: 'fixture-guest', look: { name: 'Fixture' } }] }));
  storage.set('valhallasc.account.v1:' + endpoint, JSON.stringify({ session: 'fixture-session', current: 'fixture-id', slots: {} }));
  const later = (fn, ms, interval = 0) => { const id = ++nextId; timers.set(id, { fn, at: now + ms, interval }); return id; };
  const advance = ms => {
    const end = now + ms;
    for (;;) {
      const due = [...timers].filter(([, t]) => t.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      const [id, t] = due; now = t.at; timers.delete(id); if (t.interval) timers.set(id, { ...t, at: now + t.interval }); t.fn();
    }
    now = end;
  };
  const element = () => ({ hidden: false, disabled: false, dataset: {}, textContent: '', children: [], listeners: {},
    addEventListener(name, fn) { this.listeners[name] = fn; }, append(...nodes) { this.children.push(...nodes); }, querySelector() { return null; }, focus() {}, blur() {}, remove() {}, });
  const el = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  class Socket {
    static OPEN = 1;
    constructor() { this.readyState = 0; this.sent = []; sockets.push(this); }
    open() { this.readyState = 1; this.onopen?.(); }
    send(data) { this.sent.push(JSON.parse(data)); }
    packet(packet) { this.onmessage?.({ data: JSON.stringify(packet) }); }
    close() { if (this.readyState >= 2) return; this.readyState = 2; later(() => { this.readyState = 3; this.onclose?.(); }, 0); }
  }
  const sandbox = {
    URL, location: { href: 'http://example.test/Valhallasc/' }, WebSocket: Socket,
    Date: { now: () => now }, setTimeout: (fn, ms) => later(fn, ms), clearTimeout: id => timers.delete(id),
    setInterval: (fn, ms) => later(fn, ms, ms), clearInterval: id => timers.delete(id),
    requestAnimationFrame: fn => { const id = ++nextId; frames.set(id, fn); return id; }, cancelAnimationFrame: id => frames.delete(id),
    localStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) },
    document: { getElementById: el, createElement: element, createTextNode: text => ({ textContent: text }), addEventListener() {}, activeElement: null },
    addEventListener() {}, WORLD_MAP: { city: { name: 'Alderhaven' }, zones: [] }, Keys: { label: x => x, skillRange: () => '1-9' },
    Field: { clearInput() {} }, SystemLog: { add() {}, event: p => received.push(p.kind) },
  };
  sandbox.window = sandbox;
  vm.runInNewContext(source, sandbox);
  if (account) sandbox.Online.useAccount();
  sandbox.Online.start({ look: { name: 'Fixture' }, onWelcome: () => received.push('welcome'), onSnapshot: p => received.push(p.tick) });
  const welcome = () => ({ type: 'welcome', id: 'fixture-id', snapshot: { players: [{ id: 'fixture-id', look: { name: 'Fixture' }, level: 1, x: 0, y: 0 }] } });
  const snapshot = tick => ({ type: 'snapshot', tick, online: 1, players: [{ id: 'fixture-id', zone: 0, x: 0, y: 0, look: { name: 'Fixture' } }] });
  const render = () => { const pending = [...frames.values()]; frames.clear(); for (const fn of pending) fn(now); };
  return { sandbox, sockets, advance, el, received, storage, welcome, snapshot, render, latest: () => sockets.at(-1) };
}
for (const account of [false, true]) {
  const h = harness(account); h.latest().open(); h.latest().packet(h.welcome());
  check(h.sandbox.Online.connected, 'fixture starts connected');
  const first = h.latest(); first.close(); h.advance(500);
  const retry = h.latest(); retry.open(); retry.packet(busy); h.advance(0);
  check(!h.el('connection-retry').hidden && h.el('connection-text').textContent.includes('previous connection'), 'busy reconnect remains recoverable');
  h.advance(1000); const resumed = h.latest(); resumed.open(); resumed.packet(h.welcome());
  check(h.sandbox.Online.connected && h.el('connection-overlay').hidden, 'server slot release restores play automatically');
  check(resumed.sent[0][account ? 'session' : 'token'] === (account ? 'fixture-session' : 'fixture-guest'), 'reconnect preserves the original identity');
  retry.onclose(); first.packet({ type: 'error', fatal: true, code: 'auth', text: 'Old failure' });
  check(h.sandbox.Online.connected && h.el('connection-overlay').hidden, 'stale socket callbacks cannot disconnect the replacement');
  h.sandbox.Online.stop(); h.advance(10000);
  check(h.latest() === resumed, 'leaving cancels all pending reconnects');
}
{
  const h = harness(); h.latest().open(); h.latest().packet(h.welcome()); h.received.length = 0;
  for (let i = 1; i <= 50; i++) h.latest().packet(h.snapshot(i));
  check(h.received.length === 0, 'snapshot burst waits for a paint opportunity'); h.render();
  check(h.received.join() === '50', 'a stalled client applies only the newest complete snapshot');
  h.latest().packet(h.snapshot(51)); h.latest().packet({ type: 'event', kind: 'hit' }); h.render();
  check(h.received.slice(-2).join() === '51,hit', 'events preserve order after a queued snapshot');
  h.latest().packet(h.snapshot(52)); h.sandbox.Online.stop(); h.render();
  check(!h.received.includes(52), 'stopping discards queued snapshots');
}
{
  const h = harness(true); h.latest().open(); h.latest().packet({ type: 'error', fatal: true, code: 'auth', text: 'Your login expired.' }); h.advance(30000);
  check(h.sockets.length === 1 && h.el('connection-retry').hidden, 'real authentication failures still stop immediately');
  check(h.sandbox.Online.account === null, 'expired credentials are still cleared');
}
{
  const h = harness();
  for (let i = 0; i < 25; i++) {
    h.latest().open(); h.latest().packet(busy); h.advance(5000);
    if (h.el('connection-text').textContent === busy.text) break;
  }
  const last = h.latest(); h.advance(30000);
  check(h.latest() === last && h.el('connection-text').textContent === busy.text && !h.el('connection-retry').hidden, 'a genuine second window gets a bounded wait and usable Retry');
}
{
  const h = harness(); const first = h.latest(); h.advance(12000);
  check(first.readyState === 0 && h.sockets.length === 1, 'joining timeout does not expire before the socket opens');
  first.open(); h.el('connection-retry').listeners.click(); const second = h.latest(); second.open(); second.packet(h.welcome());
  h.advance(16000); first.onclose();
  check(h.sandbox.Online.connected, 'a replaced socket timeout or late close cannot break the joined session');
}
console.log(`reconnect-recovery: ${checks} checks passed`);
