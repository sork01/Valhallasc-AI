#!/usr/bin/env python3
"""Exercise the one-command rollback on disposable RAID copies, including no-write guard failures."""
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import rollback_shared_art as B
checks=0

def check(v,label):
 global checks
 assert v,label;checks+=1;print(label)


def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


with tempfile.TemporaryDirectory(prefix='shared-rollback-check-',dir='/media/raid/valhallasc-data') as tmp:
 root=Path(tmp)/'target';backup=Path(tmp)/'backup';shutil.copytree(B.DEFAULT_BACKUP,backup)
 paths=set(json.loads((backup/'manifest.txt').read_text())['files']);paths.add('client/assets/cathedral_ember_firelord.png')
 for rel in paths:
  dst=root/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dst)
 cmd=[sys.executable,str(ROOT/'scripts/rollback_shared_art.py'),'--root',str(root),'--backup',str(backup)]
 before=hashes(root);run=subprocess.run(cmd,capture_output=True,text=True)
 check(run.returncode==0 and hashes(root)==before,'Dry run verifies everything without writes')
 field=root/'client/field.js';field.write_text(field.read_text()+'\n// unrelated later change\n');altered=hashes(root)
 run=subprocess.run(cmd+['--apply'],capture_output=True,text=True)
 check(run.returncode!=0 and hashes(root)==altered,'Unrelated renderer change refuses before all writes')
 shutil.copy2(ROOT/'client/field.js',field)
 png=backup/'client/assets/christmas_grinch.png';original=png.read_bytes();png.write_bytes(original+b'bad');before=hashes(root)
 run=subprocess.run(cmd+['--apply'],capture_output=True,text=True)
 check(run.returncode!=0 and hashes(root)==before,'Corrupt backup refuses before all writes');png.write_bytes(original)
 run=subprocess.run(cmd+['--apply'],capture_output=True,text=True);check(run.returncode==0,'One-command rollback completes')
 info=json.loads((backup/'manifest.txt').read_text())
 check(all(hashlib.sha256((root/rel).read_bytes()).hexdigest()==spec['sha256'] for rel,spec in info['files'].items()),'All fifteen originals restore exactly')
 check(not (root/'client/assets/cathedral_ember_firelord.png').exists(),'Independent candidate atlas removed on rollback')
 # The shared Cathedral manifest may contain another candidate: preserve its slice.
 rel='client/assets/cathedral.txt';shutil.copy2(ROOT/rel,root/rel);meta=json.loads((root/rel).read_text());meta['tops']['cf_brute']=123;(root/rel).write_text(json.dumps(meta,indent=2)+'\n')
 run=subprocess.run(cmd+['--apply'],capture_output=True,text=True)
 check(run.returncode==0 and json.loads((root/rel).read_text())['tops']['cf_brute']==123,'Another Cathedral art candidate survives rollback')
(ROOT/'test-results/shared-slime/rollback-proof.json').write_text(json.dumps(dict(checks=checks,passed=True),indent=2)+'\n')
print(f'{checks} rollback checks passed')
