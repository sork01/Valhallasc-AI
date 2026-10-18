#!/usr/bin/env python3
"""Write `tops` (health-bar height: foot anchor minus the highest idle pixel) into enemy manifests.

usage: python3 scripts/zone_tops.py crags [rime fen ...]   (names of client/assets/<name>.txt)
The zone export scripts rewrite their manifest without `tops`, so run this after every export. field.js copies
`tops` into SLIME[kind].top when the atlas loads.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / 'client/assets'


def main(names):
    for name in names:
        path = ASSETS / f'{name}.txt'
        meta = json.loads(path.read_text())
        w, h = meta['frame']
        ay = meta['anchor'][1]
        count = meta['clips']['idle']['n']
        tops = {}
        for kind in meta['kinds']:
            atlas = np.array(Image.open(ASSETS / f'{name}_{kind}.png').convert('RGBA'))
            row = atlas[:h, :w * count, 3] > 0
            tops[kind] = int(ay - np.nonzero(row.any(axis=1))[0].min())
        meta['tops'] = tops
        path.write_text(json.dumps(meta, indent=2) + '\n')
        print(name, tops)


if __name__ == '__main__':
    main(sys.argv[1:])
