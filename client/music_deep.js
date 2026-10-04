'use strict';
/* Music for Ran's Deep: "Lantern Tide", F minor, 90 BPM, 32 bars (85.3 s), written in dybase2 (project "Valhalla Rans Deep - Lantern Tide"):
   a downtempo, swung hip-hop groove, deliberately unlike the other zone songs: chorus electric-piano chords (Fm9 Dbmaj7 Bbm9 Cm7 / Fm9 Dbmaj7
   Dbmaj7 Cm7) and a swung kick-snare-hat loop from the first bar, an 808 sub bass at 5 (the first bar of the groove), a bell-tine theme at 9 that
   rests for the third eight bars (17-24, an open hat added) and returns at 25. No noise or drone layers. Played from assets/music_deep.mp3 by
   music_player.js. */
(() => {
  window.createDeepMusic = ctx => window.createLoopMusic(ctx, 'assets/music_deep.mp3');
})();
