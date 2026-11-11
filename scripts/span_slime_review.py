#!/usr/bin/env python3
"""Render, verify and upload the 29 The Shattered Span enemy review sheets and animations."""
import hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import span_slime_redraw as R

ROOT = R.ROOT
BACKUP = Path('/media/raid/valhallasc-data/span-slime-original-20261111')
OUT = R.OUT
FILEDROP = Path('/home/serveperry/webserver/data/filedrop')
CLIPS = [('idle', 6, 170), ('walk', 8, 100), ('attack', 8, 85), ('hurt', 4, 100), ('die', 8, 125)]


def expected_files():
    out = [
        'valhallasc-span-before.png',
        'valhallasc-span-after.png',
        'valhallasc-span-before-after.png',
        'valhallasc-span-attacks-before-after.png',
        'valhallasc-span-deaths-before-after.gif',
    ]
    for k in R.KINDS:
        out += [
            f'valhallasc-span-{k}-frames.png',
            f'valhallasc-span-{k}-animations.gif',
            f'valhallasc-span-{k}-death-before-after.gif',
            f'valhallasc-span-{k}-attack-before-after.gif',
        ]
    return out


def open_atlas(base: Path, kind: str) -> Image.Image:
    return Image.open(base / f'client/assets/cathedral_{kind}.png').convert('RGBA')


def manifest_frame(base: Path, kind: str):
    meta = json.loads((base / 'client/assets/cathedral.txt').read_text())
    return R.kindframe.frame_of(meta, kind)


def cell_crop(atlas: Image.Image, row: int, n: int, fw: int, fh: int) -> Image.Image:
    return atlas.crop((n * fw, row * fh, (n + 1) * fw, (row + 1) * fh))


def paste_anchored(dst: Image.Image, cell: Image.Image, ax: int, ay: int, cx: int, gy: int, scale: int = 2):
    bbox = cell.getbbox()
    if bbox:
        assert cx + (bbox[0] - ax) * scale >= 0 and cx + (bbox[2] - ax) * scale <= dst.width, ('review horizontal clipping', bbox, cx)
        assert gy + (bbox[1] - ay) * scale >= 0 and gy + (bbox[3] - ay) * scale <= dst.height, ('review vertical clipping', bbox, gy)
    up = cell.resize((cell.width * scale, cell.height * scale), Image.NEAREST)
    dst.alpha_composite(up, (cx - ax * scale, gy - ay * scale))


def draw_ground(d: ImageDraw.ImageDraw, x0: int, x1: int, gy: int):
    d.line([(x0, gy), (x1, gy)], fill=(76, 98, 126, 255), width=1)


def render_roster_board(base: Path, title: str, out_path: Path):
    cols = [(0, 0, 'idle 0'), (1, 2, 'walk 2'), (2, 1, 'wind-up'), (2, 3, 'strike'), (4, 3, 'die 3'), (4, 7, 'die 7')]
    cw, rh = 400, 376
    im = Image.new('RGBA', (len(cols) * cw + 180, len(R.KINDS) * rh + 60), (24, 30, 42, 255))
    d = ImageDraw.Draw(im)
    d.text((16, 14), title, fill=(204, 242, 248, 255))
    for ci, (_, _, label) in enumerate(cols):
        d.text((180 + ci * cw + 56, 34), label, fill=(175, 190, 212, 255))
    for ki, kind in enumerate(R.KINDS):
        atlas = open_atlas(base, kind)
        fw, fh, ax, ay = manifest_frame(base, kind)
        gy = 56 + ki * rh + 330
        d.text((14, gy - 68), f'{R.NAMES[kind]}\n({kind})', fill=(228, 234, 245, 255))
        for ci, (row, n, _) in enumerate(cols):
            cx = 180 + ci * cw + cw // 2
            draw_ground(d, cx - 64, cx + 64, gy)
            paste_anchored(im, cell_crop(atlas, row, n, fw, fh), ax, ay, cx, gy, scale=2)
    im.save(out_path)


