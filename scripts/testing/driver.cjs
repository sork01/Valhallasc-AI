const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { EventEmitter } = require('node:events');
const WebSocket = require('ws');
const { z } = require('zod');

const root = path.resolve(__dirname, '../..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const number = z.number().finite();
// Friends and parties (server/src/world/social.rs). A target is a character id, a player name, or a connected bot's
// name (`bot`, resolved here to that bot's character id).
const botRef = z.string().regex(/^[a-zA-Z][a-zA-Z0-9_-]{0,15}$/);
const target = { id: z.string().min(1).max(64).optional(), bot: botRef.optional() };
const socialSchema = z.discriminatedUnion('op', [
  z.object({ op: z.literal('refresh') }).strict(),
  z.object({ op: z.literal('who') }).strict(),
  z.object({ op: z.literal('friend_request'), ...target, name: z.string().max(40).optional() }).strict(),
  z.object({ op: z.literal('friend_accept'), ...target }).strict(),
  z.object({ op: z.literal('friend_decline'), ...target }).strict(),
  z.object({ op: z.literal('friend_remove'), ...target }).strict(),
  z.object({ op: z.literal('party_invite'), ...target, name: z.string().max(40).optional() }).strict(),
  z.object({ op: z.literal('party_accept'), ...target }).strict(),
  z.object({ op: z.literal('party_decline'), ...target }).strict(),
  z.object({ op: z.literal('party_leave') }).strict(),
  z.object({ op: z.literal('party_kick'), ...target }).strict(),
  z.object({ op: z.literal('party_promote'), ...target }).strict(),
  z.object({ op: z.literal('party_chat'), text: z.string().min(1).max(240) }).strict(),
]);
// The same actions accepted by ClientMessage; no arbitrary state setters or joins.
const actionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('input'), dx: number.min(-1).max(1), dy: number.min(-1).max(1) }).strict(),
  z.object({ type: z.literal('stop') }).strict(),
  z.object({ type: z.literal('allocate_stat'), stat: z.enum(['strength', 'agility', 'intellect', 'stamina', 'dexterity', 'accuracy']) }).strict(),
  z.object({ type: z.literal('move'), x: number, y: number }).strict(),
  z.object({ type: z.literal('target'), id: z.number().int().nonnegative() }).strict(),
  z.object({ type: z.literal('attack'), fx: number, fy: number }).strict(),
  z.object({ type: z.literal('dash'), dx: number.min(-1).max(1), dy: number.min(-1).max(1) }).strict(),
  z.object({ type: z.literal('skill'), id: z.string().regex(/^[a-z]{3,20}$/), fx: number, fy: number }).strict(),
  z.object({ type: z.literal('equip'), armor: z.string().max(32).optional(), weapon: z.string().max(32).optional(), slots: z.partialRecord(z.enum(['headgear', 'shoulders', 'chest', 'pants', 'gloves', 'hands', 'necklace', 'accessory1', 'accessory2']), z.string().max(64)).optional() }).strict(),
  z.object({ type: z.literal('use_item'), item: z.string().regex(/^[a-z0-9_]{1,40}$/) }).strict(),
  z.object({ type: z.literal('interact'), npc: z.string().max(32), offer: z.string().max(32).optional() }).strict(),
  z.object({ type: z.literal('chat'), text: z.string().min(1).max(240) }).strict(),
  z.object({ type: z.literal('social'), command: socialSchema }).strict(),
  z.object({ type: z.literal('ping'), nonce: z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER) }).strict(),
]);
// Test-server shortcuts (server/src/world/debug.rs). The private worlds start Rust with VALHALLA_TEST_COMMANDS=1;
// the public service never does, and it refuses these messages.
const questAction = z.enum(['accept', 'complete', 'claim', 'finish', 'reset']);
const debugSchema = z.discriminatedUnion('op', [
  z.object({ op: z.literal('set_level'), level: z.number().int().min(1).max(100) }).strict(),
  z.object({ op: z.literal('give_xp'), amount: z.number().int().min(0).max(4294967295) }).strict(),
  z.object({ op: z.literal('set_gold'), gold: z.number().int().min(0).max(4294967295) }).strict(),
  z.object({ op: z.literal('set_hp'), hp: number.positive() }).strict(),
  z.object({ op: z.literal('die') }).strict(),
  z.object({ op: z.literal('reset_stats') }).strict(),
  z.object({ op: z.literal('reset_cooldowns') }).strict(),
  z.object({ op: z.literal('set_god_mode'), enabled: z.boolean() }).strict(),
  z.object({ op: z.literal('teleport'), zone: z.number().int().min(0), x: number, y: number }).strict(),
  z.object({ op: z.literal('give_item'), item: z.string().max(64), quantity: z.number().int().min(1).max(9999).default(1), force: z.boolean().default(false) }).strict(),
  z.object({ op: z.literal('take_item'), item: z.string().max(64), quantity: z.number().int().min(1).max(9999).default(1) }).strict(),
  z.object({ op: z.literal('drop_item'), item: z.string().max(64), quantity: z.number().int().min(1).max(9999).default(1) }).strict(),
  z.object({ op: z.literal('quest'), id: z.string().max(40), action: questAction }).strict(),
  z.object({ op: z.literal('kill_enemy'), id: z.number().int().nonnegative() }).strict(),
  z.object({ op: z.literal('respawn_enemy'), id: z.number().int().nonnegative() }).strict(),
  z.object({ op: z.literal('spawn_enemy'), kind: z.enum(['green', 'blue', 'pink', 'yellow', 'beetle', 'wisp', 'spider', 'wraith', 'golem']), x: number, y: number, level: z.number().int().min(1).max(100).optional() }).strict(),
  z.object({ op: z.literal('summon_king') }).strict(),
]);
const botSchema = z.object({
  bot: z.string().regex(/^[a-zA-Z][a-zA-Z0-9_-]{0,15}$/),
  class: z.enum(['warrior', 'mage', 'assassin', 'priest', 'hunter']).default('warrior'),
}).strict();

