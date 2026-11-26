// Exercise the actual music selection code with the shipped recording wrappers.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const manifest = JSON.parse(fs.readFileSync('scripts/soundtrack-filedrop.txt', 'utf8'));
const sandbox = { console, Map, setInterval() {}, scene: 'game', ensureWeatherSound() {},
  save: { sound: true, musicVol: .35 }, taper: v => v * v };
sandbox.window = sandbox;
const context = { state: 'running', currentTime: 0, addEventListener() {} };
sandbox.audio = () => context;
sandbox.ac = context;
sandbox.createMusicTransition = () => () => {};
sandbox.createLoopMusic = (_ctx, url) => ({ url, setLevel(value) { this.level = value; }, running: false });
for (const file of fs.readdirSync('client').filter(f => /^music(?:_[a-z]+)*\.js$/.test(f) && !['music_player.js', 'music_intro.js'].includes(f))) {
  let wrapper = fs.readFileSync('client/' + file, 'utf8');
  if (process.env.MUTATE === 'asterion' && file === 'music_asterion.js') wrapper = wrapper.replace('music_asterion.mp3', 'music_city.mp3');
  vm.runInNewContext(wrapper, sandbox);
}
let source = fs.readFileSync('client/game.js', 'utf8');
if (process.env.MUTATE === 'moonwell') source = source.replace('musicZone === 18 && moonwellMusic ? moonwellMusic', 'musicZone === 18 && mmusic ? mmusic');
const start = source.indexOf('  let music = null, fmusic');
const end = source.indexOf('\n', source.indexOf('  function duckMusic(', start));
vm.runInNewContext(source.slice(start, end) + `
  ensureMusic();
  this.route = (zone, night = false, final = false) => {
    scene = 'game'; musicZone = zone; raidFinalFight = final; syncMusic();
    return (night ? activeNightMusic : activeScore)?.url;
  };
  this.volume = () => moonwellMusic?.level;
`, sandbox);
let checks = 0;
for (const track of manifest.tracks) {
  if (!track.zones.length) continue;
  const night = track.slot.endsWith('_night');
  for (const zone of track.zones) {
    const url = sandbox.route(zone, night, track.slot === 'eldmarr');
    assert.equal(url?.split('?')[0], `assets/music_${track.slot}.mp3`, `${track.title} routes to zone ${zone}`);
    if (!track.already_installed) assert.ok(url.includes('?v=saga-' + (track.asset_version || '1.15.4')), `${track.slot}: new recording bypasses the old cached asset`);
    checks++;
  }
}
assert.equal(sandbox.route(46), 'assets/music_chained_forge.mp3?v=saga-1.15.4', 'ordinary raid uses its new FileDrop recording');
assert.equal(sandbox.route(46, false, true), 'assets/music_eldmarr.mp3?v=saga-1.15.6', 'final raid encounter uses the remade Eldmarr score');
assert.equal(sandbox.route(999, true), 'assets/music_night.mp3?v=saga-1.15.6', 'an uncovered zone selects the remade shared fallback');
assert.equal(sandbox.volume(), .35 ** 2, 'Moonwell music uses the saved channel volume');
sandbox.save.sound = false; sandbox.route(18); assert.equal(sandbox.volume(), 0, 'mute reaches the new player');
console.log(`PASS soundtrack-routing: ${checks} recording/zone mappings, raid/final encounter routing, Moonwell volume/mute and cache versions`);
