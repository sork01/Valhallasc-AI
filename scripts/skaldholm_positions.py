#!/usr/bin/env python3
"""After the Skaldholm rebuild: characters saved in zone 4 carry coordinates of the old square city.

  python3 scripts/skaldholm_positions.py --db FILE [--apply]    service stopped, backup first; never on the live database.

Someone standing in the rigid strip (old x 38.5-123.5, y 13-139.5) moves with it (the same translation as skaldholm_rebuild.py); anyone
outside it, or who would land inside scenery or off the ground, goes to the new spawn. Run it ONCE per old-layout database."""
import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import skaldholm_rebuild as sk  # noqa: E402

CITY = 4


def solid(world, x, y):
    if not (0 <= int(x) < world['size'] and 0 <= int(y) < world['size']) or world['shapeFloor'][int(y)][int(x)] != '#':
        return True
    for o in world['objects']:
        if o['kind'] == 'void':
            continue
        w, d = o.get('width', 0), o.get('depth', 0)
        if w > 0 and d > 0:
            if abs(x - o['x']) < w / 2 + .3 and abs(y - o['y']) < d / 2 + .3:
                return True
        elif math.hypot(x - o['x'], y - o['y']) < o['r'] + .3:
            return True
    return False


def settle(a):
    full = json.loads((ROOT / 'world/map.txt').read_text())
    zones = {0: full, CITY: full['zones'][CITY - 1]}
    db = sqlite3.connect(a.db)
    moved = seen = 0
    for rid, state in db.execute('select rowid, state from characters').fetchall():
        c = json.loads(state)
        z = zones.get(c.get('zone', 0))
        if z is None:
            continue
        seen += 1
        if solid(z, c['x'], c['y']):
            print('to the spawn:', c.get('name'), c.get('zone', 0), round(c['x'], 1), round(c['y'], 1))
            c['x'], c['y'] = z['spawn']['x'], z['spawn']['y']
            moved += 1
            if a.apply:
                db.execute('update characters set state=? where rowid=?', (json.dumps(c), rid))
    if a.apply:
        db.commit()
    print(f'{seen} characters in Greenmeadow or Skaldholm, {moved} {"moved" if a.apply else "would move"}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--settle', action='store_true', help='only move characters of Skaldholm and Greenmeadow who stand inside scenery or off the ground to the spawn (a later layout change)')
    a = ap.parse_args()
    if a.settle:
        return settle(a)
    world = json.loads((ROOT / 'world/map.txt').read_text())['zones'][CITY - 1]
    assert world['name'] == 'Skaldholm' and 'shape' in world, 'the map is not rebuilt'
    db = sqlite3.connect(a.db)
    seen = kept = sent = 0
    for rid, state in db.execute('select rowid, state from characters').fetchall():
        c = json.loads(state)
        if c.get('zone', 0) != CITY:
            continue
        seen += 1
        if sk.in_strip(c['x'], c['y']):
            x, y = sk.mv(c['x'], c['y'])
        else:
            x = y = None
        if x is None or solid(world, x, y):
            x, y = world['spawn']['x'], world['spawn']['y']
            sent += 1
            print('to the spawn:', c.get('name'), round(c['x'], 1), round(c['y'], 1))
        else:
            kept += 1
        c['x'], c['y'] = x, y
        if a.apply:
            db.execute('update characters set state=? where rowid=?', (json.dumps(c), rid))
    if a.apply:
        db.commit()
    print(f'{seen} characters in Skaldholm: {kept} moved with the strip, {sent} to the spawn ({"applied" if a.apply else "dry run"})')


if __name__ == '__main__':
    main()
