#!/usr/bin/env python3
"""The Moonwell review | verify | upload. Upload is a separate explicit operation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/moonwell-slime-original-20261104')  # the original cel-shaded art this redo replaces
LIVE = Path('/home/serveperry/webserver/www/Valhallasc')
OUT = ROOT / 'test-results/moonwell-slime'
KINDS = ['dew_moth', 'lumen_eel', 'rootbell', 'tideglass_heron', 'hourpetal_stag', 'moonskein_weaver', 'moonwell_echo']
NAMES = dict(dew_moth='Dew Moth', lumen_eel='Lumen Eel', rootbell='Rootbell', tideglass_heron='Tideglass Heron', hourpetal_stag='Hourpetal Stag', moonskein_weaver='Moonskein Weaver', moonwell_echo='Moonwell Echo')

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 20)
small = ImageFont.truetype(FONT, 15)
BG = '#1e1a34'
CLIPS = ['idle', 'walk', 'attack', 'hurt', 'die']


def atlas_name(k):
    return 'client/assets/moonwell_echo.png' if k == 'moonwell_echo' else f'client/assets/moonwell_{k}.png'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Art:
    """One version of the zone's art: either the backup dir or the worktree root."""
    def __init__(self, root):
        self.root = Path(root)
        self.metas = {'moonwell_echo': json.loads((self.root / 'client/assets/moonwell.txt').read_text())}
        garden = json.loads((self.root / 'client/assets/moonwell_garden.txt').read_text())
        self.metas.update({k: garden for k in KINDS if k != 'moonwell_echo'})
        self.meta = garden
        self.atlas = {k: Image.open(self.root / atlas_name(k)).convert('RGBA') for k in KINDS}

    def frame(self, kind):
        meta = self.metas[kind]
        own = (meta.get('kindFrames') or {}).get(kind)
        (w, h), (ax, ay) = (own['frame'], own['anchor']) if own else (meta['frame'], meta['anchor'])
        return w, h, ax, ay

    def cell(self, kind, clip, n):
        w, h, _, _ = self.frame(kind)
        row = self.metas[kind]['clips'][clip]['row']
        return self.atlas[kind].crop((n * w, row * h, (n + 1) * w, (row + 1) * h))


CELL = (420, 300)


