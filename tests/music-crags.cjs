// "Ashfall Run", the Crags score: measured offline (tempo, key, darkness, loudness, build) and then live in a real
// game, where it must replace the meadow tune on crossing into the Crags and hand it back on the way out.
const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport, getDefaultEnvironment } = require('@modelcontextprotocol/sdk/client/stdio.js');
const root = path.resolve(__dirname, '..');
const client = new Client({ name: 'valhallasc-music-crags', version: '1.0.0' });
let browser, started = false, checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
async function call(name, args = {}) {
  const result = await client.callTool({ name, arguments: args });
  assert.ok(!result.isError, `${name}: ${JSON.stringify(result.content)}`); return result.structuredContent;
}
// Everything below runs in the page: render a score offline and measure it.
async function measure(page) {
  return page.evaluate(async () => {
    const SR = 22050, BPM = 140, STEP = 60 / BPM / 4;
    const render = async (make, seconds, off) => {
      const ctx = new OfflineAudioContext(1, SR * seconds, SR), m = make(ctx); m.renderOffline(seconds, off);
      return (await ctx.startRendering()).getChannelData(0);
    };
    const rms = (x, a = 0, b = x.length) => { let s = 0; for (let i = a; i < b; i++) s += x[i] * x[i]; return Math.sqrt(s / Math.max(1, b - a)); };
    const finite = x => { for (let i = 0; i < x.length; i++) if (!Number.isFinite(x[i])) return false; return true; };
    const peak = x => { let p = 0; for (let i = 0; i < x.length; i++) p = Math.max(p, Math.abs(x[i])); return p; };
    // a plain radix-2 FFT magnitude
    function fft(re) {
      const n = re.length, im = new Float64Array(n);
      for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; } }
      for (let len = 2; len <= n; len <<= 1) {
        const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
        for (let i = 0; i < n; i += len) { let cr = 1, ci = 0; for (let k = 0; k < len / 2; k++) {
          const a = i + k, b = a + len / 2, tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
          re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti; const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr; } }
      }
      return Float64Array.from(re.slice(0, n / 2), (v, i) => Math.hypot(v, im[i]));
    }
    // spectrum summed over a window: centroid (Hz), share of energy under 200 Hz, and a chroma over 80 Hz - 2 kHz
    function spectrum(x, from, to) {
      const N = 4096, acc = new Float64Array(N / 2), win = Float64Array.from({ length: N }, (_, i) => .5 - .5 * Math.cos(2 * Math.PI * i / N));
      for (let p = from; p + N <= to; p += N) { const mag = fft(Float64Array.from({ length: N }, (_, i) => x[p + i] * win[i])); for (let k = 0; k < N / 2; k++) acc[k] += mag[k] * mag[k]; }
      let num = 0, den = 0, low = 0; const chroma = new Float64Array(12);
      for (let k = 1; k < N / 2; k++) {
        const f = k * SR / N; num += f * acc[k]; den += acc[k]; if (f < 200) low += acc[k];
        if (f >= 80 && f <= 2000) chroma[(Math.round(12 * Math.log2(f / 440)) + 69) % 12] += acc[k];
      }
      return { centroid: num / den, low: low / den, chroma: Array.from(chroma, v => v / (chroma.reduce((a, b) => a + b, 0) || 1)) };
    }
    const barSamples = b => Math.round(b * 16 * STEP * SR);
    const loop = Math.ceil(32 * 16 * STEP) + 1;
    const crag = await render(c => createCragMusic(c), loop, []);
    const meadow = await render(c => createFieldMusic(c), 45, []);
    const drums = await render(c => createCragMusic(c), 16, ['bass', 'arp', 'lead', 'stab', 'pad', 'ember', 'rumble']);
    const tonal = await render(c => createCragMusic(c), loop, ['drum', 'bass', 'ember', 'rumble']);
    // drum onsets in bars 3-6 of pass 1: smoothed envelope, strongest hits only
    const env = new Float64Array(Math.floor(drums.length / 110)); for (let i = 0; i < env.length; i++) env[i] = rms(drums, i * 110, i * 110 + 110);
    const from = Math.floor(barSamples(2) / 110), to = Math.floor(barSamples(6) / 110), top = Math.max(...env.slice(from, to)), onsets = [];
    for (let i = from + 1; i < to; i++) if (env[i] > top * .45 && env[i] >= env[i - 1] && env[i] > env[i + 1] && (!onsets.length || (i - onsets.at(-1)) * 110 / SR > .15)) onsets.push(i);
    const gaps = onsets.slice(1).map((v, i) => (v - onsets[i]) * 110 / SR).sort((a, b) => a - b);
    const first = spectrum(crag, 0, barSamples(8)), second = spectrum(crag, barSamples(16), barSamples(24));
    return {
      finite: finite(crag), peak: peak(crag), rms: rms(crag), meadowRms: rms(meadow),
      pass1: rms(crag, barSamples(2), barSamples(14)), pass2: rms(crag, barSamples(18), barSamples(30)),
      onsets: onsets.length, medianGap: gaps[Math.floor(gaps.length / 2)], beat: 60 / BPM,
      crag: spectrum(crag, barSamples(2), barSamples(30)), meadow: spectrum(meadow, SR, SR * 40), tonal: spectrum(tonal, 0, barSamples(32)),
      first: first.centroid, second: second.centroid, tail: rms(crag, crag.length - SR, crag.length),
    };
  });
}
(async () => {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('about:blank');
  await page.addScriptTag({ path: path.join(root, 'client/music_field.js') });
  await page.addScriptTag({ path: path.join(root, 'client/music_crags.js') });
  check(await page.evaluate(() => typeof createCragMusic === 'function'), 'The Crags score registers createCragMusic');
  const api = await page.evaluate(() => { const c = new OfflineAudioContext(1, 4410, 22050), m = createCragMusic(c); return ['start', 'stop', 'setLevel', 'duck', 'renderOffline'].every(k => typeof m[k] === 'function') && m.running === false; });
  check(api, 'It has the same API as the other scores');
  const m = await measure(page);
  check(m.finite && m.peak > .05 && m.peak < .99, `Rendered audio is finite, audible and unclipped (peak ${m.peak.toFixed(2)})`);
  check(m.rms / m.meadowRms > .6 && m.rms / m.meadowRms < 2, `Its loudness sits beside the meadow tune (${(m.rms / m.meadowRms).toFixed(2)}x)`);
  check(m.onsets >= 12 && Math.abs(m.medianGap - m.beat) < .02, `The drums land on a 140 BPM beat (${m.onsets} hits, median gap ${m.medianGap.toFixed(3)} s vs ${m.beat.toFixed(3)} s)`);
  check(m.pass2 > m.pass1 * 1.1, `The second half builds (${m.pass1.toFixed(3)} to ${m.pass2.toFixed(3)} RMS)`);
  check(m.crag.centroid < m.meadow.centroid, `It is darker than the meadow tune (centroid ${Math.round(m.crag.centroid)} Hz vs ${Math.round(m.meadow.centroid)} Hz)`);
  check(m.crag.low > m.meadow.low * 1.5, `It carries far more low end (${(m.crag.low * 100).toFixed(0)}% under 200 Hz vs ${(m.meadow.low * 100).toFixed(0)}%)`);
  const pc = m.tonal.chroma, name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const ranked = pc.map((v, i) => [v, name[i]]).sort((a, b) => b[0] - a[0]).map(x => x[1]);
  check(ranked.slice(0, 4).includes('E') && ranked.slice(0, 5).includes('G') && ranked.slice(0, 5).includes('B'), `The pitches centre on the E minor triad (top five: ${ranked.slice(0, 5).join(' ')})`);
  check(pc[7] > pc[8] * 3, `It is minor: G is ${(pc[7] / pc[8]).toFixed(1)}x stronger than G sharp`);
  check(m.tail > 0, 'The loop ends with sound, ready to wrap round');

  // ---- live: the zone picks the score ----
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [path.join(root, 'scripts/test-mcp.cjs')], cwd: root, stderr: 'pipe', env: { ...getDefaultEnvironment(), VALHALLA_LEVEL_SPREAD: '0' } }));
  const world = await call('start_world'); started = true;
  const game = await browser.newPage({ viewport: { width: 1280, height: 800 }, reducedMotion: 'reduce' });
  const errors = []; game.on('pageerror', e => errors.push(e.message));
  await game.addInitScript(() => { if (!localStorage.getItem('valhallasc.save.v1')) localStorage.setItem('valhallasc.save.v1', JSON.stringify({ lang: 'en', sound: true, char: null, draft: null })); });
  await game.goto(world.url); await game.locator('#start').click(); await game.locator('#login-guest').click();
  await game.locator('#name').fill('Bard'); await game.locator('#go').click({ timeout: 60000 });
  await game.waitForFunction(() => Online.connected && !!valhalla.fmusic?.running, null, { timeout: 60000 });
  check(await game.evaluate(() => !valhalla.cmusic.running), 'In Greenmeadow the Crags score is silent and the meadow tune plays');
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 1, x: 48, y: 86.5 } }));
  await game.waitForFunction(() => Field.zone === 1 && valhalla.cmusic.running && !valhalla.fmusic.running, null, { timeout: 10000 });
  check(true, 'Crossing into the Crags swaps the meadow tune for Ashfall Run');
  await game.evaluate(() => { window.levels = []; const set = valhalla.cmusic.setLevel; valhalla.cmusic.setLevel = (v, s) => { levels.push(v); return set.call(valhalla.cmusic, v, s); }; });
  await game.evaluate(() => Prefs.set({ musicVol: .5 }));
  check(await game.evaluate(() => levels.length > 0 && Math.abs(levels.at(-1) - .25) < 1e-9), 'The music slider covers the Crags score too (50% = 0.25 gain)');
  await game.evaluate(() => Prefs.set({ sound: false }));
  check(await game.evaluate(() => levels.at(-1) === 0), 'Sound off silences it');
  await game.evaluate(() => Prefs.set({ sound: true, musicVol: 1 }));
  await game.evaluate(() => Online.send({ type: 'debug', command: { op: 'teleport', zone: 0, x: 36, y: 60 } }));
  await game.waitForFunction(() => Field.zone === 0 && valhalla.fmusic.running && !valhalla.cmusic.running, null, { timeout: 10000 });
  check(true, 'Walking back out returns the meadow tune');
  check(errors.length === 0, `No browser runtime errors: ${errors.join('; ')}`);
  console.log(`${checks} Crags music checks passed`);
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  await browser?.close();
  if (started) await call('stop_world').catch(() => {});
  await client.close().catch(() => {});
});
