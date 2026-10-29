'use strict';
// Bundled CC0 performances and authored effects; provenance is in assets/combat/.
window.RecordedCombat = (() => {
  const variants = {
    sword: ['sword', 'sword-2', 'sword-3'], dagger: ['dagger', 'dagger-2', 'dagger-3'],
    mace: ['mace', 'mace-2', 'mace-3'], staff: ['staff', 'staff-2'], bow: ['bow', 'bow-2'], arrow: ['arrow', 'arrow-2'],
    impact: ['impact', 'impact-2', 'impact-3'], metal: ['metal', 'metal-2'], wood: ['wood', 'wood-2'],
    'player-hurt': ['player-hurt', 'player-hurt-2', 'player-hurt-3'],
    'player-death': ['player-death', 'player-death-2', 'player-death-3'],
    'player-female-hurt': ['player-female-hurt', 'player-female-hurt-2', 'player-female-hurt-3'],
    'player-female-death': ['player-female-death', 'player-female-death-2', 'player-female-death-3'],
    'skill-fire': ['skill-fire', 'skill-fire-2'],
  };
  // Every learned skill has a sound identity; related skills share material at distinct base pitches.
  const skills = {
    cleave:['sword',.85], battlecry:['skill-focus',.72], shieldwall:['skill-shield',.78], whirlwind:['skill-whirl',.82],
    charge:['skill-rush',.78], groundslam:['skill-earth',.78], secondwind:['skill-heal',.85], berserk:['skill-focus',.82],
    earthshatter:['skill-earth',.9], titanswrath:['skill-blast',.7],
    twinbolt:['skill-arcane',1.12], arcaneward:['skill-shield',1.05], fireball:['skill-fire',1], barrage:['skill-arcane',1.25],
    blink:['skill-rush',1.2], chainlightning:['skill-lightning',1.12], meteor:['skill-blast',.82], lifedrain:['skill-shadow',.83],
    arcanestorm:['skill-ice',.88], starfall:['skill-holy',.85],
    throwingknives:['dagger',1.12], evasion:['skill-rush',1.1], lunge:['skill-rush',.95], flurry:['skill-whirl',1.15],
    shadowveil:['skill-shadow',.75], cycloneblades:['skill-whirl',1], assassinate:['dagger',.78], deadlyfocus:['skill-focus',1.1],
    knifering:['dagger',1.25], thousandcuts:['skill-whirl',1.28],
    mend:['skill-heal',1], smite:['skill-holy',1.1], wardoflight:['skill-shield',1.18], prayer:['skill-heal',.9],
    holynova:['skill-holy',.95], blessing:['skill-shield',1.28], guardianlight:['skill-heal',1.12], searinglight:['skill-holy',1.22],
    divinehymn:['skill-heal',.78], heavenswrath:['skill-holy',.78],
    powershot:['bow',.83], multishot:['arrow',.95], rollaway:['skill-rush',1.05], piercingarrow:['arrow',.82],
    huntersmark:['skill-focus',.94], explosivearrow:['skill-blast',1.1], rapidfire:['bow',1.18], rainofarrows:['arrow',.72],
    eaglesight:['skill-focus',1.22], arrowstorm:['arrow',1.12],
  };
  const cues = [...new Set([
    ...Object.values(variants).flat(), ...Object.values(skills).map(s => s[0]),
    ...['beast', 'insect', 'undead', 'plant', 'water', 'ranged'].flatMap(f => ['attack', 'hurt', 'death'].map(s => `${f}-${s}`)),
    'achievement', 'levelup',
  ])];
  const buffers = new Map(), pending = new Map(), voices = new Set(), celebrations = new Set();
  const lastTake = new Map(), lastRate = new Map();
  let context = null, priming = null;
  function load(c, cue) {
    if (pending.has(cue)) return pending.get(cue);
    const request = fetch(`assets/combat/${cue}.mp3`, { priority: 'low' }).then(r => {
      if (!r.ok) throw Error('Combat recording unavailable');
      return r.arrayBuffer();
    }).then(data => c.decodeAudioData(data)).then(buffer => { if (context === c) buffers.set(cue, buffer); return buffer; }).catch(() => null);
    pending.set(cue, request);
    return request;
  }
  function prime(c) {
    if (context !== c) { stop(); context = c; buffers.clear(); pending.clear(); priming = null; }
    if (priming) return priming;
    let next = 0;
    // Leave room for character art, input and painting during the first seconds of play.
    const yieldLoad = () => new Promise(resolve => {
      if (window.requestIdleCallback) window.requestIdleCallback(resolve, { timeout: 250 });
      else window.setTimeout(resolve, 16);
    });
    priming = (async () => {
      while (context === c && next < cues.length) {
        await yieldLoad();
        if (context === c) await load(c, cues[next++]);
      }
    })();
    return priming;
  }
  function stop() { for (const source of voices) source.stop(); voices.clear(); celebrations.clear(); }
  function play(c, bus, family, stage, level, enemies, finalBoss = false, heavy = false) {
    if (!(level > 0)) return true;
    const profile = family === 'skill' ? skills[stage] : null;
    if (family === 'skill' && !profile) return false;
    const key = profile ? profile[0] : family === 'construct' ? stage === 'death' ? 'metal' : stage === 'hurt' ? 'impact' : 'wood'
      : ['beast', 'insect', 'undead', 'plant', 'water', 'ranged', 'player', 'player-female'].includes(family) ? `${family}-${stage}`
      : family === 'spell' ? 'staff' : family;
    const choices = (variants[key] || [key]).filter(cue => buffers.has(cue));
    if (!choices.length) { for (const cue of variants[key] || [key]) if (cues.includes(cue)) load(c, cue); return false; }
    const important = key === 'achievement' || key === 'levelup';
    // Reserve two of the twelve slots for progression cues so combat cannot drown them out.
    if ((enemies && enemies.size >= 4) || (!important && voices.size - celebrations.size >= 10)) return true;
    if (voices.size >= 12) {
      if (!important) return true;
      const old = [...voices].find(s => !celebrations.has(s)) || voices.values().next().value;
      old.stop(); voices.delete(old); celebrations.delete(old);
    }
    const alternatives = choices.filter(cue => cue !== lastTake.get(key));
    const pool = alternatives.length ? alternatives : choices;
    const cue = pool[Math.floor(Math.random() * pool.length)]; lastTake.set(key, cue);
    const source = c.createBufferSource(), gain = c.createGain(), filter = c.createBiquadFilter();
    source.buffer = buffers.get(cue);
    const vocal = family === 'player' || family === 'player-female';
    const base = (profile?.[1] || 1) * (finalBoss ? .72 : heavy ? .86 : stage === 'miss' ? 1.25 : 1);
    const spread = important ? .02 : vocal ? .06 : .16;
    let jitter = (Math.random() - .5) * spread;
    if (Math.abs(base * (1 + jitter) - (lastRate.get(key) || 0)) < base * .008)
      jitter = jitter < 0 ? Math.max(-spread / 2, jitter - spread / 4) : Math.min(spread / 2, jitter + spread / 4);
    source.playbackRate.value = base * (1 + jitter); lastRate.set(key, source.playbackRate.value);
    gain.gain.value = Math.min(1.1, level) * (stage === 'death' ? .32 : .28) * (.93 + Math.random() * .14);
    filter.type = 'lowpass'; filter.frequency.value = 7500 + Math.random() * 3500; filter.Q.value = .5;
    source.connect(filter).connect(gain).connect(bus); voices.add(source); enemies?.add(source);
    if (important) celebrations.add(source);
    source.onended = () => { voices.delete(source); celebrations.delete(source); enemies?.delete(source); source.disconnect(); filter.disconnect(); gain.disconnect(); };
    source.start();
    return true;
  }
  return { prime, play, stop, get ready() { return buffers.size === cues.length; } };
})();
