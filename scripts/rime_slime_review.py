#!/usr/bin/env python3
"""Rimeveil redo (v2) review | verify | upload.  Upload is a separate explicit operation.

"Before" is the live v1 art (Beta 1.39.1) kept at /media/raid/valhallasc-data/rime-slime-v1-20261104; the pictures are
named valhallasc-rime-redo-* so the 15 verified v1 uploads and their receipt stay intact.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
V1 = Path('/media/raid/valhallasc-data/rime-slime-v1-20261104')
ORIGINAL = Path('/media/raid/valhallasc-data/rime-slime-original-20261103')
LIVE = Path('/home/serveperry/webserver/www/Valhallasc')
OUT = ROOT/'test-results/rime-slime'
KINDS = ['crab', 'wolf', 'yeti', 'wyrm']
NAMES = dict(crab='Rime Crab', wolf='Frost Wolf', yeti='Yeti', wyrm='Rime Wyrm')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 20)
small = ImageFont.truetype(FONT, 15)
BG = '#283c32'
CLIPS = ['idle', 'walk', 'attack', 'hurt', 'die']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Art:
    """One version of the zone's art: a root directory with client/assets/rime.txt and the four atlases."""
    def __init__(self, root):
        self.root = Path(root)
        self.meta = json.loads((self.root/'client/assets/rime.txt').read_text())
        self.atlas = {k: Image.open(self.root/f'client/assets/rime_{k}.png').convert('RGBA') for k in KINDS}

    def frame(self, kind):
        own = (self.meta.get('kindFrames') or {}).get(kind)
        (w, h), (ax, ay) = (own['frame'], own['anchor']) if own else (self.meta['frame'], self.meta['anchor'])
        return w, h, ax, ay

    def cell(self, kind, clip, n):
        w, h, _, _ = self.frame(kind)
        row = self.meta['clips'][clip]['row']
        return self.atlas[kind].crop((n*w, row*h, (n+1)*w, (row+1)*h))


CELL = (352, 240)       # a common 2x cell: the widest frame is 144 px (288 at 2x) with its anchor off-centre


