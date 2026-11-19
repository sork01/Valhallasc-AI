#!/usr/bin/env python3
"""Focused fishing catalogue, shore reachability and overlay stability checks."""
import copy
import json
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fishing_spots as spots
import fish_catalog as catalog

if os.environ.get('MUTATE') == 'clearance':
    spots.clear_of_hubs_and_seams = lambda *args, **kwargs: True
if os.environ.get('MUTATE') == 'catalog':
    original = catalog.pieces
    def broken_pieces(*args, **kwargs):
        result = original(*args, **kwargs)
        result[0]['kind'] = 'material'
        return result
    catalog.pieces = broken_pieces


class FishingData(unittest.TestCase):
    def test_catalogue_and_unrelated_items(self):
        items = json.loads((ROOT / 'world/items.txt').read_text())
        generated = catalog.pieces()
        actual = {i['id']: i for i in items}
        self.assertEqual(len(actual), len(items))
        self.assertTrue(all(actual[i['id']] == i for i in generated))
        self.assertEqual(catalog.apply(catalog.apply(items)), items)
        sentinel = dict(id='unrelated', kind='material', sell=7)
        self.assertEqual(catalog.apply([sentinel])[0], sentinel)
        fish, rods, loot = catalog.load()
        self.assertEqual(len([i for i in items if i['kind'] == 'fish']), len(fish))
        self.assertEqual(len([i for i in items if i['kind'] == 'rod']), len(rods))
        for habitat in set(spots.HABITATS.values()):
            pool = [f for f in fish if f['habitat'] == habitat]
            for rarity in ('common', 'uncommon', 'rare', 'legendary'):
                self.assertTrue(any(f['rarity'] == rarity for f in pool), (habitat, rarity))
        for row in fish:
            self.assertGreater(row['sell'], 0)
            self.assertGreater(row['raw_heal'], 0)
            self.assertLessEqual(row['kg'][0], row['kg'][1])
            self.assertTrue(row['dish'].startswith('dish_'))
            self.assertTrue(any(r['tier'] >= row['min_tier'] and (row['habitat'] != 'Lava' or r['lava']) for r in rods))
        self.assertEqual({r['tier'] for r in rods}, set(range(1, 9)))
        self.assertEqual({r['tier'] for r in rods if r['lava']}, set(range(2, 9)))
        self.assertEqual({r['category'] for r in loot}, {'junk', 'treasure'})
        self.assertTrue(all(i['kind'] in ('fish', 'rod', 'material', 'food') and 'source' not in i for i in generated))

    def test_reachable_shore_and_liquid(self):
        world = json.loads((ROOT / 'world/map.txt').read_text())
        areas = [world, *world['zones']]
        points = json.loads((ROOT / 'world/fishing-spots.txt').read_text())
        self.assertEqual({p['zone'] for p in points}, set(spots.HABITATS))
        self.assertEqual(len({p['id'] for p in points}), len(points))
        for z in spots.HABITATS:
            area = areas[z]
            reach = spots.walkable(area)
            pool = [p for p in points if p['zone'] == z]
            self.assertEqual(area['fishingSpots'], pool)
            self.assertGreaterEqual(len(pool), 2)
            for p in pool:
                x, y = p['shore']['x'], p['shore']['y']
                self.assertTrue(reach[int(y*2), int(x*2)], p['id'])
                self.assertTrue(3 <= math.hypot(p['x']-x, p['y']-y) <= 6, p['id'])
                liquid = [o for o in area['objects'] if o['kind'] in spots.SURFACES and
                          (o['kind'] in ('lava', 'ew_lava')) == (p['habitat'] == 'Lava')]
                self.assertTrue(any(math.hypot(p['x']-o['x'], p['y']-o['y']) < spots.radius(o) for o in liquid), p['id'])
                # Full seam polylines, measured independently of the generator's edge lookup.
                for portal in area.get('portals', []):
                    if not portal.get('seam'):
                        continue
                    for a, b in zip(portal['seam']['points'], portal['seam']['points'][1:]):
                        for q in (p, p['shore']):
                            self.assertGreaterEqual(spots.segment_distance(q['x'], q['y'], a, b), 18, p['id'])
                for hub in ([area['city']] if area.get('city') else []) + area.get('camps', []):
                    for q in (p, p['shore']):
                        d = math.hypot(max(hub['x0']-q['x'], 0, q['x']-hub['x1']), max(hub['y0']-q['y'], 0, q['y']-hub['y1']))
                        self.assertGreaterEqual(d, 10, p['id'])

    def test_stable_overlay(self):
        world = json.loads((ROOT / 'world/map.txt').read_text())
        first, second = spots.build(world), spots.build(world)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, indent=2, ensure_ascii=False)+'\n', (ROOT / 'world/fishing-spots.txt').read_text())
        before = copy.deepcopy(world)
        spots.install(world, first)
        self.assertEqual(before, world)
        sync = (ROOT / 'scripts/sync-world.cjs').read_text()
        self.assertGreater(sync.index("'fishing_spots.py'"), sync.index("'apply'"))
        self.assertGreater(sync.index("'fish_catalog.py'"), sync.rindex("'vendor_weapons.py'"))


if __name__ == '__main__':
    unittest.main()
