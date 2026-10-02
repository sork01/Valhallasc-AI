'use strict';
(() => {
  // Painted reference artwork; shared depth compositor, independent assets.
  class WarriorSprite extends MageSprite {}
  WarriorSprite.TIERS = ['crimson', 'azure'];
  WarriorSprite.METADATA = 'assets/warrior_layered_sprites.txt';
  WarriorSprite.HAIR = ['#514356', '#8b514a', '#d0ae75', '#3b5573', '#835b91', '#c1becb'];
  WarriorSprite.SKIN = ['#ffc1a6', '#ffe1c3', '#dba084', '#a87563'];
  WarriorSprite.ARMOR = { none: { name: 'Simple cloth', defense: 0 }, crimson: { name: 'Crimson guard', defense: 3 }, azure: { name: 'Azure guard', defense: 5 } };
  WarriorSprite.WEAPON = { none: { name: 'Empty hands', attack: 0 }, sword: { name: 'Sword & shield', attack: 4 }, royal: { name: 'Royal sword & shield', attack: 8 } };
  WarriorSprite.equipment = look => ({
    armor: MageSprite.hasGear(WarriorSprite.ARMOR, 'armor', look?.warriorArmor) ? look.warriorArmor : 'crimson',
    weapon: MageSprite.hasGear(WarriorSprite.WEAPON, 'weapon', look?.warriorWeapon) ? look.warriorWeapon : 'sword',
  });
  MageSprite.female(WarriorSprite, 'assets/warrior_layered_f_sprites.txt');
  window.WarriorSprite = WarriorSprite;
})();
