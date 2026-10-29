#!/usr/bin/env python3
"""Export female body/outfit candidates without rewriting other gear or metadata.

Usage: python3 scripts/export_character_torso.py warrior --out <candidate-dir>
The existing female rigs are generated assets, with no editable PixelFlow IDs.
Install only the checked PNG/depth files and matching bounds after visual review.
"""
import argparse
import base64
import importlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODULES = {c: f'make_{c}_cel_sprites' for c in ['warrior', 'mage', 'assassin', 'hunter']}
MODULES['priest'] = 'make_priest_sprites'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('character', choices=MODULES)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    sys.argv.append('--female')
    maker = importlib.import_module(MODULES[args.character])
    import cel_common as cc
    import sprite_bounds
    assert cc.FEMALE
    sheet = maker.SHEET
    assets = ROOT / 'client/assets'
    meta_path = assets / f'{sheet.files}_sprites.txt'
    meta = json.loads(meta_path.read_text())
    assert not meta['sprites'], 'Do not overwrite editable sprite layers'
    parts = [p for p in sheet.parts if p == 'body' or p.startswith('armor_')]
    args.out.mkdir(parents=True, exist_ok=True)
    cc.ASSETS = args.out
    sheet.groups = {'torso': parts}
    sheet.export(local=True, only=['torso'])
    # Preserve the actual catalog, palettes, gear references and clip layout.
    (args.out / meta_path.name).write_bytes(meta_path.read_bytes())
    bounds_path = assets / f'{sheet.files}_bounds.txt'
    bounds = json.loads(bounds_path.read_text())
    frames = 0
    for part in parts:
        name = meta['parts'][part]['png']
        image = np.asarray(Image.open(args.out / name).convert('RGBA'))
        for clip in meta['clips'].values():
            for direction in range(8):
                for k in range(clip['n']):
                    cell = image[(clip['row0']+direction)*160:(clip['row0']+direction+1)*160, k*160:(k+1)*160, 3]
                    assert cell.any() and not cell[[0, -1], :].any() and not cell[:, [0, -1]].any(), (part, direction, k, 'empty/clipped')
                    frames += 1
        bounds['parts'][part] = base64.b64encode(sprite_bounds.part_bounds(args.out / name, meta)).decode()
    (args.out / bounds_path.name).write_text(json.dumps(bounds, separators=(',', ':')) + '\n')
    print(f'{sheet.files}: {frames} body/outfit frames checked', flush=True)


if __name__ == '__main__':
    main()
