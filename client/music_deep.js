'use strict';
/* Music for Ran's Deep: "Lullaby of the Deep", D dorian, 72 BPM, 32 bars (106.7 s), written in dybase2 (project "Valhalla Rans Deep - Lullaby of the
   Deep"): a Mellow Pad on Dm9 Gadd9 Am7 Cmaj7 Dm9 Gadd9 Fmaj7 Am7 all the way through, a soft chorus electric-piano arpeggio from bar 5, and from bar 9
   a sub bass, a Rumble kick on beats 1 and 3 and a quiet vibrato-lead theme (bars 9-16 and 25-32; it rests in 17-24). No hats or cymbals and nothing
   above 2 kHz: an earlier song with hats and a bell lead was rejected. Played from assets/music_deep.mp3 by music_player.js. */
(() => {
  window.createDeepMusic = ctx => window.createLoopMusic(ctx, 'assets/music_deep.mp3');
})();
