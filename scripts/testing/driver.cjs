const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { EventEmitter } = require('node:events');
const WebSocket = require('ws');
const { z } = require('zod');

const root = path.resolve(__dirname, '../..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const number = z.number().finite();
// The same actions accepted by ClientMessage; no arbitrary state setters or joins.
const actionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('input'), dx: number.min(-1).max(1), dy: number.min(-1).max(1) }).strict(),
  z.object({ type: z.literal('stop') }).strict(),
  z.object({ type: z.literal('move'), x: number, y: number }).strict(),
  z.object({ type: z.literal('target'), id: z.number().int().nonnegative() }).strict(),
  z.object({ type: z.literal('attack'), fx: number, fy: number }).strict(),
  z.object({ type: z.literal('dash'), dx: number.min(-1).max(1), dy: number.min(-1).max(1) }).strict(),
  z.object({ type: z.literal('equip'), armor: z.string().max(32), weapon: z.string().max(32) }).strict(),
  z.object({ type: z.literal('interact'), npc: z.string().max(32), offer: z.string().max(32).optional() }).strict(),
  z.object({ type: z.literal('chat'), text: z.string().min(1).max(240) }).strict(),
  z.object({ type: z.literal('ping'), nonce: z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER) }).strict(),
]);
const botSchema = z.object({
  bot: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_-]{0,15}$/),
  class: z.enum(['warrior', 'mage', 'assassin']).default('warrior'),
}).strict();

function spacingViolation(snapshot) {
  const actors = [...snapshot.players, ...snapshot.slimes].filter(a => !a.dead);
  for (let i = 0; i < actors.length; i++) for (let j = i + 1; j < actors.length; j++) {
    const a = actors[i], b = actors[j];
    if (!a.kind && !b.kind) continue;
    const distance = Math.hypot(a.x - b.x, a.y - b.y);
    const gap = a.kind && b.kind ? (a.r || .3) + (b.r || .3) : 1;
    if ((Math.floor(a.x) === Math.floor(b.x) && Math.floor(a.y) === Math.floor(b.y)) || distance < gap - 1e-6) {
      return { tick: snapshot.tick, a: { id: a.id, x: a.x, y: a.y }, b: { id: b.id, x: b.x, y: b.y }, distance };
    }
  }
  return null;
}

