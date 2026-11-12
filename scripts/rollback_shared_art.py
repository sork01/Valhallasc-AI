#!/usr/bin/env python3
"""Restore only shared/event sprite slices; verify every guard before writing. Dry run by default."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_BACKUP=Path('/media/raid/valhallasc-data/shared-slime-original-20261112')
BANKS=dict(ember_firelord='cathedral',hollow_rider='halloween',grinch='christmas',bloomwarden='easter',birchcrown='solstice',briarheart='valentines',starrocketeer='newyear')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(root,backup):
 info=json.loads((backup/'manifest.txt').read_text())
 expected={'client/field.js','client/assets/cathedral_cf_eldmarr.png'}
 expected|={f'client/assets/{b}.txt' for b in BANKS.values()}
 expected|={f'client/assets/{b}_{k}.png' for k,b in BANKS.items() if k!='ember_firelord'}
 assert set(info['files'])==expected,'Unexpected backup file set'
 for rel,record in info['files'].items():
  p=backup/rel;assert p.is_file() and sha(p)==record['sha256'] and p.stat().st_size==record['bytes'],f'Corrupt backup: {rel}'
 receipt=json.loads((ROOT/'scripts/shared_slime_candidate.txt').read_text())
 writes=[]
 for k,bank in BANKS.items():
  rel=f'client/assets/{bank}.txt';path=root/rel;live=json.loads(path.read_text());old=json.loads((backup/rel).read_text())
  assert live['frame']==old['frame'] and live['anchor']==old['anchor'] and live['clips']==old['clips'],f'Unrelated geometry changed: {rel}'
  for key in ('sprites','tops','kindFrames','atlases'):
   if k in old.get(key,{}):live.setdefault(key,{})[k]=old[key][k]
   else:
    live.get(key,{}).pop(k,None)
    if key in live and not live[key] and key not in old:live.pop(key)
  writes.append((path,json.dumps(live,indent=2).encode()+b'\n'))
  rel=f'client/assets/{bank}_{k}.png';path=root/rel
  if path.exists():assert sha(path)==receipt['files'][rel] or (backup/rel).exists() and sha(path)==info['files'][rel]['sha256'],f'Candidate atlas changed: {rel}'
  writes.append((path,None if k=='ember_firelord' else (backup/rel).read_bytes()))
 path=root/'client/field.js'
 assert sha(path) in (receipt['files']['client/field.js'],info['files']['client/field.js']['sha256']),'Unrelated field.js edit; integrate reverse renderer patch manually'
 writes.append((path,(backup/'client/field.js').read_bytes()))
 return writes


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--backup',type=Path,default=DEFAULT_BACKUP);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 writes=prepare(args.root,args.backup)
 for path,data in writes:
  print(('APPLY' if args.apply else 'DRY RUN'),path,'remove' if data is None else 'restore')
  if args.apply:
   if data is None:path.unlink(missing_ok=True)
   else:path.write_bytes(data)
 print('Rollback complete' if args.apply else 'All guards passed; --apply restores shared/event art')


if __name__=='__main__':main()
