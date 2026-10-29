// New recorded-audio behavior only, in one bounded private Chromium world.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('./lib/playwright.cjs');
const { TestWorld } = require('../scripts/testing/driver.cjs');
const root = path.resolve(__dirname, '..');
const candidate = process.env.AUDIO_CANDIDATE || path.join(root, 'client');
const world = new TestWorld(); world.startLevel = 99; world.godMode = true; world.levelSpread = 0;
let browser, checks = 0;
const check = (value, label) => { assert.ok(value, label); checks++; };
(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(candidate, 'assets/combat/sources.txt'))).clips;
  for (const entry of Object.values(manifest)) {
    check(crypto.createHash('sha256').update(fs.readFileSync(path.join(candidate, 'assets/combat', entry.file))).digest('hex') === entry.sha256, `${entry.file}: pinned bytes`);
  }
  const info = await world.start();
  browser = await chromium.launch({ headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1024, height: 768 }, reducedMotion: 'reduce' });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  if (process.env.AUDIO_CANDIDATE) {
    for (const name of ['game.js', 'combat-audio.js'])
      await page.route(`**/${name}`, route => route.fulfill({ path: path.join(candidate, name), contentType: 'text/javascript' }));
    await page.route('**/assets/combat/*.mp3', route => route.fulfill({ path: path.join(candidate, 'assets/combat', new URL(route.request().url()).pathname.split('/').at(-1)), contentType: 'audio/mpeg' }));
  }
  await page.addInitScript(() => {
    localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, combatSounds: 'recorded', musicVol: 0, sfxVol: 1, weatherAudio: 0 }));
    const bytes = new WeakMap(), labels = new WeakMap(), dest = new WeakMap();
    const fetchOriginal = window.fetch, decode = AudioContext.prototype.decodeAudioData;
    const source = AudioContext.prototype.createBufferSource, oscillator = AudioContext.prototype.createOscillator;
    const connect = AudioNode.prototype.connect;
    window.__soundTap = { starts: [], oscillators: 0 };
    window.fetch = async (...args) => {
      const response = await fetchOriginal(...args), body = response.arrayBuffer.bind(response);
      response.arrayBuffer = async () => { const data = await body(); bytes.set(data, String(args[0]).split('/').at(-1)); return data; };
      return response;
    };
    AudioContext.prototype.decodeAudioData = async function (data) { const b = await decode.call(this, data); labels.set(b, bytes.get(data)); return b; };
    AudioNode.prototype.connect = function (node, ...args) { dest.set(this, node); return connect.call(this, node, ...args); };
    AudioContext.prototype.createOscillator = function () { __soundTap.oscillators++; return oscillator.call(this); };
    AudioContext.prototype.createBufferSource = function () {
      const node = source.call(this), start = node.start;
      node.start = function (...args) {
        const filter = dest.get(node), gain = filter && dest.get(filter);
        __soundTap.starts.push({ cue: labels.get(node.buffer), rate: node.playbackRate.value, cutoff: filter?.frequency?.value, volume: gain?.gain?.value });
        return start.apply(this, args);
      };
      return node;
    };
  });
  await page.goto(info.url); await page.locator('#start').click(); await page.locator('#login-guest').click();
  await page.locator('#cls-priest').click(); await page.locator('#gender-female').click();
  await page.locator('#name').fill('FemaleSoundcheck'); await page.locator('#go').click({ timeout: 60000 });
  await page.waitForFunction(() => Online.connected && RecordedCombat.ready, null, { timeout: 60000 });
  check(await page.evaluate(() => Field.hero.look.gender === 'female'), 'real female priest character');
  // A real death transition, not only a direct sound helper call, selects the female performance.
  await page.evaluate(() => { __soundTap.starts = []; Online.send({ type: 'debug', command: { op: 'die' } }); });
  await page.waitForFunction(() => __soundTap.starts.some(s => s.cue?.startsWith('player-female-death')));
  check(true, 'authoritative female death plays a female recording');
  await page.waitForFunction(() => !Field.hero.dead, null, { timeout: 15000 });
  await page.evaluate(() => Field.stop());
  await page.waitForTimeout(1200);
  const played = await page.evaluate(async () => {
    const tap = __soundTap;
    function play(name, data = {}) { RecordedCombat.stop(); tap.starts = []; const before = tap.oscillators; __combatAudioTest.play(name, data); return { starts: [...tap.starts], oscillators: tap.oscillators - before }; }
    const femaleHurt = play('hurt'), femaleDeath = play('death');
    const variations = [];
    for (let i = 0; i < 12; i++) variations.push(play('hit').starts.at(-1));
    const skillResults = WORLD_SKILLS.map(def => ({ id: def.id, ...play('skill', { skill: def.id }) }));
    const levelup = play('levelup', { level: 99, unlocked: [] });
    RecordedCombat.stop(); tap.starts = []; const before = tap.oscillators; AchievementAudio.play();
    const achievement = { starts: [...tap.starts], oscillators: tap.oscillators - before };
    // Compare the male route while preserving the actual female character state.
    const gender = Field.hero.look.gender; Field.hero.look.gender = 'male';
    const maleHurt = play('hurt'), maleDeath = play('death'); Field.hero.look.gender = gender;
    RecordedCombat.stop();
    return { femaleHurt, femaleDeath, maleHurt, maleDeath, variations, skillResults, levelup, achievement };
  });
  for (const [name, event] of [['female hurt', played.femaleHurt], ['female death', played.femaleDeath]]) {
    check(event.starts.length === 1 && event.starts[0].cue.startsWith('player-female-') && event.oscillators === 0, `${name}: original female recording without synth/male voice`);
  }
  check(played.maleHurt.starts[0].cue.startsWith('player-hurt'), 'male hurt retains male recordings');
  check(played.maleDeath.starts[0].cue.startsWith('player-death'), 'male death retains male recordings');
  const variations = played.variations;
  check(new Set(variations.map(s => s.cue)).size === 3, 'hits select all three alternate performances');
  check(variations.every((s, i) => !i || s.cue !== variations[i-1].cue), 'consecutive hits never repeat the same take');
  for (const key of ['rate', 'volume', 'cutoff']) check(new Set(variations.map(s => s[key])).size > 5, `${key} varies between hits`);
  check(variations.every(s => s.rate >= .92 && s.rate <= 1.08), 'pitch modulation stays subtle');
  check(played.skillResults.length === 50, 'all 50 learned skills checked');
  for (const skill of played.skillResults) check(skill.starts.length === 1 && skill.starts[0].cue?.endsWith('.mp3') && skill.oscillators === 0, `${skill.id}: bundled skill sound replaces synthesis`);
  check(played.levelup.starts[0].cue === 'levelup.mp3' && played.levelup.oscillators === 0, 'level-up uses its own sound');
  check(played.achievement.starts[0].cue === 'achievement.mp3' && played.achievement.oscillators === 0, 'achievement uses a distinct sound');
  const busChecks = await page.evaluate(async () => {
    RecordedCombat.stop();
    const bus = __combatAudioTest.bus(), analyser = bus.context.createAnalyser(); analyser.fftSize = 2048; bus.connect(analyser);
    const samples = new Float32Array(2048);
    async function peak(play) {
      RecordedCombat.stop(); await new Promise(r => setTimeout(r, 100)); play(); let value = 0;
      for (let i = 0; i < 25; i++) { await new Promise(r => setTimeout(r, 10)); analyser.getFloatTimeDomainData(samples); for (const s of samples) value = Math.max(value, Math.abs(s)); }
      return value;
    }
    const audible = await peak(() => __combatAudioTest.play('hurt'));
    Prefs.set({ sfxVol: 0 }); const silent = await peak(() => __combatAudioTest.play('hurt')); Prefs.set({ sfxVol: 1 });
    __combatAudioTest.play('levelup', { level: 99, unlocked: [] }); Prefs.set({ sound: false });
    await new Promise(r => setTimeout(r, 120)); analyser.getFloatTimeDomainData(samples); const muted = Math.max(...samples.map(Math.abs));
    Prefs.set({ sound: true, combatSounds: 'synthesized' }); const before = __soundTap.oscillators; __soundTap.starts = [];
    __combatAudioTest.play('hurt'); const synth = { oscillators: __soundTap.oscillators - before, starts: __soundTap.starts.length };
    return { audible, silent, muted, synth };
  });
  check(busChecks.audible > .004 && busChecks.audible < .95, 'female voice reaches the effects bus without clipping');
  check(busChecks.silent < .001 && busChecks.muted < .001, 'effects slider and mute silence the new recordings');
  check(busChecks.synth.oscillators > 0 && busChecks.synth.starts === 0, 'Synthesized choice still uses synthesis');
  assert.deepEqual(errors, [], 'no browser errors');
  fs.writeFileSync(path.join(world.runDir, 'recorded-audio-checks.json'), JSON.stringify({ checks, played, busChecks }, null, 2));
  console.log(`recorded-audio-variation: ${checks} checks passed; ${world.runDir}`);
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => { if (browser) await browser.close(); await world.stop(); });
