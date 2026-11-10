#!/usr/bin/env python3
"""Roll the NPC art back to the pre-player-style set: rollback_npc_art.py [--backup DIR] [--apply]  (dry run by default).

Restores client/assets/npc.txt and every npc_*.png from the backup (default /media/raid/valhallasc-data/npc-style-original-20261110, taken
before the player-style remake). The old PixelFlow ids are inside that npc.txt, so nothing else is needed. The new npcp_* atlases and
npcp.txt are left in place (they are inert until a client wiring reads them); pass --drop-new to delete them too.
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client/assets'
ap = argparse.ArgumentParser()
ap.add_argument('--backup', default='/media/raid/valhallasc-data/npc-style-original-20261110')
ap.add_argument('--apply', action='store_true')
ap.add_argument('--drop-new', action='store_true')
a = ap.parse_args()
src = Path(a.backup)
files = sorted([src / 'npc.txt', *src.glob('npc_*.png')])
assert files and (src / 'npc.txt').exists(), f'no backup in {src}'
changed = 0
for f in files:
    dst = ASSETS / f.name
    same = dst.exists() and dst.read_bytes() == f.read_bytes()
    changed += not same
    print(('same     ' if same else 'RESTORE  ') + f.name)
    if a.apply and not same:
        shutil.copy2(f, dst)
if a.drop_new:
    for f in [*ASSETS.glob('npcp_*.png'), ASSETS / 'npcp.txt']:
        if f.exists():
            print('REMOVE   ' + f.name)
            if a.apply:
                f.unlink()
print(f'{len(files)} files, {changed} differ;', 'applied' if a.apply else 'dry run (pass --apply)')
