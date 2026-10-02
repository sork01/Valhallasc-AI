'use strict';
(() => {
  // Shares only the equipment compositor; artwork and animation are separate.
  class AssassinSprite extends MageSprite {}
  AssassinSprite.TIERS = ['shadow', 'moon'];
  AssassinSprite.METADATA = 'assets/assassin_sprites.txt';
  AssassinSprite.HAIR = ['#465278', '#9eaccf', '#624357', '#334c4a', '#b5616d', '#d4b88b'];
  AssassinSprite.SKIN = ['#f0bfac', '#ffe0c5', '#cc927b', '#9c695a'];
  AssassinSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, shadow: { name: 'Nightweave', defense: 2 }, moon: { name: 'Moonveil', defense: 4 } };
  AssassinSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, daggers: { name: 'Twin daggers', attack: 4 }, moonfang: { name: 'Moonfang blades', attack: 8 } };
  AssassinSprite.equipment = look => ({
    armor: Object.hasOwn(AssassinSprite.ARMOR, look?.assassinArmor) ? look.assassinArmor : 'shadow',
    weapon: Object.hasOwn(AssassinSprite.WEAPON, look?.assassinWeapon) ? look.assassinWeapon : 'daggers',
  });
  window.AssassinSprite = AssassinSprite;
})();
