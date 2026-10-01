'use strict';
/* Music for the Emberfall Crags: "Ashfall Run".
   Dark but driving: E minor with a Phrygian F and a major B chord that drags every phrase back to E, 4/4 at 140 BPM,
   32 bars (about 55 s) that loop. Pass 1 (bars 1-16): kick, off-beat gallop bass, a bright arpeggio and a hushed lead.
   Pass 2 (bars 17-32): four-on-the-floor with snare and clap, sixteenth hats, a snarling doubled lead through an echo,
   chord stabs and a low pad. Toms and a snare roll mark the end of every eight bars. A lava rumble and ember crackle sit
   underneath. Everything is synthesised with WebAudio (no audio files).
   Same API as createFieldMusic in music_field.js: start(), stop(), setLevel(v, secs), duck(secs), renderOffline(seconds). */
(() => {
  const BPM = 140, STEP = 60 / BPM / 4, BAR = 16, LOOP_BARS = 32;       // 16 sixteenth-note steps per bar
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);

  // one entry per bar of a 16-bar tune: bass root, chord tones (an octave around middle C)
  const EM = [40, [64, 67, 71]], F = [41, [65, 69, 72]], G = [43, [67, 71, 74]], C = [36, [60, 64, 67]];
  const D = [38, [62, 66, 69]], B = [35, [59, 63, 66]];
  const CHORDS = [EM, EM, F, EM, EM, G, F, B, EM, C, D, EM, C, D, F, B];
  // melody: per bar [step in bar, midi, length in steps]
  const MELODY = [
    [[0, 76, 3], [3, 79, 1], [4, 76, 2], [6, 74, 2], [8, 76, 4], [12, 71, 2], [14, 74, 2]],
    [[0, 76, 2], [2, 79, 2], [4, 83, 4], [8, 81, 2], [10, 79, 2], [12, 76, 4]],
    [[0, 77, 3], [3, 76, 1], [4, 72, 4], [8, 77, 2], [10, 81, 2], [12, 77, 4]],
    [[0, 76, 6], [6, 74, 2], [8, 71, 4], [12, 69, 2], [14, 71, 2]],
    [[0, 76, 3], [3, 79, 1], [4, 83, 4], [8, 81, 2], [10, 79, 2], [12, 76, 2], [14, 79, 2]],
    [[0, 79, 3], [3, 74, 1], [4, 79, 2], [6, 83, 2], [8, 86, 4], [12, 83, 2], [14, 79, 2]],
    [[0, 77, 3], [3, 81, 1], [4, 84, 4], [8, 81, 2], [10, 77, 2], [12, 76, 4]],
    [[0, 75, 3], [3, 78, 1], [4, 83, 2], [6, 81, 2], [8, 78, 4], [12, 75, 2], [14, 78, 2]],
    [[0, 83, 3], [3, 79, 1], [4, 76, 4], [8, 79, 2], [10, 83, 2], [12, 88, 4]],
    [[0, 84, 3], [3, 83, 1], [4, 79, 4], [8, 76, 2], [10, 79, 2], [12, 84, 4]],
    [[0, 81, 3], [3, 78, 1], [4, 74, 4], [8, 78, 2], [10, 81, 2], [12, 86, 4]],
    [[0, 83, 4], [4, 79, 2], [6, 76, 2], [8, 79, 4], [12, 76, 4]],
    [[0, 79, 3], [3, 84, 1], [4, 88, 4], [8, 86, 2], [10, 84, 2], [12, 79, 4]],
    [[0, 81, 3], [3, 86, 1], [4, 86, 4], [8, 81, 2], [10, 78, 2], [12, 74, 4]],
    [[0, 77, 3], [3, 76, 1], [4, 77, 2], [6, 81, 2], [8, 84, 4], [12, 81, 4]],
    [[0, 78, 2], [2, 75, 2], [4, 78, 2], [6, 83, 2], [8, 75, 8]],
  ];
  const ARP = [0, 1, 2, 3, 2, 1, 2, 3, 0, 1, 2, 3, 2, 1, 3, 2];
  const TOMS = [165, 138, 112, 92];

  function createCragMusic(ctx) {
    let seed = 23;
    const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
    const sr = ctx.sampleRate;

    const master = ctx.createGain(); master.gain.value = 0;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 3; comp.attack.value = .02; comp.release.value = .4;
    master.connect(comp); comp.connect(ctx.destination);
    const reverb = ctx.createConvolver();
    {
      const len = Math.floor(sr * 1.8), ir = ctx.createBuffer(2, len, sr);
      for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); let lp = 0; for (let i = 0; i < len; i++) { lp += ((rnd() * 2 - 1) - lp) * .3; d[i] = lp * Math.pow(1 - i / len, 3); } }
      reverb.buffer = ir;
    }
    const wet = ctx.createGain(); wet.gain.value = .45; reverb.connect(wet); wet.connect(master);
    const bus = w => { const g = ctx.createGain(); g.connect(master); if (w > 0) { const s = ctx.createGain(); s.gain.value = w; g.connect(s); s.connect(reverb); } return g; };
    const B = { lead: bus(.25), arp: bus(.3), bass: bus(.02), kick: bus(0), snare: bus(.18), hat: bus(.05), tom: bus(.2), stab: bus(.3), pad: bus(.5), amb: bus(.2) };
    // a dotted-eighth echo for the lead (three sixteenths), darkened on every repeat
    const echoIn = ctx.createGain(); echoIn.gain.value = .0; B.lead.connect(echoIn);
    const echo = ctx.createDelay(1), echoFb = ctx.createGain(), echoTone = ctx.createBiquadFilter();
    echo.delayTime.value = STEP * 3; echoFb.gain.value = .34; echoTone.type = 'lowpass'; echoTone.frequency.value = 2400;
    echoIn.connect(echo); echo.connect(echoTone); echoTone.connect(echoFb); echoFb.connect(echo); echoTone.connect(master); echoTone.connect(reverb);

    const noise = (() => { const b = ctx.createBuffer(1, sr * 4, sr), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd() * 2 - 1; return b; })();
    // percussion noise is baked once (filtered, with an envelope) so each hit costs one source and one gain
    function bake(dur, hp, lp, decay) {
      const len = Math.floor(sr * dur), b = ctx.createBuffer(1, len, sr), d = b.getChannelData(0), a = Math.exp(-2 * Math.PI * hp / sr), c = Math.exp(-2 * Math.PI * lp / sr);
      let l1 = 0, l2 = 0;
      for (let i = 0; i < len; i++) { const x = rnd() * 2 - 1; l1 = c * l1 + (1 - c) * x; l2 = a * l2 + (1 - a) * l1; d[i] = (l1 - l2) * Math.exp(-decay * i / len); }
      let pk = 0; for (let i = 0; i < len; i++) pk = Math.max(pk, Math.abs(d[i])); for (let i = 0; i < len; i++) d[i] /= (pk || 1);
      return b;
    }
    const HIT = { hat: bake(.04, 6500, 16000, 7), open: bake(.22, 6000, 16000, 4), snare: bake(.2, 1200, 7000, 5), clap: bake(.14, 1000, 4000, 7), tick: bake(.015, 2500, 12000, 4) };
    function hit(t, buf, vol, dest) { const s = ctx.createBufferSource(), g = ctx.createGain(); s.buffer = buf; g.gain.value = vol; s.connect(g); g.connect(dest); s.start(t); }

    function kick(t, vel) {
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(150, t); o.frequency.exponentialRampToValueAtTime(44, t + .13);
      g.gain.setValueAtTime(.7 * vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .32); o.connect(g); g.connect(B.kick); o.start(t); o.stop(t + .36);
      hit(t, HIT.tick, .22 * vel, B.kick);
    }
    function snare(t, vel, clap) {
      hit(t, HIT.snare, .3 * vel, B.snare);
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'triangle'; o.frequency.setValueAtTime(230, t); o.frequency.exponentialRampToValueAtTime(150, t + .09);
      g.gain.setValueAtTime(.22 * vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .13); o.connect(g); g.connect(B.snare); o.start(t); o.stop(t + .16);
      if (clap) hit(t + .004, HIT.clap, .16 * vel, B.snare);
    }
    function tom(t, freq, vel) {
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(freq * 1.5, t); o.frequency.exponentialRampToValueAtTime(freq, t + .08);
      g.gain.setValueAtTime(.4 * vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .3); o.connect(g); g.connect(B.tom); o.start(t); o.stop(t + .34);
    }
    function bass(t, midi, vel, len) {                                 // saw and a square sub through a plucking lowpass
      const o = ctx.createOscillator(), o2 = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter();
      o.type = 'sawtooth'; o.frequency.value = hz(midi); o2.type = 'square'; o2.frequency.value = hz(midi - 12);
      f.type = 'lowpass'; f.Q.value = 3; f.frequency.setValueAtTime(1400, t); f.frequency.exponentialRampToValueAtTime(170, t + len);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .006); g.gain.setValueAtTime(vel, t + len * .6); g.gain.exponentialRampToValueAtTime(.0001, t + len + .05);
      const g2 = ctx.createGain(); g2.gain.value = .45; o2.connect(g2); g2.connect(f); o.connect(f); f.connect(g); g.connect(B.bass);
      o.start(t); o2.start(t); o.stop(t + len + .08); o2.stop(t + len + .08);
    }
    function arp(t, midi, vel) {                                        // a short square pluck
      const o = ctx.createOscillator(), o2 = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter();
      o.type = 'square'; o.frequency.value = hz(midi); o2.type = 'triangle'; o2.frequency.value = hz(midi + 12); o2.detune.value = 5;
      f.type = 'lowpass'; f.frequency.setValueAtTime(3600, t); f.frequency.exponentialRampToValueAtTime(700, t + .12);
      g.gain.setValueAtTime(vel, t); g.gain.exponentialRampToValueAtTime(.0001, t + .15);
      const g2 = ctx.createGain(); g2.gain.value = .3; o2.connect(g2); g2.connect(f); o.connect(f); f.connect(g); g.connect(B.arp);
      o.start(t); o2.start(t); o.stop(t + .18); o2.stop(t + .18);
    }
    function lead(t, midi, dur, vel, snarl) {                           // detuned saws; pass 2 adds an octave-down layer and opens the filter
      const g = ctx.createGain(), f = ctx.createBiquadFilter(), f0 = hz(midi);
      f.type = 'lowpass'; f.Q.value = snarl ? 2.5 : .6; f.frequency.setValueAtTime(snarl ? 4200 : 1500, t); f.frequency.exponentialRampToValueAtTime(snarl ? 1700 : 900, t + Math.max(.12, dur * .8));
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .012); g.gain.setValueAtTime(vel * .85, t + Math.max(.05, dur - .08)); g.gain.linearRampToValueAtTime(0, t + dur + .06);
      const lfo = ctx.createOscillator(), lg = ctx.createGain(); lfo.frequency.value = 5.6; lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(11, t + .3); lfo.connect(lg);   // vibrato in cents
      const voices = snarl ? [['sawtooth', -9, 1, 1], ['sawtooth', 9, 1, 1], ['sawtooth', 0, .5, .7]] : [['sawtooth', -6, 1, 1], ['triangle', 6, 1, .8]];
      for (const [type, det, mul, a] of voices) {
        const o = ctx.createOscillator(), og = ctx.createGain(); o.type = type; o.frequency.value = f0 * mul; o.detune.value = det; og.gain.value = a; lg.connect(o.detune); o.connect(og); og.connect(f); o.start(t); o.stop(t + dur + .1);
      }
      lfo.start(t); lfo.stop(t + dur + .1);
      f.connect(g); g.connect(B.lead);
    }
    function stab(t, tones, vel) {                                      // a short brassy chord
      const g = ctx.createGain(), f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = 1.2; f.frequency.setValueAtTime(2600, t); f.frequency.exponentialRampToValueAtTime(600, t + .16);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .008); g.gain.exponentialRampToValueAtTime(.0001, t + .2);
      for (const m of tones) for (const det of [-8, 8]) { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = hz(m - 12); o.detune.value = det; o.connect(f); o.start(t); o.stop(t + .24); }
      f.connect(g); g.connect(B.stab);
    }
    function pad(t, tones, dur, vel) {                                  // low, dark strings
      const g = ctx.createGain(), f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 800; f.Q.value = .3;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vel, t + .5); g.gain.setValueAtTime(vel, t + dur - .15); g.gain.linearRampToValueAtTime(0, t + dur + .9);
      tones.forEach((m, i) => { for (const [type, det] of [['sawtooth', -7], ['triangle', 7]]) { const o = ctx.createOscillator(); o.type = type; o.frequency.value = hz(m - 12); o.detune.value = det; o.connect(f); o.start(t + i * .02); o.stop(t + dur + 1); } });
      f.connect(g); g.connect(B.pad);
    }
    function ember(t) {                                                 // a spit of ember
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; f.type = 'highpass'; f.frequency.value = 2200 + rnd() * 3000; g.gain.setValueAtTime(.05 * (.3 + rnd()), t); g.gain.exponentialRampToValueAtTime(.0001, t + .01 + rnd() * .02);
      n.connect(f); f.connect(g); g.connect(B.amb); n.start(t, rnd() * 3, .05);
    }
    const sustained = [];
    function rumble(t) {                                                // lava: low noise swelling slowly, plus a sub drone on E
      const n = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
      n.buffer = noise; n.loop = true; f.type = 'lowpass'; f.frequency.value = 160; f.Q.value = .8; g.gain.value = .07;
      const l = ctx.createOscillator(), lg = ctx.createGain(); l.frequency.value = .08; lg.gain.value = .035; l.connect(lg); lg.connect(g.gain);
      n.connect(f); f.connect(g); g.connect(B.amb); n.start(t); l.start(t);
      const o = ctx.createOscillator(), og = ctx.createGain(); o.type = 'sine'; o.frequency.value = hz(28); og.gain.value = .05; o.connect(og); og.connect(B.amb); o.start(t);
      sustained.push(n, l, o);
    }

    // ---- sequencing: one call per sixteenth-note step ----
    let t0 = 0, step = 0, timer = 0, running = false, level = 1, duckUntil = 0, skip = new Set();
    function scheduleStep(s) {
      const t = t0 + s * STEP, bar = Math.floor(s / BAR), sb = s % BAR, pass = Math.floor(bar / 16) % 2, b16 = bar % 16, ch = CHORDS[b16], tones = ch[1], odd = b16 % 2 === 1;
      const intro = !pass && b16 < 2, fillBar = b16 === 7 || b16 === 15, rollBar = pass && b16 === 15;
      // bass: eighth notes, an octave pop on the off-beats of odd bars; off for the tom fill's last beat
      if (!skip.has('bass') && sb % 2 === 0 && !(fillBar && sb >= 12)) bass(t, ch[0] + (odd && (sb === 6 || sb === 14) ? 12 : 0), sb % 8 === 0 ? .17 : .12, STEP * 1.7);
      // arpeggio: from the third bar on in pass 1, an octave higher and brighter in pass 2
      if (!skip.has('arp') && (pass || b16 >= 2)) arp(t, [tones[0], tones[1], tones[2], tones[0] + 12][ARP[sb] % 4] + (pass ? 12 : 0), pass ? .045 : .05);
      // lead
      for (const [ls, m, len] of MELODY[b16]) if (ls === sb && !skip.has('lead')) lead(t, m, len * STEP * .94, pass ? .085 : .06, !!pass);
      // stabs and pad: pass 2 only
      if (pass && !skip.has('stab') && (sb === 0 || sb === 6 || sb === 10)) stab(t, tones, sb === 0 ? .07 : .05);
      if (pass && !skip.has('pad') && sb === 0) pad(t, tones, BAR * STEP, .03);
      // drums
      if (!skip.has('drum')) {
        if (intro) { if (sb === 0 || sb === 8) kick(t, .9); }
        else {
          if (sb % 4 === 0 && !(rollBar && sb >= 8)) kick(t, sb === 0 ? 1 : .85);
          if (pass && odd && sb === 10) kick(t, .7);
          if ((sb === 4 || sb === 12) && !rollBar) snare(t, 1, !!pass);
          if (rollBar && sb >= 8) snare(t, .45 + (sb - 8) * .09, true);
        }
        if (fillBar && sb >= 12 && !rollBar) tom(t, TOMS[sb - 12], 1 - (sb - 12) * .1);
        if (pass) { if (!(rollBar && sb >= 8)) hit(t, HIT.hat, sb % 4 === 2 ? .1 : sb % 2 === 0 ? .07 : .035, B.hat); if (sb === 14 && odd && !rollBar) hit(t, HIT.open, .09, B.hat); }
        else if (!intro && sb % 2 === 0) hit(t, HIT.hat, sb % 4 === 2 ? .08 : .05, B.hat);
      }
      if (!skip.has('ember') && rnd() < .1) ember(t + rnd() * STEP);
    }
    function applyLevel(t, secs) {
      const target = running ? level * (t < duckUntil ? .4 : 1) * .55 : 0;
      master.gain.cancelScheduledValues(t); master.gain.setValueAtTime(master.gain.value, t); master.gain.linearRampToValueAtTime(target, t + secs);
    }
    // the echo only joins in pass 2, when the lead snarls
    function echoFor(s) { echoIn.gain.setValueAtTime(Math.floor(s / (BAR * 16)) % 2 ? .26 : 0, t0 + s * STEP); }
    function scheduleAll(limit) { while (t0 + step * STEP < limit) { if (step % (BAR * 16) === 0) echoFor(step); scheduleStep(step++); } }
    return {
      start() {
        if (running) return; running = true; t0 = ctx.currentTime + .15; step = 0; seed = 23;
        rumble(t0); applyLevel(ctx.currentTime, 2.5);
        scheduleAll(ctx.currentTime + .8); timer = setInterval(() => scheduleAll(ctx.currentTime + .8), 150);
      },
      stop() {
        if (!running) return; running = false; clearInterval(timer); applyLevel(ctx.currentTime, 1.2);
        const old = sustained.splice(0);                                // only this run's nodes: a quick restart must not lose its own
        setTimeout(() => old.forEach(n => { try { n.stop(); } catch (e) { /* already stopped */ } }), 1500);
      },
      setLevel(v, secs = 1.5) { level = v; if (running) applyLevel(ctx.currentTime, secs); },
      duck(secs = 2.5) { if (!running) return; const now = ctx.currentTime; duckUntil = now + secs; applyLevel(now, .15); setTimeout(() => applyLevel(ctx.currentTime, 1.2), secs * 1000); },
      get running() { return running; },
      renderOffline(seconds, off) { skip = new Set(off || []); running = true; t0 = .05; step = 0; seed = 23; if (!skip.has('rumble')) rumble(t0); master.gain.value = .55; scheduleAll(seconds); },
    };
  }
  window.createCragMusic = createCragMusic;
})();
