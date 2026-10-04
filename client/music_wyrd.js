'use strict';
/* Music for the Wyrdwood: "Wyrdwood Wanderings". A waltz in A minor written in dybase2 (project "Valhalla Wyrdwood - Wyrdwood
   Wanderings": marimba arpeggio, flute theme, storm bridge with strings and drums, return) and played from assets/music_wyrd.mp3
   by music_player.js. */
(() => {
  window.createWyrdMusic = ctx => window.createLoopMusic(ctx, 'assets/music_wyrd.mp3');
})();
