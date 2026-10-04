'use strict';
/* Music for Bifrost Reach: "Above the Storm". D lydian, 84 BPM, 32 bars (91 s), written in dybase2 (project "Valhalla Bifrost Reach -
   Above the Storm": glass-vibes arpeggio and Mellow Pad from the first bar, bells at 5, a flute theme with a plucked bass and a soft
   drum pulse at 9, a storm bridge (bars 17-24: Bm Gmaj7 D A, strings, low toms), the theme returning higher at 25) and played from
   assets/music_sky.mp3 by music_player.js. */
(() => {
  window.createSkyMusic = ctx => window.createLoopMusic(ctx, 'assets/music_sky.mp3');
})();
