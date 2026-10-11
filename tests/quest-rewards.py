"""The quest reward table, map, item catalog and generators must stay aligned."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import quest_gear_rewards  # noqa: E402


class QuestGearRewards(unittest.TestCase):
    def test_every_assignment_exists_in_the_map_and_gear_catalog(self):
        world = json.loads((ROOT / 'world/map.txt').read_text())
        quests = {q['id']: q for zone in [world, *world['zones']] for q in zone.get('quests', [])}
        items = {i['id']: i for i in json.loads((ROOT / 'world/items.txt').read_text())}
        for quest_id, reward_id in quest_gear_rewards.REWARDS.items():
            with self.subTest(quest=quest_id):
                quest, gear = quests[quest_id], items[reward_id]
                self.assertEqual(quest['rewardItem'], reward_id)
                self.assertFalse(quest['repeatable'])
                self.assertIn(gear['rarity'], ('uncommon', 'rare'))
                self.assertNotIn('class', gear)
                self.assertNotIn('source', gear)
                self.assertLessEqual(gear['requiredLevel'], quest['level'] + 5)

    def test_zone_generators_apply_the_shared_reward_table(self):
        for source in [
            'generate_crags.py', 'generate_rimeveil.py', 'generate_gloamfen.py',
            'skaldholm_content.py', 'wyrd_content.py', 'sky_content.py',
            'deep_content.py', 'generate_nacrehold.py', 'generate_astralhollow.py',
            'generate_prismwaste.py', 'generate_orrery.py', 'generate_moonspore.py',
        ]:
            with self.subTest(generator=source):
                code = (ROOT / 'scripts' / source).read_text()
                self.assertIn('from quest_gear_rewards import add_reward', code)
                self.assertIn('return add_reward(', code)

    def test_late_rewards_are_class_legal_and_yearwheel_is_varied(self):
        world = json.loads((ROOT / 'world/map.txt').read_text())
        quests = {q['id']: q for zone in [world, *world['zones']] for q in zone.get('quests', [])}
        items = {i['id']: i for i in json.loads((ROOT / 'world/items.txt').read_text())}
        for q in quests.values():
            for cls, choices in q.get('rewardChoices', {}).items():
                self.assertIn(cls, ('warrior', 'mage', 'assassin', 'priest', 'hunter'))
                self.assertEqual(len(choices), len(set(choices)), q['id'])
                for id in choices:
                    piece = items[id]
                    self.assertIn(piece.get('class'), (None, cls))
                    self.assertLessEqual(piece['requiredLevel'], q['level'])
        year = [q for q in quests.values() if q['id'].startswith('yr_') and q['id'].split('_')[-1] in ('1', '2', '3')]
        self.assertEqual(len(year), 12)
        self.assertEqual(len({tuple(quests[q['id']]['rewardChoices']['warrior']) for q in year}), 12)
        self.assertTrue(all('rewardItem' not in q for q in year))

    def test_dungeon_boss_objectives_and_progression_givers(self):
        from progression_quests import PROGRESSION
        world = json.loads((ROOT / 'world/map.txt').read_text())
        areas = [world, *world['zones']]
        quests = {q['id']: (zone, q) for zone, area in enumerate(areas) for q in area.get('quests', [])}
        for zone_name, (id, _, npc, level, *_rest) in PROGRESSION.items():
            zone, q = quests[id]
            self.assertEqual(areas[zone]['name'], zone_name)
            self.assertEqual((q['autoLevel'], q['level'], q['npc']), (level, level, npc))
            self.assertEqual([(o['kind'], o['target']) for o in q['objectives']], [('reach', zone_name)])
        for id, targets in {
            'city_vault_bosses': {'gatewarden', 'choir', 'colossus', 'hollowking'},
            'nacre_cloister_clear': {'bellkeeper', 'mournsister', 'rootabbot', 'choirmother'},
            'nacre_reliquary_clear': {'pearlwidow', 'glasscantor', 'relicwarden', 'coralregent'},
            'nacre_nave_clear': {'chainmarshal', 'starseraph', 'tidejudicator', 'hierophant'},
        }.items():
            zone, q = quests[id]
            self.assertTrue(q['group'])
            self.assertEqual({o['target'] for o in q['objectives']}, targets)
            self.assertEqual({o['kind'] for o in q['objectives']}, {'kill'})
            self.assertTrue(any(p['to'] != zone and targets & {s['kind'] for s in areas[p['to']]['slimes']}
                                for p in areas[zone]['portals']))


if __name__ == '__main__':
    unittest.main()
