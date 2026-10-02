'use strict';
(() => {
  // The Assassin\u2019s style as a healer: shares only the equipment compositor; artwork and animation are separate.
  class PriestSprite extends MageSprite {}
  PriestSprite.METADATA = 'assets/priest_sprites.txt';
  PriestSprite.HAIR = ['#e3d6b0', '#9eaccf', '#b5616d', '#624357', '#334c4a', '#465278'];
  PriestSprite.SKIN = ['#f0bfac', '#ffe0c5', '#cc927b', '#9c695a'];
  PriestSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, pilgrim: { name: 'Pilgrim robes', defense: 3 }, dawn: { name: 'Dawnweave vestments', defense: 5 } };
  PriestSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, mace: { name: 'Oak mace', attack: 4 }, sunmace: { name: 'Sunbreaker mace', attack: 8 } };
  PriestSprite.equipment = look => ({
    armor: Object.hasOwn(PriestSprite.ARMOR, look?.priestArmor) ? look.priestArmor : 'pilgrim',
    weapon: Object.hasOwn(PriestSprite.WEAPON, look?.priestWeapon) ? look.priestWeapon : 'mace',
  });
  window.PriestSprite = PriestSprite;
})();
