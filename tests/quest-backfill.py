"""The one-time quest reward repair preserves old saves and cannot grant twice."""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from backfill_quest_gear import ITEMS, run  # noqa: E402


class QuestBackfill(unittest.TestCase):
    def test_claimed_quests_receive_one_reward_once(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / 'characters.sqlite'
            backup = Path(folder) / 'before.sqlite'
            before = {'look': {'name': 'Saved'}, 'inventory': [{'item': 'slime_gel', 'quantity': 4}],
                      'quests': [{'id': 'slime_patrol', 'claimed': True},
                                 {'id': 'ironhide_hunt', 'claimed': True},
                                 {'id': 'king_challenge', 'claimed': False}]}
            with sqlite3.connect(db_path) as db:
                db.execute('CREATE TABLE characters (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
                db.execute('INSERT INTO characters VALUES (?, ?)', ('saved', json.dumps(before)))
            self.assertEqual(run(db_path), (1, 2, 0))
            self.assertEqual(run(db_path, True, backup), (1, 2, 0))
            self.assertEqual(run(db_path), (0, 0, 0))
            with sqlite3.connect(backup) as db:
                self.assertEqual(json.loads(db.execute('SELECT state FROM characters').fetchone()[0]), before)
            with sqlite3.connect(db_path) as db:
                after = json.loads(db.execute('SELECT state FROM characters').fetchone()[0])
            self.assertEqual(after['look'], before['look'])
            self.assertEqual(after['quests'], before['quests'])
            self.assertEqual(after['inventory'], [
                {'item': 'slime_gel', 'quantity': 4},
                {'item': 'necklace_moonstone_l1_green', 'quantity': 1},
                {'item': 'pants_upgrade', 'quantity': 1},
            ])
            self.assertEqual(run(db_path, True, Path(folder) / 'again.sqlite'), (0, 0, 0))

    def test_overflow_gets_a_legacy_pack_and_rerun_repairs_prior_grants(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / 'characters.sqlite'
            materials = [item['id'] for item in ITEMS.values() if item['kind'] == 'material'][:16]
            state = {'look': {'class': 'warrior'}, 'bags': [],
                     'inventory': [{'item': item, 'quantity': 1} for item in materials],
                     'quests': [{'id': 'slime_patrol', 'claimed': True}]}
            with sqlite3.connect(db_path) as db:
                db.execute('CREATE TABLE characters (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
                db.execute('INSERT INTO characters VALUES (?, ?)', ('saved', json.dumps(state)))
            self.assertEqual(run(db_path), (1, 1, 1))
            self.assertEqual(run(db_path, True, Path(folder) / 'before.sqlite'), (1, 1, 1))
            self.assertEqual(run(db_path), (0, 0, 0))
            with sqlite3.connect(db_path) as db:
                after = json.loads(db.execute('SELECT state FROM characters').fetchone()[0])
            self.assertEqual(after['bags'], ['traveler_pack'])
            self.assertEqual(len(after['inventory']), 17)


if __name__ == '__main__':
    unittest.main()
