"""A cloak seen from behind covers the wearer's armour and trousers down to its hem.

Reads the real client atlases and repeats the compositor's depth test. For every rig, cloak style, armour and
frame of the chosen clips, seen from NW, N and NE: wherever the cloak and the armour or trousers share a pixel,
the cloak must be the nearer one (a small allowance for seams at the shoulders).

Env: CLOAK_DIR=<dir> reads the cloak atlases from another folder (the art before the fix must fail),
RIGS='hunter,mage_f', STYLES='travel,mantle', ARMOURS=<n per rig, default all>, CLIPS='idle,walk'.
"""
import json
import os
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; ASSETS = ROOT / 'client/assets'
CLOAKS = Path(os.environ.get('CLOAK_DIR', ASSETS))
RIGS = os.environ.get('RIGS', 'warrior_layered,warrior_layered_f,assassin,assassin_f,mage,mage_f,priest,priest_f,hunter,hunter_f').split(',')
STYLES = os.environ.get('STYLES', 'travel,hooded,mantle,clasp,ember').split(',')
CLIPS = os.environ.get('CLIPS', 'idle,walk').split(',')
LIMIT = int(os.environ.get('ARMOURS', '0'))
ALLOWED = .04


def layers(folder, record, meta, rows):
    """{(clip, facing): (opaque, depth)} with every frame of the row side by side."""
    colour = Image.open(folder / record['png']).convert('RGBA'); depth = Image.open(folder / record['depth']).convert('RGB')
    fw, fh = meta['frame']; out = {}
    for clip, facing in rows:
        C = meta['clips'][clip]; y = (C['row0'] + meta['dirs'].index(facing)) * fh; box = (0, y, C['n'] * fw, y + fh)
        d = np.asarray(depth.crop(box)).astype(np.int32)
        out[clip, facing] = (np.asarray(colour.crop(box))[..., 3] > 0, d[..., 0] * 256 + d[..., 1])
    return out


def main():
    checks = 0; failures = []
    for rig in RIGS:
        meta = json.loads((ASSETS / f'{rig}_sprites.txt').read_text())
        rows = [(clip, facing) for clip in CLIPS for facing in ('NW', 'N', 'NE')]
        armours = [p for p in meta['parts'] if p.startswith('armor_')]
        if LIMIT: armours = armours[:LIMIT]
        pants = layers(ASSETS, meta['parts']['pants_wayfarer'], meta, rows)
        cloaks = {s: layers(CLOAKS, meta['parts']['cloak_' + s], meta, rows) for s in STYLES}
        assert armours, rig
        for armour in armours:
            worn = layers(ASSETS, meta['parts'][armour], meta, rows)
            for style, cloak in cloaks.items():
                for row in rows:
                    cover, cz = cloak[row]
                    assert cover.sum() > 300 * meta['clips'][row[0]]['n'], (rig, style, row, 'cloak too small from behind')
                    shared = through = 0
                    for opaque, z in (worn[row], pants[row]):
                        both = cover & opaque; shared += int(both.sum()); through += int((both & (z < cz)).sum())
                    checks += 1
                    if shared and through > shared * ALLOWED:
                        failures.append(f'{rig} {style} {armour} {row[0]}/{row[1]}: {through} of {shared} shared pixels show through')
    if failures:
        print('\n'.join(failures[:20])); print(f'FAIL {len(failures)} of {checks}'); sys.exit(1)
    print(f'PASS {checks} cloak-over-armour rows seen from behind')


if __name__ == '__main__':
    main()
