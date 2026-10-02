'use strict';
/* Title and character-creation music: "Snowbound Hearth". A slow Nordic-meets-Korean theme in D minor at 68 BPM
   (kantele melody, harp arpeggios, frame drum, warm pad, icy bells), 24 bars of about 85 s that loop. Written in
   dybase2 (project "Valhalla Intro - Snowbound Hearth") and played from assets/music_title.mp3 by music_player.js. */
(() => {
  window.createMusic = ctx => window.createLoopMusic(ctx, 'assets/music_title.mp3');
})();