function spacingViolation(snapshot) {
  const actors = [...snapshot.players, ...snapshot.slimes].filter(a => !a.dead);
  for (let i = 0; i < actors.length; i++) for (let j = i + 1; j < actors.length; j++) {
    const a = actors[i], b = actors[j];
    if (!a.kind && !b.kind) continue;
    // Zones are separate maps that merely share coordinates.
    if ((a.zone || 0) !== (b.zone || 0)) continue;
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
    // The server sends each connection only the zone its character is in. Keep each bot's latest view and expose
    // one merged snapshot (players, enemies, bolts and drops of every zone a bot can see).
    this.views = new Map();
    this.merged = null;
    this.events = [];
    this.spacingFailure = null;
    this.snapshotsChecked = 0;
    this.child = null;
    this.stopping = false;
    this.runDir = null;
    this.debugRef = 0;
    // Optional per-world overrides, applied at every (re)launch: godMode true/false, levelSpread 0-5.
    this.godMode = undefined;
    this.levelSpread = undefined;
  }
  get snapshot() { return this.merged; }
  set snapshot(value) { if (value === null) { this.views.clear(); this.merged = null; } else this.merged = value; }
  merge() {
    const best = new Map();
    for (const [bot, view] of this.views) {
      const identity = this.bots.get(bot);
      if (!identity || identity.socket?.readyState !== WebSocket.OPEN) continue;
      const zone = view.players.find(p => p.id === identity.id)?.zone || 0;
      if (!best.has(zone) || view.tick > best.get(zone).tick) best.set(zone, view);
    }
    if (!best.size) return this.merged;
    const views = [...best.values()], newest = views.reduce((a, b) => b.tick > a.tick ? b : a);
    const all = key => views.flatMap(v => v[key]);
    return { ...newest, players: all('players'), slimes: all('slimes'), bolts: all('bolts'), drops: all('drops'),
      online: Math.max(...views.map(v => v.online)), zonesSeen: [...best.keys()].sort() };
  }
  async start() {
    if (this.child || this.runDir) throw Error('This world has already been started; create a new TestWorld.');
    fs.mkdirSync(path.join(root, 'test-results'), { recursive: true });
    this.runDir = fs.mkdtempSync(path.join(root, 'test-results/driver-'));
    this.db = path.join(this.runDir, 'test.sqlite');
    return this.launch();
  }
  async launch() {
    this.stopping = false;
    this.stopPromise = null;
    this.url = null;
    this.snapshot = null;
    const binary = process.env.VALHALLA_BINARY || path.join(root, 'target/debug/valhalla-server');
    const environment = { ...process.env, VALHALLA_BIND: '127.0.0.1:0', VALHALLA_DB: this.db,
      VALHALLA_CLIENT_DIR: path.join(root, 'client'), RUST_LOG: 'valhalla_server=info',
      // Test worlds are invulnerable (enemies still fight and enemy levels are still random), so scenarios never fail by dying.
      VALHALLA_GOD_MODE: this.godMode === undefined ? process.env.VALHALLA_GOD_MODE ?? '1' : this.godMode ? '1' : '0',
      // Lets bots send `debug` shortcuts (levels, items, teleports, quests); see debug() below.
      VALHALLA_TEST_COMMANDS: '1' };
    if (this.levelSpread !== undefined) environment.VALHALLA_LEVEL_SPREAD = String(this.levelSpread);
    // Optional: new characters start at this level (test servers only), so learned skills can be driven for real.
    if (this.startLevel || process.env.VALHALLA_START_LEVEL) environment.VALHALLA_START_LEVEL = String(this.startLevel || process.env.VALHALLA_START_LEVEL);
    // Use the server's normal same-host origin policy for the private port.
    // An empty configured origin rejects real browsers, and an inherited
    // production origin is wrong for a disposable loopback world.
    delete environment.VALHALLA_ORIGIN;
    this.child = spawn(binary, [], {
      cwd: root,
      env: environment,
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
      // MCP clients inherit fewer environment variables than a shell. Rust's
      // tracing output can consequently contain ANSI around address=...
      startup = (startup + data.toString()).replace(/\x1b\[[0-9;]*m/g, '').slice(-8192);
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
  async restart() {
    this.requireRunning();
    const connected = [...this.bots].filter(([, p]) => p.socket?.readyState === WebSocket.OPEN).map(([bot]) => bot);
    await this.stop();
    await this.launch();
    for (const bot of connected) await this.connect({ bot });
    return this.info();
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
      const earlier = this.views.get(bot);
      if (!earlier || snapshot.tick > earlier.tick || (packet.type === 'welcome' && snapshot.tick >= earlier.tick)) {
        this.views.set(bot, snapshot);
        this.merged = this.merge();
      }
      this.snapshotsChecked++;
      this.spacingFailure ||= spacingViolation(snapshot);
    } else {
      // The latest friends/party state per bot. Party health arrives twice a second, so it never enters the event log.
      const identity = this.bots.get(bot);
      if (identity && packet.type === 'social') identity.social = packet;
      if (identity && packet.type === 'party') {
        if (identity.social) identity.social = { ...identity.social, party: packet.party };
        this.emit('change');
        return;
      }
      if (identity && packet.type === 'who') identity.who = packet.players;
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
    const ws = new WebSocket(this.url.replace(/^http/, 'ws') + 'ws', { origin: new URL(this.url).origin });
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
    if (action.type === 'social') action = { type: 'social', command: this.resolveSocial(action.command) };
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
  resolveSocial({ bot: other, ...command }) {
    if (other === undefined) return command;
    const identity = this.bots.get(other);
    if (!identity?.id) throw Error(`Unknown bot: ${other}`);
    if (command.id !== undefined) throw Error('Give either id or bot, not both.');
    return { ...command, id: identity.id };
  }
  // One friends/party command. Resolves with what the bot was told: notices (ok false is a refusal), the state it now
  // holds (friends, incoming/outgoing requests, party) and, for `who`, the online roster.
  async social(bot, command) {
    this.requireRunning();
    command = socialSchema.parse(command);
    const identity = this.bots.get(bot);
    if (!identity) throw Error(`Unknown bot: ${bot}`);
    const earlier = new Set(this.events);
    await this.action(bot, { type: 'social', command });
    // Every command is answered: a notice (success or refusal), or for refresh/who/party_chat the state, roster or chat line.
    const answers = command.op === 'refresh' ? ['social'] : command.op === 'who' ? ['who'] : command.op === 'party_chat' ? ['notice', 'chat'] : ['notice'];
    await this.waitFor(() => this.events.find(e => !earlier.has(e) && e.bot === bot && answers.includes(e.type)), 5000, `Social ${command.op}`);
    // The notice is sent just before the new state; let both land.
    if (answers.includes('notice')) await delay(150);
    const fresh = this.events.filter(e => !earlier.has(e) && e.bot === bot);
    return { bot, op: command.op, notices: fresh.filter(e => e.type === 'notice').map(e => ({ ok: e.ok, text: e.text })),
      chat: fresh.filter(e => e.type === 'chat').map(e => ({ channel: e.channel || 'world', name: e.name, text: e.text })),
      state: this.socialState(bot), ...(command.op === 'who' ? { online: identity.who } : {}) };
  }
  socialState(bot) {
    const social = this.bots.get(bot)?.social;
    if (!social) return null;
    const { friends, incoming, outgoing, party } = social;
    return { friends: friends.map(f => ({ name: f.name, id: f.id, online: f.online, level: f.level })),
      incoming: incoming.map(i => ({ kind: i.kind, from: i.name })), outgoing: outgoing.map(i => ({ kind: i.kind, to: i.name })),
      party: party && { leader: party.members.find(m => m.id === party.leader)?.name, size: party.members.length, max: party.max,
        members: party.members.map(m => ({ name: m.name, online: m.online, hp: m.hp, maxHp: m.maxHp })) } };
  }
  // One shortcut command; resolves once the bot's own snapshot shows its effect. Errors the server reports throw.
  async debug(bot, command) {
    this.requireRunning();
    command = debugSchema.parse(command);
    const player = this.bots.get(bot);
    if (!player || player.socket?.readyState !== WebSocket.OPEN) throw Error(`Bot ${bot} is not connected.`);
    const socket = player.socket, ref = ++this.debugRef;
    const job = (player.sendQueue || Promise.resolve()).then(async () => {
      const remaining = 25 - (Date.now() - (player.sentAt || 0));
      if (remaining > 0) await delay(remaining);
      this.requireRunning();
      if (player.socket !== socket || socket.readyState !== WebSocket.OPEN) throw Error(`Bot ${bot} disconnected before the command was sent.`);
      player.sentAt = Date.now();
      socket.send(JSON.stringify({ type: 'debug', ref, command }));
      const reply = await this.waitFor(() => this.events.find(e => e.bot === bot && e.type === 'debug' && e.ref === ref), 5000, `Debug ${command.op}`);
      if (!reply.ok) throw Error(reply.error);
      // The change is in the next broadcast; wait for the bot's view to pass the reply's tick.
      await this.waitFor(() => (this.views.get(bot)?.tick ?? 0) > reply.tick, 3000, `Snapshot after ${command.op}`);
      return { bot, op: command.op, result: reply.result, player: this.summary(bot) };
    });
    player.sendQueue = job.catch(() => {});
    return job;
  }
  // The fields a test usually wants from a player, without the bulky inventory and look.
  summary(bot) {
    const p = this.player(bot);
    if (!p) return null;
    const { id, zone = 0, x, y, hp, maxHp, level, xp, xpNeed, gold, kills, statPoints, dead, skillCd, buffs, bagCapacity, bagUsed } = p;
    return { id, zone, x, y, hp, maxHp, level, xp, xpNeed, gold, kills, statPoints, dead, skillCd, buffs, bagCapacity, bagUsed };
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

module.exports = { TestWorld, root, actionSchema, botSchema, debugSchema, socialSchema, delay, spacingViolation };
