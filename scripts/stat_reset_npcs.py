"""Keep paid stat reset services on the stewards of major safe cities.

Run by sync-world.cjs after zone generators. The pass is idempotent.
"""
import json
from pathlib import Path

MAP = Path(__file__).resolve().parents[1] / 'world/map.txt'
STEWARDS = {
    'Alderhaven': 'guide',
    'Skaldholm': 'city_steward',
    'Nacrehold': 'nacre_archivist',
    'Astralhollow': 'astral_steward',
    'Asterion': 'asterion_archon',
}
OFFER = {'id': 'stat_reset', 'label': 'Reset trained attributes', 'cost': 0}

def main():
    world = json.loads(MAP.read_text())
    found = set()
    changed = False
    for zone in [world, *world.get('zones', [])]:
        city = (zone.get('city') or {}).get('name')
        if city not in STEWARDS:
            continue
        matches = [npc for npc in zone.get('npcs', []) if npc['id'] == STEWARDS[city]]
        if len(matches) != 1:
            raise ValueError(f'{city}: expected one stat reset steward')
        found.add(city)
        npc = matches[0]
        if OFFER not in npc['offers']:
            npc['offers'] = [o for o in npc['offers'] if o['id'] != OFFER['id']]
            npc['offers'].append(OFFER.copy())
            changed = True
    if found != STEWARDS.keys():
        raise ValueError(f'Missing stat reset cities: {STEWARDS.keys() - found}')
    if changed:
        MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    print(f'Stat reset services in {len(found)} cities')

if __name__ == '__main__':
    main()
