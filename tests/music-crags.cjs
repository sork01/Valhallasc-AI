// The five scores are mp3 files played by music_player.js: they must load and decode with the expected length, play
// audibly, and in a real game the zone must pick the score (meadow tune in Greenmeadow, Ashfall Run in the Crags, Rimeveil Spiral on the glacier, Lanternmere Dusk in Gloamfen).
// Not in npm run test:ui (the user does not want music tested there); run it by hand when the music changes.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-music', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
const SONGS = [
  { id: 'title', make: 'createMusic', seconds: 84.71, name: 'Snowbound Hearth' },
  { id: 'meadow', make: 'createFieldMusic', seconds: 43.64, name: 'Greenmeadow Wander' },
  { id: 'crags', make: 'createCragMusic', seconds: 54.86, name: 'Ashfall Run' },
  { id: 'rime', make: 'createRimeMusic', seconds: 76.8, name: 'Rimeveil Spiral' },
  { id: 'fen', make: 'createFenMusic', seconds: 72.73, name: 'Lanternmere Dusk' },
  { id: 'city', make: 'createCityMusic', seconds: 101.05, name: 'Skaldholm Square' },
  { id: 'wyrd', make: 'createWyrdMusic', seconds: 60.02, name: 'Wyrdwood Wanderings' },
  { id: 'sky', make: 'createSkyMusic', seconds: 91.43, name: 'Above the Storm' },
  { id: 'deep', make: 'createDeepMusic', seconds: 106.67, name: 'Lullaby of the Deep' },
];
(async () => {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const server = await call_start();
  await page.goto(server.url);
  for (const s of SONGS) {
    check(await page.evaluate(k => typeof window[k] === 'function', s.make), `${s.name}: ${s.make} is registered`);
    const r = await page.evaluate(async ({ make }) => {
      const ctx = new OfflineAudioContext(2, 44100 * 6, 44100), m = window[make](ctx);
      const api = ['start', 'stop', 'setLevel', 'duck'].every(k => typeof m[k] === 'function') && m.running === false;
      m.start(); m.setLevel(1, .01);
      for (let i = 0; i < 100 && !m.loaded; i++) await new Promise(r => setTimeout(r, 100));
      const loaded = m.loaded, duration = m.duration;
      const out = await ctx.startRendering(), d = out.getChannelData(0);
      let sum = 0, peak = 0, late = 0; for (let i = 0; i < d.length; i++) { sum += d[i] * d[i]; peak = Math.max(peak, Math.abs(d[i])); if (i > 44100 * 4) late += d[i] * d[i]; }
      return { api, loaded, duration, rms: Math.sqrt(sum / d.length), peak, late: Math.sqrt(late / (d.length - 44100 * 4)) };
    }, { make: s.make });
    check(r.api, `${s.name}: it has the start/stop/setLevel/duck API`);
    check(r.loaded && Math.abs(r.duration - s.seconds) < 1, `${s.name}: the mp3 decodes to ${r.duration.toFixed(1)} s (expected ${s.seconds} s)`);
    check(r.peak > .05 && r.peak < 1, `${s.name}: it plays audibly and unclipped (peak ${r.peak.toFixed(2)})`);
    check(r.late > .005, `${s.name}: it is still sounding after four seconds`);
  }

  // ---- live: the zone picks the score ----
  const world = server;
  const game = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; game.on('pageerror', e => errors.push(e.message));
  await game.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, char: null, draft: null })); });
  await game.goto(world.url); await game.locator('#start').click();
  await game.waitForFunction(() => valhalla.music?.running && valhalla.music.loaded, null, { timeout: 30000 });
  check(true, 'On the title screen the title theme plays');
  await game.locator('#login-guest').click();
  await game.locator('#name').fill('Bard'); await game.locator('#go').click({ timeout: 60000 });
  await game.waitForFunction(() => Online.connected && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  check(await game.evaluate(() => !valhalla.cmusic.running && !valhalla.rmusic.running && !valhalla.gmusic.running && !valhalla.smusic.running && !valhalla.wmusic.running && !valhalla.music.running), 'In Greenmeadow only the meadow tune is running');
  await game.waitForFunction(() => valhalla.fmusic.loaded, null, { timeout: 30000 });
  check(true, 'The meadow mp3 loaded in the game');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 48, y: 86.5 } }));
  await game.waitForFunction(() => Field.zone === 1 && valhalla.cmusic.running && !valhalla.fmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.cmusic.loaded, null, { timeout: 30000 });
  check(true, 'Crossing into the Crags swaps the meadow tune for Ashfall Run, and it loads');
  await game.evaluate(() => { window.levels = []; const set = valhalla.cmusic.setLevel; valhalla.cmusic.setLevel = (v, s) => { levels.push(v); return set.call(valhalla.cmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => levels.length > 0 && Math.abs(levels.at(-1) - .25) < 1e-9), 'The music slider covers the Crags score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => levels.at(-1) === 0), 'Sound off silences it');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // The glacier has its own score: Rimeveil Spiral replaces Ashfall Run, the slider covers it, and the Crags get theirs back.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 2, x: 64, y: 118.5 } }));
  await game.waitForFunction(() => Field.zone === 2 && valhalla.rmusic.running && !valhalla.cmusic.running && !valhalla.fmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.rmusic.loaded, null, { timeout: 30000 });
  check(true, 'Crossing onto the glacier swaps Ashfall Run for Rimeveil Spiral, and it loads');
  await game.evaluate(() => { window.rlevels = []; const set = valhalla.rmusic.setLevel; valhalla.rmusic.setLevel = (v, s) => { rlevels.push(v); return set.call(valhalla.rmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => rlevels.length > 0 && Math.abs(rlevels.at(-1) - .25) < 1e-9), 'The music slider covers the glacier score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => rlevels.at(-1) === 0), 'Sound off silences the glacier score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // Gloamfen has its own score too: Lanternmere Dusk replaces Rimeveil Spiral, the slider covers it, and the glacier gets its own back.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 3, x: 64, y: 9 } }));
  await game.waitForFunction(() => Field.zone === 3 && valhalla.gmusic.running && !valhalla.rmusic.running && !valhalla.cmusic.running && !valhalla.fmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.gmusic.loaded, null, { timeout: 30000 });
  check(true, 'Crossing into Gloamfen swaps Rimeveil Spiral for Lanternmere Dusk, and it loads');
  await game.evaluate(() => { window.glevels = []; const set = valhalla.gmusic.setLevel; valhalla.gmusic.setLevel = (v, s) => { glevels.push(v); return set.call(valhalla.gmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => glevels.length > 0 && Math.abs(glevels.at(-1) - .25) < 1e-9), 'The music slider covers the fen score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => glevels.at(-1) === 0), 'Sound off silences the fen score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // Skaldholm has the fifth score: Skaldholm Square replaces Lanternmere Dusk, and the slider covers it.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 4, x: 80, y: 150 } }));
  await game.waitForFunction(() => Field.zone === 4 && valhalla.smusic.running && !valhalla.gmusic.running && !valhalla.rmusic.running && !valhalla.cmusic.running && !valhalla.fmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.smusic.loaded, null, { timeout: 30000 });
  check(true, 'Crossing into Skaldholm swaps Lanternmere Dusk for Skaldholm Square, and it loads');
  await game.evaluate(() => { window.slevels = []; const set = valhalla.smusic.setLevel; valhalla.smusic.setLevel = (v, s) => { slevels.push(v); return set.call(valhalla.smusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => slevels.length > 0 && Math.abs(slevels.at(-1) - .25) < 1e-9), 'The music slider covers the city score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => slevels.at(-1) === 0), 'Sound off silences the city score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // The Wyrdwood has the seventh score: Wyrdwood Wanderings replaces Skaldholm Square, and the slider covers it.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 6, x: 33, y: 156 } }));
  await game.waitForFunction(() => Field.zone === 6 && valhalla.wmusic.running && !valhalla.smusic.running && !valhalla.cmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.wmusic.loaded, null, { timeout: 30000 });
  check(true, 'Crossing into the Wyrdwood swaps Skaldholm Square for Wyrdwood Wanderings, and it loads');
  await game.evaluate(() => { window.wlevels = []; const set = valhalla.wmusic.setLevel; valhalla.wmusic.setLevel = (v, s) => { wlevels.push(v); return set.call(valhalla.wmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => wlevels.length > 0 && Math.abs(wlevels.at(-1) - .25) < 1e-9), 'The music slider covers the Wyrdwood score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => wlevels.at(-1) === 0), 'Sound off silences the Wyrdwood score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // Bifrost Reach has the eighth score: Above the Storm replaces Wyrdwood Wanderings, and the slider covers it.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 7, x: 80, y: 144 } }));
  await game.waitForFunction(() => Field.zone === 7 && valhalla.kmusic.running && !valhalla.wmusic.running && !valhalla.smusic.running && !valhalla.cmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.kmusic.loaded, null, { timeout: 30000 });
  check(true, 'Climbing into Bifrost Reach swaps Wyrdwood Wanderings for Above the Storm, and it loads');
  await game.evaluate(() => { window.klevels = []; const set = valhalla.kmusic.setLevel; valhalla.kmusic.setLevel = (v, s) => { klevels.push(v); return set.call(valhalla.kmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => klevels.length > 0 && Math.abs(klevels.at(-1) - .25) < 1e-9), 'The music slider covers the Bifrost score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => klevels.at(-1) === 0), 'Sound off silences the Bifrost score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  // Ran's Deep has the ninth score, in a different style (a slow lullaby): it replaces Above the Storm and the slider covers it.
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 8, x: 80, y: 160 } }));
  await game.waitForFunction(() => Field.zone === 8 && valhalla.dmusic.running && !valhalla.kmusic.running && !valhalla.wmusic.running, null, { timeout: 10000 });
  await game.waitForFunction(() => valhalla.dmusic.loaded, null, { timeout: 30000 });
  check(true, 'Diving into Ran\'s Deep swaps Above the Storm for Lullaby of the Deep, and it loads');
  await game.evaluate(() => { window.dlevels = []; const set = valhalla.dmusic.setLevel; valhalla.dmusic.setLevel = (v, s) => { dlevels.push(v); return set.call(valhalla.dmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => dlevels.length > 0 && Math.abs(dlevels.at(-1) - .25) < 1e-9), 'The music slider covers the Deep score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => dlevels.at(-1) === 0), 'Sound off silences the Deep score');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 7, x: 103.5, y: 32.4 } }));
  await game.waitForFunction(() => Field.zone === 7 && valhalla.kmusic.running && !valhalla.dmusic.running, null, { timeout: 10000 });
  check(true, 'Climbing back out of the Maelstrom returns Above the Storm');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 6, x: 33, y: 156 } }));
  await game.waitForFunction(() => Field.zone === 6 && valhalla.wmusic.running && !valhalla.kmusic.running, null, { timeout: 10000 });
  check(true, 'Back in the Wyrdwood its own score returns');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 2, x: 64, y: 118.5 } }));
  await game.waitForFunction(() => Field.zone === 2 && valhalla.rmusic.running && !valhalla.gmusic.running, null, { timeout: 10000 });
  check(true, 'Back on the glacier Rimeveil Spiral returns');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 48, y: 86.5 } }));
  await game.waitForFunction(() => Field.zone === 1 && valhalla.cmusic.running && !valhalla.rmusic.running, null, { timeout: 10000 });
  check(true, 'Back in the Crags Ashfall Run returns');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 36, y: 60 } }));
  await game.waitForFunction(() => Field.zone === 0 && valhalla.fmusic.running && !valhalla.cmusic.running && !valhalla.rmusic.running, null, { timeout: 10000 });
  check(true, 'Walking back out returns the meadow tune');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} music checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
async function call_start() {
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true; return world;
}
