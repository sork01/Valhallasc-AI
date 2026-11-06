#!/usr/bin/env python3
"""After a Crags redesign: move characters saved in zone 1 who now stand inside scenery to the spawn point.

  python3 scripts/crags_positions.py --db FILE [--apply]    service stopped, backup first; never on the live database.
"""
import argparse
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def solid(world, x, y):
    if world['shapeFloor'][int(y)][int(x)] != '#':
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    world = json.loads((ROOT / "world/map.txt").read_text())["zones"][0]
    db = sqlite3.connect(a.db)
    moved = seen = 0
    for rid, state in db.execute('select rowid, state from characters').fetchall():
        c = json.loads(state)
        if c.get("zone", 0) != 1:
            continue
        seen += 1
        if solid(world, c['x'], c['y']):
            print('moving', c.get('name'), round(c['x'], 1), round(c['y'], 1))
            c['x'], c['y'] = world['spawn']['x'], world['spawn']['y']
            moved += 1
            if a.apply:
                db.execute('update characters set state=? where rowid=?', (json.dumps(c), rid))
    if a.apply:
        db.commit()
    print(f'{seen} characters in the Crags, {moved} {"moved" if a.apply else "would move"}')


if __name__ == '__main__':
    main()
