"""Build one redesigned equipment piece at a time, preserving original atlases and editor edits.

preview JOB renders both bodies/all poses and an inspected contact sheet. build JOB saves new PixelFlow sprites
and exports them back; export JOB preserves later editor changes. wire JOB maps the existing catalog entries to
the new layers/icons. Then inspect the real browser and finish the individual task with gear_art_status.py.
Raw caches are local; source, job state, final atlases and PixelFlow IDs are reusable for handoff.
"""
import argparse
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
import time
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import cel_common as cc
import gear_shapes as shape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
RAW = ROOT / 'scripts/progression_raw'
STATE = ROOT / 'docs/gear-redesign-state.txt'
MANIFEST = ROOT / 'world/gear-art.txt'
CLASSES = tuple(shape.MODULES)
DIRS = cc.DIRS
META = dict(warrior='warrior_layered', assassin='assassin', mage='mage', priest='priest', hunter='hunter')
SLOT = {'headgear': 'head'}
PALETTE = np.array([[int(h[k:k + 2], 16) for k in (1, 3, 5)] + [255 if n else 0] for n, h in enumerate(shape.PALETTE)], np.uint8)
BODY_CACHE = {}


def revision(task):
    # A change to hats must not invalidate a completed armor piece or its editor edits.
    dependencies = [shape.render, shape.pose, shape.poly, shape.jewel, getattr(shape, task['kind'])]
    source = ''.join(inspect.getsource(fn) for fn in dependencies) + Path(cc.__file__).read_text()
    source += json.dumps([shape.MATS, shape.DESIGNS[task['group']]], sort_keys=True)
    return hashlib.sha256(source.encode()).hexdigest()


def task_for(job):
    return next(t for t in json.loads(STATE.read_text())['tasks'] if t['id'] == job)


def frames(task, cls, gender):
    directory = RAW / task['id'] / f'{cls}-{gender}'
    directory.mkdir(parents=True, exist_ok=True)
    module = importlib.import_module(shape.MODULES[cls])
    result = {}
    fingerprint = revision(task)
    for clip, (_, n, _) in module.CLIPS.items():
        for facing in DIRS:
            for k in range(n):
                key = (clip, facing, k); file = directory / f'{clip}-{facing}-{k}.npz'
                if file.exists():
                    with np.load(file) as data:
                        if str(data['revision']) == fingerprint:
                            result[key] = (data['index'], data['depth']); continue
                idx, depth = shape.render(cls, task['group'], task['kind'], gender, *key)
                assert idx.any(), f'Blank {task["id"]}/{cls}/{gender}/{key}'
                assert not np.any(idx[[0, -1], :]) and not np.any(idx[:, [0, -1]]), f'Clipped {task["id"]}/{cls}/{gender}/{key}'
                np.savez_compressed(file, revision=fingerprint, index=idx, depth=depth)
                result[key] = idx, depth
    return result


def body(cls, gender, key):
    cache_key = cls, gender
    if cache_key not in BODY_CACHE:
        prefix = META[cls] + ('_f' if gender == 'female' else '')
        meta = json.loads((ASSETS / f'{prefix}_sprites.txt').read_text())
        part = meta['parts']['body']
        BODY_CACHE[cache_key] = (meta, np.array(Image.open(ASSETS / part['png']).convert('RGBA')),
                                np.array(Image.open(ASSETS / part['depth']).convert('RGB')))
    meta, rgba, encoded = BODY_CACHE[cache_key]
    clip, facing, k = key; w, h = meta['frame']; x = k * w; y = (meta['clips'][clip]['row0'] + DIRS.index(facing)) * h
    colour, dep = rgba[y:y + h, x:x + w], encoded[y:y + h, x:x + w].astype(np.int32)
    z = (dep[..., 0] * 256 + dep[..., 1]) / 64 - 512
    return colour.copy(), z


def composite(cls, gender, key, frame):
    rgba, z = body(cls, gender, key); idx, depth = frame
    take = (idx > 0) & ((rgba[..., 3] == 0) | (depth < z))
    rgba[take] = PALETTE[idx[take]]
    return Image.fromarray(rgba)


