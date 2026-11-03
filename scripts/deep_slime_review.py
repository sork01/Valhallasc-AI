#!/usr/bin/env python3
"""Ran's Deep review | verify | upload. Upload is a separate explicit operation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/deep-slime-original-20261103')
OUT = ROOT/'test-results/deep-slime'
KINDS = ['draugr','angler','moray','siren','shellback','kraken','hvitserk','ghostmaw']
NAMES = ['Drowned Draugr','Lantern Angler','Gnashing Moray','Siren','Shellback','The Kraken','Hvitserk','Ghostmaw']
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 20)
small = ImageFont.truetype(FONT, 15)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review():
    # Equal frame crop/scale: preserve the actual silhouette size of each version.
    meta = json.loads((ROOT/'client/assets/deep.txt').read_text())
    before = Image.new('RGB', (len(KINDS)*264+24, 540), '#244047')
    after = before.copy()
    for label, sheet, source in [('Before', before, BACKUP), ('After', after, ROOT)]:
        d = ImageDraw.Draw(sheet)
        d.text((22, 12), 'Rán\'s Deep — '+label+' (same 2× scale)', font=font, fill='#fff0cb')
        for col, (kind, name) in enumerate(zip(KINDS, NAMES)):
            atlas = Image.open(source/f'client/assets/deep_{kind}.png').convert('RGBA')
            corpse=atlas.crop((7*96,4*96,8*96,5*96)).resize((192,192),Image.Resampling.NEAREST)
            sheet.paste(corpse,(col*264+36,310),corpse)
            d.text((col*264+36,505),'Final death pose',font=small,fill='white')
            im = atlas.crop((0, 0, 96, 96)).resize((192,192), Image.Resampling.NEAREST)
            sheet.paste(im, (col*264+36, 60), im)
            d.text((col*264+36, 266), name, font=font, fill='white')
    before.save(OUT/'valhallasc-deep-before.png')
    after.save(OUT/'valhallasc-deep-after.png')
    compare = Image.new('RGB', (len(KINDS)*264+24, 1150), '#244047')
    compare.paste(before, (0,0)); compare.paste(after, (0,540))
    d = ImageDraw.Draw(compare)
    d.text((22,1092), 'Sailors fall apart; the angler\'s light dies as it rolls over; the moray goes limp; the siren dissolves to foam;', font=font, fill='white')
    d.text((22,1120), 'the shellback tips over; the kraken deflates; the Ghostmaw fades to bones. Feet now rest on the ground.', font=font, fill='white')
    compare.save(OUT/'valhallasc-deep-before-after.png')
    for kind, name in zip(KINDS,NAMES):
        atlas = Image.open(ROOT/f'client/assets/deep_{kind}.png').convert('RGBA')
        gallery = Image.new('RGB',(8*192,5*218+36),'#244047')
        gd = ImageDraw.Draw(gallery)
        gd.text((12,8), name+' — every exported PixelFlow frame',font=font,fill='white')
        for clip,spec in meta['clips'].items():
            for n in range(spec['n']):
                x,y = n*192,36+spec['row']*218
                im=atlas.crop((n*96,spec['row']*96,(n+1)*96,(spec['row']+1)*96)).resize((192,192),Image.Resampling.NEAREST)
                gallery.paste(im,(x,y),im)
                gd.text((x+8,y+192),f'{clip} {n+1}',font=small,fill='white')
        gallery.save(OUT/f'valhallasc-deep-{kind}-frames.png')
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
        sequence[0].save(OUT/f'valhallasc-deep-{kind}-animations.gif',save_all=True,
                         append_images=sequence[1:],duration=50,loop=0,optimize=False)
        deaths=[]
        previous=Image.open(BACKUP/f'client/assets/deep_{kind}.png').convert('RGBA')
        for tick in range(80):
            n=min(7,int(((tick/20)%2)*8))
            im=Image.new('RGB',(480,260),'#244047');d=ImageDraw.Draw(im)
            for col,(label,source) in enumerate([('Before',previous),('After',atlas)]):
                crop=source.crop((n*96,4*96,(n+1)*96,5*96)).resize((192,192),Image.Resampling.NEAREST)
                im.paste(crop,(col*240+24,16),crop)
                d.text((col*240+24,220),label+' / die',font=font,fill='white')
            deaths.append(im)
        deaths[0].save(OUT/f'valhallasc-deep-{kind}-death-before-after.gif',save_all=True,
                      append_images=deaths[1:],duration=50,loop=0,optimize=False)
    print('27 before/after pictures, complete frame sheets and original-rate animations written.')


def verify():
    proof=json.loads((OUT/'editor-export-proof.json').read_text())
    count=0
    for kind, packet in proof.items():
        atlas=Image.open(ROOT/f'client/assets/deep_{kind}.png').convert('RGBA')
        meta=json.loads((ROOT/'client/assets/deep.txt').read_text())
        assert sha(ROOT/f'client/assets/deep_{kind}.png')==packet['atlasSha256']
        for entry in packet['frames']:
            row=meta['clips'][entry['clip']]['row'];n=entry['n']
            im=atlas.crop((n*96,row*96,(n+1)*96,(row+1)*96))
            assert hashlib.sha256(im.tobytes()).hexdigest()==entry['sha256']
            count+=1
    assert count==272
    # Exercise the actual rollback command on an isolated copy, then corrupt a
    # backup to prove preflight refuses it without partially changing the target.
    with tempfile.TemporaryDirectory(prefix='rollback-',dir=OUT) as temp:
        scratch=Path(temp)
        target=scratch/'target'; damaged=scratch/'damaged'
        backup_meta=json.loads((BACKUP/'manifest.txt').read_text())
        for name in backup_meta['files']:
            (target/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,target/name)
        command=['python3',str(ROOT/'scripts/rollback_deep_art.py'),'--target',str(target),'--apply']
        subprocess.run(command,check=True,capture_output=True)
        assert all(sha(target/name)==digest for name,digest in backup_meta['files'].items())
        shutil.copytree(BACKUP,damaged)
        (damaged/'client/assets/deep_kraken.png').write_bytes(b'corrupt')
        before={name:sha(target/name) for name in backup_meta['files']}
        failed=subprocess.run(command+['--backup',str(damaged)],capture_output=True)
        assert failed.returncode!=0 and all(sha(target/name)==digest for name,digest in before.items())
    for entry in ('make_deep_sprites.py', 'deep_slime_redraw.py'):
        refused=subprocess.run(['python3',str(ROOT/'scripts'/entry),'build','--replace'],capture_output=True)
        assert refused.returncode != 0 and b'--replace is refused' in refused.stderr
    live=Path('/home/serveperry/webserver/www/Valhallasc')
    assert all(sha(live/name)==digest for name,digest in backup_meta['files'].items())
    (OUT/'validation.json').write_text(json.dumps({'editorFramesMatch':count, 'liveArtUnchanged':True,
        'rollbackNineFilesVerified':True,'corruptBackupRefusedWithoutChanges':True,'destructiveBuildRefused':True,
        'originalFiles':json.loads((BACKUP/'manifest.txt').read_text())},indent=2)+'\n')
    print('272 saved-editor/export frame matches; nine-file rollback and corrupt-backup refusal pass.')


def upload():
    receipt=[]
    paths=sorted(OUT.glob('valhallasc-deep-*.png'))+sorted(OUT.glob('valhallasc-deep-*.gif'))
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
