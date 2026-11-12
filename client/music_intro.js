'use strict';
// A finite score follows the cutscene clock, including late downloads and tab resumes.
// Each run owns its nodes so a cancelled download can never revive a skipped intro.
(() => {
  window.createCutsceneMusic = (ctx, url, elapsed) => {
    const output = ctx.createGain(); output.gain.value = 0; output.connect(ctx.destination);
    let buffer = null, voice = null, running = false, serial = 0, level = 0;
    const loading = fetch(url).then(r => {
      if (!r.ok) throw Error('Cutscene score unavailable');
      return r.arrayBuffer();
    }).then(bytes => ctx.decodeAudioData(bytes)).then(b => (buffer = b)).catch(() => null);
    function release() {
      if (!voice) return;
      const old = voice; voice = null;
      old.gain.gain.cancelScheduledValues(ctx.currentTime);
      old.gain.gain.setValueAtTime(old.gain.gain.value, ctx.currentTime);
      old.gain.gain.linearRampToValueAtTime(0, ctx.currentTime + .18);
      old.source.stop(ctx.currentTime + .2);
    }
    async function sync() {
      const token = ++serial;
      await loading;
      if (!running || token !== serial || !buffer || ctx.state !== 'running') return;
      release();
      const offset = Math.max(0, elapsed());
      if (offset >= buffer.duration) return;
      const source = ctx.createBufferSource(), gain = ctx.createGain();
      source.buffer = buffer; source.loop = false;
      gain.gain.setValueAtTime(0, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(1, ctx.currentTime + .25);
      source.connect(gain); gain.connect(output);
      const run = { source, gain, offset }; voice = run;
      source.onended = () => { source.disconnect(); gain.disconnect(); if (voice === run) voice = null; };
      source.start(ctx.currentTime, offset);
    }
    const stateChange = () => { if (ctx.state === 'running' && running) sync(); };
    ctx.addEventListener('statechange', stateChange);
    return {
      url,
      start() { if (running) return; running = true; sync(); },
      stop() {
        running = false; serial++; release();
        ctx.removeEventListener('statechange', stateChange);
        // Let the short release finish without a click. A suspended context must
        // be disconnected immediately, before a later tab resume can reach it.
        if (ctx.state === 'running') setTimeout(() => output.disconnect(), 250);
        else output.disconnect();
      },
      setLevel(v, secs = .35) {
        level = v;
        output.gain.cancelScheduledValues(ctx.currentTime);
        output.gain.setValueAtTime(output.gain.value, ctx.currentTime);
        output.gain.linearRampToValueAtTime(level, ctx.currentTime + secs);
      },
      get output() { return output; },
      get running() { return running; },
      get playing() { return !!voice; },
      get offset() { return voice?.offset ?? null; },
      get loaded() { return !!buffer; },
      get duration() { return buffer?.duration || 0; },
    };
  };
})();
