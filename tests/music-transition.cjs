// Audio-clock simulation: exercise the shipped player and game routing without a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const window = {};
let player = fs.readFileSync('client/music_player.js', 'utf8');
if (process.env.MUTATE) player = player.replace('quietAt = now + FADE_OUT', 'quietAt = now');
vm.runInNewContext(player, { window });
const ctx = { currentTime: 0, state: 'running' };
const events = [], tracks = [];
function track(name) {
  const m = { name, running: false, audibleUntil: 0, level: 0,
    start() {
      assert.ok(tracks.every(t => t === m || (!t.running && t.audibleUntil <= ctx.currentTime)), `${name} overlaps an outgoing fade`);
      this.running = true; events.push(['start', name, ctx.currentTime]);
    },
    stop() { this.running = false; this.audibleUntil = ctx.currentTime + 1.2; events.push(['stop', name, ctx.currentTime]); },
    setLevel(value) { this.level = value; }
  };
  tracks.push(m); return m;
}
const day = track('day'), night = track('night'), indoor = track('indoor'), title = track('title');
const sandbox = { window, ac: ctx, scene: 'game', musicZone: 0, nightScores: new Map([[0, night]]),
  activeScore: day, activeNightMusic: night, music: title, musicTransition: null,
  save: { sound: true, musicVol: .8 }, cutsceneScore: null, taper: v => v*v };
let mix = 0;
window.DayNight = { getNightMix: () => mix };
const game = fs.readFileSync('client/game.js', 'utf8');
const start = game.indexOf('  function musicNightMix()');
const end = game.indexOf('  setInterval(syncNightMusic', start);
vm.createContext(sandbox);
vm.runInContext(game.slice(start, end), sandbox);
function tick(time) { ctx.currentTime = time; sandbox.syncNightMusic(); }
tick(0); assert.equal(day.running, true);
mix = .49; tick(3); assert.equal(night.running, false);
mix = .5; tick(4); assert.equal(day.running, false); assert.equal(night.running, false);
tick(5.19); assert.equal(night.running, false, 'full fade must finish');
tick(5.21); assert.equal(night.running, true);
mix = .1; tick(8); assert.equal(night.running, false); assert.equal(day.running, false);
tick(9.21); assert.equal(day.running, true, 'dawn returns to day after silence');
// Change destination twice while fading. Only the latest selection may start.
mix = 1; tick(12);
sandbox.activeScore = indoor; mix = 0; tick(12.3);
sandbox.scene = 'title'; tick(12.6);
tick(13.21); assert.equal(title.running, true); assert.equal(indoor.running, false); assert.equal(night.running, false);
// Audio suspension keeps currentTime frozen, even after wall time passes.
sandbox.scene = 'game'; tick(15);
ctx.state = 'suspended'; tick(15); assert.equal(day.running, false);
ctx.state = 'running'; tick(16.21); assert.equal(indoor.running, true);
// Volume and mute must apply equally, with no remaining day/night blend factors.
const levelStart = game.indexOf('  function applyMusicLevel(');
const levelEnd = game.indexOf('  // Dip every field score', levelStart);
const levelCode = game.slice(levelStart, levelEnd);
const names = [...new Set(levelCode.match(/\b\w*(?:music|Music)\b/g))];
for (const name of names) if (!(name in sandbox)) sandbox[name] = null;
sandbox.cathedralMusic = []; sandbox.fmusic = day; sandbox.nightMusic = night;
vm.runInContext(levelCode, sandbox);
sandbox.applyMusicLevel(0); assert.ok(Math.abs(day.level - .64) < 1e-8); assert.equal(day.level, night.level);
sandbox.save.sound = false; sandbox.applyMusicLevel(0); assert.equal(day.level, 0); assert.equal(night.level, 0);
sandbox.save.sound = true; sandbox.save.musicVol = .3; sandbox.applyMusicLevel(0); assert.equal(day.level, .09);
assert.ok(!game.slice(game.indexOf('  function syncMusic()'), start).includes('.start()'), 'all score starts must go through the transition');
console.log('Music transitions: dusk, dawn, fade ordering, rapid travel, suspension, mute and volume passed');
