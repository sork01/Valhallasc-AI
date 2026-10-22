"""Cloaks only: catalogue, deterministic generation, rewards, vendors and art contract."""
import copy
import contextlib
import io
import tempfile
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import cloak_catalog as cloak
import gear_levels as gear
import orange_rules

class Cloaks(unittest.TestCase):
    def setUp(self):
        self.items=json.loads((ROOT/'world/items.txt').read_text());self.cloaks=[i for i in self.items if i['kind']=='cloak']
    def test_catalogue_and_stamina_budget(self):
        self.assertEqual(len(self.cloaks),100)
        self.assertTrue(all(not i.get('class') and not i.get('starter') and i['attack']==i['defense']==0 for i in self.cloaks))
        for level in cloak.LEVELS:
            plain=[i for i in self.cloaks if not i.get('source') and i['requiredLevel']==level]
            self.assertEqual({i['rarity'] for i in plain},set(cloak.RARITIES if level%10==0 or level==99 else cloak.RARITIES[:3]))
            for i in plain:
                if i['rarity'] in ('common','uncommon'):self.assertGreater(i['bonusStats']['stamina'],0)
                else:
                    necklace=next((n for n in self.items if n['kind']=='necklace' and not n.get('source') and n['rarity']==i['rarity'] and n['requiredLevel']==level),None)
                    expected=sum(necklace['bonusStats'].values()) if necklace else (114*(2 if i['rarity']=='epic' else 1))
                    self.assertEqual(sum(i['bonusStats'].values()),expected)
        self.assertEqual(len({i['name'] for i in self.cloaks}),100)
        colours=set()
        for item in self.cloaks:
            self.assertIn(item['art'],cloak.STYLES)
            t=item['tint'];self.assertFalse(t['hue']%360==0 and t['saturate']==t['brightness']==1)
            signature=(item['art'],t['hue'],t['saturate'],t['brightness'])
            self.assertNotIn(signature,colours,item['id']);colours.add(signature)

    def test_generation_is_stable_and_preserves_other_gear(self):
        regenerated=cloak.apply(copy.deepcopy(self.items));self.assertEqual(regenerated,self.items)
        self.assertEqual(cloak.apply(copy.deepcopy(regenerated)),regenerated)
        old=[i for i in self.items if i['kind']!='cloak'];new=[i for i in regenerated if i['kind']!='cloak'];self.assertEqual(old,new)
        rules=orange_rules.build();self.assertEqual(len(rules['pieces']),60)
        self.assertEqual(rules,json.loads((ROOT/'world/orange_rules.txt').read_text()))
    def test_full_generator_is_byte_stable_twice(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'items.txt';path.write_bytes((ROOT/'world/items.txt').read_bytes())
            old=gear.ITEMS
            try:
                gear.ITEMS=path
                before=path.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()):gear.main()
                self.assertEqual(path.read_bytes(),before)
                with contextlib.redirect_stdout(io.StringIO()):gear.main()
                self.assertEqual(path.read_bytes(),before)
            finally:gear.ITEMS=old

    def test_dungeons_quests_and_tiered_vendors(self):
        world=json.loads((ROOT/'world/map.txt').read_text());self.assertEqual(cloak.apply_world(copy.deepcopy(world),self.items),world)
        vendors=0;quests=0
        for area in [world,*world['zones']]:
            for npc in area.get('npcs',[]):
                offers=[o for o in npc.get('offers',[]) if o['id'].startswith('buy_cloak_')]
                if offers:
                    vendors+=1;self.assertEqual(len(offers),3);self.assertTrue(all(o['tiered'] for o in offers))
            for q in area.get('quests',[]):
                choices=q.get('rewardChoices',{})
                if any(any(i.startswith('cloak_') for i in ids) for ids in choices.values()):
                    quests+=1;self.assertEqual(set(choices),set(gear.CLASSES))
                    self.assertTrue(all(len([i for i in ids if i.startswith('cloak_')])==1 for ids in choices.values()))
        self.assertGreater(vendors,5);self.assertGreater(quests,20)
        self.assertEqual({i['source'] for i in self.cloaks if i.get('source') not in (None,'orange_pool')},set(cloak.DUNGEONS))
    def test_editable_records_and_runtime_atlas_contract(self):
        import base64
        import sprite_bounds
        state=json.loads((ROOT/'docs/cloak-gear-state.txt').read_text())
        manifest=json.loads((ROOT/'world/gear-art.txt').read_text())
        assets=ROOT/'client/assets';ids=[]
        stems={'warrior':'warrior_layered','mage':'mage','assassin':'assassin','priest':'priest','hunter':'hunter'}
        icons=json.loads((assets/'items.txt').read_text())['at']
        self.assertEqual(set(state),set(cloak.STYLES))
        for style,record in state.items():
            self.assertEqual(record,manifest['CLOAK-'+style.upper()])
            self.assertEqual(len(record['files']),21)
            for file in record['files']:self.assertTrue((ROOT/file).is_file(),file)
            ids.append(record['icon']['id'])
            for cls,stem in stems.items():
                for gender in ('male','female'):
                    prefix=stem+('_f' if gender=='female' else '')
                    meta_path=assets/(prefix+'_sprites.txt');meta=json.loads(meta_path.read_text())
                    part='cloak_'+style
                    self.assertIn(part,meta['lazyParts'])
                    clips=record['classes'][cls+'-'+gender]
                    self.assertEqual(set(clips),set(meta['clips']))
                    for clip,saved in clips.items():
                        self.assertEqual(saved['frameCount'],meta['clips'][clip]['n']*8)
                        ids.append(saved['id'])
                    bounds=json.loads(sprite_bounds.bounds_name(meta_path).read_text())
                    actual=sprite_bounds.part_bounds(assets/meta['parts'][part]['png'],meta)
                    self.assertEqual(base64.b64decode(bounds['parts'][part]),actual)
        self.assertEqual(len(ids),255);self.assertEqual(len(set(ids)),255)
        for item in self.cloaks:self.assertIn(item['id'],icons)

    def test_handwritten_swedish_for_every_cloak(self):
        sv=json.loads((ROOT/'scripts/sv-translations.txt').read_text())
        for i in self.cloaks:self.assertTrue(sv.get(i['name']),i['name'])

if __name__=='__main__':unittest.main()
