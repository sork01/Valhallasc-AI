'use strict';
/* Music for the Emberfall Crags: "Ashfall Run". Dark but driving: E minor with a Phrygian F and a major B chord that
   drags every phrase back to E, 4/4 at 140 BPM, 32 bars of about 55 s that loop. Pass 1 is kick, off-beat gallop bass,
   a bright arpeggio and a hushed lead; pass 2 adds four-on-the-floor with snare and clap, sixteenth hats, a snarling
   lead through an echo, chord stabs and a low pad. Written in dybase2 (project "Valhalla Crags - Ashfall Run") and
   played from assets/music_crags.mp3 by music_player.js. */
(() => {
  window.createCragMusic = ctx => window.createLoopMusic(ctx, 'assets/music_crags.mp3');
})();
