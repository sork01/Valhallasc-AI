'use strict';
(() => {
  // The Hunter: a bow-and-quiver ranger in the Assassin's anime cel style. Shares only the equipment compositor.
  class HunterSprite extends MageSprite {}
  HunterSprite.METADATA = 'assets/hunter_sprites.txt';
  HunterSprite.TIERS = ['scout', 'warden'];
  HunterSprite.HAIR = ['#a8643e', '#e3d6b0', '#5a8a68', '#465278', '#b5616d', '#c9c9d6'];
  HunterSprite.SKIN = ['#f0bfac', '#ffe0c5', '#cc927b', '#9c695a'];
  HunterSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, scout: { name: 'Scout\u2019s Jerkin', defense: 3 }, warden: { name: 'Wildwarden Coat', defense: 5 } };
  HunterSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, shortbow: { name: 'Hunter\u2019s Shortbow', attack: 4 }, wardenbow: { name: 'Wildwarden Longbow', attack: 8 } };
  HunterSprite.equipment = look => ({
    armor: Object.hasOwn(HunterSprite.ARMOR, look?.hunterArmor) ? look.hunterArmor : 'scout',
    weapon: Object.hasOwn(HunterSprite.WEAPON, look?.hunterWeapon) ? look.hunterWeapon : 'shortbow',
  });
  MageSprite.female(HunterSprite, 'assets/hunter_f_sprites.txt');
  window.HunterSprite = HunterSprite;
})();
