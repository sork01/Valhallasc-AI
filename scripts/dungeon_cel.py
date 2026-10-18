#!/usr/bin/env python3
"""Glue between the dungeon sprite makers (make_<dungeon>_sprites.py, all writing into the shared cathedral.txt atlas
set) and their cel-shaded redraws (<dungeon>_cel_redraw.py, built on cel_arch.py).

In a maker:  `import dungeon_cel; dungeon_cel.install(globals(), '<dungeon>_cel_redraw')` after PALETTES. The maker's
`draw(enemy, clip, n)` then returns the redraw for every kind the redraw lists and the old art for the rest.

Redo a dungeon from its redraw:  python3 scripts/dungeon_cel.py <key>   (preview | build)
  key: eye_below elder_hollow thousandfold rain_crown seed_vault astrolabe thunder blooming solar amber solstice
`build` deletes the PixelFlow sprites of the redrawn kinds, rebuilds them, exports their atlases and verifies them.
"""
import importlib
import json
import sys

MAKERS = dict(eye_below='make_eye_below_sprites', elder_hollow='make_elder_hollow_sprites',
              thousandfold='make_thousandfold_sprites', rain_crown='make_rain_crown_sprites',
              seed_vault='make_seed_vault_sprites', astrolabe='make_astrolabe_sprites',
              thunder='make_astrolabe_sprites', blooming='make_blooming_sprites', solar='make_solar_sprites',
              amber='make_yearwheel_dungeon_sprites', solstice='make_yearwheel_dungeon_sprites')
REDRAWS = dict(eye_below='eye_below_cel_redraw', elder_hollow='elder_hollow_cel_redraw',
               thousandfold='thousandfold_cel_redraw', rain_crown='rain_crown_cel_redraw',
               seed_vault='seed_vault_cel_redraw', astrolabe='astrolabe_cel_redraw', thunder='thunder_cel_redraw',
               blooming='blooming_cel_redraw', solar='solar_cel_redraw', amber='amber_cel_redraw',
               solstice='solstice_cel_redraw')


def install(g, redraw_name):
    """Patch a maker's globals (PALETTES, draw) with the redraw; keeps the old draw as `_old_draw`. A maker that covers
    two dungeons calls this once for each."""
    cel = importlib.import_module(redraw_name)
    g['PALETTES'].update(cel.PALETTES)
    cels = g.setdefault('CELS', [])
    cels.append(cel)
    old = g.setdefault('_old_draw', g['draw'])

    def draw(enemy, clip, n):
        for c in cels:
            if enemy['kind'] in c.KINDS:
                return c.draw(enemy['kind'], clip, n)
        return old(enemy, clip, n)
    g['draw'] = draw


def cel_kinds(key):
    return list(importlib.import_module(REDRAWS[key]).KINDS)


def build(key):
    mod = importlib.import_module(MAKERS[key])
    kinds = cel_kinds(key)
    meta = json.loads(mod.META.read_text())
    for kind in kinds:
        sid = meta['sprites'].pop(kind, None)
        if sid:
            assert mod.api('delete', {'sprite_id': sid}).get('ok'), kind
    mod.META.write_text(json.dumps(meta, indent=2) + '\n')
    mod.build(kinds)
    mod.export(kinds)
    mod.verify(kinds)


def preview(key):
    importlib.import_module(REDRAWS[key]).main()


if __name__ == '__main__':
    key = sys.argv[1]
    {'build': build, 'preview': preview}[sys.argv[2] if len(sys.argv) > 2 else 'preview'](key)
