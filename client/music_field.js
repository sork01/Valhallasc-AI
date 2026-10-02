'use strict';
/* Music for the first map: "Greenmeadow Wander". A sunny, lilting folk tune in G major, 6/8 at 88 (dotted-quarter)
   BPM, 32 bars of about 44 s that loop. Pass 1 is a plucked kantele lead over harp arpeggios and bass; pass 2 is the
   same tune on a breathy flute with a string pad, hand drum and claps. Written in dybase2 (project "Valhalla Meadow -
   Greenmeadow Wander") and played from assets/music_meadow.mp3 by music_player.js. */
(() => {
  window.createFieldMusic = ctx => window.createLoopMusic(ctx, 'assets/music_meadow.mp3');
})();
