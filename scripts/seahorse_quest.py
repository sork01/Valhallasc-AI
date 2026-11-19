#!/usr/bin/env python3
"""Add the fishing seahorse quest without moving any authored world content."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEST = 'deep_seahorse'
TITLE = 'A Friend Beneath the Tide'
DESCRIPTION = (
    'A young seahorse has followed me to Keelhaven, but it will not trust an empty hand. '
    'Bring me 10 Pier Sprat and 5 Saltby Herring, caught with a fishing rod at Saltby or another sea coast. '
    'Buy a Twig Rod from the Fisher at Saltby if you need one; you cannot fish down here. '
    'Feed our new friend and it will carry you underwater at 160% of normal movement speed. '
    'It is the only mount that can be ridden underwater, and it cannot be ridden on land.'
)


def install(world):
    area = next(a for a in [world, *world['zones']] if a.get('theme') == 'deep')
    assert any(n['id'] == 'deep_healer' for n in area['npcs'])
    levels = json.loads((ROOT / 'world/levels.txt').read_text())
    quest = dict(id=QUEST, title=TITLE, npc='deep_healer', description=DESCRIPTION,
                 objectives=[dict(kind='bring', target=item, count=count, label=label)
                             for item, count, label in [
                                 ('fish_pier_sprat', 10, 'Bring 10 Pier Sprat'),
                                 ('fish_saltby_herring', 5, 'Bring 5 Saltby Herring')]],
                 level=35, rewardXp=levels[34] // 10, rewardGold=1250,
                 requires='deep_welcome', repeatable=False, rewardMount='seahorse')
    area['quests'] = [q for q in area['quests'] if q['id'] != QUEST] + [quest]


if __name__ == '__main__':
    path = ROOT / 'world/map.txt'
    world = json.loads(path.read_text())
    install(world)
    path.write_text(json.dumps(world, ensure_ascii=False, indent=2) + '\n')
    print('Seahorse fishing quest installed in Rán’s Deep')
