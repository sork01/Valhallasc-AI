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
if os.environ.get('MUTATE')=='overlay':
    fishers.install=lambda *args: None
if os.environ.get('MUTATE')=='dishes':
    before=subprocess.check_output(['git','show','97f75da7:scripts/fish_catalog.py'],cwd=ROOT,text=True)
    exec(compile(before,'fish_catalog.py','exec'),fish_catalog.__dict__)

class Workshop(unittest.TestCase):
    def test_overlay_and_existing_world_preserved(self):
        world=json.loads((ROOT/'world/map.txt').read_text())
        def split(source):
            rest=copy.deepcopy(source);own=[]
            for area in [rest,*rest['zones']]:
                own.append({field:[row for row in area[field] if row['id'].startswith('fisher_')] for field in ('npcs','quests')})
                for field in ('npcs','quests'):
                    area[field]=[row for row in area[field] if not row['id'].startswith('fisher_')]
            return rest,own
        base,released=split(world)
        levels=json.loads((ROOT/'world/levels.txt').read_text());levels.append(levels[-1]+2300)
        recipes=json.loads((ROOT/'world/fishing-workshop.txt').read_text());fish=json.loads((ROOT/'world/fish.txt').read_text())
        rods=json.loads((ROOT/'world/rods.txt').read_text())
        check=copy.deepcopy(base)
        fishers.install(check,recipes,fish,levels,rods)
        rest,installed=split(check)
        self.assertTrue(rest==base,'the Fisher overlay changes only its own people and quests')
        self.assertEqual(installed,released)
        self.assertEqual(json.dumps(world,ensure_ascii=False,indent=2)+'\n',(ROOT/'world/map.txt').read_text())
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

    def test_quest_text_names_the_minimum_rod_for_each_local_catch(self):
        world = json.loads((ROOT/'world/map.txt').read_text())
        client = json.loads((ROOT/'client/world.js').read_text().split('window.WORLD_MAP = ', 1)[1].strip().removesuffix(';'))
        fish = {f['item']: f for f in json.loads((ROOT/'world/fish.txt').read_text())}
        rods = json.loads((ROOT/'world/rods.txt').read_text())
        names = {r['tier']: r['name'] for r in rods}
        if os.environ.get('MUTATE') == 'quest-rod':
            for catalogue in (world, client):
                quest = next(q for q in catalogue['zones'][18]['quests'] if q['id'] == 'fisher_storm_0_3')
                quest['description'] = quest['description'].replace('Silverline Rod', 'Reedglass Rod')
        hints = 0
        for zone, (area, shown) in enumerate(zip([world, *world['zones']], [client, *client['zones']])):
            shown_by_id = {q['id']: q for q in shown['quests']}
            for quest in (q for q in area['quests'] if q['id'].startswith('fisher_')):
                species = fish[quest['objectives'][0]['target']]
                water_tier = max(r['tier'] for r in rods if zone in r['zones'])
                tier = max(species['min_tier'], water_tier)
                with self.subTest(quest=quest['id']):
                    description = quest['description']
                    self.assertEqual(description, shown_by_id[quest['id']]['description'])
                    mentioned = [name for name in names.values() if f'a {name} or better' in description]
                    self.assertEqual(mentioned, [names[tier]] if tier > 1 else [])
                    if zone == 0 and species['item'] == 'fish_glass_eel':
                        self.assertIn('Reedglass Rod or better', description)
                        self.assertIn('Saltby pier', description)
                    if tier > 1:
                        hints += 1
        self.assertGreater(hints, 0)

    def test_recipes_have_no_progression_deadlock_and_dishes_are_meals(self):
        actual=json.loads((ROOT/'world/items.txt').read_text());items={i['id']:i for i in actual}
        # Compared with the catalogue itself, not a frozen commit: other overlays' pieces may change.
        fishing={i['id'] for i in fish_catalog.pieces()}
        others=[i for i in actual if i['id'] not in fishing]
        regenerated=fish_catalog.apply(copy.deepcopy(others))
        self.assertEqual([i for i in regenerated if i['id'] not in fishing],others,'unrelated catalogue values and order are preserved')
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
