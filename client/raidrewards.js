'use strict';
// Names change in the existing bar slot; the server retains its authoritative id.
window.RaidRewards = (() => {
  const weapons = {
    chainforged_warrior_weapon: { replaces: 'earthshatter', name: 'Slagshatter',
      description: 'Earthshatter also leaves a burning patch for 4 seconds. Extra skill damage affects monsters.',
      feature: '8% on a hit: send a slag wave up to 12 tiles ahead. Its total damage is capped at 60% of one basic blow. Replaces Earthshatter with Slagshatter while equipped.' },
    chainforged_mage_weapon: { replaces: 'arcaneward', name: 'Cinder Ward',
      description: 'Arcane Ward also sends out a short damaging pulse when it expires. Extra skill damage affects monsters.',
      feature: '10% on a spell hit: summon an ember orb for 6 seconds. It strikes every 1.5 seconds, for at most 48% of one basic blow in total. Replaces Arcane Ward with Cinder Ward while equipped.' },
    chainforged_assassin_weapon: { replaces: 'knifering', name: 'Ember Ring',
      description: 'Knife Ring also leaves a burning trail for 4 seconds. Extra skill damage affects monsters.',
      feature: 'Hits build an ember burn, up to five stacks. Each stack burns for 1% of one basic blow per second for 4 seconds. Replaces Knife Ring with Ember Ring while equipped.' },
    chainforged_priest_weapon: { replaces: 'mend', name: 'Bellows Mend',
      description: 'Mend also makes your next effective heal within 15 seconds 10% stronger. Extra skill healing applies outside PvP fights.',
      feature: '8% on an effective heal: give its target a 4-second ember ward worth 3% of maximum health, scaled by PvP healing rules. Replaces Mend with Bellows Mend while equipped.' },
    chainforged_hunter_weapon: { replaces: 'arrowstorm', name: 'Chain Storm',
      description: 'Arrow Storm also bounces once for 20% of one basic blow. Extra skill damage affects monsters.',
      feature: '10% on a hit: chain to two nearby foes for half the hit each, capped at 30% of one basic blow per target. Replaces Arrow Storm with Chain Storm while equipped.' },
  };
  const limits = 'Weapon procs can trigger once every 3 seconds. Damage to a player is capped at 3% of their maximum health before normal PvP reductions. The original skill returns on unequip.';
  return {
    tooltip: item => weapons[item?.id] ? `${weapons[item.id].feature} ${limits}` : '',
    skill(skill, item) {
      const w = weapons[item];
      return w?.replaces === skill.id ? { ...skill, name: w.name, description: `${skill.description} ${w.description}` } : skill;
    },
  };
})();
