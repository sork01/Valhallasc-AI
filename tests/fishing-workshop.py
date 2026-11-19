#!/usr/bin/env python3
"""Fisher overlay isolation, stability, reachability, recipes and real catalogue contracts."""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import fisher_npcs as fishers
import fish_catalog
import fishing_spots
import seahorse_quest
if os.environ.get('MUTATE')=='overlay':
    fishers.install=lambda *args: None
if os.environ.get('MUTATE')=='dishes':
    before=subprocess.check_output(['git','show','97f75da7:scripts/fish_catalog.py'],cwd=ROOT,text=True)
    exec(compile(before,'fish_catalog.py','exec'),fish_catalog.__dict__)

class Workshop(unittest.TestCase):
    def test_overlay_and_existing_world_preserved(self):
        world=json.loads((ROOT/'world/map.txt').read_text())
        original=json.loads(subprocess.check_output(['git','show','97f75da7:world/map.txt'],cwd=ROOT))
        stripped=copy.deepcopy(world)
        for area in [stripped,*stripped['zones']]:
            area['npcs']=[n for n in area['npcs'] if not n['id'].startswith('fisher_')]
            area['quests']=[q for q in area['quests'] if not q['id'].startswith('fisher_') and q['id']!=seahorse_quest.QUEST]
        self.assertTrue(stripped==original,'only new Fisher NPCs/quests and the explicit seahorse quest may change the map')
        levels=json.loads((ROOT/'world/levels.txt').read_text());levels.append(levels[-1]+2300)
        recipes=json.loads((ROOT/'world/fishing-workshop.txt').read_text());fish=json.loads((ROOT/'world/fish.txt').read_text())
        world=copy.deepcopy(original)
        fishers.install(world,recipes,fish,levels)
        seahorse_quest.install(world)
        self.assertTrue(world==json.loads((ROOT/'world/map.txt').read_text()),'Fisher and seahorse overlays reproduce the new content from the previous map')
        once=copy.deepcopy(world);fishers.install(world,recipes,fish,levels);self.assertTrue(world==once,'second overlay is stable')
        self.assertTrue(json.dumps(world,ensure_ascii=False,indent=2)+'\n'==(ROOT/'world/map.txt').read_text(),'overlay bytes are canonical and stable')
        seen=set()
        for zone,area in enumerate([world,*world['zones']]):
            people=[n for n in area['npcs'] if n['id'].startswith('fisher_')]
            if not people:continue
            reach=fishing_spots.walkable(area)
            for n in people:
                self.assertTrue(reach[int(n['y']*2),int(n['x']*2)],n['id']);seen.add(zone)
                others=copy.deepcopy(area);others['npcs']=[p for p in others['npcs'] if p['id']!=n['id']]
                self.assertTrue(fishers.safe(others,reach,n['x'],n['y']),n['id'])
                qs=[q for q in area['quests'] if q['npc']==n['id']]
                self.assertEqual(len(qs),4)
                for q in qs:
                    self.assertEqual(q['rewardXp'],levels[q['level']-1]//10)
                    self.assertTrue(q['objectives'][0]['target'].startswith('fish_'))
        self.assertEqual(seen,set(fishing_spots.HABITATS))
    def test_recipes_have_no_progression_deadlock_and_dishes_are_meals(self):
        actual=json.loads((ROOT/'world/items.txt').read_text());items={i['id']:i for i in actual}
        original_items=json.loads(subprocess.check_output(['git','show','97f75da7:world/items.txt'],cwd=ROOT))
        previous_ids={i['id'] for i in original_items}
        self.assertEqual([i['id'] for i in actual if i['id'] in previous_ids],[i['id'] for i in original_items],'unrelated catalogue order is preserved')
        self.assertTrue(all(items.get(i['id'])==i for i in original_items if i['id'] not in {g['id'] for g in fish_catalog.pieces()}),'unrelated catalogue values are preserved')
        recipes=json.loads((ROOT/'world/fishing-workshop.txt').read_text())
        fish=json.loads((ROOT/'world/fish.txt').read_text());rods=json.loads((ROOT/'world/rods.txt').read_text())
        by_rod={r['item']:r for r in rods};by_fish={f['item']:f for f in fish}
        self.assertEqual(len({r['id'] for r in recipes}),len(recipes))
        for r in recipes:
            self.assertIn(r['item'],items)
            for id,n in r['ingredients']:self.assertIn(id,items);self.assertGreater(n,0)
            if r['id'].startswith('rod:'):
                prior=by_rod[r['ingredients'][0][0]];f=by_fish[r['ingredients'][1][0]]
                self.assertLessEqual(f['min_tier'],prior['tier'])
                self.assertTrue(f['habitat']!='Lava' or prior['lava'])
                self.assertEqual(by_rod[r['item']]['tier'],prior['tier']+1)
                self.assertEqual(r['ingredients'][1][1],5)
            else:
                f=by_fish[r['ingredients'][0][0]];dish=items[r['item']]
                self.assertEqual(dish['kind'],'food');self.assertEqual(dish['cooldown'],30)
                self.assertGreater(dish['heal'],f['raw_heal']);self.assertGreater(dish['mana'],0)
        self.assertEqual({r['item'] for r in recipes if r['id'].startswith('rod:')},set(by_rod)-{'rod_twig_rod'})
        self.assertEqual({r['ingredients'][0][0] for r in recipes if r['id'].startswith('cook:')},set(by_fish))
        self.assertEqual(fish_catalog.apply(list(items.values())),list(items.values()))
        produced={i['id'] for i in fish_catalog.pieces()}
        self.assertTrue(all(r['item'] in produced for r in recipes),'catalogue generates every workshop output')

if __name__=='__main__':unittest.main()
