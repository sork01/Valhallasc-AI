#!/usr/bin/env python3
"""Focused material, volume, source-preservation and scope checks for shared/event art."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shared_slime_redraw as R
from shared_slime_review import BACKUP,cell
checks=0

def check(value,label):
 global checks
 assert value,label;checks+=1;print(f'{checks}: {label}')


def count(grid,ramp):return int(np.isin(grid,ramp).sum())


baseline=json.loads((BACKUP/'manifest.txt').read_text())
for k in R.KINDS:
 meta=json.loads(R.manifest_path(k).read_text());bank=R.BANKS[k];old=json.loads((BACKUP/f'client/assets/{bank}.txt').read_text())
 check(meta['frame']==old['frame'] and meta['anchor']==old['anchor'] and meta['clips']==old['clips'] and meta['kinds']==old['kinds'],k+': shared timing, fallback geometry and kind IDs unchanged')
 for key in ('sprites','tops','kindFrames','atlases'):
  check({x:v for x,v in meta.get(key,{}).items() if x!=k}=={x:v for x,v in old.get(key,{}).items() if x!=k},k+': unrelated '+key+' records preserved')
 check(meta['sprites'][k]!=baseline['sources'][k] and meta['sprites'][k]==R.registry()[k],k+': old editor source retained, new native source assigned')
 data=np.load(R.ROOT/f'scripts/shared_slime_{k}_raw.npz');before,_,_=cell(BACKUP,k,'idle',0)
 old_b=before.getbbox();b=R.rgba(data['idle'][0]).getbbox();delta=[abs((b[i+2]-b[i])-(old_b[i+2]-old_b[i])) for i in range(2)]
 check(max(delta)<=2,k+': idle size stays within two original pixels')
 check(all(len({f.tobytes() for f in data[c]})==8 for c in ('attack','die')),k+': eight authored attacks and eight authored deaths')
 idle,dead=data['idle'][0],data['die'][7]
 if k=='ember_firelord':
  check(count(dead,R.models.AMBER)==0 and count(idle,R.models.AMBER)>200,'Firelord crown, sockets and furnace fissures extinguish')
  check(count(dead,R.models.BASALT)>count(idle,R.models.BASALT)*.8,'Firelord retains cooled basalt volume')
 if k=='hollow_rider':
  # Folded legs and the fallen rider occlude the barrel; retain a majority
  # of visible horse material (vertical compression would leave about 20%).
  check(count(dead,R.models.BASALT)>count(idle,R.models.BASALT)*.55,'Nightmare horse retains rigid charcoal body and folded legs')
  check(count(dead,R.models.AMBER)<count(idle,R.models.AMBER)*.75,'Nightmare flames gutter while the held pumpkin remains')
  check(count(dead,R.models.PEARL)>35,'Fallen scythe retains its rigid blade')
 if k=='grinch':
  check(count(dead,R.models.SACK)>count(idle,R.models.SACK)*.9,'Fallen cloth sack keeps its full bulk')
  check(count(dead,R.models.LEAF)>count(idle,R.models.LEAF)*.8,'Furry head and hands retain their volume when fallen')
 if k=='bloomwarden':
  check(count(dead,R.models.PEARL)>count(idle,R.models.PEARL)*.9,'Egg armour falls into rigid pieces, rather than shrinking')
 if k=='birchcrown':
  check(count(dead,R.models.BIRCH)>count(idle,R.models.BIRCH)*.8,'Pale birch trunk retains its solid volume')
 if k=='briarheart':
  check(count(dead,R.models.BROWN)>count(idle,R.models.BROWN)*.9,'Thorn wood remains solid while rose petals separate')
 if k=='starrocketeer':
  check(count(dead,R.models.AMBER)==0 and count(idle,R.models.AMBER)>0,'Rocket fuses extinguish on the intact fallen pack')
  check(count(dead,R.models.CRIMSON)>count(idle,R.models.CRIMSON)*.8,'Red rocket cases retain their volume')
# The legacy Eldmarr atlas remains completely untouched by the independent Firelord.
rel='client/assets/cathedral_cf_eldmarr.png'
check(hashlib.sha256((R.ROOT/rel).read_bytes()).hexdigest()==baseline['files'][rel]['sha256'],'Independent Firelord preserves the Eldmarr atlas')
for bank in R.BANKS.values():
 if bank=='cathedral':continue
 result=subprocess.run([sys.executable,str(R.ROOT/f'scripts/make_{bank}_sprites.py'),'build','--replace'],capture_output=True,text=True)
 check(result.returncode!=0 and 'overwrite candidate frames explicitly' in result.stderr,bank+': legacy destructive replacement refused')
changed=subprocess.check_output(['git','diff','--name-only'],cwd=R.ROOT,text=True).splitlines()
check(not any(p.startswith(('world/','server/')) for p in changed),'No world, seasonal, stats or server changes')
(R.OUT/'materials-proof.json').write_text(json.dumps(dict(checks=checks,passed=True),indent=2)+'\n')
print(f'{checks} material/preservation checks passed')
