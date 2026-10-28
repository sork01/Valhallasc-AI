'use strict';
// Short recorded performances, bundled locally; sources and CC0 notices live in assets/combat/.
window.RecordedCombat = (() => {
  const cues = ['sword', 'dagger', 'mace', 'staff', 'bow', 'arrow', 'impact', 'metal', 'wood',
    ...['beast', 'insect', 'undead', 'plant', 'water', 'ranged'].flatMap(f => ['attack', 'hurt', 'death'].map(s => `${f}-${s}`)),
    'player-hurt', 'player-death'];
  const buffers = new Map(), pending = new Map(), voices = new Set();
  let context = null, priming = null;
  function load(c, cue) {
    if (pending.has(cue)) return pending.get(cue);
    const request = fetch(`assets/combat/${cue}.mp3`).then(r => {
      if (!r.ok) throw Error('Combat recording unavailable');
      return r.arrayBuffer();
    }).then(data => c.decodeAudioData(data)).then(buffer => { if (context === c) buffers.set(cue, buffer); return buffer; }).catch(() => null);
    pending.set(cue, request);
    return request;
  }
  function prime(c) {
    if (context !== c) { stop(); context = c; buffers.clear(); pending.clear(); priming = null; }
    if (priming) return priming;
    // Four downloads/decodes at once keep Safari and small devices responsive.
    let next = 0;
    const worker = async () => { while (next < cues.length) await load(c, cues[next++]); };
    priming = Promise.all(Array.from({ length: 4 }, worker));
    return priming;
  }
  function stop() { for (const source of voices) source.stop(); voices.clear(); }
  function play(c, bus, family, stage, level, enemies, finalBoss = false, heavy = false) {
    const cue = family === 'construct' ? stage === 'death' ? 'metal' : stage === 'hurt' ? 'impact' : 'wood'
      : ['beast', 'insect', 'undead', 'plant', 'water', 'ranged', 'player'].includes(family) ? `${family}-${stage}`
      : family === 'impact' ? 'impact' : family === 'spell' ? 'staff' : family;
    const buffer = buffers.get(cue);
    // Use the existing synth immediately while a recording is unavailable. Never replay a stale hit after loading.
    if (!buffer) { if (cues.includes(cue)) load(c, cue); return false; }
    if (voices.size >= 12 || (enemies && enemies.size >= 4)) return true;
    const source = c.createBufferSource(), gain = c.createGain();
    source.buffer = buffer;
    source.playbackRate.value = finalBoss ? .72 : heavy ? .86 : stage === 'miss' ? 1.25 : 1;
    gain.gain.value = Math.min(1.1, level) * (stage === 'death' ? .32 : .28);
    source.connect(gain).connect(bus); voices.add(source); enemies?.add(source);
    source.onended = () => { voices.delete(source); enemies?.delete(source); source.disconnect(); gain.disconnect(); };
    source.start();
    return true;
  }
  return { prime, play, stop, get ready() { return buffers.size === cues.length; } };
})();
