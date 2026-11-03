#!/usr/bin/env python3
"""Flooded Cloister review | verify | upload. Upload is a separate explicit operation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/cloister-slime-original-20261103')
OUT = ROOT/'test-results/cloister-slime'
KINDS = ['tidetemplar','tidecantor','tideleech','bellkeeper','mournsister','rootabbot','choirmother','choirsinger']
NAMES = ['Tide Templar','Tide Cantor','Tide Leech','Bellkeeper','Mourning Sister','Root Abbot','Choirmother','Bound Singer']
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 20)
small = ImageFont.truetype(FONT, 15)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    # Equal frame crop/scale: preserve the actual silhouette size of each version.
    meta = json.loads((ROOT/'client/assets/cathedral.txt').read_text())
    before = Image.new('RGB', (len(KINDS)*264+24, 540), '#244047')
    after = before.copy()
    for label, sheet, source in [('Before', before, BACKUP), ('After', after, ROOT)]:
        d = ImageDraw.Draw(sheet)
        d.text((22, 12), 'Flooded Cloister — '+label+' (same 2× scale)', font=font, fill='#fff0cb')
        for col, (kind, name) in enumerate(zip(KINDS, NAMES)):
            atlas = Image.open(source/f'client/assets/cathedral_{kind}.png').convert('RGBA')
            corpse=atlas.crop((7*96,4*96,8*96,5*96)).resize((192,192),Image.Resampling.NEAREST)
            sheet.paste(corpse,(col*264+36,310),corpse)
            d.text((col*264+36,505),'Final death pose',font=small,fill='white')
            im = atlas.crop((0, 0, 96, 96)).resize((192,192), Image.Resampling.NEAREST)
            sheet.paste(im, (col*264+36, 60), im)
            d.text((col*264+36, 266), name, font=font, fill='white')
    before.save(OUT/'valhallasc-cloister-before.png')
    after.save(OUT/'valhallasc-cloister-after.png')
    compare = Image.new('RGB', (len(KINDS)*264+24, 1150), '#244047')
    compare.paste(before, (0,0)); compare.paste(after, (0,540))
    d = ImageDraw.Draw(compare)
    d.text((22,1092), 'The templar\'s armour buckles; the cantor\'s robe crumples empty; the leech goes limp; the bell cracks and slumps;', font=font, fill='white')
    d.text((22,1120), 'the sister dissolves; the abbot splits into logs; the Choirmother swoons; the singer drifts away. Everything now rests on the ground.', font=font, fill='white')
    compare.save(OUT/'valhallasc-cloister-before-after.png')
    for kind, name in zip(KINDS,NAMES):
        atlas = Image.open(ROOT/f'client/assets/cathedral_{kind}.png').convert('RGBA')
        gallery = Image.new('RGB',(8*192,5*218+36),'#244047')
        gd = ImageDraw.Draw(gallery)
        gd.text((12,8), name+' — every exported PixelFlow frame',font=font,fill='white')
        for clip,spec in meta['clips'].items():
            for n in range(spec['n']):
                x,y = n*192,36+spec['row']*218
                im=atlas.crop((n*96,spec['row']*96,(n+1)*96,(spec['row']+1)*96)).resize((192,192),Image.Resampling.NEAREST)
                gallery.paste(im,(x,y),im)
                gd.text((x+8,y+192),f'{clip} {n+1}',font=small,fill='white')
        gallery.save(OUT/f'valhallasc-cloister-{kind}-frames.png')
        # Each row runs at its original fps; all five clips visible together.
        sequence=[]
        for tick in range(120):
            image=Image.new('RGB',(5*208,250),'#244047')
            d=ImageDraw.Draw(image)
            for col,(clip,spec) in enumerate(meta['clips'].items()):
                # Repeat live loops, hold the final die frame for a moment.
                count=spec['n']; time=tick/20
                n=int(time*spec['fps']) % count if clip!='die' else min(count-1,int((time%2)*spec['fps']))
                crop=atlas.crop((n*96,spec['row']*96,(n+1)*96,(spec['row']+1)*96)).resize((192,192),Image.Resampling.NEAREST)
                image.paste(crop,(col*208+8,22),crop)
                d.text((col*208+8,218),clip,font=font,fill='white')
            sequence.append(image)
        sequence[0].save(OUT/f'valhallasc-cloister-{kind}-animations.gif',save_all=True,
                         append_images=sequence[1:],duration=50,loop=0,optimize=False)
        deaths=[]
        previous=Image.open(BACKUP/f'client/assets/cathedral_{kind}.png').convert('RGBA')
        for tick in range(80):
            n=min(7,int(((tick/20)%2)*8))
            im=Image.new('RGB',(480,260),'#244047');d=ImageDraw.Draw(im)
            for col,(label,source) in enumerate([('Before',previous),('After',atlas)]):
                crop=source.crop((n*96,4*96,(n+1)*96,5*96)).resize((192,192),Image.Resampling.NEAREST)
                im.paste(crop,(col*240+24,16),crop)
                d.text((col*240+24,220),label+' / die',font=font,fill='white')
            deaths.append(im)
        deaths[0].save(OUT/f'valhallasc-cloister-{kind}-death-before-after.gif',save_all=True,
                      append_images=deaths[1:],duration=50,loop=0,optimize=False)
    print('27 before/after pictures, complete frame sheets and original-rate animations written.')


def verify():
    proof=json.loads((OUT/'editor-export-proof.json').read_text())
    count=0
    for kind, packet in proof.items():
        atlas=Image.open(ROOT/f'client/assets/cathedral_{kind}.png').convert('RGBA')
        meta=json.loads((ROOT/'client/assets/cathedral.txt').read_text())
        assert sha(ROOT/f'client/assets/cathedral_{kind}.png')==packet['atlasSha256']
        for entry in packet['frames']:
            row=meta['clips'][entry['clip']]['row'];n=entry['n']
            im=atlas.crop((n*96,row*96,(n+1)*96,(row+1)*96))
            assert hashlib.sha256(im.tobytes()).hexdigest()==entry['sha256']
            count+=1
    assert count==272
    # Exercise the actual rollback command on an isolated copy (whose shared manifest has an unrelated Reliquary edit),
    # then corrupt a backup to prove preflight refuses it without partially changing the target.
    backup_meta=json.loads((BACKUP/'manifest.txt').read_text())
    manifest='client/assets/cathedral.txt'
    with tempfile.TemporaryDirectory(prefix='rollback-',dir=OUT) as temp:
        scratch=Path(temp)
        target=scratch/'target'; damaged=scratch/'damaged'
        for name in list(backup_meta['files'])+[manifest]:
            (target/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,target/name)
        live=json.loads((target/manifest).read_text())
        live['sprites']['reliccrab']='RELIQUARY_EDIT'; live['tops']['reliccrab']=1
        (target/manifest).write_text(json.dumps(live,indent=2)+'\n')
        command=['python3',str(ROOT/'scripts/rollback_cloister_art.py'),'--target',str(target),'--apply']
        shutil.copytree(BACKUP,damaged)
        (damaged/'client/assets/cathedral_tideleech.png').write_bytes(b'corrupt')
        before={name:sha(target/name) for name in list(backup_meta['files'])+[manifest]}
        failed=subprocess.run(command+['--backup',str(damaged)],capture_output=True)
        assert failed.returncode!=0 and all(sha(target/name)==digest for name,digest in before.items())
        subprocess.run(command,check=True,capture_output=True)
        assert all(sha(target/name)==digest for name,digest in backup_meta['files'].items())
        restored=json.loads((target/manifest).read_text())
        assert all(restored['sprites'][k]==backup_meta['oldSprites'][k] and restored['tops'][k]==backup_meta['oldTops'][k] for k in backup_meta['kinds'])
        assert restored['sprites']['reliccrab']=='RELIQUARY_EDIT' and restored['tops']['reliccrab']==1, 'rollback must not touch other kinds'
        original=json.loads((BACKUP/'client/assets/cathedral.full-manifest-reference.txt').read_text())
        restored['sprites']['reliccrab']=original['sprites']['reliccrab']; restored['tops']['reliccrab']=original['tops']['reliccrab']
        assert restored==original, 'restored manifest equals the original except for the unrelated edit'
    for entry,args in (('make_cathedral_sprites.py',['tidetemplar']), ('cloister_slime_redraw.py',[])):
        refused=subprocess.run(['python3',str(ROOT/'scripts'/entry),'build',*args,'--replace'],capture_output=True)
        assert refused.returncode != 0 and b'--replace is refused' in refused.stderr
    # the old maker must still serve every other kind: a different kind is not refused
    other=subprocess.run(['python3',str(ROOT/'scripts/make_cathedral_sprites.py'),'verify','abysszealot'],capture_output=True)
    assert other.returncode==0 and b'pixel-identical' in other.stdout
    live=Path('/home/serveperry/webserver/www/Valhallasc')
    (OUT/'validation.json').write_text(json.dumps({'editorFramesMatch':count,
        'rollbackEightAtlasesAndManifestEntriesVerified':True,'unrelatedManifestEditSurvivesRollback':True,
        'corruptBackupRefusedWithoutChanges':True,'destructiveBuildRefused':True,'otherCathedralKindsStillVerify':True,
        'originalFiles':backup_meta},indent=2)+'\n')
    print('272 saved-editor/export frame matches; eight-atlas rollback (manifest merge) and corrupt-backup refusal pass.')


def upload():
    receipt=[]
    paths=sorted(OUT.glob('valhallasc-cloister-*.png'))+sorted(OUT.glob('valhallasc-cloister-*.gif'))
    expected=3+len(KINDS)*3
    assert len(paths)==expected, 'Generate the complete review set first'
    for source in paths:
        mime='image/gif' if source.suffix=='.gif' else 'image/png'
        subprocess.run(['bash',str(ROOT/'scripts/filedrop_put.sh'),str(source),source.name,mime],check=True)
        dest=Path('/home/serveperry/webserver/www/filedrop/data/Sork/files')/source.name
        metadata=json.loads(Path(str(dest)+'.meta.json').read_text())
        assert sha(source)==sha(dest)
        assert metadata['original_name']==source.name and metadata['type']==mime
        assert metadata['size']==source.stat().st_size==dest.stat().st_size
        assert Image.open(source).size==Image.open(dest).size
        receipt.append({'name':source.name,'sha256':sha(source),'bytes':source.stat().st_size,
                        'dimensions':Image.open(source).size,'mime':mime})
    (OUT/'filedrop-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(len(receipt),'FileDrop pictures/animations verified')


if __name__=='__main__':
    {'review':review,'verify':verify,'upload':upload}[sys.argv[1]]()
