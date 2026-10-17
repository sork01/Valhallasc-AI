"""Keep one banker in each of the five big cities (docs/bank.md, BANK-NPC) and nowhere else.

Run by sync-world.cjs after zone generators. The pass is idempotent: a banker that already matches is left alone, a
changed or missing one is rewritten from the table below, and a `bank` offer anywhere else is an error. Each spot is
beside the plaza and near the city's other service NPCs, at least 2.6 tiles from every NPC, 4 from every portal and
2.5 from every walked route, with 1.2 tiles of clear ground (the chest and escort rules keep their own distances).
"""
import json
from pathlib import Path

MAP = Path(__file__).resolve().parents[1] / 'world/map.txt'
NOTE = ' Mind that a quest counts only what you carry, not what is in the bank.'
OFFER = {'id': 'bank', 'label': 'Open the bank', 'cost': 0}
BANKERS = {
    'Alderhaven': {
        'after': 'guide',
        'npc': {
            'id': 'banker_alderhaven', 'name': 'Brenna Coinwright', 'role': 'Banker', 'x': 39, 'y': 82.5,
            'color': '#c9a24b',
            'dialogue': 'Gold in your pocket is gold on the road. Leave what you cannot carry with me, and I will keep it as if it were my own.' + NOTE,
            'look': {'skin': '#edc5a1', 'hair': '#7a4a2a', 'style': 'bun', 'hat': 'bonnet', 'hatColor': '#8a6a2a'},
        },
    },
    'Skaldholm': {
        'after': 'city_steward',
        'npc': {
            'id': 'banker_skaldholm', 'name': 'Hakon Vaultwarden', 'role': 'Vault warden', 'x': 78, 'y': 65.5,
            'color': '#6d7f9c',
            'dialogue': "The hall's strongroom has held a jarl's ransom. A few spare helms will not trouble it." + NOTE,
            'look': {'skin': '#e3b895', 'hair': '#b9b2a4', 'style': 'short', 'hat': 'helm', 'hatColor': '#5c6b82', 'beard': '#b9b2a4', 'scale': 1.05},
        },
    },
    'Nacrehold': {
        'after': 'nacre_archivist',
        'npc': {
            'id': 'banker_nacrehold', 'name': 'Perla Tidekeeper', 'role': 'Mermaid · Tide banker', 'x': 98.5, 'y': 93.5,
            'color': '#e2b7d6',
            'dialogue': 'Pearls and pennies, shells and swords. The sea keeps nothing but the bank does.' + NOTE,
            'look': {'species': 'merfolk', 'female': True, 'tail': '#e2b7d6', 'skin': '#a4dbc9', 'hair': '#5f8f9c', 'style': 'long'},
        },
    },
    'Astralhollow': {
        'after': 'astral_steward',
        'npc': {
            'id': 'banker_astralhollow', 'name': 'Ilvane Stargaler', 'role': 'Astral banker', 'x': 61, 'y': 116,
            'color': '#8fb4ff',
            'dialogue': 'Every deposit is entered in the sky ledger. The stars do not forget, and neither do I.' + NOTE,
            'look': {'skin': '#d9bfa8', 'hair': '#9fb6e8', 'style': 'braid', 'hat': 'hood', 'hatColor': '#3d4a86'},
        },
    },
    'Asterion': {
        'after': 'asterion_archon',
        'npc': {
            'id': 'banker_asterion', 'name': 'Archon Veyl', 'role': 'Keeper of Weights', 'x': 88, 'y': 92,
            'color': '#c7b6e8',
            'dialogue': 'Present what you would store. It will be weighed, named and returned to you unchanged.' + NOTE,
            'look': {'skin': '#c78e6e', 'hair': '#f2e7d5', 'style': 'short', 'hat': 'feather', 'hatColor': '#4b3a88', 'scale': 1},
        },
    },
}

def main():
    world = json.loads(MAP.read_text())
    found = set()
    changed = False
    for zone in [world, *world.get('zones', [])]:
        city = (zone.get('city') or {}).get('name')
        spec = BANKERS.get(city)
        npcs = zone.get('npcs', [])
        if spec is None:
            stray = [n['id'] for n in npcs if n['id'].startswith('banker_') or any(o['id'] == 'bank' for o in n['offers'])]
            if stray:
                raise ValueError(f'{zone.get("name")}: a banker outside the five big cities: {stray}')
            continue
        banker = {**spec['npc'], 'offers': [OFFER.copy()], 'buys': False}
        banker = {k: banker[k] for k in ('id', 'name', 'role', 'x', 'y', 'color', 'dialogue', 'offers', 'buys', 'look')}
        mine = [n for n in npcs if n['id'] == banker['id']]
        others = [n['id'] for n in npcs if n['id'] != banker['id'] and any(o['id'] == 'bank' for o in n['offers'])]
        if len(mine) > 1 or others:
            raise ValueError(f'{city}: expected exactly one banker, found {len(mine)} and {others}')
        if mine:
            if mine[0] != banker:
                npcs[npcs.index(mine[0])] = banker
                changed = True
        else:
            at = [n['id'] for n in npcs].index(spec['after'])
            npcs.insert(at + 1, banker)
            changed = True
        found.add(city)
    if found != BANKERS.keys():
        raise ValueError(f'Missing bankers in: {BANKERS.keys() - found}')
    if changed:
        MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
    print(f'Bankers in {len(found)} cities')

if __name__ == '__main__':
    main()
