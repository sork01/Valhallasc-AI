#!/usr/bin/env python3
"""Move saved characters into the shaped zones' new frames (SHAPE-MIGRATE, docs/zone-shapes.md).

A shaped zone keeps its old square as a core translated by `shape.offset`, so a character saved at (x, y) in zone z
stands at (x + ox, y + oy) afterwards. Fog bits of those zones are reset (the sector grid changed with the size).

  python3 scripts/zone_shapes_migrate.py --db <sqlite file>            dry run
  python3 scripts/zone_shapes_migrate.py --db <sqlite file> --apply    write (service stopped, backup first)

Never point this at the live database while the server runs; the beta uses a copy made with sqlite's backup API.
"""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def offsets():
    world = json.loads((ROOT / 'world/map.txt').read_text())
    zones = [world] + world['zones']
    return {i: z['shape']['offset'] for i, z in enumerate(zones) if z.get('shape')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    off = offsets()
    c = sqlite3.connect(args.db)
    moved = 0
    for id_, state in c.execute('select id, state from characters').fetchall():
        d = json.loads(state)
        z = d.get('zone', 0)
        if z not in off:
            continue
        d['x'] += off[z][0]
        d['y'] += off[z][1]
        ex = d.get('explored')
        if isinstance(ex, list):
            for k in off:
                if k < len(ex):
                    ex[k] = 0
        moved += 1
        if args.apply:
            c.execute('update characters set state=? where id=?', (json.dumps(d, separators=(',', ':')), id_))
    if args.apply:
        c.commit()
    print(f"{'moved' if args.apply else 'would move'} {moved} characters in zones {sorted(off)} by {off}")


if __name__ == '__main__':
    main()