def render_before_after_board(out_path: Path):
    pairs = [(0, 0, 'Idle'), (2, 1, 'Wind-up'), (2, 3, 'Strike'), (4, 3, 'Mid-die'), (4, 7, 'Dead')]
    cw, rh = 560, 376
    im = Image.new('RGBA', (len(pairs) * cw + 170, len(R.KINDS) * rh + 64), (22, 28, 40, 255))
    d = ImageDraw.Draw(im)
    d.text((16, 14), 'Zone 42 - The Shattered Span (6 dungeon encounters): Before (left) vs After (right)', fill=(240, 244, 250, 255))
    for pi, (_, _, label) in enumerate(pairs):
        d.text((170 + pi * cw + 74, 36), f'{label} (old / new)', fill=(176, 192, 214, 255))
    for ki, kind in enumerate(R.KINDS):
        old_a, new_a = open_atlas(BACKUP, kind), open_atlas(ROOT, kind)
        ofw, ofh, oax, oay = manifest_frame(BACKUP, kind)
        nfw, nfh, nax, nay = manifest_frame(ROOT, kind)
        gy = 58 + ki * rh + 330
        d.text((12, gy - 72), f'{R.NAMES[kind]}\n{kind}', fill=(230, 236, 246, 255))
        for pi, (row, n, _) in enumerate(pairs):
            x0 = 170 + pi * cw
            draw_ground(d, x0 + 14, x0 + cw - 14, gy)
            paste_anchored(im, cell_crop(old_a, row, n, ofw, ofh), oax, oay, x0 + 110, gy, scale=2)
            paste_anchored(im, cell_crop(new_a, row, n, nfw, nfh), nax, nay, x0 + 360, gy, scale=2)
    im.save(out_path)


def render_attacks_board(out_path: Path):
    cw, rh = 400, 740
    im = Image.new('RGBA', (8 * cw + 170, len(R.KINDS) * rh + 58), (22, 28, 40, 255))
    d = ImageDraw.Draw(im)
    d.text((16, 14), 'Zone 42 - The Shattered Span Attack Strip (8 frames): top = Before, bottom = After', fill=(240, 244, 250, 255))
    for n in range(8):
        d.text((170 + n * cw + 52, 34), f'atk {n}', fill=(176, 192, 214, 255))
    for ki, kind in enumerate(R.KINDS):
        old_a, new_a = open_atlas(BACKUP, kind), open_atlas(ROOT, kind)
        ofw, ofh, oax, oay = manifest_frame(BACKUP, kind)
        nfw, nfh, nax, nay = manifest_frame(ROOT, kind)
        y_top = 56 + ki * rh
        gy_old, gy_new = y_top + 350, y_top + 718
        d.text((12, y_top + 54), f'{R.NAMES[kind]}\n{kind}', fill=(230, 236, 246, 255))
        for n in range(8):
            cx = 170 + n * cw + cw // 2
            draw_ground(d, cx - 54, cx + 54, gy_old)
            draw_ground(d, cx - 54, cx + 54, gy_new)
            paste_anchored(im, cell_crop(old_a, 2, n, ofw, ofh), oax, oay, cx, gy_old, scale=2)
            paste_anchored(im, cell_crop(new_a, 2, n, nfw, nfh), nax, nay, cx, gy_new, scale=2)
    im.save(out_path)


def save_gif(frames_rgba, durations, out_path: Path):
    p_frames = []
    for fr in frames_rgba:
        p_frames.append(fr.convert('RGB').quantize(colors=256, method=Image.MEDIANCUT))
    p_frames[0].save(
        out_path,
        save_all=True,
        append_images=p_frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )


