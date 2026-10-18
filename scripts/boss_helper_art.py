#!/usr/bin/env python3
"""Build, export and verify the own PixelFlow art of the six boss-mechanic helpers (boss_helper_cel_redraw.py).

    python3 scripts/boss_helper_art.py [preview | build | export | verify | all | sheet DIR] [kind ...]

Until 2026-10-18 the helpers borrowed another kind's sprite: client/assets/cathedral.txt listed the helper with a borrowed
sprite id, and the catalog entry said `artFrom`. `build` first drops those ids from the manifest WITHOUT deleting any sprite
(a maker's `build --replace` would delete the sprite of the kind that still uses it), then builds the helper's own sprite in
the maker of its dungeon and exports it into the shared Cathedral atlas set. Safe to run again: a helper that already has an
atlas of its own is left alone by `build`.
"""
import importlib
import json
import sys

import boss_helper_cel_redraw as HC

MAKERS = {'choirsinger': 'make_cathedral_sprites', 'reliquarypearl': 'make_cathedral_sprites',
          'seed_sprout': 'make_seed_vault_sprites', 'seed_treant': 'make_seed_vault_sprites',
          'solar_cinder': 'make_solar_sprites', 'amber_cocoon': 'make_yearwheel_dungeon_sprites'}
BORROWED = {'choirsinger': 'tidecantor', 'reliquarypearl': 'pearlwidow', 'seed_sprout': 'seed_mote',
            'seed_treant': 'seed_rootguard', 'solar_cinder': 'solar_heart', 'amber_cocoon': 'amber_sentinel'}


def by_maker(kinds):
    groups = {}
    for kind in kinds:
        groups.setdefault(MAKERS[kind], []).append(kind)
    return {importlib.import_module(name): ks for name, ks in groups.items()}


def drop_borrowed(kinds):
    """Forget the borrowed sprite ids of helpers that have no atlas of their own yet (never deletes a sprite)."""
    mod = importlib.import_module('make_seed_vault_sprites')
    meta = json.loads(mod.META.read_text())
    todo = []
    for kind in kinds:
        if (mod.ASSETS / f'cathedral_{kind}.png').exists() and kind in meta['sprites']:
            print(kind, 'already has its own sprite', meta['sprites'][kind])
            continue
        meta['sprites'].pop(kind, None)
        meta['tops'].pop(kind, None)
        todo.append(kind)
    mod.META.write_text(json.dumps(meta, indent=2) + '\n')
    return todo


NAMES = dict(choirsinger='Bound Singer', reliquarypearl='Reliquary Pearl', seed_sprout='Worldseed Seed', seed_treant='Bloom Treant',
             solar_cinder='Cinder of the Crucible', amber_cocoon='Amber Cocoon')


def sheet(kinds, out):
    """One PNG per helper for FileDrop: every frame of every clip of its exported atlas, 3x on a dark ground."""
    from pathlib import Path
    from PIL import Image, ImageDraw
    from make_crag_sprites import CLIPS, H, W
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mod = importlib.import_module('make_seed_vault_sprites')
    scale, label = 3, 150
    for kind in kinds:
        atlas = Image.open(mod.ASSETS / f'cathedral_{kind}.png').convert('RGBA')
        page = Image.new('RGBA', (label + 8 * W * scale, 56 + len(CLIPS) * H * scale), '#2c3a44')
        d = ImageDraw.Draw(page)
        d.text((12, 14), f'{NAMES[kind]} ({kind}): own cel-shaded art, 96x96 frames at 3x, foot anchor (48,90)', fill='white')
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            d.text((12, 56 + row * H * scale + 10), f'{clip}\n{count} frames\n{fps} fps', fill=(255, 240, 160, 255))
            for n in range(count):
                tile = atlas.crop((n * W, row * H, (n + 1) * W, (row + 1) * H)).resize((W * scale, H * scale), Image.Resampling.NEAREST)
                page.alpha_composite(tile, (label + n * W * scale, 56 + row * H * scale))
        path = out / f'Boss helper {NAMES[kind]} sprite sheet.png'
        page.convert('RGB').save(path, optimize=True)
        print('sheet', path, path.stat().st_size // 1024, 'KB')


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if command == 'sheet':
        return sheet([k for k in sys.argv[3:] if k in HC.KINDS] or list(HC.KINDS), sys.argv[2])
    kinds = [k for k in sys.argv[2:] if k in HC.KINDS] or list(HC.KINDS)
    if command == 'preview':
        return HC.main()
    if command in ('build', 'all'):
        todo = drop_borrowed(kinds)
        for mod, ks in by_maker(todo).items():
            mod.build(ks)
    if command in ('export', 'all'):
        for mod, ks in by_maker(kinds).items():
            mod.export(ks)
    if command in ('verify', 'all'):
        for mod, ks in by_maker(kinds).items():
            mod.verify(ks)


if __name__ == '__main__':
    main()
