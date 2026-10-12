#!/usr/bin/env python3
"""Design manifest for the four sealed Yearwheel instance reward sets.

These IDs are reserved for the instance loot implementation. They are deliberately
not added to items.txt while the four doors are sealed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'world/yearwheel_rewards.txt'
ITEMS = {i['id']: i for i in json.loads((ROOT / 'world/items.txt').read_text())}
CLASSES = ('warrior', 'mage', 'assassin', 'priest', 'hunter')
MAIN = {'warrior': 'strength', 'mage': 'intellect', 'assassin': 'agility',
        'priest': 'intellect', 'hunter': 'agility'}
SETS = (
    ('sp', 'The Blooming Labyrinth', 97, 'Thornwake', 'petal steel, roots and bright jade', 1.10, 110),
    ('su', 'The Solar Crucible', 98, 'Sunforged', 'white gold, brass and molten amber', 1.15, 115),
    ('au', 'The Amber Archive', 99, 'Harvestbound', 'copper leaves, amber glass and dark leather', 1.20, 120),
    ('wi', 'The Silent Solstice', 99, 'Rimecrowned', 'pale ice, silver and midnight blue', 1.20, 120),
)


def baseline(cls, slot):
    return next(i for i in ITEMS.values() if i.get('class') == cls and i.get('kind') == slot
                and i.get('requiredLevel') == 95 and i.get('rarity') == 'rare')


def build():
    result = []
    for season, dungeon, level, family, look, scale, bonus in SETS:
        pieces = []
        for cls in CLASSES:
            for slot in ('weapon', 'armor'):
                old = baseline(cls, slot)
                pieces.append(dict(id=f'yr_{season}_{cls}_{slot}', name=f'{family} {old["name"].removeprefix("Thunderbound ")}',
                                   kind=slot, **{'class': cls}, requiredLevel=level, rarity='epic',
                                   attack=round(old['attack'] * scale, 1), defense=round(old['defense'] * scale, 1),
                                   bonusStats={MAIN[cls]: bonus, 'stamina': bonus}, motif=look))
        old = ITEMS['necklace_moonstone_l95_blue']
        pieces.append(dict(id=f'yr_{season}_necklace', name=f'{family} Season Pendant', kind='necklace',
                           **{'class': None}, requiredLevel=level, rarity='epic',
                           attack=round(old['attack'] * scale, 1), defense=round(old['defense'] * scale, 1),
                           bonusStats={'stamina': bonus, 'agility': bonus}, motif=look))
        result.append(dict(season=season, dungeon=dungeon, level=level, partySize=5,
                           source='final boss personal party roll', guaranteedDrops=2,
                           rewardRule='one class-valid weapon or armor choice per eligible member after first clear; boss pool includes the shared pendant',
                           pieces=pieces))
    ids = [p['id'] for group in result for p in group['pieces']]
    assert len(ids) == len(set(ids)) == 44
    assert all(len(g['pieces']) == 11 and g['level'] >= 97 for g in result)
    return dict(version=1, status='design_only_until_instance_open', dungeons=result)


if __name__ == '__main__':
    OUT.write_text(json.dumps(build(), indent=2) + '\n')
    print(OUT, '44 reserved rewards')