def placed(art, kind, clip, n, scale=2, size=CELL):
    """Draw the frame at 2x on a common canvas with the anchor on one ground line and the anchor column centred."""
    w, h, ax, ay = art.frame(kind)
    im = art.cell(kind, clip, n).resize((w * scale, h * scale), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    canvas.alpha_composite(im, (size[0] // 2 - ax * scale, size[1] - 14 - ay * scale - scale))
    return canvas


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    before = Art(BACKUP)
    after = Art(ROOT)
    picks = [('Idle', 'idle', 0), ('Wind-up', 'attack', 2), ('Strike', 'attack', 4), ('Death', 'die', 7)]

    def board(art, label):
        sheet = Image.new('RGB', (len(KINDS) * CELL[0], 36 + len(picks) * (CELL[1] + 24)), BG)
        d = ImageDraw.Draw(sheet)
        d.text((14, 8), f'The Moonwell redo — {label} (same 2× scale, same ground line)', font=font, fill='#fff0cb')
        for c, kind in enumerate(KINDS):
            for r, (title, clip, n) in enumerate(picks):
                im = placed(art, kind, clip, n)
                x, y = c * CELL[0], 36 + r * (CELL[1] + 24)
                sheet.paste(im, (x, y), im)
                d.line([(x + 8, y + CELL[1] - 13), (x + CELL[0] - 8, y + CELL[1] - 13)], fill='#5c4e8e')
                d.text((x + 10, y + CELL[1] + 2), f'{NAMES[kind]} / {title}', font=small, fill='white')
        return sheet

    b = board(before, 'Before (live original)')
    a = board(after, 'After (slime-style redo)')
    b.save(OUT / 'valhallasc-moonwell-before.png')
    a.save(OUT / 'valhallasc-moonwell-after.png')
    both = Image.new('RGB', (a.width, a.height * 2), BG)
    both.paste(b, (0, 0))
    both.paste(a, (0, a.height))
    both.save(OUT / 'valhallasc-moonwell-before-after.png')

    half = (CELL[0] // 2, CELL[1] // 2)
    strip = Image.new('RGB', (8 * half[0], 36 + len(KINDS) * 2 * (half[1] + 20)), BG)
    d = ImageDraw.Draw(strip)
    d.text((14, 8), 'The Moonwell attack frames 1–8: before above, after below', font=font, fill='#fff0cb')
    y = 36
    for kind in KINDS:
        for label, art in (('before', before), ('after', after)):
            for n in range(8):
                im = placed(art, kind, 'attack', n).resize(half, Image.Resampling.NEAREST)
                strip.paste(im, (n * half[0], y), im)
            d.text((6, y + half[1]), f'{NAMES[kind]} — {label}', font=small, fill='white')
            y += half[1] + 20
    strip.save(OUT / 'valhallasc-moonwell-attacks-before-after.png')

    for kind in KINDS:
        w, h, _, ay = after.frame(kind)
        gallery = Image.new('RGB', (8 * w * 2, 36 + 5 * (h * 2 + 24)), BG)
        gd = ImageDraw.Draw(gallery)
        gd.text((12, 8), f'{NAMES[kind]} — every exported PixelFlow frame ({w}×{h})', font=font, fill='white')
        for clip in CLIPS:
            spec = after.metas[kind]['clips'][clip]
            for n in range(spec['n']):
                x, y = n * w * 2, 36 + spec['row'] * (h * 2 + 24)
                im = after.cell(kind, clip, n).resize((w * 2, h * 2), Image.Resampling.NEAREST)
                gallery.paste(im, (x, y), im)
                gd.text((x + 8, y + h * 2), f'{clip} {n + 1}', font=small, fill='white')
                gd.line([(x, y + ay * 2 + 2), (x + w * 2, y + ay * 2 + 2)], fill='#5c4e8e')
        gallery.save(OUT / f'valhallasc-moonwell-{kind}-frames.png')

        frames = []
        for tick in range(120):
            im = Image.new('RGB', (5 * half[0], half[1] + 22), BG)
            dd = ImageDraw.Draw(im)
            for col, clip in enumerate(CLIPS):
                spec = after.metas[kind]['clips'][clip]
                time = tick / 20
                n = int(time * spec['fps']) % spec['n'] if clip != 'die' else min(spec['n'] - 1, int((time % 2) * spec['fps']))
                c = placed(after, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                im.paste(c, (col * half[0], 0), c)
                dd.text((col * half[0] + 8, half[1] + 2), clip, font=small, fill='white')
            frames.append(im)
        frames[0].save(OUT / f'valhallasc-moonwell-{kind}-animations.gif', save_all=True,
                       append_images=frames[1:], duration=50, loop=0)

        for clip, suffix in (('die', 'death'), ('attack', 'attack')):
            seq = []
            for tick in range(80):
                n = min(7, int(((tick / 20) % 2) * 10))
                im = Image.new('RGB', (2 * half[0] + 16, half[1] + 24), BG)
                dd = ImageDraw.Draw(im)
                for col, (label, art) in enumerate((('Before', before), ('After', after))):
                    c = placed(art, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                    im.paste(c, (col * (half[0] + 16), 0), c)
                    dd.text((col * (half[0] + 16) + 8, half[1] + 4), f'{label} / {clip}', font=small, fill='white')
                seq.append(im)
            seq[0].save(OUT / f'valhallasc-moonwell-{kind}-{suffix}-before-after.gif', save_all=True,
                        append_images=seq[1:], duration=50, loop=0)
    # All eight death comparisons together, at the manifest's 10 fps with a pause on the final pose.
    combined = []
    panel_w, panel_h = half[0] * 2, half[1] + 24
    for tick in range(80):
        canvas = Image.new('RGB', (panel_w * 4, panel_h * 2), BG)
        cd = ImageDraw.Draw(canvas)
        for i, kind in enumerate(KINDS):
            x, y = (i % 4) * panel_w, (i // 4) * panel_h
            for col, art in enumerate((before, after)):
                count = art.metas[kind]['clips']['die']['n']
                n = min(count - 1, int(((tick / 20) % 2) * art.metas[kind]['clips']['die']['fps']))
                cell = placed(art, kind, 'die', n).resize(half, Image.Resampling.NEAREST)
                canvas.paste(cell, (x + col * half[0], y), cell)
            cd.text((x + 8, y + half[1] + 3), f'{NAMES[kind]} / Before     |     After', font=small, fill='white')
        combined.append(canvas)
    combined[0].save(OUT / 'valhallasc-moonwell-deaths-before-after.gif', save_all=True,
                     append_images=combined[1:], duration=50, loop=0)
    print('33 before/after pictures, complete frame sheets and original-rate animations written.')


def verify():
    """PRE-deployment check: candidate matches saved editor frames; rollback restores all nine files; live art unchanged."""
    proof = json.loads((OUT / 'editor-export-proof.json').read_text())
    art, count = Art(ROOT), 0
    for kind, packet in proof.items():
        assert sha(ROOT / atlas_name(kind)) == packet['atlasSha256']
        for entry in packet['frames']:
            assert hashlib.sha256(art.cell(kind, entry['clip'], entry['n']).tobytes()).hexdigest() == entry['sha256']
            count += 1
    assert count == 238

    backup_meta = json.loads((BACKUP / 'manifest.txt').read_text())
    with tempfile.TemporaryDirectory(prefix='moonwell-rollback-', dir=OUT) as temp:
        scratch = Path(temp)
        target, damaged = scratch / 'target', scratch / 'damaged'
        for name in backup_meta['files']:
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target / name)
        command = ['python3', str(ROOT / 'scripts/rollback_moonwell_art.py'), '--target', str(target), '--apply']
        shutil.copytree(BACKUP, damaged)
        (damaged / 'client/assets/moonwell_dew_moth.png').write_bytes(b'corrupt')
        before = {name: sha(target / name) for name in backup_meta['files']}
        failed = subprocess.run(command + ['--backup', str(damaged)], capture_output=True)
        assert failed.returncode != 0 and all(sha(target / name) == digest for name, digest in before.items())
        subprocess.run(command, check=True, capture_output=True)
        assert all(sha(target / name) == digest for name, digest in backup_meta['files'].items())
        for name in ('client/assets/moonwell.txt', 'client/assets/moonwell_garden.txt'):
            restored = json.loads((target / name).read_text())
            assert 'kindFrames' not in restored and set(restored['kinds']) <= set(KINDS), name

    for entry in ('make_moonwell_sprites.py', 'make_moonwell_garden_sprites.py', 'moonwell_slime_redraw.py'):
        refused = subprocess.run(['python3', str(ROOT / 'scripts' / entry), 'build', '--replace'], capture_output=True)
        assert refused.returncode != 0 and b'--replace is refused' in refused.stderr
    assert all(sha(LIVE / name) == digest for name, digest in backup_meta['files'].items()), 'live art changed prematurely'

    (OUT / 'validation.json').write_text(json.dumps({
        'editorFramesMatch': count,
        'rollbackNineFilesVerified': True,
        'corruptBackupRefusedWithoutChanges': True,
        'destructiveBuildRefused': True,
        'liveArtUnchanged': True,
        'originalFiles': backup_meta,
    }, indent=2) + '\n')
    print('238 saved-editor/export frame matches; nine-file rollback and corrupt-backup refusal pass; live art untouched.')


def upload():
    receipt = []
    paths = sorted(OUT.glob('valhallasc-moonwell-*.png')) + sorted(OUT.glob('valhallasc-moonwell-*.gif'))
    expected = 5 + len(KINDS) * 4
    assert len(paths) == expected, f'Generate the complete review set first (found {len(paths)}, expected {expected})'
    for source in paths:
        mime = 'image/gif' if source.suffix == '.gif' else 'image/png'
        subprocess.run(['bash', str(ROOT / 'scripts/filedrop_put.sh'), str(source), source.name, mime], check=True)
        dest = Path('/home/serveperry/webserver/www/filedrop/data/Sork/files') / source.name
        metadata = json.loads(Path(str(dest) + '.meta.json').read_text())
        assert sha(source) == sha(dest)
        assert metadata['original_name'] == source.name and metadata['type'] == mime
        assert metadata['size'] == source.stat().st_size == dest.stat().st_size
        assert Image.open(source).size == Image.open(dest).size
        receipt.append({
            'name': source.name, 'sha256': sha(source), 'bytes': source.stat().st_size,
            'dimensions': Image.open(source).size, 'mime': mime,
        })
    (OUT / 'filedrop-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(len(receipt), 'FileDrop pictures/animations verified')


if __name__ == '__main__':
    {'review': review, 'verify': verify, 'upload': upload}[sys.argv[1]]()