def render_deaths_board_gif(out_path: Path):
    cols, rows = 4, 2
    cw, rh = 560, 376
    frames = []
    for n in range(8):
        im = Image.new('RGBA', (cols * cw, rows * rh + 44), (22, 28, 40, 255))
        d = ImageDraw.Draw(im)
        d.text((14, 12), f'Zone 42 - The Shattered Span Deaths (frame {n + 1}/8): left = Before, right = After', fill=(204, 242, 248, 255))
        for ki, kind in enumerate(R.KINDS):
            c, r = ki % cols, ki // cols
            x0, y0 = c * cw, 40 + r * rh
            gy = y0 + 350
            d.text((x0 + 14, y0 + 8), f'{R.NAMES[kind]} ({kind})', fill=(196, 210, 230, 255))
            draw_ground(d, x0 + 14, x0 + cw - 14, gy)
            old_a, new_a = open_atlas(BACKUP, kind), open_atlas(ROOT, kind)
            ofw, ofh, oax, oay = manifest_frame(BACKUP, kind)
            nfw, nfh, nax, nay = manifest_frame(ROOT, kind)
            paste_anchored(im, cell_crop(old_a, 4, n, ofw, ofh), oax, oay, x0 + 110, gy, scale=2)
            paste_anchored(im, cell_crop(new_a, 4, n, nfw, nfh), nax, nay, x0 + 360, gy, scale=2)
        frames.append(im)
    save_gif(frames, [140] * 7 + [420], out_path)


def render_kind_frames(kind: str, out_path: Path):
    atlas = open_atlas(ROOT, kind)
    fw, fh, ax, ay = manifest_frame(ROOT, kind)
    cw, rh = 400, 376
    im = Image.new('RGBA', (8 * cw + 110, 5 * rh + 48), (22, 28, 40, 255))
    d = ImageDraw.Draw(im)
    d.text((14, 12), f'{R.NAMES[kind]} ({kind}) - all 34 frames ({fw}x{fh}, anchor {ax},{ay})', fill=(240, 244, 250, 255))
    for row, (clip, count, _) in enumerate(CLIPS):
        gy = 44 + row * rh + 330
        d.text((14, gy - 68), f'{clip}\n({count}f)', fill=(188, 204, 224, 255))
        for n in range(count):
            cx = 110 + n * cw + cw // 2
            draw_ground(d, cx - 58, cx + 58, gy)
            paste_anchored(im, cell_crop(atlas, row, n, fw, fh), ax, ay, cx, gy, scale=2)
            d.text((cx - 14, gy + 6), f'{clip[0]}{n}', fill=(132, 148, 170, 255))
    im.save(out_path)


