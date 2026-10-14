#!/usr/bin/env python3
"""Append the match-only arena without changing any existing world zone or private-copy id."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
ARENA = {
    'name': 'The Arena', 'theme': 'arena', 'tagline': 'The combatants decide the outcome.',
    'size': 32, 'spawn': {'x': 16, 'y': 16}, 'objects': [], 'slimes': [],
    'npcs': [], 'quests': [], 'city': None, 'portals': [], 'places': [], 'levels': [1, 99],
}

def main():
    world = json.loads(MAP.read_text())
    zones = world['zones']
    existing = next((i for i, zone in enumerate(zones) if zone['name'] == ARENA['name']), None)
    if existing is None:
        zones.append(ARENA)
    else:
        if existing != len(zones) - 1:
            raise SystemExit('Arena must be the final file zone to preserve saved zone ids')
        zones[existing] = ARENA
    MAP.write_text(json.dumps(world, indent=2) + '\n')
    print(f'Arena is file zone {len(zones)}; entry is by queue only.')

if __name__ == '__main__':
    main()
