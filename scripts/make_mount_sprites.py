"""Mount sprites: preview | build [--replace] | export [--local] (docs/mounts.md, TODO MOUNT-*).

Five mounts (horse, raptor, lizard, sabertooth, gryphon), eight facings, two clips (idle, run), drawn with the 3D toon
renderer in mount_toon.py from the models in mount_models.py. The mount is a separate layer under and over the rider: the
client composites the rider's class frame into the mount's frame pixel by pixel on depth (client/mountart.js), so one
sheet serves every class and both bodies. Frames are 160x160 with the class anchor (80,119) and the class depth encoding.

  preview [mount ...] [--out DIR]   contact sheets (8 facings x frames) on a green ground, 2x, plus a rider test sheet
  build [mount ...] [--replace]     (re)creates the PixelFlow sprites mount_<id>_<clip>_<facing>; --replace discards editor edits
  sheet [mount ...] [--out DIR]     one sprite sheet PNG per mount for FileDrop: every facing and frame of both clips, then the five
                                    classes riding it (3840 px wide); scripts/filedrop_put.sh uploads it
  export [mount ...] [--local]      reads the sprites back from PixelFlow (edits survive) and writes assets/mount_<id>.png,
                                    mount_<id>_depth.png and assets/mounts_sprites.txt; --local skips PixelFlow
Frames are cached in scripts/mount_raw/ and rebuilt when a model or the renderer changes.
"""
import argparse
import hashlib
import json
import math
import os
from multiprocessing import Pool
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

import functools

import mount_models as models
import mount_toon as toon

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client' / 'assets'
CACHE = Path(__file__).resolve().parent / 'mount_raw'
FW, FH, AX, AY = toon.FW, toon.FH, toon.AX, toon.AY
CLIPS = {'idle': (4, 4), 'run': (11, 8)}            # name -> (fps, frames)
MOUNTS = {}


def register():
    for name, (builder, mats, flat, seat) in models.REGISTRY.items():
        MOUNTS[name] = dict(builder=builder, look=toon.Look(mats, flat), **seat)


def revision(name):
    h = hashlib.sha256()
    for path in ('mount_toon.py', 'mount_models.py'):
        h.update((Path(__file__).resolve().parent / path).read_bytes())
    h.update(name.encode())
    return h.hexdigest()


def frame_job(args):
    name, clip, facing, k = args
    mount = MOUNTS[name]
    prims, bob = mount['builder'](clip, k, CLIPS[clip][1])
    scale = mount['scale']
    for p in prims:             # models are drawn in the class's units; `scale` makes the mount big enough for its rider
        p.c, p.r = p.c * scale, p.r * scale
        if p.cam is not None:
            p.cam = tuple(v * scale for v in p.cam)
    bob *= scale
    idx, depth = toon.render(prims, toon.psi_for(facing), mount['look'])
    return name, clip, facing, k, idx, depth, bob


