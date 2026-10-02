'use strict';
(() => {
  // A golden-haired healer in ivory and crimson robes: shares only the equipment compositor; artwork and animation are the Priest\u2019s own.
  class PriestSprite extends MageSprite {}
  PriestSprite.TIERS = ['pilgrim', 'dawn'];
  PriestSprite.METADATA = 'assets/priest_sprites.txt';
  PriestSprite.HAIR = ['#ecd290', '#9eaccf', '#b5616d', '#624357', '#334c4a', '#465278'];
  PriestSprite.SKIN = ['#f0bfac', '#ffe0c5', '#cc927b', '#9c695a'];
  PriestSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, pilgrim: { name: 'Pilgrim robes', defense: 3 }, dawn: { name: 'Dawnweave vestments', defense: 5 } };
  PriestSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, mace: { name: 'Oak mace', attack: 4 }, sunmace: { name: 'Sunbreaker mace', attack: 8 } };
  PriestSprite.equipment = look => ({
    armor: Object.hasOwn(PriestSprite.ARMOR, look?.priestArmor) ? look.priestArmor : 'pilgrim',
    weapon: Object.hasOwn(PriestSprite.WEAPON, look?.priestWeapon) ? look.priestWeapon : 'mace',
  });
  MageSprite.female(PriestSprite, 'assets/priest_f_sprites.txt');
  window.PriestSprite = PriestSprite;
})();
