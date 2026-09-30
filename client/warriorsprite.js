'use strict';
(() => {
  // Painted reference artwork; shared depth compositor, independent assets.
  class WarriorSprite extends MageSprite {}
  WarriorSprite.METADATA = 'assets/warrior_layered_sprites.txt';
  WarriorSprite.HAIR = ['#514356', '#8b514a', '#d0ae75', '#3b5573', '#835b91', '#c1becb'];
  WarriorSprite.SKIN = ['#ffc1a6', '#ffe1c3', '#dba084', '#a87563'];
  WarriorSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, crimson: { name: 'Crimson guard', defense: 3 }, azure: { name: 'Azure guard', defense: 5 } };
  WarriorSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, sword: { name: 'Sword & shield', attack: 4 }, royal: { name: 'Royal sword & shield', attack: 8 } };
  WarriorSprite.equipment = look => ({
    armor: Object.hasOwn(WarriorSprite.ARMOR, look?.warriorArmor) ? look.warriorArmor : 'crimson',
    weapon: Object.hasOwn(WarriorSprite.WEAPON, look?.warriorWeapon) ? look.warriorWeapon : 'sword',
  });
  window.WarriorSprite = WarriorSprite;
})();
