#!/usr/bin/env python3
"""Give hold objectives room to maneuver around their authored places."""
import json
from pathlib import Path

MAP = Path(__file__).resolve().parents[1] / 'world/map.txt'
HOLD_MARGIN = 2.5


def apply(world):
    for area in [world, *world['zones']]:
        targets = {obj['target'] for quest in area.get('quests', [])
                   for obj in quest['objectives'] if obj['kind'] == 'hold'}
        for place in area.get('places', []):
            if place['id'] in targets:
                place['holdRadius'] = round(place['r'] + HOLD_MARGIN, 2)
            else:
                place.pop('holdRadius', None)


if __name__ == '__main__':
    world = json.loads(MAP.read_text())
    apply(world)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
