"""Regression checks for the gear generator's preservation of saves and special items."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import gear_levels as gear


class GearGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.original_path = gear.ITEMS
        self.addCleanup(setattr, gear, 'ITEMS', self.original_path)
        gear.ITEMS = pathlib.Path(self.temp.name) / 'items.txt'
        self.catalog = json.loads(self.original_path.read_text())
        gear.ITEMS.write_text(json.dumps(self.catalog, indent=2, ensure_ascii=False) + '\n')

    def run_generator(self, fn=None):
        with contextlib.redirect_stdout(io.StringIO()):
            (fn or gear.main)()

    def test_extending_old_catalog_preserves_every_old_item_and_game_master_gear(self):
        old = [i for i in self.catalog if i.get('requiredLevel', 1) <= 20 or i['kind'] not in gear.CLASS_KINDS + gear.SHARED_KINDS]
        gear.ITEMS.write_text(json.dumps(old))
        self.run_generator()
        new = {i['id']: i for i in json.loads(gear.ITEMS.read_text())}
        self.assertEqual(len(new) - len(old), 756)
        for i in old:
            self.assertEqual(i, new[i['id']], i['id'])

    def test_full_and_vault_only_rebuilds_are_byte_stable(self):
        before = gear.ITEMS.read_bytes()
        self.run_generator()
        self.assertTrue(before == gear.ITEMS.read_bytes(), 'full rebuild changed the catalog')
        self.run_generator(gear.vault_only)
        self.assertTrue(before == gear.ITEMS.read_bytes(), 'vault-only rebuild changed the catalog')

    def test_generated_colours_never_equal_the_original_or_another_set(self):
        self.run_generator()
        seen = set()
        for i in json.loads(gear.ITEMS.read_text()):
            if not i.get('art'):
                continue
            t = i['tint']
            self.assertFalse(t['hue'] % 360 == 0 and t['saturate'] == t['brightness'] == 1, i['id'])
            key = (i.get('class'), i['kind'], i['art'], t['hue'], t['saturate'], t['brightness'])
            self.assertTrue(key not in seen, i['id'])
            seen.add(key)

    def test_blue_and_purple_bonuses_are_fixed_by_item_id_and_class_useful(self):
        self.run_generator()
        items = json.loads(gear.ITEMS.read_text())
        for item in items:
            if item['kind'] not in gear.CLASS_KINDS + gear.SHARED_KINDS or item['rarity'] == 'gm':
                continue
            bonus = item.get('bonusStats', {})
            expected = {'rare': 1, 'epic': 2}.get(item['rarity'], 0)
            self.assertEqual(len(bonus), expected, item['id'])
            self.assertEqual(bonus, gear.bonus_stats(item), item['id'])
            level = min(90, max(5, item.get('requiredLevel', 1) // 5 * 5))
            self.assertTrue(all(value == gear.ATTRIBUTE_BONUS[level] and stat in gear.bonus_choices(item.get('class'), value)
                                for stat, value in bonus.items()), item['id'])

    def test_attribute_bonus_scales_beyond_the_current_catalog(self):
        expected_by_level = {
            1: 1, 5: 1, 10: 3, 15: 5, 20: 7, 25: 10, 30: 15, 35: 20,
            40: 30, 45: 35, 50: 40, 55: 48, 60: 55, 65: 63,
            70: 70, 75: 78, 80: 85, 85: 93, 90: 100,
        }
        for level, expected in expected_by_level.items():
            blue = {'id': 'future_warrior_blue', 'class': 'warrior', 'rarity': 'rare', 'requiredLevel': level}
            purple = {'id': 'future_warrior_purple', 'class': 'warrior', 'rarity': 'epic', 'requiredLevel': level}
            self.assertEqual(list(gear.bonus_stats(blue).values()), [expected])
            self.assertEqual(sorted(gear.bonus_stats(purple).values()), [expected, expected])
            self.assertNotIn('accuracy', gear.bonus_stats(blue) if expected > 20 else {})
            self.assertNotIn('dexterity', gear.bonus_stats(purple) if expected > 70 else {})
        self.assertEqual(set(gear.bonus_choices(None, 100)), {'stamina', 'strength', 'agility'})
        for rarity, count in [('rare', 1), ('epic', 2)]:
            shared = {'id': f'future_shared_{rarity}', 'rarity': rarity, 'requiredLevel': 90}
            bonus = gear.bonus_stats(shared)
            self.assertEqual(len(bonus), count)
            self.assertTrue(set(bonus) <= {'stamina', 'strength', 'agility'})
            self.assertTrue(all(value == 100 for value in bonus.values()))


if __name__ == '__main__':
    unittest.main()
