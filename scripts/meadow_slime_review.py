#!/usr/bin/env python3
"""Build Ironhide review pictures, verify art/rollback, or upload requested previews.

Usage: meadow_slime_review.py review | verify | upload
Run make_ironhide_sprites.py export before verification.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/meadow-slime-original-20261103')
OUT = ROOT/'test-results/meadow-slime'
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
SMALL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
BG = '#283c32'
W, H = 72, 64


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose(atlas, row, n, scale=3):
    return atlas.crop((n*W, row*H, (n+1)*W, (row+1)*H)).resize(
        (W*scale, H*scale), Image.Resampling.NEAREST)


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT/'client/assets/ironhide.txt').read_text())
    old = Image.open(BACKUP/'client/assets/ironhide.png').convert('RGBA')
    new = Image.open(ROOT/'client/assets/ironhide.png').convert('RGBA')
    panels = []
    for label, atlas in [('Before', old), ('After', new)]:
        panel = Image.new('RGB', (520, 300), BG)
        d = ImageDraw.Draw(panel)
        d.text((16, 12), 'Greenmeadow / Ironhide — '+label, font=FONT, fill='white')
        for col, (clip, frame) in enumerate([('idle', 0), ('die', 7)]):
            im = pose(atlas, meta['clips'][clip]['row'], frame)
            panel.paste(im, (col*252+16, 54), im)
            d.text((col*252+16, 252), clip+' / final' if clip=='die' else clip,
                   font=FONT, fill='white')
        panel.save(OUT/f'valhallasc-meadow-{label.lower()}.png')
        panels.append(panel)
    compare = Image.new('RGB', (1040, 350), BG)
    for col, panel in enumerate(panels):
        compare.paste(panel, (col*520, 0))
    ImageDraw.Draw(compare).text((16, 310),
        'Same scale: glossy steel shell preserved; jointed legs buckle and the cracked shell tips.',
        font=FONT, fill='white')
    compare.save(OUT/'valhallasc-meadow-before-after.png')

    gallery = Image.new('RGB', (8*W*3, 5*(H*3+26)+36), BG)
    d = ImageDraw.Draw(gallery)
    d.text((12, 6), 'Ironhide / every saved PixelFlow frame', font=FONT, fill='white')
    for clip, spec in meta['clips'].items():
        for n in range(spec['n']):
            x, y = n*W*3, 36+spec['row']*(H*3+26)
            im = pose(new, spec['row'], n)
            gallery.paste(im, (x, y), im)
            d.text((x+8, y+H*3), f'{clip} {n+1}', font=SMALL, fill='white')
    gallery.save(OUT/'valhallasc-meadow-frames.png')

    deaths = Image.new('RGB', (8*W*2, 2*(H*2+32)+40), BG)
    d = ImageDraw.Draw(deaths)
    d.text((12, 6), 'Ironhide death / before and after at the same scale', font=FONT, fill='white')
    for row, (label, atlas) in enumerate([('Before', old), ('After', new)]):
        for n in range(8):
            im = pose(atlas, 4, n, 2)
            deaths.paste(im, (n*W*2, 40+row*160), im)
            d.text((n*W*2+8, 40+row*160+H*2), f'{label} {n+1}', font=SMALL, fill='white')
    deaths.save(OUT/'valhallasc-meadow-death-frames.png')

    # Original clip rates; hold the last death pose briefly before restarting.
    all_clips, death_compare = [], []
    for tick in range(120):
        time = tick/20
        image = Image.new('RGB', (5*232, 250), BG)
        d = ImageDraw.Draw(image)
        for col, (clip, spec) in enumerate(meta['clips'].items()):
            n = (min(spec['n']-1, int((time%2)*spec['fps'])) if clip=='die'
                 else int(time*spec['fps']) % spec['n'])
            im = pose(new, spec['row'], n)
            image.paste(im, (col*232+8, 12), im)
            d.text((col*232+8, 212), clip, font=FONT, fill='white')
        all_clips.append(image)
        image = Image.new('RGB', (520, 256), BG)
        d = ImageDraw.Draw(image)
        n = min(7, int((time%2)*8))
        for col, (label, atlas) in enumerate([('Before', old), ('After', new)]):
            im = pose(atlas, 4, n)
            image.paste(im, (col*252+16, 8), im)
            d.text((col*252+16, 214), label+' / die', font=FONT, fill='white')
        death_compare.append(image)
    for name, frames in [('animations', all_clips), ('death-before-after', death_compare)]:
        frames[0].save(OUT/f'valhallasc-meadow-{name}.gif', save_all=True,
                       append_images=frames[1:], duration=50, loop=0, optimize=False)
    print('Seven before/after, full-frame and animated review files generated.')


def verify():
    proof = json.loads((OUT/'editor-export-proof.json').read_text())
    atlas = Image.open(ROOT/'client/assets/ironhide.png').convert('RGBA')
    meta = json.loads((ROOT/'client/assets/ironhide.txt').read_text())
    assert len(proof['frames']) == 34
    for entry in proof['frames']:
        row, n = meta['clips'][entry['clip']]['row'], entry['n']
        im = atlas.crop((n*W, row*H, (n+1)*W, (row+1)*H))
        assert hashlib.sha256(im.tobytes()).hexdigest() == entry['sha256']
    manifest = json.loads((BACKUP/'manifest.txt').read_text())
    with tempfile.TemporaryDirectory(prefix='meadow-rollback-') as temp:
        scratch = Path(temp)
        target, damaged = scratch/'target', scratch/'damaged'
        for name in manifest['files']:
            (target/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target/name)
        command = [sys.executable, str(ROOT/'scripts/rollback_meadow_art.py'),
                   '--target', str(target), '--apply']
        subprocess.run(command, check=True, capture_output=True)
        assert all(sha(target/name)==digest for name,digest in manifest['files'].items())
        shutil.copytree(BACKUP, damaged)
        (damaged/'client/assets/ironhide.png').write_bytes(b'corrupt')
        before = {name: sha(target/name) for name in manifest['files']}
        failed = subprocess.run(command+['--backup', str(damaged)], capture_output=True)
        assert failed.returncode != 0
        assert all(sha(target/name)==digest for name,digest in before.items())
    live = Path('/home/serveperry/webserver/www/Valhallasc')
    assert all(sha(live/name)==digest for name,digest in manifest['files'].items())
    (OUT/'validation.json').write_text(json.dumps(dict(editorFramesMatch=34,
        rollbackTwoFilesVerified=True, corruptBackupRefusedWithoutChanges=True,
        liveArtUnchanged=True, originalFiles=manifest,
        atlasSha256=sha(ROOT/'client/assets/ironhide.png')), indent=2)+'\n')
    print('34 editor/export matches, rollback, corrupt-backup refusal and unchanged live art pass.')


def upload():
    paths = sorted(OUT.glob('valhallasc-meadow-*.png'))+sorted(OUT.glob('valhallasc-meadow-*.gif'))
    assert len(paths) == 7, 'Generate the complete review set first'
    receipt = []
    for source in paths:
        mime = 'image/gif' if source.suffix=='.gif' else 'image/png'
        subprocess.run(['bash', str(ROOT/'scripts/filedrop_put.sh'), str(source), source.name, mime], check=True)
        dest = Path('/home/serveperry/webserver/www/filedrop/data/Sork/files')/source.name
        metadata = json.loads(Path(str(dest)+'.meta.json').read_text())
        assert sha(source)==sha(dest)
        assert metadata['original_name']==source.name and metadata['type']==mime
        assert metadata['size']==source.stat().st_size==dest.stat().st_size
        assert Image.open(source).size==Image.open(dest).size
        receipt.append(dict(name=source.name, sha256=sha(source), bytes=source.stat().st_size,
                            dimensions=Image.open(source).size, mime=mime))
    (OUT/'filedrop-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('All seven FileDrop destinations and metadata verified.')


if __name__ == '__main__':
    {'review': review, 'verify': verify, 'upload': upload}[sys.argv[1]]()