def frames_of(name, jobs=None):
    """{(clip, facing, k): (index, depth)} and {clip: [bob...]}, from the cache or rendered with all cores."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f'{name}.npz'
    rev = revision(name)
    if path.exists():
        with np.load(path, allow_pickle=True) as saved:
            if str(saved['revision']) == rev:
                return saved['frames'].item(), saved['bob'].item()
    todo = [(name, clip, facing, k) for clip, (_, n) in CLIPS.items() for facing in toon.DIRS for k in range(n)]
    started = time.time()
    with Pool(jobs or os.cpu_count()) as pool:
        done = pool.map(frame_job, todo, chunksize=2)
    frames = {(clip, facing, k): (idx, depth) for _, clip, facing, k, idx, depth, _ in done}
    bob = {clip: [next(b for (_, c, f, kk, _, _, b) in done if c == clip and f == 'S' and kk == k) for k in range(n)] for clip, (_, n) in CLIPS.items()}
    for key, (idx, _) in frames.items():
        if idx[0].any() or idx[-1].any() or idx[:, 0].any() or idx[:, -1].any():
            raise SystemExit(f'{name} {key}: a part touches the frame border')
    np.savez_compressed(path, revision=rev, frames=np.array(frames, dtype=object), bob=np.array(bob, dtype=object))
    print(f'{name}: rendered {len(todo)} frames in {time.time() - started:.0f}s', flush=True)
    return frames, bob


def contact(name, out, scale=2):
    mount = MOUNTS[name]
    frames, _ = frames_of(name)
    table = mount['look'].rgba_table()
    for clip, (_, n) in CLIPS.items():
        sheet = Image.new('RGBA', (FW * n, FH * 8), (72, 112, 72, 255))
        for di, facing in enumerate(toon.DIRS):
            for k in range(n):
                idx, _ = frames[(clip, facing, k)]
                sheet.alpha_composite(Image.fromarray(table[idx], 'RGBA'), (k * FW, di * FH))
                ImageDraw.Draw(sheet).text((k * FW + 3, di * FH + 3), f'{facing} {k}', fill='white')
        sheet.resize((sheet.width * scale, sheet.height * scale), Image.Resampling.NEAREST).save(out / f'mount_{name}_{clip}.png')


# ----------------------------------------------------------------------------- riders (previews only; the client does the same sum)
RIDER_CLASSES = ['warrior_layered', 'mage_f', 'assassin', 'priest_f', 'hunter']
COMPOSITE_H, SHIFT = 224, 64          # the composite canvas is 64 px taller than a class frame (anchor row 119 + 64)


@functools.lru_cache(maxsize=None)
def atlas_of(path):
    return np.asarray(Image.open(ASSETS / path).convert('RGBA')), np.asarray(Image.open(ASSETS / path.replace('.png', '_depth.png')).convert('RGB')).astype(np.int32)


def rider_layers(cls, di, clip='idle', i=0):
    """The rider's worn parts at one pose, nearest depth winning -> (rgba, depth) in class frame coordinates."""
    meta = json.loads((ASSETS / f'{cls}_sprites.txt').read_text())
    row = (meta['clips'][clip]['row0'] + di) * FH
    out = np.zeros((FH, FW, 4), np.uint8)
    best = np.full((FH, FW), np.inf)
    parts = ['body'] + [f'{slot}_{v}' for slot, v in meta['defaultEquipment'].items() if v != 'none']
    for part in parts:
        info = meta['parts'].get(part)
        if not info:
            continue
        colour, enc = atlas_of(info['png'])
        colour, enc = colour[row:row + FH, i * FW:(i + 1) * FW], enc[row:row + FH, i * FW:(i + 1) * FW]
        depth = (enc[..., 0] * 256 + enc[..., 1]) / 64 - 512
        take = (colour[..., 3] > 0) & (depth <= best)
        out[take], best[take] = colour[take], depth[take]
    return out, best


def mounted(name, clip, facing, k, cls, rider_clip='idle', rider_i=0):
    """The rider sitting in the mount: depth-composited onto the mount's frame (client/mountart.js does the same)."""
    mount = MOUNTS[name]
    frames, bob = frames_of(name)
    idx, depth = frames[(clip, facing, k)]
    table = mount['look'].rgba_table()
    canvas = np.zeros((COMPOSITE_H, FW, 4), np.uint8)
    zbuf = np.full((COMPOSITE_H, FW), np.inf)
    opaque = idx > 0
    canvas[SHIFT:, :][opaque] = table[idx][opaque]
    zbuf[SHIFT:, :][opaque] = depth[opaque]
    rgba, rdepth = rider_layers(cls, toon.DIRS.index(facing), rider_clip, rider_i)
    raise_by = mount['raise'] + bob[clip][k]
    shift = int(round(raise_by * toon.COSE * toon.PX))
    rows, cols = np.nonzero(rgba[..., 3] > 0)
    d = rdepth[rows, cols] - .5 * raise_by
    a = (AY - rows) / toon.PX
    z_world = toon.COSE * a - .5 * (rdepth[rows, cols]) + raise_by
    keep = z_world >= mount['cut']
    for r, c, dd, ok in zip(rows, cols, d, keep):
        if not ok:
            continue
        y = r + SHIFT - shift
        if 0 <= y < COMPOSITE_H and dd <= zbuf[y, c]:
            canvas[y, c], zbuf[y, c] = rgba[r, c], dd
    return Image.fromarray(canvas, 'RGBA')


