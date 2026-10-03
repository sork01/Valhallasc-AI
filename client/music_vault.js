'use strict';
/* Music for the Undervault: "Beneath the Stone". Written in dybase2 and played from assets/music_vault.mp3 by music_player.js.
   Until the file exists the dungeon is silent (a loop that cannot load is never an error). */
(() => {
  window.createVaultMusic = ctx => window.createLoopMusic(ctx, 'assets/music_vault.mp3');
})();