def placed(art, kind, clip, n, scale=2, size=CELL):
    """The frame drawn at 2x on a common canvas with the anchor on one ground line and the anchor column centred, so before
    and after are compared at the same scale and on the same ground."""
    w, h, ax, ay = art.frame(kind)
    im = art.cell(kind, clip, n).resize((w*scale, h*scale), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    canvas.alpha_composite(im, (size[0]//2-ax*scale, size[1]-14-ay*scale-scale))
    return canvas


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    before, after = Art(V1), Art(ROOT)
    picks = [('Idle', 'idle', 0), ('Wind-up', 'attack', 2), ('Strike', 'attack', 4), ('Death', 'die', 7)]

    def board(art, label):
        sheet = Image.new('RGB', (len(KINDS)*CELL[0], 36+len(picks)*(CELL[1]+24)), BG)
        d = ImageDraw.Draw(sheet)
        d.text((14, 8), f'Rimeveil Glacier — {label} (same 2× scale, same ground line)', font=font, fill='#fff0cb')
        for c, kind in enumerate(KINDS):
            for r, (title, clip, n) in enumerate(picks):
                im = placed(art, kind, clip, n)
                x, y = c*CELL[0], 36+r*(CELL[1]+24)
                sheet.paste(im, (x, y), im)
                d.line([(x+8, y+CELL[1]-13), (x+CELL[0]-8, y+CELL[1]-13)], fill='#4c6a58')
                d.text((x+10, y+CELL[1]+2), f'{NAMES[kind]} / {title}', font=small, fill='white')
        return sheet
    a, b = board(after, 'after (v2)'), board(before, 'before (live v1)')
    a.save(OUT/'valhallasc-rime-redo-after.png')
    both = Image.new('RGB', (a.width, a.height*2), BG)
    both.paste(b, (0, 0))
    both.paste(a, (0, a.height))
    both.save(OUT/'valhallasc-rime-redo-before-after.png')
    # every attack frame, before above after, per kind
    half = (CELL[0]//2, CELL[1]//2)
    strip = Image.new('RGB', (8*half[0], 36+len(KINDS)*2*(half[1]+20)), BG)
    d = ImageDraw.Draw(strip)
    d.text((14, 8), 'Attack frames 1–8: before (live v1) above, after (v2) below', font=font, fill='#fff0cb')
    y = 36
    for kind in KINDS:
        for label, art in (('before', before), ('after', after)):
            for n in range(8):
                im = placed(art, kind, 'attack', n).resize(half, Image.Resampling.NEAREST)
                strip.paste(im, (n*half[0], y), im)
            d.text((6, y+half[1]), f'{NAMES[kind]} — {label}', font=small, fill='white')
            y += half[1]+20
    strip.save(OUT/'valhallasc-rime-redo-attacks-before-after.png')
    for kind in KINDS:
        w, h, _, ay = after.frame(kind)
        gallery = Image.new('RGB', (8*w*2, 36+5*(h*2+24)), BG)
        gd = ImageDraw.Draw(gallery)
        gd.text((12, 8), f'{NAMES[kind]} — every exported PixelFlow frame ({w}×{h})', font=font, fill='white')
        for clip in CLIPS:
            spec = after.meta['clips'][clip]
            for n in range(spec['n']):
                x, y = n*w*2, 36+spec['row']*(h*2+24)
                im = after.cell(kind, clip, n).resize((w*2, h*2), Image.Resampling.NEAREST)
                gallery.paste(im, (x, y), im)
                gd.text((x+8, y+h*2), f'{clip} {n+1}', font=small, fill='white')
                gd.line([(x, y+ay*2+2), (x+w*2, y+ay*2+2)], fill='#4c6a58')
        gallery.save(OUT/f'valhallasc-rime-redo-{kind}-frames.png')
        frames = []
        for tick in range(120):          # all five clips side by side, each at its own fps; die holds its last frame
            im = Image.new('RGB', (5*half[0], half[1]+22), BG)
            dd = ImageDraw.Draw(im)
            for col, clip in enumerate(CLIPS):
                spec = after.meta['clips'][clip]
                time = tick/20
                n = int(time*spec['fps']) % spec['n'] if clip != 'die' else min(spec['n']-1, int((time % 2)*spec['fps']))
                c = placed(after, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                im.paste(c, (col*half[0], 0), c)
                dd.text((col*half[0]+8, half[1]+2), clip, font=small, fill='white')
            frames.append(im)
        frames[0].save(OUT/f'valhallasc-rime-redo-{kind}-animations.gif', save_all=True, append_images=frames[1:], duration=50, loop=0)
        for clip in ('die', 'attack'):
            seq = []
            for tick in range(80):
                n = min(7, int(((tick/20) % 2)*8))
                im = Image.new('RGB', (2*half[0]+16, half[1]+24), BG)
                dd = ImageDraw.Draw(im)
                for col, (label, art) in enumerate((('Before', before), ('After', after))):
                    c = placed(art, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                    im.paste(c, (col*(half[0]+16), 0), c)
                    dd.text((col*(half[0]+16)+8, half[1]+4), f'{label} / {clip}', font=small, fill='white')
                seq.append(im)
            seq[0].save(OUT/f'valhallasc-rime-redo-{kind}-{clip}-before-after.gif', save_all=True, append_images=seq[1:], duration=50, loop=0)
    print('19 before/after pictures, frame sheets and animation previews written.')


def verify():
    """PRE-deployment check: the candidate matches its saved editor frames; both rollbacks work on a disposable copy; the
    live art is still the v1 art.  After deployment use `make_rime_sprites.py verify`."""
    proof = json.loads((OUT/'editor-export-proof.json').read_text())
    art, count = Art(ROOT), 0
    for kind, packet in proof.items():
        assert sha(ROOT/f'client/assets/rime_{kind}.png') == packet['atlasSha256']
        for entry in packet['frames']:
            assert hashlib.sha256(art.cell(kind, entry['clip'], entry['n']).tobytes()).hexdigest() == entry['sha256']
            count += 1
    assert count == 136
    results = {}
    for label, backup in (('v1', V1), ('original', ORIGINAL)):
        manifest = json.loads((backup/'manifest.txt').read_text())
        with tempfile.TemporaryDirectory(prefix='rime-rollback-') as temp:
            scratch = Path(temp)
            target, damaged = scratch/'target', scratch/'damaged'
            for name in manifest['files']:
                (target/name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT/name, target/name)
            command = ['python3', str(ROOT/'scripts/rollback_rime_art.py'), '--target', str(target), '--backup']
            subprocess.run(command+[str(backup), '--apply'], check=True, capture_output=True)
            assert all(sha(target/name) == digest for name, digest in manifest['files'].items()), label
            shutil.copytree(backup, damaged)
            (damaged/'client/assets/rime_yeti.png').write_bytes(b'corrupt')
            held = {name: sha(target/name) for name in manifest['files']}
            failed = subprocess.run(command+[str(damaged), '--apply'], capture_output=True)
            assert failed.returncode != 0 and all(sha(target/name) == digest for name, digest in held.items()), label
        results[label] = 'restored five files; corrupt backup refused without changes'
    v1 = json.loads((V1/'manifest.txt').read_text())
    assert all(sha(LIVE/name) == digest for name, digest in v1['files'].items()), 'live art is no longer the v1 art'
    (OUT/'validation.json').write_text(json.dumps(dict(editorFramesMatch=count, liveArtStillV1=True, rollback=results,
                                                       v1Files=v1['files']), indent=2)+'\n')
    print('136 saved-editor/export frame matches; v1 and original rollbacks and corrupt-backup refusal pass; live art is still v1.')


def upload():
    receipt = []
    paths = sorted(OUT.glob('valhallasc-rime-redo-*.png'))+sorted(OUT.glob('valhallasc-rime-redo-*.gif'))
    assert len(paths) == 19, 'Generate the complete review set first'
    for source in paths:
        mime = 'image/gif' if source.suffix == '.gif' else 'image/png'
        subprocess.run(['bash', str(ROOT/'scripts/filedrop_put.sh'), str(source), source.name, mime], check=True)
        dest = Path('/home/serveperry/webserver/www/filedrop/data/Sork/files')/source.name
        metadata = json.loads(Path(str(dest)+'.meta.json').read_text())
        assert sha(source) == sha(dest)
        assert metadata['original_name'] == source.name and metadata['type'] == mime
        assert metadata['size'] == source.stat().st_size == dest.stat().st_size
        assert Image.open(source).size == Image.open(dest).size
        receipt.append(dict(name=source.name, sha256=sha(source), bytes=source.stat().st_size, dimensions=Image.open(source).size, mime=mime))
    (OUT/'filedrop-receipt-redo.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(len(receipt), 'FileDrop pictures/animations verified')


if __name__ == '__main__':
    {'review': review, 'verify': verify, 'upload': upload}[sys.argv[1]]()
