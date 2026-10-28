#!/usr/bin/env python3
"""Export only the chosen Priest part, preserving every other atlas and editor ID.

Run once per body, with --female for the female rig. Previews go to --out;
--write installs the two atlases and refreshes only their bounds entry.
--editor updates just the chosen layer in the existing Pilgrim editor sprites.
"""
import argparse
import base64
import json
from pathlib import Path

import numpy as np
from PIL import Image

import make_priest_sprites as priest
import sprite_bounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--female', action='store_true')
    parser.add_argument('--out', type=Path, default=priest.ROOT / 'test-results/priest-hood')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--editor', action='store_true')
    parser.add_argument('--part', choices=['head_pilgrim', 'body'], default='head_pilgrim')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sheet = priest.SHEET
    name = args.part
    colour = Image.new('RGBA', (priest.FW * 8, priest.FH * 40))
    depth = Image.new('RGB', colour.size)
    pf = sheet.pixel_api() if args.editor else None
    meta_path = priest.ASSETS / f'{sheet.files}_sprites.txt'
    meta = json.loads(meta_path.read_text())
    if pf:
        expected = [sheet.pixel_name(clip, facing, 'pilgrim') for clip in sheet.clips for facing in priest.DIRS]
        if any(name not in meta['sprites'] for name in expected):
            parser.error('This rig has no saved Pilgrim editor IDs; omit --editor to export its generated part.')
    for clip, (_, count, _) in sheet.clips.items():
        for direction, facing in enumerate(priest.DIRS):
            if pf:
                editor_name = sheet.pixel_name(clip, facing, 'pilgrim')
                sid = meta['sprites'][editor_name]
                sprite, old_frames = pf.load(sid)
                layer = [part['name'] for part in sprite['layers']].index(name)
                archive = args.out / 'editor-before' / (editor_name + '.txt')
                archive.parent.mkdir(exist_ok=True)
                if not archive.exists():
                    archive.write_text(json.dumps(sprite) + '\n')
                # Map palette indices without changing any editor palette or other layer.
                remap = np.array([sprite['palette'].index(c) for c in sheet.palette], dtype=np.uint8)
            for k in range(count):
                index, z = sheet.read_frame(clip, facing, k)[name]
                rgba = sheet.pal[index]
                opaque = index > 0
                assert opaque.any() and not any(opaque[edge].any() for edge in [0, -1])
                assert not opaque[:, 0].any() and not opaque[:, -1].any()
                encoded = np.full(index.shape, 65535, np.uint16)
                encoded[opaque] = np.clip(np.round((z[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                rgb = np.zeros((*index.shape, 3), np.uint8)
                rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                position = (k * priest.FW, (meta['clips'][clip]['row0'] + direction) * priest.FH)
                colour.paste(Image.fromarray(rgba), position)
                depth.paste(Image.fromarray(rgb), position)
                if pf:
                    pf.draw_grid(sid, k, layer, remap[index])
            if pf:
                updated, frames = pf.load(sid)
                assert updated['palette'] == sprite['palette']
                assert updated['layers'] == sprite['layers']
                for old, new in zip(old_frames, frames):
                    assert all(np.array_equal(a, b) for i, (a, b) in enumerate(zip(old, new)) if i != layer)
            print(sheet.files, clip, facing, flush=True)
    paths = [args.out / f'{sheet.files}_{name}.png', args.out / f'{sheet.files}_{name}_depth.png']
    colour.save(paths[0], optimize=True)
    depth.save(paths[1], optimize=True)
    bounds_path = sprite_bounds.bounds_name(meta_path)
    bounds = json.loads(bounds_path.read_text())
    bounds['parts'][name] = base64.b64encode(sprite_bounds.part_bounds(paths[0], meta)).decode()
    preview_bounds = args.out / bounds_path.name
    preview_bounds.write_text(json.dumps(bounds, separators=(',', ':')) + '\n')
    if args.write:
        for path in paths + [preview_bounds]:
            (priest.ASSETS / path.name).write_bytes(path.read_bytes())
    print('exported', sheet.files, name, flush=True)


if __name__ == '__main__':
    main()
