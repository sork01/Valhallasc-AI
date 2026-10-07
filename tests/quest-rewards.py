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
        ]:
            with self.subTest(generator=source):
                code = (ROOT / 'scripts' / source).read_text()
                self.assertIn('from quest_gear_rewards import add_reward', code)
                self.assertIn('return add_reward(', code)


if __name__ == '__main__':
    unittest.main()
