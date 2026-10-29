// Sound-bank selection and voice caps, independently of rendering and network timing.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const candidate = process.env.AUDIO_CANDIDATE || path.resolve(__dirname, '../client');
let source = fs.readFileSync(path.join(candidate, 'combat-audio.js'), 'utf8');
if (process.env.MUTATE === 'repeat') source = source.replace('const alternatives = choices.filter(cue => cue !== lastTake.get(key));', 'const alternatives = choices;');
const math = Object.create(Math); math.random = () => 0;
const fetched = new Set(), starts = [];
const node = extra => ({ ...extra, connect(next) { this.next = next; return next; }, disconnect() {} });
const c = {
  decodeAudioData: async data => ({ cue: data }),
  createBufferSource: () => node({ playbackRate: { value: 1 }, start() { starts.push(this); }, stop() { this.onended?.(); } }),
  createGain: () => node({ gain: { value: 1 } }),
  createBiquadFilter: () => node({ frequency: { value: 0 }, Q: { value: 0 } }),
};
const sandbox = { window: {}, Math: math, fetch: async url => { fetched.add(url.split('/').at(-1)); return { ok: true, arrayBuffer: async () => url }; } };
vm.runInNewContext(source, sandbox);
const bank = sandbox.window.RecordedCombat;
(async () => {
  await bank.prime(c);
  assert.equal(bank.ready, true);
  const manifest = JSON.parse(fs.readFileSync(path.join(candidate, 'assets/combat/sources.txt'))).clips;
  assert.deepEqual([...fetched].sort(), Object.values(manifest).map(c => c.file).sort(), 'every bundled cue is loaded exactly once');
  bank.play(c, {}, 'impact', 'hit', 1); const first = starts.at(-1).buffer;
  bank.stop(); bank.play(c, {}, 'impact', 'hit', 1);
  assert.notEqual(starts.at(-1).buffer, first, 'even a constant random number cannot immediately repeat a take');
  bank.stop();
  let seed = 17; math.random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const rates = [], volumes = [], tones = [];
  for (let i = 0; i < 20; i++) {
    bank.play(c, {}, 'beast', 'attack', 1);
    const s = starts.at(-1); rates.push(s.playbackRate.value); tones.push(s.next.frequency.value); volumes.push(s.next.next.gain.value); bank.stop();
  }
  assert(new Set(rates).size > 10 && rates.every(n => n >= .92 && n <= 1.08), 'single-take creatures also vary within a subtle pitch range');
  assert(new Set(volumes).size > 10 && new Set(tones).size > 10, 'volume and tone vary too');
  for (const stage of ['hurt', 'death']) {
    bank.play(c, {}, 'player-female', stage, 1);
    assert(starts.at(-1).buffer.cue.includes('player-female-' + stage));
    assert(starts.at(-1).playbackRate.value >= .97 && starts.at(-1).playbackRate.value <= 1.03);
    bank.stop();
  }
  const enemies = new Set(); let before = starts.length;
  for (let i = 0; i < 20; i++) bank.play(c, {}, 'beast', 'attack', 1, enemies);
  assert.equal(starts.length - before, 4, 'enemy crowd ceiling stays at four voices');
  bank.stop(); assert.equal(enemies.size, 0, 'ending voices releases the shared enemy slots');
  before = starts.length;
  for (let i = 0; i < 30; i++) bank.play(c, {}, 'impact', 'hit', 1);
  assert.equal(starts.length - before, 10, 'ordinary sounds reserve two of twelve slots for progression');
  bank.play(c, {}, 'levelup', 'celebrate', 1); assert(starts.at(-1).buffer.cue.endsWith('/levelup.mp3'));
  bank.play(c, {}, 'achievement', 'celebrate', 1); assert(starts.at(-1).buffer.cue.endsWith('/achievement.mp3'));
  before = starts.length; bank.play(c, {}, 'achievement', 'celebrate', 1);
  assert.equal(starts.length, before + 1, 'celebration is heard even when all slots are occupied');
  bank.stop();
  before = starts.length;
  assert.equal(bank.play(c, {}, 'skill', 'unknown', 1), false);
  assert.equal(starts.length, before, 'unknown skills fall back without a stale recording');
  console.log('recorded-audio: selection, modulation, female voices, all assets and voice ceilings passed');
})().catch(e => { console.error(e); process.exitCode = 1; });
