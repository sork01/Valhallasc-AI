#!/usr/bin/env python3
"""Export one class/body without touching equipment atlases or editor IDs.

Candidates and matching bounds go under test-results/turning-hair/assets.
--editor updates only the existing editable body layer, archiving it first.
--write installs the checked candidate PNGs and its body bounds entry.
"""
import argparse
import base64
import importlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MODULES = {c: f'make_{c}_cel_sprites' for c in ['warrior', 'mage', 'assassin', 'hunter']}
MODULES['priest'] = 'make_priest_sprites'
STEMS = {c: ('warrior_layered' if c == 'warrior' else c) for c in MODULES}


def crown(image, head):
    pixels = np.asarray(image.convert('RGBA'))
    origin = head['H'](0, 0); right = head['H'](1, 0) - origin; up = head['H'](0, 1) - origin
    mask = []
    for y in range(7, 28):
        for x in range(-17, 18):
            px, py = np.floor(origin + right * x + up * y + .5).astype(int)
            mask.append(pixels[py, px].tolist() if 0 <= px < 160 and 0 <= py < 160 else [0, 0, 0, 0])
    return mask


def measure(maker, meta, stem, candidates, before):
    import cel_common as cc
    name = meta['parts']['body']['png']; depth_name = meta['parts']['body']['depth']
    colours = {tuple(bytes.fromhex(c[1:])) for c in meta['ramps']['hair']}
    images = {key: (Image.open(folder / name).convert('RGBA'), Image.open(folder / depth_name))
              for key, folder in [('current', candidates), ('before', before)]}
    data = {'rig': stem, 'hair': meta['ramps']['hair'], 'current': [], 'before': [],
            'depthLevels': {'current': [], 'before': []}}
    for direction, facing in enumerate(cc.DIRS):
        p = {**maker.DEFAULT, **maker.CLIPS['idle'][2](0)}; _, xf, _ = cc.skeleton(p)
        psi = cc.rig.psi_for(facing); head = cc.head_frame(cc.Ink(psi, maker.COLOR), xf, psi, p)
        y = (meta['clips']['idle']['row0'] + direction) * 160
        for key, (colour, depth) in images.items():
            pixels = crown(colour.crop((0, y, 160, y + 160)), head)
            z = crown(depth.crop((0, y, 160, y + 160)), head)
            data[key].append(pixels)
            data['depthLevels'][key].append(len({d[0] * 256 + d[1] for c, d in zip(pixels, z)
                                                if c[3] and tuple(c[:3]) in colours}))
    (candidates / f'{stem}_hair-check.txt').write_text(json.dumps(data) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('character', choices=MODULES)
    ap.add_argument('--female', action='store_true')
    ap.add_argument('--editor', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--measure-only', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / 'test-results/turning-hair/assets')
    args = ap.parse_args()
    maker = importlib.import_module(MODULES[args.character])
    import cel_common as cc
    import sprite_bounds
    stem = STEMS[args.character] + ('_f' if args.female else '')
    assets = ROOT / 'client/assets'; args.out.mkdir(parents=True, exist_ok=True)
    meta_path = assets / f'{stem}_sprites.txt'; meta = json.loads(meta_path.read_text())
    names = [meta['parts']['body']['png'], meta['parts']['body']['depth'], f'{stem}_bounds.txt']
    before = args.out.parent / 'before'; before.mkdir(exist_ok=True)
    for name in names:
        if not (before / name).exists(): shutil.copyfile(assets / name, before / name)
    if args.measure_only:
        measure(maker, meta, stem, args.out, before)
        return
    previous = Image.open(before / names[0]).convert('RGBA')
    colour = Image.new('RGBA', previous.size); depth = Image.new('RGB', previous.size)
    sheet = maker.SHEET
    group = next((g for g, layers in sheet.groups.items() if 'body' in layers), None)
    pf = sheet.pixel_api() if args.editor and meta.get('sprites') and group else None
    for clip, (_, count, pose) in maker.CLIPS.items():
        for direction, facing in enumerate(cc.DIRS):
            if pf:
                editor_name = sheet.pixel_name(clip, facing, group); sid = meta['sprites'][editor_name]
                sprite, old_frames = pf.load(sid)
                layer = [part['name'] for part in sprite['layers']].index('body')
                archive = args.out.parent / 'editor-before' / (editor_name + '.txt')
                archive.parent.mkdir(exist_ok=True)
                if not archive.exists(): archive.write_text(json.dumps(sprite) + '\n')
                remap = np.array([sprite['palette'].index(c) if c in sprite['palette'] else 0 for c in sheet.palette], dtype=np.uint8)
            for k in range(count):
                if args.character == 'assassin': index, z = maker.render_body_frame(clip, facing, k)
                else: index, z = sheet.read_frame(clip, facing, k)['body']
                rgba = sheet.pal[index]; opaque = index > 0
                assert opaque.any() and not opaque[[0, -1], :].any() and not opaque[:, [0, -1]].any(), (stem, clip, facing, k, 'clipped')
                encoded = np.full(index.shape, 65535, np.uint16)
                encoded[opaque] = np.clip(np.round((z[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                rgb = np.zeros((*index.shape, 3), np.uint8); rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                position = (k * 160, (meta['clips'][clip]['row0'] + direction) * 160)
                picture = Image.fromarray(rgba); colour.paste(picture, position); depth.paste(Image.fromarray(rgb), position)
                if pf:
                    assert all(sheet.palette[i] in sprite['palette'] for i in np.unique(index)), (stem, 'missing used body colour')
                    pf.draw_grid(sid, k, layer, remap[index])
            if pf:
                updated, frames = pf.load(sid)
                assert updated['palette'] == sprite['palette'] and updated['layers'] == sprite['layers']
                for old, new in zip(old_frames, frames):
                    assert all(np.array_equal(a, b) for i, (a, b) in enumerate(zip(old, new)) if i != layer)
        print(stem, clip, flush=True)
    colour.save(args.out / names[0], optimize=True); depth.save(args.out / names[1], optimize=True)
    bounds = json.loads((assets / names[2]).read_text())
    bounds['parts']['body'] = base64.b64encode(sprite_bounds.part_bounds(args.out / names[0], meta)).decode()
    (args.out / names[2]).write_text(json.dumps(bounds, separators=(',', ':')) + '\n')
    measure(maker, meta, stem, args.out, before)
    if args.write:
        for name in names: shutil.copyfile(args.out / name, assets / name)


if __name__ == '__main__': main()
