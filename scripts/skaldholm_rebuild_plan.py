#!/usr/bin/env python3
"""Skaldholm rebuild, stage 1 (read-only): what the four neighbours' walls enclose and where the old city goes.

  python3 scripts/skaldholm_rebuild_plan.py [OUT.png]

Reads world/map.txt (the PILOT map: Greenmeadow, Crags, Rimeveil and Gloamfen shaped, Skaldholm still the old 126 x 126 square),
flood-fills the ground the four neighbours do not own (atlas frame = tile + shape.T), then cuts the old city: the middle strip
OLD_X0..OLD_X1 translates rigidly into the north part of that L, everything outside the strip is listed for the south band.
Writes nothing to the map. docs/skaldholm-rebuild.md has the reasoning."""
import collections
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OLD_X0, OLD_X1 = 38.5, 123.5            # the strip of the old city that stays rigid (85 wide = the north part of the L)
DX, DY = 331.5, 587.0                   # old city frame -> atlas frame for that strip (avenue x 80 -> 411.5, trade road y 76 -> 663)
GATES = {'N Rimeveil': (411, 601), 'E Crags': (452, 663), 'W Gloamfen': (371, 703), 'S Greenmeadow': (438, 755)}


def enclosed(world):
    zones = [world] + world['zones']
    ids = {0: 0, 1: 1, 2: 2, 3: 3}
    occ = {}
    for zi in (0, 1, 2, 3):
        z = world if zi == 0 else world['zones'][zi - 1]
        T = z['shape']['T']
        for y, row in enumerate(z['shapeFloor']):
            for x, c in enumerate(row):
                if c == '#':
                    occ[(x + T[0], y + T[1])] = zi
    X0, Y0, W, H = 340, 570, 200, 230
    seen = np.zeros((H, W), bool)
    stack = [(420 - X0, 690 - Y0)]
    seen[stack[0][1], stack[0][0]] = True
    while stack:
        a, b = stack.pop()
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            u, v = a + da, b + db
            if 0 <= u < W and 0 <= v < H and not seen[v, u] and (u + X0, v + Y0) not in occ:
                seen[v, u] = True
                stack.append((u, v))
    return seen, X0, Y0


def main():
    world = json.loads((ROOT / 'world/map.txt').read_text())
    city = world['zones'][3]
    assert city['name'] == 'Skaldholm' and 'shape' not in city, 'run this on the unshaped city'
    mask, X0, Y0 = enclosed(world)
    print('enclosed L:', int(mask.sum()), 'tiles')
    inA = lambda x, y: OLD_X0 <= x < OLD_X1 and 13 <= y < 139.5
    inbox = lambda x, y: 17 <= x <= 143 and 13 <= y <= 139
    keep, strip = collections.Counter(), collections.Counter()
    for o in city['objects']:
        if inbox(o['x'], o['y']) and o['kind'] not in ('rampart', 'tower'):
            (keep if inA(o['x'], o['y']) else strip)[o['kind']] += 1
    print('rigid strip keeps', dict(keep))
    print('goes to the south band', dict(strip))
    print('NPCs for the band:', [n['id'] for n in city['npcs'] if not inA(n['x'], n['y'])])
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'skaldholm-rebuild-plan.png')
    sc, ax0, ay0 = 6, 360, 590
    im = Image.new('RGB', (160 * sc, 190 * sc), (30, 30, 30))
    d = ImageDraw.Draw(im)
    for y, x in zip(*np.nonzero(mask)):
        d.rectangle([(x + X0 - ax0) * sc, (y + Y0 - ay0) * sc, (x + X0 - ax0 + 1) * sc - 1, (y + Y0 - ay0 + 1) * sc - 1], fill=(70, 100, 70))
    px, py = lambda x: (x + DX - ax0) * sc, lambda y: (y + DY - ay0) * sc
    for r in city['roads']:
        if 'x0' in r:
            x0, x1 = max(r['x0'], OLD_X0), min(r['x1'], OLD_X1)
            if x1 > x0:
                d.rectangle([px(x0), py(r['y0']), px(x1), py(min(r['y1'], 139))], fill=(130, 120, 100))
        else:
            rr = r.get('r', r.get('r1'))
            d.ellipse([px(r['x'] - rr), py(r['y'] - rr), px(r['x'] + rr), py(r['y'] + rr)], fill=(150, 140, 110))
    for o in city['objects']:
        if o['kind'] in ('rampart', 'tower') or not inA(o['x'], o['y']):
            continue
        if o.get('width'):
            d.rectangle([px(o['x'] - o['width'] / 2), py(o['y'] - o['depth'] / 2), px(o['x'] + o['width'] / 2), py(o['y'] + o['depth'] / 2)], fill=(184, 116, 78), outline=(0, 0, 0))
        else:
            rr = max(o.get('r', 1), .6)
            d.ellipse([px(o['x'] - rr), py(o['y'] - rr), px(o['x'] + rr), py(o['y'] + rr)], fill=(30, 110, 30) if o['kind'] in ('tree', 'bush') else (255, 255, 0))
    for name, (gx, gy) in GATES.items():
        d.ellipse([(gx - ax0) * sc - 8, (gy - ay0) * sc - 8, (gx - ax0) * sc + 8, (gy - ay0) * sc + 8], outline=(255, 0, 255), width=3)
    im.save(out)
    print('plan ->', out)


if __name__ == '__main__':
    main()
