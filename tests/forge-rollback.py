#!/usr/bin/env python3
"""Prove rollback guards and exact restoration only on disposable RAID copies."""
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import rollback_forge_art as R
OUT=ROOT/'test-results/forge-slime';OUT.mkdir(parents=True,exist_ok=True)
backup=R.DEFAULT_BACKUP

def digest(root):return {rel:R.sha256(root/rel) for rel in R.EXPECTED_REL}

def run(root,bak=backup,apply=False):
    return subprocess.run([sys.executable,str(ROOT/'scripts/rollback_forge_art.py'),'--root',str(root),'--backup',str(bak)]+(['--apply'] if apply else []),text=True,capture_output=True)

proof={}
with tempfile.TemporaryDirectory(prefix='forge-rollback-',dir='/media/raid/valhallasc-data') as scratch:
    scratch=Path(scratch);candidate=scratch/'candidate'
    for rel in R.EXPECTED_REL:
        p=candidate/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
    initial=digest(candidate);res=run(candidate)
    assert res.returncode==0,res.stderr
    assert digest(candidate)==initial,'dry run wrote files'
    proof['dryRun']=True
    res=run(candidate,apply=True);assert res.returncode==0,res.stderr
    expected={rel:R.sha256(backup/rel) for rel in R.EXPECTED_REL}
    assert digest(candidate)==expected,'restored hashes differ'
    proof['exactRestoration']=expected
    # A damaged backup must refuse before changing even the first file.
    bad=scratch/'bad-backup';shutil.copytree(backup,bad)
    with (bad/R.EXPECTED_REL[-1]).open('ab') as f:f.write(b'corrupt')
    before=digest(candidate);res=run(candidate,bad,True)
    assert res.returncode!=0 and 'checksum mismatch' in res.stderr
    assert digest(candidate)==before,'corrupt-backup refusal wrote files'
    proof['corruptBackupRefusedWithoutWrites']=True
    # A newer unrelated Cathedral source must survive, so whole-manifest rollback refuses.
    mpath=candidate/'client/assets/cathedral.txt';meta=json.loads(mpath.read_text());other=next(k for k in meta['kinds'] if k not in R.OWNED)
    meta['tops'][other]+=1;mpath.write_text(json.dumps(meta))
    before=digest(candidate);res=run(candidate,apply=True)
    assert res.returncode!=0 and 'unrelated Cathedral kinds changed' in res.stderr
    assert digest(candidate)==before,'unrelated-manifest refusal wrote files'
    proof['unrelatedManifestRefusedWithoutWrites']=True
(OUT/'rollback-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print('forge-rollback: dry run, all 16 original files restored exactly, corrupt-backup and unrelated-manifest refusals pass')
