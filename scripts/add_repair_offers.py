#!/usr/bin/env python3
"""Give hub smiths repair offers and every PvE instance an entrance smith.

Run after the zone generators (they rewrite their NPCs), before sync-world.cjs. Repeating it is safe. The offer has no
cost: the server prices repairs from the piece and authoritative instance zone.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
# Alderhaven's armorer, Skaldholm's master smith, Nacrehold's coral smith and Asterion's glass-forged armourer.
SMITHS = ('smith', 'city_smith', 'nacre_smith', 'asterion_smith')
OFFER = dict(id='repair', label='Repair worn gear', cost=0)


def entrance_smith(zone, index):
    sx, sy = zone['spawn']['x'], zone['spawn']['y']
    def clear(x, y):
        if not (.7 < x < zone['size'] - .7 and .7 < y < zone['size'] - .7):
            return False
        for o in zone['objects']:
            if o.get('width', 0) and o.get('depth', 0):
                if abs(x-o['x']) < o['width']/2+.4 and abs(y-o['y']) < o['depth']/2+.4:
                    return False
            elif math.hypot(x-o['x'], y-o['y']) < o.get('r', 0)+.4:
                return False
        return True
    for radius in (3, 4, 5, 6):
        for dx, dy in ((0,1),(1,0),(-1,0),(0,-1),(.7,.7),(-.7,.7),(.7,-.7),(-.7,-.7)):
            x, y = round(sx+dx*radius, 2), round(sy+dy*radius, 2)
            if not all(clear(sx+(x-sx)*t/40, sy+(y-sy)*t/40) for t in range(41)):
                continue
            if any(math.hypot(x-p['x'],y-p['y']) < p['r']+1.8 for p in zone.get('portals', [])):
                continue
            if any(math.hypot(x-n['x'],y-n['y']) < 2 for n in zone.get('npcs', [])):
                continue
            if any(math.hypot(x-s['x'],y-s['y']) < 7 for s in zone.get('slimes', [])):
                continue
            return dict(id=f'dungeon_repair_{index}',name='Repair Smith',role='Dungeon repairs',x=x,y=y,
                        dialogue='I can repair your gear here. Dungeon repairs cost four times the town price.',
                        color='#b96e45',look=dict(skin='#dca480',hair='#694737',style='bald'),offers=[dict(OFFER)])
    raise ValueError(f"No safe entrance repair position in {zone['name']}")


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
    for index, zone in enumerate(world['zones'], 1):
        if zone.get('players', 0) <= 0 or zone.get('copies', 0) <= 0:
            continue
        zone['npcs'] = [n for n in zone.get('npcs', []) if not n['id'].startswith('dungeon_repair_')]
        zone['npcs'].append(entrance_smith(zone, index))
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
