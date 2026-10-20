"""Expand the existing Linen Satchel traders after any zone generator runs.

Run through sync-world.cjs. world/map.txt and world/items.txt remain the source
of truth, and the pass is idempotent. Python preserves the generators' 9.0
coordinates when writing their JSON.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIERS = [
    ('linen_satchel', 'Linen Satchel', 1, 6, 500),
    ('adventurer_satchel', 'Adventurer Satchel', 10, 8, 1500),
    ('trail_pack_l20', 'Trail Pack', 20, 10, 4000),
    ('ranger_pack_l30', 'Ranger Pack', 30, 12, 9000),
    ('expedition_pack_l40', 'Expedition Pack', 40, 14, 18000),
    ('traveler_pack', 'Traveler Pack', 50, 16, 35000),
    ('pathfinder_pack_l60', 'Pathfinder Pack', 60, 18, 60000),
    ('warden_pack_l70', 'Warden Pack', 70, 20, 100000),
    ('hero_pack_l80', 'Hero Pack', 80, 22, 160000),
    ('sovereign_pack_l90', 'Sovereign Pack', 90, 24, 240000),
]


def apply(world, items):
    changed = False
    for item_id, name, level, slots, price in TIERS:
        item = next((entry for entry in items if entry['id'] == item_id), None)
        expected = dict(id=item_id, name=name, kind='bag', rarity='common',
                        requiredLevel=level, sell=price, price=price, bagSlots=slots)
        if item is None:
            items.append(expected)
            changed = True
        else:
            for key, value in expected.items():
                if item.get(key) != value:
                    item[key] = value
                    changed = True
    traders = 0
    for zone in [world, *world.get('zones', [])]:
        for npc in zone.get('npcs', []):
            offers = npc.get('offers', [])
            if not any(offer.get('bag') == 'linen_satchel' for offer in offers):
                continue
            traders += 1
            for item_id, name, level, slots, price in TIERS:
                offer_id = 'satchel' if level == 1 else f'bag_l{level}'
                expected = dict(id=offer_id, label=f'Buy {name} · {slots} extra bag slots',
                                cost=price, bag=item_id)
                offer = next((entry for entry in offers if entry['id'] == offer_id), None)
                if offer is None:
                    offers.append(expected)
                    changed = True
                else:
                    for key, value in expected.items():
                        if offer.get(key) != value:
                            offer[key] = value
                            changed = True
    if not traders:
        raise ValueError('No bag traders found in world/map.txt')
    return changed, traders


def sync():
    map_path = ROOT / 'world/map.txt'
    item_path = ROOT / 'world/items.txt'
    world = json.loads(map_path.read_text())
    items = json.loads(item_path.read_text())
    changed, traders = apply(world, items)
    if changed:
        map_path.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')
        item_path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')
    return changed, traders


if __name__ == '__main__':
    changed, traders = sync()
    print(f'Bag tiers {"updated" if changed else "already current"} for {traders} traders')
