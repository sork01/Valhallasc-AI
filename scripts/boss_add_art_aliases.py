#!/usr/bin/env python3
"""Give the helpers of the boss mechanics art: an enemy entry with `artFrom` borrows the sprite of another kind.

The helpers (a Bound Singer, a Reliquary Pearl, a Worldseed Seed, a Bloom Treant, Cinder, an Amber Cocoon) are catalog enemies
with `add: true` and `artFrom: <kind>`. Until they get PixelFlow sprites of their own, this adds each to the shared atlas
`client/assets/cathedral.txt` with the sprite id and label height of the kind it borrows from. Run it after any
`make_*_sprites.py export` (which rewrites the atlas), then reload the client. Safe to run twice.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / 'client/assets/cathedral.txt'
CATALOGS = ['raid_key', 'cathedral', 'seed_vault', 'solar_crucible', 'amber_archive']


def main():
    atlas = json.loads(ATLAS.read_text())
    borrowed = 0
    for name in CATALOGS:
        for enemy in json.loads((ROOT / f'world/{name}.txt').read_text()):
            source = enemy.get('artFrom')
            if not source:
                continue
            assert source in atlas['sprites'], (enemy['kind'], 'borrows from a kind with no sprite', source)
            if enemy['kind'] not in atlas['kinds']:
                atlas['kinds'].append(enemy['kind'])
            atlas['sprites'][enemy['kind']] = atlas['sprites'][source]
            atlas['tops'][enemy['kind']] = atlas['tops'][source]
            borrowed += 1
    ATLAS.write_text(json.dumps(atlas, indent=2) + '\n')
    print(f'{borrowed} helpers borrow art')


if __name__ == '__main__':
    main()