def icon_from(task, frame):
    rgba = Image.fromarray(PALETTE[frame[0]])
    box = rgba.getbbox(); rgba = rgba.crop(box)
    rgba.thumbnail((40, 40), Image.Resampling.NEAREST)
    icon = Image.new('RGBA', (48, 48)); icon.alpha_composite(rgba, ((48 - rgba.width) // 2, (48 - rgba.height) // 2))
    return icon


def preview(task):
    classes = [task['className']] if task['className'] else list(CLASSES)
    selections = [('idle', 'S', 0), ('idle', 'SE', 0), ('idle', 'N', 0), ('attack', 'S', 4), ('attack', 'SE', 4), ('die', 'S', 7)]
    path = ROOT / 'test-results/gear-redesign' / (task['id'] + '.png'); path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGBA', (6 * 320, len(classes) * 2 * 340 + 100), '#263d48'); draw = ImageDraw.Draw(image)
    draw.text((18, 15), f'{task["id"]}: {task["name"]} | new equipment only on the original body', fill='white')
    for n, cls in enumerate(classes):
        for row, gender in enumerate(('male', 'female')):
            all_frames = frames(task, cls, gender)
            for col, key in enumerate(selections):
                rgba = composite(cls, gender, key, all_frames[key]).resize((320, 320), Image.Resampling.NEAREST)
                x, y = col * 320, (n * 2 + row) * 340 + 50
                image.alpha_composite(rgba, (x, y)); draw.text((x + 8, y + 318), f'{cls} {gender}: {"/".join(map(str, key))}', fill='white')
            if n == row == 0:
                icon = icon_from(task, all_frames[('idle', 'S', 0)])
                icon.save(path.with_name(task['id'] + '-icon.png'))
    image.save(path)
    print(path, flush=True)
    return path


def api(route, payload=None, method='POST'):
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    for attempt in range(30):
        result = pf.api(route, payload, method)
        if not any(e.get('code') == 'rate_limited' for e in result.get('errors', [])):
            assert result.get('ok'), result
            return result
        time.sleep(5)
    raise RuntimeError('PixelFlow rate limit did not clear')


def rle(idx):
    flat = idx.ravel(); starts = np.r_[0, np.flatnonzero(flat[1:] != flat[:-1]) + 1]; lengths = np.diff(np.r_[starts, len(flat)])
    return np.column_stack((lengths, flat[starts])).ravel().astype(int).tolist()


def save_sprite(name, indices, fps):
    stack = np.stack(indices); yy, xx = np.nonzero(stack.any(axis=0)); x0, x1, y0, y1 = int(xx.min()), int(xx.max()) + 1, int(yy.min()), int(yy.max()) + 1
    w, h = x1 - x0, y1 - y0
    assert w * h * len(indices) <= 1048576, (name, w, h, len(indices))
    sprite = dict(name=name, width=w, height=h, fps=fps, palette=shape.PALETTE, palette_locked=True,
                  layers=[dict(name='equipment', visible=True, opacity=1)],
                  frames=[dict(cels=[dict(rle=rle(idx[y0:y1, x0:x1]))]) for idx in indices])
    result = api('save', dict(sprite=sprite))
    return dict(id=result['sprite_id'], offset=[x0, y0], frameCount=len(indices))


def load_sprite(record):
    sys.path.insert(0, str(Path.home() / '.claude/skills/makesprites'))
    import pf
    result = api('get?sprite_id=' + record['id'], method='GET'); sprite = result['sprite']
    frames_ = []
    for f in sprite['frames']:
        cel = f['cels'][0]
        flat = np.concatenate([np.full(n, v, np.uint8) for n, v in zip(cel['rle'][::2], cel['rle'][1::2])]) if 'rle' in cel else np.array(cel['grid'], np.uint8).ravel()
        frames_.append(flat.reshape(sprite['height'], sprite['width']))
    return sprite, frames_


def build(task):
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if task['id'] in manifest:
        assert not manifest[task['id']].get('files'), 'Existing completed sprites: use export to preserve editor changes'
        assert manifest[task['id']]['revision'] == revision(task), 'Source changed during partial build; review before resuming'
    preview(task)
    classes = [task['className']] if task['className'] else list(CLASSES)
    record = manifest.get(task['id']) or dict(variant=shape.variant(task['group']), kind=task['kind'], classes={}, revision=revision(task))
    # Persist each sprite immediately so interruption never loses its editable ID.
    manifest[task['id']] = record
    def remember(): MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    remember()
    for cls in classes:
        module = importlib.import_module(shape.MODULES[cls]); raw = frames(task, cls, 'male'); clips = record['classes'].setdefault(cls, {})
        for clip, (fps, n, _) in module.CLIPS.items():
            indices = [raw[(clip, facing, k)][0] for facing in DIRS for k in range(n)]
            # Most pieces fit all facings in one cropped sprite. Split large weapons only when necessary.
            mask = np.stack(indices).any(axis=0); yy, xx = np.nonzero(mask)
            chunks = 2 if (xx.max() - xx.min() + 1) * (yy.max() - yy.min() + 1) * len(indices) > 1048576 else 1
            saved_chunks = clips.setdefault(clip, [])
            assert len(saved_chunks) <= chunks
            for chunk in range(chunks):
                if chunk < len(saved_chunks): continue
                lo, hi = len(indices) * chunk // chunks, len(indices) * (chunk + 1) // chunks
                saved = save_sprite(f'gear_{task["group"].lower()}_{cls}_{task["kind"]}_{clip}_{chunk}', indices[lo:hi], fps)
                saved['start'] = lo; clips[clip].append(saved); remember()
            print(f'{task["id"]}: {cls}/{clip} saved', flush=True)
    icon = np.array(Image.open(ROOT / 'test-results/gear-redesign' / (task['id'] + '-icon.png')).convert('RGBA'))
    packed = np.sum(icon[..., :3].astype(np.int32) * [65536, 256, 1], axis=2)
    palette_rgb = np.sum(PALETTE[:, :3].astype(np.int32) * [65536, 256, 1], axis=1)
    idx = np.zeros((48, 48), np.uint8)
    for n, color in enumerate(palette_rgb[1:], 1): idx[(packed == color) & (icon[..., 3] > 0)] = n
    if 'icon' not in record:
        record['icon'] = save_sprite('gear_' + task['id'].lower() + '_icon', [idx], 1)
    remember(); export(task)


def export(task):
    manifest = json.loads(MANIFEST.read_text()); record = manifest[task['id']]
    assert record['revision'] == revision(task), 'Source changed after build: preserve editor edits and review before rebuilding'
    files = []
    for cls, clips in record['classes'].items():
        module = importlib.import_module(shape.MODULES[cls])
        for gender in ('male', 'female'):
            raw = frames(task, cls, gender); atlas = Image.new('RGBA', (1280, 6400)); depth_atlas = Image.new('RGB', (1280, 6400), (255, 255, 0))
            for ci, (clip, (_, n, _)) in enumerate(module.CLIPS.items()):
                edited = {}
                if gender == 'male':
                    for saved in clips[clip]:
                        sprite, grids = load_sprite(saved)
                        for j, idx in enumerate(grids):
                            edited[saved['start'] + j] = (saved['offset'], np.array(Image.fromarray(PALETTE[idx])))
                            assert sprite['palette'] == shape.PALETTE, 'Changed editor palette requires an explicit remap'
                for di, facing in enumerate(DIRS):
                    for k in range(n):
                        idx, dep = raw[(clip, facing, k)]; rgba = PALETTE[idx].copy(); dep = dep.copy()
                        if gender == 'male':
                            (x0, y0), patch = edited[di * n + k]; h, w = patch.shape[:2]
                            rgba.fill(0); rgba[y0:y0 + h, x0:x0 + w] = patch
                            added = (rgba[..., 3] > 0) & ~np.isfinite(dep)
                            if added.any():
                                nearest = ndi.distance_transform_edt(~np.isfinite(dep), return_distances=False, return_indices=True)
                                dep[added] = dep[tuple(nearest)][added]
                        opaque = rgba[..., 3] > 0; encoded = np.full((160, 160), 65535, np.uint16)
                        encoded[opaque] = np.clip(np.round((dep[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                        rgb = np.zeros((160, 160, 3), np.uint8); rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                        location = (k * 160, (ci * 8 + di) * 160)
                        atlas.paste(Image.fromarray(rgba), location); depth_atlas.paste(Image.fromarray(rgb), location)
            part = SLOT.get(task['kind'], task['kind']) + '_' + record['variant']
            prefix = f'{cls}_{"f_" if gender == "female" else ""}progression_{part}'
            for suffix, picture in [('', atlas), ('_depth', depth_atlas)]:
                file = ASSETS / (prefix + suffix + '.png'); picture.save(file, optimize=True); files.append(str(file.relative_to(ROOT)))
            meta_path = ASSETS / (META[cls] + ('_f' if gender == 'female' else '') + '_sprites.txt')
            meta = json.loads(meta_path.read_text()); meta['parts'][part] = dict(png=prefix + '.png', depth=prefix + '_depth.png')
            meta['lazyParts'] = sorted(set(meta.get('lazyParts', [])) | {part})
            meta.setdefault('gearSprites', {})[part] = clips if gender == 'male' else {'local': 'scripts/make_progression_gear.py export ' + task['id']}
            meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    sprite, grids = load_sprite(record['icon']); (x0, y0) = record['icon']['offset']; icon = Image.new('RGBA', (48, 48))
    icon.paste(Image.fromarray(PALETTE[grids[0]]), (x0, y0))
    icon_path = ASSETS / ('gear_icon_' + task['id'].lower() + '.png'); icon.save(icon_path); files.append(str(icon_path.relative_to(ROOT)))
    record['files'] = files; MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{task["id"]}: exported {len(files)} worn/depth/icon files', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['preview', 'build', 'export', 'wire'])
    p.add_argument('job', nargs='+')
    p.add_argument('--finish', action='store_true', help='After each reviewed piece, wire, verify in Chromium, and check off that piece immediately')
    p.add_argument('--reviewed', help='Record what was visually inspected in every supplied preview; required with --finish')
    p.add_argument('--redo', action='store_true', help='Rebuild a completed piece after an explicit visual redesign request; old editor IDs remain in the manifest history only')
    args = p.parse_args()
    if args.finish:
        assert args.command == 'build' and args.reviewed, '--finish requires build and an explicit --reviewed note'
    node = '/home/serveperry/.nvm/versions/node/v20.20.2/bin/node'
    for job in args.job:
        task = task_for(job)
        if args.redo:
            assert args.command == 'build', '--redo is only valid with build'
            manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
            if job in manifest:
                del manifest[job]
                MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
            subprocess.run([sys.executable, 'scripts/gear_art_status.py', 'reopen', job, '--phase', 'redesign build',
                            '--note', 'Explicit redesign requested; prior art is superseded and this piece will be visually rechecked.'], cwd=ROOT, check=True)
            task = task_for(job)
        if args.finish and task['done']:
            print(job + ': already checked off; preserving exported/editor art', flush=True)
            continue
        if args.finish:
            subprocess.run([sys.executable, 'scripts/gear_art_status.py', 'update', job, '--phase', 'build and verification',
                            '--note', args.reviewed + '; next: save/export, wire, browser check, immediate checklist update.'], cwd=ROOT, check=True)
        if args.command == 'wire':
            assert json.loads(MANIFEST.read_text())[task['id']].get('files'), 'Export worn art and icon first'
            import gear_art_catalog
            gear_art_catalog.wire()
            print(task['id'] + ': catalog and inventory icons wired; run sync-world next')
        elif args.finish and json.loads(MANIFEST.read_text()).get(job, {}).get('files'):
            # Resume after an interruption between export and completion without rebuilding editable sprites.
            assert json.loads(MANIFEST.read_text())[job]['revision'] == revision(task), 'Review a source change before resuming an exported piece'
        else:
            {'preview': preview, 'build': build, 'export': export}[args.command](task)
        if args.finish:
            import gear_art_catalog
            gear_art_catalog.wire()
            subprocess.run([node, 'scripts/sync-world.cjs'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([node, 'tests/gear-piece-art.cjs', job], cwd=ROOT, check=True)
            record = json.loads(MANIFEST.read_text())[job]
            evidence = ['scripts/gear_shapes.py', 'world/gear-art.txt', *record['files'],
                        'test-results/gear-redesign/' + job + '.png', 'test-results/gear-redesign/' + job + '-browser.json']
            subprocess.run([sys.executable, 'scripts/gear_art_status.py', 'finish', job, '--evidence', *evidence,
                            '--note', args.reviewed + '; all frames clear on both bodies, PixelFlow round-trip, matching icon and real-client checks passed.'], cwd=ROOT, check=True)


if __name__ == '__main__': main()
