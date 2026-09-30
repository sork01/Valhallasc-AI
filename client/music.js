'use strict';
/* Background music for Valhalla Rumble: "Snowbound Hearth".
   A generative-but-fixed score synthesised with WebAudio (no audio files): a slow Nordic-meets-Korean
   theme in D minor (pentatonic melody with sigimsae-style slides, drone + fifth, warm pad, a plucked
   gayageum/kantele voice made with Karplus-Strong, quiet harp arpeggios, frame drum, wind, fire crackle
   and icy bell sparkles). 68 BPM, an 8-bar (about 28 s) loop; layers enter over the first loops.
   API: const m = createMusic(ctx); m.start(); m.setLevel(0..1, seconds); m.duck(seconds); m.stop();
   m.renderOffline(seconds) schedules everything at once for an OfflineAudioContext (used by tests). */
(() => {
  const BPM = 68, BEAT = 60 / BPM, STEP = BEAT / 2, LOOP_STEPS = 64;
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);

  // chord changes: [step within loop, length in steps, bass root, pad notes]
  const CHORDS = [
    [0, 16, 38, [50, 57, 60, 64, 65]],    // Dm9   (D3 A3 C4 E4 F4)
    [16, 16, 34, [46, 53, 57, 62]],       // Bbmaj7
    [32, 16, 41, [53, 57, 60, 64]],       // Fmaj7
    [48, 8, 43, [55, 58, 62, 65]],        // Gm7
    [56, 8, 45, [52, 57, 62, 64]],        // Asus4, pulls back to Dm
  ];
  // melody: [beat, midi, length in beats, slide-from midi or 0]   (D minor pentatonic + Bb/E colour)
  const MELODY = [
    [0, 69, 1.5, 0], [1.5, 72, .5, 0], [2, 74, 2, 72],
    [4, 72, 1, 0], [5, 69, 1, 0], [6, 65, 2, 67],
    [8, 70, 1.5, 0], [9.5, 69, .5, 0], [10, 65, 2, 0],
    [12, 62, 1, 0], [13, 65, 1, 0], [14, 69, 2, 67],
    [16, 72, 1.5, 0], [17.5, 69, .5, 0], [18, 65, 1, 0], [19, 69, 1, 0],
    [20, 72, 2, 70], [22, 76, 1, 0], [23, 74, 1, 0],
    [24, 70, 1.5, 0], [25.5, 67, .5, 0], [26, 62, 2, 0],
    [28, 69, 1, 0], [29, 67, .5, 0], [29.5, 69, .5, 0], [30, 74, 2, 72],
  ];
  const HARP_PAT = [0, 2, 1, 3, 2, 1, 3, 1];          // eighth-note arpeggio over the chord tones
  const SPARKLE = [86, 89, 91, 93, 96];                // D6 F6 G6 A6 C7

  function createMusic(ctx) {
    let seed = 7;
    const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    const sr = ctx.sampleRate;

    // ---- signal chain: dry/wet buses -> master -> compressor -> output ----
    const master = ctx.createGain(); master.gain.value = 0;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 3; comp.attack.value = .02; comp.release.value = .4;
    master.connect(comp); comp.connect(ctx.destination);
    const reverb = ctx.createConvolver();
    {
      const len = Math.floor(sr * 3.4), ir = ctx.createBuffer(2, len, sr);
      for (let c = 0; c < 2; c++) {
        const d = ir.getChannelData(c); let lp = 0;
        for (let i = 0; i < len; i++) { lp += (((rnd() * 2 - 1)) - lp) * .35; d[i] = lp * Math.pow(1 - i / len, 2.6); }
      }
      reverb.buffer = ir;
    }
    const wetGain = ctx.createGain(); wetGain.gain.value = .55;
    reverb.connect(wetGain); wetGain.connect(master);
    const bus = wet => { const g = ctx.createGain(); g.connect(master); if (wet > 0) { const s = ctx.createGain(); s.gain.value = wet; g.connect(s); s.connect(reverb); } return g; };
    const buses = { pad: bus(.5), bass: bus(.1), pluck: bus(.42), harp: bus(.5), drum: bus(.25), bell: bus(.9), amb: bus(.2) };

    // ---- sample material generated once ----
    const noise = (() => { const b = ctx.createBuffer(1, sr * 4, sr), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd() * 2 - 1; return b; })();
    const plucks = new Map();
    function pluckBuffer(midi) {                      // Karplus-Strong string
      if (plucks.has(midi)) return plucks.get(midi);
      const f = hz(midi), N = Math.max(2, Math.round(sr / f - .5)), len = Math.floor(sr * 3.6);   // the averaging filter adds half a sample of delay
      const buf = ctx.createBuffer(1, len, sr), y = buf.getChannelData(0);
      let lp = 0;
      for (let i = 0; i < N; i++) { lp += ((rnd() * 2 - 1) - lp) * .6; y[i] = lp; }          // softened noise burst = round, woody pluck
      for (let i = N; i < len; i++) y[i] = (y[i - N] + (i > N ? y[i - N - 1] : 0)) * .5 * .9975;
      let pk = 0; for (let i = 0; i < len; i++) pk = Math.max(pk, Math.abs(y[i]));
      const k = .8 / (pk || 1); for (let i = 0; i < len; i++) y[i] *= k;
      buf.tune = f / (sr / (N + .5));                                 // playbackRate that corrects the integer-delay tuning error
      plucks.set(midi, buf); return buf;
    }

    // ---- voices ----
    function pluck(t, midi, vel, len, slideFrom, dest) {
      const s = ctx.createBufferSource(), buf = pluckBuffer(midi); s.buffer = buf;
      if (slideFrom) { s.playbackRate.setValueAtTime(buf.tune * Math.pow(2, (slideFrom - midi) / 12), t); s.playbackRate.linearRampToValueAtTime(buf.tune, t + .09); }
      else s.playbackRate.value = buf.tune;
      const g = ctx.createGain(); g.gain.setValueAtTime(vel, t);
      g.gain.setTargetAtTime(0.0001, t + len, .45);                // let long notes ring, short ones damp
      s.connect(g); g.connect(dest); s.start(t); s.stop(t + 3.5);
    }
    function padNote(t, midi, dur, vel) {
      const g = ctx.createGain(), f = ctx.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = 1000; f.Q.value = .3;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + 1.8); g.gain.setValueAtTime(vel, t + dur - .3); g.gain.linearRampToValueAtTime(0, t + dur + 2.2);
      for (const [type, det] of [['triangle', -7], ['sine', 6], ['triangle', 0]]) {
        const o = ctx.createOscillator(); o.type = type; o.frequency.value = hz(midi); o.detune.value = det;
        o.connect(f); o.start(t); o.stop(t + dur + 2.4);
      }
      f.connect(g); g.connect(buses.pad);
    }
    function bassNote(t, midi, dur) {
      const o = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter();
      o.type = 'sine'; o.frequency.value = hz(midi); f.type = 'lowpass'; f.frequency.value = 400;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.055, t + .4); g.gain.setValueAtTime(.055, t + dur - .5); g.gain.linearRampToValueAtTime(0, t + dur + .3);
      o.connect(f); f.connect(g); g.connect(buses.bass); o.start(t); o.stop(t + dur + .4);
    }
    function drum(t, vel) {                                        // soft frame drum
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine'; o.frequency.setValueAtTime(130, t); o.frequency.exponentialRampToValueAtTime(52, t + .22);
      g.gain.setValueAtTime(.28 * vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .5);
      o.connect(g); g.connect(buses.drum); o.start(t); o.stop(t + .55);
      const n = ctx.createBufferSource(), nf = ctx.createBiquadFilter(), ng = ctx.createGain();
      n.buffer = noise; nf.type = 'bandpass'; nf.frequency.value = 900; nf.Q.value = .8;
      ng.gain.setValueAtTime(.16 * vel, t); ng.gain.exponentialRampToValueAtTime(.0001, t + .09);
      n.connect(nf); nf.connect(ng); ng.connect(buses.drum); n.start(t, rnd() * 2, .12);
    }
    function bell(t, midi, vel) {                                  // icy chime: inharmonic partials
      const g = ctx.createGain(); g.gain.setValueAtTime(vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + 3.2);
      for (const [ratio, a] of [[1, 1], [2.76, .45], [5.4, .2], [8.9, .08]]) {
        const o = ctx.createOscillator(), og = ctx.createGain(); o.type = 'sine'; o.frequency.value = hz(midi) * ratio; og.gain.value = a;
        o.connect(og); og.connect(g); o.start(t); o.stop(t + 3.3);
      }
      g.connect(buses.bell);
    }
    function crackle(t) {
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; f.type = 'highpass'; f.frequency.value = 1800 + rnd() * 2500;
      g.gain.setValueAtTime(.05 * (.3 + rnd()), t); g.gain.exponentialRampToValueAtTime(.0001, t + .012 + rnd() * .02);
      n.connect(f); f.connect(g); g.connect(buses.amb); n.start(t, rnd() * 3, .05);
    }
    const sustained = [];                                          // drone / wind: started once, stopped with stop()
    function drone(t) {
      for (const [midi, vel, type, cut] of [[38, .02, 'sine', 0], [45, .012, 'sine', 0], [50, .012, 'sawtooth', 260]]) {
        const o = ctx.createOscillator(), g = ctx.createGain(); o.type = type; o.frequency.value = hz(midi); g.gain.value = vel;
        let node = o; if (cut) { const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = cut; o.connect(f); node = f; }
        const lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value = .09 + rnd() * .05; lg.gain.value = vel * .35; lfo.connect(lg); lg.connect(g.gain);
        node.connect(g); g.connect(buses.bass); o.start(t); lfo.start(t); sustained.push(o, lfo);
      }
      // wind
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; n.loop = true; f.type = 'bandpass'; f.frequency.value = 520; f.Q.value = .9; g.gain.value = .03;
      const l1 = ctx.createOscillator(), l1g = ctx.createGain(); l1.frequency.value = .06; l1g.gain.value = 260; l1.connect(l1g); l1g.connect(f.frequency);
      const l2 = ctx.createOscillator(), l2g = ctx.createGain(); l2.frequency.value = .045; l2g.gain.value = .018; l2.connect(l2g); l2g.connect(g.gain);
      n.connect(f); f.connect(g); g.connect(buses.amb); n.start(t); l1.start(t); l2.start(t); sustained.push(n, l1, l2);
    }

    // ---- sequencing ----
    let t0 = 0, step = 0, timer = 0, running = false, level = 1, duckUntil = 0;
    const melodyAt = new Map(); for (const ev of MELODY) melodyAt.set(Math.round(ev[0] * 2), ev);
    function chordAt(s) { return CHORDS.find(c => s >= c[0] && s < c[0] + c[1]); }

    function scheduleStep(s) {
      const t = t0 + s * STEP, ls = s % LOOP_STEPS, bar = Math.floor(s / 8);
      const ch = chordAt(ls);
      if (ls === ch[0]) {                                            // a new chord: pad + bass
        const dur = ch[1] * STEP;
        ch[3].forEach((m, i) => padNote(t + i * .04, m, dur, .036 - i * .003));
        bassNote(t, ch[2], dur);
      }
      if (bar >= 2 && melodyAt.has(ls)) { const [, m, len, from] = melodyAt.get(ls); pluck(t, m, .8, len * BEAT, from, buses.pluck); }
      if (bar >= 8) {                                                // second loop on: harp arpeggio and drum
        const ct = ch[3];
        pluck(t, ct[HARP_PAT[ls % 8] % ct.length] + 12, .16, .3, 0, buses.harp);
        if (ls % 8 === 0) drum(t, 1); else if (ls % 8 === 4) drum(t, .55); else if (ls % 16 === 7) drum(t, .3);
      }
      if (rnd() < .07 && bar >= 1) bell(t + rnd() * STEP, SPARKLE[Math.floor(rnd() * SPARKLE.length)], .07 + rnd() * .04);
      if (rnd() < .28) crackle(t + rnd() * STEP);
    }
    function scheduleUntil(limit) { while (t0 + step * STEP < limit) scheduleStep(step++); }

    function applyLevel(t, secs) {
      const target = running ? level * (t < duckUntil ? .4 : 1) * .55 : 0;
      master.gain.cancelScheduledValues(t); master.gain.setValueAtTime(master.gain.value, t); master.gain.linearRampToValueAtTime(target, t + secs);
    }
    return {
      start() {
        if (running) return; running = true;
        t0 = ctx.currentTime + .15; step = 0; seed = 7;
        drone(t0); applyLevel(ctx.currentTime, 4);
        scheduleUntil(ctx.currentTime + .8);
        timer = setInterval(() => scheduleUntil(ctx.currentTime + .8), 150);
      },
      stop() {
        if (!running) return; running = false; clearInterval(timer);
        applyLevel(ctx.currentTime, 1.2);
        const old = sustained.splice(0);                                // only this run's nodes: a quick restart must not lose its own
        setTimeout(() => old.forEach(n => { try { n.stop(); } catch (e) { /* already stopped */ } }), 1500);
      },
      setLevel(v, secs = 1.5) { level = v; if (running) applyLevel(ctx.currentTime, secs); },
      duck(secs = 2.5) {                                              // dip under a sound effect (the horn)
        if (!running) return; const now = ctx.currentTime; duckUntil = now + secs; applyLevel(now, .15);
        setTimeout(() => applyLevel(ctx.currentTime, 1.2), secs * 1000);
      },
      get running() { return running; },
      _pluck: pluckBuffer,                                            // exposed for tests
      // for tests: schedule the whole piece up front into an OfflineAudioContext
      renderOffline(seconds) { running = true; t0 = .05; step = 0; seed = 7; drone(t0); master.gain.value = .55; scheduleUntil(seconds); },
    };
  }
  window.createMusic = createMusic;
})();
