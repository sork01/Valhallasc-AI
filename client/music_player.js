'use strict';
/* Looping music from an mp3 for Valhalla Rumble. The three scores (title, meadow, Crags) are written in dybase2 and
   played from client/assets/music_*.mp3; this file is the one player they share.
   API: const m = createLoopMusic(ctx, url); m.start(); m.setLevel(0..1, seconds); m.duck(seconds); m.stop();
   m.running tells whether it is meant to be playing, m.loaded whether the file has been decoded.
   The file is fetched and decoded on first use. A song that cannot load is silent, never an error, and is retried on
   the next start(). Each play gets its own fade gain, so a quick stop and start never lets the old run back up. */
(() => {
  const FADE_IN = 2.5, FADE_OUT = 1.2;
  function createLoopMusic(ctx, url) {
    const master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
    let buffer = null, loading = null, voice = null, running = false, level = 1, duckUntil = 0;

    function load() {
      if (buffer) return Promise.resolve(buffer);
      if (!loading) loading = fetch(url)
        .then(r => { if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.arrayBuffer(); })
        .then(data => ctx.decodeAudioData(data))
        .then(b => (buffer = b))
        .catch(e => { loading = null; console.warn('music not loaded', e.message || e); return null; });
      return loading;
    }
    function play() {
      if (!running || voice || !buffer) return;
      const now = ctx.currentTime, gain = ctx.createGain(), source = ctx.createBufferSource();
      source.buffer = buffer; source.loop = true;
      gain.gain.setValueAtTime(0, now); gain.gain.linearRampToValueAtTime(1, now + FADE_IN);
      source.connect(gain); gain.connect(master); source.start(now + .05);
      voice = { source, gain };
    }
    function release(v) {
      const now = ctx.currentTime;
      v.gain.gain.cancelScheduledValues(now); v.gain.gain.setValueAtTime(v.gain.gain.value, now); v.gain.gain.linearRampToValueAtTime(0, now + FADE_OUT);
      setTimeout(() => { try { v.source.stop(); } catch (e) { /* already stopped */ } v.gain.disconnect(); }, (FADE_OUT + .3) * 1000);
    }
    function applyLevel(t, secs) {
      const target = level * (t < duckUntil ? .4 : 1);
      master.gain.cancelScheduledValues(t); master.gain.setValueAtTime(master.gain.value, t); master.gain.linearRampToValueAtTime(target, t + secs);
    }
    return {
      start() { if (running) return; running = true; applyLevel(ctx.currentTime, .1); load().then(play); },
      stop() { if (!running) return; running = false; if (voice) { release(voice); voice = null; } },
      setLevel(v, secs = 1.5) { level = v; applyLevel(ctx.currentTime, secs); },
      duck(secs = 2.5) {                                              // dip under a sound effect (the horn)
        if (!running) return; const now = ctx.currentTime; duckUntil = now + secs; applyLevel(now, .15);
        setTimeout(() => applyLevel(ctx.currentTime, 1.2), secs * 1000);
      },
      get running() { return running; },
      get loaded() { return !!buffer; },
      get output() { return master; },                                // the node wired to the speakers (tests tell it from the effects bus)
      get duration() { return buffer ? buffer.duration : 0; },
    };
  }
  window.createLoopMusic = createLoopMusic;
})();
