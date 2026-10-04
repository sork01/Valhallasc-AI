'use strict';
/* Music for Ran's Deep: "The Net Remembers", dub techno, F minor, 112 BPM, 40 bars (85.7 s), written in dybase2 (project "Valhalla Rans Deep -
   The Net Remembers"): bowed-plate drone, sonar pings from a glass bowl through a tape echo and sea-noise from the first bar, a soft kick and a
   sub bass at 5, electric-piano chord stabs thrown into a long echo (Fm9 Fm9 Dbmaj7 Dbmaj7 Fm9 Fm9 Bbm7 Cm7) with an off-beat open hat at 9,
   ghost hats and a low tom at 17, the kick dropping out for the undertow at 25 and returning at 29, then thinning back to the water at 37. It
   deliberately shares no instrument or rhythm with the other zone songs. Played from assets/music_deep.mp3 by music_player.js. */
(() => {
  window.createDeepMusic = ctx => window.createLoopMusic(ctx, 'assets/music_deep.mp3');
})();