def render_kind_animations_gif(kind: str, out_path: Path):
    atlas = open_atlas(ROOT, kind)
    fw, fh, ax, ay = manifest_frame(ROOT, kind)
    cw = 400
    frames = []
    for tick in range(24):
        im = Image.new('RGBA', (5 * cw, 390), (22, 28, 40, 255))
        d = ImageDraw.Draw(im)
        d.text((12, 10), f'{R.NAMES[kind]} ({kind}) - idle / walk / attack / hurt / die', fill=(204, 242, 248, 255))
        for row, (clip, count, _) in enumerate(CLIPS):
            cx = row * cw + cw // 2
            gy = 366
            d.text((cx - 24, 32), clip, fill=(182, 198, 220, 255))
            draw_ground(d, cx - 64, cx + 64, gy)
            n = min(count - 1, tick // 2) if clip == 'die' else (tick % count)
            paste_anchored(im, cell_crop(atlas, row, n, fw, fh), ax, ay, cx, gy, scale=2)
        frames.append(im)
    save_gif(frames, [105] * len(frames), out_path)


def render_kind_clip_before_after_gif(kind: str, row: int, label: str, out_path: Path):
    old_a, new_a = open_atlas(BACKUP, kind), open_atlas(ROOT, kind)
    ofw, ofh, oax, oay = manifest_frame(BACKUP, kind)
    nfw, nfh, nax, nay = manifest_frame(ROOT, kind)
    frames = []
    for n in range(8):
        im = Image.new('RGBA', (560, 390), (22, 28, 40, 255))
        d = ImageDraw.Draw(im)
        d.text((12, 10), f'{R.NAMES[kind]} - {label} ({n + 1}/8)', fill=(204, 242, 248, 255))
        d.text((64, 34), 'Before', fill=(176, 192, 214, 255))
        d.text((350, 34), 'After', fill=(176, 192, 214, 255))
        gy = 366
        draw_ground(d, 24, 536, gy)
        paste_anchored(im, cell_crop(old_a, row, n, ofw, ofh), oax, oay, 110, gy, scale=2)
        paste_anchored(im, cell_crop(new_a, row, n, nfw, nfh), nax, nay, 360, gy, scale=2)
        frames.append(im)
    save_gif(frames, [120] * 7 + [360], out_path)


def review():
    OUT.mkdir(parents=True, exist_ok=True)
    render_roster_board(BACKUP, 'Zone 42 - The Shattered Span: Original Atlases (Before)', OUT / 'valhallasc-span-before.png')
    render_roster_board(ROOT, 'Zone 42 - The Shattered Span: Native PixelFlow Remake (After)', OUT / 'valhallasc-span-after.png')
    render_before_after_board(OUT / 'valhallasc-span-before-after.png')
    render_attacks_board(OUT / 'valhallasc-span-attacks-before-after.png')
    render_deaths_board_gif(OUT / 'valhallasc-span-deaths-before-after.gif')
    for k in R.KINDS:
        render_kind_frames(k, OUT / f'valhallasc-span-{k}-frames.png')
        render_kind_animations_gif(k, OUT / f'valhallasc-span-{k}-animations.gif')
        render_kind_clip_before_after_gif(k, 4, 'Death', OUT / f'valhallasc-span-{k}-death-before-after.gif')
        render_kind_clip_before_after_gif(k, 2, 'Attack', OUT / f'valhallasc-span-{k}-attack-before-after.gif')
    verify()


def verify():
    files = expected_files()
    assert len(files) == 29, len(files)
    for name in files:
        p = OUT / name
        assert p.is_file() and p.stat().st_size > 512, f'missing or tiny review file: {p}'
        with Image.open(p) as im:
            assert im.width >= 300 and im.height >= 180, (name, im.size)
            if name.endswith('.gif'):
                assert getattr(im, 'n_frames', 1) >= 8, (name, getattr(im, 'n_frames', 1))
            else:
                arr = np.array(im.convert('RGBA'))
                assert int((arr[:, :, :3].std(axis=(0, 1))).max()) > 10, f'blank image: {name}'
    print(f'Verified {len(files)} The Shattered Span review files in {OUT}')


def upload():
    verify()
    receipt = []
    put_script = ROOT / 'scripts/filedrop_put.sh'
    filedrop_dir = Path('/home/serveperry/webserver/www/filedrop/data/Sork/files')
    for name in expected_files():
        src = OUT / name
        mime = 'image/gif' if src.suffix == '.gif' else 'image/png'
        dst = filedrop_dir / name
        meta_path = Path(str(dst) + '.meta.json')
        if not dst.is_file() or not meta_path.is_file() or hashlib.sha256(dst.read_bytes()).digest() != hashlib.sha256(src.read_bytes()).digest():
            subprocess.run(['bash', str(put_script), str(src), name, mime], check=True)
        assert dst.is_file() and meta_path.is_file(), f'FileDrop missing {name}'
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        assert hashlib.sha256(dst.read_bytes()).hexdigest() == sha, f'SHA mismatch for {name}'
        meta_json = json.loads(meta_path.read_text())
        assert meta_json['original_name'] == name and meta_json['type'] == mime, (name, meta_json)
        assert meta_json['size'] == src.stat().st_size == dst.stat().st_size, name
        with Image.open(src) as s_im, Image.open(dst) as d_im:
            assert s_im.size == d_im.size, (name, s_im.size, d_im.size)
            size = list(d_im.size)
            n_frames = int(getattr(d_im, 'n_frames', 1))
        receipt.append({
            'name': name,
            'bytes': dst.stat().st_size,
            'sha256': sha,
            'dimensions': size,
            'frames': n_frames,
            'mime': mime,
            'url': f'https://gunning.se/filedrop/api.php?action=download&file={name}',
        })
    receipt_path = OUT / 'filedrop-receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'Uploaded and verified {len(receipt)} The Shattered Span review files -> {receipt_path}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'review'
    {'review': review, 'verify': verify, 'upload': upload}[cmd]()
