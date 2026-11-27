#!/usr/bin/env python3
"""Independent authored-data gates in a temporary tree; never rewrites this checkout."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gm_island',ROOT/'scripts/generate_gm_island.py')
generator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
# Pin the accepted public map before the island, so this gate also works after commit.
original=json.loads(subprocess.check_output(['git','show','ab60773d:world/map.txt'],cwd=ROOT))
art=json.loads((ROOT/'client/assets/npc.txt').read_text())
old_art={k:v for k,v in art['npcs'].items() if not k.startswith('gmi_')}
if os.environ.get('MUTATE'):
    build=generator.build
    def broken():
        z=build()
        if os.environ['MUTATE']=='access':z['gmOnly']=False
        else:z['spawn']['y']=343
        return z
    generator.build=broken

with tempfile.TemporaryDirectory(prefix='valhalla-gm-island-') as tmp:
    root=Path(tmp);(root/'world').mkdir();(root/'client/assets').mkdir(parents=True)
    target=root/'world/map.txt';target.write_text(json.dumps(original,indent=2,ensure_ascii=False)+'\n')
    (root/'client/assets/npc.txt').write_text(json.dumps(art,indent=2,ensure_ascii=False)+'\n')
    generator.ROOT=root
    generator.install();first=target.read_bytes()
    m=json.loads(first);island=m['zones'][-1];zone=len(m['zones'])
    assert zone==47 and island['gmOnly'] is True
    assert len(island['camps'])==6 and len(island['slimes'])==6
    assert {t['id'] for t in island['gmIsland']['towns']}=={'christmas','halloween','easter','solstice','valentine','newyear'}
    old_land=sum(row.count('#') for row in original['shapeFloor'])
    land=sum(row.count('#') for row in island['shapeFloor'])
    assert abs(land/old_land-1)<.03,(land,old_land)
    entry=next(p for p in m['portals'] if p['id']=='gmi_gate')
    assert entry['gmOnly'] is True and entry['to']==zone
    for gate in island['portals']:
        assert ((entry['tx']-gate['x'])**2+(entry['ty']-gate['y'])**2)**.5>gate['r']+2.8
        assert ((island['spawn']['x']-gate['x'])**2+(island['spawn']['y']-gate['y'])**2)**.5>gate['r']+2.8
    without=copy.deepcopy(m);without['zones'].pop();without['portals'].remove(entry)
    assert without==original,'every public zone and public service preserved'
    assigned=json.loads((root/'client/assets/npc.txt').read_text())['npcs']
    assert all(n['id'] in assigned for n in island['npcs'])
    assert {k:v for k,v in assigned.items() if not k.startswith('gmi_')}==old_art
    assert all(link.startswith('gmi_') for n in island['npcs'] for link in n.get('travelLinks',[]))
    generator.install();assert target.read_bytes()==first,'second generation byte-identical'
    generator.detach();assert json.loads(target.read_text())==original,'public overlays see original data'
    generator.install();assert target.read_bytes()==first,'detach/install round trip byte-identical'
    future=dict(name='Future zone',theme='meadow',size=32,spawn=dict(x=16,y=16),
                objects=[],slimes=[],npcs=[],quests=[],portals=[],city=None)
    later=json.loads(first);later['zones'].append(future)
    target.write_text(json.dumps(later,indent=2,ensure_ascii=False)+'\n')
    generator.detach();detached=json.loads(target.read_text())
    assert len(detached['zones'])==48 and detached['zones'][-1]==future
    assert detached['zones'][46]['gmOnly'] and not detached['zones'][46]['npcs']
    generator.install();later=json.loads(target.read_text())
    assert later['zones'][46]==island and later['zones'][-1]==future,'later zone IDs and contents preserved'
    print('gm-island-map: public preservation, access, arrival clearance, six towns, NPC art, island routes and repeatability pass',hashlib.sha256(first).hexdigest())
