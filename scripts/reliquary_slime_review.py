#!/usr/bin/env python3
"""Coral Reliquary review | verify | upload. Upload is a separate explicit operation."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path('/media/raid/valhallasc-data/reliquary-slime-original-20261104')
LIVE = Path('/home/serveperry/webserver/www/Valhallasc')
OUT = ROOT / 'test-results/reliquary-slime'
KINDS = ['reliccrab', 'pearlwidow', 'glasscantor', 'relicwarden', 'coralregent', 'reliquarypearl']
NAMES = dict(
    reliccrab='Reliquary Crab',
    pearlwidow='Pearl Widow',
    glasscantor='Glass Cantor',
    relicwarden='Relic Warden',
    coralregent='Coral Regent',
    reliquarypearl='Reliquary Pearl',
)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 20)
small = ImageFont.truetype(FONT, 15)
BG = '#2c2238'
CLIPS = ['idle', 'walk', 'attack', 'hurt', 'die']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Art:
    """One version of the zone's art: either the backup dir or the worktree root."""
    def __init__(self, root, manifest_rel='client/assets/cathedral.txt'):
        self.root = Path(root)
        self.meta = json.loads((self.root / manifest_rel).read_text())
        self.atlas = {k: Image.open(self.root / f'client/assets/cathedral_{k}.png').convert('RGBA') for k in KINDS}

    def frame(self, kind):
        own = (self.meta.get('kindFrames') or {}).get(kind)
        (w, h), (ax, ay) = (own['frame'], own['anchor']) if own else (self.meta['frame'], self.meta['anchor'])
        return w, h, ax, ay

    def cell(self, kind, clip, n):
        w, h, _, _ = self.frame(kind)
        row = self.meta['clips'][clip]['row']
        return self.atlas[kind].crop((n * w, row * h, (n + 1) * w, (row + 1) * h))


CELL = (340, 256)


