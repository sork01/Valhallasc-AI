#!/usr/bin/env python3
"""Arena gauntlet quests (docs/arena-quests.md): one per level 20, 30 ... 90 and 99 at every major safe city.

A giver offers the quest and, through the `gauntlet` offer, sends the hero into the Arena where five opponents, one per
class, are fought one at a time. Winning all five makes the quest ready; the turn-in pays a blue weapon of the hero's
class for the level, experience and gold. Quest ids are `arena_<city>_<level>`; the server allows one per level per
hero whichever giver it came from (`Quest::gauntlet_level`).

Run by sync-world.cjs after the zone generators. The pass replaces its own quests and offers, so it is idempotent.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ITEMS = json.loads((ROOT / 'world/items.txt').read_text())
XP = json.loads((ROOT / 'world/levels.txt').read_text())
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
LEVELS = (20, 30, 40, 50, 60, 70, 80, 90, 99)
FIGHTS = 5
# city name -> (quest id key, the giver who already stands in it: the one that keeps the stat reset service)
GIVERS = {
    'Alderhaven': ('alder', 'guide'),
    'Skaldholm': ('skald', 'city_steward'),
    'Nacrehold': ('nacre', 'nacre_archivist'),
    'Astralhollow': ('astral', 'astral_steward'),
    'Asterion': ('aster', 'asterion_archon'),
}
OFFER = {'id': 'gauntlet', 'label': 'Enter the Arena', 'cost': 0}
# Gold: what the hardest solo quest of that level pays (owner, 2026-10-21: the gold of a hard quest at that level).
GOLD = {20: 1200, 30: 1200, 40: 2400, 50: 2500, 60: 5000, 70: 9000, 80: 15000, 90: 18000, 99: 30000}
TITLES = {
    20: 'Arena Trial: Initiate', 30: 'Arena Trial: Challenger', 40: 'Arena Trial: Contender',
    50: 'Arena Trial: Gladiator', 60: 'Arena Trial: Veteran', 70: 'Arena Trial: Champion',
    80: 'Arena Trial: Warlord', 90: 'Arena Trial: Legend', 99: 'Arena Trial: Immortal',
}
DESCRIPTION = ('Prove yourself in the Arena. Choose "Enter the Arena" and face one fighter of every class, one after the '
               'other. You are healed between the fights, and a lost run costs you nothing. Come back here once you '
               'have beaten all five.')
LABEL = 'Win five Arena fights'


def xp_need(level):
    return XP[level - 1] if level <= len(XP) else XP[-1] + (level - len(XP)) * 2300


def blue_weapon(level, cls):
    """The ordinary blue weapon of the level's progression set (level 99 uses the 95 set)."""
    want = min(level // 5 * 5, 95)
    found = [i['id'] for i in ITEMS if i.get('kind') == 'weapon' and i.get('rarity') == 'rare'
             and i.get('class') == cls and i.get('requiredLevel') == want
             and i['id'].endswith(f'_l{want}_blue') and not i.get('source') and not i.get('starter')]
    if len(found) != 1:
        raise ValueError(f'expected one blue weapon for {cls} at {want}, found {found}')
    return found[0]


def quest(key, npc, level):
    return {
        'id': f'arena_{key}_{level}',
        'title': TITLES[level],
        'npc': npc,
        'description': DESCRIPTION,
        'objectives': [{'kind': 'gauntlet', 'target': f'L{level}', 'label': LABEL, 'count': FIGHTS}],
        'level': level,
        'rewardXp': xp_need(level) // 10,
        'rewardGold': GOLD[level],
        'requires': None,
        'repeatable': False,
        'rewardChoices': {cls: [blue_weapon(level, cls)] for cls in CLASSES},
        'minLevel': level,
    }


def main():
    world = json.loads(MAP.read_text())
    found = set()
    for zone in [world, *world.get('zones', [])]:
        city = (zone.get('city') or {}).get('name')
        if city not in GIVERS:
            continue
        key, giver = GIVERS[city]
        npcs = [n for n in zone.get('npcs', []) if n['id'] == giver]
        if len(npcs) != 1:
            raise ValueError(f'{city}: expected one giver {giver}')
        npc = npcs[0]
        npc['offers'] = [o for o in npc['offers'] if o['id'] != OFFER['id']] + [OFFER.copy()]
        zone['quests'] = [q for q in zone.get('quests', []) if not q['id'].startswith('arena_')]
        zone['quests'].extend(quest(key, giver, level) for level in LEVELS)
        found.add(city)
    if found != GIVERS.keys():
        raise ValueError(f'Missing arena cities: {GIVERS.keys() - found}')
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    print(f'Arena gauntlet quests: {len(LEVELS)} levels in {len(found)} cities')


if __name__ == '__main__':
    main()
