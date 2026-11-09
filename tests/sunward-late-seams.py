#!/usr/bin/env python3
"""What each approved neighbour of Sunward Vale may keep near its (late) seam with Sunward Vale (zone 20), measured on world/map.txt.

A plain seam draws the other side's scenery with City.art but NO people and no art-less objects, so near the line: nobody and nothing art-less within 20 tiles, no loose scenery
within 2.5, no spawn within 7 (a hero must not wake a pack while crossing), no water or lava drawn that the other side cannot (16 tiles). Elites and ambush sleepers are only REPORTED
(an approved zone is not reshuffled): awareness + 3 tiles. Exit status 1 when a hard rule is broken.

    python3 tests/sunward-late-seams.py [map.txt]
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SUN = 20
PARTNERS = (19, 21, 22, 23, 25, 26)
ARTLESS = ('house', 'tent', 'stall', 'noticeboard', 'campfire', 'brazier', 'bench', 'lamp', 'chapel', 'post')
LIQUID = ('water', 'ew_lava', 'lava', 'jungle_water', 'jade_pool')


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / max(dx * dx + dy * dy, 1e-9)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def line_dist(p, pts):
    return min(seg_dist(p, a, b) for a, b in zip(pts, pts[1:]))


def audit(world, report=None):
    hard = []
    zones = [world] + world['zones']
    for zi in PARTNERS:
        z = zones[zi]
        seam = next((p for p in z['portals'] if p.get('seam') and p['to'] == SUN), None)
        if not seam:
            hard.append(f'zone {zi} has no seam to Sunward Vale')
            continue
        pts = seam['seam']['points']
        d = lambda x, y: line_dist((x, y), pts)
        for n in z['npcs']:
            if d(n['x'], n['y']) < 20:
                hard.append(f"zone {zi}: person {n['id']} stands {d(n['x'], n['y']):.1f} tiles from the Sunward seam")
        for o in z['objects']:
            if o['kind'] == 'void':
                continue
            k = d(o['x'], o['y'])
            if o['kind'] in ARTLESS and k < 20:
                hard.append(f"zone {zi}: art-less {o['kind']} at {o['x']},{o['y']} stands {k:.1f} tiles from the Sunward seam")
            if o['kind'] in LIQUID and k < 16 and (o.get('r') or 0) > 0:
                hard.append(f"zone {zi}: {o['kind']} at {o['x']},{o['y']} stands {k:.1f} tiles from the Sunward seam")
            if o.get('layout') and k < 2.5:
                hard.append(f"zone {zi}: loose {o['kind']} at {o['x']},{o['y']} stands {k:.1f} tiles from the Sunward seam")
        for s in z['slimes']:
            k = d(s['x'], s['y'])
            if k < 7 and not s.get('ambush'):
                hard.append(f"zone {zi}: spawn {s['kind']} at {s['x']},{s['y']} stands {k:.1f} tiles from the Sunward seam")
        if report is not None:
            from collections import defaultdict
            for s in z['slimes']:
                if s.get('ambush') or s['kind'] in ('snowhare',):
                    pass
            report.append((zi, [(s['kind'], s['x'], s['y'], round(d(s['x'], s['y']), 1)) for s in z['slimes'] if d(s['x'], s['y']) < 24 and (s.get('ambush') or not s.get('layout'))]))
    return hard


if __name__ == '__main__':
    w = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'world/map.txt').read_text())
    rep = []
    bad = audit(w, rep)
    for zi, rows in rep:
        print(f'zone {zi}: authored spawns (elites, sleepers) within 24 tiles of the Sunward seam: {rows}')
    for b in bad:
        print('FAIL', b)
    print(f'{len(bad)} hard problems')
    sys.exit(1 if bad else 0)
