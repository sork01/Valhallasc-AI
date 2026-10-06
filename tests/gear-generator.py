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
        self.assertEqual(len(new) - len(old), 672)
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


if __name__ == '__main__':
    unittest.main()
