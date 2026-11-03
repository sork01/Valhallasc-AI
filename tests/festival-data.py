"""Focused six-season integration, preserved geography, clear circuits and full-sync stability."""
import json,subprocess,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from compact_atlas import clear,connected
base=json.loads(subprocess.check_output(['git','show','94a9fc6:world/map.txt'],cwd=ROOT));world=json.loads((ROOT/'world/map.txt').read_text())
areas=[world,*world['zones']];old=[base,*base['zones']];assert len(areas)==len(old)==47
for a,b in zip(areas,old):
 for key in ['objects','portals','paths','city','roads','cityEntrances','spawn','size','rooms','bridges','sky','void']:
  assert a.get(key)==b.get(key),(a['name'],key)
 assert [s for s in a['slimes'] if s['kind'] not in ['briarheart','starrocketeer','birchcrown']]==[s for s in b['slimes'] if s['kind']!='birchcrown']
 for n in b['npcs']:
  actual=next(v for v in a['npcs'] if v['id']==n['id']);assert {k:v for k,v in n.items() if k!='offers'}=={k:v for k,v in actual.items() if k!='offers'}
seasons=json.loads((ROOT/'world/seasons.txt').read_text());assert {e['id'] for e in seasons}=={'halloween','christmas','newyear','valentine','easter','solstice'}
centres=[]
for zone,a in enumerate(areas):
 for n in a['npcs']:
  if not n['id'].startswith('festival_dance_'):continue
  assert zone in [0,4,9,17] and n['r']==0 and n['offers'][0]['id']=='festival:dance'
  assert clear(a,(n['x'],n['y']),(n['x'],n['y']),2.5)
  assert int(n['y'])*a['size']+int(n['x']) in connected(a)
  assert a['city']['x0']<n['x']<a['city']['x1'] and a['city']['y0']<n['y']<a['city']['y1']
  centres.append(n['id'])
assert len(centres)==24 and len(set(centres))==24
catalog=json.loads((ROOT/'world/achievements.txt').read_text());assert len(catalog)==107 and sum(a['points'] for a in catalog)==2325
mounts=json.loads((ROOT/'client/assets/mounts_sprites.txt').read_text())['mounts'];assert len(mounts)==11
node='/home/serveperry/.nvm/versions/node/v20.20.2/bin/node'
def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ['world','client'] for p in (ROOT/d).glob('*') if p.is_file()}
subprocess.run([node,'scripts/sync-world.cjs'],cwd=ROOT,check=True,capture_output=True);one=hashes()
subprocess.run([node,'scripts/sync-world.cjs'],cwd=ROOT,check=True,capture_output=True);two=hashes();assert one==two,[k for k in one if one[k]!=two[k]]
(ROOT/'test-results/festival-data.json').write_text(json.dumps(dict(zones=47,geographyPreserved=True,centrepieces=centres,seasons=[s['id'] for s in seasons],mounts=len(mounts),byteStable=True,hashes=two),indent=2)+'\n')
print('festival-data: 24 clear/reachable centrepieces, all six seasons/11 mounts/107 achievements; geography/services preserved; full sync twice byte-stable')