def rider_sheet(name, out, scale=2):
    """Every class sitting on the mount, running, in all eight facings (frame 2 of the run)."""
    mount = MOUNTS[name]
    sheet = Image.new('RGBA', (FW * 8 * 1, COMPOSITE_H * len(RIDER_CLASSES)), (72, 112, 72, 255))
    for ci, cls in enumerate(RIDER_CLASSES):
        for di, facing in enumerate(toon.DIRS):
            sheet.alpha_composite(mounted(name, 'run', facing, 2, cls), (di * FW, ci * COMPOSITE_H))
    sheet.resize((sheet.width * scale // 2 * 1, sheet.height * scale // 2 * 1), Image.Resampling.NEAREST).save(out / f'mount_{name}_riders.png')


def preview(names, out, riders=True):
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        contact(name, out)
        if riders:
            rider_sheet(name, out)
        print('preview', name, out, flush=True)


def font(size):
    from PIL import ImageFont
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLES = {'horse': 'Riding horse', 'raptor': 'Raptor', 'lizard': 'Lizard', 'sabertooth': 'Sabertooth', 'gryphon': 'Gryphon'}


def sheet(names, out):
    """The whole mount on one page: eight facings x (4 idle + 8 run) frames at 2x, then every class riding it."""
    out.mkdir(parents=True, exist_ok=True)
    scale, label = 2, 120
    columns = sum(n for _, n in CLIPS.values())
    for name in names:
        frames, _ = frames_of(name)
        table = MOUNTS[name]['look'].rgba_table()
        width = label + FW * columns * scale
        riders = len(RIDER_CLASSES)
        height = 90 + FH * 8 * scale + 70 + COMPOSITE_H * riders * scale
        page = Image.new('RGBA', (width, height), (72, 112, 72, 255))
        draw = ImageDraw.Draw(page)
        draw.text((24, 20), f'{TITLES[name]} mount: eight facings, idle (4 frames) and run (8 frames), 160x160 px at 2x', fill='white', font=font(36))
        x0 = label
        for clip, (fps, n) in CLIPS.items():
            draw.text((x0 + 8, 62), f'{clip} ({fps} fps)', fill=(255, 240, 160, 255), font=font(22))
            for di, facing in enumerate(toon.DIRS):
                if clip == 'idle':
                    draw.text((24, 90 + di * FH * scale + 20), facing, fill='white', font=font(30))
                for k in range(n):
                    tile = Image.fromarray(table[frames[(clip, facing, k)][0]], 'RGBA').resize((FW * scale, FH * scale), Image.Resampling.NEAREST)
                    page.alpha_composite(tile, (x0 + k * FW * scale, 90 + di * FH * scale))
            x0 += FW * n * scale
        top = 90 + FH * 8 * scale
        draw.text((24, top + 14), f'{TITLES[name]} with a rider of each class (run, frame 2): warrior, mage, assassin, priest, hunter', fill='white', font=font(30))
        for ci, cls in enumerate(RIDER_CLASSES):
            for di, facing in enumerate(toon.DIRS):
                tile = mounted(name, 'run', facing, 2, cls).resize((FW * scale, COMPOSITE_H * scale), Image.Resampling.NEAREST)
                page.alpha_composite(tile, (label + di * FW * scale, top + 70 + ci * COMPOSITE_H * scale))
        path = out / f'Mount {TITLES[name]} sprite sheet.png'
        page.convert('RGB').save(path, optimize=True)
        print('sheet', path, path.stat().st_size // 1024, 'KB', flush=True)


# ----------------------------------------------------------------------------- PixelFlow
def pixel_api():
    sys.path.insert(0, os.path.expanduser('~/.claude/skills/makesprites'))
    import pf
    original = pf.api

    def retry(*args, **kwargs):
        for _ in range(25):
            result = original(*args, **kwargs)
            if not any(e.get('code') == 'rate_limited' for e in result.get('errors', [])):
                return result
            time.sleep(5)
        raise RuntimeError('PixelFlow request limit did not clear')
    pf.api = retry
    return pf


def sprite_name(name, clip, facing):
    return f'mount_{name}_{clip}_{facing.lower()}'


def editor_ids(pf):
    manifest = CACHE / 'editor_ids.txt'
    ids = json.loads(manifest.read_text()) if manifest.exists() else {}
    ids.update(pf.ids('mount_'))
    return ids


def build(names, replace):
    pf = pixel_api()
    everything = editor_ids(pf)
    for name in names:
        existing = {n: sid for n, sid in everything.items() if n.startswith(f'mount_{name}_')}
        if existing and not replace:
            raise SystemExit(f'{name} sprites already exist; use export to keep edits, or build --replace to discard them.')
        for sid in existing.values():
            response = pf.api('delete', {'sprite_id': sid})
            assert response.get('ok') or any(e.get('code') == 'not_found' for e in response.get('errors', [])), response
        frames, _ = frames_of(name)
        palette = MOUNTS[name]['look'].palette
        created, ids = [], {}
        try:
            for clip, (fps, n) in CLIPS.items():
                for facing in toon.DIRS:
                    assert FW * FH * n <= 1048576
                    sprite = sprite_name(name, clip, facing)
                    sid = pf.create(sprite, FW, FH, n, palette, fps=fps)
                    created.append(sid)
                    ids[sprite] = sid
                    for k in range(n):
                        result = pf.api('draw', {'sprite_id': sid, 'frame': k, 'ops': [
                            {'op': 'grid', 'rows': frames[(clip, facing, k)][0].astype(int).tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
                        assert result.get('ok'), result
                        time.sleep(.1)
                    print(sprite, sid, flush=True)
        except BaseException:
            for sid in created:
                pf.api('delete', {'sprite_id': sid})
            raise
        everything = {n: sid for n, sid in everything.items() if n not in existing}
        everything.update(ids)
        CACHE.mkdir(exist_ok=True)
        (CACHE / 'editor_ids.txt').write_text(json.dumps(everything, indent=2) + '\n')


def export(names, local):
    from scipy import ndimage as ndi
    pf = None if local else pixel_api()
    ids = {} if local else editor_ids(pf)
    meta_path = ASSETS / 'mounts_sprites.txt'
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({'frame': [FW, FH], 'anchor': [AX, AY], 'dirs': toon.DIRS,
                 'depth': {'encoding': 'R*256+G', 'offset': 512, 'scale': 64, 'near': 'smaller'},
                 'facing': 'Same eight-direction formula and foot anchor as the class atlases; row = clip.row0 + facing, frame x = i * 160',
                 'style': 'Cel-shaded chibi mounts, 3D toon rendered (scripts/mount_toon.py) and edited in PixelFlow',
                 'editing': 'One PixelFlow sprite per mount, clip and facing (mount_<id>_<clip>_<facing>). build --replace discards edits.'})
    meta.setdefault('mounts', {})
    for name in names:
        mount = MOUNTS[name]
        frames, bob = frames_of(name)
        rows = len(CLIPS) * 8
        atlas = Image.new('RGBA', (FW * 8, FH * rows))
        depths = Image.new('RGB', (FW * 8, FH * rows), (255, 255, 0))
        clips, row0 = {}, 0
        for clip, (fps, n) in CLIPS.items():
            clips[clip] = {'row0': row0, 'n': n, 'fps': fps}
            for di, facing in enumerate(toon.DIRS):
                edited = None
                if not local:
                    sp, grids = pf.load(ids[sprite_name(name, clip, facing)])
                    assert (sp['width'], sp['height']) == (FW, FH) and len(grids) == n
                    edited = (sp['palette'], [g[0] for g in grids])
                for k in range(n):
                    idx, depth = frames[(clip, facing, k)]
                    depth = depth.copy()
                    if edited:
                        palette, grid = edited[0], edited[1][k]
                        picture = Image.fromarray(pf.to_rgba(grid, palette), 'RGBA')
                        added = (grid > 0) & ~np.isfinite(depth)
                        if added.any():
                            nearest = ndi.distance_transform_edt(~np.isfinite(depth), return_distances=False, return_indices=True)
                            depth[added] = depth[tuple(nearest)][added]
                        idx = grid
                    else:
                        picture = Image.fromarray(mount['look'].rgba_table()[idx], 'RGBA')
                    opaque = idx > 0
                    encoded = np.full((FH, FW), 65535, np.uint16)
                    encoded[opaque] = np.clip(np.round((depth[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                    rgb = np.zeros((FH, FW, 3), np.uint8)
                    rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                    atlas.paste(picture, (k * FW, (row0 + di) * FH))
                    depths.paste(Image.fromarray(rgb, 'RGB'), (k * FW, (row0 + di) * FH))
            row0 += 8
            print('export', name, clip, flush=True)
        atlas.save(ASSETS / f'mount_{name}.png', optimize=True)
        depths.save(ASSETS / f'mount_{name}_depth.png', optimize=True)
        look = mount['look']
        meta['mounts'][name] = {'png': f'mount_{name}.png', 'depth': f'mount_{name}_depth.png', 'clips': clips,
                                'bob': {c: [round(float(b), 3) for b in v] for c, v in bob.items()},
                                'raise': mount['raise'], 'cut': mount['cut'], 'shadow': list(mount['shadow']),
                                'coat': look.mats[mount['coat']], 'ramps': look.mats,
                                'sprites': {n: sid for n, sid in ids.items() if n.startswith(f'mount_{name}_')}}
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    print('exported', ', '.join(names), flush=True)


def main():
    register()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['preview', 'sheet', 'build', 'export'])
    ap.add_argument('mounts', nargs='*')
    ap.add_argument('--out', default=os.path.join(os.environ.get('TMPDIR', '/tmp'), 'valhalla-mount-preview'))
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--local', action='store_true')
    ap.add_argument('--no-riders', action='store_true')
    args = ap.parse_args()
    names = args.mounts or list(MOUNTS)
    unknown = [n for n in names if n not in MOUNTS]
    if unknown:
        raise SystemExit(f'unknown mounts {unknown}; the mounts are {list(MOUNTS)}')
    if args.command == 'preview':
        preview(names, Path(args.out), not args.no_riders)
    elif args.command == 'sheet':
        sheet(names, Path(args.out))
    elif args.command == 'build':
        build(names, args.replace)
    else:
        export(names, args.local)


if __name__ == '__main__':
    main()