def placed(art, kind, clip, n, scale=2, size=CELL):
    """Draw the frame at 2x on a common canvas with the anchor on one ground line and the anchor column centred."""
    w, h, ax, ay = art.frame(kind)
    im = art.cell(kind, clip, n).resize((w * scale, h * scale), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', size, (0, 0, 0, 0))
    canvas.alpha_composite(im, (size[0] // 2 - ax * scale, size[1] - 14 - ay * scale - scale))
    return canvas


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    before = Art(BACKUP, 'client/assets/cathedral.full-manifest-reference.txt')
    after = Art(ROOT)
    picks = [('Idle', 'idle', 0), ('Wind-up', 'attack', 2), ('Strike', 'attack', 4), ('Death', 'die', 7)]

    def board(art, label):
        sheet = Image.new('RGB', (len(KINDS) * CELL[0], 36 + len(picks) * (CELL[1] + 24)), BG)
        d = ImageDraw.Draw(sheet)
        d.text((14, 8), f'Coral Reliquary — {label} (same 2× scale, same ground line)', font=font, fill='#fff0cb')
        for c, kind in enumerate(KINDS):
            for r, (title, clip, n) in enumerate(picks):
                im = placed(art, kind, clip, n)
                x, y = c * CELL[0], 36 + r * (CELL[1] + 24)
                sheet.paste(im, (x, y), im)
                d.line([(x + 8, y + CELL[1] - 13), (x + CELL[0] - 8, y + CELL[1] - 13)], fill='#6e4a7e')
                d.text((x + 10, y + CELL[1] + 2), f'{NAMES[kind]} / {title}', font=small, fill='white')
        return sheet

    b = board(before, 'Before')
    a = board(after, 'After')
    b.save(OUT / 'valhallasc-reliquary-before.png')
    a.save(OUT / 'valhallasc-reliquary-after.png')
    both = Image.new('RGB', (a.width, a.height * 2), BG)
    both.paste(b, (0, 0))
    both.paste(a, (0, a.height))
    both.save(OUT / 'valhallasc-reliquary-before-after.png')

    half = (CELL[0] // 2, CELL[1] // 2)
    strip = Image.new('RGB', (8 * half[0], 36 + len(KINDS) * 2 * (half[1] + 20)), BG)
    d = ImageDraw.Draw(strip)
    d.text((14, 8), 'Coral Reliquary attack frames 1–8: before above, after below', font=font, fill='#fff0cb')
    y = 36
    for kind in KINDS:
        for label, art in (('before', before), ('after', after)):
            for n in range(8):
                im = placed(art, kind, 'attack', n).resize(half, Image.Resampling.NEAREST)
                strip.paste(im, (n * half[0], y), im)
            d.text((6, y + half[1]), f'{NAMES[kind]} — {label}', font=small, fill='white')
            y += half[1] + 20
    strip.save(OUT / 'valhallasc-reliquary-attacks-before-after.png')

    for kind in KINDS:
        w, h, _, ay = after.frame(kind)
        gallery = Image.new('RGB', (8 * w * 2, 36 + 5 * (h * 2 + 24)), BG)
        gd = ImageDraw.Draw(gallery)
        gd.text((12, 8), f'{NAMES[kind]} — every exported PixelFlow frame ({w}×{h})', font=font, fill='white')
        for clip in CLIPS:
            spec = after.meta['clips'][clip]
            for n in range(spec['n']):
                x, y = n * w * 2, 36 + spec['row'] * (h * 2 + 24)
                im = after.cell(kind, clip, n).resize((w * 2, h * 2), Image.Resampling.NEAREST)
                gallery.paste(im, (x, y), im)
                gd.text((x + 8, y + h * 2), f'{clip} {n + 1}', font=small, fill='white')
                gd.line([(x, y + ay * 2 + 2), (x + w * 2, y + ay * 2 + 2)], fill='#6e4a7e')
        gallery.save(OUT / f'valhallasc-reliquary-{kind}-frames.png')

        frames = []
        for tick in range(120):
            im = Image.new('RGB', (5 * half[0], half[1] + 22), BG)
            dd = ImageDraw.Draw(im)
            for col, clip in enumerate(CLIPS):
                spec = after.meta['clips'][clip]
                time = tick / 20
                n = int(time * spec['fps']) % spec['n'] if clip != 'die' else min(spec['n'] - 1, int((time % 2) * spec['fps']))
                c = placed(after, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                im.paste(c, (col * half[0], 0), c)
                dd.text((col * half[0] + 8, half[1] + 2), clip, font=small, fill='white')
            frames.append(im)
        frames[0].save(OUT / f'valhallasc-reliquary-{kind}-animations.gif', save_all=True,
                       append_images=frames[1:], duration=50, loop=0)

        for clip, suffix in (('die', 'death'), ('attack', 'attack')):
            seq = []
            for tick in range(80):
                n = min(7, int(((tick / 20) % 2) * 8))
                im = Image.new('RGB', (2 * half[0] + 16, half[1] + 24), BG)
                dd = ImageDraw.Draw(im)
                for col, (label, art) in enumerate((('Before', before), ('After', after))):
                    c = placed(art, kind, clip, n).resize(half, Image.Resampling.NEAREST)
                    im.paste(c, (col * (half[0] + 16), 0), c)
                    dd.text((col * (half[0] + 16) + 8, half[1] + 4), f'{label} / {clip}', font=small, fill='white')
                seq.append(im)
            seq[0].save(OUT / f'valhallasc-reliquary-{kind}-{suffix}-before-after.gif', save_all=True,
                        append_images=seq[1:], duration=50, loop=0)
    print('28 before/after pictures, complete frame sheets and original-rate animations written.')


def verify():
    """PRE-deployment check: candidate matches saved editor frames; rollback merges only these 6 entries; live art unchanged."""
    proof = json.loads((OUT / 'editor-export-proof.json').read_text())
    art, count = Art(ROOT), 0
    for kind, packet in proof.items():
        assert sha(ROOT / f'client/assets/cathedral_{kind}.png') == packet['atlasSha256']
        for entry in packet['frames']:
            assert hashlib.sha256(art.cell(kind, entry['clip'], entry['n']).tobytes()).hexdigest() == entry['sha256']
            count += 1
    assert count == 204

    backup_meta = json.loads((BACKUP / 'manifest.txt').read_text())
    manifest = 'client/assets/cathedral.txt'
    with tempfile.TemporaryDirectory(prefix='reliquary-rollback-', dir=OUT) as temp:
        scratch = Path(temp)
        target, damaged = scratch / 'target', scratch / 'damaged'
        for name in list(backup_meta['files']) + [manifest]:
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target / name)
        live = json.loads((target / manifest).read_text())
        live['sprites']['abysszealot'] = 'NAVE_EDIT'
        live['tops']['abysszealot'] = 1
        (target / manifest).write_text(json.dumps(live, indent=2) + '\n')
        command = ['python3', str(ROOT / 'scripts/rollback_reliquary_art.py'), '--target', str(target), '--apply']
        shutil.copytree(BACKUP, damaged)
        (damaged / 'client/assets/cathedral_reliccrab.png').write_bytes(b'corrupt')
        before = {name: sha(target / name) for name in list(backup_meta['files']) + [manifest]}
        failed = subprocess.run(command + ['--backup', str(damaged)], capture_output=True)
        assert failed.returncode != 0 and all(sha(target / name) == digest for name, digest in before.items())
        subprocess.run(command, check=True, capture_output=True)
        assert all(sha(target / name) == digest for name, digest in backup_meta['files'].items())
        restored = json.loads((target / manifest).read_text())
        assert all(restored['sprites'][k] == backup_meta['oldSprites'][k] and
                   restored['tops'][k] == backup_meta['oldTops'][k] for k in backup_meta['kinds'])
        assert all(k not in (restored.get('kindFrames') or {}) for k in backup_meta['kinds'])
        assert restored['sprites']['abysszealot'] == 'NAVE_EDIT' and restored['tops']['abysszealot'] == 1, \
            'rollback must not touch other kinds'
        original = json.loads((BACKUP / 'client/assets/cathedral.full-manifest-reference.txt').read_text())
        restored['sprites']['abysszealot'] = original['sprites']['abysszealot']
        restored['tops']['abysszealot'] = original['tops']['abysszealot']
        assert restored == original, 'restored manifest equals the original except for the unrelated edit'

    for entry, args in (('make_cathedral_sprites.py', ['reliccrab']), ('reliquary_slime_redraw.py', [])):
        refused = subprocess.run(['python3', str(ROOT / 'scripts' / entry), 'build', *args, '--replace'], capture_output=True)
        assert refused.returncode != 0 and b'--replace is refused' in refused.stderr
    other = subprocess.run(['python3', str(ROOT / 'scripts/make_cathedral_sprites.py'), 'verify', 'abysszealot'], capture_output=True)
    assert other.returncode == 0 and b'pixel-identical' in other.stdout
    assert all(sha(LIVE / name) == digest for name, digest in backup_meta['files'].items()), 'live art changed prematurely'
    assert sha(LIVE / manifest) == backup_meta['fullManifestSha256'], 'live cathedral.txt changed prematurely'

    (OUT / 'validation.json').write_text(json.dumps({
        'editorFramesMatch': count,
        'rollbackSixAtlasesAndManifestEntriesVerified': True,
        'unrelatedManifestEditSurvivesRollback': True,
        'corruptBackupRefusedWithoutChanges': True,
        'destructiveBuildRefused': True,
        'otherCathedralKindsStillVerify': True,
        'liveArtUnchanged': True,
        'originalFiles': backup_meta,
    }, indent=2) + '\n')
    print('204 saved-editor/export frame matches; six-atlas rollback (manifest merge) and corrupt-backup refusal pass; live art untouched.')


def upload():
    receipt = []
    paths = sorted(OUT.glob('valhallasc-reliquary-*.png')) + sorted(OUT.glob('valhallasc-reliquary-*.gif'))
    expected = 4 + len(KINDS) * 4
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
