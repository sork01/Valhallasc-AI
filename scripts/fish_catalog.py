#!/usr/bin/env python3
"""Idempotent fishing item overlay. Roster files own IDs; unrelated items keep order."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(root=ROOT):
    return [json.loads((root / 'world' / name).read_text())
            for name in ('fish.txt', 'rods.txt', 'fishing-loot.txt')]


def pieces(root=ROOT):
    fish, rods, loot = load(root)
    out = []
    for s in fish:
        out.append(dict(id=s['item'], name=s['name'], kind='fish', rarity=s['rarity'],
                        sell=s['sell'], requiredLevel=s['level'], heal=s['raw_heal'],
                        duration=8, cooldown=30, fishing=dict(habitat=s['habitat'],
                        minTier=s['min_tier'], kg=s['kg'], dish=s['dish'])))
    for r in rods:
        out.append(dict(id=r['item'], name=r['name'], kind='rod', rarity='common',
                        sell=r['sell'], requiredLevel=r['level'],
                        fishing=dict(tier=r['tier'], lava=r['lava'], zones=r['zones'], richZones=r['richZones'])))
    for row in loot:
        out.append(dict(id=row['item'], name=row['name'], kind='material',
                        rarity=row['rarity'], sell=row['sell'],
                        fishing=dict(loot=row['category'])))
    from consumable_tiers import fishing_dishes
    out.extend(fishing_dishes(fish))
    ids = [i['id'] for i in out]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate fishing item ID')
    if any(i.get('source') == 'orange_pool' or i['kind'] not in ('fish', 'rod', 'material', 'food') for i in out):
        raise ValueError('Fishing cannot generate equipment')
    return out


def apply(items, root=ROOT):
    generated = pieces(root)
    by_id = {i['id']: i for i in generated}
    seen = set()
    out = []
    for item in items:
        key = item['id']
        if key in by_id:
            if key not in seen:
                out.append(by_id[key])
                seen.add(key)
        else:
            out.append(item)
    out.extend(i for i in generated if i['id'] not in seen)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'world/items.txt'
    text = json.dumps(apply(json.loads(path.read_text())), indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if path.read_text() != text:
            raise SystemExit('Fishing item overlay is stale')
    else:
        path.write_text(text)
    print('Fishing catalogue:', len(pieces()), 'items')


if __name__ == '__main__':
    main()
