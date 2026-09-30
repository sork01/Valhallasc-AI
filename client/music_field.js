'use strict';
/* Music for the first map: "Greenmeadow Wander".
   A sunny, lilting folk tune in G major, 6/8 at 88 (dotted-quarter) BPM, 32 bars (about 44 s) that loop.
   Pass 1 (bars 1-16): plucked kantele-style lead, harp arpeggios, plucked bass, a light shaker.
   Pass 2 (bars 17-32): the same tune on a breathy flute with a string pad, hand drum and claps.
   Birdsong and a soft breeze sit on top. Everything is synthesised with WebAudio (no audio files).
   Same API as createMusic in music.js: start(), stop(), setLevel(v, secs), duck(secs), renderOffline(seconds). */
(() => {
  const BPM = 88, STEP = 60 / BPM / 3, BAR = 6, LOOP_BARS = 32;         // 6 eighth-note steps per bar
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);

  // one entry per bar of a 16-bar tune: bass note, chord tones (low to high)
  const G = [43, [55, 59, 62, 67]], D_F = [42, [57, 62, 66, 69]], EM = [40, [55, 59, 64, 67]], C = [48, [52, 55, 60, 64]];
  const D = [38, [57, 62, 66, 69]], AM = [45, [57, 60, 64, 69]], BM = [47, [54, 59, 62, 66]], D7 = [38, [57, 60, 62, 66]];
  const CHORDS = [G, D_F, EM, C, G, D, C, D, EM, BM, C, G, AM, D, G, D7];
  // melody: per bar [step in bar, midi, length in steps]
  const MELODY = [
    [[0, 67, 3], [3, 71, 1], [4, 74, 1], [5, 71, 1]],
    [[0, 74, 3], [3, 72, 1], [4, 71, 1], [5, 69, 1]],
    [[0, 71, 2], [2, 74, 1], [3, 76, 3]],
    [[0, 76, 3], [3, 74, 1], [4, 72, 1], [5, 74, 1]],
    [[0, 71, 3], [3, 74, 1], [4, 79, 2]],
    [[0, 78, 3], [3, 76, 1], [4, 74, 1], [5, 72, 1]],
    [[0, 71, 2], [2, 72, 1], [3, 74, 3]],
    [[0, 74, 3], [3, 71, 1], [4, 69, 1], [5, 67, 1]],
    [[0, 76, 3], [3, 79, 3]],
    [[0, 78, 3], [3, 74, 1], [4, 78, 1], [5, 74, 1]],
    [[0, 76, 3], [3, 72, 1], [4, 76, 2]],
    [[0, 74, 3], [3, 71, 1], [4, 67, 1], [5, 71, 1]],
    [[0, 72, 3], [3, 76, 1], [4, 72, 1], [5, 69, 1]],
    [[0, 69, 2], [2, 74, 1], [3, 78, 3]],
    [[0, 79, 4], [4, 74, 1], [5, 71, 1]],
    [[0, 69, 3], [3, 72, 1], [4, 74, 2]],
  ];
  const ARP = [0, 1, 2, 3, 2, 1];

  function createFieldMusic(ctx) {
    let seed = 11;
    const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    const sr = ctx.sampleRate;

    const master = ctx.createGain(); master.gain.value = 0;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 3; comp.attack.value = .02; comp.release.value = .4;
    master.connect(comp); comp.connect(ctx.destination);
    const reverb = ctx.createConvolver();
    {
      const len = Math.floor(sr * 2.2), ir = ctx.createBuffer(2, len, sr);
      for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); let lp = 0; for (let i = 0; i < len; i++) { lp += ((rnd() * 2 - 1) - lp) * .5; d[i] = lp * Math.pow(1 - i / len, 2.8); } }
      reverb.buffer = ir;
    }
    const wet = ctx.createGain(); wet.gain.value = .5; reverb.connect(wet); wet.connect(master);
    const bus = w => { const g = ctx.createGain(); g.connect(master); if (w > 0) { const s = ctx.createGain(); s.gain.value = w; g.connect(s); s.connect(reverb); } return g; };
    const B = { lead: bus(.3), flute: bus(.4), harp: bus(.35), bass: bus(.05), drum: bus(.12), perc: bus(.1), pad: bus(.5), bird: bus(.7), amb: bus(.2) };

    const noise = (() => { const b = ctx.createBuffer(1, sr * 4, sr), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd() * 2 - 1; return b; })();
    // percussion hits are baked once (filtered noise with an envelope) so each hit costs one source and one gain
    function bake(dur, hp, lp, decay) {
      const len = Math.floor(sr * dur), b = ctx.createBuffer(1, len, sr), d = b.getChannelData(0), a = Math.exp(-2 * Math.PI * hp / sr), c = Math.exp(-2 * Math.PI * lp / sr);
      let l1 = 0, l2 = 0;
      for (let i = 0; i < len; i++) { const x = rnd() * 2 - 1; l1 = c * l1 + (1 - c) * x; l2 = a * l2 + (1 - a) * l1; d[i] = (l1 - l2) * Math.exp(-decay * i / len); }
      let pk = 0; for (let i = 0; i < len; i++) pk = Math.max(pk, Math.abs(d[i])); for (let i = 0; i < len; i++) d[i] /= (pk || 1);
      return b;
    }
    const HIT = { shaker: bake(.05, 4000, 15000, 5), clap: bake(.12, 900, 3500, 6), tick: bake(.07, 350, 2500, 5) };
    function hit(t, buf, vol, dest) { const s = ctx.createBufferSource(), g = ctx.createGain(); s.buffer = buf; g.gain.value = vol; s.connect(g); g.connect(dest); s.start(t); }
    const plucks = new Map();
    function pluckBuffer(midi, bright) {                              // Karplus-Strong string, tuned exactly through playbackRate
      const key = midi + (bright ? 1000 : 0); if (plucks.has(key)) return plucks.get(key);
      const f = hz(midi), N = Math.max(2, Math.round(sr / f - .5)), len = Math.floor(sr * 2.6), buf = ctx.createBuffer(1, len, sr), y = buf.getChannelData(0);
      let lp = 0; for (let i = 0; i < N; i++) { lp += ((rnd() * 2 - 1) - lp) * (bright ? .9 : .55); y[i] = lp; }
      const decay = bright ? .9965 : .998;
      for (let i = N; i < len; i++) y[i] = (y[i - N] + (i > N ? y[i - N - 1] : 0)) * .5 * decay;
      let pk = 0; for (let i = 0; i < len; i++) pk = Math.max(pk, Math.abs(y[i])); const k = .8 / (pk || 1); for (let i = 0; i < len; i++) y[i] *= k;
      buf.tune = f / (sr / (N + .5)); plucks.set(key, buf); return buf;
    }
    function pluck(t, midi, vel, hold, dest, bright) {
      const s = ctx.createBufferSource(), buf = pluckBuffer(midi, bright); s.buffer = buf; s.playbackRate.value = buf.tune;
      const g = ctx.createGain(); g.gain.setValueAtTime(vel, t); g.gain.setTargetAtTime(.0001, t + hold, .35);
      s.connect(g); g.connect(dest); s.start(t); s.stop(t + 1.8);
    }
    function flute(t, midi, dur, vel) {                               // breathy flute: sine + a little 2nd harmonic, delayed vibrato, breath noise
      const g = ctx.createGain(), f = hz(midi);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .07); g.gain.setValueAtTime(vel * .9, t + Math.max(.1, dur - .12)); g.gain.linearRampToValueAtTime(0, t + dur + .12);
      const lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value = 5.2; lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(7, t + .35); lfo.connect(lg);   // vibrato in cents
      for (const [mul, a] of [[1, 1], [2, .16]]) {
        const o = ctx.createOscillator(), og = ctx.createGain(); o.type = 'sine'; o.frequency.value = f * mul; og.gain.value = a; lg.connect(o.detune); o.connect(og); og.connect(g); o.start(t); o.stop(t + dur + .2);
      }
      lfo.start(t); lfo.stop(t + dur + .2);
      const n = ctx.createBufferSource(), nf = ctx.createBiquadFilter(), ng = ctx.createGain();
      n.buffer = noise; nf.type = 'bandpass'; nf.frequency.value = Math.min(6000, f * 3.2); nf.Q.value = 1.4; ng.gain.setValueAtTime(0, t); ng.gain.linearRampToValueAtTime(vel * .16, t + .05); ng.gain.linearRampToValueAtTime(0, t + dur + .1);
      n.connect(nf); nf.connect(ng); ng.connect(g); n.start(t, rnd() * 2, dur + .2);
      g.connect(B.flute);
    }
    function bass(t, midi, vel) {                                     // round plucked bass
      const o = ctx.createOscillator(), o2 = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter();
      o.type = 'triangle'; o.frequency.value = hz(midi); o2.type = 'sine'; o2.frequency.value = hz(midi) * 2; f.type = 'lowpass'; f.frequency.setValueAtTime(900, t); f.frequency.exponentialRampToValueAtTime(260, t + .4);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .012); g.gain.exponentialRampToValueAtTime(.0001, t + .7);
      const g2 = ctx.createGain(); g2.gain.value = .25; o2.connect(g2); g2.connect(f); o.connect(f); f.connect(g); g.connect(B.bass); o.start(t); o2.start(t); o.stop(t + .75); o2.stop(t + .75);
    }
    function padChord(t, tones, dur, vel) {                           // soft strings
      const g = ctx.createGain(), f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 1300; f.Q.value = .3;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .6); g.gain.setValueAtTime(vel, t + dur - .2); g.gain.linearRampToValueAtTime(0, t + dur + 1.2);
      tones.forEach((m, i) => { for (const [type, det] of [['sawtooth', -7], ['triangle', 7]]) { const o = ctx.createOscillator(); o.type = type; o.frequency.value = hz(m + 12 * (i > 1 ? 0 : 0)); o.detune.value = det; o.connect(f); o.start(t + i * .03); o.stop(t + dur + 1.3); } });
      f.connect(g); g.connect(B.pad);
    }
    function drum(t, vel) {
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(70, t + .16);
      g.gain.setValueAtTime(.26 * vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .35); o.connect(g); g.connect(B.drum); o.start(t); o.stop(t + .4);
      hit(t, HIT.tick, .2 * vel, B.drum);
    }
    function noiseHit(t, freq, q, vol, dur, dest, type = 'bandpass') {
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; f.type = type; f.frequency.value = freq; f.Q.value = q; g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
      n.connect(f); f.connect(g); g.connect(dest); n.start(t, rnd() * 2.5, dur + .02);
    }
    function bird(t) {                                                // a quick trill of rising chirps
      const base = 2600 + rnd() * 1500, n = 2 + Math.floor(rnd() * 4), gap = .07 + rnd() * .05;
      for (let i = 0; i < n; i++) {
        const o = ctx.createOscillator(), g = ctx.createGain(), s = t + i * gap;
        o.type = 'sine'; o.frequency.setValueAtTime(base, s); o.frequency.exponentialRampToValueAtTime(base * (1.3 + rnd() * .3), s + .05);
        g.gain.setValueAtTime(0, s); g.gain.linearRampToValueAtTime(.022, s + .01); g.gain.exponentialRampToValueAtTime(.0001, s + .06);
        o.connect(g); g.connect(B.bird); o.start(s); o.stop(s + .08);
      }
    }
    const sustained = [];
    function breeze(t) {
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; n.loop = true; f.type = 'bandpass'; f.frequency.value = 900; f.Q.value = .7; g.gain.value = .02;
      const l1 = ctx.createOscillator(), l1g = ctx.createGain(); l1.frequency.value = .07; l1g.gain.value = 420; l1.connect(l1g); l1g.connect(f.frequency);
      const l2 = ctx.createOscillator(), l2g = ctx.createGain(); l2.frequency.value = .05; l2g.gain.value = .012; l2.connect(l2g); l2g.connect(g.gain);
      n.connect(f); f.connect(g); g.connect(B.amb); n.start(t); l1.start(t); l2.start(t); sustained.push(n, l1, l2);
    }

    // ---- sequencing: one call per eighth-note step ----
    let t0 = 0, step = 0, timer = 0, running = false, level = 1, duckUntil = 0, skip = new Set();
    function scheduleStep(s) {
      const t = t0 + s * STEP, bar = Math.floor(s / BAR), sb = s % BAR, pass = Math.floor(bar / 16) % 2, b16 = bar % 16, ch = CHORDS[b16];
      const tones = ch[1];
      // bass on the two dotted-quarter pulses
      if (!skip.has('bass') && sb === 0) bass(t, ch[0], .2);
      if (!skip.has('bass') && sb === 3) bass(t, tones[2] - 12, .13);
      // harp arpeggio, quieter (and an octave up) on the flute pass
      if (!skip.has('harp')) pluck(t, tones[ARP[sb]] + (pass ? 12 : 0), pass ? .07 : .11, .25, B.harp, false);
      // melody
      for (const [ls, m, len] of MELODY[b16]) if (ls === sb) {
        if (!pass) { if (!skip.has('lead')) pluck(t, m, .9, len * STEP, B.lead, true); }
        else if (!skip.has('flute')) flute(t, m, len * STEP * .96, .16);
      }
      if (pass && sb === 0 && !skip.has('pad')) padChord(t, tones.slice(0, 3), BAR * STEP, .024);
      // percussion
      if (!skip.has('perc') && (bar >= 4 || pass)) { const acc = sb === 0 ? 1 : sb === 3 ? .7 : .35; hit(t, HIT.shaker, .06 * acc * (pass ? 1.3 : 1), B.perc); }
      if (!skip.has('drum') && (pass || bar >= 8) && sb === 0) drum(t, .9);
      if (!skip.has('drum') && (pass || bar >= 8) && sb === 3) drum(t, .45);
      if (!skip.has('drum') && pass && sb === 3) hit(t, HIT.clap, .11, B.perc);
      if (!skip.has('bird') && rnd() < .012) bird(t + rnd() * STEP);
    }
    function scheduleUntil(limit) { while (t0 + step * STEP < limit) scheduleStep(step++); }
    function applyLevel(t, secs) {
      const target = running ? level * (t < duckUntil ? .4 : 1) * .55 : 0;
      master.gain.cancelScheduledValues(t); master.gain.setValueAtTime(master.gain.value, t); master.gain.linearRampToValueAtTime(target, t + secs);
    }
    return {
      start() {
        if (running) return; running = true; t0 = ctx.currentTime + .15; step = 0; seed = 11;
        breeze(t0); applyLevel(ctx.currentTime, 2.5);
        scheduleUntil(ctx.currentTime + .8); timer = setInterval(() => scheduleUntil(ctx.currentTime + .8), 150);
      },
      stop() {
        if (!running) return; running = false; clearInterval(timer); applyLevel(ctx.currentTime, 1.2);
        const old = sustained.splice(0);                                // only this run's nodes: a quick restart must not lose its own
        setTimeout(() => old.forEach(n => { try { n.stop(); } catch (e) { /* already stopped */ } }), 1500);
      },
      setLevel(v, secs = 1.5) { level = v; if (running) applyLevel(ctx.currentTime, secs); },
      duck(secs = 2.5) { if (!running) return; const now = ctx.currentTime; duckUntil = now + secs; applyLevel(now, .15); setTimeout(() => applyLevel(ctx.currentTime, 1.2), secs * 1000); },
      get running() { return running; },
      _pluck: pluckBuffer,
      renderOffline(seconds, off) { skip = new Set(off || []); running = true; t0 = .05; step = 0; seed = 11; if (!skip.has('breeze')) breeze(t0); master.gain.value = .55; scheduleUntil(seconds); },
    };
  }
  window.createFieldMusic = createFieldMusic;
})();
