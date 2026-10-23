#!/usr/bin/env python3
"""Give the four hub smiths the `repair` offer (docs/durability.md).

Run after the zone generators (they rewrite their NPCs), before sync-world.cjs. Repeating it is safe. The offer has no
cost: the server prices every repair from the piece (`Character::repair_price`).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
# Alderhaven's armorer, Skaldholm's master smith, Nacrehold's coral smith and Asterion's glass-forged armourer.
SMITHS = ('smith', 'city_smith', 'nacre_smith', 'asterion_smith')
OFFER = dict(id='repair', label='Repair worn gear', cost=0)


def main():
    world = json.loads(MAP.read_text())
    found = set()
    for npcs in [world['npcs']] + [z.get('npcs', []) for z in world['zones']]:
        for npc in npcs:
            if npc['id'] in SMITHS:
                found.add(npc['id'])
                npc['offers'] = [o for o in npc.get('offers', []) if o['id'] != 'repair'] + [dict(OFFER)]
    missing = set(SMITHS) - found
    if missing:
        raise SystemExit(f'smith NPCs not found: {sorted(missing)}')
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