class TestWorld extends EventEmitter {
  constructor() {
    super();
    this.bots = new Map();
    this.snapshot = null;
    this.events = [];
    this.spacingFailure = null;
    this.snapshotsChecked = 0;
    this.child = null;
    this.stopping = false;
    this.runDir = null;
  }
  async start() {
    if (this.child || this.runDir) throw Error('This world has already been started; create a new TestWorld.');
    fs.mkdirSync(path.join(root, 'test-results'), { recursive: true });
    this.runDir = fs.mkdtempSync(path.join(root, 'test-results/driver-'));
    this.db = path.join(this.runDir, 'test.sqlite');
    const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
    this.child = spawn(binary, [], {
      cwd: root,
      env: { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: this.db,
        VALHALLA_CLIENT_DIR: path.join(root, 'client'), VALHALLA_ORIGIN: '', RUST_LOG: 'valhalla_server=info' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    this.failure = null;
    let startup = '';
    this.child.on('error', error => { this.failure = `Cannot launch server: ${error.code || 'unknown error'}. Build it with cargo build.`; this.emit('change'); });
    this.exited = new Promise(resolve => this.child.once('close', (code, signal) => {
      if (!this.stopping) this.failure = `Private server exited (${signal || code}).`;
      this.emit('change');
      resolve();
    }));
    this.child.stdout.on('data', data => {
      startup = (startup + data.toString()).slice(-8192);
      const match = startup.match(/address=(127\.0\.0\.1:\d+)/);
      if (match) this.url = `http://${match[1]}/`;
      this.emit('change');
    });
    // Drain stderr, but never expose raw server logs through MCP or artifacts.
    this.child.stderr.on('data', () => {});
    try {
      await this.waitFor(() => !!this.url, 15000, 'Private server startup');
      const health = await (await fetch(this.url + 'health', { signal: AbortSignal.timeout(5000) })).json();
      if (health.status !== 'ok' || health.online !== 0) throw Error('Unexpected private server health.');
      return this.info();
    } catch (error) {
      await this.stop();
      throw error;
    }
  }
  info() {
    return { running: !!this.child && !this.stopping && !this.failure, url: this.url, database: this.db, artifacts: this.runDir,
      bots: [...this.bots].map(([bot, p]) => ({ bot, id: p.id, class: p.class, connected: p.socket?.readyState === WebSocket.OPEN })) };
  }
  requireRunning() {
    if (!this.child || this.stopping || this.failure) throw Error(this.failure || 'Start a private test world first.');
  }
  async waitFor(predicate, timeoutMs = 10000, label = 'Condition') {
    const deadline = Date.now() + timeoutMs;
    while (true) {
      if (this.failure) throw Error(this.failure);
      if (this.stopping) throw Error('Private test world is stopping.');
      const value = await predicate();
      if (value) return value;
      if (Date.now() >= deadline) throw Error(`${label} timed out after ${timeoutMs}ms (tick ${this.snapshot?.tick ?? 'unknown'}).`);
      await delay(50);
    }
  }
  receive(bot, packet) {
    const snapshot = packet.type === 'welcome' ? packet.snapshot : packet.type === 'snapshot' ? packet : null;
    if (snapshot) {
      // A welcome can include a just-joined actor before the next broadcast tick.
      // An older broadcast at that same tick must not erase the new actor.
      if (!this.snapshot || snapshot.tick > this.snapshot.tick ||
          (packet.type === 'welcome' && snapshot.tick === this.snapshot.tick)) this.snapshot = snapshot;
      this.snapshotsChecked++;
      this.spacingFailure ||= spacingViolation(snapshot);
    } else {
      // Never store a welcome packet: it contains a server-issued bearer key.
      this.events.push({ bot, ...packet });
      if (this.events.length > 500) this.events.shift();
    }
    this.emit('change');
  }
  async connect(options) {
    this.requireRunning();
    const { bot, class: playerClass } = botSchema.parse(options);
    let player = this.bots.get(bot);
    if (player?.socket && player.socket.readyState !== WebSocket.CLOSED) throw Error(`Bot ${bot} is already connected or disconnecting.`);
    if (!player && this.bots.size >= 16) throw Error('A test world supports at most 16 bot identities.');
    if (!player) {
      player = { class: playerClass, token: null, id: null, socket: null };
      this.bots.set(bot, player);
    }
    const ws = new WebSocket(this.url.replace(/^http/, 'ws') + 'ws');
    player.socket = ws;
    player.connectionError = null;
    let welcomed = false;
    ws.on('error', () => { player.connectionError = `WebSocket connection failed for ${bot}.`; });
    ws.on('open', () => ws.send(JSON.stringify({ type: 'join', version: 1, token: player.token,
      look: player.token ? undefined : { name: bot.length >= 2 ? bot : bot + 'x', class: player.class } })));
    ws.on('message', data => {
      let packet;
      try { packet = JSON.parse(data.toString()); } catch { player.connectionError = 'Invalid server packet.'; ws.close(); return; }
      if (packet.type === 'welcome') {
        player.token = packet.token || player.token;
        player.id = packet.id;
        welcomed = true;
      }
      if (packet.type === 'error' && (!welcomed || packet.fatal)) player.connectionError = packet.text;
      this.receive(bot, packet);
    });
    try {
      await this.waitFor(() => {
        if (player.connectionError) throw Error(player.connectionError);
        if (ws.readyState === WebSocket.CLOSED) throw Error(`Bot ${bot} disconnected before joining.`);
        return welcomed && !!this.player(bot);
      }, 10000, `Join ${bot}`);
    } catch (error) { ws.terminate(); throw error; }
    player.heartbeat = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping', nonce: 0 }));
    }, 10000);
    player.heartbeat.unref();
    ws.once('close', () => clearInterval(player.heartbeat));
    return { bot, id: player.id, class: player.class, player: this.player(bot) };
  }
  player(bot) {
    const identity = this.bots.get(bot);
    if (!identity) throw Error(`Unknown bot: ${bot}`);
    return this.snapshot?.players.find(p => p.id === identity.id) || null;
  }
  async disconnect(bot) {
    const player = this.bots.get(bot);
    if (!player) throw Error(`Unknown bot: ${bot}`);
    clearInterval(player.heartbeat);
    const ws = player.socket;
    if (!ws || ws.readyState === WebSocket.CLOSED) return { bot, connected: false };
    const closed = new Promise(resolve => ws.once('close', resolve));
    ws.close();
    const timer = setTimeout(() => ws.terminate(), 2000);
    try { await closed; } finally { clearTimeout(timer); }
    if (!this.stopping && !this.failure) {
      // Closing a socket precedes the simulation's Leave command; wait before resume.
      const remaining = [...this.bots.values()].filter(p => p.socket?.readyState === WebSocket.OPEN).length;
      await this.waitFor(async () => {
        const health = await (await fetch(this.url + 'health', { signal: AbortSignal.timeout(2000) })).json();
        return health.online <= remaining;
      }, 5000, `Leave ${bot}`);
    }
    return { bot, connected: false };
  }
  async action(bot, action) {
    this.requireRunning();
    action = actionSchema.parse(action);
    const player = this.bots.get(bot);
    if (!player || player.socket?.readyState !== WebSocket.OPEN) throw Error(`Bot ${bot} is not connected.`);
    const socket = player.socket;
    // Serialize concurrent API calls per bot as well as MCP calls.
    const job = (player.sendQueue || Promise.resolve()).then(async () => {
      const remaining = 25 - (Date.now() - (player.sentAt || 0));
      if (remaining > 0) await delay(remaining);
      this.requireRunning();
      if (player.socket !== socket || socket.readyState !== WebSocket.OPEN) throw Error(`Bot ${bot} disconnected before the action was sent.`);
      player.sentAt = Date.now();
      socket.send(JSON.stringify(action));
      return { bot, sent: action, tick: this.snapshot?.tick };
    });
    player.sendQueue = job.catch(() => {});
    return job;
  }
  inspect({ bot, events = 20 } = {}) {
    this.requireRunning();
    return { ...this.info(), snapshot: bot ? this.player(bot) : this.snapshot,
      events: events > 0 ? this.events.slice(-Math.min(events, 500)) : [],
      spacingFailure: this.spacingFailure, snapshotsChecked: this.snapshotsChecked };
  }
  async advance(ms) {
    this.requireRunning();
    if (!Number.isInteger(ms) || ms < 0 || ms > 30000) throw Error('Wait must be an integer from 0 to 30000 milliseconds.');
    const until = Date.now() + ms;
    await this.waitFor(() => Date.now() >= until, ms + 1000, 'Wait world');
    return this.inspect();
  }
  saveReport(report) {
    if (!this.runDir) throw Error('No test run to save.');
    const artifact = path.join(this.runDir, 'report.json');
    fs.writeFileSync(artifact, JSON.stringify({ ...report, world: this.info(), snapshot: this.snapshot,
      events: this.events, spacingFailure: this.spacingFailure, snapshotsChecked: this.snapshotsChecked }, null, 2) + '\n');
    return artifact;
  }
  async stop() {
    if (this.stopPromise) return this.stopPromise;
    this.stopping = true;
    this.stopPromise = (async () => {
      await Promise.all([...this.bots.keys()].map(bot => this.disconnect(bot)));
      if (this.child && this.child.exitCode === null && this.child.signalCode === null) {
        this.child.kill('SIGTERM');
        const timer = setTimeout(() => this.child?.kill('SIGKILL'), 7000);
        try { await this.exited; } finally { clearTimeout(timer); }
      }
      this.child = null;
      return { running: false, artifacts: this.runDir };
    })();
    return this.stopPromise;
  }
}

module.exports = { TestWorld, root, actionSchema, botSchema, delay, spacingViolation };
