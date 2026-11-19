#!/usr/bin/env python3
"""Seahorse quest source, regeneration, unchanged world and acquisition access."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import seahorse_quest as source
if os.environ.get('MUTATE')=='quest':
    source.install=lambda world: None

class Seahorse(unittest.TestCase):
    def test_overlay_is_exact_stable_and_preserves_every_other_zone_and_quest(self):
        base=json.loads(subprocess.check_output(['git','show','054e7619:world/map.txt'],cwd=ROOT))
        actual=json.loads((ROOT/'world/map.txt').read_text())
        candidate=copy.deepcopy(base);source.install(candidate)
        self.assertTrue(candidate==actual,'only the seahorse quest may change the released world')
        again=copy.deepcopy(candidate);source.install(again);self.assertTrue(again==candidate,'second overlay is stable')
        self.assertTrue(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'==(ROOT/'world/map.txt').read_text(),'canonical map bytes')
        areas=[actual,*actual['zones']]
        quests=[(i,q) for i,a in enumerate(areas) for q in a['quests'] if q.get('rewardMount')=='seahorse']
        self.assertEqual(len(quests),1);zone,q=quests[0]
        self.assertEqual(zone,8);self.assertEqual(q['id'],'deep_seahorse');self.assertFalse(q['repeatable'])
        self.assertEqual(q['npc'],'deep_healer');self.assertEqual(q['requires'],'deep_welcome')
        self.assertEqual(q['level'],35)
        levels=json.loads((ROOT/'world/levels.txt').read_text());self.assertEqual(q['rewardXp'],levels[34]//10)
        fish={f['item']:f for f in json.loads((ROOT/'world/fish.txt').read_text())}
        self.assertEqual([(o['target'],o['count']) for o in q['objectives']],[('fish_pier_sprat',10),('fish_saltby_herring',5)])
        for o in q['objectives']:
            self.assertEqual(o['kind'],'bring');f=fish[o['target']]
            self.assertEqual(f['habitat'],'Shore');self.assertEqual(f['min_tier'],1);self.assertIsNone(f['zone'])
        sync=(ROOT/'scripts/sync-world.cjs').read_text()
        self.assertLess(sync.index("'seahorse_quest.py'"),sync.index('const map ='))
        client=(ROOT/'client/world.js').read_text().split('window.WORLD_MAP = ',1)[1].rstrip(';\n')
        self.assertTrue(json.loads(client)==actual,'released client map equals authoritative map')

if __name__=='__main__':unittest.main()
