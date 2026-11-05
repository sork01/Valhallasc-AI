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


def offsets(path=None):
    world = json.loads((path or ROOT / 'world/map.txt').read_text())
    zones = [world] + world['zones']
    return {i: z['shape']['offset'] for i, z in enumerate(zones) if z.get('shape') and not z['shape'].get('warp')}


def warped(path=None):
    """Zones whose old layout was bent into the outline: a saved position has no simple offset, so the character is placed at the zone's spawn."""
    world = json.loads((path or ROOT / 'world/map.txt').read_text())
    zones = [world] + world['zones']
    return {i: z['spawn'] for i, z in enumerate(zones) if z.get('shape', {}).get('warp')}


def world_spawn(zone):
    world = json.loads((ROOT / 'world/map.txt').read_text())
    return ([world] + world['zones'])[zone]['spawn']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--old-map', help='re-migrate a database that already went through an earlier shape layout: map.txt of that layout '
                    '(a zone moves by new offset minus old offset; one that was warped before is placed at its spawn)')
    ap.add_argument('--zones', help='comma list: only move characters saved in these zones (already-migrated zones must be left out)')
    args = ap.parse_args()
    off = offsets()
    warp = warped()
    if args.old_map:
        prev, prev_warp = offsets(Path(args.old_map)), warped(Path(args.old_map))
        # a zone shaped in both layouts moves by the difference; one that was warped before has no usable offset: spawn
        off = {k: [v[0] - prev[k][0], v[1] - prev[k][1]] if k in prev else v for k, v in off.items()}
        warp = {**warp, **{k: world_spawn(k) for k in prev_warp if k not in warp}}
    if args.zones:
        keep = {int(v) for v in args.zones.split(',')}
        off = {k: v for k, v in off.items() if k in keep}
        warp = {k: v for k, v in warp.items() if k in keep}
    c = sqlite3.connect(args.db)
    moved = 0
    for id_, state in c.execute('select id, state from characters').fetchall():
        d = json.loads(state)
        z = d.get('zone', 0)
        if z not in off and z not in warp:
            continue
        if z in warp:
            d['x'], d['y'] = warp[z]['x'], warp[z]['y']
        else:
            d['x'] += off[z][0]
            d['y'] += off[z][1]
        ex = d.get('explored')
        if isinstance(ex, list):
            for k in list(off) + list(warp):
                if k < len(ex):
                    ex[k] = 0
        moved += 1
        if args.apply:
            c.execute('update characters set state=? where id=?', (json.dumps(d, separators=(',', ':')), id_))
    if args.apply:
        c.commit()
    print(f"{'moved' if args.apply else 'would move'} {moved} characters in zones {sorted(off)} by {off}, warped zones {sorted(warp)} to their spawn")


if __name__ == '__main__':
    main()
